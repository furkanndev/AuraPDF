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
from typing import List, Dict, Optional, Set, Any
import pymupdf as fitz

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QToolButton,
    QPushButton, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QListView, QMenu,
    QDialog, QSizePolicy, QApplication, QSlider, QMessageBox, QFileDialog,
    QHeaderView, QGraphicsDropShadowEffect, QAbstractItemView, QStyleOptionViewItem,
    QProgressBar, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPointF, QRect, QRectF, QTimer, QThread, QUrl, QEvent, QSettings
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QCursor, QKeySequence, QShortcut, QDesktopServices,
    QFontMetrics, QIntValidator, QLinearGradient
)

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
    return palettes.get(theme_name, palettes["gray"])


# ==============================================================================
# 1. MODERN DOKÜMAN SEKME ÇUBUĞU (ModernTabBarWidget)
# ==============================================================================
class ModernTabItem(QWidget):
    """Tek bir belge sekmesi (İkon, Başlık, Kapat butonu, Seçim efekti)."""
    closeRequested = pyqtSignal(int)
    clicked = pyqtSignal(int)

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
        self.lbl_icon.setPixmap(ModernIconFactory.icon_app().pixmap(14, 14))
        self.lbl_icon.setFixedSize(14, 14)
        layout.addWidget(self.lbl_icon)

        # Başlık
        self.lbl_title = QLabel(title)
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

    def set_active(self, active: bool, theme_name: str = "light"):
        self.is_active = active
        self._apply_style(theme_name)

    def set_title(self, title: str):
        self.title = title
        self.setToolTip(title)
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

    def __init__(self, parent=None):
        super().__init__(parent)
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
            layout.setContentsMargins(6, 2, 6, 2)
            layout.setSpacing(4)
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

        self.apply_theme(self.theme_name)

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
        
        border_style = f"border: 1px solid {c['border']}; border-radius: 8px;" if self.orientation == Qt.Orientation.Horizontal else f"border-right: 1px solid {c['border']}; border-left: 1px solid {c['border']}; border-radius: 0px;"
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
                border-radius: 6px;
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


