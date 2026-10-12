"""
AuraPDF - Modern Acrobat UI Redesign Views
===========================================
Bu modül, Adobe Acrobat'ın yeni nesil arayüz tasarımını AuraPDF için sağlar:
1. ModernTabBarWidget: Üst sekme çubuğu (açık PDF belgeleri, kapatma, yeni sekme).
2. ModernHeaderBar: Menü, 'Tüm Araçlar / Oku / Düzenle / Dönüştür / E-İmza' mod çubuğu, arama (Ctrl+K) ve hızlı eylemler.
3. ModernAllToolsPanel: Sol çekmece araç listesi (renkli vektörel ikonlar, daraltılabilir).
4. OrganizePagesWorkspace: Belge sayfalarını çok sütunlu ızgarada gösteren, döndürme/silme/çıkarma/ekleme araçlarına sahip tam ekran çalışma alanı.
5. ModernRightSidebar: Sağ çekmece (Yer İmleri, Yorumlar, Küçük Resimler).
6. ModernUtilityRail: En sağdaki dikey araç çubuğu (panel tetikleyicileri ve alt zoom/sayfa denetimleri).
7. ModernCommandPaletteDialog: Ctrl+K hızlı araç/komut arama paleti.
"""

import os
import json
import tempfile
import math
from typing import List, Dict, Optional, Set, Any
import pymupdf as fitz

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QToolButton,
    QPushButton, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QListView, QMenu,
    QDialog, QSizePolicy, QApplication, QSlider, QMessageBox, QFileDialog,
    QHeaderView, QGraphicsDropShadowEffect, QAbstractItemView, QStyleOptionViewItem,
    QProgressBar, QButtonGroup, QLayout, QRubberBand, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPointF, QRect, QRectF, QTimer, QThread, QUrl, QEvent, QSettings, QMimeData
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QCursor, QKeySequence, QShortcut, QDesktopServices,
    QFontMetrics, QIntValidator, QLinearGradient, QDrag, QTextCursor, QTextCharFormat
)
from PyQt6.QtMultimedia import QMediaDevices

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme
from src.core.speech_engine import AuraSpeechEngine, clean_text_for_speech


def get_modern_theme_colors(theme_name: str = "gray") -> Dict[str, str]:
    """Tüm temalarla kusursuz uyumlu renk paleti."""
    palettes = {
        "light": {
            "bg": "#f0f2f5",
            "tab_bar_bg": "#eaedf1",
            "surface": "#ffffff",
            "surface_hover": "#f1f5f9",
            "surface_active": "#e2e8f0",
            "border": "#cbd5e1",
            "border_subtle": "#e2e8f0",
            "text": "#0f172a",
            "text_muted": "#475569",
            "accent": "#0284c7",
            "accent_hover": "#0369a1",
            "accent_light": "rgba(2, 132, 199, 0.12)",
            "danger": "#ef4444",
            "tab_bg": "#e2e6ea",
            "tab_active": "#ffffff",
            "tab_text": "#334155",
            "tab_active_text": "#0f172a",
            "badge_bg": "#f1f5f9",
            "card_bg": "#ffffff",
            "card_border": "#cbd5e1",
        },
        "gray": {
            "bg": "#232528",
            "tab_bar_bg": "#1e2022",
            "surface": "#2b2d30",
            "surface_hover": "#35383c",
            "surface_active": "#3e4248",
            "border": "#3c3f44",
            "border_subtle": "#32353a",
            "text": "#f8fafc",
            "text_muted": "#cbd5e1",
            "accent": "#60a5fa",
            "accent_hover": "#93c5fd",
            "accent_light": "rgba(96, 165, 250, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#1e2022",
            "tab_active": "#2b2d30",
            "tab_text": "#cbd5e1",
            "tab_active_text": "#ffffff",
            "badge_bg": "#35383c",
            "card_bg": "#2b2d30",
            "card_border": "#444850",
        },
        "dark": {
            "bg": "#121212",
            "surface": "#1c1c1c",
            "surface_hover": "#262626",
            "surface_active": "#323232",
            "border": "#2e2e2e",
            "border_subtle": "#222222",
            "text": "#f8fafc",
            "text_muted": "#cbd5e1",
            "accent": "#388bfd",
            "accent_hover": "#58a6ff",
            "accent_light": "rgba(56, 139, 253, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#141414",
            "tab_active": "#1c1c1c",
            "tab_text": "#cbd5e1",
            "tab_active_text": "#ffffff",
            "badge_bg": "#262626",
            "card_bg": "#1c1c1c",
            "card_border": "#363636",
        },
        "nord": {
            "bg": "#181e29",
            "surface": "#222b3a",
            "surface_hover": "#2f3b4f",
            "surface_active": "#3a4961",
            "border": "#313e54",
            "border_subtle": "#283446",
            "text": "#f0f6fc",
            "text_muted": "#cbd5e1",
            "accent": "#38bdf8",
            "accent_hover": "#7dd3fc",
            "accent_light": "rgba(56, 189, 248, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#141922",
            "tab_active": "#222b3a",
            "tab_text": "#cbd5e1",
            "tab_active_text": "#f0f6fc",
            "badge_bg": "#2f3b4f",
            "card_bg": "#222b3a",
            "card_border": "#3b4a64",
        },
        "emerald": {
            "bg": "#071410",
            "surface": "#112a21",
            "surface_hover": "#1a4032",
            "surface_active": "#245845",
            "border": "#1d4637",
            "border_subtle": "#143328",
            "text": "#ecfdf5",
            "text_muted": "#c6f6d5",
            "accent": "#34d399",
            "accent_hover": "#6ee7b7",
            "accent_light": "rgba(52, 211, 153, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#0b1c16",
            "tab_active": "#112a21",
            "tab_text": "#a7f3d0",
            "tab_active_text": "#ecfdf5",
            "badge_bg": "#1a4032",
            "card_bg": "#112a21",
            "card_border": "#22543d",
        },
        "purple": {
            "bg": "#10091a",
            "surface": "#201435",
            "surface_hover": "#321f52",
            "surface_active": "#442a6f",
            "border": "#362058",
            "border_subtle": "#281842",
            "text": "#faf5ff",
            "text_muted": "#e9d5ff",
            "accent": "#c084fc",
            "accent_hover": "#d8b4fe",
            "accent_light": "rgba(192, 132, 252, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#140c22",
            "tab_active": "#201435",
            "tab_text": "#e9d5ff",
            "tab_active_text": "#faf5ff",
            "badge_bg": "#321f52",
            "card_bg": "#201435",
            "card_border": "#442970",
        },
        "crimson": {
            "bg": "#15070b",
            "surface": "#2d1118",
            "surface_hover": "#441924",
            "surface_active": "#5c2230",
            "border": "#491b27",
            "border_subtle": "#36141e",
            "text": "#fff1f2",
            "text_muted": "#fecdd3",
            "accent": "#fb7185",
            "accent_hover": "#fda4af",
            "accent_light": "rgba(251, 113, 133, 0.20)",
            "danger": "#f87171",
            "tab_bg": "#1a0a0f",
            "tab_active": "#2d1118",
            "tab_text": "#fecdd3",
            "tab_active_text": "#fff1f2",
            "badge_bg": "#441924",
            "card_bg": "#2d1118",
            "card_border": "#5a2130",
        },
        "vice_city": {
            "bg": "#10001a",
            "surface": "#240e3b",
            "surface_hover": "#381458",
            "surface_active": "#4d1c78",
            "border": "#421869",
            "border_subtle": "#2f114d",
            "text": "#fdf2f8",
            "text_muted": "#f5d0fe",
            "accent": "#ff2a85",
            "accent_hover": "#ff66a8",
            "accent_light": "rgba(255, 42, 133, 0.22)",
            "danger": "#ff3366",
            "tab_bg": "#160524",
            "tab_active": "#240e3b",
            "tab_text": "#f5d0fe",
            "tab_active_text": "#ffffff",
            "badge_bg": "#381458",
            "card_bg": "#240e3b",
            "card_border": "#63249e",
        },
        "apple": {
            "bg": "#0e1014",
            "surface": "#1a1d24",
            "surface_hover": "#262a34",
            "surface_active": "#333846",
            "border": "#2e3340",
            "border_subtle": "#222630",
            "text": "#f5f5f7",
            "text_muted": "#cbd5e1",
            "accent": "#38bdf8",
            "accent_hover": "#7dd3fc",
            "accent_light": "rgba(56, 189, 248, 0.20)",
            "danger": "#ff453a",
            "tab_bg": "#121419",
            "tab_active": "#1a1d24",
            "tab_text": "#cbd5e1",
            "tab_active_text": "#ffffff",
            "badge_bg": "#262a34",
            "card_bg": "#1a1d24",
            "card_border": "#363c4b",
        }
    }
    if theme_name == "navy":
        return palettes["nord"]
    if theme_name == "custom":
        return build_custom_theme_palette()
    return palettes.get(theme_name, palettes["gray"])


def get_custom_theme_colors() -> Dict[str, str]:
    """QSettings'te kayıtlı özel tema renklerini döner veya varsayılan modern renkleri verir."""
    defaults = {
        "accent": "#38bdf8",
        "bg": "#14171d",
        "surface": "#1e222b",
        "text": "#f1f5f9",
        "border": "#2e3442"
    }
    try:
        settings = QSettings("AuraPDF", "PDFViewer")
        raw = settings.value("custom_theme_colors", None)
        if raw:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and v.startswith("#"):
                        defaults[k] = v
    except Exception:
        pass
    return defaults


def build_custom_theme_palette(custom_colors: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Kullanıcının seçtiği renklerden tüm arayüz için eksiksiz ve dengeli bir palet türetir."""
    cfg = custom_colors or get_custom_theme_colors()
    accent = cfg.get("accent", "#38bdf8")
    bg = cfg.get("bg", "#14171d")
    surface = cfg.get("surface", "#1e222b")
    text = cfg.get("text", "#f1f5f9")
    border = cfg.get("border", "#2e3442")

    c_accent = QColor(accent) if QColor.isValidColor(accent) else QColor("#38bdf8")
    c_bg = QColor(bg) if QColor.isValidColor(bg) else QColor("#14171d")
    c_surf = QColor(surface) if QColor.isValidColor(surface) else QColor("#1e222b")
    c_text = QColor(text) if QColor.isValidColor(text) else QColor("#f1f5f9")
    c_border = QColor(border) if QColor.isValidColor(border) else QColor("#2e3442")

    is_dark = c_surf.lightness() < 128

    if is_dark:
        surf_hover = c_surf.lighter(118).name()
        surf_active = c_surf.lighter(132).name()
        border_subtle = c_surf.lighter(110).name()
        accent_hover = c_accent.lighter(118).name()
        muted = c_text.darker(135).name()
        badge_bg = surf_hover
        tab_bg = c_bg.lighter(106).name()
    else:
        surf_hover = c_surf.darker(106).name()
        surf_active = c_surf.darker(114).name()
        border_subtle = c_surf.darker(108).name()
        accent_hover = c_accent.darker(115).name()
        muted = c_text.lighter(140).name()
        badge_bg = surf_hover
        tab_bg = c_bg.darker(104).name()

    accent_light = f"rgba({c_accent.red()}, {c_accent.green()}, {c_accent.blue()}, 0.20)"

    return {
        "bg": c_bg.name(),
        "tab_bar_bg": c_bg.name(),
        "surface": c_surf.name(),
        "surface_hover": surf_hover,
        "surface_active": surf_active,
        "border": c_border.name(),
        "border_subtle": border_subtle,
        "text": c_text.name(),
        "text_muted": muted,
        "accent": c_accent.name(),
        "accent_hover": accent_hover,
        "accent_light": accent_light,
        "danger": "#ef4444",
        "tab_bg": tab_bg,
        "tab_active": c_surf.name(),
        "tab_text": muted,
        "tab_active_text": c_text.name(),
        "badge_bg": badge_bg,
        "card_bg": c_surf.name(),
        "card_border": c_border.name(),
    }


# ==============================================================================
# 1. MODERN DOKÜMAN SEKME ÇUBUĞU (ModernTabBarWidget)
# ==============================================================================
class ModernTabItem(QWidget):
    """Tek bir belge sekmesi (İkon, Başlık, Kapat butonu, Seçim efekti)."""
    closeRequested = pyqtSignal(int)
    clicked = pyqtSignal(int)
    hoverEntered = pyqtSignal(int, QPoint)
    hoverLeft = pyqtSignal(int)

    def __init__(self, index: int, title: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.index = index
        self.title = title
        self.is_active = is_active
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setMinimumWidth(120)
        self.setMaximumWidth(240)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(6)

        # PDF Doküman İkonu
        self.lbl_icon = QLabel()
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_icon.setPixmap(ModernIconFactory.icon_app().pixmap(14, 14))
        self.lbl_icon.setFixedSize(14, 14)
        layout.addWidget(self.lbl_icon)

        # Başlık
        self.lbl_title = QLabel(title)
        self.lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.lbl_title, stretch=1)

        # Kapat Butonu (X)
        self.btn_close = QToolButton(self)
        self.btn_close.setObjectName("TabCloseBtn")
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip(LanguageManager.tr("close_tab"))
        self.btn_close.clicked.connect(lambda: self.closeRequested.emit(self.index))
        layout.addWidget(self.btn_close)

        self.set_title(title)
        self._apply_style("light")

    def mousePressEvent(self, event):
        self.hoverLeft.emit(self.index)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.MouseButton.MiddleButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.closeRequested.emit(self.index)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        self.hoverEntered.emit(self.index, pos)
        super().enterEvent(event)

    def leaveEvent(self, event):
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(cursor_pos):
            self.hoverLeft.emit(self.index)
        super().leaveEvent(event)

    def set_active(self, active: bool, theme_name: str = "light"):
        self.is_active = active
        self._apply_style(theme_name)

    def set_title(self, title: str):
        self.title = title
        fm = self.lbl_title.fontMetrics()
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, 155)
        self.lbl_title.setText(elided)

    def _apply_style(self, theme_name: str = "light"):
        c = get_modern_theme_colors(theme_name)
        close_icon_color = c.get('tab_active_text', '#f8fafc') if self.is_active else ('#cbd5e1' if theme_name != 'light' else '#475569')
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(close_icon_color, hover_color="#ef4444"))

        if self.is_active:
            self.setStyleSheet(f"""
                ModernTabItem {{
                    background-color: {c['tab_active']};
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    border: 1px solid {c['border']};
                    border-bottom: 2px solid {c['tab_active']};
                }}
                QLabel {{
                    color: {c['tab_active_text']};
                    font-size: 12px;
                    font-weight: 600;
                }}
                QToolButton#TabCloseBtn {{
                    background-color: transparent;
                    border: none;
                    border-radius: 10px;
                    padding: 0px;
                    margin: 0px;
                    min-width: 20px;
                    max-width: 20px;
                    min-height: 20px;
                    max-height: 20px;
                }}
                QToolButton#TabCloseBtn:hover {{
                    background-color: rgba(239, 68, 68, 0.22);
                    border: 1px solid rgba(239, 68, 68, 0.40);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ModernTabItem {{
                    background-color: {c['tab_bg']};
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    border: 1px solid transparent;
                    border-bottom: 1px solid {c['border']};
                }}
                ModernTabItem:hover {{
                    background-color: {c['surface_hover']};
                }}
                QLabel {{
                    color: {c['tab_text']};
                    font-size: 12px;
                    font-weight: 500;
                }}
                QToolButton#TabCloseBtn {{
                    background-color: transparent;
                    border: none;
                    border-radius: 10px;
                    padding: 0px;
                    margin: 0px;
                    min-width: 20px;
                    max-width: 20px;
                    min-height: 20px;
                    max-height: 20px;
                }}
                QToolButton#TabCloseBtn:hover {{
                    background-color: rgba(239, 68, 68, 0.22);
                    border: 1px solid rgba(239, 68, 68, 0.40);
                }}
            """)


class ModernTabBarWidget(QWidget):
    """En üstteki sekmeler çubuğu: Home sekmesi, açık PDF belgeleri, yeni sekme ve hızlı bağlantılar."""
    tabCloseRequested = pyqtSignal(int)
    currentChanged = pyqtSignal(int)
    newTabRequested = pyqtSignal()
    homeRequested = pyqtSignal()
    helpRequested = pyqtSignal()
    tabHoverEntered = pyqtSignal(int, QPoint)
    tabHoverLeft = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent.main_window if hasattr(parent, "main_window") else None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.current_index = -1
        self.is_home_active = True
        self.items: List[ModernTabItem] = []

        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 0)
        layout.setSpacing(6)

        # 1. Ana Sayfa (Home) Butonu
        self.btn_home = QToolButton()
        self.btn_home.setIcon(ModernIconFactory.icon_home())
        self.btn_home.setIconSize(QSize(15, 15))
        self.btn_home.setText(" " + LanguageManager.tr("home_tab_text"))
        self.btn_home.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_home.setFixedHeight(30)
        self.btn_home.setCheckable(True)
        self.btn_home.setChecked(True)
        self.btn_home.clicked.connect(self._on_home_clicked)
        layout.addWidget(self.btn_home)

        # 2. Yeni Dosya Aç (+) Butonu
        self.btn_new_tab = QToolButton()
        self.btn_new_tab.setIcon(ModernIconFactory.icon_plus())
        self.btn_new_tab.setIconSize(QSize(12, 12))
        self.btn_new_tab.setText(" " + LanguageManager.tr("open"))
        self.btn_new_tab.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_new_tab.setFixedHeight(30)
        self.btn_new_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_tab.setToolTip(LanguageManager.tr("open_tooltip"))
        self.btn_new_tab.clicked.connect(self.newTabRequested.emit)
        layout.addWidget(self.btn_new_tab)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        sep.setStyleSheet("background-color: #cbd5e1; border: none;")
        layout.addWidget(sep)

        # 3. Sekmeler Taşıyıcı Widget
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(4)
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.tabs_container)

        layout.addStretch(1)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.btn_home.setText(" " + LanguageManager.tr("home_tab_text"))
        self.btn_new_tab.setText(" " + LanguageManager.tr("open"))
        self.btn_new_tab.setToolTip(LanguageManager.tr("open_tooltip"))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        home_active_bg = c['surface'] if self.is_home_active else "transparent"
        home_active_text = c['text'] if self.is_home_active else c['text_muted']
        home_border = f"1px solid {c['border']}" if self.is_home_active else "1px solid transparent"
        self.setStyleSheet(f"""
            ModernTabBarWidget {{
                background-color: {c.get('tab_bar_bg', c['bg'])};
                border-bottom: 1px solid {c['border']};
            }}
            QToolButton:not(#TabCloseBtn) {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {c['text']};
                padding: 0 8px;
                font-weight: 500;
                font-size: 12px;
            }}
            QToolButton:not(#TabCloseBtn):hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
                color: {c['text']};
            }}
            QToolButton#TabCloseBtn {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
                padding: 0px;
                margin: 0px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
            }}
            QToolButton#TabCloseBtn:hover {{
                background-color: rgba(239, 68, 68, 0.22);
                border: 1px solid rgba(239, 68, 68, 0.40);
            }}
        """)
        self.btn_home.setStyleSheet(f"""
            QToolButton {{
                background-color: {home_active_bg};
                border: {home_border};
                border-radius: 6px 6px 0 0;
                color: {home_active_text};
                padding: 0 10px;
                font-weight: {'700' if self.is_home_active else '500'};
                font-size: 12px;
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        for item in self.items:
            item._apply_style(theme_name)

    def set_home_active(self, active: bool):
        self.is_home_active = active
        self.btn_home.setChecked(active)
        if active:
            self.current_index = -1
            for item in self.items:
                item.set_active(False, self.theme_name)
        self.apply_theme(self.theme_name)

    def add_tab(self, title: str) -> int:
        idx = len(self.items)
        item = ModernTabItem(idx, title, is_active=(idx == 0 and not self.is_home_active), parent=self)
        item.clicked.connect(self._on_item_clicked)
        item.closeRequested.connect(self.tabCloseRequested.emit)
        item.hoverEntered.connect(self.tabHoverEntered.emit)
        item.hoverLeft.connect(self.tabHoverLeft.emit)
        self.items.append(item)
        self.tabs_layout.addWidget(item)
        item._apply_style(self.theme_name)
        return idx

    def remove_tab(self, index: int):
        if 0 <= index < len(self.items):
            item = self.items.pop(index)
            self.tabs_layout.removeWidget(item)
            item.deleteLater()
            for i, it in enumerate(self.items):
                it.index = i

    def set_current_index(self, index: int):
        if 0 <= index < len(self.items):
            self.is_home_active = False
            self.current_index = index
            self.btn_home.setChecked(False)
            for i, it in enumerate(self.items):
                it.set_active(i == index, self.theme_name)
            self.apply_theme(self.theme_name)

    def set_tab_text(self, index: int, text: str):
        if 0 <= index < len(self.items):
            self.items[index].set_title(text)

    def count(self) -> int:
        return len(self.items)

    def _on_item_clicked(self, index: int):
        self.set_current_index(index)
        self.currentChanged.emit(index)

    def _on_home_clicked(self):
        self.set_home_active(True)
        self.homeRequested.emit()


class ModernTabHoverPreview(QWidget):
    """Modern tarayıcı tipi açık sekme küçük resim önizleme kartı (Hover Preview Card)."""
    def __init__(self, parent=None):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(0)

        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("TabHoverPreviewCard")
        root_layout.addWidget(self.card_frame)

        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(10, 8, 10, 10)
        card_layout.setSpacing(6)

        # Üst Başlık ve Sayfa Bilgisi
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(ModernIconFactory.icon_app().pixmap(14, 14))
        self.lbl_icon.setFixedSize(14, 14)
        header_layout.addWidget(self.lbl_icon)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("PreviewTitle")
        text_layout.addWidget(self.lbl_title)

        self.lbl_page_info = QLabel()
        self.lbl_page_info.setObjectName("PreviewPageInfo")
        text_layout.addWidget(self.lbl_page_info)

        header_layout.addLayout(text_layout)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)

        # Önizleme Görseli (Küçük Resim)
        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setObjectName("PreviewThumbnail")
        self.lbl_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumbnail.setMinimumSize(180, 120)
        card_layout.addWidget(self.lbl_thumbnail)

        # Gölgelendirme efekti
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.card_frame.setGraphicsEffect(shadow)

        self._current_theme = "light"
        self.apply_theme("light")

    def apply_theme(self, theme_name: str):
        self._current_theme = theme_name
        c = get_modern_theme_colors(theme_name)
        is_dark = theme_name != "light"
        bg_col = c.get("surface", "#1e2022") if is_dark else "#ffffff"
        border_col = c.get("border", "#3c3f44")
        text_col = c.get("text", "#f8fafc") if is_dark else "#0f172a"
        text_muted = c.get("text_muted", "#94a3b8")
        thumb_bg = "#111215" if is_dark else "#f1f5f9"
        thumb_border = c.get("border_subtle", "#334155")

        self.card_frame.setStyleSheet(f"""
            QFrame#TabHoverPreviewCard {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 8px;
            }}
            QLabel#PreviewTitle {{
                color: {text_col};
                font-weight: 600;
                font-size: 12px;
                border: none;
                background: transparent;
            }}
            QLabel#PreviewPageInfo {{
                color: {text_muted};
                font-size: 11px;
                border: none;
                background: transparent;
            }}
            QLabel#PreviewThumbnail {{
                background-color: {thumb_bg};
                border: 1px solid {thumb_border};
                border-radius: 4px;
                padding: 3px;
            }}
        """)

    def show_preview(self, title: str, page_text: str, pixmap: QPixmap, global_pos: QPoint):
        fm = self.lbl_title.fontMetrics()
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, 180)
        self.lbl_title.setText(elided)
        self.lbl_page_info.setText(page_text)
        self.lbl_thumbnail.setPixmap(pixmap)
        self.lbl_thumbnail.setFixedSize(pixmap.size())
        self.adjustSize()

        screen = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        target_pos = QPoint(global_pos)
        if screen:
            card_w = self.sizeHint().width() if self.sizeHint().width() > 10 else 210
            card_h = self.sizeHint().height() if self.sizeHint().height() > 10 else 260
            if target_pos.x() + card_w > screen.right() - 8:
                target_pos.setX(screen.right() - card_w - 8)
            if target_pos.x() < screen.left() + 8:
                target_pos.setX(screen.left() + 8)
            if target_pos.y() + card_h > screen.bottom() - 8:
                target_pos.setY(screen.bottom() - card_h - 8)

        self.move(target_pos)
        self.show()
        self.raise_()


