#include <ESP32Servo.h>
//
char dato;
int velocidad = 90;  // 90 es la posición de parada para servos de rotación continua

#define servoPin 26  
#define servoPin_1 27

Servo myServo;
Servo myServo_1;

void setup() {
  myServo.attach(servoPin);
  myServo_1.attach(servoPin_1);
  myServo.write(90);  // Detiene ambos servos al inicio
  myServo_1.write(90);
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
        velocidad = velocidad + 6;
        if (velocidad > 180) velocidad = 180;  // Limitar ángulo máximo
        myServo.write(velocidad);
        break;
       

      case 'i': 
        velocidad = velocidad - 6;  // Incrementa la velocidad en la dirección opuesta
        if (velocidad < 0) velocidad = 0;  // Velocidad máxima en la otra dirección
        myServo.write(velocidad);
        break;

      case 'a': 
        velocidad = velocidad + 6;  // Incrementa la velocidad en una dirección
        if (velocidad > 180) velocidad = 180;
        myServo_1.write(velocidad);
        break;

      case 'b': 
        velocidad = velocidad - 6;  // Incrementa la velocidad en la dirección opuesta
        if (velocidad < 0) velocidad = 0;
        myServo_1.write(velocidad);
        break;

      case 'p': 
        velocidad = 90;  // Detiene ambos servos
        myServo.write(velocidad);
        myServo_1.write(velocidad);
        break;
    }
  }
}
