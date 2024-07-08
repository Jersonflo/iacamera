#include <Arduino.h>
#include <ESP32Servo.h>

Servo myServo;
const int servoPin = 9;

void setup() {
  Serial.begin(9600);  // Inicia la comunicación serial a 9600 baudios
  myServo.attach(servoPin);  // Adjunta el servo al pin definido
  Serial.println("ESP32 listo para recibir comandos.");
}

void loop() {
  if (Serial.available() > 0) {
    String message = Serial.readStringUntil('\n');  // Lee el mensaje hasta el carácter de nueva línea
    message.trim();  // Elimina los espacios en blanco

    Serial.print("Mensaje recibido: ");  // Imprime el mensaje recibido
    Serial.println(message);

    if (message == "Hola, ESP32") {
      Serial.println("Acción: Mensaje de saludo recibido");
      // Realiza alguna acción si es necesario
    } else if (message == "Controlando el servo desde Python") {
      Serial.println("Acción: Moviendo el servo a 90 grados");
      myServo.write(90);  // Mueve el servo a 90 grados como ejemplo
    } else if (message == "Mensaje final") {
      Serial.println("Acción: Moviendo el servo a 0 grados");
      myServo.write(0);  // Mueve el servo a 0 grados como ejemplo
    } else {
      Serial.println("Acción: Mensaje desconocido");
    }
  }
}
