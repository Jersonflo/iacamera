#include <Arduino.h>

void setup() {
  Serial.begin(115200);  // Inicializa la comunicación serial a 115200 baudios
}

void loop() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');  // Lee los datos recibidos hasta el carácter de nueva línea
    Serial.print("Recibido: ");
    Serial.println(data);  // Imprime los datos recibidos
  }
  delay(100);  // Espera un poco antes de la próxima lectura
}