# ==============================================================================
# 2. SABİTLENMİŞ VE ÜST GEZİNME ÇUBUĞU BİLEŞENLERİ
# ==============================================================================
class ModernPinnedQuickToolsBar(QFrame):
    """
    Üst araç çubuğuna sabitlenmiş minimalist yatay hızlı araçlar kapsülü.
    Hareketli araç çubuğundaki tüm işlevlerle (seçim, vurgulayıcı, yorum, metin, kalem, silgi)
    birebir senkronize çalışır ve minimalist şık bir yatay kapsül olarak görünür.
    """
    toolSelected = pyqtSignal(str)
    toolSelectedWithWidget = pyqtSignal(str, object)
    unpinRequested = pyqtSignal()

    def __init__(self, parent=None, orientation=Qt.Orientation.Horizontal):
        super().__init__(parent)
        self.setObjectName("PinnedQuickToolsBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.orientation = orientation
        self.active_tool = "select"
        self.theme_name = "gray"
        self.buttons: Dict[str, QToolButton] = {}

        if self.orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(42)
            layout = QHBoxLayout(self)
            layout.setContentsMargins(8, 2, 8, 2)
            layout.setSpacing(4)
            layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(16)
            shadow.setColor(QColor(0, 0, 0, 45))
            shadow.setOffset(0, 2)
            self.setGraphicsEffect(shadow)
        else:
            self.setFixedWidth(46)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(4, 6, 4, 6)
            layout.setSpacing(4)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.default_order = ["select", "selection", "pen", "highlighter", "eraser", "text", "insert", "comment", "pointer"]

        self.tool_specs_factory = {
            "select": ("quick_tool_select", lambda: ModernIconFactory.icon_cursor()),
            "selection": ("quick_tool_draw_select", lambda: ModernIconFactory.icon_select_rect("#38bdf8")),
            "pen": ("quick_tool_pen", lambda: ModernIconFactory.icon_pen("#0284c7")),
            "highlighter": ("quick_tool_highlighter", lambda: ModernIconFactory.icon_highlighter("#eab308")),
            "eraser": ("quick_tool_eraser", lambda: ModernIconFactory.icon_eraser("#ef4444")),
            "text": ("quick_tool_text", lambda: ModernIconFactory.icon_text_tool("#ec4899")),
            "insert": ("insert_btn_tip", lambda: ModernIconFactory.icon_insert("#10b981")),
            "comment": ("quick_tool_comment", lambda: ModernIconFactory.icon_comments("#f97316")),
            "pointer": ("quick_tool_pointer", lambda: ModernIconFactory.icon_pointer("#ef4444")),
        }

        # Kaydedilmiş araç sıralamasını yükle (ve sürüm kontrolüyle gerekirse yeni varsayılana taşı)
        settings = QSettings("AuraPDF", "PDFViewer")
        tb_version = settings.value("floating_tools_order_version", 0, type=int)
        raw_order = settings.value("floating_tools_order", None)
        loaded_order = []
        if raw_order and tb_version >= 2:
            try:
                if isinstance(raw_order, str):
                    loaded_order = json.loads(raw_order)
                elif isinstance(raw_order, list):
                    loaded_order = list(raw_order)
            except Exception:
                loaded_order = []

        valid_order = [x for x in loaded_order if x in self.tool_specs_factory]
        if not valid_order or tb_version < 2:
            valid_order = list(self.default_order)
        else:
            for k in self.default_order:
                if k not in valid_order:
                    valid_order.append(k)
        self.tool_order = valid_order

        # Ayırıcı ve Ayır (Unpin) butonu
        self.sep = QFrame(self)
        if self.orientation == Qt.Orientation.Horizontal:
            self.sep.setFrameShape(QFrame.Shape.VLine)
            self.sep.setFixedWidth(1)
            self.sep.setFixedHeight(24)
        else:
            self.sep.setFrameShape(QFrame.Shape.HLine)
            self.sep.setFixedHeight(1)
            self.sep.setFixedWidth(28)
        self.sep.setObjectName("PinnedSep")

        self.btn_unpin = QToolButton(self)
        self.btn_unpin.setIcon(ModernIconFactory.icon_unpin())
        self.btn_unpin.setIconSize(QSize(20, 20))
        self.btn_unpin.setFixedSize(38, 38)
        self.btn_unpin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unpin.setToolTip(LanguageManager.tr("capsule_unpin_float"))
        self.btn_unpin.clicked.connect(self.unpinRequested.emit)

        # Dikey yerleşimde unpin en üstte olsun
        if self.orientation == Qt.Orientation.Vertical:
            layout.addWidget(self.btn_unpin)
            layout.addWidget(self.sep)

        for tid in self.tool_order:
            key, icon_func = self.tool_specs_factory[tid]
            btn = QToolButton(self)
            btn.setIcon(icon_func())
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(38, 38)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(LanguageManager.tr(key))
            btn.clicked.connect(lambda checked, t=tid: self._on_btn_clicked(t))
            layout.addWidget(btn)
            self.buttons[tid] = btn

        if "select" in self.buttons:
            self.buttons["select"].setChecked(True)

        # Yatay yerleşimde unpin en sağda olsun
        if self.orientation == Qt.Orientation.Horizontal:
            layout.addWidget(self.sep)
            layout.addWidget(self.btn_unpin)

        self.adjustSize()
        self.apply_theme(self.theme_name)

    def sizeHint(self):
        if self.orientation == Qt.Orientation.Horizontal:
            btn_count = len(self.buttons) + (1 if hasattr(self, 'btn_unpin') else 0)
            total_w = btn_count * 38 + max(0, btn_count - 1) * 4 + 1 + 8 + 16
            return QSize(total_w, 42)
        return super().sizeHint()

    def set_tools_order(self, order: list):
        """Ayarlardan veya hareketli araç çubuğundan gelen yeni sıralamaya göre butonları yeniden düzenler."""
        cleaned_order = []
        for x in order:
            tid = x[4:] if x.startswith("btn_") and x[4:] in self.tool_specs_factory else x
            if tid in self.tool_specs_factory and tid not in cleaned_order:
                cleaned_order.append(tid)
        valid_order = list(cleaned_order)
        for k in self.default_order:
            if k not in valid_order:
                valid_order.append(k)
        if valid_order == self.tool_order:
            self.adjustSize()
            return
        self.tool_order = valid_order

        layout = self.layout()
        for btn in self.buttons.values():
            layout.removeWidget(btn)
        if hasattr(self, 'sep'):
            layout.removeWidget(self.sep)
        if hasattr(self, 'btn_unpin'):
            layout.removeWidget(self.btn_unpin)

        if self.orientation == Qt.Orientation.Vertical:
            if hasattr(self, 'btn_unpin'):
                layout.addWidget(self.btn_unpin)
            if hasattr(self, 'sep'):
                layout.addWidget(self.sep)
            for tid in self.tool_order:
                if tid in self.buttons:
                    layout.addWidget(self.buttons[tid])
        else:
            for tid in self.tool_order:
                if tid in self.buttons:
                    layout.addWidget(self.buttons[tid])
            if hasattr(self, 'sep'):
                layout.addWidget(self.sep)
            if hasattr(self, 'btn_unpin'):
                layout.addWidget(self.btn_unpin)
        self.adjustSize()

    def _on_btn_clicked(self, tool_id: str):
        self.set_active_tool(tool_id)
        self.toolSelected.emit(tool_id)
        btn = self.buttons.get(tool_id)
        self.toolSelectedWithWidget.emit(tool_id, btn)

    def set_active_tool(self, tool_id: str):
        self.active_tool = tool_id
        for tid, btn in self.buttons.items():
            btn.setChecked(tid == tool_id)

    def update_cursor_mode(self, mode: str):
        btn = self.buttons.get("select")
        if not btn: return
        if mode == 'pan':
            btn.setIcon(ModernIconFactory.icon_select_pan())
            btn.setToolTip(LanguageManager.tr("tb_item_cursor"))
        else:
            btn.setIcon(ModernIconFactory.icon_cursor())
            btn.setToolTip(LanguageManager.tr("quick_tool_select"))

    def update_selection_mode(self, mode: str):
        btn = self.buttons.get("selection")
        if not btn: return
        if mode == 'lasso':
            btn.setIcon(ModernIconFactory.icon_select_lasso("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("sel_lasso").strip())
        elif mode == 'move':
            btn.setIcon(ModernIconFactory.icon_select_move("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("sel_move").strip() if LanguageManager.tr("sel_move") != "sel_move" else "Seçimi Taşı")
        elif mode == 'ruler':
            btn.setIcon(ModernIconFactory.icon_ruler("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("tb_item_ruler"))
        else:
            btn.setIcon(ModernIconFactory.icon_select_rect("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("quick_tool_draw_select"))

    def retranslate_ui(self):
        for tid, btn in self.buttons.items():
            if tid in self.tool_specs_factory:
                key, _ = self.tool_specs_factory[tid]
                btn.setToolTip(LanguageManager.tr(key))
        if hasattr(self, 'btn_unpin'):
            self.btn_unpin.setToolTip(LanguageManager.tr("capsule_unpin_float"))

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'btn_unpin'):
            self.btn_unpin.setIcon(ModernIconFactory.icon_unpin(c['text_muted']))
        if "select" in self.buttons and getattr(self, 'cursor_mode', 'select') == 'select':
            self.buttons["select"].setIcon(ModernIconFactory.icon_cursor(c['text']))
        
        border_style = f"border: 1px solid {c['border']}; border-radius: 21px;" if self.orientation == Qt.Orientation.Horizontal else f"border-right: 1px solid {c['border']}; border-left: 1px solid {c['border']}; border-radius: 0px;"
        self.setStyleSheet(f"""
            #PinnedQuickToolsBar {{
                background-color: {c['card_bg']};
                {border_style}
            }}
            #PinnedSep {{
                background-color: {c['border']};
                border: none;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
                color: {c['text']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
            }}
            QToolButton:checked {{
                background-color: {c['accent_light']};
                border: 1px solid {c['accent']};
            }}
        """)


class CapsulePageLineEdit(QLineEdit):
    """
    Kapsül içi sayfa numarası giriş kutusu.
    Tıklandığında tüm metni seçer, Enter veya odak kaybında sayfaya atlar.
    """
    pageSubmitted = pyqtSignal(int)

    def __init__(self, default_text: str = "1", parent=None):
        super().__init__(default_text, parent)
        self.setObjectName("CapsulePageInput")
        self.setFixedWidth(36)
        self.setFixedHeight(24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setValidator(QIntValidator(1, 99999, self))
        self._current_page = 1
        self._total_pages = 1

    def set_page_value(self, current: int, total: int):
        self._current_page = current
        self._total_pages = max(1, total)
        if not self.hasFocus():
            self.blockSignals(True)
            self.setText(str(current))
            self.blockSignals(False)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._commit_page()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit_page()
            self.clearFocus()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.setText(str(self._current_page))
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def _commit_page(self):
        text = self.text().strip()
        try:
            val = int(text)
            val = max(1, min(val, self._total_pages))
            if val != self._current_page:
                self._current_page = val
                self.setText(str(val))
                self.pageSubmitted.emit(val)
            else:
                self.setText(str(val))
        except ValueError:
            self.setText(str(self._current_page))


class CapsuleZoomLineEdit(QLineEdit):
    """
    Kapsül içi yakınlaştırma (Zoom) giriş kutusu.
    Tıklandığında tüm metni seçer (yüzde işareti hariç sayı odaklı),
    Enter veya odak kaybında (focusOut) yeni yüzdeyi onaylar, Esc ile iptal eder.
    """
    zoomSubmitted = pyqtSignal(int)

    def __init__(self, default_text: str = "100%", parent=None):
        super().__init__(default_text, parent)
        self.setObjectName("CapsuleZoomInput")
        self.setFixedWidth(54)
        self.setFixedHeight(24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_zoom = 100
        self._is_editing = False

    def set_zoom_value(self, val: int):
        self._current_zoom = val
        if not self.hasFocus():
            self._is_editing = False
            self.blockSignals(True)
            self.setText(f"{val}%")
            self.blockSignals(False)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self._is_editing:
            self._is_editing = True
            raw_text = self.text().replace('%', '').strip()
            self.setText(raw_text)
        QTimer.singleShot(0, self.selectAll)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._is_editing = True
        raw_text = self.text().replace('%', '').strip()
        self.setText(raw_text)
        QTimer.singleShot(0, self.selectAll)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._is_editing:
            self._commit_zoom()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit_zoom()
            self.clearFocus()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self._is_editing = False
            self.setText(f"{self._current_zoom}%")
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def _commit_zoom(self):
        self._is_editing = False
        text = self.text().replace('%', '').strip()
        try:
            val = int(round(float(text)))
            val = max(10, min(val, 1000))
            self._current_zoom = val
            self.setText(f"{val}%")
            self.zoomSubmitted.emit(val)
        except ValueError:
            self.setText(f"{self._current_zoom}%")


class ModernHeaderBar(QWidget):
    pageJumpRequested = pyqtSignal(int)
    prevPageRequested = pyqtSignal()
    nextPageRequested = pyqtSignal()
    zoomInRequested = pyqtSignal()
    zoomOutRequested = pyqtSignal()
    fitPageRequested = pyqtSignal()
    rotateRequested = pyqtSignal()
    zoomSetRequested = pyqtSignal(int)

    """
    Üst Başlık Çubuğu:
    - [Menü] butonu
    - [Tüm araçlar | Oku | Düzenle | Dönüştür | E-İmza] navigasyon sekmeleri
    - [Araçları ve komutları bulun (Ctrl+K)] arama kutusu
    - [Bilgi (i)] [Yazdır] [Kaydet/Paylaş] [Ayarlar]
    """
    modeChanged = pyqtSignal(str)
    menuRequested = pyqtSignal(QPoint)
    searchRequested = pyqtSignal()
    helpRequested = pyqtSignal()
    printRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    settingsRequested = pyqtSignal()
    fullscreenRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "gray"
        self.current_mode = "all_tools"
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 14, 4)
        layout.setSpacing(10)

        # 1. Menü Butonu
        self.btn_menu = QToolButton()
        self.btn_menu.setText(" " + LanguageManager.tr("menu_btn_text"))
        self.btn_menu.setIcon(ModernIconFactory.icon_menu_hamburger())
        self.btn_menu.setIconSize(QSize(16, 16))
        self.btn_menu.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.clicked.connect(lambda: self.menuRequested.emit(self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height()))))
        layout.addWidget(self.btn_menu)

        # Dikey Ayırıcı 1
        sep1 = QFrame()
        sep1.setObjectName("HeaderSep")
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(24)
        layout.addWidget(sep1)

        # 2. Mod Gezinme Butonları (Pill / Segmented)
        self.mode_buttons: Dict[str, QToolButton] = {}
        modes = [
            ("all_tools", "nav_all_tools"),
            ("read", "nav_read"),
            ("edit", "nav_edit"),
            ("convert", "nav_convert"),
            ("esign", "nav_esign"),
        ]
        for mode_id, key in modes:
            btn = QToolButton()
            btn.setText(LanguageManager.tr(key))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, m=mode_id: self.set_mode(m))
            layout.addWidget(btn)
            self.mode_buttons[mode_id] = btn

        self.mode_buttons["all_tools"].setChecked(True)

        # Dikey Ayırıcı (Modlar ile Sayfa Denetimleri arası)
        sep_mid = QFrame()
        sep_mid.setObjectName("HeaderSep")
        sep_mid.setFrameShape(QFrame.Shape.VLine)
        sep_mid.setFixedWidth(1)
        sep_mid.setFixedHeight(24)
        layout.addWidget(sep_mid)

        # ---- 1. Sayfa Gezinme Kapsülü (Belirgin Buton Şekilli Kapsül) ----
        self.page_capsule = QFrame()
        self.page_capsule.setObjectName("HeaderNavCapsule")
        self.page_capsule.setFixedHeight(32)
        h_page = QHBoxLayout(self.page_capsule)
        h_page.setContentsMargins(4, 2, 4, 2)
        h_page.setSpacing(2)

        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(ModernIconFactory.icon_chevron_left())
        self.btn_prev.setIconSize(QSize(16, 16))
        self.btn_prev.setFixedSize(26, 26)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setToolTip(LanguageManager.tr("prev_page"))
        self.btn_prev.clicked.connect(self.prevPageRequested.emit)
        h_page.addWidget(self.btn_prev)

        self.txt_page = CapsulePageLineEdit("1", self)
        self.txt_page.setToolTip(LanguageManager.tr("page_input_tip"))
        self.txt_page.pageSubmitted.connect(self.pageJumpRequested.emit)
        h_page.addWidget(self.txt_page)

        self.lbl_total = QLabel("/ 1")
        self.lbl_total.setObjectName("RailPageTotal")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        h_page.addWidget(self.lbl_total)

        self.btn_next = QToolButton()
        self.btn_next.setIcon(ModernIconFactory.icon_chevron_right())
        self.btn_next.setIconSize(QSize(16, 16))
        self.btn_next.setFixedSize(26, 26)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setToolTip(LanguageManager.tr("next_page"))
        self.btn_next.clicked.connect(self.nextPageRequested.emit)
        h_page.addWidget(self.btn_next)

        layout.addWidget(self.page_capsule)

        # ---- 2. Zoom ve Görünüm Kapsülü (Belirgin Buton Şekilli Kapsül) ----
        self.zoom_capsule = QFrame()
        self.zoom_capsule.setObjectName("HeaderNavCapsule")
        self.zoom_capsule.setFixedHeight(32)
        h_zoom = QHBoxLayout(self.zoom_capsule)
        h_zoom.setContentsMargins(4, 2, 4, 2)
        h_zoom.setSpacing(2)

        self.btn_zout = QToolButton()
        self.btn_zout.setIcon(ModernIconFactory.icon_minus())
        self.btn_zout.setIconSize(QSize(16, 16))
        self.btn_zout.setFixedSize(26, 26)
        self.btn_zout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zout.setToolTip(LanguageManager.tr("zoom_out"))
        self.btn_zout.clicked.connect(self.zoomOutRequested.emit)
        h_zoom.addWidget(self.btn_zout)

        self.txt_zoom = CapsuleZoomLineEdit("100%", self)
        self.txt_zoom.setToolTip(LanguageManager.tr("zoom_input_tip"))
        self.txt_zoom.zoomSubmitted.connect(self.zoomSetRequested.emit)
        h_zoom.addWidget(self.txt_zoom)

        self.btn_zin = QToolButton()
        self.btn_zin.setIcon(ModernIconFactory.icon_plus())
        self.btn_zin.setIconSize(QSize(16, 16))
        self.btn_zin.setFixedSize(26, 26)
        self.btn_zin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zin.setToolTip(LanguageManager.tr("zoom_in"))
        self.btn_zin.clicked.connect(self.zoomInRequested.emit)
        h_zoom.addWidget(self.btn_zin)

        sep_cap_inner = QFrame()
        sep_cap_inner.setObjectName("CapsuleInnerSep")
        sep_cap_inner.setFrameShape(QFrame.Shape.VLine)
        sep_cap_inner.setFixedWidth(1)
        sep_cap_inner.setFixedHeight(18)
        h_zoom.addWidget(sep_cap_inner)

        self.btn_fit = QToolButton()
        self.btn_fit.setIcon(ModernIconFactory.icon_fit_page())
        self.btn_fit.setIconSize(QSize(16, 16))
        self.btn_fit.setFixedSize(28, 26)
        self.btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
        self.btn_fit.clicked.connect(self.fitPageRequested.emit)
        h_zoom.addWidget(self.btn_fit)

        self.btn_rotate = QToolButton()
        self.btn_rotate.setIcon(ModernIconFactory.icon_rotate())
        self.btn_rotate.setIconSize(QSize(16, 16))
        self.btn_rotate.setFixedSize(28, 26)
        self.btn_rotate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rotate.setToolTip(LanguageManager.tr("tb_item_rotate"))
        self.btn_rotate.clicked.connect(self.rotateRequested.emit)
        h_zoom.addWidget(self.btn_rotate)

        layout.addWidget(self.zoom_capsule)

        layout.addStretch(1)

        # Sabitlenebilir Minimalist Hızlı Araçlar Kapsülü (Üst çubuğa enjekte edilmez)
        self.pinned_tools_capsule = ModernPinnedQuickToolsBar(self)
        self.pinned_tools_capsule.hide()

        # 3. Arama Çubuğu (Ctrl+K Pill Input)
        self.search_pill = QFrame()
        self.search_pill.setObjectName("SearchPill")
        self.search_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_pill.setFixedHeight(32)
        self.search_pill.setFixedWidth(260)
        h_search = QHBoxLayout(self.search_pill)
        h_search.setContentsMargins(10, 0, 10, 0)
        h_search.setSpacing(8)

        lbl_s_icon = QLabel()
        lbl_s_icon.setPixmap(ModernIconFactory.icon_search().pixmap(14, 14))
        h_search.addWidget(lbl_s_icon)

        self.lbl_search_text = QLabel(LanguageManager.tr("search_tools_placeholder"))
        h_search.addWidget(self.lbl_search_text, stretch=1)

        badge_shortcut = QLabel("⌘K / Ctrl+K")
        badge_shortcut.setObjectName("BadgeShortcut")
        h_search.addWidget(badge_shortcut)

        self.search_pill.mousePressEvent = lambda e: self.searchRequested.emit()
        layout.addWidget(self.search_pill)

        # Dikey Ayırıcı 3 (Arama ile Hızlı Eylemler arası)
        sep3 = QFrame()
        sep3.setObjectName("HeaderSep")
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setFixedWidth(1)
        sep3.setFixedHeight(24)
        layout.addWidget(sep3)


        # 4. Hızlı Eylem İkonları
        # Yazdır
        self.btn_print = QToolButton()
        self.btn_print.setIcon(ModernIconFactory.icon_print())
        self.btn_print.setIconSize(QSize(16, 16))
        self.btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_print.setToolTip(LanguageManager.tr("print_btn"))
        self.btn_print.clicked.connect(self.printRequested.emit)
        layout.addWidget(self.btn_print)

        # Kaydet / Paylaş
        self.btn_save = QToolButton()
        self.btn_save.setIcon(ModernIconFactory.icon_cloud_share())
        self.btn_save.setIconSize(QSize(16, 16))
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setToolTip(LanguageManager.tr("save_btn"))
        self.btn_save.clicked.connect(self.saveRequested.emit)
        layout.addWidget(self.btn_save)

        # Tam Ekran (F11) - 1. Pozisyon
        self.btn_fullscreen = QToolButton()
        self.btn_fullscreen.setIcon(ModernIconFactory.icon_fullscreen())
        self.btn_fullscreen.setIconSize(QSize(16, 16))
        self.btn_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.setToolTip(LanguageManager.tr("tb_item_fullscreen"))
        self.btn_fullscreen.clicked.connect(self.fullscreenRequested.emit)
        layout.addWidget(self.btn_fullscreen)

        # Ayarlar
        self.btn_settings = QToolButton()
        self.btn_settings.setIcon(ModernIconFactory.icon_settings())
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip(LanguageManager.tr("settings_title"))
        self.btn_settings.clicked.connect(self.settingsRequested.emit)
        layout.addWidget(self.btn_settings)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.btn_menu.setText(" " + LanguageManager.tr("menu_btn_text"))
        modes = [
            ("all_tools", "nav_all_tools"),
            ("read", "nav_read"),
            ("edit", "nav_edit"),
            ("convert", "nav_convert"),
            ("esign", "nav_esign"),
        ]
        for mode_id, key in modes:
            if mode_id in self.mode_buttons:
                self.mode_buttons[mode_id].setText(LanguageManager.tr(key))
        self.lbl_search_text.setText(LanguageManager.tr("search_tools_placeholder"))
        self.btn_print.setToolTip(LanguageManager.tr("print_btn"))
        self.btn_save.setToolTip(LanguageManager.tr("save_btn"))
        if hasattr(self, 'btn_fullscreen'):
            self.btn_fullscreen.setToolTip(LanguageManager.tr("tb_item_fullscreen"))
        if hasattr(self, 'btn_settings'):
            self.btn_settings.setToolTip(LanguageManager.tr("settings_title"))
        if hasattr(self, 'pinned_tools_capsule'):
            self.pinned_tools_capsule.retranslate_ui()
        if hasattr(self, 'txt_page'):
            self.txt_page.setToolTip(LanguageManager.tr("page_input_tip"))
        if hasattr(self, 'txt_zoom'):
            self.txt_zoom.setToolTip(LanguageManager.tr("zoom_input_tip"))
        if hasattr(self, 'btn_prev'):
            self.btn_prev.setToolTip(LanguageManager.tr("prev_page"))
        if hasattr(self, 'btn_next'):
            self.btn_next.setToolTip(LanguageManager.tr("next_page"))
        if hasattr(self, 'btn_zout'):
            self.btn_zout.setToolTip(LanguageManager.tr("zoom_out"))
        if hasattr(self, 'btn_zin'):
            self.btn_zin.setToolTip(LanguageManager.tr("zoom_in"))
        if hasattr(self, 'btn_fit'):
            self.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
        if hasattr(self, 'btn_rotate'):
            self.btn_rotate.setToolTip(LanguageManager.tr("tb_item_rotate"))

    def set_mode(self, mode_id: str):
        self.current_mode = mode_id
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode_id)
        self.modeChanged.emit(mode_id)

    def update_page_info(self, current: int, total: int):
        self.total_pages = total
        if hasattr(self, 'txt_page'):
            self.txt_page.set_page_value(current, total)
        if hasattr(self, 'lbl_total'):
            self.lbl_total.setText(f"/ {total}")

    def update_zoom_info(self, zoom_percent: int):
        if hasattr(self, 'txt_zoom'):
            self.txt_zoom.set_zoom_value(zoom_percent)

    def _on_page_submitted(self):
        if hasattr(self, 'txt_page'):
            self.txt_page._commit_page()

    def _on_zoom_submitted(self):
        if hasattr(self, 'txt_zoom'):
            self.txt_zoom._commit_zoom()

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'pinned_tools_capsule'):
            self.pinned_tools_capsule.apply_theme(theme_name)

        if hasattr(self, 'btn_prev'):
            self.btn_prev.setIcon(ModernIconFactory.icon_chevron_left(c['text']))
        if hasattr(self, 'btn_next'):
            self.btn_next.setIcon(ModernIconFactory.icon_chevron_right(c['text']))
        if hasattr(self, 'btn_zout'):
            self.btn_zout.setIcon(ModernIconFactory.icon_minus(c['text']))
        if hasattr(self, 'btn_zin'):
            self.btn_zin.setIcon(ModernIconFactory.icon_plus(c['text']))
        if hasattr(self, 'btn_fit'):
            self.btn_fit.setIcon(ModernIconFactory.icon_fit_page(c['text']))
        if hasattr(self, 'btn_rotate'):
            self.btn_rotate.setIcon(ModernIconFactory.icon_rotate(c['text']))

        self.setStyleSheet(f"""
            ModernHeaderBar {{
                background-color: {c['surface']};
                border-bottom: 1px solid {c['border']};
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 10px;
                color: {c['text']};
                font-size: 13px;
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
            }}
            QToolButton:checked {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                font-weight: 600;
                border-bottom: 2px solid {c['accent']};
                border-radius: 4px;
            }}
            QFrame#SearchPill {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
            QFrame#HeaderNavCapsule {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QFrame#HeaderNavCapsule QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 5px;
                padding: 0px;
                margin: 0px;
                min-width: 26px;
                min-height: 26px;
                color: {c['text']};
            }}
            QFrame#HeaderNavCapsule QToolButton:hover {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
            }}
            QFrame#HeaderNavCapsule QToolButton:pressed {{
                background-color: {c['surface_active']};
            }}
            QFrame#HeaderNavCapsule QLineEdit {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: {c['text']};
                font-size: 12px;
                font-weight: 600;
                padding: 0px 2px;
            }}
            QFrame#HeaderNavCapsule QLineEdit:hover {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
            }}
            QFrame#HeaderNavCapsule QLineEdit:focus {{
                background-color: {c['card_bg']};
                border: 1px solid {c['accent']};
            }}
            QFrame#HeaderNavCapsule QLabel#RailPageTotal {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 500;
                padding-right: 2px;
            }}
            QFrame#CapsuleInnerSep {{
                background-color: {c['border']};
                border: none;
            }}
            QFrame#HeaderSep {{
                background-color: {c['border']};
                border: none;
            }}
            QLabel {{
                color: {c['text_muted']};
                font-size: 12px;
            }}
            QLabel#RailPageTotal {{
                color: {c['text_muted']};
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text']};
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {c['accent']};
            }}
    QLabel#BadgeShortcut {{
                background-color: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 1px 5px;
                font-size: 10px;
                font-weight: 600;
            }}
        """)


# ==============================================================================
# 3. SOL ÇEKMECE ARAÇ PANELİ (ModernAllToolsPanel)
# ==============================================================================
class ModernToolItemWidget(QFrame):
    """'Tüm araçlar' listesindeki modern, temaya duyarlı ve dinamik buton öğesi."""
    clicked = pyqtSignal(str)

    def __init__(self, tool_id: str, label_text: str, icon: QIcon, accent_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernToolItemWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tool_id = tool_id
        self.accent_color = accent_color
        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)

        h = QHBoxLayout(self)
        h.setContentsMargins(6, 0, 10, 0)
        h.setSpacing(10)

        # 1. Sol Dikey İnce Aktif Gösterge Kapsülü (Fluent/macOS Style)
        self.indicator_pill = QFrame(self)
        self.indicator_pill.setFixedSize(3, 18)
        self.indicator_pill.setStyleSheet("background-color: transparent; border-radius: 1.5px;")
        h.addWidget(self.indicator_pill)

        # 2. İkon Yuvası (Micro Badge Plate)
        self.icon_box = QFrame(self)
        self.icon_box.setFixedSize(28, 28)
        h_icon = QHBoxLayout(self.icon_box)
        h_icon.setContentsMargins(0, 0, 0, 0)
        h_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel(self.icon_box)
        self.lbl_icon.setPixmap(icon.pixmap(20, 20))
        self.lbl_icon.setFixedSize(20, 20)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        h_icon.addWidget(self.lbl_icon)
        h.addWidget(self.icon_box)

        # 3. Metin
        self.lbl_text = QLabel(label_text, self)
        self.lbl_text.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self.lbl_text, stretch=1)

        # 4. Sağ Aktif Gösterge Rozeti (Zarif nokta)
        self.lbl_active_indicator = QLabel(self)
        self.lbl_active_indicator.setFixedSize(6, 6)
        self.lbl_active_indicator.setStyleSheet("background-color: transparent; border-radius: 3px;")
        h.addWidget(self.lbl_active_indicator)

    def set_text(self, text: str):
        self.lbl_text.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool_id)
        super().mousePressEvent(event)

    def set_active(self, active: bool, theme_name: str = "light"):
        self.is_active = active
        self._apply_style(theme_name)

    def _apply_style(self, theme_name: str = "light"):
        c = get_modern_theme_colors(theme_name)
        accent = c.get('accent', '#38bdf8')
        ac = QColor(accent) if QColor.isValidColor(accent) else QColor("#38bdf8")

        tint_start = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.18)"
        tint_end = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.04)"
        border_col = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.32)"
        icon_bg = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.16)"
        icon_border = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.28)"

        is_dark = QColor(c.get('surface', '#1c1c1c')).lightness() < 128
        active_text_color = "#ffffff" if is_dark else c['text']

        if self.is_active:
            self.indicator_pill.setStyleSheet(f"""
                background-color: {accent};
                border-radius: 1.5px;
            """)
            self.icon_box.setStyleSheet(f"""
                background-color: {icon_bg};
                border: 1px solid {icon_border};
                border-radius: 7px;
            """)
            self.lbl_active_indicator.setStyleSheet(f"""
                background-color: {accent};
                border-radius: 3px;
            """)
            self.lbl_text.setStyleSheet(f"""
                color: {active_text_color};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            """)
            self.setStyleSheet(f"""
                QFrame#ModernToolItemWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {tint_start}, stop:1 {tint_end});
                    border: 1px solid {border_col};
                    border-radius: 8px;
                }}
            """)
        else:
            self.indicator_pill.setStyleSheet("background-color: transparent;")
            self.icon_box.setStyleSheet("background-color: transparent; border: none;")
            self.lbl_active_indicator.setStyleSheet("background-color: transparent;")
            self.lbl_text.setStyleSheet(f"""
                color: {c['text']};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            """)
            self.setStyleSheet(f"""
                QFrame#ModernToolItemWidget {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }}
                QFrame#ModernToolItemWidget:hover {{
                    background-color: {c['surface_hover']};
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
            """)


