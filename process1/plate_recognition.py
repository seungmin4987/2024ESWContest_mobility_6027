import os
import cv2
import numpy as np
import pytesseract
import collections
import time
import requests
import RPi.GPIO as GPIO
from datetime import datetime

# Set up GPIO
GPIO.setmode(GPIO.BCM)  # BCM pin-numbering scheme from the board
pin_to_read = 17        # Set the GPIO pin you want to read (e.g., GPIO 17)
GPIO.setup(pin_to_read, GPIO.IN)

# TESSDATA_PREFIX 환경 변수 설정
os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/4.00/tessdata/"

# 캠 설정
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

# 결과 저장을 위한 변수
recognized_numbers = collections.defaultdict(int)
last_recognized_number = None
no_recognition_counter = 0

# 타임아웃 설정 (초 단위)
timeout = 10  # 10초 동안 번호판 인식이 없을 경우, 이를 기록하지만 프로그램은 종료되지 않음
last_recognition_time = time.time()

# 재전송 간격 (초 단위)
resend_interval = 5  # 5초 이후에 중복 전송 허용
last_sent_time = time.time()

while True:

    input_state = GPIO.input(pin_to_read)
    
    # If GPIO is LOW, send "000가0000" to the REST API and skip the recognition process
    if input_state == GPIO.LOW:
        current_time = time.time()
        print(f"GPIO LOW detected! Sending fake plate number '000가0000' at {current_time}")
        
        # Send the fake plate number to the REST API
        url = 'http://127.0.0.1:5000/send_plate_number'
        fake_data = {
            'plate_number': '000가0000', 
            'timestamp': current_time
        }
        response = requests.post(url, json=fake_data)

        if response.status_code != 200:
            print("Failed to send fake plate number")
        else:
            print("Fake plate number '000가0000' sent successfully")
        
        time.sleep(1)  # Avoid flooding the server
        continue


    start_time = time.time()
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        break

    img_ori = frame
    height, width, channel = img_ori.shape

    # Step 1: Preprocessing

    gray = cv2.cvtColor(img_ori, cv2.COLOR_BGR2GRAY)
    
    structuringElement = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    imgTopHat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, structuringElement)
    imgBlackHat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, structuringElement)
    
    imgGrayscalePlusTopHat = cv2.add(gray, imgTopHat)
    gray = cv2.subtract(imgGrayscalePlusTopHat, imgBlackHat)
    
    img_blurred = cv2.GaussianBlur(gray, ksize=(5, 5), sigmaX=0)
    
    img_thresh = cv2.adaptiveThreshold(
        img_blurred,
        maxValue=255.0,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY_INV,
        blockSize=19,
        C=9
    )

    # Step 2: Finding Contours
    
    contours, _ = cv2.findContours(
        img_thresh,
        mode=cv2.RETR_LIST,
        method=cv2.CHAIN_APPROX_SIMPLE
    )

    # Step 3: Filtering Contours
    contours_dict = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        contours_dict.append({
            'contour': contour,
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'cx': x + (w / 2),
            'cy': y + (h / 2)
        })

    MIN_AREA = 80
    MIN_WIDTH, MIN_HEIGHT = 2, 8
    MIN_RATIO, MAX_RATIO = 0.25, 1.0

    possible_contours = []
    cnt = 0
    for d in contours_dict:
        area = d['w'] * d['h']
        ratio = d['w'] / d['h']

        if area > MIN_AREA and d['w'] > MIN_WIDTH and d['h'] > MIN_HEIGHT and MIN_RATIO < ratio < MAX_RATIO:
            d['idx'] = cnt
            cnt += 1
            possible_contours.append(d)

    # Step 4: Finding Chars
    MAX_DIAG_MULTIPLYER = 5
    MAX_ANGLE_DIFF = 12.0
    MAX_AREA_DIFF = 0.5
    MAX_WIDTH_DIFF = 0.8
    MAX_HEIGHT_DIFF = 0.2
    MIN_N_MATCHED = 3

    def find_chars(contour_list):
        matched_result_idx = []

        for d1 in contour_list:
            matched_contours_idx = []
            for d2 in contour_list:
                if d1['idx'] == d2['idx']:
                    continue

                dx = abs(d1['cx'] - d2['cx'])
                dy = abs(d1['cy'] - d2['cy'])

                diagonal_length1 = np.sqrt(d1['w'] ** 2 + d1['h'] ** 2)

                distance = np.linalg.norm(np.array([d1['cx'], d1['cy']]) - np.array([d2['cx'], d2['cy']]))
                if dx == 0:
                    angle_diff = 90
                else:
                    angle_diff = np.degrees(np.arctan(dy / dx))
                area_diff = abs(d1['w'] * d1['h'] - d2['w'] * d2['h']) / (d1['w'] * d1['h'])
                width_diff = abs(d1['w'] - d2['w']) / d1['w']
                height_diff = abs(d1['h'] - d2['h']) / d1['h']

                if distance < diagonal_length1 * MAX_DIAG_MULTIPLYER and angle_diff < MAX_ANGLE_DIFF and area_diff < MAX_AREA_DIFF and width_diff < MAX_WIDTH_DIFF and height_diff < MAX_HEIGHT_DIFF:
                    matched_contours_idx.append(d2['idx'])

            matched_contours_idx.append(d1['idx'])

            if len(matched_contours_idx) < MIN_N_MATCHED:
                continue

            matched_result_idx.append(matched_contours_idx)

            unmatched_contour_idx = []
            for d4 in contour_list:
                if d4['idx'] not in matched_contours_idx:
                    unmatched_contour_idx.append(d4['idx'])

            unmatched_contour = np.take(possible_contours, unmatched_contour_idx)

            recursive_contour_list = find_chars(unmatched_contour)

            for idx in recursive_contour_list:
                matched_result_idx.append(idx)

            break

        return matched_result_idx

    result_idx = find_chars(possible_contours)

    # Step 5: Extracting Plate
    matched_result = []
    for idx_list in result_idx:
        matched_result.append(np.take(possible_contours, idx_list))

    PLATE_WIDTH_PADDING = 1.3
    PLATE_HEIGHT_PADDING = 1.5
    MIN_PLATE_RATIO = 3
    MAX_PLATE_RATIO = 10

    plate_imgs = []
    plate_infos = []

    for i, matched_chars in enumerate(matched_result):
        sorted_chars = sorted(matched_chars, key=lambda x: x['cx'])

        plate_cx = (sorted_chars[0]['cx'] + sorted_chars[-1]['cx']) / 2
        plate_cy = (sorted_chars[0]['cy'] + sorted_chars[-1]['cy']) / 2

        plate_width = (sorted_chars[-1]['x'] + sorted_chars[-1]['w'] - sorted_chars[0]['x']) * PLATE_WIDTH_PADDING

        sum_height = 0
        for d in sorted_chars:
            sum_height += d['h']

        plate_height = int(sum_height / len(sorted_chars) * PLATE_HEIGHT_PADDING)

        triangle_height = sorted_chars[-1]['cy'] - sorted_chars[0]['cy']
        triangle_hypotenus = np.linalg.norm(
            np.array([sorted_chars[0]['cx'], sorted_chars[0]['cy']]) -
            np.array([sorted_chars[-1]['cx'], sorted_chars[-1]['cy']])
        )

        angle = np.degrees(np.arcsin(triangle_height / triangle_hypotenus))

        rotation_matrix = cv2.getRotationMatrix2D(center=(plate_cx, plate_cy), angle=angle, scale=1.0)

        img_rotated = cv2.warpAffine(img_thresh, M=rotation_matrix, dsize=(width, height))

        img_cropped = cv2.getRectSubPix(
            img_rotated,
            patchSize=(int(plate_width), int(plate_height)),
            center=(int(plate_cx), int(plate_cy))
        )

        if img_cropped.shape[1] / img_cropped.shape[0] < MIN_PLATE_RATIO or img_cropped.shape[1] / img_cropped.shape[0] > MAX_PLATE_RATIO:
            continue

        plate_imgs.append(img_cropped)
        plate_infos.append({
            'x': int(plate_cx - plate_width / 2),
            'y': int(plate_cy - plate_height / 2),
            'w': int(plate_width),
            'h': int(plate_height)
        })

    # Step 6: OCR
    recognized_this_frame = False
    for i, plate_img in enumerate(plate_imgs):
        if plate_img.size == 0:
            print(f"Skipping empty plate image at index {i}")
            continue

        plate_img = cv2.resize(plate_img, dsize=(0, 0), fx=1.6, fy=1.6)
        _, plate_img = cv2.threshold(plate_img, thresh=0.0, maxval=255.0, type=cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(plate_img, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)

        plate_min_x, plate_min_y = plate_img.shape[1], plate_img.shape[0]
        plate_max_x, plate_max_y = 0, 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            area = w * h
            ratio = w / h

            if area > MIN_AREA and w > MIN_WIDTH and h > MIN_HEIGHT and MIN_RATIO < ratio < MAX_RATIO:
                if x < plate_min_x:
                    plate_min_x = x
                if y < plate_min_y:
                    plate_min_y = y
                if x + w > plate_max_x:
                    plate_max_x = x + w
                if y + h > plate_max_y:
                    plate_max_y = y + h

        if plate_min_x < plate_max_x and plate_min_y < plate_max_y:
            img_result = plate_img[plate_min_y:plate_max_y, plate_min_x:plate_max_x]

            img_result = cv2.GaussianBlur(img_result, ksize=(3, 3), sigmaX=0)
            _, img_result = cv2.threshold(img_result, thresh=0.0, maxval=255.0, type=cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            img_result = cv2.copyMakeBorder(img_result, top=10, bottom=10, left=10, right=10, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))

            # OCR: 한글과 숫자를 모두 인식하도록 설정 변경
            chars = pytesseract.image_to_string(img_result, lang='kor+eng', config='--psm 7 --oem 0')

            result_chars = ''
            for c in chars:
                if c.isdigit() or u'\uAC00' <= c <= u'\uD7A3':
                    result_chars += c

            # 유효한 한글 글자 리스트
            valid_hangul = [
            '가','나','다','라','마',				# 자가용
            '거','너','더','러','머','버','서','어','저',	# 자가용
            '고','노','도','로','모','보','소','오','조',	# 자가용
            '구','누','두','루','무','부','수','우','주',	# 자가용
            '바','사','아','자',				# 영업용
            '배',						# 영업용(택배)
            '하','허','호'					# 렌터카
            ]

            # 결과 문자열 길이가 8자리이고, 4번째 자리가 유효한 한글인 경우에만 인식된 것으로 처리
            if len(result_chars) == 8 and result_chars[3] in valid_hangul and all(c.isdigit() for i, c in enumerate(result_chars) if i != 3):
                recognized_numbers[result_chars] += 1
                last_recognition_time = time.time()  # 번호판 인식 시 타이머 리셋
                recognized_this_frame = True

                current_time = time.time()

                # 차량 번호 전송 조건: 중복 번호가 아니거나 일정 시간이 지났을 경우
                if last_recognized_number != result_chars or (current_time - last_sent_time) > resend_interval:
                    last_recognized_number = result_chars
                    last_sent_time = current_time
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"차량번호: {result_chars}")
                    print(f"현재 시간: {timestamp}")
                    url = 'http://127.0.0.1:5000/send_plate_number'
                    data = {'plate_number': result_chars, 'timestamp': timestamp}
                    response = requests.post(url, json=data)
                    if response.status_code != 200:
                        print("전송 실패")

    # 타임아웃 체크
    if time.time() - last_recognition_time > timeout:
        last_recognition_time = time.time()  # 타임아웃 발생 시 시간 갱신

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
