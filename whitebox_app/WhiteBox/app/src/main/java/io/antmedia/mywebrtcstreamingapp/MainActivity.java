package io.antmedia.mywebrtcstreamingapp;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.media.AudioManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;
import org.webrtc.SurfaceViewRenderer;
import java.net.URISyntaxException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import io.antmedia.webrtcandroidframework.api.IWebRTCClient;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import android.Manifest;
import io.socket.client.IO;
import io.socket.client.Socket;
import androidx.annotation.NonNull;

public class MainActivity extends Activity {


    public static final String SERVER_IP = "192.168.252.64";


    public static final String SOCKET_URL = "https://" + SERVER_IP + ":3000";
    public static final String BASE_URL = "http://" + SERVER_IP + ":5000";
    private static final int BLUETOOTH_PERMISSION_REQUEST_CODE = 1001;
    private static final int CAMERA_REQUEST_CODE = 100;
    private static final int BLUETOOTH_REQUEST_CODE = 101;
    private static final String FIREBASE_URL = "https://whiteboxver3-default-rtdb.asia-southeast1.firebasedatabase.app";
    private static final String VEHICLES_PATH = "vehicles";
    private static final String VEHICLES_POINT_PATH = "vehicles_point";
    private IWebRTCClient webRTCClient;
    private DatabaseReference databaseReference;
    private ValueEventListener vehicleListener;
    private TextView timeTextView;
    private TextView plateNumberTextView;
    private SurfaceViewRenderer surfaceViewRenderer;
    private Socket mSocket;
    private final Handler handler = new Handler();
    private final Runnable updateTask = new Runnable() {
        @Override
        public void run() {
            fetchPlateNumbers();
            handler.postDelayed(this, 1000);  // 1초마다 반복
        }
    };
    private SurfaceView canvasView;
    private SurfaceHolder surfaceHolder;
    private float xCoordinate = 0;
    private float yCoordinate = 0;
    private String lastStreamId = null;
    private List<float[]> personCoordinates = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(R.layout.homescreen);
        surfaceViewRenderer = findViewById(R.id.surface_view_renderer);

        AudioManager audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        audioManager.adjustStreamVolume(AudioManager.STREAM_VOICE_CALL, AudioManager.ADJUST_MUTE, 0);

        requestPermissions();

