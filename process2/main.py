import torch
import cv2
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import numpy as np
import time
import threading
from collections import deque

import warnings

# FutureWarning 무시
warnings.simplefilter(action='ignore', category=FutureWarning)

from objsort import Sort

MODEL = torch.hub.load('C:/whitebox/yolov5', 'custom', 'C:/whitebox/best.pt', source='local')

# COCO 데이터셋 클래스 목록
COCO_CLASSES = MODEL.names

# SORT 초기화
tracker = Sort()

'''FIREBASE'''
# Firebase 서비스 계정 키(JSON 파일)의 경로
cred = credentials.Certificate("C:/whitebox/whiteboxver3-firebase-adminsdk-y5cgl-9b689f6f51.json")

# Firebase Admin SDK 초기화
firebase_admin.initialize_app(cred, {'databaseURL': 'https://whiteboxver3-default-rtdb.asia-southeast1.firebasedatabase.app/'})

# Firebase Realtime Database에 대한 레퍼런스
ref = db.reference()

# Firebase 업데이트 주기 (1초)
INTERVAL = 0.1

 #Firebase Update 주기
LAST_UPDATE_TIME = 0  #시간차 계산을 위한 FLAG
prev_detected = 0

'''전역변수(전 프로세스)'''
#CV관련
FRAME = None #cv2에서 가져온 프레임 // 얘가 img 토픽 역할
FIRST_FRAME = None # 첫프레임

#좌표관련
ORIGINAL_COORDINATES = []       #기존 픽셀 좌표
TRANSFORMATION_MATRIX = []      # 좌표변환행렬
CLS = None                      # 객체 cls
TRANSFORMED_COORDINATES = []    # 변환좌표
TRANSFORM_POINTS = []

'''CV2'''
# 비디오 캡처 초기화 (웹캠 사용)
cap = cv2.VideoCapture(1)

#img 프레임을 FRAME에 저장
def cv2framecall():
    global FRAME, FIRST_FRAME
    while cap.isOpened():
        ret, FRAME = cap.read()
        if not ret:
            print("이미지를 읽어올 수 없음")
            break
        if FIRST_FRAME is None:
            FIRST_FRAME = FRAME
            print("첫 번째 프레임 저장 완료")
#스레드 선언
framecall = threading.Thread(target=cv2framecall)

#FRAME 멀티스레딩 동기화 제어
FRAME_LOCK = threading.Lock()

'''좌표변환'''
#경계선을 저장할 리스트
boundary_lines = []
lines = []
def mouse_click_line(event, x, y, flags, param):
    global boundary_lines
    if event == cv2.EVENT_LBUTTONDOWN:
        global lines
        lines.append((x, y))
        print(f"Point selected: {(x, y)}")

#마우스 클릭 콜백
def mouse_click(event, x, y, flags, param):
    global TRANSFORM_POINTS
    if event == cv2.EVENT_LBUTTONDOWN:
        TRANSFORM_POINTS.append((x, y))
        print(f"Point selected: {(x, y)}")

#변환행렬 구하기
def get_coordinates_transform_matrix():
    global TRANSFORMATION_MATRIX, FIRST_FRAME, TRANSFORM_POINTS, boundary_lines
    
    # FIRST_FRAME가 설정될 때까지 대기
    while FIRST_FRAME is None:
        time.sleep(0.1)

    if FIRST_FRAME is not None:
        cv2.imshow("Original", FIRST_FRAME)
        cv2.waitKey(1)
        cv2.setMouseCallback("Original", mouse_click)
    
    # 마우스 클릭을 통해 4개의 점이 선택될 때까지 대기
    while len(TRANSFORM_POINTS) < 4:
        cv2.waitKey(10)
    cv2.destroyAllWindows()
    print(f"TRANSFORM_POINTS = {TRANSFORM_POINTS}")
    
    if len(TRANSFORM_POINTS) == 4:
        # 각각 네 개의 점 // 왼쪽 위, 오른쪽 위, 왼쪽 아래, 오른쪽 아래 순
        pixel_standard_coordinates = np.float32(TRANSFORM_POINTS)  # pixel coordiantes
        world_standard_coordinates = np.float32([[0, 0], [540, 0], [0, 840], [540, 840]])  # destination coordinates
        coordinates_transform_matrix = cv2.getPerspectiveTransform(pixel_standard_coordinates, world_standard_coordinates)
        TRANSFORMATION_MATRIX = coordinates_transform_matrix
        print(f"TRANSFORMATION MATRIX : {coordinates_transform_matrix}")
    
    while len(lines) < 4:
        lineimg = cv2.warpPerspective(FIRST_FRAME, TRANSFORMATION_MATRIX,(540,840))
        cv2.imshow("warninglinset", lineimg)
        cv2.waitKey(1)
        cv2.setMouseCallback("warninglinset", mouse_click_line)
    boundary_lines = [(lines[0], lines[1]), (lines[2], lines[3])]
    cv2.destroyAllWindows()

    # 함수의 반환 : 변환행렬
    return TRANSFORMATION_MATRIX

