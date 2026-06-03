import webbrowser
import os
import time
import keyboard

# =========================================================
# --- LÓGICA DE NEGOCIO ---
# =========================================================

class AppLogic:
    def __init__(self, links, profiles):
        self.links    = links
        self.profiles = profiles

        self.detector      = None
        self.ui            = None
        self.root          = None
        self.last_clap_time = 0

        # Lista de handles de hotkeys registradas en el sistema
        # Se guarda acá para poder eliminarlas antes de re-registrar
        self.hotkey_handles = []

    # =========================================================
    #                     APERTURA INTELIGENTE
    # =========================================================

    @staticmethod
    def detect_type(path):
        # Limpia comillas que agrega Windows al copiar paths
        path = path.strip().strip('"').strip("'")

        # Si empieza con http/https → URL de internet
        if path.startswith("http://") or path.startswith("https://"):
            return "url"
        # Si existe como path en disco → archivo local
        if os.path.exists(path):
            return "file"
        # Si no cumple ninguna → asumir URL
        return "url"

    @staticmethod
    def open_item(path, item_type):
        # Abre un archivo local con su programa predeterminado
        # o una URL en el navegador según el tipo
        if item_type == "file":
            os.startfile(path)
        else:
            webbrowser.open_new_tab(path)

    @staticmethod
    def clean_path(path):
        # Elimina comillas que Windows agrega al copiar paths con "Copy path"
        return path.strip().strip('"').strip("'")

    # =========================================================
    #                     HOTKEYS
    # Se re-registran cada vez que se guarda un cambio en perfiles.
    # =========================================================

    def register_hotkeys(self):
        # Elimina todas las hotkeys anteriores antes de registrar las nuevas
        # Evita duplicados si se llama varias veces
        for h in self.hotkey_handles:
            try:
                keyboard.remove_hotkey(h)
            except:
                pass
        self.hotkey_handles.clear()

        if not self.profiles:
            return

        for p in self.profiles:
            if p.get("hotkey"):
                try:
                    h = keyboard.add_hotkey(
                        p["hotkey"],
                        lambda prof=p: self.trigger_profile(prof)
                        # lambda prof=p: captura el perfil en el closure
                        # sin esto todos los perfiles abrirían el mismo (el último)
                    )
                    self.hotkey_handles.append(h)
                except:
                    print(f"Hotkey inválida: {p['hotkey']}")

    # =========================================================
    #                     APLAUSOS
    # =========================================================

    CLAP_WINDOW           = 0.65  # segundos de ventana para contar aplausos
    POST_TRIGGER_COOLDOWN = 2.0   # segundos de espera después de abrir un link

    def on_clap(self):
        # Puente entre el thread de audio y el thread principal de tkinter
        # root.after(0) programa handle_clap() en el thread de tkinter
        # Nunca tocar widgets de tkinter desde otro thread directamente
        if self.ui and self.ui.capturing_hotkey:
            return
        self.root.after(0, self.handle_clap)

    def handle_clap(self):
        now = time.time()

        # Si ya hay una ventana de conteo activa, solo suma el aplauso
        if getattr(self, "_in_clap_window", False):
            self._clap_count = getattr(self, "_clap_count", 1) + 1
            return

        # Cooldown post-apertura — ignora aplausos justo después de abrir
        if now - getattr(self, "_last_opened_time", 0) < self.POST_TRIGGER_COOLDOWN:
            return

        # No procesa si hay animación activa
        if self.ui.clap.cget("text") != "":
            return

        has_single = any(
            link.get("enabled") and link.get("claps", 1) == 1
            for link in self.links
        )
        has_double = any(
            link.get("enabled") and link.get("claps", 1) == 2
            for link in self.links
        )

        if not has_single and not has_double:
            self.ui.status.config(text="Sin links activos")
            return

        if not has_double:
            # Solo hay links de 1 aplauso → abrir inmediatamente sin ventana
            for link in self.links:
                if link.get("enabled") and link.get("claps", 1) == 1:
                    self.open_item(link["url"], link.get("type", "url"))
            self._last_opened_time = now
            self.ui.animate_clap()
            self.ui.status.config(text="¡Aplauso detectado!")
            self._restore_status_later()
            return

        # Hay links de doble (con o sin links de 1 aplauso)
        # → iniciar ventana de conteo
        self._in_clap_window = True
        self._clap_count     = 1
        # Cooldown corto para que el detector pueda capturar el segundo aplauso
        self.detector.use_short_cooldown = True
        self.root.after(int(self.CLAP_WINDOW * 1000), self._process_clap_window)

    def _process_clap_window(self):
        # Se ejecuta al terminar la ventana de tiempo
        # Decide qué links abrir según cuántos aplausos se contaron
        self._in_clap_window             = False
        self.detector.use_short_cooldown = False

        clap_count = getattr(self, "_clap_count", 1)
        now        = time.time()

        has_single = any(
            link.get("enabled") and link.get("claps", 1) == 1
            for link in self.links
        )
        has_double = any(
            link.get("enabled") and link.get("claps", 1) == 2
            for link in self.links
        )

        opened      = False
        status_text = ""

        if clap_count >= 2 and has_double:
            # Doble aplauso → abre solo los links de 2 aplausos
            for link in self.links:
                if link.get("enabled") and link.get("claps", 1) == 2:
                    self.open_item(link["url"], link.get("type", "url"))
                    opened = True
            status_text = "¡Doble aplauso detectado!"

        elif clap_count == 1 and has_single:
            # Un solo aplauso → abre solo los links de 1 aplauso
            for link in self.links:
                if link.get("enabled") and link.get("claps", 1) == 1:
                    self.open_item(link["url"], link.get("type", "url"))
                    opened = True
            status_text = "¡Aplauso detectado!"

        if opened:
            self._last_opened_time = now
            self.ui.animate_clap()
            self.ui.status.config(text=status_text)
            self._restore_status_later()

    def _restore_status_later(self):
        # Restaura el status 2 segundos después sin animación
        # La animación de puntos solo se activa desde update_detector_state
        def restore():
            if any(link.get("enabled") for link in self.links):
                self.ui.status.config(text="Esperando Aplausos...")
            else:
                self.ui.status.config(text="Esperando...")
        self.root.after(2000, restore)

    # =========================================================
    #                     PERFILES
    # =========================================================

    def trigger_profile(self, profile):
        # Abre todos los items del perfil (URLs o archivos)
        # No hace nada si se está capturando una hotkey nueva
        if self.ui and self.ui.capturing_hotkey:
            return

        # Soporta tanto el formato nuevo (items) como el viejo (urls)
        # para compatibilidad con datos existentes
        if "items" in profile:
            for item in profile["items"]:
                self.open_item(item["path"], item.get("type", "url"))
        else:
            for url in profile.get("urls", []):
                self.open_item(url, "url")

    # =========================================================
    #                     DETECTOR
    # =========================================================

    def update_detector_state(self):
        any_enabled  = any(link.get("enabled") for link in self.links)
        was_enabled  = getattr(self, "_was_any_enabled", False)

        if any_enabled:
            self.detector.start()
            # Solo anima en la transición 0 → 1 (primer toggle activado)
            if not was_enabled:
                self.ui.animate_dots("Esperando Aplausos", self.ui.status, 3000)
        else:
            self.detector.stop()
            # Para la animación si estaba corriendo y muestra el texto base
            if hasattr(self.ui, "_dots_stop"):
                self.ui._dots_stop()
            self.ui.status.config(text="Esperando...")

        self._was_any_enabled = any_enabled