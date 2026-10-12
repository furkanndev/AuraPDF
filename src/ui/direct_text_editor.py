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
    QTextEdit, QColorDialog, QMessageBox, QGraphicsRectItem, QGraphicsItem,
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSettings, QEvent
from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPainter, QCursor, QTextCursor, QTextCharFormat

import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import THEME_PALETTES, get_current_theme


def get_unicode_font_path(font_name: str = "Arial", bold: bool = False, italic: bool = False) -> str:
    """Windows ve diğer işletim sistemlerinde Türkçe ve Unicode karakterleri destekleyen font dosyasını döndürür."""
    fn_low = (font_name or "").lower().replace(" ", "").replace("-", "")

    # Windows sistem fontları haritası: (normal, bold, italic, bold_italic)
    FONT_MAP = {
        "calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
        "segoe": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
        "times": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
        "arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
        "helvetica": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
        "verdana": ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
        "tahoma": ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
        "trebuchet": ("trebuc.ttf", "trebucbd.ttf", "trebucit.ttf", "trebucbi.ttf"),
        "georgia": ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
        "consolas": ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
        "courier": ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
        "gothic": ("gothic.ttf", "gothicb.ttf", "gothici.ttf", "gothicbi.ttf"),
        "century": ("century.ttf", "century.ttf", "century.ttf", "century.ttf"),
        "aptos": ("aptos.ttf", "aptos-bold.ttf", "aptos-italic.ttf", "aptos-bolditalic.ttf"),
    }

    windir = os.environ.get("WINDIR", r"C:\Windows")
    fonts_dir = os.path.join(windir, "Fonts")

    target_tuple = None
    for key, files in FONT_MAP.items():
        if key in fn_low:
            target_tuple = files
            break

    if target_tuple:
        if bold and italic:
            fname = target_tuple[3]
        elif bold:
            fname = target_tuple[1]
        elif italic:
            fname = target_tuple[2]
        else:
            fname = target_tuple[0]

        candidate = os.path.join(fonts_dir, fname)
        if os.path.isfile(candidate):
            return candidate
            
    # Eğer hardcoded listede bulunamadıysa, sistemdeki fontları tara (Smart Font Matching)
    import difflib
    try:
        all_fonts = [f for f in os.listdir(fonts_dir) if f.lower().endswith(".ttf")]
        # Font ismine benzeyenleri bul
        matches = difflib.get_close_matches(fn_low + ".ttf", [f.lower() for f in all_fonts], n=5, cutoff=0.75)
        if matches:
            # Bold/Italic önceliğine göre en uygun olanı seç
            best_match = matches[0]
            for m in matches:
                is_m_bold = "b" in m.replace(fn_low, "") or "bold" in m
                is_m_italic = "i" in m.replace(fn_low, "") or "italic" in m
                if is_m_bold == bold and is_m_italic == italic:
                    best_match = m
                    break
            
            # Orijinal dosya adının büyük/küçük harf halini bul
            for f in all_fonts:
                if f.lower() == best_match:
                    return os.path.join(fonts_dir, f)
    except Exception:
        pass

    # Genel adaylar listesi (fallback)
    if bold and italic:
        candidates = [
            os.path.join(fonts_dir, "arialbi.ttf"),
            os.path.join(fonts_dir, "calibriz.ttf"),
            os.path.join(fonts_dir, "segoeuiz.ttf"),
        ]
    elif bold:
        candidates = [
            os.path.join(fonts_dir, "arialbd.ttf"),
            os.path.join(fonts_dir, "calibrib.ttf"),
            os.path.join(fonts_dir, "segoeuib.ttf"),
        ]
    elif italic:
        candidates = [
            os.path.join(fonts_dir, "ariali.ttf"),
            os.path.join(fonts_dir, "calibrii.ttf"),
            os.path.join(fonts_dir, "segoeuii.ttf"),
        ]
    else:
        candidates = [
            os.path.join(fonts_dir, "arial.ttf"),
            os.path.join(fonts_dir, "calibri.ttf"),
            os.path.join(fonts_dir, "segoeui.ttf"),
            os.path.join(fonts_dir, "tahoma.ttf"),
        ]

    for p in candidates:
        if os.path.isfile(p):
            return p

    fallback = os.path.join(fonts_dir, "arial.ttf")
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
    if fontfile and os.path.isfile(fontfile):
        try:
            tmp_page.insert_font(fontname=fontname, fontfile=fontfile)
        except Exception:
            pass

    max_page_h = max(200.0, page.rect.height - rect.y0 - 15)
    max_page_w = max(200.0, page.rect.width - rect.x0 - 15)

    is_single_line = ("\n" not in text.strip())
    lines = text.strip().split("\n")
    longest_line = max(lines, key=len) if lines else ""

    # Yazı tipi genişliğini mümkünse gerçek metriklerle hesapla
    est_w = len(longest_line) * target_fs * 0.65
    if fontfile and os.path.isfile(fontfile):
        try:
            f_obj = fitz.Font(fontfile=fontfile)
            est_w = f_obj.text_length(longest_line, fontsize=target_fs)
        except Exception:
            pass

    # 1. Aşama: Hedef punto ile kutu boyutunu genişleterek dene
    if is_single_line:
        w_candidates = (
            max(rect.width, est_w + 6),
            max(rect.width * 1.25, est_w * 1.15 + 8),
            max(rect.width * 1.6, est_w * 1.3 + 12),
            max(rect.width * 2.2, est_w * 1.6 + 16)
        )
        h_candidates = (max(rect.height, target_fs * 1.35), max(rect.height * 1.25, target_fs * 1.6))
    else:
        num_lines = max(1, len(lines))
        est_h = max(rect.height, num_lines * target_fs * 1.4)
        w_candidates = (
            max(rect.width, est_w + 6),
            rect.width * 1.15,
            rect.width * 1.35,
            max(rect.width * 1.5, est_w)
        )
        h_candidates = (
            rect.height,
            est_h,
            est_h * 1.25,
            est_h * 1.5,
            est_h * 2.0,
            max_page_h * 0.5,
            max_page_h * 0.8,
            max_page_h
        )

    for w_val in w_candidates:
        w = min(max_page_w, max(rect.width, w_val))
        for h_val in h_candidates:
            h = min(max_page_h, max(rect.height, h_val))
            test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
            # Smart reflow: use align=0 and standard lineheight
            res = tmp_page.insert_textbox(test_r, text, fontsize=target_fs, fontfile=fontfile, fontname=fontname, align=0)
            if res >= 0:
                tmp_doc.close()
                return test_r, target_fs
            tmp_page.clean_contents()

    # 2. Aşama: Puntoyu kademeli küçülterek dene
    for fs in (target_fs * 0.9, target_fs * 0.8, target_fs * 0.7, 9.0, 8.0):
        for w_val in (rect.width * 1.15, rect.width * 1.35, max_page_w):
            w = min(max_page_w, max(rect.width, w_val))
            for h_mult in (1.0, 1.4, 2.0, 3.0):
                h = min(max_page_h, max(rect.height * h_mult, fs * 1.5))
                test_r = fitz.Rect(rect.x0, rect.y0, rect.x0 + w, rect.y0 + h)
                res = tmp_page.insert_textbox(test_r, text, fontsize=fs, fontfile=fontfile, fontname=fontname)
                if res >= 0:
                    tmp_doc.close()
                    return test_r, fs
                tmp_page.clean_contents()

    tmp_doc.close()
    fallback_r = fitz.Rect(rect.x0, rect.y0, min(max_page_w + rect.x0, rect.x1 + 80), min(max_page_h + rect.y0, rect.y0 + rect.height * 2.5))
    return fallback_r, max(7.0, target_fs * 0.75)


