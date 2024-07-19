#include <Servo.h>
#include <ESP32Servo.h>

char dato;
int angulo = 90;

#define servoPin 26  
Servo myServo;

void setup() {
  myServo.attach(servoPin);
  myServo.write(0); 
  Serial.begin(9600);
  Serial.setTimeout(10);  // Ajustar el tiempo de espera para Serial

}

void loop() {
  while (Serial.available()) {
    dato = Serial.read();
    delay(10);
    Serial.println(dato);
    switch(dato) {
      case 'd': 
        angulo = angulo + 2;
        myServo.write(angulo);
        break;

      case 'i': 
        angulo = angulo - 2;
        myServo.write(angulo);
        break;

      case 'p': 
        myServo.write(angulo);
        break;
    }
  }
}