class ModernNoticeCard(QFrame):
    """
    Tüm sol panel ve çekmecelerde ortak kullanılan ultra-modern, tema duyarlı
    Callout / Bilgilendirme ve Rehber Kartı bileşeni.
    - Sol: Vektörel tematik mikro-rozet (30x30 piksel)
    - Sağ: Rozet başlığı (üstte) + 2-3 satırlık açıklama metni
    - Dinamik tema desteği: apply_theme(theme_name)
    - Dinamik dil desteği: retranslate_ui()
    """
    def __init__(self, badge_key: str, notice_key: str, icon_factory_func, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernNoticeCard")
        self.badge_key = badge_key
        self.notice_key = notice_key
        self.icon_factory_func = icon_factory_func
        self.theme_name = "light"

        self.setMinimumHeight(78)

        h_notice = QHBoxLayout(self)
        h_notice.setContentsMargins(10, 8, 10, 8)
        h_notice.setSpacing(10)

        # Sol İkon Kutusu (Micro Badge)
        self.notice_icon_box = QFrame(self)
        self.notice_icon_box.setObjectName("NoticeIconBox")
        self.notice_icon_box.setFixedSize(30, 30)
        h_nibox = QHBoxLayout(self.notice_icon_box)
        h_nibox.setContentsMargins(0, 0, 0, 0)
        h_nibox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_notice_icon = QLabel(self.notice_icon_box)
        self.lbl_notice_icon.setFixedSize(18, 18)
        self.lbl_notice_icon.setScaledContents(True)
        h_nibox.addWidget(self.lbl_notice_icon)
        h_notice.addWidget(self.notice_icon_box, alignment=Qt.AlignmentFlag.AlignTop)

        # Sağ Metin Alanı
        v_notice_texts = QVBoxLayout()
        v_notice_texts.setContentsMargins(0, 0, 0, 0)
        v_notice_texts.setSpacing(2)

        self.lbl_notice_badge = QLabel(LanguageManager.tr(self.badge_key))
        self.lbl_notice_badge.setObjectName("NoticeBadgeLabel")
        v_notice_texts.addWidget(self.lbl_notice_badge)

        self.lbl_notice = QLabel(LanguageManager.tr(self.notice_key))
        self.lbl_notice.setObjectName("NoticeBodyLabel")
        self.lbl_notice.setWordWrap(True)
        v_notice_texts.addWidget(self.lbl_notice)

        h_notice.addLayout(v_notice_texts, stretch=1)

    def retranslate_ui(self):
        self.lbl_notice_badge.setText(LanguageManager.tr(self.badge_key))
        self.lbl_notice.setText(LanguageManager.tr(self.notice_key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        accent = c.get('accent', '#38bdf8')
        ac = QColor(accent) if QColor.isValidColor(accent) else QColor("#38bdf8")

        ar, ag, ab = ac.red(), ac.green(), ac.blue()
        tint_top = f"rgba({ar}, {ag}, {ab}, 0.16)"
        tint_bot = f"rgba({ar}, {ag}, {ab}, 0.04)"
        border_col = f"rgba({ar}, {ag}, {ab}, 0.35)"
        icon_bg = f"rgba({ar}, {ag}, {ab}, 0.18)"
        icon_border = f"rgba({ar}, {ag}, {ab}, 0.30)"

        is_dark = QColor(c.get('surface', '#1c1c1c')).lightness() < 128
        body_text_col = "#f8fafc" if is_dark else "#0f172a"

        self.setStyleSheet(f"""
            QFrame#ModernNoticeCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {tint_top}, stop:1 {tint_bot});
                border: 1px solid {border_col};
                border-radius: 9px;
            }}
            QFrame#NoticeIconBox {{
                background-color: {icon_bg};
                border: 1px solid {icon_border};
                border-radius: 7px;
            }}
            QLabel#NoticeBadgeLabel {{
                color: {accent};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.6px;
                background: transparent;
                border: none;
            }}
            QLabel#NoticeBodyLabel {{
                color: {body_text_col};
                font-size: 11px;
                font-weight: 500;
                line-height: 1.25;
                background: transparent;
                border: none;
            }}
        """)
        try:
            icon = self.icon_factory_func(accent)
        except TypeError:
            icon = self.icon_factory_func()
        self.lbl_notice_icon.setPixmap(icon.pixmap(18, 18))


class ModernAllToolsPanel(QWidget):
    """
    Ekranın solunda yer alan 'Tüm Araçlar' paneli:
    - Başlık: 'Tüm araçlar' + Kapatma (✕)
    - Export a PDF, Fill & Sign, Edit a PDF, Create a PDF, Combine files,
       Organize pages, Add comments, Scan & OCR, Protect a PDF, Redact a PDF,
       Compress a PDF, Prepare a form, Add a stamp, Use a certificate
    - 'Daha fazla gör' bağlantısı
    """
    toolTriggered = pyqtSignal(str)
    closeRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent.main_window if hasattr(parent, "main_window") else None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.active_tool_id: Optional[str] = "organize_pages"
        self.is_expanded = False
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(6)

        # Başlık ve Kapat Butonu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(6, 0, 4, 6)
        self.lbl_head = QLabel(LanguageManager.tr("nav_all_tools"))
        self.lbl_head.setStyleSheet("font-size: 15px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_tools_badge", "drawer_tools_notice", ModernIconFactory.icon_toolbox, self)
        main_layout.addWidget(self.notice_box)

        # Kaydırılabilir Araçlar Listesi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tools_container = QWidget()
        tools_container.setObjectName("ToolsContainer")
        self.v_tools = QVBoxLayout(tools_container)
        self.v_tools.setContentsMargins(2, 4, 2, 4)
        self.v_tools.setSpacing(3)

        self.items: Dict[str, ModernToolItemWidget] = {}
        self.tool_keys: Dict[str, str] = {}
        standard_tool_specs = [
            ("export_pdf", "tool_export_pdf", ModernIconFactory.icon_export_pdf("#0ea5e9"), "#0ea5e9"),
            ("fill_sign", "tool_fill_sign", ModernIconFactory.icon_fill_sign("#a855f7"), "#a855f7"),
            ("edit_pdf", "tool_edit_pdf", ModernIconFactory.icon_edit_content("#ec4899"), "#ec4899"),
            ("create_pdf", "tool_create_pdf", ModernIconFactory.icon_new_document("#ef4444"), "#ef4444"),
            ("combine_files", "tool_combine_files", ModernIconFactory.icon_combine_files("#38bdf8"), "#38bdf8"),
            ("organize_pages", "tool_organize_pages", ModernIconFactory.icon_organize("#22c55e"), "#22c55e"),
            ("add_comments", "tool_add_comments", ModernIconFactory.icon_comments("#f59e0b"), "#f59e0b"),
            ("scan_ocr", "tool_scan_ocr", ModernIconFactory.icon_ocr("#10b981"), "#10b981"),
            ("protect_pdf", "tool_protect_pdf", ModernIconFactory.icon_lock("#3b82f6"), "#3b82f6"),
            ("redact_pdf", "tool_redact_pdf", ModernIconFactory.icon_redact("#ef4444"), "#ef4444"),
            ("compress_pdf", "tool_compress_pdf", ModernIconFactory.icon_compress("#ef4444"), "#ef4444"),
            ("compare_files", "tool_compare_files", ModernIconFactory.icon_compare("#a855f7"), "#a855f7"),
            ("prepare_form", "tool_prepare_form", ModernIconFactory.icon_prepare_form("#a855f7"), "#a855f7"),
            ("add_stamp", "tool_add_stamp", ModernIconFactory.icon_stamp("#06b6d4"), "#06b6d4"),
        ]

        for tid, key, icon, col in standard_tool_specs:
            self.tool_keys[tid] = key
            item = ModernToolItemWidget(tid, LanguageManager.tr(key), icon, col, parent=tools_container)
            item.clicked.connect(self._on_item_clicked)
            self.v_tools.addWidget(item)
            self.items[tid] = item

        # Aşağı Doğru Genişleyen Ekstra Araçlar Konteyneri
        self.extra_tools_container = QWidget(tools_container)
        v_extra = QVBoxLayout(self.extra_tools_container)
        v_extra.setContentsMargins(0, 0, 0, 0)
        v_extra.setSpacing(2)

        extra_tool_specs = [
            ("print_production", "tool_print_production", ModernIconFactory.icon_print("#6366f1"), "#6366f1"),
        ]

        for tid, key, icon, col in extra_tool_specs:
            self.tool_keys[tid] = key
            item = ModernToolItemWidget(tid, LanguageManager.tr(key), icon, col, parent=self.extra_tools_container)
            item.clicked.connect(self._on_item_clicked)
            v_extra.addWidget(item)
            self.items[tid] = item

        self.extra_tools_container.setVisible(False)
        self.v_tools.addWidget(self.extra_tools_container)

        # 'Daha fazla gör / Daha az gör' bağlantı butonu
        self.btn_view_more = QPushButton(LanguageManager.tr("tool_view_more"))
        self.btn_view_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_more.clicked.connect(self._toggle_expand)
        self.v_tools.addWidget(self.btn_view_more)
        self.v_tools.addStretch(1)

        scroll.setWidget(tools_container)
        main_layout.addWidget(scroll)

        self.apply_theme(self.theme_name)
        self.set_active_tool("organize_pages")

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("nav_all_tools"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        self.btn_view_more.setText(
            LanguageManager.tr("tool_view_less") if self.is_expanded else LanguageManager.tr("tool_view_more")
        )
        for tid, key in self.tool_keys.items():
            if tid in self.items:
                self.items[tid].set_text(LanguageManager.tr(key))

    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.extra_tools_container.setVisible(self.is_expanded)
        self.btn_view_more.setText(
            LanguageManager.tr("tool_view_less") if self.is_expanded else LanguageManager.tr("tool_view_more")
        )

    def _on_item_clicked(self, tool_id: str):
        self.set_active_tool(tool_id)
        self.toolTriggered.emit(tool_id)

    def set_active_tool(self, tool_id: Optional[str]):
        self.active_tool_id = tool_id
        for tid, item in self.items.items():
            item.set_active(tid == tool_id, self.theme_name)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)
        self.setStyleSheet(f"""
            ModernAllToolsPanel {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#ToolsContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: {c['accent']};
                text-align: left;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['accent_hover']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        for item in self.items.values():
            item._apply_style(theme_name)


# ==============================================================================
# 3A. BAĞLAMSAL ÇEKMECELER (ModernExportDrawer & ModernEditDrawer)
# ==============================================================================
class ModernDrawerItemWidget(QFrame):
    """
    Bağlamsal sol çekmecelerdeki (Dışa Aktar, Düzenle, Okuma, E-İmza, Form)
    seçim belirginliği ve görsel hiyerarşisi tam uyumlu modern öğe bileşeni.
    - Sol: Dikey ince aktif gösterge kapsülü (3x18)
    - Orta: İkon mikro-rozet yuvası (28x28) + Başlık metni + İsteğe bağlı rozet
    - Sağ: Zarif aktif durum rozet noktası (6x6)
    """
    clicked = pyqtSignal(str)

    def __init__(self, item_id: str, title: str, icon: QIcon, badge_text: str = "", is_ready: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernDrawerItemWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.item_id = item_id
        self.title = title
        self.icon = icon
        self.is_ready = is_ready
        self.is_active = False
        self.theme_name = "light"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)

        h = QHBoxLayout(self)
        h.setContentsMargins(6, 0, 10, 0)
        h.setSpacing(10)

        # 1. Sol Dikey İnce Aktif Gösterge Kapsülü (Fluent/macOS Style)
        self.indicator_pill = QFrame(self)
        self.indicator_pill.setFixedSize(3, 18)
        self.indicator_pill.setStyleSheet("background-color: transparent; border-radius: 1.5px;")
        h.addWidget(self.indicator_pill)

        # 2. İkon Yuvası (Micro Badge Plate)
        self.icon_box = QFrame(self)
        self.icon_box.setFixedSize(28, 28)
        h_icon = QHBoxLayout(self.icon_box)
        h_icon.setContentsMargins(0, 0, 0, 0)
        h_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel(self.icon_box)
        self.lbl_icon.setPixmap(icon.pixmap(20, 20))
        self.lbl_icon.setFixedSize(20, 20)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        h_icon.addWidget(self.lbl_icon)
        h.addWidget(self.icon_box)

        # 3. Metin
        self.lbl_text = QLabel(title, self)
        self.lbl_text.setObjectName("DrawerItemText")
        self.lbl_text.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self.lbl_text, stretch=1)

        # 4. İsteğe Bağlı Badge
        self.lbl_badge = None
        if badge_text:
            self.lbl_badge = QLabel(badge_text, self)
            self.lbl_badge.setObjectName("DrawerItemBadge")
            h.addWidget(self.lbl_badge)

        # 5. Sağ Aktif Gösterge Rozeti (Zarif nokta)
        self.lbl_active_indicator = QLabel(self)
        self.lbl_active_indicator.setFixedSize(6, 6)
        self.lbl_active_indicator.setStyleSheet("background-color: transparent; border-radius: 3px;")
        h.addWidget(self.lbl_active_indicator)

    def set_title(self, title: str):
        self.title = title
        self.lbl_text.setText(title)

    def set_badge(self, text: str):
        if self.lbl_badge:
            self.lbl_badge.setText(text)
        elif text:
            self.lbl_badge = QLabel(text, self)
            self.lbl_badge.setObjectName("DrawerItemBadge")
            idx = self.layout().indexOf(self.lbl_active_indicator)
            if idx >= 0:
                self.layout().insertWidget(idx, self.lbl_badge)
            else:
                self.layout().addWidget(self.lbl_badge)
            self._apply_style(self.theme_name)

    def set_icon(self, icon: QIcon):
        self.icon = icon
        self.lbl_icon.setPixmap(icon.pixmap(20, 20))

    def set_active(self, active: bool, theme_name: Optional[str] = None):
        self.is_active = active
        self._apply_style(theme_name or self.theme_name)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(e)

    def _apply_style(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        accent = c.get('accent', '#38bdf8')
        ac = QColor(accent) if QColor.isValidColor(accent) else QColor("#38bdf8")

        tint_start = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.18)"
        tint_end = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.04)"
        border_col = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.32)"
        icon_bg = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.16)"
        icon_border = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, 0.28)"

        is_dark = QColor(c.get('surface', '#1c1c1c')).lightness() < 128
        active_text_color = "#ffffff" if is_dark else c['text']

        badge_css = """
            QLabel#DrawerItemBadge {
                background-color: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                border: 1px solid rgba(34, 197, 94, 0.35);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
                font-weight: 600;
            }
        """ if self.lbl_badge else ""

        if getattr(self, 'is_active', False):
            self.indicator_pill.setStyleSheet(f"""
                background-color: {accent};
                border-radius: 1.5px;
            """)
            self.icon_box.setStyleSheet(f"""
                background-color: {icon_bg};
                border: 1px solid {icon_border};
                border-radius: 7px;
            """)
            self.lbl_active_indicator.setStyleSheet(f"""
                background-color: {accent};
                border-radius: 3px;
            """)
            self.lbl_text.setStyleSheet(f"""
                color: {active_text_color};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            """)
            self.setStyleSheet(f"""
                QFrame#ModernDrawerItemWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {tint_start}, stop:1 {tint_end});
                    border: 1px solid {border_col};
                    border-radius: 8px;
                }}
                {badge_css}
            """)
        else:
            self.indicator_pill.setStyleSheet("background-color: transparent;")
            self.icon_box.setStyleSheet("background-color: transparent; border: none;")
            self.lbl_active_indicator.setStyleSheet("background-color: transparent;")
            self.lbl_text.setStyleSheet(f"""
                color: {c['text']};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            """)
            self.setStyleSheet(f"""
                QFrame#ModernDrawerItemWidget {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }}
                QFrame#ModernDrawerItemWidget:hover {{
                    background-color: {c['surface_hover']};
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
                {badge_css}
            """)


class ModernExportDrawer(QWidget):
    """
    Ekranın solundaki 'Export a PDF' çekmecesi:
    - Geri butonu (<) ve Başlık 'Export a PDF' + Kapatma (✕)
    - EXPORT TO başlığı
    - Word, Excel, PPTX, PNG, HTML, RTF, TXT, EPS formatları ve durum etiketleri
    """
    backRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    exportTriggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent.main_window if hasattr(parent, "main_window") else None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.active_export_id: Optional[str] = "word"
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(8)

        # Üst Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 4)

        btn_back = QToolButton()
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(12, 12))
        btn_back.setFixedSize(22, 22)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_export_title"))
        self.lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_export_badge", "drawer_export_notice", ModernIconFactory.icon_export_pdf, self)
        main_layout.addWidget(self.notice_box)

        # Kategori Başlığı: EXPORT TO
        self.lbl_cat = QLabel(LanguageManager.tr("drawer_export_to"))
        self.lbl_cat.setObjectName("CategoryHeader")
        main_layout.addWidget(self.lbl_cat)

        # Liste Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DrawerContainer")
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(2, 4, 2, 4)
        v_items.setSpacing(3)

        self.items: List[ModernDrawerItemWidget] = []
        self.specs = [
            ("word", "drawer_export_word", ModernIconFactory.icon_word("#0284c7"), "", True),
            ("xlsx", "drawer_export_xlsx", ModernIconFactory.icon_excel("#10b981"), "", True),
            ("pptx", "drawer_export_pptx", ModernIconFactory.icon_pptx("#ea580c"), "", True),
            ("png", "drawer_export_png", ModernIconFactory.icon_image("#0284c7"), "", True),
            ("all_images", "drawer_export_all_images", ModernIconFactory.icon_image_gallery("#0284c7"), "", True),
            ("html", "drawer_export_html", ModernIconFactory.icon_html("#0284c7"), "", True),
            ("rtf", "drawer_export_rtf", ModernIconFactory.icon_txt("#10b981"), "", True),
            ("txt", "drawer_export_txt", ModernIconFactory.icon_txt("#0284c7"), "", True),
            ("eps", "drawer_export_eps", ModernIconFactory.icon_eps("#8b5cf6"), "", True),
        ]

        for cid, key, icon, badge, is_ready in self.specs:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def _on_item_clicked(self, cid: str):
        self.active_export_id = cid
        self._update_item_active_states()
        self.exportTriggered.emit(cid)

    def _update_item_active_states(self):
        for it in self.items:
            it.set_active(it.item_id == self.active_export_id, self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_export_title"))
        self.lbl_cat.setText(LanguageManager.tr("drawer_export_to"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        for it, (_, key, _, _, _) in zip(self.items, self.specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)
        self.setStyleSheet(f"""
            ModernExportDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#DrawerContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 700;
                padding-top: 8px;
                padding-bottom: 3px;
                letter-spacing: 0.8px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        self._update_item_active_states()


class ModernEditDrawer(QWidget):
    """
    Ekranın solundaki 'Edit a PDF' çekmecesi:
    - Geri butonu (<) ve Başlık 'Edit a PDF' + Kapatma (✕)
    - Bilgilendirme kutucuğu
    - MODIFY PAGE grubu (Döndür, Ekle, Sil, Çıkar, Organize et)
    - ADD CONTENT grubu (Metin ve Resimler, Metin, Resim, Filigran vb.)
    """
    backRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    editTriggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent.main_window if hasattr(parent, "main_window") else None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.active_edit_id: Optional[str] = "edit_text_images"
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(8)

        # Üst Başlık
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 4)

        btn_back = QToolButton()
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(12, 12))
        btn_back.setFixedSize(22, 22)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_edit_title"))
        self.lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_edit_badge", "drawer_edit_notice", ModernIconFactory.icon_edit_content, self)
        main_layout.addWidget(self.notice_box)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DrawerContainer")
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(2, 4, 2, 4)
        v_items.setSpacing(3)

        self.items: List[ModernDrawerItemWidget] = []

        # Grup 1: MODIFY PAGE
        self.lbl_g1 = QLabel(LanguageManager.tr("drawer_group_modify_page"))
        self.lbl_g1.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_g1)

        self.specs_modify = [
            ("rotate", "drawer_edit_rotate", ModernIconFactory.icon_rotate("#ec4899"), "", True),
            ("insert", "drawer_edit_insert", ModernIconFactory.icon_insert("#ec4899"), "", True),
            ("delete", "drawer_edit_delete", ModernIconFactory.icon_trash("#ec4899"), "", True),
            ("extract", "drawer_edit_extract", ModernIconFactory.icon_extract("#ec4899"), "", True),
            ("organize", "tool_organize_pages", ModernIconFactory.icon_organize("#ec4899"), "", True),
        ]
        for cid, key, icon, badge, is_ready in self.specs_modify:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        # Grup 2: ADD CONTENT
        self.lbl_g2 = QLabel(LanguageManager.tr("drawer_group_add_content"))
        self.lbl_g2.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_g2)

        self.specs_add = [
            ("edit_text_images", "drawer_edit_text_images", ModernIconFactory.icon_edit_content("#ec4899"), "", True),
            ("text", "drawer_edit_text", ModernIconFactory.icon_text_tool("#ec4899"), "", True),
            ("image", "drawer_edit_image", ModernIconFactory.icon_image("#ec4899"), "", True),
            ("add_gif", "drawer_edit_gif", ModernIconFactory.icon_gif("#ec4899"), "", True),
            ("header_footer", "drawer_edit_header_footer", ModernIconFactory.icon_header_footer("#ec4899"), "", True),
            ("watermark", "drawer_edit_watermark", ModernIconFactory.icon_watermark("#ec4899"), "", True),
            ("link", "drawer_edit_link", ModernIconFactory.icon_link("#ec4899"), "", True),
            ("bates", "drawer_edit_bates", ModernIconFactory.icon_bates("#ec4899"), "", True),
            ("background", "drawer_edit_background", ModernIconFactory.icon_background("#ec4899"), "", True),
            ("attach", "drawer_edit_attach", ModernIconFactory.icon_attachment("#ec4899"), "", True),
        ]
        for cid, key, icon, badge, is_ready in self.specs_add:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def _on_item_clicked(self, cid: str):
        self.active_edit_id = cid
        self._update_item_active_states()
        self.editTriggered.emit(cid)

    def _update_item_active_states(self):
        for it in self.items:
            it.set_active(it.item_id == self.active_edit_id, self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_edit_title"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        self.lbl_g1.setText(LanguageManager.tr("drawer_group_modify_page"))
        self.lbl_g2.setText(LanguageManager.tr("drawer_group_add_content"))
        all_specs = self.specs_modify + self.specs_add
        for it, (_, key, _, _, _) in zip(self.items, all_specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)
        self.setStyleSheet(f"""
            ModernEditDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#DrawerContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 700;
                padding-top: 8px;
                padding-bottom: 3px;
                letter-spacing: 0.8px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        self._update_item_active_states()


class ModernReadDrawer(QFrame):
    """
    Sadece okuma ve renk modlarını barındıran modern sol çekmece.
    - Grup 1: SAYFA DÜZENİ (Tekli, İkili, Tam Ekran)
    - Grup 2: OKUMA RENK MODLARI (Açık Kağıt, Gece Modu, Sepya / Kitap Tonu)
    """
    readTriggered = pyqtSignal(str)
    closeRequested = pyqtSignal()
    backRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent.main_window if hasattr(parent, "main_window") else None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.setFixedWidth(248)

        self._current_layout_mode = "view_single"
        self._current_color_mode = "color_normal"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(10)

        # Üst Başlık ve Geri / Kapat
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 2)
        h_head.setSpacing(6)

        btn_back = QToolButton(self)
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(12, 12))
        btn_back.setFixedSize(22, 22)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        self.btn_back = btn_back
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_read_title"))
        self.lbl_head.setStyleSheet("font-size: 13px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton(self)
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_read_badge", "drawer_read_notice", ModernIconFactory.icon_reading_mode, self)
        main_layout.addWidget(self.notice_box)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DrawerContainer")
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(2, 4, 2, 4)
        v_items.setSpacing(3)

        self.items: List[ModernDrawerItemWidget] = []

        # Grup 1: SAYFA DÜZENİ
        self.lbl_g1 = QLabel(LanguageManager.tr("view_mode_group"))
        self.lbl_g1.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_g1)

        self.specs_layout = [
            ("view_single", "view_mode_single", ModernIconFactory.icon_view_single(), "", True),
            ("view_double", "view_mode_double", ModernIconFactory.icon_view_double(), "", True),
            ("view_fullscreen", "tb_item_fullscreen", ModernIconFactory.icon_fullscreen(), "", True),
        ]
        for cid, key, icon, badge, is_ready in self.specs_layout:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        # Grup 2: OKUMA RENK MODLARI
        self.lbl_g2 = QLabel(LanguageManager.tr("reading_color_modes"))
        self.lbl_g2.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_g2)

        self.specs_color = [
            ("color_normal", "reading_mode_normal", ModernIconFactory.icon_reading_mode("#fbbf24"), "", True),
            ("color_dark", "reading_mode_dark", ModernIconFactory.icon_reading_dark("#a855f7"), "", True),
            ("color_sepia", "reading_mode_sepia", ModernIconFactory.icon_reading_sepia("#f97316"), "", True),
        ]
        for cid, key, icon, badge, is_ready in self.specs_color:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def _on_item_clicked(self, cid: str):
        if cid in ("view_single", "view_double"):
            self._current_layout_mode = cid
        elif cid in ("color_normal", "color_dark", "color_sepia"):
            self._current_color_mode = cid
        self._update_item_active_states()
        self.readTriggered.emit(cid)

    def _update_item_active_states(self):
        for it in self.items:
            is_active = (it.item_id == self._current_layout_mode) or (it.item_id == self._current_color_mode)
            it.set_active(is_active, self.theme_name)

    def set_active_modes(self, layout_mode: Optional[str] = None, color_mode: Optional[str] = None):
        if layout_mode:
            self._current_layout_mode = layout_mode
        if color_mode:
            self._current_color_mode = color_mode
        self._update_item_active_states()

    def sync_from_document(self):
        """Açık dokümanın gerçek görünüm ve renk modunu çekmeceye yansıtır."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc:
            return
        layout_mode = getattr(tab_doc, 'page_layout', 'single')
        if layout_mode == 'single':
            self._current_layout_mode = 'view_single'
        elif layout_mode == 'double':
            self._current_layout_mode = 'view_double'

        color_mode = getattr(tab_doc, 'reading_color_mode', 'normal')
        if color_mode == 'normal':
            self._current_color_mode = 'color_normal'
        elif color_mode == 'dark':
            self._current_color_mode = 'color_dark'
        elif color_mode == 'sepia':
            self._current_color_mode = 'color_sepia'

        self._update_item_active_states()

    def load_accessibility(self):
        """Geriye dönük uyumluluk için güvenli çağrı metodu."""
        pass

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_read_title"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        self.lbl_g1.setText(LanguageManager.tr("view_mode_group"))
        self.lbl_g2.setText(LanguageManager.tr("reading_color_modes"))
        all_specs = self.specs_layout + self.specs_color
        for it, (_, key, _, _, _) in zip(self.items, all_specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)

        self.setStyleSheet(f"""
            ModernReadDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#DrawerContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 700;
                padding-top: 10px;
                padding-bottom: 4px;
                padding-left: 2px;
                letter-spacing: 0.8px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        if hasattr(self, 'btn_back'):
            self.btn_back.setIcon(ModernIconFactory.icon_nav_back(c['text']))
        self._update_item_active_states()


class ModernFillSignDrawer(QWidget):
    """
    Ekranın solundaki 'Fill & Sign' (Doldur ve İmzala / E-İmza) çekmecesi:
    - Geri butonu (<) ve Başlık 'Fill & Sign' + Kapatma (✕)
    - FILL (DOLDUR) başlığı
    - 8 Hızlı Araç:
        1. Add text (Metin Ekle) - Ready
        2. Checkmark (Onay İşareti) - Ready
        3. Cross (Çarpı İşareti) - Ready
        4. Dot (Nokta) - Ready
        5. Line (Çizgi) - Ready
        6. Date (Tarih) - Ready
        7. Signature (İmza) - Ready
        8. Initials (Paraf) - Ready
    """
    backRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    toolTriggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "gray"
        self.active_tool_id: Optional[str] = "add_text"
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(8)

        # Üst Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 4)

        btn_back = QToolButton()
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(12, 12))
        btn_back.setFixedSize(22, 22)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_fillsign_title"))
        self.lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_fillsign_badge", "drawer_fillsign_notice", ModernIconFactory.icon_signature, self)
        main_layout.addWidget(self.notice_box)

        # Kategori Başlığı: FILL
        self.lbl_cat = QLabel(LanguageManager.tr("drawer_fill_group"))
        self.lbl_cat.setObjectName("CategoryHeader")
        main_layout.addWidget(self.lbl_cat)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DrawerContainer")
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(2, 4, 2, 4)
        v_items.setSpacing(3)

        self.items: List[ModernDrawerItemWidget] = []
        self.specs = [
            ("add_text", "drawer_fillsign_add_text", lambda: ModernIconFactory.icon_text_tool("#c084fc")),
            ("checkmark", "drawer_fillsign_checkmark", lambda: ModernIconFactory.icon_check("#c084fc")),
            ("cross", "drawer_fillsign_cross", lambda: ModernIconFactory.icon_cross("#c084fc")),
            ("dot", "drawer_fillsign_dot", lambda: ModernIconFactory.icon_dot("#c084fc")),
            ("line", "drawer_fillsign_line", lambda: ModernIconFactory.icon_line("#c084fc")),
            ("date", "drawer_fillsign_date", lambda: ModernIconFactory.icon_date("#c084fc")),
            ("signature", "drawer_fillsign_signature", lambda: ModernIconFactory.icon_signature("#c084fc")),
            ("initials", "drawer_fillsign_initials", lambda: ModernIconFactory.icon_initials("#c084fc")),
        ]

        for cid, key, icon_func in self.specs:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon_func(), badge_text="", is_ready=True, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def _on_item_clicked(self, cid: str):
        self.active_tool_id = cid
        self._update_item_active_states()
        self.toolTriggered.emit(cid)

    def _update_item_active_states(self):
        for it in self.items:
            it.set_active(it.item_id == self.active_tool_id, self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_fillsign_title"))
        self.lbl_cat.setText(LanguageManager.tr("drawer_fill_group"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        for it, (_, key, _) in zip(self.items, self.specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)
        self.setStyleSheet(f"""
            ModernFillSignDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#DrawerContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 700;
                padding-top: 8px;
                padding-bottom: 3px;
                letter-spacing: 0.8px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        self._update_item_active_states()


class ModernPrepareFormDrawer(QWidget):
    """
    Ekranın solundaki 'Form Hazırla' (Prepare Form) çekmecesi:
    - Geri butonu (<), Başlık 'Form Hazırla', Kapatma butonu (✕)
    - FORM ALANI EKLE grubu:
        1. Metin Kutusu (Text Field)
        2. Onay Kutusu (Checkbox)
        3. Seçenek Düğmesi (Radio Button)
        4. Açılır Liste (ComboBox)
        5. İmza Alanı (Signature Field)
    - MEVCUT ALANLAR grubu:
        - Belgedeki form alanlarını gösteren liste
        - Seçili alanı sil butonu
    - FORM İŞLEMLERİ grubu:
        - Formu Temizle
        - Verileri Dışa Aktar (JSON)
        - Verileri İçe Aktar (JSON)
    """
    backRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    toolTriggered = pyqtSignal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "gray"
        self.active_form_tool_id: Optional[str] = "form_text"
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(8)

        # Üst Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(2, 0, 2, 4)

        btn_back = QToolButton()
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(12, 12))
        btn_back.setFixedSize(22, 22)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_prepare_form_title"))
        self.lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme ve Rehber Kartı (Modern Callout Card)
        self.notice_box = ModernNoticeCard("drawer_prepare_form_badge", "drawer_prepare_form_notice", ModernIconFactory.icon_prepare_form, self)
        main_layout.addWidget(self.notice_box)

        # Mod Değiştirme Butonu (Tasarım Modu <-> Önizleme & Doldur)
        self.btn_mode_toggle = QPushButton(LanguageManager.tr("form_mode_preview"))
        self.btn_mode_toggle.setCheckable(True)
        self.btn_mode_toggle.setChecked(False)
        self.btn_mode_toggle.setIcon(ModernIconFactory.icon_view_single())
        self.btn_mode_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_toggle.clicked.connect(self._on_mode_toggled)
        main_layout.addWidget(self.btn_mode_toggle)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DrawerContainer")
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(2, 4, 2, 4)
        v_items.setSpacing(3)

        # Grup 1: FORM ALANI EKLE
        self.lbl_add_group = QLabel(LanguageManager.tr("drawer_form_add_group"))
        self.lbl_add_group.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_add_group)

        self.items: List[ModernDrawerItemWidget] = []
        self.specs = [
            ("form_text", "form_field_text", lambda: ModernIconFactory.icon_text_tool("#a855f7")),
            ("form_checkbox", "form_field_checkbox", lambda: ModernIconFactory.icon_check("#a855f7")),
            ("form_radio", "form_field_radio", lambda: ModernIconFactory.icon_dot("#a855f7")),
            ("form_combobox", "form_field_combobox", lambda: ModernIconFactory.icon_menu_hamburger("#a855f7")),
            ("form_signature", "form_field_signature", lambda: ModernIconFactory.icon_signature("#a855f7")),
        ]

        for cid, key, icon_func in self.specs:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon_func(), badge_text="", is_ready=True, parent=container)
            it.clicked.connect(self._on_item_clicked)
            v_items.addWidget(it)
            self.items.append(it)

        # Grup 2: MEVCUT ALANLAR
        self.lbl_fields_group = QLabel(LanguageManager.tr("drawer_form_fields_group"))
        self.lbl_fields_group.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_fields_group)

        self.list_fields = QListWidget()
        self.list_fields.setFixedHeight(120)
        self.list_fields.itemClicked.connect(self._on_field_clicked)
        self.list_fields.itemDoubleClicked.connect(self._on_field_double_clicked)
        v_items.addWidget(self.list_fields)

        h_field_btns = QHBoxLayout()
        h_field_btns.setSpacing(4)
        self.btn_edit_field = QPushButton(LanguageManager.tr("form_action_edit_selected"))
        self.btn_edit_field.setIcon(ModernIconFactory.icon_settings())
        self.btn_edit_field.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_field.clicked.connect(lambda: self.toolTriggered.emit("form_edit_selected"))
        h_field_btns.addWidget(self.btn_edit_field)

        self.btn_del_field = QPushButton(LanguageManager.tr("form_action_delete_selected"))
        self.btn_del_field.setIcon(ModernIconFactory.icon_trash("#ef4444"))
        self.btn_del_field.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del_field.clicked.connect(lambda: self.toolTriggered.emit("form_delete_selected"))
        h_field_btns.addWidget(self.btn_del_field)
        v_items.addLayout(h_field_btns)

        # Grup 3: FORM İŞLEMLERİ
        self.lbl_actions_group = QLabel(LanguageManager.tr("drawer_form_actions_group"))
        self.lbl_actions_group.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_actions_group)

        self.action_specs = [
            ("form_clear", "form_action_clear", lambda: ModernIconFactory.icon_trash("#ef4444")),
            ("form_export", "form_action_export", lambda: ModernIconFactory.icon_export_pdf("#38bdf8")),
            ("form_import", "form_action_import", lambda: ModernIconFactory.icon_folder_open("#10b981")),
        ]
        self.action_items: List[ModernDrawerItemWidget] = []
        for cid, key, icon_func in self.action_specs:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon_func(), badge_text="", is_ready=True, parent=container)
            it.clicked.connect(self.toolTriggered.emit)
            v_items.addWidget(it)
            self.action_items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def _on_item_clicked(self, cid: str):
        self.active_form_tool_id = cid
        self._update_item_active_states()
        self.toolTriggered.emit(cid)

    def _update_item_active_states(self):
        for it in self.items:
            it.set_active(it.item_id == self.active_form_tool_id, self.theme_name)

    def _on_mode_toggled(self):
        is_preview = self.btn_mode_toggle.isChecked()
        self.btn_mode_toggle.setText(
            LanguageManager.tr("form_mode_design") if is_preview else LanguageManager.tr("form_mode_preview")
        )
        if self.main_window:
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc:
                if is_preview:
                    tab_doc.exit_form_design_mode()
                else:
                    tab_doc.enter_form_design_mode()

    def refresh_fields_list(self):
        self.list_fields.clear()
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc:
            return
        fields = tab_doc.get_all_form_fields() if hasattr(tab_doc, 'get_all_form_fields') else []
        if not fields:
            item = QListWidgetItem(LanguageManager.tr("form_no_fields"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_fields.addItem(item)
            return

        for f in fields:
            txt = f"[{f['type']}] {f['name']} (S.{f['page'] + 1})"
            item = QListWidgetItem(ModernIconFactory.icon_prepare_form(), txt)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.list_fields.addItem(item)

    def _on_field_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and self.main_window:
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc:
                p_idx = data.get('page', 0)
                tab_doc.go_to_page(p_idx)
                if hasattr(tab_doc, 'select_form_field_on_scene'):
                    tab_doc.select_form_field_on_scene(data.get('name', ''), p_idx)

    def _on_field_double_clicked(self, item):
        self.toolTriggered.emit("form_edit_selected")

    def select_field_in_list(self, field_name: str, page_idx: int):
        self.list_fields.blockSignals(True)
        for row in range(self.list_fields.count()):
            it = self.list_fields.item(row)
            data = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get('name') == field_name and data.get('page') == page_idx:
                self.list_fields.setCurrentRow(row)
                break
        self.list_fields.blockSignals(False)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_prepare_form_title"))
        if hasattr(self, 'notice_box'):
            self.notice_box.retranslate_ui()
        self.lbl_add_group.setText(LanguageManager.tr("drawer_form_add_group"))
        self.lbl_fields_group.setText(LanguageManager.tr("drawer_form_fields_group"))
        self.lbl_actions_group.setText(LanguageManager.tr("drawer_form_actions_group"))
        self.btn_edit_field.setText(LanguageManager.tr("form_action_edit_selected"))
        self.btn_del_field.setText(LanguageManager.tr("form_action_delete_selected"))
        is_preview = self.btn_mode_toggle.isChecked()
        self.btn_mode_toggle.setText(
            LanguageManager.tr("form_mode_design") if is_preview else LanguageManager.tr("form_mode_preview")
        )
        for it, (_, key, _) in zip(self.items, self.specs):
            it.set_title(LanguageManager.tr(key))
        for it, (_, key, _) in zip(self.action_items, self.action_specs):
            it.set_title(LanguageManager.tr(key))
        self.refresh_fields_list()

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'notice_box'):
            self.notice_box.apply_theme(theme_name)
        self.setStyleSheet(f"""
            ModernPrepareFormDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QWidget#DrawerContainer {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 2px 1px 2px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                min-height: 24px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 700;
                padding-top: 6px;
                padding-bottom: 2px;
                letter-spacing: 0.8px;
            }}
            QListWidget {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_hover']};
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        self._update_item_active_states()


class ModernLeftSidebar(QStackedWidget):
    """Sol panel yığını: 0=Tüm Araçlar, 1=Export Çekmecesi, 2=Edit Çekmecesi, 3=Read Çekmecesi, 4=Fill & Sign Çekmecesi, 5=Form Hazırla Çekmecesi."""
    toolTriggered = pyqtSignal(str)
    exportTriggered = pyqtSignal(str)
    editTriggered = pyqtSignal(str)
    readTriggered = pyqtSignal(str)
    fillSignTriggered = pyqtSignal(str)
    prepareFormTriggered = pyqtSignal(str)
    closeRequested = pyqtSignal()

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setFixedWidth(248)

        self.all_tools_panel = ModernAllToolsPanel(self)
        self.all_tools_panel.toolTriggered.connect(self._on_tool_triggered)
        self.all_tools_panel.closeRequested.connect(self.closeRequested.emit)
        self.addWidget(self.all_tools_panel)

        self.export_drawer = ModernExportDrawer(self)
        self.export_drawer.backRequested.connect(lambda: self.set_page("all_tools"))
        self.export_drawer.closeRequested.connect(self.closeRequested.emit)
        self.export_drawer.exportTriggered.connect(self.exportTriggered.emit)
        self.addWidget(self.export_drawer)

        self.edit_drawer = ModernEditDrawer(self)
        self.edit_drawer.backRequested.connect(lambda: self.set_page("all_tools"))
        self.edit_drawer.closeRequested.connect(self.closeRequested.emit)
        self.edit_drawer.editTriggered.connect(self.editTriggered.emit)
        self.addWidget(self.edit_drawer)

        self.read_drawer = ModernReadDrawer(self)
        self.read_drawer.backRequested.connect(lambda: self.set_page("all_tools"))
        self.read_drawer.closeRequested.connect(self.closeRequested.emit)
        self.read_drawer.readTriggered.connect(self.readTriggered.emit)
        self.addWidget(self.read_drawer)

        self.fill_sign_drawer = ModernFillSignDrawer(self)
        self.fill_sign_drawer.backRequested.connect(lambda: self.set_page("all_tools"))
        self.fill_sign_drawer.closeRequested.connect(self.closeRequested.emit)
        self.fill_sign_drawer.toolTriggered.connect(self.fillSignTriggered.emit)
        self.addWidget(self.fill_sign_drawer)

        self.prepare_form_drawer = ModernPrepareFormDrawer(self.main_window, self)
        self.prepare_form_drawer.backRequested.connect(self._on_prepare_form_back)
        self.prepare_form_drawer.closeRequested.connect(self._on_prepare_form_close)
        self.prepare_form_drawer.toolTriggered.connect(self.prepareFormTriggered.emit)
        self.addWidget(self.prepare_form_drawer)

    def _on_prepare_form_back(self):
        if self.main_window:
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc and getattr(tab_doc, 'is_form_design_mode', False):
                tab_doc.exit_form_design_mode()
        self.set_page("all_tools")

    def _on_prepare_form_close(self):
        if self.main_window:
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc and getattr(tab_doc, 'is_form_design_mode', False):
                tab_doc.exit_form_design_mode()
        self.closeRequested.emit()

    def _on_tool_triggered(self, tool_id: str):
        if tool_id == "export_pdf":
            self.set_page("export")
        elif tool_id == "edit_pdf":
            self.set_page("edit")
        elif tool_id in ("fill_sign", "esign"):
            self.set_page("esign")
        elif tool_id == "prepare_form":
            self.set_page("prepare_form")
        else:
            self.toolTriggered.emit(tool_id)

    def set_page(self, page_name: str):
        prev_idx = self.currentIndex()
        if page_name in ("all_tools", "tools"):
            self.setCurrentIndex(0)
        elif page_name in ("export", "convert"):
            self.setCurrentIndex(1)
        elif page_name in ("edit", "modify"):
            self.setCurrentIndex(2)
        elif page_name in ("read", "reading"):
            self.setCurrentIndex(3)
            self.read_drawer.sync_from_document()
        elif page_name in ("esign", "fill_sign", "sign"):
            self.setCurrentIndex(4)
        elif page_name in ("prepare_form", "form"):
            self.setCurrentIndex(5)
            if self.main_window:
                tab_doc = self.main_window.get_current_tab_doc()
                if tab_doc:
                    tab_doc.enter_form_design_mode()
            self.prepare_form_drawer.refresh_fields_list()

        if prev_idx == 5 and self.currentIndex() != 5:
            if self.main_window:
                tab_doc = self.main_window.get_current_tab_doc()
                if tab_doc and getattr(tab_doc, 'is_form_design_mode', False):
                    tab_doc.exit_form_design_mode()

    def set_active_tool(self, tool_id: Optional[str]):
        self.all_tools_panel.set_active_tool(tool_id)

    def apply_theme(self, theme_name: str):
        self.all_tools_panel.apply_theme(theme_name)
        self.export_drawer.apply_theme(theme_name)
        self.edit_drawer.apply_theme(theme_name)
        self.read_drawer.apply_theme(theme_name)
        self.fill_sign_drawer.apply_theme(theme_name)
        self.prepare_form_drawer.apply_theme(theme_name)

    def retranslate_ui(self):
        self.all_tools_panel.retranslate_ui()
        self.export_drawer.retranslate_ui()
        self.edit_drawer.retranslate_ui()
        self.read_drawer.retranslate_ui()
        self.fill_sign_drawer.retranslate_ui()
        self.prepare_form_drawer.retranslate_ui()


class FloatingQuickToolsCapsule(QFrame):
    """
    Belge okuyucu alanının sol kenarında yüzen ve sürüklenebilir hızlı araç kapsülü:
    - Seçim (↖)
    - Vurgulayıcı (🖊)
    - Not Ekle (💬)
    - Metin Düzenle (T)
    - Çizim Kalemi (✏)
    - Silgi (⌫)
    """
    toolSelected = pyqtSignal(str)
    toolSelectedWithWidget = pyqtSignal(str, object)
    pinToTopRequested = pyqtSignal()
    pinToLeftRequested = pyqtSignal()
    pinToRightRequested = pyqtSignal()

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "gray"
        self.active_tool = "select"
        settings = QSettings("AuraPDF", "PDFViewer")
        self.user_moved = settings.contains("capsule_float_x") and settings.contains("capsule_float_y")
        self._drag_active = False
        self._drag_start_pos = QPoint()
        self._is_potential_drag = False
        self.setFixedSize(52, 436)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        self.layout_capsule = QVBoxLayout(self)
        self.layout_capsule.setContentsMargins(5, 5, 5, 8)
        self.layout_capsule.setSpacing(5)

        # Üst Sürükleme ve Sabitleme Tutamacı
        self.grip_handle = QFrame(self)
        self.grip_handle.setFixedHeight(20)
        l_grip = QHBoxLayout(self.grip_handle)
        l_grip.setContentsMargins(2, 2, 2, 2)
        l_grip.setSpacing(2)
        l_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grip_bar = QFrame(self.grip_handle)
        self.grip_bar.setFixedSize(18, 4)
        self.grip_bar.setCursor(Qt.CursorShape.SizeAllCursor)
        self.grip_bar.setToolTip(LanguageManager.tr("capsule_dock_hint"))
        self.grip_bar.setStyleSheet("background-color: rgba(150, 150, 150, 0.45); border-radius: 2px;")
        l_grip.addWidget(self.grip_bar)

        self.btn_pin = QToolButton(self.grip_handle)
        self.btn_pin.setIcon(ModernIconFactory.icon_pin())
        self.btn_pin.setIconSize(QSize(13, 13))
        self.btn_pin.setFixedSize(18, 18)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip(LanguageManager.tr("capsule_pin_top"))
        self.btn_pin.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.btn_pin.clicked.connect(self._on_pin_clicked)
        l_grip.addWidget(self.btn_pin)

        self.layout_capsule.addWidget(self.grip_handle)

        self.buttons: Dict[str, QToolButton] = {}
        self.cursor_mode = "select"
        self.selection_shape_mode = "rect"

        # Tüm araçların fabrika tanımları
        self.tool_specs_factory = {
            "select": ("quick_tool_select", lambda: ModernIconFactory.icon_cursor()),
            "selection": ("quick_tool_draw_select", lambda: ModernIconFactory.icon_select_rect("#38bdf8")),
            "pen": ("quick_tool_pen", lambda: ModernIconFactory.icon_pen("#0284c7")),
            "highlighter": ("quick_tool_highlighter", lambda: ModernIconFactory.icon_highlighter("#eab308")),
            "eraser": ("quick_tool_eraser", lambda: ModernIconFactory.icon_eraser("#ef4444")),
            "text": ("quick_tool_text", lambda: ModernIconFactory.icon_text_tool("#ec4899")),
            "insert": ("insert_btn_tip", lambda: ModernIconFactory.icon_insert("#10b981")),
            "comment": ("quick_tool_comment", lambda: ModernIconFactory.icon_comments("#f97316")),
            "pointer": ("quick_tool_pointer", lambda: ModernIconFactory.icon_pointer("#ef4444")),
        }
        self.default_order = ["select", "selection", "pen", "highlighter", "eraser", "text", "insert", "comment", "pointer"]

        # Kaydedilmiş araç sıralamasını yükle (ve sürüm kontrolüyle gerekirse yeni varsayılana taşı)
        settings = QSettings("AuraPDF", "PDFViewer")
        tb_version = settings.value("floating_tools_order_version", 0, type=int)
        raw_order = settings.value("floating_tools_order", None)
        loaded_order = []
        if raw_order and tb_version >= 2:
            try:
                if isinstance(raw_order, str):
                    loaded_order = json.loads(raw_order)
                elif isinstance(raw_order, list):
                    loaded_order = list(raw_order)
            except Exception:
                loaded_order = []

        valid_order = [x for x in loaded_order if x in self.tool_specs_factory]
        if not valid_order or tb_version < 2:
            valid_order = list(self.default_order)
        else:
            for k in self.default_order:
                if k not in valid_order:
                    valid_order.append(k)
        self.tool_order = valid_order

        # Butonları oluştur (Büyük, net ve modern ikonlar - 24x24 ikon, 38x38 buton)
        for tid in self.tool_order:
            key, icon_func = self.tool_specs_factory[tid]
            btn = QToolButton(self)
            btn.setIcon(icon_func())
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(38, 38)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(LanguageManager.tr(key))
            btn.clicked.connect(lambda checked, t=tid: self._on_btn_clicked(t))
            btn.installEventFilter(self)
            self.layout_capsule.addWidget(btn)
            self.buttons[tid] = btn

        self.installEventFilter(self)
        self.grip_handle.installEventFilter(self)
        self.grip_bar.installEventFilter(self)

        if "select" in self.buttons:
            self.buttons["select"].setChecked(True)
        self.apply_theme(self.theme_name)

    def set_tools_order(self, order: list):
        """Ayarlardan gelen yeni sıralamaya göre butonları yeniden düzenler."""
        valid_order = [x for x in order if x in self.tool_specs_factory]
        for k in self.default_order:
            if k not in valid_order:
                valid_order.append(k)
        self.tool_order = valid_order

        # Layout'taki butonları çıkarıp yeni sırayla ekle
        for tid, btn in self.buttons.items():
            self.layout_capsule.removeWidget(btn)

        for tid in self.tool_order:
            btn = self.buttons.get(tid)
            if btn:
                self.layout_capsule.addWidget(btn)

        self.update()

    def update_cursor_mode(self, mode: str):
        """İmleç/Gezinme modu değiştiğinde hareketli toolbardaki butonu günceller."""
        self.cursor_mode = mode
        btn = self.buttons.get("select")
        if not btn:
            return
        if mode == 'pan':
            btn.setIcon(ModernIconFactory.icon_select_pan())
            btn.setToolTip(LanguageManager.tr("tb_item_cursor"))
        else:
            btn.setIcon(ModernIconFactory.icon_cursor())
            btn.setToolTip(LanguageManager.tr("quick_tool_select"))

    def update_selection_mode(self, mode: str):
        """Çizim seçim modu değiştiğinde hareketli toolbardaki butonu günceller."""
        self.selection_shape_mode = mode
        btn = self.buttons.get("selection")
        if not btn:
            return
        if mode == 'lasso':
            btn.setIcon(ModernIconFactory.icon_select_lasso("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("sel_lasso").strip())
        elif mode == 'move':
            btn.setIcon(ModernIconFactory.icon_select_move("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("sel_move").strip() if LanguageManager.tr("sel_move") != "sel_move" else "Seçimi Taşı")
        elif mode == 'ruler':
            btn.setIcon(ModernIconFactory.icon_ruler("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("tb_item_ruler"))
        else:
            btn.setIcon(ModernIconFactory.icon_select_rect("#38bdf8"))
            btn.setToolTip(LanguageManager.tr("quick_tool_draw_select"))

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._button_press_pos = event.globalPosition().toPoint()
            self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
            self._is_potential_drag = True
        elif event.type() == QEvent.Type.MouseMove and getattr(self, '_is_potential_drag', False):
            delta = event.globalPosition().toPoint() - getattr(self, '_button_press_pos', event.globalPosition().toPoint())
            if delta.manhattanLength() > 8:
                self._drag_active = True
                self._do_drag_move(event.globalPosition().toPoint())
                return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if getattr(self, '_drag_active', False):
                self._drag_active = False
                self._is_potential_drag = False
                self._check_dock_on_release()
                return True
            self._is_potential_drag = False
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_drag_active', False) and (event.buttons() & Qt.MouseButton.LeftButton):
            self._do_drag_move(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_dragging = getattr(self, '_drag_active', False)
        self._drag_active = False
        self._is_potential_drag = False
        if was_dragging:
            self._check_dock_on_release()
        super().mouseReleaseEvent(event)

    def _do_drag_move(self, global_pos: QPoint):
        new_pos = global_pos - self._drag_start_pos
        if self.parent():
            p_rect = self.parent().rect()
            max_x = max(0, p_rect.width() - self.width())
            max_y = max(0, p_rect.height() - self.height())
            clamped_x = max(0, min(new_pos.x(), max_x))
            clamped_y = max(0, min(new_pos.y(), max_y))
            self.move(clamped_x, clamped_y)
            self.user_moved = True
        else:
            self.move(new_pos)
            self.user_moved = True

    def _check_dock_on_release(self):
        """Sürükleme bırakıldığında konuma göre üst, sol veya sağ çubuğa otomatik sabitleme."""
        p_width = self.parent().width() if self.parent() else 1000

        # Sadece ekranın en dış kenarına çok yakın bırakıldıysa sabitle
        if self.y() <= 12:
            self.pinToTopRequested.emit()
            return
        if self.x() <= 12:
            self.pinToLeftRequested.emit()
            return
        if (self.x() + self.width()) >= (p_width - 12):
            self.pinToRightRequested.emit()
            return

        # Belge üzerinde serbestçe bırakıldıysa -> serbest hareketli modda kal
        if self.main_window:
            self.main_window.capsule_docked_to_left = False
            self.main_window.capsule_docked_to_right = False
            self.main_window.capsule_docked_to_top = False
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("capsule_dock_position", "float")
            settings.setValue("capsule_docked_to_top", False)
            settings.setValue("capsule_docked_to_left", False)
            settings.setValue("capsule_docked_to_right", False)
            settings.setValue("capsule_float_x", self.x())
            settings.setValue("capsule_float_y", self.y())
            p_rect = self.parent().rect() if self.parent() else None
            if p_rect and p_rect.width() > 0 and p_rect.height() > 0:
                settings.setValue("capsule_float_rx", float(self.x()) / float(p_rect.width()))
                settings.setValue("capsule_float_ry", float(self.y()) / float(p_rect.height()))
        self.user_moved = True

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e24;
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #388bfd;
            }
        """)
        act_reset = menu.addAction(ModernIconFactory.icon_refresh(), LanguageManager.tr("hud_reset_pos"))
        act_reset.triggered.connect(self.reset_to_default_pos)
        menu.exec(event.globalPos())

    def reset_to_default_pos(self):
        self.user_moved = False
        if self.main_window:
            self.main_window.capsule_docked_to_left = True
            self.main_window.capsule_docked_to_right = False
            self.main_window.capsule_docked_to_top = False
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("capsule_dock_position", "left")
            settings.remove("capsule_float_x")
            settings.remove("capsule_float_y")
            self.main_window.update_floating_capsule_pos()

    def _on_pin_clicked(self):
        """Sabitleme butonuna tıklandığında konuma veya duruma göre sol, sağ veya üst çubuğa sabitler."""
        left_threshold = 160
        if self.main_window and hasattr(self.main_window, 'central_stack'):
            try:
                cs_x = self.main_window.central_stack.mapTo(self.main_window, QPoint(0, 0)).x()
                left_threshold = max(140, cs_x + 80)
            except Exception:
                pass

        p_width = self.parent().width() if self.parent() else 1000
        right_threshold = p_width - 160
        if self.main_window and hasattr(self.main_window, 'central_stack'):
            try:
                cs = self.main_window.central_stack
                cs_right = cs.mapTo(self.main_window, QPoint(cs.width(), 0)).x()
                right_threshold = min(p_width - 100, cs_right - 80)
            except Exception:
                pass

        if self.x() <= left_threshold:
            self.pinToLeftRequested.emit()
        elif (self.x() + self.width()) >= right_threshold:
            self.pinToRightRequested.emit()
        else:
            self.pinToTopRequested.emit()

    def retranslate_ui(self):
        for tid in self.tool_order:
            if tid in self.buttons and tid in self.tool_specs_factory:
                key, _ = self.tool_specs_factory[tid]
                self.buttons[tid].setToolTip(LanguageManager.tr(key))
        if getattr(self, 'cursor_mode', 'select') == 'pan':
            self.update_cursor_mode('pan')
        if getattr(self, 'selection_shape_mode', 'rect') != 'rect':
            self.update_selection_mode(self.selection_shape_mode)
        if hasattr(self, 'btn_pin'):
            self.btn_pin.setToolTip(LanguageManager.tr("capsule_pin_top"))
        if hasattr(self, 'grip_bar'):
            self.grip_bar.setToolTip(LanguageManager.tr("capsule_dock_hint"))

    def _on_btn_clicked(self, tool_id: str):
        self.set_active_tool(tool_id)
        self.toolSelected.emit(tool_id)
        btn = self.buttons.get(tool_id)
        self.toolSelectedWithWidget.emit(tool_id, btn)

    def set_active_tool(self, tool_id: str):
        self.active_tool = tool_id
        for tid, btn in self.buttons.items():
            btn.setChecked(tid == tool_id)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'btn_pin'):
            self.btn_pin.setIcon(ModernIconFactory.icon_pin(c['text_muted']))
        if "select" in self.buttons and getattr(self, 'cursor_mode', 'select') == 'select':
            self.buttons["select"].setIcon(ModernIconFactory.icon_cursor(c['text']))
        self.setStyleSheet(f"""
            FloatingQuickToolsCapsule {{
                background-color: {c['surface']};
                border: 1.5px solid {c['border']};
                border-radius: 25px;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 19px;
                color: {c['text']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
            }}
            QToolButton:checked {{
                background-color: {c['accent_light']};
                border-color: {c['accent']};
            }}
        """)


class HomeRecommendedCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, tool_id: str, title: str, subtitle: str, icon: QIcon, theme_name: str = "light", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tool_id = tool_id
        self.theme_name = theme_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 108)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(4)

        # İkon + Başlık
        h_top = QHBoxLayout()
        h_top.setSpacing(8)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon.pixmap(18, 18))
        h_top.addWidget(lbl_icon)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("CardTitle")
        h_top.addWidget(self.lbl_title)
        h_top.addStretch(1)
        layout.addLayout(h_top)

        # Alt Başlık
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setObjectName("CardSub")
        layout.addWidget(self.lbl_sub, stretch=1)

        # Şimdi Kullan Bağlantısı
        self.lbl_use_now = QLabel(LanguageManager.tr("home_use_now"))
        self.lbl_use_now.setObjectName("CardLink")
        layout.addWidget(self.lbl_use_now)

        self.apply_theme(theme_name)

    def retranslate(self, title: str, subtitle: str):
        self.lbl_title.setText(title)
        self.lbl_sub.setText(subtitle)
        self.lbl_use_now.setText(LanguageManager.tr("home_use_now"))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool_id)

    def apply_theme(self, theme_name: str):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            HomeRecommendedCard {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 10px;
            }}
            HomeRecommendedCard:hover {{
                border-color: {c['accent']};
                background-color: {c['surface_hover']};
            }}
            #CardTitle {{
                color: {c['text']};
                font-size: 13px;
                font-weight: 600;
            }}
            #CardSub {{
                color: {c['text_muted']};
                font-size: 11px;
                line-height: 1.2;
            }}
            #CardLink {{
                color: {c['accent']};
                font-size: 11px;
                font-weight: 600;
            }}
        """)


class HomeOpenFileCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, theme_name: str = "light", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = theme_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(140, 108)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_folder_open("#64748b").pixmap(30, 30))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        self.lbl_text = QLabel(LanguageManager.tr("home_open_file"))
        self.lbl_text.setObjectName("OpenCardText")
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_text)

        self.apply_theme(theme_name)

    def retranslate_ui(self):
        self.lbl_text.setText(LanguageManager.tr("home_open_file"))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def apply_theme(self, theme_name: str):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            HomeOpenFileCard {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['card_border']};
                border-radius: 10px;
            }}
            HomeOpenFileCard:hover {{
                border-color: {c['accent']};
                background-color: {c['accent_light']};
            }}
            #OpenCardText {{
                color: {c['text']};
                font-size: 13px;
                font-weight: 600;
            }}
        """)


class RecentFileRowWidget(QFrame):
    clicked = pyqtSignal(str)
    favoriteToggled = pyqtSignal(str)
    removeRequested = pyqtSignal(str)

    def __init__(self, file_path: str, page_count: int, size_str: str, is_favorite: bool = False, theme_name: str = "light", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.file_path = file_path
        self.is_favorite = is_favorite
        self.theme_name = theme_name
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(54)
        self.setToolTip(file_path)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_pdf("#ef4444").pixmap(22, 22))
        layout.addWidget(lbl_icon)

        v_info = QVBoxLayout()
        v_info.setContentsMargins(0, 0, 0, 0)
        v_info.setSpacing(2)

        basename = os.path.basename(file_path)
        self.lbl_title = QLabel(basename)
        self.lbl_title.setObjectName("RecentTitle")

        self.lbl_path = QLabel(file_path)
        self.lbl_path.setObjectName("RecentPath")

        v_info.addWidget(self.lbl_title)
        v_info.addWidget(self.lbl_path)
        layout.addLayout(v_info, stretch=1)

        template = LanguageManager.tr("home_pages_kb")
        info_str = template.format(pages=page_count, size=size_str)
        self.lbl_meta = QLabel(info_str)
        self.lbl_meta.setObjectName("RecentMeta")
        layout.addWidget(self.lbl_meta)

        self.btn_fav = QToolButton(self)
        self.btn_fav.setObjectName("BtnRowFavorite")
        self.btn_fav.setFixedSize(30, 30)
        self.btn_fav.setIconSize(QSize(16, 16))
        self.btn_fav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fav.setIcon(ModernIconFactory.icon_star(filled=self.is_favorite))
        self.btn_fav.setToolTip(LanguageManager.tr("favorite_remove") if self.is_favorite else LanguageManager.tr("favorite_add"))
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        layout.addWidget(self.btn_fav)

        self.apply_theme(theme_name)
        self._update_elided_path()

    def _on_fav_clicked(self):
        self.is_favorite = not self.is_favorite
        self.btn_fav.setIcon(ModernIconFactory.icon_star(filled=self.is_favorite))
        self.btn_fav.setToolTip(LanguageManager.tr("favorite_remove") if self.is_favorite else LanguageManager.tr("favorite_add"))
        self.favoriteToggled.emit(self.file_path)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        apply_dialog_theme(menu, self)
        act_open = menu.addAction(ModernIconFactory.icon_pdf("#ef4444"), LanguageManager.tr("home_open_file"))
        fav_icon = ModernIconFactory.icon_star(filled=not self.is_favorite)
        fav_text = LanguageManager.tr("favorite_remove") if self.is_favorite else LanguageManager.tr("favorite_add")
        act_fav = menu.addAction(fav_icon, fav_text)
        folder_text = LanguageManager.tr("sidebar_open_containing_folder") if LanguageManager.tr("sidebar_open_containing_folder") != "sidebar_open_containing_folder" else "Dosya Konumunu Aç"
        act_folder = menu.addAction(ModernIconFactory.icon_search(), folder_text)
        act_remove = menu.addAction(ModernIconFactory.icon_trash(), LanguageManager.tr("remove_from_list"))

        action = menu.exec(event.globalPos())
        if action == act_open:
            self.clicked.emit(self.file_path)
        elif action == act_fav:
            self._on_fav_clicked()
        elif action == act_folder:
            if os.path.exists(self.file_path):
                import subprocess
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.file_path)}"')
        elif action == act_remove:
            self.removeRequested.emit(self.file_path)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_elided_path()

    def _update_elided_path(self):
        if hasattr(self, 'lbl_path') and self.file_path:
            fm = QFontMetrics(self.lbl_path.font())
            w = max(120, self.lbl_path.width())
            self.lbl_path.setText(fm.elidedText(self.file_path, Qt.TextElideMode.ElideMiddle, w))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)

    def apply_theme(self, theme_name: str):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            RecentFileRowWidget {{
                background-color: transparent;
                border-radius: 8px;
                border: 1px solid transparent;
            }}
            RecentFileRowWidget:hover {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['border']};
            }}
            #RecentTitle {{
                color: {c['text']};
                font-size: 13px;
                font-weight: 600;
            }}
            #RecentPath {{
                color: {c['text_muted']};
                font-size: 11px;
            }}
            #RecentMeta {{
                color: {c['text_muted']};
                font-size: 12px;
                font-weight: 500;
            }}
            #BtnRowFavorite {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            #BtnRowFavorite:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
            }}
        """)


class HomeDashboardWorkspace(QWidget):
    """
    Ana Karşılama ve Son Açılanlar Çalışma Alanı (Screenshot 1 ve 4):
    - Başlık: Welcome to AuraPDF + Alt başlık
    - AuraPDF Topluluk Kartı (Discord, Web, GitHub, Dokümantasyon)
    - Önerilen Araçlar (Sayfaları Organize Et, Yorum Ekle, Form Hazırla, Düzenle, Koru + Dosya Aç)
    - Son Açılan Belgeler Listesi (Kırmızı PDF ikonlu, sayfa ve boyut bilgili)
    """
    openFileRequested = pyqtSignal()
    fileSelected = pyqtSignal(str)
    toolRequested = pyqtSignal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Kaydırma Alanı
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content_container = QWidget()
        self.content_container.setObjectName("HomeContentContainer")
        v_content = QVBoxLayout(self.content_container)
        v_content.setContentsMargins(36, 32, 36, 36)
        v_content.setSpacing(24)
        v_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.inner_wrapper = QWidget()
        self.inner_wrapper.setObjectName("HomeInnerWrapper")
        self.inner_wrapper.setMaximumWidth(1060)
        v_inner = QVBoxLayout(self.inner_wrapper)
        v_inner.setContentsMargins(0, 0, 0, 0)
        v_inner.setSpacing(26)

        # 1. Başlık ve Açıklama
        v_title = QVBoxLayout()
        v_title.setSpacing(6)
        self.lbl_welcome = QLabel(LanguageManager.tr("home_welcome_title"))
        self.lbl_welcome.setObjectName("WelcomeTitle")
        self.lbl_sub = QLabel(LanguageManager.tr("home_welcome_subtitle"))
        self.lbl_sub.setObjectName("WelcomeSub")
        v_title.addWidget(self.lbl_welcome)
        v_title.addWidget(self.lbl_sub)
        v_inner.addLayout(v_title)

        # 2. Önerilen Araçlar (Recommended tools)
        v_rec = QVBoxLayout()
        v_rec.setSpacing(14)
        self.lbl_rec_title = QLabel(LanguageManager.tr("home_recommended_tools"))
        self.lbl_rec_title.setObjectName("SectionTitle")
        v_rec.addWidget(self.lbl_rec_title)

        h_cards = QHBoxLayout()
        h_cards.setSpacing(12)

        self.rec_tool_specs = [
            ("organize_pages", "tool_organize_pages", "tool_sub_organize", ModernIconFactory.icon_organize("#10b981")),
            ("add_comments", "tool_add_comments", "tool_sub_comments", ModernIconFactory.icon_comments("#f97316")),
            ("prepare_form", "tool_prepare_form", "tool_sub_prepare_form", ModernIconFactory.icon_prepare_form("#9333ea")),
            ("edit_pdf", "tool_edit_pdf", "tool_sub_edit", ModernIconFactory.icon_edit_content("#ec4899")),
            ("protect_pdf", "tool_protect_pdf", "tool_sub_protect", ModernIconFactory.icon_lock("#0284c7")),
        ]

        self.recommended_cards = []
        for tid, title_key, sub_key, icon in self.rec_tool_specs:
            card = HomeRecommendedCard(
                tid,
                LanguageManager.tr(title_key),
                LanguageManager.tr(sub_key),
                icon,
                theme_name=self.theme_name,
                parent=self.inner_wrapper
            )
            card.clicked.connect(self.toolRequested.emit)
            h_cards.addWidget(card)
            self.recommended_cards.append(card)

        # Open file Kartı
        self.open_card = HomeOpenFileCard(theme_name=self.theme_name, parent=self.inner_wrapper)
        self.open_card.clicked.connect(self.openFileRequested.emit)
        h_cards.addWidget(self.open_card)
        h_cards.addStretch(1)

        v_rec.addLayout(h_cards)
        v_inner.addLayout(v_rec)

        # 3. Son Açılanlar ve Favoriler Bölümü
        v_recent = QVBoxLayout()
        v_recent.setSpacing(14)

        self.current_tab_mode = "recent"  # "recent" | "favorites"

        h_recent_header = QHBoxLayout()
        h_recent_header.setContentsMargins(0, 0, 0, 0)
        h_recent_header.setSpacing(10)

        # Sekme Butonları (Segmented Selector)
        self.btn_tab_recent = QPushButton(LanguageManager.tr("home_recent_title"))
        self.btn_tab_recent.setObjectName("BtnTabRecent")
        self.btn_tab_recent.setCheckable(True)
        self.btn_tab_recent.setChecked(True)
        self.btn_tab_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_recent.clicked.connect(lambda: self.set_tab_mode("recent"))
        h_recent_header.addWidget(self.btn_tab_recent)

        self.btn_tab_favorites = QPushButton()
        self.btn_tab_favorites.setObjectName("BtnTabFavorites")
        self.btn_tab_favorites.setIcon(ModernIconFactory.icon_star(filled=True, color="#f59e0b"))
        self.btn_tab_favorites.setIconSize(QSize(14, 14))
        self.btn_tab_favorites.setText(" " + LanguageManager.tr("home_favorites_title"))
        self.btn_tab_favorites.setCheckable(True)
        self.btn_tab_favorites.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_favorites.clicked.connect(lambda: self.set_tab_mode("favorites"))
        h_recent_header.addWidget(self.btn_tab_favorites)

        h_recent_header.addStretch(1)

        # Favorilere Ekle Butonu
        self.btn_add_favorite = QPushButton()
        self.btn_add_favorite.setObjectName("BtnAddFavorite")
        self.btn_add_favorite.setIcon(ModernIconFactory.icon_plus())
        self.btn_add_favorite.setIconSize(QSize(12, 12))
        self.btn_add_favorite.setText(" " + LanguageManager.tr("home_add_favorite"))
        self.btn_add_favorite.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_favorite.clicked.connect(self._on_add_favorite_clicked)
        self.btn_add_favorite.hide()
        h_recent_header.addWidget(self.btn_add_favorite)

        # Temizle Butonu (Son açılanlar veya Favoriler için)
        self.btn_clear_recent = QPushButton()
        self.btn_clear_recent.setObjectName("BtnClearRecent")
        self.btn_clear_recent.setIcon(ModernIconFactory.icon_trash())
        self.btn_clear_recent.setIconSize(QSize(13, 13))
        self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_recent_files"))
        self.btn_clear_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_recent.clicked.connect(self._on_clear_clicked)
        h_recent_header.addWidget(self.btn_clear_recent)

        v_recent.addLayout(h_recent_header)

        self.recent_list_container = QWidget()
        self.recent_list_container.setObjectName("RecentListContainer")
        self.v_recent_items = QVBoxLayout(self.recent_list_container)
        self.v_recent_items.setContentsMargins(0, 0, 0, 0)
        self.v_recent_items.setSpacing(4)

        v_recent.addWidget(self.recent_list_container)
        v_inner.addLayout(v_recent)

        v_content.addWidget(self.inner_wrapper)
        scroll.setWidget(self.content_container)
        main_layout.addWidget(scroll)

        self.apply_theme(self.theme_name)
        self.load_recent_files()

    def set_tab_mode(self, mode: str):
        self.current_tab_mode = mode
        self.btn_tab_recent.setChecked(mode == "recent")
        self.btn_tab_favorites.setChecked(mode == "favorites")
        if mode == "recent":
            self.btn_add_favorite.hide()
            self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_recent_files"))
        else:
            self.btn_add_favorite.show()
            self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_favorite_files"))
        self.load_recent_files()

    def load_recent_files(self):
        """Son açılan veya favori dosyaları seçili sekmeye göre yükler ve listeler."""
        while self.v_recent_items.count() > 0:
            item = self.v_recent_items.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()

        if self.current_tab_mode == "favorites":
            files = []
            if self.main_window and hasattr(self.main_window, 'get_favorite_files'):
                files = self.main_window.get_favorite_files()
            empty_title = LanguageManager.tr("home_no_favorites")
            empty_hint = LanguageManager.tr("home_no_favorites_hint")
        else:
            files = []
            if self.main_window and hasattr(self.main_window, 'get_recent_files'):
                files = self.main_window.get_recent_files()
            empty_title = LanguageManager.tr("home_no_recent")
            empty_hint = ""

        if not files:
            self.btn_clear_recent.hide()
            empty_widget = QWidget(self.recent_list_container)
            v_empty = QVBoxLayout(empty_widget)
            v_empty.setContentsMargins(10, 20, 10, 20)
            v_empty.setSpacing(6)

            lbl_empty = QLabel(empty_title)
            lbl_empty.setObjectName("RecentEmpty")
            lbl_empty.setStyleSheet("font-size: 13px; font-weight: 600;")
            v_empty.addWidget(lbl_empty)

            if empty_hint:
                lbl_hint = QLabel(empty_hint)
                lbl_hint.setObjectName("RecentEmptyHint")
                lbl_hint.setStyleSheet("font-size: 12px; opacity: 0.8;")
                v_empty.addWidget(lbl_hint)

            self.v_recent_items.addWidget(empty_widget)
            self.recent_list_container.setMinimumHeight(80)
            return

        self.btn_clear_recent.show()

        row_count = 0
        for path in files:
            if not os.path.exists(path):
                continue
            try:
                sz = os.path.getsize(path)
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024 * 1024 else f"{sz / (1024 * 1024):.1f} MB"
            except Exception:
                sz_str = "0 KB"
            try:
                d = fitz.open(path)
                pages = len(d)
                d.close()
            except Exception:
                pages = 1

            is_fav = False
            if self.main_window and hasattr(self.main_window, 'is_favorite_file'):
                is_fav = self.main_window.is_favorite_file(path)

            row = RecentFileRowWidget(path, pages, sz_str, is_favorite=is_fav, theme_name=self.theme_name, parent=self.recent_list_container)
            row.clicked.connect(self.fileSelected.emit)
            row.favoriteToggled.connect(self._on_row_favorite_toggled)
            row.removeRequested.connect(self._on_row_remove_requested)
            self.v_recent_items.addWidget(row)
            row_count += 1

        if row_count > 0:
            total_h = row_count * 54 + max(0, row_count - 1) * 4
            self.recent_list_container.setMinimumHeight(total_h)
        else:
            self.recent_list_container.setMinimumHeight(80)

        self.recent_list_container.updateGeometry()
        if self.inner_wrapper.layout():
            self.inner_wrapper.layout().invalidate()
        self.inner_wrapper.updateGeometry()
        if self.content_container.layout():
            self.content_container.layout().invalidate()
        self.content_container.updateGeometry()

    def _on_row_favorite_toggled(self, file_path: str):
        if self.main_window and hasattr(self.main_window, 'toggle_favorite_file'):
            self.main_window.toggle_favorite_file(file_path)
            if self.current_tab_mode == "favorites":
                self.load_recent_files()

    def _on_row_remove_requested(self, file_path: str):
        if self.current_tab_mode == "favorites":
            if self.main_window and hasattr(self.main_window, 'remove_from_favorite_files'):
                self.main_window.remove_from_favorite_files(file_path)
        else:
            if self.main_window and hasattr(self.main_window, 'get_recent_files'):
                current = self.main_window.get_recent_files()
                if file_path in current:
                    current.remove(file_path)
                    QSettings("AuraPDF", "History").setValue("recent_files", json.dumps(current))
                    if hasattr(self.main_window, 'update_recent_files_menu'):
                        self.main_window.update_recent_files_menu()
        self.load_recent_files()

    def _on_add_favorite_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            LanguageManager.tr("home_add_favorite"),
            "",
            "PDF Files (*.pdf)"
        )
        if file_path:
            if self.main_window and hasattr(self.main_window, 'add_to_favorite_files'):
                self.main_window.add_to_favorite_files(file_path)
            self.load_recent_files()

    def _on_clear_clicked(self):
        if self.current_tab_mode == "favorites":
            ans = QMessageBox.question(
                self,
                LanguageManager.tr("app_title"),
                LanguageManager.tr("clear_favorites_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.Yes:
                if self.main_window and hasattr(self.main_window, 'clear_favorite_files'):
                    self.main_window.clear_favorite_files()
                self.load_recent_files()
        else:
            self._on_clear_recent_clicked()

    def _on_clear_recent_clicked(self):
        ans = QMessageBox.question(
            self,
            LanguageManager.tr("app_title"),
            LanguageManager.tr("clear_recent_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            if self.main_window and hasattr(self.main_window, 'clear_recent_files'):
                self.main_window.clear_recent_files()
            self.load_recent_files()

    def retranslate_ui(self):
        self.lbl_welcome.setText(LanguageManager.tr("home_welcome_title"))
        self.lbl_sub.setText(LanguageManager.tr("home_welcome_subtitle"))
        self.lbl_rec_title.setText(LanguageManager.tr("home_recommended_tools"))
        for card, (_, title_key, sub_key, _) in zip(self.recommended_cards, self.rec_tool_specs):
            card.retranslate(LanguageManager.tr(title_key), LanguageManager.tr(sub_key))
        if hasattr(self, 'open_card'):
            self.open_card.retranslate_ui()
        if hasattr(self, 'btn_tab_recent'):
            self.btn_tab_recent.setText(LanguageManager.tr("home_recent_title"))
        if hasattr(self, 'btn_tab_favorites'):
            self.btn_tab_favorites.setText(" " + LanguageManager.tr("home_favorites_title"))
        if hasattr(self, 'btn_add_favorite'):
            self.btn_add_favorite.setText(" " + LanguageManager.tr("home_add_favorite"))
        if hasattr(self, 'btn_clear_recent'):
            if self.current_tab_mode == "favorites":
                self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_favorite_files"))
            else:
                self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_recent_files"))
        self.load_recent_files()

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            HomeDashboardWorkspace, QScrollArea, #HomeContentContainer, #HomeInnerWrapper, #RecentListContainer {{
                background-color: {c['bg']};
            }}
            #WelcomeTitle {{
                color: {c['text']};
                font-size: 26px;
                font-weight: 800;
            }}
            #WelcomeSub {{
                color: {c['text_muted']};
                font-size: 13px;
                font-weight: 500;
            }}
            #SectionTitle {{
                color: {c['text']};
                font-size: 16px;
                font-weight: 700;
            }}
            #RecentEmpty, #RecentEmptyHint {{
                color: {c['text_muted']};
            }}
            #BtnTabRecent, #BtnTabFavorites {{
                background-color: transparent;
                color: {c['text_muted']};
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 15px;
                font-weight: 700;
            }}
            #BtnTabRecent:hover, #BtnTabFavorites:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
            #BtnTabRecent:checked, #BtnTabFavorites:checked {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                border: 1px solid {c['accent']};
            }}
            #BtnAddFavorite {{
                background-color: transparent;
                color: {c['accent']};
                border: 1px solid {c['accent']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #BtnAddFavorite:hover {{
                background-color: {c['accent_light']};
            }}
            #BtnClearRecent {{
                background-color: transparent;
                color: {c['text_muted']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            #BtnClearRecent:hover {{
                background-color: {c['surface_hover']};
                color: {c['danger']};
                border-color: {c['danger']};
            }}
        """)
        for card in self.recommended_cards:
            card.apply_theme(theme_name)
        self.open_card.apply_theme(theme_name)
        for i in range(self.v_recent_items.count()):
            w = self.v_recent_items.itemAt(i).widget()
            if isinstance(w, RecentFileRowWidget):
                w.apply_theme(theme_name)


