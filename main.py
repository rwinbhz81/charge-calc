# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import time
from typing import List, Tuple

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.factory import Factory
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.animation import Animation

# Desktop test window (landscape)
Window.size = (1200, 700)

PIN_CODE = "4252"
MAX_ATTEMPTS = 3
LOCK_SECONDS = 30

ELEMENTS = ["C", "Si", "Mn", "Cr", "Ni", "Mo", "V", "Nb"]

DEFAULT_MATERIALS = [
    "Scrap",
    "Granul Coke",
    "FeSi 75%",
    "FeMn 70% HiC",
    "FeCr 70% HiC",
    "FeMo 65%",
    "Nickel",
    "Scrap 316",
    "Scrap 410",
]

# 9 columns numeric: 8 elements + weight
DEFAULT_ROWS = [
    [0.15, 0.15, 0.2, 0, 0, 0, 0, 0, 742],
    [90,   0,    0,   0, 0, 0, 0, 0, 1.8],
    [0,    70,   0,   0, 0, 0, 0, 0, 1.4],
    [7,    0,    70,  0, 0, 0, 0, 0, 4.8],
    [7,    0,    0,   70,0, 0, 0, 0, 0],
    [0.1,  0,    0,   0, 0, 65,0, 0, 0],
    [0,    0,    0,   0, 100,0, 0, 0, 0],
    [0.06, 0.5,  0.5, 16,10,2, 0, 0, 0],
    [0.03, 0.5,  0.4, 16,0, 0, 0, 0, 0],
]


def safe_float(x: str) -> float:
    s = (x or "").strip().replace(",", ".")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def calc_weighted_average(rows: List[List[float]]) -> Tuple[List[float], float]:
    """VB6 logic: weighted average; truncate to 3 decimals."""
    total_w = sum(r[8] for r in rows)
    if total_w <= 0:
        return [0.0] * 8, 0.0

    out = []
    for col in range(8):
        s = 0.0
        for r in rows:
            s += r[col] * r[8]
        val = s / total_w
        # VB: Int(val*1000)/1000  (truncate for non-negative)
        val = int(val * 1000) / 1000.0 if val >= 0 else -int(abs(val) * 1000) / 1000.0
        out.append(val)
    return out, total_w


