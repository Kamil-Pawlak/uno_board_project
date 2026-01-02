#include <Arduino.h>
#include "LIS3DHTR.h"
#include <Wire.h>
#include <U8x8lib.h>

#define BUTTON_PIN 6
#define LED_PIN 4
#define POTENTIOMETER_PIN A0
#define BUZZER_PIN 5
LIS3DHTR<TwoWire> LIS;

// Konfiguracja wyświetlacza
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(U8X8_PIN_NONE);

enum State { STATE_CONNECTING,  STATE_NEUTRAL, STATE_DRAWING, STATE_ERASING, STATE_CONFIRM };
State currentState = STATE_CONNECTING;
State lastStateDisplayed = (State)-1; 

unsigned long tAccel = 0, tSerial = 0, tButton = 0, tHandshake = 0,
              tPotentiometer = 0, tDisplay = 0, tBuzzer = 0;
unsigned long lastHeartbeat = 0;

const unsigned long HEARTBEAT_TIMEOUT = 3000;
float lastX, lastY, lastZ;
int potentiometerValue = 0;
bool buzzerOn = false;


bool shouldExecute(unsigned long &lastMillis, uint32_t interval);
void handleCommunication();
void updateHardware();
void updateDisplay();

void setup() {
    Serial.begin(9600);
    pinMode(BUTTON_PIN, INPUT);
    pinMode(LED_PIN, OUTPUT);
    pinMode(POTENTIOMETER_PIN, INPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    
    LIS.begin(Wire, 0x19);
    LIS.setFullScaleRange(LIS3DHTR_RANGE_2G);
    LIS.setOutputDataRate(LIS3DHTR_DATARATE_50HZ);
    
    u8x8.begin();
    u8x8.setPowerSave(0);
    u8x8.setFlipMode(1);
    u8x8.setFont(u8x8_font_chroma48medium8_r);
    u8x8.clearDisplay();
}

void loop() {
    handleCommunication();
    updateHardware();
}

void handleCommunication() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        if (cmd == '!') {
            lastHeartbeat = millis();
            if (currentState == STATE_CONNECTING) {
                currentState = STATE_CONFIRM;
            }
        }
    }

    if (currentState != STATE_CONNECTING && (millis() - lastHeartbeat > HEARTBEAT_TIMEOUT)) {
        currentState = STATE_CONNECTING;
        buzzerOn = false;
    }

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
            if(abs(lastX) > 0.1 || abs(lastY) > 0.1) {
                buzzerOn = true;
            }
            else {
                buzzerOn = false;
            }
        }
        if (shouldExecute(tPotentiometer, 100)) {
            potentiometerValue = analogRead(POTENTIOMETER_PIN);
        }

        if (shouldExecute(tButton, 50)) {
            static bool lastBtn = LOW;
            bool currentBtn = digitalRead(BUTTON_PIN);
            if (currentBtn == HIGH && lastBtn == LOW) {
                if (currentState == STATE_NEUTRAL) currentState = STATE_DRAWING;
                else if (currentState == STATE_DRAWING) currentState = STATE_ERASING;
                else currentState = STATE_NEUTRAL;
            }
            lastBtn = currentBtn;
        }

        if (shouldExecute(tSerial, 50)) {
            Serial.print((int)currentState); Serial.print(";");
            Serial.print(lastX); Serial.print(";");
            Serial.print(lastY); Serial.print(";");
            Serial.print(lastZ); Serial.print(";");
            Serial.println(potentiometerValue);
        }
    }

    switch (currentState) {
        case STATE_CONNECTING:
            digitalWrite(LED_PIN, (millis() / 500) % 2); 
            break;
        case STATE_CONFIRM:
            digitalWrite(LED_PIN, HIGH);
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
    if (shouldExecute(tDisplay, 200))
        updateDisplay();
    if (shouldExecute(tBuzzer, 9) && buzzerOn) {
        digitalWrite(BUZZER_PIN, HIGH);
    } else {
        digitalWrite(BUZZER_PIN, LOW);
    }
}

void updateDisplay() {
    //przy zmianie stanu odświeżamy ekran
    if (currentState != lastStateDisplayed) {
        u8x8.clearDisplay();
        
        switch (currentState) {
            case STATE_CONNECTING:
                u8x8.setCursor(0, 0); u8x8.print("STATUS:");
                u8x8.setCursor(0, 2); u8x8.print("Oczekuje na");
                u8x8.setCursor(0, 3); u8x8.print("polaczenie...");
                break;
                
            case STATE_CONFIRM:
                u8x8.setCursor(0, 0); u8x8.print("STATUS:");
                u8x8.setCursor(0, 2); u8x8.print("Wcisnij przycisk");
                u8x8.setCursor(0, 3); u8x8.print("aby polaczyc!");
                break;
                
            case STATE_NEUTRAL:
                u8x8.setCursor(0, 0); u8x8.print("TRYB:");
                u8x8.setCursor(0, 1); u8x8.print("NEUTRALNY");
                break;
                
            case STATE_DRAWING:
                u8x8.setCursor(0, 0); u8x8.print("TRYB:");
                u8x8.setCursor(0, 1); u8x8.print("RYSOWANIE");
                break;
                
            case STATE_ERASING:
                u8x8.setCursor(0, 0); u8x8.print("TRYB:");
                u8x8.setCursor(0, 1); u8x8.print("GUMKA");
                break;
        }
        
        lastStateDisplayed = currentState;
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