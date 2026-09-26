import os
import re
import json
import math
import random
import unicodedata
import urllib.request
import urllib.parse
import tempfile
from typing import Optional, Tuple, Dict, Any, List
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QSpinBox, QCheckBox, QColorDialog, QTabWidget, QWidget,
                             QLineEdit, QFileDialog, QScrollArea, QGridLayout,
                             QFrame, QMessageBox, QProgressBar, QComboBox, QSlider, QSizePolicy, QStackedWidget)
from PyQt6.QtGui import (QPixmap, QImage, QColor, QFont, QIcon, QPainter,
                         QLinearGradient, QPainterPath, QBrush, QPen, QMovie)
from PyQt6.QtCore import (Qt, QSize, QTimer, QUrl, QThread, pyqtSignal,
                          QRectF, QPointF, QPoint, QBuffer, QByteArray, QEvent)
from PyQt6.QtMultimedia import (QMediaCaptureSession, QAudioInput, QMediaRecorder,
                                QMediaPlayer, QAudioOutput, QAudioSource, QAudioFormat, QMediaDevices)
from PyQt6.QtSvg import QSvgRenderer

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet


TABLE_PRESETS = [
    {
        "name": "Modern Şık (Mor)",
        "header_bg": "#7c3aed",
        "header_text_color": "#ffffff",
        "cell_bg": "#ffffff",
        "alt_cell_bg": "#f5f3ff",
        "border_color": "#7c3aed",
        "text_color": "#1e1b4b",
    },
    {
        "name": "Modern Mavi",
        "header_bg": "#0284c7",
        "header_text_color": "#ffffff",
        "cell_bg": "#ffffff",
        "alt_cell_bg": "#f0f9ff",
        "border_color": "#0284c7",
        "text_color": "#0f172a",
    },
    {
        "name": "Zümrüt Yeşili",
        "header_bg": "#059669",
        "header_text_color": "#ffffff",
        "cell_bg": "#ffffff",
        "alt_cell_bg": "#ecfdf5",
        "border_color": "#059669",
        "text_color": "#064e3b",
    },
    {
        "name": "Kurumsal Gri",
        "header_bg": "#334155",
        "header_text_color": "#ffffff",
        "cell_bg": "#ffffff",
        "alt_cell_bg": "#f1f5f9",
        "border_color": "#475569",
        "text_color": "#0f172a",
    },
    {
        "name": "Gün Batımı",
        "header_bg": "#ea580c",
        "header_text_color": "#ffffff",
        "cell_bg": "#ffffff",
        "alt_cell_bg": "#fff7ed",
        "border_color": "#ea580c",
        "text_color": "#431407",
    },
    {
        "name": "Koyu Zarif (Dark)",
        "header_bg": "#1e293b",
        "header_text_color": "#38bdf8",
        "cell_bg": "#0f172a",
        "alt_cell_bg": "#172033",
        "border_color": "#64748b",
        "text_color": "#f8fafc",
    },
]


class TablePreviewWidget(QWidget):
    """Tablo ekleme penceresinde satır, sütun, başlık ve renkleri gösteren canlı önizleme bileşeni."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = 3
        self.cols = 3
        self.has_header = True
        self.header_bg = QColor("#7c3aed")
        self.header_text_color = QColor("#ffffff")
        self.cell_bg = QColor("#ffffff")
        self.alt_cell_bg = QColor("#f5f3ff")
        self.border_color = QColor("#7c3aed")
        self.text_color = QColor("#1e1b4b")
        self.setMinimumSize(250, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; background: rgba(0, 0, 0, 0.2);")

    def update_table(self, rows: int, cols: int, has_header: bool,
                     header_bg: QColor, cell_bg: QColor, border_color: QColor, text_color: QColor,
                     header_text_color: Optional[QColor] = None, alt_cell_bg: Optional[QColor] = None):
        self.rows = max(1, min(rows, 10))
        self.cols = max(1, min(cols, 10))
        self.has_header = has_header
        self.header_bg = QColor(header_bg)
        self.cell_bg = QColor(cell_bg)
        if alt_cell_bg:
            self.alt_cell_bg = QColor(alt_cell_bg)
        else:
            self.alt_cell_bg = self.cell_bg.lighter(118) if self.cell_bg.lightness() < 128 else self.cell_bg.darker(106)
        self.border_color = QColor(border_color)
        self.text_color = QColor(text_color)
        self.header_text_color = QColor(header_text_color) if header_text_color else QColor("#ffffff")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        pad = 14
        rect = self.rect().adjusted(pad, pad, -pad, -pad)
        if rect.width() <= 20 or rect.height() <= 20:
            return

        row_h = rect.height() / max(1, self.rows)
        col_w = rect.width() / max(1, self.cols)

        # 1. Hücre arka planları
        for r in range(self.rows):
            for c in range(self.cols):
                rx = round(rect.x() + c * col_w)
                ry = round(rect.y() + r * row_h)
                rw = round(rect.x() + (c + 1) * col_w) - rx
                rh = round(rect.y() + (r + 1) * row_h) - ry
                cell_rect = QRectF(rx, ry, rw, rh)
                if r == 0 and self.has_header:
                    bg = self.header_bg
                elif r % 2 == 1:
                    bg = self.alt_cell_bg
                else:
                    bg = self.cell_bg
                painter.fillRect(cell_rect, bg)

        # 2. Hücre çizgileri (Net, belirgin ve tam seçilen kenarlık renginde)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        grid_pen = QPen(self.border_color, 1.8, Qt.PenStyle.SolidLine)
        grid_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(grid_pen)
        for r in range(self.rows):
            for c in range(self.cols):
                rx = round(rect.x() + c * col_w)
                ry = round(rect.y() + r * row_h)
                rw = round(rect.x() + (c + 1) * col_w) - rx
                rh = round(rect.y() + (r + 1) * row_h) - ry
                painter.drawRect(QRectF(rx, ry, rw, rh))

        # Dış sınır çerçevesi (Kenarlık renginde, belirgin)
        outer_pen = QPen(self.border_color, 2.4, Qt.PenStyle.SolidLine)
        outer_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(outer_pen)
        painter.drawRect(rect)

        # 3. Örnek metinler
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font_sz = max(7, int(min(row_h * 0.38, col_w * 0.22, 10)))
        font = QFont("Segoe UI", font_sz)
        header_font = QFont("Segoe UI", font_sz, QFont.Weight.Bold)

        for r in range(self.rows):
            is_hdr = (r == 0 and self.has_header)
            painter.setFont(header_font if is_hdr else font)
            painter.setPen(self.header_text_color if is_hdr else self.text_color)
            for c in range(self.cols):
                rx = round(rect.x() + c * col_w)
                ry = round(rect.y() + r * row_h)
                rw = round(rect.x() + (c + 1) * col_w) - rx
                rh = round(rect.y() + (r + 1) * row_h) - ry
                txt_rect = QRectF(rx + 2, ry + 1, rw - 4, rh - 2)
                txt = f"Başlık {c+1}" if is_hdr else f"Hücre {r},{c+1}"
                painter.drawText(txt_rect, Qt.AlignmentFlag.AlignCenter, txt)


def make_color_icon(color: QColor) -> QIcon:
    pix = QPixmap(18, 18)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QBrush(color))
    border_pen = QPen(QColor(255, 255, 255, 180) if color.lightness() < 120 else QColor(0, 0, 0, 90), 1.2)
    p.setPen(border_pen)
    p.drawEllipse(1, 1, 15, 15)
    p.end()
    return QIcon(pix)


def make_preset_icon(header_color: str, cell_color: str) -> QIcon:
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(header_color)))
    p.drawRoundedRect(QRectF(1, 1, 18, 8), 3, 3)
    p.setBrush(QBrush(QColor(cell_color)))
    p.drawRoundedRect(QRectF(1, 10, 18, 9), 3, 3)
    p.setPen(QPen(QColor(255, 255, 255, 70), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(1, 1, 18, 18), 3, 3)
    p.end()
    return QIcon(pix)


def make_stepper_icon(is_plus: bool) -> QIcon:
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor("#cbd5e1"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(5, 10, 15, 10)
    if is_plus:
        p.drawLine(10, 5, 10, 15)
    p.end()
    return QIcon(pix)


class ModernStepperWidget(QFrame):
    """
    Apple / Figma tarzı modern bütünleşik (pill/segment) sayı seçici.
    - Tek ve derli toplu bir kapsayıcı içinde '-' ve '+' butonları.
    - Taşma yapmayan kompakt boyut ve pürüzsüz hover/basma efektleri.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, value: int = 3, min_val: int = 1, max_val: int = 10, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self._val = max(min_val, min(max_val, value))

        self.setFixedHeight(32)
        self.setFixedWidth(98)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 7px;
            }
            QFrame:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 0px !important;
                margin: 0px !important;
                min-width: 0px !important;
                min-height: 0px !important;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.18);
                border-color: #38bdf8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(56, 189, 248, 0.25);
            }
            QLabel {
                color: #f1f5f9;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self.btn_minus = QPushButton()
        self.btn_minus.setIcon(make_stepper_icon(False))
        self.btn_minus.setFixedSize(24, 24)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.setToolTip("Azalt")
        self.btn_minus.clicked.connect(self.decrement)
        layout.addWidget(self.btn_minus)

        self.lbl_value = QLabel(str(self._val))
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_value, 1)

        self.btn_plus = QPushButton()
        self.btn_plus.setIcon(make_stepper_icon(True))
        self.btn_plus.setFixedSize(24, 24)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setToolTip("Artır")
        self.btn_plus.clicked.connect(self.increment)
        layout.addWidget(self.btn_plus)

    def value(self) -> int:
        return self._val

    def setValue(self, v: int):
        new_v = max(self.min_val, min(self.max_val, v))
        if new_v != self._val:
            self._val = new_v
            self.lbl_value.setText(str(self._val))
            self.valueChanged.emit(self._val)

    def increment(self):
        self.setValue(self._val + 1)

    def decrement(self):
        self.setValue(self._val - 1)


