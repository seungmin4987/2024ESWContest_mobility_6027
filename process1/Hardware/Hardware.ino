#include <IRremote.h>

// 핀 설정
const int IR_Receive_Pin = A0;
const int motorPin1 = 9;  // IN1 핀
const int motorPin2 = 10; // IN2 핀
const int enablePin = 11; // ENA 핀 (속도 제어용 PWM 핀)
const int trig = 7;       // Trig pin
const int echo = 8;       // Echo pin
const int outputPin = 5;  // Output pin for distance check

// 적외선 신호 정의
#define FORWARD_SIGNAL 0x1FE48B7  // 전진 신호
#define BACKWARD_SIGNAL 0x1FE807F // 후진 신호

IRrecv irrecv(IR_Receive_Pin);
decode_results results;

void setup() {
  Serial.begin(9600);  // 시리얼 통신 시작
  irrecv.enableIRIn();  // 적외선 리모컨 초기화

  // 핀 모드 설정
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);
  pinMode(enablePin, OUTPUT);
  pinMode(trig, OUTPUT);
  pinMode(echo, INPUT);
  pinMode(outputPin, OUTPUT);

  Serial.println("IR Receive and Motor Control Initialized!");
}

void loop() {
  // 거리 측정
  float distance = getDistance();
  
  // 거리 체크 후 출력 핀 제어
  checkDistance(distance);

  // IR 리모컨 신호 처리
  if (irrecv.decode(&results)) {
    processIRSignal(results.value);
    irrecv.resume();  // 다음 신호를 받을 준비
  }

  delay(100); // 100ms 딜레이
}

// 초음파 센서를 사용하여 거리 측정
float getDistance() {
  digitalWrite(trig, LOW);
  delay(2);
  digitalWrite(trig, HIGH);
  delay(10);
  digitalWrite(trig, LOW);

  // Echo 핀에서 펄스 입력 측정
  float length = pulseIn(echo, HIGH);
  // 소리의 속도(340 m/s)를 사용하여 거리 계산 (cm 단위)
  return ((340 * length) / 10000) / 2;
}

// 측정된 거리가 50cm 이내일 경우 outputPin을 HIGH로 설정
void checkDistance(float distance) {
  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  if (distance < 50) {
    digitalWrite(outputPin, HIGH);  // 50cm 이내일 때
  } else {
    digitalWrite(outputPin, LOW);   // 50cm 초과일 때
  }
}

// 적외선 신호에 따라 모터를 제어하는 함수
void processIRSignal(unsigned long irValue) {
  if (irValue != 0xFFFFFFFF) {
    Serial.print("Received IR Value: ");
    Serial.println(irValue, HEX);
    
    if (irValue == FORWARD_SIGNAL) {
      moveMotorForward();
    } else if (irValue == BACKWARD_SIGNAL) {
      moveMotorBackward();
    } else {
      stopMotor();
    }
  }
}

// 모터 전진
void moveMotorForward() {
  Serial.println("Moving Forward");
  digitalWrite(motorPin1, HIGH);
  digitalWrite(motorPin2, LOW);
  analogWrite(enablePin, 255); // 최대 속도
}

// 모터 후진
void moveMotorBackward() {
  Serial.println("Moving Backward");
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);
  analogWrite(enablePin, 255); // 최대 속도
}

// 모터 정지
void stopMotor() {
  Serial.println("Stopping Motor");
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, LOW);
  analogWrite(enablePin, 0);   // 모터 정지
}

