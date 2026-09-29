# -*- coding: utf-8 -*-
"""
AuraPDF - Yeni Sayfa Ekleme & Şablon Seçim Diyaloğu (New Page Dialog)
Kullanıcının boş sayfa eklerken veya yeni boş belge oluştururken
görsel önizlemeli şablon kartlarından (Düz Beyaz, Çizgili, Kareli, Noktalı,
Cornell Not, Müzik Portesi, Karanlık Mod, Kapak) stil, yön, boyut ve
ekleme konumu seçebilmesini sağlayan modern diyalog penceresi.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QComboBox, QSpinBox, QRadioButton,
    QButtonGroup, QScrollArea, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet, get_current_theme, THEME_PALETTES
from src.ui.icons import ModernIconFactory


PAGE_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "A4": (595.32, 841.92),
    "A3": (841.92, 1190.55),
    "A5": (419.53, 595.32),
    "letter": (612.0, 792.0),
}


class TemplatePreviewCard(QFrame):
    """
    Her bir sayfa şablonunu (Çizgili, Kareli, Düz, Cornell vb.) minyatür kağıt
    çizimiyle canlı olarak resmeden, seçilebilir şık kart bileşeni.
    """
    def __init__(self, style_code: str, title_key: str, desc_key: str, parent=None, orientation: str = "portrait", palette: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.style_code = style_code
        self.title_text = LanguageManager.tr(title_key)
        self.desc_text = LanguageManager.tr(desc_key)
        self.orientation = orientation
        self.is_selected = False
        self.is_hovered = False
        self.palette = palette or THEME_PALETTES.get(get_current_theme(parent), THEME_PALETTES["gray"])

        self.setFixedSize(175, 195)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_orientation(self, orientation: str):
        if self.orientation != orientation:
            self.orientation = orientation
            self.update()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Ebeveyn diyaloga kartın seçildiğini bildir
            parent = self.parent()
            while parent and not hasattr(parent, 'select_style_card'):
                parent = parent.parent()
            if parent and hasattr(parent, 'select_style_card'):
                parent.select_style_card(self.style_code)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        accent = self.palette.get("accent", "#60a5fa")
        card_bg = self.palette.get("card", "#35383c")
        border_col_raw = self.palette.get("border", "#444850")

        # 1. Kart Arka Planı ve Kenarlık
        if self.is_selected:
            accent_col = QColor(accent)
            bg_col = QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 50)
            border_col = accent_col
            border_w = 2.0
        elif self.is_hovered:
            accent_col = QColor(accent)
            bg_col = QColor(card_bg).lighter(114)
            border_col = QColor(accent_col.red(), accent_col.green(), accent_col.blue(), 140)
            border_w = 1.2
        else:
            bg_col = QColor(card_bg)
            border_col = QColor(border_col_raw)
            border_w = 1.0

        p.setPen(QPen(border_col, border_w))
        p.setBrush(QBrush(bg_col))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 10, 10)

        # 2. Mini Sayfa Çizimi (Dikey / Yatay Yön Dinamik Boyutları)
        is_landscape = (getattr(self, 'orientation', 'portrait') == 'landscape')
        if is_landscape:
            page_w = 126.0
            page_h = 86.0
            page_x = (w - page_w) / 2.0
            page_y = 22.0
        else:
            page_w = 88.0
            page_h = 114.0
            page_x = (w - page_w) / 2.0
            page_y = 12.0
        page_rect = QRectF(page_x, page_y, page_w, page_h)

        # Kağıt Gölgesi
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 70)))
        p.drawRoundedRect(QRectF(page_x + 2, page_y + 3, page_w, page_h), 5, 5)

        # Kağıt Gövdesi
        is_dark_style = (self.style_code in ("dark", "cover"))
        paper_bg = QColor("#121316") if is_dark_style else QColor("#ffffff")
        paper_border = QColor("#3b4252") if is_dark_style else QColor("#cbd5e1")
        p.setPen(QPen(paper_border, 1.0))
        p.setBrush(QBrush(paper_bg))
        p.drawRoundedRect(page_rect, 4, 4)

        # 3. Şablona Özgü Çizgiler / Desenler
        p.save()
        p.setClipRect(page_rect)

        if self.style_code == "blank":
            # Düz Beyaz: Sade kağıt
            pass

        elif self.style_code in ("lined", "lines"):
            # Çizgili: Yatay çizgiler
            p.setPen(QPen(QColor("#94a3b8"), 0.8))
            y = page_y + 12.0
            step = 10.0 if not is_landscape else 11.0
            while y < page_y + page_h - 8:
                p.drawLine(QPointF(page_x + 8, y), QPointF(page_x + page_w - 8, y))
                y += step

        elif self.style_code == "grid":
            # Kareli: Izgara çizgileri
            p.setPen(QPen(QColor("#cbd5e1"), 0.7))
            x = page_x + 8.0
            while x < page_x + page_w - 8:
                p.drawLine(QPointF(x, page_y + 8), QPointF(x, page_y + page_h - 8))
                x += 9.0
            y = page_y + 8.0
            while y < page_y + page_h - 8:
                p.drawLine(QPointF(page_x + 8, y), QPointF(page_x + page_w - 8, y))
                y += 9.0

        elif self.style_code == "dotted":
            # Noktalı: Matris noktaları
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#64748b")))
            x = page_x + 10.0
            while x < page_x + page_w - 8:
                y = page_y + 10.0
                while y < page_y + page_h - 8:
                    p.drawEllipse(QPointF(x, y), 0.9, 0.9)
                    y += 9.0
                x += 9.0

        elif self.style_code == "cornell":
            # Cornell: Sol ipucu dikey çizgisi ve üst/alt yatay çizgiler
            cue_x = page_x + (34.0 if is_landscape else 24.0)
            p.setPen(QPen(QColor("#f87171"), 1.2))
            p.drawLine(QPointF(cue_x, page_y + 14), QPointF(cue_x, page_y + page_h - 16))
            p.drawLine(QPointF(page_x + 6, page_y + 14), QPointF(page_x + page_w - 6, page_y + 14))
            p.drawLine(QPointF(page_x + 6, page_y + page_h - 16), QPointF(page_x + page_w - 6, page_y + page_h - 16))
            # Sağ gövde çizgileri
            p.setPen(QPen(QColor("#cbd5e1"), 0.7))
            y = page_y + 22.0
            while y < page_y + page_h - 18:
                p.drawLine(QPointF(cue_x + 4, y), QPointF(page_x + page_w - 6, y))
                y += 8.0

        elif self.style_code == "music":
            # Müzik Portesi: 5'li çizgi grupları
            p.setPen(QPen(QColor("#475569"), 0.8))
            staves = [page_y + 18, page_y + 48] if is_landscape else [page_y + 20, page_y + 52, page_y + 84]
            for start_y in staves:
                for line_idx in range(5):
                    line_y = start_y + (line_idx * 3.5)
                    p.drawLine(QPointF(page_x + 8, line_y), QPointF(page_x + page_w - 8, line_y))

        elif self.style_code == "dark":
            # Koyu Mod: İnce açık gri çizgiler
            p.setPen(QPen(QColor("#334155"), 0.8))
            y = page_y + 12.0
            step = 10.0 if not is_landscape else 11.0
            while y < page_y + page_h - 8:
                p.drawLine(QPointF(page_x + 8, y), QPointF(page_x + page_w - 8, y))
                y += step

        elif self.style_code == "cover":
            # Kapak: Zarif altın / mavi iç çerçeve
            p.setPen(QPen(QColor("#eab308"), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(page_x + 8, page_y + 8, page_w - 16, page_h - 16), 3, 3)
            # Başlık çizgisi
            p.setPen(QPen(QColor("#94a3b8"), 1.2))
            mid_y = page_y + page_h * 0.42
            p.drawLine(QPointF(page_x + 18, mid_y), QPointF(page_x + page_w - 18, mid_y))
            p.drawLine(QPointF(page_x + 28, mid_y + 8), QPointF(page_x + page_w - 28, mid_y + 8))

        p.restore()

        # 4. Seçim Onay Rozeti (Sağ üst köşe ✓)
        if self.is_selected:
            badge_r = 10.0
            badge_x = w - badge_r - 8
            badge_y = badge_r + 8
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(accent)))
            p.drawEllipse(QPointF(badge_x, badge_y), badge_r, badge_r)

            p.setPen(QPen(QColor("#ffffff"), 1.8))
            p.drawLine(QPointF(badge_x - 4, badge_y), QPointF(badge_x - 1, badge_y + 3))
            p.drawLine(QPointF(badge_x - 1, badge_y + 3), QPointF(badge_x + 4, badge_y - 3))

        # 5. Başlık ve Açıklama Yazısı
        text_top = page_y + page_h + (10 if is_landscape else 6)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_col_raw = self.palette.get("text", "#f1f5f9")
        muted_col_raw = self.palette.get("muted", "#94a3b8")
        title_col = QColor(accent) if self.is_selected else QColor(text_col_raw)
        p.setPen(QPen(title_col))
        p.drawText(QRectF(6, text_top, w - 12, 18), Qt.AlignmentFlag.AlignCenter, self.title_text)

        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        desc_col = QColor(accent).lighter(115) if self.is_selected else QColor(muted_col_raw)
        p.setPen(QPen(desc_col))
        p.drawText(QRectF(8, text_top + 18, w - 16, 28), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.desc_text)

        p.end()


class NewPageDialog(QDialog):
    """
    Kullanıcının boş sayfa veya yeni belge oluştururken stil, yön, boyut ve
    yerleşim seçebildiği modern önizlemeli diyalog penceresi.
    """
    def __init__(self, main_window=None, parent=None, default_style: str = "blank", force_new_doc: bool = False):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.selected_style = default_style
        self.force_new_doc = force_new_doc

        theme = get_current_theme(parent or main_window)
        self.palette = THEME_PALETTES.get(theme, THEME_PALETTES["gray"])

        if self.force_new_doc:
            self.setWindowTitle(LanguageManager.tr("new_blank_doc_menu"))
        else:
            self.setWindowTitle(LanguageManager.tr("new_page_dialog_title"))
        self.resize(780, 580)
        self.setMinimumSize(720, 520)

        self._style_cards: Dict[str, TemplatePreviewCard] = {}
        self._init_ui()
        self.select_style_card(self.selected_style)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        accent = self.palette.get("accent", "#60a5fa")
        accent_hover = self.palette.get("accent_hover", "#3b82f6")
        bg_col = self.palette.get("bg", "#2b2d30")
        card_bg = self.palette.get("card", "#35383c")
        border_col = self.palette.get("border", "#444850")
        text_col = self.palette.get("text", "#f1f5f9")
        muted_col = self.palette.get("muted", "#94a3b8")

        # Dialog Styling (Aktif temaya tam uyumlu)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QFrame.card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 12px;
            }}
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 28px;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border-color: {accent};
            }}
            QSpinBox {{
                background-color: rgba(255, 255, 255, 0.06);
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 5px;
                min-height: 28px;
                font-size: 14px;
                font-weight: bold;
                padding: 0px 4px;
            }}
            QSpinBox:focus {{
                border-color: {accent};
            }}
            QRadioButton {{
                color: {text_col};
                font-size: 13px;
                font-weight: 500;
                spacing: 6px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 1px solid {border_col};
                background: transparent;
            }}
            QRadioButton::indicator:checked {{
                background-color: {accent};
                border: 2px solid #ffffff;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {accent};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {accent_hover};
            }}
            QPushButton#CancelBtn {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: rgba(255, 255, 255, 0.14);
                color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {border_col};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # 1. Başlık & Açıklama
        lbl_header = QLabel(LanguageManager.tr("new_page_section_styles"))
        lbl_header.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {text_col};")
        root_layout.addWidget(lbl_header)

        # 2. Şablon Kartları Grid'i (Kaydırılabilir)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(12)

        styles_info = [
            ("blank", "style_blank_title", "style_blank_desc"),
            ("lined", "style_lined_title", "style_lined_desc"),
            ("grid", "style_grid_title", "style_grid_desc"),
            ("dotted", "style_dotted_title", "style_dotted_desc"),
            ("cornell", "style_cornell_title", "style_cornell_desc"),
            ("music", "style_music_title", "style_music_desc"),
            ("dark", "style_dark_title", "style_dark_desc"),
            ("cover", "style_cover_title", "style_cover_desc"),
        ]

        cols = 4
        for idx, (code, title_k, desc_k) in enumerate(styles_info):
            card = TemplatePreviewCard(code, title_k, desc_k, self, palette=self.palette)
            self._style_cards[code] = card
            row = idx // cols
            col = idx % cols
            grid.addWidget(card, row, col)

        scroll.setWidget(grid_widget)
        root_layout.addWidget(scroll, 1)

        # 3. Sayfa Boyutu, Yönü ve Konum Ayarları Kartı
        opts_card = QFrame()
        opts_card.setProperty("class", "card")
        opts_layout = QGridLayout(opts_card)
        opts_layout.setContentsMargins(14, 10, 14, 10)
        opts_layout.setSpacing(12)

        # Yön (Orientation)
        lbl_orient = QLabel(LanguageManager.tr("page_orientation_lbl"))
        lbl_orient.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {text_col};")
        opts_layout.addWidget(lbl_orient, 0, 0)

        orient_box = QHBoxLayout()
        self.rb_portrait = QRadioButton(LanguageManager.tr("page_orientation_portrait"))
        self.rb_landscape = QRadioButton(LanguageManager.tr("page_orientation_landscape"))
        self.rb_portrait.setChecked(True)
        self.rb_portrait.toggled.connect(self._on_orientation_changed)
        self.rb_landscape.toggled.connect(self._on_orientation_changed)
        orient_box.addWidget(self.rb_portrait)
        orient_box.addWidget(self.rb_landscape)
        orient_box.addStretch()
        opts_layout.addLayout(orient_box, 0, 1)

        # Boyut (Paper Size)
        lbl_size = QLabel(LanguageManager.tr("page_size_lbl"))
        lbl_size.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {text_col};")
        opts_layout.addWidget(lbl_size, 1, 0)

        self.cmb_size = QComboBox()
        self.cmb_size.addItem("A4 (210 × 297 mm)", "A4")
        self.cmb_size.addItem("A3 (297 × 420 mm)", "A3")
        self.cmb_size.addItem("A5 (148 × 210 mm)", "A5")
        self.cmb_size.addItem("Letter (8.5 × 11 in)", "letter")
        
        # Açık belge varsa mevcut sayfa boyutuna uyma seçeneği ekle
        has_active_doc = False
        if self.main_window and hasattr(self.main_window, 'get_current_tab_doc'):
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc and tab_doc.doc is not None and len(tab_doc.doc) > 0:
                has_active_doc = True
                self.cmb_size.insertItem(0, LanguageManager.tr("page_size_match"), "match")
                self.cmb_size.setCurrentIndex(0)
        
        opts_layout.addWidget(self.cmb_size, 1, 1)

        # Sayfa Sayısı (Page Count)
        lbl_count = QLabel(LanguageManager.tr("page_count_lbl"))
        lbl_count.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {text_col};")
        opts_layout.addWidget(lbl_count, 0, 2)

        count_container = QWidget()
        count_layout = QHBoxLayout(count_container)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.setSpacing(2)

        btn_dec = QPushButton("−")
        btn_dec.setFixedSize(32, 32)
        btn_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dec.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                border-color: {accent};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.22);
            }}
        """)

        self.spn_count = QSpinBox()
        self.spn_count.setRange(1, 50)
        self.spn_count.setValue(1)
        self.spn_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spn_count.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.spn_count.setFixedSize(48, 32)

        btn_inc = QPushButton("+")
        btn_inc.setFixedSize(32, 32)
        btn_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inc.setStyleSheet(btn_dec.styleSheet())

        btn_dec.clicked.connect(lambda: self.spn_count.setValue(max(1, self.spn_count.value() - 1)))
        btn_inc.clicked.connect(lambda: self.spn_count.setValue(min(50, self.spn_count.value() + 1)))

        count_layout.addWidget(btn_dec)
        count_layout.addWidget(self.spn_count)
        count_layout.addWidget(btn_inc)
        count_layout.addStretch()

        opts_layout.addWidget(count_container, 0, 3)

        # Konum (Placement)
        lbl_pos = QLabel(LanguageManager.tr("page_placement_lbl"))
        lbl_pos.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {text_col};")
        opts_layout.addWidget(lbl_pos, 1, 2)

        self.cmb_placement = QComboBox()
        if has_active_doc and not self.force_new_doc:
            self.cmb_placement.addItem(LanguageManager.tr("placement_at_end"), "end")
            self.cmb_placement.addItem(LanguageManager.tr("placement_after_current"), "after_current")
            self.cmb_placement.addItem(LanguageManager.tr("placement_before_current"), "before_current")
            self.cmb_placement.addItem(LanguageManager.tr("placement_new_document"), "new_doc")
        else:
            self.cmb_placement.addItem(LanguageManager.tr("placement_new_document"), "new_doc")

        opts_layout.addWidget(self.cmb_placement, 1, 3)
        root_layout.addWidget(opts_card)

        # 4. Alt Eylem Butonları
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)
        bottom_bar.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("btn_cancel_settings"))
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        confirm_text = LanguageManager.tr("new_blank_doc_menu") if self.force_new_doc else LanguageManager.tr("btn_add_page_confirm")
        self.btn_confirm = QPushButton(confirm_text)
        self.btn_confirm.setObjectName("PrimaryBtn")
        self.btn_confirm.setDefault(True)
        self.btn_confirm.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_confirm)

        root_layout.addLayout(bottom_bar)

    def _on_orientation_changed(self):
        """Kullanıcı Dikey veya Yatay seçtiğinde tüm şablon önizleme kartlarını günceller."""
        orientation = "landscape" if self.rb_landscape.isChecked() else "portrait"
        for card in self._style_cards.values():
            card.set_orientation(orientation)

    def select_style_card(self, style_code: str):
        """Kullanıcının tıkladığı şablon kartını seçili yapar."""
        self.selected_style = style_code
        for code, card in self._style_cards.items():
            card.set_selected(code == style_code)

    def get_page_config(self) -> Dict[str, Any]:
        """Diyalogdan seçilen tüm parametreleri sözlük olarak döndürür."""
        orientation = "landscape" if self.rb_landscape.isChecked() else "portrait"
        size_code = self.cmb_size.currentData()
        count = self.spn_count.value()
        placement = self.cmb_placement.currentData()

        # Boyut hesabı (pt)
        if size_code == "match" and self.main_window and hasattr(self.main_window, 'get_current_tab_doc'):
            tab_doc = self.main_window.get_current_tab_doc()
            if tab_doc and tab_doc.doc is not None and len(tab_doc.doc) > 0:
                p_idx = max(0, min(getattr(tab_doc, 'current_page_idx', 0), len(tab_doc.doc) - 1))
                page = tab_doc.doc[p_idx]
                base_w, base_h = float(page.mediabox.width), float(page.mediabox.height)
            else:
                base_w, base_h = PAGE_SIZES_PT["A4"]
        elif size_code in PAGE_SIZES_PT:
            base_w, base_h = PAGE_SIZES_PT[size_code]
        else:
            base_w, base_h = PAGE_SIZES_PT["A4"]

        if orientation == "landscape":
            w = max(base_w, base_h)
            h = min(base_w, base_h)
        else:
            w = min(base_w, base_h)
            h = max(base_w, base_h)

        return {
            "style": self.selected_style,
            "orientation": orientation,
            "size_code": size_code,
            "width": w,
            "height": h,
            "count": count,
            "placement": placement
        }


