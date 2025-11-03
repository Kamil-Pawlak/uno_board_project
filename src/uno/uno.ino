// This example use I2C.
#include "LIS3DHTR.h"
#include <Wire.h>
#include <Arduino.h>
#include <U8g2lib.h>
LIS3DHTR<TwoWire> LIS;
#define WIRE Wire

#ifdef U8X8_HAVE_HW_SPI
#include <SPI.h>
#endif
#ifdef U8X8_HAVE_HW_I2C
#include <Wire.h>
#endif

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R2, /* clock=*/ SCL, /* data=*/ SDA, /* reset=*/ U8X8_PIN_NONE);

void setup()
{
  LIS.begin(WIRE,0x19);
  LIS.setOutputDataRate(LIS3DHTR_DATARATE_50HZ);
  u8g2.begin();

}
void loop()
{
    float x, y, z;
    LIS.getAcceleration(&x, &y, &z);
    
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.setCursor(0,10);
    u8g2.print("LIS3DHTR Accel:");
    u8g2.setCursor(0,30);
    u8g2.print("X: "); u8g2.print(x); 
    u8g2.setCursor(0,45);
    u8g2.print("Y: "); u8g2.print(y); 
    u8g2.setCursor(0,60);

    u8g2.sendBuffer();


}