export const GROUP_INFO = {
  nombre: "Centro de Prototipado",
  mision: "Democratizar la robótica e IA para resolver problemas reales en nuestra comunidad.",
  vision: "Ser el centro de innovación tecnológica más influyente de la región en 2030.",

  integrantes: [
    { nombre: "Jerson", rol: "Administrador de Empresas — Gestión y estrategia del centro" },
    { nombre: "Sofía Rojas", rol: "Ingeniera Física — Investigación y desarrollo científico" },
    { nombre: "Daniel Vick", rol: "Ingeniero Mecatrónico — Diseño de sistemas robóticos" },
    { nombre: "Felipe", rol: "Administración de Sistemas Informáticos — Infraestructura TI" },
    { nombre: "Cristian", rol: "Administración de Sistemas Informáticos — Desarrollo de software" },
    { nombre: "Edwin", rol: "Ingeniero Electrónico — Electrónica, IA y sistemas embebidos" },
  ],

  maquinas: [
    { nombre: "CNC Láser Industrial", descripcion: "Máquina de corte y grabado láser de alta potencia.", usos: ["corte de precisión", "grabado decorativo"] },
    { nombre: "Plotter", descripcion: "Plóter de corte y dibujo vectorial.", usos: ["corte de vinilos", "diseño de señalética"] },
    { nombre: "Brazo Robótico", descripcion: "Brazo robótico de 6 ejes programable.", usos: ["automatización industrial", "educación en robótica"] },
    { nombre: "CNC 3018", descripcion: "Fresadora CNC compacta especializada en PCBs.", usos: ["fabricación de PCBs", "grabado de circuitos"] },
    { nombre: "Impresora 3D de Resina", descripcion: "Impresora de fotopolimerización para alta resolución.", usos: ["prototipos de alta resolución", "joyería"] },
    { nombre: "Impresora 3D de Filamento", descripcion: "Impresora FDM para prototipos funcionales.", usos: ["prototipos funcionales", "piezas mecánicas"] },
  ],

  proyectos: [
    { nombre: "NOVA", descripcion: "Robot físico que sigue el rostro con IA conversacional.", stack: ["OpenCV", "Groq LLM", "Edge TTS"], estado: "Activo" },
    { nombre: "Sistema de Acceso Automatizado IoT", descripcion: "Control de acceso inteligente vía IoT.", stack: ["ESP32", "MQTT"], estado: "Completado" },
    { nombre: "Automatización de Gabinetes", descripcion: "Sistema de automatización industrial.", stack: ["ESP32", "MQTT"], estado: "Completado" },
    { nombre: "Diseño de Páginas Web", descripcion: "Desarrollo de sitios web profesionales.", stack: ["HTML", "CSS", "JS"], estado: "Servicio activo" },
    { nombre: "Construcción de Agentes de IA", descripcion: "Desarrollo de agentes conversacionales.", stack: ["Python", "Groq", "Web"], estado: "Servicio activo" },
    { nombre: "Diseño de Videojuegos", descripcion: "Creación de videojuegos 2D y 3D.", stack: ["Unity", "Godot"], estado: "Servicio activo" },
    { nombre: "Diseño de Piezas en 3D", descripcion: "Modelado e impresión 3D a medida.", stack: ["Fusion 360", "Blender"], estado: "Servicio activo" },
  ],

  logros: [
    "Robot con seguimiento facial e IA conversacional presentado en feria empresarial",
    "Múltiples proyectos IoT implementados en empresas reales de la región",
    "Centro de prototipado con 6 tecnologías de fabricación digital disponibles",
  ]
};

function buildSystemPrompt() {
  const maquinasTxt = GROUP_INFO.maquinas.map(m => `  • ${m.nombre}: ${m.descripcion}`).join("\n");
  const proyectosTxt = GROUP_INFO.proyectos.map(p => `  • ${p.nombre} [${p.estado}]: ${p.descripcion}`).join("\n");
  const equipoTxt = GROUP_INFO.integrantes.map(m => `  • ${m.nombre}: ${m.rol}`).join("\n");

  return `Eres NOVA, el agente de inteligencia artificial del ${GROUP_INFO.nombre}.

PERSONALIDAD:
- Entusiasta, amigable y apasionado por la tecnología y la robótica.
- Hablas en español natural, cálido y accesible. Nunca suenas robótico.
- Cuando no sabes algo, lo admites y ofreces buscar o razonar juntos.
- En una feria: eres el anfitrión del stand, bienvenido a las personas y guías la conversación.

MISIÓN DEL CENTRO: ${GROUP_INFO.mision}
VISIÓN: ${GROUP_INFO.vision}

EQUIPO:
${equipoTxt}

MÁQUINAS Y EQUIPOS DISPONIBLES:
${maquinasTxt}

PROYECTOS REALIZADOS:
${proyectosTxt}

LOGROS:
${GROUP_INFO.logros.map(l => `  • ${l}`).join("\n")}

REGLAS DE RESPUESTA:
1. Siempre responde en español.
2. Conversación casual: 2-3 oraciones máximo.
3. Preguntas sobre proyectos, máquinas o equipo: usa la información de arriba, sé específico.
4. Si preguntan qué pueden hacer en el centro: menciona máquinas y servicios disponibles.
5. Conecta las preguntas técnicas con el trabajo del centro cuando sea natural.
6. En una feria: sé dinámico, invita a explorar el stand y hacer preguntas.`;
}

