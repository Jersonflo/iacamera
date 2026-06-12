import { FaceDetector, FilesetResolver } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/vision_bundle.mjs";
import { NovaAgent, AgentState } from "./nova_web_agent.js";

// ═══════════════════════════════════════════════════════════════════
//  IACamera Web 2.0 - Lógica de Control
// ═══════════════════════════════════════════════════════════════════

// Elementos del DOM
const btnConnectSerial = document.getElementById('btnConnectSerial');
const btnStartCamera = document.getElementById('btnStartCamera');
const btnStopCamera = document.getElementById('btnStopCamera');
const btnCenterServos = document.getElementById('btnCenterServos');
const cameraSelect = document.getElementById('cameraSelect');
const deadZoneWidth = document.getElementById('deadZoneWidth');
const deadZoneHeight = document.getElementById('deadZoneHeight');
const valDzW = document.getElementById('valDzW');
const valDzH = document.getElementById('valDzH');
const logBox = document.getElementById('logBox');
const btnClearLog = document.getElementById('btnClearLog');

// Elementos de Video y Canvas
const videoElement = document.getElementById('inputVideo');
const canvasElement = document.getElementById('outputCanvas');
const canvasCtx = canvasElement.getContext('2d');
const videoPlaceholder = document.getElementById('videoPlaceholder');

// Elementos de Nova Agent
const btnToggleNova = document.getElementById('btnToggleNova');
const novaSubtitles = document.getElementById('novaSubtitles');
const lblUserText = document.getElementById('lblUserText');
const lblBotText = document.getElementById('lblBotText');
const statNova = document.getElementById('statNova');

// Elementos de Estado y Badge
const camStatusDot = document.getElementById('camStatusDot');
const systemStatusText = document.getElementById('systemStatusText');
const serialBadge = document.getElementById('serialBadge');
const statusBarText = document.getElementById('statusBarText');

// Métricas / Stats
const statFps = document.getElementById('statFps');
const statFaces = document.getElementById('statFaces');
const statX = document.getElementById('statX');
const statY = document.getElementById('statY');
const statConf = document.getElementById('statConf');
const statRobot = document.getElementById('statRobot');

// Variables de Estado
let port = null;
let writer = null;
let stream = null;
let isCameraRunning = false;
let lastCommandTime = 0;
let lastRobotStateText = "";

// Variable para pausar tracker (servos) cuando habla NOVA
let pauseTracker = false;

// Variables para FPS
let lastFrameTime = performance.now();
let frameCount = 0;

// Variables de control de zona muerta
let dzW = parseInt(deadZoneWidth.value);
let dzH = parseInt(deadZoneHeight.value);

// Actualizar valores de zona muerta en pantalla al cambiar los sliders
deadZoneWidth.addEventListener('input', (e) => {
  dzW = parseInt(e.target.value);
  valDzW.textContent = `${dzW} px`;
});

deadZoneHeight.addEventListener('input', (e) => {
  dzH = parseInt(e.target.value);
  valDzH.textContent = `${dzH} px`;
});

// ═══════════════════════════════════════════════════════════════════
//  INSTANCIA DE NOVA AGENT
// ═══════════════════════════════════════════════════════════════════
const agent = new NovaAgent({
  onStateChange: (state) => {
    statNova.textContent = state;
    if (state === AgentState.LISTENING) {
      log("NOVA: Escuchando...");
    }
  },
  onUserText: (text) => {
    lblUserText.textContent = `Usuario: ${text}`;
    log(`👤 ${text}`);
  },
  onBotResponse: (text) => {
    const display = text.length <= 120 ? text : text.substring(0, 117) + "...";
    lblBotText.textContent = `NOVA: ${display}`;
    log(`🤖 ${text.substring(0, 80)}...`);
  },
  onSpeakingStart: (text) => {
    pauseTracker = true;
    log("🔊 NOVA hablando — tracker pausado");
  },
  onSpeakingEnd: () => {
    pauseTracker = false;
    log("👂 NOVA escuchando — tracker activo");
  }
});

