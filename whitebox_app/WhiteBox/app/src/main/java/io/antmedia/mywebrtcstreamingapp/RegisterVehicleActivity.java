package io.antmedia.mywebrtcstreamingapp;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;
import java.util.regex.Pattern;

public class RegisterVehicleActivity extends Activity {

    private EditText vehicleNumberEditText;
    private TextView errorTextView;
    private Button registerButton, backButton;
    private DatabaseReference databaseReference;

    private static final Pattern VEHICLE_NUMBER_PATTERN = Pattern.compile("^\\d{3}[가-힣]\\d{4}$");

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_register_vehicle);

        vehicleNumberEditText = findViewById(R.id.vehicle_number_input);
        registerButton = findViewById(R.id.register_button);
        backButton = findViewById(R.id.back_button);
        errorTextView = findViewById(R.id.error_message);

        databaseReference = FirebaseDatabase.getInstance().getReference("vehicles");

        registerButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String vehicleNumber = vehicleNumberEditText.getText().toString().trim();
                errorTextView.setText("");
                if (TextUtils.isEmpty(vehicleNumber)) {
                    errorTextView.setText("차량번호를 입력해주세요.");
                    return;
                }
                if (!VEHICLE_NUMBER_PATTERN.matcher(vehicleNumber).matches()) {
                    errorTextView.setText("다시 입력해주세요.");
                    return;
                }
                databaseReference.child(vehicleNumber).addListenerForSingleValueEvent(new ValueEventListener() {
                    @Override
                    public void onDataChange(DataSnapshot snapshot) {
                        if (snapshot.exists()) {
                            errorTextView.setText("이미 등록된 차량번호입니다.");
                        } else {
                            databaseReference.child(vehicleNumber).setValue(true)
                                    .addOnSuccessListener(aVoid -> {
                                        Toast.makeText(RegisterVehicleActivity.this, "차량번호 등록 완료", Toast.LENGTH_SHORT).show();
                                        vehicleNumberEditText.setText("");
                                        errorTextView.setText("");
                                        finish();
                                    })
                                    .addOnFailureListener(e -> {
                                        Toast.makeText(RegisterVehicleActivity.this, "차량번호 등록 실패", Toast.LENGTH_SHORT).show();
                                    });
                        }
                    }
                    @Override
                    public void onCancelled(DatabaseError error) {
                        Toast.makeText(RegisterVehicleActivity.this, "데이터베이스 오류", Toast.LENGTH_SHORT).show();
                    }
                });
            }
        });
        backButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });
    }
}
