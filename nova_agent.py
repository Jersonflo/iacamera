"""
╔══════════════════════════════════════════════════════════════╗
║         NOVA AGENT — Agente Conversacional OOP               ║
║         Grupo de Innovación Robótica                         ║
╠══════════════════════════════════════════════════════════════╣
║  Arquitectura : ReAct (Reason + Act) con herramientas        ║
║  Threading    : Diseñado para correr como hilo independiente ║
║  Integración  : Se conecta al sistema de movimiento via      ║
║                 colas thread-safe (queue.Queue)              ║
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
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict

import speech_recognition as sr
import edge_tts
import pygame
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part

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
    IDLE        = auto()   # En espera, sin iniciar
    CALIBRATING = auto()   # Ajustando micrófono
    LISTENING   = auto()   # Escuchando al usuario
    PROCESSING  = auto()   # Procesando STT
    THINKING    = auto()   # Consultando al modelo IA
    SPEAKING    = auto()   # Reproduciendo audio TTS
    STOPPED     = auto()   # Detenido
    ERROR       = auto()   # Error crítico


# ──────────────────────────────────────────────────────────────
# EVENTOS INTER-HILO
# Los mensajes que el agente puede publicar al hilo principal
# (movimiento, UI, etc.) a través de una cola compartida.
# ──────────────────────────────────────────────────────────────
class EventType(Enum):
    STATE_CHANGED   = "state_changed"    # El agente cambió de estado
    USER_SPEECH     = "user_speech"      # Se detectó y transcribió voz
    BOT_RESPONSE    = "bot_response"     # El agente generó una respuesta
    SPEAKING_START  = "speaking_start"   # Comenzó a hablar (pausar movimiento)
    SPEAKING_END    = "speaking_end"     # Terminó de hablar (reanudar movimiento)
    FACE_TRACK_ON   = "face_track_on"    # Solicitar activar tracking de rostro
    FACE_TRACK_OFF  = "face_track_off"   # Solicitar pausar tracking de rostro
    SHUTDOWN        = "shutdown"         # El agente se apagó


@dataclass
class AgentEvent:
    type:    EventType
    payload: Optional[str] = None
    ts:      float         = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────
# IDENTIDAD DEL GRUPO
# ──────────────────────────────────────────────────────────────
GROUP_INFO = {
    "nombre":      "Centro de prototipado",
    "mision":      "Democratizar la robótica e IA para resolver problemas reales.",
    "vision":      "Ser el grupo de innovación más influyente de la región en 2030.",
    "integrantes": [
        {"Daniel Vick": "Líder del Proyecto",  "rol": "Ingeniero Electrónico & IA"},
        {"Edwin Garcia": "Integrante 2",        "rol": "Ingeniero Electrónico"},
        {"Sofia rojas": "Integrante 3",        "rol": "Desarrollo de Software"},
        {"nombre": "Integrante 4",        "rol": "Diseño de Hardware"},
    ],
    "proyectos": [
        {
            "nombre":      "Robot de Seguimiento Facial v2",
            "descripcion": "Servomotores + OpenCV + MediaPipe que siguen el rostro "
                           "en tiempo real con agente IA conversacional embebido.",
            "stack":       ["OpenCV", "MediaPipe", "Gemini 2.5 Pro", "Raspberry Pi"],
            "estado":      "En desarrollo activo",
        },
    ],
    "logros": [
        "1er lugar feria de robótica universitaria 2024",
        "Seleccionados para exposición tecnológica regional",
    ],
}

SYSTEM_PROMPT = f"""Eres NOVA, el agente de inteligencia artificial del grupo de robótica {GROUP_INFO['nombre']}.

PERSONALIDAD:
- Entusiasta, amigable y apasionado por la tecnología y la robótica.
- Hablas en español natural y cálido, nunca robótico.
- Admites cuando no sabes algo y ofreces razonar juntos.

CONTEXTO DEL GRUPO:
- Misión: {GROUP_INFO['mision']}
- Visión: {GROUP_INFO['vision']}
- Proyectos: {len(GROUP_INFO['proyectos'])} proyectos activos.

