import os
import datetime
from typing import Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QStackedWidget, QWidget,
                             QGridLayout, QFrame, QScrollArea, QGraphicsDropShadowEffect)
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPixmap, QImage, QPainterPath)
from PyQt6.QtCore import Qt, QSize, QRectF, QBuffer, QIODevice, QPointF

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.icons import ModernIconFactory


class ModernStampDialog(QDialog):
    """
    Adobe Acrobat benzeri gelişmiş damga ekleme iletişim kutusu.
    - Standart İş Damgaları (ONAYLANDI, GİZLİ, TASLAK, NİHAİ, vb.)
    - Dinamik Damgalar (Tarih ve yazar bilgisi içeren damgalar)
    - Özel Damga (Kullanıcı metni ve renk seçimi)
    """
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window or parent
        self.setWindowTitle(LanguageManager.tr("stamp_dialog_title"))
        self.setFixedSize(540, 520)

        self.stamp_bytes: Optional[bytes] = None
        self.stamp_name: str = "APPROVED"
        self.selected_category = "standard"
        self.selected_color = "#16a34a"
        self.selected_text = LanguageManager.tr("stamp_approved")
        self.is_dynamic = False
        self.author_name = self._get_author_name()

        self._build_ui()
        apply_dialog_theme(self, parent)
        self._update_preview()

    def _get_author_name(self) -> str:
        if self.main_window and hasattr(self.main_window, 'settings'):
            author = self.main_window.settings.value("author_name", "")
            if author:
                return str(author).strip()
        try:
            from src.ui.dialogs.settings_dialog import get_default_author_info
            def_user, _ = get_default_author_info()
            return def_user or "Kullanici"
        except Exception:
            import getpass
            try:
                return getpass.getuser() or "Kullanici"
            except Exception:
                return "Kullanici"

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 1. Kategori Değiştirici (Segmented Switcher)
        h_cat = QHBoxLayout()
        h_cat.setSpacing(8)

        self.btn_cat_std = QPushButton(LanguageManager.tr("stamp_cat_standard"))
        self.btn_cat_std.setCheckable(True)
        self.btn_cat_std.setChecked(True)
        self.btn_cat_std.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cat_std.clicked.connect(lambda: self._set_category("standard"))

        self.btn_cat_dyn = QPushButton(LanguageManager.tr("stamp_cat_dynamic"))
        self.btn_cat_dyn.setCheckable(True)
        self.btn_cat_dyn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cat_dyn.clicked.connect(lambda: self._set_category("dynamic"))

        self.btn_cat_custom = QPushButton(LanguageManager.tr("stamp_cat_custom"))
        self.btn_cat_custom.setCheckable(True)
        self.btn_cat_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cat_custom.clicked.connect(lambda: self._set_category("custom"))

        h_cat.addWidget(self.btn_cat_std)
        h_cat.addWidget(self.btn_cat_dyn)
        h_cat.addWidget(self.btn_cat_custom)
        layout.addLayout(h_cat)

        # 2. Yığın (Kategori İçerikleri)
        self.stack = QStackedWidget()

        # Sayfa 0: Standart Damgalar
        self.page_std = QWidget()
        l_std = QGridLayout(self.page_std)
        l_std.setContentsMargins(0, 8, 0, 8)
        l_std.setSpacing(8)

        self.std_stamps = [
            ("stamp_approved", "#16a34a"),
            ("stamp_confidential", "#dc2626"),
            ("stamp_draft", "#2563eb"),
            ("stamp_final", "#7c3aed"),
            ("stamp_void", "#b91c1c"),
            ("stamp_completed", "#0d9488"),
            ("stamp_sign_here", "#d97706"),
            ("stamp_urgent", "#ea580c"),
        ]

        for idx, (key, col) in enumerate(self.std_stamps):
            txt = LanguageManager.tr(key)
            btn = QPushButton(txt)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {col};
                    border: 2px solid {col};
                    border-radius: 6px;
                    font-weight: 800;
                    font-size: 11px;
                    letter-spacing: 1px;
                    background-color: transparent;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                }}
            """)
            btn.clicked.connect(lambda _, t=txt, c=col: self._select_preset_stamp(t, c, False))
            r = idx // 2
            c = idx % 2
            l_std.addWidget(btn, r, c)

        self.stack.addWidget(self.page_std)

        # Sayfa 1: Dinamik Damgalar
        self.page_dyn = QWidget()
        l_dyn = QVBoxLayout(self.page_dyn)
        l_dyn.setContentsMargins(0, 8, 0, 8)
        l_dyn.setSpacing(8)

        self.dyn_stamps = [
            ("stamp_approved", "#16a34a"),
            ("stamp_received", "#2563eb"),
            ("stamp_reviewed", "#7c3aed"),
        ]

        for key, col in self.dyn_stamps:
            txt = LanguageManager.tr(key)
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            display_title = f"{txt}  •  {self.author_name}  •  {now_str}"
            btn = QPushButton(display_title)
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {col};
                    border: 2px dashed {col};
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 11px;
                    background-color: transparent;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                }}
            """)
            btn.clicked.connect(lambda _, t=txt, c=col: self._select_preset_stamp(t, c, True))
            l_dyn.addWidget(btn)

        l_dyn.addStretch(1)
        self.stack.addWidget(self.page_dyn)

        # Sayfa 2: Özel Damga
        self.page_custom = QWidget()
        l_custom = QVBoxLayout(self.page_custom)
        l_custom.setContentsMargins(0, 8, 0, 8)
        l_custom.setSpacing(10)

        lbl_custom_txt = QLabel(LanguageManager.tr("stamp_custom_text_label"))
        lbl_custom_txt.setStyleSheet("font-weight: 600; font-size: 12px;")
        l_custom.addWidget(lbl_custom_txt)

        self.txt_custom = QLineEdit()
        self.txt_custom.setText(LanguageManager.tr("stamp_approved"))
        self.txt_custom.setFixedHeight(34)
        self.txt_custom.textChanged.connect(self._on_custom_text_changed)
        l_custom.addWidget(self.txt_custom)

        lbl_custom_col = QLabel(LanguageManager.tr("stamp_custom_color_label"))
        lbl_custom_col.setStyleSheet("font-weight: 600; font-size: 12px;")
        l_custom.addWidget(lbl_custom_col)

        h_colors = QHBoxLayout()
        h_colors.setSpacing(8)
        self.color_palette = [
            ("#16a34a", "Green"),
            ("#dc2626", "Red"),
            ("#2563eb", "Blue"),
            ("#7c3aed", "Purple"),
            ("#ea580c", "Orange"),
            ("#0d9488", "Teal"),
        ]
        for col_hex, _ in self.color_palette:
            btn_col = QPushButton()
            btn_col.setFixedSize(28, 28)
            btn_col.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_col.setStyleSheet(f"""
                QPushButton {{
                    background-color: {col_hex};
                    border-radius: 14px;
                    border: 2px solid transparent;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            btn_col.clicked.connect(lambda _, ch=col_hex: self._select_custom_color(ch))
            h_colors.addWidget(btn_col)
        h_colors.addStretch(1)
        l_custom.addLayout(h_colors)

        l_custom.addStretch(1)
        self.stack.addWidget(self.page_custom)

        layout.addWidget(self.stack, stretch=1)

        # 3. Canlı Önizleme Kartı
        lbl_preview_title = QLabel(LanguageManager.tr("stamp_custom_preview"))
        lbl_preview_title.setStyleSheet("font-weight: 600; font-size: 11px; opacity: 0.8;")
        layout.addWidget(lbl_preview_title)

        self.preview_card = QFrame()
        self.preview_card.setFixedHeight(110)
        self.preview_card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        l_prev = QVBoxLayout(self.preview_card)
        l_prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_img = QLabel()
        self.lbl_preview_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_prev.addWidget(self.lbl_preview_img)
        layout.addWidget(self.preview_card)

        # 4. Alt Butonlar
        h_bottom = QHBoxLayout()
        h_bottom.addStretch(1)

        btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        h_bottom.addWidget(btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("stamp_apply_btn"))
        self.btn_apply.setObjectName("PrimaryBtn")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self._apply_and_accept)
        h_bottom.addWidget(self.btn_apply)

        layout.addLayout(h_bottom)

    def _set_category(self, cat: str):
        self.selected_category = cat
        self.btn_cat_std.setChecked(cat == "standard")
        self.btn_cat_dyn.setChecked(cat == "dynamic")
        self.btn_cat_custom.setChecked(cat == "custom")
        if cat == "standard":
            self.stack.setCurrentIndex(0)
            self.is_dynamic = False
            self.selected_text = LanguageManager.tr("stamp_approved")
            self.selected_color = "#16a34a"
        elif cat == "dynamic":
            self.stack.setCurrentIndex(1)
            self.is_dynamic = True
            self.selected_text = LanguageManager.tr("stamp_approved")
            self.selected_color = "#16a34a"
        else:
            self.stack.setCurrentIndex(2)
            self.is_dynamic = False
            self.selected_text = self.txt_custom.text().strip() or "STAMP"
        self._update_preview()

    def _select_preset_stamp(self, text: str, color: str, is_dyn: bool):
        self.selected_text = text
        self.selected_color = color
        self.is_dynamic = is_dyn
        self._update_preview()

    def _select_custom_color(self, color_hex: str):
        self.selected_color = color_hex
        self._update_preview()

    def _on_custom_text_changed(self, text: str):
        if self.selected_category == "custom":
            self.selected_text = text.strip() or "STAMP"
            self._update_preview()

    def _render_stamp_pixmap(self, scale: float = 1.0) -> QPixmap:
        w = int(260 * scale)
        h = int(90 * scale)
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        col = QColor(self.selected_color)

        # Damga hafif yatay eğimle (-4 derece) gerçekçi görünür
        p.translate(w / 2.0, h / 2.0)
        p.rotate(-3.5)
        p.translate(-w / 2.0, -h / 2.0)

        # Dış Kalın Çerçeve
        p.setPen(QPen(col, 3.0 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(8 * scale, 8 * scale, (260 - 16) * scale, (90 - 16) * scale), 6 * scale, 6 * scale)

        # İç İnce Çerçeve
        p.setPen(QPen(col, 1.2 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(QRectF(13 * scale, 13 * scale, (260 - 26) * scale, (90 - 26) * scale), 4 * scale, 4 * scale)

        if not self.is_dynamic:
            # Standart veya Özel Tek Başlık Damgası
            font = QFont("Arial Black", int(17 * scale), QFont.Weight.Black)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5 * scale)
            p.setFont(font)
            p.setPen(col)
            rect_text = QRectF(15 * scale, 15 * scale, (260 - 30) * scale, (90 - 30) * scale)
            p.drawText(rect_text, Qt.AlignmentFlag.AlignCenter, self.selected_text.upper())
        else:
            # Dinamik Damga: Başlık + Tarih & Yazar Alt Başlığı
            font_title = QFont("Arial Black", int(15 * scale), QFont.Weight.Black)
            font_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2 * scale)
            p.setFont(font_title)
            p.setPen(col)
            rect_title = QRectF(15 * scale, 14 * scale, (260 - 30) * scale, 34 * scale)
            p.drawText(rect_title, Qt.AlignmentFlag.AlignCenter, self.selected_text.upper())

            # Çizgi Ayracı
            p.setPen(QPen(col, 1.0 * scale, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(24 * scale, 50 * scale), QPointF((260 - 24) * scale, 50 * scale))

            # Yazar & Zaman Damgası
            font_sub = QFont("Segoe UI", int(8.5 * scale), QFont.Weight.Bold)
            p.setFont(font_sub)
            p.setPen(col)
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            info_str = f"{self.author_name}  •  {now_str}"
            rect_sub = QRectF(15 * scale, 52 * scale, (260 - 30) * scale, 24 * scale)
            p.drawText(rect_sub, Qt.AlignmentFlag.AlignCenter, info_str)

        p.end()
        return pix

    def _update_preview(self):
        pix = self._render_stamp_pixmap(scale=1.0)
        self.lbl_preview_img.setPixmap(pix)

    def _apply_and_accept(self):
        # Yüksek çözünürlüklü çıktı (Retina / 2x DPI)
        hi_pix = self._render_stamp_pixmap(scale=2.0)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        hi_pix.save(buf, "PNG")
        self.stamp_bytes = bytes(buf.data())
        self.stamp_name = self.selected_text
        self.accept()
