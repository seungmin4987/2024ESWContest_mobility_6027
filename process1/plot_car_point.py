import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import firebase_admin
from firebase_admin import credentials, db

# Firebase 설정
cred = credentials.Certificate("whiteboxver3-firebase-adminsdk-y5cgl-1dc5246022.json")  # 서비스 계정 키 파일 경로
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://whiteboxver3-default-rtdb.asia-southeast1.firebasedatabase.app/'  # Firebase 실시간 데이터베이스 URL
})

reader = SimpleMFRC522()

MYID = "111ga1111"

# 루크업 테이블 (예시로 UID와 해당 2차원 좌표값을 매핑)
lookup_table = {
    472588347898: (525, 20), 1026471291277: (525, 20), 268191525331: (675, 20), 888747125182: (675, 20), 339008088381: (675, 20),
    817930561874: (525, 140), 886515820858: (525, 140), 336659343792: (675, 140), 270557047133: (675, 140), 820145088983: (675, 140),
    888730347967: (525, 260), 338991311166: (525, 260), 476598036740: (675, 260), 1026337073541: (675, 260), 335266834909: (675, 260),
    885022648669: (525, 380), 955134634272: (525, 380), 405395597729: (675, 380), 955151411489: (675, 380), 338890647860: (675, 380),
    888646461876: (525, 500), 338907425083: (525, 500), 820279306719: (675, 500), 270540269918: (675, 500), 820296083934: (675, 500),
    335283612098: (525, 620), 884871653716: (525, 620), 335132617173: (675, 620), 817947339091: (675, 620), 268208302544: (675, 620),
    818064779610: (525, 740), 336776784315: (525, 740), 886532598075: (675, 740), 336793561528: (675, 740), 476732254476: (675, 740),
    1026488068492: (525, 860), 472454130162: (525, 860), 270406052182: (675, 860), 820161866198: (675, 860), 270422829397: (675, 860),
    1022327384437: (525, 980), 472571570677: (525, 980), 955637950914: (675, 980), 1094922332557: (675, 980), 476614813963: (675, 980),
    1026353850756: (525, 1100), 1094939109772: (525, 1100), 231318126130: (675, 1100), 816135399719: (675, 1100), 266396363172: (675, 1100)
}

previous_coordinates = None  # 이전 좌표 저장 변수
previous_time = None  # 이전 시간 저장 변수

def upload_coordinates_to_firebase(myid, coordinates):
    """Firebase에 차량의 현재 좌표를 업로드"""
    data = {
        'x': coordinates[0],  # 현재 x 좌표
        'y': coordinates[1],  # 현재 y 좌표
        'timestamp': time.time()  # 타임스탬프 추가
    }

    ref = db.reference(f'/vehicles_point/{myid}')  # 차량 데이터가 저장될 경로
    ref.set(data)
    print(f"Firebase에 차량 ID {myid}의 좌표 {coordinates} 업로드 완료.")

try:
    while True:
        print("RFID 스캔...")
        uid, text = reader.read()  # RFID 태그 읽기
        print(f"카드 UID: {uid}")

        # 루크업 테이블에서 해당 ID가 있는지 확인
        if uid in lookup_table:
            current_coordinates = lookup_table[uid]  # UID에 대응하는 2차원 좌표값
            print(f"현재 좌표: {current_coordinates}")
            
            # Firebase에 현재 좌표 업로드
            upload_coordinates_to_firebase(MYID, current_coordinates)

            # 현재 좌표와 시간을 저장하여 다음 루프에서 사용
            previous_coordinates = current_coordinates
            previous_time = time.time()  # 현재 시간 저장
        else:
            print("루크업 테이블에 등록되지 않은 UID입니다.")

        time.sleep(0.1)  # 0.1초 대기 후 다시 감지 시작

finally:
    GPIO.cleanup()

