"""
AuraPDF - Gelişmiş Yazdırma ve PDF Dışa Aktarma Diyaloğu (Adobe Acrobat Pro Stili)
Tüm AuraPDF temalarıyla tam uyumlu, canlı etkileşimli önizlemeli, çoklu sayfa (N-up),
poster, kitapçık ve hassas ölçeklendirme destekli yazdırma motoru.
"""
from typing import List, Dict, Optional, Any, Tuple
import os
import sys
import math
import tempfile
import pymupdf as fitz

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QStackedWidget, QScrollArea,
    QFrame, QMessageBox, QFileDialog, QSizePolicy
)
from PyQt6.QtGui import (
    QPainter, QImage, QPixmap, QColor, QPen, QBrush, QFont,
    QPainterPath, QRadialGradient, QPageSize, QPageLayout
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import (
    apply_dialog_theme, get_dialog_theme_stylesheet,
    get_current_theme, THEME_PALETTES
)
from src.ui.modern_stepper import ModernSpinBox, ModernDoubleSpinBox


# --- KAĞIT BOYUTU VE ÖLÇÜ TANIMLARI (Puan, İnç, Milimetre) ---
PAPER_SIZES: Dict[str, Dict[str, Any]] = {
    "letter": {
        "id": "print_paper_letter",
        "name": "US Letter",
        "w_pt": 612.0,
        "h_pt": 792.0,
        "w_in": 8.50,
        "h_in": 11.00,
        "desc": "8.50 × 11.00 in",
        "page_size_id": QPageSize.PageSizeId.Letter,
    },
    "a4": {
        "id": "print_paper_a4",
        "name": "A4",
        "w_pt": 595.28,
        "h_pt": 841.89,
        "w_in": 8.27,
        "h_in": 11.69,
        "desc": "210 × 297 mm",
        "page_size_id": QPageSize.PageSizeId.A4,
    },
    "a3": {
        "id": "print_paper_a3",
        "name": "A3",
        "w_pt": 841.89,
        "h_pt": 1190.55,
        "w_in": 11.69,
        "h_in": 16.54,
        "desc": "297 × 420 mm",
        "page_size_id": QPageSize.PageSizeId.A3,
    },
    "legal": {
        "id": "print_paper_legal",
        "name": "Legal",
        "w_pt": 612.0,
        "h_pt": 1008.0,
        "w_in": 8.50,
        "h_in": 14.00,
        "desc": "8.50 × 14.00 in",
        "page_size_id": QPageSize.PageSizeId.Legal,
    },
    "a5": {
        "id": "print_paper_a5",
        "name": "A5",
        "w_pt": 419.53,
        "h_pt": 595.28,
        "w_in": 5.83,
        "h_in": 8.27,
        "desc": "148 × 210 mm",
        "page_size_id": QPageSize.PageSizeId.A5,
    },
    "tabloid": {
        "id": "print_paper_tabloid",
        "name": "Tabloid",
        "w_pt": 792.0,
        "h_pt": 1224.0,
        "w_in": 11.00,
        "h_in": 17.00,
        "desc": "11.00 × 17.00 in",
        "page_size_id": QPageSize.PageSizeId.Tabloid,
    },
    "auto": {
        "id": "print_paper_auto",
        "name": "Auto",
        "w_pt": 0.0,
        "h_pt": 0.0,
        "w_in": 0.0,
        "h_in": 0.0,
        "desc": "",
        "page_size_id": QPageSize.PageSizeId.A4,
    },
}


# --- SEGMENTLİ SEKMELER BUTON ÇUBUĞU (ADOBE ACROBAT PRO STİLİ) ---
class AcrobatSegmentedTabBar(QWidget):
    """
    Adobe Acrobat Pro'daki 'Size | Poster | Multiple | Booklet' tab buton çubuğu.
    Aktif sekmede alt çizgi göstergesi ve vurgulanmış metin ile modern görünüm sunar.
    """
    tabChanged = pyqtSignal(int)

    def __init__(self, tabs: List[Tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tabs = tabs
        self.current_index = 0
        self.buttons: List[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for idx, (key, label) in enumerate(tabs):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName(f"AcrobatTabBtn_{idx}")
            btn.clicked.connect(lambda checked, i=idx: self.set_current_index(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        self._update_styles()

    def set_current_index(self, index: int):
        if 0 <= index < len(self.tabs):
            self.current_index = index
            self._update_styles()
            self.tabChanged.emit(index)

    def _update_styles(self):
        for idx, btn in enumerate(self.buttons):
            is_active = (idx == self.current_index)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-bottom: 2.5px solid #0a84ff;
                        font-weight: bold;
                        color: #ffffff;
                        padding: 4px 10px;
                        border-radius: 0px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-bottom: 2.5px solid transparent;
                        font-weight: normal;
                        color: #94a3b8;
                        padding: 4px 10px;
                        border-radius: 0px;
                    }
                    QPushButton:hover {
                        color: #e2e8f0;
                    }
                """)


# --- CANLI ETKİLEŞİMLİ YAZDIRMA ÖNİZLEME TUVALİ ---
class PrintPreviewCanvas(QWidget):
    """
    Gerçek zamanlı olarak kağıt boyutunu, yönünü, sayfa düzenini,
    gri tonlamayı ve işaretlemeleri yansıtan vektörel/yüksek çözünürlüklü önizleme alanı.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(320, 380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Önizleme Durumu
        self.current_sheet_pages: List[int] = [0]
        self.doc: Optional[fitz.Document] = None
        self.tab_doc: Any = None
        self.paper_key: str = "letter"
        self.paper_info: Dict[str, Any] = PAPER_SIZES["letter"]
        self.is_landscape: bool = False
        self.sizing_mode: str = "fit"       # fit, actual, shrink, custom
        self.custom_scale_pct: int = 100
        self.grayscale: bool = False
        self.comments_mode: str = "doc_markups"
        self.layout_mode: str = "size"      # size, poster, multiple, booklet
        self.multiple_n: int = 2
        self.multiple_order: str = "horiz"
        self.print_border: bool = False

        # Önbellek (Hızlı gezinme için)
        self._pixmap_cache: Dict[int, QImage] = {}

    def clear_cache(self):
        self._pixmap_cache.clear()

    def set_document(self, tab_doc: Any):
        self.tab_doc = tab_doc
        self.doc = tab_doc.doc if tab_doc else None
        self.clear_cache()
        self.update()

    def update_state(self,
                     sheet_pages: List[int],
                     paper_key: str,
                     is_landscape: bool,
                     sizing_mode: str,
                     custom_scale_pct: int,
                     grayscale: bool,
                     comments_mode: str,
                     layout_mode: str,
                     multiple_n: int,
                     multiple_order: str,
                     print_border: bool):
        self.current_sheet_pages = sheet_pages
        self.paper_key = paper_key
        self.paper_info = PAPER_SIZES.get(paper_key, PAPER_SIZES["letter"])
        self.is_landscape = is_landscape
        self.sizing_mode = sizing_mode
        self.custom_scale_pct = custom_scale_pct
        self.grayscale = grayscale
        self.comments_mode = comments_mode
        self.layout_mode = layout_mode
        self.multiple_n = multiple_n
        self.multiple_order = multiple_order
        self.print_border = print_border
        self.update()

    def _get_page_image(self, page_idx: int) -> Optional[QImage]:
        if not self.doc or page_idx < 0 or page_idx >= len(self.doc):
            return None

        cache_key = page_idx
        if cache_key in self._pixmap_cache:
            base_img = self._pixmap_cache[cache_key]
        else:
            try:
                page = self.doc[page_idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                base_img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                self._pixmap_cache[cache_key] = base_img
            except Exception:
                return None

        if self.grayscale:
            return base_img.convertToFormat(QImage.Format.Format_Grayscale8)
        return base_img

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # 1. Koyu Tuval Arka Planı
        bg_color = QColor("#16181f")
        painter.fillRect(0, 0, w, h, bg_color)

        # Tuval Çerçevesi
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

        if not self.doc or len(self.doc) == 0:
            painter.end()
            return

        # 2. Kağıt En-Boy Oranı Hesabı
        first_page_idx = self.current_sheet_pages[0] if self.current_sheet_pages else 0
        if first_page_idx < 0 or first_page_idx >= len(self.doc):
            first_page_idx = 0

        first_page = self.doc[first_page_idx]
        doc_page_w = first_page.rect.width
        doc_page_h = first_page.rect.height

        if self.paper_key == "auto":
            paper_w = doc_page_w
            paper_h = doc_page_h
        else:
            paper_w = self.paper_info["w_pt"]
            paper_h = self.paper_info["h_pt"]

        if self.is_landscape:
            paper_w, paper_h = max(paper_w, paper_h), min(paper_w, paper_h)
        else:
            paper_w, paper_h = min(paper_w, paper_h), max(paper_w, paper_h)

        # 3. Kağıdı Tuvale Orantılı Sığdırma (Margin: 20px)
        margin = 20.0
        avail_w = max(10.0, w - margin * 2)
        avail_h = max(10.0, h - margin * 2)

        scale = min(avail_w / paper_w, avail_h / paper_h)
        sheet_w = paper_w * scale
        sheet_h = paper_h * scale
        sheet_x = (w - sheet_w) / 2.0
        sheet_y = (h - sheet_h) / 2.0
        sheet_rect = QRectF(sheet_x, sheet_y, sheet_w, sheet_h)

        # 4. Yumuşak Kağıt Gölgesi (Drop Shadow)
        shadow_rect = sheet_rect.adjusted(-4, -2, 6, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 75))
        painter.drawRoundedRect(shadow_rect, 4, 4)

        # 5. Beyaz Kağıt Yüzeyi
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor(0, 0, 0, 45), 1.0))
        painter.drawRect(sheet_rect)

        # 6. Sayfa İçeriğini Kağıda Çizme
        if self.layout_mode == "multiple" and len(self.current_sheet_pages) > 0:
            self._paint_multiple(painter, sheet_rect)
        elif self.layout_mode == "booklet" and len(self.current_sheet_pages) > 0:
            self._paint_booklet(painter, sheet_rect)
        else:
            self._paint_single(painter, sheet_rect, first_page_idx, paper_w, paper_h)

        painter.end()

    def _paint_single(self, painter: QPainter, sheet_rect: QRectF, page_idx: int, paper_w: float, paper_h: float):
        img = self._get_page_image(page_idx)
        if not img or img.isNull():
            return

        page = self.doc[page_idx]
        pw = page.rect.width
        ph = page.rect.height

        # Sizing Mode Hesabı
        if self.sizing_mode == "actual":
            # 1:1 Ölçek
            scale_factor = (sheet_rect.width() / paper_w)
            draw_w = pw * scale_factor
            draw_h = ph * scale_factor
        elif self.sizing_mode == "shrink":
            # Yalnızca kağıttan büyükse küçült, değilse 1:1
            if pw > paper_w or ph > paper_h:
                fit_scale = min(sheet_rect.width() / pw, sheet_rect.height() / ph)
                draw_w = pw * fit_scale
                draw_h = ph * fit_scale
            else:
                scale_factor = (sheet_rect.width() / paper_w)
                draw_w = pw * scale_factor
                draw_h = ph * scale_factor
        elif self.sizing_mode == "custom":
            factor = (self.custom_scale_pct / 100.0) * (sheet_rect.width() / paper_w)
            draw_w = pw * factor
            draw_h = ph * factor
        else:
            # "fit" (Varsayılan - tam sığdırma)
            fit_scale = min(sheet_rect.width() / pw, sheet_rect.height() / ph) * 0.96
            draw_w = pw * fit_scale
            draw_h = ph * fit_scale

        draw_x = sheet_rect.left() + (sheet_rect.width() - draw_w) / 2.0
        draw_y = sheet_rect.top() + (sheet_rect.height() - draw_h) / 2.0
        target_rect = QRectF(draw_x, draw_y, draw_w, draw_h)

        painter.drawImage(target_rect, img)

    def _paint_multiple(self, painter: QPainter, sheet_rect: QRectF):
        n = self.multiple_n
        if n == 2:
            cols, rows = (1, 2) if sheet_rect.height() > sheet_rect.width() else (2, 1)
        elif n == 4:
            cols, rows = (2, 2)
        elif n == 6:
            cols, rows = (2, 3) if sheet_rect.height() > sheet_rect.width() else (3, 2)
        elif n == 9:
            cols, rows = (3, 3)
        elif n == 16:
            cols, rows = (4, 4)
        else:
            cols, rows = (1, 2)

        pad = 4.0
        cell_w = (sheet_rect.width() - pad * (cols + 1)) / cols
        cell_h = (sheet_rect.height() - pad * (rows + 1)) / rows

        for i, p_idx in enumerate(self.current_sheet_pages[:n]):
            c = i % cols
            r = i // cols
            cx = sheet_rect.left() + pad + c * (cell_w + pad)
            cy = sheet_rect.top() + pad + r * (cell_h + pad)
            cell_rect = QRectF(cx, cy, cell_w, cell_h)

            img = self._get_page_image(p_idx)
            if img and not img.isNull():
                page = self.doc[p_idx]
                pw = page.rect.width
                ph = page.rect.height
                scale = min(cell_w / pw, cell_h / ph)
                dw = pw * scale
                dh = ph * scale
                dx = cx + (cell_w - dw) / 2.0
                dy = cy + (cell_h - dh) / 2.0
                painter.drawImage(QRectF(dx, dy, dw, dh), img)

            if self.print_border:
                painter.setPen(QPen(QColor(160, 160, 160), 0.8))
                painter.drawRect(cell_rect)

    def _paint_booklet(self, painter: QPainter, sheet_rect: QRectF):
        # Kitapçık: Yan yana 2 sayfa
        half_w = sheet_rect.width() / 2.0
        for i, p_idx in enumerate(self.current_sheet_pages[:2]):
            bx = sheet_rect.left() + i * half_w
            by = sheet_rect.top()
            b_rect = QRectF(bx, by, half_w, sheet_rect.height())

            img = self._get_page_image(p_idx)
            if img and not img.isNull():
                page = self.doc[p_idx]
                pw = page.rect.width
                ph = page.rect.height
                scale = min((half_w * 0.95) / pw, (sheet_rect.height() * 0.95) / ph)
                dw = pw * scale
                dh = ph * scale
                dx = bx + (half_w - dw) / 2.0
                dy = by + (sheet_rect.height() - dh) / 2.0
                painter.drawImage(QRectF(dx, dy, dw, dh), img)

            # Cilt Çizgisi
            if i == 0:
                painter.setPen(QPen(QColor(210, 210, 210), 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(sheet_rect.left() + half_w, sheet_rect.top()),
                                 QPointF(sheet_rect.left() + half_w, sheet_rect.bottom()))


# --- 8. AURA YAZDIRMA & PRINT TO PDF DİYALOĞU (ADOBE ACROBAT PRO DÜZENİ) ---
class AuraPrintDialog(QDialog):
    """
    Adobe Acrobat Pro standartlarında gelişmiş AuraPDF Yazdırma Diyaloğu.
    """
    def __init__(self, tab_doc, main_window=None):
        parent_widget = main_window if isinstance(main_window, QWidget) else (tab_doc if isinstance(tab_doc, QWidget) else None)
        super().__init__(parent_widget)
        self.tab_doc = tab_doc
        self.main_window = main_window or parent_widget
        if hasattr(tab_doc, 'doc') and tab_doc.doc:
            self.doc = tab_doc.doc
        elif hasattr(tab_doc, 'page_count') or hasattr(tab_doc, 'load_page'):
            self.doc = tab_doc
        else:
            self.doc = getattr(tab_doc, 'doc', None)
        self.total_pages = len(self.doc) if self.doc else 1
        self.current_page_idx = getattr(tab_doc, 'current_page_idx', 0)
        if self.current_page_idx < 0 or self.current_page_idx >= self.total_pages:
            self.current_page_idx = 0

        # Hesaplanan yapraklar ve önizleme dizini
        self.calculated_sheets: List[List[int]] = []
        self.current_sheet_idx: int = 0

        self.setWindowTitle(LanguageManager.tr("print_dialog_title"))
        self.resize(880, 640)
        self.setMinimumSize(780, 560)
        self.setSizeGripEnabled(True)

        # Önizleme Debounce Timer
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._recalculate_and_render_preview)

        self._build_ui()
        self._populate_printers()
        self._connect_signals()

        # Tema Uygula
        apply_dialog_theme(self, main_window, extra_css="""
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLabel.SectionHeader {
                font-weight: bold;
                font-size: 11px;
                color: #94a3b8;
                letter-spacing: 0.5px;
                margin-top: 8px;
                margin-bottom: 2px;
            }
        """)

        # İlk hesaplama ve önizleme
        self._recalculate_and_render_preview()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 14)
        root_layout.setSpacing(12)

        # Ana Gövde (Sol Panel: Ayarlar, Sağ Panel: Önizleme)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        # ==============================================================
        # SOL PANEL: TÜM YAZDIRMA AYARLARI
        # ==============================================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 1. ÜST AYARLAR (Printer, Copies, Two-sided, Paper)
        grid_top = QGridLayout()
        grid_top.setHorizontalSpacing(10)
        grid_top.setVerticalSpacing(7)
        grid_top.setColumnMinimumWidth(0, 72)

        # Satır 0: Yazıcı
        lbl_printer = QLabel(LanguageManager.tr("print_lbl_printer"))
        lbl_printer.setMinimumWidth(60)
        self.cmb_printer = QComboBox()
        self.cmb_printer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_properties = QPushButton(LanguageManager.tr("print_btn_properties"))
        self.btn_properties.setMinimumWidth(88)
        self.btn_properties.setEnabled(False)
        self.btn_properties.clicked.connect(self._open_printer_properties)

        h_printer = QHBoxLayout()
        h_printer.setSpacing(6)
        h_printer.addWidget(self.cmb_printer)
        h_printer.addWidget(self.btn_properties)

        grid_top.addWidget(lbl_printer, 0, 0)
        grid_top.addLayout(h_printer, 0, 1)

        # Satır 1: Kopya + Harmanla + Gri Tonlama
        lbl_copies = QLabel(LanguageManager.tr("print_lbl_copies"))
        self.spn_copies = ModernSpinBox(min_val=1, max_val=999, default_val=1, parent=self)
        self.spn_copies.setFixedWidth(84)

        self.chk_collate = QCheckBox(LanguageManager.tr("print_chk_collate"))
        self.chk_collate.setChecked(True)

        self.chk_grayscale = QCheckBox(LanguageManager.tr("print_chk_grayscale"))
        self.chk_grayscale.setChecked(False)

        h_copies = QHBoxLayout()
        h_copies.setSpacing(14)
        h_copies.addWidget(self.spn_copies)
        h_copies.addWidget(self.chk_collate)
        h_copies.addWidget(self.chk_grayscale)
        h_copies.addStretch()

        grid_top.addWidget(lbl_copies, 1, 0)
        grid_top.addLayout(h_copies, 1, 1)

        # Satır 2: İki Taraflı
        lbl_twosided = QLabel(LanguageManager.tr("print_lbl_twosided"))
        self.cmb_twosided = QComboBox()
        self.cmb_twosided.addItem(LanguageManager.tr("print_twosided_off"), "off")
        self.cmb_twosided.addItem(LanguageManager.tr("print_twosided_long"), "long")
        self.cmb_twosided.addItem(LanguageManager.tr("print_twosided_short"), "short")
        grid_top.addWidget(lbl_twosided, 2, 0)
        grid_top.addWidget(self.cmb_twosided, 2, 1)

        # Satır 3: Kağıt Boyutu
        lbl_paper = QLabel(LanguageManager.tr("print_lbl_paper"))
        self.cmb_paper = QComboBox()
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_letter')} (8.5 × 11 in)", "letter")
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_a4')} (210 × 297 mm)", "a4")
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_a3')} (297 × 420 mm)", "a3")
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_legal')} (8.5 × 14 in)", "legal")
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_a5')} (148 × 210 mm)", "a5")
        self.cmb_paper.addItem(f"{LanguageManager.tr('print_paper_tabloid')} (11 × 17 in)", "tabloid")
        self.cmb_paper.addItem(LanguageManager.tr("print_paper_auto"), "auto")
        grid_top.addWidget(lbl_paper, 3, 0)
        grid_top.addWidget(self.cmb_paper, 3, 1)

        left_layout.addLayout(grid_top)

        # --------------------------------------------------------------
        # 2. BÖLÜM: YAZDIRILACAK SAYFALAR (PAGES TO PRINT)
        # --------------------------------------------------------------
        lbl_sec_pages = QLabel(LanguageManager.tr("print_sec_pages"))
        lbl_sec_pages.setProperty("class", "SectionHeader")
        lbl_sec_pages.setStyleSheet("font-weight: bold; font-size: 11px; color: #94a3b8; margin-top: 6px;")
        left_layout.addWidget(lbl_sec_pages)

        # Radyo Butonları: Tümü | Geçerli Sayfa | Sayfalar
        h_pages_radios = QHBoxLayout()
        h_pages_radios.setSpacing(12)

        self.btn_grp_pages = QButtonGroup(self)
        self.rb_pages_all = QRadioButton(LanguageManager.tr("print_radio_all"))
        self.rb_pages_all.setChecked(True)
        self.rb_pages_curr = QRadioButton(LanguageManager.tr("print_radio_current"))
        self.rb_pages_range = QRadioButton(LanguageManager.tr("print_radio_pages"))

        self.btn_grp_pages.addButton(self.rb_pages_all, 0)
        self.btn_grp_pages.addButton(self.rb_pages_curr, 1)
        self.btn_grp_pages.addButton(self.rb_pages_range, 2)

        self.txt_pages_range = QLineEdit(f"1-{self.total_pages}")
        self.txt_pages_range.setEnabled(False)
        self.txt_pages_range.setPlaceholderText(f"1-{self.total_pages}")
        self.txt_pages_range.setFixedWidth(100)

        h_pages_radios.addWidget(self.rb_pages_all)
        h_pages_radios.addWidget(self.rb_pages_curr)
        h_pages_radios.addWidget(self.rb_pages_range)
        h_pages_radios.addWidget(self.txt_pages_range)
        h_pages_radios.addStretch()
        left_layout.addLayout(h_pages_radios)

        # Alt Satır: Daha Fazla Seçenek + Sayfaları Ters Çevir
        h_more_opts = QHBoxLayout()
        h_more_opts.setSpacing(10)
        lbl_more = QLabel(LanguageManager.tr("print_lbl_more_options"))
        self.cmb_more_opts = QComboBox()
        self.cmb_more_opts.addItem(LanguageManager.tr("print_opt_all_in_range"), "all")
        self.cmb_more_opts.addItem(LanguageManager.tr("print_opt_odd_only"), "odd")
        self.cmb_more_opts.addItem(LanguageManager.tr("print_opt_even_only"), "even")

        self.chk_reverse_pages = QCheckBox(LanguageManager.tr("print_chk_reverse"))

        h_more_opts.addWidget(lbl_more)
        h_more_opts.addWidget(self.cmb_more_opts)
        h_more_opts.addWidget(self.chk_reverse_pages)
        h_more_opts.addStretch()
        left_layout.addLayout(h_more_opts)

        # --------------------------------------------------------------
        # 3. BÖLÜM: SAYFA BOYUTLANDIRMA VE YÖNETİMİ (PAGE SIZING & HANDLING)
        # --------------------------------------------------------------
        lbl_sec_sizing = QLabel(LanguageManager.tr("print_sec_sizing"))
        lbl_sec_sizing.setStyleSheet("font-weight: bold; font-size: 11px; color: #94a3b8; margin-top: 8px;")
        left_layout.addWidget(lbl_sec_sizing)

        # Segmentli Sekmeler: Size | Poster | Multiple | Booklet
        self.sizing_tabs = AcrobatSegmentedTabBar([
            ("size", LanguageManager.tr("print_tab_size")),
            ("poster", LanguageManager.tr("print_tab_poster")),
            ("multiple", LanguageManager.tr("print_tab_multiple")),
            ("booklet", LanguageManager.tr("print_tab_booklet")),
        ])
        left_layout.addWidget(self.sizing_tabs)

        # Yığıt (Stacked Widget)
        self.stack_sizing = QStackedWidget()

        # --- PANEL 0: SIZE ---
        panel_size = QWidget()
        v_size = QVBoxLayout(panel_size)
        v_size.setContentsMargins(4, 6, 4, 4)
        v_size.setSpacing(6)

        h_size_radios = QHBoxLayout()
        h_size_radios.setSpacing(12)
        self.btn_grp_size = QButtonGroup(self)
        self.rb_size_fit = QRadioButton(LanguageManager.tr("print_size_fit"))
        self.rb_size_fit.setChecked(True)
        self.rb_size_actual = QRadioButton(LanguageManager.tr("print_size_actual"))
        self.rb_size_shrink = QRadioButton(LanguageManager.tr("print_size_shrink"))

        self.btn_grp_size.addButton(self.rb_size_fit, 0)
        self.btn_grp_size.addButton(self.rb_size_actual, 1)
        self.btn_grp_size.addButton(self.rb_size_shrink, 2)

        h_size_radios.addWidget(self.rb_size_fit)
        h_size_radios.addWidget(self.rb_size_actual)
        h_size_radios.addWidget(self.rb_size_shrink)
        h_size_radios.addStretch()
        v_size.addLayout(h_size_radios)

        h_custom_scale = QHBoxLayout()
        h_custom_scale.setSpacing(8)
        self.rb_size_custom = QRadioButton(LanguageManager.tr("print_size_custom"))
        self.btn_grp_size.addButton(self.rb_size_custom, 3)
        self.spn_custom_scale = ModernSpinBox(min_val=10, max_val=1000, default_val=100, suffix=" %", parent=self)
        self.spn_custom_scale.setEnabled(False)
        self.spn_custom_scale.setFixedWidth(92)

        h_custom_scale.addWidget(self.rb_size_custom)
        h_custom_scale.addWidget(self.spn_custom_scale)
        h_custom_scale.addStretch()
        v_size.addLayout(h_custom_scale)
        self.stack_sizing.addWidget(panel_size)

        # --- PANEL 1: POSTER ---
        panel_poster = QWidget()
        v_poster = QVBoxLayout(panel_poster)
        v_poster.setContentsMargins(4, 6, 4, 4)
        v_poster.setSpacing(6)

        h_poster_row1 = QHBoxLayout()
        h_poster_row1.setSpacing(12)
        lbl_tile = QLabel(LanguageManager.tr("print_poster_tile_scale"))
        self.spn_tile_scale = ModernSpinBox(min_val=10, max_val=1000, default_val=100, suffix=" %", parent=self)
        self.spn_tile_scale.setFixedWidth(92)

        lbl_overlap = QLabel(LanguageManager.tr("print_poster_overlap"))
        self.spn_overlap = ModernDoubleSpinBox(min_val=0.0, max_val=50.0, default_val=0.0, suffix=" pt", parent=self)
        self.spn_overlap.setFixedWidth(92)

        h_poster_row1.addWidget(lbl_tile)
        h_poster_row1.addWidget(self.spn_tile_scale)
        h_poster_row1.addWidget(lbl_overlap)
        h_poster_row1.addWidget(self.spn_overlap)
        h_poster_row1.addStretch()
        v_poster.addLayout(h_poster_row1)

        h_poster_row2 = QHBoxLayout()
        h_poster_row2.setSpacing(14)
        self.chk_cut_marks = QCheckBox(LanguageManager.tr("print_poster_cut_marks"))
        self.chk_poster_labels = QCheckBox(LanguageManager.tr("print_poster_labels"))
        h_poster_row2.addWidget(self.chk_cut_marks)
        h_poster_row2.addWidget(self.chk_poster_labels)
        h_poster_row2.addStretch()
        v_poster.addLayout(h_poster_row2)
        self.stack_sizing.addWidget(panel_poster)

        # --- PANEL 2: MULTIPLE ---
        panel_multiple = QWidget()
        v_multiple = QVBoxLayout(panel_multiple)
        v_multiple.setContentsMargins(4, 6, 4, 4)
        v_multiple.setSpacing(6)

        h_mult_row1 = QHBoxLayout()
        h_mult_row1.setSpacing(10)
        lbl_pages_sheet = QLabel(LanguageManager.tr("print_mult_pages_per_sheet"))
        self.cmb_pages_per_sheet = QComboBox()
        self.cmb_pages_per_sheet.addItem("2", 2)
        self.cmb_pages_per_sheet.addItem("4", 4)
        self.cmb_pages_per_sheet.addItem("6", 6)
        self.cmb_pages_per_sheet.addItem("9", 9)
        self.cmb_pages_per_sheet.addItem("16", 16)

        lbl_page_order = QLabel(LanguageManager.tr("print_mult_page_order"))
        self.cmb_page_order = QComboBox()
        self.cmb_page_order.addItem(LanguageManager.tr("print_mult_order_horiz"), "horiz")
        self.cmb_page_order.addItem(LanguageManager.tr("print_mult_order_horiz_rev"), "horiz_rev")
        self.cmb_page_order.addItem(LanguageManager.tr("print_mult_order_vert"), "vert")
        self.cmb_page_order.addItem(LanguageManager.tr("print_mult_order_vert_rev"), "vert_rev")

        h_mult_row1.addWidget(lbl_pages_sheet)
        h_mult_row1.addWidget(self.cmb_pages_per_sheet)
        h_mult_row1.addWidget(lbl_page_order)
        h_mult_row1.addWidget(self.cmb_page_order)
        h_mult_row1.addStretch()
        v_multiple.addLayout(h_mult_row1)

        self.chk_mult_border = QCheckBox(LanguageManager.tr("print_mult_print_border"))
        v_multiple.addWidget(self.chk_mult_border)
        self.stack_sizing.addWidget(panel_multiple)

        # --- PANEL 3: BOOKLET ---
        panel_booklet = QWidget()
        v_booklet = QVBoxLayout(panel_booklet)
        v_booklet.setContentsMargins(4, 6, 4, 4)
        v_booklet.setSpacing(6)

        h_bklt_row1 = QHBoxLayout()
        h_bklt_row1.setSpacing(10)
        lbl_bklt_subset = QLabel(LanguageManager.tr("print_booklet_subset"))
        self.cmb_booklet_subset = QComboBox()
        self.cmb_booklet_subset.addItem(LanguageManager.tr("print_booklet_both"), "both")
        self.cmb_booklet_subset.addItem(LanguageManager.tr("print_booklet_front"), "front")
        self.cmb_booklet_subset.addItem(LanguageManager.tr("print_booklet_back"), "back")

        lbl_binding = QLabel(LanguageManager.tr("print_booklet_binding"))
        self.cmb_binding = QComboBox()
        self.cmb_binding.addItem(LanguageManager.tr("print_booklet_left"), "left")
        self.cmb_binding.addItem(LanguageManager.tr("print_booklet_right"), "right")
        self.cmb_binding.addItem(LanguageManager.tr("print_booklet_left_tall"), "left_tall")
        self.cmb_binding.addItem(LanguageManager.tr("print_booklet_right_tall"), "right_tall")

        h_bklt_row1.addWidget(lbl_bklt_subset)
        h_bklt_row1.addWidget(self.cmb_booklet_subset)
        h_bklt_row1.addWidget(lbl_binding)
        h_bklt_row1.addWidget(self.cmb_binding)
        h_bklt_row1.addStretch()
        v_booklet.addLayout(h_bklt_row1)
        self.stack_sizing.addWidget(panel_booklet)

        left_layout.addWidget(self.stack_sizing)

        # YÖN (ORIENTATION)
        h_orient = QHBoxLayout()
        h_orient.setSpacing(10)
        lbl_orient = QLabel(LanguageManager.tr("print_lbl_orientation"))
        lbl_orient.setStyleSheet("font-weight: bold;")

        self.btn_grp_orient = QButtonGroup(self)
        self.rb_orient_auto = QRadioButton(LanguageManager.tr("print_orient_auto"))
        self.rb_orient_auto.setChecked(True)
        self.rb_orient_port = QRadioButton(LanguageManager.tr("print_orient_portrait"))
        self.rb_orient_land = QRadioButton(LanguageManager.tr("print_orient_landscape"))

        self.btn_grp_orient.addButton(self.rb_orient_auto, 0)
        self.btn_grp_orient.addButton(self.rb_orient_port, 1)
        self.btn_grp_orient.addButton(self.rb_orient_land, 2)

        h_orient.addWidget(lbl_orient)
        h_orient.addWidget(self.rb_orient_auto)
        h_orient.addWidget(self.rb_orient_port)
        h_orient.addWidget(self.rb_orient_land)
        h_orient.addStretch()
        left_layout.addLayout(h_orient)

        # --------------------------------------------------------------
        # 4. BÖLÜM: AÇIKLAMALAR VE FORMLAR (COMMENTS & FORMS)
        # --------------------------------------------------------------
        lbl_sec_comments = QLabel(LanguageManager.tr("print_sec_comments"))
        lbl_sec_comments.setStyleSheet("font-weight: bold; font-size: 11px; color: #94a3b8; margin-top: 8px;")
        left_layout.addWidget(lbl_sec_comments)

        self.cmb_comments = QComboBox()
        self.cmb_comments.addItem(LanguageManager.tr("print_comments_doc_markups"), "doc_markups")
        self.cmb_comments.addItem(LanguageManager.tr("print_comments_doc_only"), "doc_only")
        self.cmb_comments.addItem(LanguageManager.tr("print_comments_doc_stamps"), "doc_stamps")
        self.cmb_comments.addItem(LanguageManager.tr("print_comments_forms_only"), "forms_only")
        left_layout.addWidget(self.cmb_comments)

        left_layout.addStretch()
        body_layout.addWidget(left_widget, 50)

        # ==============================================================
        # SAĞ PANEL: CANLI ÖNİZLEME (LIVE PREVIEW)
        # ==============================================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Önizleme Tuvali
        self.preview_canvas = PrintPreviewCanvas(self)
        self.preview_canvas.set_document(self.tab_doc)
        right_layout.addWidget(self.preview_canvas, 1)

        # Yaprak Gezinme Kontrolleri: [ < ] Sheet 1 of 428 [ > ]
        h_sheet_nav = QHBoxLayout()
        h_sheet_nav.setContentsMargins(0, 2, 0, 0)
        h_sheet_nav.setSpacing(8)
        h_sheet_nav.addStretch()

        self.btn_sheet_prev = QPushButton()
        self.btn_sheet_prev.setFixedSize(28, 28)
        self.btn_sheet_prev.setIcon(ModernIconFactory.icon_chevron_left())
        self.btn_sheet_prev.clicked.connect(self._goto_prev_sheet)

        self.lbl_sheet_info = QLabel(LanguageManager.tr("print_sheet_of", curr=1, total=self.total_pages))
        self.lbl_sheet_info.setStyleSheet("font-weight: 500; font-size: 12px;")

        self.btn_sheet_next = QPushButton()
        self.btn_sheet_next.setFixedSize(28, 28)
        self.btn_sheet_next.setIcon(ModernIconFactory.icon_chevron_right())
        self.btn_sheet_next.clicked.connect(self._goto_next_sheet)

        h_sheet_nav.addWidget(self.btn_sheet_prev)
        h_sheet_nav.addWidget(self.lbl_sheet_info)
        h_sheet_nav.addWidget(self.btn_sheet_next)
        h_sheet_nav.addStretch()
        right_layout.addLayout(h_sheet_nav)

        # Kağıt Boyutu ve Ölçüleri Etiketi: e.g. "8.50 × 11.00 in"
        self.lbl_paper_dimensions = QLabel("8.50 × 11.00 in")
        self.lbl_paper_dimensions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_paper_dimensions.setStyleSheet("font-size: 11px; color: #94a3b8;")
        right_layout.addWidget(self.lbl_paper_dimensions)

        body_layout.addWidget(right_widget, 50)
        root_layout.addLayout(body_layout, 1)

        # ==============================================================
        # ALT EYLEM ÇUBUĞU (Cancel & Save as PDF / Print)
        # ==============================================================
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(10)
        bottom_layout.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("print_btn_cancel"))
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setMinimumWidth(88)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_run = QPushButton(LanguageManager.tr("print_btn_save_pdf"))
        self.btn_run.setObjectName("PrimaryBtn")
        self.btn_run.setMinimumWidth(110)
        self.btn_run.clicked.connect(self.execute_print)
        bottom_layout.addWidget(self.btn_run)

        root_layout.addLayout(bottom_layout)

    def _populate_printers(self):
        """Yazıcı listesini doldurur: İlki 'Save as PDF', ardından sistem yazıcıları."""
        self.cmb_printer.clear()
        self.cmb_printer.addItem(LanguageManager.tr("print_opt_save_pdf"), "save_pdf")

        available = QPrinterInfo.availablePrinterNames()
        for p_name in available:
            self.cmb_printer.addItem(p_name, p_name)

        # Varsayılan seçim "Save as PDF"
        self.cmb_printer.setCurrentIndex(0)

    def _connect_signals(self):
        # Yazıcı değiştiğinde buton etiketini ve özellikler butonunu güncelle
        self.cmb_printer.currentIndexChanged.connect(self._on_printer_changed)

        # Sekme değişimi (Size, Poster, Multiple, Booklet)
        self.sizing_tabs.tabChanged.connect(self.stack_sizing.setCurrentIndex)
        self.sizing_tabs.tabChanged.connect(lambda _: self._schedule_preview_update())

        # Sayfa aralığı radyo değişimi
        self.rb_pages_all.toggled.connect(self._on_page_selection_changed)
        self.rb_pages_curr.toggled.connect(self._on_page_selection_changed)
        self.rb_pages_range.toggled.connect(self._on_page_selection_changed)
        self.txt_pages_range.textChanged.connect(self._schedule_preview_update)

        # Filtreler
        self.cmb_more_opts.currentIndexChanged.connect(self._schedule_preview_update)
        self.chk_reverse_pages.toggled.connect(self._schedule_preview_update)

        # Kağıt, Kopya, Gri Tonlama, İki Taraflı
        self.cmb_paper.currentIndexChanged.connect(self._schedule_preview_update)
        self.chk_grayscale.toggled.connect(self._schedule_preview_update)
        self.spn_copies.valueChanged.connect(self._schedule_preview_update)

        # Boyutlandırma
        self.rb_size_fit.toggled.connect(self._schedule_preview_update)
        self.rb_size_actual.toggled.connect(self._schedule_preview_update)
        self.rb_size_shrink.toggled.connect(self._schedule_preview_update)
        self.rb_size_custom.toggled.connect(self._on_custom_scale_toggled)
        self.spn_custom_scale.valueChanged.connect(self._schedule_preview_update)

        # Çoklu (Multiple)
        self.cmb_pages_per_sheet.currentIndexChanged.connect(self._schedule_preview_update)
        self.cmb_page_order.currentIndexChanged.connect(self._schedule_preview_update)
        self.chk_mult_border.toggled.connect(self._schedule_preview_update)

        # Yön
        self.rb_orient_auto.toggled.connect(self._schedule_preview_update)
        self.rb_orient_port.toggled.connect(self._schedule_preview_update)
        self.rb_orient_land.toggled.connect(self._schedule_preview_update)

        # Açıklamalar ve Formlar
        self.cmb_comments.currentIndexChanged.connect(self._schedule_preview_update)

    def _on_printer_changed(self, index: int):
        data = self.cmb_printer.currentData()
        if data == "save_pdf":
            self.btn_run.setText(LanguageManager.tr("print_btn_save_pdf"))
            self.btn_properties.setEnabled(False)
        else:
            self.btn_run.setText(LanguageManager.tr("print_btn_print"))
            self.btn_properties.setEnabled(True)

    def _open_printer_properties(self):
        p_name = self.cmb_printer.currentData()
        if p_name and p_name != "save_pdf":
            printer_info = QPrinterInfo.printerInfo(p_name)
            printer = QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)
            dlg = QPrintDialog(printer, self)
            dlg.exec()

    def _on_page_selection_changed(self):
        is_range = self.rb_pages_range.isChecked()
        self.txt_pages_range.setEnabled(is_range)
        self._schedule_preview_update()

    def _on_custom_scale_toggled(self, checked: bool):
        self.spn_custom_scale.setEnabled(checked)
        self._schedule_preview_update()

    def _schedule_preview_update(self):
        """Debounce edilmiş şekilde önizlemeyi yeniler."""
        self._preview_timer.start(40)

    # --- SAYFA VE YAPRAK HESAPLAMA MOTORU ---
    def _parse_target_pages(self) -> List[int]:
        if not self.doc or len(self.doc) == 0:
            return []

        # 1. Seçim tipine göre temel sayfalar
        if self.rb_pages_curr.isChecked():
            pages = [self.current_page_idx]
        elif self.rb_pages_range.isChecked():
            raw = self.txt_pages_range.text().strip()
            indices = set()
            for part in raw.split(','):
                part = part.strip()
                if not part:
                    continue
                if '-' in part:
                    try:
                        s, e = map(int, part.split('-'))
                        for p in range(s, e + 1):
                            if 1 <= p <= self.total_pages:
                                indices.add(p - 1)
                    except ValueError:
                        pass
                else:
                    try:
                        p = int(part)
                        if 1 <= p <= self.total_pages:
                            indices.add(p - 1)
                    except ValueError:
                        pass
            pages = sorted(list(indices))
        else:
            pages = list(range(self.total_pages))

        # 2. Daha fazla seçenek (Odd / Even)
        more_mode = self.cmb_more_opts.currentData()
        if more_mode == "odd":
            pages = [p for p in pages if (p + 1) % 2 != 0]
        elif more_mode == "even":
            pages = [p for p in pages if (p + 1) % 2 == 0]

        # 3. Ters Çevirme
        if self.chk_reverse_pages.isChecked():
            pages = list(reversed(pages))

        return pages

    def _calculate_sheets(self, target_pages: List[int]) -> List[List[int]]:
        tab_idx = self.sizing_tabs.current_index
        if not target_pages:
            return []

        # Multiple (Çoklu)
        if tab_idx == 2:
            n = self.cmb_pages_per_sheet.currentData() or 2
            sheets = []
            for i in range(0, len(target_pages), n):
                sheets.append(target_pages[i:i + n])
            return sheets

        # Booklet (Kitapçık)
        if tab_idx == 3:
            sheets = []
            for i in range(0, len(target_pages), 2):
                sheets.append(target_pages[i:i + 2])
            return sheets

        # Standard (1 sayfa = 1 yaprak)
        return [[p] for p in target_pages]

    def _recalculate_and_render_preview(self):
        target_pages = self._parse_target_pages()
        self.calculated_sheets = self._calculate_sheets(target_pages)

        total_sheets = max(1, len(self.calculated_sheets))
        if self.current_sheet_idx >= total_sheets:
            self.current_sheet_idx = total_sheets - 1
        if self.current_sheet_idx < 0:
            self.current_sheet_idx = 0

        # Navigasyon güncelle
        self.btn_sheet_prev.setEnabled(self.current_sheet_idx > 0)
        self.btn_sheet_next.setEnabled(self.current_sheet_idx < total_sheets - 1)
        self.lbl_sheet_info.setText(LanguageManager.tr("print_sheet_of",
                                                       curr=self.current_sheet_idx + 1 if self.calculated_sheets else 0,
                                                       total=len(self.calculated_sheets)))

        # Kağıt ve Yön Bilgisi
        paper_key = self.cmb_paper.currentData() or "letter"
        paper_info = PAPER_SIZES.get(paper_key, PAPER_SIZES["letter"])

        # Yön
        if self.rb_orient_land.isChecked():
            is_landscape = True
        elif self.rb_orient_port.isChecked():
            is_landscape = False
        else:
            # Otomatik
            sheet_pages = self.calculated_sheets[self.current_sheet_idx] if self.calculated_sheets else [0]
            first_p = sheet_pages[0] if sheet_pages else 0
            if self.doc and 0 <= first_p < len(self.doc):
                p_rect = self.doc[first_p].rect
                is_landscape = (p_rect.width > p_rect.height)
            else:
                is_landscape = False

        # Ölçü Metni
        if paper_key == "auto":
            if self.doc and self.total_pages > 0:
                p_rect = self.doc[0].rect
                dim_str = f"{p_rect.width / 72.0:.2f} × {p_rect.height / 72.0:.2f} in"
            else:
                dim_str = "Auto"
        else:
            if is_landscape:
                dim_str = f"{max(paper_info['w_in'], paper_info['h_in']):.2f} × {min(paper_info['w_in'], paper_info['h_in']):.2f} in"
            else:
                dim_str = f"{min(paper_info['w_in'], paper_info['h_in']):.2f} × {max(paper_info['w_in'], paper_info['h_in']):.2f} in"
        self.lbl_paper_dimensions.setText(dim_str)

        # Boyutlandırma parametreleri
        sizing_idx = self.btn_grp_size.checkedId()
        sizing_mode = "fit"
        if sizing_idx == 1: sizing_mode = "actual"
        elif sizing_idx == 2: sizing_mode = "shrink"
        elif sizing_idx == 3: sizing_mode = "custom"

        layout_mode = "size"
        tab_idx = self.sizing_tabs.current_index
        if tab_idx == 1: layout_mode = "poster"
        elif tab_idx == 2: layout_mode = "multiple"
        elif tab_idx == 3: layout_mode = "booklet"

        active_pages = self.calculated_sheets[self.current_sheet_idx] if self.calculated_sheets else []

        self.preview_canvas.update_state(
            sheet_pages=active_pages,
            paper_key=paper_key,
            is_landscape=is_landscape,
            sizing_mode=sizing_mode,
            custom_scale_pct=self.spn_custom_scale.value(),
            grayscale=self.chk_grayscale.isChecked(),
            comments_mode=self.cmb_comments.currentData() or "doc_markups",
            layout_mode=layout_mode,
            multiple_n=self.cmb_pages_per_sheet.currentData() or 2,
            multiple_order=self.cmb_page_order.currentData() or "horiz",
            print_border=self.chk_mult_border.isChecked()
        )

    def _goto_prev_sheet(self):
        if self.current_sheet_idx > 0:
            self.current_sheet_idx -= 1
            self._schedule_preview_update()

    def _goto_next_sheet(self):
        if self.current_sheet_idx < len(self.calculated_sheets) - 1:
            self.current_sheet_idx += 1
            self._schedule_preview_update()

    # ==============================================================
    # YAZDIRMA & PDF OLARAK KAYDETME MOTORU
    # ==============================================================
    def execute_print(self):
        target_pages = self._parse_target_pages()
        if not target_pages:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("print_no_valid_pages"))
            return

        printer_target = self.cmb_printer.currentData()

        if printer_target == "save_pdf":
            self._execute_save_pdf(target_pages)
        else:
            self._execute_physical_print(target_pages, printer_target)

    def _execute_save_pdf(self, target_pages: List[int]):
        orig_name = os.path.splitext(os.path.basename(self.tab_doc.file_path))[0] if getattr(self.tab_doc, 'file_path', None) else "belge"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            LanguageManager.tr("print_btn_save_pdf"),
            f"{orig_name}_printed.pdf",
            "PDF (*.pdf)"
        )
        if not save_path:
            return

        tmp_save_path = save_path + ".tmp_save"
        try:
            out_doc = fitz.open()
            tab_idx = self.sizing_tabs.current_index
            paper_key = self.cmb_paper.currentData() or "letter"
            paper_info = PAPER_SIZES.get(paper_key, PAPER_SIZES["letter"])

            is_grayscale = self.chk_grayscale.isChecked()
            include_markups = (self.cmb_comments.currentData() == "doc_markups")

            # Çoklu (Multiple) N-up Düzeni
            if tab_idx == 2:
                n = self.cmb_pages_per_sheet.currentData() or 2
                border = self.chk_mult_border.isChecked()

                pw = paper_info["w_pt"] if paper_key != "auto" else 595.28
                ph = paper_info["h_pt"] if paper_key != "auto" else 841.89
                if self.rb_orient_land.isChecked() or (self.rb_orient_auto.isChecked() and n in [2, 6]):
                    pw, ph = max(pw, ph), min(pw, ph)

                cols, rows = (2, 1) if n == 2 else ((2, 2) if n == 4 else (3, 2))
                pad = 12.0
                cell_w = (pw - pad * (cols + 1)) / cols
                cell_h = (ph - pad * (rows + 1)) / rows

                for i in range(0, len(target_pages), n):
                    sub_pages = target_pages[i:i + n]
                    new_p = out_doc.new_page(width=pw, height=ph)

                    for cell_idx, p_idx in enumerate(sub_pages):
                        c = cell_idx % cols
                        r = cell_idx // cols
                        cx = pad + c * (cell_w + pad)
                        cy = pad + r * (cell_h + pad)
                        target_rect = fitz.Rect(cx, cy, cx + cell_w, cy + cell_h)

                        new_p.show_pdf_page(target_rect, self.doc, p_idx, keep_proportion=True)
                        if border:
                            new_p.draw_rect(target_rect, color=(0.6, 0.6, 0.6), width=0.8)

            # Standart Sayfa Yerleşimi
            else:
                for p_idx in target_pages:
                    src_page = self.doc[p_idx]
                    if paper_key == "auto":
                        pw = src_page.rect.width
                        ph = src_page.rect.height
                    else:
                        pw = paper_info["w_pt"]
                        ph = paper_info["h_pt"]

                    if self.rb_orient_land.isChecked():
                        pw, ph = max(pw, ph), min(pw, ph)
                    elif self.rb_orient_port.isChecked():
                        pw, ph = min(pw, ph), max(pw, ph)

                    new_p = out_doc.new_page(width=pw, height=ph)

                    # Sayfa Yerleşimi
                    sizing_idx = self.btn_grp_size.checkedId()
                    if sizing_idx == 1:   # Actual size
                        draw_rect = fitz.Rect(0, 0, src_page.rect.width, src_page.rect.height)
                        draw_rect = draw_rect + fitz.Point((pw - src_page.rect.width) / 2, (ph - src_page.rect.height) / 2)
                    elif sizing_idx == 3: # Custom scale
                        factor = self.spn_custom_scale.value() / 100.0
                        dw = src_page.rect.width * factor
                        dh = src_page.rect.height * factor
                        draw_rect = fitz.Rect((pw - dw) / 2, (ph - dh) / 2, (pw + dw) / 2, (ph + dh) / 2)
                    else:                 # Fit (Varsayılan)
                        margin_rect = fitz.Rect(10, 10, pw - 10, ph - 10)
                        draw_rect = margin_rect

                    new_p.show_pdf_page(draw_rect, self.doc, p_idx, keep_proportion=True)

            # Çizimleri ve Notları Aktar (Gerekliyse)
            if include_markups and hasattr(self.tab_doc, 'export_drawings_to_pdf'):
                self.tab_doc.export_drawings_to_pdf(out_doc, list(range(len(out_doc))))

            # Atomik Güvenli Kayıt
            out_doc.save(tmp_save_path, garbage=4, deflate=True, clean=True)
            out_doc.close()

            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    pass
            os.replace(tmp_save_path, save_path)

            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("print_success"))
            self.accept()

        except Exception as e:
            if os.path.exists(tmp_save_path):
                try:
                    os.remove(tmp_save_path)
                except Exception:
                    pass
            QMessageBox.critical(self, LanguageManager.tr("error"), LanguageManager.tr("print_failed", error=str(e)))

    def _execute_physical_print(self, target_pages: List[int], printer_name: str):
        try:
            printer_info = QPrinterInfo.printerInfo(printer_name)
            printer = QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)

            # Kağıt Boyutu
            paper_key = self.cmb_paper.currentData() or "letter"
            paper_info = PAPER_SIZES.get(paper_key, PAPER_SIZES["letter"])
            printer.setPageSize(QPageSize(paper_info["page_size_id"]))

            # Yön
            if self.rb_orient_land.isChecked():
                printer.setPageOrientation(QPageLayout.Orientation.Landscape)
            else:
                printer.setPageOrientation(QPageLayout.Orientation.Portrait)

            # Kopya ve Harmanlama
            printer.setCopyCount(self.spn_copies.value())
            printer.setCollateCopies(self.chk_collate.isChecked())

            # İki Taraflı (Duplex)
            two_sided = self.cmb_twosided.currentData()
            if two_sided == "long":
                printer.setDuplex(QPrinter.DuplexMode.DuplexLongSide)
            elif two_sided == "short":
                printer.setDuplex(QPrinter.DuplexMode.DuplexShortSide)
            else:
                printer.setDuplex(QPrinter.DuplexMode.DuplexNone)

            # Gri Tonlama
            if self.chk_grayscale.isChecked():
                printer.setColorMode(QPrinter.ColorMode.GrayScale)
            else:
                printer.setColorMode(QPrinter.ColorMode.Color)

            painter = QPainter(printer)
            page_rect = printer.pageLayout().paintRectPixels(printer.resolution())

            sheets = self._calculate_sheets(target_pages)
            for s_idx, p_list in enumerate(sheets):
                if s_idx > 0:
                    printer.newPage()

                first_p = p_list[0]
                page = self.doc[first_p]
                pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                if self.chk_grayscale.isChecked():
                    qimg = qimg.convertToFormat(QImage.Format.Format_Grayscale8)

                scaled_size = qimg.size().scaled(int(page_rect.width()), int(page_rect.height()), Qt.AspectRatioMode.KeepAspectRatio)
                tx = int(page_rect.left() + (page_rect.width() - scaled_size.width()) / 2)
                ty = int(page_rect.top() + (page_rect.height() - scaled_size.height()) / 2)
                painter.drawImage(QRectF(tx, ty, scaled_size.width(), scaled_size.height()), qimg)

            painter.end()
            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("print_success"))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), LanguageManager.tr("print_failed", error=str(e)))

    def closeEvent(self, event):
        try:
            self._preview_timer.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def reject(self):
        try:
            self._preview_timer.stop()
        except Exception:
            pass
        super().reject()


# Geriye Dönük Uyumluluk için Takma Ad (Alias)
ModernPrintDialog = AuraPrintDialog
