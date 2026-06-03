import tkinter as tk
import threading
import sys
import os

from core.storage import load_json, save_json
from core.audio import ClapDetector
from core.logic import AppLogic
from ui.app import AppUI

import pystray
from PIL import Image
import ctypes

# =========================================================
# --- INSTANCIA ÚNICA ---
# Evita que se abran múltiples instancias de la app.
# CreateMutexW crea un objeto mutex con nombre único en Windows.
# Si ya existe (error 183) significa que la app ya está corriendo
# y esta nueva instancia se cierra inmediatamente.
# =========================================================
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "JarvisAppMutex_v1")
if ctypes.windll.kernel32.GetLastError() == 183:
    # ERROR_ALREADY_EXISTS → ya hay una instancia corriendo
    # El usuario puede abrirla desde el ícono en la bandeja
    ctypes.windll.kernel32.CloseHandle(_mutex)
    sys.exit(0)
    
# =========================================================
# --- BASE PATH ---
# Detecta si corre como .exe compilado o como script .py
# y establece la carpeta raíz del proyecto.
# Todos los paths de archivos se construyen desde acá.
# =========================================================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.json")
LINKS_PATH    = os.path.join(BASE_DIR, "data",   "links.json")

# =========================================================
# --- CARGA INICIAL --- 
# =========================================================
settings = load_json(SETTINGS_PATH, {"sensitivity": 0.5, "cooldown": 2, "minimize_to_tray": False})
data     = load_json(LINKS_PATH,    {"links": [], "profiles": []})

links    = data["links"]
profiles = data["profiles"]

# =========================================================
# --- INSTANCIAS BASE ---
# logic y detector se conectan entre sí antes de crear la UI
# =========================================================
logic = AppLogic(links, profiles)
root  = tk.Tk()
is_tray_start = "--tray" in sys.argv

# =========================================================
# --- DETECTOR DE AUDIO ---
# Usa logic.on_clap como callback para mantener
# toda la lógica de aplausos dentro de AppLogic
# =========================================================
detector = ClapDetector(
    settings["sensitivity"],
    settings["cooldown"],
    logic.on_clap,
    settings.get("mic_device", None)  # None = dispositivo por defecto
)
logic.detector = detector

# =========================================================
# --- GUARDADO ---
# Persiste links y perfiles en disco y actualiza el estado.
# =========================================================
def save_links():
    global links, profiles

    if not isinstance(links, list):
        links = []
    if not isinstance(profiles, list):
        profiles = []

    save_json(LINKS_PATH, {
        "links":    links,
        "profiles": profiles
    })

    logic.register_hotkeys()
    logic.update_detector_state()

# =========================================================
# --- SETTINGS ---
# Actualiza la sensibilidad en caliente (sin reiniciar)
# y persiste los nuevos valores en disco.
# =========================================================
def save_settings(new_settings):
    settings.update(new_settings)
    detector.sens = settings["sensitivity"]

    # Actualiza el dispositivo — requiere reiniciar el stream
    new_device = settings.get("mic_device", None)

    # RESETEA ADAPTACIÓN DEL AMBIENTE
    detector.noise_floor = 0.01
    detector.prev_rms = 0

    if detector.device != new_device:
        detector.device = new_device

        if detector.running:
            detector.stop()
            detector.start()

    save_json(SETTINGS_PATH, settings)

# =========================================================
# --- BANDEJA (SYSTEM TRAY) ---
# =========================================================

def get_icon_path():
    return os.path.join(BASE_DIR, "assets", "IconoJarvis.ico")

tray_icon = None

def show_window():
    # Programa la restauración en el thread de tkinter
    # No llamar _restore_window() directamente desde el thread del tray
    root.after(0, _restore_window)

def _restore_window():
    root.deiconify()
    root.lift()
    root.focus_force()
    
def quit_app():
    if tray_icon:
        tray_icon.stop()
    root.after(0, root.destroy)

def start_tray():
    # pystray.run() es bloqueante, por eso necesita su propio thread
    global tray_icon
    with Image.open(get_icon_path()) as img:
        image = img.copy()

    # Los lambdas reciben (icon, item) porque así los llama pystray
    menu = pystray.Menu(
        # default=True → se ejecuta con single click izquierdo en Windows
        pystray.MenuItem("Abrir", lambda icon, item: show_window(), default=True),
        pystray.MenuItem("Salir", lambda icon, item: quit_app())
    )
    tray_icon = pystray.Icon("Jarvis", image, "Jarvis", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

def hide_to_tray():
    # Cierra cualquier ventana emergente abierta antes de ocultar
    for widget in root.winfo_children():
        if isinstance(widget, tk.Toplevel):
            widget.destroy()
    root.withdraw()
    
# =========================================================
# --- UI ---
# =========================================================
ui = AppUI(
    root,
    links,
    profiles,
    save_links,
    logic,
    settings,
    save_settings,
    hide_to_tray
)

logic.ui   = ui
logic.root = root

# =========================================================
# --- INIT ---
# =========================================================
logic.register_hotkeys()
root.after(100, logic.update_detector_state)

# Bandeja siempre activa desde el arranque
start_tray()

if is_tray_start:
    root.withdraw()

root.title("JARVIS - Personal Assistant")
if sys.platform.startswith("win"):
    root.iconbitmap(get_icon_path())
else:
    root.iconphoto(get_icon_path())
# =========================================================
# --- LOOP PRINCIPAL ---
# =========================================================
root.mainloop()