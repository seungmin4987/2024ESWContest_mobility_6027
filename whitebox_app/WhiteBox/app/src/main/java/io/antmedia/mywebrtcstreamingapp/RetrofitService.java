package io.antmedia.mywebrtcstreamingapp;

import retrofit2.Call;
import retrofit2.http.GET;

public interface RetrofitService {
    @GET("/get_plate_numbers")
    Call<PlateNumbersResponse> getPlateNumbers();
}
