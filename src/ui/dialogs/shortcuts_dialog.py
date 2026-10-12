"""
AuraPDF - Klavye Kısayolları Başvuru Rehberi (Keyboard Shortcuts Dialog)
=======================================================================
Kullanıcının AuraPDF içerisindeki tüm klavye kısayollarını kategorilerine göre
kolayca inceleyebilmesini sağlayan modern, filtreli yardım penceresi.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QLineEdit, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.icons import ModernIconFactory


class KeyboardShortcutsDialog(QDialog):
    """Klavye Kısayolları Rehberi Penceresi."""

    def _get_categories(self):
        is_tr = LanguageManager.current_lang == "tr"
        if is_tr:
            return [
                ("Gezinme & Okuma", [
                    ("Page Down / Space", "Sonraki sayfaya kaydır / geç"),
                    ("Page Up / Shift+Space", "Önceki sayfaya kaydır / geç"),
                    ("Home", "Belgenin ilk sayfasına git"),
                    ("End", "Belgenin son sayfasına git"),
                    ("Alt + Sol Ok", "Önceki sayfa görünümüne geri dön"),
                    ("Alt + Sağ Ok", "Sonraki sayfa görünümüne ilerle"),
                    ("Ctrl + F", "Belge içinde metin ara"),
                    ("F3 / Shift + F3", "Sonraki / önceki arama sonucuna git"),
                    ("F11", "Tam ekran modunu aç / kapat"),
                ]),
                ("Dosya & Sekmeler", [
                    ("Ctrl + O", "Yeni PDF belgesi aç"),
                    ("Ctrl + S", "Belgeyi kaydet"),
                    ("Ctrl + Shift + S", "Belgeyi farklı kaydet..."),
                    ("Ctrl + N", "Yeni boş PDF belgesi oluştur"),
                    ("Ctrl + W", "Aktif belge sekmesini kapat"),
                    ("Ctrl + Shift + T", "Son kapatılan sekmeyi yeniden aç"),
                    ("Ctrl + P", "Belgeyi yazdır"),
                    ("Ctrl + D", "Belge özelliklerini ve izinlerini görüntüle"),
                ]),
                ("Yakınlaştırma & Görünüm", [
                    ("Ctrl + Artı (+)", "Sayfayı yakınlaştır"),
                    ("Ctrl + Eksi (-)", "Sayfayı uzaklaştır"),
                    ("Ctrl + 0", "Sayfayı pencere genişliğine sığdır"),
                    ("Ctrl + Fare Tekerleği", "İmleç noktasında akıcı yakınlaştır / uzaklaştır"),
                ]),
                ("Düzenleme & Araçlar", [
                    ("Esc", "Seçili aracı bırak, normal imleç moduna dön"),
                    ("Ctrl + Z", "Son işlemi geri al"),
                    ("Ctrl + Y / Ctrl+Shift+Z", "Geri alınan işlemi ileri al"),
                    ("Delete / Backspace", "Seçili çizim, metin veya medyayı sil"),
                    ("Ctrl + C", "Seçili metni panoya kopyala"),
                    ("Ctrl + A", "Tüm metni seç"),
                    ("F1", "Klavye kısayolları kılavuzunu aç"),
                ])
            ]
        else:
            return [
                ("Navigation & Reading", [
                    ("Page Down / Space", "Scroll / go to next page"),
                    ("Page Up / Shift+Space", "Scroll / go to previous page"),
                    ("Home", "Go to first page of document"),
                    ("End", "Go to last page of document"),
                    ("Alt + Left Arrow", "Navigate back to previous view"),
                    ("Alt + Right Arrow", "Navigate forward to next view"),
                    ("Ctrl + F", "Search text inside document"),
                    ("F3 / Shift + F3", "Find next / previous occurrence"),
                    ("F11", "Toggle fullscreen mode"),
                ]),
                ("File & Tabs", [
                    ("Ctrl + O", "Open PDF document"),
                    ("Ctrl + S", "Save document"),
                    ("Ctrl + Shift + S", "Save document as..."),
                    ("Ctrl + N", "Create new blank document"),
                    ("Ctrl + W", "Close active tab"),
                    ("Ctrl + Shift + T", "Reopen last closed tab"),
                    ("Ctrl + P", "Print document"),
                    ("Ctrl + D", "View document properties & metadata"),
                ]),
                ("Zoom & View", [
                    ("Ctrl + Plus (+)", "Zoom in"),
                    ("Ctrl + Minus (-)", "Zoom out"),
                    ("Ctrl + 0", "Fit page to window"),
                    ("Ctrl + Mouse Wheel", "Smooth zoom at cursor position"),
                ]),
                ("Editing & Tools", [
                    ("Esc", "Cancel active tool, switch to normal cursor"),
                    ("Ctrl + Z", "Undo last operation"),
                    ("Ctrl + Y / Ctrl+Shift+Z", "Redo reverted operation"),
                    ("Delete / Backspace", "Delete selected drawing, annotation, or media"),
                    ("Ctrl + C", "Copy selected text to clipboard"),
                    ("Ctrl + A", "Select all text"),
                    ("F1", "Open keyboard shortcuts guide"),
                ])
            ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LanguageManager.tr("shortcuts_dialog_title") + " - AuraPDF")
        self.resize(620, 520)
        self.setMinimumSize(560, 460)
        self.setModal(True)

        self._init_ui()
        apply_dialog_theme(self, parent)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Başlık
        header_layout = QHBoxLayout()
        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(ModernIconFactory.icon_keyboard_shortcuts().pixmap(30, 30))
        header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel(LanguageManager.tr("shortcuts_dialog_title"), self)
        f_title = QFont()
        f_title.setPointSize(12)
        f_title.setBold(True)
        lbl_title.setFont(f_title)
        lbl_desc = QLabel(LanguageManager.tr("shortcuts_dialog_desc"), self)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_desc)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Tab Widget
        self.tab_widget = QTabWidget(self)

        col_key = LanguageManager.tr("shortcuts_col_key")
        col_desc = LanguageManager.tr("shortcuts_col_desc")

        for cat_name, shortcuts in self._get_categories():
            table = QTableWidget(len(shortcuts), 2, self)
            table.setHorizontalHeaderLabels([col_key, col_desc])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

            for row_idx, (key_seq, desc) in enumerate(shortcuts):
                item_key = QTableWidgetItem(f" {key_seq} ")
                item_key.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                font_key = QFont()
                font_key.setBold(True)
                item_key.setFont(font_key)

                item_desc = QTableWidgetItem(desc)
                item_desc.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                table.setItem(row_idx, 0, item_key)
                table.setItem(row_idx, 1, item_desc)

            self.tab_widget.addTab(table, cat_name)

        main_layout.addWidget(self.tab_widget, 1)

        # Kapat Butonu
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton(LanguageManager.tr("close"), self)
        btn_close.setObjectName("CancelBtn")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)


ShortcutsDialog = KeyboardShortcutsDialog