# 좌표 변환 함수
def coordinates_transform(pixel_coordinates):
    global TRANSFORMATION_MATRIX
    pixel_coordinates = np.array([pixel_coordinates[0], pixel_coordinates[1], 1])  # 픽셀좌표 행렬로 변환 (x,y,1)
    scaled_transformed_coordinates = np.dot(TRANSFORMATION_MATRIX, pixel_coordinates)  # 투영좌표 = 변환행렬 x 픽셀좌표
    transformed_coordinates = scaled_transformed_coordinates[:2] / scaled_transformed_coordinates[2]  # 행렬 scaling
    return transformed_coordinates

'''''''''프로세스 실행'''''''''

'''벡터 기반 경고시스템'''
## 변수 선언 ##
prev_detected = 0

#최근 위치를 저장하기 위한 deque
position_history = {}

# 특정 직선과 점의 상대적인 위치 확인 함수 (좌/우 확인)
def is_left_of_line(point, line):
    p1, p2 = line[0], line[-1]
    return (p2[0] - p1[0]) * (point[1] - p1[1]) - (p2[1] - p1[1]) * (point[0] - p1[0]) < 0

# 영역 확인 (인도-차도-인도)
def check_zone(person_center, boundary_lines):
    if len(boundary_lines) < 2:
        print("경계선이 두 개 설정되지 않음")  # 디버깅 출력
        return -1  # 경계선이 없으면 무시

    left_of_first_line = is_left_of_line(person_center, boundary_lines[0])
    left_of_second_line = is_left_of_line(person_center, boundary_lines[1])

    #도로 위 객체 위치 판단
    if not left_of_first_line:
        return 0  # 첫 번째 인도
    elif left_of_first_line and not left_of_second_line:
        return 1  # 차도
    else:
        return 2  # 두 번째 인도


