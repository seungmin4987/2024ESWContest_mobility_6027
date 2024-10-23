# 2024_ESW_whitebox

# 프로젝트 개요


# 프로젝트 구성

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

```

## 프로세스 설명

### Process 1
- **Hardware.ino**: 하드웨어 제어를 위한 코드가 포함되어 있으며, 특정 센서나 장치와 상호작용합니다.
- **plate_recognition.py**: 번호판 인식 알고리즘이 구현되어 있습니다.
- **plot_car_point.py**: 차량의 위치를 시각화하는 스크립트입니다.

### Process 2
- **flag.py**: 제어 신호와 관련된 플래그 설정을 처리합니다.
- **objsort.py**: 물체를 정렬하고 처리하는 로직이 구현되어 있습니다.

## 어플리케이션 설명

### Whitebox App
`whitebox_app` 디렉토리에는 앱의 소스 코드가 위치하며, `MainActivity.java`를 통해 앱의 메인 기능이 구현됩니다. Retrofit을 사용하여 서버와 통신하고, 차량 정보를 처리하는 여러 액티비티들이 포함되어 있습니다.