btnToggleNova.addEventListener('click', () => {
  if (agent.isRunning) {
    agent.stop();
    btnToggleNova.textContent = "🎙️ Activar NOVA";
    btnToggleNova.style.backgroundColor = "#8e44ad";
    novaSubtitles.style.display = 'none';
    log("NOVA desactivada.");
  } else {
    agent.start();
    btnToggleNova.textContent = "🔇 Desactivar NOVA";
    btnToggleNova.style.backgroundColor = "var(--btn-stop)";
    novaSubtitles.style.display = 'flex';
    log("NOVA activada.");
  }
});

// ═══════════════════════════════════════════════════════════════════
//  SOPORTE DE NAVEGADOR
// ═══════════════════════════════════════════════════════════
const isSerialSupported = 'serial' in navigator;

if (!isSerialSupported) {
  log("⚠️ Tu navegador no soporta Web Serial API. Usa Google Chrome o Microsoft Edge.", "danger");
  serialBadge.textContent = "⬤ Incompatible con Serial";
  btnConnectSerial.disabled = true;
}

// ═══════════════════════════════════════════════════════════════════
//  LOGGING Y CONSOLA
// ═══════════════════════════════════════════════════════════
function log(msg, type = "") {
  const ts = new Date().toTimeString().split(' ')[0];
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  line.textContent = `[${ts}] ${msg}`;
  
  logBox.appendChild(line);
  logBox.scrollTop = logBox.scrollHeight;
  
  statusBarText.textContent = msg;
}

btnClearLog.addEventListener('click', () => {
  logBox.innerHTML = '';
  log("Log limpiado.");
});

// ═══════════════════════════════════════════════════════════════════
//  WEB SERIAL API
// ═══════════════════════════════════════════════════════════
btnConnectSerial.addEventListener('click', async () => {
  if (port) {
    // Desconectar
    await disconnectSerial();
    return;
  }

  try {
    log("Solicitando puerto serial...");
    port = await navigator.serial.requestPort();
    await port.open({ baudRate: 9600 });
    writer = port.writable.getWriter();
    
    log("Puerto serial conectado con éxito.", "success");
    serialBadge.textContent = "⬤ Conectado a Serial";
    serialBadge.className = "serial-badge success";
    btnConnectSerial.textContent = "🔌 Desconectar Serial";
    btnConnectSerial.className = "btn btn-stop";
    
    // Habilitar controles
    btnStartCamera.disabled = false;
    btnCenterServos.disabled = false;
    
    // Mandar comando inicial de centrado
    await sendSerialCommand('p');
  } catch (err) {
    log(`Error de conexión serial: ${err.message}`, "danger");
    port = null;
    writer = null;
  }
});

async function disconnectSerial() {
  log("Cerrando puerto serial...");
  if (isCameraRunning) {
    await stopCamera();
  }
  
  if (writer) {
    try {
      await sendSerialCommand('p'); // Centrar antes de desconectar
      writer.releaseLock();
    } catch (e) {}
    writer = null;
  }
  
  if (port) {
    try {
      await port.close();
    } catch (e) {}
    port = null;
  }
  
  log("Puerto serial desconectado.");
  serialBadge.textContent = "⬤ Sin conexión serial";
  serialBadge.className = "serial-badge danger";
  btnConnectSerial.textContent = "🔌 Conectar Serial";
  btnConnectSerial.className = "btn btn-connect";
  
  btnStartCamera.disabled = true;
  btnStopCamera.disabled = true;
  btnCenterServos.disabled = true;
  resetStats();
}

