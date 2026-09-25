"""
AuraPDF - PDF İmzalama Diyaloğu (PDF Signature Dialog)
======================================================
Kullanıcının fare/kalem ile çizerek, adını yazarak (kaligrafi/el yazısı fontlarıyla)
veya imza/kaşe resmi yükleyip (beyaz arka planı şeffaflaştırarak) PDF belgesine
imza eklemesini sağlayan modern arayüz bileşeni.
"""

import os
import io
import base64
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QLineEdit, QComboBox, QSlider,
    QFileDialog, QMessageBox, QFrame, QCheckBox, QButtonGroup,
    QRadioButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize, QSettings
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QImage, QPixmap, QPainterPath,
    QFontDatabase, QCursor
)

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet
from src.ui.icons import ModernIconFactory


class SignatureCanvasWidget(QWidget):
    """
    Kullanıcının serbestçe imza çizebileceği antialiased ve pürüzsüz çizim tuvali.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.strokes: List[dict] = []  # List of {"points": [QPointF], "color": QColor, "width": float}
        self.current_points: List[QPointF] = []
        self.pen_color = QColor("#0d47a1")  # Resmi mavi default
        self.pen_width = 3.0

        self.setStyleSheet(" border: 1.5px dashed #4a5568; border-radius: 8px;")

    def set_pen_color(self, color: QColor):
        self.pen_color = color

    def set_pen_width(self, width: float):
        self.pen_width = width

    def clear(self):
        self.strokes.clear()
        self.current_points.clear()
        self.update()

    def undo_stroke(self):
        if self.strokes:
            self.strokes.pop()
            self.update()

    def has_signature(self) -> bool:
        return len(self.strokes) > 0 or len(self.current_points) > 1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.current_points = [event.position()]
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.current_points.append(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and len(self.current_points) > 1:
            self.strokes.append({
                "points": list(self.current_points),
                "color": QColor(self.pen_color),
                "width": float(self.pen_width)
            })
            self.current_points.clear()
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Beyaz zemin
        p.fillRect(self.rect(), QColor("#ffffff"))

        # İmza çizgi rehberi (Signature baseline hint)
        p.setPen(QPen(QColor("#e2e8f0"), 1.2, Qt.PenStyle.DashLine))
        guide_y = self.height() * 0.72
        p.drawLine(QPointF(30, guide_y), QPointF(self.width() - 30, guide_y))

        # "x" işareti
        p.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        p.setPen(QPen(QColor("#cbd5e1")))
        p.drawText(QRectF(15, guide_y - 18, 20, 20), Qt.AlignmentFlag.AlignCenter, "✕")

        # Çizimleri çiz
        all_strokes = list(self.strokes)
        if len(self.current_points) > 1:
            all_strokes.append({
                "points": self.current_points,
                "color": self.pen_color,
                "width": self.pen_width
            })

        for stroke in all_strokes:
            pts = stroke["points"]
            if len(pts) < 2:
                continue
            pen = QPen(stroke["color"], stroke["width"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)

            path = QPainterPath()
            path.moveTo(pts[0])
            for i in range(1, len(pts)):
                # Bezier yumuşatma
                mid = QPointF((pts[i - 1].x() + pts[i].x()) / 2.0, (pts[i - 1].y() + pts[i].y()) / 2.0)
                path.quadTo(pts[i - 1], mid)
            path.lineTo(pts[-1])
            p.drawPath(path)

        p.end()

    def get_signature_image(self) -> Optional[QImage]:
        if not self.strokes:
            return None

        # Sınırları hesapla (Bounding rect)
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for stroke in self.strokes:
            w = stroke["width"]
            for pt in stroke["points"]:
                min_x = min(min_x, pt.x() - w)
                min_y = min(min_y, pt.y() - w)
                max_x = max(max_x, pt.x() + w)
                max_y = max(max_y, pt.y() + w)

        pad = 12.0
        min_x = max(0.0, min_x - pad)
        min_y = max(0.0, min_y - pad)
        max_x = min(float(self.width()), max_x + pad)
        max_y = min(float(self.height()), max_y + pad)

        crop_w = int(max_x - min_x)
        crop_h = int(max_y - min_y)
        if crop_w <= 0 or crop_h <= 0:
            return None

        # Şeffaf yüksek kaliteli QImage oluştur
        scale = 2.0  # 2x Retina kalitesi
        img = QImage(int(crop_w * scale), int(crop_h * scale), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(scale, scale)
        p.translate(-min_x, -min_y)

        for stroke in self.strokes:
            pts = stroke["points"]
            if len(pts) < 2:
                continue
            pen = QPen(stroke["color"], stroke["width"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)

            path = QPainterPath()
            path.moveTo(pts[0])
            for i in range(1, len(pts)):
                mid = QPointF((pts[i - 1].x() + pts[i].x()) / 2.0, (pts[i - 1].y() + pts[i].y()) / 2.0)
                path.quadTo(pts[i - 1], mid)
            path.lineTo(pts[-1])
            p.drawPath(path)

        p.end()
        return img


class PDFSignatureDialog(QDialog):
    """
    Modern 3 Modlu PDF İmzalama Penceresi:
    1. Çizerek İmza (Interactive Canvas)
    2. Yazarak İmza (Calligraphic Typography)
    3. Resim Yükleyerek İmza (Image with Transparency filter)
    """
    def __init__(self, parent=None, default_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle(LanguageManager.tr("sign_dialog_title"))
        self.resize(640, 540)
        self.setMinimumSize(540, 440)
        self.setSizeGripEnabled(True)
        self.default_name = default_name
        self.result_image: Optional[QImage] = None

        self._init_ui()
        self._load_saved_signature()

    def _init_ui(self):
        self.setStyleSheet(get_dialog_theme_stylesheet(self) + """
            QDialog {   }
            QLabel {  font-size: 12px; }
            QLineEdit {   border: 1px solid; border-radius: 6px; padding: 7px 10px; font-size: 13px; }
            QLineEdit:focus { border: 1.5px solid #0a84ff; }
            QComboBox {   border: 1px solid; border-radius: 6px; padding: 5px 10px; }
            QTabWidget::pane { border: 1px solid;  border-radius: 8px; }
            QTabBar::tab {   padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: 500; font-size: 12px; }
            QTabBar::tab:selected {   border-bottom: 2.5px solid #0a84ff; font-weight: bold; }
            QPushButton {   border: 1px solid; border-radius: 6px; padding: 6px 14px; font-weight: 500; min-height: 26px; }
            QPushButton:hover {  }
            QPushButton#PrimaryBtn {  border: none; font-weight: bold;  }
            QPushButton#PrimaryBtn:hover {  }
            QPushButton#ActionBtn {  border: 1px solid; }
            QPushButton#ActionBtn:hover {  }
            QCheckBox {  font-size: 12px; spacing: 8px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Tab Widget
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # 1. SEKME: Çizerek İmza
        tab_draw = QWidget()
        self._build_draw_tab(tab_draw)
        self.tabs.addTab(tab_draw, LanguageManager.tr("sign_tab_draw"))

        # 2. SEKME: Yazarak İmza
        tab_type = QWidget()
        self._build_type_tab(tab_type)
        self.tabs.addTab(tab_type, LanguageManager.tr("sign_tab_type"))

        # 3. SEKME: Resim Yükle
        tab_image = QWidget()
        self._build_image_tab(tab_image)
        self.tabs.addTab(tab_image, LanguageManager.tr("sign_tab_image"))

        # Alt Seçenekler ve Butonlar
        bottom_bar = QHBoxLayout()
        self.chk_save_default = QCheckBox(LanguageManager.tr("sign_save_as_default"))
        bottom_bar.addWidget(self.chk_save_default)
        bottom_bar.addStretch()

        self.btn_load_saved = QPushButton(LanguageManager.tr("sign_use_saved"))
        self.btn_load_saved.setObjectName("ActionBtn")
        self.btn_load_saved.clicked.connect(self._apply_saved_signature)
        bottom_bar.addWidget(self.btn_load_saved)
        layout.addLayout(bottom_bar)

        h_action = QHBoxLayout()
        h_action.addStretch()
        btn_cancel = QPushButton(LanguageManager.tr("print_btn_cancel"))
        btn_cancel.clicked.connect(self.reject)
        h_action.addWidget(btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("sign_btn_place"))
        self.btn_apply.setObjectName("PrimaryBtn")
        self.btn_apply.clicked.connect(self.accept_signature)
        h_action.addWidget(self.btn_apply)
        layout.addLayout(h_action)

    # ----------------------------------------------------
    # SEKME 1: ÇİZEREK İMZA
    # ----------------------------------------------------
    def _build_draw_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        lbl_hint = QLabel(LanguageManager.tr("sign_draw_hint"))
        lbl_hint.setStyleSheet("")
        layout.addWidget(lbl_hint)

        self.canvas = SignatureCanvasWidget(self)
        layout.addWidget(self.canvas, stretch=1)

        # Araçlar: Renk ve Kalınlık
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        tool_row.addWidget(QLabel(LanguageManager.tr("sign_pen_color")))
        self.selected_draw_color = "#0d47a1"
        self.draw_color_buttons = {}
        color_options = [
            ("#0d47a1", LanguageManager.tr("sign_color_blue")),
            ("#1a1a1a", LanguageManager.tr("sign_color_black")),
            ("#002171", LanguageManager.tr("sign_color_navy")),
            ("#b71c1c", LanguageManager.tr("sign_color_red"))
        ]

        for hex_code, name in color_options:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, c=hex_code: self._set_draw_color(c))
            self.draw_color_buttons[hex_code] = (btn, name)
            tool_row.addWidget(btn)

        self._refresh_draw_color_buttons()

        tool_row.addSpacing(10)
        tool_row.addWidget(QLabel(LanguageManager.tr("sign_pen_thickness")))
        self.sld_thickness = QSlider(Qt.Orientation.Horizontal)
        self.sld_thickness.setRange(15, 60)
        self.sld_thickness.setValue(30)
        self.sld_thickness.setFixedWidth(90)
        self.sld_thickness.valueChanged.connect(lambda v: self.canvas.set_pen_width(v / 10.0))
        tool_row.addWidget(self.sld_thickness)

        tool_row.addStretch()

        btn_undo = QPushButton(LanguageManager.tr("sign_btn_undo_stroke"))
        btn_undo.setObjectName("ActionBtn")
        btn_undo.clicked.connect(self.canvas.undo_stroke)
        tool_row.addWidget(btn_undo)

        btn_clear = QPushButton(LanguageManager.tr("sign_btn_clear"))
        btn_clear.clicked.connect(self.canvas.clear)
        tool_row.addWidget(btn_clear)

        layout.addLayout(tool_row)

    def _set_draw_color(self, hex_code: str):
        self.selected_draw_color = hex_code
        self.canvas.set_pen_color(QColor(hex_code))
        self._refresh_draw_color_buttons()

    def _refresh_draw_color_buttons(self):
        for hex_code, (btn, name) in self.draw_color_buttons.items():
            if hex_code == self.selected_draw_color:
                btn.setText(f"✓ {name}")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        
                        font-weight: bold;
                        border: 2.5px solid #38bdf8;
                        border-radius: 6px;
                        padding: 5px 10px;
                    }}
                """)
            else:
                btn.setText(name)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        
                        font-weight: 500;
                        border: 1px solid;
                        border-radius: 5px;
                        padding: 4px 8px;
                        opacity: 0.85;
                    }}
                    QPushButton:hover {{
                        border-
                        
                    }}
                """)

    # ----------------------------------------------------
    # SEKME 2: YAZARAK İMZA
    # ----------------------------------------------------
    def _build_type_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(QLabel(LanguageManager.tr("sign_type_label")))
        self.txt_type_name = QLineEdit()
        self.txt_type_name.setPlaceholderText(LanguageManager.tr("sign_type_placeholder"))
        if self.default_name:
            self.txt_type_name.setText(self.default_name)
        layout.addWidget(self.txt_type_name)

        # Font Seçimi & Renk
        h_opt = QHBoxLayout()
        h_opt.addWidget(QLabel(LanguageManager.tr("sign_type_font")))
        self.cmb_font = QComboBox()

        all_fonts = QFontDatabase.families()
        script_candidates = [
            "Segoe Script", "Lucida Handwriting", "Brush Script MT", 
            "Mistral", "Freestyle Script", "Monotype Corsiva", 
            "Comic Sans MS", "Gabriola", "Georgia"
        ]
        available_scripts = [f for f in script_candidates if f in all_fonts]
        if not available_scripts:
            available_scripts = ["Arial", "Times New Roman"]

        for f in available_scripts:
            self.cmb_font.addItem(f, f)
        h_opt.addWidget(self.cmb_font, stretch=1)

        h_opt.addSpacing(10)
        h_opt.addWidget(QLabel(LanguageManager.tr("sign_pen_color")))
        self.selected_type_color = "#0d47a1"
        self.type_color_buttons = {}
        type_colors = [
            ("#0d47a1", LanguageManager.tr("sign_color_blue")),
            ("#1a1a1a", LanguageManager.tr("sign_color_black")),
            ("#002171", LanguageManager.tr("sign_color_navy")),
            ("#b71c1c", LanguageManager.tr("sign_color_red"))
        ]
        for hex_code, name in type_colors:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, c=hex_code: self._set_type_color(c))
            self.type_color_buttons[hex_code] = (btn, name)
            h_opt.addWidget(btn)

        layout.addLayout(h_opt)
        self._refresh_type_color_buttons()

        # Canlı Önizleme Kutusu
        self.lbl_type_preview = QLabel()
        self.lbl_type_preview.setMinimumHeight(140)
        self.lbl_type_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_type_preview.setStyleSheet(" border: 1.5px dashed #4a5568; border-radius: 8px;")
        layout.addWidget(self.lbl_type_preview, stretch=1)

        self.txt_type_name.textChanged.connect(self._update_type_preview)
        self.cmb_font.currentIndexChanged.connect(self._update_type_preview)
        self._update_type_preview()

    def _set_type_color(self, hex_code: str):
        self.selected_type_color = hex_code
        self._refresh_type_color_buttons()
        self._update_type_preview()

    def _refresh_type_color_buttons(self):
        for hex_code, (btn, name) in self.type_color_buttons.items():
            if hex_code == self.selected_type_color:
                btn.setText(f"✓ {name}")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        
                        font-weight: bold;
                        border: 2.5px solid #38bdf8;
                        border-radius: 6px;
                        padding: 5px 10px;
                    }}
                """)
            else:
                btn.setText(name)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_code};
                        
                        font-weight: 500;
                        border: 1px solid;
                        border-radius: 5px;
                        padding: 4px 8px;
                        opacity: 0.85;
                    }}
                    QPushButton:hover {{
                        border-
                        
                    }}
                """)

    def _update_type_preview(self):
        text = self.txt_type_name.text().strip() or "İmza Örneği"
        font_family = self.cmb_font.currentData() or "Segoe Script"
        color_hex = getattr(self, 'selected_type_color', '#0d47a1')

        pix = QPixmap(480, 140)
        pix.fill(QColor("#ffffff"))

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Rehber çizgi
        p.setPen(QPen(QColor("#e2e8f0"), 1.2, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(20, 105), QPointF(460, 105))

        font = QFont(font_family, 26)
        font.setItalic(True)
        p.setFont(font)
        p.setPen(QPen(QColor(color_hex)))
        p.drawText(QRectF(10, 10, 460, 95), Qt.AlignmentFlag.AlignCenter, text)
        p.end()

        self.lbl_type_preview.setPixmap(pix)

    # ----------------------------------------------------
    # SEKME 3: RESİM / KAŞE YÜKLE
    # ----------------------------------------------------
    def _build_image_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        h_browse = QHBoxLayout()
        btn_browse = QPushButton(LanguageManager.tr("sign_image_choose"))
        btn_browse.setIcon(ModernIconFactory.icon_image())
        btn_browse.setObjectName("PrimaryBtn")
        btn_browse.clicked.connect(self._browse_signature_image)
        h_browse.addWidget(btn_browse)

        self.lbl_img_path = QLabel("")
        self.lbl_img_path.setStyleSheet(" font-size: 11px;")
        h_browse.addWidget(self.lbl_img_path, stretch=1)
        layout.addLayout(h_browse)

        self.chk_remove_bg = QCheckBox(LanguageManager.tr("sign_remove_bg"))
        self.chk_remove_bg.setChecked(True)
        self.chk_remove_bg.toggled.connect(self._process_and_preview_image)
        layout.addWidget(self.chk_remove_bg)

        self.lbl_img_preview = QLabel()
        self.lbl_img_preview.setMinimumHeight(150)
        self.lbl_img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img_preview.setStyleSheet(" border: 1.5px dashed #4a5568; border-radius: 8px;")
        layout.addWidget(self.lbl_img_preview, stretch=1)

        self.loaded_raw_image: Optional[QImage] = None

    def _browse_signature_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, LanguageManager.tr("sign_image_choose"), "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)"
        )
        if path and os.path.isfile(path):
            self.lbl_img_path.setText(os.path.basename(path))
            self.loaded_raw_image = QImage(path)
            self._process_and_preview_image()

    def _process_and_preview_image(self):
        if not self.loaded_raw_image or self.loaded_raw_image.isNull():
            return

        img = self.loaded_raw_image.convertToFormat(QImage.Format.Format_ARGB32)

        if self.chk_remove_bg.isChecked():
            # Beyaz / açık gri arka planı şeffaflaştır
            w, h = img.width(), img.height()
            for y in range(h):
                for x in range(w):
                    col = img.pixelColor(x, y)
                    lum = (col.red() * 299 + col.green() * 587 + col.blue() * 114) // 1000
                    if lum > 215:
                        col.setAlpha(0)
                        img.setPixelColor(x, y, col)
                    elif lum > 175:
                        factor = (215 - lum) / 40.0
                        col.setAlpha(int(col.alpha() * factor))
                        img.setPixelColor(x, y, col)

        pix = QPixmap.fromImage(img)
        scaled = pix.scaled(380, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.lbl_img_preview.setPixmap(scaled)
        self.processed_signature_image = img

    # ----------------------------------------------------
    # KAYITLI İMZA & KABUL ETME
    # ----------------------------------------------------
    def _load_saved_signature(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_b64 = settings.value("saved_signature_png", None)
        if saved_b64:
            self.btn_load_saved.setEnabled(True)
        else:
            self.btn_load_saved.setEnabled(False)

    def _apply_saved_signature(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_b64 = settings.value("saved_signature_png", None)
        if not saved_b64:
            return
        try:
            raw = base64.b64decode(saved_b64)
            img = QImage()
            img.loadFromData(raw, "PNG")
            if not img.isNull():
                self.result_image = img
                self.accept()
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("error"), str(e))

    def accept_signature(self):
        tab_idx = self.tabs.currentIndex()
        final_img = None

        if tab_idx == 0:
            final_img = self.canvas.get_signature_image()
        elif tab_idx == 1:
            text = self.txt_type_name.text().strip()
            if text:
                font_family = self.cmb_font.currentData() or "Segoe Script"
                color_hex = getattr(self, 'selected_type_color', '#0d47a1')

                font = QFont(font_family, 36)
                font.setItalic(True)
                dummy = QPixmap(1, 1)
                p_dummy = QPainter(dummy)
                p_dummy.setFont(font)
                br = p_dummy.fontMetrics().boundingRect(text)
                p_dummy.end()

                pad = 16
                tw = max(100, br.width() + pad * 2)
                th = max(50, br.height() + pad * 2)

                final_img = QImage(tw, th, QImage.Format.Format_ARGB32_Premultiplied)
                final_img.fill(Qt.GlobalColor.transparent)

                p = QPainter(final_img)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                p.setFont(font)
                p.setPen(QPen(QColor(color_hex)))
                p.drawText(QRectF(0, 0, tw, th), Qt.AlignmentFlag.AlignCenter, text)
                p.end()
        elif tab_idx == 2:
            final_img = getattr(self, 'processed_signature_image', None)

        if final_img is None or final_img.isNull():
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("sign_warn_no_sig"))
            return

        self.result_image = final_img

        if self.chk_save_default.isChecked():
            try:
                from PyQt6.QtCore import QBuffer, QIODevice
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                final_img.save(buf, "PNG")
                b64 = base64.b64encode(buf.data().data()).decode('ascii')
                settings = QSettings("AuraPDF", "PDFViewer")
                settings.setValue("saved_signature_png", b64)
            except Exception:
                pass

        self.accept()
