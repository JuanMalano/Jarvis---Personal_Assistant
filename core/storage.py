import json
import os

# =========================================================
# --- ALMACENAMIENTO ---
# Maneja la lectura y escritura de archivos JSON.
# Todos los datos persistentes de la app pasan por acá.
# =========================================================

def ensure_file(path, default):
    # Crea el archivo con valores default si no existe
    # También crea las carpetas intermedias si faltan
    folder = os.path.dirname(path)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f, indent=4)

def load_json(path, default):
    # Carga un archivo JSON y devuelve su contenido
    # Si el archivo no existe lo crea con los valores default
    # Si el contenido no es un dict devuelve default (archivo corrupto)
    ensure_file(path, default)

    try:
        with open(path, "r") as f:
            data = json.load(f)

            if not isinstance(data, dict):
                return default

            return data
    except:
        # Si falla la lectura por cualquier motivo, devuelve default
        return default

def save_json(path, data):
    # Guarda un dict como JSON en el path indicado
    # Crea las carpetas intermedias si no existen
    folder = os.path.dirname(path)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    with open(path, "w") as f:
        json.dump(data, f, indent=4)