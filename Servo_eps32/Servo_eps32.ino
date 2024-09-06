#include <ESP32Servo.h>
//
char dato;
int velocidad_h = 90;  // Velocidad para el servo horizontal
int velocidad_v = 90;  // Velocidad para el servo vertical

#define servoPin 26  
#define servoPin_1 27

Servo myServo;
Servo myServo_1;

void setup() {
  myServo.attach(servoPin);
  myServo_1.attach(servoPin_1);
  myServo.write(90);  // Posicionar los servos en 90 grados al iniciar el código
  myServo_1.write(90);
  Serial.begin(9600);
  Serial.setTimeout(5);  // Ajustar el tiempo de espera para Serial
}

void loop() {
  
  while (Serial.available()) {
    dato = Serial.read();
    delay(10);
    Serial.println(dato);
    
    switch(dato) {
      // Movimiento horizontal a la derecha
      case 'd': 
        velocidad_h = velocidad_h + 12;
        if (velocidad_h > 180) velocidad_h = 180;  // Limitar ángulo máximo
        myServo.write(velocidad_h);
        break;
       
      // Movimiento horizontal a la izquierda
      case 'i': 
        velocidad_h = velocidad_h - 12;  // Incrementa la velocidad en la dirección opuesta
        if (velocidad_h < 0) velocidad_h = 0;  // Limitar ángulo mínimo
        myServo.write(velocidad_h);
        break;
    
      // Movimiento vertical hacia arriba
      case 'a': 
        velocidad_v = velocidad_v + 16;
        if (velocidad_v > 180) velocidad_v = 180;  // Limitar ángulo máximo
        myServo_1.write(velocidad_v);
        break;

      // Movimiento vertical hacia abajo
      case 'b': 
        velocidad_v = velocidad_v - 16;
        if (velocidad_v < 0) velocidad_v = 0;  // Limitar ángulo mínimo
        myServo_1.write(velocidad_v);
        break;

        // Movimiento diagonal izquierda-arriba
      case '1':  // Nueva etiqueta para el caso 'i' + 'a'
        velocidad_h = velocidad_h - 12;
        velocidad_v = velocidad_v + 16;
        if (velocidad_h < 0) velocidad_h = 0;
        if (velocidad_v > 180) velocidad_v = 180;
        myServo.write(velocidad_h);
        myServo_1.write(velocidad_v);
        break;

      // Movimiento diagonal derecha-arriba
      case '2':  // Nueva etiqueta para el caso 'd' + 'a'
        velocidad_h = velocidad_h + 12;
        velocidad_v = velocidad_v + 16;
        if (velocidad_h > 180) velocidad_h = 180;
        if (velocidad_v > 180) velocidad_v = 180;
        myServo.write(velocidad_h);
        myServo_1.write(velocidad_v);
        break;

      // Movimiento diagonal izquierda-abajo
      case '3':  // Nueva etiqueta para el caso 'i' + 'b'
        velocidad_h = velocidad_h - 12;
        velocidad_v = velocidad_v - 16;
        if (velocidad_h < 0) velocidad_h = 0;
        if (velocidad_v < 0) velocidad_v = 0;
        myServo.write(velocidad_h);
        myServo_1.write(velocidad_v);
        break;

      // Movimiento diagonal derecha-abajo
      case '4':  // Nueva etiqueta para el caso 'd' + 'b'
        velocidad_h = velocidad_h + 12;
        velocidad_v = velocidad_v - 16;
        if (velocidad_h > 180) velocidad_h = 180;
        if (velocidad_v < 0) velocidad_v = 0;
        myServo.write(velocidad_h);
        myServo_1.write(velocidad_v);
        break;

      case 'p': 
        velocidad_h = 90;  // Detiene ambos servos
        velocidad_v = 90;
        myServo.write(velocidad_h);
        myServo_1.write(velocidad_v);
        break;

    }
  }
}