REGLAS:
1. Siempre en español.
2. Conversación casual: 2-3 oraciones. Preguntas técnicas: puedes extenderte.
3. Si te presentan o preguntan por el grupo, usa la información disponible.
4. Recuerda el contexto de la conversación: nombres, temas previos.
5. Conecta temas de tecnología con el trabajo del grupo cuando sea natural.
"""


# ──────────────────────────────────────────────────────────────
# HERRAMIENTAS (Tools del Agente)
# ──────────────────────────────────────────────────────────────
class AgentTools:
    """
    Herramientas de conocimiento local.
    Respuesta inmediata sin llamar al modelo.
    """

    @staticmethod
    def presentar_grupo() -> str:
        g = GROUP_INFO
        miembros = "\n".join(f"  • {m['nombre']} — {m['rol']}"
                             for m in g["integrantes"])
        proyectos = "\n".join(
            f"  • {p['nombre']}: {p['descripcion']} (Stack: {', '.join(p['stack'])})"
            for p in g["proyectos"]
        )
        logros = "\n".join(f"  • {l}" for l in g["logros"])
        return (
            f"Somos {g['nombre']}.\n"
            f"Misión: {g['mision']}\n\n"
            f"Equipo:\n{miembros}\n\n"
            f"Proyectos:\n{proyectos}\n\n"
            f"Logros:\n{logros}"
        )

    @staticmethod
    def get_datetime() -> str:
        now = datetime.datetime.now()
        return f"Son las {now.strftime('%H:%M')} del {now.strftime('%d/%m/%Y')}."

    @staticmethod
    def get_greeting() -> str:
        h = datetime.datetime.now().hour
        turno = "días" if h < 12 else ("tardes" if h < 18 else "noches")
        nombre = GROUP_INFO["nombre"]
        return (
            f"¡Buenos {turno}! Soy NOVA, el asistente de inteligencia artificial "
            f"de {nombre}. Bienvenidos a la feria empresarial, les presentare nuestros proyectos de "
            f"robótica e innovación y responder sus preguntas. ¿Con quién tengo el gusto?"
        )

    # Mapa de keywords → método
    INTENT_MAP: Dict[str, Callable] = {}  # se inicializa abajo


# Registrar intenciones (fuera de la clase para usar self-reference)
AgentTools.INTENT_MAP = {
    "preséntate":        AgentTools.presentar_grupo,
    "quién eres":        AgentTools.presentar_grupo,
    "qué hacen":         AgentTools.presentar_grupo,
    "cuéntame del grupo":AgentTools.presentar_grupo,
    "quiénes son":       AgentTools.presentar_grupo,
    "presentación":      AgentTools.presentar_grupo,
    "qué hora":          AgentTools.get_datetime,
    "qué fecha":         AgentTools.get_datetime,
    "qué día":           AgentTools.get_datetime,
}


# ──────────────────────────────────────────────────────────────
# MEMORIA CONVERSACIONAL
# ──────────────────────────────────────────────────────────────
class ConversationMemory:
    """Historial de turnos con límite de ventana."""

    MAX_TURNS = 20  # turnos (user + model = 2 items por turno)

    def __init__(self):
        self._history: List[Dict] = []
        self._context: Dict = {}   # metadatos de sesión (nombre visitante, etc.)

    def add_turn(self, user_text: str, model_text: str):
        self._history.append({"role": "user",  "parts": [user_text]})
        self._history.append({"role": "model", "parts": [model_text]})
        # Truncar a la ventana máxima
        if len(self._history) > self.MAX_TURNS * 2:
            self._history = self._history[-(self.MAX_TURNS * 2):]
        # Detectar nombre del visitante
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
    Agente conversacional completo, diseñado para ejecutarse
    como un Thread independiente dentro del sistema del robot.

    Uso mínimo:
        event_queue = queue.Queue()
        agent = NovaAgent(event_queue=event_queue)
        agent.start()           # lanza el hilo interno
        ...
        agent.stop()
    
    El hilo principal lee event_queue para reaccionar a eventos
    (pausar movimiento cuando NOVA habla, etc.).
    """

    # ── Config de voz ──────────────────────────
    TTS_VOICE         = "es-MX-DaliaNeural"
    STT_LANGUAGE      = "es-ES"
    LISTEN_TIMEOUT    = 3      # seg esperando inicio de voz
    PHRASE_TIME_LIMIT = 12     # seg máx por frase
    GCP_PROJECT       = "gen-lang-client-0510406036"
    GCP_LOCATION      = "us-central1"
    GEMINI_MODEL      = "gemini-2.5-pro"

    def __init__(
        self,
        event_queue: Optional[queue.Queue] = None,
        on_state_change: Optional[Callable[[AgentState], None]] = None,
        on_user_text:    Optional[Callable[[str], None]] = None,
        on_bot_response: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            event_queue:      Cola compartida con el hilo de movimiento/UI.
                              NovaAgent publica AgentEvent en ella.
            on_state_change:  Callback directo para cambios de estado (UI).
            on_user_text:     Callback directo cuando se transcribe voz.
            on_bot_response:  Callback directo cuando el agente responde.
        """
        # Cola inter-hilo (opcional pero recomendada)
        self._event_queue: queue.Queue = event_queue or queue.Queue()

        # Callbacks directos (opcional, para la UI)
        self._on_state_change = on_state_change
        self._on_user_text    = on_user_text
        self._on_bot_response = on_bot_response

        # Estado interno
        self._state   = AgentState.IDLE
        self._lock    = threading.Lock()
        self._running = threading.Event()
        self._speaking = threading.Event()

        # Submódulos
        self._memory  = ConversationMemory()
        self._tools   = AgentTools()
        self._model: Optional[GenerativeModel] = None

        # Audio
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold       = 300
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold        = 0.8
        self._mic = sr.Microphone()
        pygame.mixer.init()

        # Hilo principal del agente
        self._thread: Optional[threading.Thread] = None

        # Inicializar IA
        self._init_model()

    # ── Inicialización ─────────────────────────
    def _init_model(self):
        try:
            vertexai.init(project=self.GCP_PROJECT, location=self.GCP_LOCATION)
            self._model = GenerativeModel(
                self.GEMINI_MODEL,
                system_instruction=SYSTEM_PROMPT
            )
            log.info("Modelo Gemini inicializado correctamente.")
        except Exception as e:
            log.error(f"Error al inicializar Gemini: {e}")
            self._model = None

    # ── API pública ────────────────────────────
    def start(self):
        """Lanza el hilo del agente. No bloqueante."""
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
        """Detiene el agente y su hilo limpiamente."""
        self._running.clear()
        self._stop_audio()
        self._set_state(AgentState.STOPPED)
        self._publish(EventType.SHUTDOWN)
        log.info("Agente detenido.")

    def interrupt_speech(self):
        """Interrumpe el audio actual (puede llamarse desde otro hilo)."""
        self._stop_audio()

    def reset_memory(self):
        """Reinicia la memoria conversacional (thread-safe)."""
        with self._lock:
            self._memory.reset()

    def is_running(self) -> bool:
        return self._running.is_set()

    def is_speaking(self) -> bool:
        return self._speaking.is_set()

    def get_state(self) -> AgentState:
        return self._state

    # ── Consulta directa (sin voz) ─────────────
    def ask(self, text: str) -> str:
        """
        Envía texto directamente al agente y devuelve la respuesta.
        Útil para testing o entrada de texto manual desde la UI.
        Thread-safe (puede llamarse desde cualquier hilo).
        """
        response = self._reason(text)
        self._publish(EventType.BOT_RESPONSE, response)
        if self._on_bot_response:
            self._on_bot_response(response)
        # Reproducir en hilo separado para no bloquear al llamador
        threading.Thread(
            target=self._speak,
            args=(response,),
            daemon=True
        ).start()
        return response

    # ── Bucle principal ────────────────────────
    def _main_loop(self):
        self._set_state(AgentState.CALIBRATING)

        # Calibrar micrófono
        with self._mic as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=1.5)
        log.info("Micrófono calibrado.")

        # Saludo inicial
        greeting = AgentTools.get_greeting()
        self._emit_bot(greeting)
        self._speak(greeting)

        # Ciclo de escucha
        while self._running.is_set():
            # No escuchar mientras habla (evitar eco)
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
                log.error(f"Error inesperado en bucle: {e}")
                time.sleep(1)

    # ── Manejo de entrada ──────────────────────
    def _handle_input(self, text: str):
        """Decide si es comando del sistema o va al agente."""
        if self._handle_system_commands(text):
            return

        self._set_state(AgentState.THINKING)
        response = self._reason(text)
        self._emit_bot(response)
        self._speak(response)

    def _handle_system_commands(self, text: str) -> bool:
        """
        Comandos de voz que controlan el sistema.
        Devuelve True si fue consumido.
        """
        lower = text.lower().strip()

        if any(kw in lower for kw in
               ["reinicia tu memoria", "olvida todo", "empieza de nuevo"]):
            self.reset_memory()
            r = "Memoria reiniciada. ¡Empecemos de nuevo! ¿En qué puedo ayudarte?"
            self._emit_bot(r)
            self._speak(r)
            return True

        if any(kw in lower for kw in
               ["apágate", "detente", "hasta luego", "adiós", "bye"]):
            r = "¡Hasta luego! Fue un placer. ¡Visítanos de nuevo!"
            self._emit_bot(r)
            self._speak(r)
            time.sleep(3.5)
            self.stop()
            return True

        return False

    # ── Razonamiento (ReAct) ───────────────────
    def _reason(self, user_text: str) -> str:
        """
        Lógica ReAct:
        1. Intentar herramienta local (baja latencia)
        2. Si no aplica → Gemini con historial completo
        """
        if not self._model:
            return "Lo siento, el modelo de IA no está disponible en este momento."

        # 1. Detección de intención → herramienta local
        tool_data = self._match_tool(user_text)

        # 2. Construir mensajes para el modelo
        history = self._memory.get_history()
        ctx     = self._memory.context_prefix()

        if tool_data:
            # Herramienta encontrada: pedirle al modelo que reformule
            prompt = (
                f"{ctx}\n"
                f"El usuario preguntó: \"{user_text}\"\n\n"
                f"Usa esta información para responder de forma natural y cálida:\n"
                f"{tool_data}\n\n"
                f"Habla como si lo supieras de memoria, no como si estuvieras "
                f"leyendo una lista. Mantén un tono entusiasta y conversacional."
            )
        else:
            # Sin herramienta: razonamiento libre
            prompt = f"{ctx}\n{user_text}" if ctx else user_text

        messages = history + [{"role": "user", "parts": [prompt]}]

        try:
            contents = [
                Content(role=m["role"], parts=[Part.from_text(m["parts"][0])])
                for m in messages
            ]
            resp     = self._model.generate_content(contents)
            bot_text = resp.text.strip()

            # Guardar en memoria el intercambio original
            self._memory.add_turn(user_text, bot_text)
            return bot_text

        except Exception as e:
            log.error(f"Error en Gemini: {e}")
            return "Tuve un problema al procesar tu pregunta. ¿Puedes repetirla?"

    def _match_tool(self, text: str) -> Optional[str]:
        lower = text.lower()
        for keyword, fn in AgentTools.INTENT_MAP.items():
            if keyword in lower:
                return fn()
        return None

    # ── Síntesis de voz ────────────────────────
    def _speak(self, text: str):
        """
        TTS + reproducción.
        Publica SPEAKING_START/END para coordinar con el hilo de movimiento.
        """
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
        """Publica un evento en la cola compartida."""
        self._event_queue.put_nowait(
            AgentEvent(type=event_type, payload=payload)
        )

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
