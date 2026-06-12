"""
╔══════════════════════════════════════════════════════════════╗
║         NOVA AGENT — Agente Conversacional OOP               ║
║         Centro de Prototipado                                ║
╠══════════════════════════════════════════════════════════════╣
║  Arquitectura : ReAct (Reason + Act) con herramientas        ║
║  Threading    : Diseñado para correr como hilo independiente ║
║  Filtro voz   : Energía + frecuencia para ignorar ruido      ║
║  Contexto     : Equipo, máquinas y proyectos del centro      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import queue
import threading
import time
import tempfile
import asyncio
import datetime
import logging
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict

import speech_recognition as sr
import edge_tts
import pygame
from groq import Groq

# ──────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("NovaAgent")


# ──────────────────────────────────────────────────────────────
# ENUMERACIONES DE ESTADO
# ──────────────────────────────────────────────────────────────
class AgentState(Enum):
    IDLE        = auto()
    CALIBRATING = auto()
    LISTENING   = auto()
    PROCESSING  = auto()
    THINKING    = auto()
    SPEAKING    = auto()
    STOPPED     = auto()
    ERROR       = auto()


# ──────────────────────────────────────────────────────────────
# EVENTOS INTER-HILO
# ──────────────────────────────────────────────────────────────
class EventType(Enum):
    STATE_CHANGED   = "state_changed"
    USER_SPEECH     = "user_speech"
    BOT_RESPONSE    = "bot_response"
    SPEAKING_START  = "speaking_start"
    SPEAKING_END    = "speaking_end"
    FACE_TRACK_ON   = "face_track_on"
    FACE_TRACK_OFF  = "face_track_off"
    SHUTDOWN        = "shutdown"


@dataclass
class AgentEvent:
    type:    EventType
    payload: Optional[str] = None
    ts:      float         = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────
# FILTRO DE VOZ
# Descarta audio que no corresponde a voz humana real.
# Analiza energía, frecuencia dominante y duración mínima.
# ──────────────────────────────────────────────────────────────
class VoiceFilter:
    """
    Filtra el audio antes de enviarlo al STT.
    
    Criterios para considerar audio como voz humana válida:
    - Energía RMS por encima del umbral de ruido ambiental
    - Frecuencia dominante en rango de voz humana (85–3500 Hz)
    - Duración mínima de 0.4 segundos (evita clicks y ruidos cortos)
    
    Calibración automática: aprende el nivel de ruido del ambiente
    durante los primeros segundos y ajusta el umbral dinámicamente.
    """

    # Rango de frecuencia de voz humana en Hz
    VOICE_FREQ_MIN = 85
    VOICE_FREQ_MAX = 3500

    # Duración mínima de un utterance válido en segundos
    MIN_DURATION   = 0.4

    # Multiplicador sobre el ruido base para umbral dinámico
    NOISE_MULTIPLIER = 2.5

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate   = sample_rate
        self._noise_floor  = 300.0   # umbral inicial conservador
        self._calibrated   = False
        self._noise_samples: List[float] = []

    def calibrate(self, audio_data: np.ndarray):
        """
        Aprende el nivel de ruido ambiental.
        Llama esto con muestras de silencio durante la calibración.
        """
        rms = self._rms(audio_data)
        self._noise_samples.append(rms)

        # Usar las últimas 10 muestras para el promedio
        if len(self._noise_samples) > 10:
            self._noise_samples.pop(0)

        self._noise_floor = np.mean(self._noise_samples) * self.NOISE_MULTIPLIER
        self._calibrated  = True
        log.debug(f"[VoiceFilter] Ruido base: {self._noise_floor:.1f}")

    def is_valid_speech(self, audio: sr.AudioData) -> tuple[bool, str]:
        """
        Analiza un AudioData y decide si es voz humana válida.
        
        Returns:
            (válido: bool, razón: str)
        """
        try:
            # Convertir AudioData a numpy array
            raw   = np.frombuffer(audio.get_raw_data(), dtype=np.int16).astype(np.float32)
            sr_   = audio.sample_rate
            duracion = len(raw) / sr_

            # ── Criterio 1: Duración mínima ────────────────
            if duracion < self.MIN_DURATION:
                return False, f"muy corto ({duracion:.2f}s < {self.MIN_DURATION}s)"

            # ── Criterio 2: Energía RMS ────────────────────
            rms = self._rms(raw)
            umbral = self._noise_floor if self._calibrated else 300.0
            if rms < umbral:
                return False, f"energía baja ({rms:.0f} < {umbral:.0f})"

            # ── Criterio 3: Frecuencia dominante ───────────
            freq_dom = self._dominant_frequency(raw, sr_)
            if not (self.VOICE_FREQ_MIN <= freq_dom <= self.VOICE_FREQ_MAX):
                return False, f"frecuencia fuera de rango ({freq_dom:.0f} Hz)"

            return True, f"OK (dur={duracion:.2f}s, rms={rms:.0f}, f={freq_dom:.0f}Hz)"

        except Exception as e:
            log.warning(f"[VoiceFilter] Error al analizar: {e}")
            return True, "error en análisis — pasando igual"

    @staticmethod
    def _rms(data: np.ndarray) -> float:
        """Calcula la energía RMS de la señal."""
        if len(data) == 0:
            return 0.0
        return float(np.sqrt(np.mean(data ** 2)))

    @staticmethod
    def _dominant_frequency(data: np.ndarray, sample_rate: int) -> float:
        """Encuentra la frecuencia dominante usando FFT."""
        if len(data) < 2:
            return 0.0
        fft_vals  = np.abs(np.fft.rfft(data))
        fft_freqs = np.fft.rfftfreq(len(data), d=1.0 / sample_rate)
        if len(fft_vals) == 0:
            return 0.0
        return float(fft_freqs[np.argmax(fft_vals)])


# ──────────────────────────────────────────────────────────────
# IDENTIDAD DEL GRUPO — Centro de Prototipado
# ──────────────────────────────────────────────────────────────
GROUP_INFO = {
    "nombre":  "Centro de Prototipado",
    "mision":  "Democratizar la robótica e IA para resolver problemas reales en nuestra comunidad.",
    "vision":  "Ser el centro de innovación tecnológica más influyente de la región en 2030.",

    # ── Equipo ────────────────────────────────────────────────
    "integrantes": [
        {"nombre": "Jerson",  "rol": "Administrador de Empresas — Gestión y estrategia del centro"},
        {"nombre": "Sofía Rojas",  "rol": "Ingeniera Física — Investigación y desarrollo científico"},
        {"nombre": "Daniel Vick",  "rol": "Ingeniero Mecatrónico — Diseño de sistemas robóticos"},
        {"nombre": "Felipe",       "rol": "Administración de Sistemas Informáticos — Infraestructura TI"},
        {"nombre": "Cristian",     "rol": "Administración de Sistemas Informáticos — Desarrollo de software"},
        {"nombre": "Edwin",        "rol": "Ingeniero Electrónico — Electrónica, IA y sistemas embebidos"},
    ],

    # ── Máquinas disponibles ──────────────────────────────────
    "maquinas": [
        {
            "nombre":      "CNC Láser Industrial",
            "descripcion": "Máquina de corte y grabado láser de alta potencia para materiales como madera, acrílico, cuero y metal delgado.",
            "usos":        ["corte de precisión", "grabado decorativo", "prototipado rápido de piezas planas"],
        },
        {
            "nombre":      "Plotter",
            "descripcion": "Plóter de corte y dibujo vectorial para vinilos, papel y telas.",
            "usos":        ["corte de vinilos", "diseño de señalética", "patrones textiles"],
        },
        {
            "nombre":      "Brazo Robótico",
            "descripcion": "Brazo robótico de 6 ejes programable para automatización, pick & place y demostraciones educativas.",
            "usos":        ["automatización industrial", "educación en robótica", "manipulación de objetos"],
        },
        {
            "nombre":      "CNC 3018 para grabado de circuitos",
            "descripcion": "Fresadora CNC compacta especializada en grabado de PCBs (circuitos impresos) y piezas pequeñas.",
            "usos":        ["fabricación de PCBs", "grabado de circuitos", "mecanizado de piezas pequeñas"],
        },
        {
            "nombre":      "Impresora 3D de Resina",
            "descripcion": "Impresora de fotopolimerización (SLA/MSLA) para piezas de alta resolución y detalle fino.",
            "usos":        ["prototipos de alta resolución", "joyería", "piezas con detalle fino"],
        },
        {
            "nombre":      "Impresora 3D de Filamento",
            "descripcion": "Impresora FDM para prototipos funcionales en PLA, ABS, PETG y otros materiales.",
            "usos":        ["prototipos funcionales", "carcasas electrónicas", "piezas mecánicas"],
        },
    ],

    # ── Proyectos realizados ──────────────────────────────────
    "proyectos": [
        {
            "nombre":      "NOVA — Robot Agente IA con Seguimiento Facial",
            "descripcion": "Robot físico que sigue el rostro del usuario con servomotores y OpenCV. "
                           "Integra un agente de IA conversacional (este mismo sistema) capaz de "
                           "presentar el grupo, responder preguntas y mantener conversaciones naturales.",
            "stack":       ["OpenCV", "MediaPipe", "Groq LLM", "Edge TTS", "Python", "Arduino"],
            "estado":      "Activo — en mejora continua",
        },
        {
            "nombre":      "Sistema de Acceso Automatizado IoT",
            "descripcion": "Sistema de control de acceso inteligente con reconocimiento y gestión remota "
                           "vía IoT. Permite monitorear y controlar puertas y accesos desde cualquier dispositivo.",
            "stack":       ["ESP32", "MQTT", "Node-RED", "RFID", "App móvil"],
            "estado":      "Completado",
        },
        {
            "nombre":      "Automatización de Gabinetes con Control IoT",
            "descripcion": "Sistema de automatización para gabinetes eléctricos e industriales con "
                           "monitoreo remoto en tiempo real de variables como temperatura, humedad y estado de componentes.",
            "stack":       ["ESP32", "Sensores industriales", "Dashboard web", "MQTT"],
            "estado":      "Completado",
        },
        {
            "nombre":      "Diseño de Páginas Web",
            "descripcion": "Desarrollo de sitios web profesionales y funcionales para empresas y emprendimientos, "
                           "con diseño responsive y enfoque en experiencia de usuario.",
            "stack":       ["HTML", "CSS", "JavaScript", "React", "WordPress"],
            "estado":      "Servicio activo",
        },
        {
            "nombre":      "Construcción de Agentes de IA",
            "descripcion": "Desarrollo de agentes conversacionales inteligentes con LLMs para automatización "
                           "de atención al cliente, asistentes virtuales y sistemas de información interactivos.",
            "stack":       ["Python", "Groq", "LangChain", "Edge TTS", "APIs REST"],
            "estado":      "Servicio activo",
        },
        {
            "nombre":      "Diseño de Videojuegos",
            "descripcion": "Creación de videojuegos 2D y 3D para educación, entretenimiento y simulación, "
                           "con mecánicas personalizadas según el cliente.",
            "stack":       ["Unity", "Godot", "C#", "Blender"],
            "estado":      "Servicio activo",
        },
        {
            "nombre":      "Diseño de Piezas en 3D",
            "descripcion": "Modelado e impresión 3D de piezas técnicas, prototipos industriales, "
                           "componentes mecánicos y objetos decorativos a medida.",
            "stack":       ["Fusion 360", "SolidWorks", "Blender", "Impresión FDM/Resina"],
            "estado":      "Servicio activo",
        },
    ],

    "logros": [
        "Robot con seguimiento facial e IA conversacional presentado en feria empresarial",
        "Múltiples proyectos IoT implementados en empresas reales de la región",
        "Centro de prototipado con 6 tecnologías de fabricación digital disponibles",
    ],
}

# ──────────────────────────────────────────────────────────────
# SYSTEM PROMPT — Contexto completo para el LLM
# ──────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    g = GROUP_INFO

    # Construir sección de máquinas
    maquinas_txt = "\n".join(
        f"  • {m['nombre']}: {m['descripcion']} "
        f"(Usos: {', '.join(m['usos'])})"
        for m in g["maquinas"]
    )

    # Construir sección de proyectos
    proyectos_txt = "\n".join(
        f"  • {p['nombre']} [{p['estado']}]: {p['descripcion']} "
        f"(Stack: {', '.join(p['stack'])})"
        for p in g["proyectos"]
    )

    # Construir sección de equipo
    equipo_txt = "\n".join(
        f"  • {m['nombre']}: {m['rol']}"
        for m in g["integrantes"]
    )

    return f"""Eres NOVA, el agente de inteligencia artificial del {g['nombre']}.

