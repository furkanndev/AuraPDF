# -*- coding: utf-8 -*-
"""
AuraPDF - Adobe Acrobat Tarzı Yorum ve Yapışkan Not Diyaloğu
Kullanıcının belge üzerine tıkladığı noktaya standart PDF yapışkan notu
eklemesini veya mevcut notu düzenlemesini sağlar.
"""

from typing import Optional, Tuple
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QToolButton, QFrame, QButtonGroup
)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme, get_dialog_theme_stylesheet


class AuraCommentInputDialog(QDialog):
    """Adobe Acrobat benzeri modern, tema duyarlı yapışkan not / yorum giriş diyaloğu."""

    COLOR_PRESETS = [
        ("#f97316", "Turuncu / Klasik"),
        ("#eab308", "Sarı"),
        ("#0ea5e9", "Mavi"),
        ("#10b981", "Yeşil"),
        ("#a855f7", "Mor"),
        ("#ef4444", "Kırmızı"),
    ]

    def __init__(self, parent=None, initial_text: str = "", initial_author: str = "", initial_color: str = "#f97316"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 320)

        self.selected_color = initial_color
        from src.ui.dialogs.settings_dialog import get_effective_author_name
        effective_author = get_effective_author_name()
        if not initial_author or initial_author.strip().lower() in ("kullanıcı", "kullanici", "user", "test author", "admin"):
            self.author_name = effective_author
        else:
            self.author_name = initial_author.strip()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Kart konteyneri (çerçeve ve gölge için)
        self.card = QFrame(self)
        self.card.setObjectName("CommentDialogCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 14)
        card_layout.setSpacing(10)

        # 1. Başlık Çubuğu
        h_head = QHBoxLayout()
        h_head.setContentsMargins(0, 0, 0, 0)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_comments(self.selected_color).pixmap(18, 18))
        self.lbl_icon = lbl_icon
        h_head.addWidget(lbl_icon)

        title_text = LanguageManager.tr("comment_edit_dialog_title") if initial_text else LanguageManager.tr("comment_dialog_title")
        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet("font-weight: 700; font-size: 13px;")
        h_head.addWidget(lbl_title, stretch=1)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        h_head.addWidget(btn_close)
        card_layout.addLayout(h_head)

        # 2. Yazar Adı Satırı
        h_author = QHBoxLayout()
        h_author.setContentsMargins(0, 0, 0, 0)
        h_author.setSpacing(8)

        lbl_auth = QLabel(LanguageManager.tr("comment_author_label"))
        lbl_auth.setStyleSheet("font-weight: 600; font-size: 11px;")
        h_author.addWidget(lbl_auth)

        self.txt_author = QLineEdit(self.author_name)
        self.txt_author.setPlaceholderText(LanguageManager.tr("comment_author_placeholder"))
        self.txt_author.setFixedHeight(26)
        h_author.addWidget(self.txt_author, stretch=1)
        card_layout.addLayout(h_author)

        # 3. Renk Seçim Paleti
        h_colors = QHBoxLayout()
        h_colors.setContentsMargins(0, 0, 0, 0)
        h_colors.setSpacing(8)

        lbl_col = QLabel(LanguageManager.tr("comment_color_label"))
        lbl_col.setStyleSheet("font-weight: 600; font-size: 11px;")
        h_colors.addWidget(lbl_col)

        self.color_group = QButtonGroup(self)
        self.color_buttons = []
        for hex_code, desc in self.COLOR_PRESETS:
            btn_col = QToolButton()
            btn_col.setFixedSize(18, 18)
            btn_col.setCheckable(True)
            btn_col.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_col.setToolTip(desc)
            is_active = (hex_code.lower() == self.selected_color.lower())
            btn_col.setChecked(is_active)
            self._style_color_btn(btn_col, hex_code, is_active)
            btn_col.clicked.connect(lambda checked, h=hex_code, b=btn_col: self._on_color_selected(h, b))
            self.color_group.addButton(btn_col)
            self.color_buttons.append((btn_col, hex_code))
            h_colors.addWidget(btn_col)

        h_colors.addStretch(1)
        card_layout.addLayout(h_colors)

        # 4. Yorum Metin Alanı
        self.txt_comment = QTextEdit()
        self.txt_comment.setPlaceholderText(LanguageManager.tr("comment_input_placeholder"))
        self.txt_comment.setText(initial_text)
        if initial_text:
            self.txt_comment.selectAll()
        self.txt_comment.setFixedHeight(120)
        card_layout.addWidget(self.txt_comment)

        # 5. Alt Butonlar
        h_btns = QHBoxLayout()
        h_btns.setContentsMargins(0, 0, 0, 0)
        h_btns.setSpacing(8)

        submit_text = LanguageManager.tr("comment_save_btn") if initial_text else LanguageManager.tr("comments_add_btn")
        lbl_hint = QLabel(f"Ctrl+Enter: {submit_text}")
        lbl_hint.setStyleSheet("font-size: 10px; color: #94a3b8;")
        h_btns.addWidget(lbl_hint)
        h_btns.addStretch(1)

        self.btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton(submit_text)
        self.btn_submit.setObjectName("PrimaryBtn")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.clicked.connect(self._on_submit)
        h_btns.addWidget(self.btn_submit)

        card_layout.addLayout(h_btns)
        main_layout.addWidget(self.card)

        apply_dialog_theme(self, parent)

        # Kart için tema duyarlı şık modern arka plan, kenarlık ve tipografi
        from src.ui.dialog_theme import get_current_theme, THEME_PALETTES
        theme_name = get_current_theme(parent)
        pal = THEME_PALETTES.get(theme_name, THEME_PALETTES.get("gray", {}))
        card_bg = pal.get("card", "#2b2d30")
        border_col = pal.get("border", "rgba(255, 255, 255, 0.15)")
        text_col = pal.get("text", "#f8fafc")

        self.card.setStyleSheet(f"""
            #CommentDialogCard {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            #CommentDialogCard QLabel {{
                color: {text_col};
            }}
        """)

    def _style_color_btn(self, btn: QToolButton, hex_code: str, is_active: bool):
        border = "2px solid #ffffff" if is_active else "1px solid rgba(0, 0, 0, 0.3)"
        btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {hex_code};
                border: {border};
                border-radius: 9px;
            }}
            QToolButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def _on_color_selected(self, hex_code: str, clicked_btn: QToolButton):
        self.selected_color = hex_code
        self.lbl_icon.setPixmap(ModernIconFactory.icon_comments(self.selected_color).pixmap(18, 18))
        for btn, h in self.color_buttons:
            self._style_color_btn(btn, h, btn == clicked_btn)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._on_submit()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def _on_submit(self):
        text = self.txt_comment.toPlainText().strip()
        if not text:
            self.txt_comment.setFocus()
            return

        author = self.txt_author.text().strip() or "Kullanıcı"
        # Yazar adını gelecekteki notlar için hatırla
        try:
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("author_name", author)
        except Exception:
            pass

        self.accept()

    def get_comment_data(self) -> Tuple[str, str, str]:
        """(comment_text, author, hex_color) döndürür."""
        text = self.txt_comment.toPlainText().strip()
        author = self.txt_author.text().strip() or "Kullanıcı"
        return text, author, self.selected_color


CommentDialog = AuraCommentInputDialog
ModernCommentInputDialog = AuraCommentInputDialog
