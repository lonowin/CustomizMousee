import sys
import json
import os
import urllib.request
import math
import random

# ── Windows-only imports (graceful fallback for dev on non-Windows) ──────────
try:
    import win32con
    import win32gui
    import win32api
    _WIN32 = True
except ImportError:
    _WIN32 = False

import pyautogui
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, QSize, pyqtSignal
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                          QIcon, QPainterPath, QPixmap, QFont, QRadialGradient,
                          QFontDatabase)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QComboBox, QCheckBox, QPushButton, QTabWidget, QFrame,
    QColorDialog, QFileDialog, QSystemTrayIcon, QMenu, QAction,
    QMessageBox, QSpacerItem, QSizePolicy, QScrollArea
)

# ── Win32 extended-style constants ───────────────────────────────────────────
WS_EX_TRANSLUCENT = 0x00000020
WS_EX_LAYERED     = 0x00080000
WS_EX_NOACTIVATE  = 0x08000000


# ─────────────────────────────────────────────────────────────────────────────
# Font Awesome loader
# ─────────────────────────────────────────────────────────────────────────────
_FA_FONT_ID = None

def _ensure_fa_font():
    """Download and register Font Awesome Solid if not already done."""
    global _FA_FONT_ID
    if _FA_FONT_ID is not None:
        return
    fa_path = os.path.join(_config_dir(), "fa-solid-900.ttf")
    if not os.path.exists(fa_path):
        os.makedirs(_config_dir(), exist_ok=True)
        try:
            url = ("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/"
                   "6.x/webfonts/fa-solid-900.ttf")
            urllib.request.urlretrieve(url, fa_path)
        except Exception:
            return
    _FA_FONT_ID = QFontDatabase.addApplicationFont(fa_path)

def fa_font(size=14) -> QFont:
    _ensure_fa_font()
    families = QFontDatabase.applicationFontFamilies(_FA_FONT_ID) if _FA_FONT_ID is not None and _FA_FONT_ID >= 0 else []
    family = families[0] if families else "Font Awesome 6 Free Solid"
    f = QFont(family)
    f.setPointSize(size)
    return f

# Unicode codepoints for FA solid icons
FA = {
    "palette":    "\uf53f",   # palette
    "sun":        "\uf185",   # sun (halo)
    "gear":       "\uf013",   # gear / settings
    "wrench":     "\uf0ad",   # wrench / maintenance
    "save":       "\uf0c7",   # floppy disk
    "folder":     "\uf07c",   # open folder
    "rotate":     "\uf2f1",   # rotate (reset)
    "eye":        "\uf06e",   # eye
    "eye_slash":  "\uf070",   # eye-slash
    "trail":      "\uf1eb",   # wifi-like / trail symbol
    "upload":     "\uf093",   # upload
    "times":      "\uf00d",   # ×
    "tray_show":  "\uf06e",
    "tray_hide":  "\uf070",
    "tray_toggle":"\uf021",
    "tray_exit":  "\uf011",
}


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
def _config_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "CustomizeMousee")

def _default_config():
    return {
        "cursor_type":        "Custom Cursor",
        "enable_trails":      True,
        "halo_enabled":       True,
        "opacity":            220,
        "trail_length":       30,
        "halo_radius":        24,
        "trail_color":        [255, 30, 67],
        "halo_color":         [40, 230, 80],
        "theme":              "Dark",
        "run_background":     False,   # ← default: start visible, do not start hidden in tray
        "ui_scale":           100,
        "trail_width":        7,
        "trail_texture_path": "",
    }

