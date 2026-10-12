"""
AuraPDF - PDF Doğrudan İçerik & Resim Düzenleyici
=================================================
PDF içerisindeki gömülü resimleri listeleme, önizleme, silme, değiştirme ve dışa aktarma;
gömülü metin bloklarını görsel olarak seçme, doğrudan düzenleme, silme ve yeni metin ekleme;
sayfa metinlerini optik karakter tanıma (OCR) ile okuma aracı.
"""

import os
import io
import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QFrame,
    QMessageBox, QFileDialog, QTextEdit, QLineEdit, QSplitter,
    QScrollArea, QSpinBox, QComboBox, QColorDialog
)
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QImage, QFont, QPainter, QPen, QBrush, QColor

import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet, apply_dialog_theme
from src.ui.icons import ModernIconFactory
from src.ui.modern_stepper import ModernSpinBox


class VisualBlockCanvas(QLabel):
    """Sayfadaki metin bloklarını veya görselleri görsel kutularla gösteren ve tıklamayla seçen etiket."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.blocks = []  # list of fitz.Rect
        self.selected_idx = -1
        self.on_block_clicked = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.base_pixmap = None

    def set_page_pixmap(self, pixmap, page_w, page_h, blocks, selected_idx=-1):
        self.base_pixmap = pixmap
        self.setPixmap(pixmap)
        self.blocks = blocks
        self.selected_idx = selected_idx
        if pixmap.width() > 0 and pixmap.height() > 0:
            self.scale_x = pixmap.width() / page_w
            self.scale_y = pixmap.height() / page_h
        self.update()

    def set_selected_idx(self, idx):
        self.selected_idx = idx
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.blocks:
            pos = event.position().toPoint()
            # Tıklanan noktaya denk gelen bloğu bul
            for i, rect in enumerate(self.blocks):
                bx0 = rect.x0 * self.scale_x
                by0 = rect.y0 * self.scale_y
                bx1 = rect.x1 * self.scale_x
                by1 = rect.y1 * self.scale_y
                if bx0 <= pos.x() <= bx1 and by0 <= pos.y() <= by1:
                    self.selected_idx = i
                    self.update()
                    if self.on_block_clicked:
                        self.on_block_clicked(i)
                    return

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.base_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, rect in enumerate(self.blocks):
            rx = rect.x0 * self.scale_x
            ry = rect.y0 * self.scale_y
            rw = (rect.x1 - rect.x0) * self.scale_x
            rh = (rect.y1 - rect.y0) * self.scale_y

            if i == self.selected_idx:
                painter.setPen(QPen(QColor("#388bfd"), 2.2))
                painter.setBrush(QBrush(QColor(56, 139, 253, 55)))
            else:
                painter.setPen(QPen(QColor("#94a3b8"), 0.9, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush(QColor(148, 163, 184, 15)))

            painter.drawRect(QRectF(rx, ry, rw, rh))

        painter.end()


class PDFContentEditorDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.tab_doc = getattr(self.main_window, 'get_current_tab_doc', lambda: None)()
        self.current_page_idx = getattr(self.tab_doc, 'current_page_idx', 0) if self.tab_doc else 0

        self.setWindowTitle(LanguageManager.tr("editor_dialog_title"))
        self.setWindowIcon(ModernIconFactory.icon_edit_content())
        self.resize(1060, 720)
        self.setMinimumSize(850, 560)
        self.setSizeGripEnabled(True)

        self.current_theme = getattr(self.main_window, 'current_theme', 'dark')
        self._init_ui()
        self._apply_dialog_style()
        apply_dialog_theme(self, self.main_window)
        self.load_data()

    def _apply_dialog_style(self):
        bg = "#1c1c1e"
        card_bg = "#2c2c2e"
        border = "#3a3a3c"
        accent = "#0a84ff"
        text = "#f5f5f7"

        if self.current_theme == "gray":
            bg = "#2b2d30"; card_bg = "#35383c"; border = "#444850"; accent = "#60a5fa"; text = "#f1f5f9"
        elif self.current_theme == "navy":
            bg = "#0f172a"; card_bg = "#1e293b"; border = "#334155"; accent = "#38bdf8"; text = "#e2e8f0"
        elif self.current_theme == "emerald":
            bg = "#091a14"; card_bg = "#112a21"; border = "#1a3d30"; accent = "#10b981"; text = "#ecfdf5"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {text}; }}
            QTabWidget::pane {{ border: 1px solid {border}; background-color: {card_bg}; border-radius: 6px; }}
            QTabBar::tab {{ background-color: {bg};  padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: 500; }}
            QTabBar::tab:selected {{ background-color: {card_bg};  border-bottom: 2.5px solid {accent}; font-weight: bold; }}
            QLabel {{ color: {text}; }}
            QListWidget {{ background-color: {bg}; color: {text}; border: 1.2px solid {border}; border-radius: 6px; }}
            QListWidget::item {{ padding: 8px; border-bottom: 1px solid {border}; }}
            QListWidget::item:selected {{ background-color: {border};  font-weight: bold; }}
            QTextEdit, QLineEdit, QComboBox, QSpinBox {{ background-color: {bg};  border: 1.2px solid {border}; border-radius: 5px; padding: 5px; }}
            QTextEdit:focus, QLineEdit:focus {{ border-color: {accent}; }}
            QFrame.card {{ background-color: {card_bg}; border: 1.2px solid {border}; border-radius: 8px; padding: 10px; }}
            QPushButton {{ background-color: {card_bg}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 6px 14px; font-weight: 500; }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton#PrimaryBtn {{ background-color: {accent};  font-weight: bold; border: none; }}
            QPushButton#DangerBtn {{   font-weight: bold; border: none; }}
            QPushButton#DangerBtn:hover {{  }}
            QScrollArea {{ border: 1px solid {border};  border-radius: 6px; }}
        """)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Üst Gezinti Çubuğu (Sayfa Değiştirici)
        top_bar = QFrame()
        top_bar.setProperty("class", "card")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(8, 5, 8, 5)

        self.btn_prev_page = QPushButton(f"◀ {LanguageManager.tr('prev_page')}")
        self.btn_prev_page.clicked.connect(self._prev_page)
        tb_lay.addWidget(self.btn_prev_page)

        tb_lay.addWidget(QLabel(LanguageManager.tr("page_prefix_label")))
        self.spn_page = ModernSpinBox(min_val=1, max_val=len(self.tab_doc.doc) if (self.tab_doc and self.tab_doc.doc) else 1, default_val=self.current_page_idx + 1, parent=self)
        self.spn_page.setFixedWidth(78)
        self.spn_page.valueChanged.connect(self._on_page_spin_changed)
        tb_lay.addWidget(self.spn_page)

        self.lbl_page_total = QLabel(f"/ {len(self.tab_doc.doc) if (self.tab_doc and self.tab_doc.doc) else 1}")
        tb_lay.addWidget(self.lbl_page_total)

        self.btn_next_page = QPushButton(f"{LanguageManager.tr('next_page')} ▶")
        self.btn_next_page.clicked.connect(self._next_page)
        tb_lay.addWidget(self.btn_next_page)

        tb_lay.addStretch()

        help_lbl = QLabel(LanguageManager.tr("content_editor_hint"))
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet(" font-size: 11px;")
        tb_lay.addWidget(help_lbl)

        root_layout.addWidget(top_bar)

        # Tab Widget
        self.tab_widget = QTabWidget(self)
        root_layout.addWidget(self.tab_widget, 1)

        # Sekme 1: Metinleri Doğrudan Düzenle & Sil
        self.tab_text = QWidget()
        self._build_text_tab(self.tab_text)
        self.tab_widget.addTab(self.tab_text, LanguageManager.tr("content_tab_text"))

        # Sekme 2: Gömülü Görselleri Düzenle
        self.tab_images = QWidget()
        self._build_images_tab(self.tab_images)
        self.tab_widget.addTab(self.tab_images, LanguageManager.tr("content_tab_images"))

        # Sekme 3: Metin Tanıma (OCR)
        self.tab_ocr = QWidget()
        self._build_ocr_tab(self.tab_ocr)
        self.tab_widget.addTab(self.tab_ocr, LanguageManager.tr("content_tab_ocr"))

        # Alt Butonlar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        btn_close = QPushButton(LanguageManager.tr("btn_cancel_settings"))
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        root_layout.addLayout(bottom_layout)

    # ----------------------------------------------------
    # SEKME 1: METİNLERİ DOĞRUDAN DÜZENLE
    # ----------------------------------------------------
    def _build_text_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Sol: Sayfa Görsel Blok Haritası
        canvas_box = QWidget()
        cb_lay = QVBoxLayout(canvas_box)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        lbl_block_title = QLabel(f"<b>{LanguageManager.tr('content_blocks_title')}</b>")
        lbl_block_title.setWordWrap(True)
        cb_lay.addWidget(lbl_block_title)

        self.scroll_canvas = QScrollArea()
        self.scroll_canvas.setWidgetResizable(True)
        self.canvas_text = VisualBlockCanvas()
        self.canvas_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_text.on_block_clicked = self._on_canvas_block_selected
        self.scroll_canvas.setWidget(self.canvas_text)
        cb_lay.addWidget(self.scroll_canvas, 1)
        splitter.addWidget(canvas_box)

        # 2. Orta: Metin Blokları Listesi
        list_box = QWidget()
        lb_lay = QVBoxLayout(list_box)
        lb_lay.setContentsMargins(0, 0, 0, 0)
        lb_lay.addWidget(QLabel(f"<b>{LanguageManager.tr('content_text_blocks')}</b>"))

        self.txt_filter_text = QLineEdit()
        self.txt_filter_text.setPlaceholderText(LanguageManager.tr("content_filter_placeholder"))
        self.txt_filter_text.textChanged.connect(self._filter_text_blocks)
        lb_lay.addWidget(self.txt_filter_text)

        self.list_texts = QListWidget()
        self.list_texts.currentRowChanged.connect(self._on_text_selected)
        lb_lay.addWidget(self.list_texts, 1)
        splitter.addWidget(list_box)

        # 3. Sağ: Düzenleme Paneli
        edit_panel = QFrame()
        edit_panel.setProperty("class", "card")
        ep_layout = QVBoxLayout(edit_panel)
        ep_layout.setSpacing(8)

        ep_layout.addWidget(QLabel(f"<b>{LanguageManager.tr('content_selected_text')}</b>"))
        self.edit_text_content = QTextEdit()
        self.edit_text_content.setPlaceholderText(LanguageManager.tr("content_selected_placeholder"))
        ep_layout.addWidget(self.edit_text_content, 1)

        # Font & Boyut Ayarları
        font_bar = QHBoxLayout()
        font_bar.addWidget(QLabel(LanguageManager.tr("size_label")))
        self.spn_font_size = ModernSpinBox(min_val=6, max_val=48, default_val=11, suffix=" pt", parent=self)
        self.spn_font_size.setFixedWidth(84)
        font_bar.addWidget(self.spn_font_size)

        font_bar.addWidget(QLabel(LanguageManager.tr("color_prefix_label")))
        self.btn_text_color = QPushButton("⬛ Siyah")
        self.chosen_color = (0, 0, 0)
        self.btn_text_color.clicked.connect(self._choose_text_color)
        font_bar.addWidget(self.btn_text_color)
        ep_layout.addLayout(font_bar)

        self.btn_replace_text = QPushButton(LanguageManager.tr("content_btn_replace_text_apply"))
        self.btn_replace_text.setObjectName("PrimaryBtn")
        self.btn_replace_text.clicked.connect(self.replace_selected_text)
        ep_layout.addWidget(self.btn_replace_text)

        self.btn_del_text = QPushButton(LanguageManager.tr("content_btn_del_text_whiteout"))
        self.btn_del_text.setObjectName("DangerBtn")
        self.btn_del_text.clicked.connect(self.delete_selected_text)
        ep_layout.addWidget(self.btn_del_text)

        ep_layout.addSpacing(6)
        self.btn_add_text = QPushButton(LanguageManager.tr("content_btn_add_text_page"))
        self.btn_add_text.clicked.connect(self.insert_custom_text)
        ep_layout.addWidget(self.btn_add_text)

        splitter.addWidget(edit_panel)
        splitter.setSizes([380, 260, 310])
        layout.addWidget(splitter)

    def _choose_text_color(self):
        c = QColorDialog.getColor(QColor(0, 0, 0), self, "Metin Rengi Seç")
        if c.isValid():
            self.chosen_color = (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)
            self.btn_text_color.setText(c.name().upper())
            self.btn_text_color.setStyleSheet(f"background-color: {c.name()}; color: {'#000' if c.lightness() > 130 else '#fff'}; font-weight: bold;")

    # ----------------------------------------------------
    # SEKME 2: GÖMÜLÜ GÖRSELLER
    # ----------------------------------------------------
    def _build_images_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.lbl_img_count = QLabel(LanguageManager.tr("content_scanning_images"))
        layout.addWidget(self.lbl_img_count)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol: Resim Listesi
        self.list_images = QListWidget()
        self.list_images.setIconSize(QSize(96, 96))
        self.list_images.currentRowChanged.connect(self._on_image_selected)
        splitter.addWidget(self.list_images)

        # Sağ: Detay ve Eylemler
        detail_panel = QFrame()
        detail_panel.setProperty("class", "card")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setSpacing(10)

        self.lbl_img_preview = QLabel()
        self.lbl_img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img_preview.setMinimumSize(180, 180)
        self.lbl_img_preview.setStyleSheet(" border-radius: 6px;")
        detail_layout.addWidget(self.lbl_img_preview)

        self.lbl_img_info = QLabel("—")
        self.lbl_img_info.setWordWrap(True)
        self.lbl_img_info.setStyleSheet("font-size: 12px; ")
        detail_layout.addWidget(self.lbl_img_info)

        detail_layout.addStretch()

        self.btn_replace_img = QPushButton(LanguageManager.tr("content_btn_replace_img_dialog"))
        self.btn_replace_img.setObjectName("PrimaryBtn")
        self.btn_replace_img.clicked.connect(self.replace_selected_image)
        detail_layout.addWidget(self.btn_replace_img)

        self.btn_del_img = QPushButton(LanguageManager.tr("content_btn_del_img_dialog"))
        self.btn_del_img.setObjectName("DangerBtn")
        self.btn_del_img.clicked.connect(self.delete_selected_image)
        detail_layout.addWidget(self.btn_del_img)

        self.btn_export_img = QPushButton(LanguageManager.tr("content_btn_export_img_dialog"))
        self.btn_export_img.clicked.connect(self.export_selected_image)
        detail_layout.addWidget(self.btn_export_img)

        self.btn_add_img = QPushButton(LanguageManager.tr("content_btn_add_img_dialog"))
        self.btn_add_img.clicked.connect(self.insert_new_image)
        detail_layout.addWidget(self.btn_add_img)

        splitter.addWidget(detail_panel)
        splitter.setSizes([450, 350])
        layout.addWidget(splitter)

    # ----------------------------------------------------
    # SEKME 3: METİN TANIMA (OCR)
    # ----------------------------------------------------
    def _build_ocr_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self.btn_run_ocr = QPushButton(LanguageManager.tr("content_btn_ocr_page"))
        self.btn_run_ocr.setObjectName("PrimaryBtn")
        self.btn_run_ocr.clicked.connect(self.run_ocr_recognition)
        top_bar.addWidget(self.btn_run_ocr)

        self.lbl_ocr_status = QLabel(LanguageManager.tr("content_ocr_ready"))
        self.lbl_ocr_status.setStyleSheet(" font-size: 12px;")
        top_bar.addWidget(self.lbl_ocr_status)
        top_bar.addStretch()

        self.btn_copy_ocr = QPushButton(LanguageManager.tr("content_btn_copy_ocr_btn"))
        self.btn_copy_ocr.clicked.connect(self.copy_ocr_text)
        top_bar.addWidget(self.btn_copy_ocr)

        self.btn_save_ocr = QPushButton(LanguageManager.tr("content_btn_save_ocr_txt"))
        self.btn_save_ocr.clicked.connect(self.save_ocr_to_file)
        top_bar.addWidget(self.btn_save_ocr)

        layout.addLayout(top_bar)

        self.txt_ocr_result = QTextEdit()
        self.txt_ocr_result.setFont(QFont("Consolas", 10))
        self.txt_ocr_result.setPlaceholderText("Tanınan metin burada görüntülenecektir...")
        layout.addWidget(self.txt_ocr_result)

    # ----------------------------------------------------
    # SAYFA GEZİNTİSİ
    # ----------------------------------------------------
    def _prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.spn_page.setValue(self.current_page_idx + 1)

    def _next_page(self):
        if self.tab_doc and self.tab_doc.doc and self.current_page_idx + 1 < len(self.tab_doc.doc):
            self.current_page_idx += 1
            self.spn_page.setValue(self.current_page_idx + 1)

    def _on_page_spin_changed(self, val):
        self.current_page_idx = val - 1
        self.load_data()

    # ----------------------------------------------------
    # VERİ YÜKLEME
    # ----------------------------------------------------
    def load_data(self):
        if not self.tab_doc or not self.tab_doc.doc:
            self.lbl_img_count.setText("Açık belge bulunamadı.")
            return

        total_pages = len(self.tab_doc.doc)
        if self.current_page_idx >= total_pages:
            self.current_page_idx = max(0, total_pages - 1)

        self.lbl_page_total.setText(f"/ {total_pages}")
        page = self.tab_doc.doc[self.current_page_idx]

        # 1. Resimleri Yükle
        self.images_data = []
        self.list_images.clear()
        img_list = page.get_images()
        self.lbl_img_count.setText(f"Bu sayfada toplam {len(img_list)} görsel bulundu.")

        for i, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                base_img = self.tab_doc.doc.extract_image(xref)
                img_bytes = base_img["image"]
                ext = base_img.get("ext", "png")
                w = base_img.get("width", 0)
                h = base_img.get("height", 0)

                qimg = QImage.fromData(img_bytes)
                pixmap = QPixmap.fromImage(qimg)
                icon = QIcon(pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

                rects = page.get_image_rects(xref)
                rect = rects[0] if rects else fitz.Rect()

                item_data = {
                    "xref": xref, "index": i + 1, "ext": ext,
                    "width": w, "height": h, "rect": rect,
                    "bytes": img_bytes, "pixmap": pixmap
                }
                self.images_data.append(item_data)

                item = QListWidgetItem(icon, f"Görsel #{i+1} ({ext.upper()} - {w}x{h} px)")
                self.list_images.addItem(item)
            except Exception as e:
                print("Görsel yüklenemedi:", e)

        if self.images_data:
            self.list_images.setCurrentRow(0)

        # 2. Metin Bloklarını ve Sayfa Renderını Yükle
        self.text_blocks_data = []
        self.list_texts.clear()
        blocks = page.get_text("blocks")
        rect_list = []

        for b in blocks:
            if len(b) >= 7 and b[6] == 0:
                text = b[4].strip()
                if text:
                    rect = fitz.Rect(b[0], b[1], b[2], b[3])
                    rect_list.append(rect)
                    data = {"rect": rect, "text": text, "block_no": b[5]}
                    self.text_blocks_data.append(data)
                    preview_txt = text.replace('\n', ' ')
                    item = QListWidgetItem(f"[{b[5]}] {preview_txt[:55]}..." if len(preview_txt) > 55 else f"[{b[5]}] {preview_txt}")
                    self.list_texts.addItem(item)

        # Sayfa Görsel Haritasını çiz
        mat = fitz.Matrix(1.2, 1.2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        self.canvas_text.set_page_pixmap(QPixmap.fromImage(qimg), page.rect.width, page.rect.height, rect_list, 0 if rect_list else -1)

        if self.text_blocks_data:
            self.list_texts.setCurrentRow(0)

    def _on_canvas_block_selected(self, idx):
        if 0 <= idx < self.list_texts.count():
            self.list_texts.setCurrentRow(idx)

    def _on_image_selected(self, row):
        if 0 <= row < len(self.images_data):
            d = self.images_data[row]
            pix = d["pixmap"]
            self.lbl_img_preview.setPixmap(pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.lbl_img_info.setText(
                f"<b>Format:</b> {d['ext'].upper()}<br>"
                f"<b>Çözünürlük:</b> {d['width']} x {d['height']} px<br>"
                f"<b>Referans (xref):</b> {d['xref']}<br>"
                f"<b>Konum:</b> x={d['rect'].x0:.1f}, y={d['rect'].y0:.1f}"
            )
        else:
            self.lbl_img_preview.clear()
            self.lbl_img_info.setText("—")

    def _on_text_selected(self, row):
        if 0 <= row < len(self.text_blocks_data):
            self.edit_text_content.setPlainText(self.text_blocks_data[row]["text"])
            self.canvas_text.set_selected_idx(row)
        else:
            self.edit_text_content.clear()
            self.canvas_text.set_selected_idx(-1)

    def _filter_text_blocks(self, query):
        query = query.lower().strip()
        for i in range(self.list_texts.count()):
            item = self.list_texts.item(i)
            item.setHidden(query not in item.text().lower())

    # ----------------------------------------------------
    # METİN İŞLEMLERİ
    # ----------------------------------------------------
    @staticmethod
    def _get_unicode_font_path():
        for fp in [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]:
            if os.path.isfile(fp):
                return fp
        return None

    def _find_fitting_box(self, page, rect, text, target_fs=11.0, fontfile=None):
        """Metnin insert_textbox içinde kırpılmadan veya kaybolmadan sığmasını sağlayan kutu ve punto hesaplayıcı."""
        fontname = "f_test" if fontfile else "helv"
        tmp_doc = fitz.open()
        tmp_page = tmp_doc.new_page(width=max(800.0, page.rect.width), height=max(1200.0, page.rect.height))

        max_page_h = max(200.0, page.rect.height - rect.y0 - 15)
        max_page_w = max(200.0, page.rect.width - rect.x0 - 15)

        # 1. Adım: Hedef punto ile kutu yüksekliğini genişleterek dene
        for h_mult in [1.0, 1.2, 1.5, 2.0, 3.0, 4.0]:
            h = min(max_page_h, rect.height * h_mult)
            w = min(max_page_w, max(rect.width, rect.width * 1.05))
            test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
            res = tmp_page.insert_textbox(test_r, text, fontsize=target_fs, fontfile=fontfile, fontname=fontname)
            if res >= 0:
                tmp_doc.close()
                return test_r, target_fs
            tmp_page.clean_contents()

        # 2. Adım: Puntoyu kademeli küçülterek dene
        for fs in [target_fs * 0.9, target_fs * 0.8, target_fs * 0.7, 8.0, 7.0]:
            for h_mult in [1.0, 1.3, 1.8, 2.5, 3.5]:
                h = min(max_page_h, rect.height * h_mult)
                w = min(max_page_w, max(rect.width, rect.width * 1.05))
                test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
                res = tmp_page.insert_textbox(test_r, text, fontsize=fs, fontfile=fontfile, fontname=fontname)
                if res >= 0:
                    tmp_doc.close()
                    return test_r, fs
                tmp_page.clean_contents()

        tmp_doc.close()
        fallback_r = fitz.Rect(rect.x0, rect.y0, rect.x1, min(max_page_h, rect.y0 + rect.height * 2.5))
        return fallback_r, max(7.0, target_fs * 0.7)

    def replace_selected_text(self):
        row = self.list_texts.currentRow()
        if not (0 <= row < len(self.text_blocks_data)):
            QMessageBox.warning(self, "Uyarı", "Lütfen önce düzenlemek istediğiniz bir metin bloğu seçin.")
            return

        new_text = self.edit_text_content.toPlainText().strip()
        if not new_text:
            self.delete_selected_text()
            return

        d = self.text_blocks_data[row]
        page = self.tab_doc.doc[self.current_page_idx]
        rect = fitz.Rect(d["rect"])

        try:
            # 1. Eski metin alanını kalıcı olarak temizle (redact)
            page.add_redact_annot(rect)
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                text=fitz.PDF_REDACT_TEXT_REMOVE
            )

            # 2. Yeni metni alana yaz (Unicode & Türkçe karakter uyumlu)
            fs = float(self.spn_font_size.value())
            col = self.chosen_color
            fontfile = self._get_unicode_font_path()

            # Metnin sığmasını garanti altına almak için akıllı boyut/kutu belirleme
            fit_rect, fit_fs = self._find_fitting_box(page, rect, new_text, target_fs=fs, fontfile=fontfile)

            res = page.insert_textbox(
                fit_rect, new_text,
                fontsize=fit_fs,
                fontfile=fontfile,
                fontname="arial_u" if fontfile else "helv",
                color=col
            )
            if res < 0:
                # Son çare: doğrudan koordinata yaz
                page.insert_text(
                    fitz.Point(rect.x0, rect.y0 + fit_fs),
                    new_text,
                    fontsize=fit_fs,
                    fontfile=fontfile,
                    fontname="arial_u" if fontfile else "helv",
                    color=col
                )

            self._commit_and_reload("Metin başarıyla güncellendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Metin güncellenirken hata oluştu:\n{e}")

    def delete_selected_text(self):
        row = self.list_texts.currentRow()
        if not (0 <= row < len(self.text_blocks_data)):
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek bir metin seçin.")
            return

        reply = QMessageBox.question(
            self, "Metni Sil", "Seçili metin alandan kalıcı olarak silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        d = self.text_blocks_data[row]
        page = self.tab_doc.doc[self.current_page_idx]

        try:
            page.add_redact_annot(d["rect"])
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                text=fitz.PDF_REDACT_TEXT_REMOVE
            )
            self._commit_and_reload("Metin başarıyla silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Metin silinemedi:\n{e}")

    def insert_custom_text(self):
        text = self.edit_text_content.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Uyarı", "Lütfen eklenecek metni sağdaki kutucuğa yazın.")
            return

        page = self.tab_doc.doc[self.current_page_idx]
        try:
            fs = float(self.spn_font_size.value())
            col = self.chosen_color
            fontfile = self._get_unicode_font_path()
            page.insert_text(
                fitz.Point(72, 100), text,
                fontsize=fs,
                fontfile=fontfile,
                fontname="arial_u" if fontfile else "helv",
                color=col
            )
            self._commit_and_reload("Yeni metin sayfaya başarıyla eklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Metin eklenemedi:\n{e}")

    # ----------------------------------------------------
    # GÖRSEL İŞLEMLERİ
    # ----------------------------------------------------
    def replace_selected_image(self):
        row = self.list_images.currentRow()
        if not (0 <= row < len(self.images_data)):
            QMessageBox.warning(self, "Uyarı", "Lütfen değiştirilecek bir görsel seçin.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Yeni Görsel Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path or not os.path.isfile(file_path):
            return

        d = self.images_data[row]
        page = self.tab_doc.doc[self.current_page_idx]

        try:
            rect = d["rect"] if (d["rect"] and not d["rect"].is_empty) else fitz.Rect(100, 100, 300, 300)
            page.delete_image(d["xref"])
            page.add_redact_annot(rect)
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
            page.insert_image(rect, filename=file_path)

            self._commit_and_reload("Görsel başarıyla değiştirildi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Görsel değiştirilemedi:\n{e}")

    def delete_selected_image(self):
        row = self.list_images.currentRow()
        if not (0 <= row < len(self.images_data)):
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek bir görsel seçin.")
            return

        reply = QMessageBox.question(
            self, "Görseli Sil", "Seçili görsel PDF'ten kalıcı olarak silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        d = self.images_data[row]
        page = self.tab_doc.doc[self.current_page_idx]

        try:
            page.delete_image(d["xref"])
            if d["rect"] and not d["rect"].is_empty:
                page.add_redact_annot(d["rect"])
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
            self._commit_and_reload("Görsel başarıyla silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Görsel silinemedi:\n{e}")

    def export_selected_image(self):
        row = self.list_images.currentRow()
        if not (0 <= row < len(self.images_data)):
            return
        d = self.images_data[row]
        ext = d["ext"].lower()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Görseli Kaydet", f"gorsel_s{self.current_page_idx+1}_{d['index']}.{ext}", f"{ext.upper()} (*.{ext})"
        )
        if save_path:
            with open(save_path, "wb") as f:
                f.write(d["bytes"])
            QMessageBox.information(self, "Başarılı", f"Görsel kaydedildi:\n{save_path}")

    def insert_new_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Eklenecek Görseli Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path or not os.path.isfile(file_path):
            return

        page = self.tab_doc.doc[self.current_page_idx]
        rect = fitz.Rect(72, 72, 72 + 200, 72 + 150)
        try:
            page.insert_image(rect, filename=file_path)
            self._commit_and_reload("Yeni görsel sayfaya eklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Görsel eklenemedi:\n{e}")

    # ----------------------------------------------------
    # OCR İŞLEMİ
    # ----------------------------------------------------
    def run_ocr_recognition(self):
        if not self.tab_doc or not self.tab_doc.doc:
            return

        page = self.tab_doc.doc[self.current_page_idx]
        self.lbl_ocr_status.setText("Metinler taranıyor ve tanınıyor...")
        self.txt_ocr_result.clear()

        # Önce dijital metni dene
        full_text = page.get_text("text").strip()

        # Eğer taranmış sayfa ise RapidOCR kullan
        if not full_text:
            try:
                from rapidocr_onnxruntime import RapidOCR
                engine = RapidOCR()
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
                result, _ = engine(img_arr)
                if result:
                    lines = [line[1] for line in result if len(line) > 1 and line[1]]
                    full_text = "\n".join(lines)
            except Exception as e:
                print("RapidOCR hatası:", e)

        if not full_text:
            full_text = "Sayfada metin tespit edilemedi."

        self.txt_ocr_result.setPlainText(full_text)
        words = len(full_text.split())
        self.lbl_ocr_status.setText(f"Metin tanıma tamamlandı ({words} kelime).")

    def copy_ocr_text(self):
        txt = self.txt_ocr_result.toPlainText()
        if txt:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(txt)
            QMessageBox.information(self, "Kopyalandı", "Metin panoya kopyalandı.")

    def save_ocr_to_file(self):
        txt = self.txt_ocr_result.toPlainText()
        if not txt:
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek metin bulunamadı.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Metni Kaydet", "taninan_metin.txt", "Metin Dosyası (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            QMessageBox.information(self, "Başarılı", f"Metin dosyası kaydedildi:\n{path}")

    # ----------------------------------------------------
    # KAYDETME VE GÜNCELLEME
    # ----------------------------------------------------
    def _commit_and_reload(self, msg=None):
        if self.tab_doc and self.tab_doc.doc:
            page_idx = self.current_page_idx

            # 1. Ana penceredeki (arkadaki belgedeki) sayfa pixmap'ini ANLIK olarak yeniden render et
            if hasattr(self.tab_doc, 'page_positions') and page_idx in self.tab_doc.page_positions:
                try:
                    pinfo = self.tab_doc.page_positions[page_idx]
                    target_scale = self.tab_doc.base_render_dpi * self.tab_doc.zoom_level
                    mat = fitz.Matrix(target_scale, target_scale)
                    pix = self.tab_doc.doc[page_idx].get_pixmap(matrix=mat)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    pinfo['item'].setPixmap(QPixmap.fromImage(qimg))
                    pinfo['item'].setScale(1.0 / self.tab_doc.zoom_level)
                    pinfo['rendered_zoom'] = self.tab_doc.zoom_level

                    if hasattr(self.tab_doc, 'scene') and self.tab_doc.scene:
                        self.tab_doc.scene.update()
                    if hasattr(self.tab_doc, 'view') and self.tab_doc.view:
                        self.tab_doc.view.viewport().update()
                except Exception as e:
                    print("Anlık sayfa render hatası:", e)

            if hasattr(self.tab_doc, 'rerender_visible_pages'):
                try:
                    self.tab_doc.rerender_visible_pages(force=True)
                except Exception:
                    pass

            self.tab_doc.is_modified = True
            if hasattr(self.tab_doc, 'update_tab_title'):
                self.tab_doc.update_tab_title()

            # 2. Sol kenardaki sayfa küçük resimlerini (thumbnails) de anlık güncelle
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                try:
                    if hasattr(self.main_window.thumbnails_dock, 'update_page_thumbnail'):
                        self.main_window.thumbnails_dock.update_page_thumbnail(page_idx)
                    elif hasattr(self.main_window.thumbnails_dock, 'render_thumbnails'):
                        self.main_window.thumbnails_dock.render_thumbnails()
                except Exception:
                    pass

        # 3. Diyalog penceresindeki önizleme canvasını ve metin bloklarını da güncelle
        self.load_data()
        if msg:
            QMessageBox.information(self, "Bilgi", msg)
