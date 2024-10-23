import serial
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# Firebase 초기화
#cred = credentials.Certificate('D:/vscode/ESWCAR/esw2024-streaming-service-firebase-adminsdk-aqj00-8d08bb6457.json')
cred = credentials.Certificate("D:/vscode/ESWCAR/whiteboxver3-firebase-adminsdk-y5cgl-9b689f6f51.json")

#firebase_admin.initialize_app(cred, {'databaseURL': 'https://esw2024-streaming-service-default-rtdb.firebaseio.com/'})  # Firebase 데이터베이스 URL 입력
firebase_admin.initialize_app(cred, {'databaseURL': 'https://whiteboxver3-default-rtdb.asia-southeast1.firebasedatabase.app/'})
                            

# 아두이노와 시리얼 통신 설정
arduino = serial.Serial('COM10', 9600) 
time.sleep(2)  # 아두이노 초기화 시간 대기

def get_flag_value():
    ref = db.reference('/Warning by Line')
    return ref.get()

def main():
    previous_flag = None
    while True:
        try:
            flag_value = get_flag_value()
            if flag_value != previous_flag:
                print(f"Flag value changed to: {flag_value}")
                if flag_value == 2:
                    arduino.write(b'2')
                elif flag_value == 1:
                    arduino.write(b'1')  # 아두이노로 '1' 전송
                else:
                    arduino.write(b'0')  # 아두이노로 '0' 전송

                previous_flag = flag_value

            # 아두이노로부터 응답 읽기
            while arduino.in_waiting:
                response = arduino.readline().decode().strip()
                #print(f"Arduino: {response}")

            time.sleep(0.05)  # 1초마다 확인

        except KeyboardInterrupt:
            print("프로그램 종료")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()