def _load_config():
    path = os.path.join(_config_dir(), "settings.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = _default_config()
            cfg.update(data)
            return cfg
        except Exception:
            pass
    # Automatically create the default settings.json file if it does not exist
    cfg = _default_config()
    try:
        _save_config(cfg)
    except Exception:
        pass
    return cfg

def _save_config(cfg: dict):
    os.makedirs(_config_dir(), exist_ok=True)
    path = os.path.join(_config_dir(), "settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


# ─────────────────────────────────────────────────────────────────────────────
# Overlay widget — covers ALL monitors
# ─────────────────────────────────────────────────────────────────────────────
class UltimateMouseOverlay(QWidget):
    """Full-desktop transparent overlay that draws cursor trails + halo
    across every connected monitor."""

    def __init__(self):
        super().__init__()
        flags = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                 | Qt.Tool | Qt.WindowTransparentForInput)
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        # ── cover the virtual desktop (all monitors combined) ─────────────
        # Updated for Qt5: QDesktopWidget.virtualGeometry() is deprecated/removed.
        # Use the primary screen's virtual geometry which spans all monitors.
        screen = QApplication.instance().primaryScreen()
        vg = screen.virtualGeometry()   # bounding rect of all screens
        self.setGeometry(vg)
        self._vg_origin = QPoint(vg.x(), vg.y())
        self._vg_origin = QPoint(vg.x(), vg.y())

        # ── state ──────────────────────────────────────────────────────────
        self.trail_points:    list[QPoint] = []
        self.max_trail_length = 30
        self.halo_radius      = 24
        self.opacity_val      = 220
        self.trail_width      = 7
        self.enable_trails    = True
        self.enable_halo      = True

        self.trail_color = QColor(255, 30, 67)
        self.halo_color  = QColor(40, 230, 80)

        self.trail_texture_path: str | None = None
        self.trail_texture:     QPixmap | None = None

        # ── click animation state ──────────────────────────────────────────
        self.ripples = []
        self.particles = []
        self.left_was_pressed = False
        self.right_was_pressed = False
        self.wave_angle = 0.0

        # ── timer ──────────────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._track_mouse)
        self._timer.start(10)

    # ── Win32 setup (make truly click-through and always-on-top) ─────────────
    def showEvent(self, event):
        super().showEvent(event)
        if _WIN32:
            hwnd = int(self.winId())
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd, win32con.GWL_EXSTYLE,
                ex | WS_EX_TRANSLUCENT | WS_EX_LAYERED | WS_EX_NOACTIVATE
            )
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )

    # ── mouse tracking (uses global coords mapped to virtual desktop) ─────────
    def _track_mouse(self):
        # ── Update ripples & particles ─────────────────────────
        self._update_animations()

        # ── Detect clicks ──────────────────────────────────────
        if _WIN32:
            left_pressed = (win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000) != 0
            right_pressed = (win32api.GetAsyncKeyState(win32con.VK_RBUTTON) & 0x8000) != 0

            # Map global position to local QPoint
            pos = pyautogui.position()
            local = QPoint(pos.x - self._vg_origin.x(), pos.y - self._vg_origin.y())

            if left_pressed and not self.left_was_pressed:
                self._trigger_click_effect(local, self.trail_color)
            if right_pressed and not self.right_was_pressed:
                self._trigger_click_effect(local, self.halo_color)

            self.left_was_pressed = left_pressed
            self.right_was_pressed = right_pressed

        if not (self.enable_trails or self.enable_halo):
            if self.trail_points:
                self.trail_points.clear()
            if self.ripples or self.particles:
                self.update()
            return

        pos = pyautogui.position()
        local = QPoint(pos.x - self._vg_origin.x(), pos.y - self._vg_origin.y())

        # If we have active animations or trail to wave, we must redraw even if mouse doesn't move
        if self.ripples or self.particles or (self.enable_trails and len(self.trail_points) > 1):
            self.update()

        if self.trail_points and self.trail_points[-1] == local:
            if len(self.trail_points) > 1:
                self.trail_points.pop(0)
                self.update()
            return

        self.trail_points.append(local)
        if len(self.trail_points) > self.max_trail_length:
            self.trail_points.pop(0)
        self.update()

    def _trigger_click_effect(self, pos: QPoint, color: QColor):
        # 1. Add ripple
        self.ripples.append({
            "pos": pos,
            "radius": 5.0,
            "opacity": 1.0,
            "color": color
        })

        # 2. Add particles
        num_particles = 12
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 5.0)
            self.particles.append({
                "x": float(pos.x()),
                "y": float(pos.y()),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "radius": random.uniform(1.5, 3.5),
                "life": 1.0,
                "decay": random.uniform(0.03, 0.06),
                "color": color
            })

    def _update_animations(self):
        self.wave_angle += 0.15
        # Update ripples
        active_ripples = []
        for r in self.ripples:
            r["radius"] += 2.5
            r["opacity"] -= 0.06
            if r["opacity"] > 0:
                active_ripples.append(r)
        self.ripples = active_ripples

        # Update particles
        active_particles = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.94
            p["vy"] *= 0.94
            p["life"] -= p["decay"]
            if p["life"] > 0:
                active_particles.append(p)
        self.particles = active_particles

    # ── painting ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        if not self.trail_points and not self.ripples and not self.particles:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # ── trail ──────────────────────────────────────────────────────────
        if self.trail_points and self.enable_trails and len(self.trail_points) > 1:
            cur = self.trail_points[-1]
            if self.trail_texture:
                sz = max(8, self.trail_width * 2)
                scaled = self.trail_texture.scaled(sz, sz, Qt.KeepAspectRatio,
                                                    Qt.SmoothTransformation)
                n = len(self.trail_points)
                for i, pt in enumerate(self.trail_points):
                    alpha = int((i / n) * self.opacity_val)
                    painter.setOpacity(alpha / 255)
                    x = pt.x() - scaled.width() // 2
                    y = pt.y() - scaled.height() // 2
                    painter.drawPixmap(x, y, scaled)
                painter.setOpacity(1.0)
            else:
                n = len(self.trail_points)
                c1 = self.trail_color
                c2 = self.halo_color
                
                for i in range(n - 1):
                    p1 = self.trail_points[i]
                    p2 = self.trail_points[i + 1]
                    
                    # Calculate ratio along the trail (0.0 at tail, 1.0 at cursor)
                    ratio = i / (n - 1)
                    
                    # Wave effect: stronger at the tail, 0 at the cursor to maintain precision
                    wave = math.sin(self.wave_angle - ratio * 10.0) * (self.trail_width * 0.25) * (1.0 - ratio)
                    
                    # Tapering width: narrower at start, wider at cursor, modulated by wave
                    width = self.trail_width * (0.15 + 0.85 * ratio) + wave
                    if width < 1.0:
                        width = 1.0
                    
                    # Interpolated color between trail_color and halo_color
                    r = int(c1.red() * (1 - ratio) + c2.red() * ratio)
                    g = int(c1.green() * (1 - ratio) + c2.green() * ratio)
                    b = int(c1.blue() * (1 - ratio) + c2.blue() * ratio)
                    alpha = int(self.opacity_val * ratio)
                    
                    # ── Neon Glow passes ──────────────────────────────────
                    # Pass 1: Wide outer glow (very faint)
                    glow1_pen = QPen(QColor(r, g, b, int(alpha * 0.15)))
                    glow1_pen.setWidthF(width * 2.5)
                    glow1_pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(glow1_pen)
                    painter.drawLine(p1, p2)
                    
                    # Pass 2: Medium glow
                    glow2_pen = QPen(QColor(r, g, b, int(alpha * 0.35)))
                    glow2_pen.setWidthF(width * 1.6)
                    glow2_pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(glow2_pen)
                    painter.drawLine(p1, p2)
                    
                    # Pass 3: Core line
                    core_pen = QPen(QColor(r, g, b, alpha))
                    core_pen.setWidthF(width)
                    core_pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(core_pen)
                    painter.drawLine(p1, p2)

        # ── halo ───────────────────────────────────────────────────────────
        if self.trail_points and self.enable_halo:
            cur = self.trail_points[-1]
            hc = self.halo_color
            for r_off, alpha_factor in [(6, 0.15), (3, 0.30), (0, 1.0)]:
                r = self.halo_radius + r_off
                glow_pen = QPen(QColor(hc.red(), hc.green(), hc.blue(),
                                       int(self.opacity_val * alpha_factor)))
                glow_pen.setWidth(2)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    QRectF(cur.x() - r, cur.y() - r, r * 2, r * 2)
                )

        # ── ripples ────────────────────────────────────────────────────────
        for r in self.ripples:
            painter.save()
            color = r["color"]
            # Main expanding ring
            pen = QPen(QColor(color.red(), color.green(), color.blue(), int(r["opacity"] * 255)))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            radius = r["radius"]
            painter.drawEllipse(QRectF(r["pos"].x() - radius, r["pos"].y() - radius, radius * 2, radius * 2))
            
            # Inner ring
            pen.setWidth(1)
            pen.setColor(QColor(color.red(), color.green(), color.blue(), int(r["opacity"] * 120)))
            painter.setPen(pen)
            inner_radius = radius * 0.6
            painter.drawEllipse(QRectF(r["pos"].x() - inner_radius, r["pos"].y() - inner_radius, inner_radius * 2, inner_radius * 2))
            painter.restore()

        # ── particles ──────────────────────────────────────────────────────
        for p in self.particles:
            painter.save()
            color = p["color"]
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), int(p["life"] * 255)))
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            radius = p["radius"]
            painter.drawEllipse(QRectF(p["x"] - radius, p["y"] - radius, radius * 2, radius * 2))
            painter.restore()

    # ── public API ───────────────────────────────────────────────────────────
    def load_texture(self, file_path: str):
        if not os.path.isfile(file_path):
            return False
        pix = QPixmap(file_path)
        if pix.isNull():
            return False
        self.trail_texture_path = file_path
        self.trail_texture = pix
        return True

    def clear_texture(self):
        self.trail_texture_path = None
        self.trail_texture = None

    def apply_config(self, cfg: dict):
        self.enable_trails    = cfg.get("enable_trails", True)
        self.enable_halo      = cfg.get("halo_enabled", True)
        self.opacity_val      = cfg.get("opacity", 220)
        self.max_trail_length = cfg.get("trail_length", 30)
        self.halo_radius      = cfg.get("halo_radius", 24)
        self.trail_width      = cfg.get("trail_width", 7)
        tc = cfg.get("trail_color", [255, 30, 67])
        hc = cfg.get("halo_color",  [40, 230, 80])
        self.trail_color = QColor(*tc)
        self.halo_color  = QColor(*hc)
        tp = cfg.get("trail_texture_path", "")
        if tp:
            self.load_texture(tp)
        else:
            self.clear_texture()

    def to_config_dict(self) -> dict:
        return {
            "enable_trails":      self.enable_trails,
            "halo_enabled":       self.enable_halo,
            "opacity":            self.opacity_val,
            "trail_length":       self.max_trail_length,
            "halo_radius":        self.halo_radius,
            "trail_width":        self.trail_width,
            "trail_color":        [self.trail_color.red(),
                                   self.trail_color.green(),
                                   self.trail_color.blue()],
            "halo_color":         [self.halo_color.red(),
                                   self.halo_color.green(),
                                   self.halo_color.blue()],
            "trail_texture_path": self.trail_texture_path or "",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Animated toggle switch
# ─────────────────────────────────────────────────────────────────────────────
class AnimatedToggle(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 24)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if self.isChecked():
            p.setBrush(QColor("#3a86ff"))
            p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(self.width() - 21, 3, 18, 18)
        else:
            p.setBrush(QColor("#4e5058"))
            p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
            p.setBrush(QColor("#b5bac1"))
            p.drawEllipse(3, 3, 18, 18)


# ─────────────────────────────────────────────────────────────────────────────
# Colour swatch button
# ─────────────────────────────────────────────────────────────────────────────
class ColorSwatchButton(QPushButton):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, label: str, color: QColor, parent=None):
        super().__init__(parent)
        self._color = color
        self._label = label
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self._refresh_style()
        self.clicked.connect(self._pick)

    def _refresh_style(self):
        r, g, b = self._color.red(), self._color.green(), self._color.blue()
        luma = 0.299*r + 0.587*g + 0.114*b
        fg = "#000000" if luma > 128 else "#ffffff"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r},{g},{b});
                color: {fg};
                border: 1px solid #444;
                border-radius: 6px;
                font-size: 12px;
                padding: 0 10px;
            }}
            QPushButton:hover {{ border-color: #ffffff; }}
        """)
        self.setText(self._label)

    def _pick(self):
        c = QColorDialog.getColor(self._color, self, self._label)
        if c.isValid():
            self._color = c
            self._refresh_style()
            self.colorChanged.emit(c)

    def color(self) -> QColor:
        return self._color

    def set_color(self, c: QColor):
        self._color = c
        self._refresh_style()


# ─────────────────────────────────────────────────────────────────────────────
# FA icon label helper
# ─────────────────────────────────────────────────────────────────────────────
def _fa_label(icon_char: str, size=14, color="#a3a9b2") -> QLabel:
    lbl = QLabel(icon_char)
    lbl.setFont(fa_font(size))
    lbl.setStyleSheet(f"color: {color};")
    lbl.setFixedWidth(22)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl

def _fa_btn(icon_char: str, text: str, size=13) -> QPushButton:
    """Button with a FA icon prefix."""
    btn = QPushButton()
    btn.setFixedHeight(40)
    # Use two labels approach via custom widget? Simpler: just set text with icon char
    # We set the font manually on a custom label inside, but QPushButton doesn't
    # easily mix fonts. Use a workaround: rich text label on top.
    btn.setText(f"  {text}")
    btn.setProperty("fa_icon", icon_char)
    return btn


# ─────────────────────────────────────────────────────────────────────────────
# Labelled slider row helper
# ─────────────────────────────────────────────────────────────────────────────
def _make_slider_row(label: str, lo: int, hi: int, val: int,
                     changed_cb, unit: str = "",
                     icon: str = "") -> tuple[QSlider, QWidget]:
    container = QWidget()
    vl = QVBoxLayout(container)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(4)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)

    if icon:
        row.addWidget(_fa_label(icon, 12))

    lbl = QLabel(label)
    lbl.setStyleSheet("color:#a3a9b2; font-size:12px;")
    val_lbl = QLabel(f"{val}{unit}")
    val_lbl.setStyleSheet("color:#ffffff; font-size:12px;")
    val_lbl.setFixedWidth(40)
    val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(lbl)
    row.addStretch()
    row.addWidget(val_lbl)
    vl.addLayout(row)

    slider = QSlider(Qt.Horizontal)
    slider.setRange(lo, hi)
    slider.setValue(val)
    slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v}{unit}"))
    slider.valueChanged.connect(changed_cb)
    vl.addWidget(slider)

    return slider, container


# ─────────────────────────────────────────────────────────────────────────────
# Main UI window
# ─────────────────────────────────────────────────────────────────────────────
class CustomizerHubUI(QMainWindow):

    DARK_STYLE = """
        QMainWindow, QWidget { background-color: #1a1b1e; }
        QTabWidget::pane {
            border: 1px solid #2b2d31;
            background: #1a1b1e;
            border-radius: 8px;
        }
        QTabBar::tab {
            background: #222428; color: #8a8f98;
            padding: 9px 18px; margin-right: 4px; font-size: 13px;
            border-top-left-radius: 6px; border-top-right-radius: 6px;
        }
        QTabBar::tab:selected { background: #2b2d31; color: #ffffff; font-weight: bold; }
        QTabBar::tab:hover    { background: #2b2d31; color: #cccccc; }
        QLabel  { color: #a3a9b2; font-size: 13px; font-family: 'Segoe UI', Arial; }
        QSlider::groove:horizontal {
            border: none; height: 5px; background: #2b2d31; border-radius: 2px;
        }
        QSlider::sub-page:horizontal { background: #3a86ff; border-radius: 2px; }
        QSlider::handle:horizontal {
            background: #ffffff; border: 2px solid #3a86ff;
            width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
        }
        QComboBox {
            background: #222428; border: 1px solid #2b2d31;
            border-radius: 6px; padding: 6px 12px;
            color: #ffffff; font-size: 13px;
        }
        QComboBox::drop-down { width: 22px; border: none; }
        QComboBox QAbstractItemView {
            background: #222428; color: #ffffff;
            selection-background-color: #3a86ff;
        }
        QCheckBox { color: #ffffff; font-size: 13px; }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            background: #222428; border: 1px solid #4e5058; border-radius: 3px;
        }
        QCheckBox::indicator:checked { background: #3a86ff; border-color: #3a86ff; }
        QPushButton {
            background: #222428; color: #ffffff;
            border: 1px solid #2b2d31; border-radius: 6px;
            padding: 8px 14px; font-size: 13px;
        }
        QPushButton:hover   { background: #2b2d31; border-color: #3a86ff; }
        QPushButton:pressed { background: #1a1b1e; }
        QScrollArea { border: none; background: transparent; }
        QScrollBar:vertical { background: #1a1b1e; width: 6px; }
        QScrollBar::handle:vertical { background: #3a86ff; border-radius: 3px; }
    """

    LIGHT_STYLE = """
        QMainWindow, QWidget { background-color: #f0f2f5; }
        QTabWidget::pane {
            border: 1px solid #d0d3d8; background: #f0f2f5; border-radius: 8px;
        }
        QTabBar::tab {
            background: #e0e3e8; color: #555; padding: 9px 18px;
            margin-right: 4px; font-size: 13px;
            border-top-left-radius: 6px; border-top-right-radius: 6px;
        }
        QTabBar::tab:selected { background: #ffffff; color: #000; font-weight: bold; }
        QLabel  { color: #333333; font-size: 13px; }
        QSlider::groove:horizontal {
            border: none; height: 5px; background: #d0d3d8; border-radius: 2px;
        }
        QSlider::sub-page:horizontal { background: #3a86ff; border-radius: 2px; }
        QSlider::handle:horizontal {
            background: #ffffff; border: 2px solid #3a86ff;
            width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
        }
        QComboBox {
            background: #ffffff; border: 1px solid #d0d3d8;
            border-radius: 6px; padding: 6px 12px; color: #000; font-size: 13px;
        }
        QCheckBox { color: #000; font-size: 13px; }
        QPushButton {
            background: #e0e3e8; color: #000;
            border: 1px solid #c0c3c8; border-radius: 6px;
            padding: 8px 14px; font-size: 13px;
        }
        QPushButton:hover { background: #d0d3d8; border-color: #3a86ff; }
        QScrollArea { border: none; background: transparent; }
    """

    def __init__(self, overlay: UltimateMouseOverlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("✨ Customize Mouse")
        self.setFixedSize(480, 520)
        self.setWindowIcon(self._make_icon())
        self.setStyleSheet(self.DARK_STYLE)

        self._cfg = _load_config()
        self.overlay.apply_config(self._cfg)

        self._build_ui()
        self._build_tray()
        self._load_cfg_to_ui(self._cfg)

    # ── icon ──────────────────────────────────────────────────────────────────
    def _make_icon(self) -> QIcon:
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#3a86ff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(10, 10, 12, 12)
        p.end()
        return QIcon(pix)

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        tabs = QTabWidget()
        # Tab labels use FA icons via unicode in QLabel but QTabBar needs plain text.
        # We use unicode chars directly (they render if FA font is set on the tab bar).
        tabs.addTab(self._make_trails_tab(),     f"{FA['palette']}  Trail")
        tabs.addTab(self._make_halo_tab(),       f"{FA['sun']}  Halo")
        tabs.addTab(self._make_general_tab(),    f"{FA['gear']}  General")
        tabs.addTab(self._make_maintenance_tab(),f"{FA['wrench']}  Maintenance")

        # Apply FA font to tab bar so icons render
        tab_bar = tabs.tabBar()
        tab_bar.setFont(fa_font(12))

        tabs.setCurrentIndex(0)
        self.setCentralWidget(tabs)

    # ── helper: icon+text row label ───────────────────────────────────────────
    def _icon_label_row(self, layout, icon_char, text):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(_fa_label(icon_char, 13, "#3a86ff"))
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#a3a9b2; font-size:13px;")
        row.addWidget(lbl)
        row.addStretch()
        layout.addLayout(row)

    # ── Trail tab ─────────────────────────────────────────────────────────────
    def _make_trails_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Enable toggle
        row = QHBoxLayout()
        row.addWidget(_fa_label(FA["eye"], 13, "#3a86ff"))
        row.addWidget(QLabel("Enable Trails"))
        self.enable_trails_toggle = AnimatedToggle()
        self.enable_trails_toggle.setChecked(True)
        self.enable_trails_toggle.stateChanged.connect(
            lambda s: setattr(self.overlay, "enable_trails", bool(s))
        )
        row.addStretch()
        row.addWidget(self.enable_trails_toggle)
        layout.addLayout(row)

        self._div(layout)

        # Cursor type
        self._icon_label_row(layout, FA["trail"], "Cursor Type")
        self.cursor_combo = QComboBox()
        self.cursor_combo.addItems(["Custom Cursor", "Standard Arrow", "Crosshair"])
        layout.addWidget(self.cursor_combo)

        # Trail color
        self._icon_label_row(layout, FA["palette"], "Trail Colour")
        self.trail_color_btn = ColorSwatchButton(
            "  Choose Trail Colour", self.overlay.trail_color)
        self.trail_color_btn.colorChanged.connect(
            lambda c: setattr(self.overlay, "trail_color", c))
        layout.addWidget(self.trail_color_btn)

        # Sliders
        self.opacity_slider, opw = _make_slider_row(
            "Opacity", 30, 255, self.overlay.opacity_val,
            lambda v: setattr(self.overlay, "opacity_val", v))
        layout.addWidget(opw)

        self.length_slider, lnw = _make_slider_row(
            "Trail Length", 5, 80, self.overlay.max_trail_length,
            lambda v: setattr(self.overlay, "max_trail_length", v), " pts")
        layout.addWidget(lnw)

        self.trail_width_slider, tww = _make_slider_row(
            "Trail Width", 2, 20, self.overlay.trail_width,
            lambda v: setattr(self.overlay, "trail_width", v), " px")
        layout.addWidget(tww)

        self._div(layout)

        # Texture
        tex_row = QHBoxLayout()
        self.upload_btn = QPushButton(f"{FA['upload']}  Upload Texture")
        self.upload_btn.setFont(fa_font(12))
        self.upload_btn.clicked.connect(self._upload_texture)
        self.clear_tex_btn = QPushButton(f"{FA['times']}  Clear")
        self.clear_tex_btn.setFont(fa_font(12))
        self.clear_tex_btn.setFixedWidth(90)
        self.clear_tex_btn.clicked.connect(self._clear_texture)
        tex_row.addWidget(self.upload_btn)
        tex_row.addWidget(self.clear_tex_btn)
        layout.addLayout(tex_row)

        self.tex_label = QLabel("No texture loaded")
        self.tex_label.setStyleSheet("color:#555; font-size:11px;")
        self.tex_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tex_label)

        layout.addStretch()
        return w

    # ── Halo tab ──────────────────────────────────────────────────────────────
    def _make_halo_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        row = QHBoxLayout()
        row.addWidget(_fa_label(FA["sun"], 13, "#3a86ff"))
        row.addWidget(QLabel("Enable Halo"))
        self.overlay_toggle = AnimatedToggle()
        self.overlay_toggle.setChecked(True)
        self.overlay_toggle.stateChanged.connect(
            lambda s: setattr(self.overlay, "enable_halo", bool(s))
        )
        row.addStretch()
        row.addWidget(self.overlay_toggle)
        layout.addLayout(row)

        self._div(layout)

        self._icon_label_row(layout, FA["palette"], "Halo Colour")
        self.halo_color_btn = ColorSwatchButton(
            "  Choose Halo Colour", self.overlay.halo_color)
        self.halo_color_btn.colorChanged.connect(
            lambda c: setattr(self.overlay, "halo_color", c))
        layout.addWidget(self.halo_color_btn)

        self.halo_radius_slider, hrw = _make_slider_row(
            "Halo Radius", 10, 80, self.overlay.halo_radius,
            lambda v: setattr(self.overlay, "halo_radius", v), " px")
        layout.addWidget(hrw)

        layout.addStretch()
        return w

    # ── General tab ───────────────────────────────────────────────────────────
    def _make_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self._icon_label_row(layout, FA["gear"], "Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        layout.addWidget(self.theme_combo)

        self._div(layout)

        # Run in background
        row = QHBoxLayout()
        row.addWidget(_fa_label(FA["tray_hide"], 13, "#3a86ff"))
        row.addWidget(QLabel("Run in Background (hide to tray)"))
        self.background_checkbox = AnimatedToggle()
        self.background_checkbox.setChecked(True)   # ← default ON
        self.background_checkbox.stateChanged.connect(self._toggle_background)
        row.addStretch()
        row.addWidget(self.background_checkbox)
        layout.addLayout(row)

        hint = QLabel("When enabled the window hides to the system tray.\n"
                       "Right-click the tray icon to restore.")
        hint.setStyleSheet("color:#555; font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return w

    # ── Maintenance tab ───────────────────────────────────────────────────────
    def _make_maintenance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        save_btn  = QPushButton(f"{FA['save']}   Save Configuration")
        load_btn  = QPushButton(f"{FA['folder']}   Load Configuration")
        reset_btn = QPushButton(f"{FA['rotate']}   Reset to Defaults")

        for btn in [save_btn, load_btn, reset_btn]:
            btn.setFont(fa_font(12))

        for btn, cb in [(save_btn, self.save_config),
                        (load_btn, self.load_config),
                        (reset_btn, self.reset_defaults)]:
            btn.setFixedHeight(40)
            btn.clicked.connect(cb)
            layout.addWidget(btn)

        self._div(layout)

        cfg_path = os.path.join(_config_dir(), "settings.json")
        info = QLabel(f"Config file:\n{cfg_path}")
        info.setStyleSheet("color:#555; font-size:11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        return w

    # ── tray icon ─────────────────────────────────────────────────────────────
    def _build_tray(self):
        self.tray_icon = QSystemTrayIcon(self._make_icon(), self)
        menu = QMenu()

        items = [
            (f"{FA['tray_show']}  Show UI",          self.show),
            (f"{FA['tray_hide']}  Hide UI",           self.hide),
            (f"{FA['tray_toggle']}  Toggle Overlay",  self._toggle_overlay_from_tray),
            (None, None),
            (f"{FA['tray_exit']}  Exit",              QApplication.instance().quit),
        ]
        for label, fn in items:
            if label is None:
                menu.addSeparator()
            else:
                act = QAction(label, self)
                act.setFont(fa_font(10))
                act.triggered.connect(fn)
                menu.addAction(act)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "Customize Mouse",
            "Running in the background. Right-click tray icon to open.",
            QSystemTrayIcon.Information, 3000
        )

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()

    # ─────────────────────────────────────────────────────────────────────────
    # Slot helpers
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _div(layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #2b2d31;")
        layout.addWidget(line)

    def _upload_texture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Texture Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            ok = self.overlay.load_texture(path)
            if ok:
                self.tex_label.setText(f"{FA['eye']} {os.path.basename(path)}")
                self.tex_label.setStyleSheet("color:#3a86ff; font-size:11px;")
            else:
                QMessageBox.warning(self, "Error", "Failed to load texture.")

    def _clear_texture(self):
        self.overlay.clear_texture()
        self.tex_label.setText("No texture loaded")
        self.tex_label.setStyleSheet("color:#555; font-size:11px;")

    def _toggle_background(self, state):
        if state:
            self.hide()

    def _toggle_overlay_from_tray(self):
        new = not self.overlay.enable_trails
        self.overlay.enable_trails = new
        self.overlay.enable_halo   = new
        self.enable_trails_toggle.setChecked(new)
        self.overlay_toggle.setChecked(new)

    def _apply_theme(self, name: str):
        if name == "Dark":
            self.setStyleSheet(self.DARK_STYLE)
        else:
            self.setStyleSheet(self.LIGHT_STYLE)

    # ─────────────────────────────────────────────────────────────────────────
    # Config save / load / reset
    # ─────────────────────────────────────────────────────────────────────────
    def _collect_cfg(self) -> dict:
        cfg = _default_config()
        cfg.update(self.overlay.to_config_dict())
        cfg["cursor_type"]    = self.cursor_combo.currentText()
        cfg["theme"]          = self.theme_combo.currentText()
        cfg["run_background"] = self.background_checkbox.isChecked()
        return cfg

    def _load_cfg_to_ui(self, cfg: dict):
        self.enable_trails_toggle.setChecked(cfg.get("enable_trails", True))
        idx = self.cursor_combo.findText(cfg.get("cursor_type", "Custom Cursor"))
        if idx >= 0:
            self.cursor_combo.setCurrentIndex(idx)
        tc = cfg.get("trail_color", [255, 30, 67])
        self.trail_color_btn.set_color(QColor(*tc))
        self.opacity_slider.setValue(cfg.get("opacity", 220))
        self.length_slider.setValue(cfg.get("trail_length", 30))
        self.trail_width_slider.setValue(cfg.get("trail_width", 7))
        tp = cfg.get("trail_texture_path", "")
        if tp and os.path.isfile(tp):
            self.tex_label.setText(f"{FA['eye']} {os.path.basename(tp)}")
            self.tex_label.setStyleSheet("color:#3a86ff; font-size:11px;")
        self.overlay_toggle.setChecked(cfg.get("halo_enabled", True))
        hc = cfg.get("halo_color", [40, 230, 80])
        self.halo_color_btn.set_color(QColor(*hc))
        self.halo_radius_slider.setValue(cfg.get("halo_radius", 24))
        self.theme_combo.setCurrentText(cfg.get("theme", "Dark"))
        self._apply_theme(cfg.get("theme", "Dark"))
        run_bg = cfg.get("run_background", True)
        self.background_checkbox.setChecked(run_bg)
        if run_bg:
            self.hide()   # ← start hidden in tray

    def save_config(self):
        try:
            cfg = self._collect_cfg()
            _save_config(cfg)
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", _config_dir(), "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            full = _default_config()
            full.update(cfg)
            self.overlay.apply_config(full)
            self._load_cfg_to_ui(full)
            QMessageBox.information(self, "Loaded", "Configuration loaded.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

    def reset_defaults(self):
        reply = QMessageBox.question(
            self, "Reset", "Reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        cfg = _default_config()
        self.overlay.apply_config(cfg)
        self._load_cfg_to_ui(cfg)
        self._clear_texture()

    # ── Close → hide to tray if background mode ───────────────────────────────
    def closeEvent(self, event):
        if self.background_checkbox.isChecked():
            event.ignore()
            self.hide()
        else:
            event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # stay alive when main window closes

    # Load FA font as early as possible
    _ensure_fa_font()

    overlay = UltimateMouseOverlay()
    overlay.show()

    ui = CustomizerHubUI(overlay)
    # Window starts hidden (tray) or visible based on saved config.
    # _load_cfg_to_ui() inside __init__ handles this automatically.

    sys.exit(app.exec_())