        databaseReference = FirebaseDatabase.getInstance(FIREBASE_URL).getReference(VEHICLES_PATH);
        timeTextView = findViewById(R.id.time_text);
        plateNumberTextView = findViewById(R.id.vehicle_number_text);
        try {
            mSocket = IO.socket(SOCKET_URL);
            mSocket.on(Socket.EVENT_CONNECT, args -> Log.d("SocketIO", "Connected"))
                    .on(Socket.EVENT_DISCONNECT, args -> Log.d("SocketIO", "Disconnected"));
            mSocket.connect();
        } catch (URISyntaxException e) {
            e.printStackTrace();
        }
        fetchCoordinatesFromFirebase();
        fetchPersonCoordinatesFromFirebase();
        canvasView = findViewById(R.id.canvas_view);
        ViewTreeObserver observer = canvasView.getViewTreeObserver();
        observer.addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override
            public void onGlobalLayout() {
                int width = canvasView.getWidth();
                int height = canvasView.getHeight();
                Log.d("CanvasViewSize", "Canvas width: " + width + ", height: " + height);
                canvasView.getViewTreeObserver().removeOnGlobalLayoutListener(this);
            }
        });
        surfaceHolder = canvasView.getHolder();
        surfaceHolder.addCallback(new SurfaceHolder.Callback() {
            @Override
            public void surfaceCreated(SurfaceHolder holder) {
                drawPointsOnCanvas(xCoordinate, yCoordinate, personCoordinates);
            }
            @Override
            public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
                drawPointsOnCanvas(xCoordinate, yCoordinate, personCoordinates);
            }
            @Override
            public void surfaceDestroyed(SurfaceHolder holder) {
            }
        });
        DatabaseReference detectedNumberRef = FirebaseDatabase.getInstance(FIREBASE_URL).getReference("detected_number");
        detectedNumberRef.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                if (dataSnapshot.exists()) {
                    String detectedNumber = dataSnapshot.getValue(String.class);
                    if (detectedNumber != null) {
                        plateNumberTextView.setText(detectedNumber);
                        fetchStreamingInfo(detectedNumber);
                    } else {
                        plateNumberTextView.setText("차량번호 정보 없음");
                        stopStream();
                    }
                } else {
                    plateNumberTextView.setText("차량번호 정보 없음");
                    stopStream();
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("FirebaseError", "Firebase 데이터 로드 실패: " + databaseError.getMessage());
            }
        });
        Button queryButton = findViewById(R.id.query_vehicle_button);
        queryButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, VehicleListActivity.class);
            startActivity(intent);
        });
        Button registerButton = findViewById(R.id.register_vehicle_button);
        registerButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, RegisterVehicleActivity.class);
            startActivity(intent);
        });
        handler.post(updateTask);
        listenForVehicleNumberUpdates();
    }

    private void fetchStreamingInfo(String plateNumber) {
        DatabaseReference vehicleRef = FirebaseDatabase.getInstance(FIREBASE_URL).getReference("vehicles").child(plateNumber);
        vehicleRef.addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                if (dataSnapshot.exists() && dataSnapshot.hasChild("serverUrl") && dataSnapshot.hasChild("streamId")) {
                    String serverUrl = dataSnapshot.child("serverUrl").getValue(String.class);
                    String streamId = dataSnapshot.child("streamId").getValue(String.class);
                    if (serverUrl != null && streamId != null) {
                        startWebRTCStream(serverUrl, streamId);
                    } else {
                        stopStreamWithDelay();
                    }
                } else {
                    stopStreamWithDelay();
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                stopStreamWithDelay();  // 데이터 로드 실패 시에도 5초 후 스트림 중지
            }
        });
    }
    private void startWebRTCStream(String serverUrl, String streamId) {
        if (webRTCClient != null && lastStreamId != null) {
            webRTCClient.stop(lastStreamId);  // 마지막 스트림 중단
        }
        lastStreamId = streamId;  // 새로운 스트림 ID 저장
        webRTCClient = IWebRTCClient.builder()
                .setActivity(this)
                .addRemoteVideoRenderer(surfaceViewRenderer)
                .setServerUrl(serverUrl)
                .build();
        webRTCClient.play(streamId);  // 새로운 스트림 재생
    }
    private void stopStream() {
        if (webRTCClient != null && lastStreamId != null) {
            try {
                webRTCClient.stop(lastStreamId);  // 현재 스트림 중단
                lastStreamId = null;  // 마지막 스트림 ID를 초기화
            } catch (IllegalStateException e) {
                Log.e("WebRTCError", "DataChannel has been disposed or WebRTC client is already stopped.", e);
            }
        }
        if (surfaceViewRenderer != null) {
            surfaceViewRenderer.setVisibility(View.VISIBLE);
        }
    }
    private void stopStreamWithDelay() {
        new Handler().postDelayed(() -> {
            try {
                stopStream();  // 5초 후 스트림 중단
            } catch (IllegalStateException e) {
                Log.e("WebRTCError", "Error stopping the stream after delay.", e);
            }
        }, 5000);
    }

    private void fetchCoordinatesFromFirebase() {
        DatabaseReference vehicleCoordinatesRef = FirebaseDatabase.getInstance().getReference("vehicles_point");
        vehicleCoordinatesRef.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                if (dataSnapshot.exists()) {
                    for (DataSnapshot pointSnapshot : dataSnapshot.getChildren()) {
                        Double x = pointSnapshot.child("x").getValue(Double.class);
                        Double y = pointSnapshot.child("y").getValue(Double.class);
                        if (x != null && y != null) {
                            xCoordinate = x.floatValue();
                            yCoordinate = y.floatValue();
                            drawPointsOnCanvas(xCoordinate, yCoordinate, personCoordinates);
                        }
                    }
                } else {
                    Log.e("Firebase", "Firebase 데이터가 존재하지 않습니다.");
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("FirebaseError", "Firebase 데이터 로드 실패: " + databaseError.getMessage());
            }
        });
    }
    private void fetchPersonCoordinatesFromFirebase() {
        DatabaseReference personCoordinatesRef = FirebaseDatabase.getInstance().getReference("Coordinates");
        personCoordinatesRef.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                if (dataSnapshot.exists()) {
                    personCoordinates.clear();
                    for (DataSnapshot personSnapshot : dataSnapshot.getChildren()) {
                        if (personSnapshot.getKey().startsWith("Person")) {
                            Double x = personSnapshot.child("x").getValue(Double.class);
                            Double y = personSnapshot.child("y").getValue(Double.class);
                            if (x != null && y != null) {
                                personCoordinates.add(new float[]{x.floatValue(), y.floatValue()});
                            }
                        }
                    }
                    drawPointsOnCanvas(xCoordinate, yCoordinate, personCoordinates);
                } else {
                    Log.e("PersonCoordinates", "Firebase 데이터가 존재하지 않습니다.");
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("PersonCoordinates", "Firebase 데이터 로드 실패: " + databaseError.getMessage());
            }
        });
    }
    private void drawPointsOnCanvas(float vehicleX, float vehicleY, List<float[]> personCoordinates) {
        if (surfaceHolder.getSurface().isValid()) {
            Canvas canvas = surfaceHolder.lockCanvas();  // Canvas 잠금

            Bitmap backgroundBitmap = BitmapFactory.decodeResource(getResources(), R.drawable.school);  // 스쿨존 배경 이미지
            Bitmap scaledBitmap = Bitmap.createScaledBitmap(backgroundBitmap, canvas.getWidth(), canvas.getHeight(), true);  // 스케일링
            canvas.drawBitmap(scaledBitmap, 0, 0, null);  // 캔버스에 배경 그리기

            Paint vehiclePaint = new Paint();
            vehiclePaint.setColor(Color.RED);
            vehiclePaint.setAntiAlias(true);
            vehiclePaint.setStyle(Paint.Style.FILL);

            Paint personPaint = new Paint();
            personPaint.setColor(Color.BLUE);
            personPaint.setAntiAlias(true);
            personPaint.setStyle(Paint.Style.FILL);

            int radius = 40;

            float aX =(vehicleX/768)*1200-150;
            float aY =(vehicleY/854)*900;

            canvas.drawCircle(aX, aY, radius, vehiclePaint);

            // 중점 좌표를 설정 (캔버스 뷰의 중점 좌표)
            float centerX = 384;  // 가로의 절반
            float centerY = 427;  // 세로의 절반

            // 여러 사람의 좌표에 대해 변환 후 그리기
            for (float[] coords : personCoordinates) {
                // 중점을 기준으로 대칭 좌표 계산
                float newX = (2 * centerX - coords[0]);  // x좌표를 중점 기준으로 반전
                float newY = (2 * centerY - coords[1]);  // y좌표를 중점 기준으로 반전

                float bX =(newX/768)*1320-300;
                float bY =(newY/854)*1260;

                // 변환된 좌표에 파란 점 그리기
                canvas.drawCircle((float) (bX*1.25)-50, (float) (bY*0.6)-100, radius, personPaint);  // 대칭된 좌표에 원 그리기
            }
            surfaceHolder.unlockCanvasAndPost(canvas);  // Canvas 잠금 해제 및 그리기 완료
        }
    }

    private void updateUI(String plateNumber, String timestamp, boolean isRegistered) {
        runOnUiThread(() -> {
            if (plateNumberTextView != null && timeTextView != null) {
                plateNumberTextView.setText(plateNumber);
                timeTextView.setText(timestamp);

                if (isRegistered) {
                    if (surfaceViewRenderer != null) {
                        surfaceViewRenderer.setVisibility(View.VISIBLE);
                    }
                    findViewById(R.id.vehicle_error_text).setVisibility(View.GONE);
                } else {
                    if (surfaceViewRenderer != null) {
                        surfaceViewRenderer.setVisibility(View.GONE);
                    }
                    findViewById(R.id.vehicle_error_text).setVisibility(View.VISIBLE);
                }
            } else {
                Log.e("TextViewError", "TextView 중 하나가 null입니다.");
            }
        });
    }
    private void fetchPlateNumbers() {
        RetrofitService retrofitService = RetrofitClient.getInstance();
        retrofitService.getPlateNumbers().enqueue(new Callback<PlateNumbersResponse>() {
            @Override
            public void onResponse(Call<PlateNumbersResponse> call, Response<PlateNumbersResponse> response) {
                if (response.isSuccessful()) {
                    PlateNumbersResponse responseBody = response.body();
                    if (responseBody != null && responseBody.getPlateNumbers() != null && !responseBody.getPlateNumbers().isEmpty()) {
                        List<PlateNumbersResponse.PlateNumberData> plateNumbers = responseBody.getPlateNumbers();
                        PlateNumbersResponse.PlateNumberData latestPlateData = plateNumbers.get(plateNumbers.size() - 1);
                        String latestPlateNumber = latestPlateData.getPlateNumber();
                        String timestamp = latestPlateData.getTimestamp();

                        DatabaseReference detectedNumberRef = FirebaseDatabase.getInstance(FIREBASE_URL).getReference("detected_number");
                        detectedNumberRef.setValue(latestPlateNumber);

                        checkVehicleNumber(latestPlateNumber, timestamp);
                    } else {
                        Log.d("VehicleInfo", "서버로부터 차량번호 리스트가 비어있습니다.");
                        updateUI("차량번호 정보 없음", "시간 정보 없음", false);
                    }
                } else {
                    Log.e("RetrofitError", "응답 실패: " + response.errorBody());
                }
            }
            @Override
            public void onFailure(Call<PlateNumbersResponse> call, Throwable t) {
                Log.e("RetrofitError", "서버 통신 실패: " + t.getMessage());
            }
        });
    }
    private void checkVehicleNumber(String latestPlateNumber, String timestamp) {
        databaseReference.addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                boolean isRegistered = false;
                for (DataSnapshot snapshot : dataSnapshot.getChildren()) {
                    String registeredPlateNumber = snapshot.getKey();
                    Log.d("VehicleCheck", "비교할 등록된 차량번호: " + registeredPlateNumber);
                    Log.d("VehicleCheck", "비교할 인식된 차량번호: " + latestPlateNumber);
                    if (registeredPlateNumber != null && registeredPlateNumber.trim().equals(latestPlateNumber.trim())) {
                        isRegistered = true;
                        break;
                    }
                }
                if (isRegistered) {
                    Log.d("VehicleCheck", "차량번호 일치: " + latestPlateNumber);
                    updateUI(latestPlateNumber, timestamp, true);
                } else {
                    Log.d("VehicleCheck", "차량번호 불일치: " + latestPlateNumber);
                    updateUI(latestPlateNumber, timestamp, false);
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("FirebaseError", "Firebase 데이터 로드 실패: " + databaseError.getMessage());
            }
        });
    }
    private void listenForVehicleNumberUpdates() {
        vehicleListener = new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                String latestPlateNumber = null;

                long latestTimestamp = 0;
                for (DataSnapshot snapshot : dataSnapshot.getChildren()) {
                    Long timestamp = snapshot.child("timestamp").getValue(Long.class);
                    String plateNumber = snapshot.child("plateNumber").getValue(String.class);

                    if (timestamp != null && plateNumber != null && timestamp > latestTimestamp) {
                        latestTimestamp = timestamp;
                        latestPlateNumber = plateNumber;
                    }
                }
                if (latestPlateNumber != null) {
                    String formattedTime = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date(latestTimestamp));
                    updateUI(latestPlateNumber, formattedTime, true);
                    fetchStreamingInfo(latestPlateNumber);
                } else {
                    updateUI("차량번호 정보 없음", "시간 정보 없음", false);
                }
            }
            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("FirebaseError", "Firebase 데이터 로드 실패: " + databaseError.getMessage());
            }
        };
        databaseReference.addValueEventListener(vehicleListener);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            } else {
                Toast.makeText(this, "카메라 권한이 필요합니다.", Toast.LENGTH_SHORT).show();
            }
        } else if (requestCode == BLUETOOTH_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            } else {
                Toast.makeText(this, "블루투스 권한이 필요합니다.", Toast.LENGTH_SHORT).show();
            }
        }
    }
    private void requestPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CAMERA}, CAMERA_REQUEST_CODE);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.BLUETOOTH_CONNECT}, BLUETOOTH_PERMISSION_REQUEST_CODE);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (webRTCClient != null) {
            webRTCClient.stop(lastStreamId);
        }
        if (surfaceViewRenderer != null) {
            surfaceViewRenderer.release();
        }
        if (databaseReference != null && vehicleListener != null) {
            databaseReference.removeEventListener(vehicleListener);
        }
        handler.removeCallbacks(updateTask);
    }
}