# ==============================================================================
# 4. TAM EKRAN SAYFA ORGANİZE ETME ÇALIŞMA ALANI (OrganizePagesWorkspace)
# ==============================================================================
class PageThumbnailCard(QFrame):
    """Organize Pages görünümünde tek bir sayfanın kartı."""
    clicked = pyqtSignal(int, object)
    doubleClicked = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    rotateRequested = pyqtSignal(int, int)

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.page_index = page_index
        self.is_selected = False
        self.theme_name = "light"
        self.has_thumbnail = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(148, 194)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 5)
        layout.setSpacing(5)

        # Önizleme Resmi
        self.lbl_preview = QLabel(self)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setFixedSize(132, 150)
        self.lbl_preview.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 2px;")
        layout.addWidget(self.lbl_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Sayfa Numarası
        self.lbl_num = QLabel(str(page_index + 1), self)
        self.lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_num.setFixedHeight(22)
        layout.addWidget(self.lbl_num)

        # Kart üzerine gelindiğinde görünen hızlı silme butonu
        self.btn_quick_del = QToolButton(self)
        self.btn_quick_del.setIcon(ModernIconFactory.icon_trash("#ef4444"))
        self.btn_quick_del.setIconSize(QSize(13, 13))
        self.btn_quick_del.setFixedSize(24, 24)
        self.btn_quick_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_del.setToolTip(LanguageManager.tr("sidebar_delete_page"))
        self.btn_quick_del.setStyleSheet("""
            QToolButton {
                background: rgba(15, 23, 42, 0.82);
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 12px;
                padding: 2px;
            }
            QToolButton:hover {
                background: #ef4444;
                border-color: #ef4444;
            }
        """)
        self.btn_quick_del.move(116, 8)
        self.btn_quick_del.hide()
        self.btn_quick_del.clicked.connect(lambda: self.deleteRequested.emit(self.page_index))

        self._apply_style("light")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.btn_quick_del.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.btn_quick_del.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index, event.modifiers())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.page_index)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        apply_dialog_theme(menu, self.window())
        act_del = menu.addAction(ModernIconFactory.icon_trash("#ef4444"), "  " + LanguageManager.tr("sidebar_delete_page"))
        act_rot_cw = menu.addAction(ModernIconFactory.icon_rotate(), "  " + LanguageManager.tr("organize_rotate_cw"))
        act_rot_ccw = menu.addAction(ModernIconFactory.icon_rotate_ccw(), "  " + LanguageManager.tr("organize_rotate_ccw"))
        act = menu.exec(event.globalPos())
        if act == act_del:
            self.deleteRequested.emit(self.page_index)
        elif act == act_rot_cw:
            self.rotateRequested.emit(self.page_index, 90)
        elif act == act_rot_ccw:
            self.rotateRequested.emit(self.page_index, -90)

    def set_pixmap(self, pix: QPixmap):
        self.lbl_preview.setPixmap(pix)
        self.has_thumbnail = True

    def clear_thumbnail(self):
        self.lbl_preview.clear()
        self.has_thumbnail = False

    def set_selected(self, selected: bool, theme_name: str = "light"):
        self.is_selected = selected
        self._apply_style(theme_name)

    def _apply_style(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if self.is_selected:
            self.setStyleSheet(f"""
                PageThumbnailCard {{
                    background-color: {c['surface']};
                    border: 2.5px solid {c['accent']};
                    border-radius: 6px;
                }}
                QLabel {{
                    color: {c['accent']};
                    font-weight: 700;
                    font-size: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                PageThumbnailCard {{
                    background-color: {c['card_bg']};
                    border: 1px solid {c['card_border']};
                    border-radius: 6px;
                }}
                PageThumbnailCard:hover {{
                    border: 1.5px solid {c['accent']};
                    background-color: {c['surface_hover']};
                }}
                QLabel {{
                    color: {c['text']};
                    font-weight: 600;
                    font-size: 11px;
                }}
            """)


class OrganizePagesListWidget(QListWidget):
    """
    Organize Pages çalışma alanı için fare ile sürükle-bırak (Drag & Drop)
    sayfa yer değiştirme desteği sağlayan liste bileşeni.
    Hassas aralık tespiti ve modern yerleştirme gösterge çizgisi barındırır.
    """
    pagesReordered = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OrganizeListWidget")
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Snap)
        self.setSpacing(16)
        self.setIconSize(QSize(148, 194))
        self.setGridSize(QSize(170, 230))
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)  # Kendi modern vektörel göstergemizi çiziyoruz
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._drag_start_pos = None
        self._drop_indicator = None  # (x, y0, y1, target_row, is_before)
        self._drop_target_row = None
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._is_rubber_banding = False
        self._rubber_band_origin = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item is None:
                # Boş alana tıklandı: Rastgele herhangi bir sayfayı seçmeyi önle!
                # Ctrl veya Shift basılı değilse mevcut seçimi temizle
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                    self.clearSelection()
                    self.setCurrentItem(None)

                # Boş alandan fare ile sürükleyerek sayfaları kutu ile seçme (Marquee / RubberBand) başlat
                self._is_rubber_banding = True
                self._rubber_band_origin = event.pos()
                self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
                self._rubber_band.show()
                self._drag_start_pos = None
                event.accept()
                return
            else:
                self._is_rubber_banding = False
                self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_rubber_banding:
            rect = QRect(self._rubber_band_origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)

            modifiers = event.modifiers()
            ctrl_pressed = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

            for i in range(self.count()):
                it = self.item(i)
                item_rect = self.visualItemRect(it)
                if rect.intersects(item_rect):
                    it.setSelected(True)
                else:
                    if not ctrl_pressed:
                        it.setSelected(False)
            event.accept()
            return

        if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_start_pos:
            # Sadece kart üzerinden sürükleme başladıysa sayfa taşıma drag'ini başlat
            it_start = self.itemAt(self._drag_start_pos)
            if it_start is not None:
                dist = (event.pos() - self._drag_start_pos).manhattanLength()
                if dist >= QApplication.startDragDistance():
                    items = self.selectedItems()
                    if not items:
                        it_start.setSelected(True)
                        items = [it_start]
                    if items:
                        self._start_custom_drag(items)
                        return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_rubber_banding:
            self._is_rubber_banding = False
            self._rubber_band.hide()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_custom_drag(self, items):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-aurapdf-page-reorder", b"reorder")
        drag.setMimeData(mime)

        first_item = items[0]
        icon = first_item.icon()
        if not icon.isNull():
            pix = icon.pixmap(QSize(120, 155))
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            # Kart çerçevesi ve yarı saydam gölge
            p.setPen(QPen(QColor("#38bdf8"), 2.5))
            p.drawRoundedRect(QRectF(1.5, 1.5, pix.width() - 3, pix.height() - 3), 6, 6)

            if len(items) > 1:
                badge_text = f"+{len(items)}"
                p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                badge_w = 34
                badge_h = 22
                badge_rect = QRectF(pix.width() - badge_w - 4, 4, badge_w, badge_h)
                p.setBrush(QBrush(QColor("#0284c7")))
                p.setPen(QPen(QColor("#ffffff"), 1.5))
                p.drawRoundedRect(badge_rect, 11, 11)
                p.setPen(QColor("#ffffff"))
                p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
            p.end()
            drag.setPixmap(pix)
            drag.setHotSpot(QPoint(pix.width() // 2, pix.height() // 2))

        drag.exec(Qt.DropAction.MoveAction)
        self._drop_indicator = None
        self._drop_target_row = None
        self.viewport().update()

    def _calc_drop_target(self, pos: QPoint):
        """
        Fare koordinatına göre hedeflenen ekleme sırasını ve dikey gösterge çizgisini hesaplar.
        Izgaradaki satır geçişlerini ve öğeler arası boşlukları kusursuz yakalar.
        """
        n = self.count()
        if n == 0:
            return 0, None

        item_rects = [self.visualItemRect(self.item(i)) for i in range(n)]

        # 1. Kartları dikey Y koordinatlarına göre satırlara grupla
        rows = []
        current_row = [0]
        for i in range(1, n):
            prev_r = item_rects[i - 1]
            curr_r = item_rects[i]
            if abs(curr_r.center().y() - prev_r.center().y()) < 55:
                current_row.append(i)
            else:
                rows.append(current_row)
                current_row = [i]
        if current_row:
            rows.append(current_row)

        # 2. Fare Y koordinatına en yakın satırı bul
        chosen_row = rows[0]
        min_dy = float('inf')
        for r in rows:
            row_top = min(item_rects[i].top() for i in r)
            row_bottom = max(item_rects[i].bottom() for i in r)
            if row_top - 20 <= pos.y() <= row_bottom + 20:
                chosen_row = r
                break
            dy = min(abs(pos.y() - row_top), abs(pos.y() - row_bottom))
            if dy < min_dy:
                min_dy = dy
                chosen_row = r

        # 3. Seçilen satır içinde ekleme noktasını bul
        first_idx = chosen_row[0]
        last_idx = chosen_row[-1]
        rf = item_rects[first_idx]
        rl = item_rects[last_idx]

        if pos.x() <= rf.center().x():
            target_idx = first_idx
            ind_x = rf.left() - 8
            return target_idx, (ind_x, rf.top() - 4, rf.bottom() + 4, target_idx, True)

        if pos.x() >= rl.center().x():
            target_idx = last_idx + 1
            ind_x = rl.right() + 8
            return target_idx, (ind_x, rl.top() - 4, rl.bottom() + 4, target_idx, False)

        for k in range(len(chosen_row) - 1):
            idx_a = chosen_row[k]
            idx_b = chosen_row[k + 1]
            ra = item_rects[idx_a]
            rb = item_rects[idx_b]
            if pos.x() < rb.center().x():
                target_idx = idx_b
                ind_x = (ra.right() + rb.left()) / 2.0
                y0 = min(ra.top(), rb.top()) - 4
                y1 = max(ra.bottom(), rb.bottom()) + 4
                return target_idx, (ind_x, y0, y1, target_idx, True)

        target_idx = last_idx + 1
        ind_x = rl.right() + 8
        return target_idx, (ind_x, rl.top() - 4, rl.bottom() + 4, target_idx, False)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_indicator:
            ind_x, y0, y1, target_row, is_before = self._drop_indicator
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # 1. Yumuşak dış parlama (Glow)
            glow_col = QColor(56, 189, 248, 85)
            painter.setPen(QPen(glow_col, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(ind_x, y0 + 6), QPointF(ind_x, y1 - 6))

            # 2. Ana dikey gösterge ışını (Beam)
            is_light = self.palette().window().color().lightness() > 128
            beam_col = QColor("#0284c7") if is_light else QColor("#38bdf8")
            pen_beam = QPen(beam_col, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_beam)
            painter.drawLine(QPointF(ind_x, y0 + 6), QPointF(ind_x, y1 - 6))

            # 3. Üst ve alt dairesel tutamaçlar (Caps)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(beam_col))
            painter.drawEllipse(QPointF(ind_x, y0 + 6), 5.5, 5.5)
            painter.drawEllipse(QPointF(ind_x, y1 - 6), 5.5, 5.5)

            # 4. Yüzen bilgilendirme rozeti (Floating Tooltip Pill)
            badge_text = LanguageManager.tr("organize_drop_insert_before", target=target_row + 1) if is_before else LanguageManager.tr("organize_drop_insert_after", target=target_row)
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(badge_text) + 16
            th = fm.height() + 8

            bx = max(8.0, min(float(self.viewport().width() - tw - 8), ind_x - tw / 2.0))
            by = y0 - th - 8
            if by < 8:
                by = y1 + 8

            badge_rect = QRectF(bx, by, tw, th)
            painter.setPen(QPen(beam_col, 1.2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            painter.drawRoundedRect(badge_rect, 6, 6)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

            painter.end()

    def dragEnterEvent(self, event):
        if event.source() == self or event.mimeData().hasFormat("application/x-aurapdf-page-reorder"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self or event.mimeData().hasFormat("application/x-aurapdf-page-reorder"):
            pos = event.position().toPoint()
            target_idx, indicator = self._calc_drop_target(pos)
            if self._drop_indicator != indicator:
                self._drop_indicator = indicator
                self._drop_target_row = target_idx
                self.viewport().update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self._drop_indicator is not None:
            self._drop_indicator = None
            self._drop_target_row = None
            self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.source() != self and not event.mimeData().hasFormat("application/x-aurapdf-page-reorder"):
            event.ignore()
            return

        selected_items = self.selectedItems()
        if not selected_items:
            self._drop_indicator = None
            self._drop_target_row = None
            self.viewport().update()
            event.ignore()
            return

        pos = event.position().toPoint()
        target_row, _ = self._calc_drop_target(pos)

        self._drop_indicator = None
        self._drop_target_row = None
        self.viewport().update()

        selected_rows = sorted([self.row(it) for it in selected_items])

        current_rows = list(range(self.count()))
        moving = [r for r in current_rows if r in selected_rows]
        remaining = [r for r in current_rows if r not in selected_rows]

        items_before = sum(1 for r in selected_rows if r < target_row)
        insert_idx = max(0, min(target_row - items_before, len(remaining)))

        new_row_order = remaining[:insert_idx] + moving + remaining[insert_idx:]
        new_page_order = [self.item(r).data(Qt.ItemDataRole.UserRole) for r in new_row_order]

        event.acceptProposedAction()
        self.pagesReordered.emit(new_page_order)


class OrganizePagesWorkspace(QWidget):
    closeRequested = pyqtSignal()
    openPageRequested = pyqtSignal(int)
    documentModified = pyqtSignal()

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"
        self.selected_pages = set()
        
        self._render_queue = []
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_next_batch)
        self._loaded_doc_id = None
        self._loaded_page_count = 0
        self._rendered_pages = set()
        self._raw_thumb_images = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Ust Arac Cubugu
        self.top_toolbar = QWidget()
        self.top_toolbar.setObjectName("TopToolbar")
        self.top_toolbar.setFixedHeight(56)
        h_top = QHBoxLayout(self.top_toolbar)
        h_top.setContentsMargins(20, 8, 20, 8)
        h_top.setSpacing(8)

        def _add_sep():
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFixedHeight(22)
            sep.setStyleSheet("color: rgba(125, 125, 125, 0.35);")
            h_top.addWidget(sep)

        self.lbl_page_info = QLabel(LanguageManager.tr("page_of", total=0))
        self.lbl_page_info.setStyleSheet("font-size: 14px; font-weight: 600;")
        h_top.addWidget(self.lbl_page_info)
        h_top.addSpacing(10)
        _add_sep()

        # Sayfa Konumunu Değiştirme (Sola / Sağa Taşı)
        self.btn_move_left = QToolButton()
        self.btn_move_left.setIcon(ModernIconFactory.icon_move_left())
        self.btn_move_left.setIconSize(QSize(16, 16))
        self.btn_move_left.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_move_left.setToolTip(LanguageManager.tr("organize_move_left"))
        self.btn_move_left.clicked.connect(self.move_selected_left)
        h_top.addWidget(self.btn_move_left)

        self.btn_move_right = QToolButton()
        self.btn_move_right.setIcon(ModernIconFactory.icon_move_right())
        self.btn_move_right.setIconSize(QSize(16, 16))
        self.btn_move_right.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_move_right.setToolTip(LanguageManager.tr("organize_move_right"))
        self.btn_move_right.clicked.connect(self.move_selected_right)
        h_top.addWidget(self.btn_move_right)

        _add_sep()

        # Döndürme & Silme
        self.btn_rot_ccw = QToolButton()
        self.btn_rot_ccw.setIcon(ModernIconFactory.icon_rotate_ccw())
        self.btn_rot_ccw.setIconSize(QSize(16, 16))
        self.btn_rot_ccw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rot_ccw.setToolTip(LanguageManager.tr("organize_rotate_ccw"))
        self.btn_rot_ccw.clicked.connect(self.rotate_selected_ccw)
        h_top.addWidget(self.btn_rot_ccw)

        self.btn_rot_cw = QToolButton()
        self.btn_rot_cw.setIcon(ModernIconFactory.icon_rotate())
        self.btn_rot_cw.setIconSize(QSize(16, 16))
        self.btn_rot_cw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rot_cw.setToolTip(LanguageManager.tr("organize_rotate_cw"))
        self.btn_rot_cw.clicked.connect(self.rotate_selected_cw)
        h_top.addWidget(self.btn_rot_cw)

        self.btn_delete = QToolButton()
        self.btn_delete.setIcon(ModernIconFactory.icon_trash())
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setToolTip(LanguageManager.tr("organize_delete_pages"))
        self.btn_delete.clicked.connect(self.delete_selected_pages)
        h_top.addWidget(self.btn_delete)

        _add_sep()

        # Ekleme & Çoğaltma
        self.btn_insert_pdf = QToolButton()
        self.btn_insert_pdf.setIcon(ModernIconFactory.icon_insert_pdf())
        self.btn_insert_pdf.setIconSize(QSize(16, 16))
        self.btn_insert_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_insert_pdf.setToolTip(LanguageManager.tr("organize_insert_pdf"))
        self.btn_insert_pdf.clicked.connect(self.insert_pdf_action)
        h_top.addWidget(self.btn_insert_pdf)

        self.btn_insert = QToolButton()
        self.btn_insert.setIcon(ModernIconFactory.icon_add_page())
        self.btn_insert.setIconSize(QSize(16, 16))
        self.btn_insert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_insert.setToolTip(LanguageManager.tr("organize_insert_page"))
        self.btn_insert.clicked.connect(self.insert_page_action)
        h_top.addWidget(self.btn_insert)

        self.btn_duplicate = QToolButton()
        self.btn_duplicate.setIcon(ModernIconFactory.icon_duplicate())
        self.btn_duplicate.setIconSize(QSize(16, 16))
        self.btn_duplicate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_duplicate.setToolTip(LanguageManager.tr("organize_duplicate_page"))
        self.btn_duplicate.clicked.connect(self.duplicate_selected_pages)
        h_top.addWidget(self.btn_duplicate)

        _add_sep()

        # Sayfa Etiketi & Kırpma
        self.btn_page_label = QToolButton()
        self.btn_page_label.setIcon(ModernIconFactory.icon_page_label())
        self.btn_page_label.setIconSize(QSize(16, 16))
        self.btn_page_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_page_label.setToolTip(LanguageManager.tr("organize_page_label"))
        self.btn_page_label.clicked.connect(self.open_page_label_dialog)
        h_top.addWidget(self.btn_page_label)

        self.btn_crop = QToolButton()
        self.btn_crop.setIcon(ModernIconFactory.icon_crop())
        self.btn_crop.setIconSize(QSize(16, 16))
        self.btn_crop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_crop.setToolTip(LanguageManager.tr("organize_crop_page"))
        self.btn_crop.clicked.connect(self.open_crop_dialog)
        h_top.addWidget(self.btn_crop)

        _add_sep()

        # Çıkar, Böl, Değiştir, Tümünü Seç
        self.btn_extract = QToolButton()
        self.btn_extract.setIcon(ModernIconFactory.icon_extract())
        self.btn_extract.setIconSize(QSize(16, 16))
        self.btn_extract.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extract.setToolTip(LanguageManager.tr("organize_extract_pages"))
        self.btn_extract.clicked.connect(self.extract_pages_action)
        h_top.addWidget(self.btn_extract)

        self.btn_split = QToolButton()
        self.btn_split.setIcon(ModernIconFactory.icon_split())
        self.btn_split.setIconSize(QSize(16, 16))
        self.btn_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_split.setToolTip(LanguageManager.tr("organize_split_doc"))
        self.btn_split.clicked.connect(self.split_doc_action)
        h_top.addWidget(self.btn_split)

        self.btn_replace = QToolButton()
        self.btn_replace.setIcon(ModernIconFactory.icon_replace_page())
        self.btn_replace.setIconSize(QSize(16, 16))
        self.btn_replace.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_replace.setToolTip(LanguageManager.tr("organize_replace_pages"))
        self.btn_replace.clicked.connect(self.replace_pages_action)
        h_top.addWidget(self.btn_replace)

        self.btn_select_all = QToolButton()
        self.btn_select_all.setIcon(ModernIconFactory.icon_select_rect())
        self.btn_select_all.setIconSize(QSize(16, 16))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setToolTip(LanguageManager.tr("organize_select_all"))
        self.btn_select_all.clicked.connect(self.select_all_pages)
        h_top.addWidget(self.btn_select_all)

        h_top.addStretch(1)

        self.btn_close = QPushButton(" " + LanguageManager.tr("organize_close_btn"))
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                font-weight: 600;
                font-size: 13px;
                padding: 5px 14px;
                border-radius: 6px;
            }
        """)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_top.addWidget(self.btn_close)

        main_layout.addWidget(self.top_toolbar)

        # 2. QListWidget Izgarasi (Fare Sürükle-Bırak Destekli)
        self.list_widget = OrganizePagesListWidget(self)
        self.list_widget.pagesReordered.connect(self._on_custom_pages_reordered)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        # Ozel sag tik menusu
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        main_layout.addWidget(self.list_widget)

        self.apply_theme(self.theme_name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def cancel_rendering(self):
        if hasattr(self, '_render_timer') and self._render_timer.isActive():
            self._render_timer.stop()
        if hasattr(self, '_render_queue'):
            self._render_queue.clear()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.cancel_rendering()

    def _clear_cards(self):
        self.cancel_rendering()
        self.list_widget.clear()
        self.selected_pages.clear()
        self._loaded_doc_id = None
        self._loaded_page_count = 0
        self._rendered_pages.clear()
        self._raw_thumb_images.clear()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_pages()
            event.accept()
        elif event.key() == Qt.Key.Key_A and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.select_all_pages()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_document()

    def _create_placeholder_pixmap(self) -> QPixmap:
        w, h = 148, 194
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 255, 255))
        painter = QPainter(img)
        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawRect(0, 0, w - 1, h - 1)
        painter.end()
        return QPixmap.fromImage(img)

    def load_document(self, force: bool = False):
        if not self.isVisible() and (self.main_window and hasattr(self.main_window, 'central_stack') and self.main_window.central_stack.currentWidget() != self):
            return

        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self._clear_cards()
            self.lbl_page_info.setText(LanguageManager.tr("page_of", total=0))
            return

        doc_id = id(tab_doc.doc)
        total = len(tab_doc.doc)
        curr = getattr(tab_doc, 'current_page_idx', getattr(tab_doc, 'current_page', 0))
        if curr >= total:
            curr = max(0, total - 1)
            tab_doc.current_page_idx = curr

        if not force and self._loaded_doc_id == doc_id and self._loaded_page_count == total and self.list_widget.count() == total:
            self._update_selection_info()
            self._queue_visible_thumbnails()
            return

        self._clear_cards()
        self._loaded_doc_id = doc_id
        self._loaded_page_count = total
        self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=curr + 1, total=total))
        
        # 1000+ sayfa olsa bile aninda QListWidgetItem olusturmak performansi etkilemez
        placeholder = QIcon(self._create_placeholder_pixmap())
        for idx in range(total):
            lbl_txt = str(idx + 1)
            try:
                page_label = tab_doc.doc[idx].get_label()
                if page_label and page_label != str(idx + 1):
                    lbl_txt = f"{idx + 1} ({page_label})"
            except Exception:
                pass
            item = QListWidgetItem(placeholder, lbl_txt)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.list_widget.addItem(item)
            
        if 0 <= curr < total:
            self.list_widget.setCurrentRow(curr)
            self.list_widget.scrollToItem(self.list_widget.item(curr), QAbstractItemView.ScrollHint.PositionAtCenter)
            
        self._queue_visible_thumbnails()

    def _on_scroll(self, val):
        self._queue_visible_thumbnails()

    def _queue_visible_thumbnails(self):
        if not self.isVisible() or self.list_widget.count() == 0:
            return
            
        visible_unrendered = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            # Check visibility via viewport
            rect = self.list_widget.visualItemRect(item)
            if rect.isValid() and not rect.isEmpty():
                if i not in self._rendered_pages:
                    visible_unrendered.append(i)
        
        other_unrendered = [i for i in range(self.list_widget.count()) if i not in self._rendered_pages and i not in visible_unrendered]
        
        self._render_queue = visible_unrendered + other_unrendered
        if not self._render_timer.isActive() and self._render_queue:
            self._render_timer.start(5)

    def _render_next_batch(self):
        if not self.isVisible() or self.list_widget.count() == 0 or not self._render_queue:
            return
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        batch_size = 12
        current_batch = self._render_queue[:batch_size]
        self._render_queue = self._render_queue[batch_size:]

        for idx in current_batch:
            if idx >= self.list_widget.count() or idx in self._rendered_pages:
                continue
                
            item = self.list_widget.item(idx)
            page_index = item.data(Qt.ItemDataRole.UserRole)
            
            if page_index < len(tab_doc.doc):
                try:
                    page = tab_doc.doc[page_index]
                    rect = page.rect
                    scale = min(148.0 / max(rect.width, 1), 194.0 / max(rect.height, 1))
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    
                    icon = QIcon(QPixmap.fromImage(qimg))
                    item.setIcon(icon)
                    self._rendered_pages.add(idx)
                except Exception:
                    pass

        if self._render_queue and self.isVisible():
            self._render_timer.start(5)

    def _reorder_list_items(self, new_order: List[int], new_sel: List[int]):
        """Mevcut QListWidgetItem kartlarini ve onizlemeleri sifirlamadan yer degistirir."""
        total = self.list_widget.count()
        if total != len(new_order):
            self.load_document(force=True)
            return

        self.list_widget.blockSignals(True)
        try:
            self.list_widget.clearSelection()
            items = [self.list_widget.takeItem(0) for _ in range(total)]
            for orig_idx in new_order:
                self.list_widget.addItem(items[orig_idx])

            tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
            for idx in range(total):
                item = self.list_widget.item(idx)
                item.setData(Qt.ItemDataRole.UserRole, idx)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
                lbl_txt = str(idx + 1)
                if tab_doc and tab_doc.doc and idx < len(tab_doc.doc):
                    try:
                        pl = tab_doc.doc[idx].get_label()
                        if pl and pl != str(idx + 1):
                            lbl_txt = f"{idx + 1} ({pl})"
                    except Exception:
                        pass
                item.setText(lbl_txt)
        finally:
            self.list_widget.blockSignals(False)

        self._restore_selection(new_sel)

    def _on_custom_pages_reordered(self, new_order: List[int]):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        current_order = list(range(len(tab_doc.doc)))
        if new_order == current_order:
            return

        self.cancel_rendering()
        old_sel = set(self.selected_pages)
        tab_doc.reorder_pages(new_order, push_undo=True)
        tab_doc.set_modified(True)
        self.documentModified.emit()

        new_sel = [new_order.index(p) for p in old_sel if p in new_order]
        self._reorder_list_items(new_order, new_sel)

    def _restore_selection(self, pages: List[int]):
        self.list_widget.clearSelection()
        self.selected_pages = set()
        first_item = None
        for p in pages:
            if 0 <= p < self.list_widget.count():
                it = self.list_widget.item(p)
                it.setSelected(True)
                self.selected_pages.add(p)
                if first_item is None:
                    first_item = it
        if first_item:
            self.list_widget.scrollToItem(first_item, QAbstractItemView.ScrollHint.EnsureVisible)
        self._update_selection_info()

    def move_selected_left(self):
        """Seçili sayfaları bir konum sola / önceye taşır."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        total = len(tab_doc.doc)
        if total <= 1:
            return

        self.cancel_rendering()

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < total:
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr < total:
                    self.selected_pages = {curr}

        sel = sorted(list(self.selected_pages))
        if not sel or 0 in sel:
            return

        current = list(range(total))
        sel_set = set(sel)
        for i in range(total - 1):
            if current[i + 1] in sel_set and current[i] not in sel_set:
                current[i], current[i + 1] = current[i + 1], current[i]

        new_sel = [p - 1 if p in sel_set else p for p in sel]
        tab_doc.reorder_pages(current, push_undo=True)
        tab_doc.set_modified(True)
        self.documentModified.emit()
        self._reorder_list_items(current, new_sel)

    def move_selected_right(self):
        """Seçili sayfaları bir konum sağa / sonraya taşır."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        total = len(tab_doc.doc)
        if total <= 1:
            return

        self.cancel_rendering()

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < total:
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr < total:
                    self.selected_pages = {curr}

        sel = sorted(list(self.selected_pages))
        if not sel or (total - 1) in sel:
            return

        current = list(range(total))
        sel_set = set(sel)
        for i in range(total - 1, 0, -1):
            if current[i - 1] in sel_set and current[i] not in sel_set:
                current[i], current[i - 1] = current[i - 1], current[i]

        new_sel = [p + 1 if p in sel_set else p for p in sel]
        tab_doc.reorder_pages(current, push_undo=True)
        tab_doc.set_modified(True)
        self.documentModified.emit()
        self._reorder_list_items(current, new_sel)

    def duplicate_selected_pages(self):
        """Seçili sayfaları çoğaltıp ardına ekler."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < len(tab_doc.doc):
                self.list_widget.item(row).setSelected(True)
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr < len(tab_doc.doc):
                    self.list_widget.item(curr).setSelected(True)
                    self.selected_pages = {curr}

        if not self.selected_pages:
            return

        # Büyük indeksten küçüğe doğru kopyala ki eklemeler sonraki indeksleri kaydırmasın
        for p in sorted(list(self.selected_pages), reverse=True):
            tab_doc.duplicate_page(p)

        tab_doc.set_modified(True)
        self.load_document(force=True)
        self.documentModified.emit()

    def insert_pdf_action(self):
        """Harici PDF dosyalarından sayfaları belgeye ekler."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            LanguageManager.tr("organize_insert_pdf_title"),
            "",
            "PDF (*.pdf)"
        )
        if not file_paths:
            return

        if self.selected_pages:
            target_after = max(self.selected_pages)
        else:
            row = self.list_widget.currentRow()
            target_after = row if (0 <= row < len(tab_doc.doc)) else (len(tab_doc.doc) - 1)

        total_inserted = 0
        try:
            for path in file_paths:
                prev_len = len(tab_doc.doc)
                tab_doc.insert_pdf_at(path, after_page=target_after + total_inserted)
                new_len = len(tab_doc.doc)
                total_inserted += (new_len - prev_len)

            tab_doc.set_modified(True)
            self.load_document(force=True)
            self.documentModified.emit()
            QMessageBox.information(
                self,
                LanguageManager.tr("app_title"),
                LanguageManager.tr("insert_pdf_success", count=total_inserted)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                LanguageManager.tr("app_title"),
                LanguageManager.tr("insert_pdf_error", error=str(e))
            )

    def open_page_label_dialog(self):
        """Sayfa etiketleri ve numaralandırma yapılandırma diyaloğunu açar."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < len(tab_doc.doc):
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr < len(tab_doc.doc):
                    self.selected_pages = {curr}

        from src.ui.dialogs.page_organize_dialogs import PageLabelDialog
        dlg = PageLabelDialog(tab_doc.doc, selected_pages=list(self.selected_pages), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tab_doc.set_modified(True)
            self.load_document(force=True)
            self.documentModified.emit()
            if self.main_window and hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                try:
                    self.main_window.thumbnails_dock.load_thumbnails_lazy()
                except Exception:
                    pass

    def open_crop_dialog(self):
        """Sayfa kırpma ve kenar boşlukları diyaloğunu açar."""
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < len(tab_doc.doc):
                self.selected_pages = {row}
            else:
                curr_idx = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr_idx < len(tab_doc.doc):
                    self.selected_pages = {curr_idx}

        curr = next(iter(self.selected_pages)) if self.selected_pages else getattr(tab_doc, 'current_page_idx', 0)
        from src.ui.dialogs.page_organize_dialogs import CropPageDialog
        dlg = CropPageDialog(tab_doc.doc, current_page_idx=curr, selected_pages=list(self.selected_pages), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tab_doc.render_pages_init()
            tab_doc.rerender_visible_pages()
            tab_doc.notify_thumbnails_updated(curr)
            tab_doc.set_modified(True)
            self.load_document(force=True)
            self.documentModified.emit()
            QMessageBox.information(
                self,
                LanguageManager.tr("app_title"),
                LanguageManager.tr("organize_crop_success")
            )

    def _on_selection_changed(self):
        self.selected_pages = set()
        for item in self.list_widget.selectedItems():
            self.selected_pages.add(item.data(Qt.ItemDataRole.UserRole))
        self._update_selection_info()

    def _on_item_double_clicked(self, item):
        page_idx = item.data(Qt.ItemDataRole.UserRole)
        self.openPageRequested.emit(page_idx)

    def _show_context_menu(self, pos: QPoint):
        item = self.list_widget.itemAt(pos)
        idx = item.data(Qt.ItemDataRole.UserRole) if item else -1

        menu = QMenu(self)
        apply_dialog_theme(menu, self)

        act_del = menu.addAction(ModernIconFactory.icon_trash("#ef4444"), "  " + LanguageManager.tr("sidebar_delete_page"))
        act_rot_cw = menu.addAction(ModernIconFactory.icon_rotate(), "  " + LanguageManager.tr("organize_rotate_cw"))
        act_rot_ccw = menu.addAction(ModernIconFactory.icon_rotate_ccw(), "  " + LanguageManager.tr("organize_rotate_ccw"))
        menu.addSeparator()
        act_move_left = menu.addAction(ModernIconFactory.icon_move_left(), "  " + LanguageManager.tr("organize_move_left"))
        act_move_right = menu.addAction(ModernIconFactory.icon_move_right(), "  " + LanguageManager.tr("organize_move_right"))
        menu.addSeparator()
        act_dup = menu.addAction(ModernIconFactory.icon_duplicate(), "  " + LanguageManager.tr("organize_duplicate_page"))
        act_insert_pdf = menu.addAction(ModernIconFactory.icon_insert_pdf(), "  " + LanguageManager.tr("organize_insert_pdf"))
        act_crop = menu.addAction(ModernIconFactory.icon_crop(), "  " + LanguageManager.tr("organize_crop_page"))
        act_label = menu.addAction(ModernIconFactory.icon_page_label(), "  " + LanguageManager.tr("organize_page_label"))
        menu.addSeparator()
        act_extract = menu.addAction(ModernIconFactory.icon_extract(), "  " + LanguageManager.tr("organize_extract_pages"))

        act = menu.exec(self.list_widget.viewport().mapToGlobal(pos))
        if not act or idx < 0:
            return

        if idx not in self.selected_pages:
            self.list_widget.clearSelection()
            item.setSelected(True)
            self.selected_pages = {idx}
            self._update_selection_info()

        if act == act_del:
            self.delete_selected_pages()
        elif act == act_rot_cw:
            self.rotate_selected_cw()
        elif act == act_rot_ccw:
            self.rotate_selected_ccw()
        elif act == act_move_left:
            self.move_selected_left()
        elif act == act_move_right:
            self.move_selected_right()
        elif act == act_dup:
            self.duplicate_selected_pages()
        elif act == act_insert_pdf:
            self.insert_pdf_action()
        elif act == act_crop:
            self.open_crop_dialog()
        elif act == act_label:
            self.open_page_label_dialog()
        elif act == act_extract:
            self.extract_pages_action()

    def retranslate_ui(self):
        if hasattr(self, 'btn_move_left'):
            self.btn_move_left.setToolTip(LanguageManager.tr("organize_move_left"))
        if hasattr(self, 'btn_move_right'):
            self.btn_move_right.setToolTip(LanguageManager.tr("organize_move_right"))
        self.btn_rot_ccw.setToolTip(LanguageManager.tr("organize_rotate_ccw"))
        self.btn_rot_cw.setToolTip(LanguageManager.tr("organize_rotate_cw"))
        self.btn_delete.setToolTip(LanguageManager.tr("organize_delete_pages"))
        if hasattr(self, 'btn_insert_pdf'):
            self.btn_insert_pdf.setToolTip(LanguageManager.tr("organize_insert_pdf"))
        self.btn_insert.setToolTip(LanguageManager.tr("organize_insert_page"))
        if hasattr(self, 'btn_duplicate'):
            self.btn_duplicate.setToolTip(LanguageManager.tr("organize_duplicate_page"))
        if hasattr(self, 'btn_page_label'):
            self.btn_page_label.setToolTip(LanguageManager.tr("organize_page_label"))
        if hasattr(self, 'btn_crop'):
            self.btn_crop.setToolTip(LanguageManager.tr("organize_crop_page"))
        self.btn_extract.setToolTip(LanguageManager.tr("organize_extract_pages"))
        self.btn_split.setToolTip(LanguageManager.tr("organize_split_doc"))
        self.btn_replace.setToolTip(LanguageManager.tr("organize_replace_pages"))
        self.btn_select_all.setToolTip(LanguageManager.tr("organize_select_all"))
        self.btn_close.setText(" " + LanguageManager.tr("organize_close_btn"))
        self._update_selection_info()

    def _update_selection_info(self):
        total = self.list_widget.count()
        sel_count = len(self.selected_pages)
        if sel_count > 1:
            self.lbl_page_info.setText(LanguageManager.tr("organize_pages_selected", count=sel_count))
        elif sel_count == 1:
            p = next(iter(self.selected_pages))
            self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=p + 1, total=total))
        else:
            self.lbl_page_info.setText(LanguageManager.tr("page_of", total=total))

    def select_all_pages(self):
        self.list_widget.selectAll()

    def rotate_selected_cw(self):
        self._rotate_pages(90)

    def rotate_selected_ccw(self):
        self._rotate_pages(-90)

    def _rotate_pages(self, angle: int):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < len(tab_doc.doc):
                self.list_widget.item(row).setSelected(True)
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page_idx', getattr(tab_doc, 'current_page', 0))
                if 0 <= curr < len(tab_doc.doc):
                    self.list_widget.item(curr).setSelected(True)
                    self.selected_pages = {curr}

        if not self.selected_pages:
            return

        for p in self.selected_pages:
            if 0 <= p < len(tab_doc.doc):
                page = tab_doc.doc[p]
                page.set_rotation((page.rotation + angle) % 360)
                if p < self.list_widget.count():
                    self._rendered_pages.discard(p)
                    self.list_widget.item(p).setIcon(QIcon(self._create_placeholder_pixmap()))

        tab_doc.set_modified(True)
        self.documentModified.emit()
        self._queue_visible_thumbnails()

    def delete_selected_pages(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            row = self.list_widget.currentRow()
            if 0 <= row < len(tab_doc.doc):
                self.list_widget.item(row).setSelected(True)
                self.selected_pages = {row}
            else:
                curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
                if 0 <= curr < len(tab_doc.doc):
                    self.list_widget.item(curr).setSelected(True)
                    self.selected_pages = {curr}

        if not self.selected_pages:
            return

        if len(self.selected_pages) >= len(tab_doc.doc):
            QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_cannot_delete_last_page"))
            return

        count = len(self.selected_pages)
        if count == 1:
            msg = LanguageManager.tr("sidebar_delete_page_confirm", page=list(self.selected_pages)[0] + 1)
        else:
            msg = LanguageManager.tr("organize_delete_pages_confirm", count=count)

        res = QMessageBox.question(
            self, LanguageManager.tr("app_title"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        pages_to_delete = sorted(list(self.selected_pages), reverse=True)
        min_p = min(self.selected_pages)

        for p in pages_to_delete:
            tab_doc.delete_page(p)

        self.list_widget.clearSelection()

        new_total = len(tab_doc.doc)
        if new_total > 0:
            target_page = min(min_p, new_total - 1)
            tab_doc.current_page_idx = target_page

        tab_doc.set_modified(True)
        self.load_document(force=True)
        self.documentModified.emit()

    def insert_page_action(self):
        if hasattr(self.main_window, 'show_new_page_dialog'):
            self.main_window.show_new_page_dialog()
            QTimer.singleShot(300, lambda: self.load_document(force=True))

    def extract_pages_action(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            curr = getattr(tab_doc, 'current_page', 0)
            if 0 <= curr < len(tab_doc.doc):
                self.list_widget.item(curr).setSelected(True)

        if not self.selected_pages:
            return

        path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("organize_extract_pages"), "extracted.pdf", "PDF (*.pdf)")
        if not path:
            return

        try:
            new_doc = fitz.open()
            for p in sorted(list(self.selected_pages)):
                if 0 <= p < len(tab_doc.doc):
                    new_doc.insert_pdf(tab_doc.doc, from_page=p, to_page=p)
            new_doc.save(path)
            new_doc.close()
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("organize_extract_success", path=path))
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")

    def split_doc_action(self):
        if hasattr(self.main_window, 'open_split_dialog'):
            self.main_window.open_split_dialog()

    def replace_pages_action(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            curr = getattr(tab_doc, 'current_page', 0)
            if 0 <= curr < len(tab_doc.doc):
                self.list_widget.item(curr).setSelected(True)

        if not self.selected_pages:
            return

        src_pdf, _ = QFileDialog.getOpenFileName(self, LanguageManager.tr("organize_replace_select_source"), "", "PDF (*.pdf)")
        if not src_pdf:
            return

        try:
            other = fitz.open(src_pdf)
            for idx, p in enumerate(sorted(list(self.selected_pages))):
                if idx < len(other) and 0 <= p < len(tab_doc.doc):
                    tab_doc.doc.delete_page(p)
                    tab_doc.doc.insert_pdf(other, from_page=idx, to_page=idx, start_at=p)
            other.close()
            tab_doc.direct_edit_hover_item = None
            tab_doc.direct_edit_editor = None
            if hasattr(tab_doc, '_page_text_blocks_cache'):
                tab_doc._page_text_blocks_cache.clear()
            tab_doc.render_pages_init()
            tab_doc.rerender_visible_pages()
            tab_doc.set_modified(True)
            self.load_document(force=True)
            self.documentModified.emit()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            OrganizePagesWorkspace {{
                background-color: {c['bg']};
            }}
            QWidget#TopToolbar {{
                background-color: {c['surface']};
                border-bottom: 1px solid {c['border']};
            }}
            QListWidget#OrganizeListWidget {{
                background-color: {c['bg']};
                border: none;
                outline: 0;
            }}
            QListWidget#OrganizeListWidget::item {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 6px;
                padding: 4px;
                color: {c['text']};
            }}
            QListWidget#OrganizeListWidget::item:hover {{
                border: 1.5px solid {c['accent']};
                background-color: {c['surface_hover']};
            }}
            QListWidget#OrganizeListWidget::item:selected {{
                background-color: {c['surface']};
                border: 2.5px solid {c['accent']};
                color: {c['accent']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px;
                color: {c['text']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
            }}
            QPushButton {{
                background-color: {c['surface_hover']};
                color: {c['text']};
                border: 1px solid {c['border']};
            }}
            QPushButton:hover {{
                background-color: {c['surface_active']};
                border-color: {c['accent']};
            }}
            QRubberBand {{
                background-color: {c['accent_light']};
                border: 1.5px solid {c['accent']};
                border-radius: 4px;
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))



