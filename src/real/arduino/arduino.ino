#include <Arduino.h>
#include <SoftPWM.h>

#include "car_control.h"
#include "ultrasonic.h"

#define BAUDRATE 115200

#define IR_LEFT_PIN A0
#define IR_RIGHT_PIN 7

#define SENSOR_PERIOD_MS 50   // 20 Hz

// hysteresis thresholds for analog IR
#define IR_LEFT_ON  280
#define IR_LEFT_OFF 330

void setup() {
  Serial.begin(BAUDRATE);

  SoftPWMBegin();
  carBegin();

  pinMode(IR_LEFT_PIN, INPUT);
  pinMode(IR_RIGHT_PIN, INPUT);

  Serial.println("READY");
}

void loop() {
  handleSerial();
  publishSensors();
  delay(SENSOR_PERIOD_MS);
}

void handleSerial() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd.startsWith("M")) {
    int left, right;
    if (sscanf(cmd.c_str(), "M %d %d", &left, &right) == 2) {
      left = constrain(left, -100, 100);
      right = constrain(right, -100, 100);
      carSetMotors(left, right);

      Serial.print("OK M ");
      Serial.print(left);
      Serial.print(" ");
      Serial.println(right);
    }
  }
  else if (cmd == "S") {
    carStop();
    Serial.println("OK S");
  }
}

int readIRLeft() {
  static int state = 0;
  int v = analogRead(IR_LEFT_PIN);

  if (!state && v < IR_LEFT_ON) state = 1;
  else if (state && v > IR_LEFT_OFF) state = 0;

  return state;
}

int readIRRight() {
  // digital IR: LOW = obstacle
  return digitalRead(IR_RIGHT_PIN) == LOW ? 1 : 0;
}

void publishSensors() {
  float dist_cm = ultrasonicRead();
  if (dist_cm < 0) dist_cm = 999;

  int ir_left  = readIRLeft();
  int ir_right = readIRRight();

  Serial.print("D ");
  Serial.print((int)dist_cm);
  Serial.print(" ");
  Serial.print(ir_left);
  Serial.print(" ");
  Serial.println(ir_right);
}
