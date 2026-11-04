# -*- coding: utf-8 -*-
"""
NightCoop Manager - GUI (PyQt6)
Dark neon theme (black + yellow), EN/SV/RU, single-file EXE via PyInstaller.
"""

import sys
import os
import time
import threading
import tempfile
import traceback

# PyInstaller one-file resource path helper
def resource_path(relative_path):
    """Absolute path to a bundled resource (works frozen and from source)."""
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ---------------------------------------------------------------------------
# Session log (kept in %TEMP%, never next to the EXE)
# ---------------------------------------------------------------------------

LOG_PATH = None
LOG_DIR = None


def _init_log():
    """Create a session log file in the temporary folder."""
    global LOG_PATH, LOG_DIR
    try:
        LOG_DIR = os.path.join(tempfile.gettempdir(), "NightCoopManager")
        os.makedirs(LOG_DIR, exist_ok=True)
        LOG_PATH = os.path.join(
            LOG_DIR, time.strftime("manager-%Y%m%d-%H%M%S.log")
        )
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(f"NightCoop Manager log\n")
            f.write(f"started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"python: {sys.version.split()[0]}\n")
            f.write(f"platform: {sys.platform}\n")
            f.write("-" * 60 + "\n")
    except OSError:
        LOG_PATH = None


def log(message):
    """Append a timestamped line to the session log."""
    if not LOG_PATH:
        return
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")
    except OSError:
        pass


def log_exception(exc_type, exc_value, exc_tb):
    """sys.excepthook replacement - write the traceback into the log."""
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write("\n=== UNHANDLED EXCEPTION ===\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except OSError:
            pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar,
    QGroupBox, QMessageBox, QFileDialog, QCheckBox, QFrame,
    QDialog, QTextBrowser
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QUrl, QLocale, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QDesktopServices, QIcon, QPainter, QPen, QPixmap
)

from translations import (
    gettext, LANGUAGE_FLAGS, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
)
import updater


# ---------------------------------------------------------------------------
# Theme / StyleSheet  (black + neon yellow + cyan, sharp edges)
# ---------------------------------------------------------------------------

ACCENT = "#FFE500"       # neon yellow
ACCENT_DIM = "#C9B400"
CYAN = "#00E5FF"
TEXT = "#EDEDED"
MUTED = "#8C8C8C"
BORDER = "#262626"

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #000000;
    color: #EDEDED;
    font-family: "Bahnschrift", "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}
QWidget#surface {
    background-color: #050505;
}
QGroupBox {
    border: 1px solid #1F1F1F;
    border-radius: 0px;
    margin-top: 14px;
    padding: 12px 12px 12px 12px;
    color: #EDEDED;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px 0 8px;
    color: #FFE500;
    font-weight: 700;
    letter-spacing: 1px;
}
QLineEdit {
    background-color: #0A0A0A;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    padding: 7px;
    color: #EDEDED;
    selection-background-color: #FFE500;
    selection-color: #000000;
}
QLineEdit:focus {
    border: 1px solid #FFE500;
}
QPushButton {
    background-color: #0A0A0A;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    color: #CFCFCF;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    color: #FFE500;
    border: 1px solid #FFE500;
}
QPushButton:pressed {
    background-color: #141400;
}
QPushButton:disabled {
    border: 1px solid #1A1A1A;
    color: #4A4A4A;
    background-color: #060606;
}
QPushButton#primary {
    background-color: #FFE500;
    border: 1px solid #FFE500;
    color: #000000;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 12px 16px;
}
QPushButton#primary:hover {
    background-color: #FFF45C;
    border: 1px solid #FFF45C;
    color: #000000;
}
QPushButton#primary:pressed {
    background-color: #C9B400;
}
QPushButton#primary:disabled {
    background-color: #0D0D0D;
    border: 1px solid #1E1E1E;
    color: #4A4A4A;
}
QPushButton#secondary {
    background-color: transparent;
    border: 1px solid #2A2A2A;
    color: #9A9A9A;
    padding: 7px 12px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#secondary:hover {
    border: 1px solid #FFE500;
    color: #FFE500;
}
QPushButton#secondary:disabled {
    border: 1px solid #161616;
    color: #3F3F3F;
}
QPushButton#flag {
    background-color: transparent;
    border: 1px solid #262626;
    padding: 2px;
}
QPushButton#flag:hover {
    border: 1px solid #4A4A4A;
}
QPushButton#flag[active="true"] {
    border: 2px solid #FFE500;
}
QPushButton#segment {
    background-color: #0A0A0A;
    border: 1px solid #2A2A2A;
    color: #9A9A9A;
    padding: 6px 14px;
    font-weight: 700;
    min-width: 56px;
}
QPushButton#segment:hover {
    border: 1px solid #FFE500;
    color: #FFE500;
}
QPushButton#segment:checked {
    background-color: #FFE500;
    border: 1px solid #FFE500;
    color: #000000;
}
QPushButton#changelog {
    background-color: transparent;
    border: 1px solid #2A2A2A;
    color: #9A9A9A;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#changelog:hover {
    border: 1px solid #00E5FF;
    color: #00E5FF;
}
QComboBox {
    background-color: #0A0A0A;
    border: 1px solid #2A2A2A;
    border-radius: 0px;
    padding: 6px 8px;
    color: #EDEDED;
}
QComboBox:focus {
    border: 1px solid #FFE500;
}
QComboBox QAbstractItemView {
    background-color: #0A0A0A;
    border: 1px solid #2A2A2A;
    color: #EDEDED;
    outline: none;
    selection-background-color: #FFE500;
    selection-color: #000000;
}
QProgressBar {
    border: none;
    border-radius: 0px;
    text-align: center;
    color: #000000;
    background-color: #141414;
    height: 6px;
    max-height: 6px;
}
QProgressBar::chunk {
    background-color: #FFE500;
    border-radius: 0px;
}
QCheckBox {
    color: #9A9A9A;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #3A3A3A;
    background-color: #0A0A0A;
}
QCheckBox::indicator:checked {
    background-color: #FFE500;
    border: 1px solid #FFE500;
}
QLabel {
    color: #EDEDED;
}
QLabel#sectionLabel {
    color: #FFE500;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel#mutedLabel {
    color: #8C8C8C;
    font-size: 11px;
}
QLabel#statusInstalled {
    color: #FFFFFF;
    font-size: 19px;
    font-weight: 700;
}
QLabel#statusAvailable {
    color: #00E5FF;
    font-size: 12px;
    font-weight: 600;
}
QToolTip {
    background-color: #0A0A0A;
    color: #EDEDED;
    border: 1px solid #FFE500;
    padding: 4px;
}
"""


# ---------------------------------------------------------------------------
# Decorative widgets (grid background, corner-bracket panel)
# ---------------------------------------------------------------------------

class GridBackground(QWidget):
    """Black surface with a faint technical grid, like the site background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("surface")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))

        pen = QPen(QColor("#141414"))
        pen.setWidth(1)
        painter.setPen(pen)

        step = 44
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

        painter.end()
        super().paintEvent(event)