class WaveformWidget(QWidget):
    """Ses çalarken hafifçe hareketlenen modern AI ses dalgası animasyonu."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 18)
        self._is_active = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._color = QColor("#38bdf8")

    def set_active(self, active: bool):
        self._is_active = active
        if active:
            if not self._timer.isActive():
                self._timer.start(75)
        else:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def _on_tick(self):
        self._phase += 0.35
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bars = 4
        bar_w = 4.0
        gap = 4.0
        start_x = (self.width() - (bars * bar_w + (bars - 1) * gap)) / 2.0
        cy = self.height() / 2.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)

        for i in range(bars):
            if self._is_active:
                h = 4.5 + 8.0 * (0.5 + 0.5 * math.sin(self._phase + i * 1.4))
            else:
                h = 3.5
            x = start_x + i * (bar_w + gap)
            y = cy - h / 2.0
            p.drawRoundedRect(QRectF(x, y, bar_w, h), 2.0, 2.0)
        p.end()


class ModernAccessibilityPanel(QWidget):
    """
    Gelişmiş Erişilebilirlik ve Sesli Okuma (EMA Lightning TTS) Paneli.
    - Cümle takibi ve canlı metin vurgulama (Karaoke tarzı okuma)
    - 0.5x - 2.5x hız seçimi
    - 5 sn ileri/geri atlama ve önceki/sonraki cümle denetimleri
    - Tıklanabilir / sürüklenebilir interaktif arama çubuğu
    - Tek tıkla ses dosyasını (.wav) dışa aktarma
    - Belge sayfaları arasında doğrudan hızlı geçiş ve okuma
    """
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self._is_seeking = False
        self._last_total_dur = 0
        self._current_sentence_index = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # 1. Kompakt Üst Model ve Durum Şeridi (TTSHeaderStrip)
        self.header_status_bar = QFrame()
        self.header_status_bar.setObjectName("TTSHeaderStrip")
        self.header_status_bar.setToolTip(LanguageManager.tr("tts_model_desc"))
        h_mhead = QHBoxLayout(self.header_status_bar)
        h_mhead.setContentsMargins(8, 4, 8, 4)
        h_mhead.setSpacing(6)

        self.lbl_model_status_dot = QLabel("●")
        self.lbl_model_status_dot.setObjectName("TTSStatusDot")
        self.lbl_model_status_dot.setStyleSheet("color: #10b981; font-size: 11px;")
        h_mhead.addWidget(self.lbl_model_status_dot)

        self.lbl_model_status_text = QLabel(LanguageManager.tr("tts_status_ready"))
        self.lbl_model_status_text.setObjectName("TTSStatusText")
        h_mhead.addWidget(self.lbl_model_status_text)

        lbl_ai_badge = QLabel("EMA AI")
        lbl_ai_badge.setObjectName("TTSBadge")
        h_mhead.addWidget(lbl_ai_badge)

        self.waveform = WaveformWidget(self)
        self.waveform.setFixedSize(36, 14)
        h_mhead.addWidget(self.waveform)
        h_mhead.addStretch(1)

        self.btn_model_info = QToolButton()
        self.btn_model_info.setObjectName("TTSInfoBtn")
        self.btn_model_info.setIcon(ModernIconFactory.icon_info())
        self.btn_model_info.setIconSize(QSize(13, 13))
        self.btn_model_info.setFixedSize(22, 22)
        self.btn_model_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_model_info.setToolTip(LanguageManager.tr("tts_model_desc"))

        self.btn_download_model = QPushButton(" " + LanguageManager.tr("tts_btn_download_model"))
        self.btn_download_model.setObjectName("TTSDownloadBtn")
        self.btn_download_model.setIcon(ModernIconFactory.icon_recovery())
        self.btn_download_model.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_model.clicked.connect(self._on_download_model_clicked)
        self.btn_download_model.hide()
        h_mhead.addWidget(self.btn_download_model)

        # Geriye dönük uyumluluk referansları
        self.card_tts_model = self.header_status_bar
        self.lbl_model_desc = QLabel(LanguageManager.tr("tts_model_desc"))
        self.lbl_model_desc.hide()
        main_layout.addWidget(self.header_status_bar, stretch=0)

        # 2. Üçlü Kaynak Seçim Kapsülü (Segment Frame: Sayfa | Tüm Belge | Seçim)
        self._source_mode = "page"
        self.seg_source = QFrame()
        self.seg_source.setObjectName("TTSSegmentFrame")
        h_seg = QHBoxLayout(self.seg_source)
        h_seg.setContentsMargins(2, 2, 2, 2)
        h_seg.setSpacing(2)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.btn_mode_page = QPushButton(" " + LanguageManager.tr("tts_read_page_short"))
        self.btn_mode_page.setObjectName("TTSSegBtn")
        self.btn_mode_page.setCheckable(True)
        self.btn_mode_page.setChecked(True)
        self.btn_mode_page.setIcon(ModernIconFactory.icon_view_single())
        self.btn_mode_page.setIconSize(QSize(12, 12))
        self.btn_mode_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_page.clicked.connect(lambda: self._set_source_mode("page"))
        self.mode_group.addButton(self.btn_mode_page)
        h_seg.addWidget(self.btn_mode_page)

        self.btn_mode_all = QPushButton(" " + LanguageManager.tr("tts_read_all_short"))
        self.btn_mode_all.setObjectName("TTSSegBtn")
        self.btn_mode_all.setCheckable(True)
        self.btn_mode_all.setIcon(ModernIconFactory.icon_organize())
        self.btn_mode_all.setIconSize(QSize(12, 12))
        self.btn_mode_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_all.clicked.connect(lambda: self._set_source_mode("all"))
        self.mode_group.addButton(self.btn_mode_all)
        h_seg.addWidget(self.btn_mode_all)

        self.btn_mode_sel = QPushButton(" " + LanguageManager.tr("tts_read_selection_short"))
        self.btn_mode_sel.setObjectName("TTSSegBtn")
        self.btn_mode_sel.setCheckable(True)
        self.btn_mode_sel.setIcon(ModernIconFactory.icon_cursor())
        self.btn_mode_sel.setIconSize(QSize(12, 12))
        self.btn_mode_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_sel.clicked.connect(lambda: self._set_source_mode("selection"))
        self.mode_group.addButton(self.btn_mode_sel)
        h_seg.addWidget(self.btn_mode_sel)

        # Geriye dönük uyumluluk referansları
        self.btn_read_page = self.btn_mode_page
        self.btn_read_all = self.btn_mode_all
        self.btn_read_selection = self.btn_mode_sel

        main_layout.addWidget(self.seg_source, stretch=0)

        # 3. Sayfa Atlama ve Hızlı İşlemler Alt Satırı
        self.bar_sub_actions = QFrame()
        self.bar_sub_actions.setObjectName("TTSActionToolbar")
        h_sub = QHBoxLayout(self.bar_sub_actions)
        h_sub.setContentsMargins(2, 0, 2, 0)
        h_sub.setSpacing(4)

        self.nav_page_container = QWidget()
        h_nav = QHBoxLayout(self.nav_page_container)
        h_nav.setContentsMargins(0, 0, 0, 0)
        h_nav.setSpacing(2)

        self.btn_page_prev = QToolButton()
        self.btn_page_prev.setObjectName("TTSPageNavBtn")
        self.btn_page_prev.setIcon(ModernIconFactory.icon_chevron_left())
        self.btn_page_prev.setIconSize(QSize(11, 11))
        self.btn_page_prev.setFixedSize(20, 20)
        self.btn_page_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_page_prev.setToolTip(LanguageManager.tr("tts_prev_page"))
        self.btn_page_prev.clicked.connect(self._go_prev_page)
        h_nav.addWidget(self.btn_page_prev)

        self.lbl_page_info = QLabel(LanguageManager.tr("tts_page_nav", curr=1, total=1))
        self.lbl_page_info.setObjectName("TTSPageInfoLabel")
        self.lbl_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_nav.addWidget(self.lbl_page_info)

        self.btn_page_next = QToolButton()
        self.btn_page_next.setObjectName("TTSPageNavBtn")
        self.btn_page_next.setIcon(ModernIconFactory.icon_chevron_right())
        self.btn_page_next.setIconSize(QSize(11, 11))
        self.btn_page_next.setFixedSize(20, 20)
        self.btn_page_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_page_next.setToolTip(LanguageManager.tr("tts_next_page"))
        self.btn_page_next.clicked.connect(self._go_next_page)
        h_nav.addWidget(self.btn_page_next)

        h_sub.addWidget(self.nav_page_container)
        h_sub.addStretch(1)

        self.btn_paste_clipboard = QToolButton()
        self.btn_paste_clipboard.setObjectName("TTSToolBtn")
        self.btn_paste_clipboard.setIcon(ModernIconFactory.icon_paste())
        self.btn_paste_clipboard.setIconSize(QSize(12, 12))
        self.btn_paste_clipboard.setFixedSize(22, 22)
        self.btn_paste_clipboard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste_clipboard.setToolTip(LanguageManager.tr("tts_paste_clipboard"))
        self.btn_paste_clipboard.clicked.connect(self._paste_clipboard)
        h_sub.addWidget(self.btn_paste_clipboard)

        self.btn_export_audio = QToolButton()
        self.btn_export_audio.setObjectName("TTSToolBtn")
        self.btn_export_audio.setIcon(ModernIconFactory.icon_export_audio())
        self.btn_export_audio.setIconSize(QSize(12, 12))
        self.btn_export_audio.setFixedSize(22, 22)
        self.btn_export_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_audio.setToolTip(LanguageManager.tr("tts_export_audio"))
        self.btn_export_audio.clicked.connect(self._export_audio_action)
        h_sub.addWidget(self.btn_export_audio)

        self.btn_clear_text = QToolButton()
        self.btn_clear_text.setObjectName("TTSToolBtn")
        self.btn_clear_text.setIcon(ModernIconFactory.icon_trash())
        self.btn_clear_text.setIconSize(QSize(12, 12))
        self.btn_clear_text.setFixedSize(22, 22)
        self.btn_clear_text.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_text.setToolTip(LanguageManager.tr("tts_clear_text"))
        self.btn_clear_text.clicked.connect(self._clear_text)
        h_sub.addWidget(self.btn_clear_text)

        # Geriye dönük uyumluluk referansları
        self.bar_actions = self.bar_sub_actions
        self.card_page_nav = self.bar_sub_actions
        self._action_buttons = [
            self.btn_read_page, self.btn_read_all, self.btn_read_selection,
            self.btn_paste_clipboard, self.btn_clear_text, self.btn_export_audio
        ]
        main_layout.addWidget(self.bar_sub_actions, stretch=0)

        # 3. Dinamik Genişleyen Canlı Okuma Tuvali (Hero Reading Canvas)
        self.card_reading_canvas = QFrame()
        self.card_reading_canvas.setObjectName("TTSReadingCanvas")
        v_canvas = QVBoxLayout(self.card_reading_canvas)
        v_canvas.setContentsMargins(8, 6, 8, 8)
        v_canvas.setSpacing(4)

        # Tuval Başlık ve Canlı İstatistik Şeridi
        h_chead = QHBoxLayout()
        h_chead.setContentsMargins(0, 0, 0, 0)
        h_chead.setSpacing(6)

        self.lbl_canvas_icon = QLabel()
        self.lbl_canvas_icon.setPixmap(ModernIconFactory.icon_reading_mode().pixmap(13, 13))
        h_chead.addWidget(self.lbl_canvas_icon)

        self.lbl_canvas_title = QLabel(LanguageManager.tr("tts_reading_canvas_title"))
        self.lbl_canvas_title.setObjectName("TTSCanvasTitle")
        h_chead.addWidget(self.lbl_canvas_title)

        h_chead.addStretch(1)

        self.lbl_canvas_stats = QLabel(LanguageManager.tr("tts_stats_empty"))
        self.lbl_canvas_stats.setObjectName("TTSCanvasStats")
        h_chead.addWidget(self.lbl_canvas_stats)

        v_canvas.addLayout(h_chead)

        # Esnek ve Dikeyde Otomatik Büyüyen Metin Alanı
        self.txt_tts_input = QTextEdit()
        self.txt_tts_input.setObjectName("TTSTextInput")
        self.txt_tts_input.setPlaceholderText(LanguageManager.tr("tts_no_text_found"))
        self.txt_tts_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.txt_tts_input.setMinimumHeight(120)
        self.txt_tts_input.textChanged.connect(self._update_text_stats)
        v_canvas.addWidget(self.txt_tts_input, stretch=1)

        main_layout.addWidget(self.card_reading_canvas, stretch=1)

        # 4. Gelişmiş Minimalist Oynatıcı Kartı (TTSPlayerCard)
        self.card_tts_player = QFrame()
        self.card_tts_player.setObjectName("TTSPlayerCard")
        v_pcard = QVBoxLayout(self.card_tts_player)
        v_pcard.setContentsMargins(8, 8, 8, 8)
        v_pcard.setSpacing(5)

        # 4a. Durum ve Zaman Göstergesi
        h_pstatus = QHBoxLayout()
        h_pstatus.setContentsMargins(0, 0, 0, 0)
        self.lbl_tts_playback_status = QLabel(LanguageManager.tr("tts_status_ready"))
        self.lbl_tts_playback_status.setObjectName("TTSPlaybackStatus")
        h_pstatus.addWidget(self.lbl_tts_playback_status, stretch=1)

        self.lbl_tts_time = QLabel("00:00")
        self.lbl_tts_time.setObjectName("TTSTimeLabel")
        h_pstatus.addWidget(self.lbl_tts_time)
        v_pcard.addLayout(h_pstatus)

        # 4b. Özel Tasarımlı İlerleme Çubuğu (Seek Slider)
        self.slider_tts_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_tts_progress.setObjectName("TTSProgressSlider")
        self.slider_tts_progress.setFixedHeight(16)
        self.slider_tts_progress.setRange(0, 1000)
        self.slider_tts_progress.setValue(0)
        self.slider_tts_progress.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_tts_progress.sliderPressed.connect(self._on_seek_pressed)
        self.slider_tts_progress.sliderReleased.connect(self._on_seek_released)
        self.slider_tts_progress.sliderMoved.connect(self._on_seek_moved)
        v_pcard.addWidget(self.slider_tts_progress)

        # 4c. Oynatma Kontrol Butonları Satırı (4 Buton: Ferah, Sıfır Çakışma)
        h_pbtns = QHBoxLayout()
        h_pbtns.setContentsMargins(0, 2, 0, 2)
        h_pbtns.setSpacing(8)
        h_pbtns.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_prev_chunk = QToolButton()
        self.btn_prev_chunk.setObjectName("TTSRoundBtn")
        self.btn_prev_chunk.setIcon(ModernIconFactory.icon_media_prev())
        self.btn_prev_chunk.setIconSize(QSize(13, 13))
        self.btn_prev_chunk.setFixedSize(30, 30)
        self.btn_prev_chunk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_chunk.setToolTip(LanguageManager.tr("tts_prev_sentence"))
        self.btn_prev_chunk.clicked.connect(self._prev_sentence)
        h_pbtns.addWidget(self.btn_prev_chunk)

        self.btn_tts_play = QPushButton(" " + LanguageManager.tr("tts_play_btn"))
        self.btn_tts_play.setObjectName("TTSHeroPlayBtn")
        self.btn_tts_play.setIcon(ModernIconFactory.icon_play("#ffffff"))
        self.btn_tts_play.setIconSize(QSize(14, 14))
        self.btn_tts_play.setFixedSize(112, 34)
        self.btn_tts_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts_play.clicked.connect(self._toggle_play_tts)
        h_pbtns.addWidget(self.btn_tts_play)

        self.btn_next_chunk = QToolButton()
        self.btn_next_chunk.setObjectName("TTSRoundBtn")
        self.btn_next_chunk.setIcon(ModernIconFactory.icon_media_next())
        self.btn_next_chunk.setIconSize(QSize(13, 13))
        self.btn_next_chunk.setFixedSize(30, 30)
        self.btn_next_chunk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_chunk.setToolTip(LanguageManager.tr("tts_next_sentence"))
        self.btn_next_chunk.clicked.connect(self._next_sentence)
        h_pbtns.addWidget(self.btn_next_chunk)

        self.btn_tts_stop = QToolButton()
        self.btn_tts_stop.setObjectName("TTSRoundBtn")
        self.btn_tts_stop.setIcon(ModernIconFactory.icon_stop())
        self.btn_tts_stop.setIconSize(QSize(13, 13))
        self.btn_tts_stop.setFixedSize(30, 30)
        self.btn_tts_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts_stop.setToolTip(LanguageManager.tr("tts_stop_btn"))
        self.btn_tts_stop.clicked.connect(self._stop_tts)
        h_pbtns.addWidget(self.btn_tts_stop)

        # Geriye dönük uyumluluk için görünmez referanslar
        self.btn_skip_back = QToolButton()
        self.btn_skip_back.hide()
        self.btn_skip_fwd = QToolButton()
        self.btn_skip_fwd.hide()
        self._control_buttons = [
            self.btn_page_prev, self.btn_page_next, self.btn_prev_chunk,
            self.btn_next_chunk, self.btn_tts_stop
        ]
        v_pcard.addLayout(h_pbtns)

        # 4d. Hız, Ses Çıkış Cihazı ve Ses Seviyesi Satırı
        h_util = QHBoxLayout()
        h_util.setContentsMargins(0, 2, 0, 0)
        h_util.setSpacing(4)

        self._current_speed = 1.0
        self._speed_values = [0.75, 1.0, 1.25, 1.5, 2.0]
        self._speed_actions = {}
        self.speed_group = QButtonGroup(self)

        self.btn_speed = QPushButton("1.0x ▾")
        self.btn_speed.setObjectName("TTSPillBtn")
        self.btn_speed.setIcon(ModernIconFactory.icon_speed())
        self.btn_speed.setIconSize(QSize(12, 12))
        self.btn_speed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speed.setToolTip(LanguageManager.tr("tts_speed"))
        self.btn_speed.setFixedHeight(22)
        self._setup_speed_menu()
        h_util.addWidget(self.btn_speed)

        self.btn_audio_device = QPushButton("Ses ▾")
        self.btn_audio_device.setObjectName("TTSPillBtn")
        self.btn_audio_device.setIcon(ModernIconFactory.icon_speech())
        self.btn_audio_device.setIconSize(QSize(12, 12))
        self.btn_audio_device.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_audio_device.setToolTip(LanguageManager.tr("tts_device"))
        self.btn_audio_device.setFixedHeight(22)
        h_util.addWidget(self.btn_audio_device)

        # Geriye dönük uyumluluk için dummy combo
        self.combo_audio_dev = QComboBox()
        self.combo_audio_dev.hide()
        self.lbl_dev_icon = QLabel()
        self.lbl_dev_icon.hide()

        h_util.addStretch(1)

        lbl_vol_icon = QLabel()
        lbl_vol_icon.setPixmap(ModernIconFactory.icon_speech().pixmap(12, 12))
        h_util.addWidget(lbl_vol_icon)

        self.slider_tts_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_tts_vol.setObjectName("TTSVolumeSlider")
        self.slider_tts_vol.setFixedWidth(55)
        self.slider_tts_vol.setFixedHeight(14)
        self.slider_tts_vol.setRange(0, 100)
        self.slider_tts_vol.setValue(100)
        self.slider_tts_vol.setToolTip("100%")
        self.slider_tts_vol.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_tts_vol.valueChanged.connect(self._on_volume_changed)
        h_util.addWidget(self.slider_tts_vol)

        v_pcard.addLayout(h_util)
        main_layout.addWidget(self.card_tts_player, stretch=0)

        # Ses Motoru Bağlantıları
        self.speech_engine = AuraSpeechEngine(self)
        self.speech_engine.state_changed.connect(self._on_tts_state_changed)
        self.speech_engine.reading_started.connect(self._on_tts_reading_started)
        self.speech_engine.reading_finished.connect(self._on_tts_reading_finished)
        self.speech_engine.playback_progress.connect(self._on_tts_playback_progress)
        self.speech_engine.error_occurred.connect(self._on_tts_error)
        self.speech_engine.model_status_changed.connect(self._on_tts_model_status_changed)
        self.speech_engine.current_chunk_changed.connect(self._on_tts_chunk_changed)
        self.speech_engine.audio_device_changed.connect(self._on_speech_device_changed)
        self.speech_engine.available_devices_changed.connect(self._refresh_audio_devices)
        self.speech_engine.check_and_notify_status()
        self._refresh_audio_devices()

    def _extract_text_from_page(self, tab_doc, page_idx: int) -> str:
        """
        Sayfadaki TÜM metin kaynaklarını (PDF metin katmanı, inline metin kutuları,
        çizimler, ek açıklamalar, form alanları ve doğrudan düzenleyiciler) eksiksiz toplar.
        """
        if not tab_doc or not tab_doc.doc or not (0 <= page_idx < len(tab_doc.doc)):
            return ""

        collected = []
        seen = set()

        def add_t(t: str):
            if not t:
                return
            cleaned = t.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                collected.append(cleaned)

        # 1. Standart PyMuPDF sayfa metin katmanı
        try:
            p = tab_doc.doc[page_idx]
            raw_text = p.get_text().strip()
            if raw_text:
                add_t(raw_text)
        except Exception:
            pass

        # 2. Canlı düzenleme modundaki doğrudan metin düzenleyici (DirectTextInplaceEditor)
        direct_editor = getattr(tab_doc, 'direct_edit_editor', None)
        if direct_editor and getattr(direct_editor, 'page_idx', None) == page_idx:
            try:
                ed_txt = direct_editor.txt_edit.toPlainText().strip()
                if ed_txt:
                    add_t(ed_txt)
            except Exception:
                pass

        # 3. Aktif veya son seçili metin kutusu (EditableInlineTextItem)
        for attr in ('active_text_item', 'last_text_item'):
            it = getattr(tab_doc, attr, None)
            if it and getattr(it, 'page_idx', None) == page_idx:
                try:
                    txt = it.toPlainText().strip()
                    if txt:
                        add_t(txt)
                except Exception:
                    pass

        # 4. Sayfadaki çizimler ve eklenen metin kutuları (tab_doc.drawings)
        if hasattr(tab_doc, 'drawings') and tab_doc.drawings:
            for d in tab_doc.drawings:
                if d.get("page") == page_idx:
                    d_txt = d.get("text", "")
                    if not d_txt and d.get("item_ref"):
                        try:
                            d_txt = d["item_ref"].toPlainText()
                        except Exception:
                            d_txt = ""
                    if d_txt:
                        add_t(d_txt)

        # 5. Sahnedeki (QGraphicsScene) tüm EditableInlineTextItem öğeleri
        if hasattr(tab_doc, 'scene') and tab_doc.scene:
            try:
                from src.ui.widgets import EditableInlineTextItem
                for item in tab_doc.scene.items():
                    if isinstance(item, EditableInlineTextItem):
                        if getattr(item, 'page_idx', None) == page_idx:
                            txt = item.toPlainText().strip()
                            if txt:
                                add_t(txt)
            except Exception:
                pass

        # 6. PDF Ek Açıklamaları (Annotations: Sticky Note, FreeText vb.)
        try:
            p = tab_doc.doc[page_idx]
            for annot in p.annots():
                info = annot.info or {}
                content = info.get("content", "").strip()
                if content:
                    add_t(content)
        except Exception:
            pass

        # 7. Form Alanları (Widgets)
        try:
            p = tab_doc.doc[page_idx]
            for widget in p.widgets():
                val = widget.field_value
                if val and isinstance(val, str) and val.strip():
                    add_t(val.strip())
        except Exception:
            pass

        return "\n\n".join(collected)

    def _extract_selected_text_for_speech(self, tab_doc) -> str:
        """
        Kullanıcının seçtiği metni tüm seçim mekanizmalarından tespit eder.
        """
        if not tab_doc:
            return ""

        # 1. Klasik PDF metin seçimi
        sel = getattr(tab_doc, 'selected_text', '').strip()
        if sel:
            return sel

        # 2. Aktif metin kutusu (EditableInlineTextItem) içindeki seçim veya tüm metin
        for attr in ('active_text_item', 'last_text_item'):
            it = getattr(tab_doc, attr, None)
            if it:
                try:
                    cur = it.textCursor()
                    if cur and cur.hasSelection():
                        st = cur.selectedText().strip()
                        if st:
                            return st
                    full_it = it.toPlainText().strip()
                    if full_it:
                        return full_it
                except Exception:
                    pass

        # 3. Doğrudan metin düzenleyici (DirectTextInplaceEditor) seçimi veya metni
        direct_editor = getattr(tab_doc, 'direct_edit_editor', None)
        if direct_editor:
            try:
                cur = direct_editor.txt_edit.textCursor()
                if cur and cur.hasSelection():
                    st = cur.selectedText().strip()
                    if st:
                        return st
                ed_txt = direct_editor.txt_edit.toPlainText().strip()
                if ed_txt:
                    return ed_txt
            except Exception:
                pass

        # 4. Seçili çizimler (selected_drawings)
        if hasattr(tab_doc, 'selected_drawings') and tab_doc.selected_drawings:
            texts = []
            for d in tab_doc.selected_drawings:
                d_txt = d.get("text", "")
                if not d_txt and d.get("item_ref"):
                    try:
                        d_txt = d["item_ref"].toPlainText()
                    except Exception:
                        d_txt = ""
                if d_txt and d_txt.strip():
                    texts.append(d_txt.strip())
            if texts:
                return "\n".join(texts)

        # 5. Sahne üzerinde seçili olan öğeler (scene.selectedItems())
        if hasattr(tab_doc, 'scene') and tab_doc.scene:
            try:
                from src.ui.widgets import EditableInlineTextItem
                for item in tab_doc.scene.selectedItems():
                    if isinstance(item, EditableInlineTextItem):
                        txt = item.toPlainText().strip()
                        if txt:
                            return txt
            except Exception:
                pass

        return ""

    def _set_source_mode(self, mode: str):
        self._source_mode = mode
        if hasattr(self, 'btn_mode_page'):
            self.btn_mode_page.setChecked(mode == "page")
        if hasattr(self, 'btn_mode_all'):
            self.btn_mode_all.setChecked(mode == "all")
        if hasattr(self, 'btn_mode_sel'):
            self.btn_mode_sel.setChecked(mode == "selection")

        if hasattr(self, 'nav_page_container'):
            self.nav_page_container.setVisible(mode == "page")

        if mode == "page":
            self._load_current_page_text()
        elif mode == "all":
            self._load_all_pages_text()
        elif mode == "selection":
            self._load_selection_text()

    def _load_current_source_text(self):
        if getattr(self, '_source_mode', 'page') == "page":
            self._load_current_page_text()
        elif getattr(self, '_source_mode', 'page') == "all":
            self._load_all_pages_text()
        elif getattr(self, '_source_mode', 'page') == "selection":
            self._load_selection_text()

    def _setup_audio_device_menu(self):
        if not hasattr(self, 'btn_audio_device'):
            return
        menu = QMenu(self)
        self._audio_device_menu = menu
        devices = self.speech_engine.get_available_audio_devices()
        curr_id = getattr(self.speech_engine, '_current_device_id', None)
        def_dev = QMediaDevices.defaultAudioOutput()
        def_id = def_dev.id()

        # Sistem varsayılanı (Otomatik)
        def_desc = def_dev.description() if not def_dev.isNull() else "Sistem"
        act_def = menu.addAction(f"{LanguageManager.tr('tts_device_default')} ({def_desc})")
        act_def.setCheckable(True)
        act_def.setChecked(curr_id is None)
        act_def.triggered.connect(lambda: self._select_audio_device(None))

        if devices:
            menu.addSeparator()

        for d in devices:
            name = d["name"]
            is_bt = any(k in name.lower() for k in ("bluetooth", "headphone", "earphone", "buds", "airpods", "kulaklık"))
            icon = ModernIconFactory.icon_headphones() if is_bt else ModernIconFactory.icon_speech()
            act = menu.addAction(icon, name)
            act.setCheckable(True)
            is_active = (curr_id == d["id"])
            act.setChecked(is_active)
            dev_id = d["id"]
            act.triggered.connect(lambda checked, did=dev_id: self._select_audio_device(did))

        self.btn_audio_device.setMenu(menu)

    def _select_audio_device(self, dev_id):
        self.speech_engine.set_audio_device(dev_id)
        self._refresh_audio_devices()

    def _refresh_audio_devices(self, devices=None):
        if not hasattr(self, 'btn_audio_device'):
            return
        desc = self.speech_engine.get_current_audio_device_desc()
        is_bt = any(k in desc.lower() for k in ("bluetooth", "headphone", "earphone", "buds", "airpods", "kulaklık"))
        c = get_modern_theme_colors(self.theme_name)
        icon = ModernIconFactory.icon_headphones(c.get('accent', '#38bdf8')) if is_bt else ModernIconFactory.icon_speech(c.get('accent', '#38bdf8'))
        self.btn_audio_device.setIcon(icon)

        def _elide(text: str, max_len: int = 14) -> str:
            return (text[:max_len - 1] + "…") if len(text) > max_len else text

        short_desc = _elide(desc, 14)
        self.btn_audio_device.setText(f"{short_desc} ▾")
        self.btn_audio_device.setToolTip(f"{LanguageManager.tr('tts_device')}: {desc}")
        self._setup_audio_device_menu()

    def _on_speech_device_changed(self, device_name: str, is_auto_switched: bool):
        self._refresh_audio_devices()
        if is_auto_switched:
            short_name = device_name[:28] + ("..." if len(device_name) > 28 else "")
            self.lbl_tts_playback_status.setText(
                LanguageManager.tr("tts_device_auto_switched", device=short_name)
            )

    def load_accessibility(self):
        """Erişilebilirlik ve TTS panelini günceller."""
        if hasattr(self, 'speech_engine'):
            self.speech_engine.check_and_notify_status()
        self._refresh_audio_devices()
        self._sync_page_info()
        self._load_current_source_text()

    def _sync_page_info(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if tab_doc and tab_doc.doc:
            curr = getattr(tab_doc, 'current_page_idx', 0) + 1
            total = len(tab_doc.doc)
            self.lbl_page_info.setText(LanguageManager.tr("tts_page_nav", curr=curr, total=total))
            self.btn_page_prev.setEnabled(curr > 1)
            self.btn_page_next.setEnabled(curr < total)
        else:
            self.lbl_page_info.setText(LanguageManager.tr("tts_page_nav", curr=1, total=1))
            self.btn_page_prev.setEnabled(False)
            self.btn_page_next.setEnabled(False)

    def _go_prev_page(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        curr = getattr(tab_doc, 'current_page_idx', 0)
        if curr > 0:
            tab_doc.go_to_page(curr - 1)
            self._sync_page_info()
            if getattr(self, '_source_mode', 'page') == "page":
                self._load_current_page_text()

    def _go_next_page(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        curr = getattr(tab_doc, 'current_page_idx', 0)
        if curr < len(tab_doc.doc) - 1:
            tab_doc.go_to_page(curr + 1)
            self._sync_page_info()
            if getattr(self, '_source_mode', 'page') == "page":
                self._load_current_page_text()

    def _load_current_page_text(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        curr = getattr(tab_doc, 'current_page_idx', 0)
        text = self._extract_text_from_page(tab_doc, curr)
        cleaned = clean_text_for_speech(text)
        if cleaned:
            self.txt_tts_input.setPlainText(cleaned)

    def _load_all_pages_text(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        all_text = ""
        for i in range(len(tab_doc.doc)):
            p_text = self._extract_text_from_page(tab_doc, i)
            if p_text:
                all_text += p_text + "\n\n"
        cleaned = clean_text_for_speech(all_text)
        if cleaned:
            self.txt_tts_input.setPlainText(cleaned)

    def _load_selection_text(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        text = self._extract_selected_text_for_speech(tab_doc) if tab_doc else ""
        cleaned = clean_text_for_speech(text)
        if cleaned:
            self.txt_tts_input.setPlainText(cleaned)

    def _read_current_page(self):
        self._set_source_mode("page")
        self._load_current_page_text()
        text = self.txt_tts_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.speech_engine.speak(text)

    def _read_all_pages(self):
        self._set_source_mode("all")
        self._load_all_pages_text()
        text = self.txt_tts_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.speech_engine.speak(text)

    def _read_selected_text(self):
        self._set_source_mode("selection")
        self._load_selection_text()
        text = self.txt_tts_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.speech_engine.speak(text)

    def _paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            cleaned = clean_text_for_speech(text)
            self.txt_tts_input.setPlainText(cleaned or text)

    def _clear_text(self):
        self.txt_tts_input.clear()
        self._stop_tts()

    def _export_audio_action(self):
        if not self.speech_engine._all_chunks:
            QMessageBox.information(
                self, LanguageManager.tr("app_title"),
                LanguageManager.tr("tts_no_audio_to_export")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            LanguageManager.tr("tts_export_audio"),
            "speech.wav",
            LanguageManager.tr("tts_audio_filter")
        )
        if not file_path:
            return

        ok = self.speech_engine.export_audio_file(file_path)
        if ok:
            QMessageBox.information(
                self, LanguageManager.tr("app_title"),
                LanguageManager.tr("tts_export_success", path=file_path)
            )
        else:
            QMessageBox.warning(
                self, LanguageManager.tr("app_title"),
                LanguageManager.tr("tts_export_error", error="Failed to save audio file")
            )

    def _setup_speed_menu(self):
        menu = QMenu(self)
        self._speed_menu = menu
        self._speed_actions = {}
        for sval in self._speed_values:
            act = menu.addAction(LanguageManager.tr("tts_speed_val", val=sval))
            act.setCheckable(True)
            if sval == 1.0:
                act.setChecked(True)
            act.triggered.connect(lambda checked, v=sval: self._on_speed_selected(v))
            self._speed_actions[sval] = act
        self.btn_speed.setMenu(menu)

    def _on_speed_selected(self, val: float):
        self._current_speed = val
        self.speech_engine.set_playback_rate(val)
        if hasattr(self, 'btn_speed'):
            self.btn_speed.setText(f"{val}x ▾")
        if hasattr(self, '_speed_actions'):
            for sval, act in self._speed_actions.items():
                act.setChecked(abs(sval - val) < 0.01)

    def _prev_sentence(self):
        self.speech_engine.prev_chunk()

    def _next_sentence(self):
        self.speech_engine.next_chunk()

    def _on_seek_pressed(self):
        self._is_seeking = True

    def _on_seek_moved(self, val: int):
        if self._last_total_dur > 0:
            pos_ms = int((val / 1000.0) * self._last_total_dur)
            sec = pos_ms // 1000
            m, s = sec // 60, sec % 60
            tot_sec = self._last_total_dur // 1000
            tm, ts = tot_sec // 60, tot_sec % 60
            self.lbl_tts_time.setText(f"{m:02d}:{s:02d} / {tm:02d}:{ts:02d}")

    def _on_seek_released(self):
        self._is_seeking = False
        if self._last_total_dur > 0:
            target_ms = int((self.slider_tts_progress.value() / 1000.0) * self._last_total_dur)
            self.speech_engine.seek_to_ms(target_ms)

    def _toggle_play_tts(self):
        if self.speech_engine.is_paused():
            self.speech_engine.resume()
        elif self.speech_engine.is_speaking():
            self.speech_engine.pause()
        else:
            text = self.txt_tts_input.toPlainText().strip()
            if not text:
                tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
                curr_idx = getattr(tab_doc, 'current_page_idx', 0) if tab_doc else 0
                page_text = self._extract_text_from_page(tab_doc, curr_idx)
                if page_text:
                    self.txt_tts_input.setPlainText(page_text)
                    text = page_text
            if not text:
                QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
                return
            self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
            self.speech_engine.speak(text)

    def _pause_tts(self):
        self.speech_engine.pause()

    def _stop_tts(self):
        self.speech_engine.stop()
        self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
        self.btn_tts_play.setIcon(ModernIconFactory.icon_play("#ffffff"))
        self.slider_tts_progress.setValue(0)
        self.lbl_tts_time.setText("00:00")
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_stopped"))
        self.waveform.set_active(False)
        self._clear_highlights()

    def _on_volume_changed(self, val: int):
        if hasattr(self, 'slider_tts_vol'):
            self.slider_tts_vol.setToolTip(f"{val}%")
        self.speech_engine.set_volume(val)

    def _on_download_model_clicked(self):
        self.btn_download_model.setEnabled(False)
        self.lbl_model_status_text.setText(LanguageManager.tr("tts_status_downloading"))
        self.speech_engine.download_model()

    def _on_tts_model_status_changed(self, is_ready: bool, message: str):
        if is_ready:
            self.lbl_model_status_dot.setText("●")
            self.lbl_model_status_dot.setStyleSheet("color: #10b981; font-size: 11px;")
            self.lbl_model_status_text.setText(LanguageManager.tr("tts_status_ready"))
            self.btn_download_model.hide()
        else:
            self.lbl_model_status_dot.setText("●")
            self.lbl_model_status_dot.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.lbl_model_status_text.setText(message)
            self.btn_download_model.show()
            self.btn_download_model.setEnabled(True)

    def _on_tts_state_changed(self, is_speaking: bool):
        self.waveform.set_active(is_speaking)
        if is_speaking:
            self.btn_tts_play.setText(" " + LanguageManager.tr("tts_pause_btn"))
            self.btn_tts_play.setIcon(ModernIconFactory.icon_pause("#ffffff"))
            self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        else:
            self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
            self.btn_tts_play.setIcon(ModernIconFactory.icon_play("#ffffff"))
            if self.speech_engine.is_paused():
                self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_paused"))

    def _on_tts_reading_started(self, snippet: str):
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.waveform.set_active(True)

    def _on_tts_reading_finished(self):
        self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
        self.btn_tts_play.setIcon(ModernIconFactory.icon_play("#ffffff"))
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_ready"))
        self.slider_tts_progress.setValue(0)
        self.lbl_tts_time.setText("00:00")
        self.waveform.set_active(False)
        self._clear_highlights()

    def _on_tts_chunk_changed(self, idx: int, total: int, chunk_text: str):
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_sentence_progress", curr=idx + 1, total=total))
        self._highlight_chunk_text(chunk_text)

    def _clear_highlights(self):
        if not self.txt_tts_input:
            return
        doc = self.txt_tts_input.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        default_fmt = QTextCharFormat()
        default_fmt.setBackground(Qt.GlobalColor.transparent)
        cursor.setCharFormat(default_fmt)

    def _update_text_stats(self):
        if not hasattr(self, 'lbl_canvas_stats') or not hasattr(self, 'txt_tts_input'):
            return
        text = self.txt_tts_input.toPlainText().strip()
        if not text:
            self.lbl_canvas_stats.setText(LanguageManager.tr("tts_stats_empty"))
            return
        words = len(text.split())
        self.lbl_canvas_stats.setText(LanguageManager.tr("tts_stats_words", words=words))

    def _highlight_chunk_text(self, chunk_text: str):
        if not chunk_text or not self.txt_tts_input:
            return
        self._clear_highlights()
        doc = self.txt_tts_input.document()
        snippet = chunk_text.strip()
        search_target = snippet[:min(32, len(snippet))]
        found_cursor = doc.find(search_target)
        if not found_cursor.isNull():
            end_pos = found_cursor.position() + max(0, len(snippet) - len(search_target))
            found_cursor.setPosition(found_cursor.anchor())
            found_cursor.setPosition(min(end_pos, doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
            fmt = QTextCharFormat()
            c = get_modern_theme_colors(self.theme_name)
            accent_col = QColor(c.get('accent', '#38bdf8'))
            accent_col.setAlpha(70)
            fmt.setBackground(accent_col)
            found_cursor.setCharFormat(fmt)
            self.txt_tts_input.setTextCursor(found_cursor)
            self.txt_tts_input.ensureCursorVisible()

    def _on_tts_playback_progress(self, pos_ms: int, dur_ms: int):
        self._last_total_dur = dur_ms
        if dur_ms > 0 and not self._is_seeking:
            frac = int((pos_ms / dur_ms) * 1000)
            self.slider_tts_progress.setValue(min(1000, frac))
            sec = int(pos_ms / 1000)
            m = sec // 60
            s = sec % 60
            tot_sec = int(dur_ms / 1000)
            tm = tot_sec // 60
            ts = tot_sec % 60
            self.lbl_tts_time.setText(f"{m:02d}:{s:02d} / {tm:02d}:{ts:02d}")

    def _on_tts_error(self, err: str):
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_error", error=err[:40]))
        self.waveform.set_active(False)
        QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_status_error", error=err))

    def retranslate_ui(self):
        if hasattr(self, 'lbl_canvas_title'):
            self.lbl_canvas_title.setText(LanguageManager.tr("tts_reading_canvas_title"))
        if hasattr(self, '_update_text_stats'):
            self._update_text_stats()
        if hasattr(self, 'btn_read_page'):
            self.btn_read_page.setText(" " + LanguageManager.tr("tts_read_page_short"))
            self.btn_read_page.setToolTip(LanguageManager.tr("tts_read_page"))
        if hasattr(self, 'btn_read_all'):
            self.btn_read_all.setText(" " + LanguageManager.tr("tts_read_all_short"))
            self.btn_read_all.setToolTip(LanguageManager.tr("tts_read_all"))
        if hasattr(self, 'btn_read_selection'):
            self.btn_read_selection.setText(" " + LanguageManager.tr("tts_read_selection_short"))
            self.btn_read_selection.setToolTip(LanguageManager.tr("tts_read_selection"))
        if hasattr(self, 'btn_page_prev'):
            self.btn_page_prev.setToolTip(LanguageManager.tr("tts_prev_page"))
        if hasattr(self, 'btn_page_next'):
            self.btn_page_next.setToolTip(LanguageManager.tr("tts_next_page"))
        if hasattr(self, 'btn_paste_clipboard'):
            self.btn_paste_clipboard.setToolTip(LanguageManager.tr("tts_paste_clipboard"))
        if hasattr(self, 'btn_export_audio'):
            self.btn_export_audio.setToolTip(LanguageManager.tr("tts_export_audio"))
        if hasattr(self, 'btn_clear_text'):
            self.btn_clear_text.setToolTip(LanguageManager.tr("tts_clear_text"))
        if hasattr(self, 'btn_tts_play'):
            if hasattr(self, 'speech_engine') and self.speech_engine.is_speaking():
                self.btn_tts_play.setText(" " + LanguageManager.tr("tts_pause_btn"))
            else:
                self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
        if hasattr(self, 'btn_skip_back'):
            self.btn_skip_back.setToolTip(LanguageManager.tr("tts_skip_back"))
        if hasattr(self, 'btn_prev_chunk'):
            self.btn_prev_chunk.setToolTip(LanguageManager.tr("tts_prev_sentence"))
        if hasattr(self, 'btn_next_chunk'):
            self.btn_next_chunk.setToolTip(LanguageManager.tr("tts_next_sentence"))
        if hasattr(self, 'btn_skip_fwd'):
            self.btn_skip_fwd.setToolTip(LanguageManager.tr("tts_skip_forward"))
        if hasattr(self, 'btn_tts_stop'):
            self.btn_tts_stop.setToolTip(LanguageManager.tr("tts_stop_btn"))
        if hasattr(self, 'btn_download_model'):
            self.btn_download_model.setText(" " + LanguageManager.tr("tts_btn_download_model"))
        if hasattr(self, 'btn_model_info'):
            self.btn_model_info.setToolTip(LanguageManager.tr("tts_model_desc"))
        if hasattr(self, 'header_status_bar'):
            self.header_status_bar.setToolTip(LanguageManager.tr("tts_model_desc"))
        if hasattr(self, 'btn_speed'):
            self.btn_speed.setToolTip(LanguageManager.tr("tts_speed"))
        if hasattr(self, '_speed_actions'):
            for sval, act in self._speed_actions.items():
                act.setText(LanguageManager.tr("tts_speed_val", val=sval))
        if hasattr(self, 'txt_tts_input'):
            self.txt_tts_input.setPlaceholderText(LanguageManager.tr("tts_no_text_found"))
        self._sync_page_info()
        self._refresh_audio_devices()

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'waveform'):
            self.waveform.set_color(c.get('accent', '#38bdf8'))
        if hasattr(self, 'lbl_canvas_icon'):
            self.lbl_canvas_icon.setPixmap(ModernIconFactory.icon_reading_mode(c.get('accent', '#38bdf8')).pixmap(13, 13))
        if hasattr(self, 'btn_download_model'):
            self.btn_download_model.setIcon(ModernIconFactory.icon_recovery(c['accent']))
        if hasattr(self, 'btn_model_info'):
            self.btn_model_info.setIcon(ModernIconFactory.icon_info(c['text_muted']))
        if hasattr(self, 'btn_page_prev'):
            self.btn_page_prev.setIcon(ModernIconFactory.icon_chevron_left(c['text']))
        if hasattr(self, 'btn_page_next'):
            self.btn_page_next.setIcon(ModernIconFactory.icon_chevron_right(c['text']))
        if hasattr(self, 'btn_read_page'):
            self.btn_read_page.setIcon(ModernIconFactory.icon_view_single(c['accent']))
        if hasattr(self, 'btn_read_all'):
            self.btn_read_all.setIcon(ModernIconFactory.icon_organize(c['text']))
        if hasattr(self, 'btn_read_selection'):
            self.btn_read_selection.setIcon(ModernIconFactory.icon_cursor(c['text']))
        if hasattr(self, 'btn_paste_clipboard'):
            self.btn_paste_clipboard.setIcon(ModernIconFactory.icon_paste(c['text']))
        if hasattr(self, 'btn_export_audio'):
            self.btn_export_audio.setIcon(ModernIconFactory.icon_export_audio(c['text']))
        if hasattr(self, 'btn_clear_text'):
            self.btn_clear_text.setIcon(ModernIconFactory.icon_trash(c.get('danger', '#ef4444')))
        if hasattr(self, 'btn_skip_back'):
            self.btn_skip_back.setIcon(ModernIconFactory.icon_skip_back(c['text']))
        if hasattr(self, 'btn_prev_chunk'):
            self.btn_prev_chunk.setIcon(ModernIconFactory.icon_media_prev(c['text']))
        if hasattr(self, 'btn_next_chunk'):
            self.btn_next_chunk.setIcon(ModernIconFactory.icon_media_next(c['text']))
        if hasattr(self, 'btn_skip_fwd'):
            self.btn_skip_fwd.setIcon(ModernIconFactory.icon_skip_forward(c['text']))
        if hasattr(self, 'btn_tts_stop'):
            self.btn_tts_stop.setIcon(ModernIconFactory.icon_stop(c.get('danger', '#ef4444')))
        if hasattr(self, 'btn_speed'):
            self.btn_speed.setIcon(ModernIconFactory.icon_speed(c['accent']))
        self._refresh_audio_devices()


class ModernRightSidebar(QWidget):
    """
    Ekranın sağındaki çekmece panel (Yer İmleri ve Adobe benzeri Yorumlar paneli):
    - Yer İmleri: İçindekiler hiyerarşisi, hızlı sayfa atlama, yeni yer imi ekleme.
    - Yorumlar: Belgedeki tüm PDF ek açıklamaları/yorumları, arama, yeni not/yorum ekleme, silme.
    """
    closeRequested = pyqtSignal()
    bookmarkClicked = pyqtSignal(int)
    thumbnailClicked = pyqtSignal(int)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"
        self.current_panel = "thumbnails"
        self._current_thumb_doc = None
        self._thumb_render_queue = []
        self._rendered_pages = set()
        self._raw_thumb_images = {}
        self.is_loaded = False
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self.MIN_WIDTH = 180
        self.MAX_WIDTH = 550
        self.DEFAULT_WIDTH = 250
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_width = settings.value("sidebar_panel_width", self.DEFAULT_WIDTH, type=int)
        if saved_width < self.MIN_WIDTH or saved_width > self.MAX_WIDTH:
            saved_width = self.DEFAULT_WIDTH
        self.setFixedWidth(saved_width)

        self._is_resizing = False
        self._resize_start_x = 0
        self._resize_start_w = saved_width
        self._hovering_resize_edge = False
        self.setMouseTracking(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(4, 0, 4, 2)

        self.lbl_head_icon = QLabel()
        self.lbl_head_icon.setPixmap(ModernIconFactory.icon_thumbnails().pixmap(16, 16))
        h_head.addWidget(self.lbl_head_icon)

        self.lbl_head_title = QLabel(LanguageManager.tr("dock_title"))
        self.lbl_head_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(self.lbl_head_title)
        h_head.addStretch(1)

        self.btn_add = QToolButton()
        self.btn_add.setIcon(ModernIconFactory.icon_plus("#ffffff"))
        self.btn_add.setIconSize(QSize(16, 16))
        self.btn_add.setFixedSize(28, 28)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_page"))
        self.btn_add.setStyleSheet("""
            QToolButton {
                background-color: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: rgba(56, 189, 248, 0.3);
                border: 1px solid rgba(56, 189, 248, 0.5);
            }
        """)
        self.btn_add.clicked.connect(self._on_header_add_clicked)
        h_head.addWidget(self.btn_add)

        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Yatay Sekme Çubuğu (Sayfalar, İçindekiler, Ekler, Yorumlar)
        self.tab_container = QWidget()
        self.tab_container.setObjectName("SidebarTabContainer")
        h_tabs = QHBoxLayout(self.tab_container)
        h_tabs.setContentsMargins(0, 2, 0, 4)
        h_tabs.setSpacing(2)

        self.btn_tab_thumbs = QToolButton()
        self.btn_tab_thumbs.setProperty("class", "SidebarTabButton")
        self.btn_tab_thumbs.setIcon(ModernIconFactory.icon_thumbnails())
        self.btn_tab_thumbs.setIconSize(QSize(14, 14))
        self.btn_tab_thumbs.setText(" " + LanguageManager.tr("sidebar_thumbnails"))
        self.btn_tab_thumbs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_thumbs.setCheckable(True)
        self.btn_tab_thumbs.setChecked(True)
        self.btn_tab_thumbs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_thumbs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h_tabs.addWidget(self.btn_tab_thumbs)

        self.btn_tab_bookmarks = QToolButton()
        self.btn_tab_bookmarks.setProperty("class", "SidebarTabButton")
        self.btn_tab_bookmarks.setIcon(ModernIconFactory.icon_bookmark())
        self.btn_tab_bookmarks.setIconSize(QSize(14, 14))
        self.btn_tab_bookmarks.setText(" " + LanguageManager.tr("sidebar_bookmarks"))
        self.btn_tab_bookmarks.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_bookmarks.setCheckable(True)
        self.btn_tab_bookmarks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_bookmarks.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h_tabs.addWidget(self.btn_tab_bookmarks)

        self.btn_tab_attachments = QToolButton()
        self.btn_tab_attachments.setProperty("class", "SidebarTabButton")
        self.btn_tab_attachments.setIcon(ModernIconFactory.icon_attachment())
        self.btn_tab_attachments.setIconSize(QSize(14, 14))
        self.btn_tab_attachments.setText(" " + LanguageManager.tr("sidebar_attachments"))
        self.btn_tab_attachments.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_attachments.setCheckable(True)
        self.btn_tab_attachments.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_attachments.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h_tabs.addWidget(self.btn_tab_attachments)

        self.btn_tab_comments = QToolButton()
        self.btn_tab_comments.setProperty("class", "SidebarTabButton")
        self.btn_tab_comments.setIcon(ModernIconFactory.icon_comments())
        self.btn_tab_comments.setIconSize(QSize(14, 14))
        self.btn_tab_comments.setText(" " + LanguageManager.tr("sidebar_comments"))
        self.btn_tab_comments.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_comments.setCheckable(True)
        self.btn_tab_comments.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_comments.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h_tabs.addWidget(self.btn_tab_comments)

        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.btn_tab_thumbs, 0)
        self.nav_button_group.addButton(self.btn_tab_bookmarks, 1)
        self.nav_button_group.addButton(self.btn_tab_attachments, 2)
        self.nav_button_group.addButton(self.btn_tab_comments, 3)

        self.btn_tab_thumbs.clicked.connect(lambda: self.set_panel("thumbnails"))
        self.btn_tab_bookmarks.clicked.connect(lambda: self.set_panel("bookmarks"))
        self.btn_tab_attachments.clicked.connect(lambda: self.set_panel("attachments"))
        self.btn_tab_comments.clicked.connect(lambda: self.set_panel("comments"))

        main_layout.addWidget(self.tab_container)
        self.tab_container.hide()

        # Ana Panel Yığını: 0=Yer İmleri, 1=Yorumlar, 2=Küçük Resimler
        self.main_stack = QStackedWidget()

        # ======================================================================
        # PANEL 0: YER İMLERİ
        # ======================================================================
        self.panel_bookmarks = QWidget()
        v_bm = QVBoxLayout(self.panel_bookmarks)
        v_bm.setContentsMargins(0, 0, 0, 0)
        v_bm.setSpacing(6)

        self.stack = QStackedWidget()

        # Görünüm 0: Yer İmleri Boş Durumu
        self.empty_widget = QWidget()
        v_empty = QVBoxLayout(self.empty_widget)
        v_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty.setSpacing(12)

        lbl_big_icon = QLabel()
        lbl_big_icon.setPixmap(ModernIconFactory.icon_bookmark("#94a3b8").pixmap(36, 36))
        lbl_big_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty.addWidget(lbl_big_icon)

        self.lbl_empty_msg = QLabel(LanguageManager.tr("bookmarks_empty_title"))
        self.lbl_empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_msg.setStyleSheet("font-size: 13px; font-weight: 500;")
        v_empty.addWidget(self.lbl_empty_msg)

        self.stack.addWidget(self.empty_widget)

        # Görünüm 1: Yer İmleri Ağacı
        self.tree_bookmarks = QTreeWidget()
        self.tree_bookmarks.setColumnCount(2)
        self.tree_bookmarks.setHeaderHidden(True)
        self.tree_bookmarks.header().setStretchLastSection(False)
        self.tree_bookmarks.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_bookmarks.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_bookmarks.itemClicked.connect(self._on_tree_item_clicked)
        self.stack.addWidget(self.tree_bookmarks)

        v_bm.addWidget(self.stack)
        self.main_stack.addWidget(self.panel_bookmarks)

        # ======================================================================
        # PANEL 1: ADOBE TARZI YORUMLAR PANELİ
        # ======================================================================
        self.panel_comments = QWidget()
        v_com = QVBoxLayout(self.panel_comments)
        v_com.setContentsMargins(0, 0, 0, 0)
        v_com.setSpacing(8)

        # Arama / Filtre Kutusu
        self.txt_filter_comments = QLineEdit()
        self.txt_filter_comments.setPlaceholderText(LanguageManager.tr("comments_filter_placeholder"))
        self.txt_filter_comments.setFixedHeight(30)
        self.txt_filter_comments.textChanged.connect(self._filter_comments)
        v_com.addWidget(self.txt_filter_comments)

        # Yeni Yorum Ekle Kartı
        self.card_new_comment = QFrame()
        self.card_new_comment.setObjectName("NewCommentCard")
        l_new_c = QVBoxLayout(self.card_new_comment)
        l_new_c.setContentsMargins(8, 8, 8, 8)
        l_new_c.setSpacing(6)

        self.txt_new_comment = QTextEdit()
        self.txt_new_comment.setPlaceholderText(LanguageManager.tr("comments_input_placeholder"))
        self.txt_new_comment.setFixedHeight(56)
        l_new_c.addWidget(self.txt_new_comment)

        h_post = QHBoxLayout()
        h_post.addStretch(1)
        self.btn_post_comment = QPushButton(LanguageManager.tr("comments_post_btn"))
        self.btn_post_comment.setObjectName("PostCommentBtn")
        self.btn_post_comment.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_post_comment.clicked.connect(self._add_comment_action)
        h_post.addWidget(self.btn_post_comment)
        l_new_c.addLayout(h_post)

        v_com.addWidget(self.card_new_comment)

        # Yorum Listesi Yığını (Boş Durum vs Ağaç)
        self.comments_stack = QStackedWidget()

        # Boş Durum
        self.empty_comments_widget = QWidget()
        v_empty_c = QVBoxLayout(self.empty_comments_widget)
        v_empty_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_c.setSpacing(8)

        lbl_com_empty_icon = QLabel()
        lbl_com_empty_icon.setPixmap(ModernIconFactory.icon_comments("#94a3b8").pixmap(36, 36))
        lbl_com_empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_c.addWidget(lbl_com_empty_icon)

        self.lbl_empty_comments = QLabel(LanguageManager.tr("comments_no_comments"))
        self.lbl_empty_comments.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_comments.setStyleSheet("font-size: 13px; font-weight: 600;")
        v_empty_c.addWidget(self.lbl_empty_comments)

        self.lbl_empty_comments_desc = QLabel(LanguageManager.tr("comments_no_comments_desc"))
        self.lbl_empty_comments_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_comments_desc.setWordWrap(True)
        self.lbl_empty_comments_desc.setStyleSheet("font-size: 11px; opacity: 0.7;")
        v_empty_c.addWidget(self.lbl_empty_comments_desc)

        self.comments_stack.addWidget(self.empty_comments_widget)

        # Yorum Ağacı
        self.tree_comments = QTreeWidget()
        self.tree_comments.setHeaderHidden(True)
        self.tree_comments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_comments.customContextMenuRequested.connect(self._on_comment_context_menu)
        self.tree_comments.itemClicked.connect(self._on_comment_item_clicked)
        self.tree_comments.itemDoubleClicked.connect(self._on_comment_item_double_clicked)
        self.comments_stack.addWidget(self.tree_comments)

        v_com.addWidget(self.comments_stack, stretch=1)
        self.main_stack.addWidget(self.panel_comments)

        # ======================================================================
        # PANEL 2: SAYFA KÜÇÜK RESİMLERİ (THUMBNAILS)
        # ======================================================================
        self.panel_thumbnails = QWidget()
        v_th = QVBoxLayout(self.panel_thumbnails)
        v_th.setContentsMargins(0, 0, 0, 0)
        v_th.setSpacing(6)

        self.stack_thumbnails = QStackedWidget()

        # Boş Durum
        self.empty_thumbs_widget = QWidget()
        self.empty_thumbs_widget.setAcceptDrops(True)
        self.empty_thumbs_widget.installEventFilter(self)
        v_empty_th = QVBoxLayout(self.empty_thumbs_widget)
        v_empty_th.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_th.setSpacing(10)

        lbl_th_icon = QLabel()
        lbl_th_icon.setPixmap(ModernIconFactory.icon_thumbnails("#94a3b8").pixmap(40, 40))
        lbl_th_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_th.addWidget(lbl_th_icon)

        self.lbl_empty_thumbs = QLabel(LanguageManager.tr("sidebar_no_pages_title"))
        self.lbl_empty_thumbs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_thumbs.setStyleSheet("font-size: 13px; font-weight: 600;")
        v_empty_th.addWidget(self.lbl_empty_thumbs)

        self.lbl_empty_desc = QLabel(LanguageManager.tr("sidebar_no_pages_desc"))
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_desc.setStyleSheet("font-size: 11px; opacity: 0.7;")
        v_empty_th.addWidget(self.lbl_empty_desc)

        self.btn_empty_insert_pdf = QPushButton(" " + LanguageManager.tr("sidebar_btn_add_pdf"))
        self.btn_empty_insert_pdf.setObjectName("PrimaryActionBtn")
        self.btn_empty_insert_pdf.setIcon(ModernIconFactory.icon_new_document("#ffffff"))
        self.btn_empty_insert_pdf.setIconSize(QSize(14, 14))
        self.btn_empty_insert_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_insert_pdf.clicked.connect(lambda: self._on_add_pdf_clicked())
        v_empty_th.addWidget(self.btn_empty_insert_pdf)

        self.btn_empty_add_blank = QPushButton(" " + LanguageManager.tr("sidebar_btn_add_blank"))
        self.btn_empty_add_blank.setObjectName("PrimaryActionBtn")
        self.btn_empty_add_blank.setIcon(ModernIconFactory.icon_add_page("#ffffff"))
        self.btn_empty_add_blank.setIconSize(QSize(14, 14))
        self.btn_empty_add_blank.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_add_blank.clicked.connect(lambda: self._on_add_blank_page_clicked())
        v_empty_th.addWidget(self.btn_empty_add_blank)

        self.stack_thumbnails.addWidget(self.empty_thumbs_widget)

        # Sayfalar (Küçük Resimler) Listesi
        self.list_thumbnails = QListWidget()
        self.list_thumbnails.setObjectName("RightRailThumbnailsList")
        self.list_thumbnails.setIconSize(QSize(140, 190))
        self.list_thumbnails.setSpacing(6)
        self.list_thumbnails.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_thumbnails.setAcceptDrops(True)
        self.list_thumbnails.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_thumbnails.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_thumbnails.model().rowsMoved.connect(self._on_pages_reordered)
        self.list_thumbnails.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_thumbnails.customContextMenuRequested.connect(self._show_thumbnails_context_menu)
        self.list_thumbnails.itemClicked.connect(self._on_thumbnail_item_clicked)
        self.list_thumbnails.setMouseTracking(True)
        self.list_thumbnails.viewport().setMouseTracking(True)
        self.list_thumbnails.installEventFilter(self)
        self.list_thumbnails.viewport().installEventFilter(self)
        self.stack_thumbnails.addWidget(self.list_thumbnails)

        v_th.addWidget(self.stack_thumbnails)
        self.main_stack.addWidget(self.panel_thumbnails)

        # ======================================================================
        # PANEL 3: EKLER (ATTACHMENTS)
        # ======================================================================
        self.panel_attachments = QWidget()
        v_att = QVBoxLayout(self.panel_attachments)
        v_att.setContentsMargins(0, 0, 0, 0)
        v_att.setSpacing(6)

        self.stack_attachments = QStackedWidget()

        # Görünüm 0: Ekler Boş Durumu
        self.empty_att_widget = QWidget()
        v_empty_att = QVBoxLayout(self.empty_att_widget)
        v_empty_att.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_att.setSpacing(12)

        lbl_att_icon = QLabel()
        lbl_att_icon.setPixmap(ModernIconFactory.icon_attachment("#94a3b8").pixmap(36, 36))
        lbl_att_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_empty_att.addWidget(lbl_att_icon)

        self.lbl_empty_att = QLabel(LanguageManager.tr("sidebar_no_attachments"))
        self.lbl_empty_att.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_att.setStyleSheet("font-size: 13px; font-weight: 500;")
        v_empty_att.addWidget(self.lbl_empty_att)

        self.empty_att_btn = QPushButton(" " + LanguageManager.tr("sidebar_add_attachment"))
        self.empty_att_btn.setIcon(ModernIconFactory.icon_plus())
        self.empty_att_btn.setObjectName("PrimaryActionBtn")
        self.empty_att_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_att_btn.clicked.connect(self._add_attachment_action)
        v_empty_att.addWidget(self.empty_att_btn)

        self.stack_attachments.addWidget(self.empty_att_widget)

        # Görünüm 1: Ekler Listesi
        self.list_attachments = QListWidget()
        self.list_attachments.setObjectName("RightRailAttachmentsList")
        self.list_attachments.setSpacing(4)
        self.list_attachments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_attachments.customContextMenuRequested.connect(self._show_attachment_context_menu)
        self.list_attachments.itemDoubleClicked.connect(self._on_attachment_double_clicked)
        self.stack_attachments.addWidget(self.list_attachments)

        v_att.addWidget(self.stack_attachments)
        self.main_stack.addWidget(self.panel_attachments)

        # 4. Panel: Erişilebilirlik ve Sesli Okuma (TTS)
        self.panel_accessibility = ModernAccessibilityPanel(main_window=self.main_window, parent=self)
        self.speech_engine = self.panel_accessibility.speech_engine
        self.main_stack.addWidget(self.panel_accessibility)

        main_layout.addWidget(self.main_stack, stretch=1)
        self.apply_theme(self.theme_name)

    def set_panel(self, panel_name: str):
        """Çekmeceyi 'thumbnails', 'bookmarks', 'attachments', 'comments' veya 'accessibility' paneline geçirir."""
        self.current_panel = panel_name
        if panel_name == "accessibility":
            self.tab_container.hide()
            self.main_stack.setCurrentIndex(4)
            self.lbl_head_title.setText(LanguageManager.tr("accessibility_panel_title"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_accessibility().pixmap(16, 16))
            self.btn_add.hide()
            self.setFixedWidth(270)
            self.panel_accessibility.load_accessibility()
            return

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        if panel_name == "comments":
            self.tab_container.hide()
            self.btn_tab_comments.setChecked(True)
            self.main_stack.setCurrentIndex(1)
            self.lbl_head_title.setText(LanguageManager.tr("sidebar_comments"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_comments().pixmap(16, 16))
            self.btn_add.hide()
            self.load_comments()
        elif panel_name == "thumbnails":
            self.tab_container.hide()
            self.btn_tab_thumbs.setChecked(True)
            self.main_stack.setCurrentIndex(2)
            self.lbl_head_title.setText(LanguageManager.tr("sidebar_thumbnails"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_thumbnails().pixmap(16, 16))
            self.btn_add.show()
            self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_page"))
            self.load_thumbnails()
        elif panel_name == "attachments":
            self.tab_container.hide()
            self.btn_tab_attachments.setChecked(True)
            self.main_stack.setCurrentIndex(3)
            self.lbl_head_title.setText(LanguageManager.tr("sidebar_attachments"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_attachment().pixmap(16, 16))
            self.btn_add.show()
            self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_attachment"))
            self.load_attachments()
        else:
            self.tab_container.hide()
            self.btn_tab_bookmarks.setChecked(True)
            self.main_stack.setCurrentIndex(0)
            self.lbl_head_title.setText(LanguageManager.tr("sidebar_bookmarks"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_bookmark().pixmap(16, 16))
            self.btn_add.show()
            self.btn_add.setToolTip(LanguageManager.tr("bookmarks_add_btn"))
            self.load_bookmarks()

    def retranslate_ui(self):
        if hasattr(self, 'btn_tab_thumbs'):
            self.btn_tab_thumbs.setText(" " + LanguageManager.tr("sidebar_thumbnails"))
            self.btn_tab_bookmarks.setText(" " + LanguageManager.tr("sidebar_bookmarks"))
            self.btn_tab_attachments.setText(" " + LanguageManager.tr("sidebar_attachments"))
            self.btn_tab_comments.setText(" " + LanguageManager.tr("sidebar_comments"))

        panel_title_map = {
            "thumbnails": "sidebar_thumbnails",
            "bookmarks": "sidebar_bookmarks",
            "comments": "sidebar_comments",
            "attachments": "sidebar_attachments",
            "accessibility": "accessibility_panel_title",
        }
        title_key = panel_title_map.get(getattr(self, 'current_panel', 'bookmarks'), "sidebar_bookmarks")
        self.lbl_head_title.setText(LanguageManager.tr(title_key))

        self.lbl_empty_msg.setText(LanguageManager.tr("bookmarks_empty_title"))
        self.lbl_empty_comments.setText(LanguageManager.tr("comments_no_comments"))
        self.lbl_empty_comments_desc.setText(LanguageManager.tr("comments_no_comments_desc"))
        if hasattr(self, 'lbl_empty_thumbs'):
            self.lbl_empty_thumbs.setText(LanguageManager.tr("sidebar_no_pages_title"))
        if hasattr(self, 'btn_empty_insert_pdf'):
            self.btn_empty_insert_pdf.setText(" " + LanguageManager.tr("sidebar_btn_add_pdf"))
        if hasattr(self, 'btn_empty_add_blank'):
            self.btn_empty_add_blank.setText(" " + LanguageManager.tr("sidebar_btn_add_blank"))
        if hasattr(self, 'lbl_empty_att'):
            self.lbl_empty_att.setText(LanguageManager.tr("sidebar_no_attachments"))
        if hasattr(self, 'empty_att_btn'):
            self.empty_att_btn.setText(" " + LanguageManager.tr("sidebar_add_attachment"))
        self.txt_filter_comments.setPlaceholderText(LanguageManager.tr("comments_filter_placeholder"))
        self.txt_new_comment.setPlaceholderText(LanguageManager.tr("comments_input_placeholder"))
        self.btn_post_comment.setText(LanguageManager.tr("comments_post_btn"))
        if hasattr(self, 'btn_add'):
            if self.current_panel == "attachments":
                self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_attachment"))
            elif self.current_panel == "thumbnails":
                self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_page"))
            else:
                self.btn_add.setToolTip(LanguageManager.tr("bookmarks_add_btn"))
        if hasattr(self, 'panel_accessibility'):
            self.panel_accessibility.retranslate_ui()

    # ==========================================================================
    # SAYFA KÜÇÜK RESİMLERİ (THUMBNAILS) İŞLEMLERİ
    # ==========================================================================
    def _is_pos_on_bookmark_ribbon(self, pos: QPoint) -> tuple:
        item = self.list_thumbnails.itemAt(pos)
        if not item:
            return False, None, -1
        page_idx = item.data(Qt.ItemDataRole.UserRole)
        if page_idx is None or page_idx < 0:
            return False, item, -1

        bookmarked_pages = self.get_bookmarked_pages()
        if page_idx not in bookmarked_pages:
            return False, item, page_idx

        item_rect = self.list_thumbnails.visualItemRect(item)
        opt = QStyleOptionViewItem()
        self.list_thumbnails.initViewItemOption(opt)
        opt.rect = item_rect
        opt.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration
        opt.decorationSize = self.list_thumbnails.iconSize()

        style = self.list_thumbnails.style()
        icon_rect = style.subElementRect(style.SubElement.SE_ItemViewItemDecoration, opt, self.list_thumbnails)

        ribbon_hit_rect = QRect(icon_rect.right() - 32, icon_rect.top() - 2, 34, 38)
        if ribbon_hit_rect.contains(pos):
            return True, item, page_idx
        return False, item, page_idx

    def eventFilter(self, source, event):
        if hasattr(self, 'list_thumbnails') and source == self.list_thumbnails.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                is_hit, item, page_idx = self._is_pos_on_bookmark_ribbon(event.pos())
                if is_hit and page_idx >= 0:
                    self.show_bookmark_for_page(page_idx)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                is_hit, item, page_idx = self._is_pos_on_bookmark_ribbon(event.pos())
                if is_hit:
                    self.list_thumbnails.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.list_thumbnails.viewport().unsetCursor()
            elif event.type() == QEvent.Type.Leave:
                self.list_thumbnails.viewport().unsetCursor()

        if hasattr(self, 'list_thumbnails') and source in (self.list_thumbnails, getattr(self, 'empty_thumbs_widget', None)):
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
                    if pdf_urls:
                        if self.main_window and hasattr(self.main_window, 'handle_dropped_urls'):
                            self.main_window.handle_dropped_urls(pdf_urls)
                            event.acceptProposedAction()
                            return True
        return super().eventFilter(source, event)

    def _create_placeholder_pixmap(self, is_bookmarked: bool = False) -> QPixmap:
        c = get_modern_theme_colors(self.theme_name)
        pix = QPixmap(140, 190)
        pix.fill(QColor(c.get('card_bg', '#242426')))
        if is_bookmarked:
            return self._draw_bookmark_ribbon_badge(pix)
        return pix

    def load_thumbnails(self):
        """Aktif belgenin sayfa küçük resimlerini yükler."""
        if not self.main_window:
            self.stack_thumbnails.setCurrentIndex(0)
            self.is_loaded = False
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or getattr(tab_doc.doc, 'is_closed', False) or len(tab_doc.doc) == 0:
            self.stack_thumbnails.setCurrentIndex(0)
            self.is_loaded = False
            return

        total_pages = len(tab_doc.doc)
        curr_idx = getattr(tab_doc, 'current_page_idx', 0)

        # Hızlı yol: aynı belge ve aynı sayfa sayısı yüklüyse sadece aktif sayfayı seç ve güncelle
        if getattr(self, '_current_thumb_doc', None) == tab_doc and self.list_thumbnails.count() == total_pages:
            self.stack_thumbnails.setCurrentIndex(1)
            self._render_thumbnail_page(tab_doc, curr_idx)
            self.select_page(curr_idx)
            self.is_loaded = True
            return

        self._thumb_timer.stop()
        self.list_thumbnails.clear()
        self._thumb_render_queue.clear()
        self._rendered_pages.clear()
        self._raw_thumb_images.clear()
        self._current_thumb_doc = tab_doc
        self.stack_thumbnails.setCurrentIndex(1)

        # Boş yer tutucuları anında ekle (<1ms)
        bookmarked_pages = self.get_bookmarked_pages()
        thumb_w = max(75, min(140, self.width() - 36))
        thumb_h = int(thumb_w * 1.38)
        hint_size = QSize(thumb_w + 14, thumb_h + 26)
        for idx in range(total_pages):
            is_bm = idx in bookmarked_pages
            placeholder_pix = self._create_placeholder_pixmap(is_bm)
            item = QListWidgetItem(QIcon(placeholder_pix), f"{idx + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setSizeHint(hint_size)
            if is_bm:
                item.setToolTip(LanguageManager.tr("sidebar_page_bookmarked", page=idx + 1))
            else:
                item.setToolTip(LanguageManager.tr("sidebar_page_tooltip", page=idx + 1))
            self.list_thumbnails.addItem(item)

        self._adapt_to_width(self.width())
        self.is_loaded = True

        # Aktif sayfa ve yakın komşuları öncelikli çiz
        immediate = [curr_idx]
        for offset in (1, -1, 2, -2):
            p = curr_idx + offset
            if 0 <= p < total_pages:
                immediate.append(p)

        for p in immediate:
            self._render_thumbnail_page(tab_doc, p)

        self.select_page(curr_idx)

        # Kalan sayfaları mesafeye göre sıralı kuyruğa al
        remaining = [p for p in range(total_pages) if p not in immediate]
        remaining.sort(key=lambda p: abs(p - curr_idx))
        self._thumb_render_queue = remaining

        if self._thumb_render_queue:
            self._thumb_timer.start(10)

    def load_thumbnails_lazy(self):
        """ThumbnailsDock ile tam uyumluluk sağlayan takma ad."""
        self.load_thumbnails()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, 'current_panel', '') == "thumbnails":
            self.load_thumbnails()
        elif getattr(self, 'current_panel', '') == "comments":
            self.load_comments()

    def hideEvent(self, event):
        super().hideEvent(event)
        try:
            self._thumb_timer.stop()
            self._thumb_render_queue.clear()
        except Exception:
            pass

    def clear_thumbnails(self):
        try:
            self._thumb_timer.stop()
            self._thumb_render_queue.clear()
        except Exception:
            pass
        self._current_thumb_doc = None
        self._rendered_pages.clear()
        self._raw_thumb_images.clear()
        self.is_loaded = False
        if hasattr(self, 'list_thumbnails'):
            self.list_thumbnails.clear()
        if hasattr(self, 'stack_thumbnails'):
            self.stack_thumbnails.setCurrentIndex(0)

    def get_bookmarked_pages(self) -> set:
        if not self.main_window:
            return set()
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return set()
        try:
            toc = tab_doc.doc.get_toc(simple=False)
            return {
                entry[2] - 1 for entry in toc
                if len(entry) > 2 and isinstance(entry[2], int) and entry[2] >= 1
            }
        except Exception:
            return set()

    def _draw_bookmark_ribbon_badge(self, base_pixmap: QPixmap) -> QPixmap:
        pix = base_pixmap.copy()
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rw = 16.0
        rh = 24.0
        rnotch = 5.5
        rx = max(0.0, float(pix.width()) - rw - 5.0)
        ry = 0.0

        shadow_path = QPainterPath()
        shadow_path.moveTo(rx + 1.0, ry + 1.0)
        shadow_path.lineTo(rx + rw + 1.0, ry + 1.0)
        shadow_path.lineTo(rx + rw + 1.0, ry + rh + 1.5)
        shadow_path.lineTo(rx + rw / 2.0 + 1.0, ry + rh - rnotch + 1.5)
        shadow_path.lineTo(rx + 1.0, ry + rh + 1.5)
        shadow_path.closeSubpath()
        painter.fillPath(shadow_path, QColor(0, 0, 0, 80))

        ribbon_path = QPainterPath()
        ribbon_path.moveTo(rx, ry)
        ribbon_path.lineTo(rx + rw, ry)
        ribbon_path.lineTo(rx + rw, ry + rh)
        ribbon_path.lineTo(rx + rw / 2.0, ry + rh - rnotch)
        ribbon_path.lineTo(rx, ry + rh)
        ribbon_path.closeSubpath()

        grad = QLinearGradient(rx, ry, rx + rw, ry + rh)
        grad.setColorAt(0.0, QColor("#fb7185"))
        grad.setColorAt(0.45, QColor("#ef4444"))
        grad.setColorAt(1.0, QColor("#be123c"))

        painter.setPen(QPen(QColor("#881337"), 1.0))
        painter.setBrush(QBrush(grad))
        painter.drawPath(ribbon_path)

        painter.setPen(QPen(QColor(255, 255, 255, 160), 1.0))
        painter.drawLine(QPointF(rx + 1, ry + 0.5), QPointF(rx + rw - 1, ry + 0.5))

        iw = 6.6
        ih = 8.8
        inot = 2.2
        ix = rx + (rw - iw) / 2.0
        iy = ry + 4.0
        ipath = QPainterPath()
        ipath.moveTo(ix, iy)
        ipath.lineTo(ix + iw, iy)
        ipath.lineTo(ix + iw, iy + ih)
        ipath.lineTo(ix + iw / 2.0, iy + ih - inot)
        ipath.lineTo(ix, iy + ih)
        ipath.closeSubpath()

        painter.setPen(QPen(QColor(255, 255, 255, 235), 0.9))
        painter.setBrush(QBrush(QColor(255, 255, 255, 75)))
        painter.drawPath(ipath)

        painter.end()
        return pix

    def _render_thumbnail_page(self, tab_doc, page_idx: int):
        if not tab_doc or not tab_doc.doc or getattr(tab_doc.doc, 'is_closed', False):
            return
        if page_idx < 0 or page_idx >= len(tab_doc.doc):
            return
        if page_idx >= self.list_thumbnails.count():
            return
        item = self.list_thumbnails.item(page_idx)
        if not item:
            return

        thumb_w = 140
        img = None

        # 1. Canlı çizimlerle (çizim, not, vurgulayıcı, şekiller vb.) render et
        if hasattr(tab_doc, 'page_positions') and page_idx in tab_doc.page_positions:
            pinfo = tab_doc.page_positions[page_idx]
            thumb_h = max(20, int(thumb_w * (pinfo['height'] / max(1.0, pinfo['width']))))

            laser = getattr(tab_doc, 'laser_pointer_item', None)
            was_laser_vis = laser.isVisible() if laser else False
            if laser and was_laser_vis:
                laser.setVisible(False)

            sel_item = getattr(tab_doc, 'selection_item', None)
            was_sel_vis = sel_item.isVisible() if sel_item else False
            if sel_item and was_sel_vis:
                sel_item.setVisible(False)

            ribbon = getattr(tab_doc, 'bookmark_ribbon_items', {}).get(page_idx, None)
            was_ribbon_vis = ribbon.isVisible() if ribbon else False
            if ribbon and was_ribbon_vis:
                ribbon.setVisible(False)

            selected_items = tab_doc.scene.selectedItems() if hasattr(tab_doc, 'scene') and tab_doc.scene else []
            for sit in selected_items:
                sit.setSelected(False)

            src_rect = QRectF(pinfo.get('left', 0), pinfo['top'], pinfo['width'], pinfo['height'])

            try:
                if pinfo.get('item') and not pinfo['item'].pixmap().isNull():
                    img = QImage(thumb_w, thumb_h, QImage.Format.Format_ARGB32_Premultiplied)
                    img.fill(QColor(255, 255, 255))
                    painter = QPainter(img)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    tab_doc.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                    painter.end()
                else:
                    page = tab_doc.doc[page_idx]
                    pw = max(1.0, page.rect.width)
                    scale = float(thumb_w) / pw
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    base_img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                    img = base_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)

                    bg_rect = pinfo.get('bg_rect')
                    was_bg_vis = bg_rect.isVisible() if bg_rect else False
                    if bg_rect and was_bg_vis:
                        bg_rect.setVisible(False)
                    pix_item = pinfo.get('item')
                    was_pix_vis = pix_item.isVisible() if pix_item else False
                    if pix_item and was_pix_vis:
                        pix_item.setVisible(False)

                    painter = QPainter(img)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    try:
                        tab_doc.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                    finally:
                        painter.end()
                        if bg_rect and was_bg_vis:
                            bg_rect.setVisible(True)
                        if pix_item and was_pix_vis:
                            pix_item.setVisible(True)
            except Exception:
                img = None
            finally:
                if laser and was_laser_vis:
                    laser.setVisible(True)
                if sel_item and was_sel_vis:
                    sel_item.setVisible(True)
                if ribbon and was_ribbon_vis:
                    ribbon.setVisible(True)
                for sit in selected_items:
                    sit.setSelected(True)

        if img is None:
            try:
                page = tab_doc.doc[page_idx]
                pw = max(1.0, page.rect.width)
                ph = max(1.0, page.rect.height)
                thumb_h = max(20, int(thumb_w * (ph / pw)))
                scale = float(thumb_w) / pw
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                base_img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                img = base_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            except Exception:
                return

        self._raw_thumb_images[page_idx] = img.copy()

        pixmap = QPixmap.fromImage(img)
        bookmarked_pages = self.get_bookmarked_pages()
        is_bm = page_idx in bookmarked_pages
        if is_bm:
            pixmap = self._draw_bookmark_ribbon_badge(pixmap)
            item.setToolTip(LanguageManager.tr("sidebar_page_bookmarked", page=page_idx + 1))
        else:
            item.setToolTip(LanguageManager.tr("sidebar_page_tooltip", page=page_idx + 1))
        item.setIcon(QIcon(pixmap))
        self._rendered_pages.add(page_idx)

    def _process_thumb_render_queue(self):
        if not self.isVisible() or self.current_panel != "thumbnails" or not self._thumb_render_queue:
            return
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or getattr(tab_doc.doc, 'is_closed', False) or tab_doc != getattr(self, '_current_thumb_doc', None):
            self._thumb_render_queue.clear()
            return

        for _ in range(3):
            if not self._thumb_render_queue:
                break
            p_idx = self._thumb_render_queue.pop(0)
            self._render_thumbnail_page(tab_doc, p_idx)

        if self._thumb_render_queue:
            try:
                self._thumb_timer.start(10)
            except Exception:
                pass

    def _on_thumbnail_item_clicked(self, item: QListWidgetItem):
        page_idx = item.data(Qt.ItemDataRole.UserRole)
        if page_idx is not None:
            self.thumbnailClicked.emit(page_idx)

    def select_page(self, page_idx: int):
        if not hasattr(self, 'list_thumbnails') or self.list_thumbnails.count() == 0:
            return
        if 0 <= page_idx < self.list_thumbnails.count():
            self.list_thumbnails.blockSignals(True)
            self.list_thumbnails.setCurrentRow(page_idx)
            item = self.list_thumbnails.item(page_idx)
            if item:
                self.list_thumbnails.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
            self.list_thumbnails.blockSignals(False)
            if page_idx not in self._rendered_pages:
                tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
                if tab_doc:
                    self._render_thumbnail_page(tab_doc, page_idx)

    def update_thumbnail(self, page_idx: int):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or getattr(tab_doc.doc, 'is_closed', False):
            return
        self._render_thumbnail_page(tab_doc, page_idx)
        if hasattr(self, 'list_thumbnails'):
            self.list_thumbnails.viewport().update()

    def update_all_thumbnails(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or getattr(tab_doc.doc, 'is_closed', False):
            return
        for idx in range(self.list_thumbnails.count()):
            self._render_thumbnail_page(tab_doc, idx)
        if hasattr(self, 'list_thumbnails'):
            self.list_thumbnails.viewport().update()

    def refresh_bookmark_indicators(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        bookmarked_pages = self.get_bookmarked_pages()
        for idx in range(self.list_thumbnails.count()):
            item = self.list_thumbnails.item(idx)
            if not item:
                continue
            is_bm = idx in bookmarked_pages
            if idx in self._raw_thumb_images:
                base_img = self._raw_thumb_images[idx]
                pix = QPixmap.fromImage(base_img)
                if is_bm:
                    pix = self._draw_bookmark_ribbon_badge(pix)
                item.setIcon(QIcon(pix))
            else:
                placeholder_pix = self._create_placeholder_pixmap(is_bm)
                item.setIcon(QIcon(placeholder_pix))

            if is_bm:
                item.setToolTip(LanguageManager.tr("sidebar_page_bookmarked", page=idx + 1))
            else:
                item.setToolTip(LanguageManager.tr("sidebar_page_tooltip", page=idx + 1))
        if hasattr(self, 'list_thumbnails'):
            self.list_thumbnails.viewport().update()

    def _on_pages_reordered(self, parent=None, start=None, end=None, destination=None, row=None):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        new_order = []
        for i in range(self.list_thumbnails.count()):
            it = self.list_thumbnails.item(i)
            new_order.append(it.data(Qt.ItemDataRole.UserRole))
        tab_doc.reorder_pages(new_order, push_undo=True)
        for i in range(self.list_thumbnails.count()):
            self.list_thumbnails.item(i).setData(Qt.ItemDataRole.UserRole, i)
            self.list_thumbnails.item(i).setText(f"{i + 1}")
        self.load_thumbnails()

    def _show_thumbnails_context_menu(self, pos: QPoint):
        item = self.list_thumbnails.itemAt(pos)
        idx = item.data(Qt.ItemDataRole.UserRole) if item else -1
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None

        menu = QMenu(self)
        apply_dialog_theme(menu, self)

        act_goto = None
        act_show_bm = None
        act_rotate_cw = None
        act_rotate_ccw = None
        act_dup = None
        act_del = None
        act_style = None
        act_crop = None
        act_label = None

        if item and idx >= 0:
            act_goto = menu.addAction(ModernIconFactory.icon_cursor(), LanguageManager.tr("sidebar_goto_page", page=idx + 1))
            if idx in self.get_bookmarked_pages():
                act_show_bm = menu.addAction(ModernIconFactory.icon_bookmark(), LanguageManager.tr("sidebar_show_in_toc"))
            menu.addSeparator()
            act_rotate_cw = menu.addAction(ModernIconFactory.icon_rotate(), LanguageManager.tr("sidebar_rotate_cw"))
            act_rotate_ccw = menu.addAction(ModernIconFactory.icon_rotate_ccw(), LanguageManager.tr("sidebar_rotate_ccw"))
            menu.addSeparator()
            act_crop = menu.addAction(ModernIconFactory.icon_crop(), LanguageManager.tr("organize_crop_page_title"))
            act_label = menu.addAction(ModernIconFactory.icon_page_label(), LanguageManager.tr("organize_page_label_title"))
            menu.addSeparator()

        act_blank = menu.addAction(ModernIconFactory.icon_add_page(), LanguageManager.tr("sidebar_btn_add_blank"))
        act_pdf = menu.addAction(ModernIconFactory.icon_new_document(), LanguageManager.tr("sidebar_btn_add_pdf"))

        if item and idx >= 0:
            if hasattr(self.main_window, 'show_change_page_style_dialog'):
                act_style = menu.addAction(ModernIconFactory.icon_brush(), LanguageManager.tr("change_page_style_action"))
            act_dup = menu.addAction(ModernIconFactory.icon_new_document(), LanguageManager.tr("sidebar_duplicate_page"))
            menu.addSeparator()
            act_del = menu.addAction(ModernIconFactory.icon_trash(), LanguageManager.tr("sidebar_delete_page"))

        chosen = menu.exec(self.list_thumbnails.mapToGlobal(pos))
        if not chosen:
            return

        if chosen == act_goto and tab_doc:
            tab_doc.go_to_page(idx)
        elif chosen == act_show_bm and idx >= 0:
            self.show_bookmark_for_page(idx)
        elif chosen == act_rotate_cw and idx >= 0:
            self._rotate_page(idx, 90)
        elif chosen == act_rotate_ccw and idx >= 0:
            self._rotate_page(idx, -90)
        elif chosen == act_crop and idx >= 0 and tab_doc and tab_doc.doc:
            from src.ui.dialogs.page_organize_dialogs import CropPageDialog
            dlg = CropPageDialog(tab_doc.doc, current_page_idx=idx, parent=self.main_window)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                tab_doc.rerender_visible_pages(force=True)
                self.load_thumbnails()
        elif chosen == act_label and idx >= 0 and tab_doc and tab_doc.doc:
            from src.ui.dialogs.page_organize_dialogs import PageLabelDialog
            dlg = PageLabelDialog(tab_doc.doc, selected_pages=[idx], parent=self.main_window)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.load_thumbnails()
        elif chosen == act_blank:
            self._on_add_blank_page_clicked(idx if idx >= 0 else None)
        elif chosen == act_pdf:
            self._on_add_pdf_clicked(idx if idx >= 0 else None)
        elif chosen == act_style and idx >= 0 and hasattr(self.main_window, 'show_change_page_style_dialog'):
            self.main_window.show_change_page_style_dialog(idx)
        elif chosen == act_dup and idx >= 0:
            self._duplicate_page(idx)
        elif chosen == act_del and idx >= 0:
            self._delete_page(idx)

    def _on_add_page_menu_requested(self):
        menu = QMenu(self)
        apply_dialog_theme(menu, self)
        act_blank = menu.addAction(ModernIconFactory.icon_add_page(), LanguageManager.tr("sidebar_btn_add_blank"))
        act_pdf = menu.addAction(ModernIconFactory.icon_new_document(), LanguageManager.tr("sidebar_btn_add_pdf"))
        pos = self.btn_add.mapToGlobal(QPoint(0, self.btn_add.height() + 2)) if hasattr(self, 'btn_add') else QCursor.pos()
        chosen = menu.exec(pos)
        if chosen == act_blank:
            self._on_add_blank_page_clicked()
        elif chosen == act_pdf:
            self._on_add_pdf_clicked()

    def _on_add_blank_page_clicked(self, after_page: Optional[int] = None):
        if self.main_window and hasattr(self.main_window, 'show_new_page_dialog'):
            self.main_window.show_new_page_dialog()
            return

        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        target_after = after_page
        if target_after is None and tab_doc:
            curr_item = self.list_thumbnails.currentItem()
            target_after = curr_item.data(Qt.ItemDataRole.UserRole) if curr_item else getattr(tab_doc, 'current_page_idx', None)

        menu = QMenu(self)
        apply_dialog_theme(menu, self)
        styles = [
            (LanguageManager.tr("template_blank"), "blank"),
            (LanguageManager.tr("template_grid"), "grid"),
            (LanguageManager.tr("template_lines"), "lined"),
            (LanguageManager.tr("template_dotted"), "dotted"),
            (LanguageManager.tr("template_cornell"), "cornell"),
            (LanguageManager.tr("template_cover"), "cover")
        ]
        for name, style_code in styles:
            act = menu.addAction(name)
            act.setData(style_code)

        chosen = menu.exec(QCursor.pos())
        if chosen:
            style = chosen.data()
            if tab_doc and tab_doc.doc is not None:
                tab_doc.insert_blank_page(after_page=target_after, style=style)
                self.load_thumbnails()
                if target_after is not None:
                    tab_doc.go_to_page(target_after + 1)
            elif self.main_window and hasattr(self.main_window, 'new_blank_document'):
                self.main_window.new_blank_document(style)

    def _on_add_pdf_clicked(self, after_page: Optional[int] = None):
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        target_after = after_page
        if target_after is None and tab_doc:
            curr_item = self.list_thumbnails.currentItem()
            target_after = curr_item.data(Qt.ItemDataRole.UserRole) if curr_item else getattr(tab_doc, 'current_page_idx', None)

        if tab_doc and tab_doc.doc is not None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                LanguageManager.tr("sidebar_select_pdf"),
                "",
                LanguageManager.tr("sidebar_pdf_filter")
            )
            if path:
                tab_doc.insert_pdf_at(path, after_page=target_after)
                self.load_thumbnails()
        elif self.main_window:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                LanguageManager.tr("sidebar_select_pdf"),
                "",
                LanguageManager.tr("sidebar_pdf_filter")
            )
            if paths:
                for p in paths:
                    self.main_window.add_pdf_tab(p)

    def _rotate_page(self, page_idx: int, angle: int):
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        if not tab_doc or not tab_doc.doc or not (0 <= page_idx < len(tab_doc.doc)):
            return
        if hasattr(tab_doc, 'rotate_page'):
            tab_doc.rotate_page(page_idx, angle)
        else:
            page = tab_doc.doc[page_idx]
            page.set_rotation((page.rotation + angle) % 360)
            tab_doc.set_modified(True)
            if hasattr(tab_doc, 'render_all_pages'):
                tab_doc.render_all_pages()
        self.load_thumbnails()

    def _duplicate_page(self, page_idx: int):
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        if not tab_doc or not tab_doc.doc or not (0 <= page_idx < len(tab_doc.doc)):
            return
        if hasattr(tab_doc, 'duplicate_page'):
            if tab_doc.duplicate_page(page_idx):
                self.load_thumbnails()
            else:
                QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_duplicate_page_error", error="Failed to duplicate page"))
        else:
            try:
                temp = fitz.open("pdf", tab_doc.doc.tobytes())
                tab_doc.doc.insert_pdf(temp, from_page=page_idx, to_page=page_idx, start_at=page_idx + 1)
                temp.close()
                if hasattr(tab_doc, 'drawings') and tab_doc.drawings:
                    for d in tab_doc.drawings:
                        if d.get("page", 0) > page_idx:
                            d["page"] += 1
                tab_doc.set_modified(True)
                if hasattr(tab_doc, 'render_all_pages'):
                    tab_doc.render_all_pages()
                self.load_thumbnails()
                tab_doc.go_to_page(page_idx + 1)
            except Exception as e:
                QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_duplicate_page_error", error=str(e)))

    def _delete_page(self, page_idx: int):
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        if not tab_doc or not tab_doc.doc:
            return
        if len(tab_doc.doc) <= 1:
            QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_cannot_delete_last_page"))
            return
        ans = QMessageBox.question(
            self, LanguageManager.tr("app_title"),
            LanguageManager.tr("sidebar_delete_page_confirm", page=page_idx + 1),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ans == QMessageBox.StandardButton.Yes:
            tab_doc.delete_page(page_idx)
            self.load_thumbnails()

    def show_bookmark_for_page(self, page_idx: int):
        self.set_panel("bookmarks")
        def search_item(parent):
            for i in range(parent.childCount()):
                ch = parent.child(i)
                if ch.data(0, Qt.ItemDataRole.UserRole) == page_idx:
                    return ch
                found = search_item(ch)
                if found:
                    return found
            return None

        target = None
        for i in range(self.tree_bookmarks.topLevelItemCount()):
            top = self.tree_bookmarks.topLevelItem(i)
            if top.data(0, Qt.ItemDataRole.UserRole) == page_idx:
                target = top
                break
            target = search_item(top)
            if target:
                break

        if target:
            p = target.parent()
            while p:
                p.setExpanded(True)
                p = p.parent()
            self.tree_bookmarks.clearSelection()
            target.setSelected(True)
            self.tree_bookmarks.setCurrentItem(target)
            self.tree_bookmarks.scrollToItem(target)

    def load_bookmarks(self):
        """Aktif belgenin yer imlerini yükler."""
        self.tree_bookmarks.clear()
        if not self.main_window:
            self.stack.setCurrentIndex(0)
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.stack.setCurrentIndex(0)
            return

        try:
            toc = tab_doc.doc.get_toc(simple=False)
        except Exception:
            toc = []

        if not toc:
            self.stack.setCurrentIndex(0)
            return

        # Yer imleri var: Ağacı doldur
        self.stack.setCurrentIndex(1)
        items_by_level = {0: self.tree_bookmarks.invisibleRootItem()}
        for entry in toc:
            level = entry[0]
            title = entry[1]
            page_1_based = entry[2] if len(entry) > 2 else 1
            page_idx = max(0, page_1_based - 1)

            parent_item = items_by_level.get(level - 1, self.tree_bookmarks.invisibleRootItem())
            tree_item = QTreeWidgetItem(parent_item)
            tree_item.setText(0, title)
            tree_item.setIcon(0, ModernIconFactory.icon_bookmark())
            tree_item.setText(1, str(page_1_based))
            tree_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, page_idx)
            tree_item.setData(1, Qt.ItemDataRole.UserRole, page_idx)
            items_by_level[level] = tree_item

        self.tree_bookmarks.expandAll()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        p = item.data(0, Qt.ItemDataRole.UserRole)
        if p is not None:
            self.bookmarkClicked.emit(p)

    def _add_bookmark_action(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        curr = getattr(tab_doc, 'current_page', 0)
        from PyQt6.QtWidgets import QInputDialog
        title, ok = QInputDialog.getText(self, LanguageManager.tr("bookmarks_add_btn"), "Yer İmi Başlığı:")
        if ok and title.strip():
            toc = tab_doc.doc.get_toc(simple=False)
            toc.append([1, title.strip(), curr + 1])
            tab_doc.doc.set_toc(toc)
            tab_doc.set_modified(True)
            self.load_bookmarks()
            if hasattr(tab_doc, 'update_bookmark_ribbons'):
                tab_doc.update_bookmark_ribbons()

    # ==========================================================================
    # YORUMLAR İŞLEMLERİ (ADOBE ACROBAT TARZI)
    # ==========================================================================
    def load_comments(self):
        """Aktif belgenin yorumlarını ve ek açıklamalarını yükler."""
        self.tree_comments.clear()
        if not self.main_window:
            self.comments_stack.setCurrentIndex(0)
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.comments_stack.setCurrentIndex(0)
            return

        pages_dict = {}
        total_count = 0

        # 1. PyMuPDF Standart Ek Açıklamaları
        for p_idx in range(len(tab_doc.doc)):
            try:
                page = tab_doc.doc[p_idx]
                for annot in page.annots():
                    info = annot.info or {}
                    author = info.get("title", "") or "AuraPDF"
                    content = info.get("content", "") or annot.get_text() or annot.type[1]
                    date_val = info.get("modDate", "") or info.get("creationDate", "")
                    pages_dict.setdefault(p_idx, []).append({
                        "author": author,
                        "content": content,
                        "date": date_val,
                        "type": annot.type[1],
                        "page": p_idx,
                        "xref": getattr(annot, 'xref', 0),
                        "rect": list(annot.rect) if hasattr(annot, 'rect') else None,
                        "annot_ref": annot
                    })
                    total_count += 1
            except Exception:
                pass

        # 2. TabDocument Serbest Not Çizimleri
        for d in getattr(tab_doc, 'drawings', []):
            if d.get("text"):
                p_idx = d.get("page", 0)
                pages_dict.setdefault(p_idx, []).append({
                    "author": d.get("author", "Not"),
                    "content": d.get("text", ""),
                    "date": "",
                    "type": "Not",
                    "page": p_idx,
                    "drawing_ref": d
                })
                total_count += 1

        if total_count == 0:
            self.comments_stack.setCurrentIndex(0)
            return

        self.comments_stack.setCurrentIndex(1)
        for p_idx in sorted(pages_dict.keys()):
            annots = pages_dict[p_idx]
            page_group = QTreeWidgetItem(self.tree_comments)
            page_group.setText(0, f"Sayfa {p_idx + 1} ({len(annots)})")
            page_group.setExpanded(True)

            for a in annots:
                item = QTreeWidgetItem(page_group)
                icon = ModernIconFactory.icon_highlighter() if "high" in a['type'].lower() else ModernIconFactory.icon_comments()
                item.setIcon(0, icon)
                author_title = f"{a['author']}: {a['content'][:45]}"
                item.setText(0, author_title)
                item.setData(0, Qt.ItemDataRole.UserRole, a)

    def _add_comment_action(self):
        text = self.txt_new_comment.toPlainText().strip()
        if not text or not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        p_idx = getattr(tab_doc, 'current_page_idx', getattr(tab_doc, 'current_page', 0))
        if p_idx < 0 or p_idx >= len(tab_doc.doc):
            p_idx = 0

        from src.ui.dialogs.settings_dialog import get_effective_author_name
        author = get_effective_author_name()

        try:
            page = tab_doc.doc[p_idx]
            # Standart PDF metin ek açıklaması (Sticky Note / Annotation)
            annot = page.add_text_annot(fitz.Point(72, 72), text)
            annot.set_info(title=author, content=text)
            annot.update()
            tab_doc.set_modified(True)
            if hasattr(tab_doc, 'render_all_pages'):
                tab_doc.render_all_pages()
            if hasattr(tab_doc, 'rerender_visible_pages'):
                tab_doc.rerender_visible_pages()
            self.txt_new_comment.clear()
            self.load_comments()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def _on_comment_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and "page" in data:
            self.bookmarkClicked.emit(data["page"])

    def _on_comment_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self._edit_comment_item(data)

    def _on_comment_context_menu(self, pos):
        item = self.tree_comments.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)
        apply_dialog_theme(menu, self)
        act_edit = menu.addAction(ModernIconFactory.icon_edit(), LanguageManager.tr("comment_edit_btn"))
        act_del = menu.addAction(ModernIconFactory.icon_trash(), LanguageManager.tr("comments_delete_tooltip"))
        act = menu.exec(self.tree_comments.mapToGlobal(pos))
        if act == act_edit:
            self._edit_comment_item(data)
        elif act == act_del:
            self._delete_comment_item(data)

    def _edit_comment_item(self, data: dict):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            from src.ui.dialogs.comment_dialog import AuraCommentInputDialog
            curr_text = data.get("content", "")
            curr_auth = data.get("author", "")
            dlg = AuraCommentInputDialog(self, initial_text=curr_text, initial_author=curr_auth)
            if dlg.exec():
                new_text, new_author, _ = dlg.get_comment_data()
                p_idx = data.get("page", 0)
                if "annot_ref" in data and 0 <= p_idx < len(tab_doc.doc):
                    page = tab_doc.doc[p_idx]
                    annot = data["annot_ref"]
                    updated = False
                    try:
                        annot.set_info(title=new_author, content=new_text)
                        annot.update()
                        updated = True
                    except Exception:
                        pass
                    if not updated:
                        xref = data.get("xref", 0)
                        rect = data.get("rect")
                        for a in page.annots():
                            if (xref and getattr(a, 'xref', 0) == xref) or (rect and list(a.rect) == rect):
                                a.set_info(title=new_author, content=new_text)
                                a.update()
                                break
                    tab_doc.set_modified(True)
                    if hasattr(tab_doc, 'render_all_pages'):
                        tab_doc.render_all_pages()
                    if hasattr(tab_doc, 'rerender_visible_pages'):
                        tab_doc.rerender_visible_pages()
                elif "drawing_ref" in data and hasattr(tab_doc, 'drawings'):
                    d = data["drawing_ref"]
                    d["text"] = new_text
                    d["author"] = new_author
                    tab_doc.set_modified(True)
                    if hasattr(tab_doc, 'render_all_pages'):
                        tab_doc.render_all_pages()
                    if hasattr(tab_doc, 'rerender_visible_pages'):
                        tab_doc.rerender_visible_pages()
                self.load_comments()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def _delete_comment_item(self, data: dict):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        res = QMessageBox.question(
            self, LanguageManager.tr("app_title"),
            LanguageManager.tr("comments_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        p_idx = data.get("page", 0)
        try:
            if "annot_ref" in data and 0 <= p_idx < len(tab_doc.doc):
                page = tab_doc.doc[p_idx]
                deleted = False
                try:
                    page.delete_annot(data["annot_ref"])
                    deleted = True
                except Exception:
                    pass
                if not deleted:
                    xref = data.get("xref", 0)
                    rect = data.get("rect")
                    for a in page.annots():
                        if (xref and getattr(a, 'xref', 0) == xref) or (rect and list(a.rect) == rect):
                            page.delete_annot(a)
                            break
                tab_doc.set_modified(True)
                if hasattr(tab_doc, 'render_all_pages'):
                    tab_doc.render_all_pages()
                if hasattr(tab_doc, 'rerender_visible_pages'):
                    tab_doc.rerender_visible_pages()
            elif "drawing_ref" in data and hasattr(tab_doc, 'drawings'):
                if data["drawing_ref"] in tab_doc.drawings:
                    tab_doc.drawings.remove(data["drawing_ref"])
                    tab_doc.set_modified(True)
                    if hasattr(tab_doc, 'render_all_pages'):
                        tab_doc.render_all_pages()
                    if hasattr(tab_doc, 'rerender_visible_pages'):
                        tab_doc.rerender_visible_pages()
            self.load_comments()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def _filter_comments(self, text: str):
        query = text.lower().strip()
        for i in range(self.tree_comments.topLevelItemCount()):
            top = self.tree_comments.topLevelItem(i)
            group_match = False
            for j in range(top.childCount()):
                child = top.child(j)
                txt = child.text(0).lower()
                matched = not query or (query in txt)
                child.setHidden(not matched)
                if matched:
                    group_match = True
            top.setHidden(not group_match and bool(query))

    def _on_header_add_clicked(self):
        if self.current_panel == "attachments":
            self._add_attachment_action()
        elif self.current_panel == "thumbnails":
            self._on_add_page_menu_requested()
        else:
            self._add_bookmark_action()

    # ==========================================================================
    # EKLER (ATTACHMENTS) İŞLEMLERİ
    # ==========================================================================
    def load_attachments(self):
        """Aktif belgenin eklerini yükler."""
        if not self.main_window:
            self.stack_attachments.setCurrentIndex(0)
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.stack_attachments.setCurrentIndex(0)
            return
        try:
            names = tab_doc.doc.embfile_names() if hasattr(tab_doc.doc, 'embfile_names') else []
        except Exception:
            names = []
        if not names:
            self.stack_attachments.setCurrentIndex(0)
            return
        self.stack_attachments.setCurrentIndex(1)
        self.list_attachments.clear()
        for name in names:
            info = {}
            try:
                info = tab_doc.doc.embfile_info(name)
            except Exception:
                pass
            size_bytes = info.get("size", 0) if isinstance(info, dict) else 0
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"
            elif size_bytes > 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes > 0:
                size_str = f"{size_bytes} B"
            else:
                size_str = ""
            display_text = f"{name}"
            if size_str:
                display_text += f"  ({size_str})"
            item = QListWidgetItem(ModernIconFactory.icon_attachment(), display_text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_attachments.addItem(item)

    def _add_attachment_action(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, LanguageManager.tr("sidebar_add_attachment"))
        if not paths:
            return
        try:
            added_any = False
            for path in paths:
                with open(path, "rb") as f:
                    content = f.read()
                basename = os.path.basename(path)
                tab_doc.doc.embfile_add(basename, content)
                added_any = True
            if added_any:
                tab_doc.set_modified(True)
                self.load_attachments()
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("error"), f"{e}")

    def _on_attachment_double_clicked(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        if name:
            self._open_attachment(name)

    def _open_attachment(self, name: str):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            content = tab_doc.doc.embfile_get(name)
            temp_dir = tempfile.gettempdir()
            safe_name = os.path.basename(name)
            out_path = os.path.join(temp_dir, safe_name)
            with open(out_path, "wb") as f:
                f.write(content)
            os.startfile(out_path)
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("error"), f"{e}")

    def _save_attachment(self, name: str):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            content = tab_doc.doc.embfile_get(name)
            safe_name = os.path.basename(name)
            out_path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("sidebar_save_attachment"), safe_name)
            if out_path:
                with open(out_path, "wb") as f:
                    f.write(content)
                QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_attachment_saved", path=out_path))
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("error"), f"{e}")

    def _delete_attachment(self, name: str):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            tab_doc.doc.embfile_del(name)
            tab_doc.set_modified(True)
            self.load_attachments()
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("error"), f"{e}")

    def _show_attachment_context_menu(self, pos: QPoint):
        item = self.list_attachments.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        menu = QMenu(self)
        act_open = menu.addAction(ModernIconFactory.icon_attachment(), LanguageManager.tr("sidebar_open_attachment"))
        act_save = menu.addAction(ModernIconFactory.icon_save(), LanguageManager.tr("sidebar_save_attachment"))
        menu.addSeparator()
        act_del = menu.addAction(ModernIconFactory.icon_close(), LanguageManager.tr("sidebar_delete_attachment"))

        action = menu.exec(self.list_attachments.mapToGlobal(pos))
        if action == act_open:
            self._open_attachment(name)
        elif action == act_save:
            self._save_attachment(name)
        elif action == act_del:
            self._delete_attachment(name)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernRightSidebar {{
                background-color: {c['surface']};
                border-right: 1px solid {c['border']};
            }}
            QWidget {{
                background-color: {c['surface']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            QLabel#EmptyMsg {{
                color: {c['text_muted']};
            }}
            QTreeWidget {{
                background-color: {c['surface']};
                color: {c['text']};
                border: none;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                border-radius: 4px;
                color: {c['text']};
            }}
            QTreeWidget::item:hover {{
                background-color: {c['surface_hover']};
            }}
            QTreeWidget::item:selected {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                font-weight: 600;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
            #NewCommentCard {{
                background-color: {c['surface_hover']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QTextEdit {{
                background-color: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 11.5px;
            }}
            QLineEdit {{
                background-color: {c['surface_hover']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11.5px;
            }}
            QPushButton#PostCommentBtn {{
                background-color: {c['accent']};
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                border-radius: 5px;
                padding: 4px 12px;
                border: none;
            }}
            QPushButton#PostCommentBtn:hover {{
                opacity: 0.9;
            }}
            #RightRailThumbnailsList {{
                background-color: transparent;
                border: none;
            }}
            #RightRailThumbnailsList::item {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px;
                margin: 2px 2px;
                color: {c['text']};
                font-size: 10px;
                font-weight: 500;
            }}
            #RightRailThumbnailsList::item:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
            }}
            #RightRailThumbnailsList::item:selected {{
                background-color: {c['surface_hover']};
                border: 1.5px solid {c['accent']};
                color: {c['accent']};
                font-weight: 600;
            }}
            #RightRailAttachmentsList {{
                background-color: transparent;
                border: none;
            }}
            #RightRailAttachmentsList::item {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 8px;
                margin: 2px 2px;
                color: {c['text']};
                font-size: 11.5px;
                font-weight: 500;
            }}
            #RightRailAttachmentsList::item:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
            }}
            #RightRailAttachmentsList::item:selected {{
                background-color: {c['accent_light']};
                border: 1.5px solid {c['accent']};
                color: {c['accent']};
                font-weight: 600;
            }}
            #SidebarTabContainer {{
                background-color: transparent;
                border-bottom: 1px solid {c['border']};
                padding-bottom: 3px;
            }}
            QToolButton.SidebarTabButton {{
                background-color: transparent;
                color: {c['text_muted']};
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 4px;
                padding: 4px 4px;
                font-size: 11px;
                font-weight: 500;
            }}
            QToolButton.SidebarTabButton:hover {{
                background-color: {c['surface_hover']};
                color: {c['text']};
            }}
            QToolButton.SidebarTabButton:checked {{
                background-color: {c['surface_hover']};
                color: {c['accent']};
                border-bottom: 2px solid {c['accent']};
                font-weight: 700;
            }}
            #PrimaryActionBtn {{
                background-color: {c['card_bg']};
                color: {c['text']};
                font-weight: 600;
                font-size: 12px;
                border-radius: 6px;
                padding: 7px 14px;
                border: 1px solid {c['border']};
            }}
            #PrimaryActionBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            #TTSHeaderStrip {{
                background-color: {c['surface']};
                border: 1px solid {c['border_subtle']};
                border-radius: 6px;
            }}
            #TTSBadge {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                font-size: 9.5px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 4px;
            }}
            #TTSStatusDot {{
                font-size: 11px;
            }}
            #TTSStatusText {{
                color: {c['text']};
                font-size: 11px;
                font-weight: 600;
            }}
            #TTSInfoBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {c['text_muted']};
            }}
            #TTSInfoBtn:hover {{
                background-color: {c['surface_hover']};
                color: {c['accent']};
            }}
            #TTSActionToolbar {{
                background-color: transparent;
                border: none;
            }}
            #TTSPageNavBtn {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border_subtle']};
                border-radius: 5px;
                color: {c['text']};
            }}
            #TTSPageNavBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
            }}
            #TTSPageInfoLabel {{
                font-size: 11px;
                font-weight: 600;
                color: {c['text']};
                padding: 0 4px;
            }}
            #TTSPrimaryBtn {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                border: 1px solid {c['accent']};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #TTSPrimaryBtn:hover {{
                background-color: {c['accent']};
                color: #ffffff;
            }}
            #TTSSegmentFrame {{
                background-color: {c['surface']};
                border: 1px solid {c['border_subtle']};
                border-radius: 7px;
            }}
            #TTSSegBtn {{
                background-color: transparent;
                color: {c['text_muted']};
                border: none;
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            #TTSSegBtn:hover {{
                color: {c['text']};
                background-color: {c['surface_hover']};
            }}
            #TTSSegBtn:checked {{
                color: #ffffff;
                background-color: {c['accent']};
                font-weight: 700;
            }}
            #TTSToolBtn {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border_subtle']};
                border-radius: 5px;
                padding: 2px 6px;
                font-size: 10.5px;
                font-weight: 500;
            }}
            #TTSToolBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            #TTSReadingCanvas {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border_subtle']};
                border-radius: 8px;
            }}
            #TTSReadingCanvas:hover {{
                border-color: {c['border']};
            }}
            #TTSCanvasTitle {{
                font-size: 11px;
                font-weight: 700;
                color: {c['text']};
            }}
            #TTSCanvasStats {{
                font-size: 10px;
                font-weight: 500;
                color: {c['text_muted']};
                padding: 1px 6px;
                background-color: {c['surface']};
                border-radius: 4px;
            }}
            #TTSTextInput {{
                background-color: transparent;
                color: {c['text']};
                border: none;
                padding: 4px 4px;
                font-size: 12px;
                line-height: 1.45;
                selection-background-color: {c['accent_light']};
                selection-color: {c['text']};
            }}
            #TTSPlayerCard {{
                background-color: {c['surface']};
                border: 1px solid {c['border_subtle']};
                border-radius: 8px;
            }}
            #TTSPlaybackStatus {{
                color: {c['text_muted']};
                font-size: 10.5px;
            }}
            #TTSTimeLabel {{
                color: {c['accent']};
                font-size: 10.5px;
                font-weight: 600;
            }}
            #TTSProgressSlider::groove:horizontal, #TTSVolumeSlider::groove:horizontal {{
                height: 3px;
                background: {c['border']};
                border-radius: 1.5px;
            }}
            #TTSProgressSlider::sub-page:horizontal, #TTSVolumeSlider::sub-page:horizontal {{
                background: {c['accent']};
                border-radius: 1.5px;
            }}
            #TTSProgressSlider::handle:horizontal, #TTSVolumeSlider::handle:horizontal {{
                background: #ffffff;
                border: 2px solid {c['accent']};
                width: 10px;
                height: 10px;
                margin: -3.5px 0;
                border-radius: 5px;
            }}
            #TTSProgressSlider::handle:horizontal:hover, #TTSVolumeSlider::handle:horizontal:hover {{
                background: {c['accent']};
                border: 2px solid #ffffff;
                width: 12px;
                height: 12px;
                margin: -4.5px 0;
                border-radius: 6px;
            }}
            #TTSHeroPlayBtn, #TTSPlayBtn {{
                background-color: {c['accent']};
                color: #ffffff;
                border: none;
                border-radius: 17px;
                padding: 4px 12px;
                font-size: 11.5px;
                font-weight: 700;
            }}
            #TTSHeroPlayBtn:hover, #TTSPlayBtn:hover {{
                background-color: {c['accent_hover']};
            }}
            #TTSRoundBtn, #TTSControlBtn {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border_subtle']};
                border-radius: 15px;
                color: {c['text']};
            }}
            #TTSRoundBtn:hover, #TTSControlBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            #TTSPillBtn, #TTSSpeedMenuBtn {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border_subtle']};
                border-radius: 11px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 600;
            }}
            #TTSPillBtn:hover, #TTSSpeedMenuBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            #TTSPillBtn::menu-indicator, #TTSSpeedMenuBtn::menu-indicator {{
                image: none;
                width: 0;
            }}
            #TTSDeviceCombo {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border_subtle']};
                border-radius: 6px;
                padding: 2px 6px;
                font-size: 10.5px;
                font-weight: 500;
            }}
            #TTSDeviceCombo:hover {{
                border-color: {c['accent']};
            }}
            #TTSDeviceCombo::drop-down {{
                border: none;
                width: 14px;
            }}
            #TTSDeviceCombo QAbstractItemView {{
                background-color: {c['surface']};
                color: {c['text']};
                selection-background-color: {c['accent_light']};
                selection-color: {c['accent']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            #TTSDownloadBtn {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                border: 1px solid {c['accent']};
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            #TTSDownloadBtn:hover {{
                background-color: {c['accent']};
                color: #ffffff;
            }}
            QMenu {{
                background-color: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 4px 18px 4px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {c['accent_light']};
                color: {c['accent']};
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        if hasattr(self, 'panel_accessibility'):
            self.panel_accessibility.apply_theme(theme_name)

    def mouseMoveEvent(self, event):
        if self._is_resizing:
            delta = event.globalPosition().x() - self._resize_start_x
            new_w = max(self.MIN_WIDTH, min(self.MAX_WIDTH, int(self._resize_start_w + delta)))
            self.setFixedWidth(new_w)
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("sidebar_panel_width", new_w)
            self._adapt_to_width(new_w)
            event.accept()
            return

        is_near_right = (event.pos().x() >= self.width() - 8)
        if is_near_right != self._hovering_resize_edge:
            self._hovering_resize_edge = is_near_right
            self.update()

        if is_near_right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.setToolTip(LanguageManager.tr("sidebar_resize_hint"))
        else:
            self.unsetCursor()
            self.setToolTip("")
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().x() >= self.width() - 8:
            self._is_resizing = True
            self._resize_start_x = event.globalPosition().x()
            self._resize_start_w = self.width()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_resizing:
            self._is_resizing = False
            if event.pos().x() < self.width() - 8:
                self.unsetCursor()
                self._hovering_resize_edge = False
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.pos().x() >= self.width() - 8:
            target_w = self.MIN_WIDTH if self.width() > 220 else self.DEFAULT_WIDTH
            self.setFixedWidth(target_w)
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("sidebar_panel_width", target_w)
            self._adapt_to_width(target_w)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event):
        if not self._is_resizing:
            self.unsetCursor()
            if self._hovering_resize_edge:
                self._hovering_resize_edge = False
                self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        rx = self.width() - 1
        if self._is_resizing or self._hovering_resize_edge:
            p.setPen(QPen(QColor("#38bdf8"), 2))
        else:
            c = get_modern_theme_colors(self.theme_name)
            p.setPen(QPen(QColor(c.get('border', 'rgba(255, 255, 255, 0.12)')), 1))
        p.drawLine(rx, 0, rx, self.height())
        p.end()

    def _adapt_to_width(self, width: int):
        """Panel genişliği değiştiğinde iç bileşenleri (thumbnails vb.) orantılı olarak uyarlar."""
        if hasattr(self, 'list_thumbnails') and self.list_thumbnails:
            thumb_w = max(75, min(140, width - 36))
            thumb_h = int(thumb_w * 1.38)
            self.list_thumbnails.setIconSize(QSize(thumb_w, thumb_h))
            hint_size = QSize(thumb_w + 14, thumb_h + 26)
            for i in range(self.list_thumbnails.count()):
                it = self.list_thumbnails.item(i)
                if it:
                    it.setSizeHint(hint_size)
        if hasattr(self, 'tab_container') and self.tab_container:
            # Genişlik daraldığında tab butonlarının metin görünümünü uyarla
            is_compact = width < 230
            for btn in (getattr(self, 'btn_tab_thumbs', None),
                        getattr(self, 'btn_tab_bookmarks', None),
                        getattr(self, 'btn_tab_attachments', None),
                        getattr(self, 'btn_tab_comments', None)):
                if btn:
                    btn.setToolButtonStyle(
                        Qt.ToolButtonStyle.ToolButtonIconOnly if is_compact
                        else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                    )


# ==============================================================================
# 6. EN SAĞ DİKEY ARAÇ ÇUBUĞU (ModernUtilityRail)
# ==============================================================================
class ModernUtilityRail(QWidget):
    """
    En sağ kenardaki dikey araç çubuğu (Kullanıcı görselindeki sağ ikon rayı):
    - Üst grup:
      - Yorumlar
      - Yer İmleri (Seçili / Aktif)
      - Sayfa Küçük Resimleri
      - Ekler
      - İmzalar
    - Alt grup:
      - Sayfa Gezintisi: 1 / 135 (▲ / ▼)
      - Yakınlaştırma Yüzdesi: 146%
      - Sayfaya Sığdır / Genişliğe Sığdır / Tam Ekran
      - Zoom In (+) / Zoom Out (-)
    """
    railItemToggled = pyqtSignal(str)
    fullscreenRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "gray"
        self.active_rail_id: Optional[str] = None
        self.total_pages = 1
        self.setFixedWidth(64)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 8, 4, 8)
        main_layout.setSpacing(6)

        # Üst Panel Tetikleyicileri
        self.buttons: Dict[str, QToolButton] = {}
        top_items = [
            ("thumbnails", ModernIconFactory.icon_thumbnails(), "dock_title"),
            ("bookmarks", ModernIconFactory.icon_bookmark(), "sidebar_bookmarks"),
            ("comments", ModernIconFactory.icon_comments(), "sidebar_comments"),
            ("attachments", ModernIconFactory.icon_attachment(), "sidebar_attachments"),
        ]

        for rid, icon, tip_key in top_items:
            btn = QToolButton()
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(40, 36)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(LanguageManager.tr(tip_key))
            btn.clicked.connect(lambda checked, r=rid: self._on_button_clicked(r))
            main_layout.addWidget(btn)
            self.buttons[rid] = btn

        main_layout.addStretch(1)

        # Alt Panel Tetikleyicisi (En alt kısım): Erişilebilirlik ve Sesli Okuma
        btn_acc = QToolButton()
        btn_acc.setIcon(ModernIconFactory.icon_accessibility())
        btn_acc.setIconSize(QSize(18, 18))
        btn_acc.setFixedSize(40, 36)
        btn_acc.setCheckable(True)
        btn_acc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_acc.setToolTip(LanguageManager.tr("right_rail_accessibility"))
        btn_acc.clicked.connect(lambda checked: self._on_button_clicked("accessibility"))
        main_layout.addWidget(btn_acc)
        self.buttons["accessibility"] = btn_acc

        self.apply_theme(self.theme_name)

    @property
    def current_item(self) -> str:
        return self.active_rail_id or "none"

    @current_item.setter
    def current_item(self, val: str):
        self.set_active_rail_item(val if val != "none" else None)

    def retranslate_ui(self):
        tip_map = {
            "thumbnails": "dock_title",
            "bookmarks": "sidebar_bookmarks",
            "comments": "sidebar_comments",
            "attachments": "sidebar_attachments",
            "accessibility": "right_rail_accessibility",
        }
        for rid, key in tip_map.items():
            if rid in self.buttons:
                self.buttons[rid].setToolTip(LanguageManager.tr(key))

    def _on_button_clicked(self, rail_id: str):
        if self.active_rail_id == rail_id:
            # Tekrar tıklandı: Kapat
            self.active_rail_id = None
            self.buttons[rail_id].setChecked(False)
            self.railItemToggled.emit("none")
        else:
            self.active_rail_id = rail_id
            for r, b in self.buttons.items():
                b.setChecked(r == rail_id)
            self.railItemToggled.emit(rail_id)

    def set_active_rail_item(self, rail_id: Optional[str]):
        self.active_rail_id = rail_id
        for r, b in self.buttons.items():
            b.setChecked(r == rail_id)



    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernUtilityRail {{
                background-color: {c['surface']};
                border-right: 1px solid {c['border']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            #RailPageInput {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['accent']};
                font-weight: 700;
                font-size: 13px;
                padding: 1px;
            }}
            #RailPageInput:focus {{
                border: 1.5px solid {c['accent']};
                background-color: {c['surface']};
            }}
            #RailPageTotal {{
                color: {c['text_muted']};
                font-weight: 600;
                font-size: 12px;
            }}
            #RailZoom {{
                color: {c['text']};
                font-size: 12px;
                font-weight: 700;
                padding: 2px 0;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {c['text']};
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
            }}
            QToolButton:checked {{
                background-color: {c['accent_light']};
                border: 1.5px solid {c['accent']};
                color: {c['accent']};
            }}
        """)


