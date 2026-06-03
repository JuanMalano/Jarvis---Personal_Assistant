import tkinter as tk
import customtkinter as ctk
import webbrowser
import winreg
import sys
import sounddevice as sd

from ui.theme import (
    BG, BG2, TITLEBAR, FG, CARD,
    ACCENT, ACCENT2, BTN, BTN_HOVER,
    CARD_BORDER, RED, GREEN, 
    GRIS_CLARO, GRIS_OSCURO
)

# =========================================================
# --- MIXIN DE EDITORES ---
# Contiene todas las ventanas emergentes de edición.
# Se separa de app.py para mantenerlo manejable.
# AppUI hereda de esta clase para tener estos métodos.
# =========================================================

class EditorsMixin:

    # =========================================================
    #                     EDITOR DE LINKS
    # =========================================================
    def open_link_editor(self, index=None, item_entries=None):
        import os
        from tkinter import filedialog
        from core.logic import AppLogic

        editing = index is not None
        item = self.links[index] if editing else {"name": "", "url": "", "type": "url", "claps": 1}

        win, content = self._make_window(420, 270, "Editar link")
        win.resizable(False, False)

        n_row = tk.Frame(content, bg=BG2)
        n_row.pack(anchor="w", padx=20, pady=(10, 5))

        tk.Label(
            n_row, text="➤ Nombre",
            font=("Consolas", 9), bg=BG2, fg=GRIS_OSCURO
        ).pack(side="left")

        self._help_icon(
            n_row,
            "Agrega un nombre personalizado.\n\n" \
            "👏¹ - Se abre con un solo aplauso\n" \
            "👏² . se abre con dos aplausos consecutivos",
            f_color=BG2
        ).pack(side="left", padx=(5, 0))

        name_row = tk.Frame(content, bg=BG2)
        name_row.pack(fill="x", padx=20)

        name_entry = ctk.CTkEntry(
            name_row, width=264, height=32, corner_radius=6,
            fg_color=BTN, border_color=CARD_BORDER,
            text_color=FG, font=("Consolas", 11)
        )
        name_entry.pack(side="left")
        name_entry.insert(0, item["name"])

        # ---- SELECTOR DE APLAUSOS ----
        clap_var = tk.IntVar(value=item.get("claps", 1))

        clap_frame = tk.Frame(name_row, bg=BG2)
        clap_frame.pack(side="left", padx=(10, 0))

        btn_clap1 = ctk.CTkButton(
            clap_frame, text="👏¹",
            font=("Segoe UI Emoji", 18),
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color=BG,
            width=50, height=32,
            corner_radius=5,
            command=lambda: select_clap(1)
        )
        btn_clap1.pack(side="left", padx=(0, 4))

        btn_clap2 = ctk.CTkButton(
            clap_frame, text="👏²",
            font=("Segoe UI Emoji", 18),
            fg_color=BTN, hover_color=BTN_HOVER,
            text_color=GRIS_OSCURO,
            width=50, height=32,
            corner_radius=5,
            command=lambda: select_clap(2)
        )
        btn_clap2.pack(side="left")

        def select_clap(n):
            clap_var.set(n)
            if n == 1:
                btn_clap1.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color=BG)
                btn_clap2.configure(fg_color=BTN,    hover_color=BTN_HOVER, text_color=GRIS_OSCURO)
            else:
                btn_clap1.configure(fg_color=BTN,    hover_color=BTN_HOVER, text_color=GRIS_OSCURO)
                btn_clap2.configure(fg_color=ACCENT,  hover_color=ACCENT2,  text_color=BG)

        select_clap(item.get("claps", 1))

        btn_clap1.bind("<Button-1>", lambda e: select_clap(1))
        btn_clap2.bind("<Button-1>", lambda e: select_clap(2))

        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(12, 0))
        
        p_row = tk.Frame(content, bg=BG2)
        p_row.pack(anchor="w", padx=20, pady=(10, 5))
        tk.Label(
            p_row, text="➤ URLs - Paths",
            font=("Consolas", 9), bg=BG2, fg=GRIS_OSCURO
        ).pack(side="left")

        self._help_icon(
            p_row,
            "Agregá URLs de internet o archivos locales, se abrirá en cuanto aplaudas.\n\n"
            "Dos formas de cargar archivos: click derecho + copiar como ruta de acceso, o buscarlos con 📁\n\n"
            "● Marrón: archivos\n● Celeste: URLs",
            f_color=BG2
        ).pack(side="left", padx=(5, 0))

        # Fila con campo de texto + botón examinar
        path_row = tk.Frame(content, bg=BG2)
        path_row.pack(fill="x", padx=20)

        path_entry = ctk.CTkEntry(
            path_row, width=340, height=32, corner_radius=6,
            fg_color=BTN, border_color=CARD_BORDER,
            text_color=FG, font=("Consolas", 11)
        )
        path_entry.pack(side="left")
        path_entry.insert(0, item["url"])

        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(12, 0))
        
        def update_path_color(known_type=None):
            # Si se pasa known_type (cargado del JSON), lo usa directamente
            # Si no, lo detecta desde el texto — solo en escritura manual o browse
            path = AppLogic.clean_path(path_entry.get().strip())
            if not path:
                path_entry.configure(text_color=FG)
                return
            type_ = known_type if known_type else AppLogic.detect_type(path)
            if type_ == "file":
                path_entry.configure(text_color="#b8936a")
            else:
                path_entry.configure(text_color="#6aafcc")

        # Al abrir usa el tipo guardado en el JSON — no re-detecta
        update_path_color(item.get("type"))

        path_entry.bind("<KeyRelease>", lambda e: update_path_color())

        def browse():
            win.grab_release()
            win.transient("")
            path = filedialog.askopenfilename(title="Seleccionar archivo")
            def restore():
                try:
                    if win.winfo_exists():
                        win.deiconify()
                        win.transient(self.root)
                        win.lift()
                        win.focus_force()
                        win.grab_set()
                except:
                    pass
            win.after(50, restore)
            if path:
                path_entry.delete(0, "end")
                path_entry.insert(0, path)
                update_path_color()
                check_changes()

        self._ctk_button(path_row, "📁", browse, width=100).pack(side="left", padx=(8, 0))

        status = tk.Label(content, text="", font=("Consolas", 8), bg=BG2, fg=RED)
        status.pack(pady=4)
        
        def test():
            path = path_entry.get().strip()

            if not path:
                status.config(text="- Campo vacío -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return

            type_ = AppLogic.detect_type(path)

            if type_ == "file":
                try:
                    os.startfile(path)
                except:
                    status.config(text=f"- No se pudo abrir: {path} -", fg=RED)
                    win.after(3000, lambda: status.config(text=""))
                    return
            else:
                if not path.startswith("http"):
                    path = "https://" + path
                webbrowser.open(path)

            status.config(text="- Abriendo -", fg=GREEN)
            win.after(3000, lambda: status.config(text=""))

        def save():
            name = name_entry.get().strip()
            path = path_entry.get().strip()
            if not name or not path:
                status.config(text="- Campos vacíos -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return
            # Detecta el tipo y corrige la URL si es necesario
            path  = AppLogic.clean_path(path)
            type_ = AppLogic.detect_type(path)
            if type_ == "url" and not path.startswith("http"):
                path = "https://" + path
            d = {"name": name, "url": path, "type": type_, "claps": clap_var.get()}
            if editing:
                self.links[index] = d
            else:
                self.links.append(d)
            self.save_links()
            self.refresh()
            win.destroy()

        # Valores originales para detectar si hubo cambios
        original_name = item["name"]
        original_path = item["url"]

        frame = tk.Frame(content, bg=BG2)
        frame.pack(pady=(0, 0))
        win.bind("<Return>", lambda e: save())
        win.bind("<Escape>", lambda e: win.destroy())

        self._ctk_button(frame, "Probar", test, width=90).pack(side="left", padx=4)
        save_btn = self._ctk_button(frame, "Guardar", None, width=90, accent=False)
        save_btn.pack(side="left", padx=4)
        self._ctk_button(frame, "Cancelar", win.destroy, width=90).pack(side="left", padx=4)

        def check_changes(*args):
            name = name_entry.get().strip()
            path = path_entry.get().strip()
            if editing:
                changed = name != original_name or path != original_path
            else:
                changed = bool(name) or bool(path)
            if changed:
                save_btn.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color="#000000")
            else:
                save_btn.configure(fg_color=BTN, hover_color=BTN_HOVER, text_color=FG)

        name_entry.bind("<KeyRelease>", check_changes)
        path_entry.bind("<KeyRelease>", check_changes)
        save_btn.configure(command=save)

    # =========================================================
    #                     EDITOR DE PERFILES
    # =========================================================
    def open_profile_editor(self, index=None):
        import os
        from tkinter import filedialog
        from core.logic import AppLogic

        editing      = index is not None
        self.editing = True

        # Carga el perfil existente o crea uno vacío
        # Soporta el formato viejo (urls: lista de strings)
        # y el nuevo (items: lista de dicts con path y type)
        if editing:
            raw = self.profiles[index]
            if "items" in raw:
                existing_items = raw["items"]
            else:
                # Migración del formato viejo al nuevo
                existing_items = [{"path": u, "type": "url"} for u in raw.get("urls", [])]
            item = {"name": raw["name"], "hotkey": raw.get("hotkey", ""), "items": existing_items}
        else:
            item = {"name": "", "hotkey": "", "items": []}

        win, content = self._make_window(460, 500, "Editar perfil")
        win.resizable(False, False)

        # ---- NOMBRE ----
        tk.Label(content, text="➤ Nombre", font=("Consolas", 9), bg=BG2, fg=GRIS_OSCURO).pack(anchor="w", padx=20, pady=(16, 2))
        name_entry = ctk.CTkEntry(
            content, width=255, height=32, corner_radius=6,
            fg_color=BTN, border_color=CARD_BORDER,
            text_color=FG, font=("Consolas", 11)
        )
        name_entry.pack(padx=20, anchor="w")
        name_entry.insert(0, item["name"])
        
        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(12, 0))
        # ---- HOTKEY ----
        h_row = tk.Frame(content, bg=BG2)
        h_row.pack(anchor="w", padx=20, pady=(10, 2))

        tk.Label(
            h_row,
            text="➤ Hotkey",
            font=("Consolas", 9),
            bg=BG2,
            fg=GRIS_OSCURO
        ).pack(side="left")

        self._help_icon(
            h_row,
            "Asigná una hotkey para activar el perfil desde cualquier lado mientras la app esté en uso.\n\nEjemplos: Ctrl+Alt+P, Shift+F2, ctrl+1, etc.", f_color=BG2
        ).pack(side="left", padx=(5, 0))

        hotkey_var = tk.StringVar(value=item.get("hotkey", ""))
        hotkey_row = tk.Frame(content, bg=BG2)
        hotkey_row.pack(fill="x", padx=20)

        tk.Label(
            hotkey_row, textvariable=hotkey_var,
            font=("Consolas", 10), bg=BTN, fg=ACCENT,
            width=18, anchor="w", padx=8, pady=6
        ).pack(side="left")

        self._ctk_button(
            hotkey_row, "Capturar",
            lambda: self.capture_hotkey(hotkey_var), width=100
        ).pack(side="left", padx=8)

        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(12, 0))
        # ---- LISTA DE ITEMS ----
        h_row = tk.Frame(content, bg=BG2)
        h_row.pack(anchor="w", padx=20, pady=(10, 2))

        tk.Label(
            h_row,
            text="➤ URLs y Paths",
            font=("Consolas", 9),
            bg=BG2,
            fg=GRIS_OSCURO
        ).pack(side="left")

        self._help_icon(
            h_row,
            "Agregá URLs de internet o archivos locales, estos se abrirán juntos cuando actives este perfil.\n\nEl primer paso es \"+ agregar\", luego copiar y pegar las direcciones que deseas agregar." \
            "\n\nHay dos formas de interactuar con los archivos:\n- Hacer click derecho sobre los archivos/carpetas y \"copiar como ruta de acceso\"\n- Buscarlos desde 📁\n\n" \
            "● Marrón: archivos\n● Celeste: URLs", f_color=BG2
        ).pack(side="left", padx=(5, 0))


        # Wrapper con padding para el scrollable frame
        items_section = tk.Frame(content, bg=BG2)
        items_section.pack(fill="x", padx=20)

        # Reutiliza _scrollable_frame con bg=BTN para que coincida con el editor
        # La lógica de scroll, detección por posición del mouse y chequeo de
        # contenido vs altura visible ya están resueltos en WidgetsMixin
        items_inner = self._scrollable_frame(items_section, height=150, bg=BTN, event_widget=win)

        item_entries = []

        def repack_all():
            # Desempaqueta y reempaqueta todos los rows en el orden actual
            for ie in item_entries:
                ie["row"].pack_forget()
            for ie in item_entries:
                ie["row"].pack(fill="x", padx=6, pady=(2, 2))

        def move_up(ref):
            idx = item_entries.index(ref)
            if idx == 0:
                return
            item_entries[idx], item_entries[idx - 1] = item_entries[idx - 1], item_entries[idx]
            repack_all()

        def move_down(ref):
            idx = item_entries.index(ref)
            if idx == len(item_entries) - 1:
                return
            item_entries[idx], item_entries[idx + 1] = item_entries[idx + 1], item_entries[idx]
            repack_all()

        def update_entry_color(entry, known_type=None):
            path = AppLogic.clean_path(entry.get().strip())
            if not path:
                entry.configure(text_color=FG)
                return
            type_ = known_type if known_type else AppLogic.detect_type(path)
            if type_ == "file":
                entry.configure(text_color="#b8936a")
            else:
                entry.configure(text_color="#6aafcc")

        def add_item_row(path="", known_type=None):
            row = tk.Frame(items_inner, bg=BTN, pady=3)
            row.pack(fill="x", padx=6)
            
            ref = {"row": row, "entry": None}
            item_entries.append(ref)

            # ---- Flechas de orden ----
            arrows = tk.Frame(row, bg=BTN)
            arrows.pack(side="left", padx=(0, 4))

            up_btn = tk.Label(arrows, text="↑", font=("Consolas", 9),
                              bg=BTN, fg="#555e6e", cursor="hand2")
            up_btn.pack()
            up_btn.bind("<Enter>",    lambda e: up_btn.config(fg=ACCENT))
            up_btn.bind("<Leave>",    lambda e: up_btn.config(fg="#555e6e"))
            up_btn.bind("<Button-1>", lambda e: move_up(ref))

            down_btn = tk.Label(arrows, text="↓", font=("Consolas", 9),
                                bg=BTN, fg="#555e6e", cursor="hand2")
            down_btn.pack()
            down_btn.bind("<Enter>",    lambda e: down_btn.config(fg=ACCENT))
            down_btn.bind("<Leave>",    lambda e: down_btn.config(fg="#555e6e"))
            down_btn.bind("<Button-1>", lambda e: move_down(ref))

            # ---- Campo de texto ----
            entry = ctk.CTkEntry(
                row, width=310, height=28, corner_radius=6,
                fg_color=CARD, border_color=CARD_BORDER,
                text_color=FG, font=("Consolas", 10)
            )
            entry.pack(side="left")
            ref["entry"] = entry

            if path:
                entry.insert(0, path)
                update_entry_color(entry, known_type=known_type)

            # Actualiza el color mientras el usuario escribe
            entry.bind("<KeyRelease>", lambda e, en=entry: [
                items_touched.__setitem__(0, True),
                update_entry_color(en),
                check_changes()
            ])
            
            def browse(e=entry):
                win.grab_release()
                win.transient("")
                p = filedialog.askopenfilename(title="Seleccionar archivo")
                def restore():
                    try:
                        if win.winfo_exists():
                            win.deiconify()
                            win.transient(self.root)
                            win.lift()
                            win.focus_force()
                            win.grab_set()
                    except:
                        pass
                win.after(50, restore)
                if p:
                    e.delete(0, "end")
                    e.insert(0, p)
                    update_entry_color(e)


            self._ctk_button(row, "📁", browse, width=36).pack(side="left", padx=(4, 0))

            def remove(r=row, t=ref):
                if t in item_entries:
                    item_entries.remove(t)
                r.destroy()
                items_touched[0] = True
                check_changes()

            del_btn = tk.Label(row, text="🗑", font=("Segoe UI Emoji", 9),
                               bg=BTN, fg="#555e6e", cursor="hand2")
            del_btn.pack(side="left", padx=(6, 0))
            del_btn.bind("<Enter>",    lambda e: del_btn.config(fg=RED))
            del_btn.bind("<Leave>",    lambda e: del_btn.config(fg="#555e6e"))
            del_btn.bind("<Button-1>", lambda e: remove())

        for it in item["items"]:
            add_item_row(it["path"], it.get("type"))

        # Botón + agregar fuera del scroll, siempre visible
        add_row_btn = tk.Label(
            content, text="+ agregar",
            font=("Consolas", 9), bg=BG2, fg="#555e6e", cursor="hand2"
        )
        add_row_btn.pack(anchor="w", padx=20, pady=(4, 0))
        add_row_btn.bind("<Enter>",    lambda e: add_row_btn.config(fg=ACCENT))
        add_row_btn.bind("<Leave>",    lambda e: add_row_btn.config(fg="#555e6e"))
        add_row_btn.bind("<Button-1>", lambda e: add_item_row())

        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(10, 0))

        status = tk.Label(content, text="", font=("Consolas", 8), bg=BG2, fg=RED)
        status.pack(pady=6)

        def test():
            # Abre todos los items para probarlos antes de guardar
            entries = [
                ie["entry"].get().strip()
                for ie in item_entries
                if ie["entry"].get().strip()
            ]
            if not entries:
                status.config(text="- Sin items -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return
            for path in entries:
                type_ = AppLogic.detect_type(path)
                if type_ == "file":
                    try:
                        os.startfile(path)
                    except:
                        status.config(text=f"- No se pudo abrir: {path} -", fg=RED)
                        win.after(3000, lambda: status.config(text=""))
                        return
                else:
                    if not path.startswith("http"):
                        path = "https://" + path
                    webbrowser.open(path)
            status.config(text="- Abriendo Perfil -", fg=GREEN)
            win.after(3000, lambda: status.config(text=""))

        def save():
            name_val = name_entry.get().strip()
            if not name_val:
                status.config(text="- Nombre vacío -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return
            if not hotkey_var.get().strip():
                status.config(text="- Asigná una hotkey al perfil -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return

            items = []
            for ie in item_entries:
                path = ie["entry"].get().strip()
                if not path:
                    continue
                path  = AppLogic.clean_path(path)
                type_ = AppLogic.detect_type(path)
                if type_ == "url" and not path.startswith("http"):
                    path = "https://" + path
                items.append({"path": path, "type": type_})

            if not items:
                status.config(text="- Agregá al menos un item -", fg=RED)
                win.after(3000, lambda: status.config(text=""))
                return

            d = {"name": name_val, "hotkey": hotkey_var.get(), "items": items}
            if editing:
                self.profiles[index] = d
            else:
                self.profiles.append(d)
            self.editing = False
            self.save_links()
            self.refresh()
            win.destroy()

        # Valores originales para detectar cambios
        original_name   = item["name"]
        original_hotkey = item.get("hotkey", "")
        # Lista mutable para que las funciones internas puedan modificarla
        items_touched = [False]

        frame = tk.Frame(content, bg=BG2)
        frame.pack(pady=(0, 0))
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>", lambda e: save())

        self._ctk_button(frame, "Probar", test, width=90).pack(side="left", padx=4)
        save_btn = self._ctk_button(frame, "Guardar", None, width=90, accent=False)
        save_btn.pack(side="left", padx=4)
        self._ctk_button(frame, "Cancelar", win.destroy, width=90).pack(side="left", padx=4)

        def check_changes(*args):
            name   = name_entry.get().strip()
            hotkey = hotkey_var.get()
            if editing:
                changed = (name != original_name or
                           hotkey != original_hotkey or
                           items_touched[0])
            else:
                # Al agregar: habilitar si hay nombre o items
                changed = bool(name) or items_touched[0]
            if changed:
                save_btn.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color="#000000")
            else:
                save_btn.configure(fg_color=BTN, hover_color=BTN_HOVER, text_color=FG)

        name_entry.bind("<KeyRelease>", lambda e: [items_touched.__setitem__(0, True), check_changes()])
        # Detecta cambios en la hotkey capturada
        hotkey_var.trace_add("write", check_changes)
        save_btn.configure(command=save)
        
    # =========================================================
    #                        AJUSTES
    # =========================================================
    def open_settings(self):
        DEFAULT_SENSITIVITY = 0.5
        REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "Jarvis"

        # Lee el registro de Windows para saber si está activado el inicio automático
        def get_startup_state():
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
                winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return True
            except:
                return False

        # Escribe o borra la entrada en el registro de Windows
        # Esto hace que el .exe arranque automáticamente con Windows si está activado
        def set_startup(enable):
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
                if enable:
                    exe = sys.executable
                    # --tray hace que arranque minimizado en la bandeja
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}" --tray')
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except:
                        pass
                winreg.CloseKey(key)
            except Exception as ex:
                print(f"Error registro: {ex}")

        win, content = self._make_window(400, 390, "Ajustes")

        # ---- GENERAL ----
        tk.Label(content, text="General",
                 font=("Consolas", 9, "bold"), bg=BG2, fg=FG).pack(anchor="w", padx=20, pady=(14, 6))

        # Toggle: iniciar con Windows
        startup_row = tk.Frame(content, bg=BG2)
        startup_row.pack(fill="x", padx=24, pady=(0, 6))

        startup_var = tk.BooleanVar(value=get_startup_state())

        ctk.CTkSwitch(
            startup_row, text="",
            variable=startup_var,
            width=36, height=18,
            switch_width=36, switch_height=18,
            progress_color=ACCENT,
            button_color="#ffffff",
            button_hover_color="#dddddd"
        ).pack(side="left", padx=(0, 8))

        tk.Label(startup_row, text="Iniciar con Windows",
                 font=("Consolas", 10), bg=BG2, fg=FG).pack(side="left")
        
        self._help_icon(
            startup_row,
            "Si está activo, al iniciar la pc el programa se ejecutará de fondo y se minimizara automaticamente en la bandeja.", f_color=BG2
        ).pack(side="left", padx=(5, 0))
        
        # Toggle: minimizar a la bandeja
        tray_row = tk.Frame(content, bg=BG2)
        tray_row.pack(fill="x", padx=24, pady=(0, 6))

        minimize_tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", False))

        ctk.CTkSwitch(
            tray_row, text="",
            variable=minimize_tray_var,
            width=36, height=18,
            switch_width=36, switch_height=18,
            progress_color=ACCENT,
            button_color="#ffffff",
            button_hover_color="#dddddd"
        ).pack(side="left", padx=(0, 8))

        tk.Label(tray_row, text="Minimizar en bandeja",
        font=("Consolas", 10), bg=BG2, fg=FG).pack(side="left")

        self._help_icon(
            tray_row,
            "Si está activo, al minimizar la app, no aparecerá el icono en la barra de tareas y solamente lo hará en la bandeja.", f_color=BG2
        ).pack(side="left", padx=(5, 0))
        
        # ---- AUDIO ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(12, 0))

        tk.Label(content, text="Audio",
                 font=("Consolas", 9, "bold"), bg=BG2, fg=FG).pack(anchor="w", padx=20, pady=(10, 6))

        # --- Selector de micrófono ---
        mic_row = tk.Frame(content, bg=BG2)
        mic_row.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(mic_row, text="Micrófono",
                 font=("Consolas", 9), bg=BG2, fg="#888").pack(side="left", padx=(0, 8))

        # Palabras clave para filtrar dispositivos virtuales o irrelevantes
        VIRTUAL_KEYWORDS = [
            "virtual", "cable", "voicemeeter", "vb-audio",
            "mix", "loopback", "wasapi", "output", "stereo mix"
        ]

        devices    = sd.query_devices()

        # Obtiene el nombre del dispositivo por defecto del sistema
        try:
            default_dev_idx  = sd.default.device[0]
            default_dev_name = devices[default_dev_idx]["name"]
        except:
            default_dev_name = "desconocido"

        # Obtiene dispositivos de entrada reales, descartando virtuales
        # y el dispositivo por defecto (ya aparece como primera opción)
        input_devs = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                name_lower = d["name"].lower()
                if any(kw in name_lower for kw in VIRTUAL_KEYWORDS):
                    continue
                # Evita duplicar el dispositivo por defecto en la lista
                if d["name"] == default_dev_name:
                    continue
                input_devs.append((i, d["name"]))

        input_devs = input_devs[:5]

        # Primera opción muestra el nombre del dispositivo por defecto entre guiones
        dev_names   = [f"Por defecto  —  {default_dev_name}"] + [name for _, name in input_devs]
        dev_indices = [None] + [i for i, _ in input_devs]

        current_device = self.settings.get("mic_device", None)
        try:
            current_idx = dev_indices.index(current_device)
        except ValueError:
            current_idx = 0

        mic_var = tk.StringVar(value=dev_names[current_idx])

        ctk.CTkOptionMenu(
            mic_row,
            values=dev_names,
            variable=mic_var,
            width=260,
            fg_color=BTN,
            button_color=ACCENT2,
            button_hover_color=ACCENT,
            text_color=FG,
            font=("Consolas", 10)
        ).pack(side="left")

        # --- SENSIBILIDAD DEL MICRÓFONO ---

        h_row = tk.Frame(content, bg=BG2)
        h_row.pack(anchor="w", padx=22.5, pady=(10, 2))

        tk.Label(
            h_row,
            text="Sensibilidad del micrófono",
            font=("Consolas", 9),
            bg=BG2,
            fg=GRIS_OSCURO
        ).pack(side="left")

        self._help_icon(
            h_row,
            "Ajusta la sensibilidad del micrófono para detectar aplausos o chasquidos más o menos fácilmente.\n\nIMPORTANTE: A mayor valor, más fácil se detectarán los sonidos.", f_color=BG2
        ).pack(side="left", padx=(5, 0))
        
        slider_row = tk.Frame(content, bg=BG2)
        slider_row.pack(fill="x", padx=24)

        # Valor REAL interno (0.0 → 2.0)
        real_sens = self.settings.get("sensitivity", DEFAULT_SENSITIVITY)

        # Convertir a porcentaje visual
        initial_percent = max(1, int((real_sens / 2.0) * 100))

        sens_var = tk.IntVar(value=initial_percent)

        val_label = tk.Label(
            slider_row,
            text=f"{sens_var.get()}%",
            font=("Consolas", 10),
            highlightthickness=3,
            highlightbackground=BTN,
            bg=CARD_BORDER,
            fg=ACCENT,
            width=5
        )
        val_label.pack(side="right")

        def percent_to_real(percent):
            return round((percent / 100) * 2.0, 2)

        def real_to_percent(real):
            return max(1, int((real / 2.0) * 100))

        def on_slider(val):
            val_label.config(text=f"{int(float(val))}%")

        ctk.CTkSlider(
            slider_row,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=sens_var,
            command=on_slider,
            width=300,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT2
        ).pack(side="left")

        status = tk.Label(content, text="", font=("Consolas", 8), bg=BG2, fg=GREEN)
        status.pack(pady=(2, 0))

        # ---- SEPARADOR ----
        tk.Frame(content, bg=CARD_BORDER, height=1).pack(fill="x", padx=20, pady=(0, 0))

        # ---- BOTONES ----
        btn_frame = tk.Frame(content, bg=BG2)
        btn_frame.pack(pady=(2, 0))

        # Valores originales al abrir ajustes — para detectar si hubo cambios
        original_startup = get_startup_state()
        original_minimize_tray = self.settings.get("minimize_to_tray", False)
        original_sens    = self.settings.get("sensitivity", DEFAULT_SENSITIVITY)
        original_device  = self.settings.get("mic_device", None)

        status = tk.Label(content, text="", font=("Consolas", 8), bg=BG2, fg=GREEN)
        status.pack(pady=(4, 0))

        btn_frame = tk.Frame(content, bg=BG2)
        btn_frame.pack(pady=(2, 0))

        def restore():
            sens_var.set(real_to_percent(DEFAULT_SENSITIVITY))
            val_label.config(text=f"{real_to_percent(DEFAULT_SENSITIVITY)}%")
            status.config(text="Restaurado al valor original", fg=ACCENT)
            check_changes()

        save_btn = self._ctk_button(btn_frame, "Guardar", None, width=100, accent=False)
        save_btn.pack(side="left", padx=4)
        self._ctk_button(btn_frame, "Cancelar", win.destroy, width=100).pack(side="left", padx=4)

        def check_changes(*args):
            current_real_sens   = percent_to_real(sens_var.get())
            sens_changed        = round(current_real_sens, 2) != round(original_sens, 2)
            startup_changed     = startup_var.get() != original_startup
            selected_device     = dev_indices[dev_names.index(mic_var.get())]
            device_changed      = selected_device != original_device
            tray_changed        = minimize_tray_var.get() != original_minimize_tray

            if sens_changed or startup_changed or device_changed or tray_changed:
                save_btn.configure(fg_color=ACCENT, hover_color=ACCENT2, text_color="#000000")
            else:
                save_btn.configure(fg_color=BTN, hover_color=BTN_HOVER, text_color=FG)

        # Escucha cambios en las cuatro variables
        sens_var.trace_add("write",    check_changes)
        startup_var.trace_add("write", check_changes)
        minimize_tray_var.trace_add("write", check_changes)
        mic_var.trace_add("write",     check_changes)

        def save():
            set_startup(startup_var.get())
            new_sens        = percent_to_real(sens_var.get())
            selected_device = dev_indices[dev_names.index(mic_var.get())]

            if self.save_settings:
                self.save_settings({
                    "sensitivity":      new_sens,
                    "mic_device":       selected_device,
                    "minimize_to_tray": minimize_tray_var.get(),
                    "windows_startup": startup_var.get()
                })

            status.config(text="- Guardado -", fg=GREEN)
            win.after(900, win.destroy)

        save_btn.configure(command=save)

        restore_btn = tk.Label(
            content, text="↺ restaurar valores",
            font=("Consolas", 8, "bold"), bg=BG2, fg="#444e5e", cursor="hand2"
        )
        restore_btn.pack(anchor="sw", padx=12, pady=(10, 10))
        restore_btn.bind("<Enter>",    lambda e: restore_btn.config(fg=ACCENT))
        restore_btn.bind("<Leave>",    lambda e: restore_btn.config(fg="#444e5e"))
        restore_btn.bind("<Button-1>", lambda e: restore())

    # =========================================================
    #                     CAPTURA DE HOTKEY
    # =========================================================
    def capture_hotkey(self, var):
        import keyboard
        keyboard.unhook_all()
        capture = []

        # Quita el foco de cualquier entry activo antes de capturar
        # Evita que las teclas presionadas se escriban en el campo de texto
        self.root.focus_set()

        def on_press(event):
            key = normalize_key(event.name).lower()

            if key not in capture:
                capture.append(key)
            var.set("+".join(capture))

        def on_release(event):
            keyboard.unhook_all()

        def normalize_key(key):
            key = key.lower()
            return KEY_ALIASES.get(key, key.upper())

        keyboard.hook(on_press)
        keyboard.on_release(on_release)

        KEY_ALIASES = {
            "left shift": "Shift",
            "right shift": "Shift",
            "shift": "Shift",
            "mayus": "Shift",
            "mayúsculas": "Shift",
            "mayusculas": "Shift",

            "left ctrl": "Ctrl",
            "right ctrl": "Ctrl",
            "ctrl": "Ctrl",
            "control": "Ctrl",

            "left alt": "Alt",
            "right alt": "Alt",
            "alt gr": "AltGr",

            "caps lock": "Caps",
            "backspace": "Back",
            "escape": "Esc",
            "enter": "Enter",
            "windows": "Win",

            "!": "1",
            "@": "2",
            "#": "3",
            "$": "4",
            "%": "5",
            "^": "6",
            "&": "7",
            "*": "8",
            "(": "9",
            ")": "0",
        }
        