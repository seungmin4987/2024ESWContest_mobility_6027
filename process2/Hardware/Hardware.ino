void setup() {
  Serial.begin(9600); // 시리얼 통신 시작
  pinMode(2, OUTPUT); // 릴레이 핀 설정
  digitalWrite(2, LOW); // 릴레이 초기화
}
char command;

void loop() {
  if (Serial.available()) {
    command = Serial.read(); // 노트북에서 명령 읽기
  }
  //예상 위치기반
  if (command == '2'){
    Serial.println("Relay OFF");
    digitalWrite(2, HIGH); // 릴레이 켜기
    delay(1000);
  }
  //실제 위치 기반
  else if (command == '1') {
    Serial.println("Relay OFF");
    digitalWrite(2, HIGH); // 릴레이 켜기
    delay(100);
    digitalWrite(2,LOW);
    delay(100);
    } 
  else if (command == '0') {
    digitalWrite(2, LOW); // 릴레이 끄기
    Serial.println("Relay OFF");
  }
}

