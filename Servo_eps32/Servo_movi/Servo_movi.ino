#include <ESP32Servo.h>

char dato;
int velocidad_h = 90;  // Ángulo para el servo horizontal
int velocidad_v = 90;  // Ángulo para el servo vertical
bool movimientoEnProceso = false;  // Bandera para indicar si el servo está en movimiento

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

    // Si no hay un movimiento en proceso, procesar el nuevo comando
    if (!movimientoEnProceso) {
      switch(dato) {
        // Movimiento horizontal a la derecha
        case 'd': 
          movimientoEnProceso = true;
          moverServoSuavemente(myServo, &velocidad_h, 8, 150);
          movimientoEnProceso = false;
          break;
         
        // Movimiento horizontal a la izquierda
        case 'i': 
          movimientoEnProceso = true;
          moverServoSuavemente(myServo, &velocidad_h, -8, 50);
          movimientoEnProceso = false;
          break;
      
        // Movimiento vertical hacia arriba
        case 'a': 
          movimientoEnProceso = true;
          moverServoSuavemente(myServo_1, &velocidad_v, 8, 150);
          movimientoEnProceso = false;
          break;

        // Movimiento vertical hacia abajo
        case 'b': 
          movimientoEnProceso = true;
          moverServoSuavemente(myServo_1, &velocidad_v, -8, 50);
          movimientoEnProceso = false;
          break;

        case 'p':
          movimientoEnProceso = true;
          centrarServos();
          movimientoEnProceso = false;
          break;
      }
    }
  }
}

// Función para mover el servo suavemente
void moverServoSuavemente(Servo &servo, int *anguloActual, int incremento, int limite) {
  int anguloObjetivo = *anguloActual + incremento;

  // Limitar el ángulo dentro de los límites especificados
  if (incremento > 0 && anguloObjetivo > limite) anguloObjetivo = limite;
  if (incremento < 0 && anguloObjetivo < limite) anguloObjetivo = limite;

  // Mover el servo gradualmente hacia el ángulo objetivo
  while (*anguloActual != anguloObjetivo) {
    if (*anguloActual < anguloObjetivo) (*anguloActual)++;
    else if (*anguloActual > anguloObjetivo) (*anguloActual)--;
    servo.write(*anguloActual);
    delay(20);  // Ajusta este valor para controlar la suavidad del movimiento
  }
}

// Función para centrar ambos servos suavemente
void centrarServos() {
  while (velocidad_h != 90 || velocidad_v != 90) {
    if (velocidad_h < 90) velocidad_h++;
    else if (velocidad_h > 90) velocidad_h--;
    if (velocidad_v < 90) velocidad_v++;
    else if (velocidad_v > 90) velocidad_v--;
    myServo.write(velocidad_h);
    myServo_1.write(velocidad_v);
    delay(20);  // Añadir un pequeño retardo para un ajuste gradual
  }
}