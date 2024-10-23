from flask import Flask, request, jsonify
import logging
import urllib.parse
import firebase_admin
from firebase_admin import credentials, db

# Firebase 초기화
cred = credentials.Certificate('/home/whitebox/whitebox_ws/whiteboxver3-firebase-adminsdk-y5cgl-f85b7a6b1c.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://whiteboxver3-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

app = Flask(__name__)

# 저장된 차량 번호를 관리할 리스트
plate_numbers = []

# 로그 레벨을 ERROR로 설정하여 기본 요청 로그를 숨깁니다.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/send_plate_number', methods=['POST'])
def receive_plate_number():
    data = request.get_json()
    plate_number = data.get('plate_number')
    timestamp = data.get('timestamp')

    if plate_number and timestamp:
        # 차량번호와 시간을 함께 저장
        plate_numbers.append({"plate_number": plate_number, "timestamp": timestamp})
        print(f"Received plate number: {plate_number} at {timestamp}")

        # Firebase Realtime Database에 데이터 전송
        ref = db.reference('detected_number')
        ref.set(plate_number)  # 차량번호를 Firebase에 설정
        

        return jsonify({"message": "Plate number and timestamp received, and data sent to Firebase"}), 200
    else:
        return jsonify({"error": "No plate number or timestamp provided"}), 400

@app.route('/getLatestPlateNumber', methods=['GET'])
def get_latest_plate_number():
    latest_plate_data = plate_numbers[-1] if plate_numbers else {}
    # 차량번호와 timestamp 객체 반환
    return jsonify(latest_plate_data), 200

@app.route('/get_plate_numbers', methods=['GET'])
def get_plate_numbers():
    # plate_numbers 객체 리스트 반환
    return jsonify({"plate_numbers": plate_numbers}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

