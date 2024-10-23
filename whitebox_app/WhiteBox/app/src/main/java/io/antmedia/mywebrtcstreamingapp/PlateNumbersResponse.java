package io.antmedia.mywebrtcstreamingapp;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class PlateNumbersResponse {

    @SerializedName("plate_numbers")
    private List<PlateNumberData> plateNumbers;

    public List<PlateNumberData> getPlateNumbers() {
        return plateNumbers;
    }

    public void setPlateNumbers(List<PlateNumberData> plateNumbers) {
        this.plateNumbers = plateNumbers;
    }

    // 내부 PlateNumberData 클래스를 추가하여 timestamp를 처리
    public static class PlateNumberData {
        @SerializedName("plate_number")
        private String plateNumber;

        @SerializedName("timestamp")
        private String timestamp;

        public String getPlateNumber() {
            return plateNumber;
        }

        public void setPlateNumber(String plateNumber) {
            this.plateNumber = plateNumber;
        }

        public String getTimestamp() {
            return timestamp;
        }

        public void setTimestamp(String timestamp) {
            this.timestamp = timestamp;
        }
    }
}
