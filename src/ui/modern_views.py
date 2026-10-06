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
from typing import List, Dict, Optional, Set, Any
import pymupdf as fitz

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QToolButton,
    QPushButton, QScrollArea, QGridLayout, QFrame, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QMenu,
    QDialog, QSizePolicy, QApplication, QSlider, QMessageBox, QFileDialog,
    QHeaderView, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QRect, QTimer, QThread, QUrl
from PyQt6.QtGui import (
    QIcon, QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont,
    QPainterPath, QCursor, QKeySequence, QShortcut, QDesktopServices
)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory


def get_modern_theme_colors(theme_name: str = "light") -> Dict[str, str]:
    """Tüm temalarla kusursuz uyumlu renk paleti."""
    palettes = {
        "light": {
            "bg": "#f0f2f5",
            "tab_bar_bg": "#eaedf1",
            "surface": "#ffffff",
            "surface_hover": "#f1f5f9",
            "surface_active": "#e2e8f0",
            "border": "#e2e8f0",
            "border_subtle": "#edf2f7",
            "text": "#0f172a",
            "text_muted": "#64748b",
            "accent": "#0284c7",
            "accent_hover": "#0369a1",
            "accent_light": "rgba(2, 132, 199, 0.12)",
            "danger": "#ef4444",
            "tab_bg": "#e2e6ea",
            "tab_active": "#ffffff",
            "tab_text": "#475569",
            "tab_active_text": "#0f172a",
            "badge_bg": "#f1f5f9",
            "card_bg": "#ffffff",
            "card_border": "#cbd5e1",
        },
        "gray": {
            "bg": "#232528",
            "surface": "#2b2d30",
            "surface_hover": "#35383c",
            "surface_active": "#3e4248",
            "border": "#3c3f44",
            "border_subtle": "#32353a",
            "text": "#f1f5f9",
            "text_muted": "#94a3b8",
            "accent": "#60a5fa",
            "accent_hover": "#3b82f6",
            "accent_light": "rgba(96, 165, 250, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#1e2022",
            "tab_active": "#2b2d30",
            "tab_text": "#94a3b8",
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
            "border": "#2c2c2c",
            "border_subtle": "#202020",
            "text": "#f3f4f6",
            "text_muted": "#9ca3af",
            "accent": "#388bfd",
            "accent_hover": "#1d76f2",
            "accent_light": "rgba(56, 139, 253, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#141414",
            "tab_active": "#1c1c1c",
            "tab_text": "#9ca3af",
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
            "text_muted": "#94a3b8",
            "accent": "#38bdf8",
            "accent_hover": "#0ea5e9",
            "accent_light": "rgba(56, 189, 248, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#141922",
            "tab_active": "#222b3a",
            "tab_text": "#94a3b8",
            "tab_active_text": "#f0f6fc",
            "badge_bg": "#2f3b4f",
            "card_bg": "#222b3a",
            "card_border": "#3b4a64",
        },
        "emerald": {
            "bg": "#071410",
            "surface": "#112a21",
            "surface_hover": "#183c2f",
            "surface_active": "#214f3e",
            "border": "#1a3d30",
            "border_subtle": "#142f25",
            "text": "#ecfdf5",
            "text_muted": "#a7f3d0",
            "accent": "#10b981",
            "accent_hover": "#059669",
            "accent_light": "rgba(16, 185, 129, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#0b1c16",
            "tab_active": "#112a21",
            "tab_text": "#6ee7b7",
            "tab_active_text": "#ecfdf5",
            "badge_bg": "#183c2f",
            "card_bg": "#112a21",
            "card_border": "#1a3d30",
        },
        "purple": {
            "bg": "#10091a",
            "surface": "#201435",
            "surface_hover": "#2f1d4d",
            "surface_active": "#3f2666",
            "border": "#321f52",
            "border_subtle": "#271840",
            "text": "#faf5ff",
            "text_muted": "#d8b4fe",
            "accent": "#a855f7",
            "accent_hover": "#9333ea",
            "accent_light": "rgba(168, 85, 247, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#140c22",
            "tab_active": "#201435",
            "tab_text": "#c084fc",
            "tab_active_text": "#faf5ff",
            "badge_bg": "#2f1d4d",
            "card_bg": "#201435",
            "card_border": "#3b2561",
        },
        "crimson": {
            "bg": "#15070b",
            "surface": "#2d1118",
            "surface_hover": "#401923",
            "surface_active": "#54212e",
            "border": "#441924",
            "border_subtle": "#36141d",
            "text": "#fff1f2",
            "text_muted": "#fecdd3",
            "accent": "#f43f5e",
            "accent_hover": "#e11d48",
            "accent_light": "rgba(244, 63, 94, 0.18)",
            "danger": "#f87171",
            "tab_bg": "#1a0a0f",
            "tab_active": "#2d1118",
            "tab_text": "#fb7185",
            "tab_active_text": "#fff1f2",
            "badge_bg": "#401923",
            "card_bg": "#2d1118",
            "card_border": "#4f1d2a",
        },
        "vice_city": {
            "bg": "#10001a",
            "surface": "#240e3b",
            "surface_hover": "#381458",
            "surface_active": "#4d1c78",
            "border": "#3d1663",
            "border_subtle": "#2f114d",
            "text": "#fdf2f8",
            "text_muted": "#e2d1f0",
            "accent": "#ff2a85",
            "accent_hover": "#e0186f",
            "accent_light": "rgba(255, 42, 133, 0.20)",
            "danger": "#ff3366",
            "tab_bg": "#160524",
            "tab_active": "#240e3b",
            "tab_text": "#d8b4fe",
            "tab_active_text": "#ffffff",
            "badge_bg": "#381458",
            "card_bg": "#240e3b",
            "card_border": "#ff2a85",
        },
        "apple": {
            "bg": "#0e1014",
            "surface": "#1a1d24",
            "surface_hover": "#252932",
            "surface_active": "#323744",
            "border": "#2d323e",
            "border_subtle": "#222630",
            "text": "#f5f5f7",
            "text_muted": "#98989d",
            "accent": "#0a84ff",
            "accent_hover": "#0071e3",
            "accent_light": "rgba(10, 132, 255, 0.20)",
            "danger": "#ff453a",
            "tab_bg": "#121419",
            "tab_active": "#1a1d24",
            "tab_text": "#98989d",
            "tab_active_text": "#ffffff",
            "badge_bg": "#252932",
            "card_bg": "#1a1d24",
            "card_border": "#2d323e",
        }
    }
    return palettes.get(theme_name, palettes["light"])


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
        layout.addWidget(self.lbl_title, stretch=1)

        # Kapat Butonu
        self.btn_close = QToolButton()
        self.btn_close.setIcon(ModernIconFactory.icon_close())
        self.btn_close.setIconSize(QSize(10, 10))
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip(LanguageManager.tr("close_tab"))
        self.btn_close.clicked.connect(lambda: self.closeRequested.emit(self.index))
        layout.addWidget(self.btn_close)

        self._apply_style("light")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def set_active(self, active: bool, theme_name: str = "light"):
        self.is_active = active
        self._apply_style(theme_name)

    def set_title(self, title: str):
        self.title = title
        self.lbl_title.setText(title)
        self.setToolTip(title)

    def _apply_style(self, theme_name: str = "light"):
        c = get_modern_theme_colors(theme_name)
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
                QToolButton {{
                    background: transparent;
                    border: none;
                    border-radius: 9px;
                    color: {c['text_muted']};
                }}
                QToolButton:hover {{
                    background-color: {c['surface_hover']};
                    color: {c['danger']};
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
                QToolButton {{
                    background: transparent;
                    border: none;
                    border-radius: 9px;
                    color: {c['text_muted']};
                }}
                QToolButton:hover {{
                    background-color: {c['surface_active']};
                    color: {c['danger']};
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

        # 4. Sağ Taraf Kısayolları (Discord & Bilgi)
        self.btn_discord = QToolButton()
        self.btn_discord.setIcon(ModernIconFactory.icon_discord("#5865f2"))
        self.btn_discord.setIconSize(QSize(14, 14))
        self.btn_discord.setText(" Discord")
        self.btn_discord.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_discord.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discord.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/aurapdf")))
        layout.addWidget(self.btn_discord)

        self.btn_help = QToolButton()
        self.btn_help.setIcon(ModernIconFactory.icon_info())
        self.btn_help.setIconSize(QSize(14, 14))
        self.btn_help.setFixedSize(28, 28)
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setToolTip(LanguageManager.tr("shortcuts_title"))
        self.btn_help.clicked.connect(self.helpRequested.emit)
        layout.addWidget(self.btn_help)

        self.apply_theme(self.theme_name)

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
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {c['text_muted']};
                padding: 0 8px;
                font-weight: 500;
                font-size: 12px;
            }}
            QToolButton:hover {{
                background-color: {c['surface_hover']};
                border-color: {c['border']};
                color: {c['text']};
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
# 2. MODERN ÜST GEZİNME VE EYLEM ÇUBUĞU (ModernHeaderBar)
# ==============================================================================
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.theme_name = "light"
        self.current_mode = "all_tools"
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
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
        # Bilgi (i)
        self.btn_help = QToolButton()
        self.btn_help.setIcon(ModernIconFactory.icon_info())
        self.btn_help.setIconSize(QSize(16, 16))
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_help.setToolTip(LanguageManager.tr("shortcuts_title"))
        self.btn_help.clicked.connect(self.helpRequested.emit)
        layout.addWidget(self.btn_help)

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

        # Ayarlar
        self.btn_settings = QToolButton()
        self.btn_settings.setIcon(ModernIconFactory.icon_settings())
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip(LanguageManager.tr("settings_title"))
        self.btn_settings.clicked.connect(self.settingsRequested.emit)
        layout.addWidget(self.btn_settings)

        self.apply_theme(self.theme_name)

    def set_mode(self, mode_id: str):
        self.current_mode = mode_id
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode_id)
        self.modeChanged.emit(mode_id)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
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
                color: {c['text_muted']};
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
        self.lbl_icon.setPixmap(icon.pixmap(18, 18))
        self.lbl_icon.setFixedSize(18, 18)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(label_text)
        layout.addWidget(self.lbl_text, stretch=1)

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
        self.setFixedWidth(248)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(6)

        # Başlık ve Kapat Butonu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(6, 0, 4, 6)
        lbl_head = QLabel(LanguageManager.tr("nav_all_tools"))
        lbl_head.setStyleSheet("font-size: 15px; font-weight: 700;")
        h_head.addWidget(lbl_head)
        h_head.addStretch(1)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(btn_close)
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
        tool_specs = [
            ("export_pdf", "tool_export_pdf", ModernIconFactory.icon_export_pdf("#0284c7"), "#0284c7"),
            ("fill_sign", "tool_fill_sign", ModernIconFactory.icon_fill_sign("#8b5cf6"), "#8b5cf6"),
            ("edit_pdf", "tool_edit_pdf", ModernIconFactory.icon_edit_content("#ec4899"), "#ec4899"),
            ("create_pdf", "tool_create_pdf", ModernIconFactory.icon_new_document("#ef4444"), "#ef4444"),
            ("combine_files", "tool_combine_files", ModernIconFactory.icon_combine_files("#0284c7"), "#0284c7"),
            ("organize_pages", "tool_organize_pages", ModernIconFactory.icon_organize("#10b981"), "#10b981"),
            ("add_comments", "tool_add_comments", ModernIconFactory.icon_comments("#f97316"), "#f97316"),
            ("scan_ocr", "tool_scan_ocr", ModernIconFactory.icon_ocr("#10b981"), "#10b981"),
            ("protect_pdf", "tool_protect_pdf", ModernIconFactory.icon_lock("#0284c7"), "#0284c7"),
            ("redact_pdf", "tool_redact_pdf", ModernIconFactory.icon_redact("#ef4444"), "#ef4444"),
            ("compress_pdf", "tool_compress_pdf", ModernIconFactory.icon_compress("#ef4444"), "#ef4444"),
            ("prepare_form", "tool_prepare_form", ModernIconFactory.icon_prepare_form("#9333ea"), "#9333ea"),
            ("add_stamp", "tool_add_stamp", ModernIconFactory.icon_stamp("#a855f7"), "#a855f7"),
            ("use_certificate", "tool_use_certificate", ModernIconFactory.icon_certificate("#0284c7"), "#0284c7"),
        ]

        for tid, key, icon, col in tool_specs:
            item = ModernToolItemWidget(tid, LanguageManager.tr(key), icon, col, parent=tools_container)
            item.clicked.connect(self._on_item_clicked)
            self.v_tools.addWidget(item)
            self.items[tid] = item

        # 'Daha fazla gör' bağlantısı
        btn_view_more = QPushButton(LanguageManager.tr("tool_view_more"))
        btn_view_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_more.setStyleSheet("border: none; text-align: left; padding: 8px 12px; font-weight: 600;")
        btn_view_more.clicked.connect(lambda: self.toolTriggered.emit("view_more"))
        self.v_tools.addWidget(btn_view_more)
        self.v_tools.addStretch(1)

        scroll.setWidget(tools_container)
        main_layout.addWidget(scroll)

        self.apply_theme(self.theme_name)
        self.set_active_tool("organize_pages")

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
                border-right: 1px solid {c['border']};
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
                color: {c['accent']};
            }}
            QPushButton:hover {{
                color: {c['accent_hover']};
            }}
        """)
        for item in self.items.values():
            item._apply_style(theme_name)


# ==============================================================================
# 3A. BAĞLAMSAL ÇEKMECELER (ModernExportDrawer & ModernEditDrawer)
# ==============================================================================
class ModernDrawerItemWidget(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, item_id: str, title: str, icon: QIcon, badge_text: str = "Ready", is_ready: bool = True, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.item_id = item_id
        self.title = title
        self.badge_text = badge_text
        self.is_ready = is_ready
        self.theme_name = "light"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(icon.pixmap(18, 18))
        self.lbl_icon.setFixedSize(18, 18)
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(title)
        self.lbl_text.setObjectName("DrawerItemText")
        layout.addWidget(self.lbl_text, stretch=1)

        self.lbl_badge = QLabel(badge_text)
        self.lbl_badge.setObjectName("DrawerItemBadge")
        layout.addWidget(self.lbl_badge)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)

    def _apply_style(self, theme_name: str):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        badge_bg = "rgba(16, 185, 129, 0.15)" if self.is_ready else "rgba(148, 163, 184, 0.15)"
        badge_col = "#10b981" if self.is_ready else "#94a3b8"
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
                background-color: {badge_bg};
                color: {badge_col};
                border-radius: 7px;
                padding: 1px 6px;
                font-size: 9.5px;
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

        lbl_head = QLabel(LanguageManager.tr("drawer_export_title"))
        lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(lbl_head)
        h_head.addStretch(1)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(btn_close)
        main_layout.addLayout(h_head)

        # Kategori Başlığı: EXPORT TO
        lbl_cat = QLabel(LanguageManager.tr("drawer_export_to"))
        lbl_cat.setObjectName("CategoryHeader")
        main_layout.addWidget(lbl_cat)

        # Liste Kaydırma Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        v_items = QVBoxLayout(container)
        v_items.setContentsMargins(0, 0, 0, 0)
        v_items.setSpacing(2)

        ready_text = LanguageManager.tr("badge_ready")
        self.items: List[ModernDrawerItemWidget] = []
        specs = [
            ("word", "drawer_export_word", ModernIconFactory.icon_word("#0284c7"), ready_text, True),
            ("xlsx", "drawer_export_xlsx", ModernIconFactory.icon_excel("#10b981"), "M10", False),
            ("pptx", "drawer_export_pptx", ModernIconFactory.icon_pptx("#ea580c"), "M10", False),
            ("png", "drawer_export_png", ModernIconFactory.icon_image("#0284c7"), ready_text, True),
            ("all_images", "drawer_export_all_images", ModernIconFactory.icon_image_gallery("#0284c7"), ready_text, True),
            ("html", "drawer_export_html", ModernIconFactory.icon_html("#0284c7"), ready_text, True),
            ("rtf", "drawer_export_rtf", ModernIconFactory.icon_txt("#10b981"), ready_text, True),
            ("txt", "drawer_export_txt", ModernIconFactory.icon_txt("#0284c7"), ready_text, True),
            ("eps", "drawer_export_eps", ModernIconFactory.icon_eps("#8b5cf6"), "M10", False),
        ]

        for cid, key, icon, badge, is_ready in specs:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self.exportTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernExportDrawer {{
                background-color: {c['surface']};
                border-right: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 10px;
                font-weight: 700;
                padding-top: 6px;
                padding-bottom: 2px;
                letter-spacing: 0.5px;
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

        lbl_head = QLabel(LanguageManager.tr("drawer_edit_title"))
        lbl_head.setStyleSheet("font-size: 14px; font-weight: 700;")
        h_head.addWidget(lbl_head)
        h_head.addStretch(1)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(btn_close)
        main_layout.addLayout(h_head)

        # Bilgilendirme Kutusu
        self.notice_box = QFrame()
        self.notice_box.setObjectName("NoticeBox")
        v_notice = QVBoxLayout(self.notice_box)
        v_notice.setContentsMargins(10, 8, 10, 8)
        lbl_notice = QLabel(LanguageManager.tr("drawer_edit_notice"))
        lbl_notice.setWordWrap(True)
        lbl_notice.setStyleSheet("font-size: 11px; line-height: 1.2;")
        v_notice.addWidget(lbl_notice)
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

        ready_text = LanguageManager.tr("badge_ready")
        self.items: List[ModernDrawerItemWidget] = []

        # Grup 1: MODIFY PAGE
        lbl_g1 = QLabel(LanguageManager.tr("drawer_group_modify_page"))
        lbl_g1.setObjectName("CategoryHeader")
        v_items.addWidget(lbl_g1)

        specs_modify = [
            ("rotate", "drawer_edit_rotate", ModernIconFactory.icon_rotate("#ec4899"), ready_text, True),
            ("insert", "drawer_edit_insert", ModernIconFactory.icon_insert("#ec4899"), ready_text, True),
            ("delete", "drawer_edit_delete", ModernIconFactory.icon_trash("#ec4899"), ready_text, True),
            ("extract", "drawer_edit_extract", ModernIconFactory.icon_extract("#ec4899"), ready_text, True),
            ("organize", "tool_organize_pages", ModernIconFactory.icon_organize("#ec4899"), ready_text, True),
        ]
        for cid, key, icon, badge, is_ready in specs_modify:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self.editTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        # Grup 2: ADD CONTENT
        lbl_g2 = QLabel(LanguageManager.tr("drawer_group_add_content"))
        lbl_g2.setObjectName("CategoryHeader")
        v_items.addWidget(lbl_g2)

        specs_add = [
            ("edit_text_images", "drawer_edit_text_images", ModernIconFactory.icon_edit_content("#ec4899"), ready_text, True),
            ("text", "drawer_edit_text", ModernIconFactory.icon_text_tool("#ec4899"), ready_text, True),
            ("image", "drawer_edit_image", ModernIconFactory.icon_image("#ec4899"), ready_text, True),
            ("header_footer", "drawer_edit_header_footer", ModernIconFactory.icon_header_footer("#ec4899"), ready_text, True),
            ("watermark", "drawer_edit_watermark", ModernIconFactory.icon_watermark("#ec4899"), ready_text, True),
            ("link", "drawer_edit_link", ModernIconFactory.icon_link("#ec4899"), ready_text, True),
            ("bates", "drawer_edit_bates", ModernIconFactory.icon_bates("#ec4899"), ready_text, True),
            ("background", "drawer_edit_background", ModernIconFactory.icon_background("#ec4899"), ready_text, True),
            ("attach", "drawer_edit_attach", ModernIconFactory.icon_attachment("#ec4899"), "M12", False),
        ]
        for cid, key, icon, badge, is_ready in specs_add:
            it = ModernDrawerItemWidget(cid, LanguageManager.tr(key), icon, badge, is_ready, parent=container)
            it.clicked.connect(self.editTriggered.emit)
            v_items.addWidget(it)
            self.items.append(it)

        v_items.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        self.apply_theme(self.theme_name)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernEditDrawer {{
                background-color: {c['surface']};
                border-right: 1px solid {c['border']};
            }}
            QScrollArea, QWidget {{
                background-color: {c['surface']};
            }}
            QLabel {{
                color: {c['text']};
            }}
            #CategoryHeader {{
                color: {c['text_muted']};
                font-size: 10px;
                font-weight: 700;
                padding-top: 8px;
                padding-bottom: 2px;
                letter-spacing: 0.5px;
            }}
            #NoticeBox {{
                background-color: {c['accent_light']};
                border: 1px solid {c['border']};
                border-radius: 8px;
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
        for item in self.items:
            item._apply_style(theme_name)


class ModernLeftSidebar(QStackedWidget):
    """Sol panel yığını: 0=Tüm Araçlar, 1=Export Çekmecesi, 2=Edit Çekmecesi."""
    toolTriggered = pyqtSignal(str)
    exportTriggered = pyqtSignal(str)
    editTriggered = pyqtSignal(str)
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

    def _on_tool_triggered(self, tool_id: str):
        if tool_id == "export_pdf":
            self.set_page("export")
        elif tool_id == "edit_pdf":
            self.set_page("edit")
        else:
            self.toolTriggered.emit(tool_id)

    def set_page(self, page_name: str):
        if page_name in ("all_tools", "tools"):
            self.setCurrentIndex(0)
        elif page_name in ("export", "convert"):
            self.setCurrentIndex(1)
        elif page_name in ("edit", "modify"):
            self.setCurrentIndex(2)

    def set_active_tool(self, tool_id: Optional[str]):
        self.all_tools_panel.set_active_tool(tool_id)

    def apply_theme(self, theme_name: str):
        self.all_tools_panel.apply_theme(theme_name)
        self.export_drawer.apply_theme(theme_name)
        self.edit_drawer.apply_theme(theme_name)


class FloatingQuickToolsCapsule(QFrame):
    """
    Belge okuyucu alanının sol kenarında yüzen hızlı araç kapsülü (Screenshot 3):
    - Seçim (↖)
    - Vurgulayıcı (🖊)
    - Not Ekle (💬)
    - Metin Düzenle (T)
    - Çizim Kalemi (✏)
    - Silgi (⌫)
    """
    toolSelected = pyqtSignal(str)

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"
        self.active_tool = "select"
        self.setFixedSize(42, 240)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(6)

        self.buttons: Dict[str, QToolButton] = {}
        tool_specs = [
            ("select", "quick_tool_select", ModernIconFactory.icon_cursor()),
            ("highlighter", "quick_tool_highlighter", ModernIconFactory.icon_highlighter("#eab308")),
            ("comment", "quick_tool_comment", ModernIconFactory.icon_comments("#f97316")),
            ("text", "quick_tool_text", ModernIconFactory.icon_text_tool("#ec4899")),
            ("pen", "quick_tool_pen", ModernIconFactory.icon_pen("#0284c7")),
            ("eraser", "quick_tool_eraser", ModernIconFactory.icon_eraser("#ef4444")),
        ]

        for tid, key, icon in tool_specs:
            btn = QToolButton(self)
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
            btn.setFixedSize(32, 32)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(LanguageManager.tr(key))
            btn.clicked.connect(lambda checked, t=tid: self._on_btn_clicked(t))
            layout.addWidget(btn)
            self.buttons[tid] = btn

        self.buttons["select"].setChecked(True)
        self.apply_theme(self.theme_name)

    def _on_btn_clicked(self, tool_id: str):
        self.set_active_tool(tool_id)
        self.toolSelected.emit(tool_id)

    def set_active_tool(self, tool_id: str):
        self.active_tool = tool_id
        for tid, btn in self.buttons.items():
            btn.setChecked(tid == tool_id)

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            FloatingQuickToolsCapsule {{
                background-color: {c['surface']};
                border: 1.5px solid {c['border']};
                border-radius: 20px;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 16px;
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
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
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
        v_content = QVBoxLayout(self.content_container)
        v_content.setContentsMargins(36, 32, 36, 36)
        v_content.setSpacing(24)
        v_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.inner_wrapper = QWidget()
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

        # 2. Topluluk Kartı (Community Banner)
        self.banner_frame = QFrame()
        self.banner_frame.setObjectName("CommunityBanner")
        v_banner = QVBoxLayout(self.banner_frame)
        v_banner.setContentsMargins(20, 18, 20, 18)
        v_banner.setSpacing(14)

        h_banner_head = QHBoxLayout()
        h_banner_head.setSpacing(12)
        lbl_app_logo = QLabel()
        lbl_app_logo.setPixmap(ModernIconFactory.icon_app().pixmap(24, 24))
        h_banner_head.addWidget(lbl_app_logo)

        v_head_texts = QVBoxLayout()
        v_head_texts.setSpacing(2)
        self.lbl_comm_title = QLabel(LanguageManager.tr("home_community_title"))
        self.lbl_comm_title.setObjectName("CommunityTitle")
        self.lbl_comm_desc = QLabel(LanguageManager.tr("home_community_desc"))
        self.lbl_comm_desc.setObjectName("CommunityDesc")
        v_head_texts.addWidget(self.lbl_comm_title)
        v_head_texts.addWidget(self.lbl_comm_desc)
        h_banner_head.addLayout(v_head_texts, stretch=1)
        v_banner.addLayout(h_banner_head)

        h_banner_btns = QHBoxLayout()
        h_banner_btns.setSpacing(10)

        # Discord Butonu (Mavi Dolgulu)
        self.btn_discord = QPushButton(" " + LanguageManager.tr("home_btn_discord"))
        self.btn_discord.setIcon(ModernIconFactory.icon_discord("#ffffff"))
        self.btn_discord.setObjectName("BtnDiscord")
        self.btn_discord.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discord.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/aurapdf")))
        h_banner_btns.addWidget(self.btn_discord)

        # Web Butonu
        self.btn_web = QPushButton(" " + LanguageManager.tr("home_btn_web"))
        self.btn_web.setIcon(ModernIconFactory.icon_web())
        self.btn_web.setObjectName("BtnOutline")
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aurapdf.org")))
        h_banner_btns.addWidget(self.btn_web)

        # GitHub Butonu
        self.btn_github = QPushButton(" " + LanguageManager.tr("home_btn_github"))
        self.btn_github.setIcon(ModernIconFactory.icon_github())
        self.btn_github.setObjectName("BtnOutline")
        self.btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/furkanndev/AuraPDF")))
        h_banner_btns.addWidget(self.btn_github)

        # Docs Butonu
        self.btn_website = QPushButton(" " + LanguageManager.tr("home_btn_website"))
        self.btn_website.setIcon(ModernIconFactory.icon_web())
        self.btn_website.setObjectName("BtnOutline")
        self.btn_website.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_website.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/furkanndev/AuraPDF#readme")))
        h_banner_btns.addWidget(self.btn_website)

        h_banner_btns.addStretch(1)
        v_banner.addLayout(h_banner_btns)
        v_inner.addWidget(self.banner_frame)

        # 3. Önerilen Araçlar (Recommended tools)
        v_rec = QVBoxLayout()
        v_rec.setSpacing(14)
        self.lbl_rec_title = QLabel(LanguageManager.tr("home_recommended_tools"))
        self.lbl_rec_title.setObjectName("SectionTitle")
        v_rec.addWidget(self.lbl_rec_title)

        h_cards = QHBoxLayout()
        h_cards.setSpacing(12)

        rec_tools = [
            ("organize_pages", "tool_organize_pages", "tool_sub_organize", ModernIconFactory.icon_organize("#10b981")),
            ("add_comments", "tool_add_comments", "tool_sub_comments", ModernIconFactory.icon_comments("#f97316")),
            ("prepare_form", "tool_prepare_form", "tool_sub_prepare_form", ModernIconFactory.icon_prepare_form("#9333ea")),
            ("edit_pdf", "tool_edit_pdf", "tool_sub_edit", ModernIconFactory.icon_edit_content("#ec4899")),
            ("protect_pdf", "tool_protect_pdf", "tool_sub_protect", ModernIconFactory.icon_lock("#0284c7")),
        ]

        self.recommended_cards = []
        for tid, title_key, sub_key, icon in rec_tools:
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

        # 4. Son Açılanlar (Recent)
        v_recent = QVBoxLayout()
        v_recent.setSpacing(14)
        self.lbl_recent_title = QLabel(LanguageManager.tr("home_recent_title"))
        self.lbl_recent_title.setObjectName("SectionTitle")
        v_recent.addWidget(self.lbl_recent_title)

        self.recent_list_container = QWidget()
        self.v_recent_items = QVBoxLayout(self.recent_list_container)
        self.v_recent_items.setContentsMargins(0, 0, 0, 0)
        self.v_recent_items.setSpacing(2)

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
            if item.widget():
                item.widget().deleteLater()

        files = []
        if self.main_window and hasattr(self.main_window, 'get_recent_files'):
            files = self.main_window.get_recent_files()

        if not files:
            lbl_empty = QLabel(LanguageManager.tr("home_no_recent"))
            lbl_empty.setObjectName("RecentEmpty")
            lbl_empty.setStyleSheet("padding: 20px 4px; font-size: 13px;")
            self.v_recent_items.addWidget(lbl_empty)
            return

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

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            HomeDashboardWorkspace {{
                background-color: {c['bg']};
            }}
            QScrollArea, QWidget {{
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
            #CommunityBanner {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            #CommunityTitle {{
                color: {c['text']};
                font-size: 15px;
                font-weight: 700;
            }}
            #CommunityDesc {{
                color: {c['text_muted']};
                font-size: 12px;
            }}
            #BtnDiscord {{
                background-color: #5865f2;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #BtnDiscord:hover {{
                background-color: #4752c4;
            }}
            #BtnOutline {{
                background-color: {c['surface_hover']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            #BtnOutline:hover {{
                background-color: {c['surface_active']};
                border-color: {c['accent']};
            }}
            #SectionTitle {{
                color: {c['text']};
                font-size: 16px;
                font-weight: 700;
            }}
            #RecentEmpty {{
                color: {c['text_muted']};
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

        self._apply_style("light")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index, event.modifiers())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.page_index)
        super().mouseDoubleClickEvent(event)

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
                    color: {c['text_muted']};
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

    def load_document(self):
        """Aktif PDF belgesinin sayfalarını yükler ve kartları oluşturur."""
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
            self.lbl_page_info.setText("Belge Açık Değil")
            return

        total = len(tab_doc.doc)
        curr = getattr(tab_doc, 'current_page', 0)
        self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=curr + 1, total=total))

        # Kartları 6 sütunlu olarak ızgaraya yerleştir
        cols = 6
        for page_idx in range(total):
            card = PageThumbnailCard(page_idx, parent=self.grid_container)
            card.clicked.connect(self._on_card_clicked)
            card.doubleClicked.connect(self._on_card_double_clicked)
            self.cards.append(card)
            r = page_idx // cols
            c = page_idx % cols
            self.grid_layout.addWidget(card, r, c)

        # İlk aktif sayfayı seç
        if 0 <= curr < total:
            self.selected_pages.add(curr)
            self.cards[curr].set_selected(True, self.theme_name)

        # Küçük resimleri hemen yükle (ilk 36 sayfa anında, kalanlar arka planda)
        self._render_thumbnails(start=0, limit=36)
        if total > 36:
            QTimer.singleShot(100, lambda: self._render_thumbnails(start=36))

    def _render_thumbnails(self, start: int = 0, limit: Optional[int] = None):
        if not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        end = len(self.cards) if limit is None else min(len(self.cards), start + limit)
        for i in range(start, end):
            card = self.cards[i]
            if card.page_index < len(tab_doc.doc):
                try:
                    page = tab_doc.doc[card.page_index]
                    pix = page.get_pixmap(dpi=72)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    card.set_pixmap(QPixmap.fromImage(qimg))
                except Exception as e:
                    pass

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

    def _update_selection_info(self):
        total = len(self.cards)
        sel_count = len(self.selected_pages)
        if sel_count > 1:
            self.lbl_page_info.setText(LanguageManager.tr("organize_pages_selected", count=sel_count))
        elif sel_count == 1:
            p = next(iter(self.selected_pages))
            self.lbl_page_info.setText(LanguageManager.tr("organize_page_of", curr=p + 1, total=total))
        else:
            self.lbl_page_info.setText(f"{total} Pages")

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
        if not self.selected_pages or not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        for p in self.selected_pages:
            if 0 <= p < len(tab_doc.doc):
                page = tab_doc.doc[p]
                page.set_rotation((page.rotation + angle) % 360)

        tab_doc.set_modified(True)
        self.documentModified.emit()
        self._render_thumbnails()

    def delete_selected_pages(self):
        if not self.selected_pages or not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        if len(self.selected_pages) >= len(tab_doc.doc):
            QMessageBox.warning(self, LanguageManager.tr("app_title"), "Belgedeki tüm sayfaları silemezsiniz.")
            return

        res = QMessageBox.question(
            self, LanguageManager.tr("app_title"),
            f"{len(self.selected_pages)} sayfa kalıcı olarak silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        # Sayfaları sondan başa doğru sil
        for p in sorted(list(self.selected_pages), reverse=True):
            tab_doc.doc.delete_page(p)

        tab_doc.set_modified(True)
        tab_doc.total_pages = len(tab_doc.doc)
        if tab_doc.current_page >= tab_doc.total_pages:
            tab_doc.current_page = max(0, tab_doc.total_pages - 1)

        self.load_document()
        self.documentModified.emit()

    def insert_page_action(self):
        if hasattr(self.main_window, 'show_new_page_dialog'):
            self.main_window.show_new_page_dialog()
            QTimer.singleShot(300, self.load_document)

    def extract_pages_action(self):
        if not self.selected_pages or not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("organize_extract_pages"), "extracted.pdf", "PDF (*.pdf)")
        if not path:
            return

        new_doc = fitz.open()
        for p in sorted(list(self.selected_pages)):
            new_doc.insert_pdf(tab_doc.doc, from_page=p, to_page=p)
        new_doc.save(path)
        new_doc.close()
        QMessageBox.information(self, LanguageManager.tr("app_title"), f"Sayfalar başarıyla çıkarıldı:\n{path}")

    def split_doc_action(self):
        if hasattr(self.main_window, 'open_split_dialog'):
            self.main_window.open_split_dialog()

    def replace_pages_action(self):
        if not self.selected_pages or not self.main_window:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        src_pdf, _ = QFileDialog.getOpenFileName(self, "Değiştirilecek Kaynak PDF", "", "PDF (*.pdf)")
        if not src_pdf:
            return

        try:
            other = fitz.open(src_pdf)
            for idx, p in enumerate(sorted(list(self.selected_pages))):
                if idx < len(other):
                    tab_doc.doc.delete_page(p)
                    tab_doc.doc.insert_pdf(other, from_page=idx, to_page=idx, start_at=p)
            other.close()
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
        for card in self.cards:
            card._apply_style(theme_name)


# ==============================================================================
# 5. SAĞ ÇEKMECE PANELİ (ModernRightSidebar)
# ==============================================================================
class ModernRightSidebar(QWidget):
    """
    Ekranın sağındaki çekmece panel (Kullanıcı görselindeki 'Bookmarks' paneli):
    - Başlık: 'Bookmarks' + Bookmark İkonu + Kapatma (✕)
    - Boş durum: Yer imi ikonu + 'This document has no bookmarks.'
    - Ağaç görünümü: Yer imleri listesi
    """
    closeRequested = pyqtSignal()
    bookmarkClicked = pyqtSignal(int)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.main_window = main_window
        self.theme_name = "light"
        self.current_panel = "bookmarks"
        self.setFixedWidth(260)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(4, 0, 4, 4)

        self.lbl_head_icon = QLabel()
        self.lbl_head_icon.setPixmap(ModernIconFactory.icon_bookmark().pixmap(16, 16))
        h_head.addWidget(self.lbl_head_icon)

        self.lbl_head_title = QLabel(LanguageManager.tr("bookmarks_panel_title"))
        self.lbl_head_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        h_head.addWidget(self.lbl_head_title)
        h_head.addStretch(1)

        btn_add = QToolButton()
        btn_add.setIcon(ModernIconFactory.icon_plus())
        btn_add.setIconSize(QSize(12, 12))
        btn_add.setFixedSize(22, 22)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setToolTip(LanguageManager.tr("bookmarks_add_btn"))
        btn_add.clicked.connect(self._add_bookmark_action)
        h_head.addWidget(btn_add)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.closeRequested.emit)
        h_head.addWidget(btn_close)
        main_layout.addLayout(h_head)

        # Yığın (Boş Durum vs Ağaç)
        self.stack = QStackedWidget()

        # Görünüm 0: Yer İmleri Boş Durumu (Kullanıcı görselindeki gibi!)
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

        # Görünüm 1: Yer İmleri Ağacı (2 Sütun: Başlık ve Sağ Hizalı Sayfa Numarası)
        self.tree_bookmarks = QTreeWidget()
        self.tree_bookmarks.setColumnCount(2)
        self.tree_bookmarks.setHeaderHidden(True)
        self.tree_bookmarks.header().setStretchLastSection(False)
        self.tree_bookmarks.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_bookmarks.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_bookmarks.itemClicked.connect(self._on_tree_item_clicked)
        self.stack.addWidget(self.tree_bookmarks)

        main_layout.addWidget(self.stack, stretch=1)
        self.apply_theme(self.theme_name)

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

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernRightSidebar {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
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
        """)


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
        self.theme_name = "light"
        self.active_rail_id: Optional[str] = "bookmarks"
        self.setFixedWidth(42)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 8, 4, 8)
        main_layout.setSpacing(6)

        # Üst Panel Tetikleyicileri
        self.buttons: Dict[str, QToolButton] = {}
        top_items = [
            ("comments", ModernIconFactory.icon_comments(), "right_rail_comments"),
            ("bookmarks", ModernIconFactory.icon_bookmark(), "right_rail_bookmarks"),
            ("thumbnails", ModernIconFactory.icon_thumbnails(), "right_rail_thumbnails"),
            ("attachments", ModernIconFactory.icon_attachment(), "right_rail_attachments"),
            ("signatures", ModernIconFactory.icon_sign(), "right_rail_signatures"),
        ]

        for rid, icon, tip_key in top_items:
            btn = QToolButton()
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(34, 34)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(LanguageManager.tr(tip_key))
            btn.clicked.connect(lambda checked, r=rid: self._on_button_clicked(r))
            main_layout.addWidget(btn)
            self.buttons[rid] = btn

        self.buttons["bookmarks"].setChecked(True)

        main_layout.addStretch(1)

        # Alt Zoom ve Sayfa Kontrolleri
        # Sayfa No Etiketi
        self.lbl_page = QLabel("1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setStyleSheet("font-size: 11px; font-weight: 700;")
        main_layout.addWidget(self.lbl_page)

        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(ModernIconFactory.icon_chevron_up())
        self.btn_prev.setIconSize(QSize(12, 12))
        self.btn_prev.setFixedSize(34, 20)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self.prevPageRequested.emit)
        main_layout.addWidget(self.btn_prev)

        self.btn_next = QToolButton()
        self.btn_next.setIcon(ModernIconFactory.icon_chevron_down())
        self.btn_next.setIconSize(QSize(12, 12))
        self.btn_next.setFixedSize(34, 20)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.nextPageRequested.emit)
        main_layout.addWidget(self.btn_next)

        # Zoom Yüzdesi
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_zoom.setStyleSheet("font-size: 10px; font-weight: 600;")
        main_layout.addWidget(self.lbl_zoom)

        # Sığdır
        self.btn_fit = QToolButton()
        self.btn_fit.setIcon(ModernIconFactory.icon_fit_page())
        self.btn_fit.setIconSize(QSize(16, 16))
        self.btn_fit.setFixedSize(34, 28)
        self.btn_fit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
        self.btn_fit.clicked.connect(self.fitPageRequested.emit)
        main_layout.addWidget(self.btn_fit)

        # Zoom +
        self.btn_zin = QToolButton()
        self.btn_zin.setIcon(ModernIconFactory.icon_plus())
        self.btn_zin.setIconSize(QSize(12, 12))
        self.btn_zin.setFixedSize(34, 24)
        self.btn_zin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zin.clicked.connect(self.zoomInRequested.emit)
        main_layout.addWidget(self.btn_zin)

        # Zoom -
        self.btn_zout = QToolButton()
        self.btn_zout.setIcon(ModernIconFactory.icon_minus())
        self.btn_zout.setIconSize(QSize(12, 12))
        self.btn_zout.setFixedSize(34, 24)
        self.btn_zout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_zout.clicked.connect(self.zoomOutRequested.emit)
        main_layout.addWidget(self.btn_zout)

        self.apply_theme(self.theme_name)

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

    def update_page_info(self, current: int, total: int):
        self.lbl_page.setText(f"{current + 1}")

    def update_zoom_info(self, zoom_percent: int):
        self.lbl_zoom.setText(f"{zoom_percent}%")

    def apply_theme(self, theme_name: str = "light"):
        self.theme_name = theme_name
        c = get_modern_theme_colors(theme_name)
        self.setStyleSheet(f"""
            ModernUtilityRail {{
                background-color: {c['surface']};
                border-left: 1px solid {c['border']};
            }}
            QLabel {{
                color: {c['text_muted']};
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
        layout.addWidget(self.txt_search)

        # Komut Listesi
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(20, 20))
        self.list_widget.itemDoubleClicked.connect(lambda it: self._execute_command(it.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.list_widget, stretch=1)

        self.commands = [
            ("organize_pages", "tool_organize_pages", ModernIconFactory.icon_organize("#10b981")),
            ("edit_pdf", "tool_edit_pdf", ModernIconFactory.icon_edit_content("#ec4899")),
            ("combine_files", "tool_combine_files", ModernIconFactory.icon_combine_files("#0284c7")),
            ("compress_pdf", "tool_compress_pdf", ModernIconFactory.icon_compress("#ef4444")),
            ("scan_ocr", "tool_scan_ocr", ModernIconFactory.icon_ocr("#10b981")),
            ("export_pdf", "tool_export_pdf", ModernIconFactory.icon_export_pdf("#0284c7")),
            ("protect_pdf", "tool_protect_pdf", ModernIconFactory.icon_lock("#0284c7")),
            ("redact_pdf", "tool_redact_pdf", ModernIconFactory.icon_redact("#ef4444")),
            ("fill_sign", "tool_fill_sign", ModernIconFactory.icon_fill_sign("#8b5cf6")),
            ("print", "print_btn", ModernIconFactory.icon_print()),
            ("save", "save_btn", ModernIconFactory.icon_save()),
            ("settings", "settings_title", ModernIconFactory.icon_settings()),
            ("shortcuts", "shortcuts_title", ModernIconFactory.icon_info()),
        ]

        self._filter_commands("")
        self._apply_style()

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
