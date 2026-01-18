import sys
import os
import keyboard
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout, 
    QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QSize

# ------------------ EXE CONVERSION HELPER ------------------

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ------------------ UI COMPONENTS ------------------

class KeyButton(QPushButton):
    def __init__(self, tam, eng, parent=None):
        super().__init__(parent)
        self.setFixedSize(65, 55)
        self.setFocusPolicy(Qt.NoFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(0)
        
        self.tam_label = QLabel(tam)
        self.tam_label.setAlignment(Qt.AlignCenter)
        # WA_TransparentForMouseEvents allows clicks to pass through to the button
        self.tam_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.eng_label = QLabel(eng.upper())
        self.eng_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.eng_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout.addWidget(self.tam_label, stretch=3)
        layout.addWidget(self.eng_label, stretch=1)
        
        # PERFECTED HOVER: Targets the whole button and resets label styles
        self.default_style = """
            KeyButton { 
                background: #333; 
                border-radius: 6px; 
                border: 1px solid #333; 
            }
            KeyButton:hover { 
                background: #444; 
                border: 1px solid #0091FF; 
            }
            /* Ensures labels don't create their own boxes/borders */
            KeyButton QLabel {
                background: transparent;
                border: none;
            }
            KeyButton:hover QLabel { 
                color: #FFFFFF !important; 
            }
        """
        self.active_style = "background:#555; border: 2px solid #0091FF; border-radius:6px;"
        self.setStyleSheet(self.default_style)

    def trigger_visual_press(self):
        """Visual feedback for physical key presses"""
        self.setStyleSheet(self.active_style)
        QTimer.singleShot(150, lambda: self.setStyleSheet(self.default_style))

class TamilOSK(QWidget):
    update_ui_signal = Signal(str)
    visual_press_signal = Signal(str) 

    def __init__(self):
        super().__init__()
        self.drag_pos = QPoint(0, 0)
        self.mode = "TA"
        self.last_cons = None 
        self.btn_objects = {} 
        
        # Window Configuration
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # SET WINDOW ICON (Requires app_icon.ico in same folder)
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path)) 

        self.physical_map = {eng.lower(): tam for row in KEY_DATA for eng, tam in row}
        self.init_ui()
        
        # Signal Connections
        self.update_ui_signal.connect(self.refresh_ui_logic)
        self.visual_press_signal.connect(self.animate_button)
        
        # Keyboard Hook
        keyboard.hook(self.handle_physical_input, suppress=True)

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        
        self.mode_label = QLabel()
        header.addWidget(self.mode_label)
        header.addStretch()
        
        # Minimize Button
        min_btn = QPushButton("—")
        min_btn.setFixedSize(30, 25)
        min_btn.setFocusPolicy(Qt.NoFocus)
        min_btn.setStyleSheet("background:#444; color:white; border-radius:5px; font-weight:bold;")
        min_btn.clicked.connect(self.showMinimized)
        header.addWidget(min_btn)
        
        # Close Button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 25)
        close_btn.setFocusPolicy(Qt.NoFocus)
        close_btn.setStyleSheet("background:#B71C1C; color:white; border-radius:5px;")
        close_btn.clicked.connect(self.exit_app) 
        header.addWidget(close_btn)
        
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(6)
        for r, row in enumerate(KEY_DATA):
            for c, (eng, tam) in enumerate(row):
                btn = KeyButton(tam, eng)
                btn.clicked.connect(lambda _, t=tam, e=eng: self.toggle_mode() if e=="f12" else self.execute_typing(t, e))
                grid.addWidget(btn, r, c)
                self.btn_objects[eng.lower()] = {"obj": btn, "base_tam": tam}

        self.add_system_keys(grid)
        layout.addLayout(grid)
        
        # Main Window Style
        self.setStyleSheet("QWidget { background:#252525; border: 1px solid #444; border-radius:10px; }")
        self.refresh_ui_logic("CLEAR")

    def add_system_keys(self, grid):
        sys_style = """
            QPushButton { 
                color: #0091FF; 
                background: #333; 
                border-radius: 6px; 
                border: 1px solid #333; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background: #444; 
                border: 1px solid #0091FF; 
                color: #FFFFFF; 
            }
        """
        keys = [("BACKSPACE", 4, 0, 1, 2), ("SPACE", 4, 2, 1, 6), ("ENTER", 4, 8, 1, 2)]
        for text, r, c, rs, cs in keys:
            btn = QPushButton(text)
            btn.setFixedHeight(55)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setStyleSheet(sys_style)
            if text == "BACKSPACE": btn.clicked.connect(self.do_bksp)
            elif text == "SPACE": btn.clicked.connect(lambda: self.execute_typing(" ", "space"))
            elif text == "ENTER": btn.clicked.connect(lambda: keyboard.send("enter"))
            grid.addWidget(btn, r, c, rs, cs)
            self.btn_objects[text.lower()] = {"obj": btn}

    def exit_app(self):
        """Cleans up keyboard hooks and ensures background process terminates"""
        keyboard.unhook_all()
        QApplication.quit()
        sys.exit(0)

    def toggle_mode(self):
        self.mode = "EN" if self.mode == "TA" else "TA"
        self.last_cons = None
        self.update_ui_signal.emit("CLEAR")

    def refresh_ui_logic(self, cons):
        t_col, e_col = ("yellow", "#666") if self.mode == "TA" else ("#666", "#0091FF")
        self.mode_label.setText(f"<html><b><span style='color:{t_col}; font-size:11pt;'>TAM</span><span style='color:{e_col}; font-size:11pt;'> / ENG</span></b></html>")
        
        for key, data in self.btn_objects.items():
            if "base_tam" not in data: continue 
            btn, tam = data["obj"], data["base_tam"]
            display_tam = tam
            
            if self.mode == "TA" and cons != "CLEAR" and tam in VOWEL_SIGN_ONLY:
                display_tam = cons + VOWEL_SIGN_ONLY[tam]
            
            tam_color = ("yellow" if tam in "அஆஇஈஉஊஎஏஐஒஓஔஃ" else "#00FF7F") if self.mode == "TA" else "#444"
            eng_color = "#0091FF" if self.mode == "EN" else "#555"

            # FIXED: Removed potential for individual label borders/backgrounds
            btn.tam_label.setText(display_tam)
            btn.tam_label.setStyleSheet(f"color: {tam_color}; font-size: 13pt; font-family: 'Nirmala UI'; background:transparent; border:none;")
            btn.eng_label.setStyleSheet(f"color: {eng_color}; font-size: 8pt; font-family: 'Segoe UI'; background:transparent; border:none;")

    def handle_physical_input(self, e):
        if e.event_type == "down":
            k = e.name.lower()
            if k in self.btn_objects: self.visual_press_signal.emit(k)
            if k == "f12": self.toggle_mode(); return False
            if k == "backspace": self.do_bksp(); return False
            if self.mode == "TA" and k in self.physical_map:
                self.execute_typing(self.physical_map[k], k); return False
        return True

    def animate_button(self, key_name):
        btn = self.btn_objects.get(key_name, {}).get("obj")
        if isinstance(btn, KeyButton): btn.trigger_visual_press()

    def do_bksp(self):
        keyboard.send("backspace")
        self.last_cons = None 
        self.update_ui_signal.emit("CLEAR")

    def execute_typing(self, tam, eng):
        if self.mode == "EN": keyboard.write(eng if eng != "space" else " "); return
        if self.last_cons and tam in VOWEL_SIGN_ONLY:
            keyboard.send("backspace")
            keyboard.write(self.last_cons + ("்" if tam == "அ" else VOWEL_SIGN_ONLY[tam]))
            self.last_cons = None; self.update_ui_signal.emit("CLEAR")
        else:
            keyboard.write(tam)
            if tam in "கஙசஞடணதநபமயரலவழளறனக்ஷஜஷஸஹ":
                self.last_cons = tam; self.update_ui_signal.emit(tam)
            else: self.last_cons = None; self.update_ui_signal.emit("CLEAR")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