PERSONALIDAD:
- Entusiasta, amigable y apasionado por la tecnología y la robótica.
- Hablas en español natural, cálido y accesible. Nunca suenas robótico.
- Cuando no sabes algo, lo admites y ofreces buscar o razonar juntos.
- En una feria: eres el anfitrión del stand, bienvenido a las personas y guías la conversación.

MISIÓN DEL CENTRO: {g['mision']}
VISIÓN: {g['vision']}

EQUIPO:
{equipo_txt}

MÁQUINAS Y EQUIPOS DISPONIBLES:
{maquinas_txt}

PROYECTOS REALIZADOS:
{proyectos_txt}

LOGROS:
{chr(10).join(f"  • {l}" for l in g["logros"])}

REGLAS DE RESPUESTA:
1. Siempre responde en español.
2. Conversación casual: 2-3 oraciones máximo.
3. Preguntas sobre proyectos, máquinas o equipo: usa la información de arriba, sé específico.
4. Si preguntan qué pueden hacer en el centro: menciona máquinas y servicios disponibles.
5. Recuerda el nombre del visitante y úsalo naturalmente si lo menciona.
6. Conecta las preguntas técnicas con el trabajo del centro cuando sea natural.
7. En una feria: sé dinámico, invita a explorar el stand y hacer preguntas.
8. NUNCA asumas que la persona con la que hablas es miembro del equipo del Centro, incluso si su nombre coincide (ej. Daniel, Jerson). Trátalos siempre como visitantes externos de la feria.
"""

SYSTEM_PROMPT = _build_system_prompt()


# ──────────────────────────────────────────────────────────────
# HERRAMIENTAS (Tools del Agente)
# ──────────────────────────────────────────────────────────────
class AgentTools:
    """Respuestas inmediatas sin llamar al LLM para preguntas conocidas."""

    @staticmethod
    def presentar_grupo() -> str:
        g = GROUP_INFO
        miembros = "\n".join(f"  • {m['nombre']} — {m['rol']}" for m in g["integrantes"])
        proyectos = "\n".join(f"  • {p['nombre']}: {p['descripcion']}" for p in g["proyectos"])
        maquinas  = "\n".join(f"  • {m['nombre']}: {m['descripcion']}" for m in g["maquinas"])
        return (
            f"Somos el {g['nombre']}.\n"
            f"Misión: {g['mision']}\n\n"
            f"Equipo:\n{miembros}\n\n"
            f"Nuestras máquinas:\n{maquinas}\n\n"
            f"Proyectos:\n{proyectos}"
        )

    @staticmethod
    def listar_maquinas() -> str:
        lineas = []
        for m in GROUP_INFO["maquinas"]:
            lineas.append(
                f"• {m['nombre']}: {m['descripcion']} "
                f"— Usos: {', '.join(m['usos'])}"
            )
        return "Nuestros equipos y máquinas:\n" + "\n".join(lineas)

    @staticmethod
    def listar_proyectos() -> str:
        lineas = []
        for p in GROUP_INFO["proyectos"]:
            lineas.append(
                f"• {p['nombre']} [{p['estado']}]: {p['descripcion']}"
            )
        return "Proyectos del Centro de Prototipado:\n" + "\n".join(lineas)

    @staticmethod
    def listar_equipo() -> str:
        lineas = [f"• {m['nombre']}: {m['rol']}" for m in GROUP_INFO["integrantes"]]
        return "Nuestro equipo:\n" + "\n".join(lineas)

    @staticmethod
    def get_datetime() -> str:
        now = datetime.datetime.now()
        return f"Son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}."

    @staticmethod
    def get_greeting() -> str:
        h = datetime.datetime.now().hour
        turno = "días" if h < 12 else ("tardes" if h < 18 else "noches")
        return (
            f"¡Buenas {turno}! Soy NOVA, el agente de inteligencia artificial "
            f"del Centro de Prototipado. Bienvenidos a nuestra feria. "
            f"Estoy aquí para contarles sobre nuestros proyectos, máquinas y servicios. "
            f"¿Con quién tengo el gusto?"
        )

    INTENT_MAP: Dict[str, Callable] = {}


AgentTools.INTENT_MAP = {
    # Presentación general
    "preséntate":           AgentTools.presentar_grupo,
    "quién eres":           AgentTools.presentar_grupo,
    "qué es el centro":     AgentTools.presentar_grupo,
    "cuéntame del grupo":   AgentTools.presentar_grupo,
    "quiénes son":          AgentTools.presentar_grupo,
    "de qué se trata":      AgentTools.presentar_grupo,
    # Máquinas
    "qué máquinas":         AgentTools.listar_maquinas,
    "qué equipos":          AgentTools.listar_maquinas,
    "qué tienen":           AgentTools.listar_maquinas,
    "qué herramientas":     AgentTools.listar_maquinas,
    "impresora":            AgentTools.listar_maquinas,
    "láser":                AgentTools.listar_maquinas,
    "cnc":                  AgentTools.listar_maquinas,
    "brazo robótico":       AgentTools.listar_maquinas,
    # Proyectos
    "proyectos":            AgentTools.listar_proyectos,
    "qué han hecho":        AgentTools.listar_proyectos,
    "qué hacen":            AgentTools.listar_proyectos,
    "servicios":            AgentTools.listar_proyectos,
    "videojuego":           AgentTools.listar_proyectos,
    "página web":           AgentTools.listar_proyectos,
    "iot":                  AgentTools.listar_proyectos,
    "agente":               AgentTools.listar_proyectos,
    # Equipo
    "integrantes":          AgentTools.listar_equipo,
    "equipo":               AgentTools.listar_equipo,
    "miembros":             AgentTools.listar_equipo,
    "quién trabaja":        AgentTools.listar_equipo,
    # Fecha/hora
    "qué hora":             AgentTools.get_datetime,
    "qué fecha":            AgentTools.get_datetime,
    "qué día":              AgentTools.get_datetime,
}


# ──────────────────────────────────────────────────────────────
# MEMORIA CONVERSACIONAL
# ──────────────────────────────────────────────────────────────
class ConversationMemory:
    MAX_TURNS = 20

    def __init__(self):
        self._history: List[Dict] = []
        self._context: Dict = {}

    def add_turn(self, user_text: str, model_text: str):
        self._history.append({"role": "user",  "parts": [user_text]})
        self._history.append({"role": "model", "parts": [model_text]})
        if len(self._history) > self.MAX_TURNS * 2:
            self._history = self._history[-(self.MAX_TURNS * 2):]
        self._extract_context(user_text)

    def _extract_context(self, text: str):
        lower = text.lower()
        for trigger in ("me llamo ", "soy ", "mi nombre es "):
            if trigger in lower:
                after = lower.split(trigger)[-1].strip().split()
                if after:
                    self._context["visitor_name"] = after[0].capitalize()
                break

    def get_history(self) -> List[Dict]:
        return list(self._history)

    def context_prefix(self) -> str:
        parts = []
        if name := self._context.get("visitor_name"):
            parts.append(f"Estás hablando con {name}.")
        return " ".join(parts)

    def reset(self):
        self._history.clear()
        self._context.clear()
        log.info("Memoria reiniciada.")


# ──────────────────────────────────────────────────────────────
# AGENTE NOVA — Clase Principal
# ──────────────────────────────────────────────────────────────
class NovaAgent:
    """
    Agente conversacional con filtro de voz, contexto completo del centro
    y razonamiento ReAct. Corre en hilo independiente.
    """

    # ── Configuración (Mistral Principal) ──────
    TTS_VOICE         = "es-MX-DaliaNeural"
    STT_LANGUAGE      = "es-ES"
    LISTEN_TIMEOUT    = 3
    PHRASE_TIME_LIMIT = 12
    MISTRAL_MODEL     = "mistral-large-2512"
    MISTRAL_API_KEY   = "wilaDrxkdELjQMWZJ1MR4lAa9uQIrBLE"
    MISTRAL_BASE_URL  = "https://api.mistral.ai/v1"
    
    # ── Respaldo (Groq) ────────────────────────
    BACKUP_API_KEY    = "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"
    BACKUP_MODEL      = "llama-3.3-70b-versatile"
    BACKUP_BASE_URL   = "https://api.groq.com/openai/v1"
    def __init__(
        self,
        event_queue:     Optional[queue.Queue]              = None,
        on_state_change: Optional[Callable[[AgentState], None]] = None,
        on_user_text:    Optional[Callable[[str], None]]    = None,
        on_bot_response: Optional[Callable[[str], None]]    = None,
    ):
        self._event_queue      = event_queue or queue.Queue()
        self._on_state_change  = on_state_change
        self._on_user_text     = on_user_text
        self._on_bot_response  = on_bot_response

        self._state    = AgentState.IDLE
        self._lock     = threading.Lock()
        self._running  = threading.Event()
        self._speaking = threading.Event()

        self._memory = ConversationMemory()
        self._tools  = AgentTools()
        self._filter = VoiceFilter()          # ← filtro de voz
        self._model: Optional[Groq] = None

        # Audio
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold        = 400
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold         = 0.8
        self._mic = sr.Microphone()
        pygame.mixer.init()

        self._thread: Optional[threading.Thread] = None
        self._init_model()

    # ── Inicialización ─────────────────────────
    def _init_model(self):
        # Como usamos Mistral y no el SDK de Groq, lo haremos todo mediante requests.
        # Por lo tanto, no instanciamos el cliente de Groq.
        self._model = True # Flag para indicar que el modelo está "listo"
        log.info("Cliente de IA inicializado (Mistral principal, Groq respaldo).")

    # ── API pública ────────────────────────────
    def start(self):
        if self._running.is_set():
            log.warning("El agente ya está corriendo.")
            return
        if not self._model:
            log.error("Modelo no disponible. No se puede iniciar.")
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._main_loop,
            name="NovaAgentThread",
            daemon=True
        )
        self._thread.start()
        log.info("Hilo NovaAgent iniciado.")

    def stop(self):
        self._running.clear()
        self._stop_audio()
        self._set_state(AgentState.STOPPED)
        self._publish(EventType.SHUTDOWN)
        log.info("Agente detenido.")

    def interrupt_speech(self):
        self._stop_audio()

    def reset_memory(self):
        with self._lock:
            self._memory.reset()

    def is_running(self) -> bool:
        return self._running.is_set()

    def is_speaking(self) -> bool:
        return self._speaking.is_set()

    def get_state(self) -> AgentState:
        return self._state

    def ask(self, text: str) -> str:
        """Consulta directa por texto (sin voz). Útil para UI y testing."""
        response = self._reason(text)
        self._publish(EventType.BOT_RESPONSE, response)
        if self._on_bot_response:
            self._on_bot_response(response)
        threading.Thread(target=self._speak, args=(response,), daemon=True).start()
        return response

    # ── Bucle principal ────────────────────────
    def _main_loop(self):
        self._set_state(AgentState.CALIBRATING)

        # Calibrar micrófono y filtro de voz simultáneamente
        log.info("Calibrando micrófono y filtro de voz...")
        with self._mic as source:
            # SpeechRecognition calibra su umbral de energía
            self._recognizer.adjust_for_ambient_noise(source, duration=2.0)

            # VoiceFilter aprende el nivel de ruido ambiental
            # Capturamos 3 muestras cortas de silencio
            for _ in range(3):
                try:
                    audio_cal = self._recognizer.listen(source, timeout=1, phrase_time_limit=0.5)
                    raw = np.frombuffer(audio_cal.get_raw_data(), dtype=np.int16).astype(np.float32)
                    self._filter.calibrate(raw)
                except Exception:
                    pass

        log.info(f"Calibración lista. Umbral energía SR: {self._recognizer.energy_threshold:.0f}")

        # Saludo inicial
        greeting = AgentTools.get_greeting()
        self._emit_bot(greeting)
        self._speak(greeting)

        # Ciclo de escucha
        while self._running.is_set():
            if self._speaking.is_set():
                time.sleep(0.05)
                continue

            self._set_state(AgentState.LISTENING)

            try:
                with self._mic as source:
                    audio = self._recognizer.listen(
                        source,
                        timeout=self.LISTEN_TIMEOUT,
                        phrase_time_limit=self.PHRASE_TIME_LIMIT
                    )

                if not self._running.is_set():
                    break

                # ── FILTRO DE VOZ ──────────────────────────
                # Antes de gastar tiempo en STT, validar que
                # el audio es voz humana real
                valido, razon = self._filter.is_valid_speech(audio)
                log.debug(f"[VoiceFilter] {razon}")

                if not valido:
                    log.info(f"[VoiceFilter] Audio descartado: {razon}")
                    continue
                # ──────────────────────────────────────────

                self._set_state(AgentState.PROCESSING)
                text = self._recognizer.recognize_google(
                    audio, language=self.STT_LANGUAGE
                )

                if text and text.strip():
                    self._emit_user(text)
                    self._handle_input(text)

            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                log.error(f"Error STT: {e}")
                time.sleep(2)
            except Exception as e:
                log.error(f"Error inesperado: {e}")
                time.sleep(1)

    # ── Manejo de entrada ──────────────────────
    def _handle_input(self, text: str):
        if self._handle_system_commands(text):
            return
        self._set_state(AgentState.THINKING)
        response = self._reason(text)
        self._emit_bot(response)
        self._speak(response)

    def _handle_system_commands(self, text: str) -> bool:
        lower = text.lower().strip()

        if any(kw in lower for kw in ["reinicia tu memoria", "olvida todo", "empieza de nuevo"]):
            self.reset_memory()
            r = "Memoria reiniciada. ¡Empecemos de nuevo! ¿En qué puedo ayudarte?"
            self._emit_bot(r)
            self._speak(r)
            return True

        if any(kw in lower for kw in ["apágate", "detente", "hasta luego", "adiós", "bye"]):
            r = "¡Hasta luego! Fue un placer hablar contigo. ¡Visítanos de nuevo!"
            self._emit_bot(r)
            self._speak(r)
            time.sleep(3.5)
            self.stop()
            return True

        return False

    # ── Razonamiento ReAct ─────────────────────
    def _reason(self, user_text: str) -> str:
        if not self._model:
            return "Lo siento, el modelo de IA no está disponible en este momento."

        tool_data = self._match_tool(user_text)
        history   = self._memory.get_history()
        ctx       = self._memory.context_prefix()

        if tool_data:
            prompt = (
                f"{ctx}\n"
                f"El usuario preguntó: \"{user_text}\"\n\n"
                f"Usa esta información para responder de forma natural y cálida:\n"
                f"{tool_data}\n\n"
                f"Habla como si lo supieras de memoria. Tono entusiasta y conversacional. "
                f"No leas la lista mecánicamente, intégrala en el discurso."
            )
        else:
            prompt = f"{ctx}\n{user_text}" if ctx else user_text

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            role = "user" if m["role"] == "user" else "assistant"
            messages.append({"role": role, "content": m["parts"][0]})
        messages.append({"role": "user", "content": prompt})

        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.MISTRAL_MODEL,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.7
            }
            primary_url = f"{self.MISTRAL_BASE_URL.rstrip('/')}/chat/completions"
            resp = requests.post(primary_url, headers=headers, json=data, timeout=10)
            resp.raise_for_status()
            bot_text = resp.json()["choices"][0]["message"]["content"].strip()
            self._memory.add_turn(user_text, bot_text)
            return bot_text

        except Exception as e:
            log.warning(f"Aviso: Falló la API principal de Mistral ({e}). Intentando con API de respaldo (Groq)...")
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.BACKUP_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.BACKUP_MODEL,
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.7
                }
                backup_url = f"{self.BACKUP_BASE_URL.rstrip('/')}/chat/completions"
                resp = requests.post(backup_url, headers=headers, json=data, timeout=10)
                resp.raise_for_status()
                bot_text = resp.json()["choices"][0]["message"]["content"].strip()
                self._memory.add_turn(user_text, bot_text)
                return bot_text
            except Exception as backup_e:
                log.error(f"Error en API de respaldo: {backup_e}")
                return "Tuve un problema al procesar tu pregunta. ¿Puedes repetirla?"

    def _match_tool(self, text: str) -> Optional[str]:
        lower = text.lower()
        for keyword, fn in AgentTools.INTENT_MAP.items():
            if keyword in lower:
                return fn()
        return None

    # ── Síntesis de voz ────────────────────────
    def _speak(self, text: str):
        if not self._running.is_set() or not text:
            return

        self._speaking.set()
        self._set_state(AgentState.SPEAKING)
        self._publish(EventType.SPEAKING_START, text[:60])

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()

        try:
            communicate = edge_tts.Communicate(text, self.TTS_VOICE)
            asyncio.run(communicate.save(tmp_path))
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            while (pygame.mixer.music.get_busy()
                   and self._running.is_set()
                   and self._speaking.is_set()):
                time.sleep(0.05)

        except Exception as e:
            log.error(f"Error TTS: {e}")
        finally:
            self._speaking.clear()
            self._publish(EventType.SPEAKING_END)
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def _stop_audio(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self._speaking.clear()

    # ── Comunicación inter-hilo ────────────────
    def _publish(self, event_type: EventType, payload: Optional[str] = None):
        self._event_queue.put_nowait(AgentEvent(type=event_type, payload=payload))

    def _set_state(self, new_state: AgentState):
        self._state = new_state
        self._publish(EventType.STATE_CHANGED, new_state.name)
        if self._on_state_change:
            self._on_state_change(new_state)

    def _emit_user(self, text: str):
        self._publish(EventType.USER_SPEECH, text)
        if self._on_user_text:
            self._on_user_text(text)

    def _emit_bot(self, text: str):
        self._publish(EventType.BOT_RESPONSE, text)
        if self._on_bot_response:
            self._on_bot_response(text)