class Panel(QGroupBox):
    """Border-box with small accent corner brackets, like the site panels."""

    def __init__(self, title="", accent=ACCENT, parent=None):
        super().__init__(title, parent)
        self._accent = accent

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        pen = QPen(QColor(self._accent))
        pen.setWidth(2)
        painter.setPen(pen)

        w, h = self.width() - 1, self.height() - 1
        arm = 9

        # four corner brackets
        painter.drawLine(0, 0, arm, 0)
        painter.drawLine(0, 0, 0, arm)

        painter.drawLine(w - arm, 0, w, 0)
        painter.drawLine(w, 0, w, arm)

        painter.drawLine(0, h - arm, 0, h)
        painter.drawLine(0, h, arm, h)

        painter.drawLine(w, h - arm, w, h)
        painter.drawLine(w - arm, h, w, h)

        painter.end()


# ---------------------------------------------------------------------------
# Clickable link label
# ---------------------------------------------------------------------------

class ClickableLabel(QLabel):
    """A label that opens a URL when clicked.

    Font size/weight are set through QFont once, so hovering never changes the
    label metrics (only the colour and underline).
    """

    def __init__(self, text, url, parent=None, color=None, size=10, weight=700):
        super().__init__(text, parent)
        self.url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = color or ACCENT
        self._font_px = size
        self._weight = weight
        self._refresh_style(hover=False)

    def _refresh_style(self, hover):
        color = "#FFFFFF" if hover else self._color
        decoration = "underline" if hover else "none"
        # font-size stays the same in both states, so the label never resizes
        self.setStyleSheet(
            f"color: {color};"
            f" font-size: {self._font_px}px;"
            f" font-weight: {self._weight};"
            f" text-decoration: {decoration};"
        )

    def enterEvent(self, event):
        self._refresh_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._refresh_style(hover=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url))
        super().mousePressEvent(event)


def tracked_font(widget, size=13, weight=600, spacing=1.0, uppercase=False):
    """Apply a letter-spaced font (QSS cannot do letter-spacing)."""
    font = widget.font()
    font.setPointSize(size)
    font.setWeight(QFont.Weight(weight))
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    if uppercase:
        font.setCapitalization(QFont.Capitalization.AllUppercase)
    widget.setFont(font)


# ---------------------------------------------------------------------------
# Worker thread - install / update / uninstall
# ---------------------------------------------------------------------------

class UpdateWorker(QThread):
    """Background worker for install/update/uninstall operations."""

    progress = pyqtSignal(int, int)   # downloaded, total
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, operation, game_path, game_version="", mod_version="latest",
                 base_url="", cancel_event=None):
        super().__init__()
        self.operation = operation        # "install", "update", "uninstall"
        self.game_path = game_path
        self.game_version = game_version
        self.mod_version = mod_version    # "latest" or specific version string
        self.base_url = base_url
        self.cancel_event = cancel_event

    def run(self):
        try:
            if self.operation == "uninstall":
                updater.uninstall_mod(self.game_path, log_callback=self.log.emit)
                self.finished.emit(True, "mod_removed")
                return

            # install or update
            def prog(downloaded, total):
                self.progress.emit(downloaded, total)

            target_version = None if self.mod_version == "latest" else self.mod_version
            version = updater.install_mod(
                self.game_path,
                self.game_version,
                target_version=target_version,
                base_url=self.base_url,
                progress_callback=prog,
                log_callback=self.log.emit,
                cancel_event=self.cancel_event,
            )
            self.finished.emit(True, f"mod_installed:{version}")
        except updater.OperationCancelled:
            self.finished.emit(False, "cancelled")
        except Exception as e:
            self.finished.emit(False, str(e))


# ---------------------------------------------------------------------------
# Worker thread - fetch releases + versions list
# ---------------------------------------------------------------------------

class VersionsWorker(QThread):
    """Background worker to fetch releases.json and list versions for a game version."""

    finished = pyqtSignal(object, str)   # releases_dict, error_message

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url

    def run(self):
        try:
            releases = updater.fetch_releases(self.base_url)
            self.finished.emit(releases, "")
        except Exception as e:
            self.finished.emit(None, str(e))


# ---------------------------------------------------------------------------
# Worker thread - check for updates
# ---------------------------------------------------------------------------

