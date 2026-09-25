"""
AuraPDF - Kalıcı Karartma & Hassas Veri Temizleme (PDF Redaction & Sanitization)
================================================================================
Hassas verileri (T.C. Kimlik, Telefon, E-Posta, IBAN/Kart ve özel kelimeler)
PDF belgesinden fiziksel ve geri alınamaz biçimde kazıyan güvenlik aracı.
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTabWidget, QWidget, QFrame, QSplitter,
    QScrollArea, QSpinBox, QCheckBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar,
    QComboBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QBrush

import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet
from src.ui.icons import ModernIconFactory


class RedactPreviewLabel(QLabel):
    """Kullanıcının fareyle serbest dikdörtgen çizip alan karartabilmesini sağlayan etiket."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.start_pos = None
        self.current_pos = None
        self.is_drawing = False
        self.manual_rects = []  # [(x0, y0, x1, y1) in page coordinates]
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.base_pixmap = None

    def set_page_pixmap(self, pixmap, page_w, page_h):
        self.base_pixmap = pixmap
        self.setPixmap(pixmap)
        if pixmap.width() > 0 and pixmap.height() > 0:
            self.scale_x = page_w / pixmap.width()
            self.scale_y = page_h / pixmap.height()
        self.manual_rects.clear()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.base_pixmap:
            self.start_pos = event.position().toPoint()
            self.current_pos = self.start_pos
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.current_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            p1 = self.start_pos
            p2 = event.position().toPoint()
            if p1 and p2:
                x0 = min(p1.x(), p2.x()) * self.scale_x
                y0 = min(p1.y(), p2.y()) * self.scale_y
                x1 = max(p1.x(), p2.x()) * self.scale_x
                y1 = max(p1.y(), p2.y()) * self.scale_y
                if (x1 - x0) > 5 and (y1 - y0) > 5:
                    self.manual_rects.append((x0, y0, x1, y1))
            self.start_pos = None
            self.current_pos = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.base_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Daha önce eklenen manuel alanlar
        for (x0, y0, x1, y1) in self.manual_rects:
            rx0 = x0 / self.scale_x
            ry0 = y0 / self.scale_y
            rw = (x1 - x0) / self.scale_x
            rh = (y1 - y0) / self.scale_y
            painter.setPen(QPen(QColor("#ef4444"), 2))
            painter.setBrush(QBrush(QColor(239, 68, 68, 120)))
            painter.drawRect(QRectF(rx0, ry0, rw, rh))

        # Çizilmekte olan dikdörtgen
        if self.is_drawing and self.start_pos and self.current_pos:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())
            painter.setPen(QPen(QColor("#38bdf8"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(56, 189, 248, 80)))
            painter.drawRect(QRectF(x, y, w, h))

        painter.end()


class PDFRedactionDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle(LanguageManager.tr("redact_title"))
        self.setWindowIcon(ModernIconFactory.icon_redact())
        self.resize(1050, 720)
        self.setMinimumSize(850, 560)
        self.setSizeGripEnabled(True)

        self.current_theme = getattr(self.main_window, 'current_theme', 'dark')

        self.tab_doc = getattr(self.main_window, 'get_current_tab_doc', lambda: None)()
        self.doc = None
        self.file_path = ""
        self.current_page = 0
        self.detected_items = []  # [{page, text, rect, type, checked}]

        if self.tab_doc and getattr(self.tab_doc, 'doc', None):
            self.doc = self.tab_doc.doc
            self.file_path = getattr(self.tab_doc, 'file_path', "")
            self.current_page = getattr(self.tab_doc, 'current_page_idx', 0)

        self._apply_style()
        self._init_ui()

        if self.doc:
            self._render_current_page()
            self._auto_detect_sensitive_data()

    def _apply_style(self):
        bg = "#1c1c1e"
        card_bg = "#2c2c2e"
        border = "#3a3a3c"
        accent = "#ff3b30"
        text = "#f5f5f7"

        if self.current_theme == "gray":
            bg = "#2b2d30"; card_bg = "#35383c"; border = "#444850"; accent = "#f87171"; text = "#f1f5f9"
        elif self.current_theme == "navy":
            bg = "#0f172a"; card_bg = "#1e293b"; border = "#334155"; accent = "#38bdf8"; text = "#e2e8f0"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {text}; }}
            QTabWidget::pane {{ border: 1px solid {border}; background-color: {card_bg}; border-radius: 6px; }}
            QTabBar::tab {{ background-color: {bg};  padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: 500; }}
            QTabBar::tab:selected {{ background-color: {card_bg};  border-bottom: 2.5px solid {accent}; font-weight: bold; }}
            QLabel {{ color: {text}; }}
            QFrame.card {{ background-color: {card_bg}; border: 1.2px solid {border}; border-radius: 8px; padding: 10px; }}
            QPushButton {{ background-color: {card_bg}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 7px 15px; font-weight: 500; }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton#DangerBtn {{   font-weight: bold; border: none; }}
            QPushButton#DangerBtn:hover {{  }}
            QPushButton#PrimaryBtn {{   font-weight: bold; border: none; }}
            QLineEdit, QComboBox, QSpinBox {{ background-color: {bg};  border: 1.2px solid {border}; border-radius: 5px; padding: 5px; }}
            QTableWidget {{ background-color: {bg}; color: {text}; border: 1px solid {border}; gridline-color: {border}; border-radius: 6px; }}
            QTableWidget::item:selected {{   }}
            QHeaderView::section {{ background-color: {card_bg};  border: 1px solid {border}; padding: 4px; font-weight: bold; }}
            QScrollArea {{ border: 1px solid {border};  border-radius: 6px; }}
        """)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Üst Başlık & Açıklama
        header_card = QFrame()
        header_card.setProperty("class", "card")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(8, 6, 8, 6)

        info_icon = QLabel("🛡️")
        info_icon.setStyleSheet("font-size: 24px;")
        h_layout.addWidget(info_icon)

        v_box = QVBoxLayout()
        lbl_title = QLabel(f"<b>{LanguageManager.tr('redact_banner_title')}</b>")
        lbl_title.setStyleSheet("font-size: 13px; ")
        v_box.addWidget(lbl_title)
        lbl_sub = QLabel(LanguageManager.tr("redact_banner_sub"))
        lbl_sub.setStyleSheet("font-size: 11px; ")
        v_box.addWidget(lbl_sub)
        h_layout.addLayout(v_box, 1)

        root.addWidget(header_card)

        # Ana Bölücü (Sol Ayarlar & Algılama, Sağ Canlı Önizleme)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------------- SOL PANEL: AYARLAR VE LİSTE ----------------
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(10)

        self.tabs = QTabWidget()
        lp_layout.addWidget(self.tabs, 1)

        # Sekme 1: Otomatik Veri Algılama
        tab_auto = QWidget()
        self._build_auto_tab(tab_auto)
        self.tabs.addTab(tab_auto, LanguageManager.tr("redact_tab_auto"))

        # Sekme 2: Karartma Stili ve Ayarları
        tab_style = QWidget()
        self._build_style_tab(tab_style)
        self.tabs.addTab(tab_style, LanguageManager.tr("redact_tab_appearance"))

        # Sekme 3: Belge Üstveri Temizliği
        tab_clean = QWidget()
        self._build_sanitize_tab(tab_clean)
        self.tabs.addTab(tab_clean, LanguageManager.tr("redact_tab_sanitize"))

        splitter.addWidget(left_panel)

        # ---------------- SAĞ PANEL: CANLI ÖNİZLEME ----------------
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(8)

        # Sayfa Gezintisi
        nav_box = QHBoxLayout()
        btn_prev = QPushButton(f"◀ {LanguageManager.tr('prev_page')}")
        btn_prev.clicked.connect(self._prev_page)
        nav_box.addWidget(btn_prev)

        self.lbl_page_info = QLabel(LanguageManager.tr("page_info_format", current=self.current_page + 1, total=len(self.doc) if self.doc else 1))
        self.lbl_page_info.setStyleSheet("font-weight: bold; ")
        nav_box.addWidget(self.lbl_page_info)

        btn_next = QPushButton(f"{LanguageManager.tr('next_page')} ▶")
        btn_next.clicked.connect(self._next_page)
        nav_box.addWidget(btn_next)

        nav_box.addStretch()

        btn_clear_manual = QPushButton(LanguageManager.tr("redact_clear_manual"))
        btn_clear_manual.clicked.connect(self._clear_manual_rects)
        nav_box.addWidget(btn_clear_manual)

        rp_layout.addLayout(nav_box)

        hint_lbl = QLabel(LanguageManager.tr("redact_hint"))
        hint_lbl.setStyleSheet(" font-size: 11px;")
        rp_layout.addWidget(hint_lbl)

        self.scroll_preview = QScrollArea()
        self.scroll_preview.setWidgetResizable(True)
        self.preview_label = RedactPreviewLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_preview.setWidget(self.preview_label)
        rp_layout.addWidget(self.scroll_preview, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([450, 550])

        root.addWidget(splitter, 1)

        # ---------------- ALT EYLEM BUTONLARI ----------------
        bottom_bar = QHBoxLayout()

        self.btn_apply = QPushButton(LanguageManager.tr("redact_btn_apply"))
        self.btn_apply.setObjectName("DangerBtn")
        self.btn_apply.clicked.connect(self._apply_redactions_current)
        bottom_bar.addWidget(self.btn_apply)

        self.btn_save_as = QPushButton(LanguageManager.tr("redact_btn_save_as"))
        self.btn_save_as.setObjectName("PrimaryBtn")
        self.btn_save_as.clicked.connect(self._apply_redactions_save_as)
        bottom_bar.addWidget(self.btn_save_as)

        bottom_bar.addStretch()

        btn_cancel = QPushButton(LanguageManager.tr("btn_cancel_settings"))
        btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cancel)

        root.addLayout(bottom_bar)

    # -------------------------------------------------------------------
    # SEKME 1: OTOMATİK VERİ ALGILAMA
    # -------------------------------------------------------------------
    def _build_auto_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        grp = QFrame()
        grp.setProperty("class", "card")
        g_lay = QVBoxLayout(grp)
        g_lay.setSpacing(6)

        self.chk_tc = QCheckBox(LanguageManager.tr("redact_tc"))
        self.chk_tc.setChecked(True)
        g_lay.addWidget(self.chk_tc)

        self.chk_phone = QCheckBox(LanguageManager.tr("redact_phone"))
        self.chk_phone.setChecked(True)
        g_lay.addWidget(self.chk_phone)

        self.chk_email = QCheckBox(LanguageManager.tr("redact_email"))
        self.chk_email.setChecked(True)
        g_lay.addWidget(self.chk_email)

        self.chk_iban = QCheckBox(LanguageManager.tr("redact_iban"))
        self.chk_iban.setChecked(True)
        g_lay.addWidget(self.chk_iban)

        # Özel Arama
        h_custom = QHBoxLayout()
        h_custom.addWidget(QLabel(LanguageManager.tr("redact_custom_word")))
        self.txt_custom_search = QLineEdit()
        self.txt_custom_search.setPlaceholderText(LanguageManager.tr("redact_custom_placeholder"))
        h_custom.addWidget(self.txt_custom_search)
        g_lay.addLayout(h_custom)

        # Kapsam
        scope_lay = QHBoxLayout()
        scope_lay.addWidget(QLabel(LanguageManager.tr("redact_scope")))
        self.rb_all_pages = QRadioButton(LanguageManager.tr("redact_all_pages"))
        self.rb_all_pages.setChecked(True)
        self.rb_curr_page = QRadioButton(LanguageManager.tr("redact_curr_page"))
        scope_group = QButtonGroup(self)
        scope_group.addButton(self.rb_all_pages)
        scope_group.addButton(self.rb_curr_page)
        scope_lay.addWidget(self.rb_all_pages)
        scope_lay.addWidget(self.rb_curr_page)
        g_lay.addLayout(scope_lay)

        btn_rescan = QPushButton(LanguageManager.tr("redact_scan_sensitive"))
        btn_rescan.setObjectName("PrimaryBtn")
        btn_rescan.clicked.connect(self._auto_detect_sensitive_data)
        g_lay.addWidget(btn_rescan)

        layout.addWidget(grp)

        self.lbl_found_count = QLabel(LanguageManager.tr("redact_found_count", count=0))
        self.lbl_found_count.setStyleSheet("font-weight: bold; ")
        layout.addWidget(self.lbl_found_count)

        self.tbl_items = QTableWidget(0, 4)
        self.tbl_items.setHorizontalHeaderLabels([LanguageManager.tr("tbl_select"), LanguageManager.tr("tbl_page"), LanguageManager.tr("tbl_category"), LanguageManager.tr("tbl_text_data")])
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl_items.cellClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tbl_items, 1)

    # -------------------------------------------------------------------
    # SEKME 2: GÖRÜNÜM & DAMGA
    # -------------------------------------------------------------------
    def _build_style_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(10)

        c_lay.addWidget(QLabel(f"<b>{LanguageManager.tr('redact_color_label')}</b>"))
        self.cmb_color = QComboBox()
        self.cmb_color.addItem(LanguageManager.tr("redact_col_black"), (0, 0, 0))
        self.cmb_color.addItem(LanguageManager.tr("redact_col_white"), (1, 1, 1))
        self.cmb_color.addItem(LanguageManager.tr("redact_col_gray"), (0.5, 0.5, 0.5))
        self.cmb_color.addItem(LanguageManager.tr("redact_col_red"), (0.8, 0.1, 0.1))
        c_lay.addWidget(self.cmb_color)

        c_lay.addSpacing(6)
        c_lay.addWidget(QLabel(f"<b>{LanguageManager.tr('redact_overlay_label')}</b>"))
        self.cmb_overlay_text = QComboBox()
        self.cmb_overlay_text.setEditable(True)
        self.cmb_overlay_text.addItem("")  # Boş
        self.cmb_overlay_text.addItem("[GİZLENDİ]")
        self.cmb_overlay_text.addItem("[SANSÜRLENDİ]")
        self.cmb_overlay_text.addItem("[REDACTED]")
        self.cmb_overlay_text.addItem("[KVKK KAPSAMINDA GİZLİDİR]")
        c_lay.addWidget(self.cmb_overlay_text)

        c_lay.addSpacing(6)
        desc = QLabel(LanguageManager.tr("redact_color_stamp_desc"))
        desc.setStyleSheet(" font-size: 11px;")
        c_lay.addWidget(desc)

        c_lay.addStretch()
        layout.addWidget(card)

    # -------------------------------------------------------------------
    # SEKME 3: BELGE ÜSTVERİ & EK TEMİZLİĞİ (SANITIZATION)
    # -------------------------------------------------------------------
    def _build_sanitize_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        card = QFrame()
        card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(10)

        c_lay.addWidget(QLabel(f"<b>{LanguageManager.tr('redact_clean_title')}</b>"))
        self.chk_clean_meta = QCheckBox(LanguageManager.tr("redact_clean_meta"))
        self.chk_clean_meta.setChecked(True)
        c_lay.addWidget(self.chk_clean_meta)

        self.chk_clean_attachments = QCheckBox(LanguageManager.tr("redact_clean_attachments"))
        self.chk_clean_attachments.setChecked(True)
        c_lay.addWidget(self.chk_clean_attachments)

        self.chk_clean_links = QCheckBox(LanguageManager.tr("redact_clean_links"))
        c_lay.addWidget(self.chk_clean_links)

        c_lay.addSpacing(8)
        warning = QLabel(LanguageManager.tr("redact_clean_warning"))
        warning.setStyleSheet(" font-size: 11px;")
        c_lay.addWidget(warning)

        c_lay.addStretch()
        layout.addWidget(card)

    # -------------------------------------------------------------------
    # SAYFA VE GÖRSELLEŞTİRME
    # -------------------------------------------------------------------
    def _render_current_page(self):
        if not self.doc or len(self.doc) == 0:
            return

        total = len(self.doc)
        self.lbl_page_info.setText(f"Sayfa: {self.current_page + 1} / {total}")

        page = self.doc[self.current_page]
        rect = page.rect
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        self.preview_label.set_page_pixmap(QPixmap.fromImage(qimg), rect.width, rect.height)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.doc and self.current_page + 1 < len(self.doc):
            self.current_page += 1
            self._render_current_page()

    def _clear_manual_rects(self):
        self.preview_label.manual_rects.clear()
        self.preview_label.update()

    # -------------------------------------------------------------------
    # HASSAS VERİ ARAMA (SCAN)
    # -------------------------------------------------------------------
    def _auto_detect_sensitive_data(self):
        if not self.doc:
            return

        self.detected_items.clear()
        self.tbl_items.setRowCount(0)

        # Regex kalıpları
        PATTERNS = []
        if self.chk_tc.isChecked():
            PATTERNS.append(("TC Kimlik", re.compile(r'\b[1-9]\d{10}\b')))
        if self.chk_phone.isChecked():
            PATTERNS.append(("Telefon", re.compile(r'(?:\+90|0)?\s*[5]\d{2}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}')))
        if self.chk_email.isChecked():
            PATTERNS.append(("E-Posta", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')))
        if self.chk_iban.isChecked():
            PATTERNS.append(("IBAN", re.compile(r'\bTR\d{2}\s*(?:\d{4}\s*){5}\d{2}\b', re.IGNORECASE)))
            PATTERNS.append(("Kredi Kartı", re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')))

        custom_word = self.txt_custom_search.text().strip()
        if custom_word:
            PATTERNS.append(("Özel Terim", re.compile(re.escape(custom_word), re.IGNORECASE)))

        pages_to_scan = [self.current_page] if self.rb_curr_page.isChecked() else list(range(len(self.doc)))

        for p_idx in pages_to_scan:
            page = self.doc[p_idx]
            page_text = page.get_text("text")

            for cat_name, pattern in PATTERNS:
                for m in pattern.finditer(page_text):
                    match_str = m.group(0).strip()
                    # Koordinatları bul
                    rects = page.search_for(match_str)
                    for r in rects:
                        item = {
                            "page": p_idx,
                            "type": cat_name,
                            "text": match_str,
                            "rect": r,
                            "checked": True
                        }
                        self.detected_items.append(item)

        self.lbl_found_count.setText(LanguageManager.tr("redact_found_count", count=len(self.detected_items)))
        self.tbl_items.setRowCount(len(self.detected_items))

        for row, item in enumerate(self.detected_items):
            chk = QCheckBox()
            chk.setChecked(True)
            chk.stateChanged.connect(lambda state, r=row: self._on_item_check_changed(r, state))
            self.tbl_items.setCellWidget(row, 0, chk)

            p_item = QTableWidgetItem(f"{LanguageManager.tr('page_prefix_label')} {item['page'] + 1}")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_items.setItem(row, 1, p_item)

            t_item = QTableWidgetItem(item["type"])
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_items.setItem(row, 2, t_item)

            val_item = QTableWidgetItem(item["text"])
            self.tbl_items.setItem(row, 3, val_item)

    def _on_item_check_changed(self, row, state):
        if 0 <= row < len(self.detected_items):
            self.detected_items[row]["checked"] = (state == Qt.CheckState.Checked.value)

    def _on_item_clicked(self, row, col):
        if 0 <= row < len(self.detected_items):
            item = self.detected_items[row]
            if item["page"] != self.current_page:
                self.current_page = item["page"]
                self._render_current_page()

    # -------------------------------------------------------------------
    # KALICI KARARTMA UYGULAMA (PERMANENT REDACTION)
    # -------------------------------------------------------------------
    def _execute_redactions_on_doc(self, target_doc):
        fill_color = self.cmb_color.currentData() or (0, 0, 0)
        overlay_text = self.cmb_overlay_text.currentText().strip()

        # 1. Algılanan onaylı verileri karart
        for item in self.detected_items:
            if item.get("checked", True):
                p_idx = item["page"]
                if p_idx < len(target_doc):
                    page = target_doc[p_idx]
                    page.add_redact_annot(
                        item["rect"],
                        text=overlay_text,
                        fill=fill_color,
                        text_color=(1, 1, 1) if sum(fill_color) < 1.5 else (0, 0, 0),
                        fontsize=9
                    )

        # 2. Önizleme ekranındaki manuel çizilen alanları karart
        for (x0, y0, x1, y1) in self.preview_label.manual_rects:
            if self.current_page < len(target_doc):
                page = target_doc[self.current_page]
                rect = fitz.Rect(x0, y0, x1, y1)
                page.add_redact_annot(
                    rect,
                    text=overlay_text,
                    fill=fill_color,
                    text_color=(1, 1, 1) if sum(fill_color) < 1.5 else (0, 0, 0),
                    fontsize=9
                )

        # 3. Tüm sayfalara kalıcı kazıma uygula
        for p in target_doc:
            p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

        # 4. Üstveri & Ek Temizliği (Sanitization)
        if self.chk_clean_meta.isChecked():
            target_doc.set_metadata({
                "title": "", "author": "", "subject": "", "keywords": "",
                "creator": "", "producer": "AuraPDF Sanitizer",
                "creationDate": "", "modDate": ""
            })

        if self.chk_clean_attachments.isChecked():
            # Gömülü dosyaları kaldır
            for i in reversed(range(target_doc.embfile_count())):
                target_doc.embfile_del(i)

    def _apply_redactions_current(self):
        reply = QMessageBox.question(
            self, "Kalıcı Karartmayı Onayla",
            "Bu işlem seçili hassas verileri belgeden <b>geri alınamaz biçimde tamamen silecektir</b>.\n"
            "Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._execute_redactions_on_doc(self.doc)
            if self.tab_doc:
                self.tab_doc.is_modified = True
                if hasattr(self.tab_doc, 'render_current_page'):
                    self.tab_doc.render_current_page()
            self._render_current_page()
            self._clear_manual_rects()
            self.detected_items.clear()
            self.tbl_items.setRowCount(0)
            QMessageBox.information(self, "Başarılı", "Hassas veriler kalıcı olarak silindi ve temizlendi.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Karartma uygulanamadı:\n{e}")

    def _apply_redactions_save_as(self):
        default_name = "belge_karartilmis.pdf"
        if self.file_path:
            base, ext = os.path.splitext(self.file_path)
            default_name = f"{base}_karartilmis.pdf"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Karartılmış Kopya Olarak Kaydet", default_name, "PDF Dosyaları (*.pdf)"
        )
        if not save_path:
            return

        try:
            # Kopya oluştur ve onun üzerinde uygula
            copy_doc = fitz.open(self.file_path) if (self.file_path and os.path.isfile(self.file_path)) else fitz.open()
            if not copy_doc or len(copy_doc) == 0:
                copy_doc = fitz.open()
                copy_doc.insert_pdf(self.doc)

            self._execute_redactions_on_doc(copy_doc)
            copy_doc.save(save_path, garbage=4, deflate=True)
            copy_doc.close()

            QMessageBox.information(self, "Başarılı", f"Kalıcı karartılmış güvenli PDF başarıyla kaydedildi:\n{save_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydedilemedi:\n{e}")
