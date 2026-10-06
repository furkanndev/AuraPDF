"""
AuraPDF - Doğrudan Belge Üzerinde Metin Düzenleyici (RevPDF Stili)
=================================================================
Açık belgedeki mevcut metin bloklarını doğrudan görüntüleyici penceresi üzerinde algılayan,
fare ile üzerine gelindiğinde vurgulayan, tıklandığında yerinde (in-place) WYSIWYG düzenleme
ve biçimlendirme araçlarını açan ve değişiklikleri doğrudan PDF belgesine kalıcı olarak
(redaction + insert_textbox ile) uygulayan modern modül.
"""

import os
from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QColorDialog, QMessageBox, QGraphicsRectItem, QGraphicsItem
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF, QSettings, QEvent
from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPainter, QCursor, QTextCursor

import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import THEME_PALETTES, get_current_theme


def get_unicode_font_path(bold: bool = False, italic: bool = False) -> str:
    """Windows ve diğer işletim sistemlerinde Türkçe ve Unicode karakterleri destekleyen font dosyasını döndürür."""
    if bold and italic:
        candidates = [
            r"C:\Windows\Fonts\arialbi.ttf",
            r"C:\Windows\Fonts\calibriz.ttf",
            r"C:\Windows\Fonts\segoeuiz.ttf",
        ]
    elif bold:
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ]
    elif italic:
        candidates = [
            r"C:\Windows\Fonts\ariali.ttf",
            r"C:\Windows\Fonts\calibrii.ttf",
            r"C:\Windows\Fonts\segoeuii.ttf",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
        ]

    for p in candidates:
        if os.path.isfile(p):
            return p
    # Fallback to standard arial if specific variant not found
    fallback = r"C:\Windows\Fonts\arial.ttf"
    if os.path.isfile(fallback):
        return fallback
    return ""


def find_fitting_box(page: fitz.Page, rect: fitz.Rect, text: str, target_fs: float = 12.0,
                      fontfile: str = None, fontname: str = "f_arial") -> Tuple[fitz.Rect, float]:
    """
    Metnin hedef kutu içerisine sığması için kademeli olarak kutuyu genişleten
    veya puntoyu optimize eden hesaplayıcı.
    """
    tmp_doc = fitz.open()
    tmp_page = tmp_doc.new_page(width=max(800.0, page.rect.width), height=max(1200.0, page.rect.height))

    max_page_h = max(200.0, page.rect.height - rect.y0 - 15)
    max_page_w = max(200.0, page.rect.width - rect.x0 - 15)

    # 1. Aşama: Hedef punto ile kutu boyutunu genişleterek dene
    for h_mult in (1.0, 1.25, 1.6, 2.2, 3.2):
        w = min(max_page_w, max(rect.width, rect.width * 1.1))
        h = min(max_page_h, max(rect.height * h_mult, target_fs * 1.5))
        test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
        res = tmp_page.insert_textbox(test_r, text, fontsize=target_fs, fontfile=fontfile, fontname=fontname)
        if res >= 0:
            tmp_doc.close()
            return test_r, target_fs
        tmp_page.clean_contents()

    # 2. Aşama: Puntoyu kademeli küçülterek dene
    for fs in (target_fs * 0.9, target_fs * 0.8, target_fs * 0.7, 9.0, 8.0):
        for h_mult in (1.0, 1.4, 2.0, 3.0):
            w = min(max_page_w, max(rect.width, rect.width * 1.1))
            h = min(max_page_h, max(rect.height * h_mult, fs * 1.5))
            test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
            res = tmp_page.insert_textbox(test_r, text, fontsize=fs, fontfile=fontfile, fontname=fontname)
            if res >= 0:
                tmp_doc.close()
                return test_r, fs
            tmp_page.clean_contents()

    tmp_doc.close()
    fallback_r = fitz.Rect(rect.x0, rect.y0, min(max_page_w + rect.x0, rect.x1 + 60), min(max_page_h + rect.y0, rect.y0 + rect.height * 2.5))
    return fallback_r, max(7.0, target_fs * 0.75)


