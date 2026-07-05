"""
Tastatur-Autoclicker PRO
========================
Professionelle Desktop-App mit modernem, abgerundetem UI (CustomTkinter),
Presets, frei waehlbarer Rate, Dark/Light-Mode und Startverzoegerung +
Auto-Minimieren, damit die Tastendruecke garantiert im zuletzt aktiven
Fenster/Tab ankommen.

WICHTIG ZUM VERSTAENDNIS:
Die 'keyboard'-Bibliothek erzeugt echte, systemweite Tastatur-Events
(genau wie ein physischer Tastendruck). Diese gehen automatisch an das
Fenster, das gerade den Fokus hat - unabhaengig davon, ob diese App
sichtbar ist. Die Startverzoegerung + Auto-Minimieren-Funktion sorgen
nur dafuer, dass du bequem Zeit hast, zum Zielfenster zu wechseln,
bevor die Eingaben losgehen.

Installation:
    pip install customtkinter keyboard

Start:
    Windows : als Administrator ausfuehren  ->  python autoclicker_pro.py
    Linux   : sudo python3 autoclicker_pro.py
    macOS   : Terminal unter "Bedienungshilfen" freigeben

Falls du eine eigene Datei "keyboard.py" oder "customtkinter.py" im
selben Ordner hast, benenne sie um - sonst importiert Python die
falsche Datei statt der echten Bibliothek.
"""

import customtkinter as ctk
from tkinter import messagebox
import keyboard
import threading
import time
import json
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autoclicker_presets.json")
QUICK_RATES = [1, 5, 10, 20, 50, 100]
QUICK_DELAYS = [0, 1, 3, 5]

CORNER = 16          # einheitlicher Radius fuer Karten
CORNER_SMALL = 10    # fuer Buttons/Eingabefelder

# ---------------- Globaler Zustand ----------------
active = False
keys = ["space"]
base_interval = 0.1
press_count = 0
start_time = None            # Zeitpunkt, an dem der Button gedrueckt wurde
activation_time = None       # Zeitpunkt, ab dem tatsaechlich gedrueckt wird (nach Delay)
start_delay = 0.0
current_hotkey = "f6"
quit_hotkey = "f9"
quit_requested = False
minimize_requested = False
auto_minimize = True


def clicker_loop():
    global press_count
    while True:
        if active and activation_time and time.time() >= activation_time:
            for k in keys:
                keyboard.press_and_release(k)
            press_count += 1
            time.sleep(base_interval)
        else:
            time.sleep(0.03)


def toggle_active():
    global active, start_time, activation_time, press_count, minimize_requested
    active = not active
    if active:
        start_time = time.time()
        activation_time = start_time + start_delay
        press_count = 0
        if auto_minimize:
            minimize_requested = True
    else:
        start_time = None
        activation_time = None


def request_quit():
    global quit_requested
    quit_requested = True