def extract_page_text_blocks(page: fitz.Page) -> List[Dict[str, Any]]:
    """
    Sayfadaki tüm metin öğelerini akıllı stil segmentleri (styled text runs)
    ve satırlar düzeyinde çıkarır.

    Temel özellikler:
    - Farklı renk, punto, font ve biçimdeki metinleri (ör. mavi başlık, siyah açıklama)
      birbirine karıştırmadan kendi bağımsız stil ve koordinatlarıyla korur.
    - Madde imi (bullet) simgelerini metin içeriğinden ayırarak punto ve renk bozulmalarını önler.
    - Metin altı çizgi (underline) vektör çizimlerini algılar ve metin stiliyle ilişkilendirir.
    - Aynı satırdaki ardışık ve aynı stile sahip span'leri tek bir pürüzsüz metin biriminde birleştirir.
    """
    # 1. Sayfadaki olası altı çizgi vektör çizimlerini (horizontal line / thin rect) topla
    underlines: List[fitz.Rect] = []
    try:
        for d in page.get_drawings():
            r = d.get('rect')
            if not r:
                continue
            # Altı çizgi tipik olarak yatay ince bir çizgi veya dikdörtgendir
            # (yükseklik <= 3.5 pt, genişlik >= 5.0 pt)
            if r.height <= 3.5 and r.width >= 5.0:
                underlines.append(fitz.Rect(r))
    except Exception:
        underlines = []

    d = page.get_text("dict")
    results: List[Dict[str, Any]] = []
    unit_id = 0

    BULLETS = {'•', '●', '○', '■', '▪', '–', '-', '—', '*', '·', '❖', '➢', '✓'}

    for b_no, b in enumerate(d.get("blocks", [])):
        if b.get("type") != 0:
            continue

        cur_run: Optional[Dict[str, Any]] = None

        for l_no, line in enumerate(b.get("lines", [])):
            for s_no, span in enumerate(line.get("spans", [])):
                t = span.get("text", "")
                if not t:
                    continue

                # Eğer sadece boşluktan ibaretse ve henüz metin başlamamışsa (ör. madde imi sonrası girinti boşluğu)
                # Yeni bir run başlatma, böylece metin kutusu ve koordinat doğrudan harflerin başladığı yerden başlar.
                if not t.strip() and (cur_run is None or cur_run.get('is_bullet', False)):
                    continue

                sz = float(span.get("size", 12.0))
                fn = str(span.get("font", ""))
                col_int = int(span.get("color", 0))
                fl = int(span.get("flags", 0))
                fn_low = fn.lower()
                is_bold = bool((fl & 16) or "bold" in fn_low or "black" in fn_low or "heavy" in fn_low)
                is_italic = bool((fl & 2) or "italic" in fn_low or "oblique" in fn_low)
                has_font_underline = False

                is_bullet = (t.strip() in BULLETS)

                r_col = ((col_int >> 16) & 0xFF) / 255.0
                g_col = ((col_int >> 8) & 0xFF) / 255.0
                b_col = (col_int & 0xFF) / 255.0

                # Birleştirme kriteri: Madde imi değilse, font, punto, renk, bold/italic eşleşiyorsa birleştir
                can_merge = False
                if cur_run and not is_bullet and not cur_run["is_bullet"]:
                    same_font = (normalize_font_family(cur_run["font_name"]) == normalize_font_family(fn))
                    same_sz = (abs(cur_run["font_size"] - sz) <= 0.8)
                    same_col = (cur_run["color_int"] == col_int)
                    same_bold = (cur_run["bold"] == is_bold)
                    same_italic = (cur_run["italic"] == is_italic)
                    if same_font and same_sz and same_col and same_bold and same_italic:
                        can_merge = True

                if can_merge:
                    if cur_run["line_no"] != l_no:
                        if not cur_run["text"].endswith("\n"):
                            cur_run["text"] += "\n"
                        cur_run["line_no"] = l_no
                    cur_run["text"] += t
                    cur_run["bbox"] = cur_run["bbox"] | fitz.Rect(span["bbox"])
                else:
                    if cur_run and cur_run["text"].strip():
                        results.append(cur_run)

                    cur_run = {
                        "id": unit_id,
                        "block_no": b_no,
                        "line_no": l_no,
                        "bbox": fitz.Rect(span["bbox"]),
                        "text": t,
                        "font_size": sz,
                        "font_name": fn,
                        "color_int": col_int,
                        "color_rgb": (r_col, g_col, b_col),
                        "bold": is_bold,
                        "italic": is_italic,
                        "underline": has_font_underline,
                        "vector_underline_rect": None,
                        "is_bullet": is_bullet
                    }
                    unit_id += 1

        if cur_run and cur_run["text"].strip():
            results.append(cur_run)

    # 2. Altı çizgi vektör çizimlerini metin birimleriyle eşleştir
    for u in results:
        ubox = u["bbox"]
        for ur in underlines:
            # Dikey yakınlık: çizgi, metin kutusunun alt kenarına (baseline) 2.5 pt yakın olmalı (Çok geniş aralıkları alma, tablo kenarlığı olabilir)
            if abs(ur.y0 - ubox.y1) <= 2.5 or abs(ur.y1 - ubox.y1) <= 2.5:
                # Yatay örtüşme
                if ur.x0 < ubox.x1 and ur.x1 > ubox.x0:
                    u["underline"] = True
                    u["vector_underline_rect"] = ur
                    break

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
    Doğrudan metin ve görsel düzenleme modu aktifken görüntüleyici ekranının üstünde beliren,
    kullanıcıya metin düzenleme/taşıma, resim ekleme, çizim yapma alt araçlarını sunan ve
    moddan çıkma / gelişmiş pencereyi açma kontrolleri sağlayan modern floating HUD bildirim çubuğu.
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
        layout.setContentsMargins(14, 6, 12, 6)
        layout.setSpacing(8)

        # İkon
        self.lbl_icon = QLabel(self)
        self.lbl_icon.setPixmap(ModernIconFactory.icon_edit_content().pixmap(18, 18))
        layout.addWidget(self.lbl_icon)

        # Başlık
        self.lbl_title = QLabel(f"<b>{LanguageManager.tr('direct_edit_banner_title')}</b>", self)
        self.lbl_title.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.lbl_title)

        # Dikey Ayırıcı
        sep1 = QFrame(self)
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFixedHeight(18)
        layout.addWidget(sep1)

        # 1. Alt Araç: Metin Düzenle / Taşı
        self.btn_tool_text = QPushButton(self)
        self.btn_tool_text.setObjectName("ToolTextBtn")
        self.btn_tool_text.setIcon(ModernIconFactory.icon_text_box())
        self.btn_tool_text.setText(LanguageManager.tr("direct_edit_subtool_text"))
        self.btn_tool_text.setCheckable(True)
        self.btn_tool_text.setChecked(True)
        self.btn_tool_text.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tool_text.setToolTip(LanguageManager.tr("direct_edit_subtool_text"))
        self.btn_tool_text.clicked.connect(self._on_tool_text_clicked)
        layout.addWidget(self.btn_tool_text)

        # 2. Alt Araç: Görsel Ekle
        self.btn_tool_image = QPushButton(self)
        self.btn_tool_image.setObjectName("ToolImageBtn")
        self.btn_tool_image.setIcon(ModernIconFactory.icon_image())
        self.btn_tool_image.setText(LanguageManager.tr("direct_edit_subtool_image"))
        self.btn_tool_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tool_image.setToolTip(LanguageManager.tr("direct_edit_subtool_image"))
        self.btn_tool_image.clicked.connect(self._on_tool_image_clicked)
        layout.addWidget(self.btn_tool_image)

        # 3. Alt Araç: Çizim Yap
        self.btn_tool_draw = QPushButton(self)
        self.btn_tool_draw.setObjectName("ToolDrawBtn")
        self.btn_tool_draw.setIcon(ModernIconFactory.icon_pen())
        self.btn_tool_draw.setText(LanguageManager.tr("direct_edit_subtool_draw"))
        self.btn_tool_draw.setCheckable(True)
        self.btn_tool_draw.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tool_draw.setToolTip(LanguageManager.tr("direct_edit_subtool_draw"))
        self.btn_tool_draw.clicked.connect(self._on_tool_draw_clicked)
        layout.addWidget(self.btn_tool_draw)

        # Dikey Ayırıcı
        sep2 = QFrame(self)
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFixedHeight(18)
        layout.addWidget(sep2)

        # Gelişmiş Düzenleyici (Pencere) Butonu
        self.btn_legacy = QPushButton(self)
        self.btn_legacy.setIcon(ModernIconFactory.icon_ocr())
        self.btn_legacy.setText(LanguageManager.tr("direct_edit_open_legacy"))
        self.btn_legacy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_legacy.clicked.connect(self._on_open_legacy)
        layout.addWidget(self.btn_legacy)

        layout.addSpacing(6)

        # Moddan Çık Butonu
        self.btn_exit = QPushButton(self)
        self.btn_exit.setObjectName("ExitBtn")
        self.btn_exit.setIcon(ModernIconFactory.icon_close())
        self.btn_exit.setText(LanguageManager.tr("direct_edit_exit_btn"))
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self._on_exit_clicked)
        layout.addWidget(self.btn_exit)

    def update_active_tool(self, tool_name: str):
        """Aktif araç değiştikçe banner üzerindeki alt araç butonlarının seçili durumunu günceller."""
        if hasattr(self, 'btn_tool_text'):
            self.btn_tool_text.setChecked(tool_name == 'direct_edit')
        if hasattr(self, 'btn_tool_draw'):
            self.btn_tool_draw.setChecked(tool_name == 'pen')

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
                background-color: rgba(255, 255, 255, 0.16);
                border-color: {accent};
            }}
            QPushButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent_h};
            }}
            QPushButton#ExitBtn {{
                background-color: rgba(239, 68, 68, 0.12);
                border-color: rgba(239, 68, 68, 0.35);
                color: {fg};
            }}
            QPushButton#ExitBtn:hover {{
                background-color: #ef4444;
                border-color: #dc2626;
                color: #ffffff;
            }}
            QFrame[frameShape="5"] {{
                background-color: {border};
                border: none;
                width: 1px;
            }}
        """)

        # Modern yumuşak gölge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def reposition(self):
        if not self.tab_doc or not self.tab_doc.view:
            return
        vp = self.tab_doc.view.viewport()
        self.adjustSize()
        x = max(10, (vp.width() - self.width()) // 2)
        y = 12
        self.move(x, y)
        self.raise_()

    def _on_tool_text_clicked(self):
        if self.tab_doc and hasattr(self.tab_doc, 'main_window'):
            self.tab_doc.main_window.set_tool_state('direct_edit')

    def _on_tool_image_clicked(self):
        if self.tab_doc and hasattr(self.tab_doc, 'main_window'):
            self.tab_doc.main_window.show_insert_image_dialog(default_tab=0)

    def _on_tool_draw_clicked(self):
        if self.tab_doc and hasattr(self.tab_doc, 'main_window'):
            self.tab_doc.main_window.set_tool_state('pen')

    def _on_open_legacy(self):
        if hasattr(self.tab_doc.main_window, 'open_pdf_content_editor_dialog'):
            self.tab_doc.main_window.open_pdf_content_editor_dialog()

    def _on_exit_clicked(self):
        self.tab_doc.exit_direct_text_edit()


def normalize_font_family(fn: str) -> str:
    """PostScript veya PDF font adlarını Qt QFont ile uyumlu standart aile adına dönüştürür."""
    if not fn:
        return "Arial"
    # Subset ön eki temizle (ör. 'ABCDEF+Calibri' -> 'Calibri')
    if "+" in fn:
        fn = fn.split("+")[-1]

    fl = fn.lower().replace("-", " ").replace("_", " ")
    if "calibri" in fl:
        return "Calibri"
    elif "segoe" in fl:
        return "Segoe UI"
    elif "times" in fl:
        return "Times New Roman"
    elif "verdana" in fl:
        return "Verdana"
    elif "tahoma" in fl:
        return "Tahoma"
    elif "trebuchet" in fl:
        return "Trebuchet MS"
    elif "georgia" in fl:
        return "Georgia"
    elif "consolas" in fl:
        return "Consolas"
    elif "courier" in fl or "mono" in fl:
        return "Courier New"
    elif "helvetica" in fl or "arial" in fl:
        return "Arial"
    elif "aptos" in fl:
        return "Aptos"
    elif "century" in fl:
        return "Century Gothic"
    return fn.split(",")[0].strip()


class SeamlessDirectTextEdit(QTextEdit):
    """
    Belge üzerindeki arka planı (resimler, degradeler, vektör çizimler)
    birebir kopyalayarak kendi viewport'unda çizen ve yeni metni bu arka planın
    üzerine pürüzsüzce yerleştiren Acrobat stili dikişsiz metin düzenleyici.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_pixmap: Optional[Any] = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.document().setDocumentMargin(1)

    def paintEvent(self, event):
        # Arka plan pixmap'i varsa viewport'a dikişsiz olarak çiz (Adobe Acrobat stili kamuflaj)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter = QPainter(self.viewport())
            painter.drawPixmap(0, 0, self.viewport().width(), self.viewport().height(), self.bg_pixmap)
            painter.end()
        super().paintEvent(event)