def extract_page_text_blocks(page: fitz.Page) -> List[Dict[str, Any]]:
    """Sayfadaki tüm metin bloklarını ve font/renk niteliklerini çıkarır."""
    d = page.get_text("dict")
    results = []

    for b_no, b in enumerate(d.get("blocks", [])):
        if b.get("type") != 0:
            continue
        bbox = b.get("bbox")
        if not bbox or len(bbox) < 4:
            continue

        full_text = ""
        sizes: List[float] = []
        fonts: List[str] = []
        colors: List[int] = []
        is_bold = False
        is_italic = False

        for line in b.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                t = span.get("text", "")
                line_text += t
                sz = float(span.get("size", 12.0))
                fn = str(span.get("font", ""))
                col_int = int(span.get("color", 0))
                fl = int(span.get("flags", 0))

                char_cnt = len(t)
                sizes.extend([sz] * char_cnt)
                fonts.extend([fn] * char_cnt)
                colors.extend([col_int] * char_cnt)

                fn_low = fn.lower()
                if (fl & 16) or "bold" in fn_low or "black" in fn_low or "heavy" in fn_low:
                    is_bold = True
                if (fl & 2) or "italic" in fn_low or "oblique" in fn_low:
                    is_italic = True

            full_text += line_text + "\n"

        full_text = full_text.rstrip("\n")
        if not full_text.strip():
            continue

        dom_size = max(set(sizes), key=sizes.count) if sizes else 12.0
        dom_font = max(set(fonts), key=fonts.count) if fonts else "Arial"
        dom_col_int = max(set(colors), key=colors.count) if colors else 0

        r = ((dom_col_int >> 16) & 0xFF) / 255.0
        g = ((dom_col_int >> 8) & 0xFF) / 255.0
        b_val = (dom_col_int & 0xFF) / 255.0

        results.append({
            "block_no": b_no,
            "bbox": fitz.Rect(bbox),
            "text": full_text,
            "font_size": round(dom_size, 1),
            "font_name": dom_font,
            "color_rgb": (r, g, b_val),
            "bold": is_bold,
            "italic": is_italic
        })

    return results