# ------------------ DATA ------------------
KEY_DATA = [
    [("1","அ"), ("2","ஆ"), ("3","இ"), ("4","க"), ("5","ங"), ("6","ச"), ("7","ஞ"), ("8","ட"), ("9","ண"), ("0","ஃ")],
    [("q","ஈ"), ("w","உ"), ("e","ஊ"), ("r","த"), ("t","ந"), ("y","ப"), ("u","ம"), ("i","ய"), ("o","ர"), ("p","க்ஷ")],
    [("a","எ"), ("s","ஏ"), ("d","ஐ"), ("f","ல"), ("g","வ"), ("h","ழ"), ("j","ள"), ("k","ற"), ("l","ன")],
    [("z","ஒ"), ("x","ஓ"), ("c","ஔ"), ("v","ஷ"), ("b","ஸ"), ("n","ஜ"), ("m","ஹ"), ("f12","Md")]
]
VOWEL_SIGN_ONLY = {"அ":"்","ஆ":"ா","இ":"ி","ஈ":"ீ","உ":"ு","ஊ":"ூ","எ":"ெ","ஏ":"ே","ஐ":"ை","ஒ":"ொ","ஓ":"ோ","ஔ":"ௌ"}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TamilOSK()
    window.show()
    sys.exit(app.exec())