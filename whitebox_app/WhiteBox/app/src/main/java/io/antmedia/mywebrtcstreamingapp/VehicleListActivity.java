package io.antmedia.mywebrtcstreamingapp;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;
import java.util.ArrayList;
import java.util.Collections;

public class VehicleListActivity extends Activity {

    private ListView listView;
    private Button backButton;
    private ArrayAdapter<String> adapter;
    private ArrayList<String> vehicleNumbersList;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_vehicle_list);

        listView = findViewById(R.id.list_view);
        backButton = findViewById(R.id.back_button);
        vehicleNumbersList = new ArrayList<>();
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, vehicleNumbersList);
        listView.setAdapter(adapter);

        DatabaseReference databaseReference = FirebaseDatabase.getInstance().getReference("vehicles");

        databaseReference.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                vehicleNumbersList.clear();
                for (DataSnapshot snapshot : dataSnapshot.getChildren()) {
                    String vehicleNumber = snapshot.getKey();
                    Log.d("VehicleList", "Retrieved vehicle number: " + vehicleNumber);
                    vehicleNumbersList.add(vehicleNumber);
                }
                Collections.sort(vehicleNumbersList);
                adapter.notifyDataSetChanged();
            }

            @Override
            public void onCancelled(DatabaseError databaseError) {
                Log.e("VehicleList", "Error retrieving vehicle numbers: " + databaseError.getMessage());
            }
        });
        backButton.setOnClickListener(v -> finish());
    }
}