class DirectEditHoverItem(QGraphicsRectItem):
    """Görüntüleyici sahnesinde fare ile üzerine gelinen metin bloğunu vurgulayan şık kesikli çerçeve."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setZValue(95)
        self.setAcceptHoverEvents(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        pen = QPen(QColor(10, 132, 255, 220), 1.6, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(10, 132, 255, 26)))
        self.hide()


class DirectEditBanner(QFrame):
    """
    Doğrudan metin düzenleme modu aktifken görüntüleyici ekranının üstünde beliren,
    kullanıcıya rehberlik eden ve moddan çıkma / gelişmiş pencereyi açma butonları sunan modern bildirim çubuğu.
    """
    def __init__(self, tab_doc):
        super().__init__(tab_doc.view.viewport())
        self.tab_doc = tab_doc
        self.setObjectName("DirectEditBanner")
        self._init_ui()
        self.apply_theme()
        self.reposition()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 12, 8)
        layout.setSpacing(12)

        # İkon
        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(ModernIconFactory.icon_edit_content().pixmap(18, 18))
        layout.addWidget(self.lbl_icon)

        # Başlık ve Açıklama
        self.lbl_title = QLabel(f"<b>{LanguageManager.tr('direct_edit_banner_title')}</b> — {LanguageManager.tr('direct_edit_banner_msg')}")
        self.lbl_title.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # Gelişmiş Düzenleyici (Pencere) Butonu
        self.btn_legacy = QPushButton(LanguageManager.tr("direct_edit_open_legacy"))
        self.btn_legacy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_legacy.clicked.connect(self._on_open_legacy)
        layout.addWidget(self.btn_legacy)

        # Moddan Çık Butonu
        self.btn_exit = QPushButton(LanguageManager.tr("direct_edit_exit_btn"))
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self._on_exit_clicked)
        layout.addWidget(self.btn_exit)

    def apply_theme(self):
        th_name = get_current_theme()
        pal = THEME_PALETTES.get(th_name, THEME_PALETTES["dark"])
        bg = pal["card"]
        border = pal["border"]
        accent = pal["accent"]
        accent_h = pal["accent_hover"]
        fg = pal["text"]
        muted = pal.get("muted", "#94a3b8")

        self.setStyleSheet(f"""
            QFrame#DirectEditBanner {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 20px;
            }}
            QLabel {{
                color: {fg};
                background: transparent;
                border: none;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent_h};
            }}
        """)

    def reposition(self):
        if not self.tab_doc or not self.tab_doc.view:
            return
        vp = self.tab_doc.view.viewport()
        self.adjustSize()
        x = max(10, (vp.width() - self.width()) // 2)
        y = 12
        self.move(x, y)
        self.raise_()

    def _on_open_legacy(self):
        if hasattr(self.tab_doc.main_window, 'open_pdf_content_editor_dialog'):
            self.tab_doc.main_window.open_pdf_content_editor_dialog()

    def _on_exit_clicked(self):
        self.tab_doc.exit_direct_text_edit()


class DirectTextInplaceEditor(QFrame):
    """
    Belge üzerinde seçilen metin bloğunun tam üzerine açılan,
    orijinal metni maskeleyen ve üstünde zengin mini biçimlendirme çubuğu barındıran yerinde düzenleyici.
    """
    def __init__(self, tab_doc, page_idx: int, pdf_rect: fitz.Rect, text: str,
                 font_size: float = 12.0, color_rgb: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 bold: bool = False, italic: bool = False, is_new: bool = False):
        super().__init__(tab_doc.view.viewport())
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.pdf_rect = pdf_rect
        self.orig_text = text
        self.font_size = max(6.0, float(font_size))
        self.chosen_color = color_rgb
        self.is_bold = bold
        self.is_italic = italic
        self.is_new = is_new

        self.setObjectName("DirectTextInplaceEditor")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._init_ui()
        self.apply_theme()
        self.reposition()

        # Metin alanına odaklan ve imleci sona al
        self.txt_edit.setFocus()
        cur = self.txt_edit.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.txt_edit.setTextCursor(cur)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)

        # 1. ÜST BİÇİMLENDİRME VE EYLEM ÇUBUĞU (MINI-HUD)
        self.bar_frame = QFrame()
        self.bar_frame.setObjectName("MiniActionBar")
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(6, 3, 6, 3)
        bar_layout.setSpacing(4)

        # Punto Küçült
        self.btn_dec_size = QPushButton("−")
        self.btn_dec_size.setFixedSize(24, 24)
        self.btn_dec_size.setToolTip(LanguageManager.tr("direct_edit_decrease_size"))
        self.btn_dec_size.clicked.connect(self._on_dec_size)
        bar_layout.addWidget(self.btn_dec_size)

        # Punto Değeri
        self.lbl_size_val = QLabel(f"{int(round(self.font_size))} pt")
        self.lbl_size_val.setFixedWidth(38)
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(self.lbl_size_val)

        # Punto Büyüt
        self.btn_inc_size = QPushButton("+")
        self.btn_inc_size.setFixedSize(24, 24)
        self.btn_inc_size.setToolTip(LanguageManager.tr("direct_edit_increase_size"))
        self.btn_inc_size.clicked.connect(self._on_inc_size)
        bar_layout.addWidget(self.btn_inc_size)

        # Renk Butonu
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(24, 24)
        self.btn_color.setToolTip(LanguageManager.tr("direct_edit_font_color"))
        self._update_color_button()
        self.btn_color.clicked.connect(self._on_choose_color)
        bar_layout.addWidget(self.btn_color)

        # Kalın (B)
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setChecked(self.is_bold)
        self.btn_bold.setFixedSize(24, 24)
        self.btn_bold.setStyleSheet("font-weight: 900; font-size: 11px;")
        self.btn_bold.setToolTip(LanguageManager.tr("direct_edit_bold"))
        self.btn_bold.clicked.connect(self._on_toggle_bold)
        bar_layout.addWidget(self.btn_bold)

        # İtalik (I)
        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setChecked(self.is_italic)
        self.btn_italic.setFixedSize(24, 24)
        self.btn_italic.setStyleSheet("font-style: italic; font-size: 11px; font-weight: bold;")
        self.btn_italic.setToolTip(LanguageManager.tr("direct_edit_italic"))
        self.btn_italic.clicked.connect(self._on_toggle_italic)
        bar_layout.addWidget(self.btn_italic)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(18)
        bar_layout.addWidget(sep)

        # [✓ Uygula / Kaydet]
        self.btn_apply = QPushButton(LanguageManager.tr("direct_edit_apply"))
        self.btn_apply.setObjectName("ApplyBtn")
        self.btn_apply.setIcon(ModernIconFactory.icon_check())
        self.btn_apply.setToolTip(f"{LanguageManager.tr('direct_edit_apply')} (Ctrl+Enter)")
        self.btn_apply.clicked.connect(self.apply_changes)
        bar_layout.addWidget(self.btn_apply)

        # [🗑 Metni Sil]
        if not self.is_new:
            self.btn_delete = QPushButton()
            self.btn_delete.setObjectName("DeleteBtn")
            self.btn_delete.setIcon(ModernIconFactory.icon_trash())
            self.btn_delete.setFixedSize(26, 24)
            self.btn_delete.setToolTip(LanguageManager.tr("direct_edit_delete"))
            self.btn_delete.clicked.connect(self.delete_block)
            bar_layout.addWidget(self.btn_delete)

        # [✕ Vazgeç]
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setIcon(ModernIconFactory.icon_close())
        self.btn_cancel.setFixedSize(26, 24)
        self.btn_cancel.setToolTip(LanguageManager.tr("direct_edit_cancel"))
        self.btn_cancel.clicked.connect(self.cancel_edit)
        bar_layout.addWidget(self.btn_cancel)

        self.main_layout.addWidget(self.bar_frame)

        # 2. METİN DÜZENLEME ALANI
        self.txt_edit = QTextEdit()
        self.txt_edit.setPlainText(self.orig_text)
        self.txt_edit.setPlaceholderText(LanguageManager.tr("direct_edit_placeholder"))
        self.txt_edit.textChanged.connect(self._on_text_changed)
        self.txt_edit.installEventFilter(self)
        self.main_layout.addWidget(self.txt_edit)

        self._apply_editor_font()

    def _update_color_button(self):
        r, g, b = self.chosen_color
        hex_c = f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_c};
                border: 2px solid rgba(255, 255, 255, 0.4);
                border-radius: 12px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def _apply_editor_font(self):
        scaled_size = max(8.0, self.font_size * getattr(self.tab_doc, 'zoom_level', 1.0))
        font = QFont("Arial", int(round(scaled_size)))
        font.setBold(self.is_bold)
        font.setItalic(self.is_italic)
        self.txt_edit.setFont(font)

        r, g, b = self.chosen_color
        hex_c = f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"
        self.txt_edit.setTextColor(QColor(hex_c))

    def apply_theme(self):
        th_name = get_current_theme()
        pal = THEME_PALETTES.get(th_name, THEME_PALETTES["dark"])
        bg = pal["card"]
        border = pal["border"]
        accent = pal["accent"]
        accent_h = pal["accent_hover"]
        fg = pal["text"]

        reading_mode = getattr(self.tab_doc, 'reading_color_mode', 'normal')
        if reading_mode == 'dark':
            txt_bg = "#18181a"
            txt_border = "#0a84ff"
        elif reading_mode == 'sepia':
            txt_bg = "#f6eedc"
            txt_border = "#8b5cf6"
        else:
            txt_bg = "#ffffff"
            txt_border = accent

        self.setStyleSheet(f"""
            QFrame#DirectTextInplaceEditor {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 10px;
            }}
            QFrame#MiniActionBar {{
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {fg};
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                border-color: {accent};
            }}
            QPushButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent_h};
            }}
            QPushButton#ApplyBtn {{
                background-color: {accent};
                color: #ffffff;
                font-weight: bold;
                padding: 3px 10px;
                border: 1px solid {accent_h};
            }}
            QPushButton#ApplyBtn:hover {{
                background-color: {accent_h};
            }}
            QPushButton#DeleteBtn:hover {{
                background-color: #ef4444;
                border-color: #dc2626;
                color: #ffffff;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: rgba(239, 68, 68, 0.4);
                border-color: #ef4444;
            }}
            QTextEdit {{
                background-color: {txt_bg};
                border: 2px solid {txt_border};
                border-radius: 6px;
                padding: 4px;
                selection-background-color: {accent};
            }}
        """)

    def reposition(self):
        """Metin kutusunu PDF'teki koordinatına göre Viewport üzerinde tam konuma oturtur."""
        if not self.tab_doc or not self.tab_doc.view:
            return
        p_info = self.tab_doc.page_positions.get(self.page_idx)
        if not p_info:
            return

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.tab_doc.base_render_dpi

        # PDF koordinatlarını sahne koordinatına çevir
        sx0 = page_left + self.pdf_rect.x0 * dpi
        sy0 = page_top + self.pdf_rect.y0 * dpi
        sx1 = page_left + self.pdf_rect.x1 * dpi
        sy1 = page_top + self.pdf_rect.y1 * dpi

        # Sahne koordinatını görüntüleyici Viewport piksel koordinatına çevir
        tl = self.tab_doc.view.mapFromScene(QPointF(sx0, sy0))
        br = self.tab_doc.view.mapFromScene(QPointF(sx1, sy1))

        box_w = max(260, br.x() - tl.x() + 18)
        content_lines = max(1, self.txt_edit.toPlainText().count('\n') + 1)
        line_h = max(20, int(self.font_size * getattr(self.tab_doc, 'zoom_level', 1.0) * 1.3))
        est_txt_h = max(br.y() - tl.y() + 12, content_lines * line_h + 20)
        total_h = est_txt_h + 46  # bar height

        # Konumlandırma: mini çubuğun sayfa üstünden taşmaması için y koordinatı
        top_y = tl.y() - 42
        if top_y < 5:
            top_y = tl.y()  # Eğer sayfa üstüne sığmıyorsa alta al

        self.setGeometry(tl.x() - 6, top_y, box_w, total_h)
        self.raise_()

    def _on_dec_size(self):
        if self.font_size > 6.0:
            self.font_size = max(6.0, self.font_size - 1.0)
            self.lbl_size_val.setText(f"{int(round(self.font_size))} pt")
            self._apply_editor_font()
            self.reposition()

    def _on_inc_size(self):
        if self.font_size < 96.0:
            self.font_size = min(96.0, self.font_size + 1.0)
            self.lbl_size_val.setText(f"{int(round(self.font_size))} pt")
            self._apply_editor_font()
            self.reposition()

    def _on_choose_color(self):
        r, g, b = self.chosen_color
        init_c = QColor(int(r * 255), int(g * 255), int(b * 255))
        c = QColorDialog.getColor(init_c, self, LanguageManager.tr("direct_edit_font_color"))
        if c.isValid():
            self.chosen_color = (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)
            self._update_color_button()
            self._apply_editor_font()

    def _on_toggle_bold(self):
        self.is_bold = self.btn_bold.isChecked()
        self._apply_editor_font()

    def _on_toggle_italic(self):
        self.is_italic = self.btn_italic.isChecked()
        self._apply_editor_font()

    def _on_text_changed(self):
        self.reposition()

    def eventFilter(self, obj, event):
        if obj == self.txt_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.apply_changes()
                return True
            elif event.key() == Qt.Key.Key_Escape:
                self.cancel_edit()
                return True
        return super().eventFilter(obj, event)

    def apply_changes(self):
        new_text = self.txt_edit.toPlainText().strip()
        if not new_text and not self.is_new:
            self.delete_block()
            return

        self.tab_doc.commit_direct_text_edit(
            self.page_idx, self.pdf_rect, new_text,
            self.font_size, self.chosen_color,
            self.is_bold, self.is_italic, is_new=self.is_new
        )

    def delete_block(self):
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("direct_edit_delete"),
            LanguageManager.tr("direct_edit_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tab_doc.delete_direct_text_block(self.page_idx, self.pdf_rect)

    def cancel_edit(self):
        self.tab_doc.close_inplace_editor()
