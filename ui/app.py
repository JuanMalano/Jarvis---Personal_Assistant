import customtkinter as ctk
import tkinter as tk
import hPyT as hpt
import ctypes
from ui.theme import (
    BG, BG2, TITLEBAR, FG,
    ACCENT, ACCENT_CARD, ACCENT3, ACCENT2, BTN, BTN_HOVER,
    CARD, CARD_BORDER, RED, GREEN, 
    GRIS_CLARO, GRIS_OSCURO, EDT, HELPER
)
from ui.editors import EditorsMixin
from ui.widgets import WidgetsMixin

# =========================================================
#                        EJE PRINCIPAL
# AppUI hereda de dos mixins para mantener el archivo limpio:
#   - WidgetsMixin  → helpers de construcción de UI (scrollable, botones, ventanas)
#   - EditorsMixin  → ventanas emergentes (link editor, profile editor, ajustes)
# =========================================================
class AppUI(WidgetsMixin, EditorsMixin):
    def __init__(self, root, links, profiles, save_links, logic, settings, save_settings=None, hide_to_tray=None):
        # Callbacks externos — funciones definidas en main.py
        self.save_settings = save_settings  # persiste settings.json y actualiza el detector
        self.hide_to_tray  = hide_to_tray   # oculta la ventana y la manda a la bandeja

        # Datos compartidos con main.py (mismos objetos, no copias)
        # Cualquier cambio acá se refleja en main.py y viceversa
        self.links    = links
        self.profiles = profiles
        self.settings = settings

        # Referencias a funciones y objetos del core
        self.root       = root
        self.save_links = save_links  # guarda links.json, re-registra hotkeys
        self.logic      = logic

        # Estado interno de la UI
        self.capturing_hotkey  = False  # True mientras se está capturando una hotkey nueva
        self._selected_link    = None   # índice del link seleccionado en la lista (o None)
        self._selected_profile = None   # índice del perfil seleccionado en la lista (o None)
        self._link_rows        = []     # referencias a los frames de cada link (para resaltar)
        self._profile_cards    = []     # referencias a los frames de cada perfil (para resaltar)

        # ---- DRAG AND DROP ----
        self._drag_active     = False
        self._drag_type       = None     # "link" o "profile"
        self._drag_source_idx = None     # índice original
        self._drag_source_row = None     # widget del row original
        self._drag_ghost      = None     # ventana flotante que sigue el mouse
        self._drag_indicator  = None     # línea pill que indica dónde caería
        self._drag_ind_canvas = None     # canvas de la línea pill
        self._drag_hold_timer = None     # timer de 500ms
        self._drag_target_idx = None     # índice del target actual
        self._drag_target_pos = None     # "above" o "below"
        self._drag_last_target = None
        self._drag_ghost_w     = 0
        self._drag_ghost_h     = 0
        self._drag_pill_width  = 0

        # Estado del drag — coordenadas al inicio del arrastre para mover la ventana
        self._drag_x = 0
        self._drag_y = 0
        
        self.build()

    # =========================================================
    #                        BUILD
    # Construye toda la interfaz principal al arrancar.
    # Se llama una sola vez desde __init__.
    # =========================================================
    def build(self):
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0)
        self.root.withdraw()
        self.center_window(self.root, 560, 600)
        self.root.update_idletasks()
        
        self.root.after(100, self.root.deiconify)
        hpt.title_bar.hide(self.root)
        
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-alpha", 1)

        # ---- TITLEBAR CUSTOM ----
        self._build_titlebar()

        # ---- SEPARADOR ----
        tk.Frame(self.root, bg=CARD_BORDER, height=1).pack(fill="x")

        # ---- MAIN CONTENT ----
        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # ---- COLUMNA LINKS ----
        links_col = tk.Frame(content, bg=BG)
        links_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self._section_label(
            links_col, "Links", "Activados con aplausos",
            help_text="Activá los links que quieras abrir al aplaudir, podés tener varios activos a la vez.\n\n"
            "Al momento de tener activo algun link, se empezara a usar el microfono preseleccionado. Aparecera para confirmarlo, el siguiente mensaje: \"esperando aplausos...\"\n\n" \
            "Activación:\n- Doble click sobre el link\n- Click sobre el borde izquierdo.\n\nOrdenar:\n - Mantener el click sobre el item a cambiar.", f_color=BG
        )
        self.links_inner = self._scrollable_frame(links_col, height=220)
        self._add_button(links_col, "Agregar link", self.open_link_editor)

        # ---- COLUMNA PERFILES ----
        profiles_col = tk.Frame(content, bg=BG)
        profiles_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._section_label(
            profiles_col, "Perfiles", "Activados con hotkey",
            help_text="Cada perfil agrupa URLs y/o archivos que se abren junto mediante una combinación de teclas.\n\nAsignale una hotkey para abrirlo en cualquier momento mientras la app este en uso." \
            "\n\nOrdenar:\n - Mantener el click sobre el item a cambiar.", f_color=BG
        )
        self.profiles_inner = self._scrollable_frame(profiles_col, height=220)
        self._add_button(profiles_col, "Agregar perfil", self.open_profile_editor)

        # ---- SEPARADOR ----
        tk.Frame(self.root, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(5, 0))

        # ---- CONTROLES ----
        controls = tk.Frame(self.root, bg=BG)
        controls.pack(pady=10)

        self._ctk_button(controls, "⚙  Ajustes", self.open_settings, width=120).pack(side="left", padx=5)

        # Botón Abrir: gris por defecto, se vuelve celeste al seleccionar un item
        # Se actualiza desde _update_open_btn() cada vez que cambia la selección
        self.open_btn = self._ctk_button(controls, "▶  Abrir", self.start, width=120, accent=False)
        self.open_btn.pack(side="left", padx=5)

        # ---- STATUS ----
        # Muestra mensajes de estado: aplausos detectados, errores, item abierto, etc.
        self.status = tk.Label(
            self.root, text=". . .",
            font=("Consolas", 9), bg=BG, fg=GRIS_OSCURO
        )
        self.status.pack()

        # Label para la animación del emoji de aplauso 👏
        self.clap = tk.Label(self.root, text="", font=("Arial", 26), bg=BG, fg=ACCENT)
        self.clap.pack()

        # ---- FOOTER ----
        tk.Frame(self.root, bg=CARD_BORDER, height=1).pack(fill="x", padx=20)

        footer = tk.Frame(self.root, bg=BG, pady=5)
        footer.pack(fill="x", padx=20)

        tk.Label(
            footer,
            text=f"by Juan Malano",
            font=("Consolas", 7), bg=BG, fg=GRIS_OSCURO
        ).pack(side="left")

        # Versión y fecha apiladas a la derecha
        right_footer = tk.Frame(footer, bg=BG)
        right_footer.pack(side="right")

        tk.Label(
            right_footer,
            text=self.settings.get("version", "v?"),
            font=("Consolas", 7), bg=BG, fg=ACCENT2
        ).pack(anchor="e")

        tk.Label(
            right_footer,
            text=f"editado: {self.settings.get('fecha_ultima_edicion', '?')}",
            font=("Consolas", 7), bg=BG, fg=GRIS_OSCURO
        ).pack(anchor="e")

        # Carga los items en las listas
        self.refresh()

        # Listener global de clicks para deseleccionar al hacer click fuera
        self.root.bind_all("<Button-1>", self._global_click)

    # =========================================================
    #                     TITLEBAR CUSTOM
    # Barra superior personalizada con título, minimizar y cerrar.
    # También maneja el drag para mover la ventana.
    # =========================================================
    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=TITLEBAR, height=38)
        bar.pack(fill="x")
        bar.pack_propagate(False)  # respeta el height fijo de 38px

        # ---- TÍTULO izquierda ----
        title_frame = tk.Frame(bar, bg=TITLEBAR)
        title_frame.pack(side="left", padx=14, pady=6)

        tk.Label(
            title_frame,
            text="JARVIS",
            font=("Consolas", 14, "bold"),
            bg=TITLEBAR, fg=ACCENT
        ).pack(side="left")

        tk.Label(
            title_frame,
            text="Personal Assistant",
            font=("Consolas", 8),
            bg=TITLEBAR, fg="#555e6e"
        ).pack(side="left", padx=6, pady=2)

        # ---- BOTONES derecha ----
        btn_frame = tk.Frame(bar, bg=TITLEBAR)
        btn_frame.pack(side="right", fill="y")

        close_btn = tk.Label(
            btn_frame, text="  ✕  ",
            font=("Consolas", 11),
            bg=TITLEBAR, fg=GRIS_OSCURO
        )
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Enter>",    lambda e: close_btn.config(bg=RED, fg="white"))
        close_btn.bind("<Leave>",    lambda e: close_btn.config(bg=TITLEBAR, fg=GRIS_CLARO))
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        min_btn = tk.Label(
            btn_frame, text="  —  ",
            font=("Consolas", 11),
            bg=TITLEBAR, fg=GRIS_CLARO
        )
        min_btn.pack(side="right", fill="y")
        min_btn.bind("<Enter>",    lambda e: min_btn.config(bg=BTN_HOVER, fg=FG))
        min_btn.bind("<Leave>",    lambda e: min_btn.config(bg=TITLEBAR,  fg=GRIS_CLARO))
        min_btn.bind("<Button-1>", lambda e: self._on_minimize())

        # ---- DRAG para mover ventana ----
        # Se bindea al bar y al title_frame y sus hijos para que el drag
        # funcione en toda la barra, no solo en el texto
        for widget in [bar, title_frame] + list(title_frame.winfo_children()):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>",     self._drag_move)

    def _on_minimize(self):
        if self.settings.get("minimize_to_tray") == True and self.hide_to_tray:
            # Minimizar solo a bandeja — oculta completamente
            self.hide_to_tray()
        else:
            # Minimizar a barra de tareas normalmente
            self.root.iconify()
            self.root.bind("<Map>", self._on_restore)

    def _on_restore(self, event):
        self.root.unbind("<Map>")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    #####################################
    ###### POR FAVOR NO TOCAR ESTO ######
    #####################################    

    def _drag_start(self, event):
        # Guarda la posición inicial del drag relativa a la ventana
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()
    def _drag_move(self, event):

        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y

        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

        if not hwnd:
            hwnd = self.root.winfo_id()

        ctypes.windll.user32.SetWindowPos(
            hwnd,
            None,
            x,
            y,
            0,
            0,
            0x0001 | 0x0004  # SWP_NOSIZE | SWP_NOZORDER
        )
    # =========================================================
    #                     APARTADO / LINKS
    # Construye cada fila de link en la lista.
    # =========================================================
    def _build_link_item(self, parent, link, index):
        enabled = link.get("enabled", False)

        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 1))

        # ---- BORDE LATERAL IZQUIERDO ----
        # Actúa como indicador visual de estado Y como botón de toggle
        # Celeste = activo, gris = inactivo
        border_bar = tk.Frame(row, width=8, cursor="hand2",
                              bg=ACCENT if enabled else CARD_BORDER)
        border_bar.pack(side="left", fill="y")
        border_bar._skip_bg = True  # excluir del cambio de fondo al seleccionar

        # Frame interior con padding — separa el contenido del borde
        inner = tk.Frame(row, bg=CARD)
        inner.pack(side="left", fill="x", expand=True, padx=8, pady=5)

        # ---- ICONOS (right) ----
        icons_frame = tk.Frame(inner, bg=CARD, width=46, height=24)
        icons_frame.pack(side="right", padx=(4, 0))
        icons_frame.pack_propagate(False)

        edit_btn = tk.Label(
            icons_frame, text="✏", font=("Segoe UI Emoji", 9),
            bg=CARD, fg=CARD, cursor="hand2"
        )
        edit_btn.pack(side="left", padx=(0, 4))

        del_btn = tk.Label(
            icons_frame, text="🗑", font=("Segoe UI Emoji", 9),
            bg=CARD, fg=CARD, cursor="hand2"
        )
        del_btn.pack(side="left")

        # Badge de aplausos — igual al badge de hotkey en perfiles
        # Se packea después de icons_frame → queda a su izquierda
        clap_text  = "①" if link.get("claps", 1) == 1 else "②"
        clap_badge = tk.Label(
            row, text=clap_text,
            font=("Segoe UI Emoji", 10),
            fg=ACCENT if enabled else GRIS_OSCURO,
            bg=CARD,  # mismo fondo que la card para "camuflarlo"
            padx=2, pady=2
        )
        clap_badge.pack(side="right", padx=(0, 6))

        # ---- NOMBRE ----
        # Color del texto según estado: FG si activo, GRIS_OSCURO si inactivo
        name_label = tk.Label(
            inner, text=link["name"],
            font=("Consolas", 10, "bold"), bg=CARD,
            fg=FG if enabled else GRIS_OSCURO,
            anchor="w", cursor="hand2"
        )
        name_label.pack(side="left", fill="x", expand=True)

        # ---- TOGGLE ----
        def do_toggle():
            link["enabled"] = not link.get("enabled", False)
            is_on = link["enabled"]
            border_bar.config(bg=ACCENT if is_on else CARD_BORDER)
            name_label.config(fg=FG if is_on else GRIS_OSCURO)
            clap_badge.config(fg=ACCENT if is_on else GRIS_OSCURO)
            self.save_links()

        border_bar.bind("<Button-1>", lambda e: do_toggle())
        border_bar.bind("<Enter>",    lambda e: border_bar.config(bg=ACCENT2))
        border_bar.bind("<Leave>",    lambda e: border_bar.config(
            bg=ACCENT if link.get("enabled") else CARD_BORDER))
        # Doble click en el nombre o el row también activa/desactiva
        # Más ergonómico que hacer click en el borde fino
        name_label.bind("<Double-Button-1>", lambda e: do_toggle())
        inner.bind(     "<Double-Button-1>", lambda e: do_toggle())

        # ---- HOVER iconos ----
        def show_icons(e=None):
            edit_btn.config(fg=GRIS_CLARO)
            del_btn.config(fg=GRIS_CLARO)

        def hide_icons(e=None):
            edit_btn.config(fg=CARD)
            del_btn.config(fg=CARD)

        def on_leave(e=None):
            row.after(50, _check_leave)

        def _check_leave():
            try:
                x, y   = row.winfo_pointerxy()
                rx, ry  = row.winfo_rootx(), row.winfo_rooty()
                rw, rh  = row.winfo_width(), row.winfo_height()
                if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
                    hide_icons()
            except:
                hide_icons()

        for w in [row, inner, icons_frame, name_label, edit_btn, del_btn, clap_badge]:
            w.bind("<Enter>", lambda e: show_icons())
            w.bind("<Leave>", on_leave)

        edit_btn.bind("<Enter>", lambda e: (show_icons(), edit_btn.config(fg=EDT)))
        del_btn.bind( "<Enter>", lambda e: (show_icons(), del_btn.config(fg=RED)))

        # ---- SELECCIÓN ----
        # Ignora clicks en los botones de editar/eliminar y en el border toggle
        def select_item(e):
            if e.widget in (edit_btn, del_btn, border_bar):
                return
            if self._drag_active:
                return
            self._select_link(index, row)

        name_label.bind("<Button-1>", select_item)
        inner.bind(     "<Button-1>", select_item)
        row.bind(       "<Button-1>", select_item)

        edit_btn.bind("<Button-1>", lambda e, i=index: self.open_link_editor(i))
        del_btn.bind( "<Button-1>", lambda e, i=index: self._delete_link(i))

        # ---- DRAG HOLD ----
        def on_press_drag(e):
            if e.widget in (edit_btn, del_btn, border_bar):
                return
            if self._drag_hold_timer:
                self.root.after_cancel(self._drag_hold_timer)
            self._drag_hold_timer = self.root.after(
                500, lambda: self._drag_begin(index, "link")
            )

        def cancel_drag_hold(e):
            # Cancela el timer si el usuario soltó antes de 500ms
            if self._drag_hold_timer:
                self.root.after_cancel(self._drag_hold_timer)
                self._drag_hold_timer = None

        for w in [row, inner, name_label]:
            w.bind("<ButtonPress-1>",   on_press_drag,    "+")
            w.bind("<ButtonRelease-1>", cancel_drag_hold, "+")

        return row

    def _select_link(self, index, row):
        # Deselecciona todos y resalta el seleccionado
        for r in self._link_rows:
            self._set_bg_recursive(r, CARD)
        self._set_bg_recursive(row, BTN_HOVER)
        self._selected_link = index
        self._update_open_btn()

    def _toggle_link(self, index, var):
        # Actualiza el estado enabled del link y guarda en disco
        self.links[index]["enabled"] = var.get()
        self.save_links()

    def _delete_link(self, index):
        del self.links[index]
        self._selected_link = None
        self.save_links()
        self.refresh()

    # =========================================================
    #                     APARTADO / PERFILES
    # Construye cada card de perfil en la lista.
    # =========================================================
    def _build_profile_card(self, parent, profile, index):
        card = tk.Frame(
            parent, bg=CARD, bd=0,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,  # borde visible cuando no está seleccionado
            padx=10, pady=8
        )
        card.pack(fill="x", pady=(0, 4))

        # Badge con la hotkey asignada (solo si tiene una)
        hk = profile.get("hotkey", "")
        if hk:
            tk.Label(
                card, text=hk,
                font=("Consolas", 8),
                bg=BTN, fg=ACCENT,
                highlightthickness=2,
                highlightbackground="#272B33",
                padx=6, pady=2
            ).pack(side="right", padx=(0, 6))

        # Iconos se packean ANTES del nombre (misma lógica que en links)
        icons_frame = tk.Frame(card, bg=CARD, width=46, height=24)
        icons_frame.pack(side="right", padx=(4, 8))
        icons_frame.pack_propagate(False)

        edit_btn = tk.Label(
            icons_frame, text="✏", font=("Segoe UI Emoji", 9),
            bg=CARD, fg=CARD, cursor="hand2"
        )
        edit_btn.pack(side="left", padx=(0, 4))

        del_btn = tk.Label(
            icons_frame, text="🗑", font=("Segoe UI Emoji", 9),
            bg=CARD, fg=CARD, cursor="hand2"
        )
        del_btn.pack(side="left")

        name_label = tk.Label(
            card, text=profile["name"],
            font=("Consolas", 10, "bold"),
            bg=CARD, fg=FG,
            anchor="w", cursor="hand2"
        )
        name_label.pack(side="left", fill="x", expand=True)

        def show_icons(e=None):
            edit_btn.config(fg=GRIS_CLARO)
            del_btn.config(fg=GRIS_CLARO)

        def hide_icons(e=None):
            edit_btn.config(fg=CARD)
            del_btn.config(fg=CARD)

        def on_leave(e=None):
            card.after(50, _check_leave)

        def _check_leave():
            try:
                x, y   = card.winfo_pointerxy()
                cx, cy  = card.winfo_rootx(), card.winfo_rooty()
                cw, ch  = card.winfo_width(), card.winfo_height()
                if not (cx <= x <= cx + cw and cy <= y <= cy + ch):
                    hide_icons()
            except:
                hide_icons()

        for w in [card, name_label, icons_frame, edit_btn, del_btn]:
            w.bind("<Enter>", lambda e: show_icons())
            w.bind("<Leave>", on_leave)

        edit_btn.bind("<Enter>", lambda e: (show_icons(), edit_btn.config(fg=EDT)))
        del_btn.bind( "<Enter>", lambda e: (show_icons(), del_btn.config(fg=RED)))

        def select_card(e=None):
            if self._drag_active:
                return
            self._select_profile(index, card)

        name_label.bind("<Button-1>", select_card)
        card.bind(      "<Button-1>", select_card)

        edit_btn.bind("<Button-1>", lambda e, i=index: self.open_profile_editor(i))
        del_btn.bind( "<Button-1>", lambda e, i=index: self._delete_profile(i))

        # ---- DRAG HOLD ----
        def on_press_drag(e):
            if e.widget in (edit_btn, del_btn):
                return
            if self._drag_hold_timer:
                self.root.after_cancel(self._drag_hold_timer)
            self._drag_hold_timer = self.root.after(
                500, lambda: self._drag_begin(index, "profile")
            )

        def cancel_drag_hold(e):
            if self._drag_hold_timer:
                self.root.after_cancel(self._drag_hold_timer)
                self._drag_hold_timer = None

        for w in [card, name_label]:
            w.bind("<ButtonPress-1>",   on_press_drag,    "+")
            w.bind("<ButtonRelease-1>", cancel_drag_hold, "+")

        return card

    def _select_profile(self, index, card):
        # Deselecciona todos (borde gris) y resalta el seleccionado (borde celeste)
        for c in self._profile_cards:
            c.config(highlightbackground=CARD_BORDER)
        card.config(highlightbackground=ACCENT)
        self._selected_profile = index
        self._update_open_btn()

    def _delete_profile(self, index):
        del self.profiles[index]
        self._selected_profile = None
        self.save_links()
        self.refresh()

    # =========================================================
    #                       REFRESH
    # Reconstruye ambas listas desde cero.
    # Se llama después de cualquier cambio en links o perfiles.
    # =========================================================
    def refresh(self):
        self._link_rows     = []
        self._profile_cards = []

        # Destruye todos los widgets existentes antes de reconstruir
        for w in self.links_inner.winfo_children():
            w.destroy()
        for i, link in enumerate(self.links):
            self._link_rows.append(self._build_link_item(self.links_inner, link, i))

        for w in self.profiles_inner.winfo_children():
            w.destroy()
        for i, profile in enumerate(self.profiles):
            self._profile_cards.append(self._build_profile_card(self.profiles_inner, profile, i))

    # =========================================================
    #                       ACCIONES / ABRIR
    # =========================================================
    def start(self):
        # Abre el link o perfil seleccionado
        from core.logic import AppLogic

        if self._selected_link is not None:
            link = self.links[self._selected_link]
            self.logic.open_item(link["url"], link.get("type", "url"))
            self.status.config(text=f"Abriendo: {link['name']}")
            self.root.after(2000, lambda: self.status.config(text="Esperando"))
            return

        if self._selected_profile is not None:
            profile = self.profiles[self._selected_profile]
            # Soporta formato nuevo (items) y viejo (urls)
            if "items" in profile:
                for it in profile["items"]:
                    AppLogic.open_item(it["path"], it.get("type", "url"))
            else:
                for url in profile.get("urls", []):
                    AppLogic.open_item(url, "url")
            self.status.config(text=f"Perfil: {profile['name']}")
            self.root.after(2000, lambda: self.status.config(text="Esperando"))
            return

        self.status.config(text="Nada seleccionado")
        self.root.after(2000, lambda: self.status.configjk(text="Esperando..."))
    # =========================================================
    #                     ANIMACIONES
    # =========================================================
    def animate_clap(self):
        # Hace parpadear el emoji 👏 tres veces (6 frames alternando visible/invisible)
        def flash(i=0):
            if i >= 6:
                self.clap.config(text="")
                return
            self.clap.config(text="👏" if i % 2 == 0 else "")
            self.root.after(200, flash, i + 1)
        flash()

    def animate_dots(self, base_text, label, duration=3000):
        # Cancela animación anterior si existe
        if hasattr(self, "_dots_stop"):
            self._dots_stop()

        dots   = ["", ".", "..", "..."]
        active = [True]  # lista mutable para que stop() pueda modificarla

        def stop():
            active[0] = False

        self._dots_stop = stop

        def step(i=0):
            if not active[0]:
                return
            label.config(text=base_text + dots[i % 4])
            self.root.after(400, lambda: step(i + 1))

        step()
        self.root.after(duration, stop)

    # =========================================================
    #                   SELECCIÓN / DESELECCIÓN
    # =========================================================
    def _global_click(self, event):
        # Pequeño delay de 1ms para que el evento de selección
        # de los items se procese antes que la deselección global
        self.root.after(1, lambda: self._handle_global_click(event))

    def _handle_global_click(self, event):
        if self._drag_active:
            return
        widget = event.widget
        if not hasattr(widget, "winfo_exists"):
            return

        # Si el click fue dentro de un link o perfil, no deseleccionar
        for row in self._link_rows:
            if self._is_child_of(widget, row):
                return
        for card in self._profile_cards:
            if self._is_child_of(widget, card):
                return

        # No deseleccionar si el click fue en un widget interactivo
        if isinstance(widget, (
            tk.Button,
            tk.Label,
            tk.Entry,
            ctk.CTkButton,
            ctk.CTkEntry,
            ctk.CTkSwitch
        )):
            return

        self._clear_selection()

    def _clear_selection(self):
        # Vuelve todos los items a su color base y limpia la selección
        for r in self._link_rows:
            self._set_bg_recursive(r, CARD)
        for c in self._profile_cards:
            c.config(highlightbackground=CARD_BORDER)

        self._selected_link    = None
        self._selected_profile = None
        self._update_open_btn()

    def _update_open_btn(self):
        # Resalta el botón Abrir cuando hay algo seleccionado
        # Lo vuelve gris cuando no hay nada seleccionado
        if self._selected_link is not None or self._selected_profile is not None:
            self.open_btn.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color=BG2)
        else:
            self.open_btn.configure(fg_color=BTN, hover_color=BTN_HOVER, text_color=FG)
    
    # =========================================================
    #                     DRAG AND DROP
    # =========================================================

    def _drag_begin(self, index, drag_type):
        self._drag_hold_timer = None

        rows = self._link_rows if drag_type == "link" else self._profile_cards
        if index >= len(rows):
            return

        row = rows[index]
        self._drag_active     = True
        self._drag_type       = drag_type
        self._drag_source_idx = index
        self._drag_source_row = row
        self._drag_target_idx = None
        self._drag_target_pos = None
        self._drag_last_target = None  # para detectar cambios de target

        self._clear_selection()
        self._set_bg_recursive(row, BTN_HOVER)

        name = (self.links[index] if drag_type == "link" else self.profiles[index]).get("name", "")

        row.update_idletasks()
        rw = row.winfo_width()
        rx = row.winfo_rootx()
        ry = row.winfo_rooty()
        rh = row.winfo_height()

        # ---- GHOST ----
        self._drag_ghost = tk.Toplevel(self.root)
        self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes('-alpha', 0.85)
        self._drag_ghost.attributes('-topmost', True)
        self._drag_ghost.configure(bg=CARD_BORDER)

        ghost_inner = tk.Frame(self._drag_ghost, bg=BG2, highlightthickness=2, highlightbackground=ACCENT_CARD, padx=14, pady=1)
        ghost_inner.pack(padx=1, pady=1)
        tk.Label(ghost_inner, text=name, font=("Consolas", 10, "bold"), bg=BG2, fg=FG).pack()

        self._drag_ghost.update_idletasks()
        # Cache de dimensiones para no recalcular en cada frame
        self._drag_ghost_w = self._drag_ghost.winfo_reqwidth()
        self._drag_ghost_h = self._drag_ghost.winfo_reqheight()
        self._drag_ghost.geometry(f"+{rx + rw//2 - self._drag_ghost_w//2}+{ry + rh//2 - self._drag_ghost_h//2}")
        self._drag_ghost.lift()

        # ---- INDICADOR ----
        # Toplevel sólido sin transparentcolor — evita el bug de rendering
        # de la ventana principal en Windows al usar layered windows
        self._drag_indicator = tk.Toplevel(self.root)
        self._drag_indicator.overrideredirect(True)
        self._drag_indicator.configure(bg=BG)
        self._drag_indicator.withdraw()

        self._drag_ind_canvas = tk.Canvas(
            self._drag_indicator, bg=BG,
            width=rw, height=10, highlightthickness=0
        )
        self._drag_ind_canvas.pack()
        self._drag_draw_pill(rw)
        self._drag_pill_width = rw

        # Sin grab_set — bindear a root y al ghost directamente
        # grab_set causaba bugs en el drag del titlebar de modales
        self.root.bind("<B1-Motion>",       self._drag_motion)
        self.root.bind("<ButtonRelease-1>",  self._drag_end)
        self._drag_ghost.bind("<B1-Motion>",      self._drag_motion)
        self._drag_ghost.bind("<ButtonRelease-1>", self._drag_end)

        self.root.configure(cursor="fleur")

    def _drag_draw_pill(self, width, height=6):
        # Dibuja una línea con extremos redondeados (pill) en el canvas
        c = self._drag_ind_canvas
        c.delete("all")
        c.configure(width=width, height=height)
        r = height // 2
        c.create_rectangle(0, 0, width - r, height, fill=ACCENT3, outline=ACCENT)
        c.create_oval(width - height - 1, 0, width - 1, height, fill=ACCENT3, outline=ACCENT3)
        
    def _drag_motion(self, event):
        if not self._drag_active:
            return

        # Mueve el ghost usando dimensiones cacheadas (sin recalcular layout)
        if self._drag_ghost and self._drag_ghost.winfo_exists():
            self._drag_ghost.geometry(
                f"+{event.x_root - self._drag_ghost_w//2}"
                f"+{event.y_root - self._drag_ghost_h//2}"
            )

        # Detecta target
        rows = self._link_rows if self._drag_type == "link" else self._profile_cards
        target_idx = None
        target_pos = None

        for i, row in enumerate(rows):
            if i == self._drag_source_idx:
                continue
            try:
                rx = row.winfo_rootx()
                ry = row.winfo_rooty()
                rw = row.winfo_width()
                rh = row.winfo_height()
                if rx <= event.x_root <= rx + rw and ry <= event.y_root <= ry + rh:
                    target_idx = i
                    target_pos = "above" if event.y_root < ry + rh // 2 else "below"
                    break
            except:
                pass

        self._drag_target_idx = target_idx
        self._drag_target_pos = target_pos

        # Solo redibujar la pill si el target cambió — evita trabajo innecesario
        current_target = (target_idx, target_pos)
        if current_target == self._drag_last_target:
            return
        self._drag_last_target = current_target

        if target_idx is not None and self._drag_indicator:
            try:
                target_row = rows[target_idx]
                rx  = target_row.winfo_rootx()
                rw  = target_row.winfo_width()
                iy  = (target_row.winfo_rooty() - 4
                       if target_pos == "above"
                       else target_row.winfo_rooty() + target_row.winfo_height() - 4)

                # Solo redibujar pill si el ancho cambió
                if rw != self._drag_pill_width:
                    self._drag_draw_pill(rw)
                    self._drag_pill_width = rw

                self._drag_indicator.geometry(f"{rw}x8+{rx}+{iy}")
                self._drag_indicator.deiconify()
                self._drag_indicator.lift()
            except:
                self._drag_indicator.withdraw()
        elif self._drag_indicator:
            try:
                self._drag_indicator.withdraw()
            except:
                pass

    def _drag_end(self, event):
        if not self._drag_active:
            return

        self.root.unbind("<B1-Motion>")
        self.root.unbind("<ButtonRelease-1>")
        self.root.configure(cursor="")

        target_idx  = self._drag_target_idx
        target_pos  = self._drag_target_pos
        source_idx  = self._drag_source_idx
        source_row  = self._drag_source_row
        drag_type   = self._drag_type

        self._drag_cleanup()
        self.root.update_idletasks()  # fuerza repintado después del drag

        if target_idx is None:
            # Cancelado — reset visual del row sin reconstruir toda la lista
            if source_row:
                try:
                    self._set_bg_recursive(source_row, CARD)
                except:
                    pass
            return

        # Calcula nuevo índice
        new_idx = target_idx + (1 if target_pos == "below" else 0)
        if source_idx < new_idx:
            new_idx -= 1

        if new_idx == source_idx:
            if source_row:
                try:
                    self._set_bg_recursive(source_row, CARD)
                except:
                    pass
            return

        # Reordena y guarda
        if drag_type == "link":
            item = self.links.pop(source_idx)
            self.links.insert(new_idx, item)
        else:
            item = self.profiles.pop(source_idx)
            self.profiles.insert(new_idx, item)

        self.save_links()
        self.refresh()

    def _drag_cleanup(self):
        self._drag_active      = False
        self._drag_type        = None
        self._drag_source_idx  = None
        self._drag_source_row  = None
        self._drag_target_idx  = None
        self._drag_target_pos  = None
        self._drag_ind_canvas  = None
        self._drag_last_target = None
        self._drag_ghost_w     = 0
        self._drag_ghost_h     = 0
        self._drag_pill_width  = 0

        for attr in ("_drag_ghost", "_drag_indicator"):
            w = getattr(self, attr, None)
            if w:
                try:
                    w.destroy()
                except:
                    pass
            setattr(self, attr, None)