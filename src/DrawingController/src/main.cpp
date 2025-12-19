#include <Arduino.h>
#include "LIS3DHTR.h"
#include <Wire.h>

LIS3DHTR<TwoWire> LIS;
#define WIRE Wire

unsigned long previousMillis = 0;
const long interval = 50;
//funkcje
bool shouldExecute(unsigned long &lastMillis, uint32_t interval);
void sendData(float x, float y, float z);

void setup() {
  Serial.begin(9600);
  while (!Serial) {};

  LIS.begin(WIRE, 0x19);
  LIS.setFullScaleRange(LIS3DHTR_RANGE_2G);
  LIS.setOutputDataRate(LIS3DHTR_DATARATE_50HZ);
}

unsigned long timerAccel = 0;
unsigned long timerDisplay = 0;
unsigned long timerBlink = 0;

void loop() {
  //odczyt akcelerometru co 20ms
  float x, y, z;
  if (shouldExecute(timerAccel, 20)) {
    if (LIS.available()) {
      LIS.getAcceleration(&x, &y, &z);
    }
  }
  //wysyłanie danych co 50ms
  if (shouldExecute(timerDisplay, 50)) {
    sendData(x, y, z);
  }
}



void sendData(float x, float y, float z) {
  Serial.print("X: ");
  Serial.print(x);
  Serial.print(" Y: ");
  Serial.print(y);
  Serial.print(" Z: ");
  Serial.println(z);
}

bool shouldExecute(unsigned long &lastMillis, uint32_t interval)  {
  unsigned long currentMillis = millis();
  if (currentMillis - lastMillis >= interval) {
    lastMillis = currentMillis;
    return true;
  }
  return false;
}