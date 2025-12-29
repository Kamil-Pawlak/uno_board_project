#include <Arduino.h>
#include "LIS3DHTR.h"
#include <Wire.h>

const int BUTTON_PIN = 6;
const int LED_PIN = 4;
LIS3DHTR<TwoWire> LIS;

enum State { STATE_CONNECTING, STATE_CONFIRM, STATE_NEUTRAL, STATE_DRAWING, STATE_ERASING };
State currentState = STATE_CONNECTING;

unsigned long tAccel = 0, tSerial = 0, tButton = 0, tHandshake = 0;
unsigned long lastHeartbeat = 0;

const unsigned long HEARTBEAT_TIMEOUT = 3000;
float lastX, lastY, lastZ;

bool shouldExecute(unsigned long &lastMillis, uint32_t interval);
void handleCommunication();
void updateHardware();

void setup() {
    Serial.begin(9600);
    pinMode(BUTTON_PIN, INPUT);
    pinMode(LED_PIN, OUTPUT);
    LIS.begin(Wire, 0x19);
    LIS.setFullScaleRange(LIS3DHTR_RANGE_2G);
    LIS.setOutputDataRate(LIS3DHTR_DATARATE_50HZ);
}

void loop() {
    handleCommunication();
    updateHardware();
}

void handleCommunication() {
    // 1. Odbieranie danych z PC
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        if (cmd == '!') {
            lastHeartbeat = millis();
            if (currentState == STATE_CONNECTING) {
                currentState = STATE_CONFIRM;
            }
        }
    }

    //sprawdzenie czy jest sygnał z PC
    if (currentState != STATE_CONNECTING && (millis() - lastHeartbeat > HEARTBEAT_TIMEOUT)) {
        currentState = STATE_CONNECTING;
    }

    // wysyłanie zapytania o połączenie
    if (currentState == STATE_CONNECTING) {
        if (shouldExecute(tHandshake, 1000)) {
            Serial.println("?");
        }
    }
}

void updateHardware() {
    if (currentState != STATE_CONNECTING && currentState != STATE_CONFIRM) {
        if (shouldExecute(tAccel, 20)) {
            if (LIS.available()) LIS.getAcceleration(&lastX, &lastY, &lastZ);
        }

        // Obsługa przycisku (zmiana trybów)
        if (shouldExecute(tButton, 50)) {
            static bool lastBtn = LOW;
            bool currentBtn = digitalRead(BUTTON_PIN);
            if (currentBtn == HIGH && lastBtn == LOW) {
                // zmiana stanu
                if (currentState == STATE_NEUTRAL) currentState = STATE_DRAWING;
                else if (currentState == STATE_DRAWING) currentState = STATE_ERASING;
                else currentState = STATE_NEUTRAL;
            }
            lastBtn = currentBtn;
        }

        // Wysyłanie danych pomiarowych
        if (shouldExecute(tSerial, 50)) {
            Serial.print((int)currentState); Serial.print(";");
            Serial.print(lastX); Serial.print(";");
            Serial.print(lastY); Serial.print(";");
            Serial.println(lastZ);
        }
    }

    switch (currentState) {
        case STATE_CONNECTING:
            // Miganie diodą podczas łączenia
            digitalWrite(LED_PIN, (millis() / 500) % 2); 
            break;
        case STATE_CONFIRM:
            // Stałe świecenie diody podczas potwierdzania
            digitalWrite(LED_PIN, HIGH);
            //potwierdzenie połączenia przyciskiem
            if (digitalRead(BUTTON_PIN) == HIGH) {
                currentState = STATE_NEUTRAL;
            }
            break;
        case STATE_NEUTRAL:
        case STATE_DRAWING:
        case STATE_ERASING:
            digitalWrite(LED_PIN, HIGH);
            break;
    }
}

bool shouldExecute(unsigned long &lastMillis, uint32_t interval) {
    unsigned long currentMillis = millis();
    if (currentMillis - lastMillis >= interval) {
        lastMillis = currentMillis;
        return true;
    }
    return false;
}