class TableInsertDialog(QDialog):
    """Tablo ekleme diyalogu: Satır, sütun, tablo şekilleri/şablonları, metin/renk ve canlı önizleme."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tablo Ekle")
        self.setFixedSize(740, 530)
        self.setStyleSheet(get_dialog_theme_stylesheet(self))

        self.border_color = QColor("#7c3aed")
        self.header_bg = QColor("#7c3aed")
        self.header_text_color = QColor("#ffffff")
        self.cell_bg = QColor("#ffffff")
        self.alt_cell_bg = QColor("#f5f3ff")
        self.text_color = QColor("#1e1b4b")
        self.font_size = 11

        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)
        root_layout.setContentsMargins(18, 18, 18, 18)

        # Üst başlık
        hdr = QLabel("Tablo Ekle")
        hdr.setStyleSheet("font-size: 16px; font-weight: bold; ")
        root_layout.addWidget(hdr)

        desc = QLabel("PDF sayfasına eklenecek tablonun satır, sütun ve stil şablonunu belirleyin (Maks. 10x10). Sağdaki panelden canlı olarak önizleyebilirsiniz.")
        desc.setWordWrap(True)
        desc.setStyleSheet(" font-size: 11px;")
        root_layout.addWidget(desc)

        # İki Kolonlu Gövde
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # --- SOL KOLON (Parametreler, Şablonlar ve Renkler) ---
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # 1. Satır ve Sütun (Modern Bütünleşik Stepper Kontrolleri)
        form_frame = QFrame()
        form_frame.setObjectName("StepperFormFrame")
        form_frame.setStyleSheet("""
            QFrame#StepperFormFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(12, 10, 12, 10)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(8)

        lbl_rows = QLabel("Satır:")
        lbl_rows.setStyleSheet(" font-weight: 600; font-size: 13px; border: none; background: transparent;")
        self.spin_rows = ModernStepperWidget(3, 1, 10)
        self.spin_rows.valueChanged.connect(self._on_params_changed)

        lbl_cols = QLabel("Sütun:")
        lbl_cols.setStyleSheet(" font-weight: 600; font-size: 13px; border: none; background: transparent;")
        self.spin_cols = ModernStepperWidget(3, 1, 10)
        self.spin_cols.valueChanged.connect(self._on_params_changed)

        form_layout.addWidget(lbl_rows, 0, 0)
        form_layout.addWidget(self.spin_rows, 0, 1)
        form_layout.addWidget(lbl_cols, 0, 2)
        form_layout.addWidget(self.spin_cols, 0, 3)

        self.chk_header = QCheckBox("İlk satırı başlık olarak vurgula")
        self.chk_header.setChecked(True)
        self.chk_header.setStyleSheet("""
            QCheckBox {
                color: #f1f5f9;
                font-size: 12px;
                font-weight: 500;
                spacing: 8px;
                border: none;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border: 1.5px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.06);
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self.chk_header.toggled.connect(self._on_params_changed)
        form_layout.addWidget(self.chk_header, 1, 0, 1, 4)

        left_col.addWidget(form_frame)

        # 2. Tablo Şekilleri / Şablonlar
        lbl_presets = QLabel("Tablo Şekilleri (Şablonlar):")
        lbl_presets.setStyleSheet(" font-weight: bold; font-size: 11px;")
        left_col.addWidget(lbl_presets)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        self.theme_buttons = []

        for idx, pr in enumerate(TABLE_PRESETS):
            btn = QPushButton(f" {pr['name']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(make_preset_icon(pr["header_bg"], pr["cell_bg"]))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #f1f5f9;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    padding: 7px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda ch, p=pr, b=btn: self._apply_preset(p, b))
            preset_grid.addWidget(btn, idx // 2, idx % 2)
            self.theme_buttons.append(btn)

        left_col.addLayout(preset_grid)

        # 3. Renkleri Özelleştir
        lbl_colors = QLabel("Renkleri Özelleştir:")
        lbl_colors.setStyleSheet(" font-size: 11px; font-weight: bold;")
        left_col.addWidget(lbl_colors)

        colors_grid = QGridLayout()
        colors_grid.setSpacing(6)

        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: #38bdf8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(56, 189, 248, 0.2);
            }
        """

        self.btn_text_col = QPushButton(" Metin Rengi")
        self.btn_text_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_text_col.setStyleSheet(btn_style)
        self.btn_text_col.setIcon(make_color_icon(self.text_color))
        self.btn_text_col.clicked.connect(self._pick_text_color)

        self.btn_border_col = QPushButton(" Kenarlık Rengi")
        self.btn_border_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_border_col.setStyleSheet(btn_style)
        self.btn_border_col.setIcon(make_color_icon(self.border_color))
        self.btn_border_col.clicked.connect(self._pick_border_color)

        self.btn_header_bg = QPushButton(" Başlık Rengi")
        self.btn_header_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_header_bg.setStyleSheet(btn_style)
        self.btn_header_bg.setIcon(make_color_icon(self.header_bg))
        self.btn_header_bg.clicked.connect(self._pick_header_bg)

        self.btn_cell_bg = QPushButton(" Hücre Rengi")
        self.btn_cell_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cell_bg.setStyleSheet(btn_style)
        self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))
        self.btn_cell_bg.clicked.connect(self._pick_cell_bg)

        colors_grid.addWidget(self.btn_text_col, 0, 0)
        colors_grid.addWidget(self.btn_border_col, 0, 1)
        colors_grid.addWidget(self.btn_header_bg, 1, 0)
        colors_grid.addWidget(self.btn_cell_bg, 1, 1)
        left_col.addLayout(colors_grid)

        left_col.addStretch()
        body_layout.addLayout(left_col, 5)

        # --- SAĞ KOLON (Canlı Önizleme) ---
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        lbl_pv = QLabel("Canlı Tablo Önizlemesi:")
        lbl_pv.setStyleSheet(" font-weight: bold; font-size: 12px;")
        right_col.addWidget(lbl_pv)

        self.preview_widget = TablePreviewWidget(self)
        right_col.addWidget(self.preview_widget, 1)

        lbl_tip = QLabel("Tablo sayfaya eklendikten sonra köşelerinden tutularak serbestçe boyutlandırılabilir.")
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet(" font-size: 10px;")
        right_col.addWidget(lbl_tip)

        body_layout.addLayout(right_col, 6)
        root_layout.addLayout(body_layout)

        # Alt Butonlar
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #475569;
                color: #ffffff;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Tabloyu Ekle")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        root_layout.addLayout(btn_box)

        self._update_preview()

    def _apply_preset(self, p: Dict[str, str], clicked_btn: Optional[QPushButton] = None):
        self.header_bg = QColor(p["header_bg"])
        self.cell_bg = QColor(p["cell_bg"])
        self.border_color = QColor(p["border_color"])
        self.text_color = QColor(p["text_color"])
        self.header_text_color = QColor(p.get("header_text_color", "#ffffff"))
        if "alt_cell_bg" in p:
            self.alt_cell_bg = QColor(p["alt_cell_bg"])
        else:
            self.alt_cell_bg = self.cell_bg.lighter(118) if self.cell_bg.lightness() < 128 else self.cell_bg.darker(106)

        # İkonları ve buton renklerini güncelle
        self.btn_text_col.setIcon(make_color_icon(self.text_color))
        self.btn_border_col.setIcon(make_color_icon(self.border_color))
        self.btn_header_bg.setIcon(make_color_icon(self.header_bg))
        self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))

        # Seçili şablonu vurgula
        for btn in self.theme_buttons:
            if btn == clicked_btn:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0f172a;
                        color: #38bdf8;
                        border: 1.5px solid #38bdf8;
                        border-radius: 8px;
                        padding: 7px 10px;
                        font-size: 11px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e293b;
                        color: #e2e8f0;
                        border: 1.5px solid #334155;
                        border-radius: 8px;
                        padding: 7px 10px;
                        font-size: 11px;
                        font-weight: 600;
                        text-align: left;
                    }
                    QPushButton:hover {
                        border-color: #38bdf8;
                        background-color: #334155;
                    }
                """)

        self._update_preview()

    def _on_params_changed(self):
        self._update_preview()

    def _update_preview(self):
        if hasattr(self, 'preview_widget'):
            self.preview_widget.update_table(
                rows=self.spin_rows.value(),
                cols=self.spin_cols.value(),
                has_header=self.chk_header.isChecked(),
                header_bg=self.header_bg,
                cell_bg=self.cell_bg,
                border_color=self.border_color,
                text_color=self.text_color,
                header_text_color=self.header_text_color,
                alt_cell_bg=self.alt_cell_bg
            )

    def _pick_text_color(self):
        col = QColorDialog.getColor(self.text_color, self, "Metin Rengi Seç")
        if col.isValid():
            self.text_color = col
            self.btn_text_col.setIcon(make_color_icon(self.text_color))
            self._update_preview()

    def _pick_border_color(self):
        col = QColorDialog.getColor(self.border_color, self, "Kenarlık Rengi Seç")
        if col.isValid():
            self.border_color = col
            self.btn_border_col.setIcon(make_color_icon(self.border_color))
            self._update_preview()

    def _pick_header_bg(self):
        col = QColorDialog.getColor(self.header_bg, self, "Başlık Arkaplanı Seç")
        if col.isValid():
            self.header_bg = col
            self.btn_header_bg.setIcon(make_color_icon(self.header_bg))
            self._update_preview()

    def _pick_cell_bg(self):
        col = QColorDialog.getColor(self.cell_bg, self, "Hücre Arkaplanı Seç")
        if col.isValid():
            self.cell_bg = col
            self.alt_cell_bg = self.cell_bg.lighter(118) if self.cell_bg.lightness() < 128 else self.cell_bg.darker(106)
            self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))
            self._update_preview()

    def get_data(self) -> Dict[str, Any]:
        return {
            "rows": self.spin_rows.value(),
            "cols": self.spin_cols.value(),
            "has_header": self.chk_header.isChecked(),
            "border_color": self.border_color.name(),
            "header_bg": self.header_bg.name(),
            "header_text_color": self.header_text_color.name(),
            "cell_bg": self.cell_bg.name(),
            "alt_cell_bg": self.alt_cell_bg.name(),
            "text_color": self.text_color.name(),
        }


class TableStyleDialog(QDialog):
    """
    Eklenmiş bir tablonun metin tipi, punto boyutu, metin rengi ve hücre renklerini
    ayarlamayı sağlayan stil penceresi (Metin kutusu ayarları gibi).
    """
    def __init__(self, table_item, parent=None):
        super().__init__(parent)
        self.table_item = table_item
        self.setWindowTitle("Tablo Metin ve Renk Ayarları")
        self.setFixedSize(480, 590)
        self.setStyleSheet(get_dialog_theme_stylesheet(self))

        self.text_color = QColor(table_item.text_color)
        self.header_text_color = QColor(table_item.header_text_color)
        self.header_bg = QColor(table_item.header_bg)
        self.cell_bg = QColor(table_item.cell_bg)
        self.alt_cell_bg = getattr(table_item, 'alt_cell_bg', QColor(self.cell_bg.darker(106) if self.cell_bg.lightness() > 128 else self.cell_bg.lighter(118)))
        self.border_color = QColor(table_item.border_color)
        self.font_family = table_item.font_family
        self.font_size = int(table_item.font_size)
        self.bold = getattr(table_item, 'bold', False)
        self.italic = getattr(table_item, 'italic', False)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        hdr = QLabel("Tablo Metin ve Renk Ayarları")
        hdr.setStyleSheet("font-size: 15px; font-weight: bold; ")
        layout.addWidget(hdr)

        # 1. Hızlı Şablonlar
        lbl_pr = QLabel("Hızlı Şablon Uygula:")
        lbl_pr.setStyleSheet(" font-weight: bold; font-size: 11px;")
        layout.addWidget(lbl_pr)

        pr_grid = QGridLayout()
        pr_grid.setSpacing(6)
        self.preset_buttons = []
        for idx, pr in enumerate(TABLE_PRESETS):
            btn = QPushButton(f" {pr['name']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(make_preset_icon(pr["header_bg"], pr["cell_bg"]))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #e2e8f0;
                    border: 1.5px solid #334155;
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: left;
                }
                QPushButton:hover {
                    border-color: #38bdf8;
                    background-color: #334155;
                }
            """)
            btn.clicked.connect(lambda ch, p=pr, b=btn: self._apply_preset(p, b))
            pr_grid.addWidget(btn, idx // 2, idx % 2)
            self.preset_buttons.append(btn)
        layout.addLayout(pr_grid)

        # 2. Yazı Tipi ve Boyutu
        font_frame = QFrame()
        font_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        ff_layout = QGridLayout(font_frame)
        ff_layout.setSpacing(8)

        lbl_fam = QLabel("Yazı Tipi:")
        lbl_fam.setStyleSheet(" font-weight: 600; border: none; background: transparent;")
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(["Arial", "Times New Roman", "Courier New", "Segoe UI", "Calibri", "Georgia", "Verdana", "Tahoma"])
        self.cmb_font.setStyleSheet("""
            QComboBox {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1.5px solid #334155;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #38bdf8;
            }
        """)
        idx = self.cmb_font.findText(self.font_family)
        if idx >= 0: self.cmb_font.setCurrentIndex(idx)
        self.cmb_font.currentTextChanged.connect(self._on_font_changed)

        lbl_sz = QLabel("Yazı Boyutu:")
        lbl_sz.setStyleSheet(" font-weight: 600; border: none; background: transparent;")
        self.slider_sz = QSlider(Qt.Orientation.Horizontal)
        self.slider_sz.setRange(8, 36)
        self.slider_sz.setValue(self.font_size)
        self.lbl_sz_val = QLabel(f"{self.font_size} pt")
        self.lbl_sz_val.setStyleSheet(" font-weight: bold; border: none; background: transparent;")
        self.slider_sz.valueChanged.connect(self._on_size_changed)

        ff_layout.addWidget(lbl_fam, 0, 0)
        ff_layout.addWidget(self.cmb_font, 0, 1, 1, 2)
        ff_layout.addWidget(lbl_sz, 1, 0)
        ff_layout.addWidget(self.slider_sz, 1, 1)
        ff_layout.addWidget(self.lbl_sz_val, 1, 2)

        # Kalın ve İtalik Butonları
        toggle_btn_style = """
            QPushButton {
                padding: 6px 14px;
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:checked {
                background-color: rgba(56, 189, 248, 0.25);
                color: #38bdf8;
                border: 1px solid #38bdf8;
            }
            QPushButton:hover:!checked {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.3);
                color: #ffffff;
            }
        """
        btn_row = QHBoxLayout()
        self.btn_bold = QPushButton("Kalın (B)")
        self.btn_bold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setChecked(self.bold)
        self.btn_bold.setStyleSheet(toggle_btn_style)
        self.btn_bold.clicked.connect(self._on_style_changed)

        self.btn_italic = QPushButton("İtalik (I)")
        self.btn_italic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setChecked(self.italic)
        self.btn_italic.setStyleSheet(toggle_btn_style)
        self.btn_italic.clicked.connect(self._on_style_changed)

        btn_row.addWidget(self.btn_bold)
        btn_row.addWidget(self.btn_italic)
        ff_layout.addLayout(btn_row, 2, 0, 1, 3)

        layout.addWidget(font_frame)

        # 3. Renk Seçimleri
        lbl_colors = QLabel("Özel Renk Seçenekleri:")
        lbl_colors.setStyleSheet(" font-weight: bold; font-size: 11px;")
        layout.addWidget(lbl_colors)

        c_grid = QGridLayout()
        c_grid.setSpacing(6)

        c_btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: #38bdf8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(56, 189, 248, 0.2);
            }
        """

        self.btn_txt_col = QPushButton(" Hücre Metin Rengi")
        self.btn_txt_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_txt_col.setStyleSheet(c_btn_style)
        self.btn_txt_col.setIcon(make_color_icon(self.text_color))
        self.btn_txt_col.clicked.connect(self._pick_text_color)

        self.btn_hdr_txt_col = QPushButton(" Başlık Metin Rengi")
        self.btn_hdr_txt_col.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hdr_txt_col.setStyleSheet(c_btn_style)
        self.btn_hdr_txt_col.setIcon(make_color_icon(self.header_text_color))
        self.btn_hdr_txt_col.clicked.connect(self._pick_header_text_color)

        self.btn_hdr_bg = QPushButton(" Başlık Arkaplanı")
        self.btn_hdr_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hdr_bg.setStyleSheet(c_btn_style)
        self.btn_hdr_bg.setIcon(make_color_icon(self.header_bg))
        self.btn_hdr_bg.clicked.connect(self._pick_header_bg)

        self.btn_cell_bg = QPushButton(" Hücre Arkaplanı")
        self.btn_cell_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cell_bg.setStyleSheet(c_btn_style)
        self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))
        self.btn_cell_bg.clicked.connect(self._pick_cell_bg)

        self.btn_border = QPushButton(" Kenarlık Rengi")
        self.btn_border.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_border.setStyleSheet(c_btn_style)
        self.btn_border.setIcon(make_color_icon(self.border_color))
        self.btn_border.clicked.connect(self._pick_border_color)

        c_grid.addWidget(self.btn_txt_col, 0, 0)
        c_grid.addWidget(self.btn_hdr_txt_col, 0, 1)
        c_grid.addWidget(self.btn_hdr_bg, 1, 0)
        c_grid.addWidget(self.btn_cell_bg, 1, 1)
        c_grid.addWidget(self.btn_border, 2, 0, 1, 2)
        layout.addLayout(c_grid)

        layout.addStretch()

        # Butonlar
        btn_box = QHBoxLayout()
        btn_close = QPushButton("Kapat")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                
                
                font-size: 12px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                
            }
            QPushButton:pressed {
                
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _apply_preset(self, p: Dict[str, str], clicked_btn: Optional[QPushButton] = None):
        self.header_bg = QColor(p["header_bg"])
        self.cell_bg = QColor(p["cell_bg"])
        self.border_color = QColor(p["border_color"])
        self.text_color = QColor(p["text_color"])
        self.header_text_color = QColor(p.get("header_text_color", "#ffffff"))
        if "alt_cell_bg" in p:
            self.alt_cell_bg = QColor(p["alt_cell_bg"])
        else:
            self.alt_cell_bg = self.cell_bg.lighter(118) if self.cell_bg.lightness() < 128 else self.cell_bg.darker(106)

        # İkonları güncelle
        self.btn_txt_col.setIcon(make_color_icon(self.text_color))
        self.btn_hdr_txt_col.setIcon(make_color_icon(self.header_text_color))
        self.btn_hdr_bg.setIcon(make_color_icon(self.header_bg))
        self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))
        self.btn_border.setIcon(make_color_icon(self.border_color))

        for btn in getattr(self, 'preset_buttons', []):
            if btn == clicked_btn:
                btn.setStyleSheet("""
                    QPushButton {
                        
                        
                        border: 1.5px solid #38bdf8;
                        border-radius: 8px;
                        padding: 6px 10px;
                        font-size: 11px;
                        font-weight: 600;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.06);
                        color: #f1f5f9;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 8px;
                        padding: 6px 10px;
                        font-size: 11px;
                        font-weight: 600;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 0.12);
                        border-color: #38bdf8;
                        color: #ffffff;
                    }
                """)
        self._apply()

    def _on_font_changed(self, fam):
        self.font_family = fam
        self._apply()

    def _on_size_changed(self, val):
        self.font_size = val
        self.lbl_sz_val.setText(f"{val} pt")
        self._apply()

    def _on_style_changed(self):
        self.bold = self.btn_bold.isChecked()
        self.italic = self.btn_italic.isChecked()
        self._apply()

    def _pick_text_color(self):
        col = QColorDialog.getColor(self.text_color, self, "Hücre Metin Rengi")
        if col.isValid():
            self.text_color = col
            self.btn_txt_col.setIcon(make_color_icon(self.text_color))
            self._apply()

    def _pick_header_text_color(self):
        col = QColorDialog.getColor(self.header_text_color, self, "Başlık Metin Rengi")
        if col.isValid():
            self.header_text_color = col
            self.btn_hdr_txt_col.setIcon(make_color_icon(self.header_text_color))
            self._apply()

    def _pick_header_bg(self):
        col = QColorDialog.getColor(self.header_bg, self, "Başlık Arkaplan Rengi")
        if col.isValid():
            self.header_bg = col
            self.btn_hdr_bg.setIcon(make_color_icon(self.header_bg))
            self._apply()

    def _pick_cell_bg(self):
        col = QColorDialog.getColor(self.cell_bg, self, "Hücre Arkaplan Rengi")
        if col.isValid():
            self.cell_bg = col
            self.alt_cell_bg = self.cell_bg.lighter(118) if self.cell_bg.lightness() < 128 else self.cell_bg.darker(106)
            self.btn_cell_bg.setIcon(make_color_icon(self.cell_bg))
            self._apply()

    def _pick_border_color(self):
        col = QColorDialog.getColor(self.border_color, self, "Kenarlık Rengi")
        if col.isValid():
            self.border_color = col
            self.btn_border.setIcon(make_color_icon(self.border_color))
            self._apply()

    def _apply(self):
        t = self.table_item
        t.font_family = self.font_family
        t.font_size = float(self.font_size)
        t.bold = self.bold
        t.italic = self.italic
        t.text_color = self.text_color
        t.header_text_color = self.header_text_color
        t.header_bg = self.header_bg
        t.cell_bg = self.cell_bg
        t.alt_cell_bg = self.alt_cell_bg
        t.border_color = self.border_color
        t._sync_record()
        t.update()
        if hasattr(t.tab_doc, 'notify_drawings_changed'):
            t.tab_doc.notify_drawings_changed(t.record.get("page"))


TR_EMOJI_NAMES: Dict[str, str] = {
    # Yüzler
    "😀": "Sırıtan Yüz", "😃": "Geniş Gülen Yüz", "😄": "Mutlu Gülen Gözler", "😁": "Diş Gösteren Yüz",
    "😆": "Kısık Gözlü Gülen", "😅": "Terleyen Gülen Yüz", "🤣": "Gülmekten Yerlere Yatan", "😂": "Gözlerinden Yaş Gelen Gülen",
    "🙂": "Hafif Gülümseyen", "🙃": "Ters Yüz", "😉": "Göz Kırpan Yüz", "😊": "Tebessüm Eden",
    "😇": "Melek Yüzü", "🥰": "Aşık ve Sevecen", "😍": "Kalp Gözlü Yüz", "🤩": "Yıldız Gözlü Hayran",
    "😘": "Öpücük Atan", "😗": "Öpücük Yüzü", "😚": "Gözleri Kapalı Öpen", "😋": "Lezzetli / Dili Dışarıda",
    "😛": "Dil Çıkaran", "😜": "Göz Kırpıp Dil Çıkaran", "🤪": "Çılgın / Eğlenceli Yüz", "😝": "Kısık Gözle Dil Çıkaran",
    "🤑": "Para Düşkünü", "🤗": "Kucaklayan Yüz", "🤭": "Eliyle Ağzını Kapatan", "🤫": "Sessiz Ol / Şşş",
    "🤔": "Düşünen Yüz", "🤐": "Ağzı Fermuarlı", "🤨": "Tek Kaşı Havada", "😐": "Nötr Yüz",
    "😑": "İfadesiz Yüz", "😶": "Ağızsız Yüz", "😏": "Alaycı Gülüş", "😒": "Memnuniyetsiz",
    "🙄": "Göz Deviren", "😬": "Diş Sıkan / Gergin", "🤥": "Yalancı (Pinokyo)", "😌": "Huzurlu Yüz",
    "😔": "Düşünceli / Hüzünlü", "😪": "Uykulu Yüz", "🤤": "Ağzı Sulanmış", "😴": "Uyuyan Yüz",
    "😷": "Maskeli Yüz", "🤒": "Termometreli / Ateşli", "🤕": "Sargılı Yüz", "🤢": "Midesi Bulanan",
    "🤮": "Kusan Yüz", "🤧": "Hapşıran Yüz", "🥵": "Aşırı Sıcaklamış", "🥶": "Donmuş / Üşümüş",
    "🥴": "Çakırkeyif / Sersem", "😵": "Baş Dönmesi", "🤯": "Beyni Yanan / Şok", "🤠": "Kovboy Şapkalı",
    "🥳": "Kutlama / Parti Yapan", "😎": "Güneş Gözlüklü / Havalı", "🤓": "Gözlüklü / Zeki", "🧐": "Monokllü Meraklı",
    "😕": "Kafası Karışık", "😟": "Endişeli Yüz", "🙁": "Hafif Üzgün", "😮": "Ağzı Açık Şaşkın",
    "😲": "Çok Şaşırmış", "😳": "Utanmış / Kızarmış", "🥺": "Yalvaran / Masum Bakış", "😦": "Şaşkın ve Üzgün",
    "😧": "Acı Çeken", "😨": "Korkan Yüz", "😰": "Soğuk Ter Döken", "😥": "Rahatlamış Üzüntü",
    "😢": "Ağlayan Yüz", "😭": "Hıçkıra Hıçkıra Ağlayan", "😱": "Çığlık Atan / Dehşet", "😖": "Bunalmış Yüz",
    "😣": "Tahammül Eden", "😞": "Hayal Kırıklığı", "😓": "Zorlanan Yüz", "😩": "Yorulmuş / Bıkmış",

    # İnsanlar / Eller
    "👋": "El Sallama", "🤚": "Kalkık El", "🖐️": "Açık Beş Parmak", "✋": "Dur El / Selam",
    "🖖": "Volkan Selamı", "👌": "Harika / Tamam", "🤌": "Parmak Uçları Birleşik (İtalyan)", "🤏": "Birazcık / Azcık",
    "✌️": "Zafer / Barış İşareti", "🤞": "Şans Dileği", "🤟": "Seni Seviyorum İşareti", "🤘": "Rock İşareti",
    "🤙": "Ara Beni / Havalı", "👈": "Solu Gösteren Parmak", "👉": "Sağı Gösteren Parmak", "👆": "Yukarıyı Gösteren Parmak",
    "👇": "Aşağıyı Gösteren Parmak", "☝️": "İşaret Parmağı", "👍": "Beğendim (Onay)", "👎": "Beğenmedim (Ret)",
    "✊": "Yumruk", "👊": "Öne Yumruk / Çak", "🤛": "Sola Yumruk", "🤜": "Sağa Yumruk",
    "👏": "Alkış", "🙌": "Elleri Havaya Kaldırma", "👐": "Açık Eller", "🤲": "Dua Eden Eller",
    "🤝": "El Sıkışma", "🙏": "Teşekkür / Rica / Dua", "✍️": "Yazı Yazan El", "💅": "Oje Sürme",
    "🤳": "Selfie Çeken", "💪": "Pazı / Güç", "🦾": "Mekanik Kol", "🦿": "Mekanik Bacak",
    "🦵": "Bacak", "🦶": "Ayak", "👂": "Kulak", "🦻": "İşitme Cihazlı Kulak",
    "👃": "Burun", "🧠": "Beyin / Zeka", "👀": "Gözler (Dikkat)", "👁️": "Göz",
    "👅": "Dil", "👄": "Dudak / Ağız", "🧑": "Kişi / İnsan", "👧": "Kız Çocuğu",

    # Doğa
    "🐶": "Köpek", "🐱": "Kedi", "🐭": "Fare", "🐹": "Hamster", "🐰": "Tavşan", "🦊": "Tilki",
    "🐻": "Ayı", "🐼": "Panda", "🐨": "Koala", "🐯": "Kaplan", "🦁": "Aslan", "🐮": "İnek",
    "🐷": "Domuz", "🐸": "Kurbağa", "🐵": "Maymun", "🐔": "Tavuk", "🐧": "Penguen", "🐦": "Kuş",
    "🐤": "Civciv", "🦆": "Ördek", "🦅": "Kartal", "🦉": "Baykuş", "🐺": "Kurt", "🐗": "Yaban Domuzu",
    "🐴": "At", "🦄": "Tekboynuz (Unicorn)", "🐝": "Arı", "🐛": "Tırtıl", "🦋": "Kelebek", "🐌": "Salyangoz",
    "🐞": "Uğur Böceği", "🐜": "Karınca", "🐢": "Kaplumbağa", "🐍": "Yılan", "🐙": "Ahtapot", "🦑": "Mürekkep Balığı",
    "🦐": "Karides", "🦞": "Istakoz", "🦀": "Yengeç", "🐬": "Yunus", "🐳": "Balina", "🦈": "Köpekbalığı",
    "🐊": "Timsah", "🐅": "Kaplan", "🐘": "Fil", "🦛": "Su Aygırı", "🦒": "Zürafa", "🌲": "Çam Ağacı",
    "🌳": "Yapraklı Ağaç", "🌴": "Palmiye", "🌵": "Kaktüs", "🌷": "Lale", "🌸": "Kiraz Çiçeği",
    "🌹": "Gül", "🌺": "Ebegümeci Çiçeği", "🌻": "Ayçiçeği", "🌼": "Papatya", "🌿": "Yeşil Dal",
    "🍀": "Dört Yapraklı Yonca", "🍁": "Akçaağaç Yaprağı", "🍂": "Dökülmüş Yaprak", "🍃": "Rüzgarda Yaprak",
    "☀️": "Güneş", "🌙": "Hilal Ay",

    # Yiyecek
    "🍏": "Yeşil Elma", "🍎": "Kırmızı Elma", "🍐": "Armut", "🍊": "Mandalina / Portakal",
    "🍋": "Limon", "🍌": "Muz", "🍉": "Karpuz", "🍇": "Üzüm", "🍓": "Çilek", "🫐": "Yaban Mersini",
    "🍈": "Kavun", "🍒": "Kiraz", "🍑": "Şeftali", "🍍": "Ananas", "🥥": "Hindistan Cevizi", "🥝": "Kivi",
    "🍅": "Domates", "🥑": "Avokado", "🥦": "Brokoli", "🥒": "Salatalık", "🌶️": "Acı Biber",
    "🌽": "Mısır", "🥕": "Havuç", "🥔": "Patates", "🥐": "Kruvasan", "🍞": "Ekmek", "🥖": "Baget Ekmek",
    "🥨": "Pretzel Simit", "🧀": "Peynir", "🥚": "Yumurta", "🍳": "Tavada Yumurta", "🥓": "Pastırma",
    "🥩": "Et Parçası", "🍗": "Tavuk But", "🍖": "Kemikli Et", "🌭": "Sosisli Sandviç", "🍔": "Hamburger",
    "🍟": "Patates Kızartması", "🍕": "Pizza", "🥪": "Sandviç", "🌮": "Tako", "🌯": "Dürüm (Burrito)",
    "🥗": "Yeşil Salata", "🍝": "Spagetti Makarna", "🍜": "Erişte / Ramen Kasesi", "🍣": "Suşi",
    "🍱": "Bento Kutusu", "🍦": "Yumuşak Dondurma", "🍧": "Buzlu Tatlı", "🍨": "Dondurma Kasesi",
    "🍩": "Donut", "🍪": "Kurabiye", "🎂": "Doğum Günü Pastası", "🍰": "Pasta Dilimi", "🧁": "Kapkek",
    "🍫": "Çikolata", "🍬": "Şeker", "🍭": "Lolipop", "🍿": "Patlamış Mısır", "☕": "Sıcak Kahve / Çay",
    "🍵": "Yeşil Çay", "🧃": "Meyve Suyu Kutusu", "🥤": "Pipetli İçecek", "🍺": "Bira Bardağı",

    # Aktiviteler
    "⚽": "Futbol Topu", "🏀": "Basketbol", "🏈": "Amerikan Futbolu", "⚾": "Beyzbol",
    "🥎": "Softbol", "🎾": "Tenis", "🏐": "Voleybol", "🥏": "Frizbi", "🎱": "Bilardo Topu",
    "🏓": "Masa Tenisi", "🏸": "Badminton", "🏒": "Buz Hokeyi", "🏏": "Kriket", "🥊": "Boks Eldiveni",
    "🥋": "Dövüş Kıyafeti", "🎯": "Hedef Tahtası", "⛳": "Golf Bayrağı", "🎣": "Balık Oltası",
    "🎿": "Kayak", "🏂": "Snowboard", "🏋️": "Ağırlık Kaldırma", "🤼": "Güreş", "🤸": "Jimnastik / Takla",
    "⛹️": "Top Süren Oyuncu", "🏄": "Sörf Yapan", "🏊": "Yüzen Kişi", "🚴": "Bisikletçi",
    "🏆": "Şampiyonluk Kupası", "🥇": "Altın Madalya (1.)", "🥈": "Gümüş Madalya (2.)",
    "🥉": "Bronz Madalya (3.)", "🏅": "Spor Madalyası", "🎖️": "Onur Nişanı / Madalya",
    "🎫": "Bilet", "🎟️": "Giriş Bileti", "🎪": "Sirk Çadırı", "🎨": "Ressam Paleti",
    "🎬": "Klaket / Sinema", "🎤": "Mikrofon", "🎧": "Kulaklık", "🎼": "Müzik Notaları",
    "🎹": "Piyano Klavyesi", "🥁": "Davul", "🎸": "Gitar", "🎲": "Oyun Zarı", "🧩": "Yapboz Parçası",
    "🎮": "Oyun Kolu / Gamepad",

    # Semboller
    "💡": "Ampul / Yeni Fikir", "🔦": "El Feneri", "🧱": "Tuğla", "🔑": "Anahtar", "🗝️": "Antika Anahtar",
    "🔨": "Çekiç", "🛠️": "Tamir Aletleri", "⚙️": "Dişli / Ayarlar", "💣": "Bomba", "🔫": "Su Tabancası",
    "🛡️": "Kalkan / Güvenlik", "🔮": "Kristal Küre", "🧪": "Deney Tüpü", "🧬": "DNA Sarmalı",
    "⏰": "Çalar Saat", "⏱️": "Kronometre", "⌛": "Kum Saati", "❤️": "Kırmızı Kalp",
    "🧡": "Turuncu Kalp", "💛": "Sarı Kalp", "💚": "Yeşil Kalp", "💙": "Mavi Kalp",
    "💜": "Mor Kalp", "🖤": "Siyah Kalp", "🤍": "Beyaz Kalp", "🤎": "Kahverengi Kalp",
    "💔": "Kırık Kalp", "❣️": "Ünlem Kalp", "💕": "İki Kalp", "💞": "Dönen Kalpler",
    "💓": "Atan Kalp", "💗": "Büyüyen Kalp", "💖": "Pırıldayan Kalp", "💘": "Oklu Kalp",
    "💝": "Kurdeleli Kalp", "✨": "Parıltı / Işıltı", "⭐": "Sarı Yıldız", "🌟": "Parlayan Yıldız",
    "💫": "Baş Dönmesi Yıldızı", "💥": "Çarpışma / Patlama", "💯": "Yüz Puan / Mükemmel",
    "💢": "Öfke İşareti", "💬": "Konuşma Balonu", "💭": "Düşünce Balonu", "💤": "Uyku Sembolü (Zzz)",
    "⚠️": "Dikkat / Uyarı", "⛔": "Girilmez İşareti", "🚫": "Yasak İşareti",
    "✅": "Yeşil Onay İşareti", "✔️": "Doğru İmi", "❌": "Kırmızı Çarpı (Hata)", "❎": "Kare Çarpı",
    "➕": "Artı İşareti", "➖": "Eksi İşareti", "➗": "Bölme İşareti", "❓": "Kırmızı Soru İşareti",
    "❗": "Kırmızı Ünlem", "‼️": "Çift Ünlem", "🔥": "Ateş / Trend", "💧": "Su Damlası",
    "⚡": "Yüksek Gerilim / Şimşek", "🌈": "Gökkuşağı", "🎉": "Parti Konfetisi", "🎊": "Kutlama Topu",

    # Bayraklar
    "🇹🇷": "Türkiye Bayrağı", "🇦🇿": "Azerbaycan Bayrağı", "🇺🇸": "ABD Bayrağı",
    "🇬🇧": "Birleşik Krallık (İngiltere)", "🇩🇪": "Almanya Bayrağı", "🇫🇷": "Fransa Bayrağı",
    "🇮🇹": "İtalya Bayrağı", "🇪🇸": "İspanya Bayrağı", "🇷🇺": "Rusya Bayrağı",
    "🇯🇵": "Japonya Bayrağı", "🇨🇳": "Çin Bayrağı", "🇰🇷": "Güney Kore Bayrağı",
    "🇧🇷": "Brezilya Bayrağı", "🇨🇦": "Kanada Bayrağı", "🇦🇺": "Avustralya Bayrağı",
    "🇮🇳": "Hindistan Bayrağı", "🇲🇽": "Meksika Bayrağı", "🇸🇦": "Suudi Arabistan Bayrağı",
    "🇵🇦": "Panama Bayrağı", "🇪🇬": "Mısır Bayrağı", "🇮🇶": "Irak Bayrağı",
    "🇮🇷": "İran Bayrağı", "🇸🇾": "Suriye Bayrağı", "🇬🇷": "Yunanistan Bayrağı",
    "🇧🇬": "Bulgaristan Bayrağı", "🇷🇴": "Romanya Bayrağı", "🇷🇸": "Sırbistan Bayrağı",
    "🇦🇹": "Avusturya Bayrağı", "🇨🇭": "İsviçre Bayrağı", "🇳🇱": "Hollanda Bayrağı"
}


def get_emoji_title(emoji_char: str) -> Tuple[str, str, str]:
    """
    Emojinin Türkçe adı, İngilizce Unicode adı ve Unicode kodunu döner.
    """
    clean_char = emoji_char.replace("\ufe0f", "")
    tr_name = TR_EMOJI_NAMES.get(emoji_char) or TR_EMOJI_NAMES.get(clean_char)

    en_parts = []
    codes = []
    for ch in emoji_char:
        try:
            name = unicodedata.name(ch, "").title()
            if name and "Selector" not in name:
                en_parts.append(name)
            codes.append(f"U+{ord(ch):04X}")
        except Exception:
            pass

    en_name = " / ".join(en_parts) if en_parts else "Emoji"
    code_str = " ".join(codes)

    if not tr_name:
        tr_name = en_name

    return tr_name, en_name, code_str


_ACTIVE_WORKERS: set = set()


def _register_worker(worker: QThread) -> QThread:
    """
    QThread nesnesini C++ ve Python çöp toplayıcısına karşı korur.
    İş parçacığı henüz arka planda ağ sorgusu yaparken Python nesnesinin silinmesini engelleyerek
    'QThread: Destroyed while thread is still running' çökmesini kesin olarak önler.
    """
    _ACTIVE_WORKERS.add(worker)
    def _on_finished(w=worker):
        _ACTIVE_WORKERS.discard(w)
    try:
        worker.finished.connect(_on_finished)
    except Exception:
        pass
    return worker


class ImageDownloadWorker(QThread):
    finished = pyqtSignal(bytes, str)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuraPDF/2.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if not data:
                    self.error.emit("Boş yanıt alındı.")
                    return
                img = QImage()
                if not img.loadFromData(data):
                    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
                        self.finished.emit(data, "GIF Animasyonu")
                        return
                    self.error.emit("Geçersiz resim veya GIF formatı.")
                    return
                self.finished.emit(data, f"{img.width()}x{img.height()} px")
        except Exception as e:
            self.error.emit(str(e))


class EmojiHoverButton(QPushButton):
    """Üzerine gelindiğinde emojinin adını ve detayını haber veren buton."""
    hovered = pyqtSignal(str)

    def __init__(self, emoji_char: str, parent=None):
        super().__init__(emoji_char, parent)
        self.emoji_char = emoji_char
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.hovered.emit(self.emoji_char)
        super().enterEvent(event)


TR_MAP = {
    'alkış': 'applause', 'alkis': 'applause', 'tebrik': 'congratulations',
    'komik': 'funny', 'dans': 'dance', 'kedi': 'cat', 'köpek': 'dog', 'kopek': 'dog',
    'harika': 'thumbs up', 'şaşkın': 'shocked', 'saskin': 'shocked',
    'evet': 'yes', 'hayır': 'no', 'hayir': 'no', 'kutlama': 'celebration',
    'gülen': 'laughing', 'gulen': 'laughing', 'ağlayan': 'crying', 'aglayan': 'crying',
    'aşk': 'love', 'ask': 'love', 'kalp': 'heart', 'mutlu': 'happy', 'üzgün': 'sad',
    'uzgun': 'sad', 'kızgın': 'angry', 'kizgin': 'angry', 'korkmuş': 'scared',
    'ateş': 'fire', 'ates': 'fire', 'bayram': 'celebration', 'kahve': 'coffee',
    'günaydın': 'good morning', 'gunaydin': 'good morning', 'iyi geceler': 'good night',
    'selam': 'hello', 'merhaba': 'hello', 'bay bay': 'bye', 'hoşçakal': 'goodbye',
    'hoscakal': 'goodbye', 'tamam': 'ok', 'parti': 'party', 'alkol': 'cheers',
    'şampanya': 'cheers', 'zafer': 'victory', 'şok': 'shocked', 'düşünceli': 'thinking',
    'uyku': 'sleepy', 'uykulu': 'sleepy', 'koş': 'running', 'yemek': 'food',
    'pizza': 'pizza', 'çalışma': 'working', 'calisma': 'working', 'bebek': 'baby'
}

TRENDING_TAGS = [
    "applause", "thumbs up", "laughing", "mind blown", "dancing", "celebration",
    "cat", "cheers", "shocked", "happy", "party", "dog", "yes", "cool",
    "love", "fire", "excited", "wow", "coffee", "victory", "sleepy"
]


# GIPHY API Anahtarı
_GIPHY_API_KEY = "Gc7131jiJuvI7IdN0HZ1D7nh0ow5BU6g"


class GifSearchWorker(QThread):
    """
    GIPHY API üzerinden arama sorgusuna uygun GIF URL'lerini asenkron olarak çeker.
    Türkçe arama terimlerini otomatik olarak optimize eder.
    """
    results_ready = pyqtSignal(str, list)  # query, list_of_urls

    def __init__(self, query: str, limit: int = 30):
        super().__init__()
        self.query = query.strip()
        self.limit = limit
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        if not self.query or self._stopped:
            return

        queries = [self.query]
        q_lower = self.query.lower()
        if q_lower in TR_MAP:
            queries.insert(0, TR_MAP[q_lower])

        found_urls = []
        for q in queries:
            if self._stopped:
                break
            try:
                encoded = urllib.parse.quote(q)
                api_url = (
                    f"https://api.giphy.com/v1/gifs/search?"
                    f"api_key={_GIPHY_API_KEY}"
                    f"&q={encoded}&limit={self.limit}&lang=tr"
                )
                req = urllib.request.Request(
                    api_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuraPDF/2.0"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    for result in data.get("data", []):
                        images = result.get("images", {})
                        # WhatsApp gibi hızlı yükleme için fixed_height_small kullanıyoruz
                        gif_url = images.get("fixed_height_small", {}).get("url", "")
                        if not gif_url:
                            gif_url = images.get("original", {}).get("url", "")
                        if gif_url:
                            found_urls.append(gif_url)
            except Exception:
                pass
            if found_urls:
                break

        seen = set()
        unique_urls = [u for u in found_urls if not (u in seen or seen.add(u))]

        if not self._stopped:
            self.results_ready.emit(self.query, unique_urls)


import concurrent.futures

class GiphyTrendingWorker(QThread):
    """
    GIPHY API üzerinden güncel popüler GIF URL'lerini asenkron olarak çeker.
    Sayfalama (pagination) desteği ile sonsuz kaydırma için offset kullanır.
    """
    results_ready = pyqtSignal(list, int)  # list_of_urls, next_offset

    def __init__(self, limit: int = 50, offset: int = 0):
        super().__init__()
        self.limit = limit
        self.offset = offset
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        if self._stopped:
            return
        try:
            api_url = (
                f"https://api.giphy.com/v1/gifs/trending?"
                f"api_key={_GIPHY_API_KEY}"
                f"&limit={self.limit}&offset={self.offset}"
            )
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuraPDF/2.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                urls = []
                for result in data.get("data", []):
                    images = result.get("images", {})
                    gif_url = images.get("fixed_height_small", {}).get("url", "")
                    if not gif_url:
                        gif_url = images.get("original", {}).get("url", "")
                    if gif_url:
                        urls.append(gif_url)
                
                pagination = data.get("pagination", {})
                next_offset = pagination.get("count", 0) + pagination.get("offset", 0)
                
                if not self._stopped:
                    self.results_ready.emit(urls, next_offset)
        except Exception:
            if not self._stopped:
                self.results_ready.emit([], 0)


class GifThumbnailsWorker(QThread):
    """
    Popüler GIF ve arama sonuçları kartları için arka planda asenkron veri indirir.
    ThreadPoolExecutor ile tamamen eşzamanlı (paralel) indirme yaparak hızı çok artırır.
    """
    thumb_ready = pyqtSignal(int, bytes)

    def __init__(self, items: List[Tuple[int, str]]):
        super().__init__()
        self.items = items  # List of (card_idx, url)
        self._stopped = False

    def stop(self):
        self._stopped = True

    def _fetch_one(self, idx: int, url: str) -> Optional[bytes]:
        if self._stopped or not url:
            return None
        if url in GifThumbnailCard._THUMB_CACHE:
            return GifThumbnailCard._THUMB_CACHE[url]
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AuraPDF/2.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
                if data and not self._stopped:
                    GifThumbnailCard._THUMB_CACHE[url] = data
                    return data
        except Exception:
            pass
        return None

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self._fetch_one, idx, url): idx for idx, url in self.items if not self._stopped}
            for future in concurrent.futures.as_completed(futures):
                if self._stopped:
                    break
                idx = futures[future]
                data = future.result()
                if data and not self._stopped:
                    # Signal'i QThread üzerinden emit ediyoruz (Python ThreadPool içinden değil)
                    # Bu PyQt'de çökmeleri ve instabiliteleri önler
                    self.thumb_ready.emit(idx, data)


class WhatsAppCategoryTab(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, cat_id: str, icon_text: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.cat_id = cat_id
        self.is_active = False
        self.raw_icon = icon_text
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setFixedHeight(34)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_icon)

        self.indicator = QFrame()
        self.indicator.setFixedHeight(3)
        self.indicator.setStyleSheet("background-color: transparent; border-radius: 1px;")
        layout.addWidget(self.indicator)
        
        self.set_active(False)

    def _render_svg(self, svg_str: str, color: str):
        svg_str = svg_str.replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        self.lbl_icon.setPixmap(pixmap)
        self.lbl_icon.setText("")

    def set_active(self, active: bool):
        self.is_active = active
        color = "#ffffff" if active else "#8696a0"
        
        if self.raw_icon.startswith("<svg"):
            self._render_svg(self.raw_icon, color)
        else:
            self.lbl_icon.setText(self.raw_icon)
            self.lbl_icon.setStyleSheet(f"font-size: 18px; color: {color};")
            
        if active:
            self.indicator.setStyleSheet(" border-radius: 1px;")
        else:
            self.indicator.setStyleSheet("background-color: transparent; border-radius: 1px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cat_id)
        super().mousePressEvent(event)


class GifThumbnailCard(QFrame):
    """
    WhatsApp tarzı saf medya kartı:
    - İsim ve kaynak rozeti YOKTUR.
    - QMovie ile canlı hareketli GIF önizlemesi oynatır.
    - Çift tıklandığında doğrudan belgeye eklenir.
    """
    clicked = pyqtSignal(str)        # url
    doubleClicked = pyqtSignal(str)  # url
    _THUMB_CACHE: Dict[str, bytes] = {}

    def __init__(self, item, card_idx: int = 0, parent=None):
        super().__init__(parent)
        self.card_idx = card_idx
        self.item = item
        self.url = item if isinstance(item, str) else item.get("url", "")
        self.is_selected = False
        self._gif_data: Optional[bytes] = None
        self._movie: Optional[QMovie] = None
        self._buf: Optional[QBuffer] = None

        self.setFixedSize(126, 96)  # 3 sütun için optimize edildi (3 * 126 + boşluklar < 400)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # WhatsApp tarzı tam dolgulu görsel önizleme alanı
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(134, 96)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet(" border-radius: 4px;  font-size: 11px;")
        self.lbl_thumb.setText("...")
        layout.addWidget(self.lbl_thumb)

        self._update_style(False)

        if self.url in self._THUMB_CACHE:
            self.set_thumbnail_data(self._THUMB_CACHE[self.url])

    def set_thumbnail_data(self, data: bytes):
        self._gif_data = data
        try:
            self.stop_movie()
            self._ba = QByteArray(data)
            self._buf = QBuffer(self._ba)
            self._buf.open(QBuffer.OpenModeFlag.ReadOnly)
            self._movie = QMovie(self._buf, QByteArray(b"GIF"))
            if self._movie.isValid():
                self._movie.setScaledSize(self.lbl_thumb.size())
                self.lbl_thumb.setMovie(self._movie)
                self._movie.start()
                self.lbl_thumb.setText("")
                return
        except Exception:
            pass

        pix = QPixmap()
        if pix.loadFromData(data):
            scaled = pix.scaled(
                self.lbl_thumb.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = max(0, (scaled.width() - self.lbl_thumb.width()) // 2)
            y = max(0, (scaled.height() - self.lbl_thumb.height()) // 2)
            cropped = scaled.copy(x, y, self.lbl_thumb.width(), self.lbl_thumb.height())
            self.lbl_thumb.setPixmap(cropped)
            self.lbl_thumb.setText("")
        else:
            self.lbl_thumb.setText("GIF")

    def stop_movie(self):
        if self._movie:
            try:
                self._movie.stop()
                self.lbl_thumb.setMovie(None)
            except Exception:
                pass
            self._movie = None
        if self._buf:
            try:
                if self._buf.isOpen():
                    self._buf.close()
            except Exception:
                pass
            self._buf = None
        self._ba = None

    def deleteLater(self):
        self.stop_movie()
        super().deleteLater()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style(False)

    def _update_style(self, hovered: bool):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(56, 189, 248, 0.2);
                    border: 2px solid #38bdf8;
                    border-radius: 4px;
                }
            """)
        elif hovered:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1.5px solid #00a884;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                }
            """)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.url)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self.url)
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        # Kaydırma olayını üst QScrollArea'ya ilet — scroll ile daha fazla GIF yüklenir
        parent = self.parent()
        while parent is not None:
            from PyQt6.QtWidgets import QScrollArea
            if isinstance(parent, QScrollArea):
                parent.verticalScrollBar().setValue(
                    parent.verticalScrollBar().value() - int(event.angleDelta().y() / 8)
                )
                event.accept()
                return
            parent = parent.parent()
        super().wheelEvent(event)


class EmojiGifPickerDialog(QDialog):
    """
    WhatsApp Tarzı GIF ve Emoji Seçici Penceresi:
    - Üst Kategori İkonları (Yeşil alt çizgi aktif göstergeli)
    - Yeşil Çerçeveli WhatsApp Tarzı Arama Çubuğu
    - 3 Sütunlu Canlı Hareketli GIF Izgarası (Sonsuz Kaydırma & Çift Tıklamayla Ekleme)
    - Kategori Filtreli Emoji Izgarası (Tek Tıklamayla Belgeye Ekleme)
    - Alt Kısımda WhatsApp Mod Değiştirici Hap: [ 😄 | GIF | 🏷️ ]
    """
    POPULAR_GIFS = [
        {"title": "Alkış ve Tebrikler", "source": "GIPHY", "url": "https://media.giphy.com/media/ytTYwIlbD1FBu/200w.gif"},
        {"title": "Başparmak / Harika", "source": "GIPHY", "url": "https://media.giphy.com/media/111ebonMs90YLu/200w.gif"},
        {"title": "Kadeh / Kutlama", "source": "GIPHY", "url": "https://media.giphy.com/media/g9582DNuQppxC/200w.gif"},
        {"title": "Aklım Uçtu (Mind Blown)", "source": "GIPHY", "url": "https://media.giphy.com/media/26ufdipQqU2lhNA4g/200w.gif"},
        {"title": "Evet / Kesinlikle", "source": "GIPHY", "url": "https://media.giphy.com/media/nXxOjZrbnbRxS/200w.gif"},
        {"title": "Şaşkınlık (Wow)", "source": "GIPHY", "url": "https://media.giphy.com/media/5VKbvrjxpVJCM/200w.gif"},
        {"title": "Parti Dansı", "source": "GIPHY", "url": "https://media.giphy.com/media/blSTtZehjAZ8I/200w.gif"},
        {"title": "Çalışan Kedi", "source": "GIPHY", "url": "https://media.giphy.com/media/JIX9t2j0ZTN9S/200w.gif"},
        {"title": "Kusursuz / Bravo", "source": "GIPHY", "url": "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/200w.gif"},
        {"title": "Kahkaha / Gülüş", "source": "GIPHY", "url": "https://media.giphy.com/media/10JhviFuU2gWD6/200w.gif"},
        {"title": "Büyük Alkış", "source": "TENOR", "url": "https://media.tenor.com/d9PZBo-BAGsAAAAM/applause-applaud.gif"},
        {"title": "Onay / Beğeni (Like)", "source": "TENOR", "url": "https://media.tenor.com/YXJb-GI93WYAAAAM/like.gif"},
        {"title": "Kutlama / Neşe", "source": "TENOR", "url": "https://media.tenor.com/0Sh7u1lRsyEAAAAM/wedding-crasher-hro.gif"},
        {"title": "Şaşıran Kedi", "source": "TENOR", "url": "https://media.tenor.com/qcMImeiWbrwAAAAM/shocked-shocked-cat.gif"},
        {"title": "Neşeli Dans", "source": "TENOR", "url": "https://media.tenor.com/x8v1oNUOmg4AAAAd/rickroll-roll.gif"},
    ]

    POPULAR_EMOJIS = [
        "❤️", "🔥", "😂", "🥰", "👍", "✨", "😊", "🎉", "👏", "😍", "🙏", "💯", "🥺", "🤣", "✔️",
        "😘", "💀", "😭", "🚀", "💪", "😎", "🌟", "🤩", "💖", "👌", "🙌", "🎯", "💡", "🥳", "⚡",
        "💙", "😁", "😴", "🤔", "👀", "⭐", "🎶", "☕", "🍕", "🍔", "🍻", "🌈", "✅", "❌", "👑",
        "💎", "🎂", "🎊", "🍀", "🌹", "🌞", "⚽", "🏖️", "✈️", "🏆", "🎁", "🎈", "🌸", "🍫", "🍩",
        "🤝", "🤗", "🤤", "🤯", "😇", "🤫", "🤑", "😜", "🤭", "🤠", "😻", "🙈", "🙉", "🙊", "💋",
        "💔", "💕", "💘", "💌", "💤", "💬", "💭", "💥", "💫", "🔔", "📢", "💰", "💵", "🔑", "🛡️",
        "🚗", "🚲", "📱", "💻", "📸", "🎧", "🎨", "🎤", "🍿", "🥑", "🍓", "🍉", "🍇", "🍦", "🥂",
        "☀️", "🌙", "🌍", "🌺", "🌻", "🐶", "🐱", "🦁", "🐻", "🐼", "🐨", "🦊", "🐯", "🐵"
    ]

    EMOJI_CATEGORIES = {
        "Yüzler": [
            "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", "😉", "😊", "😇", "🥰", "😍", "🤩",
            "😘", "😗", "😚", "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🤐", "🤨", "😐",
            "😑", "😶", "😏", "😒", "🙄", "😬", "🤥", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢",
            "🤮", "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "😎", "🤓", "🧐", "😕", "😟", "🙁", "😮",
            "😲", "😳", "🥺", "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖", "😣", "😞", "😓", "😩",
            "😫", "🥱", "😤", "😡", "😠", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👹", "👺", "👻", "👽"
        ],
        "İnsanlar": [
            "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆",
            "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💅",
            "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "👀", "👁️", "👅", "👄", "🧑", "👧",
            "👦", "👨", "👩", "🧓", "👵", "👴", "👶", "👱", "👨‍🦰", "👩‍🦰", "👨‍🦱", "👩‍🦱", "👨‍🦲", "👩‍🦲", "🧔", "🦸",
            "🦹", "🧙", "🧚", "🧛", "🧜", "🧝", "🧞", "🧟", "🚶", "🏃", "💃", "🕺", "🧖", "🧗"
        ],
        "Doğa": [
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔",
            "🐧", "🐦", "🐤", "🦆", "🦅", "🦉", "🐺", "🐗", "🐴", "🦄", "🐝", "🐛", "🦋", "🐌", "🐞", "🐜",
            "🐢", "🐍", "🐙", "🦑", "🦐", "🦞", "🦀", "🐬", "🐳", "🦈", "🐊", "🐅", "🐘", "🦛", "🦒", "🦓",
            "🦍", "🦧", "🦥", "🦦", "🦨", "🦘", "🦡", "🌲", "🌳", "🌴", "🌵", "🌷", "🌸", "🌹", "🌺", "🌻",
            "🌼", "🌿", "🍀", "🍁", "🍂", "🍃", "☀️", "🌙", "⭐", "🌟", "⚡", "🔥", "💧", "🌊", "🌈", "❄️"
        ],
        "Yiyecek": [
            "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🍍", "🥥", "🥝",
            "🍅", "🥑", "🥦", "🥒", "🌶️", "🌽", "🥕", "🥔", "🥐", "🍞", "🥖", "🥨", "🧀", "🥚", "🍳", "🥓",
            "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🌮", "🌯", "🥗", "🍝", "🍜", "🍣", "🍱", "🥟",
            "🍦", "🍧", "🍨", "🍩", "🍪", "🎂", "🍰", "🧁", "🍫", "🍬", "🍭", "🍿", "☕", "🍵", "🧃", "🥤",
            "🍺", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹", "🧉", "🍾", "🧊"
        ],
        "Aktiviteler": [
            "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🥏", "🎱", "🏓", "🏸", "🏒", "🏏", "🥊", "🥋", "🎯",
            "⛳", "🎣", "🎿", "🏂", "🏋️", "🤼", "🤸", "⛹️", "🏄", "🏊", "🚴", "🧗", "🏇", "🏆", "🥇", "🥈",
            "🥉", "🏅", "🎖️", "🎫", "🎟️", "🎪", "🎨", "🎬", "🎤", "🎧", "🎼", "🎹", "🥁", "🎸", "🎲", "🧩",
            "🎮", "🕹️", "🎰", "🎳", "🛹", "🛴", "🏹", "🪁"
        ],
        "Semboller": [
            "💡", "🔦", "🧱", "🔑", "🗝️", "🔨", "🛠️", "⚙️", "💣", "🔫", "🛡️", "🔮", "🧪", "🧬", "⏰", "⏱️",
            "⌛", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓", "💗",
            "💖", "💘", "💝", "✨", "⭐", "🌟", "💫", "💥", "💯", "💢", "💬", "💭", "💤", "⚠️", "⛔", "🚫",
            "✅", "✔️", "❌", "❎", "➕", "➖", "➗", "❓", "❗", "‼️", "🔥", "💧", "⚡", "🌈", "🎉", "🎊",
            "🔔", "🔕", "📢", "📣", "💰", "💵", "💳", "💎", "🔒", "🔓", "🔍", "🔎", "📌", "📍", "📎", "🔗"
        ],
        "Bayraklar": [
            "🇹🇷", "🇦🇿", "🇺🇸", "🇬🇧", "🇩🇪", "🇫🇷", "🇮🇹", "🇪🇸", "🇷🇺", "🇯🇵", "🇨🇳", "🇰🇷", "🇧🇷", "🇨🇦", "🇦🇺", "🇮🇳",
            "🇲🇽", "🇸🇦", "🇵🇦", "🇪🇬", "🇮🇶", "🇮🇷", "🇸🇾", "🇬🇷", "🇧🇬", "🇷🇴", "🇷🇸", "🇦🇹", "🇨🇭", "🇳🇱", "🇵🇹", "🇸🇪",
            "🇳🇴", "🇩🇰", "🇫🇮", "🇵🇱", "🇺🇦", "🇬🇪", "🇰🇿", "🇺🇿", "🇹🇲", "🇰🇬", "🇹🇯", "🇦🇷", "🇨🇱", "🇨🇴", "🇿🇦"
        ]
    }

    SVG_TRENDING = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline><polyline points="16 7 22 7 22 13"></polyline></svg>'
    SVG_HAPPY = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>'
    SVG_SAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M16 16s-1.5-2-4-2-4 2-4 2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>'
    SVG_LOVE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>'
    SVG_THUMBSUP = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>'
    SVG_SPORTS = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><line x1="12" y1="2" x2="12" y2="22"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
    SVG_TV = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="15" rx="2" ry="2"></rect><polyline points="17 2 12 7 7 2"></polyline></svg>'

    GIF_CATEGORIES = [
        ("trending", SVG_TRENDING, "TRENDING"),
        ("haha", SVG_HAPPY, "HAHA"),
        ("sad", SVG_SAD, "SAD"),
        ("love", SVG_LOVE, "LOVE"),
        ("reaction", SVG_THUMBSUP, "REACTION"),
        ("sports", SVG_SPORTS, "SPORTS"),
        ("tv", SVG_TV, "TV")
    ]

    EMOJI_CATEGORIES_LIST = [
        ("populer", "🔥", "Popüler"),
        ("Yüzler", "😀", "Yüzler"),
        ("İnsanlar", "🧑", "İnsanlar"),
        ("Doğa", "🐶", "Doğa"),
        ("Yiyecek", "🍔", "Yiyecek"),
        ("Aktiviteler", "⚽", "Aktiviteler"),
        ("Semboller", "💡", "Semboller"),
        ("Bayraklar", "🚩", "Bayraklar")
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GIF & Emoji")
        self.setFixedSize(450, 560)
        self.setStyleSheet(get_dialog_theme_stylesheet(self) + """
            QDialog {
                
            }
            QScrollBar:vertical {
                background: #111b21;
                width: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #374248;
                border-radius: 2.5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
        """)

        self.selected_emoji: Optional[str] = None
        self.selected_gif_bytes: Optional[bytes] = None
        self._current_mode: str = "gif"
        self._active_cat_id: str = "trending"

        self._current_emoji_list: List[str] = []
        self._rendered_emoji_count: int = 0
        self._is_loading_emojis: bool = False
        self._emoji_batch_size: int = 56

        self._search_worker: Optional[GifSearchWorker] = None
        self._trending_worker: Optional[GiphyTrendingWorker] = None
        self._thumb_workers: List[GifThumbnailsWorker] = []
        self.gif_cards: List[GifThumbnailCard] = []
        self._all_gif_urls: List[str] = []
        self._rendered_gif_count: int = 0
        self._is_loading_batch: bool = False
        self._trending_next_offset: int = 0  # GIPHY API sayfalama imleci
        self._is_fetching_trending: bool = False
        self._current_search_query: str = ""
        self._pending_double_click_url: Optional[str] = None

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_triggered)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(8)

        # 1. Üst Kategori Çubuğu (Aktif kategorinin altında yeşil çizgi)
        self.top_cat_bar = QHBoxLayout()
        self.top_cat_bar.setSpacing(2)
        self.top_cat_bar.setContentsMargins(0, 0, 0, 0)
        self.top_cat_widgets: List[WhatsAppCategoryTab] = []
        layout.addLayout(self.top_cat_bar)

        # 2. Arama Çubuğu (Yeşil Çerçeveli WhatsApp Pill)
        self.search_box = QFrame()
        self.search_box.setStyleSheet("""
            QFrame {
                
                border: 1.5px solid #00a884;
                border-radius: 17px;
            }
        """)
        sb_layout = QHBoxLayout(self.search_box)
        sb_layout.setContentsMargins(14, 4, 12, 4)
        sb_layout.setSpacing(6)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search GIFs via GIPHY")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                
                font-size: 13px;
                padding-left: 2px;
            }
        """)
        self.txt_search.returnPressed.connect(self._on_search_triggered)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        sb_layout.addWidget(self.txt_search, 1)
        layout.addWidget(self.search_box)

        # 3. Stacked Widget: Sayfa 0 = GIF (3 Sütunlu), Sayfa 1 = Emoji
        self.stacked = QStackedWidget()

        # Sayfa 0: 3 Sütunlu Canlı GIF Izgarası
        self.gif_scroll = QScrollArea()
        self.gif_scroll.setWidgetResizable(True)
        self.gif_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.gif_scroll.setStyleSheet("background: transparent; border: none;")
        self.gif_scroll.verticalScrollBar().valueChanged.connect(self._on_gif_scroll)

        self.gif_grid_widget = QWidget()
        self.gif_grid_widget.setStyleSheet("background: transparent;")
        self.gif_cards_grid = QGridLayout(self.gif_grid_widget)
        self.gif_cards_grid.setSpacing(6)
        self.gif_cards_grid.setContentsMargins(0, 4, 0, 80)

        self.gif_scroll.setWidget(self.gif_grid_widget)
        self.stacked.addWidget(self.gif_scroll)

        # Sayfa 1: Emoji Izgarası (Scroll ile Dinamik Yükleme)
        self.emoji_scroll = QScrollArea()
        self.emoji_scroll.setWidgetResizable(True)
        self.emoji_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.emoji_scroll.setStyleSheet("background: transparent; border: none;")
        self.emoji_scroll.verticalScrollBar().valueChanged.connect(self._on_emoji_scroll)

        self.emoji_grid_widget = QWidget()
        self.emoji_grid_widget.setStyleSheet("background: transparent;")
        self.emoji_grid = QGridLayout(self.emoji_grid_widget)
        self.emoji_grid.setSpacing(4)
        self.emoji_grid.setContentsMargins(2, 4, 2, 4)
        self._populate_all_emojis()
        self.emoji_scroll.setWidget(self.emoji_grid_widget)
        self.stacked.addWidget(self.emoji_scroll)

        layout.addWidget(self.stacked, 1)

        # 4. Alt WhatsApp Mod Değiştirici: [ 😄 | GIF ] (Stickers kaldırıldı)
        bottom_bar = QHBoxLayout()
        bottom_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pill = QFrame()
        pill.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 17px;
            }
        """)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(6, 3, 6, 3)
        pill_layout.setSpacing(4)

        self.btn_mode_emoji = QPushButton("😄")
        self.btn_mode_gif = QPushButton("GIF")

        for b in [self.btn_mode_emoji, self.btn_mode_gif]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(28)

        self.btn_mode_emoji.clicked.connect(lambda: self.set_mode("emoji"))
        self.btn_mode_gif.clicked.connect(lambda: self.set_mode("gif"))

        pill_layout.addWidget(self.btn_mode_emoji)
        pill_layout.addWidget(self.btn_mode_gif)

        bottom_bar.addWidget(pill)
        layout.addLayout(bottom_bar)

        # Başlangıç modunu ve ilk GIF paketini yükle
        self.set_mode("gif")
        self._populate_initial_gifs()

    def set_mode(self, mode: str):
        self._current_mode = mode
        self._update_pill_styles()
        self._rebuild_top_categories()

        if mode == "emoji":
            self.stacked.setCurrentIndex(1)
            self.txt_search.setPlaceholderText("Search emojis...")
            self.txt_search.clear()
            self._filter_emojis_by_cat("populer")
        else: # gif
            self.stacked.setCurrentIndex(0)
            self.txt_search.setPlaceholderText("Search GIFs via GIPHY")

    def _update_pill_styles(self):
        normal_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 14px;
                border-radius: 14px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.08);
            }
        """
        active_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 14px;
                border-radius: 14px;
            }
        """
        self.btn_mode_emoji.setStyleSheet(active_style if self._current_mode == "emoji" else normal_style)
        self.btn_mode_gif.setStyleSheet(active_style if self._current_mode == "gif" else normal_style)

    def _rebuild_top_categories(self):
        while self.top_cat_bar.count():
            it = self.top_cat_bar.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.top_cat_widgets.clear()

        cats = self.EMOJI_CATEGORIES_LIST if self._current_mode == "emoji" else self.GIF_CATEGORIES
        for idx, (cid, icon_text, tt) in enumerate(cats):
            item = WhatsAppCategoryTab(cid, icon_text, tt)
            item.clicked.connect(self._on_top_category_clicked)
            self.top_cat_bar.addWidget(item)
            self.top_cat_widgets.append(item)
            if idx == 0:
                item.set_active(True)
                self._active_cat_id = cid

    def _on_top_category_clicked(self, cat_id: str):
        self._active_cat_id = cat_id
        for w in self.top_cat_widgets:
            w.set_active(w.cat_id == cat_id)

        if self._current_mode == "emoji":
            self._filter_emojis_by_cat(cat_id)
        else:
            tag_map = {
                "trending": "",
                "haha": "haha",
                "sad": "sad",
                "love": "love",
                "reaction": "reaction",
                "sports": "sports",
                "tv": "tv"
            }
            tag = tag_map.get(cat_id, cat_id)
            if tag:
                self.txt_search.setText(tag)
                self._start_gif_search(tag)
            else:
                self.txt_search.clear()
                self._reset_to_popular()

    def _on_emoji_scroll(self, val: int):
        if self._current_mode != "emoji":
            return
        sb = self.emoji_scroll.verticalScrollBar()
        if sb.maximum() > 0 and val >= sb.maximum() - 100:
            self._load_more_emojis()

    def _display_emojis(self, emoji_list: List[str]):
        while self.emoji_grid.count():
            it = self.emoji_grid.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._current_emoji_list = emoji_list
        self._rendered_emoji_count = 0
        self.emoji_scroll.verticalScrollBar().setValue(0)
        self._load_more_emojis()

    def _load_more_emojis(self):
        if self._is_loading_emojis or self._rendered_emoji_count >= len(self._current_emoji_list):
            return
        self._is_loading_emojis = True
        cols = 7
        start_idx = self._rendered_emoji_count
        end_idx = min(start_idx + self._emoji_batch_size, len(self._current_emoji_list))
        for i in range(start_idx, end_idx):
            em = self._current_emoji_list[i]
            btn = QPushButton(em)
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-size: 22px;
                    border-radius: 8px;
                    padding: 0px !important;
                    margin: 0px !important;
                }
                QPushButton:hover {
                    
                }
            """)
            btn.clicked.connect(lambda ch, e=em: self._select_emoji(e))
            self.emoji_grid.addWidget(btn, i // cols, i % cols)
        self._rendered_emoji_count = end_idx
        self._is_loading_emojis = False

    def _filter_emojis_by_cat(self, cat_name: str):
        if cat_name == "populer":
            seen = set()
            emojis = []
            for em in self.POPULAR_EMOJIS:
                if em not in seen:
                    seen.add(em)
                    emojis.append(em)
            for cat_emojis in self.EMOJI_CATEGORIES.values():
                for em in cat_emojis:
                    if em not in seen:
                        seen.add(em)
                        emojis.append(em)
        else:
            emojis = self.EMOJI_CATEGORIES.get(cat_name, [])
        self._display_emojis(emojis)

    def _populate_all_emojis(self):
        self._filter_emojis_by_cat("populer")

    def _select_emoji(self, em: str):
        self.selected_emoji = em
        self.selected_gif_bytes = None
        self.accept()

    def _on_search_triggered(self):
        q = self.txt_search.text().strip()
        if self._current_mode == "emoji":
            self._search_emojis(q)
        else:
            if q:
                self._start_gif_search(q)
            else:
                self._reset_to_popular()

    def _on_search_text_changed(self, text: str):
        if self._current_mode == "emoji":
            self._search_emojis(text.strip())
        else:
            self._search_timer.start(500)

    def _search_emojis(self, q: str):
        q = q.lower().strip()
        seen = set()
        all_em = []
        for em in self.POPULAR_EMOJIS:
            if em not in seen:
                seen.add(em)
                all_em.append(em)
        for cat_emojis in self.EMOJI_CATEGORIES.values():
            for em in cat_emojis:
                if em not in seen:
                    seen.add(em)
                    all_em.append(em)

        if q:
            filtered = [em for em in all_em if q in em]
            if not filtered:
                filtered = all_em
        else:
            filtered = all_em
        self._display_emojis(filtered)

    def _populate_initial_gifs(self):
        """GIPHY API üzerinden güncel popüler GIF'leri canlı olarak çeker."""
        self._all_gif_urls = []
        self._rendered_gif_count = 0
        self._trending_next_offset = 0
        self._is_fetching_trending = False
        self._fetch_more_trending_urls()

    def _fetch_more_trending_urls(self):
        """GIPHY trending API'sinden bir sonraki sayfayı çeker."""
        if self._is_fetching_trending:
            return
        self._is_fetching_trending = True
        worker = GiphyTrendingWorker(limit=50, offset=self._trending_next_offset)
        _register_worker(worker)
        worker.results_ready.connect(self._on_trending_urls_fetched)
        worker.start()
        self._trending_worker = worker
        self._thumb_workers.append(worker)

    def _on_trending_urls_fetched(self, urls: list, next_offset: int):
        """GIPHY API'den dönen trending GIF URL'lerini listeye ekler ve kartları oluşturur."""
        self._is_fetching_trending = False
        self._trending_next_offset = next_offset
        for u in urls:
            if u not in self._all_gif_urls:
                self._all_gif_urls.append(u)
        self._load_next_gif_batch()

    def _on_gif_scroll(self, val: int):
        max_val = self.gif_scroll.verticalScrollBar().maximum()
        # 300px eşiğiyle önceden yükle; max_val==0 yani henüz render edilmemiş ise de tetikle
        if (max_val == 0 or val >= max_val - 300) and not self._is_loading_batch:
            self._load_next_gif_batch()
            # Tüm URL'ler tükendiyse ve trending modundaysak API'den sonraki sayfayı getir
            if self._rendered_gif_count >= len(self._all_gif_urls) and not self._current_search_query:
                self._fetch_more_trending_urls()

    def _load_next_gif_batch(self):
        if self._is_loading_batch:
            return

        BATCH_SIZE = 12
        start_idx = self._rendered_gif_count
        end_idx = min(start_idx + BATCH_SIZE, len(self._all_gif_urls))

        if start_idx >= end_idx:
            if not self._current_search_query:
                self._fetch_more_trending_urls()
            return

        self._is_loading_batch = True
        new_urls = self._all_gif_urls[start_idx:end_idx]
        download_batch = []
        cols_count = 3  # WhatsApp tarzı tam 3 sütun

        for i, url in enumerate(new_urls):
            card_id = start_idx + i
            card = GifThumbnailCard(url, card_idx=card_id)
            card.clicked.connect(self._on_gif_card_clicked)
            card.doubleClicked.connect(self._on_gif_card_double_clicked)

            row = card_id // cols_count
            col = card_id % cols_count
            self.gif_cards_grid.addWidget(card, row, col)
            self.gif_cards.append(card)
            download_batch.append((card_id, url))

        self._rendered_gif_count = end_idx

        worker = GifThumbnailsWorker(download_batch)
        _register_worker(worker)
        worker.thumb_ready.connect(self._on_card_thumb_ready)
        worker.finished.connect(self._on_batch_finished)
        worker.start()
        self._thumb_workers.append(worker)

    def _on_batch_finished(self):
        self._is_loading_batch = False
        
        # Ekran dolana kadar yüklemeye devam et, böylece kullanıcının kaydırmasına gerek kalmaz
        val = self.gif_scroll.verticalScrollBar().value()
        max_val = self.gif_scroll.verticalScrollBar().maximum()
        if max_val == 0 or val >= max_val - 300:
            if self._rendered_gif_count < len(self._all_gif_urls):
                QTimer.singleShot(50, self._load_next_gif_batch)
            elif not self._current_search_query:
                QTimer.singleShot(50, self._fetch_more_trending_urls)

    def _on_card_thumb_ready(self, card_idx: int, data: bytes):
        if 0 <= card_idx < len(self.gif_cards):
            self.gif_cards[card_idx].set_thumbnail_data(data)
            card = self.gif_cards[card_idx]
            if self._pending_double_click_url == card.url:
                self._pending_double_click_url = None
                self.selected_gif_bytes = data
                self.selected_emoji = None
                self.accept()

    def _start_gif_search(self, query: Optional[str] = None):
        q = (query or self.txt_search.text()).strip()
        if not q:
            self._reset_to_popular()
            return

        if q.startswith("http://") or q.startswith("https://"):
            self._clear_gif_grid()
            self._all_gif_urls = [q]
            self._rendered_gif_count = 0
            self._load_next_gif_batch()
            return

        self._current_search_query = q
        self._clear_gif_grid()

        if self._search_worker:
            try:
                self._search_worker.stop()
                self._search_worker.results_ready.disconnect()
            except Exception:
                pass
            self._search_worker = None

        self._search_worker = GifSearchWorker(q)
        _register_worker(self._search_worker)
        self._search_worker.results_ready.connect(self._on_search_results_ready)
        self._search_worker.start()

    def _on_search_results_ready(self, query: str, urls: list):
        if not urls:
            return
        self._clear_gif_grid()
        self._all_gif_urls = urls
        self._rendered_gif_count = 0
        self._load_next_gif_batch()

    def _reset_to_popular(self):
        self._current_search_query = ""
        self._clear_gif_grid()
        self._trending_next_offset = 0
        self._is_fetching_trending = False
        self._populate_initial_gifs()

    def _stop_all_workers(self):
        if self._search_worker:
            try:
                self._search_worker.stop()
                self._search_worker.results_ready.disconnect()
            except Exception:
                pass
            self._search_worker = None

        if self._trending_worker:
            try:
                self._trending_worker.stop()
                self._trending_worker.results_ready.disconnect()
            except Exception:
                pass
            self._trending_worker = None

        for worker in list(self._thumb_workers):
            try:
                worker.stop()
                if hasattr(worker, 'thumb_ready'):
                    worker.thumb_ready.disconnect()
            except Exception:
                pass
        self._thumb_workers.clear()
        self._is_loading_batch = False
        self._is_fetching_trending = False

    def _clear_gif_grid(self):
        self._stop_all_workers()

        for card in self.gif_cards:
            try:
                card.stop_movie()
            except Exception:
                pass
        self.gif_cards.clear()

        while self.gif_cards_grid.count():
            item = self.gif_cards_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._rendered_gif_count = 0

    def _on_gif_card_clicked(self, url: str):
        for card in self.gif_cards:
            card.set_selected(card.url == url)
        if url in GifThumbnailCard._THUMB_CACHE:
            self.selected_gif_bytes = GifThumbnailCard._THUMB_CACHE[url]

    def _on_gif_card_double_clicked(self, url: str):
        for card in self.gif_cards:
            card.set_selected(card.url == url)

        data = GifThumbnailCard._THUMB_CACHE.get(url)
        if not data:
            for card in self.gif_cards:
                if card.url == url and card._gif_data:
                    data = card._gif_data
                    break

        if data:
            self.selected_gif_bytes = data
            self.selected_emoji = None
            self.accept()
        else:
            self._pending_double_click_url = url

    def _stop_and_cleanup(self):
        self._stop_all_workers()
        for card in self.gif_cards:
            try:
                card.stop_movie()
            except Exception:
                pass
        self.gif_cards.clear()

    def accept(self):
        self._stop_and_cleanup()
        super().accept()

    def reject(self):
        self._stop_and_cleanup()
        super().reject()

    def closeEvent(self, event):
        self._stop_and_cleanup()
        super().closeEvent(event)


class ImageInsertDialog(QDialog):
    """
    Tek bir pencere üzerinden:
    1. Bilgisayardan dosya seçimi
    2. Web sitesi adresinden (URL) indirme
    """
    def __init__(self, parent=None, default_tab=0):
        super().__init__(parent)
        self.setWindowTitle("Görsel Ekle")
        self.setFixedSize(480, 440)
        self.setStyleSheet(get_dialog_theme_stylesheet(self))

        self.image_bytes: Optional[bytes] = None
        self.image_pixmap: Optional[QPixmap] = None
        self._worker: Optional[ImageDownloadWorker] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; background-color: rgba(255, 255, 255, 0.02); }
            QTabBar::tab { background: rgba(255, 255, 255, 0.04); color: #94a3b8; padding: 8px 18px; border-top-left-radius: 4px; border-top-right-radius: 4px; font-size: 12px; font-weight: bold; }
            QTabBar::tab:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
            QTabBar::tab:selected { background: rgba(255, 255, 255, 0.1); color: #38bdf8; border-bottom: 2px solid #38bdf8; }
        """)

        # Sekme 1: Bilgisayardan
        tab_local = QWidget()
        tl_layout = QVBoxLayout(tab_local)
        tl_layout.setSpacing(10)
        tl_layout.setContentsMargins(14, 14, 14, 14)

        btn_browse = QPushButton("Bilgisayardan Dosya Seç...")
        btn_browse.setStyleSheet("""
            QPushButton {
                  font-weight: bold;
                padding: 10px; border-radius: 6px; border: none;
            }
            QPushButton:hover {  }
        """)
        btn_browse.clicked.connect(self._browse_local)
        tl_layout.addWidget(btn_browse)

        self.lbl_local_info = QLabel("Desteklenen formatlar: PNG, JPG, JPEG, WEBP, BMP, SVG, GIF")
        self.lbl_local_info.setStyleSheet(" font-size: 11px;")
        tl_layout.addWidget(self.lbl_local_info)

        self.lbl_local_preview = QLabel("Önizleme yok")
        self.lbl_local_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_local_preview.setStyleSheet(" border-radius: 6px; ")
        self.lbl_local_preview.setFixedHeight(160)
        tl_layout.addWidget(self.lbl_local_preview)

        tl_layout.addStretch()
        self.tabs.addTab(tab_local, "Bilgisayardan")

        # Sekme 2: Web Adresi (URL)
        tab_url = QWidget()
        tu_layout = QVBoxLayout(tab_url)
        tu_layout.setSpacing(10)
        tu_layout.setContentsMargins(14, 14, 14, 14)

        lbl_url_desc = QLabel("Web Sitesi veya Görsel Adresi (URL):")
        lbl_url_desc.setStyleSheet(" font-size: 12px; font-weight: bold;")
        tu_layout.addWidget(lbl_url_desc)

        url_input_box = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://ornek.com/resim.jpg")
        self.txt_url.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 8px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        btn_fetch = QPushButton("İndir ve Önizle")
        btn_fetch.setStyleSheet("""
            QPushButton {
                  font-weight: bold;
                padding: 8px 14px; border-radius: 6px; border: none;
            }
            QPushButton:hover {  }
        """)
        btn_fetch.clicked.connect(self._fetch_url)
        url_input_box.addWidget(self.txt_url)
        url_input_box.addWidget(btn_fetch)
        tu_layout.addLayout(url_input_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.hide()
        tu_layout.addWidget(self.progress_bar)

        self.lbl_url_preview = QLabel("Önizleme yok")
        self.lbl_url_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_url_preview.setStyleSheet(" border-radius: 6px; ")
        self.lbl_url_preview.setFixedHeight(150)
        tu_layout.addWidget(self.lbl_url_preview)

        self.lbl_url_status = QLabel("")
        self.lbl_url_status.setStyleSheet(" font-size: 11px;")
        tu_layout.addWidget(self.lbl_url_status)

        tu_layout.addStretch()
        self.tabs.addTab(tab_url, "Web Adresi (URL)")

        self.tabs.setCurrentIndex(default_tab)
        layout.addWidget(self.tabs)

        # En-boy oranını koru seçeneği
        self.chk_keep_aspect = QCheckBox("En boy oranını koru")
        self.chk_keep_aspect.setChecked(True)
        self.chk_keep_aspect.setStyleSheet(" font-size: 12px; margin-top: 4px; margin-bottom: 4px;")
        layout.addWidget(self.chk_keep_aspect)

        # Alt Butonlar
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("padding: 8px 16px;   border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)

        self.btn_insert = QPushButton("Belgeye Ekle")
        self.btn_insert.setEnabled(False)
        self.btn_insert.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;  
                font-weight: bold; border-radius: 6px;
            }
            QPushButton:disabled {   }
        """)
        self.btn_insert.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_insert)
        layout.addLayout(btn_box)

    @property
    def keep_aspect_ratio(self) -> bool:
        return self.chk_keep_aspect.isChecked()

    def _browse_local(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Görsel Seç", "",
            "Görseller (*.png *.jpg *.jpeg *.webp *.bmp *.svg *.gif)"
        )
        if fpath and os.path.exists(fpath):
            with open(fpath, "rb") as f:
                self.image_bytes = f.read()

            img = QImage()
            img.loadFromData(self.image_bytes)
            if not img.isNull():
                pix = QPixmap.fromImage(img)
                self.image_pixmap = pix
                scaled = pix.scaled(self.lbl_local_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.lbl_local_preview.setPixmap(scaled)
                self.lbl_local_info.setText(f"Seçilen dosya: {os.path.basename(fpath)} ({img.width()}x{img.height()} px)")
                self.btn_insert.setEnabled(True)

    def _fetch_url(self):
        url = self.txt_url.text().strip()
        if not url:
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        self.progress_bar.show()
        self.lbl_url_status.setText("Görsel indiriliyor...")
        self.lbl_url_status.setStyleSheet("")

        self._worker = ImageDownloadWorker(url)
        _register_worker(self._worker)
        self._worker.finished.connect(self._on_fetch_success)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_success(self, data: bytes, info: str):
        self.progress_bar.hide()
        self.image_bytes = data
        img = QImage()
        img.loadFromData(data)
        pix = QPixmap.fromImage(img)
        self.image_pixmap = pix
        scaled = pix.scaled(self.lbl_url_preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_url_preview.setPixmap(scaled)
        self.lbl_url_status.setText(f"Görsel başarıyla indirildi: {info}")
        self.lbl_url_status.setStyleSheet("")
        self.btn_insert.setEnabled(True)

    def _on_fetch_error(self, err_msg: str):
        self.progress_bar.hide()
        self.lbl_url_status.setText(f"İndirilemedi: {err_msg}")
        self.lbl_url_status.setStyleSheet("")

    def _cleanup_worker(self):
        if self._worker:
            try:
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
            except Exception:
                pass
            self._worker = None

    def reject(self):
        self._cleanup_worker()
        super().reject()

    def closeEvent(self, event):
        self._cleanup_worker()
        super().closeEvent(event)


class AudioWaveformVisualizer(QWidget):
    """
    Canlı ses kaydı veya oynatmayı gösteren animasyonlu dalga / ekolayzır önizleme bileşeni.
    Kayıt anında hareketli neon dalga çubukları ve yanıp sönen canlı kayıt rozeti sunar.
    """
    MODE_IDLE = 0
    MODE_RECORDING = 1
    MODE_PLAYING = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(76)
        self.mode = self.MODE_IDLE
        self.bars_count = 24
        self.bar_heights = [4.0] * self.bars_count
        self.phase = 0.0
        self.blink_state = True
        self.blink_counter = 0
        self.audio_level = 0.0
        self.smoothed_level = 0.0

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_tick)

        self.setStyleSheet("border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; background: rgba(0, 0, 0, 0.2);")

    def set_audio_level(self, level: float):
        """Mikrofondan gelen anlık gerçek ses şiddetini ayarlar (0.0 - 1.0)."""
        self.audio_level = max(0.0, min(1.0, float(level)))

    def start_recording_anim(self):
        self.mode = self.MODE_RECORDING
        self.audio_level = 0.0
        self.smoothed_level = 0.0
        for i in range(self.bars_count):
            self.bar_heights[i] = 4.0
        if not self.anim_timer.isActive():
            self.anim_timer.start(40)

    def start_playing_anim(self):
        self.mode = self.MODE_PLAYING
        if not self.anim_timer.isActive():
            self.anim_timer.start(40)

    def stop_anim(self):
        self.mode = self.MODE_IDLE
        self.anim_timer.stop()
        self.audio_level = 0.0
        self.smoothed_level = 0.0
        self.bar_heights = [4.0] * self.bars_count
        self.update()

    def _on_tick(self):
        self.blink_counter = (self.blink_counter + 1) % 12
        if self.blink_counter == 0:
            self.blink_state = not self.blink_state

        max_h = max(16.0, float(self.height() - 32))
        baseline_h = 4.0

        if self.mode == self.MODE_RECORDING:
            SILENCE_THRESHOLD = 0.035
            if self.audio_level <= SILENCE_THRESHOLD:
                # Sessizlikte seviye hızla 0'a iner
                self.smoothed_level = max(0.0, self.smoothed_level * 0.65)
            else:
                # Konuşma algılandığında dinamik tepki ver
                raw_speech = min(1.0, (self.audio_level - SILENCE_THRESHOLD) / 0.35)
                self.smoothed_level = self.smoothed_level * 0.4 + raw_speech * 0.6

            if self.smoothed_level < 0.015:
                # Sessiz ortam: Barlar tamamen düz çizgi, hiçbir hareket yok!
                for i in range(self.bars_count):
                    self.bar_heights[i] = baseline_h
            else:
                # Konuşuluyor: Ses şiddetine göre dinamik hareket ve dalga
                self.phase += 0.35
                for i in range(self.bars_count):
                    center_factor = 1.0 - abs(i - (self.bars_count / 2.0)) / (self.bars_count / 2.0) * 0.35
                    w1 = math.sin(self.phase * 1.8 + i * 0.5)
                    w2 = math.cos(self.phase * 1.1 - i * 0.7)
                    wave_val = abs(w1 * 0.6 + w2 * 0.4)
                    target_h = baseline_h + (self.smoothed_level * center_factor * wave_val) * (max_h - baseline_h)
                    self.bar_heights[i] = self.bar_heights[i] * 0.4 + target_h * 0.6
        elif self.mode == self.MODE_PLAYING:
            self.phase += 0.2
            for i in range(self.bars_count):
                wave = math.sin(self.phase * 2.2 + i * 0.5)
                self.bar_heights[i] = baseline_h + abs(wave) * (max_h - baseline_h)
        else:
            for i in range(self.bars_count):
                self.bar_heights[i] = baseline_h

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Arka plan ve sınır çerçevesi
        painter.fillRect(self.rect(), QColor("#090d16"))
        painter.setPen(QPen(QColor("#1e293b"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8.0, 8.0)

        # Durum rozeti / başlığı
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        if self.mode == self.MODE_RECORDING:
            if self.blink_state:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#ef4444"))
                painter.drawEllipse(14, 12, 8, 8)
            painter.setPen(QColor("#f87171"))
            painter.drawText(28, 20, "CANLI SES KAYDEDİLİYOR...")
        elif self.mode == self.MODE_PLAYING:
            painter.setPen(QColor("#38bdf8"))
            painter.drawText(14, 20, "▶ SES OYNATILIYOR")
        else:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(14, 20, "Ses Görselleştirici (Hazır)")

        # Çubukları çiz
        avail_w = w - 28
        bar_w = max(4.0, (avail_w / self.bars_count) - 3.0)
        gap = 3.0
        center_y = h - 24

        for i in range(self.bars_count):
            bx = 14 + i * (bar_w + gap)
            bh = self.bar_heights[i]
            by = center_y - (bh / 2.0)

            rect = QRectF(bx, by, bar_w, bh)
            if self.mode == self.MODE_RECORDING:
                grad = QLinearGradient(bx, by, bx, by + bh)
                grad.setColorAt(0.0, QColor("#ef4444"))
                grad.setColorAt(1.0, QColor("#f97316"))
                painter.setBrush(grad)
                painter.setPen(Qt.PenStyle.NoPen)
            elif self.mode == self.MODE_PLAYING:
                grad = QLinearGradient(bx, by, bx, by + bh)
                grad.setColorAt(0.0, QColor("#38bdf8"))
                grad.setColorAt(1.0, QColor("#6366f1"))
                painter.setBrush(grad)
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setBrush(QColor("#334155"))
                painter.setPen(Qt.PenStyle.NoPen)

            painter.drawRoundedRect(rect, bar_w / 2.0, bar_w / 2.0)


class AudioRecordDialog(QDialog):
    """
    Canlı mikrofon kaydı veya dosya seçimi ile PDF'e ses notu ekleme diyalogu.
    Ayrı Kaydı Başlat / Kaydı Durdur butonları ve canlı ses dalgası önizlemesi içerir.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ses Kaydı Ekle")
        self.setFixedSize(500, 520)
        self.setStyleSheet(get_dialog_theme_stylesheet(self))

        # Belgeyi düzenlemeye devam edebilmek için modeless ve üstte kalma bayrakları
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.is_compact = False

        self.audio_bytes: Optional[bytes] = None
        self.duration_sec: float = 0.0
        self.format: str = "wav"

        self.capture_session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.recorder = QMediaRecorder()
        self.capture_session.setAudioInput(self.audio_input)
        self.capture_session.setRecorder(self.recorder)

        self.player_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.player_output)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self.temp_record_path = tempfile.mktemp(suffix=".m4a")
        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.temp_record_path))

        self.is_recording = False
        self.is_paused = False
        self.elapsed_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_timer)

        # Gerçek mikrofon seviyesini okumak için QAudioSource
        self.audio_fmt = QAudioFormat()
        self.audio_fmt.setSampleRate(8000)
        self.audio_fmt.setChannelCount(1)
        self.audio_fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self.audio_source: Optional[QAudioSource] = None
        self.audio_source_io = None

        self.level_timer = QTimer(self)
        self.level_timer.setInterval(40)
        self.level_timer.timeout.connect(self._read_audio_level)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr_box = QHBoxLayout()
        hdr = QLabel("Ses Kaydı Ekle")
        hdr.setStyleSheet("font-size: 16px; font-weight: bold; ")
        hdr_box.addWidget(hdr)
        hdr_box.addStretch()

        self.btn_compact = QPushButton("🗕 Kompakt Mod")
        self.btn_compact.setToolTip("Belgeyi rahatça düzenleyebilmek için pencereyi küçültür / genişletir")
        self.btn_compact.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_compact.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }
        """)
        self.btn_compact.clicked.connect(self._toggle_compact_mode)
        hdr_box.addWidget(self.btn_compact)
        layout.addLayout(hdr_box)

        self.lbl_title = QLabel("Ses Notu Başlığı:")
        self.lbl_title.setStyleSheet(" font-size: 11px;")
        layout.addWidget(self.lbl_title)

        self.txt_title = QLineEdit("Ses Notu")
        self.txt_title.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 7px 10px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        layout.addWidget(self.txt_title)

        # Sayaç Paneli
        self.timer_frame = QFrame()
        self.timer_frame.setObjectName("timer_frame")
        self.timer_frame.setMinimumHeight(92)
        self.timer_frame.setStyleSheet("""
            QFrame#timer_frame {
                background-color: rgba(0, 0, 0, 0.25);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        t_layout = QVBoxLayout(self.timer_frame)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.setSpacing(4)
        t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_time = QLabel("00:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setStyleSheet("font-size: 34px; font-weight: bold;  font-family: 'Consolas', 'Segoe UI', monospace; border: none; background: transparent; padding: 0; min-height: 42px;")
        t_layout.addWidget(self.lbl_time)

        self.lbl_status = QLabel("Kayda hazır")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(" font-size: 12px; font-weight: 500; border: none; background: transparent; padding: 0; min-height: 20px;")
        t_layout.addWidget(self.lbl_status)
        layout.addWidget(self.timer_frame)

        # Canlı Ses Dalga Önizleme Bileşeni
        self.visualizer = AudioWaveformVisualizer(self)
        layout.addWidget(self.visualizer)

        # Kontrol Butonları (Başlat / Duraklat / Durdur / Sıfırla / Dinle)
        ctrl_box = QHBoxLayout()
        ctrl_box.setSpacing(8)

        btn_disabled_css = "background-color: rgba(255, 255, 255, 0.03); color: #64748b; border: 1px solid rgba(255, 255, 255, 0.06);"

        self.btn_start = QPushButton("Kaydı Başlat")
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_start.clicked.connect(self._start_record)

        self.btn_pause = QPushButton("Duraklat")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_stop = QPushButton("Durdur")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_stop.clicked.connect(self._stop_record)

        self.btn_reset = QPushButton("Sıfırla")
        self.btn_reset.setEnabled(False)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_reset.clicked.connect(self._reset_record)

        self.btn_play_preview = QPushButton("Dinle")
        self.btn_play_preview.setEnabled(False)
        self.btn_play_preview.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_play_preview.clicked.connect(self._play_preview)

        ctrl_box.addWidget(self.btn_start)
        ctrl_box.addWidget(self.btn_pause)
        ctrl_box.addWidget(self.btn_stop)
        ctrl_box.addWidget(self.btn_reset)
        ctrl_box.addWidget(self.btn_play_preview)
        layout.addLayout(ctrl_box)

        self.btn_choose_file = QPushButton("veya Bilgisayardan Ses Dosyası Seç (.mp3, .wav, .m4a)...")
        self.btn_choose_file.setStyleSheet("""
            QPushButton {
                background-color: transparent;  text-decoration: underline;
                border: none; font-size: 11px; padding: 4px;
            }
            QPushButton:hover {  }
        """)
        self.btn_choose_file.clicked.connect(self._choose_audio_file)
        layout.addWidget(self.btn_choose_file)

        layout.addStretch()

        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setStyleSheet("padding: 8px 16px;   border-radius: 6px; font-size: 12px;")
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_ok = QPushButton("Belgeye Ekle")
        self.btn_ok.setEnabled(False)
        self.btn_ok.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 20px;  
                font-weight: bold; border-radius: 6px; font-size: 12px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_ok.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)

    def _toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.lbl_title.hide()
            self.txt_title.hide()
            self.visualizer.hide()
            self.btn_choose_file.hide()
            self.btn_cancel.hide()
            self.timer_frame.setMinimumHeight(56)
            self.lbl_time.setStyleSheet(
                "font-size: 24px; font-weight: bold;  font-family: 'Consolas', 'Segoe UI', monospace; border: none; background: transparent; padding: 0;"
            )
            self.lbl_status.setStyleSheet(
                " font-size: 11px; font-weight: 500; border: none; background: transparent; padding: 0;"
            )
            self.btn_compact.setText("🗖 Tam Görünüm")
            self.btn_compact.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #f1f5f9;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border-color: rgba(255, 255, 255, 0.25);
                    color: #ffffff;
                }
            """)
            self.setFixedSize(480, 235)
        else:
            self.lbl_title.show()
            self.txt_title.show()
            self.visualizer.show()
            self.btn_choose_file.show()
            self.btn_cancel.show()
            self.timer_frame.setMinimumHeight(92)
            self.lbl_time.setStyleSheet(
                "font-size: 34px; font-weight: bold;  font-family: 'Consolas', 'Segoe UI', monospace; border: none; background: transparent; padding: 0; min-height: 42px;"
            )
            self.lbl_status.setStyleSheet(
                " font-size: 12px; font-weight: 500; border: none; background: transparent; padding: 0; min-height: 20px;"
            )
            self.btn_compact.setText("🗕 Kompakt Mod")
            self.btn_compact.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #f1f5f9;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border-color: rgba(255, 255, 255, 0.25);
                    color: #ffffff;
                }
            """)
            self.setFixedSize(500, 520)

    def _read_audio_level(self):
        if not self.is_recording or self.is_paused or not self.audio_source_io:
            self.visualizer.set_audio_level(0.0)
            return
        try:
            raw_bytes = bytes(self.audio_source_io.readAll())
            if len(raw_bytes) >= 2:
                import struct
                count = len(raw_bytes) // 2
                samples = struct.unpack(f"<{count}h", raw_bytes[:count*2])
                peak = max(abs(s) for s in samples)
                level = peak / 32768.0
                self.visualizer.set_audio_level(level)
            else:
                self.visualizer.set_audio_level(0.0)
        except Exception:
            self.visualizer.set_audio_level(0.0)

    def _set_status(self, text: str, color: str = "#94a3b8"):
        self.lbl_status.setText(text)
        font_size = "11px" if self.is_compact else "12px"
        self.lbl_status.setStyleSheet(
            f"color: {color}; font-size: {font_size}; font-weight: 500; border: none; background: transparent; padding: 0;"
        )

    def _start_record(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        self.recorder.record()
        self.is_recording = True
        self.is_paused = False
        self.elapsed_seconds = 0
        self.lbl_time.setText("00:00")
        self.timer.start(1000)

        try:
            if not self.audio_source:
                dev = QMediaDevices.defaultAudioInput()
                self.audio_source = QAudioSource(dev, self.audio_fmt, self)
            self.audio_source_io = self.audio_source.start()
            self.level_timer.start()
        except Exception as e:
            print("AudioSource error:", e)

        btn_disabled_css = "background-color: rgba(255, 255, 255, 0.03); color: #64748b; border: 1px solid rgba(255, 255, 255, 0.06);"

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Duraklat")
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                  font-weight: bold;
                padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
            }}
            QPushButton:hover {{  }}
            QPushButton:disabled {{ {btn_disabled_css} }}
        """)
        self.btn_stop.setEnabled(True)
        self.btn_reset.setEnabled(False)
        self.btn_play_preview.setEnabled(False)
        self.btn_ok.setEnabled(False)

        self._set_status("Mikrofondan ses kaydediliyor...", "#f87171")
        self.visualizer.start_recording_anim()

    def _toggle_pause(self):
        if not self.is_recording:
            return

        btn_disabled_css = "background-color: rgba(255, 255, 255, 0.03); color: #64748b; border: 1px solid rgba(255, 255, 255, 0.06);"

        if not self.is_paused:
            self.recorder.pause()
            self.is_paused = True
            self.timer.stop()
            self.btn_pause.setText("Devam Et")
            self.btn_pause.setStyleSheet(f"""
                QPushButton {{
                      font-weight: bold;
                    padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
                }}
                QPushButton:hover {{  }}
                QPushButton:disabled {{ {btn_disabled_css} }}
            """)
            self._set_status("Kayıt duraklatıldı", "#eab308")
            self.visualizer.set_audio_level(0.0)
        else:
            self.recorder.record()
            self.is_paused = False
            self.timer.start(1000)
            self.btn_pause.setText("Duraklat")
            self.btn_pause.setStyleSheet(f"""
                QPushButton {{
                      font-weight: bold;
                    padding: 9px 8px; border-radius: 6px; border: none; font-size: 11px; min-width: 72px;
                }}
                QPushButton:hover {{  }}
                QPushButton:disabled {{ {btn_disabled_css} }}
            """)
            self._set_status("Mikrofondan ses kaydediliyor...", "#f87171")

    def _stop_record(self):
        if not self.is_recording:
            return

        self.recorder.stop()
        self.is_recording = False
        self.is_paused = False
        self.timer.stop()
        self.level_timer.stop()
        if self.audio_source:
            self.audio_source.stop()
            self.audio_source_io = None
        self.duration_sec = float(self.elapsed_seconds)

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Duraklat")
        self.btn_stop.setEnabled(False)
        self.btn_reset.setEnabled(True)

        self._set_status("Kayıt tamamlandı", "#10b981")
        self.visualizer.stop_anim()

        QTimer.singleShot(500, self._load_temp_audio)

    def _reset_record(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        if self.audio_source:
            self.audio_source.stop()
            self.audio_source_io = None
        self.level_timer.stop()

        self.audio_bytes = None
        self.duration_sec = 0.0
        self.elapsed_seconds = 0
        self.is_paused = False
        self.lbl_time.setText("00:00")
        self._set_status("Kayda hazır", "#94a3b8")

        self.visualizer.stop_anim()

        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Duraklat")
        self.btn_stop.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_play_preview.setEnabled(False)
        self.btn_ok.setEnabled(False)

    def _tick_timer(self):
        self.elapsed_seconds += 1
        m = self.elapsed_seconds // 60
        s = self.elapsed_seconds % 60
        self.lbl_time.setText(f"{m:02d}:{s:02d}")

    def _load_temp_audio(self):
        if os.path.exists(self.temp_record_path):
            with open(self.temp_record_path, "rb") as f:
                self.audio_bytes = f.read()
            self.btn_play_preview.setEnabled(True)
            self.btn_ok.setEnabled(True)

    def _play_preview(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()
            self.visualizer.stop_anim()
            self.btn_play_preview.setText("Dinle")
            return

        if self.temp_record_path and os.path.exists(self.temp_record_path):
            self.player.setSource(QUrl.fromLocalFile(self.temp_record_path))
            self.player_output.setVolume(1.0)
            self.player.play()
            self.visualizer.start_playing_anim()
            self.btn_play_preview.setText("Durdur")

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.visualizer.stop_anim()
            self.btn_play_preview.setText("Dinle")

    def _choose_audio_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Ses Dosyası Seç", "", "Ses Dosyaları (*.mp3 *.wav *.m4a *.ogg *.aac)")
        if fpath and os.path.exists(fpath):
            with open(fpath, "rb") as f:
                self.audio_bytes = f.read()
            ext = os.path.splitext(fpath)[1].replace(".", "")
            self.format = ext
            self.txt_title.setText(os.path.basename(fpath))
            self._set_status(f"Dosya yüklendi: {os.path.basename(fpath)}", "#10b981")
            self.temp_record_path = fpath
            self.btn_reset.setEnabled(True)
            self.btn_play_preview.setEnabled(True)
            self.btn_ok.setEnabled(True)

    def closeEvent(self, event):
        self._on_cancel()
        super().closeEvent(event)

    def _on_cancel(self):
        if self.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            try:
                self.player.stop()
            except Exception:
                pass
        if self.audio_source:
            try:
                self.audio_source.stop()
            except Exception:
                pass
            self.audio_source_io = None
        self.level_timer.stop()
        self.timer.stop()
        self.visualizer.stop_anim()
        self.reject()


class VideoInsertDialog(QDialog):
    """
    Video ekleme penceresi: Bilgisayardan video seçme veya video URL'si girme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Video Ekle")
        self.setFixedSize(440, 380)
        self.setStyleSheet(get_dialog_theme_stylesheet(self))

        self.video_url_or_path: str = ""
        self.thumbnail_bytes: Optional[bytes] = None
        self.title: str = "Video"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        hdr = QLabel("Video Ekle")
        hdr.setStyleSheet("font-size: 16px; font-weight: bold; ")
        layout.addWidget(hdr)

        desc = QLabel("PDF sayfasına video önizleme kartı ekleyin. Belgeyi okuyanlar karta tıklayarak videoyu izleyebilir.")
        desc.setWordWrap(True)
        desc.setStyleSheet(" font-size: 11px;")
        layout.addWidget(desc)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; background-color: rgba(255, 255, 255, 0.02); }
            QTabBar::tab { background: rgba(255, 255, 255, 0.04); color: #94a3b8; padding: 6px 14px; border-top-left-radius: 4px; border-top-right-radius: 4px; font-size: 11px; font-weight: bold; }
            QTabBar::tab:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
            QTabBar::tab:selected { background: rgba(255, 255, 255, 0.1); color: #38bdf8; border-bottom: 2px solid #38bdf8; }
        """)

        # Sekme 1: Bilgisayardan
        tab_local = QWidget()
        tl = QVBoxLayout(tab_local)
        tl.setSpacing(10)
        btn_sel_video = QPushButton("Bilgisayardan Video Seç (.mp4, .mkv, .avi, .webm)...")
        btn_sel_video.setStyleSheet("background-color: #2563eb; color: #ffffff; font-weight: bold; padding: 10px; border-radius: 6px; border: none;")
        btn_sel_video.clicked.connect(self._select_local_video)
        tl.addWidget(btn_sel_video)

        self.lbl_local_info = QLabel("Seçilen video yok")
        self.lbl_local_info.setStyleSheet(" font-size: 11px;")
        tl.addWidget(self.lbl_local_info)
        tl.addStretch()
        tabs.addTab(tab_local, "Bilgisayardan")

        # Sekme 2: Web URL
        tab_url = QWidget()
        tu = QVBoxLayout(tab_url)
        tu.setSpacing(10)

        lbl_u = QLabel("Video Bağlantısı (YouTube, Vimeo veya doğrudan video URL):")
        lbl_u.setStyleSheet(" font-size: 11px;")
        tu.addWidget(lbl_u)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.txt_url.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 8px;")
        tu.addWidget(self.txt_url)

        btn_apply_url = QPushButton("Bağlantıyı Tanımla")
        btn_apply_url.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); color: #f1f5f9; font-weight: bold; padding: 8px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.15);")
        btn_apply_url.clicked.connect(self._apply_url)
        tu.addWidget(btn_apply_url)
        tu.addStretch()
        tabs.addTab(tab_url, "Web / YouTube")

        layout.addWidget(tabs)

        # Başlık Kutusu
        lbl_t = QLabel("Video Başlığı:")
        lbl_t.setStyleSheet(" font-size: 11px;")
        layout.addWidget(lbl_t)
        self.txt_title = QLineEdit("Tanıtım Videosu")
        self.txt_title.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 6px 10px;")
        layout.addWidget(self.txt_title)

        layout.addStretch()

        # Butonlar
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("padding: 8px 16px;   border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("Belgeye Ekle")
        self.btn_ok.setEnabled(False)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;  
                font-weight: bold; border-radius: 6px;
            }
            QPushButton:disabled {   }
        """)
        self.btn_ok.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)

    def _select_local_video(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Video Seç", "", "Video Dosyaları (*.mp4 *.mkv *.avi *.mov *.webm)")
        if fpath and os.path.exists(fpath):
            self.video_url_or_path = fpath
            name = os.path.basename(fpath)
            self.txt_title.setText(os.path.splitext(name)[0])
            self.lbl_local_info.setText(f"Seçildi: {name}")
            self.lbl_local_info.setStyleSheet("")
            self.thumbnail_bytes = self._generate_default_thumbnail(name)
            self.btn_ok.setEnabled(True)

    def _apply_url(self):
        url = self.txt_url.text().strip()
        if not url:
            return
        self.video_url_or_path = url
        yt_id = self._extract_youtube_id(url)
        if yt_id:
            try:
                thumb_url = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
                req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    self.thumbnail_bytes = resp.read()
            except Exception:
                self.thumbnail_bytes = self._generate_default_thumbnail("YouTube Video")
        else:
            self.thumbnail_bytes = self._generate_default_thumbnail("Web Video")

        self.btn_ok.setEnabled(True)
        QMessageBox.information(self, "Bilgi", "Video bağlantısı başarıyla tanımlandı.")

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    def _generate_default_thumbnail(self, title: str) -> bytes:
        pix = QPixmap(320, 180)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        grad = QLinearGradient(0, 0, 320, 180)
        grad.setColorAt(0.0, QColor("#1e1b4b"))
        grad.setColorAt(1.0, QColor("#09090b"))
        p.fillRect(0, 0, 320, 180, grad)

        p.setPen(QColor("#38bdf8"))
        p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        p.drawText(QRectF(0, 40, 320, 40), Qt.AlignmentFlag.AlignCenter, "VIDEO")

        p.setPen(QColor("#cbd5e1"))
        p.setFont(QFont("Arial", 10))
        p.drawText(QRectF(10, 120, 300, 30), Qt.AlignmentFlag.AlignCenter, title)
        p.end()

        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        return bytes(buf.data())

    def get_data(self) -> Tuple[str, Optional[bytes], str]:
        return (self.video_url_or_path, self.thumbnail_bytes, self.txt_title.text().strip())