async function sendSerialCommand(char) {
  if (writer) {
    const now = Date.now();
    // Limitar velocidad de comandos para no saturar el buffer (mínimo 50ms)
    if (now - lastCommandTime >= 50 || char === 'p') {
      try {
        const data = new TextEncoder().encode(char);
        await writer.write(data);
        lastCommandTime = now;
      } catch (err) {
        log(`Error enviando datos: ${err.message}`, "danger");
      }
    }
  }
}

btnCenterServos.addEventListener('click', async () => {
  await sendSerialCommand('p');
  log("Comando enviado: Centrar Servos ('p')");
});

// ═══════════════════════════════════════════════════════════════════
//  LISTADO DE CÁMARAS
// ═══════════════════════════════════════════════════════════
async function getCameras() {
  try {
    // Solicitar permiso inicial de cámara para poder listar nombres correctos
    const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
    tempStream.getTracks().forEach(track => track.stop());

    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');
    
    cameraSelect.innerHTML = '';
    
    if (videoDevices.length === 0) {
      const opt = document.createElement('option');
      opt.textContent = "No se encontraron cámaras";
      opt.value = "";
      cameraSelect.appendChild(opt);
      return;
    }

    videoDevices.forEach((device, index) => {
      const opt = document.createElement('option');
      opt.value = device.deviceId;
      // Poner nombres legibles, buscando identificar la del robot
      opt.textContent = device.label || `Cámara ${index + 1}`;
      cameraSelect.appendChild(opt);
    });

    log(`${videoDevices.length} cámara(s) detectada(s).`);
  } catch (err) {
    log(`Error listando cámaras: ${err.message}`, "danger");
  }
}

let faceDetector;

async function initFaceDetector() {
  log("Cargando modelo FaceDetector...");
  try {
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm"
    );
    faceDetector = await FaceDetector.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
        delegate: "GPU"
      },
      runningMode: "VIDEO",
      minDetectionConfidence: 0.5
    });
    log("Modelo FaceDetector cargado exitosamente.", "success");
  } catch (err) {
    log(`Error cargando modelo: ${err.message}`, "danger");
  }
}

// Escanear cámaras al cargar la página
window.addEventListener('DOMContentLoaded', async () => {
  await getCameras();
  await initFaceDetector();
});

btnStartCamera.addEventListener('click', startCamera);
btnStopCamera.addEventListener('click', stopCamera);

async function startCamera() {
  const deviceId = cameraSelect.value;
  
  const constraints = {
    video: deviceId ? { deviceId: { exact: deviceId }, width: 640, height: 480 } : { width: 640, height: 480 }
  };

  try {
    log("Iniciando transmisión de video...");
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    videoElement.srcObject = stream;
    
    // Esperar a que el video esté listo para reproducir
    videoElement.onloadedmetadata = () => {
      videoElement.play();
      canvasElement.width = videoElement.videoWidth;
      canvasElement.height = videoElement.videoHeight;
      isCameraRunning = true;
      videoPlaceholder.style.display = 'none';
      
      btnStartCamera.disabled = true;
      btnStopCamera.disabled = false;
      cameraSelect.disabled = true;
      
      camStatusDot.className = "status-dot active";
      systemStatusText.textContent = "— En vivo (Tracking activo)";
      systemStatusText.style.color = "var(--accent-success)";
      
      log("Cámara iniciada. Procesando detección facial...");
      
      // Loop del cuadro
      tick();
    };
  } catch (err) {
    log(`Error al abrir la cámara: ${err.message}`, "danger");
  }
}

async function stopCamera() {
  log("Deteniendo cámara...");
  isCameraRunning = false;
  
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }
  
  videoElement.srcObject = null;
  videoPlaceholder.style.display = 'flex';
  
  btnStartCamera.disabled = false;
  btnStopCamera.disabled = true;
  cameraSelect.disabled = false;
  
  camStatusDot.className = "status-dot";
  systemStatusText.textContent = "— Sistema detenido";
  systemStatusText.style.color = "var(--text-dim)";
  
  // Limpiar Canvas
  canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
  
  // Detener servos
  await sendSerialCommand('p');
  
  resetStats();
}