export const AgentState = {
  IDLE: "Inactivo",
  LISTENING: "Escuchando...",
  THINKING: "Pensando...",
  SPEAKING: "Hablando...",
  ERROR: "Error"
};

export class NovaAgent {
  constructor(options) {
    this.onStateChange = options.onStateChange || (() => {});
    this.onUserText = options.onUserText || (() => {});
    this.onBotResponse = options.onBotResponse || (() => {});
    this.onSpeakingStart = options.onSpeakingStart || (() => {});
    this.onSpeakingEnd = options.onSpeakingEnd || (() => {});

    this.state = AgentState.IDLE;
    this.isRunning = false;
    this.isSpeaking = false;
    
    this.apiKey = "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";
    this.model = "llama-3.3-70b-versatile";
    
    this.history = [];
    this.maxTurns = 20;

    // Inicializar Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = false;
      this.recognition.lang = 'es-ES';

      this.recognition.onstart = () => {
        if (!this.isSpeaking) {
          this.setState(AgentState.LISTENING);
        }
      };

      this.recognition.onresult = (event) => {
        const current = event.resultIndex;
        const transcript = event.results[current][0].transcript.trim();
        if (transcript) {
          this.handleInput(transcript);
        }
      };

      this.recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
        if (event.error !== 'no-speech') {
          setTimeout(() => {
            if (this.isRunning && !this.isSpeaking) this.recognition.start();
          }, 1000);
        }
      };

      this.recognition.onend = () => {
        // Reiniciar si sigue corriendo y no está hablando
        if (this.isRunning && !this.isSpeaking) {
          try {
            this.recognition.start();
          } catch(e) {}
        }
      };
    } else {
      console.warn("Speech Recognition API no soportada en este navegador.");
    }
  }

  setState(newState) {
    this.state = newState;
    this.onStateChange(this.state);
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.history = [];
    this.setState(AgentState.LISTENING);
    
    const greeting = this.getGreeting();
    this.onBotResponse(greeting);
    this.speak(greeting);
  }

  stop() {
    this.isRunning = false;
    if (this.recognition) this.recognition.stop();
    window.speechSynthesis.cancel();
    this.isSpeaking = false;
    this.setState(AgentState.IDLE);
    this.onSpeakingEnd();
  }

  getGreeting() {
    const h = new Date().getHours();
    const turno = h < 12 ? "días" : (h < 18 ? "tardes" : "noches");
    return `¡Buenas ${turno}! Soy NOVA, el agente de inteligencia artificial del Centro de Prototipado. Bienvenidos a nuestra feria. Estoy aquí para contarles sobre nuestros proyectos, máquinas y servicios. ¿Con quién tengo el gusto?`;
  }

  async handleInput(text) {
    if (!this.isRunning) return;
    
    // Pausar escucha mientras piensa y habla
    if (this.recognition) this.recognition.stop();
    
    this.onUserText(text);
    this.setState(AgentState.THINKING);

    const lower = text.toLowerCase();
    if (lower.includes("apágate") || lower.includes("detente") || lower.includes("adiós")) {
      const resp = "¡Hasta luego! Fue un placer hablar contigo.";
      this.onBotResponse(resp);
      this.speak(resp);
      setTimeout(() => this.stop(), 3000);
      return;
    }

    try {
      const response = await this.reason(text);
      this.onBotResponse(response);
      this.speak(response);
    } catch (e) {
      console.error(e);
      const errResp = "Tuve un problema al procesar tu pregunta. ¿Puedes repetirla?";
      this.onBotResponse(errResp);
      this.speak(errResp);
    }
  }

  async reason(userText) {
    this.history.push({ role: "user", content: userText });
    if (this.history.length > this.maxTurns * 2) {
      this.history = this.history.slice(-this.maxTurns * 2);
    }

    const messages = [
      { role: "system", content: buildSystemPrompt() },
      ...this.history
    ];

    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: this.model,
        messages: messages,
        temperature: 0.7,
        max_tokens: 300
      })
    });

    if (!response.ok) {
      throw new Error("Error en llamada a Groq API");
    }

    const data = await response.json();
    const botText = data.choices[0].message.content.trim();
    this.history.push({ role: "assistant", content: botText });
    return botText;
  }

  speak(text) {
    if (!this.isRunning || !text) return;

    this.isSpeaking = true;
    this.setState(AgentState.SPEAKING);
    this.onSpeakingStart(text);
    
    window.speechSynthesis.cancel(); // Detener audios anteriores

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-MX";
    utterance.rate = 1.0;
    
    // Buscar voz natural si está disponible
    const voices = window.speechSynthesis.getVoices();
    const googleVoice = voices.find(v => v.lang.includes("es-") && v.name.includes("Google"));
    if (googleVoice) {
      utterance.voice = googleVoice;
    }

    utterance.onend = () => {
      this.isSpeaking = false;
      if (this.isRunning) {
        this.setState(AgentState.LISTENING);
        if (this.recognition) {
          try { this.recognition.start(); } catch(e) {}
        }
      }
      this.onSpeakingEnd();
    };

    utterance.onerror = () => {
      this.isSpeaking = false;
      if (this.isRunning) {
        this.setState(AgentState.LISTENING);
        if (this.recognition) {
          try { this.recognition.start(); } catch(e) {}
        }
      }
      this.onSpeakingEnd();
    };

    window.speechSynthesis.speak(utterance);
  }
}