KV = r"""
#:import dp kivy.metrics.dp

<HeaderCell@Label>:
    bold: True
    color: 0.92, 0.93, 0.95, 1
    size_hint_y: None
    height: dp(30)
    halign: "center"
    valign: "middle"
    text_size: self.size

<RowLabel@Label>:
    color: 0.75, 0.78, 0.82, 1
    size_hint_y: None
    height: dp(40)
    halign: "left"
    valign: "middle"
    text_size: self.size

<Cell@TextInput>:
    multiline: False
    write_tab: False
    size_hint_y: None
    height: dp(40)
    halign: "center"
    padding: dp(8), dp(10)
    font_size: "16sp"
    background_normal: ""
    background_active: ""
    background_color: 0.12, 0.14, 0.18, 1
    foreground_color: 0.95, 0.95, 0.95, 1
    cursor_color: 0.95, 0.95, 0.95, 1

<Pill@Label>:
    size_hint: None, None
    size: dp(190), dp(34)
    bold: True
    halign: "center"
    valign: "middle"
    text_size: self.size
    color: 1,1,1,1
    canvas.before:
        Color:
            rgba: 0.16, 0.52, 0.55, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14),]

<Card@BoxLayout>:
    padding: dp(12)
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: 0.10, 0.11, 0.14, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16),]

<PrimaryBtn@Button>:
    bold: True
    background_normal: ""
    background_color: 0.16, 0.52, 0.55, 1

<SecondaryBtn@Button>:
    background_normal: ""
    background_color: 0.22, 0.24, 0.28, 1

<GhostBtn@Button>:
    background_normal: ""
    background_color: 0.15, 0.16, 0.20, 1

# ---------------- PIN SCREEN (PRO) ----------------

<PinScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(18)
        spacing: dp(14)
        canvas.before:
            Color:
                rgba: 0.07, 0.08, 0.10, 1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(56)
            spacing: dp(10)

            BoxLayout:
                orientation: "vertical"
                spacing: dp(2)

                Label:
                    text: "Locked App"
                    font_size: "20sp"
                    bold: True
                    color: 0.95,0.95,0.95,1
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

                Label:
                    text: "Enter your 4-digit PIN to continue"
                    font_size: "13sp"
                    color: 0.65,0.68,0.72,1
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

            Widget:

            Pill:
                text: root.lock_text

        BoxLayout:
            spacing: dp(14)

            Card:
                orientation: "vertical"
                size_hint_x: 0.48
                id: pin_card

                Label:
                    text: "PIN"
                    bold: True
                    font_size: "16sp"
                    color: 0.95,0.95,0.95,1
                    size_hint_y: None
                    height: dp(28)
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

                Label:
                    id: dots
                    text: root.dots_text
                    font_size: "44sp"
                    color: 0.95,0.95,0.95,1
                    size_hint_y: None
                    height: dp(70)
                    halign: "center"
                    valign: "middle"
                    text_size: self.size

                Label:
                    id: msg
                    text: root.message_text
                    color: 1, 0.4, 0.4, 1
                    size_hint_y: None
                    height: dp(22)
                    halign: "center"
                    valign: "middle"
                    text_size: self.size

                BoxLayout:
                    size_hint_y: None
                    height: dp(48)
                    spacing: dp(10)

                    SecondaryBtn:
                        text: "Clear"
                        on_release: root.clear_pin()

                    PrimaryBtn:
                        text: "Enter"
                        on_release: root.submit_pin()

            Card:
                orientation: "vertical"
                size_hint_x: 0.52

                Label:
                    text: "Keypad"
                    bold: True
                    font_size: "16sp"
                    color: 0.95,0.95,0.95,1
                    size_hint_y: None
                    height: dp(28)
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

                GridLayout:
                    cols: 3
                    spacing: dp(10)
                    size_hint_y: None
                    height: dp(4*56 + 3*10)

                    GhostBtn:
                        text: "1"
                        font_size: "20sp"
                        on_release: root.add_digit("1")
                    GhostBtn:
                        text: "2"
                        font_size: "20sp"
                        on_release: root.add_digit("2")
                    GhostBtn:
                        text: "3"
                        font_size: "20sp"
                        on_release: root.add_digit("3")

                    GhostBtn:
                        text: "4"
                        font_size: "20sp"
                        on_release: root.add_digit("4")
                    GhostBtn:
                        text: "5"
                        font_size: "20sp"
                        on_release: root.add_digit("5")
                    GhostBtn:
                        text: "6"
                        font_size: "20sp"
                        on_release: root.add_digit("6")

                    GhostBtn:
                        text: "7"
                        font_size: "20sp"
                        on_release: root.add_digit("7")
                    GhostBtn:
                        text: "8"
                        font_size: "20sp"
                        on_release: root.add_digit("8")
                    GhostBtn:
                        text: "9"
                        font_size: "20sp"
                        on_release: root.add_digit("9")

                    SecondaryBtn:
                        text: "⌫"
                        font_size: "18sp"
                        on_release: root.backspace()
                    GhostBtn:
                        text: "0"
                        font_size: "20sp"
                        on_release: root.add_digit("0")
                    SecondaryBtn:
                        text: "Help"
                        on_release: root.show_help()

# ---------------- MAIN SCREEN (MODERN LANDSCAPE) ----------------

<MainScreen>:
    BoxLayout:
        orientation: "vertical"
        padding: dp(14)
        spacing: dp(12)
        canvas.before:
            Color:
                rgba: 0.07, 0.08, 0.10, 1
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(56)
            spacing: dp(10)

            BoxLayout:
                orientation: "vertical"
                spacing: dp(2)
                Label:
                    text: "Charge Calculation"
                    font_size: "20sp"
                    bold: True
                    color: 0.95,0.95,0.95,1
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                Label:
                    text: "Landscape-friendly • Weighted composition (VB logic)"
                    font_size: "13sp"
                    color: 0.65,0.68,0.72,1
                    halign: "left"
                    valign: "middle"
                    text_size: self.size

            Widget:

            Pill:
                text: root.total_weight_text

        BoxLayout:
            spacing: dp(12)

            Card:
                orientation: "vertical"

                BoxLayout:
                    size_hint_y: None
                    height: dp(34)
                    Label:
                        text: "Inputs"
                        bold: True
                        font_size: "16sp"
                        color: 0.95,0.95,0.95,1
                        halign: "left"
                        valign: "middle"
                        text_size: self.size
                    Label:
                        text: "9 materials × 8 elements + Weight"
                        font_size: "13sp"
                        color: 0.65,0.68,0.72,1
                        halign: "right"
                        valign: "middle"
                        text_size: self.size

                ScrollView:
                    do_scroll_x: True
                    do_scroll_y: True

                    GridLayout:
                        id: grid
                        cols: 10
                        size_hint: None, None
                        width: dp(1250)
                        height: self.minimum_height
                        spacing: dp(6)
                        padding: dp(6), dp(6)

                BoxLayout:
                    size_hint_y: None
                    height: dp(46)
                    spacing: dp(10)

                    PrimaryBtn:
                        text: "Calculate"
                        on_release: root.on_calculate()

                    SecondaryBtn:
                        text: "Clear Weights"
                        on_release: root.on_clear_weights()

                    SecondaryBtn:
                        text: "Reset Defaults"
                        on_release: root.on_reset()

                    SecondaryBtn:
                        text: "Help"
                        on_release: root.on_help()

            Card:
                orientation: "vertical"
                size_hint_x: 0.36

                Label:
                    text: "Result"
                    bold: True
                    font_size: "16sp"
                    color: 0.95,0.95,0.95,1
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    size_hint_y: None
                    height: dp(30)

                GridLayout:
                    cols: 2
                    spacing: dp(8)
                    size_hint_y: None
                    height: self.minimum_height

                    HeaderCell:
                        text: "%C"
                    Cell:
                        id: out_c
                        readonly: True

                    HeaderCell:
                        text: "%Si"
                    Cell:
                        id: out_si
                        readonly: True

                    HeaderCell:
                        text: "%Mn"
                    Cell:
                        id: out_mn
                        readonly: True

                    HeaderCell:
                        text: "%Cr"
                    Cell:
                        id: out_cr
                        readonly: True

                    HeaderCell:
                        text: "%Ni"
                    Cell:
                        id: out_ni
                        readonly: True

                    HeaderCell:
                        text: "%Mo"
                    Cell:
                        id: out_mo
                        readonly: True

                    HeaderCell:
                        text: "%V"
                    Cell:
                        id: out_v
                        readonly: True

                    HeaderCell:
                        text: "%Nb"
                    Cell:
                        id: out_nb
                        readonly: True

                    HeaderCell:
                        text: "Total Weight"
                    Cell:
                        id: out_tw
                        readonly: True

                Label:
                    text: root.status_text
                    color: 0.65,0.68,0.72,1
                    halign: "left"
                    valign: "top"
                    text_size: self.size

                Widget:

                SecondaryBtn:
                    text: "Lock"
                    size_hint_y: None
                    height: dp(44)
                    on_release: root.lock_app()
"""


