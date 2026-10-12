import os
import sys
from typing import Optional, Any
from PyQt6.QtCore import QSettings, Qt, QObject, QEvent
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout

THEME_PALETTES = {
    "gray": {
        "bg": "#2b2d30",
        "card": "#35383c",
        "border": "#444850",
        "accent": "#60a5fa",
        "accent_hover": "#93c5fd",
        "text": "#f8fafc",
        "muted": "#cbd5e1",
    },
    "emerald": {
        "bg": "#091a14",
        "card": "#112a21",
        "border": "#1a3d30",
        "accent": "#34d399",
        "accent_hover": "#6ee7b7",
        "text": "#ecfdf5",
        "muted": "#c6f6d5",
    },
    "purple": {
        "bg": "#150d22",
        "card": "#201435",
        "border": "#321f52",
        "accent": "#c084fc",
        "accent_hover": "#d8b4fe",
        "text": "#faf5ff",
        "muted": "#e9d5ff",
    },
    "crimson": {
        "bg": "#1d0b10",
        "card": "#2d1118",
        "border": "#441924",
        "accent": "#fb7185",
        "accent_hover": "#fda4af",
        "text": "#fff1f2",
        "muted": "#fecdd3",
    },
    "nord": {
        "bg": "#181e29",
        "card": "#222b3a",
        "border": "#313e54",
        "accent": "#38bdf8",
        "accent_hover": "#7dd3fc",
        "text": "#f0f6fc",
        "muted": "#cbd5e1",
    },
    "vice_city": {
        "bg": "#160024",
        "card": "#240e3b",
        "border": "#421869",
        "accent": "#ff2a85",
        "accent_hover": "#ff66a8",
        "text": "#fdf2f8",
        "muted": "#f5d0fe",
    },
    "apple": {
        "bg": "#0e1014",
        "card": "#1a1d24",
        "border": "#2e3340",
        "accent": "#38bdf8",
        "accent_hover": "#7dd3fc",
        "text": "#f5f5f7",
        "muted": "#cbd5e1",
    },
}
# Geriye dönük uyumluluk ve güvenli eşleme:
THEME_PALETTES["light"] = THEME_PALETTES["gray"]
THEME_PALETTES["dark"] = THEME_PALETTES["gray"]

def get_custom_dialog_palette() -> dict:
    try:
        from src.ui.modern_views import get_modern_theme_colors
        c = get_modern_theme_colors("custom")
        return {
            "bg": c["bg"],
            "card": c["surface"],
            "border": c["border"],
            "accent": c["accent"],
            "accent_hover": c["accent_hover"],
            "text": c["text"],
            "muted": c["text_muted"],
        }
    except Exception:
        return THEME_PALETTES["gray"].copy()

THEME_PALETTES["custom"] = get_custom_dialog_palette()


def get_current_theme(parent: Optional[Any] = None) -> str:
    """Aktif temayı ana pencereden veya QSettings'ten okur."""
    th = "gray"
    if parent is not None:
        if hasattr(parent, 'current_theme') and parent.current_theme:
            th = parent.current_theme
        elif hasattr(parent, 'main_window') and hasattr(parent.main_window, 'current_theme') and parent.main_window.current_theme:
            th = parent.main_window.current_theme
    else:
        try:
            settings = QSettings("AuraPDF", "PDFViewer")
            th = settings.value("app_theme", "gray")
        except Exception:
            th = "gray"
    if th in ("light", "dark"):
        return "gray"
    return th


def get_current_font_size(parent: Optional[Any] = None) -> int:
    """Aktif uygulama yazı tipi boyutunu (pt) okur (Varsayılan: 10pt)."""
    if parent is not None:
        if hasattr(parent, 'app_font_size') and parent.app_font_size and int(parent.app_font_size) > 0:
            return max(8, int(parent.app_font_size))
        if hasattr(parent, 'main_window') and hasattr(parent.main_window, 'app_font_size') and parent.main_window.app_font_size and int(parent.main_window.app_font_size) > 0:
            return max(8, int(parent.main_window.app_font_size))
    try:
        settings = QSettings("AuraPDF", "PDFViewer")
        val = settings.value("app_font_size", 10)
        return max(8, int(val)) if val and int(val) > 0 else 10
    except Exception:
        return 10