class VersionCheckWorker(QThread):
    """Background worker to check for updates."""

    result = pyqtSignal(dict)   # {"available": bool, "version": str, "message": str}
    error = pyqtSignal(str)

    def __init__(self, game_path, game_version, base_url):
        super().__init__()
        self.game_path = game_path
        self.game_version = game_version
        self.base_url = base_url

    def run(self):
        try:
            releases = updater.fetch_releases(self.base_url)
            release, file_info = updater.find_release_for_game(releases, self.game_version)
            installed_version = updater.get_installed_version(self.game_path)
            mod_present = updater.is_mod_installed(self.game_path)

            if installed_version:
                installed_label = installed_version
            elif mod_present:
                installed_label = "unknown"
            else:
                installed_label = "not_installed"

            if not release or not file_info:
                self.result.emit({
                    "available": False,
                    "version": "",
                    "installed": installed_label,
                    "message": "no_mod_for_version",
                })
                return

            online_version = release.get("version", "unknown")

            if installed_version:
                # We know the installed version — compare it
                available = (installed_version != online_version)
            else:
                # Nothing installed (or version unknown) — there is always
                # something to install/refresh, so keep the action enabled.
                available = True

            self.result.emit({
                "available": available,
                "version": online_version,
                "installed": installed_label,
                "message": "update_available" if available else "no_update",
            })
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class NightCoopManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.lang = self._system_language()
        self.lang_manual = False

        # Fully portable: nothing is persisted between runs
        self.game_path = ""
        self.game_version = "2.5"
        self.mod_version = "latest"
        self.base_url = updater.BASE_URL

        self.worker = None
        self.version_worker = None
        self.versions_worker = None
        self.releases_data = None
        self._last_check_state = None
        self.auto_check_enabled = True
        self._versions_generation = 0
        self._bg_workers = []
        self._cancel_event = None
        self._closing = False

        self.setWindowTitle(gettext("app_title", self.lang))
        self.setMinimumSize(540, 790)
        self.resize(600, 900)
        self.setStyleSheet(DARK_STYLE)

        # Debounce for manual path typing
        self._path_timer = QTimer(self)
        self._path_timer.setSingleShot(True)
        self._path_timer.setInterval(450)
        self._path_timer.timeout.connect(self._path_settled)

        # Window icon - set both on window and application
        icon_path = resource_path("icon.ico")
        if os.path.isfile(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)

        self._build_ui()
        self._apply_lang()

        log("window created")
        log(f"language: {self.lang}")

        # Auto-detect game path on startup
        QApplication.instance().processEvents()
        self._auto_detect_startup()

        # Auto-check on startup (default ON)
        if self.auto_check_enabled:
            self.auto_check_cb.setChecked(True)
            QApplication.instance().processEvents()
            self._check_updates(automatic=True)

    # ------------------------------------------------------------------
    # System language
    # ------------------------------------------------------------------
    @staticmethod
    def _system_language():
        """Return the supported language matching the Windows UI language.

        Tries the native Windows API first (works reliably in a frozen EXE),
        then QLocale, then Python's locale module.
        """
        # Primary language IDs (LANGID low 10 bits)
        win_map = {0x19: "ru", 0x1D: "sv", 0x09: "en"}

        # 1) Native Windows API — most reliable for a PyInstaller build
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            for getter in (
                kernel32.GetUserDefaultUILanguage,
                kernel32.GetSystemDefaultUILanguage,
            ):
                try:
                    langid = getter()
                except Exception:
                    continue
                if langid:
                    primary = langid & 0x3FF
                    if primary in win_map:
                        return win_map[primary]
                    # unsupported UI language — fall through to other checks
                    break
        except Exception:
            pass

        # 2) Qt locale
        try:
            prefix = (QLocale.system().name() or "").split("_")[0].lower()
            if prefix in SUPPORTED_LANGUAGES:
                return prefix
        except Exception:
            pass

        # 3) Python locale
        try:
            import locale as _locale

            loc = _locale.getlocale()[0] or ""
            prefix = loc.split("_")[0].lower()
            if prefix in SUPPORTED_LANGUAGES:
                return prefix
        except Exception:
            pass

        return DEFAULT_LANGUAGE

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = GridBackground()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 16, 20, 14)
        main_layout.setSpacing(12)

        # ---------------- Top bar: logo + right-hand tag ----------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.logo_label = QLabel()
        logo_path = resource_path("logo.png")
        if os.path.isfile(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToWidth(
                190, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("NIGHTCOOP")
            self.logo_label.setStyleSheet(
                f"color: {ACCENT}; font-size: 20px; font-weight: 800;"
            )
        top_bar.addWidget(self.logo_label)
        top_bar.addStretch()

        # GitHub link
        self.github_label = ClickableLabel(
            "GitHub ↗",
            "https://github.com/N8mare777/nc-mod-manager",
            color=MUTED,
            size=11,
            weight=600,
        )
        top_bar.addWidget(self.github_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(top_bar)

        # thin accent underline (like the site's nav indicator)
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(f"background-color: {ACCENT}; border: none;")
        main_layout.addWidget(line)

        # ---------------- Game path ----------------
        self.path_group = Panel("", accent=ACCENT)
        path_layout = QVBoxLayout(self.path_group)
        path_layout.setContentsMargins(12, 10, 12, 12)
        path_layout.setSpacing(8)

        self.path_caption = QLabel()
        self.path_caption.setObjectName("sectionLabel")
        tracked_font(self.path_caption, size=8, weight=700, spacing=2.0, uppercase=True)
        path_layout.addWidget(self.path_caption)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(
            "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Cyberpunk 2077"
        )
        path_layout.addWidget(self.path_edit)

        path_btns = QHBoxLayout()
        path_btns.setSpacing(8)
        self.btn_browse = QPushButton()
        self.btn_detect = QPushButton()
        for btn in (self.btn_browse, self.btn_detect):
            btn.setObjectName("secondary")
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(self._button_font())
            path_btns.addWidget(btn)
        path_layout.addLayout(path_btns)

        main_layout.addWidget(self.path_group)

        # ---------------- Versions ----------------
        self.ver_group = Panel("", accent=ACCENT)
        ver_layout = QVBoxLayout(self.ver_group)
        ver_layout.setContentsMargins(12, 10, 12, 12)
        ver_layout.setSpacing(8)

        self.ver_caption = QLabel()
        self.ver_caption.setObjectName("sectionLabel")
        tracked_font(self.ver_caption, size=8, weight=700, spacing=2.0, uppercase=True)
        ver_layout.addWidget(self.ver_caption)

        row_mod = QHBoxLayout()
        row_mod.setSpacing(10)
        self.lbl_mod_ver = QLabel()
        self.lbl_mod_ver.setObjectName("mutedLabel")
        tracked_font(self.lbl_mod_ver, size=9, weight=600, spacing=1.2, uppercase=True)
        self.mod_ver_combo = QComboBox()
        self.mod_ver_combo.addItems([gettext("loading_versions", self.lang)])
        self.mod_ver_combo.setEnabled(False)
        self.mod_ver_combo.setMinimumHeight(32)
        self.mod_ver_combo.setMinimumWidth(170)
        self.mod_ver_combo.setMaximumWidth(210)
        row_mod.addWidget(self.lbl_mod_ver)
        # Half-width combo, the rest is left for the changelog button
        row_mod.addWidget(self.mod_ver_combo, 0)

        # Changelog of the selected build
        self.btn_changelog = QPushButton()
        self.btn_changelog.setObjectName("changelog")
        self.btn_changelog.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_changelog.setMinimumHeight(32)
        self.btn_changelog.setFont(self._button_font(size=8, weight=700, spacing=0.8))
        row_mod.addWidget(self.btn_changelog)
        row_mod.addStretch(1)

        ver_layout.addLayout(row_mod)

        row_game = QHBoxLayout()
        row_game.setSpacing(10)
        self.lbl_game_ver = QLabel()
        self.lbl_game_ver.setObjectName("mutedLabel")
        tracked_font(self.lbl_game_ver, size=9, weight=600, spacing=1.2, uppercase=True)
        row_game.addWidget(self.lbl_game_ver)

        # Game version as two toggle buttons
        self.game_version_buttons = {}
        for value in ("2.5", "2.31"):
            btn = QPushButton(value)
            btn.setObjectName("segment")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.setFont(self._button_font(size=9, weight=700, spacing=0.6))
            btn.clicked.connect(
                lambda checked, v=value: self._set_game_version(v)
            )
            self.game_version_buttons[value] = btn
            row_game.addWidget(btn)
        self.game_version_buttons["2.5"].setChecked(True)

        row_game.addStretch()
        ver_layout.addLayout(row_game)

        main_layout.addWidget(self.ver_group)

        # ---------------- Status ----------------
        self.status_group = Panel("", accent=CYAN)
        status_layout = QVBoxLayout(self.status_group)
        status_layout.setContentsMargins(12, 10, 12, 12)
        status_layout.setSpacing(4)

        self.status_tag = QLabel("STATUS")
        self.status_tag.setObjectName("sectionLabel")
        self.status_tag.setStyleSheet(f"color: {CYAN};")
        tracked_font(self.status_tag, size=8, weight=700, spacing=2.0, uppercase=True)
        status_layout.addWidget(self.status_tag)

        self.status_installed = QLabel()
        self.status_installed.setObjectName("statusInstalled")
        self.status_installed.setWordWrap(True)
        status_layout.addWidget(self.status_installed)

        self.status_available = QLabel("")
        self.status_available.setObjectName("statusAvailable")
        self.status_available.setWordWrap(True)
        status_layout.addWidget(self.status_available)

        main_layout.addWidget(self.status_group)

        # ---------------- Primary action (install / update) ----------------
        btn_primary = QHBoxLayout()
        btn_primary.setSpacing(10)
        self.btn_action = QPushButton()
        self.btn_action.setObjectName("primary")
        self.btn_action.setMinimumHeight(44)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setFont(self._button_font(size=10, weight=800))
        btn_primary.addWidget(self.btn_action)
        main_layout.addLayout(btn_primary)

        # ---------------- Secondary actions ----------------
        btn_secondary = QHBoxLayout()
        btn_secondary.setSpacing(10)
        self.btn_check = QPushButton()
        self.btn_uninstall = QPushButton()
        self.btn_backup = QPushButton()
        for btn in (self.btn_check, self.btn_uninstall, self.btn_backup):
            btn.setObjectName("secondary")
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(self._button_font(size=8, weight=600, spacing=0.8))
            btn_secondary.addWidget(btn)
        main_layout.addLayout(btn_secondary)

        # ---------------- Progress ----------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        main_layout.addWidget(self.progress)

        # ---------------- Auto-check ----------------
        self.auto_check_cb = QCheckBox()
        self.auto_check_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.auto_check_cb)

        # ---------------- Hint ----------------
        self.hint_group = Panel("", accent=MUTED)
        hint_layout = QVBoxLayout(self.hint_group)
        hint_layout.setContentsMargins(12, 10, 12, 12)
        self.hint_label = QLabel()
        self.hint_label.setObjectName("mutedLabel")
        self.hint_label.setWordWrap(True)
        hint_layout.addWidget(self.hint_label)
        main_layout.addWidget(self.hint_group)

        main_layout.addStretch(1)

        # ---------------- Language flags ----------------
        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        lang_row.addStretch()
        self.lang_buttons = {}
        for lang_code in SUPPORTED_LANGUAGES:
            btn = QPushButton()
            btn.setObjectName("flag")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(46, 32)
            flag_path = resource_path(
                os.path.join("assets", "flags", f"{lang_code}.png")
            )
            if os.path.isfile(flag_path):
                btn.setIcon(QIcon(flag_path))
                btn.setIconSize(QSize(34, 22))
            else:
                btn.setText(LANGUAGE_FLAGS.get(lang_code, "?"))
            btn.clicked.connect(
                lambda checked, c=lang_code: self._set_language(c)
            )
            self.lang_buttons[lang_code] = btn
            lang_row.addWidget(btn)
        lang_row.addStretch()
        main_layout.addLayout(lang_row)

        # ---------------- README + log + visit site ----------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        self.btn_readme = QPushButton()
        self.btn_save_log = QPushButton()
        for btn in (self.btn_readme, self.btn_save_log):
            btn.setObjectName("secondary")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(30)
            btn.setFont(self._button_font(size=8, weight=600, spacing=0.8))
            bottom_row.addWidget(btn)
        bottom_row.addStretch()

        self.visit_label = ClickableLabel(
            gettext("visit_site", self.lang), "https://nightcoop.net/", size=11, weight=700
        )
        bottom_row.addWidget(self.visit_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(bottom_row)

        # ---------------- Signals ----------------
        self.btn_browse.clicked.connect(self._browse_path)
        self.btn_detect.clicked.connect(self._detect_path)
        self.path_edit.textChanged.connect(self._path_edited)
        self.mod_ver_combo.currentTextChanged.connect(self._mod_version_changed)
        self.btn_check.clicked.connect(self._check_updates)
        self.btn_action.clicked.connect(self._primary_action)
        self.btn_uninstall.clicked.connect(self._uninstall)
        self.btn_backup.clicked.connect(self._backup_settings)
        self.btn_readme.clicked.connect(self._open_readme)
        self.btn_save_log.clicked.connect(self._save_log)
        self.btn_changelog.clicked.connect(self._open_changelog)
        self.auto_check_cb.stateChanged.connect(self._on_auto_check_changed)

        self._update_language_buttons()

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _button_font(size=9, weight=700, spacing=1.4):
        font = QFont("Bahnschrift")
        font.setPointSize(size)
        font.setWeight(QFont.Weight(weight))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        font.setCapitalization(QFont.Capitalization.AllUppercase)
        return font

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    def _set_language(self, lang_code):
        self.lang = lang_code
        self.lang_manual = True   # remembered for this session only
        log(f"language changed: {lang_code}")
        self._apply_lang()
        self._update_language_buttons()

    def _update_language_buttons(self):
        for code, btn in self.lang_buttons.items():
            btn.setProperty("active", "true" if code == self.lang else "false")
            # Re-apply the stylesheet so the dynamic property takes effect
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _apply_lang(self):
        self.setWindowTitle(gettext("app_title", self.lang))
        self.path_caption.setText(gettext("select_game_path", self.lang))
        self.ver_caption.setText(gettext("versions", self.lang))
        self.btn_browse.setText(gettext("browse", self.lang))
        self.btn_detect.setText(gettext("detect", self.lang))
        self.lbl_mod_ver.setText(gettext("mod_version", self.lang))
        self.lbl_game_ver.setText(gettext("game_version", self.lang))
        self.btn_check.setText(gettext("check_updates", self.lang))
        self.btn_uninstall.setText(gettext("uninstall", self.lang))
        self.btn_backup.setText(gettext("backup_settings", self.lang))
        self.btn_readme.setText(gettext("readme", self.lang))
        self.btn_save_log.setText(gettext("save_log", self.lang))
        self.btn_changelog.setText(gettext("changelog_btn", self.lang))
        self.btn_changelog.setToolTip(gettext("whats_new", self.lang))
        self.github_label.setText(gettext("github", self.lang) + " ↗")
        self.auto_check_cb.setText(gettext("auto_check", self.lang))
        self.hint_label.setText(gettext("hint", self.lang))
        self.visit_label.setText(gettext("visit_site", self.lang).upper())
        # Re-render status: if a check already ran, show it in the new language
        if getattr(self, "_last_check_state", None):
            self._render_check_state(self._last_check_state)
        else:
            self._refresh_status_labels(preserve_available=True)

    # ------------------------------------------------------------------
    # README / changelog
    # ------------------------------------------------------------------
    def _readme_path(self):
        lang = self.lang if self.lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        path = resource_path(os.path.join("readme", f"README_{lang}.md"))
        if not os.path.isfile(path):
            path = resource_path(os.path.join("readme", "README_en.md"))
        return path

    def _open_readme(self):
        path = self._readme_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            text = "# README\n\nREADME file was not found."
        self._show_markdown(f"{gettext('app_title', self.lang)} — README", text)

    def _show_markdown(self, title, text):
        """Modal dark-styled viewer for markdown content."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(780, 660)
        dlg.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.document().setDefaultStyleSheet(
            "h1 { color: #FFE500; font-size: 20px; }"
            "h2 { color: #FFE500; font-size: 15px; margin-top: 14px; }"
            "a { color: #00E5FF; }"
            "code { color: #00E5FF; }"
            "li { margin-bottom: 4px; }"
        )
        view.setMarkdown(text)
        view.setStyleSheet(
            "QTextBrowser {"
            "  background-color: #050505;"
            "  border: 1px solid #262626;"
            "  color: #EDEDED;"
            "  padding: 10px;"
            "}"
        )
        layout.addWidget(view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(gettext("close", self.lang))
        btn_close.setObjectName("secondary")
        btn_close.setMinimumHeight(32)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFont(self._button_font(size=9, weight=600))
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        dlg.exec()

    # ------------------------------------------------------------------
    # Changelog
    # ------------------------------------------------------------------
    @staticmethod
    def _pick_localized(mapping, lang):
        """Pick the best available language from a {lang: value} dict."""
        if not isinstance(mapping, dict) or not mapping:
            return None
        for key in (lang, "en", "ru"):
            if mapping.get(key):
                return mapping[key]
        return next((v for v in mapping.values() if v), None)

    def _render_changelog(self, release):
        title = self._pick_localized(release.get("title"), self.lang) or release.get("version", "?")
        notes = self._pick_localized(release.get("notes"), self.lang) or []

        lines = [f"# {title}", ""]

        meta = []
        if release.get("date"):
            meta.append(gettext("released", self.lang, date=release["date"]))
        if release.get("channel"):
            meta.append(gettext("channel_label", self.lang, channel=release["channel"]))
        if release.get("protocol"):
            meta.append(gettext("protocol_label", self.lang, protocol=release["protocol"]))
        if release.get("build"):
            meta.append(gettext("build_label", self.lang, build=release["build"]))
        if release.get("game"):
            meta.append(gettext("game_version", self.lang) + " " + ", ".join(release["game"]))
        if meta:
            lines.append(" · ".join(meta))
            lines.append("")

        if release.get("yanked"):
            lines.append(f"**{gettext('yanked_note', self.lang)}**")
            lines.append("")

        if notes:
            for item in notes:
                lines.append(f"- {item}")
        else:
            lines.append(gettext("no_notes", self.lang))

        return "\n".join(lines)

    def _open_changelog(self):
        selected = self.mod_ver_combo.currentData() or "latest"
        if self.releases_data:
            self._show_changelog(self.releases_data, selected)
            return

        # Data not loaded yet - fetch it without freezing the UI
        self.btn_changelog.setEnabled(False)
        worker = VersionsWorker(self.base_url)
        worker.finished.connect(
            lambda releases, error: self._on_changelog_loaded(releases, error, selected)
        )
        worker.finished.connect(lambda *_: self.btn_changelog.setEnabled(True))
        worker.finished.connect(lambda *_: self._forget_worker(worker))
        self._bg_workers.append(worker)
        worker.start()

    def _on_changelog_loaded(self, releases, error, selected):
        if error or not releases:
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("changelog_unavailable", self.lang),
            )
            return
        self.releases_data = releases
        self._show_changelog(releases, selected)

    def _show_changelog(self, releases, selected):
        release = None
        wanted = selected if selected != "latest" else releases.get("latest")
        for item in releases.get("releases", []):
            if item.get("version") == wanted:
                release = item
                break
        if release is None:
            for item in releases.get("releases", []):
                if item.get("version") == releases.get("latest"):
                    release = item
                    break
        if release is None:
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("changelog_unavailable", self.lang),
            )
            return

        log(f"changelog opened: {release.get('version')}")
        self._show_markdown(
            f"{gettext('whats_new', self.lang)} — {release.get('version', '')}",
            self._render_changelog(release),
        )

    # ------------------------------------------------------------------
    # Path / version
    # ------------------------------------------------------------------
    def _apply_detected_path(self, path):
        # Set the text without triggering _path_edited (avoids a second reload)
        was_blocked = self.path_edit.blockSignals(True)
        try:
            self.path_edit.setText(path)
        finally:
            self.path_edit.blockSignals(was_blocked)
        self._path_timer.stop()
        self.game_path = path
        self._last_check_state = None
        log(f"game path: {path}")
        self._refresh_status_labels()
        self._load_mod_versions()

    def _auto_detect_startup(self):
        """Auto-detect game path on startup (nothing is persisted)."""
        self._log("Auto-detecting game path...")
        path = updater.detect_game_path()
        if path:
            self._apply_detected_path(path)
        else:
            self._log("Game path not found automatically.")
            self.mod_ver_combo.setEnabled(False)
            self.mod_ver_combo.clear()
            self.mod_ver_combo.addItems([gettext("no_game_path", self.lang)])

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(
            self, gettext("select_game_folder", self.lang), self.game_path
        )
        if not folder:
            return
        if not updater.is_valid_game_path(folder):
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("game_exe_missing", self.lang),
            )
            return
        self._apply_detected_path(folder)
        self._check_updates(automatic=True)

    def _detect_path(self):
        self._log("Auto-detecting game path...")
        path = updater.detect_game_path()
        if path:
            self._apply_detected_path(path)
            self._check_updates(automatic=True)
            QMessageBox.information(
                self, gettext("title_done", self.lang),
                gettext("log_detected_path", self.lang, path=path),
            )
        else:
            self._log("Game path not found automatically.")
            QMessageBox.warning(
                self, gettext("title_not_found", self.lang),
                gettext("game_not_found", self.lang),
            )

    def _path_edited(self, text):
        self.game_path = text.strip()
        self._last_check_state = None
        self._refresh_status_labels(preserve_available=True)
        # Reload the version list shortly after the user stops typing
        self._path_timer.start()

    def _path_settled(self):
        if updater.is_valid_game_path(self.game_path):
            self._load_mod_versions()
            self._check_updates(automatic=True)

    def _set_game_version(self, value):
        self.game_version = value
        for version, btn in self.game_version_buttons.items():
            btn.setChecked(version == value)
        # The previous check was made for another game version - drop it
        self._last_check_state = None
        self._refresh_status_labels()
        self._load_mod_versions()
        if updater.is_valid_game_path(self.game_path):
            self._check_updates(automatic=True)

    def _mod_version_changed(self, text):
        self.mod_version = self.mod_ver_combo.currentData() or text

    def _load_mod_versions(self):
        """Fetch releases.json and populate the mod version dropdown."""
        if not updater.is_valid_game_path(self.game_path):
            self.mod_ver_combo.setEnabled(False)
            self.mod_ver_combo.clear()
            self.mod_ver_combo.addItems([gettext("no_game_path", self.lang)])
            return

        # Remember the user's choice - repopulating the combo emits signals
        self._wanted_mod_version = self.mod_version

        self.mod_ver_combo.setEnabled(False)
        was_blocked = self.mod_ver_combo.blockSignals(True)
        try:
            self.mod_ver_combo.clear()
            self.mod_ver_combo.addItems([gettext("loading_versions", self.lang)])
        finally:
            self.mod_ver_combo.blockSignals(was_blocked)

        # Generation counter prevents a stale worker from overwriting a newer list
        self._versions_generation += 1
        generation = self._versions_generation

        worker = VersionsWorker(self.base_url)
        worker.finished.connect(
            lambda releases, error, gen=generation: self._on_versions_loaded(
                releases, error, gen
            )
        )
        worker.finished.connect(lambda *_: self._forget_worker(worker))
        self._bg_workers.append(worker)
        self.versions_worker = worker
        worker.start()

    def _forget_worker(self, worker):
        try:
            self._bg_workers.remove(worker)
        except ValueError:
            pass

    def _on_versions_loaded(self, releases, error, generation=0):
        if generation and generation != self._versions_generation:
            return  # a newer request already took over

        if error:
            log(f"versions load error: {error}")
            self.mod_ver_combo.setEnabled(False)
            was_blocked = self.mod_ver_combo.blockSignals(True)
            try:
                self.mod_ver_combo.clear()
                self.mod_ver_combo.addItems([gettext("error_loading", self.lang)])
            finally:
                self.mod_ver_combo.blockSignals(was_blocked)
            return

        self.releases_data = releases
        game_version = self.game_version
        versions = updater.list_versions_for_game(releases, game_version)

        wanted = getattr(self, "_wanted_mod_version", self.mod_version)

        was_blocked = self.mod_ver_combo.blockSignals(True)
        try:
            self.mod_ver_combo.clear()
            for version_label, release, file_info in versions:
                if version_label == "latest":
                    online_ver = release.get("version", "unknown")
                    self.mod_ver_combo.addItem(f"latest ({online_ver})", userData="latest")
                else:
                    self.mod_ver_combo.addItem(version_label, userData=version_label)

            idx = self.mod_ver_combo.findData(wanted)
            if idx < 0:
                idx = 0
            self.mod_ver_combo.setCurrentIndex(idx)
            self.mod_version = self.mod_ver_combo.itemData(idx) or "latest"
        finally:
            self.mod_ver_combo.blockSignals(was_blocked)

        self.mod_ver_combo.setEnabled(True)

        # Do not wipe the "update available" line: the version check may have
        # finished earlier than this list. Re-render the last result instead.
        if self._last_check_state:
            self._render_check_state(self._last_check_state)
        else:
            self._refresh_status_labels(preserve_available=True)

    # ------------------------------------------------------------------
    # Status / buttons logic
    # ------------------------------------------------------------------
    def _log(self, msg):
        log(str(msg))

    def _refresh_status_labels(self, preserve_available=False):
        installed = updater.get_installed_version(self.game_path) if self.game_path else None
        present = updater.is_mod_installed(self.game_path) if self.game_path else False
        is_installed = bool(installed or present)

        # First line: always visible — installed version or not installed
        if is_installed:
            shown = installed if installed else gettext("unknown", self.lang)
            self.status_installed.setText(gettext("installed_version", self.lang, version=shown))
            self.status_installed.setStyleSheet("color: #FFFFFF;")
        else:
            self.status_installed.setText(gettext("installed_version", self.lang, version=gettext("not_installed", self.lang)))
            self.status_installed.setStyleSheet(f"color: {ACCENT};")

        # Without a fresh check the update state is unknown - keep it disabled
        self._apply_action_button(is_installed, update_available=False)
        self.btn_uninstall.setEnabled(is_installed)

        # Second line: preserve existing text if requested (e.g. on language switch)
        if not preserve_available:
            self._set_available_text("", color=MUTED)

    def _apply_action_button(self, is_installed, update_available):
        """One button that means Install or Update depending on the state."""
        if is_installed:
            self.btn_action.setText(gettext("update", self.lang))
            self.btn_action.setEnabled(bool(update_available))
            self._action_operation = "update"
        else:
            self.btn_action.setText(gettext("install", self.lang))
            self.btn_action.setEnabled(True)
            self._action_operation = "install"

    def _set_available_text(self, text, color=CYAN):
        self.status_available.setText(text)
        self.status_available.setStyleSheet(f"color: {color};")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _check_updates(self, automatic=False):
        if not updater.is_valid_game_path(self.game_path):
            if not automatic:
                QMessageBox.warning(
                    self, gettext("title_error", self.lang),
                    gettext("game_not_found", self.lang),
                )
            return
        if updater.is_game_running():
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("game_running", self.lang),
            )
            return

        self.btn_check.setEnabled(False)
        self._log(gettext("log_checking", self.lang))

        self.version_worker = VersionCheckWorker(
            self.game_path, self.game_version, self.base_url
        )
        self.version_worker.result.connect(self._on_version_result)
        self.version_worker.error.connect(self._on_version_error)
        self.version_worker.finished.connect(lambda: self.btn_check.setEnabled(True))
        self.version_worker.start()

    def _on_version_result(self, data):
        # Remember last check so language switches can re-render it
        self._last_check_state = data
        self._render_check_state(data)

    def _render_check_state(self, data):
        msg = data.get("message", "")
        version = data.get("version", "")
        installed = data.get("installed", "")

        is_installed = bool(installed and installed != "not_installed")
        # Translate the "unknown" marker coming from the worker
        installed_shown = gettext("unknown", self.lang) if installed == "unknown" else installed

        if msg == "no_mod_for_version":
            self._log(f"No mod available for game version {self.game_version}")
            if is_installed:
                self.status_installed.setText(gettext("installed_version", self.lang, version=installed_shown))
                self.status_installed.setStyleSheet("color: #FFFFFF;")
            else:
                self.status_installed.setText(gettext("installed_version", self.lang, version=gettext("not_installed", self.lang)))
                self.status_installed.setStyleSheet(f"color: {ACCENT};")
            self._apply_action_button(is_installed, update_available=False)
            self.btn_uninstall.setEnabled(is_installed)
            self._set_available_text(gettext("no_update", self.lang), color=MUTED)

        elif msg == "update_available":
            self._log(gettext("update_available", self.lang, version=version))
            if is_installed:
                self.status_installed.setText(gettext("installed_version", self.lang, version=installed_shown))
                self.status_installed.setStyleSheet("color: #FFFFFF;")
            else:
                self.status_installed.setText(gettext("installed_version", self.lang, version=gettext("not_installed", self.lang)))
                self.status_installed.setStyleSheet(f"color: {ACCENT};")
            self._apply_action_button(is_installed, update_available=True)
            self.btn_uninstall.setEnabled(is_installed)
            self._set_available_text(gettext("update_available", self.lang, version=version), color=CYAN)

        elif msg == "no_update":
            self._log(gettext("no_update", self.lang))
            self.status_installed.setText(gettext("installed_version", self.lang, version=installed_shown))
            self.status_installed.setStyleSheet("color: #FFFFFF;")
            self._apply_action_button(True, update_available=False)
            self.btn_uninstall.setEnabled(True)
            self._set_available_text(gettext("no_update", self.lang), color=MUTED)

    def _on_version_error(self, err):
        self._log(gettext("error", self.lang, message=err))
        self.btn_check.setEnabled(True)
        # Keep the button usable - a failed check must not lock the app
        self._refresh_status_labels(preserve_available=True)

    def _primary_action(self):
        if not self._ready_for_action():
            return
        operation = getattr(self, "_action_operation", "install")
        self._start_worker(operation)

    def _ready_for_action(self):
        """Common checks before install/update/uninstall."""
        if not updater.is_valid_game_path(self.game_path):
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("game_not_found", self.lang),
            )
            return False
        if updater.is_game_running():
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("game_running", self.lang),
            )
            return False
        return True

    def _uninstall(self):
        if not self._ready_for_action():
            return
        reply = QMessageBox.question(
            self, gettext("title_confirm", self.lang),
            gettext("confirm_uninstall", self.lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_worker("uninstall")

    def _backup_settings(self):
        if not updater.is_valid_game_path(self.game_path):
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("game_not_found", self.lang),
            )
            return
        result = updater.backup_mod_settings(self.game_path, log_callback=self._log)
        if result:
            QMessageBox.information(
                self, gettext("title_backup", self.lang),
                gettext("backup_done", self.lang, path=result),
            )
        else:
            QMessageBox.warning(
                self, gettext("title_backup", self.lang),
                gettext("backup_failed", self.lang),
            )

    def _save_log(self):
        """Offer to save the session log where the user wants it."""
        if not LOG_PATH or not os.path.isfile(LOG_PATH):
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("log_missing", self.lang),
            )
            return
        default_name = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
            time.strftime("NightCoopManager-log-%Y-%m-%d_%H-%M.txt"),
        )
        target, _ = QFileDialog.getSaveFileName(
            self, gettext("save_log", self.lang), default_name, "Text (*.txt)"
        )
        if not target:
            return
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as src:
                content = src.read()
            header = (
                f"{gettext('app_title', self.lang)}\n"
                f"game path: {self.game_path}\n"
                f"game version: {self.game_version}\n"
                f"mod version: {self.mod_version}\n"
                f"language: {self.lang}\n"
                f"log source: {LOG_PATH}\n"
                + "-" * 60 + "\n"
            )
            with open(target, "w", encoding="utf-8") as dst:
                dst.write(header + content)
            QMessageBox.information(
                self, gettext("title_done", self.lang),
                gettext("log_saved", self.lang, path=target),
            )
        except OSError as exc:
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("error", self.lang, message=str(exc)),
            )

    def _start_worker(self, operation):
        selected = self.mod_ver_combo.currentData()
        if operation != "uninstall" and not selected:
            QMessageBox.warning(
                self, gettext("title_error", self.lang),
                gettext("no_version_selected", self.lang),
            )
            return

        log(f"operation started: {operation} (mod {selected})")
        self._cancel_event = threading.Event()
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_buttons_enabled(False)

        self.worker = UpdateWorker(
            operation, self.game_path, self.game_version,
            selected or "latest", self.base_url, cancel_event=self._cancel_event,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _set_buttons_enabled(self, enabled):
        self.btn_check.setEnabled(enabled)
        self.btn_action.setEnabled(enabled)
        self.btn_uninstall.setEnabled(enabled)
        self.btn_backup.setEnabled(enabled)
        self.btn_changelog.setEnabled(enabled)

    def _on_progress(self, downloaded, total):
        if total > 0:
            self.progress.setRange(0, 100)
            self.progress.setValue(min(100, int(downloaded / total * 100)))
        else:
            # Unknown size - show a busy indicator instead of a frozen 0%
            self.progress.setRange(0, 0)

    def _on_worker_finished(self, success, message):
        self.progress.setVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._set_buttons_enabled(True)
        self._cancel_event = None

        if success:
            if message == "mod_removed":
                self._log(gettext("mod_removed", self.lang))
                QMessageBox.information(
                    self, gettext("title_done", self.lang),
                    gettext("mod_removed", self.lang),
                )
            elif message.startswith("mod_installed:"):
                version = message.split(":", 1)[1]
                self._log(gettext("mod_installed", self.lang))
                QMessageBox.information(
                    self, gettext("title_done", self.lang),
                    gettext("mod_installed", self.lang) + "\n"
                    + gettext("version_line", self.lang, version=version),
                )
            self._last_check_state = None
            self._refresh_status_labels()
            installed = updater.get_installed_version(self.game_path) if self.game_path else None
            if installed:
                self._set_available_text(gettext("no_update", self.lang), color=MUTED)
            # Refresh the real update state: the merged button must disable itself
            # when the freshly installed build is already the latest one.
            if message.startswith("mod_installed:") and updater.is_valid_game_path(self.game_path):
                self._check_updates(automatic=True)
        elif message == "cancelled":
            self._log("operation cancelled by user")
            self._refresh_status_labels()
        else:
            self._log(f"operation failed: {message}")
            QMessageBox.critical(
                self, gettext("title_error", self.lang),
                gettext("error", self.lang, message=message),
            )
            self._refresh_status_labels()

        self.worker = None

    def _on_auto_check_changed(self, state):
        log(f"auto check: {bool(state)}")

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return

        busy = self.worker is not None and self.worker.isRunning()
        if busy:
            reply = QMessageBox.question(
                self, gettext("title_confirm", self.lang),
                gettext("cancel_and_exit", self.lang),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            # Ask the worker to stop, give it time to finish the current chunk
            self._closing = True
            if self._cancel_event is not None:
                self._cancel_event.set()
            if not self.worker.wait(20000):
                # Last resort: never destroy a running QThread (that crashes Qt)
                log("install worker did not stop in time, terminating")
                self.worker.terminate()
                self.worker.wait(2000)

        # Stop every background worker so none is destroyed while running
        workers = [self.version_worker, self.versions_worker] + list(self._bg_workers)
        for worker in workers:
            if worker is not None and worker.isRunning():
                worker.requestInterruption()
                worker.wait(3000)

        log("window closed")
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _init_log()
    sys.excepthook = log_exception

    # Crisp rendering on 125% / 150% Windows scaling
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Dark palette matching the new theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#EDEDED"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0A0A0A"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#141414"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#EDEDED"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#0A0A0A"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#CFCFCF"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#FFE500"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0A0A0A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#EDEDED"))
    app.setPalette(palette)

    log(f"log file: {LOG_PATH}")

    window = NightCoopManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()