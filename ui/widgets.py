import tkinter as tk
import customtkinter as ctk

from ui.theme import (
    BG, BG2, TITLEBAR, FG,
    ACCENT, ACCENT2, BTN, BTN_HOVER,
    CARD, CARD_BORDER, RED, GREEN,
    GRIS_OSCURO, GRIS_CLARO, HELPER
)

# =========================================================
# --- MIXIN DE WIDGETS ---
# Métodos reutilizables de construcción de UI.
# Se separan de app.py para mantenerlo manejable.
# AppUI hereda de esta clase para tener estos métodos.
# =========================================================

class WidgetsMixin:

    # ---- Título de sección con subtítulo ----
    def _section_label(self, parent, title, subtitle=None, help_text=None, f_color=None):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            frame, text=title,
            font=("Consolas", 11, "bold"),
            bg=BG, fg=FG
        ).pack(side="left")

        tk.Label(
            frame, text=subtitle,
            font=("Consolas", 8),
            bg=BG, fg="#555e6e"
        ).pack(side="left", padx=6, pady=3)

        # Si se pasa help_text, agrega el ícono ? a la derecha
        if help_text:
            self._help_icon(frame, help_text, f_color).pack(side="left", padx=(2, 0))
    
    def _help_icon(self, parent, text, f_color=None):
        # =========================================================
        # Ícono de ayuda "?" que muestra un tooltip al hover o click.
        # Hover 1s  → aparece automáticamente, desaparece al sacar el mouse
        # Click     → queda fijo hasta que clickeás en otra parte
        # Retorna el label para que el caller lo packee donde quiera.
        # =========================================================
        tooltip_win  = None
        hover_after  = None
        pinned       = False
        dismiss_bind = None

        label = tk.Label(
            parent, text="❓",
            font=("Segoe UI Emoji)", 7),
            bg=f_color, fg=GRIS_OSCURO,
            cursor="hand2"
        )

        def show():
            nonlocal tooltip_win
            # No crea otro si ya existe
            if tooltip_win and tooltip_win.winfo_exists():
                return

            tooltip_win = tk.Toplevel(self.root)
            tooltip_win.overrideredirect(True)
            # Borde de 1px en ACCENT usando el fondo de la ventana
            tooltip_win.configure(bg=HELPER)

            inner = tk.Frame(tooltip_win, bg="#1a1e26", padx=10, pady=8)
            inner.pack(padx=1, pady=1)

            tk.Label(
                inner, text=text,
                font=("Consolas", 9),
                bg="#1a1e26", fg=FG,
                wraplength=220, justify="left"
            ).pack()

            # Posiciona debajo del ícono ?
            tooltip_win.update_idletasks()
            lx = label.winfo_rootx()
            ly = label.winfo_rooty() + label.winfo_height() + 4
            tooltip_win.geometry(f"+{lx}+{ly}")
            tooltip_win.lift()

        def hide():
            nonlocal tooltip_win
            if tooltip_win:
                try:
                    tooltip_win.destroy()
                except:
                    pass
                tooltip_win = None

        def on_enter(e):
            nonlocal hover_after
            label.config(fg=ACCENT)
            # Espera 1 segundo antes de mostrar
            hover_after = label.after(1000, show)

        def on_leave(e):
            nonlocal hover_after
            label.config(fg=GRIS_OSCURO)
            if hover_after:
                label.after_cancel(hover_after)
                hover_after = None
            # Solo oculta si no está fijo por click
            if not pinned:
                hide()

        def on_click(e):
            nonlocal pinned, dismiss_bind, hover_after
            if pinned:
                # Segundo click → desancla y oculta
                pinned = False
                hide()
                if dismiss_bind:
                    try:
                        self.root.unbind("<Button-1>", dismiss_bind)
                    except:
                        pass
                    dismiss_bind = None
            else:
                # Primer click → ancla el tooltip
                pinned = True
                if hover_after:
                    label.after_cancel(hover_after)
                    hover_after = None
                show()
                # Bind temporal para cerrar al clickear en otra parte
                self.root.bind_all("<Button-1>", on_dismiss, "+")
            # Evita que el click propague al _global_click de la app
            return "break"

        def on_dismiss(e):
            nonlocal pinned, dismiss_bind
            # Ignora si el click fue en el propio ícono
            if e.widget == label:
                return
            pinned = False
            hide()
            if dismiss_bind:
                try:
                    self.root.unbind_all("<Button-1>")
                except:
                    pass
                dismiss_bind = None

        label.bind("<Enter>",    on_enter)
        label.bind("<Leave>",    on_leave)
        label.bind("<Button-1>", on_click)

        return label

    # ---- Contenedor scrolleable con canvas interno ----
    # height: altura fija del contenedor en píxeles
    def _scrollable_frame(self, parent, height=200, bg=None, event_widget=None):
        # bg=None usa CARD por defecto
        # event_widget=None usa self.root — pasar win cuando se usa dentro de un modal
        # con grab_set() activo, porque los eventos van al modal, no al root
        if bg is None:
            bg = CARD
        if event_widget is None:
            event_widget = self.root
        if not hasattr(self, "_scroll_canvases"):
            self._scroll_canvases = []

        container = tk.Frame(
            parent, bg=bg,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            height=height
        )
        container.pack(fill="x", pady=(0, 6))
        container.pack_propagate(False)

        canvas = tk.Canvas(container, bg=bg, bd=0, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._scroll_canvases.append(canvas)

        inner = tk.Frame(canvas, bg=bg)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def resize_inner(event):
            canvas.itemconfig(window, width=event.width)
        canvas.bind("<Configure>", resize_inner)

        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", update_scrollregion)

        def on_global_mousewheel(event):
            for c in self._scroll_canvases:
                try:
                    cx = c.winfo_rootx()
                    cy = c.winfo_rooty()
                    cw = c.winfo_width()
                    ch = c.winfo_height()
                    mx = event.x_root
                    my = event.y_root
                    if cx <= mx <= cx + cw and cy <= my <= cy + ch:
                        inner_frame = c.children.get("!frame") or c.children.get(list(c.children.keys())[0])
                        content_h = inner_frame.winfo_reqheight()
                        visible_h = c.winfo_height()
                        if content_h > visible_h:
                            c.yview_scroll(-1 * (event.delta // 120), "units")
                        return
                except:
                    pass

        event_widget.bind("<MouseWheel>", on_global_mousewheel)

        return inner

    # ---- Botón de texto discreto tipo "+ Agregar algo" ----
    def _add_button(self, parent, text, command):
        btn = tk.Label(
            parent, text=f"+ {text}",
            font=("Consolas", 8),
            bg=BG, fg="#555e6e", cursor="hand2"
        )
        btn.pack(anchor="w", pady=(2, 8))
        btn.bind("<Enter>",    lambda e: btn.config(fg=ACCENT))
        btn.bind("<Leave>",    lambda e: btn.config(fg="#555e6e"))
        btn.bind("<Button-1>", lambda e: command())

    # ---- Botón CTk estilizado ----
    # accent=True → fondo celeste (acción principal)
    # accent=False → fondo gris (acción secundaria)
    def _ctk_button(self, parent, text, command, width=140, accent=False):
        color = ACCENT  if accent else BTN
        hover = ACCENT2 if accent else BTN_HOVER
        fg    = "#000000" if accent else FG

        return ctk.CTkButton(
            parent, text=text, command=command,
            width=width, height=32, corner_radius=6,
            fg_color=color, hover_color=hover,
            text_color=fg, font=("Consolas", 11)
        )

    # ---- Centrar una ventana en la pantalla ----
    def center_window(self, win, width, height):
        win.update_idletasks()
        x = (win.winfo_screenwidth()  // 2) - (width  // 2)
        y = (win.winfo_screenheight() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.lift()

    # ---- Crear ventana modal con titlebar custom ----
    # Todas las ventanas emergentes (editores, ajustes) usan esto.
    # Retorna (win, content) donde content es el frame interior usable.
    def _make_window(self, width, height, title=""):
        win = tk.Toplevel(self.root)

        # Fondo negro para el borde de 1px
        win.configure(bg=TITLEBAR)
        win.geometry(f"{width}x{height}")
        win.overrideredirect(True)  # sin decoración nativa de Windows

        # ----- TITLEBAR -----
        bar = tk.Frame(win, bg=TITLEBAR, height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(
            bar, text=title,
            font=("Consolas", 10, "bold"),
            bg=TITLEBAR, fg=ACCENT
        ).pack(side="left", padx=10)

        close_btn = tk.Label(
            bar, text="  ✕  ",
            font=("Consolas", 10),
            bg=TITLEBAR, fg="#666e7a"
        )
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Enter>",    lambda e: close_btn.config(bg=RED, fg="white"))
        close_btn.bind("<Leave>",    lambda e: close_btn.config(bg=TITLEBAR, fg="#666e7a"))
        close_btn.bind("<Button-1>", lambda e: win.destroy())

        # Drag para mover la ventana emergente
        def start_drag(e):
            win._drag_x = e.x_root - win.winfo_x()
            win._drag_y = e.y_root - win.winfo_y()

        def drag(e):
            x = e.x_root - win._drag_x
            y = e.y_root - win._drag_y
            win.geometry(f"+{x}+{y}")

        bar.bind("<ButtonPress-1>", start_drag)
        bar.bind("<B1-Motion>", drag)

        # Border frame de 1px negro alrededor del contenido
        border = tk.Frame(win, bg=TITLEBAR, padx=2, pady=2)
        border.pack(fill="both", expand=True)

        content = tk.Frame(border, bg=BG2)
        content.pack(fill="both", expand=True)

        # Centra la ventana después de que tkinter la renderice
        # Se usa after(0) porque geometry no es inmediato
        def do_center():
            win.update_idletasks()
            w  = win.winfo_width()
            h  = win.winfo_height()
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x  = (sw - w) // 2
            y  = (sh - h) // 2
            win.geometry(f"{w}x{h}+{x}+{y}")
            win.deiconify()
            win.lift()
            win.focus_force()
            # Pequeño delay para asegurarse que el foco está establecido
            # antes de poner el grab — evita que la segunda apertura quede bloqueada
            win.after(10, win.grab_set)

        win.withdraw()
        win.after(0, do_center)

        return win, content

    # ---- Verifica si un widget es hijo de otro ----
    # Se usa para saber si el click fue dentro de un item de la lista
    def _is_child_of(self, widget, parent):
        if not hasattr(widget, "master"):
            return False
        while widget:
            if widget == parent:
                return True
            widget = getattr(widget, "master", None)
        return False

    # ---- Cambia el color de fondo de un widget y todos sus hijos ----
    # Se usa para resaltar o deseleccionar items de las listas
    # Ignora CTkSwitch porque maneja su propio fondo internamente
    def _set_bg_recursive(self, widget, color):
        try:
            if not isinstance(widget, ctk.CTkSwitch) and not getattr(widget, "_skip_bg", False):
                widget.config(bg=color)
        except:
            pass
        for child in widget.winfo_children():
            self._set_bg_recursive(child, color)
    