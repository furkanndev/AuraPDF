"""
AuraPDF - İki PDF Karşılaştırma & Fark Analizi (PDF Compare)
============================================================
İki farklı PDF belgesini veya aynı belgenin iki revizyonunu sayfa sayfa
görsel, piksel örtüştürme ve metin düzeyinde karşılaştıran profesyonel araç.
"""

import os
import difflib
import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTabWidget, QWidget, QFrame, QSplitter,
    QScrollArea, QSpinBox, QSlider, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont

import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet
from src.ui.icons import ModernIconFactory


class PDFCompareDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle(LanguageManager.tr("compare_title"))
        self.setWindowIcon(ModernIconFactory.icon_compare())
        self.resize(1100, 720)
        self.setMinimumSize(850, 560)
        self.setSizeGripEnabled(True)

        self.current_theme = getattr(self.main_window, 'current_theme', 'dark')

        self.doc1_path = ""
        self.doc2_path = ""
        self.doc1 = None
        self.doc2 = None
        self.current_page = 0
        self.zoom_scale = 1.0

        # Pre-fill doc1 if currently opened in main_window
        tab_doc = getattr(self.main_window, 'get_current_tab_doc', lambda: None)()
        if tab_doc and getattr(tab_doc, 'file_path', None) and os.path.isfile(tab_doc.file_path):
            self.doc1_path = tab_doc.file_path
            self.current_page = getattr(tab_doc, 'current_page_idx', 0)

        self._apply_style()
        self._init_ui()

        if self.doc1_path:
            self._load_doc(1, self.doc1_path)

    def _apply_style(self):
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
        elif self.current_theme == "purple":
            bg = "#150d22"; card_bg = "#201435"; border = "#321f52"; accent = "#a855f7"; text = "#faf5ff"
        elif self.current_theme == "crimson":
            bg = "#1d0b10"; card_bg = "#2d1118"; border = "#441924"; accent = "#f43f5e"; text = "#fff1f2"
        elif self.current_theme == "nord":
            bg = "#181e29"; card_bg = "#222b3a"; border = "#313e54"; accent = "#38bdf8"; text = "#f0f6fc"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {text}; }}
            QTabWidget::pane {{ border: 1px solid {border}; background-color: {card_bg}; border-radius: 6px; }}
            QTabBar::tab {{ background-color: {bg};  padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: 500; }}
            QTabBar::tab:selected {{ background-color: {card_bg};  border-bottom: 2.5px solid {accent}; font-weight: bold; }}
            QLabel {{ color: {text}; }}
            QFrame.card {{ background-color: {card_bg}; border: 1.2px solid {border}; border-radius: 8px; padding: 8px; }}
            QPushButton {{ background-color: {card_bg}; color: {text}; border: 1px solid {border}; border-radius: 6px; padding: 6px 14px; font-weight: 500; }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton#PrimaryBtn {{ background-color: {accent};  font-weight: bold; border: none; }}
            QPushButton#PrimaryBtn:hover {{ opacity: 0.9; }}
            QSpinBox {{ background-color: {card_bg};  border: 1.2px solid {border}; border-radius: 5px; padding: 3px 6px; }}
            QScrollArea {{ border: 1px solid {border};  border-radius: 6px; }}
            QTableWidget {{ background-color: {bg}; color: {text}; border: 1px solid {border}; gridline-color: {border}; border-radius: 6px; }}
            QTableWidget::item:selected {{ background-color: {accent};  }}
            QHeaderView::section {{ background-color: {card_bg};  border: 1px solid {border}; padding: 4px; font-weight: bold; }}
        """)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # 1. Üst Dosya Seçim Çubuğu
        files_bar = QFrame()
        files_bar.setProperty("class", "card")
        fb_layout = QHBoxLayout(files_bar)
        fb_layout.setContentsMargins(8, 6, 8, 6)

        # Doc 1
        fb_layout.addWidget(QLabel(f"<b>{LanguageManager.tr('compare_doc1_short_lbl')}</b>"))
        self.lbl_doc1 = QLabel(os.path.basename(self.doc1_path) if self.doc1_path else LanguageManager.tr("file_not_selected"))
        self.lbl_doc1.setStyleSheet(" font-weight: bold;")
        fb_layout.addWidget(self.lbl_doc1, 1)

        btn_browse1 = QPushButton(LanguageManager.tr("split_btn_browse"))
        btn_browse1.clicked.connect(lambda: self._browse_doc(1))
        fb_layout.addWidget(btn_browse1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("")
        fb_layout.addWidget(sep)

        # Doc 2
        fb_layout.addWidget(QLabel(f"<b>{LanguageManager.tr('compare_doc2_short_lbl')}</b>"))
        self.lbl_doc2 = QLabel(LanguageManager.tr("file_not_selected"))
        self.lbl_doc2.setStyleSheet(" font-weight: bold;")
        fb_layout.addWidget(self.lbl_doc2, 1)

        btn_browse2 = QPushButton(LanguageManager.tr("split_btn_browse"))
        btn_browse2.clicked.connect(lambda: self._browse_doc(2))
        fb_layout.addWidget(btn_browse2)

        root.addWidget(files_bar)

        # 2. Gezinti ve Kontrol Çubuğu
        nav_bar = QHBoxLayout()
        self.btn_prev = QPushButton(f"◀ {LanguageManager.tr('prev_page')}")
        self.btn_prev.clicked.connect(self._prev_page)
        nav_bar.addWidget(self.btn_prev)

        nav_bar.addWidget(QLabel(LanguageManager.tr("page_prefix_label")))
        self.spn_page = QSpinBox()
        self.spn_page.setMinimum(1)
        self.spn_page.setMaximum(1)
        self.spn_page.valueChanged.connect(self._on_page_spin_changed)
        nav_bar.addWidget(self.spn_page)

        self.lbl_total_pages = QLabel("/ 0")
        nav_bar.addWidget(self.lbl_total_pages)

        self.btn_next = QPushButton(f"{LanguageManager.tr('next_page')} ▶")
        self.btn_next.clicked.connect(self._next_page)
        nav_bar.addWidget(self.btn_next)

        nav_bar.addSpacing(20)

        # Yakınlaştırma
        nav_bar.addWidget(QLabel("Zoom:"))
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedWidth(30)
        btn_zoom_out.clicked.connect(lambda: self._change_zoom(-0.2))
        nav_bar.addWidget(btn_zoom_out)

        self.lbl_zoom = QLabel("%100")
        self.lbl_zoom.setFixedWidth(45)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_bar.addWidget(self.lbl_zoom)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedWidth(30)
        btn_zoom_in.clicked.connect(lambda: self._change_zoom(0.2))
        nav_bar.addWidget(btn_zoom_in)

        btn_zoom_reset = QPushButton(LanguageManager.tr("compare_fit_btn"))
        btn_zoom_reset.clicked.connect(self._reset_zoom)
        nav_bar.addWidget(btn_zoom_reset)

        nav_bar.addStretch()

        self.lbl_diff_badge = QLabel(LanguageManager.tr("compare_diff_status_none"))
        self.lbl_diff_badge.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;  ")
        nav_bar.addWidget(self.lbl_diff_badge)

        root.addLayout(nav_bar)

        # 3. Sekmeler (Tabs)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Sekme 1: Yan Yana Görsel Fark
        self.tab_visual = QWidget()
        self._build_visual_tab(self.tab_visual)
        self.tabs.addTab(self.tab_visual, LanguageManager.tr("compare_tab_visual"))

        # Sekme 2: Piksel Örtüştürme (Overlay Diff)
        self.tab_overlay = QWidget()
        self._build_overlay_tab(self.tab_overlay)
        self.tabs.addTab(self.tab_overlay, LanguageManager.tr("compare_tab_overlay"))

        # Sekme 3: Metin Farkları (Text Diff)
        self.tab_text = QWidget()
        self._build_text_tab(self.tab_text)
        self.tabs.addTab(self.tab_text, LanguageManager.tr("compare_tab_text"))

        # Sekme 4: Tüm Belge Fark Özeti
        self.tab_summary = QWidget()
        self._build_summary_tab(self.tab_summary)
        self.tabs.addTab(self.tab_summary, LanguageManager.tr("compare_tab_summary"))

        # 4. Alt Kapat / Rapor Butonları
        bottom_bar = QHBoxLayout()
        self.btn_export_report = QPushButton(LanguageManager.tr("compare_btn_export_report"))
        self.btn_export_report.clicked.connect(self._export_report)
        bottom_bar.addWidget(self.btn_export_report)

        bottom_bar.addStretch()

        btn_close = QPushButton(LanguageManager.tr("btn_cancel_settings"))
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        root.addLayout(bottom_bar)

    # -------------------------------------------------------------------
    # SEKME 1: YAN YANA GÖRSEL FARK
    # -------------------------------------------------------------------
    def _build_visual_tab(self, parent):
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sol: Belge 1 Scroll
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_v1_title = QLabel(LanguageManager.tr("compare_doc1_title"))
        self.lbl_v1_title.setStyleSheet("font-weight: bold; ")
        left_layout.addWidget(self.lbl_v1_title)

        self.scroll1 = QScrollArea()
        self.scroll1.setWidgetResizable(True)
        self.lbl_view1 = QLabel(LanguageManager.tr("compare_doc1_not_loaded"))
        self.lbl_view1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll1.setWidget(self.lbl_view1)
        left_layout.addWidget(self.scroll1)

        splitter.addWidget(left_box)

        # Sağ: Belge 2 Scroll
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_v2_title = QLabel(LanguageManager.tr("compare_doc2_title"))
        self.lbl_v2_title.setStyleSheet("font-weight: bold; ")
        right_layout.addWidget(self.lbl_v2_title)

        self.scroll2 = QScrollArea()
        self.scroll2.setWidgetResizable(True)
        self.lbl_view2 = QLabel(LanguageManager.tr("compare_doc2_not_loaded"))
        self.lbl_view2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll2.setWidget(self.lbl_view2)
        right_layout.addWidget(self.scroll2)

        splitter.addWidget(right_box)
        splitter.setSizes([500, 500])

        # Senkronize kaydırma (Scroll sync)
        self.scroll1.verticalScrollBar().valueChanged.connect(self.scroll2.verticalScrollBar().setValue)
        self.scroll2.verticalScrollBar().valueChanged.connect(self.scroll1.verticalScrollBar().setValue)
        self.scroll1.horizontalScrollBar().valueChanged.connect(self.scroll2.horizontalScrollBar().setValue)
        self.scroll2.horizontalScrollBar().valueChanged.connect(self.scroll1.horizontalScrollBar().setValue)

        layout.addWidget(splitter)

    # -------------------------------------------------------------------
    # SEKME 2: ÖRTÜŞTÜRME & PİKSEL FARKLARI (OVERLAY)
    # -------------------------------------------------------------------
    def _build_overlay_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel(LanguageManager.tr("compare_overlay_mode_lbl")))
        self.slider_blend = QSlider(Qt.Orientation.Horizontal)
        self.slider_blend.setRange(0, 100)
        self.slider_blend.setValue(50)
        self.slider_blend.valueChanged.connect(self._render_overlay_page)
        ctrl_bar.addWidget(self.slider_blend)
        self.lbl_blend = QLabel(LanguageManager.tr("compare_blend_diff"))
        ctrl_bar.addWidget(self.lbl_blend)
        ctrl_bar.addStretch()

        legend = QLabel(LanguageManager.tr("compare_legend"))
        legend.setStyleSheet(" font-size: 11px;")
        ctrl_bar.addWidget(legend)

        layout.addLayout(ctrl_bar)

        self.scroll_overlay = QScrollArea()
        self.scroll_overlay.setWidgetResizable(True)
        self.lbl_view_overlay = QLabel(LanguageManager.tr("compare_overlay_hint"))
        self.lbl_view_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_overlay.setWidget(self.lbl_view_overlay)
        layout.addWidget(self.scroll_overlay)

    # -------------------------------------------------------------------
    # SEKME 3: METİN FARKLARI (TEXT DIFF)
    # -------------------------------------------------------------------
    def _build_text_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)

        info_bar = QHBoxLayout()
        self.lbl_text_diff_stat = QLabel(LanguageManager.tr("compare_text_diff_hint"))
        self.lbl_text_diff_stat.setStyleSheet("")
        info_bar.addWidget(self.lbl_text_diff_stat)
        info_bar.addStretch()
        layout.addLayout(info_bar)

        self.txt_diff = QTextEdit()
        self.txt_diff.setReadOnly(True)
        self.txt_diff.setFont(QFont("Consolas", 10))
        self.txt_diff.setStyleSheet("  border-radius: 6px;")
        layout.addWidget(self.txt_diff)

    # -------------------------------------------------------------------
    # SEKME 4: TÜM BELGE FARK ÖZETİ (SUMMARY)
    # -------------------------------------------------------------------
    def _build_summary_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)

        top_bar = QHBoxLayout()
        self.btn_scan_all = QPushButton(LanguageManager.tr("compare_btn_scan_all_emoji"))
        self.btn_scan_all.setObjectName("PrimaryBtn")
        self.btn_scan_all.clicked.connect(self._scan_all_pages)
        top_bar.addWidget(self.btn_scan_all)

        self.progress_scan = QProgressBar()
        self.progress_scan.setVisible(False)
        self.progress_scan.setFixedHeight(18)
        top_bar.addWidget(self.progress_scan)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.tbl_summary = QTableWidget(0, 4)
        self.tbl_summary.setHorizontalHeaderLabels(["Sayfa", "Görsel Durum", "Metin Durumu", "Fark Oranı"])
        self.tbl_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_summary.cellDoubleClicked.connect(self._on_summary_row_clicked)
        layout.addWidget(self.tbl_summary)

    # -------------------------------------------------------------------
    # BELGE YÜKLEME & SAYFA KONTROLLERİ
    # -------------------------------------------------------------------
    def _browse_doc(self, which: int):
        path, _ = QFileDialog.getOpenFileName(
            self, f"{which}. PDF Belgesini Seç", "", "PDF Dosyaları (*.pdf)"
        )
        if path and os.path.isfile(path):
            self._load_doc(which, path)

    def _load_doc(self, which: int, path: str):
        try:
            doc = fitz.open(path)
            if which == 1:
                self.doc1_path = path
                self.doc1 = doc
                self.lbl_doc1.setText(f"{os.path.basename(path)} ({len(doc)} sf)")
                self.lbl_v1_title.setText(f"1. Belge: {os.path.basename(path)}")
            else:
                self.doc2_path = path
                self.doc2 = doc
                self.lbl_doc2.setText(f"{os.path.basename(path)} ({len(doc)} sf)")
                self.lbl_v2_title.setText(f"2. Belge: {os.path.basename(path)}")

            self._update_total_pages()
            self._render_current_page()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Belge açılamadı:\n{e}")

    def _update_total_pages(self):
        n1 = len(self.doc1) if self.doc1 else 0
        n2 = len(self.doc2) if self.doc2 else 0
        max_n = max(n1, n2)
        if max_n > 0:
            self.spn_page.blockSignals(True)
            self.spn_page.setMaximum(max_n)
            self.spn_page.setValue(min(self.current_page + 1, max_n))
            self.spn_page.blockSignals(False)
            self.lbl_total_pages.setText(f"/ {max_n}")
        else:
            self.lbl_total_pages.setText("/ 0")

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.spn_page.setValue(self.current_page + 1)
            self._render_current_page()

    def _next_page(self):
        max_n = max(len(self.doc1) if self.doc1 else 0, len(self.doc2) if self.doc2 else 0)
        if self.current_page + 1 < max_n:
            self.current_page += 1
            self.spn_page.setValue(self.current_page + 1)
            self._render_current_page()

    def _on_page_spin_changed(self, val):
        self.current_page = val - 1
        self._render_current_page()

    def _change_zoom(self, delta):
        new_zoom = max(0.4, min(3.0, self.zoom_scale + delta))
        if abs(new_zoom - self.zoom_scale) > 0.01:
            self.zoom_scale = new_zoom
            self.lbl_zoom.setText(f"%{int(self.zoom_scale * 100)}")
            self._render_current_page()

    def _reset_zoom(self):
        self.zoom_scale = 1.0
        self.lbl_zoom.setText("%100")
        self._render_current_page()

    # -------------------------------------------------------------------
    # RENDER İŞLEMLERİ
    # -------------------------------------------------------------------
    def _render_current_page(self):
        self._render_visual_page()
        self._render_overlay_page()
        self._render_text_diff_page()

    def _render_visual_page(self):
        mat = fitz.Matrix(self.zoom_scale, self.zoom_scale)

        # Belge 1
        if self.doc1 and 0 <= self.current_page < len(self.doc1):
            page1 = self.doc1[self.current_page]
            pix1 = page1.get_pixmap(matrix=mat, alpha=False)
            qimg1 = QImage(pix1.samples, pix1.width, pix1.height, pix1.stride, QImage.Format.Format_RGB888)
            self.lbl_view1.setPixmap(QPixmap.fromImage(qimg1))
        elif self.doc1:
            self.lbl_view1.setText(f"[1. Belgede {self.current_page + 1}. sayfa mevcut değil]")
        else:
            self.lbl_view1.setText("1. Belge seçilmedi")

        # Belge 2
        if self.doc2 and 0 <= self.current_page < len(self.doc2):
            page2 = self.doc2[self.current_page]
            pix2 = page2.get_pixmap(matrix=mat, alpha=False)
            qimg2 = QImage(pix2.samples, pix2.width, pix2.height, pix2.stride, QImage.Format.Format_RGB888)
            self.lbl_view2.setPixmap(QPixmap.fromImage(qimg2))
        elif self.doc2:
            self.lbl_view2.setText(f"[2. Belgede {self.current_page + 1}. sayfa mevcut değil]")
        else:
            self.lbl_view2.setText("2. Belge seçilmedi")

    def _render_overlay_page(self):
        if not (self.doc1 and self.doc2):
            self.lbl_view_overlay.setText("Karşılaştırma için lütfen iki PDF belgesi de seçin.")
            return

        has_p1 = 0 <= self.current_page < len(self.doc1)
        has_p2 = 0 <= self.current_page < len(self.doc2)

        if not has_p1 or not has_p2:
            self.lbl_view_overlay.setText(f"Sayfa {self.current_page + 1} yalnızca belgelerden birinde mevcut.")
            self.lbl_diff_badge.setText("Sayfa Eksik (Farklı Uzunluk)")
            self.lbl_diff_badge.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;  ")
            return

        mat = fitz.Matrix(self.zoom_scale, self.zoom_scale)
        p1 = self.doc1[self.current_page].get_pixmap(matrix=mat, alpha=False)
        p2 = self.doc2[self.current_page].get_pixmap(matrix=mat, alpha=False)

        im1 = Image.frombytes("RGB", (p1.width, p1.height), p1.samples)
        im2 = Image.frombytes("RGB", (p2.width, p2.height), p2.samples)

        # Aynı boyuta getir
        w = max(im1.width, im2.width)
        h = max(im1.height, im2.height)
        if im1.size != (w, h):
            bg1 = Image.new("RGB", (w, h), (255, 255, 255))
            bg1.paste(im1, (0, 0))
            im1 = bg1
        if im2.size != (w, h):
            bg2 = Image.new("RGB", (w, h), (255, 255, 255))
            bg2.paste(im2, (0, 0))
            im2 = bg2

        arr1 = np.array(im1, dtype=np.int16)
        arr2 = np.array(im2, dtype=np.int16)

        # Fark matrisi
        diff = np.abs(arr1 - arr2)
        diff_mask = np.max(diff, axis=2) > 25  # 25 threshold

        diff_ratio = (np.count_nonzero(diff_mask) / diff_mask.size) * 100

        res_arr = np.full((h, w, 3), 245, dtype=np.uint8)

        base_gray = (arr1[:, :, 0] * 0.299 + arr1[:, :, 1] * 0.587 + arr1[:, :, 2] * 0.114).astype(np.uint8)
        res_arr[:, :, 0] = base_gray
        res_arr[:, :, 1] = base_gray
        res_arr[:, :, 2] = base_gray

        del_mask = diff_mask & (arr1.mean(axis=2) < arr2.mean(axis=2))
        add_mask = diff_mask & (arr2.mean(axis=2) < arr1.mean(axis=2))

        res_arr[del_mask] = [239, 68, 68]    # Kırmızı
        res_arr[add_mask] = [16, 185, 129]   # Yeşil

        diff_img = Image.fromarray(res_arr)
        qimg = QImage(diff_img.tobytes(), w, h, w * 3, QImage.Format.Format_RGB888)
        self.lbl_view_overlay.setPixmap(QPixmap.fromImage(qimg))

        if diff_ratio < 0.05:
            self.lbl_diff_badge.setText("Sayfalar Birebir Aynı (%0 Fark)")
            self.lbl_diff_badge.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;  ")
        else:
            self.lbl_diff_badge.setText(f"Görsel Fark Bulundu: %{diff_ratio:.1f}")
            self.lbl_diff_badge.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;  ")

    def _render_text_diff_page(self):
        if not (self.doc1 and self.doc2):
            self.txt_diff.setPlainText("Metin karşılaştırması için her iki belgeyi de seçin.")
            return

        has_p1 = 0 <= self.current_page < len(self.doc1)
        has_p2 = 0 <= self.current_page < len(self.doc2)

        t1 = self.doc1[self.current_page].get_text("text").splitlines() if has_p1 else []
        t2 = self.doc2[self.current_page].get_text("text").splitlines() if has_p2 else []

        matcher = difflib.ndiff(t1, t2)
        html_lines = []
        add_cnt = 0
        del_cnt = 0

        for line in matcher:
            code = line[:2]
            content = line[2:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if code == "+ ":
                add_cnt += 1
                html_lines.append(f"<div style='  padding: 2px;'>+ {content}</div>")
            elif code == "- ":
                del_cnt += 1
                html_lines.append(f"<div style='  padding: 2px;'>- {content}</div>")
            elif code == "? ":
                continue
            else:
                html_lines.append(f"<div style=' padding: 1px;'>  {content}</div>")

        if not html_lines:
            self.txt_diff.setHtml("<p style=''>Her iki sayfada da çıkarılabilir metin bulunamadı (Taranmış sayfa olabilir).</p>")
            self.lbl_text_diff_stat.setText("Metin bulunamadı.")
        else:
            self.txt_diff.setHtml("".join(html_lines))
            self.lbl_text_diff_stat.setText(f"Sayfa Metin Analizi: {add_cnt} satır eklendi, {del_cnt} satır silindi/değişti.")

    # -------------------------------------------------------------------
    # TÜM SAYFALARI TARAMA (SCAN ALL)
    # -------------------------------------------------------------------
    def _scan_all_pages(self):
        if not (self.doc1 and self.doc2):
            QMessageBox.warning(self, "Uyarı", "Lütfen önce iki belgeyi de seçin.")
            return

        n1 = len(self.doc1)
        n2 = len(self.doc2)
        total = max(n1, n2)

        self.tbl_summary.setRowCount(total)
        self.progress_scan.setVisible(True)
        self.progress_scan.setMaximum(total)
        self.progress_scan.setValue(0)

        diff_count = 0

        for i in range(total):
            self.progress_scan.setValue(i + 1)
            has_1 = i < n1
            has_2 = i < n2

            item_page = QTableWidgetItem(f"Sayfa {i+1}")
            item_page.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_summary.setItem(i, 0, item_page)

            if not has_1:
                self.tbl_summary.setItem(i, 1, QTableWidgetItem("Yalnızca 2. Belgede var"))
                self.tbl_summary.setItem(i, 2, QTableWidgetItem("—"))
                self.tbl_summary.setItem(i, 3, QTableWidgetItem("%100"))
                diff_count += 1
                continue
            if not has_2:
                self.tbl_summary.setItem(i, 1, QTableWidgetItem("Yalnızca 1. Belgede var"))
                self.tbl_summary.setItem(i, 2, QTableWidgetItem("—"))
                self.tbl_summary.setItem(i, 3, QTableWidgetItem("%100"))
                diff_count += 1
                continue

            t1 = self.doc1[i].get_text("text").strip()
            t2 = self.doc2[i].get_text("text").strip()
            text_match = (t1 == t2)

            mat = fitz.Matrix(0.5, 0.5)
            p1 = self.doc1[i].get_pixmap(matrix=mat, alpha=False)
            p2 = self.doc2[i].get_pixmap(matrix=mat, alpha=False)

            arr1 = np.frombuffer(p1.samples, dtype=np.uint8)
            arr2 = np.frombuffer(p2.samples, dtype=np.uint8)

            if arr1.shape == arr2.shape:
                diff_pixels = np.count_nonzero(np.abs(arr1.astype(np.int16) - arr2.astype(np.int16)) > 25)
                ratio = (diff_pixels / arr1.size) * 100
            else:
                ratio = 50.0

            ratio_item = QTableWidgetItem(f"%{ratio:.1f}")
            ratio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if ratio < 0.05 and text_match:
                v_item = QTableWidgetItem("Birebir Aynı")
                v_item.setForeground(QColor("#10b981"))
                t_item = QTableWidgetItem("Aynı")
            else:
                diff_count += 1
                v_item = QTableWidgetItem("Farklı" if ratio >= 0.05 else "Görsel Benzer")
                v_item.setForeground(QColor("#f59e0b" if ratio < 10 else "#ef4444"))
                t_item = QTableWidgetItem("Metin Farklı" if not text_match else "Metin Aynı")

            self.tbl_summary.setItem(i, 1, v_item)
            self.tbl_summary.setItem(i, 2, t_item)
            self.tbl_summary.setItem(i, 3, ratio_item)

        self.progress_scan.setVisible(False)
        QMessageBox.information(
            self, "Tarama Tamamlandı",
            f"Toplam {total} sayfa tarandı.\n{diff_count} sayfada fark tespit edildi."
        )

    def _on_summary_row_clicked(self, row, col):
        self.current_page = row
        self.spn_page.setValue(row + 1)
        self.tabs.setCurrentIndex(0)
        self._render_current_page()

    def _export_report(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Fark Raporunu Kaydet", "karsilastirma_raporu.txt", "Metin Dosyası (*.txt)"
        )
        if not save_path:
            return

        lines = [
            "==================================================",
            "AuraPDF - İki PDF Karşılaştırma Raporu",
            "==================================================",
            f"1. Belge: {self.doc1_path}",
            f"2. Belge: {self.doc2_path}",
            f"1. Belge Sayfa Sayısı: {len(self.doc1) if self.doc1 else 0}",
            f"2. Belge Sayfa Sayısı: {len(self.doc2) if self.doc2 else 0}",
            "--------------------------------------------------\n"
        ]

        row_count = self.tbl_summary.rowCount()
        if row_count > 0:
            for r in range(row_count):
                p = self.tbl_summary.item(r, 0).text() if self.tbl_summary.item(r, 0) else f"Sayfa {r+1}"
                v = self.tbl_summary.item(r, 1).text() if self.tbl_summary.item(r, 1) else "—"
                t = self.tbl_summary.item(r, 2).text() if self.tbl_summary.item(r, 2) else "—"
                d = self.tbl_summary.item(r, 3).text() if self.tbl_summary.item(r, 3) else "—"
                lines.append(f"{p}: Görsel={v} | Metin={t} | Fark Oranı={d}")
        else:
            lines.append("Detaylı sayfa taraması çalıştırılmadı.")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        QMessageBox.information(self, "Başarılı", f"Fark raporu kaydedildi:\n{save_path}")