class InfoBody(BoxLayout):
    def __init__(self, text="", **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(10), **kwargs)
        from kivy.uix.label import Label
        from kivy.uix.button import Button

        lab = Label(
            text=text,
            color=(0.95, 0.95, 0.95, 1),
            halign="left",
            valign="top",
            text_size=(dp(560), None),
        )
        self.add_widget(lab)

        btn = Button(
            text="Close",
            size_hint_y=None,
            height=dp(44),
            background_normal="",
            background_color=(0.16, 0.52, 0.55, 1),
        )
        btn.bind(on_release=lambda *_: self.parent.parent.dismiss() if self.parent and self.parent.parent else None)
        self.add_widget(btn)


class PinScreen(Screen):
    dots_text = StringProperty("○ ○ ○ ○")
    message_text = StringProperty("")
    lock_text = StringProperty("Unlocked")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pin = ""
        self._attempts = 0
        self._locked_until = 0.0

    def on_pre_enter(self, *args):
        self._pin = ""
        self._attempts = 0
        self._locked_until = 0.0
        self.message_text = ""
        self._refresh()

    def _refresh(self):
        filled = "●"
        empty = "○"
        dots = [filled if i < len(self._pin) else empty for i in range(4)]
        self.dots_text = " ".join(dots)

        now = time.time()
        if now < self._locked_until:
            remaining = int(self._locked_until - now)
            self.lock_text = f"Locked: {remaining}s"
        else:
            self.lock_text = "Unlocked"

    def _shake(self):
        card = self.ids.get("pin_card")
        if not card:
            return
        x0, y0 = card.pos
        a = (
            Animation(x=x0 - dp(10), duration=0.05)
            + Animation(x=x0 + dp(10), duration=0.05)
            + Animation(x=x0 - dp(8), duration=0.05)
            + Animation(x=x0 + dp(8), duration=0.05)
            + Animation(x=x0, duration=0.05)
        )
        a.start(card)

    def _tick_lock(self, *_):
        self._refresh()
        if time.time() >= self._locked_until:
            try:
                from kivy.clock import Clock
                Clock.unschedule(self._tick_lock)
            except Exception:
                pass
            self.message_text = ""
            self._refresh()

    def add_digit(self, d: str):
        now = time.time()
        if now < self._locked_until:
            self.message_text = "Too many attempts. Please wait."
            self._refresh()
            return

        if len(self._pin) >= 4:
            return
        self._pin += d
        self.message_text = ""
        self._refresh()

        if len(self._pin) == 4:
            self.submit_pin()

    def backspace(self):
        if self._pin:
            self._pin = self._pin[:-1]
            self.message_text = ""
            self._refresh()

    def clear_pin(self):
        self._pin = ""
        self.message_text = ""
        self._refresh()

    def submit_pin(self):
        now = time.time()
        if now < self._locked_until:
            self.message_text = "Too many attempts. Please wait."
            self._refresh()
            return

        if len(self._pin) != 4:
            self.message_text = "Enter 4 digits."
            self._shake()
            self._refresh()
            return

        if self._pin == PIN_CODE:
            self.message_text = ""
            self._pin = ""
            self._refresh()
            self.manager.current = "main"
            return

        self._attempts += 1
        self.message_text = f"Wrong PIN. Attempt {self._attempts}/{MAX_ATTEMPTS}"
        self._shake()
        self._pin = ""
        self._refresh()

        if self._attempts >= MAX_ATTEMPTS:
            self._locked_until = time.time() + LOCK_SECONDS
            self.message_text = f"Locked for {LOCK_SECONDS} seconds."
            self._refresh()
            from kivy.clock import Clock
            Clock.schedule_interval(self._tick_lock, 0.2)

    def show_help(self):
        msg = (
            "Charge Calculation Application\n\n"
            "Login:\n"
            "Enter the 4-digit PIN to unlock.\n\n"
            "----------------------------------------\n"
            "Programmer:Bahar System\n"
            "Email: arvinbaharzadeh@gmail.com"
        )
        Popup(title="Help", content=InfoBody(text=msg), size_hint=(0.78, 0.55)).open()


