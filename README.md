# 2024_ESW_whitebox
2024_esw_whitebox

# 프로젝트 디렉토리 구성

프로젝트는 크게 두가지의 프로세스(process1, process2)로 구분되며, 이를 통합하는 어플리케이션 (whitebox_app)으로 구성된다.

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
