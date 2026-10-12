"""
AuraPDF - Sayfa Organize Dialogs (Page Labels & Page Cropping)
==============================================================
Sayfaları organize etme çalışma alanında kullanılan:
1. PageLabelDialog: Sayfa etiketleri ve numaralandırma yapılandırma diyaloğu.
2. CropPageDialog: Sayfa kırpma, kenar boşlukları, görsel önizleme ve beyaz alan kırpma diyaloğu.
"""

from typing import List, Optional, Set, Any
import pymupdf as fitz

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QSpinBox, QComboBox, QPushButton, QRadioButton, QButtonGroup,
    QGroupBox, QFrame, QMessageBox, QWidget, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSize, pyqtSignal, QLineF
from PyQt6.QtGui import (
    QFont, QImage, QPixmap, QPainter, QPen, QBrush, QColor, QPainterPath
)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.modern_stepper import ModernSpinBox


def apply_page_labels_to_doc(
    doc,
    start_p: int,
    end_p: int,
    style_code: Optional[str],
    prefix: str,
    start_num: int
):
    """
    Belirli bir sayfa aralığına sayfa etiketi kuralı uygular.
    PDF standardı gereği startpage=0 kuralının her zaman mevcut olmasını garanti eder.
    Var olan diğer kuralları güvenli şekilde birleştirir ve aralık sonrasında numaralandırmayı sürdürür.
    """
    total = len(doc)
    if total == 0:
        return

    start_p = max(0, min(start_p, total - 1))
    end_p = max(start_p, min(end_p, total - 1))

    new_rule = {
        'startpage': start_p,
        'firstpagenum': max(1, int(start_num)),
        'prefix': prefix or ''
    }
    if style_code:
        new_rule['style'] = style_code

    # Tüm belge tek seferde yapılandırılıyorsa
    if start_p == 0 and end_p >= total - 1:
        doc.set_page_labels([new_rule])
        return

    old_rules = []
    if hasattr(doc, 'get_page_labels'):
        try:
            old_rules = doc.get_page_labels() or []
        except Exception:
            old_rules = []

    # start_p öncesindeki kurallar
    before_rules = [r for r in old_rules if r.get('startpage', 0) < start_p]
    if start_p > 0 and (not before_rules or before_rules[0].get('startpage', 0) != 0):
        before_rules.insert(0, {'startpage': 0, 'firstpagenum': 1, 'style': 'D', 'prefix': ''})

    # end_p sonrasındaki devam kuralı
    after_rule = None
    exact_rules = [r for r in old_rules if r.get('startpage', 0) == end_p + 1]
    if end_p + 1 < total and not exact_rules:
        gov = [r for r in old_rules if r.get('startpage', 0) <= end_p + 1]
        if gov:
            prev = gov[-1]
            offset = (end_p + 1) - prev.get('startpage', 0)
            cont_num = prev.get('firstpagenum', 1) + offset
            after_rule = {
                'startpage': end_p + 1,
                'firstpagenum': max(1, cont_num),
                'prefix': prev.get('prefix', '')
            }
            if 'style' in prev:
                after_rule['style'] = prev['style']
        else:
            after_rule = {
                'startpage': end_p + 1,
                'firstpagenum': end_p + 2,
                'style': 'D',
                'prefix': ''
            }

    # end_p + 1 sonrasındaki diğer kurallar
    later_rules = [r for r in old_rules if r.get('startpage', 0) > end_p + 1]

    final_rules = before_rules + [new_rule]
    if exact_rules:
        final_rules += exact_rules
    elif after_rule:
        final_rules.append(after_rule)
    final_rules += later_rules

    # startpage=0 kuralı kontrolü
    if not final_rules or final_rules[0].get('startpage', 0) != 0:
        final_rules.insert(0, {'startpage': 0, 'firstpagenum': 1, 'style': 'D', 'prefix': ''})

    doc.set_page_labels(final_rules)