class ModernHeaderBar(QWidget):
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

        # Dikey Ayırıcı
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedWidth(1)
        sep1.setStyleSheet(f"background-color: #e2e8f0; border: none;")
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

        layout.addStretch(1)

        # Sabitlenebilir Minimalist Hızlı Araçlar Kapsülü (Orta boşlukta estetik yerleşim)
        self.pinned_tools_capsule = ModernPinnedQuickToolsBar(self)
        self.pinned_tools_capsule.hide()
        layout.addWidget(self.pinned_tools_capsule)

        layout.addStretch(1)

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
        if hasattr(self, 'pinned_tools_capsule'):
            self.pinned_tools_capsule.retranslate_ui()

    def set_mode(self, mode_id: str):
        self.current_mode = mode_id
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode_id)
        self.modeChanged.emit(mode_id)

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        if hasattr(self, 'pinned_tools_capsule'):
            self.pinned_tools_capsule.apply_theme(theme_name)
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
            QLabel {{
                color: {c['text_muted']};
                font-size: 12px;
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
class ModernToolItemWidget(QWidget):
    """'Tüm araçlar' listesindeki renkli buton öğesi."""
    clicked = pyqtSignal(str)

    def __init__(self, tool_id: str, label_text: str, icon: QIcon, accent_color: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tool_id = tool_id
        self.accent_color = accent_color
        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(icon.pixmap(20, 20))
        self.lbl_icon.setFixedSize(20, 20)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(label_text)
        layout.addWidget(self.lbl_text, stretch=1)

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
        if self.is_active:
            self.setStyleSheet(f"""
                ModernToolItemWidget {{
                    background-color: {c['accent_light']};
                    border-radius: 6px;
                    border-left: 3px solid {c['accent']};
                }}
                QLabel {{
                    color: {c['accent']};
                    font-size: 13px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ModernToolItemWidget {{
                    background-color: transparent;
                    border-radius: 6px;
                    border-left: 3px solid transparent;
                }}
                ModernToolItemWidget:hover {{
                    background-color: {c['surface_hover']};
                }}
                QLabel {{
                    color: {c['text']};
                    font-size: 13px;
                    font-weight: 500;
                }}
            """)


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

        # Kaydırılabilir Araçlar Listesi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tools_container = QWidget()
        self.v_tools = QVBoxLayout(tools_container)
        self.v_tools.setContentsMargins(0, 0, 0, 0)
        self.v_tools.setSpacing(2)

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
            ("print_production", "tool_print_production", ModernIconFactory.icon_print("#a855f7"), "#a855f7"),
            ("measure_objects", "tool_measure_objects", ModernIconFactory.icon_ruler("#ec4899"), "#ec4899"),
            ("search_index", "tool_search_index", ModernIconFactory.icon_search_index("#ec4899"), "#ec4899"),
            ("prepare_accessibility", "tool_prepare_accessibility", ModernIconFactory.icon_accessibility("#a855f7"), "#a855f7"),
            ("add_gif", "tool_add_gif", ModernIconFactory.icon_gif("#10b981"), "#10b981"),
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
        self.setStyleSheet(f"""
            ModernAllToolsPanel {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
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
class ModernDrawerItemWidget(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, item_id: str, title: str, icon: QIcon, badge_text: str = "", is_ready: bool = True, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.item_id = item_id
        self.title = title
        self.is_ready = is_ready
        self.theme_name = "light"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(icon.pixmap(18, 18))
        self.lbl_icon.setFixedSize(18, 18)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(title)
        self.lbl_text.setObjectName("DrawerItemText")
        layout.addWidget(self.lbl_text, stretch=1)

        self.lbl_badge = None
        if badge_text:
            self.lbl_badge = QLabel(badge_text)
            self.lbl_badge.setObjectName("DrawerItemBadge")
            layout.addWidget(self.lbl_badge)

    def set_title(self, title: str):
        self.title = title
        self.lbl_text.setText(title)

    def set_badge(self, text: str):
        if self.lbl_badge:
            self.lbl_badge.setText(text)

    def set_icon(self, icon: QIcon):
        self.lbl_icon.setPixmap(icon.pixmap(18, 18))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)

    def _apply_style(self, theme_name: str):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernDrawerItemWidget {{
                background-color: transparent;
                border-radius: 6px;
            }}
            ModernDrawerItemWidget:hover {{
                background-color: {c['surface_hover']};
            }}
            #DrawerItemText {{
                color: {c['text']};
                font-size: 12.5px;
                font-weight: 500;
            }}
            #DrawerItemBadge {{
                background-color: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                border: 1px solid rgba(34, 197, 94, 0.35);
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
                font-weight: 600;
            }}
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
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
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
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(0, 0, 0, 0)
        v_items.setSpacing(2)

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
            it.clicked.connect(self.exportTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_export_title"))
        self.lbl_cat.setText(LanguageManager.tr("drawer_export_to"))
        for it, (_, key, _, _, _) in zip(self.items, self.specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernExportDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
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
        for item in self.items:
            item._apply_style(theme_name)


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
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
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

        # Bilgilendirme Kutusu
        self.notice_box = QFrame()
        self.notice_box.setObjectName("NoticeBox")
        v_notice = QVBoxLayout(self.notice_box)
        v_notice.setContentsMargins(10, 8, 10, 8)
        self.lbl_notice = QLabel(LanguageManager.tr("drawer_edit_notice"))
        self.lbl_notice.setWordWrap(True)
        self.lbl_notice.setStyleSheet("font-size: 11px; line-height: 1.2;")
        v_notice.addWidget(self.lbl_notice)
        main_layout.addWidget(self.notice_box)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(0, 0, 0, 0)
        v_items.setSpacing(4)

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
            it.clicked.connect(self.editTriggered.emit)
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
            it.clicked.connect(self.editTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_edit_title"))
        self.lbl_notice.setText(LanguageManager.tr("drawer_edit_notice"))
        self.lbl_g1.setText(LanguageManager.tr("drawer_group_modify_page"))
        self.lbl_g2.setText(LanguageManager.tr("drawer_group_add_content"))
        all_specs = self.specs_modify + self.specs_add
        for it, (_, key, _, _, _) in zip(self.items, all_specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernEditDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
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
            #NoticeBox {{
                background-color: {c['accent_light']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            #NoticeBox QLabel {{
                color: {c['text']};
                font-size: 11.5px;
                line-height: 1.3;
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
        for item in self.items:
            item._apply_style(theme_name)


class ModernReadDrawer(QFrame):
    """
    Sadece okuma ve renk modlarını barındıran modern sol çekmece.
    - Grup 1: SAYFA DÜZENİ (Tekli, İkili, Tam Ekran)
    - Grup 2: OKUMA RENK MODLARI (Açık, Gece, Sepya)
    """
    readTriggered = pyqtSignal(str)
    closeRequested = pyqtSignal()
    backRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Üst Başlık ve Geri / Kapat
        h_head = QHBoxLayout()
        h_head.setSpacing(6)

        btn_back = QToolButton(self)
        btn_back.setIcon(ModernIconFactory.icon_nav_back())
        btn_back.setIconSize(QSize(16, 16))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.backRequested.emit)
        h_head.addWidget(btn_back)

        self.lbl_head = QLabel(LanguageManager.tr("drawer_read_title"))
        self.lbl_head.setStyleSheet("font-size: 13px; font-weight: 700;")
        h_head.addWidget(self.lbl_head)
        h_head.addStretch(1)

        self.btn_close = QToolButton(self)
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(14, 14))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(self.btn_close)
        main_layout.addLayout(h_head)

        # Bilgi / İpucu Kutusu
        self.notice_box = QFrame(self)
        self.notice_box.setObjectName("NoticeBox")
        v_notice = QVBoxLayout(self.notice_box)
        v_notice.setContentsMargins(10, 8, 10, 8)
        self.lbl_notice = QLabel(LanguageManager.tr("drawer_read_notice"))
        self.lbl_notice.setWordWrap(True)
        self.lbl_notice.setStyleSheet("font-size: 11px; line-height: 1.2;")
        v_notice.addWidget(self.lbl_notice)
        main_layout.addWidget(self.notice_box)

        # Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(0, 0, 0, 0)
        v_items.setSpacing(4)

        self.items: List[ModernDrawerItemWidget] = []

        # Grup 1: SAYFA DÜZENİ
        self.lbl_g1 = QLabel(LanguageManager.tr("view_mode_group"))
        self.lbl_g1.setObjectName("CategoryHeader")
        v_items.addWidget(self.lbl_g1)

        self.specs_layout = [
            ("view_single", "view_mode_single", ModernIconFactory.icon_view_single("#0284c7"), "", True),
            ("view_double", "view_mode_double", ModernIconFactory.icon_view_double("#0284c7"), "", True),
            ("view_fullscreen", "tb_item_fullscreen", ModernIconFactory.icon_fullscreen("#0284c7"), "", True),
        ]
        for cid, key, icon, badge, is_ready in self.specs_layout:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self.readTriggered.emit)
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
            it.clicked.connect(self.readTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_read_title"))
        self.lbl_notice.setText(LanguageManager.tr("drawer_read_notice"))
        self.lbl_g1.setText(LanguageManager.tr("view_mode_group"))
        self.lbl_g2.setText(LanguageManager.tr("reading_color_modes"))
        all_specs = self.specs_layout + self.specs_color
        for it, (_, key, _, _, _) in zip(self.items, all_specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernReadDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
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
            #NoticeBox {{
                background-color: {c['accent_light']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            #NoticeBox QLabel {{
                color: {c['text']};
                font-size: 11.5px;
                line-height: 1.3;
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
        for item in self.items:
            item._apply_style(theme_name)


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
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(0, 0, 0, 0)
        v_items.setSpacing(4)

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
            it.clicked.connect(self.toolTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def retranslate_ui(self):
        self.lbl_head.setText(LanguageManager.tr("drawer_fillsign_title"))
        self.lbl_cat.setText(LanguageManager.tr("drawer_fill_group"))
        for it, (_, key, _) in zip(self.items, self.specs):
            it.set_title(LanguageManager.tr(key))

    def apply_theme(self, theme_name: str = "gray"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernFillSignDrawer {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
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
        for item in self.items:
            item._apply_style(theme_name)


class ModernLeftSidebar(QStackedWidget):
    """Sol panel yığını: 0=Tüm Araçlar, 1=Export Çekmecesi, 2=Edit Çekmecesi, 3=Read Çekmecesi, 4=Fill & Sign Çekmecesi."""
    toolTriggered = pyqtSignal(str)
    exportTriggered = pyqtSignal(str)
    editTriggered = pyqtSignal(str)
    readTriggered = pyqtSignal(str)
    fillSignTriggered = pyqtSignal(str)
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

    def _on_tool_triggered(self, tool_id: str):
        if tool_id == "export_pdf":
            self.set_page("export")
        elif tool_id == "edit_pdf":
            self.set_page("edit")
        elif tool_id in ("fill_sign", "esign"):
            self.set_page("esign")
        else:
            self.toolTriggered.emit(tool_id)

    def set_page(self, page_name: str):
        if page_name in ("all_tools", "tools"):
            self.setCurrentIndex(0)
        elif page_name in ("export", "convert"):
            self.setCurrentIndex(1)
        elif page_name in ("edit", "modify"):
            self.setCurrentIndex(2)
        elif page_name in ("read", "reading"):
            self.setCurrentIndex(3)
        elif page_name in ("esign", "fill_sign", "sign"):
            self.setCurrentIndex(4)

    def set_active_tool(self, tool_id: Optional[str]):
        self.all_tools_panel.set_active_tool(tool_id)

    def apply_theme(self, theme_name: str):
        self.all_tools_panel.apply_theme(theme_name)
        self.export_drawer.apply_theme(theme_name)
        self.edit_drawer.apply_theme(theme_name)
        self.read_drawer.apply_theme(theme_name)
        self.fill_sign_drawer.apply_theme(theme_name)

    def retranslate_ui(self):
        self.all_tools_panel.retranslate_ui()
        self.export_drawer.retranslate_ui()
        self.edit_drawer.retranslate_ui()
        self.read_drawer.retranslate_ui()
        self.fill_sign_drawer.retranslate_ui()


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

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "gray"
        self.active_tool = "select"
        self.user_moved = False
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
        """Sürükleme bırakıldığında konuma göre üst veya sol çubuğa otomatik sabitleme."""
        # 1. Üst araç çubuğuna sabitleme: Y ekseninde tepeye yakın bırakıldıysa
        if self.y() <= 75:
            self.pinToTopRequested.emit()
            return

        # 2. Sol araç çubuğuna sabitleme: X ekseninde sol kenara veya sol toolbara yakın bırakıldıysa
        left_threshold = 130
        if self.main_window and hasattr(self.main_window, 'central_stack'):
            try:
                cs_x = self.main_window.central_stack.mapTo(self.main_window, QPoint(0, 0)).x()
                left_threshold = max(110, cs_x + 60)
            except Exception:
                pass
        if self.x() <= left_threshold:
            self.pinToLeftRequested.emit()
            return

        # 3. Belge üzerinde serbestçe bırakıldıysa -> serbest hareketli mod
        if self.main_window:
            self.main_window.capsule_docked_to_left = False
            self.main_window.capsule_docked_to_top = False
            QSettings("AuraPDF", "PDFViewer").setValue("capsule_dock_position", "float")
            QSettings("AuraPDF", "PDFViewer").setValue("capsule_docked_to_top", False)
            QSettings("AuraPDF", "PDFViewer").setValue("capsule_docked_to_left", False)
        self.user_moved = True

    def _on_pin_clicked(self):
        """Sabitleme butonuna tıklandığında konuma veya duruma göre sol veya üst çubuğa sabitler."""
        left_threshold = 160
        if self.main_window and hasattr(self.main_window, 'central_stack'):
            try:
                cs_x = self.main_window.central_stack.mapTo(self.main_window, QPoint(0, 0)).x()
                left_threshold = max(140, cs_x + 80)
            except Exception:
                pass
        if self.x() <= left_threshold:
            self.pinToLeftRequested.emit()
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

    def __init__(self, file_path: str, page_count: int, size_str: str, theme_name: str = "light", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.file_path = file_path
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

        self.apply_theme(theme_name)
        self._update_elided_path()

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

        # 3. Son Açılanlar (Recent)
        v_recent = QVBoxLayout()
        v_recent.setSpacing(14)

        h_recent_header = QHBoxLayout()
        h_recent_header.setContentsMargins(0, 0, 0, 0)
        h_recent_header.setSpacing(10)

        self.lbl_recent_title = QLabel(LanguageManager.tr("home_recent_title"))
        self.lbl_recent_title.setObjectName("SectionTitle")
        h_recent_header.addWidget(self.lbl_recent_title)

        h_recent_header.addStretch(1)

        self.btn_clear_recent = QPushButton()
        self.btn_clear_recent.setObjectName("BtnClearRecent")
        self.btn_clear_recent.setIcon(ModernIconFactory.icon_trash())
        self.btn_clear_recent.setIconSize(QSize(13, 13))
        self.btn_clear_recent.setText(" " + LanguageManager.tr("clear_recent_files"))
        self.btn_clear_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_recent.clicked.connect(self._on_clear_recent_clicked)
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

    def load_recent_files(self):
        """Son açılan dosyaları yükler ve listeler."""
        while self.v_recent_items.count() > 0:
            item = self.v_recent_items.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        files = []
        if self.main_window and hasattr(self.main_window, 'get_recent_files'):
            files = self.main_window.get_recent_files()

        if not files:
            if hasattr(self, 'btn_clear_recent'):
                self.btn_clear_recent.hide()
            lbl_empty = QLabel(LanguageManager.tr("home_no_recent"))
            lbl_empty.setObjectName("RecentEmpty")
            lbl_empty.setStyleSheet("padding: 20px 4px; font-size: 13px;")
            self.v_recent_items.addWidget(lbl_empty)
            self.recent_list_container.setMinimumHeight(60)
            return

        if hasattr(self, 'btn_clear_recent'):
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

            row = RecentFileRowWidget(path, pages, sz_str, theme_name=self.theme_name, parent=self.recent_list_container)
            row.clicked.connect(self.fileSelected.emit)
            self.v_recent_items.addWidget(row)
            row_count += 1

        if row_count > 0:
            total_h = row_count * 54 + max(0, row_count - 1) * 4
            self.recent_list_container.setMinimumHeight(total_h)
        else:
            self.recent_list_container.setMinimumHeight(60)

        self.recent_list_container.updateGeometry()
        if self.inner_wrapper.layout():
            self.inner_wrapper.layout().invalidate()
        self.inner_wrapper.updateGeometry()
        if self.content_container.layout():
            self.content_container.layout().invalidate()
        self.content_container.updateGeometry()

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
        self.lbl_recent_title.setText(LanguageManager.tr("home_recent_title"))
        if hasattr(self, 'btn_clear_recent'):
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
            #RecentEmpty {{
                color: {c['text_muted']};
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
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(148, 194)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 5)
        layout.setSpacing(5)

        # Önizleme Resmi
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setFixedSize(132, 150)
        self.lbl_preview.setStyleSheet("background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 2px;")
        layout.addWidget(self.lbl_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Sayfa Numarası
        self.lbl_num = QLabel(str(page_index + 1))
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
        act_rot_ccw = menu.addAction(ModernIconFactory.icon_undo(), "  " + LanguageManager.tr("organize_rotate_ccw"))
        act = menu.exec(event.globalPos())
        if act == act_del:
            self.deleteRequested.emit(self.page_index)
        elif act == act_rot_cw:
            self.rotateRequested.emit(self.page_index, 90)
        elif act == act_rot_ccw:
            self.rotateRequested.emit(self.page_index, -90)

    def set_pixmap(self, pix: QPixmap):
        scaled = pix.scaled(
            130, 148,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_preview.setPixmap(scaled)

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


class OrganizePagesWorkspace(QWidget):
    """
    Ekranın merkezindeki 'Sayfaları Organize Et' çalışma alanı (Kullanıcı görselindeki tasarım):
    - Üst alt-çubuk:
      - 'Sayfa 1 / 135' (veya 'X sayfa seçildi')
      - [Sola Döndür ↺] [Sağa Döndür ↻] [Sil 🗑] [Ekle 📄+] [Çıkar ⤓] [Böl ✂] [Değiştir ⇄]
      - Yakınlaştırma kontrolleri (- slider +)
      - [✕ Kapat] Butonu
    - Çok sütunlu sayfa kartları ızgarası
    """
    closeRequested = pyqtSignal()
    openPageRequested = pyqtSignal(int)
    documentModified = pyqtSignal()

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"
        self.selected_pages: Set[int] = set()
        self.last_clicked_page: Optional[int] = None
        self.cards: List[PageThumbnailCard] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Üst Eylem Çubuğu
        self.top_toolbar = QWidget()
        self.top_toolbar.setObjectName("TopToolbar")
        self.top_toolbar.setFixedHeight(46)
        h_top = QHBoxLayout(self.top_toolbar)
        h_top.setContentsMargins(16, 6, 16, 6)
        h_top.setSpacing(8)

        # Sayfa Bilgisi Etiketi
        self.lbl_page_info = QLabel("Page 1 of 1")
        self.lbl_page_info.setStyleSheet("font-size: 13px; font-weight: 600;")
        h_top.addWidget(self.lbl_page_info)

        h_top.addSpacing(12)

        # Döndür (Sola)
        self.btn_rot_ccw = QToolButton()
        self.btn_rot_ccw.setIcon(ModernIconFactory.icon_undo())
        self.btn_rot_ccw.setIconSize(QSize(16, 16))
        self.btn_rot_ccw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rot_ccw.setToolTip(LanguageManager.tr("organize_rotate_ccw"))
        self.btn_rot_ccw.clicked.connect(self.rotate_selected_ccw)
        h_top.addWidget(self.btn_rot_ccw)

        # Döndür (Sağa)
        self.btn_rot_cw = QToolButton()
        self.btn_rot_cw.setIcon(ModernIconFactory.icon_rotate())
        self.btn_rot_cw.setIconSize(QSize(16, 16))
        self.btn_rot_cw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rot_cw.setToolTip(LanguageManager.tr("organize_rotate_cw"))
        self.btn_rot_cw.clicked.connect(self.rotate_selected_cw)
        h_top.addWidget(self.btn_rot_cw)

        # Sil
        self.btn_delete = QToolButton()
        self.btn_delete.setIcon(ModernIconFactory.icon_trash())
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setToolTip(LanguageManager.tr("organize_delete_pages"))
        self.btn_delete.clicked.connect(self.delete_selected_pages)
        h_top.addWidget(self.btn_delete)

        # Sayfa Ekle
        self.btn_insert = QToolButton()
        self.btn_insert.setIcon(ModernIconFactory.icon_add_page())
        self.btn_insert.setIconSize(QSize(16, 16))
        self.btn_insert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_insert.setToolTip(LanguageManager.tr("organize_insert_page"))
        self.btn_insert.clicked.connect(self.insert_page_action)
        h_top.addWidget(self.btn_insert)

        # Çıkar (Extract)
        self.btn_extract = QToolButton()
        self.btn_extract.setIcon(ModernIconFactory.icon_extract())
        self.btn_extract.setIconSize(QSize(16, 16))
        self.btn_extract.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extract.setToolTip(LanguageManager.tr("organize_extract_pages"))
        self.btn_extract.clicked.connect(self.extract_pages_action)
        h_top.addWidget(self.btn_extract)

        # Böl (Split)
        self.btn_split = QToolButton()
        self.btn_split.setIcon(ModernIconFactory.icon_split())
        self.btn_split.setIconSize(QSize(16, 16))
        self.btn_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_split.setToolTip(LanguageManager.tr("organize_split_doc"))
        self.btn_split.clicked.connect(self.split_doc_action)
        h_top.addWidget(self.btn_split)

        # Değiştir (Replace)
        self.btn_replace = QToolButton()
        self.btn_replace.setIcon(ModernIconFactory.icon_replace_page())
        self.btn_replace.setIconSize(QSize(16, 16))
        self.btn_replace.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_replace.setToolTip(LanguageManager.tr("organize_replace_pages"))
        self.btn_replace.clicked.connect(self.replace_pages_action)
        h_top.addWidget(self.btn_replace)

        # Tümünü Seç
        self.btn_select_all = QToolButton()
        self.btn_select_all.setIcon(ModernIconFactory.icon_select_rect())
        self.btn_select_all.setIconSize(QSize(16, 16))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setToolTip(LanguageManager.tr("organize_select_all"))
        self.btn_select_all.clicked.connect(self.select_all_pages)
        h_top.addWidget(self.btn_select_all)

        h_top.addStretch(1)

        # Kapat Butonu (✕ Close)
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

        # 2. Çok Sütunlu Sayfa Izgarası
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.grid_container = QWidget()
        self.grid_container.setObjectName("GridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(24, 24, 24, 24)
        self.grid_layout.setHorizontalSpacing(18)
        self.grid_layout.setVerticalSpacing(22)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)

        self.apply_theme(self.theme_name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_pages()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.cards:
            self.load_document()

    def load_document(self):
        """Aktif PDF belgesinin sayfalarını yükler ve kartları oluşturur."""
        if not self.isVisible() and (self.main_window and hasattr(self.main_window, 'central_stack') and self.main_window.central_stack.currentWidget() != self):
            return

        # Eski kartları ve düzen öğelerini tamamen temizle
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        self.cards.clear()
        self.selected_pages.clear()
        self.last_clicked_page = None

        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.lbl_page_info.setText(LanguageManager.tr("page_of", total=0))
            return

        total = len(tab_doc.doc)
        curr = getattr(tab_doc, 'current_page_idx', getattr(tab_doc, 'current_page', 0))
        if curr >= total:
            curr = max(0, total - 1)
            tab_doc.current_page_idx = curr
        self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=curr + 1, total=total))

        # Kartları 6 sütunlu olarak ızgaraya yerleştir
        cols = 6
        for page_idx in range(total):
            card = PageThumbnailCard(page_idx, parent=self.grid_container)
            card.clicked.connect(self._on_card_clicked)
            card.doubleClicked.connect(self._on_card_double_clicked)
            card.deleteRequested.connect(self._on_card_delete_requested)
            card.rotateRequested.connect(self._on_card_rotate_requested)
            self.cards.append(card)
            r = page_idx // cols
            c = page_idx % cols
            self.grid_layout.addWidget(card, r, c)

        # İlk aktif sayfayı seç
        if 0 <= curr < total:
            self.selected_pages.add(curr)
            self.cards[curr].set_selected(True, self.theme_name)

        # Küçük resimleri parça parça asenkron yükle (UI kilitlenmesini engeller)
        self._render_thumbnails(start=0, limit=24)

    def retranslate_ui(self):
        self.btn_rot_ccw.setToolTip(LanguageManager.tr("organize_rotate_ccw"))
        self.btn_rot_cw.setToolTip(LanguageManager.tr("organize_rotate_cw"))
        self.btn_delete.setToolTip(LanguageManager.tr("organize_delete_pages"))
        self.btn_insert.setToolTip(LanguageManager.tr("organize_insert_page"))
        self.btn_extract.setToolTip(LanguageManager.tr("organize_extract_pages"))
        self.btn_split.setToolTip(LanguageManager.tr("organize_split_doc"))
        self.btn_replace.setToolTip(LanguageManager.tr("organize_replace_pages"))
        self.btn_select_all.setToolTip(LanguageManager.tr("organize_select_all"))
        self.btn_close.setText(" " + LanguageManager.tr("organize_close_btn"))
        self._update_selection_info()

    def _render_thumbnails(self, start: int = 0, limit: Optional[int] = 24):
        if not self.isVisible() and (self.main_window and hasattr(self.main_window, 'central_stack') and self.main_window.central_stack.currentWidget() != self):
            return
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        end = len(self.cards) if limit is None else min(len(self.cards), start + limit)
        for i in range(start, end):
            if not self.isVisible() and (self.main_window and hasattr(self.main_window, 'central_stack') and self.main_window.central_stack.currentWidget() != self):
                return
            card = self.cards[i]
            if card.page_index < len(tab_doc.doc):
                try:
                    page = tab_doc.doc[card.page_index]
                    pix = page.get_pixmap(dpi=72)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    card.set_pixmap(QPixmap.fromImage(qimg))
                except Exception:
                    pass

        # Kalan kartları akıcı şekilde arka planda işle
        if end < len(self.cards):
            QTimer.singleShot(25, lambda: self._render_thumbnails(start=end, limit=24))

    def _on_card_clicked(self, page_index: int, modifiers):
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Tekil seçim değiştir
            if page_index in self.selected_pages:
                self.selected_pages.remove(page_index)
            else:
                self.selected_pages.add(page_index)
            self.last_clicked_page = page_index
        elif modifiers & Qt.KeyboardModifier.ShiftModifier and self.last_clicked_page is not None:
            # Aralık seçimi
            start = min(self.last_clicked_page, page_index)
            end = max(self.last_clicked_page, page_index)
            self.selected_pages = set(range(start, end + 1))
        else:
            # Tek seçim
            self.selected_pages = {page_index}
            self.last_clicked_page = page_index

        for card in self.cards:
            card.set_selected(card.page_index in self.selected_pages, self.theme_name)

        self._update_selection_info()

    def _on_card_double_clicked(self, page_index: int):
        self.openPageRequested.emit(page_index)

    def _on_card_delete_requested(self, page_index: int):
        self.selected_pages = {page_index}
        for c in self.cards:
            c.set_selected(c.page_index == page_index, self.theme_name)
        self._update_selection_info()
        self.delete_selected_pages()

    def _on_card_rotate_requested(self, page_index: int, angle: int):
        self.selected_pages = {page_index}
        for c in self.cards:
            c.set_selected(c.page_index == page_index, self.theme_name)
        self._update_selection_info()
        self._rotate_pages(angle)

    def _update_selection_info(self):
        total = len(self.cards)
        sel_count = len(self.selected_pages)
        if sel_count > 1:
            self.lbl_page_info.setText(LanguageManager.tr("organize_pages_selected", count=sel_count))
        elif sel_count == 1:
            p = next(iter(self.selected_pages))
            self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=p + 1, total=total))
        else:
            self.lbl_page_info.setText(LanguageManager.tr("page_of", total=total))

    def select_all_pages(self):
        self.selected_pages = set(range(len(self.cards)))
        for card in self.cards:
            card.set_selected(True, self.theme_name)
        self._update_selection_info()

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
            curr = getattr(tab_doc, 'current_page_idx', getattr(tab_doc, 'current_page', 0))
            if 0 <= curr < len(tab_doc.doc):
                self.selected_pages.add(curr)
                if curr < len(self.cards):
                    self.cards[curr].set_selected(True, self.theme_name)

        if not self.selected_pages:
            return

        for p in self.selected_pages:
            if 0 <= p < len(tab_doc.doc):
                page = tab_doc.doc[p]
                page.set_rotation((page.rotation + angle) % 360)

        tab_doc.set_modified(True)
        self.documentModified.emit()
        self._render_thumbnails()

    def delete_selected_pages(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            curr = getattr(tab_doc, 'current_page', getattr(tab_doc, 'current_page_idx', 0))
            if 0 <= curr < len(tab_doc.doc):
                self.selected_pages.add(curr)
                if curr < len(self.cards):
                    self.cards[curr].set_selected(True, self.theme_name)

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

        # Sayfaları sondan başa doğru tab_doc.delete_page ile güvenle sil
        pages_to_delete = sorted(list(self.selected_pages), reverse=True)
        min_p = min(self.selected_pages)

        for p in pages_to_delete:
            tab_doc.delete_page(p)

        self.selected_pages.clear()

        new_total = len(tab_doc.doc)
        if new_total > 0:
            target_page = min(min_p, new_total - 1)
            tab_doc.current_page_idx = target_page
            self.selected_pages = {target_page}

        tab_doc.set_modified(True)
        self.load_document()
        self.documentModified.emit()

    def insert_page_action(self):
        if hasattr(self.main_window, 'show_new_page_dialog'):
            self.main_window.show_new_page_dialog()
            QTimer.singleShot(300, self.load_document)

    def extract_pages_action(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if not self.selected_pages:
            curr = getattr(tab_doc, 'current_page', 0)
            if 0 <= curr < len(tab_doc.doc):
                self.selected_pages.add(curr)
                if curr < len(self.cards):
                    self.cards[curr].set_selected(True, self.theme_name)

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
            QMessageBox.information(self, LanguageManager.tr("app_title"), f"Sayfalar başarıyla çıkarıldı:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"Hata: {e}")

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
                self.selected_pages.add(curr)
                if curr < len(self.cards):
                    self.cards[curr].set_selected(True, self.theme_name)

        if not self.selected_pages:
            return

        src_pdf, _ = QFileDialog.getOpenFileName(self, "Değiştirilecek Kaynak PDF", "", "PDF (*.pdf)")
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
            self.load_document()
            self.documentModified.emit()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"Hata: {e}")

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
            QScrollArea, QWidget#GridContainer {{
                background-color: {c['bg']};
                border: none;
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
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))
        for card in self.cards:
            card._apply_style(theme_name)


# ==============================================================================
# 5. SAĞ ÇEKMECE PANELİ (ModernRightSidebar)
# ==============================================================================
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
        self._thumb_timer.timeout.connect(self._process_thumb_render_queue)
        self.setFixedWidth(320)

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
        self.btn_add.setIcon(ModernIconFactory.icon_plus())
        self.btn_add.setIconSize(QSize(12, 12))
        self.btn_add.setFixedSize(22, 22)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_page"))
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
        self.list_thumbnails.setIconSize(QSize(160, 220))
        self.list_thumbnails.setSpacing(8)
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

        # ======================================================================
        # PANEL 4: ERİŞİLEBİLİRLİK VE SESLİ OKUMA (EMA LIGHTNING TTS)
        # ======================================================================
        self.panel_accessibility = QWidget()
        v_tts = QVBoxLayout(self.panel_accessibility)
        v_tts.setContentsMargins(0, 0, 0, 0)
        v_tts.setSpacing(10)

        # 1. Model Durumu Kartı
        self.card_tts_model = QFrame()
        self.card_tts_model.setObjectName("TTSModelCard")
        v_mcard = QVBoxLayout(self.card_tts_model)
        v_mcard.setContentsMargins(10, 10, 10, 10)
        v_mcard.setSpacing(6)

        h_mhead = QHBoxLayout()
        h_mhead.setSpacing(6)
        lbl_ai_badge = QLabel("⚡ EMA LIGHTNING")
        lbl_ai_badge.setObjectName("TTSBadge")
        h_mhead.addWidget(lbl_ai_badge)
        h_mhead.addStretch(1)

        self.lbl_model_status_dot = QLabel("●")
        self.lbl_model_status_dot.setObjectName("TTSStatusDot")
        h_mhead.addWidget(self.lbl_model_status_dot)

        self.lbl_model_status_text = QLabel(LanguageManager.tr("tts_status_ready"))
        self.lbl_model_status_text.setObjectName("TTSStatusText")
        h_mhead.addWidget(self.lbl_model_status_text)
        v_mcard.addLayout(h_mhead)

        self.lbl_model_desc = QLabel(LanguageManager.tr("tts_model_desc"))
        self.lbl_model_desc.setObjectName("TTSDesc")
        self.lbl_model_desc.setWordWrap(True)
        v_mcard.addWidget(self.lbl_model_desc)

        self.btn_download_model = QPushButton(" " + LanguageManager.tr("tts_btn_download_model"))
        self.btn_download_model.setObjectName("TTSDownloadBtn")
        self.btn_download_model.setIcon(ModernIconFactory.icon_recovery())
        self.btn_download_model.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_model.clicked.connect(self._on_download_model_clicked)
        self.btn_download_model.hide()
        v_mcard.addWidget(self.btn_download_model)

        v_tts.addWidget(self.card_tts_model)

        # 2. Hızlı Eylem Butonları
        self.btn_read_page = QPushButton(" " + LanguageManager.tr("tts_read_page"))
        self.btn_read_page.setObjectName("TTSActionBtn")
        self.btn_read_page.setIcon(ModernIconFactory.icon_view_single())
        self.btn_read_page.setIconSize(QSize(15, 15))
        self.btn_read_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_read_page.clicked.connect(self._read_current_page)
        v_tts.addWidget(self.btn_read_page)

        self.btn_read_selection = QPushButton(" " + LanguageManager.tr("tts_read_selection"))
        self.btn_read_selection.setObjectName("TTSActionBtn")
        self.btn_read_selection.setIcon(ModernIconFactory.icon_cursor())
        self.btn_read_selection.setIconSize(QSize(15, 15))
        self.btn_read_selection.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_read_selection.clicked.connect(self._read_selected_text)
        v_tts.addWidget(self.btn_read_selection)

        # 3. Metin Alanı
        self.txt_tts_input = QTextEdit()
        self.txt_tts_input.setObjectName("TTSTextInput")
        self.txt_tts_input.setPlaceholderText(LanguageManager.tr("tts_no_text_found"))
        self.txt_tts_input.setFixedHeight(115)
        v_tts.addWidget(self.txt_tts_input)

        # 4. Oynatıcı Kontrolleri
        self.card_tts_player = QFrame()
        self.card_tts_player.setObjectName("TTSPlayerCard")
        v_pcard = QVBoxLayout(self.card_tts_player)
        v_pcard.setContentsMargins(10, 10, 10, 10)
        v_pcard.setSpacing(8)

        h_pbtns = QHBoxLayout()
        h_pbtns.setSpacing(8)

        self.btn_tts_play = QPushButton(" " + LanguageManager.tr("tts_play_btn"))
        self.btn_tts_play.setObjectName("TTSPlayBtn")
        self.btn_tts_play.setIcon(ModernIconFactory.icon_play())
        self.btn_tts_play.setIconSize(QSize(14, 14))
        self.btn_tts_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts_play.clicked.connect(self._toggle_play_tts)
        h_pbtns.addWidget(self.btn_tts_play, stretch=1)

        self.btn_tts_pause = QToolButton()
        self.btn_tts_pause.setObjectName("TTSControlBtn")
        self.btn_tts_pause.setIcon(ModernIconFactory.icon_pause())
        self.btn_tts_pause.setIconSize(QSize(14, 14))
        self.btn_tts_pause.setFixedSize(32, 32)
        self.btn_tts_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts_pause.setToolTip(LanguageManager.tr("tts_pause_btn"))
        self.btn_tts_pause.clicked.connect(self._pause_tts)
        h_pbtns.addWidget(self.btn_tts_pause)

        self.btn_tts_stop = QToolButton()
        self.btn_tts_stop.setObjectName("TTSControlBtn")
        self.btn_tts_stop.setIcon(ModernIconFactory.icon_close())
        self.btn_tts_stop.setIconSize(QSize(14, 14))
        self.btn_tts_stop.setFixedSize(32, 32)
        self.btn_tts_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tts_stop.setToolTip(LanguageManager.tr("tts_stop_btn"))
        self.btn_tts_stop.clicked.connect(self._stop_tts)
        h_pbtns.addWidget(self.btn_tts_stop)

        v_pcard.addLayout(h_pbtns)

        # İlerleme Çubuğu ve Süre
        self.progress_tts = QProgressBar()
        self.progress_tts.setObjectName("TTSProgressBar")
        self.progress_tts.setFixedHeight(5)
        self.progress_tts.setTextVisible(False)
        self.progress_tts.setRange(0, 1000)
        self.progress_tts.setValue(0)
        v_pcard.addWidget(self.progress_tts)

        h_pstatus = QHBoxLayout()
        self.lbl_tts_playback_status = QLabel(LanguageManager.tr("tts_status_ready"))
        self.lbl_tts_playback_status.setObjectName("TTSPlaybackStatus")
        h_pstatus.addWidget(self.lbl_tts_playback_status, stretch=1)

        self.lbl_tts_time = QLabel("00:00")
        self.lbl_tts_time.setObjectName("TTSTimeLabel")
        h_pstatus.addWidget(self.lbl_tts_time)
        v_pcard.addLayout(h_pstatus)

        # Ses Seviyesi Kaydırıcısı
        h_vol = QHBoxLayout()
        h_vol.setSpacing(6)
        lbl_vol_icon = QLabel()
        lbl_vol_icon.setPixmap(ModernIconFactory.icon_speech().pixmap(14, 14))
        h_vol.addWidget(lbl_vol_icon)

        self.slider_tts_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_tts_vol.setObjectName("TTSVolumeSlider")
        self.slider_tts_vol.setRange(0, 100)
        self.slider_tts_vol.setValue(100)
        self.slider_tts_vol.valueChanged.connect(self._on_volume_changed)
        h_vol.addWidget(self.slider_tts_vol, stretch=1)
        v_pcard.addLayout(h_vol)

        v_tts.addWidget(self.card_tts_player)
        v_tts.addStretch(1)

        self.main_stack.addWidget(self.panel_accessibility)

        # Motor ve Sinyal Bağlantıları
        self.speech_engine = AuraSpeechEngine(self)
        self.speech_engine.state_changed.connect(self._on_tts_state_changed)
        self.speech_engine.reading_started.connect(self._on_tts_reading_started)
        self.speech_engine.reading_finished.connect(self._on_tts_reading_finished)
        self.speech_engine.playback_progress.connect(self._on_tts_playback_progress)
        self.speech_engine.error_occurred.connect(self._on_tts_error)
        self.speech_engine.model_status_changed.connect(self._on_tts_model_status_changed)
        self.speech_engine.check_and_notify_status()

        main_layout.addWidget(self.main_stack, stretch=1)
        self.apply_theme(self.theme_name)

    def set_panel(self, panel_name: str):
        """Çekmeceyi 'thumbnails', 'bookmarks', 'attachments', 'comments' veya 'accessibility' paneline geçirir."""
        self.current_panel = panel_name
        if panel_name == "comments":
            self.tab_container.show()
            self.btn_tab_comments.setChecked(True)
            self.main_stack.setCurrentIndex(1)
            self.lbl_head_title.setText(LanguageManager.tr("dock_title"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_comments().pixmap(16, 16))
            self.btn_add.hide()
            self.load_comments()
        elif panel_name == "thumbnails":
            self.tab_container.show()
            self.btn_tab_thumbs.setChecked(True)
            self.main_stack.setCurrentIndex(2)
            self.lbl_head_title.setText(LanguageManager.tr("dock_title"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_thumbnails().pixmap(16, 16))
            self.btn_add.show()
            self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_page"))
            self.load_thumbnails()
        elif panel_name == "attachments":
            self.tab_container.show()
            self.btn_tab_attachments.setChecked(True)
            self.main_stack.setCurrentIndex(3)
            self.lbl_head_title.setText(LanguageManager.tr("dock_title"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_attachment().pixmap(16, 16))
            self.btn_add.show()
            self.btn_add.setToolTip(LanguageManager.tr("sidebar_add_attachment"))
            self.load_attachments()
        elif panel_name == "accessibility":
            self.tab_container.hide()
            self.main_stack.setCurrentIndex(4)
            self.lbl_head_title.setText(LanguageManager.tr("accessibility_panel_title"))
            self.lbl_head_icon.setPixmap(ModernIconFactory.icon_accessibility().pixmap(16, 16))
            self.btn_add.hide()
            self.load_accessibility()
        else:
            self.tab_container.show()
            self.btn_tab_bookmarks.setChecked(True)
            self.main_stack.setCurrentIndex(0)
            self.lbl_head_title.setText(LanguageManager.tr("dock_title"))
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

        if self.current_panel == "accessibility":
            self.lbl_head_title.setText(LanguageManager.tr("accessibility_panel_title"))
        else:
            self.lbl_head_title.setText(LanguageManager.tr("dock_title"))

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
        if hasattr(self, 'btn_read_page'):
            self.btn_read_page.setText(" " + LanguageManager.tr("tts_read_page"))
            self.btn_read_selection.setText(" " + LanguageManager.tr("tts_read_selection"))
            self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
            self.btn_tts_pause.setToolTip(LanguageManager.tr("tts_pause_btn"))
            self.btn_tts_stop.setToolTip(LanguageManager.tr("tts_stop_btn"))
            self.btn_download_model.setText(" " + LanguageManager.tr("tts_btn_download_model"))
            self.lbl_model_desc.setText(LanguageManager.tr("tts_model_desc"))
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
        pix = QPixmap(160, 220)
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
        for idx in range(total_pages):
            is_bm = idx in bookmarked_pages
            placeholder_pix = self._create_placeholder_pixmap(is_bm)
            item = QListWidgetItem(QIcon(placeholder_pix), f"{idx + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setSizeHint(QSize(180, 240))
            if is_bm:
                item.setToolTip(LanguageManager.tr("sidebar_page_bookmarked", page=idx + 1))
            else:
                item.setToolTip(LanguageManager.tr("sidebar_page_tooltip", page=idx + 1))
            self.list_thumbnails.addItem(item)

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

        thumb_w = 160
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

        if item and idx >= 0:
            act_goto = menu.addAction(ModernIconFactory.icon_cursor(), LanguageManager.tr("sidebar_goto_page", page=idx + 1))
            if idx in self.get_bookmarked_pages():
                act_show_bm = menu.addAction(ModernIconFactory.icon_bookmark(), LanguageManager.tr("sidebar_show_in_toc"))
            menu.addSeparator()
            act_rotate_cw = menu.addAction(ModernIconFactory.icon_rotate(), LanguageManager.tr("sidebar_rotate_cw"))
            act_rotate_ccw = menu.addAction(ModernIconFactory.icon_undo(), LanguageManager.tr("sidebar_rotate_ccw"))
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
        path, _ = QFileDialog.getOpenFileName(self, LanguageManager.tr("sidebar_add_attachment"))
        if not path:
            return
        try:
            with open(path, "rb") as f:
                content = f.read()
            basename = os.path.basename(path)
            tab_doc.doc.embfile_add(basename, content)
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

    # ==========================================================================
    # ERİŞİLEBİLİRLİK VE SESLİ OKUMA (EMA LIGHTNING TTS) İŞLEMLERİ
    # ==========================================================================
    def load_accessibility(self):
        """Erişilebilirlik ve TTS panelini günceller."""
        if hasattr(self, 'speech_engine'):
            self.speech_engine.check_and_notify_status()
        tab_doc = self.main_window.get_current_tab_doc() if self.main_window else None
        if tab_doc and getattr(tab_doc, 'selected_text', '').strip():
            self.txt_tts_input.setPlainText(tab_doc.selected_text.strip())

    def _read_current_page(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        curr_idx = getattr(tab_doc, 'current_page_idx', 0)
        try:
            page = tab_doc.doc[curr_idx]
            text = page.get_text().strip()
        except Exception:
            text = ""
        cleaned = clean_text_for_speech(text)
        if not cleaned:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        self.txt_tts_input.setPlainText(cleaned)
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.speech_engine.speak(cleaned)

    def _read_selected_text(self):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        text = getattr(tab_doc, 'selected_text', '').strip() if tab_doc else ''
        if not text:
            text = self.txt_tts_input.toPlainText().strip()
        cleaned = clean_text_for_speech(text)
        if not cleaned:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_no_text_found"))
            return
        self.txt_tts_input.setPlainText(cleaned)
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_reading"))
        self.speech_engine.speak(cleaned)

    def _toggle_play_tts(self):
        if self.speech_engine.is_paused():
            self.speech_engine.resume()
        elif self.speech_engine.is_speaking():
            self.speech_engine.pause()
        else:
            text = self.txt_tts_input.toPlainText().strip()
            if not text:
                self._read_current_page()
            else:
                self.speech_engine.speak(text)

    def _pause_tts(self):
        self.speech_engine.pause()

    def _stop_tts(self):
        self.speech_engine.stop()
        self.progress_tts.setValue(0)
        self.lbl_tts_time.setText("00:00")
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_stopped"))

    def _on_volume_changed(self, val: int):
        self.speech_engine.set_volume(val)

    def _on_download_model_clicked(self):
        self.btn_download_model.setEnabled(False)
        self.lbl_model_status_text.setText(LanguageManager.tr("tts_status_downloading"))
        self.speech_engine.download_model()

    def _on_tts_model_status_changed(self, is_ready: bool, message: str):
        if is_ready:
            self.lbl_model_status_dot.setText("●")
            self.lbl_model_status_dot.setStyleSheet("color: #10b981; font-size: 14px;")
            self.lbl_model_status_text.setText(LanguageManager.tr("tts_status_ready"))
            self.btn_download_model.hide()
        else:
            self.lbl_model_status_dot.setText("●")
            self.lbl_model_status_dot.setStyleSheet("color: #f59e0b; font-size: 14px;")
            self.lbl_model_status_text.setText(message)
            self.btn_download_model.show()
            self.btn_download_model.setEnabled(True)

    def _on_tts_state_changed(self, is_speaking: bool):
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

    def _on_tts_reading_finished(self):
        self.btn_tts_play.setText(" " + LanguageManager.tr("tts_play_btn"))
        self.btn_tts_play.setIcon(ModernIconFactory.icon_play("#ffffff"))
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_ready"))
        self.progress_tts.setValue(0)
        self.lbl_tts_time.setText("00:00")

    def _on_tts_playback_progress(self, pos_ms: int, dur_ms: int):
        if dur_ms > 0:
            frac = int((pos_ms / dur_ms) * 1000)
            self.progress_tts.setValue(min(1000, frac))
            sec = int(pos_ms / 1000)
            m = sec // 60
            s = sec % 60
            tot_sec = int(dur_ms / 1000)
            tm = tot_sec // 60
            ts = tot_sec % 60
            self.lbl_tts_time.setText(f"{m:02d}:{s:02d} / {tm:02d}:{ts:02d}")

    def _on_tts_error(self, err: str):
        self.lbl_tts_playback_status.setText(LanguageManager.tr("tts_status_error", error=err[:40]))
        QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("tts_status_error", error=err))

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
                border: 1.5px solid {c['border']};
                border-radius: 8px;
                padding: 6px;
                margin: 4px 4px;
                color: {c['text']};
                font-size: 11px;
                font-weight: 600;
            }}
            #RightRailThumbnailsList::item:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
            }}
            #RightRailThumbnailsList::item:selected {{
                background-color: {c['surface_hover']};
                border: 2px solid {c['accent']};
                color: {c['accent']};
                font-weight: 700;
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
            #TTSModelCard, #TTSPlayerCard {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            #TTSBadge {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                font-size: 10px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
            }}
            #TTSStatusDot {{
                font-size: 14px;
            }}
            #TTSStatusText {{
                color: {c['text_muted']};
                font-size: 11px;
                font-weight: 600;
            }}
            #TTSDesc {{
                color: {c['text_muted']};
                font-size: 11px;
                line-height: 1.3;
            }}
            #TTSActionBtn {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}
            #TTSActionBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
                color: {c['accent']};
            }}
            #TTSTextInput {{
                background-color: {c['card_bg']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }}
            #TTSTextInput:focus {{
                border: 1.5px solid {c['accent']};
            }}
            #TTSPlayBtn {{
                background-color: {c['accent']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 700;
            }}
            #TTSPlayBtn:hover {{
                background-color: {c['accent_hover']};
            }}
            #TTSControlBtn {{
                background-color: {c['card_bg']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                color: {c['text']};
            }}
            #TTSControlBtn:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['accent']};
            }}
            #TTSProgressBar {{
                background-color: {c['border_subtle']};
                border-radius: 2px;
                border: none;
            }}
            #TTSProgressBar::chunk {{
                background-color: {c['accent']};
                border-radius: 2px;
            }}
            #TTSPlaybackStatus {{
                color: {c['text_muted']};
                font-size: 11px;
            }}
            #TTSTimeLabel {{
                color: {c['accent']};
                font-size: 11px;
                font-weight: 600;
            }}
            #TTSDownloadBtn {{
                background-color: {c['accent_light']};
                color: {c['accent']};
                border: 1px solid {c['accent']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #TTSDownloadBtn:hover {{
                background-color: {c['accent']};
                color: #ffffff;
            }}
        """)
        if hasattr(self, 'btn_close'):
            self.btn_close.setIcon(ModernIconFactory.icon_close(c['text']))


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
    pageJumpRequested = pyqtSignal(int)
    prevPageRequested = pyqtSignal()
    nextPageRequested = pyqtSignal()
    zoomInRequested = pyqtSignal()
    zoomOutRequested = pyqtSignal()
    fitPageRequested = pyqtSignal()
    fitWidthRequested = pyqtSignal()
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
            ("accessibility", ModernIconFactory.icon_accessibility(), "right_rail_accessibility"),
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

        # Alt Zoom ve Sayfa Kontrolleri
        # Sayfa No Kutusu ve Toplam Sayfa Sayısı
        page_box = QHBoxLayout()
        page_box.setContentsMargins(0, 2, 0, 2)
        page_box.setSpacing(2)
        page_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.txt_page = QLineEdit("1")
        self.txt_page.setObjectName("RailPageInput")
        self.txt_page.setFixedWidth(30)
        self.txt_page.setFixedHeight(24)
        self.txt_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_page.setValidator(QIntValidator(1, 99999, self))
        self.txt_page.setToolTip(LanguageManager.tr("page_input_tip"))
        self.txt_page.returnPressed.connect(self._on_page_submitted)
        page_box.addWidget(self.txt_page)

        self.lbl_total = QLabel("/ 1")
        self.lbl_total.setObjectName("RailPageTotal")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        page_box.addWidget(self.lbl_total)

        main_layout.addLayout(page_box)

        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(ModernIconFactory.icon_chevron_up())
        self.btn_prev.setIconSize(QSize(12, 12))
        self.btn_prev.setFixedSize(40, 22)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self.prevPageRequested.emit)
        main_layout.addWidget(self.btn_prev)

        self.btn_next = QToolButton()
        self.btn_next.setIcon(ModernIconFactory.icon_chevron_down())
        self.btn_next.setIconSize(QSize(12, 12))
        self.btn_next.setFixedSize(40, 22)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.nextPageRequested.emit)
        main_layout.addWidget(self.btn_next)

        # Zoom Yüzdesi (Sağ alt panelde net ve okunaklı)
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setObjectName("RailZoom")
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.lbl_zoom)

        # Sığdır
        self.btn_fit = QToolButton()
        self.btn_fit.setIcon(ModernIconFactory.icon_fit_page())
        self.btn_fit.setIconSize(QSize(16, 16))
        self.btn_fit.setFixedSize(40, 28)
        self.btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
        self.btn_fit.clicked.connect(self.fitPageRequested.emit)
        main_layout.addWidget(self.btn_fit)

        # Zoom +
        self.btn_zin = QToolButton()
        self.btn_zin.setIcon(ModernIconFactory.icon_plus())
        self.btn_zin.setIconSize(QSize(12, 12))
        self.btn_zin.setFixedSize(40, 24)
        self.btn_zin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zin.clicked.connect(self.zoomInRequested.emit)
        main_layout.addWidget(self.btn_zin)

        # Zoom -
        self.btn_zout = QToolButton()
        self.btn_zout.setIcon(ModernIconFactory.icon_minus())
        self.btn_zout.setIconSize(QSize(12, 12))
        self.btn_zout.setFixedSize(40, 24)
        self.btn_zout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zout.clicked.connect(self.zoomOutRequested.emit)
        main_layout.addWidget(self.btn_zout)

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
            "accessibility": "right_rail_accessibility",
        }
        for rid, key in tip_map.items():
            if rid in self.buttons:
                self.buttons[rid].setToolTip(LanguageManager.tr(key))
        self.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
        self.txt_page.setToolTip(LanguageManager.tr("page_input_tip"))

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
        if rail_id in ("bookmarks", "comments", "attachments"):
            rail_id = "thumbnails"
        self.active_rail_id = rail_id
        for r, b in self.buttons.items():
            b.setChecked(r == rail_id)

    def _on_page_submitted(self):
        text = self.txt_page.text().strip()
        if text.isdigit():
            val = int(text)
            self.pageJumpRequested.emit(val - 1)

    def update_page_info(self, current: int, total: int):
        self.total_pages = max(1, total)
        if not self.txt_page.hasFocus():
            self.txt_page.setText(str(current + 1))
        self.lbl_total.setText(f"/ {self.total_pages}")

    def update_zoom_info(self, zoom_percent: int):
        self.lbl_zoom.setText(f"{zoom_percent}%")

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
            ("print", "print_btn", ModernIconFactory.icon_print("#a855f7")),
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
