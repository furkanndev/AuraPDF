import os
import sys
from typing import Optional, Any
from PyQt6.QtCore import QSettings

THEME_PALETTES = {
    "dark": {
        "bg": "#1c1c1e",
        "card": "#2c2c2e",
        "border": "#3a3a3c",
        "accent": "#0071e3",
        "accent_hover": "#0077ed",
        "text": "#f5f5f7",
        "muted": "#888888",
    },
    "gray": {
        "bg": "#2b2d30",
        "card": "#35383c",
        "border": "#444850",
        "accent": "#60a5fa",
        "accent_hover": "#3b82f6",
        "text": "#f1f5f9",
        "muted": "#94a3b8",
    },
    "navy": {
        "bg": "#0f172a",
        "card": "#1e293b",
        "border": "#334155",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
    },
    "emerald": {
        "bg": "#091a14",
        "card": "#112a21",
        "border": "#1a3d30",
        "accent": "#10b981",
        "accent_hover": "#059669",
        "text": "#ecfdf5",
        "muted": "#6ee7b7",
    },
    "purple": {
        "bg": "#150d22",
        "card": "#201435",
        "border": "#321f52",
        "accent": "#a855f7",
        "accent_hover": "#9333ea",
        "text": "#faf5ff",
        "muted": "#c084fc",
    },
    "crimson": {
        "bg": "#1d0b10",
        "card": "#2d1118",
        "border": "#441924",
        "accent": "#f43f5e",
        "accent_hover": "#e11d48",
        "text": "#fff1f2",
        "muted": "#fda4af",
    },
    "nord": {
        "bg": "#181e29",
        "card": "#222b3a",
        "border": "#313e54",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "text": "#f0f6fc",
        "muted": "#89b4fa",
    },
    "vice_city": {
        "bg": "#160024",
        "card": "#240e3b",
        "border": "#4a1c72",
        "accent": "#ff2a85",
        "accent_hover": "#ff4d9a",
        "text": "#fdf2f8",
        "muted": "#00f0ff",
    },
}


def get_current_theme(parent: Optional[Any] = None) -> str:
    """Aktif temayı ana pencereden veya QSettings'ten okur."""
    if parent is not None:
        if hasattr(parent, 'current_theme') and parent.current_theme:
            return parent.current_theme
        if hasattr(parent, 'main_window') and hasattr(parent.main_window, 'current_theme') and parent.main_window.current_theme:
            return parent.main_window.current_theme
    try:
        settings = QSettings("AuraPDF", "PDFViewer")
        return settings.value("app_theme", "dark")
    except Exception:
        return "dark"


def get_dialog_theme_stylesheet(parent: Optional[Any] = None, extra_css: str = "") -> str:
    """
    Diyalog pencereleri için tema stil şablonunu üretir.
    """
    theme = get_current_theme(parent)

    if theme == "apple":
        css = """

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
                padding: 4px 8px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #0a84ff;
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
            QFrame[class="card"], QFrame.card {{
                background-color: {pal['card']};
                border: 1.2px solid {pal['border']};
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
                color: #ffffff;
                border: 1.2px solid {pal['border']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QKeySequenceEdit:focus {{
                border-color: {pal['accent']};
            }}
            QComboBox {{
                background-color: {pal['card']};
                color: #ffffff;
                border: 1.2px solid {pal['border']};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox:focus {{
                border-color: {pal['accent']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {pal['card']};
                color: #ffffff;
                selection-background-color: {pal['accent']};
                selection-color: #ffffff;
                border: 1px solid {pal['border']};
                padding: 4px;
                outline: none;
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {pal['bg']};
                color: #ffffff;
                border: 1.2px solid {pal['border']};
                border-radius: 5px;
                padding: 3px 6px;
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
                background-color: #262626;
                color: #666666;
                border-color: #333333;
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
                color: #ffffff;
                border-bottom: 2.5px solid {pal['accent']};
                font-weight: bold;
            }}
            QListWidget, QTableWidget, QTreeWidget {{
                background-color: {pal['bg']};
                color: {pal['text']};
                border: 1.2px solid {pal['border']};
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
                border: 1px solid #777777;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
            QHeaderView::section {{
                background-color: {pal['card']};
                color: #94a3b8;
                border: 1px solid {pal['border']};
                padding: 4px;
                font-weight: bold;
            }}
        """

    if extra_css:
        css += "\n" + extra_css
    return css


def apply_dialog_theme(dialog: Any, parent: Optional[Any] = None, extra_css: str = "") -> None:
    """Belirtilen diyalog nesnesine geçerli tema stilini uygular."""
    dialog.setStyleSheet(get_dialog_theme_stylesheet(parent, extra_css))

apply_modern_dialog_style = apply_dialog_theme
