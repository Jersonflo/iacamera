#include <ESP32Servo.h>

// Declaración de variables y configuración
char dato;
int velocidad_h = 90;  // Ángulo para el servo horizontal
int velocidad_v = 90;  // Ángulo para el servo vertical
bool movimientoEnProceso = false;  // Bandera para indicar si el servo está en movimiento

#define servoPin 26  
#define servoPin_1 27
#define IN1 14  // Pin de control para IN1 del motor DC
#define IN2 12  // Pin de control para IN2 del motor DC
#define ENA 13  // Pin de habilitación (PWM) del motor DC

#define PWM_CHANNEL 0
#define PWM_FREQ 5000
#define PWM_RESOLUTION 8  // Resolución de 8 bits (0-255)

Servo myServo;
Servo myServo_1;

// --- Variables para la máquina de estados del pivote ---
enum PivotState {
  PIVOT_RAMP_UP,    // Aumentar velocidad de 0 a 255
  PIVOT_HOLD_UP,    // Mantener velocidad máxima cierto tiempo
  PIVOT_RAMP_DOWN,  // Bajar velocidad de 255 a 0
  PIVOT_HOLD_DOWN   // Mantener velocidad mínima cierto tiempo
};

PivotState pivotState = PIVOT_RAMP_UP;

int pivotSpeed = 0;           // Velocidad actual del pivote (0-255)
int pivotIncrement = 5;       // Paso de incremento/decremento
unsigned long pivotInterval = 50;    // Tiempo entre pasos de rampa (ms)
unsigned long pivotHoldTime = 2000;  // Tiempo para mantener velocidad máx/mín (ms)
unsigned long lastPivotMillis = 0;   // Marca de tiempo para controlar incrementos
unsigned long holdStartMillis = 0;   // Marca de tiempo para mantener velocidades


void setup() {
  // Configuración de los servos
  myServo.attach(servoPin);
  myServo_1.attach(servoPin_1);
  myServo.write(90);  // Posicionar los servos en 90 grados al iniciar el código
  myServo_1.write(90);

  // Configuración del monitor serial
  Serial.begin(9600);
  Serial.setTimeout(5);  // Ajustar el tiempo de espera para Serial

  // Configuración de los pines del motor DC
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENA, OUTPUT);


  // Configurar el PWM para el ESP32
  analogWrite(ENA, 128);  // PWM de 50% de ciclo de trabajo (ajusta el valor si es necesario)

  // Inicialmente apagamos el motor
  ledcWrite(PWM_CHANNEL, 0);

  // Arranque: Estado inicial de la máquina del pivote
  pivotState = PIVOT_RAMP_UP;
  pivotSpeed = 0;
  lastPivotMillis = millis();
  holdStartMillis = 0;

} 

// --- Loop principal ---
void loop() {
  // (1) Actualiza el pivote (motor DC) de manera no bloqueante
  actualizarPivote();

  // (2) Verifica si hay datos seriales para mover servos
  if (Serial.available()) {
    procesarComandosSerial();
  }

  // Otras lógicas si las hubiera ...
}

// --- MÁQUINA DE ESTADOS DEL PIVOTE ---
void actualizarPivote() {
  unsigned long ahora = millis();

  switch (pivotState) {
    case PIVOT_RAMP_UP:
      // Rampa de velocidad 0 -> 255
      if (ahora - lastPivotMillis >= pivotInterval) {
        lastPivotMillis = ahora;
        pivotSpeed += pivotIncrement;
        if (pivotSpeed >= 255) {
          pivotSpeed = 255;
          pivotState = PIVOT_HOLD_UP;     // Pasa a estado de mantener velocidad
          holdStartMillis = ahora;       // Inicia conteo de retención
        }
      }
      // Configura la dirección "SUBIR"
      digitalWrite(IN1, HIGH);
      digitalWrite(IN2, LOW);
      ledcWrite(PWM_CHANNEL, pivotSpeed);
      break;

    case PIVOT_HOLD_UP:
      // Mantiene velocidad máxima por pivotHoldTime
      digitalWrite(IN1, HIGH);
      digitalWrite(IN2, LOW);
      ledcWrite(PWM_CHANNEL, pivotSpeed);

      if (ahora - holdStartMillis >= pivotHoldTime) {
        // Terminado el tiempo de mantener
        pivotState = PIVOT_RAMP_DOWN;
        lastPivotMillis = ahora;  // Para la nueva rampa
      }
      break;

    case PIVOT_RAMP_DOWN:
      // Rampa de velocidad 255 -> 0
      if (ahora - lastPivotMillis >= pivotInterval) {
        lastPivotMillis = ahora;
        pivotSpeed -= pivotIncrement;
        if (pivotSpeed <= 0) {
          pivotSpeed = 0;
          pivotState = PIVOT_HOLD_DOWN;
          holdStartMillis = ahora;
        }
      }
      // Configura la dirección "BAJAR"
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      ledcWrite(PWM_CHANNEL, pivotSpeed);
      break;

    case PIVOT_HOLD_DOWN:
      // Mantiene velocidad mínima por pivotHoldTime
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      ledcWrite(PWM_CHANNEL, pivotSpeed);

      if (ahora - holdStartMillis >= pivotHoldTime) {
        pivotState = PIVOT_RAMP_UP;  // Volver a subir
        lastPivotMillis = ahora;
      }
      break;
  }
}



// Función para procesar los comandos seriales
void procesarComandosSerial() {
  dato = Serial.read();
  delay(10);
  Serial.println(dato);

  if (!movimientoEnProceso) {
    switch (dato) {
      case 'd': 
        movimientoEnProceso = true;
        moverServoSuavemente(myServo, &velocidad_h, 8, 150);
        movimientoEnProceso = false;
        break;
        
      case 'i': 
        movimientoEnProceso = true;
        moverServoSuavemente(myServo, &velocidad_h, -8, 50);
        movimientoEnProceso = false;
        break;

      case 'a': 
        movimientoEnProceso = true;
        moverServoSuavemente(myServo_1, &velocidad_v, 8, 150);
        movimientoEnProceso = false;
        break;

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

// --- Función para mover un servo suavemente (bloqueante) ---
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
    delay(15);  // Este delay sólo afecta a los servos, NO al pivote
  }
}


// --- Función para centrar ambos servos suavemente ---
void centrarServos() {
  while (velocidad_h != 90 || velocidad_v != 90) {
    if (velocidad_h < 90) velocidad_h++;
    else if (velocidad_h > 90) velocidad_h--;
    
    if (velocidad_v < 90) velocidad_v++;
    else if (velocidad_v > 90) velocidad_v--;
    
    myServo.write(velocidad_h);
    myServo_1.write(velocidad_v);
    delay(20);  // Sólo bloquea el centrado del servo
  }
}