# ==============================================================================
# 7. HIZLI KOMUT VE ARAÇ PALETİ (ModernCommandPaletteDialog)
# ==============================================================================
class ModernCommandPaletteDialog(QDialog):
    """Ctrl+K ile açılan modern araç arama kutusu."""
    commandTriggered = pyqtSignal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle(LanguageManager.tr("cmd_palette_title"))
        self.setFixedSize(540, 360)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Arama Girişi
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(LanguageManager.tr("cmd_palette_placeholder"))
        self.txt_search.setFixedHeight(38)
        self.txt_search.textChanged.connect(self._filter_commands)
        self.txt_search.returnPressed.connect(self._execute_selected)
        self.txt_search.installEventFilter(self)
        layout.addWidget(self.txt_search)

        # Komut Listesi
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(20, 20))
        self.list_widget.itemDoubleClicked.connect(lambda it: self._execute_command(it.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.list_widget, stretch=1)

        self.commands = [
            ("organize_pages", "tool_organize_pages", ModernIconFactory.icon_organize("#22c55e")),
            ("edit_pdf", "tool_edit_pdf", ModernIconFactory.icon_edit_content("#ec4899")),
            ("combine_files", "tool_combine_files", ModernIconFactory.icon_combine_files("#38bdf8")),
            ("compress_pdf", "tool_compress_pdf", ModernIconFactory.icon_compress("#ef4444")),
            ("scan_ocr", "tool_scan_ocr", ModernIconFactory.icon_ocr("#10b981")),
            ("export_pdf", "tool_export_pdf", ModernIconFactory.icon_export_pdf("#0ea5e9")),
            ("protect_pdf", "tool_protect_pdf", ModernIconFactory.icon_lock("#3b82f6")),
            ("redact_pdf", "tool_redact_pdf", ModernIconFactory.icon_redact("#ef4444")),
            ("fill_sign", "tool_fill_sign", ModernIconFactory.icon_fill_sign("#a855f7")),
            ("compare_files", "tool_compare_files", ModernIconFactory.icon_compare("#a855f7")),
            ("add_gif", "tool_add_gif", ModernIconFactory.icon_gif("#10b981")),
            ("print", "print_btn", ModernIconFactory.icon_print("#ffffff")),
            ("save", "save_btn", ModernIconFactory.icon_save()),
            ("settings", "settings_title", ModernIconFactory.icon_settings()),
            ("shortcuts", "shortcuts_title", ModernIconFactory.icon_info()),
        ]

        self._filter_commands("")
        self._apply_style()

    def eventFilter(self, obj, event):
        if obj == self.txt_search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                curr = self.list_widget.currentRow()
                if curr < self.list_widget.count() - 1:
                    self.list_widget.setCurrentRow(curr + 1)
                return True
            elif key == Qt.Key.Key_Up:
                curr = self.list_widget.currentRow()
                if curr > 0:
                    self.list_widget.setCurrentRow(curr - 1)
                return True
            elif key == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self.txt_search.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.txt_search.selectAll()
        QTimer.singleShot(0, self._ensure_search_focus)

    def _ensure_search_focus(self):
        try:
            self.activateWindow()
            self.txt_search.setFocus()
            self.txt_search.selectAll()
        except Exception:
            pass

    def _filter_commands(self, text: str):
        self.list_widget.clear()
        query = text.lower().strip()
        for cid, key, icon in self.commands:
            title = LanguageManager.tr(key)
            if not query or query in title.lower() or query in cid.lower():
                item = QListWidgetItem(icon, f"  {title}")
                item.setData(Qt.ItemDataRole.UserRole, cid)
                self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    filter_commands = _filter_commands

    def _execute_selected(self):
        curr = self.list_widget.currentItem()
        if curr:
            cid = curr.data(Qt.ItemDataRole.UserRole)
            self._execute_command(cid)

    def _execute_command(self, cid: str):
        self.commandTriggered.emit(cid)
        self.close()

    def _apply_style(self):
        c = get_modern_theme_colors(getattr(self.main_window, 'current_theme', 'light'))
        self.setStyleSheet(f"""
            ModernCommandPaletteDialog {{
                background-color: {c['surface']};
                border: 1.5px solid {c['border']};
                border-radius: 10px;
            }}
            QLineEdit {{
                background-color: {c['surface_hover']};
                color: {c['text']};
                border: 1.5px solid {c['accent']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 14px;
            }}
            QListWidget {{
                background-color: {c['surface']};
                color: {c['text']};
                border: none;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
            QListWidget::item:hover {{
                background-color: {c['surface_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                font-weight: 600;
            }}
        """)