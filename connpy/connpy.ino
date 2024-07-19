#include <ESP32Servo.h>


Servo miServo;

#define servoPin 26       //Pin al que conectamos el cable naranja del servo.

void setup() {   
  miServo.attach(servoPin);
  miServo.write(0);       //Ángulo de giro en grados.
} 

void loop() {

  delay(2000); 
  miServo.write(90);

  delay(2000); 
  miServo.write(180);

  delay(2000); 
  miServo.write(90);

  delay(2000); 
  miServo.write(0);
  
}