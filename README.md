# 2024_ESW_whitebox
2024_esw_whitebox

# 프로젝트 디렉토리 구조

이 문서는 핵심 코드와 관련된 디렉토리 구조를 설명합니다.

## 디렉토리 구조

```bash
.
├── process1
│   ├── Hardware
│   │   └── Hardware.ino
│   ├── plate_recognition.py
│   ├── plot_car_point.py
│   ├── send_plate_number_to_firebase.py
│   └── WebRTC
│       ├── css
│       │   └── main.css
│       ├── index.html
│       ├── index.js
│       ├── js
│       │   └── main.js
│       ├── package.json
│       ├── package-lock.json
│       ├── private.pem
│       ├── public.pem
│       └── README.md
├── process2
│   ├── flag.py
│   ├── Hardware
│   │   └── Hardware.ino
│   ├── main.py
│   └── objsort.py
├── README.md
└── whitebox_app
    └── WhiteBox
        └── app
            └── src
                └── main
                    └── java
                        └── io
                            └── antmedia
                                └── mywebrtcstreamingapp
                                    ├── MainActivity.java
                                    ├── PlateNumbersResponse.java
                                    ├── RegisterVehicleActivity.java
                                    ├── RetrofitClient.java
                                    ├── RetrofitService.java
                                    └── VehicleListActivity.java