async function tick() {
  if (!isCameraRunning) return;
  
  if (videoElement.readyState >= 2 && faceDetector) {
    try {
      let startTimeMs = performance.now();
      const results = faceDetector.detectForVideo(videoElement, startTimeMs);
      onResults(results);
    } catch (err) {
      console.error("Error en faceDetector.detectForVideo:", err);
    }
  }
  
  requestAnimationFrame(tick);
}

// ═══════════════════════════════════════════════════════════════════
//  PROCESAMIENTO DE RESULTADOS Y HUD
// ═══════════════════════════════════════════════════════════
function onResults(results) {
  // Dibujar el cuadro en el canvas
  canvasCtx.save();
  canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
  canvasCtx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
  
  const w = canvasElement.width;
  const h = canvasElement.height;
  const frame_cx = w / 2;
  const frame_cy = h / 2;

  // Calcular FPS
  frameCount++;
  const now = performance.now();
  if (now - lastFrameTime >= 1000) {
    const fps = (frameCount * 1000) / (now - lastFrameTime);
    statFps.textContent = `${fps.toFixed(1)} fps`;
    frameCount = 0;
    lastFrameTime = now;
  }

  statFaces.textContent = results.detections ? results.detections.length : 0;

  if (results.detections && results.detections.length > 0) {
    // Seleccionar el rostro más grande (mayor área del bounding box)
    let maxArea = 0;
    let idx = 0;
    
    results.detections.forEach((det, i) => {
      const area = det.boundingBox.width * det.boundingBox.height;
      if (area > maxArea) {
        maxArea = area;
        idx = i;
      }
    });

    const face = results.detections[idx];
    const bbox = face.boundingBox;
    
    // En tasks-vision, el bounding box viene en píxeles
    const face_x = bbox.originX;
    const face_y = bbox.originY;
    const face_w = bbox.width;
    const face_h = bbox.height;
    const cx = face_x + face_w / 2;
    const cy = face_y + face_h / 2;

    // Calcular porcentajes
    const posXPct = (cx / w) * 100;
    const posYPct = (cy / h) * 100;
    
    const confidence = face.categories && face.categories.length > 0 ? face.categories[0].score : 0;
    
    statX.textContent = `${posXPct.toFixed(1)}%`;
    statY.textContent = `${posYPct.toFixed(1)}%`;
    statConf.textContent = `${(confidence * 100).toFixed(1)}%`;

    // Dibujar HUD del rostro (verde neón)
    drawHudRect(canvasCtx, face_x, face_y, face_w, face_h, '#00ff88', 20, 2);

    // Dibujar mira central sobre el rostro
    canvasCtx.strokeStyle = '#00d4ff';
    canvasCtx.lineWidth = 1;
    // Línea vertical
    canvasCtx.beginPath();
    canvasCtx.moveTo(cx, 0);
    canvasCtx.lineTo(cx, h);
    canvasCtx.stroke();
    // Línea horizontal
    canvasCtx.beginPath();
    canvasCtx.moveTo(0, cy);
    canvasCtx.lineTo(w, cy);
    canvasCtx.stroke();
    // Círculos concéntricos
    canvasCtx.fillStyle = '#00d4ff';
    canvasCtx.beginPath();
    canvasCtx.arc(cx, cy, 5, 0, 2 * Math.PI);
    canvasCtx.fill();
    canvasCtx.beginPath();
    canvasCtx.arc(cx, cy, 12, 0, 2 * Math.PI);
    canvasCtx.stroke();

    // Texto de confianza
    canvasCtx.fillStyle = '#00ff88';
    canvasCtx.font = '13px Share Tech Mono, monospace';
    canvasCtx.fillText(`CONF: ${(confidence * 100).toFixed(1)}%`, face_x, face_y - 8);

    // Zona muerta dinámica
    const dz_w = Math.min(dzW, face_w * 2);
    const dz_h = Math.min(dzH, face_h * 2);
    const tl_x = frame_cx - dz_w / 2;
    const tl_y = frame_cy - dz_h / 2;
    
    // Dibujar Zona Muerta en el canvas (naranja/azul)
    drawHudRect(canvasCtx, tl_x, tl_y, dz_w, dz_h, '#008cff', 15, 1);

    // CONTROL DEL ROBOT (Simulación de tracker.py)
    // Espejamos el eje horizontal para la lógica, ya que la canvas está espejada con CSS
    // diff_x positivo significa que la cara está a la derecha en la imagen de la cámara (izquierda física de la pantalla)
    const diff_x = frame_cx - cx;
    const diff_y = cy - frame_cy; // Y no se altera por espejo

    let cmd_label = "";

    if (!pauseTracker) {
      // Eje Horizontal
      if (Math.abs(diff_x) > dz_w / 2) {
        if (diff_x < 0) {
          cmd_label = "← Izquierda";
          sendSerialCommand('i');
        } else {
          cmd_label = "→ Derecha";
          sendSerialCommand('d');
        }
      }

      // Eje Vertical
      if (Math.abs(diff_y) > dz_h / 2) {
        if (diff_y < 0) {
          const suffix = "↑ Arriba";
          sendSerialCommand('b');
          cmd_label = cmd_label ? `${cmd_label} ${suffix}` : suffix;
        } else {
          const suffix = "↓ Abajo";
          sendSerialCommand('a');
          cmd_label = cmd_label ? `${cmd_label} ${suffix}` : suffix;
        }
      }
    } else {
      cmd_label = "Pausado (Hablando)";
    }

    const robotState = cmd_label || "Centrado";
    statRobot.textContent = robotState;
    
    if (robotState !== lastRobotStateText && robotState !== "Centrado") {
      log(`Robot: ${robotState}`);
    }
    lastRobotStateText = robotState;

  } else {
    // No se detecta rostro
    statX.textContent = "—";
    statY.textContent = "—";
    statConf.textContent = "—";
    statRobot.textContent = "Buscando...";
    lastRobotStateText = "Buscando...";

    // Dibujar Zona Muerta por defecto
    const tl_x = frame_cx - dzW / 2;
    const tl_y = frame_cy - dzH / 2;
    drawHudRect(canvasCtx, tl_x, tl_y, '#ff8c00', 15, 1);
  }

  canvasCtx.restore();
}