'''인도-차선 기반 객체 좌표 및 벡터 기반 경고시스템'''
def warnbyline():
    global prev_detected, ORIGINAL_COORDINATES, INTERVAL, TRANSFORM_POINTS, TRANSFORMATION_MATRIX, FRAME, FRAME_LOCK, MODEL, COCO_CLASSES, LAST_UPDATE_TIME
    while True:
        with FRAME_LOCK:
            warnbylineimg = FRAME
            orgimg = FRAME
            img  = cv2.cvtColor(warnbylineimg, cv2.COLOR_BGR2RGB)
            results = MODEL(img)
            warnbylineimgdis = cv2.warpPerspective(warnbylineimg, TRANSFORMATION_MATRIX,(540,840))
            cv2.line(warnbylineimgdis, boundary_lines[0][0], boundary_lines[0][1], (0,0,255),2)
            cv2.line(warnbylineimgdis, boundary_lines[1][0], boundary_lines[1][1], (0,0,255),2)
            
            #results 결과 저장 리스트
            detections = []     # 객체 감지 데이터 저장
            labels = []         # 객체 CLS저장
            for det in results.xyxy[0]:
                xmin, ymin, xmax, ymax, conf, cls = det.detach().cpu().numpy()
                cls = int(cls)
                if COCO_CLASSES[cls] in ["Person"]:      #대문자 주의
                    detections.append([xmin, ymin, xmax, ymax, conf])
                    labels.append(COCO_CLASSES[cls])
                #print(f"Labels : {labels}") #디버깅
            detected=0

            # SORT로 객체 추적
            if len(detections) > 0:
                detections = np.array(detections)
                tracked_objects = tracker.update(detections)
                person_boxes = []
                bbox_coordinates = []

                #여집합 제거
                present_track = []
                for i, x in enumerate(tracked_objects):
                    xmin, ymin, xmax, ymax, track_id = x[:5]
                    label = labels[i] # labels는 각 탐지된 객체 종류 / label은 그중 하나
                    ident  = label + str(track_id)
                    present_track.append(ident)
                
                to_remove = []
                for ident in position_history.keys():
                    if ident not in present_track:
                        to_remove.append(ident)

                for ident in to_remove:
                    del position_history[ident]
                    print(f"객체 {ident} 제거됨")

                # Tracked Objects 기반 플로팅
                for i, output in enumerate(tracked_objects):
                    xmin, ymin, xmax, ymax, track_id = output[:5]
                    box = (xmin, ymin, xmax, ymax)
                    label = labels[i] # labels는 각 탐지된 객체 종류 / label은 그중 하나
                    ident  = label + str(track_id)
                    # 현재 프레임의 중심 좌표 계산 (바운딩박스 맨 아래 기준)
                    current_position = ((xmin + xmax) / 2, ymax)
                    trans_current_position = coordinates_transform(current_position)
                    print(f"Position History : {position_history}")
                    
                    # 최근 위치 업데이트
                    if ident not in position_history:
                        position_history[ident] = deque(maxlen=5)  # 최근 5 프레임 위치 저장
                    position_history[ident].append(current_position)
                    
                    if label == "Person":
                        person_boxes.append(box)
                        c1 ,c2 = (int(xmin), int(ymin)), (int(xmax), int(ymax))
                        #가중치 여기도 수정
                        center_point = round((c1[0]+c2[0])/2), round(c2[1])
                        trans_center_point = coordinates_transform(center_point)
                        trans_center_point = (int(trans_center_point[0]), int(trans_center_point[1]))
                        trans_xmin_ymin = coordinates_transform((int(xmin), int(ymin)))
                        trans_xmax_ymax = coordinates_transform((int(xmax), int(ymax)))
                        trans_xmin, trans_ymin = int(trans_xmin_ymin[0]), int(trans_xmin_ymin[1])
                        trans_xmax, trans_ymax = int(trans_xmax_ymax[0]), int(trans_xmax_ymax[1])

                        cv2.circle(warnbylineimgdis, trans_center_point,5,(0,255,0),2)
                        cv2.circle(orgimg, center_point,5,(0,255,0),2)
                        cv2.rectangle(warnbylineimgdis, (trans_xmin, trans_ymin), (trans_xmax, trans_ymax), (0, 255, 0), 2)
                        cv2.rectangle(orgimg, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (0, 255, 0), 2)
                        cv2.putText(warnbylineimgdis, f'Person {int(track_id)}', (trans_xmin, trans_ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
                        cv2.putText(orgimg, f'Person {int(track_id)}', (int(xmin), int(ymin) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
                        bbox_coordinates.append((f'Person {int(track_id)}', trans_center_point))  # 식별구분 및 좌표 데이터 리스트 형태로 bbox_coordinates에 추가
                        
                        # 최근 위치를 사용한 속도 기반 예상 위치 계산
                        if len(position_history[ident]) >= 2:
                            print(f"Calculating predicted position for {ident}")
                            positions = np.array(position_history[ident])
                            if len(positions) > 1:
                                velocity = np.mean(np.diff(positions, axis=0),axis = 0)
                                # 예측 거리 (예 : 5프레임 후)
                                predicted_distance = 10 * velocity
                                predicted_position = positions[-1] + predicted_distance
                                trans_predicted_position = coordinates_transform(predicted_position)
                                
                                # 예상 위치 시각화
                                cv2.circle(warnbylineimgdis, (int(trans_predicted_position[0]), int(trans_predicted_position[1])), 5, (255, 0, 0), -1)  # 파란색 점으로 예상 위치 표시
                                cv2.circle(orgimg, (int(predicted_position[0]), int(predicted_position[1])), 5, (255, 0, 0), -1)  # 파란색 점으로 예상 위치 표시
                                cv2.line(warnbylineimgdis, (int(trans_current_position[0]), int(trans_current_position[1])), (int(trans_predicted_position[0]), int(trans_predicted_position[1])), (0, 255, 0), thickness = 2, lineType=None, shift=None)
                                cv2.line(orgimg, (int(current_position[0]), int(current_position[1])), (int(predicted_position[0]), int(predicted_position[1])), (0, 255, 0), thickness = 2, lineType=None, shift=None)
                                # 예상 위치로 영역 확인
                                predicted_zone = check_zone(trans_predicted_position, boundary_lines)
                                if predicted_zone == 1:  # 차도 영역
                                    detected = 2
                                    print("예상 위치가 차도 영역에 있음")  # 디버깅 출력

                        # 현재 위치로 영역 확인
                        zone = check_zone(trans_current_position, boundary_lines)
                        if zone == 1:  # 차도 영역
                            detected = 1
                            print("차도 영역에서 사람 감지됨")  # 디버깅 출력
                print(f"Detected : {detected}")

                #픽셀 좌표 저장
                ORIGINAL_COORDINATES = bbox_coordinates

                coordinates_data = {}
                for item in bbox_coordinates:
                    label, coord = item
                    x, y = coord
                    coordinates_data[label] = {'x': float(x), 'y': float(y)}

                current_time = time.time()    
                # bbox_coordinates를 Firebase에 업데이트
                if current_time - LAST_UPDATE_TIME >= INTERVAL:
                    ref.update({'Coordinates': coordinates_data})

                #Firebase 업데이트 조건 확인
                if detected != prev_detected and current_time - LAST_UPDATE_TIME >= INTERVAL:
                    
                    #레퍼런스 업데이트
                    ref.update({'Warning by Line': int(detected)})

                    # 상태 업데이트 및 타이머 리셋
                    prev_detected = detected
                    LAST_UPDATE_TIME = current_time
            cv2.imshow('Transformed View', warnbylineimgdis)
            cv2.imshow('Original View', orgimg)
            cv2.waitKey(1)

warning = threading.Thread(target=warnbyline)
'''main 루프'''

def main():
    #img 수신 시작
    framecall.start()
    get_coordinates_transform_matrix()
    warning.start()
    

#메인루프 실행
if __name__ == '__main__':
    time.sleep(1)
    main()