class MainScreen(Screen):
    total_weight_text = StringProperty("Total W: 0")
    status_text = StringProperty("Ready.")

    SAVE_FILENAME = "saved_data.json"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cells = []  # 9x9 inputs

    def _data_path(self) -> str:
        """
        Use Kivy's user_data_dir (best for Android).
        Falls back to current directory on desktop if app isn't ready.
        """
        try:
            app = App.get_running_app()
            folder = getattr(app, "user_data_dir", None) or os.getcwd()
        except Exception:
            folder = os.getcwd()

        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, self.SAVE_FILENAME)

    def on_pre_enter(self, *args):
        if not self._cells:
            self._build_table()
            # Load saved data if exists; else defaults
            if not self.load_data():
                self.on_reset()
            else:
                self.status_text = "Loaded saved data."
                self.on_calculate(save=False)  # show result without re-saving immediately

    def _build_table(self):
        grid = self.ids.grid
        grid.clear_widgets()
        self._cells.clear()

        headers = ["Material"] + [f"%{e}" for e in ELEMENTS] + ["Weight"]
        for h in headers:
            grid.add_widget(Factory.HeaderCell(text=h))

        for r in range(9):
            grid.add_widget(Factory.RowLabel(text=DEFAULT_MATERIALS[r]))
            row_cells = []
            for c in range(9):
                inp = Factory.Cell()
                row_cells.append(inp)
                grid.add_widget(inp)
            self._cells.append(row_cells)

    def _set_defaults(self):
        for r in range(9):
            for c in range(9):
                v = DEFAULT_ROWS[r][c]
                self._cells[r][c].text = "" if v == 0 else str(v)

    def _read_rows(self):
        rows = []
        for r in range(9):
            row = [safe_float(self._cells[r][c].text) for c in range(9)]
            rows.append(row)
        return rows

    # ---------- Persistence ----------
    def save_data(self) -> bool:
        try:
            rows_text = []
            for r in range(9):
                row = []
                for c in range(9):
                    row.append(self._cells[r][c].text)
                rows_text.append(row)

            payload = {"rows": rows_text}
            with open(self._data_path(), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            return True
        except Exception:
            return False

    def load_data(self) -> bool:
        path = self._data_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            rows = payload.get("rows")
            if not rows or len(rows) != 9:
                return False

            for r in range(9):
                if len(rows[r]) != 9:
                    return False
                for c in range(9):
                    self._cells[r][c].text = str(rows[r][c] or "")
            return True
        except Exception:
            return False

    # ---------- Actions ----------
    def on_calculate(self, save: bool = True):
        rows = self._read_rows()
        out, total_w = calc_weighted_average(rows)

        self.total_weight_text = f"Total W: {total_w:g}"

        self.ids.out_c.text = f"{out[0]:.3f}"
        self.ids.out_si.text = f"{out[1]:.3f}"
        self.ids.out_mn.text = f"{out[2]:.3f}"
        self.ids.out_cr.text = f"{out[3]:.3f}"
        self.ids.out_ni.text = f"{out[4]:.3f}"
        self.ids.out_mo.text = f"{out[5]:.3f}"
        self.ids.out_v.text = f"{out[6]:.3f}"
        self.ids.out_nb.text = f"{out[7]:.3f}"
        self.ids.out_tw.text = f"{total_w:g}"

        if total_w <= 0:
            self.status_text = "Total weight is zero. Please enter weights."
            Popup(
                title="Info",
                content=InfoBody(text="Total weight is zero.\nPlease enter weights in the Weight column."),
                size_hint=(0.75, 0.4),
            ).open()
        else:
            self.status_text = "Calculated successfully."

        if save:
            self.save_data()

    def on_clear_weights(self):
        for r in range(9):
            self._cells[r][8].text = ""
        self.status_text = "Weights cleared."
        self.on_calculate()

    def on_reset(self):
        self._set_defaults()
        self.status_text = "Defaults loaded."
        self.on_calculate()

    def on_help(self):
        msg = (
            "Charge Calculation Application\n\n"
            "Each row contains 8 element percentages and one Weight value.\n\n"
            "Formula used:\n"
            "Final %Element = Σ(%Element × Weight) / Σ(Weight)\n\n"
            "Rounding method:\n"
            "Values are truncated to 3 decimal places (same as VB6 logic).\n\n"
            "----------------------------------------\n"
            "Programmer: Arvin Baharzadeh\n"
            "Email: arvinbaharzadeh@gmail.com"
        )
        Popup(title="Help", content=InfoBody(text=msg), size_hint=(0.78, 0.6)).open()

    def lock_app(self):
        # Save when locking too (extra safe)
        self.save_data()
        self.manager.current = "pin"


class ChargeCalcApp(App):
    def build(self):
        self.title = "Charge Calculation"
        Builder.load_string(KV)

        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        sm.add_widget(PinScreen(name="pin"))
        sm.add_widget(MainScreen(name="main"))
        sm.current = "pin"
        return sm


if __name__ == "__main__":
    ChargeCalcApp().run()