def get_theme_palette(parent_or_theme: Optional[Any] = None) -> dict:
    """Aktif temaya karşılık gelen renk paleti sözlüğünü döner."""
    if isinstance(parent_or_theme, str):
        theme = parent_or_theme
    else:
        theme = get_current_theme(parent_or_theme)
    if theme == "custom":
        pal = get_custom_dialog_palette()
        THEME_PALETTES["custom"] = pal
        return pal
    return THEME_PALETTES.get(theme, THEME_PALETTES["gray"])


class ModernInfoCard(QFrame):
    """
    Tüm temalarla (dark, gray, emerald, purple, crimson, nord, vice_city, apple, light)
    tam uyumlu, otomatik metin kaydırmalı (wordWrap=True),
    vektörel ikonlu modern bilgilendirme / ipucu / uyarı paneli.
    """
    def __init__(
        self,
        text: str = "",
        title: Optional[str] = None,
        icon_type: str = "info",
        parent: Optional[Any] = None,
        is_warning: bool = False,
    ):
        super().__init__(parent)
        self.is_warning = is_warning
        self.icon_type = icon_type
        self.setObjectName("ModernInfoCard")
        self.setProperty("class", "info-card")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        
        self.lbl_icon = QLabel(self)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.lbl_icon)
        
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        self.lbl_title = QLabel(self)
        self.lbl_title.setWordWrap(True)
        if title:
            self.lbl_title.setText(f"<b>{title}</b>")
            self.lbl_title.setVisible(True)
        else:
            self.lbl_title.setVisible(False)
        text_layout.addWidget(self.lbl_title)
        
        self.lbl_text = QLabel(text, self)
        self.lbl_text.setWordWrap(True)
        text_layout.addWidget(self.lbl_text)
        
        layout.addLayout(text_layout, 1)
        self.apply_theme(get_current_theme(parent))

    def set_text(self, text: str):
        self.lbl_text.setText(text)

    def set_title(self, title: Optional[str]):
        if title:
            self.lbl_title.setText(f"<b>{title}</b>")
            self.lbl_title.setVisible(True)
        else:
            self.lbl_title.setVisible(False)

    def apply_theme(self, theme_name: str = "gray"):
        from src.ui.icons import ModernIconFactory
        pal = THEME_PALETTES.get(theme_name, THEME_PALETTES["gray"])
        accent = pal["accent"] if not self.is_warning else "#f59e0b"
        
        if self.icon_type == "ocr" and hasattr(ModernIconFactory, "icon_ocr"):
            icon = ModernIconFactory.icon_ocr(accent)
        elif self.icon_type == "redact" and hasattr(ModernIconFactory, "icon_redact"):
            icon = ModernIconFactory.icon_redact(accent)
        elif self.is_warning or self.icon_type == "warning":
            icon = ModernIconFactory.icon_warning(accent)
        else:
            icon = ModernIconFactory.icon_info(accent)
        self.lbl_icon.setPixmap(icon.pixmap(22, 22))
        
        card_bg = pal["card"]
        border_col = pal["border"]
        text_col = pal["text"]
        
        self.setStyleSheet(f"""
            QFrame#ModernInfoCard {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-left: 3.5px solid {accent};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {accent}; font-size: 12px; font-weight: 600; background: transparent;")
        self.lbl_text.setStyleSheet(f"color: {text_col}; font-size: 11px; background: transparent;")


def get_dialog_theme_stylesheet(parent: Optional[Any] = None, extra_css: str = "") -> str:
    """
    Diyalog pencereleri için tema stil şablonunu ve aktif font boyutunu üretir.
    """
    theme = get_current_theme(parent)

    if theme == "apple":
        css = """
            QDialog {
                background-color: #16181f;
                color: #f5f5f7;
            }
            QLabel {
                color: #f5f5f7;
                font-size: 12px;
            }
            QLabel[class="muted"], QLabel#MutedLabel {
                color: #cbd5e1;
            }
            QLabel[class="accent"], QLabel#AccentLabel, QLabel[class="accent-title"] {
                color: #38bdf8;
                font-weight: 600;
            }
            QFrame[class="card"], QFrame.card, QFrame#CardFrame {
                background-color: #1a1d24;
                border: 1px solid #2e3340;
                border-radius: 8px;
            }
            QFrame[class="info-card"], QFrame.InfoCard, QFrame#InfoCard, QFrame#InfoBox, QFrame#ModernInfoCard {
                background-color: #1a1d24;
                border: 1px solid #2e3340;
                border-left: 3.5px solid #38bdf8;
                border-radius: 8px;
            }
            QFrame[class="tip-card"], QFrame.TipCard {
                background-color: #1a1d24;
                border: 1px solid #2e3340;
                border-left: 3px solid #38bdf8;
                border-radius: 6px;
            }
            QFrame[class="preview-card"], QFrame#PreviewCard, QFrame#PreviewFrame, QFrame.PreviewBox, QFrame#preview_frame, QFrame#frame_box {
                background-color: #0e1014;
                border: 1px solid #2e3340;
                border-radius: 8px;
            }
            QGroupBox {
                color: #0a84ff;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QKeySequenceEdit {
                background-color: rgba(14, 15, 20, 0.75);
                color: #ffffff;
                border: 1.2px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QKeySequenceEdit:focus {
                border-color: #0a84ff;
                background-color: rgba(18, 20, 28, 0.90);
            }
            QComboBox {
                background-color: rgba(14, 15, 20, 0.75);
                color: #ffffff;
                border: 1.2px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QComboBox:focus {
                border-color: #0a84ff;
            }
            QComboBox QAbstractItemView {
                background-color: #1e202a;
                color: #ffffff;
                selection-background-color: #0a84ff;
                selection-color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.14);
                padding: 4px;
                outline: none;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: rgba(14, 15, 20, 0.75);
                color: #ffffff;
                border: 1.2px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 4px 22px 4px 8px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #0a84ff;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid rgba(255, 255, 255, 0.14);
                background-color: transparent;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid rgba(255, 255, 255, 0.14);
                background-color: transparent;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.07);
                color: #f5f5f7;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
                min-height: 26px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
                border-color: rgba(255, 255, 255, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton#PrimaryBtn, QPushButton[class="primary"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a84ff, stop:1 #0066cc);
                border: 1px solid #388bfd;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton#PrimaryBtn:hover, QPushButton[class="primary"]:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3399ff, stop:1 #0071e3);
            }
            QPushButton#DangerBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff453a, stop:1 #d70015);
                border: 1px solid #ff6961;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton#DangerBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6961, stop:1 #e02636);
            }
            QPushButton#CancelBtn {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f5f5f7;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton#CancelBtn:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QPushButton#SecondaryBtn {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f5f5f7;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QPushButton.PresetBtn, QPushButton.NavBtn {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                min-height: 24px;
                color: #f5f5f7;
            }
            QPushButton.PresetBtn:hover, QPushButton.NavBtn:hover {
                background-color: rgba(255, 255, 255, 0.14);
                border-color: #0a84ff;
            }
            QPushButton.NavBtn:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                color: #64748b;
                border-color: rgba(255, 255, 255, 0.05);
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.12);
                background-color: rgba(30, 32, 42, 0.85);
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: rgba(22, 24, 32, 0.70);
                color: #94a3b8;
                padding: 8px 18px;
                margin-right: 3px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: rgba(36, 39, 52, 0.90);
                color: #ffffff;
                border-top: 2.5px solid #0a84ff;
                border-left: 1px solid rgba(255, 255, 255, 0.15);
                border-right: 1px solid rgba(255, 255, 255, 0.15);
                font-weight: bold;
            }
            QListWidget, QTableWidget, QTreeWidget {
                background-color: rgba(16, 18, 24, 0.85);
                color: #f5f5f7;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 6px;
                margin: 2px 0;
                color: #e2e8f0;
            }
            QListWidget::item:selected, QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a84ff, stop:1 #0066cc);
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #388bfd;
            }
            QCheckBox, QRadioButton {
                color: #f5f5f7;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator:checked {
                background-color: #0a84ff;
                border: 2px solid #ffffff;
                border-radius: 6px;
            }
            QCheckBox::indicator:checked {
                background-color: #0a84ff;
                border: 2px solid #ffffff;
                border-radius: 4px;
            }
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 0.12);
                height: 6px;
                background: rgba(14, 15, 20, 0.8);
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a84ff, stop:1 #0077ed);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #94a3b8;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: 500;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a84ff, stop:1 #0066cc);
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: rgba(26, 28, 38, 0.95);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.10);
                padding: 5px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.22);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.38);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: transparent;
                height: 8px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(255, 255, 255, 0.22);
                border-radius: 4px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(255, 255, 255, 0.38);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """
    else:
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["dark"])
        css = f"""
            QDialog {{
                background-color: {pal['bg']};
                color: {pal['text']};
            }}
            QLabel {{
                color: {pal['text']};
                font-size: 12px;
            }}
            QLabel[class="muted"], QLabel#MutedLabel {{
                color: {pal['muted']};
            }}
            QLabel[class="accent"], QLabel#AccentLabel, QLabel[class="accent-title"] {{
                color: {pal['accent']};
                font-weight: 600;
            }}
            QFrame[class="card"], QFrame.card, QFrame#CardFrame {{
                background-color: {pal['card']};
                border: 1px solid {pal['border']};
                border-radius: 8px;
            }}
            QFrame[class="info-card"], QFrame.InfoCard, QFrame#InfoCard, QFrame#InfoBox, QFrame#ModernInfoCard {{
                background-color: {pal['card']};
                border: 1px solid {pal['border']};
                border-left: 3.5px solid {pal['accent']};
                border-radius: 8px;
            }}
            QFrame[class="tip-card"], QFrame.TipCard {{
                background-color: {pal['card']};
                border: 1px solid {pal['border']};
                border-left: 3px solid {pal['accent']};
                border-radius: 6px;
            }}
            QFrame[class="preview-card"], QFrame#PreviewCard, QFrame#PreviewFrame, QFrame.PreviewBox, QFrame#preview_frame, QFrame#frame_box {{
                background-color: {pal['bg']};
                border: 1px solid {pal['border']};
                border-radius: 8px;
            }}
            QGroupBox {{
                color: {pal['accent']};
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {pal['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QKeySequenceEdit {{
                background-color: {pal['bg']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QKeySequenceEdit:focus {{
                border-color: {pal['accent']};
            }}
            QComboBox {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox:focus {{
                border-color: {pal['accent']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {pal['card']};
                color: {pal['text']};
                selection-background-color: {pal['accent']};
                selection-color: #ffffff;
                border: 1px solid {pal['border']};
                padding: 4px;
                outline: none;
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {pal['bg']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 5px;
                padding: 3px 22px 3px 6px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {pal['accent']};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid {pal['border']};
                background-color: transparent;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid {pal['border']};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
                min-height: 26px;
            }}
            QPushButton:hover {{
                background-color: {pal['border']};
            }}
            QPushButton#PrimaryBtn, QPushButton[class="primary"] {{
                background-color: {pal['accent']};
                border: none;
                font-weight: bold;
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton#PrimaryBtn:hover, QPushButton[class="primary"]:hover {{
                background-color: {pal['accent_hover']};
            }}
            QPushButton#DangerBtn {{
                background-color: #dc2626;
                border: none;
                font-weight: bold;
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton#DangerBtn:hover {{
                background-color: #b91c1c;
            }}
            QPushButton#CancelBtn {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {pal['border']};
            }}
            QPushButton#SecondaryBtn {{
                background-color: {pal['bg']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 5px;
                padding: 5px 12px;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {pal['card']};
            }}
            QPushButton.PresetBtn, QPushButton.NavBtn {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 5px;
                padding: 4px 6px;
                font-size: 11px;
                min-height: 26px;
            }}
            QPushButton.PresetBtn:hover, QPushButton.NavBtn:hover {{
                background-color: {pal['border']};
                border-color: {pal['accent']};
            }}
            QPushButton.NavBtn:disabled {{
                background-color: transparent;
                color: {pal['muted']};
                border-color: transparent;
            }}
            QTabWidget::pane {{
                border: 1px solid {pal['border']};
                background-color: {pal['card']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {pal['bg']};
                color: {pal['muted']};
                padding: 8px 18px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background-color: {pal['card']};
                color: {pal['text']};
                border-bottom: 2.5px solid {pal['accent']};
                font-weight: bold;
            }}
            QListWidget, QTableWidget, QTreeWidget {{
                background-color: {pal['bg']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                background-color: {pal['card']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 6px;
                margin: 3px;
                color: {pal['text']};
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: {pal['accent']};
                border: 1px solid {pal['accent_hover']};
                color: #ffffff;
                font-weight: bold;
            }}
            QCheckBox, QRadioButton {{
                color: {pal['text']};
                font-size: 12px;
                spacing: 8px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {pal['border']};
                height: 6px;
                background: {pal['card']};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {pal['accent']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                border: 1px solid {pal['border']};
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
            QHeaderView::section {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                padding: 4px;
                font-weight: bold;
            }}
        """

    fs = get_current_font_size(parent)
    font_scale_css = f"""
        QDialog, QWidget {{
            font-size: {fs}pt;
        }}
        QLabel, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton {{
            font-size: {fs}pt;
        }}
        QGroupBox {{
            font-size: {fs}pt;
        }}
        QGroupBox::title {{
            font-size: {fs}pt;
        }}
        QListWidget, QTableWidget, QTreeWidget, QHeaderView::section {{
            font-size: {fs}pt;
        }}
        QCheckBox, QRadioButton {{
            font-size: {fs}pt;
        }}
        QMenu, QMenu::item {{
            font-size: {fs}pt;
        }}
    """
    css += "\n" + font_scale_css

    if extra_css:
        css += "\n" + extra_css
    return css


def apply_dialog_theme(dialog: Any, parent: Optional[Any] = None, extra_css: str = "") -> None:
    """Belirtilen diyalog nesnesine geçerli tema stilini ve aktif font boyutunu uygular."""
    fs = max(8, get_current_font_size(parent))
    try:
        f = dialog.font()
        if fs > 0:
            f.setPointSize(fs)
            dialog.setFont(f)
    except Exception:
        pass
    dialog.setStyleSheet(get_dialog_theme_stylesheet(parent, extra_css))

    curr_theme = get_current_theme(parent)

    # 1. ModernStepper / ModernSpinBox / ModernDoubleSpinBox çocuk bileşenlerini tema ile senkronize et
    try:
        from src.ui.modern_stepper import ModernSpinBox, ModernDoubleSpinBox
        for sp in dialog.findChildren(ModernSpinBox):
            sp.apply_theme(curr_theme)
        for dsp in dialog.findChildren(ModernDoubleSpinBox):
            dsp.apply_theme(curr_theme)
    except Exception:
        pass

    # 2. ModernInfoCard çocuk bileşenlerini tema ile senkronize et
    try:
        for card in dialog.findChildren(ModernInfoCard):
            card.apply_theme(curr_theme)
    except Exception:
        pass

    # 3. Otomatik Metin Kaydırma (Word-Wrap) Güvenliği
    # Diyalog pencerelerinde uzun metinlerin, ipuçlarının ve açıklamaların
    # pencere sınırlarından taşmasını veya kesilmesini kesin olarak önler.
    def _apply_word_wraps():
        try:
            for lbl in dialog.findChildren(QLabel):
                txt = lbl.text()
                if txt and len(txt) > 35 and not lbl.wordWrap():
                    lbl.setWordWrap(True)
        except Exception:
            pass

    _apply_word_wraps()

    # adjustSize çağrıldığında etiketleri yeniden tara
    try:
        if not getattr(dialog, "_wrap_hook_installed", False):
            orig_adjust = dialog.adjustSize
            def _safe_adjust_size(*args, **kwargs):
                _apply_word_wraps()
                return orig_adjust(*args, **kwargs)
            dialog.adjustSize = _safe_adjust_size
            dialog._wrap_hook_installed = True
    except Exception:
        pass

    # Pencere gösterildiğinde (Show / Polish) sonradan eklenen etiketleri de otomatik olarak sar
    try:
        class _ThemeSafetyFilter(QObject):
            def eventFilter(self, watched, event):
                if event.type() in (QEvent.Type.Show, QEvent.Type.Polish):
                    _apply_word_wraps()
                return super().eventFilter(watched, event)

        if not getattr(dialog, "_theme_filter_installed", False):
            flt = _ThemeSafetyFilter(dialog)
            dialog.installEventFilter(flt)
            dialog._theme_filter_installed = True
    except Exception:
        pass

apply_aura_dialog_style = apply_dialog_theme
apply_modern_dialog_style = apply_dialog_theme
