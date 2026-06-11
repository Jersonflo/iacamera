import customtkinter as ctk
from PIL import Image
import cv2
import os
import threading
import queue
from datetime import datetime

# ── CAMBIO 1: importar NovaAgent en lugar de VoiceAssistant ──
from nova_agent import NovaAgent, AgentEvent, EventType, AgentState


# ═══════════════════════════════════════════════════════════════════
#  Paleta de colores (tema "tech" cian/neón)
# ═══════════════════════════════════════════════════════════════════
COLORS = {
    "bg":          "#0d1117",
    "surface":     "#161b22",
    "surface2":    "#1c2128",
    "accent":      "#00d4ff",
    "accent2":     "#00ff88",
    "danger":      "#ff4757",
    "warn":        "#ffa502",
    "text":        "#e6edf3",
    "text_dim":    "#8b949e",
    "btn_start":   "#00c853",
    "btn_start_h": "#00a844",
    "btn_stop":    "#ff4757",
    "btn_stop_h":  "#e63950",
    "btn_gray":    "#30363d",
    "btn_gray_h":  "#3d444d",
}

MAX_LOG_LINES = 60


class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["bg"])

        self.title("IACamera 2.0")
        self.geometry("1200x720")
        self.minsize(900, 580)

        # ── Estado ────────────────────────────────────────────
        self.tracker = None
        self.is_running = False
        self._log_lines = []
        self._last_robot_state = ""

        # ── CAMBIO 2: cola de eventos compartida ──────────────
        # La cola conecta NovaAgent ↔ UI ↔ FaceTracker
        self._agent_event_queue: queue.Queue[AgentEvent] = queue.Queue()

        # ── CAMBIO 3: instanciar NovaAgent con callbacks ──────
        # Los callbacks son exactamente iguales a los del VoiceAssistant anterior:
        # on_state_change, on_user_text, on_bot_response — mismo nombre, misma firma.
        self.assistant = NovaAgent(
            event_queue     = self._agent_event_queue,
            on_state_change = self._on_assistant_state,   # fn(AgentState)
            on_user_text    = self._on_assistant_user_text,  # fn(str)
            on_bot_response = self._on_assistant_bot_response,  # fn(str)
        )

        self._build_ui()
        self._log("Sistema iniciado. Listo.")
        self.after(400, self._escanear_camaras)

        # ── CAMBIO 4: leer eventos del agente cada 100ms ──────
        # Coordina el FaceTracker cuando NOVA empieza/termina de hablar
        self._poll_agent_events()

    # ═══════════════════════════════════════════════════════════
    #  NUEVO: consumidor de eventos del agente
    # ═══════════════════════════════════════════════════════════
    def _poll_agent_events(self):
        """
        Lee la cola de eventos del NovaAgent y reacciona.
        Corre en el hilo principal de Tkinter cada 100ms (after).
        
        Eventos clave:
          SPEAKING_START → pausar FaceTracker (servos quietos mientras habla)
          SPEAKING_END   → reanudar FaceTracker
        """
        try:
            while True:  # vaciar todos los eventos acumulados
                event: AgentEvent = self._agent_event_queue.get_nowait()
                self._handle_agent_event(event)
        except queue.Empty:
            pass  # normal, no hay eventos nuevos

        # Reprogramar la próxima revisión
        self.after(100, self._poll_agent_events)

    def _handle_agent_event(self, event: AgentEvent):
        """Reacciona a eventos publicados por NovaAgent."""
        if event.type == EventType.SPEAKING_START:
            # NOVA va a hablar → pausar servos para evitar ruido / eco del mic
            if self.tracker:
                self._pause_tracker()
            self._log("🔊 NOVA hablando — tracker pausado")

        elif event.type == EventType.SPEAKING_END:
            # NOVA terminó → reanudar seguimiento facial
            if self.tracker:
                self._resume_tracker()
            self._log("👂 NOVA escuchando — tracker activo")

        elif event.type == EventType.STATE_CHANGED:
            # Actualizar barra de estado con el estado del agente
            pass  # ya lo hace on_state_change callback

        elif event.type == EventType.SHUTDOWN:
            self._log("Agente NOVA apagado.")

    def _pause_tracker(self):
        """
        Pausa el seguimiento facial mientras NOVA habla.
        El FaceTracker actual no tiene pause(), así que usamos
        una bandera interna para saltar el envío de comandos serial.
        """
        if self.tracker:
            self.tracker.robot_mode = False
            self._log("Tracker: comandos serial suspendidos.")

    def _resume_tracker(self):
        """Reanuda el envío de comandos al robot."""
        if self.tracker and self._robot_var.get() == "Con Robot":
            self.tracker.robot_mode = True
            self._log("Tracker: comandos serial reanudados.")

    # ═══════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN DE LA UI  (sin cambios respecto al original)
    # ═══════════════════════════════════════════════════════════
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_content()
        self._build_statusbar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=60, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        self._dot_cam = ctk.CTkLabel(hdr, text="⬤", font=("Roboto", 14),
                                      text_color=COLORS["text_dim"], width=20)
        self._dot_cam.grid(row=0, column=0, padx=(18, 4), pady=18)

        ctk.CTkLabel(
            hdr, text="IACamera  2.0",
            font=("Roboto", 22, "bold"),
            text_color=COLORS["accent"]
        ).grid(row=0, column=1, sticky="w", padx=4)

        self._lbl_estado_hdr = ctk.CTkLabel(
            hdr, text="— Sistema detenido",
            font=("Roboto", 13),
            text_color=COLORS["text_dim"]
        )
        self._lbl_estado_hdr.grid(row=0, column=2, sticky="w", padx=12)

        self._badge_serial = ctk.CTkLabel(
            hdr,
            text="⬤  Sin conexión serial",
            font=("Roboto", 12),
            text_color=COLORS["danger"]
        )
        self._badge_serial.grid(row=0, column=3, padx=20, pady=18, sticky="e")

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=0)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=0)

        self._build_video_area(content)
        self._build_subtitle_area(content)
        self._build_side_panel(content)

    def _build_video_area(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"],
                             corner_radius=14, border_width=1,
                             border_color=COLORS["surface2"])
        frame.grid(row=0, column=0, padx=(16, 8), pady=(16, 8), sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.label_video = ctk.CTkLabel(
            frame,
            text="🎥  Cámara apagada",
            font=("Roboto", 22),
            text_color=COLORS["text_dim"]
        )
        self.label_video.grid(row=0, column=0, sticky="nsew")
        self._frame_camara = frame

    def _build_subtitle_area(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], height=100, corner_radius=14)
        frame.grid(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="ew")
        frame.grid_propagate(False)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self.lbl_user_text = ctk.CTkLabel(
            frame, text="Usuario: ...",
            font=("Roboto", 14), text_color=COLORS["text_dim"], anchor="w"
        )
        self.lbl_user_text.grid(row=0, column=0, padx=16, pady=(10, 0), sticky="w")

        self.lbl_bot_text = ctk.CTkLabel(
            frame, text="Robot: ...",
            font=("Roboto", 16, "bold"), text_color=COLORS["accent"], anchor="w"
        )
        self.lbl_bot_text.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

    def _build_side_panel(self, parent):
        panel = ctk.CTkScrollableFrame(
            parent, fg_color=COLORS["surface"],
            corner_radius=14, width=280
        )
        panel.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)

        row = 0

        row = self._section(panel, "⚡  Controles", row)

        self.btn_iniciar = self._big_button(
            panel, "▶  Iniciar", COLORS["btn_start"], COLORS["btn_start_h"],
            self.iniciar_camara, row
        )
        row += 1

        self.btn_detener = self._big_button(
            panel, "⏹  Detener", COLORS["btn_stop"], COLORS["btn_stop_h"],
            self.detener_camara, row, state="disabled"
        )
        row += 1

        self.btn_captura = self._big_button(
            panel, "📸  Capturar foto", COLORS["btn_gray"], COLORS["btn_gray_h"],
            self.capturar_foto, row, state="disabled"
        )
        row += 1

        self.btn_voz = self._big_button(
            panel, "🎙️  Activar NOVA", "#8e44ad", "#9b59b6",
            self.toggle_voz, row
        )
        row += 1

        self.btn_cerrar = self._big_button(
            panel, "✕  Cerrar app", COLORS["btn_gray"], COLORS["btn_gray_h"],
            self.cerrar_app, row
        )
        row += 1

        row = self._section(panel, "⚙  Configuración", row)

        ctk.CTkLabel(panel, text="Modo Robot", font=("Roboto", 13),
                      text_color=COLORS["text_dim"]).grid(
            row=row, column=0, sticky="w", padx=16, pady=(4, 0))
        row += 1

        self._robot_var = ctk.StringVar(value="Con Robot")
        self._toggle_robot = ctk.CTkSegmentedButton(
            panel,
            values=["Con Robot", "Solo Visión"],
            variable=self._robot_var,
            font=("Roboto", 12),
            fg_color=COLORS["surface2"],
            selected_color=COLORS["accent"],
            selected_hover_color="#00aacf",
            command=self._on_toggle_robot
        )
        self._toggle_robot.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        row += 1

        cam_header = ctk.CTkFrame(panel, fg_color="transparent")
        cam_header.grid(row=row, column=0, sticky="ew", padx=16, pady=(4, 0))
        cam_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cam_header, text="Cámara disponible", font=("Roboto", 13),
                      text_color=COLORS["text_dim"]).grid(row=0, column=0, sticky="w")
        self._btn_scan = ctk.CTkButton(
            cam_header, text="🔍", width=32, height=24,
            font=("Roboto", 13),
            fg_color=COLORS["surface2"], hover_color=COLORS["btn_gray"],
            command=self._escanear_camaras
        )
        self._btn_scan.grid(row=0, column=1, sticky="e")
        row += 1

        self._cam_var = ctk.StringVar(value="")
        self._cam_menu = ctk.CTkSegmentedButton(
            panel,
            values=["Buscando..."],
            variable=self._cam_var,
            font=("Roboto", 13, "bold"),
            fg_color=COLORS["surface2"],
            selected_color=COLORS["accent"],
            selected_hover_color="#00aacf",
            unselected_color=COLORS["surface2"],
            unselected_hover_color=COLORS["btn_gray"],
            state="disabled",
            command=self._on_cam_change
        )
        self._cam_menu.grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        row += 1

        ctk.CTkLabel(panel, text="Zona muerta — Ancho", font=("Roboto", 13),
                      text_color=COLORS["text_dim"]).grid(
            row=row, column=0, sticky="w", padx=16, pady=(4, 0))
        row += 1

        self._dz_w_var = ctk.IntVar(value=300)
        self._lbl_dz_w = ctk.CTkLabel(panel, text="300 px", font=("Roboto", 12),
                                        text_color=COLORS["accent"])
        self._lbl_dz_w.grid(row=row, column=0, sticky="e", padx=16)
        row += 1

        ctk.CTkSlider(
            panel, from_=50, to=600, number_of_steps=55,
            variable=self._dz_w_var,
            button_color=COLORS["accent"],
            button_hover_color="#00aacf",
            progress_color=COLORS["accent"],
            command=self._on_dz_w_change
        ).grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        row += 1

        ctk.CTkLabel(panel, text="Zona muerta — Alto", font=("Roboto", 13),
                      text_color=COLORS["text_dim"]).grid(
            row=row, column=0, sticky="w", padx=16, pady=(4, 0))
        row += 1

        self._dz_h_var = ctk.IntVar(value=300)
        self._lbl_dz_h = ctk.CTkLabel(panel, text="300 px", font=("Roboto", 12),
                                        text_color=COLORS["accent"])
        self._lbl_dz_h.grid(row=row, column=0, sticky="e", padx=16)
        row += 1

        ctk.CTkSlider(
            panel, from_=50, to=600, number_of_steps=55,
            variable=self._dz_h_var,
            button_color=COLORS["accent"],
            button_hover_color="#00aacf",
            progress_color=COLORS["accent"],
            command=self._on_dz_h_change
        ).grid(row=row, column=0, padx=16, pady=(0, 8), sticky="ew")
        row += 1

        row = self._section(panel, "📊  Estadísticas", row)

        stats_labels = [
            ("FPS", "_stat_fps"),
            ("Rostros detectados", "_stat_faces"),
            ("Posición X", "_stat_x"),
            ("Posición Y", "_stat_y"),
            ("Confianza", "_stat_conf"),
            ("Estado robot", "_stat_robot"),
            # ── NUEVO: estado del agente NOVA ─────────────────
            ("NOVA estado", "_stat_nova"),
        ]
        for label_text, attr in stats_labels:
            row = self._stat_row(panel, label_text, attr, row)

        row = self._section(panel, "📋  Log de comandos", row)

        self._log_box = ctk.CTkTextbox(
            panel, height=160,
            font=("Courier New", 11),
            fg_color=COLORS["surface2"],
            text_color=COLORS["text_dim"],
            border_color=COLORS["btn_gray"],
            border_width=1,
            corner_radius=8,
            state="disabled"
        )
        self._log_box.grid(row=row, column=0, padx=16, pady=(0, 12), sticky="ew")
        row += 1

        ctk.CTkButton(
            panel, text="Limpiar log",
            font=("Roboto", 12),
            height=30,
            fg_color=COLORS["surface2"],
            hover_color=COLORS["btn_gray"],
            command=self._clear_log
        ).grid(row=row, column=0, padx=16, pady=(0, 16), sticky="ew")
        row += 1

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=28, corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        self._lbl_status = ctk.CTkLabel(
            bar, text="Listo",
            font=("Roboto", 11),
            text_color=COLORS["text_dim"],
            anchor="w"
        )
        self._lbl_status.grid(row=0, column=0, padx=12, pady=4, sticky="w")

    # ═══════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════
    def _section(self, parent, title: str, row: int) -> int:
        ctk.CTkFrame(parent, fg_color=COLORS["surface2"],
                     height=1, corner_radius=0).grid(
            row=row, column=0, sticky="ew", padx=8, pady=(14, 2))
        row += 1
        ctk.CTkLabel(parent, text=title, font=("Roboto", 13, "bold"),
                      text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", padx=16, pady=(2, 4))
        return row + 1

    def _big_button(self, parent, text, fg, hover, cmd, row, state="normal"):
        btn = ctk.CTkButton(
            parent, text=text,
            font=("Roboto", 14, "bold"),
            height=44,
            fg_color=fg,
            hover_color=hover,
            corner_radius=10,
            state=state,
            command=cmd
        )
        btn.grid(row=row, column=0, padx=16, pady=4, sticky="ew")
        return btn

    def _stat_row(self, parent, label: str, attr: str, row: int) -> int:
        ctk.CTkLabel(parent, text=label, font=("Roboto", 12),
                      text_color=COLORS["text_dim"]).grid(
            row=row, column=0, sticky="w", padx=16, pady=(2, 0))
        row += 1
        lbl = ctk.CTkLabel(parent, text="—", font=("Roboto", 13, "bold"),
                             text_color=COLORS["text"])
        lbl.grid(row=row, column=0, sticky="w", padx=24, pady=(0, 4))
        setattr(self, attr, lbl)
        return row + 1

    # ═══════════════════════════════════════════════════════════
    #  ACCIONES
    # ═══════════════════════════════════════════════════════════
    def iniciar_camara(self):
        if not self.is_running:
            from tracker import FaceTracker
            robot_mode = (self._robot_var.get() == "Con Robot")
            cam_val = self._cam_var.get()
            if not cam_val.isdigit():
                self._log("⚠ Error: Selección de cámara no válida o buscando...")
                self._lbl_status.configure(text="Selección de cámara no válida.")
                return
            cam_idx = int(cam_val)
            self.tracker = FaceTracker(
                camera_index=cam_idx,
                robot_mode=robot_mode,
                dead_zone_width=self._dz_w_var.get(),
                dead_zone_height=self._dz_h_var.get()
            )
            self.is_running = True

            self.btn_iniciar.configure(state="disabled")
            self.btn_detener.configure(state="normal")
            self.btn_captura.configure(state="normal")
            self.label_video.configure(text="")

            self._dot_cam.configure(text_color=COLORS["accent2"])
            self._lbl_estado_hdr.configure(
                text=f"— En vivo · Cámara {cam_idx}",
                text_color=COLORS["accent2"]
            )
            self._update_serial_badge()
            self._log(f"Cámara {cam_idx} iniciada. Modo: {'Con Robot' if robot_mode else 'Solo Visión'}")
            self._actualizar_frame()

    def detener_camara(self):
        self.is_running = False
        if self.tracker:
            self.tracker._enviar_comando(b'p')
            self.tracker.limpiar()
            self.tracker = None

        self.label_video.configure(image=None, text="🎥  Cámara apagada")
        self.btn_iniciar.configure(state="normal")
        self.btn_detener.configure(state="disabled")
        self.btn_captura.configure(state="disabled")

        self._dot_cam.configure(text_color=COLORS["text_dim"])
        self._lbl_estado_hdr.configure(text="— Sistema detenido", text_color=COLORS["text_dim"])
        self._badge_serial.configure(text="⬤  Sin conexión serial", text_color=COLORS["danger"])
        self._reset_stats()
        self._log("Cámara detenida.")

    def capturar_foto(self):
        if not self.is_running or not self.tracker:
            return
        frame = self.tracker.capturar_y_procesar()
        if frame is not None:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            folder = os.path.expanduser("~/Desktop/IACamera_Capturas")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"captura_{ts}.png")
            cv2.imwrite(path, frame)
            self._log(f"📸 Foto guardada: captura_{ts}.png")
            self._lbl_status.configure(text="Foto guardada en ~/Desktop/IACamera_Capturas/")

    def toggle_voz(self):
        # ── CAMBIO 5: is_running ahora es threading.Event en NovaAgent ──
        # Usamos el método is_running() del agente
        if self.assistant.is_running():
            self.assistant.stop()
            self.btn_voz.configure(
                text="🎙️  Activar NOVA",
                fg_color="#8e44ad",
                hover_color="#9b59b6"
            )
            self._log("NOVA desactivada.")
        else:
            self.assistant.start()
            self.btn_voz.configure(
                text="🔇  Desactivar NOVA",
                fg_color=COLORS["btn_stop"],
                hover_color=COLORS["btn_stop_h"]
            )
            self._log("NOVA activada — calibrando micrófono...")

    def cerrar_app(self):
        self.detener_camara()
        if self.assistant.is_running():
            self.assistant.stop()
        self.destroy()

    # ═══════════════════════════════════════════════════════════
    #  CALLBACKS DE VOZ (NovaAgent → UI)
    #  Misma firma que antes, solo cambia el tipo del primer arg
    # ═══════════════════════════════════════════════════════════
    def _on_assistant_state(self, state: AgentState):
        """
        Antes recibía un str. Ahora recibe AgentState (Enum).
        Convertimos a string para mostrar igual que antes.
        """
        state_str = state.name.capitalize().replace("_", " ")
        self.after(0, lambda: self._lbl_status.configure(text=f"NOVA: {state_str}"))
        self.after(0, lambda: self._stat_nova.configure(text=state_str))

    def _on_assistant_user_text(self, text: str):
        self.after(0, lambda: self.lbl_user_text.configure(text=f"Usuario: {text}"))
        self.after(0, lambda: self._log(f"👤 {text}"))

    def _on_assistant_bot_response(self, text: str):
        # Truncar en pantalla si es muy largo
        display = text if len(text) <= 120 else text[:117] + "..."
        self.after(0, lambda: self.lbl_bot_text.configure(text=f"NOVA: {display}"))
        self.after(0, lambda: self._log(f"🤖 {text[:80]}..."))

    # ═══════════════════════════════════════════════════════════
    #  CALLBACKS DE CONFIGURACIÓN (sin cambios)
    # ═══════════════════════════════════════════════════════════
    def _on_toggle_robot(self, value):
        if self.tracker:
            self.tracker.set_robot_mode(value == "Con Robot")
            self._update_serial_badge()
        self._log(f"Modo cambiado a: {value}")

    def _on_cam_change(self, value):
        if not (self.is_running and self.tracker):
            return
        if not value.isdigit():
            return

        self._cam_menu.configure(state="disabled")
        self._btn_scan.configure(state="disabled")
        self._lbl_status.configure(text=f"Cambiando a cámara {value}…")

        def _cambiar():
            self.tracker.cambiar_camara(int(value))
            self.after(0, lambda: self._cam_menu.configure(state="normal"))
            self.after(0, lambda: self._btn_scan.configure(state="normal"))
            self.after(0, lambda: self._log(f"Cámara cambiada a índice {value}"))

        threading.Thread(target=_cambiar, daemon=True).start()

    def _escanear_camaras(self):
        self._cam_menu.configure(state="disabled", values=["Buscando..."])
        self._cam_var.set("Buscando...")
        self._btn_scan.configure(state="disabled")
        self._lbl_status.configure(text="Buscando cámaras disponibles…")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        disponibles = []
        for idx in range(6):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                disponibles.append(str(idx))
                cap.release()
        self.after(0, lambda: self._aplicar_camaras(disponibles))

    def _aplicar_camaras(self, disponibles: list[str]):
        if not disponibles:
            self._cam_menu.configure(values=["N/A"], state="disabled")
            self._cam_var.set("N/A")
            self._log("⚠ No se encontraron cámaras.")
        else:
            default = "1" if "1" in disponibles else disponibles[0]
            self._cam_menu.configure(values=disponibles, state="normal")
            self._cam_var.set(default)
            self._log(f"Cámaras: {', '.join(disponibles)} → seleccionada {default}")
        self._btn_scan.configure(state="normal")
        self._lbl_status.configure(text=f"{len(disponibles)} cámara(s) detectada(s).")

    def _on_dz_w_change(self, value):
        v = int(value)
        self._lbl_dz_w.configure(text=f"{v} px")
        if self.tracker:
            self.tracker.dead_zone_width = v

    def _on_dz_h_change(self, value):
        v = int(value)
        self._lbl_dz_h.configure(text=f"{v} px")
        if self.tracker:
            self.tracker.dead_zone_height = v

    # ═══════════════════════════════════════════════════════════
    #  BUCLE DE VÍDEO (sin cambios)
    # ═══════════════════════════════════════════════════════════
    def _actualizar_frame(self):
        if not self.is_running or not self.tracker:
            return

        frame = self.tracker.capturar_y_procesar()
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            w = max(self._frame_camara.winfo_width() - 20, 10)
            h = max(self._frame_camara.winfo_height() - 20, 10)

            if w > 10 and h > 10:
                ctk_img = ctk.CTkImage(
                    light_image=pil_image, dark_image=pil_image, size=(w, h)
                )
                self.label_video.configure(image=ctk_img)
                self.label_video.image = ctk_img

        self._update_stats()
        self.after(15, self._actualizar_frame)

    # ═══════════════════════════════════════════════════════════
    #  ESTADÍSTICAS (sin cambios)
    # ═══════════════════════════════════════════════════════════
    def _update_stats(self):
        if not self.tracker:
            return
        fd = self.tracker.face_data

        self._stat_fps.configure(text=f"{self.tracker.fps:.1f} fps")
        self._stat_faces.configure(text=str(fd["num_faces"]))

        if fd["detected"]:
            self._stat_x.configure(text=f"{fd['pos_x_pct']:.1f}%")
            self._stat_y.configure(text=f"{fd['pos_y_pct']:.1f}%")
            self._stat_conf.configure(text=f"{fd['confidence']*100:.1f}%")
        else:
            self._stat_x.configure(text="—")
            self._stat_y.configure(text="—")
            self._stat_conf.configure(text="—")

        robot_state = fd["robot_state"]
        self._stat_robot.configure(text=robot_state)

        if robot_state != self._last_robot_state and robot_state not in ("Centrado", "Buscando...", "Esperando"):
            self._log(f"Robot: {robot_state}")
        self._last_robot_state = robot_state

    def _reset_stats(self):
        for attr in ("_stat_fps", "_stat_faces", "_stat_x", "_stat_y",
                     "_stat_conf", "_stat_robot", "_stat_nova"):
            getattr(self, attr).configure(text="—")

    def _update_serial_badge(self):
        if self.tracker and self.tracker.serial_connected:
            self._badge_serial.configure(
                text=f"⬤  Serial: {self.tracker.serial_port}",
                text_color=COLORS["accent2"]
            )
        elif self._robot_var.get() == "Con Robot":
            self._badge_serial.configure(
                text="⬤  Sin conexión serial", text_color=COLORS["danger"]
            )
        else:
            self._badge_serial.configure(
                text="⬤  Modo Solo Visión", text_color=COLORS["accent"]
            )

    # ═══════════════════════════════════════════════════════════
    #  LOG (sin cambios)
    # ═══════════════════════════════════════════════════════════
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        if len(self._log_lines) > MAX_LOG_LINES:
            self._log_lines.pop(0)

        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.insert("end", "\n".join(self._log_lines))
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

        self._lbl_status.configure(text=line)

    def _clear_log(self):
        self._log_lines.clear()
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._lbl_status.configure(text="Log limpiado.")