// Función auxiliar para dibujar rectángulos estilo HUD (solo esquinas)
function drawHudRect(ctx, x, y, w, h, color, length = 15, thickness = 2) {
  ctx.strokeStyle = color;
  ctx.lineWidth = thickness;
  
  // Esquina Superior Izquierda
  ctx.beginPath();
  ctx.moveTo(x, y + length);
  ctx.lineTo(x, y);
  ctx.lineTo(x + length, y);
  ctx.stroke();
  
  // Esquina Superior Derecha
  ctx.beginPath();
  ctx.moveTo(x + w - length, y);
  ctx.lineTo(x + w, y);
  ctx.lineTo(x + w, y + length);
  ctx.stroke();
  
  // Esquina Inferior Izquierda
  ctx.beginPath();
  ctx.moveTo(x, y + h - length);
  ctx.lineTo(x, y + h);
  ctx.lineTo(x + length, y + h);
  ctx.stroke();
  
  // Esquina Inferior Derecha
  ctx.beginPath();
  ctx.moveTo(x + w - length, y + h);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x + w, y + h - length);
  ctx.stroke();
}

function resetStats() {
  statFps.textContent = "—";
  statFaces.textContent = "0";
  statX.textContent = "—";
  statY.textContent = "—";
  statConf.textContent = "—";
  statRobot.textContent = "Esperando";
}