class PageLabelDialog(QDialog):
    """
    Sayfa Etiketleri ve Numaralandırma (Page Labels) Yapılandırma Diyaloğu.
    """

    def __init__(self, doc_or_parent=None, selected_pages: Optional[Any] = None, parent=None):
        if hasattr(doc_or_parent, 'doc'):
            parent_widget = parent or (doc_or_parent if isinstance(doc_or_parent, QWidget) else None)
            doc = doc_or_parent.doc
        elif isinstance(doc_or_parent, QWidget) and parent is None:
            parent_widget = doc_or_parent
            doc = getattr(doc_or_parent, 'doc', None)
        else:
            parent_widget = parent
            doc = doc_or_parent
        super().__init__(parent_widget)
        self.doc = doc
        if isinstance(selected_pages, (list, tuple, set)):
            self.selected_pages = sorted(list(selected_pages))
        elif isinstance(selected_pages, int):
            self.selected_pages = [selected_pages]
        else:
            self.selected_pages = []
        self.total_pages = len(doc) if doc else 0
        self.setWindowTitle(LanguageManager.tr("organize_page_label_title"))
        self.setMinimumWidth(500)
        self.resize(520, 480)
        self.setModal(True)
        self._init_ui()
        self._load_current_page_rule()
        apply_dialog_theme(self, parent_widget)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1. Sayfa Aralığı Grubu
        grp_range = QGroupBox(LanguageManager.tr("organize_page_label_range"))
        v_range = QVBoxLayout(grp_range)
        v_range.setSpacing(8)

        self.btn_grp_range = QButtonGroup(self)

        self.rb_all = QRadioButton(LanguageManager.tr("organize_page_label_all") + f" (1 - {self.total_pages})")
        self.btn_grp_range.addButton(self.rb_all)
        v_range.addWidget(self.rb_all)

        has_sel = len(self.selected_pages) > 0
        sel_desc = f" {LanguageManager.tr('organize_crop_pages_count', count=len(self.selected_pages))}" if has_sel else ""
        self.rb_selected = QRadioButton(LanguageManager.tr("organize_page_label_selected") + sel_desc)
        self.rb_selected.setEnabled(has_sel)
        self.btn_grp_range.addButton(self.rb_selected)
        v_range.addWidget(self.rb_selected)

        # Özel Sayfa Aralığı
        h_custom = QHBoxLayout()
        h_custom.setContentsMargins(0, 0, 0, 0)
        self.rb_custom = QRadioButton(LanguageManager.tr("organize_page_label_custom_range"))
        self.btn_grp_range.addButton(self.rb_custom)
        h_custom.addWidget(self.rb_custom)

        h_custom.addSpacing(10)
        h_custom.addWidget(QLabel(LanguageManager.tr("organize_page_label_from")))
        self.spn_from = ModernSpinBox(min_val=1, max_val=max(1, self.total_pages), default_val=1, parent=self)
        self.spn_from.setFixedWidth(70)
        h_custom.addWidget(self.spn_from)

        h_custom.addWidget(QLabel(LanguageManager.tr("organize_page_label_to")))
        self.spn_to = ModernSpinBox(min_val=1, max_val=max(1, self.total_pages), default_val=max(1, self.total_pages), parent=self)
        self.spn_to.setFixedWidth(70)
        h_custom.addWidget(self.spn_to)
        h_custom.addStretch(1)

        v_range.addLayout(h_custom)

        self.rb_all.toggled.connect(self._on_range_mode_changed)
        self.rb_selected.toggled.connect(self._on_range_mode_changed)
        self.rb_custom.toggled.connect(self._on_range_mode_changed)

        if has_sel:
            self.rb_selected.setChecked(True)
            self.spn_from.setValue(min(self.selected_pages) + 1)
            self.spn_to.setValue(max(self.selected_pages) + 1)
        else:
            self.rb_all.setChecked(True)

        self._on_range_mode_changed()
        layout.addWidget(grp_range)

        # 2. Numaralandırma Stili Grubu
        grp_style = QGroupBox(LanguageManager.tr("organize_page_label_style"))
        grid_style = QGridLayout(grp_style)
        grid_style.setSpacing(10)

        # Stil Seçimi
        grid_style.addWidget(QLabel(LanguageManager.tr("organize_page_label_style")), 0, 0)
        self.cmb_style = QComboBox()
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_arabic"), "D")
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_roman_lower"), "r")
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_roman_upper"), "R")
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_alpha_lower"), "a")
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_alpha_upper"), "A")
        self.cmb_style.addItem(LanguageManager.tr("organize_page_label_style_none"), None)
        self.cmb_style.currentIndexChanged.connect(self._update_preview)
        grid_style.addWidget(self.cmb_style, 0, 1)

        # Önek
        grid_style.addWidget(QLabel(LanguageManager.tr("organize_page_label_prefix")), 1, 0)
        self.txt_prefix = QLineEdit()
        self.txt_prefix.setPlaceholderText(LanguageManager.tr("organize_page_label_prefix_placeholder"))
        self.txt_prefix.textChanged.connect(self._update_preview)
        grid_style.addWidget(self.txt_prefix, 1, 1)

        # Başlangıç Numarası
        grid_style.addWidget(QLabel(LanguageManager.tr("organize_page_label_start")), 2, 0)
        self.spn_start = ModernSpinBox(min_val=1, max_val=99999, default_val=1, parent=self)
        self.spn_start.setFixedWidth(100)
        self.spn_start.valueChanged.connect(self._update_preview)
        grid_style.addWidget(self.spn_start, 2, 1)

        layout.addWidget(grp_style)

        # 3. Canlı Önizleme Kutusu
        self.lbl_preview = QLabel()
        self.lbl_preview.setObjectName("LabelPreviewBadge")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("""
            QLabel#LabelPreviewBadge {
                background: rgba(125, 125, 125, 0.12);
                border: 1px dashed rgba(125, 125, 125, 0.35);
                border-radius: 6px;
                padding: 8px;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.lbl_preview)
        self._update_preview()

        # 4. Alt Butonlar
        h_buttons = QHBoxLayout()

        self.btn_reset = QPushButton(LanguageManager.tr("organize_page_label_reset"))
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset_to_default)
        h_buttons.addWidget(self.btn_reset)

        h_buttons.addStretch(1)

        self.btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        h_buttons.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("apply"))
        self.btn_apply.setObjectName("PrimaryBtn")
        self.btn_apply.clicked.connect(self._on_apply)
        h_buttons.addWidget(self.btn_apply)

        layout.addLayout(h_buttons)

    def _on_range_mode_changed(self):
        is_custom = self.rb_custom.isChecked()
        self.spn_from.setEnabled(is_custom)
        self.spn_to.setEnabled(is_custom)

    def _load_current_page_rule(self):
        """Aktif sayfanın veya ilk seçili sayfanın var olan kuralını okuyup alanlara yükler."""
        if not self.doc or self.total_pages == 0:
            return
        active_idx = self.selected_pages[0] if self.selected_pages else 0
        if hasattr(self.doc, 'get_page_labels'):
            try:
                rules = self.doc.get_page_labels() or []
                matching = [r for r in rules if r.get('startpage', 0) <= active_idx]
                if matching:
                    r = matching[-1]
                    code = r.get('style', None)
                    idx = self.cmb_style.findData(code)
                    if idx >= 0:
                        self.cmb_style.setCurrentIndex(idx)
                    self.txt_prefix.setText(r.get('prefix', ''))
                    base_first = r.get('firstpagenum', 1)
                    if r.get('startpage', 0) == active_idx:
                        self.spn_start.setValue(base_first)
                    else:
                        self.spn_start.setValue(base_first + (active_idx - r.get('startpage', 0)))
            except Exception:
                pass

    def _format_sample(self, num: int, style_code: Optional[str], prefix: str) -> str:
        res = ""
        if style_code == "D":
            res = str(num)
        elif style_code == "r":
            res = self._to_roman(num).lower()
        elif style_code == "R":
            res = self._to_roman(num)
        elif style_code == "a":
            res = self._to_alpha(num).lower()
        elif style_code == "A":
            res = self._to_alpha(num)
        return f"{prefix}{res}"

    @staticmethod
    def _to_roman(num: int) -> str:
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ''
        i = 0
        while num > 0 and i < len(val):
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num or "I"

    @staticmethod
    def _to_alpha(num: int) -> str:
        s = ""
        num -= 1
        while num >= 0:
            s = chr(num % 26 + 65) + s
            num = num // 26 - 1
        return s or "A"

    def _update_preview(self):
        style_code = self.cmb_style.currentData()
        prefix = self.txt_prefix.text()
        start = self.spn_start.value()
        s1 = self._format_sample(start, style_code, prefix)
        s2 = self._format_sample(start + 1, style_code, prefix)
        s3 = self._format_sample(start + 2, style_code, prefix)
        self.lbl_preview.setText(LanguageManager.tr("organize_page_label_example", s1=s1, s2=s2, s3=s3))

    def _on_reset_to_default(self):
        """Tüm sayfa etiketlerini varsayılan 1, 2, 3... numaralandırmaya döndürür."""
        if not self.doc or self.total_pages == 0:
            return
        ans = QMessageBox.question(
            self,
            LanguageManager.tr("app_title"),
            LanguageManager.tr("organize_page_label_reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if ans == QMessageBox.StandardButton.Yes:
            try:
                self.doc.set_page_labels([{'startpage': 0, 'firstpagenum': 1, 'style': 'D', 'prefix': ''}])
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")

    def _on_apply(self):
        if not self.doc or self.total_pages == 0:
            self.reject()
            return

        style_code = self.cmb_style.currentData()
        prefix = self.txt_prefix.text()
        start_num = self.spn_start.value()

        # Sayfa aralığını belirle
        if self.rb_all.isChecked():
            start_p = 0
            end_p = self.total_pages - 1
        elif self.rb_selected.isChecked() and self.selected_pages:
            start_p = min(self.selected_pages)
            end_p = max(self.selected_pages)
        elif self.rb_custom.isChecked():
            start_p = min(self.spn_from.value(), self.spn_to.value()) - 1
            end_p = max(self.spn_from.value(), self.spn_to.value()) - 1
        else:
            start_p = 0
            end_p = self.total_pages - 1

        try:
            apply_page_labels_to_doc(
                self.doc,
                start_p=start_p,
                end_p=end_p,
                style_code=style_code,
                prefix=prefix,
                start_num=start_num
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")


# Handle constants
_HANDLE_NONE = 0
_HANDLE_TL = 1
_HANDLE_T = 2
_HANDLE_TR = 3
_HANDLE_R = 4
_HANDLE_BR = 5
_HANDLE_B = 6
_HANDLE_BL = 7
_HANDLE_L = 8
_HANDLE_MOVE = 9
_HANDLE_NEW = 10


class CropPreviewWidget(QWidget):
    """
    Sayfa Kırpma için canlı ve interaktif görsel önizleme bileşeni.
    - PDF sayfasını yüksek netlikte gösterir.
    - Kırpma kutusunu, yarı saydam maskesini ve 8 adet profesyonel tutamaçı çizer.
    - Önizleme üzerinden doğrudan fare ile:
      * 8 tutamaçtan herhangi birini sürükleyerek kenarları/köşeleri yeniden boyutlandırma
      * Kutu içerisinden sürükleyerek tüm kırpma alanını taşıma
      * Sayfa üzerinde boş alandan sürükleyerek yeni kırpma alanı oluşturma
    olanaklarını kusursuz şekilde sunar.
    """
    marginsChanged = pyqtSignal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.page_idx = 0
        self.left_margin = 0.0
        self.top_margin = 0.0
        self.right_margin = 0.0
        self.bottom_margin = 0.0
        self._cached_pixmap = None
        self._page_w = 595.0
        self._page_h = 842.0

        # Fare etkileşimi durumları
        self._drag_mode = _HANDLE_NONE
        self._drag_start_mouse = QPointF()
        self._drag_start_margins = (0.0, 0.0, 0.0, 0.0)
        self._hover_handle = _HANDLE_NONE
        self.setMouseTracking(True)

        self.setMinimumSize(320, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_document(self, doc, page_idx: int = 0):
        self.doc = doc
        self.set_page(page_idx)

    def set_page(self, page_idx: int):
        self.page_idx = page_idx
        self._render_current_page()
        self.update()

    def set_margins(self, left: float, top: float, right: float, bottom: float):
        self.left_margin = max(0.0, float(left))
        self.top_margin = max(0.0, float(top))
        self.right_margin = max(0.0, float(right))
        self.bottom_margin = max(0.0, float(bottom))
        self.update()

    def _render_current_page(self):
        if not self.doc or self.page_idx < 0 or self.page_idx >= len(self.doc):
            self._cached_pixmap = None
            return
        try:
            page = self.doc[self.page_idx]
            mb = page.mediabox
            self._page_w = max(1.0, float(mb.width))
            self._page_h = max(1.0, float(mb.height))
            # 120-150 DPI arası keskin net önizleme
            zoom = min(2.0, max(0.5, 460.0 / max(self._page_w, self._page_h)))
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            self._cached_pixmap = QPixmap.fromImage(qimg)
        except Exception:
            self._cached_pixmap = None

    def _is_dark(self) -> bool:
        return self.palette().window().color().lightness() < 128

    def _get_geometry(self):
        """Mevcut widget boyutuna göre sayfa ve kırpma geometrilerini döndürür."""
        w = self.width()
        h = self.height()
        pad = 20
        avail_w = max(10.0, float(w - pad * 2))
        avail_h = max(10.0, float(h - pad * 2))
        scale = min(avail_w / max(self._page_w, 1.0), avail_h / max(self._page_h, 1.0))
        render_w = self._page_w * scale
        render_h = self._page_h * scale
        px0 = (w - render_w) / 2.0
        py0 = (h - render_h) / 2.0
        page_rect = QRectF(px0, py0, render_w, render_h)

        cw = max(5.0, self._page_w - self.left_margin - self.right_margin)
        ch = max(5.0, self._page_h - self.top_margin - self.bottom_margin)
        cx0 = px0 + self.left_margin * scale
        cy0 = py0 + self.top_margin * scale
        cx1 = cx0 + cw * scale
        cy1 = cy0 + ch * scale
        crop_rect = QRectF(cx0, cy0, max(2.0, cx1 - cx0), max(2.0, cy1 - cy0))

        return page_rect, crop_rect, scale, px0, py0

    def _get_handles(self, crop_rect: QRectF) -> dict:
        """8 adet tutamaç merkez noktasını döndürür."""
        cx0 = crop_rect.left()
        cy0 = crop_rect.top()
        cx1 = crop_rect.right()
        cy1 = crop_rect.bottom()
        mx = (cx0 + cx1) / 2.0
        my = (cy0 + cy1) / 2.0
        return {
            _HANDLE_TL: QPointF(cx0, cy0),
            _HANDLE_T:  QPointF(mx, cy0),
            _HANDLE_TR: QPointF(cx1, cy0),
            _HANDLE_R:  QPointF(cx1, my),
            _HANDLE_BR: QPointF(cx1, cy1),
            _HANDLE_B:  QPointF(mx, cy1),
            _HANDLE_BL: QPointF(cx0, cy1),
            _HANDLE_L:  QPointF(cx0, my),
        }

    def _hit_test(self, pos: QPointF) -> int:
        """Verilen fare noktasına göre hedef tutamaç veya bölgeyi tespit eder."""
        if not self._cached_pixmap:
            return _HANDLE_NONE

        page_rect, crop_rect, scale, px0, py0 = self._get_geometry()
        handles = self._get_handles(crop_rect)

        hit_tol = 10.0
        # 1. Önce köşeleri kontrol et (daha spesifik)
        for hid in (_HANDLE_TL, _HANDLE_TR, _HANDLE_BR, _HANDLE_BL):
            pt = handles[hid]
            if (pos - pt).manhattanLength() <= hit_tol * 1.5 and QLineF(pos, pt).length() <= hit_tol:
                return hid

        # 2. Kenar orta noktalarını kontrol et
        for hid in (_HANDLE_T, _HANDLE_R, _HANDLE_B, _HANDLE_L):
            pt = handles[hid]
            if (pos - pt).manhattanLength() <= hit_tol * 1.5 and QLineF(pos, pt).length() <= hit_tol:
                return hid

        # 3. Kırpma kutusunun içi (Taşıma modu)
        if crop_rect.contains(pos):
            return _HANDLE_MOVE

        # 4. Sayfa içi boş alan (Yeni kırpma kutusu çizme modu)
        if page_rect.contains(pos):
            return _HANDLE_NEW

        return _HANDLE_NONE

    def _update_cursor(self, handle_id: int):
        """Etkileşim durumuna göre fare imlecini günceller."""
        if handle_id in (_HANDLE_TL, _HANDLE_BR):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle_id in (_HANDLE_TR, _HANDLE_BL):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle_id in (_HANDLE_T, _HANDLE_B):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle_id in (_HANDLE_L, _HANDLE_R):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif handle_id == _HANDLE_MOVE:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        elif handle_id == _HANDLE_NEW:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._cached_pixmap:
            pos = event.position()
            target = self._hit_test(pos)
            if target != _HANDLE_NONE:
                self._drag_mode = target
                self._drag_start_mouse = pos
                self._drag_start_margins = (self.left_margin, self.top_margin, self.right_margin, self.bottom_margin)
                self._update_cursor(target)
                self.update()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._drag_mode == _HANDLE_NONE:
            target = self._hit_test(pos)
            if target != self._hover_handle:
                self._hover_handle = target
                self._update_cursor(target)
                self.update()
            super().mouseMoveEvent(event)
            return

        page_rect, crop_rect, scale, px0, py0 = self._get_geometry()
        if scale <= 0:
            return

        dx = pos.x() - self._drag_start_mouse.x()
        dy = pos.y() - self._drag_start_mouse.y()
        pt_dx = dx / scale
        pt_dy = dy / scale

        start_l, start_t, start_r, start_b = self._drag_start_margins
        min_sz = 15.0

        if self._drag_mode == _HANDLE_MOVE:
            box_w = self._page_w - start_l - start_r
            box_h = self._page_h - start_t - start_b
            new_l = max(0.0, min(self._page_w - box_w, start_l + pt_dx))
            new_r = max(0.0, self._page_w - box_w - new_l)
            new_t = max(0.0, min(self._page_h - box_h, start_t + pt_dy))
            new_b = max(0.0, self._page_h - box_h - new_t)
            self.set_margins(new_l, new_t, new_r, new_b)
            self.marginsChanged.emit(int(round(new_l)), int(round(new_t)), int(round(new_r)), int(round(new_b)))

        elif self._drag_mode == _HANDLE_NEW:
            # Serbest çizimle yeni dikdörtgen oluştur
            x0 = max(page_rect.left(), min(page_rect.right(), min(self._drag_start_mouse.x(), pos.x())))
            x1 = max(page_rect.left(), min(page_rect.right(), max(self._drag_start_mouse.x(), pos.x())))
            y0 = max(page_rect.top(), min(page_rect.bottom(), min(self._drag_start_mouse.y(), pos.y())))
            y1 = max(page_rect.top(), min(page_rect.bottom(), max(self._drag_start_mouse.y(), pos.y())))

            if (x1 - x0) >= 10 and (y1 - y0) >= 10:
                new_l = max(0.0, (x0 - px0) / scale)
                new_t = max(0.0, (y0 - py0) / scale)
                new_r = max(0.0, self._page_w - (x1 - px0) / scale)
                new_b = max(0.0, self._page_h - (y1 - py0) / scale)
                self.set_margins(new_l, new_t, new_r, new_b)
                self.marginsChanged.emit(int(round(new_l)), int(round(new_t)), int(round(new_r)), int(round(new_b)))

        else:
            # Tutamaç ile kenar veya köşe boyutlandırma
            new_l, new_t, new_r, new_b = start_l, start_t, start_r, start_b

            if self._drag_mode in (_HANDLE_L, _HANDLE_TL, _HANDLE_BL):
                new_l = max(0.0, min(self._page_w - start_r - min_sz, start_l + pt_dx))
            if self._drag_mode in (_HANDLE_R, _HANDLE_TR, _HANDLE_BR):
                new_r = max(0.0, min(self._page_w - start_l - min_sz, start_r - pt_dx))
            if self._drag_mode in (_HANDLE_T, _HANDLE_TL, _HANDLE_TR):
                new_t = max(0.0, min(self._page_h - start_b - min_sz, start_t + pt_dy))
            if self._drag_mode in (_HANDLE_B, _HANDLE_BL, _HANDLE_BR):
                new_b = max(0.0, min(self._page_h - start_t - min_sz, start_b - pt_dy))

            self.set_margins(new_l, new_t, new_r, new_b)
            self.marginsChanged.emit(int(round(new_l)), int(round(new_t)), int(round(new_r)), int(round(new_b)))

        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_mode != _HANDLE_NONE:
            self._drag_mode = _HANDLE_NONE
            self._hover_handle = self._hit_test(event.position())
            self._update_cursor(self._hover_handle)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._hover_handle = _HANDLE_NONE
        if self._drag_mode == _HANDLE_NONE:
            self.unsetCursor()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()

        # Canvas arka planı
        bg_color = QColor(24, 24, 27) if self._is_dark() else QColor(241, 245, 249)
        painter.fillRect(0, 0, w, h, bg_color)

        if not self._cached_pixmap or self._page_w <= 0 or self._page_h <= 0:
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, LanguageManager.tr("organize_crop_preview_title"))
            painter.end()
            return

        page_rect, crop_rect, scale, px0, py0 = self._get_geometry()

        # 1. Sayfa Yumuşak Kağıt Gölgesi
        shadow_rect = QRectF(px0 + 3, py0 + 4, page_rect.width(), page_rect.height())
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 45 if self._is_dark() else 25))

        # 2. Sayfa Pixmap Çizimi
        painter.drawPixmap(page_rect.toRect(), self._cached_pixmap)

        # 3. Sayfa Dış Sınırı
        painter.setPen(QPen(QColor(100, 116, 139, 80), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(page_rect)

        # 4. Kırpılacak Dış Alan Maskesi (Yarı saydam karanlık katman)
        has_crop = (self.left_margin > 0 or self.top_margin > 0 or self.right_margin > 0 or self.bottom_margin > 0)
        if has_crop or self._drag_mode != _HANDLE_NONE:
            path_page = QPainterPath()
            path_page.addRect(page_rect)
            path_crop = QPainterPath()
            path_crop.addRect(crop_rect)
            mask_path = path_page.subtracted(path_crop)
            painter.fillPath(mask_path, QBrush(QColor(15, 23, 42, 175)))

        # 5. Kural Üçte-Bir Çizgileri (Rule of Thirds Grid - Hover veya Drag esnasında)
        accent = QColor("#0284c7") if not self._is_dark() else QColor("#38bdf8")
        if self._drag_mode != _HANDLE_NONE or self._hover_handle != _HANDLE_NONE:
            grid_pen = QPen(QColor(255, 255, 255, 50) if self._is_dark() else QColor(2, 132, 199, 45), 1, Qt.PenStyle.DashLine)
            painter.setPen(grid_pen)
            cw = crop_rect.width()
            ch = crop_rect.height()
            painter.drawLine(QPointF(crop_rect.left() + cw / 3.0, crop_rect.top()), QPointF(crop_rect.left() + cw / 3.0, crop_rect.bottom()))
            painter.drawLine(QPointF(crop_rect.left() + 2 * cw / 3.0, crop_rect.top()), QPointF(crop_rect.left() + 2 * cw / 3.0, crop_rect.bottom()))
            painter.drawLine(QPointF(crop_rect.left(), crop_rect.top() + ch / 3.0), QPointF(crop_rect.right(), crop_rect.top() + ch / 3.0))
            painter.drawLine(QPointF(crop_rect.left(), crop_rect.top() + 2 * ch / 3.0), QPointF(crop_rect.right(), crop_rect.top() + 2 * ch / 3.0))

        # 6. Kırpma Çerçevesi (Canlı Gösterge)
        pen_crop = QPen(accent, 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_crop)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_rect)

        # 7. 8 Adet Profesyonel Tutamaç Çizimi
        handles = self._get_handles(crop_rect)

        handle_pen = QPen(QColor(255, 255, 255), 1.8)
        handle_brush = QBrush(accent)
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)

        # 4 Köşe Tutamacı (Kare/Yuvarlatılmış 10x10)
        c_sz = 10.0
        for hid in (_HANDLE_TL, _HANDLE_TR, _HANDLE_BR, _HANDLE_BL):
            pt = handles[hid]
            painter.drawRoundedRect(QRectF(pt.x() - c_sz / 2.0, pt.y() - c_sz / 2.0, c_sz, c_sz), 2.5, 2.5)

        # 4 Kenar Tutamacı (Hap/Pill şeklinde)
        # Üst ve Alt (yatay kapsül: 16x6 px)
        for hid in (_HANDLE_T, _HANDLE_B):
            pt = handles[hid]
            painter.drawRoundedRect(QRectF(pt.x() - 8.0, pt.y() - 3.5, 16.0, 7.0), 3.5, 3.5)

        # Sol ve Sağ (dikey kapsül: 6x16 px)
        for hid in (_HANDLE_L, _HANDLE_R):
            pt = handles[hid]
            painter.drawRoundedRect(QRectF(pt.x() - 3.5, pt.y() - 8.0, 7.0, 16.0), 3.5, 3.5)

        # 8. Kırpma Alanı Boyut Rozeti
        cw_pt = max(5.0, self._page_w - self.left_margin - self.right_margin)
        ch_pt = max(5.0, self._page_h - self.top_margin - self.bottom_margin)
        badge_text = f"{cw_pt:.0f} × {ch_pt:.0f} pt"
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(badge_text) + 14
        th = fm.height() + 6
        badge_x = crop_rect.center().x() - tw / 2.0
        badge_y = crop_rect.bottom() - th - 8
        if badge_y < crop_rect.top() + 6:
            badge_y = crop_rect.center().y() - th / 2.0

        badge_rect = QRectF(badge_x, badge_y, tw, th)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 215)))
        painter.drawRoundedRect(badge_rect, 4, 4)

        painter.setPen(QColor(255, 255, 255))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.end()


class CropPageDialog(QDialog):
    """
    Sayfa Kırpma (Crop Margins, Live Preview & Auto-Crop) Yapılandırma Diyaloğu.
    """

    def __init__(self, doc_or_parent=None, current_page_idx: int = 0, selected_pages: Optional[Any] = None, parent=None):
        if hasattr(doc_or_parent, 'doc'):
            parent_widget = parent or (doc_or_parent if isinstance(doc_or_parent, QWidget) else None)
            doc = doc_or_parent.doc
        elif isinstance(doc_or_parent, QWidget) and parent is None:
            parent_widget = doc_or_parent
            doc = getattr(doc_or_parent, 'doc', None)
        else:
            parent_widget = parent
            doc = doc_or_parent
        super().__init__(parent_widget)
        self.doc = doc
        self.total_pages = len(doc) if doc else 0
        p_idx = getattr(current_page_idx, 'number', current_page_idx)
        if not isinstance(p_idx, int):
            try:
                p_idx = int(p_idx)
            except Exception:
                p_idx = 0
        self.current_page_idx = max(0, min(p_idx, self.total_pages - 1)) if self.total_pages > 0 else 0
        self.preview_page_idx = self.current_page_idx
        if isinstance(selected_pages, (list, tuple, set)):
            self.selected_pages = sorted(list(selected_pages))
        elif isinstance(selected_pages, int):
            self.selected_pages = [selected_pages]
        else:
            self.selected_pages = [self.current_page_idx]

        self.setWindowTitle(LanguageManager.tr("organize_crop_page_title"))
        self.setMinimumWidth(820)
        self.setMinimumHeight(520)
        self.resize(860, 560)
        self.setModal(True)
        self._init_ui()
        apply_dialog_theme(self, parent_widget)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        # Mevcut sayfanın var olan kırpma durumunu oku
        init_l, init_t, init_r, init_b = 0, 0, 0, 0
        if self.doc and self.current_page_idx < len(self.doc):
            p = self.doc[self.current_page_idx]
            mb = p.mediabox
            cb = p.cropbox
            if cb != mb:
                init_l = max(0, int(round(cb.x0 - mb.x0)))
                init_t = max(0, int(round(cb.y0 - mb.y0)))
                init_r = max(0, int(round(mb.x1 - cb.x1)))
                init_b = max(0, int(round(mb.y1 - cb.y1)))

        # ======================================================================
        # SOL KOLON: CANLI GÖRSEL ÖNİZLEME (PREVIEW)
        # ======================================================================
        grp_preview = QGroupBox(LanguageManager.tr("organize_crop_preview_title"))
        v_preview = QVBoxLayout(grp_preview)
        v_preview.setContentsMargins(10, 12, 10, 10)
        v_preview.setSpacing(10)

        self.preview_widget = CropPreviewWidget(self)
        self.preview_widget.set_document(self.doc, self.preview_page_idx)
        self.preview_widget.set_margins(init_l, init_t, init_r, init_b)
        self.preview_widget.marginsChanged.connect(self._on_preview_margins_changed)
        v_preview.addWidget(self.preview_widget, stretch=1)

        # Önizleme Sayfa Navigasyon Çubuğu (◀ Sayfa 1 / 10 ▶)
        h_nav = QHBoxLayout()
        h_nav.setContentsMargins(4, 0, 4, 0)
        h_nav.setSpacing(8)

        self.btn_prev_page = QToolButton()
        self.btn_prev_page.setIcon(ModernIconFactory.icon_move_left())
        self.btn_prev_page.setIconSize(QSize(14, 14))
        self.btn_prev_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_page.setEnabled(self.preview_page_idx > 0)
        self.btn_prev_page.clicked.connect(self._on_prev_page)
        h_nav.addWidget(self.btn_prev_page)

        self.lbl_page_nav = QLabel(LanguageManager.tr("organize_crop_preview_page", curr=self.preview_page_idx + 1, total=self.total_pages))
        self.lbl_page_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page_nav.setStyleSheet("font-weight: 600; font-size: 13px;")
        h_nav.addWidget(self.lbl_page_nav, stretch=1)

        self.btn_next_page = QToolButton()
        self.btn_next_page.setIcon(ModernIconFactory.icon_move_right())
        self.btn_next_page.setIconSize(QSize(14, 14))
        self.btn_next_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_page.setEnabled(self.preview_page_idx < self.total_pages - 1)
        self.btn_next_page.clicked.connect(self._on_next_page)
        h_nav.addWidget(self.btn_next_page)

        v_preview.addLayout(h_nav)

        lbl_hint = QLabel(LanguageManager.tr("organize_crop_drag_hint"))
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("font-size: 11px; color: rgba(148, 163, 184, 0.85); padding: 2px;")
        v_preview.addWidget(lbl_hint)
        main_layout.addWidget(grp_preview, stretch=1)

        # ======================================================================
        # SAĞ KOLON: KIRPMA KONTROLLERİ VE AYARLARI
        # ======================================================================
        controls_widget = QWidget(self)
        controls_widget.setFixedWidth(340)
        v_controls = QVBoxLayout(controls_widget)
        v_controls.setContentsMargins(0, 0, 0, 0)
        v_controls.setSpacing(12)

        # 1. Kenar Boşlukları Grubu
        grp_margins = QGroupBox(LanguageManager.tr("organize_crop_margins"))
        grid_m = QGridLayout(grp_margins)
        grid_m.setSpacing(8)

        # Üst
        grid_m.addWidget(QLabel(LanguageManager.tr("organize_crop_top")), 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.spn_top = ModernSpinBox()
        self.spn_top.setRange(0, 1000)
        self.spn_top.setValue(init_t)
        self.spn_top.valueChanged.connect(self._on_margins_changed)
        grid_m.addWidget(self.spn_top, 0, 2)

        # Sol & Sağ
        grid_m.addWidget(QLabel(LanguageManager.tr("organize_crop_left")), 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self.spn_left = ModernSpinBox()
        self.spn_left.setRange(0, 1000)
        self.spn_left.setValue(init_l)
        self.spn_left.valueChanged.connect(self._on_margins_changed)
        grid_m.addWidget(self.spn_left, 1, 1)

        grid_m.addWidget(QLabel(LanguageManager.tr("organize_crop_right")), 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.spn_right = ModernSpinBox()
        self.spn_right.setRange(0, 1000)
        self.spn_right.setValue(init_r)
        self.spn_right.valueChanged.connect(self._on_margins_changed)
        grid_m.addWidget(self.spn_right, 1, 3)

        # Alt
        grid_m.addWidget(QLabel(LanguageManager.tr("organize_crop_bottom")), 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        self.spn_bottom = ModernSpinBox()
        self.spn_bottom.setRange(0, 1000)
        self.spn_bottom.setValue(init_b)
        self.spn_bottom.valueChanged.connect(self._on_margins_changed)
        grid_m.addWidget(self.spn_bottom, 2, 2)

        # Hızlı Eylem Butonları
        h_quick = QHBoxLayout()
        self.btn_auto_crop = QPushButton(" " + LanguageManager.tr("organize_crop_auto_margins"))
        self.btn_auto_crop.setIcon(ModernIconFactory.icon_auto_crop())
        self.btn_auto_crop.clicked.connect(self._on_auto_detect)
        h_quick.addWidget(self.btn_auto_crop)

        self.btn_reset_crop = QPushButton(LanguageManager.tr("organize_crop_reset"))
        self.btn_reset_crop.clicked.connect(self._on_reset_margins)
        h_quick.addWidget(self.btn_reset_crop)

        grid_m.addLayout(h_quick, 3, 0, 1, 4)
        v_controls.addWidget(grp_margins)

        # 2. Boyut Bilgi Çubuğu
        self.lbl_dims = QLabel()
        self.lbl_dims.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_dims.setWordWrap(True)
        self.lbl_dims.setStyleSheet("""
            background: rgba(125, 125, 125, 0.1);
            border-radius: 4px;
            padding: 6px;
            font-size: 12px;
            font-weight: 600;
        """)
        v_controls.addWidget(self.lbl_dims)
        self._update_dim_label()

        # 3. Kapsam (Uygulama Hedefi)
        grp_scope = QGroupBox(LanguageManager.tr("organize_crop_apply_to"))
        v_scope = QVBoxLayout(grp_scope)
        v_scope.setSpacing(6)

        self.btn_grp_scope = QButtonGroup(self)

        has_sel = len(self.selected_pages) > 0
        sel_text = LanguageManager.tr("organize_crop_apply_selected") + (f" {LanguageManager.tr('organize_crop_pages_count', count=len(self.selected_pages))}" if has_sel else "")
        self.rb_selected = QRadioButton(sel_text)
        self.rb_selected.setEnabled(has_sel)
        self.btn_grp_scope.addButton(self.rb_selected)
        v_scope.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(LanguageManager.tr("organize_crop_apply_all") + f" {LanguageManager.tr('organize_crop_pages_count', count=self.total_pages)}")
        self.btn_grp_scope.addButton(self.rb_all)
        v_scope.addWidget(self.rb_all)

        self.rb_odd = QRadioButton(LanguageManager.tr("organize_crop_apply_odd"))
        self.btn_grp_scope.addButton(self.rb_odd)
        v_scope.addWidget(self.rb_odd)

        self.rb_even = QRadioButton(LanguageManager.tr("organize_crop_apply_even"))
        self.btn_grp_scope.addButton(self.rb_even)
        v_scope.addWidget(self.rb_even)

        if has_sel:
            self.rb_selected.setChecked(True)
        else:
            self.rb_all.setChecked(True)

        v_controls.addWidget(grp_scope)
        v_controls.addStretch(1)

        # 4. Alt Butonlar
        h_buttons = QHBoxLayout()
        h_buttons.addStretch(1)

        self.btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        h_buttons.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("apply"))
        self.btn_apply.setObjectName("PrimaryBtn")
        self.btn_apply.clicked.connect(self._on_apply)
        h_buttons.addWidget(self.btn_apply)

        v_controls.addLayout(h_buttons)
        main_layout.addWidget(controls_widget)

    def _on_prev_page(self):
        if self.preview_page_idx > 0:
            self.preview_page_idx -= 1
            self._update_preview_page()

    def _on_next_page(self):
        if self.preview_page_idx < self.total_pages - 1:
            self.preview_page_idx += 1
            self._update_preview_page()

    def _update_preview_page(self):
        self.btn_prev_page.setEnabled(self.preview_page_idx > 0)
        self.btn_next_page.setEnabled(self.preview_page_idx < self.total_pages - 1)
        self.lbl_page_nav.setText(
            LanguageManager.tr("organize_crop_preview_page", curr=self.preview_page_idx + 1, total=self.total_pages)
        )
        self.preview_widget.set_page(self.preview_page_idx)
        self._update_dim_label()

    def _on_preview_margins_changed(self, l: int, t: int, r: int, b: int):
        """Önizleme üzerinden fare ile sürüklenen yeni kenar boşluklarını spinbox'lara aktarır."""
        self.spn_left.blockSignals(True)
        self.spn_top.blockSignals(True)
        self.spn_right.blockSignals(True)
        self.spn_bottom.blockSignals(True)
        self.spn_left.setValue(l)
        self.spn_top.setValue(t)
        self.spn_right.setValue(r)
        self.spn_bottom.setValue(b)
        self.spn_left.blockSignals(False)
        self.spn_top.blockSignals(False)
        self.spn_right.blockSignals(False)
        self.spn_bottom.blockSignals(False)
        self._update_dim_label()

    def _on_margins_changed(self):
        l = self.spn_left.value()
        r = self.spn_right.value()
        t = self.spn_top.value()
        b = self.spn_bottom.value()
        self.preview_widget.set_margins(l, t, r, b)
        self._update_dim_label()

    def _update_dim_label(self):
        if not self.doc or self.preview_page_idx >= len(self.doc):
            return
        page = self.doc[self.preview_page_idx]
        orig_w = round(page.mediabox.width, 1)
        orig_h = round(page.mediabox.height, 1)

        l = self.spn_left.value()
        r = self.spn_right.value()
        t = self.spn_top.value()
        b = self.spn_bottom.value()

        crop_w = max(5.0, round(orig_w - l - r, 1))
        crop_h = max(5.0, round(orig_h - t - b, 1))

        self.lbl_dims.setText(
            LanguageManager.tr(
                "organize_crop_original_cropped_fmt",
                orig_w=orig_w, orig_h=orig_h,
                crop_w=crop_w, crop_h=crop_h
            )
        )

    def _on_reset_margins(self):
        self.spn_top.setValue(0)
        self.spn_bottom.setValue(0)
        self.spn_left.setValue(0)
        self.spn_right.setValue(0)
        self._on_margins_changed()

    def _on_auto_detect(self):
        if not self.doc or self.preview_page_idx >= len(self.doc):
            return
        page = self.doc[self.preview_page_idx]
        w = page.mediabox.width
        h = page.mediabox.height

        content_rect = fitz.Rect()

        # 1. Metin blokları
        try:
            for b in page.get_text("blocks"):
                if len(b) >= 4:
                    rb = fitz.Rect(b[:4])
                    if rb.width < w * 0.98 or rb.height < h * 0.98:
                        content_rect |= rb
        except Exception:
            pass

        # 2. Vektörel çizimler
        try:
            for d in page.get_drawings():
                dr = d.get("rect")
                if dr and (dr.width < w * 0.95 or dr.height < h * 0.95):
                    content_rect |= dr
        except Exception:
            pass

        # 3. Görseller
        try:
            for img_info in page.get_images():
                xref = img_info[0]
                for r in page.get_image_rects(xref):
                    if r.width < w * 0.95 or r.height < h * 0.95:
                        content_rect |= r
        except Exception:
            pass

        # 4. Piksel bazlı en hassas tarama (numpy mevcut ise)
        if not content_rect.is_valid or content_rect.is_empty or (content_rect.width >= w * 0.95 and content_rect.height >= h * 0.95):
            try:
                import numpy as np
                scale = min(1.0, 300.0 / max(w, 1.0))
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                non_white = np.any(arr[:, :, :3] < 242, axis=2)
                y_idx, x_idx = np.where(non_white)
                if len(x_idx) > 0 and len(y_idx) > 0:
                    px0 = float(x_idx.min()) / scale
                    px1 = float(x_idx.max() + 1) / scale
                    py0 = float(y_idx.min()) / scale
                    py1 = float(y_idx.max() + 1) / scale
                    content_rect = fitz.Rect(px0, py0, px1, py1)
            except Exception:
                pass

        if content_rect.is_valid and not content_rect.is_empty:
            pad = 12
            left = max(0, int(content_rect.x0 - pad))
            top = max(0, int(content_rect.y0 - pad))
            right = max(0, int(w - (content_rect.x1 + pad)))
            bottom = max(0, int(h - (content_rect.y1 + pad)))

            if left == 0 and top == 0 and right == 0 and bottom == 0:
                QMessageBox.information(
                    self,
                    LanguageManager.tr("app_title"),
                    LanguageManager.tr("organize_crop_no_margin_found")
                )
                return

            self.spn_left.setValue(left)
            self.spn_top.setValue(top)
            self.spn_right.setValue(right)
            self.spn_bottom.setValue(bottom)
            self._on_margins_changed()
        else:
            QMessageBox.information(
                self,
                LanguageManager.tr("app_title"),
                LanguageManager.tr("organize_crop_no_margin_found")
            )

    def _on_apply(self):
        if not self.doc or self.total_pages == 0:
            self.reject()
            return

        l = self.spn_left.value()
        r = self.spn_right.value()
        t = self.spn_top.value()
        b = self.spn_bottom.value()

        # Hedef sayfaları belirle
        target_pages: List[int] = []
        if self.rb_selected.isChecked():
            target_pages = [p for p in self.selected_pages if 0 <= p < self.total_pages]
        elif self.rb_all.isChecked():
            target_pages = list(range(self.total_pages))
        elif self.rb_odd.isChecked():
            target_pages = [p for p in range(self.total_pages) if (p + 1) % 2 != 0]
        elif self.rb_even.isChecked():
            target_pages = [p for p in range(self.total_pages) if (p + 1) % 2 == 0]

        if not target_pages:
            self.reject()
            return

        try:
            is_reset = (l == 0 and r == 0 and t == 0 and b == 0)

            for p_idx in target_pages:
                page = self.doc[p_idx]
                mb = page.mediabox
                if is_reset:
                    page.set_cropbox(mb)
                else:
                    new_crop = fitz.Rect(
                        mb.x0 + l,
                        mb.y0 + t,
                        mb.x1 - r,
                        mb.y1 - b
                    )
                    if new_crop.is_valid and not new_crop.is_empty and new_crop.width >= 10 and new_crop.height >= 10:
                        page.set_cropbox(new_crop)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")