class DirectTextInplaceEditor(QWidget):
    """
    Belge üzerinde seçilen metin bloğunun tam üzerine açılan,
    orijinal metni doğrudan sayfa üzerinde düzenlenebilir kılan (in-place)
    ve üstünde şık, ayrık, yüzen bir mini biçimlendirme çubuğu (floating HUD pill)
    sunan modern RevPDF/Acrobat stili yerinde düzenleyici.
    """
    def __init__(self, tab_doc, page_idx: int, pdf_rect: fitz.Rect, text: str,
                 font_size: float = 12.0, color_rgb: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 bold: bool = False, italic: bool = False, underline: bool = False,
                 vector_underline_rect: Optional[fitz.Rect] = None,
                 font_name: str = "Arial", is_new: bool = False):
        super().__init__(tab_doc.view.viewport())
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.orig_page_idx = page_idx
        self.pdf_rect = fitz.Rect(pdf_rect)
        self.orig_pdf_rect = fitz.Rect(pdf_rect)
        self.orig_text = text
        self.font_size = max(6.0, float(font_size))
        self.chosen_color = color_rgb
        self.is_bold = bold
        self.is_italic = italic
        self.is_underline = underline
        self.vector_underline_rect = vector_underline_rect
        self.font_name = normalize_font_family(font_name)
        self.is_new = is_new

        # Değişiklik ve taşıma takibi
        self._has_moved = False
        self._is_dragging = False
        self._initial_text = text
        self._initial_font_size = self.font_size
        self._initial_color = self.chosen_color
        self._initial_bold = self.is_bold
        self._initial_italic = self.is_italic
        self._initial_underline = self.is_underline

        self.setObjectName("DirectTextInplaceEditor")
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._init_ui()
        self.apply_theme()
        self.reposition()

        # Metin alanına odaklan ve imleci sona al
        self._apply_editor_font()
        self.txt_edit.setFocus()

    def _init_ui(self):
        # 1. AYRIK, YÜZEN BİÇİMLENDİRME ARAÇ ÇUBUĞU (FLOATING HUD PILL)
        self.bar_frame = QFrame(self)
        self.bar_frame.setObjectName("MiniActionBar")
        bar_layout = QHBoxLayout(self.bar_frame)
        bar_layout.setContentsMargins(10, 4, 10, 4)
        bar_layout.setSpacing(5)

        # 0. Taşıma Tutamacı (Grip / Move Handle)
        self.btn_move = QPushButton(self.bar_frame)
        self.btn_move.setObjectName("MoveHandleBtn")
        self.btn_move.setIcon(ModernIconFactory.icon_select_move())
        self.btn_move.setText(LanguageManager.tr("direct_edit_move"))
        self.btn_move.setFixedSize(58, 22)
        self.btn_move.setCursor(Qt.CursorShape.SizeAllCursor)
        self.btn_move.setToolTip(LanguageManager.tr("direct_edit_move_hint"))
        bar_layout.addWidget(self.btn_move)

        sep_m = QFrame(self.bar_frame)
        sep_m.setFrameShape(QFrame.Shape.VLine)
        sep_m.setFixedHeight(16)
        bar_layout.addWidget(sep_m)

        # Punto Küçült
        self.btn_dec_size = QPushButton("−", self.bar_frame)
        self.btn_dec_size.setFixedSize(22, 22)
        self.btn_dec_size.setToolTip(LanguageManager.tr("direct_edit_decrease_size"))
        self.btn_dec_size.clicked.connect(self._on_dec_size)
        bar_layout.addWidget(self.btn_dec_size)

        # Punto Değeri
        self.lbl_size_val = QLabel(f"{int(round(self.font_size))} pt", self.bar_frame)
        self.lbl_size_val.setFixedWidth(36)
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(self.lbl_size_val)

        # Punto Büyüt
        self.btn_inc_size = QPushButton("+", self.bar_frame)
        self.btn_inc_size.setFixedSize(22, 22)
        self.btn_inc_size.setToolTip(LanguageManager.tr("direct_edit_increase_size"))
        self.btn_inc_size.clicked.connect(self._on_inc_size)
        bar_layout.addWidget(self.btn_inc_size)

        # Renk Butonu
        self.btn_color = QPushButton(self.bar_frame)
        self.btn_color.setFixedSize(22, 22)
        self.btn_color.setToolTip(LanguageManager.tr("direct_edit_font_color"))
        self._update_color_button()
        self.btn_color.clicked.connect(self._on_choose_color)
        bar_layout.addWidget(self.btn_color)

        # Kalın (B)
        self.btn_bold = QPushButton("B", self.bar_frame)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setChecked(self.is_bold)
        self.btn_bold.setFixedSize(22, 22)
        self.btn_bold.setStyleSheet("font-weight: 900; font-size: 11px;")
        self.btn_bold.setToolTip(LanguageManager.tr("direct_edit_bold"))
        self.btn_bold.clicked.connect(self._on_toggle_bold)
        bar_layout.addWidget(self.btn_bold)

        # İtalik (I)
        self.btn_italic = QPushButton("I", self.bar_frame)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setChecked(self.is_italic)
        self.btn_italic.setFixedSize(22, 22)
        self.btn_italic.setStyleSheet("font-style: italic; font-size: 11px; font-weight: bold;")
        self.btn_italic.setToolTip(LanguageManager.tr("direct_edit_italic"))
        self.btn_italic.clicked.connect(self._on_toggle_italic)
        bar_layout.addWidget(self.btn_italic)

        # Altı Çizili (U)
        self.btn_underline = QPushButton("U", self.bar_frame)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setChecked(self.is_underline)
        self.btn_underline.setFixedSize(22, 22)
        self.btn_underline.setStyleSheet("text-decoration: underline; font-weight: bold; font-size: 11px;")
        self.btn_underline.setToolTip(LanguageManager.tr("direct_edit_underline"))
        self.btn_underline.clicked.connect(self._on_toggle_underline)
        bar_layout.addWidget(self.btn_underline)

        # Dikey Ayırıcı
        sep = QFrame(self.bar_frame)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(16)
        bar_layout.addWidget(sep)

        # [✓ Uygula / Kaydet]
        self.btn_apply = QPushButton(LanguageManager.tr("direct_edit_apply"), self.bar_frame)
        self.btn_apply.setObjectName("ApplyBtn")
        self.btn_apply.setIcon(ModernIconFactory.icon_check())
        self.btn_apply.setToolTip(f"{LanguageManager.tr('direct_edit_apply')} (Ctrl+Enter)")
        self.btn_apply.clicked.connect(self.apply_changes)
        bar_layout.addWidget(self.btn_apply)

        # [🗑 Metni Sil]
        if not self.is_new:
            self.btn_delete = QPushButton(self.bar_frame)
            self.btn_delete.setObjectName("DeleteBtn")
            self.btn_delete.setIcon(ModernIconFactory.icon_trash())
            self.btn_delete.setFixedSize(24, 22)
            self.btn_delete.setToolTip(LanguageManager.tr("direct_edit_delete"))
            self.btn_delete.clicked.connect(self.delete_block)
            bar_layout.addWidget(self.btn_delete)
        else:
            self.btn_delete = None

        # [✕ Vazgeç]
        self.btn_cancel = QPushButton(self.bar_frame)
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.setIcon(ModernIconFactory.icon_close())
        self.btn_cancel.setFixedSize(24, 22)
        self.btn_cancel.setToolTip(LanguageManager.tr("direct_edit_cancel"))
        self.btn_cancel.clicked.connect(self.cancel_edit)
        bar_layout.addWidget(self.btn_cancel)

        # Sürükleme ve taşıma için bar_frame ve btn_move'a eventFilter bağla
        self.bar_frame.setCursor(Qt.CursorShape.SizeAllCursor)
        self.bar_frame.installEventFilter(self)
        self.btn_move.installEventFilter(self)

        # Araç çubuğu butonlarının klavye odağını çalmaması için NoFocus ayarla
        for btn in (self.btn_move, self.btn_dec_size, self.btn_inc_size, self.btn_color,
                    self.btn_bold, self.btn_italic, self.btn_underline, self.btn_apply,
                    self.btn_delete, self.btn_cancel):
            if btn:
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # 2. DOĞRUDAN BELGE ÜZERİNDE METİN DÜZENLEME ALANI (ON-PAGE SEAMLESS TEXT EDIT)
        self.txt_edit = SeamlessDirectTextEdit(self)
        self.txt_edit.setObjectName("DirectTextOnPageEdit")
        self.txt_edit.setPlainText(self.orig_text)
        self.txt_edit.setPlaceholderText(LanguageManager.tr("direct_edit_placeholder"))
        self.txt_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.txt_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.txt_edit.textChanged.connect(self._on_text_changed)
        self.txt_edit.installEventFilter(self)

        self._apply_editor_font()

    def _update_color_button(self):
        r, g, b = self.chosen_color
        hex_c = f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_c};
                border: 2px solid rgba(255, 255, 255, 0.45);
                border-radius: 11px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def _apply_editor_font(self):
        zoom = getattr(self.tab_doc, 'zoom_level', 1.0)
        dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        # Punto boyutunu hesapla: PDF punto × DPI faktörü × zoom
        pt_size = max(6.0, self.font_size * dpi * zoom)

        font = QFont(self.font_name)
        font.setPointSizeF(pt_size)
        font.setBold(self.is_bold)
        font.setItalic(self.is_italic)
        font.setUnderline(self.is_underline)
        self.txt_edit.setFont(font)

        r, g, b = self.chosen_color
        hex_c = f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"
        text_color = QColor(hex_c)

        # Mevcut tüm metne rengi ve fontu uygula (setTextColor sadece yeni yazılanlara uygulanır)
        char_fmt = QTextCharFormat()
        char_fmt.setForeground(text_color)
        char_fmt.setFont(font)
        char_fmt.setFontUnderline(self.is_underline)

        cursor = self.txt_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeCharFormat(char_fmt)
        # İmleci sona taşı, seçimi kaldır
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.txt_edit.setTextCursor(cursor)

    def _update_bg_pixmap(self, txt_x: int, txt_y: int, txt_w: int, txt_h: int):
        """Metin kutusunun viewport üzerindeki tam alanına ait PDF arka planını (eski metin silinmiş olarak) pixmap olarak hazırlar."""
        if not self.tab_doc or not self.tab_doc.doc or self.page_idx >= len(self.tab_doc.doc):
            return
        if txt_w <= 0 or txt_h <= 0:
            return

        try:
            dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
            zoom = getattr(self.tab_doc, 'zoom_level', 1.0)
            p_info = self.tab_doc.page_positions.get(self.page_idx)
            if not p_info:
                return

            page_left = p_info.get('left', 0.0)
            page_top = p_info.get('top', 0.0)

            # Viewport piksellerinden sahne koordinatına çevir
            scene_tl = self.tab_doc.view.mapToScene(QPoint(txt_x, txt_y))
            scene_br = self.tab_doc.view.mapToScene(QPoint(txt_x + txt_w, txt_y + txt_h))

            # Sahne koordinatından PDF sayfa koordinatına çevir
            pdf_x0 = (scene_tl.x() - page_left) / dpi
            pdf_y0 = (scene_tl.y() - page_top) / dpi
            pdf_x1 = (scene_br.x() - page_left) / dpi
            pdf_y1 = (scene_br.y() - page_top) / dpi

            # Geçici kopyada orijinal metni temizle (asıl PDF dokümanını değiştirmeden)
            tmp_doc = fitz.open()
            tmp_doc.insert_pdf(self.tab_doc.doc, from_page=self.page_idx, to_page=self.page_idx)
            tmp_page = tmp_doc[0]

            if not self.is_new:
                clean_rect = fitz.Rect(self.pdf_rect)
                clean_rect.x0 = max(0.0, clean_rect.x0 - 0.5)
                clean_rect.y0 = max(0.0, clean_rect.y0 - 0.5)
                clean_rect.x1 = min(tmp_page.rect.width, clean_rect.x1 + 0.5)
                clean_rect.y1 = min(tmp_page.rect.height, clean_rect.y1 + 0.5)
                tmp_page.add_redact_annot(clean_rect)
                # KRİTİK: images=0, graphics=0 ile arka plan resimleri ve vektör şekilleri ASLA silinmez veya beyaza boyanmaz!
                tmp_page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                    text=fitz.PDF_REDACT_TEXT_REMOVE
                )
                if self.vector_underline_rect:
                    d_r = fitz.Rect(self.vector_underline_rect)
                    d_r.x0 -= 0.5
                    d_r.y0 -= 0.5
                    d_r.x1 += 0.5
                    d_r.y1 += 0.5
                    tmp_page.add_redact_annot(d_r)
                    tmp_page.apply_redactions(
                        images=fitz.PDF_REDACT_IMAGE_NONE,
                        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                        text=fitz.PDF_REDACT_TEXT_NONE
                    )

            clip_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            mat = fitz.Matrix(zoom * dpi, zoom * dpi)

            pix = tmp_page.get_pixmap(clip=clip_rect, matrix=mat)
            tmp_doc.close()

            mode = getattr(self.tab_doc, 'reading_color_mode', 'normal')
            if mode == 'dark':
                pix.invert_irect()

            from PyQt6.QtGui import QImage, QPixmap
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            if mode == 'sepia':
                p_sepia = QPainter(qimg)
                p_sepia.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                p_sepia.end()

            self.txt_edit.bg_pixmap = QPixmap.fromImage(qimg)
            self.txt_edit.viewport().update()
        except Exception:
            pass

    def apply_theme(self):
        th_name = get_current_theme()
        pal = THEME_PALETTES.get(th_name, THEME_PALETTES["dark"])
        bg = pal["card"]
        border = pal["border"]
        accent = pal["accent"]
        accent_h = pal["accent_hover"]
        fg = pal["text"]

        self.setStyleSheet("""
            QWidget#DirectTextInplaceEditor {
                background: transparent;
                border: none;
            }
        """)

        # Yüzen HUD hap araç çubuğu stili
        self.bar_frame.setStyleSheet(f"""
            QFrame#MiniActionBar {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 17px;
            }}
            QLabel {{
                color: {fg};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            QPushButton#MoveHandleBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 1px 4px;
            }}
            QPushButton#MoveHandleBtn:hover {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent_h};
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
                background-color: rgba(255, 255, 255, 0.16);
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
                font-weight: 700;
                padding: 2px 10px;
                border: 1px solid {accent_h};
                border-radius: 11px;
            }}
            QPushButton#ApplyBtn:hover {{
                background-color: {accent_h};
            }}
            QPushButton#DeleteBtn {{
                border-radius: 11px;
            }}
            QPushButton#DeleteBtn:hover {{
                background-color: #ef4444;
                border-color: #dc2626;
                color: #ffffff;
            }}
            QPushButton#CancelBtn {{
                border-radius: 11px;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: rgba(239, 68, 68, 0.25);
                border-color: #ef4444;
            }}
            QFrame[frameShape="5"] {{
                background-color: {border};
                border: none;
                width: 1px;
            }}
        """)

        # Yüzen çubuğa modern yumuşak gölge ekle
        shadow = QGraphicsDropShadowEffect(self.bar_frame)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 3)
        self.bar_frame.setGraphicsEffect(shadow)

        # Doğrudan belge üzerindeki metin kutusu stili:
        # Şeffaf arka plan + viewport'ta birebir PDF arka plan kamuflajı ve Acrobat stili kesikli seçim çerçevesi
        self.txt_edit.setStyleSheet(f"""
            QTextEdit#DirectTextOnPageEdit {{
                background: transparent;
                border: 1.5px dashed {accent};
                border-radius: 2px;
                padding: 0px;
                margin: 0px;
                selection-background-color: {accent};
                selection-color: #ffffff;
            }}
            QTextEdit#DirectTextOnPageEdit:focus {{
                border: 1.5px dashed {accent};
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

        vp = self.tab_doc.view.viewport()
        vp_w = vp.width()

        # 1. Metin kutusu boyutları
        doc = self.txt_edit.document()
        doc_w = int(round(doc.idealWidth()))
        doc_h = int(round(doc.size().height()))

        orig_w = max(30, br.x() - tl.x())
        orig_h = max(18, br.y() - tl.y())

        txt_w = max(orig_w + 12, doc_w + 18, 60)
        max_allowed_w = max(60, vp_w - tl.x() - 15)
        txt_w = min(txt_w, max_allowed_w)

        txt_h = max(orig_h + 4, doc_h + 6, 22)
        txt_x = tl.x() - 2
        txt_y = tl.y() - 1

        # 2. Yüzen araç çubuğu (Floating HUD)
        self.bar_frame.adjustSize()
        bar_w = max(390, self.bar_frame.sizeHint().width())
        bar_h = 34

        # Çubuk varsayılan olarak metin kutusunun ÜSTÜNDE yüzer
        bar_y = txt_y - bar_h - 7
        # Üstte yer yoksa (viewport üstüne veya banner altına giriyorsa) ALTINA koy
        if bar_y < 50:
            bar_y = txt_y + txt_h + 7

        bar_x = txt_x
        if bar_x + bar_w > vp_w - 10:
            bar_x = max(10, vp_w - bar_w - 10)
        if bar_x < 10:
            bar_x = 10

        # 3. Kapsayıcı widget (self) her iki bileşeni de kapsayacak boyuta getirilir
        min_x = min(txt_x, bar_x)
        min_y = min(txt_y, bar_y)
        max_r = max(txt_x + txt_w, bar_x + bar_w)
        max_b = max(txt_y + txt_h, bar_y + bar_h)

        self.setGeometry(min_x, min_y, max(1, max_r - min_x), max(1, max_b - min_y))

        # 4. Çocuk bileşenler yerel koordinatlara yerleştirilir
        self.bar_frame.setGeometry(bar_x - min_x, bar_y - min_y, bar_w, bar_h)
        self.txt_edit.setGeometry(txt_x - min_x, txt_y - min_y, txt_w, txt_h)

        # 5. Eğer metin henüz taşınmadıysa Acrobat stili dikişsiz arka plan pixmap'ini yenile
        if not getattr(self, '_has_moved', False):
            self._update_bg_pixmap(txt_x, txt_y, txt_w, txt_h)

        self.raise_()

    def contains_viewport_pos(self, vp_pos: QPoint) -> bool:
        """Tıklanan viewport noktasının araç çubuğu veya metin kutusuna denk gelip gelmediğini kontrol eder."""
        local_pos = self.mapFromParent(vp_pos)
        return self.txt_edit.geometry().contains(local_pos) or self.bar_frame.geometry().contains(local_pos)

    def has_uncommitted_changes(self) -> bool:
        """Kullanıcının metin, konum veya biçimlendirmede bir değişiklik yapıp yapmadığını döndürür."""
        if getattr(self, '_has_moved', False):
            return True
        curr_text = self.txt_edit.toPlainText().strip()
        orig_text = self._initial_text.strip()
        if curr_text != orig_text:
            return True
        if abs(self.font_size - self._initial_font_size) > 0.1:
            return True
        if self.chosen_color != self._initial_color:
            return True
        if self.is_bold != self._initial_bold:
            return True
        if self.is_italic != self._initial_italic:
            return True
        if self.is_underline != self._initial_underline:
            return True
        return False

    def _update_pdf_rect_from_viewport_position(self):
        """Metin kutusunun sürükleme sonrası yeni viewport konumunu PDF sayfa koordinatlarına dönüştürür."""
        if not self.tab_doc or not self.tab_doc.view:
            return

        vp_txt_x = self.x() + self.txt_edit.x()
        vp_txt_y = self.y() + self.txt_edit.y()
        scene_pos = self.tab_doc.view.mapToScene(QPoint(vp_txt_x, vp_txt_y))

        hit_page_idx = self.tab_doc.get_page_at_pos(scene_pos)
        if hit_page_idx is not None:
            self.page_idx = hit_page_idx

        p_info = self.tab_doc.page_positions.get(self.page_idx)
        if not p_info:
            return

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.tab_doc.base_render_dpi

        pdf_x0 = (scene_pos.x() - page_left) / dpi
        pdf_y0 = (scene_pos.y() - page_top) / dpi

        orig_w = self.orig_pdf_rect.width
        orig_h = self.orig_pdf_rect.height

        page_w = p_info.get('width', 595.0) / dpi
        page_h = p_info.get('height', 842.0) / dpi

        pdf_x0 = max(2.0, min(page_w - orig_w - 2.0, pdf_x0))
        pdf_y0 = max(2.0, min(page_h - orig_h - 2.0, pdf_y0))

        self.pdf_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x0 + orig_w, pdf_y0 + orig_h)
        self._has_moved = True

    def mousePressEvent(self, event):
        pos = event.pos()
        if not self.txt_edit.geometry().contains(pos) and not self.bar_frame.geometry().contains(pos):
            # Araç çubuğu ve metin kutusu dışındaki şeffaf alana tıklandıysa
            if self.has_uncommitted_changes():
                self.apply_changes()
            else:
                self.tab_doc.close_inplace_editor()
            event.ignore()
        else:
            super().mousePressEvent(event)

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

    def _on_toggle_underline(self):
        self.is_underline = self.btn_underline.isChecked()
        self._apply_editor_font()

    def _on_text_changed(self):
        self.reposition()

    def eventFilter(self, obj, event):
        # 1. Metin kutusu klavye olayları
        if obj == self.txt_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.apply_changes()
                return True
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                if "\n" not in self._initial_text:
                    self.apply_changes()
                    return True
            elif event.key() == Qt.Key.Key_Escape:
                self.cancel_edit()
                return True

        # 2. Taşıma Tutamacı ve Çubuk Sürükleme Olayları
        if obj in (self.bar_frame, getattr(self, 'btn_move', None)):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if obj == self.bar_frame:
                    child = self.bar_frame.childAt(event.pos())
                    if child and child not in (self.bar_frame, getattr(self, 'btn_move', None)) and isinstance(child, QPushButton):
                        return super().eventFilter(obj, event)

                self._is_dragging = True
                self._drag_start_global = event.globalPosition().toPoint()
                self._drag_start_pos = self.pos()
                self._has_moved = True
                self.bar_frame.grabMouse()
                QApplication.setOverrideCursor(Qt.CursorShape.SizeAllCursor)
                return True

            elif event.type() == QEvent.Type.MouseMove and getattr(self, '_is_dragging', False):
                delta = event.globalPosition().toPoint() - self._drag_start_global
                new_x = self._drag_start_pos.x() + delta.x()
                new_y = self._drag_start_pos.y() + delta.y()
                self.move(new_x, new_y)
                if self.txt_edit.bg_pixmap is not None:
                    self.txt_edit.bg_pixmap = None
                    self.txt_edit.viewport().update()
                return True

            elif event.type() == QEvent.Type.MouseButtonRelease and getattr(self, '_is_dragging', False):
                self._is_dragging = False
                try:
                    self.bar_frame.releaseMouse()
                except Exception:
                    pass
                QApplication.restoreOverrideCursor()
                self._update_pdf_rect_from_viewport_position()
                return True

        return super().eventFilter(obj, event)

    def apply_changes(self):
        new_text = self.txt_edit.toPlainText().strip()
        if not new_text and not self.is_new:
            self.delete_block()
            return
        elif not new_text and self.is_new:
            self.cancel_edit()
            return

        if not self.has_uncommitted_changes() and not self.is_new:
            self.tab_doc.close_inplace_editor()
            return

        target_box = self.pdf_rect if getattr(self, '_has_moved', False) else None
        target_pg = self.page_idx if getattr(self, '_has_moved', False) else None

        self.tab_doc.commit_direct_text_edit(
            self.orig_page_idx, self.orig_pdf_rect, new_text,
            self.font_size, self.chosen_color,
            self.is_bold, self.is_italic,
            underline=self.is_underline,
            vector_underline_rect=self.vector_underline_rect,
            font_name=self.font_name, is_new=self.is_new,
            target_bbox=target_box, target_page_idx=target_pg
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
            self.tab_doc.delete_direct_text_block(
                self.orig_page_idx, self.orig_pdf_rect,
                vector_underline_rect=self.vector_underline_rect
            )

    def cancel_edit(self):
        self.tab_doc.close_inplace_editor()

