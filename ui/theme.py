import customtkinter as ctk

# =========================================================
# --- TEMA VISUAL ---
# Todos los colores de la app están centralizados acá.
# Si querés cambiar el esquema visual, solo tocás este archivo.
# =========================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Fondos principales
BG        = "#16191f"   # fondo general de la ventana
BG2       = "#1e222a"   # fondo de ventanas emergentes

# Titlebar
TITLEBAR  = "#12151a"   # barra superior de la ventana principal

# Texto
FG        = "#e6e6e6"   # texto principal
GRIS_CLARO   = "#cbd0db"   # texto de la consola
GRIS_OSCURO = "#888888"   # texto secundario, placeholders, labels 
# Acentos
ACCENT      = "#00d4ff"   # color principal de resaltado (celeste)
ACCENT3     = "#12b4d5"
ACCENT2     = "#0099bb"   # versión más oscura del acento (hover)
ACCENT_CARD = "#033039" 

HELPER    = "#0c4d46" 
EDT       = "#20DB90" 

# Botones
BTN       = "#2a2f3a"   # fondo de botones normales
BTN_HOVER = "#3a4150"   # fondo de botones al pasar el mouse

# Cards / items
CARD        = "#22272f"   # fondo de items en las listas
CARD_BORDER = "#2e3440"   # borde de cards y separadores

# Estados
RED   = "#e05c5c"   # errores, eliminar, cerrar
GREEN = "#4caf7d"   # éxito, guardado, confirmación