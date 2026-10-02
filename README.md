# iacamera 🤖👁️

Robot con **visión por computador** que detecta y sigue rostros, con interfaz gráfica de telemetría en tiempo real y un asistente conversacional por voz. Proyecto desarrollado en el Aula STEM FabLab de la Universidad Nacional de Colombia.

## Características

- 🎯 **Seguimiento facial** con MediaPipe y OpenCV, con zona muerta configurable.
- 🔌 **Control de servomotores** en un ESP32 por comunicación serial.
- 🖥️ **Interfaz moderna** (CustomTkinter) con telemetría en tiempo real.
- 🗣️ **Asistente de voz "Nova":** agente conversacional con reconocimiento de voz, LLM y síntesis de voz (edge-tts).
- 🌐 **Versión web** del asistente (`index.html`, `app.js`).
- ⚙️ **Diseño mecánico** en Fusion 360 y piezas impresas en 3D.

## Stack

Python · OpenCV · MediaPipe · CustomTkinter · PySerial · ESP32 (Arduino) · LLMs · edge-tts

## Estructura

```
iacamera/
├── main.py             # Punto de entrada
├── ui_app.py           # Interfaz gráfica
├── tracker.py          # Seguimiento facial y envío serial
├── nova_agent.py       # Agente conversacional por voz
├── assistant.py        # Lógica del asistente
├── Servo_eps32/        # Firmware del ESP32 (servos y motor DC)
└── requirements.txt
```

## Instalación

```bash
git clone https://github.com/Jersonflo/iacamera.git
cd iacamera
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y completa tus claves (el archivo no se sube al repositorio):

```env
MISTRAL_API_KEY=...
GROQ_API_KEY=...
```

Para la versión web, copia `config.example.js` a `config.js` y completa las mismas claves.

Carga `Servo_eps32/Servo_movi/Servo_movi.ino` en tu ESP32, ajusta el puerto serial en `tracker.py` y ejecuta:

```bash
python main.py
```

## Autor

**Jerson Estiven Giraldo Florez** · [LinkedIn](https://linkedin.com/in/jerson-estiven-giraldo-florez-96a3031b0)