class ChangePageStyleDialog(QDialog):
    """
    AuraPDF - Sayfa Stilini / Şablonunu Değiştirme Diyaloğu.
    Kullanıcının mevcut açık sayfayı veya tüm belge sayfalarını seçili şablonla
    (Düz Beyaz, Çizgili, Kareli, Noktalı, Cornell, Müzik, Karanlık, Kapak)
    değiştirmesini sağlar. Notlar ve çizimler korunur.
    """
    def __init__(self, parent=None, current_page_idx: int = 0, total_pages: int = 1, current_style: str = "blank"):
        super().__init__(parent)
        self.current_page_idx = current_page_idx
        self.total_pages = total_pages
        self.selected_style = current_style
        self._style_cards: Dict[str, TemplatePreviewCard] = {}

        self.setWindowTitle(LanguageManager.tr("change_page_style_title"))
        self.setFixedSize(780, 620)

        theme = get_current_theme(parent)
        self.palette = THEME_PALETTES.get(theme, THEME_PALETTES["gray"])
        accent = self.palette.get("accent", "#60a5fa")
        accent_hover = self.palette.get("accent_hover", "#3b82f6")
        bg_col = self.palette.get("bg", "#2b2d30")
        card_bg = self.palette.get("card", "#35383c")
        border_col = self.palette.get("border", "#444850")
        text_col = self.palette.get("text", "#f1f5f9")
        muted_col = self.palette.get("muted", "#94a3b8")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                border: 1px solid {border_col};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: {card_bg};
                color: {accent};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: {accent};
            }}
            QRadioButton {{
                font-size: 13px;
                color: {text_col};
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 1px solid {border_col};
                background: transparent;
            }}
            QRadioButton::indicator:checked {{
                background-color: {accent};
                border: 2px solid #ffffff;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {accent};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                min-height: 22px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {accent_hover};
            }}
            QPushButton#SecondaryBtn {{
                background-color: {card_bg};
                color: {text_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 8px 20px;
                min-height: 22px;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {border_col};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 16)
        root_layout.setSpacing(14)

        text_col = self.palette.get("text", "#f1f5f9")
        muted_col = self.palette.get("muted", "#94a3b8")
        card_bg = self.palette.get("card", "#35383c")
        border_col = self.palette.get("border", "#444850")

        # Başlık ve Açıklama
        hdr_layout = QVBoxLayout()
        hdr_layout.setSpacing(4)
        lbl_title = QLabel(LanguageManager.tr("change_page_style_title"))
        lbl_title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {text_col};")
        hdr_layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("change_page_style_desc"))
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {muted_col};")
        lbl_desc.setWordWrap(True)
        hdr_layout.addWidget(lbl_desc)
        root_layout.addLayout(hdr_layout)

        # Şablon Kartları (Scroll Area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_container)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 4, 8, 4)

        styles_info = [
            ("blank", "style_blank_title", "style_blank_desc"),
            ("lined", "style_lined_title", "style_lined_desc"),
            ("grid", "style_grid_title", "style_grid_desc"),
            ("dotted", "style_dotted_title", "style_dotted_desc"),
            ("cornell", "style_cornell_title", "style_cornell_desc"),
            ("music", "style_music_title", "style_music_desc"),
            ("dark", "style_dark_title", "style_dark_desc"),
            ("cover", "style_cover_title", "style_cover_desc"),
        ]

        for i, (code, title_k, desc_k) in enumerate(styles_info):
            card = TemplatePreviewCard(code, title_k, desc_k, self, orientation="portrait", palette=self.palette)
            self._style_cards[code] = card
            row, col = divmod(i, 4)
            grid.addWidget(card, row, col)

        scroll.setWidget(grid_container)
        root_layout.addWidget(scroll, 1)

        # Uygulama Kapsamı (Yalnızca Mevcut Sayfa vs Tüm Sayfalar)
        scope_frame = QFrame()
        scope_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        scope_layout = QHBoxLayout(scope_frame)
        scope_layout.setContentsMargins(14, 8, 14, 8)
        scope_layout.setSpacing(24)

        self.rb_current = QRadioButton(LanguageManager.tr("apply_to_current_page", page=self.current_page_idx + 1))
        self.rb_current.setChecked(True)
        self.rb_all = QRadioButton(LanguageManager.tr("apply_to_all_pages", count=self.total_pages))

        scope_layout.addWidget(self.rb_current)
        scope_layout.addWidget(self.rb_all)
        scope_layout.addStretch()
        root_layout.addWidget(scope_frame)

        # Alt Butonlar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("btn_apply_style"))
        self.btn_apply.setObjectName("PrimaryBtn")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_apply)

        root_layout.addLayout(bottom_bar)

        # Varsayılan seçimi uygula
        self.select_style_card(self.selected_style)

    def select_style_card(self, style_code: str):
        self.selected_style = style_code
        for code, card in self._style_cards.items():
            card.set_selected(code == style_code)

    def get_selected_style(self) -> Tuple[str, bool]:
        """(selected_style: str, all_pages: bool) döndürür."""
        all_pages = self.rb_all.isChecked()
        return self.selected_style, all_pages
