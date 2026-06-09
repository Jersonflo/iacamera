#include <ESP32Servo.h>

Servo myServo;          // Objeto servo
const int servoPin = 26; // Pin GPIO del ESP32

void setup() {
  Serial.begin(9600);
  // Inicializa la librería servo y adjunta el pin
  myServo.attach(servoPin);
  Serial.println("Iniciando test de servo...");
}

void loop() {
  // Mueve lentamente de 0 a 180 grados
  for (int angulo = 0; angulo <= 180; angulo++) {
    myServo.write(angulo);
    delay(15); // Ajusta retardo para cambiar velocidad
  }
  delay(500);  // Mantener en 180 medio segundo

  // Mueve lentamente de 180 a 0 grados
  for (int angulo = 180; angulo >= 0; angulo--) {
    myServo.write(angulo);
    delay(15);
  }
  delay(500);  // Mantener en 0 medio segundo
}