# ---------------- Presets ----------------
def load_presets():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_presets(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Fehler", f"Presets konnten nicht gespeichert werden:\n{e}")


# ---------------- GUI ----------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tastatur-Autoclicker PRO")
        self.geometry("500x720")
        self.resizable(False, False)

        self.presets = load_presets()

        self._build_header()
        self._build_tabs()
        self._register_hotkeys()

        self.after(150, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Header ----------
    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#e9ecf3", "#161824"))
        header.pack(fill="x")

        title = ctk.CTkLabel(header, text="⌨  Mads Tastatur-Autoclicker V1",
                              font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(side="left", padx=22, pady=20)

        # Sauberes Segment-"Dropdown" statt klassischem OptionMenu
        self.appearance_switch = ctk.CTkSegmentedButton(
            header, values=["🌙 Dunkel", "☀ Hell"],
            command=self._on_appearance_change, corner_radius=CORNER_SMALL
        )
        self.appearance_switch.set("🌙 Dunkel")
        self.appearance_switch.pack(side="right", padx=18)

        status_box = ctk.CTkFrame(header, fg_color="transparent")
        status_box.pack(side="right", padx=(0, 10))
        self.status_dot = ctk.CTkLabel(status_box, text="●", font=ctk.CTkFont(size=18),
                                        text_color="#e74c3c")
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_text = ctk.CTkLabel(status_box, text="Gestoppt", font=ctk.CTkFont(size=13))
        self.status_text.pack(side="left")

    def _on_appearance_change(self, choice):
        ctk.set_appearance_mode("dark" if "Dunkel" in choice else "light")

    # ---------- Tabs ----------
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, width=480, height=640, corner_radius=CORNER)
        self.tabs.pack(padx=12, pady=12, fill="both", expand=True)

        self.tabs.add("Steuerung")
        self.tabs.add("Presets")
        self.tabs.add("Info")

        self._build_control_tab(self.tabs.tab("Steuerung"))
        self._build_presets_tab(self.tabs.tab("Presets"))
        self._build_info_tab(self.tabs.tab("Info"))

    # ---------- Tab: Steuerung ----------
    def _build_control_tab(self, tab):
        card = ctk.CTkFrame(tab, corner_radius=CORNER)
        card.pack(fill="x", padx=8, pady=(10, 10))

        ctk.CTkLabel(card, text="Taste(n), kommagetrennt", anchor="w").pack(fill="x", padx=18, pady=(18, 3))
        self.keys_entry = ctk.CTkEntry(card, placeholder_text="z.B. space  oder  w,a,s,d",
                                        corner_radius=CORNER_SMALL, height=36)
        self.keys_entry.insert(0, ",".join(keys))
        self.keys_entry.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(card, text="Anschlaege pro Sekunde", anchor="w").pack(fill="x", padx=18, pady=(0, 3))

        quick_row = ctk.CTkFrame(card, fg_color="transparent")
        quick_row.pack(fill="x", padx=18, pady=(0, 8))
        for rate in QUICK_RATES:
            ctk.CTkButton(quick_row, text=f"{rate}/s", width=62, corner_radius=CORNER_SMALL,
                          command=lambda r=rate: self._set_rate(r)).pack(side="left", padx=(0, 6))

        custom_row = ctk.CTkFrame(card, fg_color="transparent")
        custom_row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkLabel(custom_row, text="Eigener Wert:").pack(side="left", padx=(0, 8))
        self.rate_entry = ctk.CTkEntry(custom_row, width=100, placeholder_text="z.B. 250",
                                        corner_radius=CORNER_SMALL, height=32)
        self.rate_entry.insert(0, str(1 / base_interval))
        self.rate_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(custom_row, text="Setzen", width=80, corner_radius=CORNER_SMALL,
                      command=self._set_custom_rate).pack(side="left")
        self.rate_current_label = ctk.CTkLabel(custom_row, text=f"Aktuell: {1/base_interval:.0f}/s",
                                                 font=ctk.CTkFont(size=12))
        self.rate_current_label.pack(side="left", padx=(15, 0))

        # Startverzoegerung
        ctk.CTkLabel(card, text="Startverzoegerung (Sekunden)", anchor="w").pack(fill="x", padx=18, pady=(0, 3))
        delay_row = ctk.CTkFrame(card, fg_color="transparent")
        delay_row.pack(fill="x", padx=18, pady=(0, 8))
        for d in QUICK_DELAYS:
            ctk.CTkButton(delay_row, text=f"{d}s", width=50, corner_radius=CORNER_SMALL,
                          command=lambda dd=d: self._set_delay(dd)).pack(side="left", padx=(0, 6))
        self.delay_label = ctk.CTkLabel(delay_row, text="Aktuell: 0s", font=ctk.CTkFont(size=12))
        self.delay_label.pack(side="left", padx=(15, 0))

        self.auto_min_switch = ctk.CTkSwitch(card, text="Fenster beim Start automatisch minimieren",
                                              command=self._on_auto_min_toggle)
        self.auto_min_switch.select()
        self.auto_min_switch.pack(anchor="w", padx=18, pady=(4, 16))

        # Hotkeys
        hk_row = ctk.CTkFrame(card, fg_color="transparent")
        hk_row.pack(fill="x", padx=18, pady=(0, 18))

        col1 = ctk.CTkFrame(hk_row, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(col1, text="Start/Stop-Hotkey", anchor="w").pack(fill="x")
        self.hotkey_entry = ctk.CTkEntry(col1, corner_radius=CORNER_SMALL, height=32)
        self.hotkey_entry.insert(0, current_hotkey)
        self.hotkey_entry.pack(fill="x", pady=(2, 0))

        col2 = ctk.CTkFrame(hk_row, fg_color="transparent")
        col2.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(col2, text="Beenden-Hotkey", anchor="w").pack(fill="x")
        self.quit_entry = ctk.CTkEntry(col2, corner_radius=CORNER_SMALL, height=32)
        self.quit_entry.insert(0, quit_hotkey)
        self.quit_entry.pack(fill="x", pady=(2, 0))

        ctk.CTkButton(card, text="Einstellungen Übernehmen", corner_radius=CORNER_SMALL,
                      command=self._apply_settings).pack(fill="x", padx=18, pady=(0, 18))

        self.toggle_btn = ctk.CTkButton(tab, text="▶   STARTEN", height=56, corner_radius=CORNER,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         fg_color="#2ecc71", hover_color="#27ae60",
                                         command=toggle_active)
        self.toggle_btn.pack(fill="x", padx=8, pady=(0, 10))

        stats = ctk.CTkFrame(tab, corner_radius=CORNER)
        stats.pack(fill="x", padx=8, pady=(0, 10))

        self.count_label = ctk.CTkLabel(stats, text="Tastendruecke: 0", font=ctk.CTkFont(size=13))
        self.count_label.pack(side="left", padx=18, pady=14)

        self.time_label = ctk.CTkLabel(stats, text="Laufzeit: 00:00", font=ctk.CTkFont(size=13))
        self.time_label.pack(side="right", padx=18, pady=14)

    def _set_rate(self, rate):
        self.rate_entry.delete(0, "end")
        self.rate_entry.insert(0, str(rate))
        self._set_custom_rate()

    def _set_custom_rate(self):
        global base_interval
        try:
            rate = float(self.rate_entry.get())
            if rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gueltige Zahl groesser 0 eingeben.")
            return
        base_interval = 1.0 / rate
        self.rate_current_label.configure(text=f"Aktuell: {rate:.0f}/s")

    def _set_delay(self, d):
        global start_delay
        start_delay = float(d)
        self.delay_label.configure(text=f"Aktuell: {d}s")

    def _on_auto_min_toggle(self):
        global auto_minimize
        auto_minimize = bool(self.auto_min_switch.get())

    # ---------- Tab: Presets ----------
    def _build_presets_tab(self, tab):
        ctk.CTkLabel(tab, text="Aktuelle Einstellungen als Preset speichern:",
                     anchor="w").pack(fill="x", padx=18, pady=(18, 6))

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        self.preset_name_entry = ctk.CTkEntry(row, placeholder_text="Preset-Name, z.B. 'Minecraft Farmen'",
                                               corner_radius=CORNER_SMALL, height=34)
        self.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(row, text="Speichern", width=100, corner_radius=CORNER_SMALL,
                      command=self._save_preset).pack(side="left")

        ctk.CTkLabel(tab, text="Gespeicherte Presets:", anchor="w").pack(fill="x", padx=18, pady=(6, 6))

        self.preset_list_frame = ctk.CTkScrollableFrame(tab, height=420, corner_radius=CORNER)
        self.preset_list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self._refresh_preset_list()

    def _refresh_preset_list(self):
        for widget in self.preset_list_frame.winfo_children():
            widget.destroy()

        if not self.presets:
            ctk.CTkLabel(self.preset_list_frame, text="Noch keine Presets gespeichert.").pack(pady=10)
            return

        for name, cfg in self.presets.items():
            row = ctk.CTkFrame(self.preset_list_frame, corner_radius=CORNER_SMALL)
            row.pack(fill="x", pady=5, padx=4)

            info = f"{name}  —  Tasten: {','.join(cfg['keys'])}  |  {cfg['rate']}/s  |  Hotkey: {cfg['hotkey']}"
            ctk.CTkLabel(row, text=info, anchor="w", wraplength=270).pack(side="left", padx=12, pady=10, fill="x", expand=True)

            ctk.CTkButton(row, text="Laden", width=60, corner_radius=CORNER_SMALL,
                          command=lambda n=name: self._load_preset(n)).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Löschen", width=70, corner_radius=CORNER_SMALL,
                          fg_color="#c0392b", hover_color="#922b21",
                          command=lambda n=name: self._delete_preset(n)).pack(side="left", padx=(3, 8))

    def _save_preset(self):
        name = self.preset_name_entry.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Bitte einen Namen fuer das Preset eingeben.")
            return

        try:
            rate_val = float(self.rate_entry.get())
        except ValueError:
            rate_val = round(1 / base_interval, 1)

        self.presets[name] = {
            "keys": [k.strip() for k in self.keys_entry.get().split(",") if k.strip()],
            "rate": rate_val,
            "hotkey": self.hotkey_entry.get().strip() or "f6",
        }
        save_presets(self.presets)
        self.preset_name_entry.delete(0, "end")
        self._refresh_preset_list()

    def _load_preset(self, name):
        cfg = self.presets.get(name)
        if not cfg:
            return
        self.keys_entry.delete(0, "end")
        self.keys_entry.insert(0, ",".join(cfg["keys"]))
        self.rate_entry.delete(0, "end")
        self.rate_entry.insert(0, str(cfg["rate"]))
        self.hotkey_entry.delete(0, "end")
        self.hotkey_entry.insert(0, cfg["hotkey"])
        self._apply_settings()
        self.tabs.set("Steuerung")

    def _delete_preset(self, name):
        if name in self.presets:
            del self.presets[name]
            save_presets(self.presets)
            self._refresh_preset_list()

    # ---------- Tab: Info ----------
    def _build_info_tab(self, tab):
        text = (
            "So funktioniert die App:\n\n"
            "1. Taste(n) eingeben (mehrere durch Komma getrennt werden\n"
            "   der Reihe nach gedrueckt, z.B. w,a,s,d)\n"
            "2. Rate per Schnellwahl-Button waehlen oder eigenen Wert\n"
            "   eintragen und mit 'Setzen' bestaetigen\n"
            "3. Startverzoegerung waehlen, falls du nach dem Start noch\n"
            "   Zeit brauchst, um zum Zielfenster zu wechseln\n"
            "4. Hotkeys festlegen, 'Einstellungen Übernehmen' klicken\n"
            "5. Mit Start-Button oder Hotkey starten/stoppen\n\n"
            "Wichtig: Die Tastendruecke werden als echte System-Events\n"
            "gesendet - sie kommen also automatisch in dem Fenster/Tab\n"
            "an, der gerade den Fokus hat, genau wie bei einem echten\n"
            "Tastendruck. Mit 'Fenster beim Start automatisch minimieren'\n"
            "verschwindet diese App direkt beim Start, damit der Fokus\n"
            "zuverlaessig beim zuletzt aktiven Fenster bleibt.\n\n"
            "Presets speichern haeufig genutzte Konfigurationen dauerhaft\n"
            "in einer Datei im Programmordner.\n\n"
            "Hinweis: Manche Programme/Spiele mit Anti-Cheat-Schutz\n"
            "erkennen automatisierte Eingaben - bitte Nutzungsbedingungen\n"
            "der jeweiligen Anwendung beachten."
        )
        ctk.CTkLabel(tab, text=text, justify="left", anchor="w").pack(
            fill="both", expand=True, padx=18, pady=18)

    # ---------- Einstellungen anwenden ----------
    def _apply_settings(self):
        global keys, current_hotkey, quit_hotkey

        raw_keys = [k.strip() for k in self.keys_entry.get().split(",") if k.strip()]
        if not raw_keys:
            messagebox.showerror("Fehler", "Bitte mindestens eine Taste angeben.")
            return
        keys = raw_keys

        self._set_custom_rate()

        new_hotkey = self.hotkey_entry.get().strip() or "f6"
        new_quit = self.quit_entry.get().strip() or "f9"

        if new_hotkey != current_hotkey or new_quit != quit_hotkey:
            current_hotkey = new_hotkey
            quit_hotkey = new_quit
            self._register_hotkeys()

        messagebox.showinfo("Gespeichert", "Einstellungen wurden Übernommen.")

    def _register_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            keyboard.add_hotkey(current_hotkey, toggle_active)
            keyboard.add_hotkey(quit_hotkey, request_quit)
        except Exception as e:
            messagebox.showerror("Hotkey-Fehler", f"Hotkey konnte nicht gesetzt werden:\n{e}")

    # ---------- Polling (thread-sicher GUI aktualisieren) ----------
    def _poll(self):
        global quit_requested, minimize_requested

        if active:
            self.status_dot.configure(text_color="#2ecc71")
            self.status_text.configure(text="Läuft...")
            self.toggle_btn.configure(text="■   STOPPEN", fg_color="#e74c3c", hover_color="#c0392b")
        else:
            self.status_dot.configure(text_color="#e74c3c")
            self.status_text.configure(text="Gestoppt")
            self.toggle_btn.configure(text="▶   STARTEN", fg_color="#2ecc71", hover_color="#27ae60")

        self.count_label.configure(text=f"Tastendruecke: {press_count}")

        if active and start_time:
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            self.time_label.configure(text=f"Laufzeit: {mins:02d}:{secs:02d}")
        else:
            self.time_label.configure(text="Laufzeit: 00:00")

        if minimize_requested:
            minimize_requested = False
            self.iconify()

        if quit_requested:
            self._on_close()
            return

        self.after(150, self._poll)

    def _on_close(self):
        global active
        active = False
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    worker = threading.Thread(target=clicker_loop, daemon=True)
    worker.start()

    app = App()
    app.mainloop()
