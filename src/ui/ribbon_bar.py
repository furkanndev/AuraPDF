"""
AuraPDF - Ribbon Kategori Çubuğu (Ribbon Category Bar)
======================================================
Araç çubuğunun (toolbar) üstünde yer alan, modern ofis ve PDF düzenleyici
yazılımlarında (MS Office, Adobe Acrobat, Foxit PDF) bulunan şerit (Ribbon)
kategori sekmeleri paneli.

Kategoriler:
- Dosya (File): Aç, Kaydet, Farklı Kaydet, Yazdır, Özellikler, Yeni Sekme
- Giriş (Home): En sık kullanılan temel PDF okuma ve düzenleme araçları
- Çizimler (Drawings): Kalem, Fosforlu Kalem, Metin, Silgi, Lazer, Cetvel, Seçim
- Ekle (Insert): Görsel, Ses Kaydı, Video, Ses Dosyası, GIF/Emoji, Tablo, Boş Sayfa
- Görünüm (View): Küçük Resimler, Yakınlaştırma, Döndürme, Çift Sayfa, Gece Modu, TTS
- Araçlar (Tools): PDF Birleştir, Böl, OCR, Word/Excel Dönüştür, İmza, Karşılaştır
- Tümü (All): Klasik tam araç çubuğu (tüm butonların bir arada gösterimi)
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QToolButton, QButtonGroup, 
                             QSizePolicy, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QSettings
from PyQt6.QtGui import QIcon, QCursor

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory


# Her kategoriye ait araç çubuğu elemanlarının objectName eşlemesi
CATEGORY_ITEMS = {
    "cat_file": [
        "btn_open", "btn_save", "btn_save_as", "btn_print", "sep_file_1",
        "btn_doc_props", "btn_new_tab", "btn_close_tab", "sep_file_2",
        "btn_toolbox", "btn_settings"
    ],
    "cat_home": [
        "btn_open", "btn_save", "sep_home_1",
        "btn_undo", "btn_redo", "sep_home_2",
        "btn_cursor", "btn_selection", "btn_hl", "btn_pen", "btn_text", "btn_eraser", "btn_insert", "sep_home_3",
        "lbl_zoom", "btn_fit_page", "spacer_left",
        "page_widget", "spacer_right",
        "btn_search", "btn_fullscreen"
    ],
    "cat_draw": [
        "btn_undo", "btn_redo", "sep_draw_1",
        "btn_cursor", "btn_selection", "sep_draw_2",
        "btn_pen", "btn_hl", "btn_text", "btn_eraser", "btn_pointer", "btn_ruler", "sep_draw_3",
        "lbl_zoom", "btn_fit_page", "spacer_left",
        "page_widget", "spacer_right",
        "btn_fullscreen"
    ],
    "cat_insert": [
        "btn_insert_img", "btn_insert_voice", "btn_insert_camera", "btn_insert_audio", 
        "btn_insert_emoji", "btn_insert_table", "btn_insert_blank", "sep_insert_1",
        "lbl_zoom", "btn_fit_page", "spacer_left",
        "page_widget", "spacer_right",
        "btn_fullscreen"
    ],
    "cat_view": [
        "btn_contents", "sep_view_1",
        "btn_nav_back", "btn_nav_forward", "sep_view_2",
        "lbl_zoom", "btn_fit_page", "btn_rotate", "sep_view_3",
        "btn_view_mode", "btn_reading_mode", "btn_speech", "spacer_left",
        "page_widget", "spacer_right",
        "btn_search", "btn_fullscreen"
    ],
    "cat_tools": [
        "btn_toolbox", "sep_tool_1",
        "btn_tool_organize", "btn_tool_merge", "btn_tool_split", "sep_tool_2",
        "btn_tool_word", "btn_tool_excel", "sep_tool_3",
        "btn_tool_ocr", "btn_tool_editor", "btn_tool_sign", "btn_tool_compare", "btn_tool_redact", "btn_tool_encrypt", "spacer_right",
        "btn_settings"
    ],
    "cat_all": None  # Tüm klasik butonları gösterir
}


class CategoryTabButton(QToolButton):
    """Ribbon sekme butonu. Çift tıklandığında araç çubuğunu daraltır/genişletir."""
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(15, 15))
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ModernCategoryBar(QWidget):
    """
    Toolbar'ın hemen üstünde yer alan seçenekler ve kategori çubuğu.
    Kullanıcı sekmeler arasında geçiş yaparak toolbar'ı ilgili moda odaklar.
    """
    categoryChanged = pyqtSignal(str)
    toolbarCollapseToggled = pyqtSignal(bool)

    # Kategori tanımları: (anahtar, dil_anahtarı, ipucu_anahtarı, ikon_fonksiyonu)
    CATEGORIES = [
        ("cat_file", "cat_file", "cat_file_tip", ModernIconFactory.icon_folder),
        ("cat_home", "cat_home", "cat_home_tip", ModernIconFactory.icon_home),
        ("cat_draw", "cat_draw", "cat_draw_tip", ModernIconFactory.icon_pen),
        ("cat_insert", "cat_insert", "cat_insert_tip", ModernIconFactory.icon_insert),
        ("cat_view", "cat_view", "cat_view_tip", ModernIconFactory.icon_view_single),
        ("cat_tools", "cat_tools", "cat_tools_tip", ModernIconFactory.icon_toolbox),
        ("cat_all", "cat_all", "cat_all_tip", ModernIconFactory.icon_all_grid),
    ]

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setObjectName("ModernCategoryBar")
        self.setFixedHeight(35)

        self._active_category = "cat_home"
        self._is_collapsed = False
        self._tab_buttons = {}

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 0)
        layout.setSpacing(3)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for cat_key, lang_key, tip_key, icon_fn in self.CATEGORIES:
            btn = CategoryTabButton(self)
            btn.setObjectName(f"cat_btn_{cat_key}")
            btn.setProperty("is_category_tab", True)
            btn.setText(f" {LanguageManager.tr(lang_key)}")
            btn.setToolTip(LanguageManager.tr(tip_key))
            if icon_fn:
                try:
                    btn.setIcon(icon_fn())
                except Exception:
                    pass

            btn.clicked.connect(lambda checked, k=cat_key: self._on_tab_clicked(k))
            btn.doubleClicked.connect(self.toggle_toolbar_collapse)
            self.btn_group.addButton(btn)
            layout.addWidget(btn)
            self._tab_buttons[cat_key] = btn

        # Sağa yaslama boşluğu
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)

        # Araç çubuğunu daraltma / genişletme butonu (Chevron Up / Down)
        self.btn_toggle_collapse = QToolButton(self)
        self.btn_toggle_collapse.setObjectName("btn_toggle_toolbar")
        self.btn_toggle_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_collapse.setIcon(ModernIconFactory.icon_chevron_up())
        self.btn_toggle_collapse.setText("")
        self.btn_toggle_collapse.setToolTip(LanguageManager.tr("collapse_toolbar"))
        self.btn_toggle_collapse.clicked.connect(self.toggle_toolbar_collapse)
        layout.addWidget(self.btn_toggle_collapse)

    def _on_tab_clicked(self, cat_key: str):
        # Eğer toolbar daraltılmışsa, sekmeye tıklandığında aç
        if self._is_collapsed:
            self.set_toolbar_collapsed(False)
        self.set_active_category(cat_key, trigger_signal=True)

    def set_active_category(self, cat_key: str, trigger_signal: bool = True):
        if cat_key not in self._tab_buttons:
            cat_key = "cat_home"

        self._active_category = cat_key
        btn = self._tab_buttons.get(cat_key)
        if btn and not btn.isChecked():
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)

        if trigger_signal:
            self.categoryChanged.emit(cat_key)

    def get_active_category(self) -> str:
        return self._active_category

    def toggle_toolbar_collapse(self):
        self.set_toolbar_collapsed(not self._is_collapsed)

    def set_toolbar_collapsed(self, collapsed: bool):
        self._is_collapsed = collapsed
        self.btn_toggle_collapse.setIcon(
            ModernIconFactory.icon_chevron_down() if collapsed else ModernIconFactory.icon_chevron_up()
        )
        self.toolbarCollapseToggled.emit(collapsed)
        if self.main_window and hasattr(self.main_window, 'toolbar'):
            self.main_window.toolbar.setVisible(not collapsed)

    def retranslate_ui(self):
        for cat_key, lang_key, tip_key, _ in self.CATEGORIES:
            btn = self._tab_buttons.get(cat_key)
            if btn:
                btn.setText(f" {LanguageManager.tr(lang_key)}")
                btn.setToolTip(LanguageManager.tr(tip_key))
        self.btn_toggle_collapse.setToolTip(LanguageManager.tr("collapse_toolbar"))

    def apply_theme(self, spec: dict):
        """Aktif temaya göre kategori çubuğunun ve butonlarının QSS stillerini günceller."""
        main_bg = spec.get("main_bg", "#2b2d30")
        tb_bg = spec.get("tb_bg", "#35383c")
        tb_border = spec.get("tb_border", "#222427")
        btn_hover = spec.get("tab_hover", spec.get("btn_hover", "#42464b"))
        accent = spec.get("accent", "#60a5fa")
        tab_text = spec.get("tab_text", "#cbd5e1")
        main_text = spec.get("main_text", "#f1f5f9")

        self.setStyleSheet(f"""
            QWidget#ModernCategoryBar {{
                background-color: {main_bg};
                border-bottom: 1px solid {tb_border};
            }}
            QToolButton[is_category_tab="true"] {{
                background-color: transparent;
                border: 1px solid transparent;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 4px 12px 5px 12px;
                font-size: 12px;
                font-weight: 500;
                color: {tab_text};
                margin-bottom: 0px;
            }}
            QToolButton[is_category_tab="true"]:hover {{
                background-color: {btn_hover};
                color: #ffffff;
            }}
            QToolButton[is_category_tab="true"]:checked {{
                background-color: {tb_bg};
                color: #ffffff;
                font-weight: bold;
                border-top: 2.5px solid {accent};
                border-left: 1px solid {tb_border};
                border-right: 1px solid {tb_border};
                border-bottom: 1px solid {tb_bg};
            }}
            QToolButton#btn_toggle_toolbar {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px 8px;
                color: {tab_text};
                font-size: 13px;
                font-weight: bold;
            }}
            QToolButton#btn_toggle_toolbar:hover {{
                background-color: {btn_hover};
                color: #ffffff;
            }}
        """)
