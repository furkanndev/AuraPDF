"""
AuraPDF - Ayarlar Diyaloğu (Settings Dialog)
===========================================
Kullanıcının genel tercihlerini, uygulama temasını (Siyah, Gri, Lacivert, Zümrüt, Mor, Kızıl, Nord),
klavye kısayollarını, PDF düzenleyen kişi / yazar üstveri bilgilerini ve arayüz dilini
yönetebildiği modern ve kapsamlı ayarlar paneli.
"""

import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QCheckBox, QRadioButton, 
                             QButtonGroup, QTabWidget, QWidget, QFrame, 
                             QComboBox, QMessageBox, QKeySequenceEdit, QScrollArea,
                             QGridLayout, QListWidget, QListWidgetItem, QAbstractItemView,
                             QFileDialog, QApplication, QToolButton, QMenu)
from PyQt6.QtCore import Qt, QSettings, QRectF, QPointF, QTimer, QEvent
from PyQt6.QtGui import QIcon, QFont, QColor, QKeySequence, QPainter, QPen, QBrush
from PyQt6.QtCore import QSize

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet
from src.core.shortcut_helper import (
    is_mouse_shortcut,
    parse_mouse_shortcut,
    build_mouse_shortcut_string,
    format_shortcut_display,
    get_mouse_preset_options,
    clean_modifiers,
)
from src.ui.icons import ModernIconFactory
from src.ui.cursors import CursorFactory, CURSOR_PRESETS

TOOLBAR_ITEMS_META = {
    "btn_contents": ("tb_item_contents", ModernIconFactory.icon_contents),
    "btn_undo": ("tb_item_undo", ModernIconFactory.icon_undo),
    "btn_redo": ("tb_item_redo", ModernIconFactory.icon_redo),
    "btn_nav_back": ("tb_item_nav_back", ModernIconFactory.icon_nav_back),
    "btn_nav_forward": ("tb_item_nav_forward", ModernIconFactory.icon_nav_forward),
    "btn_cursor": ("tb_item_cursor", ModernIconFactory.icon_cursor),
    "btn_selection": ("tb_item_selection", ModernIconFactory.icon_select_rect),
    "btn_hl": ("tb_item_hl", ModernIconFactory.icon_highlighter),
    "btn_pen": ("tb_item_pen", ModernIconFactory.icon_pen),
    "btn_text": ("tb_item_text", ModernIconFactory.icon_text_box),
    "btn_eraser": ("tb_item_eraser", ModernIconFactory.icon_eraser),
    "btn_pointer": ("tb_item_pointer", ModernIconFactory.icon_pointer),
    "lbl_zoom": ("tb_item_zoom", None),
    "btn_fit_page": ("tb_item_fit_page", ModernIconFactory.icon_fit_page),
    "page_widget": ("tb_item_page_nav", None),
    "btn_rotate": ("tb_item_rotate", ModernIconFactory.icon_rotate),
    "btn_view_mode": ("tb_item_view_mode", ModernIconFactory.icon_view_single),
    "btn_reading_mode": ("tb_item_reading_mode", ModernIconFactory.icon_reading_mode),
    "btn_search": ("tb_item_search", ModernIconFactory.icon_search),
    "btn_print": ("tb_item_print", ModernIconFactory.icon_print),
    "btn_save": ("tb_item_save", ModernIconFactory.icon_save),
    "btn_open": ("tb_item_open", None),
    "btn_toolbox": ("tb_item_toolbox", ModernIconFactory.icon_toolbox),
    "btn_settings": ("tb_item_settings", ModernIconFactory.icon_settings),
    "btn_fullscreen": ("tb_item_fullscreen", ModernIconFactory.icon_fullscreen),
    "btn_insert": ("tb_item_insert", ModernIconFactory.icon_insert),
}

DEFAULT_TOOLBAR_LAYOUT = [
    "btn_contents", "btn_undo", "btn_redo", "btn_nav_back", "btn_nav_forward", "sep_1",
    "btn_cursor", "btn_selection", "btn_hl", "btn_pen",
    "btn_text", "btn_insert", "btn_eraser", "btn_pointer", "sep_2",
    "lbl_zoom", "btn_fit_page",
    "spacer_left",
    "page_widget", "btn_rotate", "btn_view_mode", "btn_reading_mode",
    "spacer_right",
    "btn_search", "sep_3",
    "btn_print", "btn_save", "btn_open", "btn_toolbox", "btn_settings", "btn_fullscreen"
]

DEFAULT_TOOLBAR_USER_ITEMS = [
    x for x in DEFAULT_TOOLBAR_LAYOUT if not x.startswith("sep_") and not x.startswith("spacer_")
]


def build_full_toolbar_order(items: list) -> list:
    """Kullanıcının belirlediği buton sıralamasına göre ayırıcıları (separator) ve
    hizalama boşluklarını (spacer) doğru konumlara yerleştirerek eksiksiz toolbar sıralamasını döner."""
    if not items:
        return list(DEFAULT_TOOLBAR_LAYOUT)

    # 1. Spacers ve separotorları ayıkla, sadece butonları al
    buttons = [x for x in items if x in TOOLBAR_ITEMS_META]

    # Sıralamayı koruyarak tekilleştir
    deduped = []
    for b in buttons:
        if b not in deduped:
            deduped.append(b)

    # Eksik buton varsa varsayılan sıradan ekle
    for b in DEFAULT_TOOLBAR_USER_ITEMS:
        if b not in deduped:
            deduped.append(b)

    # Eğer butonlar varsayılan sıralama ile birebir aynıysa doğrudan ana düzeni dön
    if deduped == DEFAULT_TOOLBAR_USER_ITEMS:
        return list(DEFAULT_TOOLBAR_LAYOUT)

    # Özel sıralama için orta küme tespiti (page_widget etrafındaki bitişik gezinim/görünüm butonları)
    center_candidates = {"page_widget", "btn_rotate", "btn_view_mode", "btn_fullscreen"}

    if "page_widget" in deduped:
        p_idx = deduped.index("page_widget")
        start_idx = p_idx
        while start_idx - 1 >= 0 and deduped[start_idx - 1] in center_candidates:
            start_idx -= 1
        end_idx = p_idx
        while end_idx + 1 < len(deduped) and deduped[end_idx + 1] in center_candidates:
            end_idx += 1
        left_part = deduped[:start_idx]
        mid_part = deduped[start_idx:end_idx + 1]
        right_part = deduped[end_idx + 1:]
    else:
        left_part = deduped
        mid_part = []
        right_part = []

    # Sol kısma ayırıcıları yerleştir
    final_left = []
    for b in left_part:
        if b == "btn_cursor" and "sep_1" not in final_left and "btn_redo" in final_left:
            final_left.append("sep_1")
        if b == "lbl_zoom" and "sep_2" not in final_left and ("btn_pointer" in final_left or "btn_eraser" in final_left):
            final_left.append("sep_2")
        final_left.append(b)

    if "sep_1" not in final_left and "btn_redo" in final_left:
        idx = final_left.index("btn_redo") + 1
        if idx < len(final_left):
            final_left.insert(idx, "sep_1")
    if "sep_2" not in final_left and "lbl_zoom" in final_left:
        idx = final_left.index("lbl_zoom")
        if idx > 0:
            final_left.insert(idx, "sep_2")

    # Sağ kısma ayırıcıları yerleştir
    final_right = []
    for b in right_part:
        if b in ("btn_print", "btn_save", "btn_open") and "sep_3" not in final_right and "btn_search" in final_right:
            final_right.append("sep_3")
        final_right.append(b)

    if "sep_3" not in final_right and "btn_search" in final_right:
        idx = final_right.index("btn_search") + 1
        if idx < len(final_right):
            final_right.insert(idx, "sep_3")

    return final_left + ["spacer_left"] + mid_part + ["spacer_right"] + final_right

DEFAULT_SHORTCUTS = {
    "pen": "P",
    "highlighter": "H",
    "eraser": "E",
    "select": "V",
    "selection_tool": "S",
    "text": "T",
    "pointer": "L",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "zoom_in": "Ctrl++",
    "zoom_out": "Ctrl+-",
    "fit_width": "Ctrl+0",
    "fullscreen": "F11",
}


def get_default_author_info():
    """Varsayılan olarak bilgisayar kullanıcı adını ve bilgisayar adını döner."""
    import os
    try:
        import getpass
        username = getpass.getuser()
    except Exception:
        username = os.environ.get("USERNAME", "") or os.environ.get("USER", "")
    
    computer_name = os.environ.get("COMPUTERNAME", "") or os.environ.get("HOSTNAME", "")
    if not computer_name:
        try:
            import platform
            computer_name = platform.node()
        except Exception:
            computer_name = ""

    return username, computer_name


class CursorPreviewBox(QFrame):
    """
    Kullanıcının seçtiği imleci hem açık (beyaz) hem de koyu (karanlık) sayfa
    arka planında fareyle üzerine gelerek canlı olarak test etmesini sağlayan
    bölünmüş (split) etkileşimli önizleme alanı.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setMouseTracking(True)
        self.active_cursor = None

    def set_preview_cursor(self, cursor):
        self.active_cursor = cursor
        if cursor is not None:
            self.setCursor(cursor)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush, QPen, QFont
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        mid = w / 2.0

        # Dış çerçeve ve sol açık sayfa (beyaz)
        p.setPen(QPen(QColor("#444850"), 1.2))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)

        # Sağ koyu sayfa (karanlık mod)
        p.save()
        p.setClipRect(QRectF(mid, 0, mid, h))
        p.setBrush(QBrush(QColor("#1A1A20")))
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)
        p.restore()

        # Dikey kesikli ayırıcı çizgi
        p.setPen(QPen(QColor("#64748b"), 1.0, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(mid, 0), QPointF(mid, h))

        # Sol taraf açık sayfa çizgileri ve yazısı
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor("#334155")))
        p.drawText(QRectF(15, 12, mid - 30, 18), Qt.AlignmentFlag.AlignLeft, LanguageManager.tr("cursor_preview_light"))
        p.setPen(QPen(QColor("#94a3b8"), 1.0))
        p.drawLine(QPointF(15, 42), QPointF(mid - 25, 42))
        p.drawLine(QPointF(15, 58), QPointF(mid - 55, 58))
        p.drawLine(QPointF(15, 74), QPointF(mid - 35, 74))

        # Sağ taraf koyu sayfa çizgileri ve yazısı
        p.setPen(QPen(QColor("#f1f5f9")))
        p.drawText(QRectF(mid + 15, 12, mid - 30, 18), Qt.AlignmentFlag.AlignLeft, LanguageManager.tr("cursor_preview_dark"))
        p.setPen(QPen(QColor("#475569"), 1.0))
        p.drawLine(QPointF(mid + 15, 42), QPointF(w - 25, 42))
        p.drawLine(QPointF(mid + 15, 58), QPointF(w - 55, 58))
        p.drawLine(QPointF(mid + 15, 74), QPointF(w - 35, 74))

        p.end()


class _KeySeqWrapper:
    def __init__(self, val: str):
        self._val = str(val) if val else ""
    def toString(self):
        return self._val
    def isEmpty(self):
        return not bool(self._val)
    def __str__(self):
        return self._val


class ModernShortcutButton(QPushButton):
    """
    Kullanıcının kutuya tıkladığı anda farenin basılan tuşunu (Orta Tuş,
    Yan Tuş 4 / Geri, Yan Tuş 5 / İleri, Sağ Tık) otomatik olarak yakalayan
    veya sol tıklandığında dinleme moduna geçip basılacak ilk klavye tuşunu
    ya da fare tuşunu anında kaydeden özel kısayol butonu.
    """
    def __init__(self, parent_edit):
        super().__init__(parent_edit)
        self.parent_edit = parent_edit
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(160)
        self.setFixedHeight(32)

    def mousePressEvent(self, event):
        btn = event.button()
        # Eğer doğrudan Orta tuş, Yan tuş 1 (Geri), Yan tuş 2 (İleri), Sağ tık basıldıysa anında yakala
        if btn in (Qt.MouseButton.MiddleButton, Qt.MouseButton.XButton1, 
                   Qt.MouseButton.XButton2, Qt.MouseButton.RightButton):
            mouse_str = build_mouse_shortcut_string(btn, clean_modifiers(event.modifiers()))
            if mouse_str:
                self.parent_edit.setShortcutValue(mouse_str)
                self.parent_edit.stop_recording()
                event.accept()
                return

        # Sol tık durumu
        if btn == Qt.MouseButton.LeftButton:
            if self.parent_edit._is_recording:
                # Kayıt modundayken modifier ile sol tık yapıldıysa (örn: Ctrl + Sol Tık)
                mods = clean_modifiers(event.modifiers())
                if mods != Qt.KeyboardModifier.NoModifier:
                    mouse_str = build_mouse_shortcut_string(btn, mods)
                    if mouse_str:
                        self.parent_edit.setShortcutValue(mouse_str)
                        self.parent_edit.stop_recording()
                        event.accept()
                        return
                # Düz sol tık ile kaydı sonlandır
                self.parent_edit.stop_recording()
                event.accept()
                return
            else:
                # Kayıt modunu başlat
                self.parent_edit.start_recording()
                event.accept()
                return

        super().mousePressEvent(event)


class ModernShortcutEdit(QWidget):
    """
    Hem klavye tuş kombinasyonlarını hem de fare tuşlarını (Orta Tuş,
    Yan Tuş 4 / Geri, Yan Tuş 5 / İleri, Ctrl/Shift kombinasyonları)
    otomatik olarak dinleyip atayabilen modern kısayol düzenleyici bileşeni.
    """
    def __init__(self, default_value: str = "", parent=None):
        super().__init__(parent)
        self._current_shortcut = str(default_value or "")
        self._is_recording = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_input = ModernShortcutButton(self)

        self.btn_clear = QToolButton(self)
        self.btn_clear.setText("✕")
        self.btn_clear.setToolTip(LanguageManager.tr("shortcut_clear_tooltip"))
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setFixedSize(28, 32)
        self.btn_clear.clicked.connect(self.clear_shortcut)

        layout.addWidget(self.btn_input)
        layout.addWidget(self.btn_clear)

        self._update_display()

    def _toggle_recording(self):
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self._is_recording:
            return
        self._is_recording = True
        self.btn_input.setText(LanguageManager.tr("shortcut_press_key_or_mouse"))
        self._apply_style()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def stop_recording(self):
        if self._is_recording:
            self._is_recording = False
            app = QApplication.instance()
            if app:
                try:
                    app.removeEventFilter(self)
                except Exception:
                    pass
            self._update_display()

    def hideEvent(self, event):
        self.stop_recording()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.stop_recording()
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if not self._is_recording:
            return super().eventFilter(obj, event)

        ev_type = event.type()
        if ev_type == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.stop_recording()
                return True
            if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                mods_list = []
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    mods_list.append("Ctrl")
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    mods_list.append("Shift")
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    mods_list.append("Alt")
                if mods_list:
                    self.btn_input.setText(" + ".join(mods_list) + " + ...")
                return True

            mods = event.modifiers().value
            key_combo = mods | key
            seq_str = QKeySequence(key_combo).toString()
            if seq_str:
                self.setShortcutValue(seq_str)
            self.stop_recording()
            return True

        elif ev_type == QEvent.Type.MouseButtonPress:
            btn = event.button()
            if btn in (Qt.MouseButton.MiddleButton, Qt.MouseButton.XButton1, Qt.MouseButton.XButton2, Qt.MouseButton.RightButton):
                mouse_str = build_mouse_shortcut_string(btn, clean_modifiers(event.modifiers()))
                if mouse_str:
                    self.setShortcutValue(mouse_str)
                self.stop_recording()
                return True
            elif btn == Qt.MouseButton.LeftButton:
                g_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                if self.btn_clear.rect().contains(self.btn_clear.mapFromGlobal(g_pos)):
                    self.stop_recording()
                    return False
                if self.btn_input.rect().contains(self.btn_input.mapFromGlobal(g_pos)):
                    mods = clean_modifiers(event.modifiers())
                    if mods != Qt.KeyboardModifier.NoModifier:
                        mouse_str = build_mouse_shortcut_string(btn, mods)
                        if mouse_str:
                            self.setShortcutValue(mouse_str)
                    self.stop_recording()
                    return True
                self.stop_recording()
                return False

        return super().eventFilter(obj, event)

    def keySequence(self):
        return _KeySeqWrapper(self._current_shortcut)

    def setKeySequence(self, seq):
        if isinstance(seq, QKeySequence):
            self.setShortcutValue(seq.toString())
        else:
            self.setShortcutValue(str(seq) if seq else "")

    def shortcutValue(self) -> str:
        return self._current_shortcut

    def setShortcutValue(self, val: str):
        new_val = str(val).strip() if val else ""
        # Çakışma kontrolü: Aynı kısayol başka bir araca atanmış mı?
        if new_val:
            conflict_action = self._check_conflict(new_val)
            if conflict_action:
                # Çakışma var, kullanıcıya bildir ve eski değere geri dön
                from PyQt6.QtWidgets import QMessageBox
                action_labels = {
                    "pen": LanguageManager.tr("shortcut_pen"),
                    "highlighter": LanguageManager.tr("shortcut_highlighter"),
                    "eraser": LanguageManager.tr("shortcut_eraser"),
                    "select": LanguageManager.tr("shortcut_select"),
                    "selection_tool": LanguageManager.tr("shortcut_selection_tool"),
                    "text": LanguageManager.tr("shortcut_text"),
                    "pointer": LanguageManager.tr("shortcut_pointer"),
                    "undo": LanguageManager.tr("shortcut_undo"),
                    "redo": LanguageManager.tr("shortcut_redo"),
                    "zoom_in": LanguageManager.tr("shortcut_zoom_in"),
                    "zoom_out": LanguageManager.tr("shortcut_zoom_out"),
                    "fit_width": LanguageManager.tr("shortcut_fit_width"),
                    "fullscreen": LanguageManager.tr("shortcut_fullscreen"),
                }
                conflict_name = action_labels.get(conflict_action, conflict_action)
                display_val = format_shortcut_display(new_val)
                QMessageBox.warning(
                    self,
                    LanguageManager.tr("shortcut_conflict_title"),
                    LanguageManager.tr("shortcut_conflict_text").format(
                        shortcut=display_val, action=conflict_name
                    ),
                )
                self._update_display()
                return
        self._current_shortcut = new_val
        self._update_display()

    def clear_shortcut(self):
        self.setShortcutValue("")

    def _check_conflict(self, new_val: str) -> str:
        """Aynı kısayolun başka bir araca atanıp atanmadığını kontrol eder.
        Çakışma varsa çakışan action_key'i, yoksa boş string döner."""
        # Üst widget'ları dolaşarak ModernSettingsDialog'u bul
        dialog = self.parent()
        while dialog is not None and not isinstance(dialog, ModernSettingsDialog):
            dialog = dialog.parent() if hasattr(dialog, 'parent') and callable(dialog.parent) else None
        if dialog is None or not hasattr(dialog, 'shortcut_edits'):
            return ""
        normalized = new_val.strip().lower()
        for action_key, edit_widget in dialog.shortcut_edits.items():
            if edit_widget is self:
                continue
            existing = edit_widget.shortcutValue().strip().lower()
            if existing and existing == normalized:
                return action_key
        return ""

    def _update_display(self):
        txt = format_shortcut_display(self._current_shortcut)
        self.btn_input.setText(txt)
        self._apply_style()

    def _apply_style(self):
        if self._is_recording:
            self.btn_input.setStyleSheet(
                "QPushButton { background: rgba(56, 189, 248, 0.22); border: 2px solid #38bdf8; "
                "border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: bold; "
                "color: #ffffff; text-align: center; }"
            )
        else:
            has_val = bool(self._current_shortcut)
            col = "#e2e8f0" if has_val else "#94a3b8"
            self.btn_input.setStyleSheet(
                f"QPushButton {{ background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15); "
                f"border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; "
                f"color: {col}; text-align: center; }} "
                "QPushButton:hover { background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.35); color: #ffffff; }"
            )
        self.btn_clear.setStyleSheet(
            "QToolButton { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15); "
            "border-radius: 6px; font-size: 11px; color: #cbd5e1; } "
            "QToolButton:hover { background: rgba(239, 68, 68, 0.22); border: 1px solid #ef4444; color: #ffffff; }"
        )


class AuraSettingsDialog(QDialog):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.settings = QSettings("AuraPDF", "PDFViewer")
        self.shortcut_settings = QSettings("AuraPDF", "Shortcuts")
        
        self.setWindowTitle(LanguageManager.tr("settings_title"))
        self.setWindowIcon(ModernIconFactory.icon_settings())
        self.resize(880, 680)
        self.setMinimumSize(740, 520)
        self.setSizeGripEnabled(True)
        
        # Seçili temanın rengine göre stil
        self.current_theme = self.settings.value("app_theme", "gray")
        self._apply_dialog_style()
        self._init_ui()
        self._load_saved_values()

    def _apply_dialog_style(self):
        theme_colors = {
            "gray": {
                "bg": "#2b2d30", "card": "#35383c", "border": "#444850",
                "accent": "#60a5fa", "text": "#f1f5f9", "muted": "#94a3b8", "cancel": "#444850"
            },
            "navy": {
                "bg": "#0f172a", "card": "#1e293b", "border": "#334155",
                "accent": "#38bdf8", "text": "#e2e8f0", "muted": "#94a3b8", "cancel": "#334155"
            },
            "emerald": {
                "bg": "#091a14", "card": "#112a21", "border": "#1a3d30",
                "accent": "#10b981", "text": "#ecfdf5", "muted": "#a7f3d0", "cancel": "#1a3d30"
            },
            "purple": {
                "bg": "#150d22", "card": "#201435", "border": "#321f52",
                "accent": "#a855f7", "text": "#faf5ff", "muted": "#d8b4fe", "cancel": "#321f52"
            },
            "crimson": {
                "bg": "#1d0b10", "card": "#2d1118", "border": "#441924",
                "accent": "#f43f5e", "text": "#fff1f2", "muted": "#fecdd3", "cancel": "#441924"
            },
            "nord": {
                "bg": "#181e29", "card": "#222b3a", "border": "#313e54",
                "accent": "#38bdf8", "text": "#f0f6fc", "muted": "#94a3b8", "cancel": "#313e54"
            },
            "dark": {
                "bg": "#121212", "card": "#1c1c1c", "border": "#2a2a2a",
                "accent": "#388bfd", "text": "#e0e0e0", "muted": "#888888", "cancel": "#2c2c2c"
            },
            "vice_city": {
                "bg": "#160024", "card": "#240e3b", "border": "#4a1c72",
                "accent": "#ff2a85", "text": "#ffffff", "muted": "#00f0ff", "cancel": "#381458"
            }
        }
        c = theme_colors.get(self.current_theme, theme_colors["dark"])

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg']};
                color: {c['text']};
            }}
            QListWidget#SettingsSidebar {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 8px 0px;
            }}
            QListWidget#SettingsSidebar::item {{
                background-color: transparent;
                border: 1px solid transparent;
                margin: 2px 4px;
                border-radius: 8px;
                padding: 10px 14px;
                color: {c['muted']};
                font-size: 13px;
                font-weight: 500;
            }}
            QListWidget#SettingsSidebar::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }}
            QListWidget#SettingsSidebar::item:selected {{
                background-color: {c['accent']};
                border-color: {c['accent']};
                color: #ffffff;
                font-weight: bold;
            }}
            QListWidget#SettingsSidebar::item:selected:hover {{
                background-color: {c['accent']};
                border-color: {c['accent']};
                color: #ffffff;
                font-weight: bold;
            }}
            QStackedWidget {{
                background-color: {c['card']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }}
            QLabel {{
                color: {c['text']};
            }}
            QLineEdit, QComboBox, QKeySequenceEdit {{
                background-color: {c['bg']};
                color: {c['text']};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 13px;
                min-height: 28px;
            }}
            QLineEdit:focus, QComboBox:focus, QKeySequenceEdit:focus {{
                border-color: {c['accent']};
            }}
            QListWidget#ToolbarList {{
                background-color: {c['bg']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget#ToolbarList::item {{
                background-color: {c['card']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 6px 10px;
                margin: 2px;
                font-size: 12px;
                font-weight: 500;
                color: {c['text']};
            }}
            QListWidget#ToolbarList::item:hover {{
                background-color: {c['bg']};
                border-color: {c['accent']};
                color: #ffffff;
            }}
            QListWidget#ToolbarList::item:selected {{
                background-color: {c['accent']};
                border: 1px solid {c['accent']};
                color: #ffffff;
                font-weight: bold;
            }}
            QWidget#TransparentWidget {{
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {c['card']};
                color: {c['text']};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: {c['accent']};
                color: #ffffff;
            }}
            QPushButton[class="primary"] {{
                background-color: {c['accent']};
                border-color: {c['accent']};
                color: #ffffff;
                font-weight: bold;
            }}
            QRadioButton {{
                color: {c['text']};
                font-size: 13px;
                font-weight: bold;
            }}
            QRadioButton::indicator:checked {{
                background-color: {c['accent']};
                border: 2px solid {c['accent']};
                border-radius: 6px;
            }}
            QListWidget {{
                background-color: {c['bg']};
                color: {c['text']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }}
            QListWidget::item {{
                background-color: {c['card']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
                color: {c['text']};
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }}
            QListWidget::item:selected {{
                background-color: {c['accent']};
                color: #ffffff;
                font-weight: bold;
                border-color: {c['accent']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {c['card']};
                color: {c['text']};
                selection-background-color: {c['accent']};
                selection-color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 28px;
                padding: 6px 10px;
                border-radius: 4px;
                color: {c['text']};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {c['accent']};
                color: #ffffff;
            }}
            QCheckBox, QRadioButton {{
                color: {c['text']};
                font-size: 13px;
                spacing: 8px;
            }}
            QFrame.card {{
                background-color: {c['card']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 12px;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {c['accent']};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {c['accent']};
                color: #ffffff;
            }}
            QPushButton#CancelBtn {{
                background-color: {c['cancel']};
                color: {c['text']};
                font-weight: 500;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton#CancelBtn:hover {{
                background-color: {c['border']};
                color: #ffffff;
            }}
            QPushButton#SecondaryBtn {{
                background-color: {c['bg']};
                color: {c['text']};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 5px 12px;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {c['card']};
                border-color: {c['accent']};
                color: #ffffff;
            }}
            QPushButton#DangerBtn {{
                background-color: rgba(239, 68, 68, 0.12);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#DangerBtn:hover {{
                background-color: rgba(239, 68, 68, 0.25);
                border-color: #ef4444;
                color: #ffffff;
            }}
            QPushButton#DangerBtn:pressed {{
                background-color: #dc2626;
                color: #ffffff;
            }}
        """)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        main_split = QHBoxLayout()
        root_layout.addLayout(main_split, 1)

        # Sidebar (QListWidget)
        from PyQt6.QtWidgets import QListWidget, QStackedWidget, QListWidgetItem
        self.sidebar = QListWidget(self)
        self.sidebar.setFixedWidth(210)
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setSpacing(4)
        main_split.addWidget(self.sidebar)

        # Content Area (QStackedWidget)
        self.stacked_widget = QStackedWidget(self)
        main_split.addWidget(self.stacked_widget, 1)

        # Pages
        pages = [
            (LanguageManager.tr("settings_tab_general"), self._build_general_tab),
            (LanguageManager.tr("settings_tab_theme"), self._build_theme_tab),
            (LanguageManager.tr("settings_tab_shortcuts"), self._build_shortcuts_tab),
            (LanguageManager.tr("settings_tab_author"), self._build_author_tab),
            (LanguageManager.tr("settings_tab_lang"), self._build_lang_tab),
            (LanguageManager.tr("settings_tab_toolbar"), self._build_toolbar_tab),
            (LanguageManager.tr("cursor_settings_title"), self._build_cursor_tab),
            (LanguageManager.tr("settings_tab_updates"), self._build_updates_tab)
        ]
        
        for name, build_func in pages:
            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setSizeHint(QSize(0, 44))
            self.sidebar.addItem(item)
            
            page_widget = QWidget()
            build_func(page_widget)
            self.stacked_widget.addWidget(page_widget)
            
        self.sidebar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # Alt Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("btn_cancel_settings"))
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("btn_apply_settings"))
        self.btn_apply.setObjectName("SecondaryBtn")
        self.btn_apply.clicked.connect(self.apply_settings)
        btn_layout.addWidget(self.btn_apply)

        self.btn_save = QPushButton(LanguageManager.tr("btn_save_settings"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)

        root_layout.addLayout(btn_layout)

    # ----------------------------------------------------
    # SEKME: GENEL TERCİHLER (İLK SEKME)
    # ----------------------------------------------------
    def _build_general_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_title = QLabel(LanguageManager.tr("general_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        card_layout.addWidget(QLabel(LanguageManager.tr("default_zoom_mode_lbl")))
        self.cmb_zoom_mode = QComboBox()
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_last"), "last")
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_100"), "100")
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_fit"), "fit")
        card_layout.addWidget(self.cmb_zoom_mode)
        
        card_layout.addSpacing(6)
        card_layout.addWidget(QLabel(LanguageManager.tr("default_page_template_lbl")))
        self.cmb_default_template = QComboBox()
        self.cmb_default_template.addItem(LanguageManager.tr("style_blank_title"), "blank")
        self.cmb_default_template.addItem(LanguageManager.tr("style_lined_title"), "lined")
        self.cmb_default_template.addItem(LanguageManager.tr("style_grid_title"), "grid")
        self.cmb_default_template.addItem(LanguageManager.tr("style_dotted_title"), "dotted")
        self.cmb_default_template.addItem(LanguageManager.tr("style_cornell_title"), "cornell")
        self.cmb_default_template.addItem(LanguageManager.tr("style_music_title"), "music")
        self.cmb_default_template.addItem(LanguageManager.tr("style_dark_title"), "dark")
        self.cmb_default_template.addItem(LanguageManager.tr("style_cover_title"), "cover")
        card_layout.addWidget(self.cmb_default_template)
        
        card_layout.addSpacing(8)
        self.chk_enable_animations = QCheckBox(LanguageManager.tr("enable_animations"))
        self.chk_enable_animations.setToolTip(LanguageManager.tr("enable_animations_desc"))
        self.chk_enable_animations.setStyleSheet("""
            QCheckBox { font-size: 13px; font-weight: 500; }
        """)
        card_layout.addWidget(self.chk_enable_animations)

        layout.addWidget(card)

        # Fabrika Ayarlarına Sıfırlama Kartı
        card_reset = QFrame()
        card_reset.setProperty("class", "card")
        card_reset_layout = QVBoxLayout(card_reset)
        card_reset_layout.setSpacing(8)

        lbl_reset_title = QLabel(LanguageManager.tr("reset_all_section_title"))
        lbl_reset_title.setStyleSheet("font-size: 14px; font-weight: bold; ")
        card_reset_layout.addWidget(lbl_reset_title)

        lbl_reset_desc = QLabel(LanguageManager.tr("reset_all_section_desc"))
        lbl_reset_desc.setStyleSheet(" font-size: 12px;")
        lbl_reset_desc.setWordWrap(True)
        card_reset_layout.addWidget(lbl_reset_desc)

        btn_reset_card = QPushButton(LanguageManager.tr("btn_reset_all_settings"))
        btn_reset_card.setObjectName("DangerBtn")
        btn_reset_card.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_card.clicked.connect(self._confirm_and_reset_all_settings)
        card_reset_layout.addWidget(btn_reset_card, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(card_reset)
        layout.addStretch()

    def _confirm_and_reset_all_settings(self):
        """Kullanıcı onayından sonra tüm QSettings ayarlarını ve arayüzü fabrika varsayılanlarına döndürür."""
        msg = QMessageBox(self)
        msg.setWindowTitle(LanguageManager.tr("reset_all_confirm_title"))
        msg.setText(LanguageManager.tr("reset_all_confirm_text"))
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_yes = msg.addButton(LanguageManager.tr("btn_reset_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(LanguageManager.tr("btn_reset_no"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(btn_no)
        msg.exec()

        if msg.clickedButton() != btn_yes:
            return

        # 1. QSettings kayıtlarını temizle
        self.settings.clear()
        self.shortcut_settings.clear()

        # 2. Arayüz kontrollerini varsayılan değerlerine döndür
        if "gray" in self.theme_radios:
            self.theme_radios["gray"].setChecked(True)
        self.current_theme = "gray"
        self._apply_dialog_style()

        # Kısayollar
        self._reset_shortcuts_to_default()

        # Toolbar listesi
        self._populate_toolbar_list(list(DEFAULT_TOOLBAR_USER_ITEMS))

        # Zoom modu ve animasyonlar
        self._set_cmb_data(self.cmb_zoom_mode, "last")
        self._set_cmb_data(self.cmb_default_template, "blank")
        self.chk_enable_animations.setChecked(True)

        # Yazar bilgileri
        def_user, def_comp = get_default_author_info()
        self.txt_author_name.setText(def_user)
        self.txt_author_title.setText(def_comp)
        self.txt_author_email.setText("")
        self.chk_save_metadata.setChecked(True)
        self.chk_use_notes.setChecked(True)

        # Dil (Mevcut seçili dil)
        if hasattr(self, 'rb_lang_tr'):
            self.rb_lang_tr.setChecked(True)

        # İmleç ayarları
        self._reset_cursors_to_apple()

        # Güncelleme ayarları
        if hasattr(self, 'chk_auto_update'):
            self.chk_auto_update.setChecked(True)
        if hasattr(self, 'cmb_update_freq'):
            self._set_cmb_data(self.cmb_update_freq, "startup")
        if hasattr(self, 'txt_github_token'):
            self.txt_github_token.setText("")

        # 3. Kaydet & Ana Uygulamaya Uygula
        self.apply_settings()

        # 4. Bildirim
        QMessageBox.information(
            self,
            LanguageManager.tr("reset_all_success_title"),
            LanguageManager.tr("reset_all_success_text")
        )

    # ----------------------------------------------------
    # SEKME: GÖRÜNÜM & TEMA (7 KOYU TEMA)
    # ----------------------------------------------------
    def _build_theme_tab(self, parent_widget):
        layout_main = QVBoxLayout(parent_widget)
        layout_main.setContentsMargins(18, 18, 18, 18)
        layout_main.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentWidget")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl_title = QLabel(LanguageManager.tr("theme_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("theme_section_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        self.theme_group = QButtonGroup(self)

        themes_info = [
            ("dark", "theme_dark", "theme_dark_desc", 1),
            ("gray", "theme_gray", "theme_gray_desc", 2),

            ("emerald", "theme_emerald", "theme_emerald_desc", 4),
            ("purple", "theme_purple", "theme_purple_desc", 5),
            ("crimson", "theme_crimson", "theme_crimson_desc", 6),
            ("nord", "theme_nord", "theme_nord_desc", 7),
            ("vice_city", "theme_vice_city", "theme_vice_city_desc", 8),
        ]

        self.theme_radios = {}
        for code, title_key, desc_key, group_id in themes_info:
            rb = QRadioButton(LanguageManager.tr(title_key))
            lbl_desc_item = QLabel(f"    {LanguageManager.tr(desc_key)}")
            lbl_desc_item.setStyleSheet(" font-size: 11px;")
            self.theme_group.addButton(rb, group_id)
            self.theme_radios[code] = rb
            card_layout.addWidget(rb)
            card_layout.addWidget(lbl_desc_item)

        # Geriye dönük uyumluluk için referanslar
        self.rb_dark = self.theme_radios["dark"]
        self.rb_gray = self.theme_radios["gray"]

        self.rb_emerald = self.theme_radios["emerald"]
        self.rb_purple = self.theme_radios["purple"]
        self.rb_crimson = self.theme_radios["crimson"]
        self.rb_nord = self.theme_radios["nord"]
        self.rb_vice_city = self.theme_radios["vice_city"]

        layout.addWidget(card)
        layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout_main.addWidget(scroll)

    # ----------------------------------------------------
    # SEKME: KLAVYE KISAYOLLARI (YENİ)
    # ----------------------------------------------------
    def _build_shortcuts_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        lbl_title = QLabel(LanguageManager.tr("shortcuts_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("shortcuts_section_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        layout.addWidget(lbl_desc)

        lbl_hint = QLabel(LanguageManager.tr("shortcut_hint"))
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(
            " font-size: 11px; padding: 8px 12px; "
            "background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); "
            "border-radius: 6px; color: #cbd5e1;"
        )
        layout.addWidget(lbl_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        card = QFrame()
        card.setProperty("class", "card")
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setSpacing(10)

        self.shortcut_edits = {}
        shortcut_items = [
            ("pen", "shortcut_pen"),
            ("highlighter", "shortcut_highlighter"),
            ("eraser", "shortcut_eraser"),
            ("select", "shortcut_select"),
            ("selection_tool", "shortcut_selection_tool"),
            ("text", "shortcut_text"),
            ("pointer", "shortcut_pointer"),
            ("undo", "shortcut_undo"),
            ("redo", "shortcut_redo"),
            ("zoom_in", "shortcut_zoom_in"),
            ("zoom_out", "shortcut_zoom_out"),
            ("fit_width", "shortcut_fit_width"),
            ("fullscreen", "shortcut_fullscreen"),
        ]

        for row, (action_key, label_key) in enumerate(shortcut_items):
            lbl = QLabel(LanguageManager.tr(label_key))
            lbl.setStyleSheet("font-size: 13px; font-weight: 500;")
            
            edit = ModernShortcutEdit()
            self.shortcut_edits[action_key] = edit

            grid.addWidget(lbl, row, 0)
            grid.addWidget(edit, row, 1, Qt.AlignmentFlag.AlignRight)

        scroll.setWidget(card)
        layout.addWidget(scroll, 1)

        # Sıfırlama Butonu
        reset_bar = QHBoxLayout()
        self.btn_reset_shortcuts = QPushButton(LanguageManager.tr("btn_reset_shortcuts"))
        self.btn_reset_shortcuts.setObjectName("SecondaryBtn")
        self.btn_reset_shortcuts.clicked.connect(self._reset_shortcuts_to_default)
        reset_bar.addWidget(self.btn_reset_shortcuts)
        reset_bar.addStretch()
        layout.addLayout(reset_bar)

    def _reset_shortcuts_to_default(self):
        for action, default_seq in DEFAULT_SHORTCUTS.items():
            if action in self.shortcut_edits:
                self.shortcut_edits[action].setShortcutValue(default_seq)

    # ----------------------------------------------------
    # SEKME: PDF YAZAR PROFİLİ
    # ----------------------------------------------------
    def _build_author_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_title = QLabel(LanguageManager.tr("author_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("author_section_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        def_user, def_comp = get_default_author_info()

        card_layout.addWidget(QLabel(LanguageManager.tr("author_name_lbl")))
        self.txt_author_name = QLineEdit()
        self.txt_author_name.setPlaceholderText(def_user or LanguageManager.tr("author_name_placeholder"))
        card_layout.addWidget(self.txt_author_name)

        card_layout.addWidget(QLabel(LanguageManager.tr("author_title_lbl")))
        self.txt_author_title = QLineEdit()
        self.txt_author_title.setPlaceholderText(def_comp or LanguageManager.tr("author_title_placeholder"))
        card_layout.addWidget(self.txt_author_title)

        card_layout.addWidget(QLabel(LanguageManager.tr("author_email_lbl")))
        self.txt_author_email = QLineEdit()
        self.txt_author_email.setPlaceholderText(LanguageManager.tr("author_email_placeholder"))
        card_layout.addWidget(self.txt_author_email)

        self.chk_save_metadata = QCheckBox(LanguageManager.tr("author_save_metadata_chk"))
        card_layout.addWidget(self.chk_save_metadata)

        self.chk_use_notes = QCheckBox(LanguageManager.tr("author_use_notes_chk"))
        card_layout.addWidget(self.chk_use_notes)

        # Varsayılan Bilgisayar Bilgilerini Yükle Butonu
        reset_bar = QHBoxLayout()
        self.btn_reset_author = QPushButton(LanguageManager.tr("btn_reset_author_info"))
        self.btn_reset_author.setObjectName("SecondaryBtn")
        self.btn_reset_author.clicked.connect(self._reset_author_to_default)
        reset_bar.addWidget(self.btn_reset_author)
        reset_bar.addStretch()
        card_layout.addLayout(reset_bar)

        layout.addWidget(card)
        layout.addStretch()

    def _reset_author_to_default(self):
        def_user, def_comp = get_default_author_info()
        self.txt_author_name.setText(def_user)
        self.txt_author_title.setText(def_comp)
        self.txt_author_email.clear()

    # ----------------------------------------------------
    # SEKME: DİL & BÖLGE
    # ----------------------------------------------------
    def _build_lang_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_title = QLabel(LanguageManager.tr("lang_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("lang_section_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        self.lang_group = QButtonGroup(self)
        self.rb_lang_tr = QRadioButton("Türkçe (Turkish)")
        self.lang_group.addButton(self.rb_lang_tr, 1)
        card_layout.addWidget(self.rb_lang_tr)

        self.rb_lang_en = QRadioButton("English (İngilizce)")
        self.lang_group.addButton(self.rb_lang_en, 2)
        card_layout.addWidget(self.rb_lang_en)

        layout.addWidget(card)
        layout.addStretch()

    # ----------------------------------------------------
    # SEKME: ARAÇ ÇUBUĞU DÜZENİ (TOOLBAR LAYOUT)
    # ----------------------------------------------------
    def _build_toolbar_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_title = QLabel(LanguageManager.tr("toolbar_order_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("toolbar_order_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(14)

        self.list_toolbar = QListWidget()
        self.list_toolbar.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_toolbar.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_toolbar.setObjectName("ToolbarList")
        card_layout.addWidget(self.list_toolbar, stretch=1)

        v_btns = QVBoxLayout()
        v_btns.setSpacing(8)

        self.btn_tb_up = QPushButton(LanguageManager.tr("toolbar_move_up"))
        self.btn_tb_up.setObjectName("SecondaryBtn")
        self.btn_tb_up.clicked.connect(lambda: self._move_toolbar_item(-1))

        self.btn_tb_down = QPushButton(LanguageManager.tr("toolbar_move_down"))
        self.btn_tb_down.setObjectName("SecondaryBtn")
        self.btn_tb_down.clicked.connect(lambda: self._move_toolbar_item(1))

        self.btn_tb_reset = QPushButton(LanguageManager.tr("toolbar_reset_default"))
        self.btn_tb_reset.setObjectName("SecondaryBtn")
        self.btn_tb_reset.clicked.connect(self._reset_toolbar_items)

        v_btns.addWidget(self.btn_tb_up)
        v_btns.addWidget(self.btn_tb_down)
        v_btns.addSpacing(12)
        v_btns.addWidget(self.btn_tb_reset)
        v_btns.addStretch()

        card_layout.addLayout(v_btns)
        layout.addWidget(card, stretch=1)

    def _move_toolbar_item(self, delta: int):
        row = self.list_toolbar.currentRow()
        if row < 0:
            return
        new_row = row + delta
        if 0 <= new_row < self.list_toolbar.count():
            item = self.list_toolbar.takeItem(row)
            self.list_toolbar.insertItem(new_row, item)
            self.list_toolbar.setCurrentRow(new_row)

    def _populate_toolbar_list(self, order_list: list):
        self.list_toolbar.clear()
        for k in order_list:
            meta = TOOLBAR_ITEMS_META.get(k)
            if meta:
                trans_key, icon_func = meta
                title = LanguageManager.tr(trans_key)
                icon = icon_func() if icon_func else QIcon()
                item = QListWidgetItem(icon, title)
                item.setData(Qt.ItemDataRole.UserRole, k)
                self.list_toolbar.addItem(item)
        if self.list_toolbar.count() > 0:
            self.list_toolbar.setCurrentRow(0)

    def _reset_toolbar_items(self):
        self._populate_toolbar_list(DEFAULT_TOOLBAR_USER_ITEMS)

    # ----------------------------------------------------
    # BÖLÜM: İMLEÇLER (CURSORS SECTION IN THEME TAB)
    # ----------------------------------------------------
    def _build_cursor_tab(self, parent_widget):
        layout_main = QVBoxLayout(parent_widget)
        layout_main.setContentsMargins(18, 18, 18, 18)
        layout_main.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll_widget.setObjectName("TransparentWidget")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Başlık ve Açıklama
        lbl_title = QLabel(LanguageManager.tr("cursor_settings_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("cursor_settings_desc"))
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(" font-size: 12px; margin-bottom: 2px;")
        layout.addWidget(lbl_desc)

        # Kart 1: Hazır İmleç Stili (Presets)
        card_preset = QFrame()
        card_preset.setProperty("class", "card")
        p_layout = QHBoxLayout(card_preset)
        p_layout.setContentsMargins(12, 10, 12, 10)
        p_layout.setSpacing(12)

        p_lbl = QLabel(LanguageManager.tr("cursor_preset_lbl"))
        p_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        p_layout.addWidget(p_lbl)

        self.cmb_cursor_preset = QComboBox()
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_apple"), "apple")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_figma"), "figma")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_canva"), "canva")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_notion"), "notion")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_vscode"), "vscode")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_google_docs"), "google_docs")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_vice_city"), "vice_city")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_classic"), "classic")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_precision"), "precision")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_system"), "system")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_artist"), "artist")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_calligraphy"), "calligraphy")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_pixel_art"), "pixel_art")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_neon"), "neon")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_draftsman"), "draftsman")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_minimalist"), "minimalist")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_heavy_duty"), "heavy_duty")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_stealth"), "stealth")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_creative"), "creative")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_tactical"), "tactical")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_legacy"), "legacy")
        self.cmb_cursor_preset.addItem(LanguageManager.tr("cursor_preset_custom"), "custom")
        self.cmb_cursor_preset.currentIndexChanged.connect(self._on_cursor_preset_changed)
        p_layout.addWidget(self.cmb_cursor_preset, stretch=1)

        layout.addWidget(card_preset)

        # Kart 2: Araç Başına İmleç Seçimi
        card_tools = QFrame()
        card_tools.setProperty("class", "card")
        grid = QGridLayout(card_tools)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # 1. Kalem
        lbl_pen = QLabel(LanguageManager.tr("cursor_pen_lbl"))
        lbl_pen.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_pen, 0, 0)
        self.cmb_pen_cursor = QComboBox()
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_apple_pencil"), "apple_pencil")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_figma_pen"), "figma_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_canva_magic_pen"), "canva_magic_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_notion_pen"), "notion_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_vscode_pen"), "vscode_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_docs_pen"), "docs_pen")
        self.cmb_pen_cursor.addItem("Vice City Neon Kalem", "vice_city_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_classic_pen"), "classic_pen")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_crosshair"), "crosshair")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_dot"), "dot")
        self.cmb_pen_cursor.addItem(LanguageManager.tr("cursor_style_system_arrow"), "arrow")
        self.cmb_pen_cursor.addItem("Dolma Kalem (Fountain Pen)", "fountain_pen")
        self.cmb_pen_cursor.addItem("Fırça Kalem (Brush Pen)", "brush_pen")
        self.cmb_pen_cursor.addItem("Piksel Nokta (Pixel)", "pixel")
        self.cmb_pen_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("pen"))
        grid.addWidget(self.cmb_pen_cursor, 0, 1)

        # 2. Vurgulayıcı Kalem
        lbl_hl = QLabel(LanguageManager.tr("cursor_hl_lbl"))
        lbl_hl.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_hl, 1, 0)
        self.cmb_hl_cursor = QComboBox()
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_apple_chisel"), "apple_chisel")
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_figma_marker"), "figma_marker")
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_notion_marker"), "notion_marker")
        self.cmb_hl_cursor.addItem("Vice City Neon Fosforlu", "vice_city_marker")
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_classic_marker"), "classic_marker")
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_crosshair"), "crosshair")
        self.cmb_hl_cursor.addItem(LanguageManager.tr("cursor_style_system_arrow"), "arrow")
        self.cmb_hl_cursor.addItem("Kalın Keçeli (Thick Marker)", "thick_marker")
        self.cmb_hl_cursor.addItem("Düz Fırça (Flat Brush)", "flat_brush")
        self.cmb_hl_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("highlighter"))
        grid.addWidget(self.cmb_hl_cursor, 1, 1)

        # 3. Silgi
        lbl_eraser = QLabel(LanguageManager.tr("cursor_eraser_lbl"))
        lbl_eraser.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_eraser, 2, 0)
        self.cmb_eraser_cursor = QComboBox()
        self.cmb_eraser_cursor.addItem(LanguageManager.tr("cursor_style_apple_ring"), "apple_ring")
        self.cmb_eraser_cursor.addItem("Vice City Neon Küp", "vice_city_cube")
        self.cmb_eraser_cursor.addItem(LanguageManager.tr("cursor_style_cad_cross"), "cad_cross")
        self.cmb_eraser_cursor.addItem(LanguageManager.tr("cursor_style_square"), "square")
        self.cmb_eraser_cursor.addItem(LanguageManager.tr("cursor_style_dot"), "dot")
        self.cmb_eraser_cursor.addItem("Katı Blok (Solid Block)", "solid_block")
        self.cmb_eraser_cursor.addItem("Dairesel Sünger (Sponge)", "sponge")
        self.cmb_eraser_cursor.addItem("Temizlik Fırçası (Cleaning Brush)", "cleaning_brush")
        self.cmb_eraser_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("eraser"))
        grid.addWidget(self.cmb_eraser_cursor, 2, 1)

        # 4. Lazer İşaretçi
        lbl_pointer = QLabel(LanguageManager.tr("cursor_pointer_lbl"))
        lbl_pointer.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_pointer, 3, 0)
        self.cmb_pointer_cursor = QComboBox()
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_apple_laser"), "apple_laser")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_figma_pointer"), "figma_pointer")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_canva_sparkle"), "canva_sparkle")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_vscode_pointer"), "vscode_pointer")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_docs_pointer"), "docs_pointer")
        self.cmb_pointer_cursor.addItem("Vice City Neon Lazer", "vice_city_neon")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_apple_glow_ring"), "apple_glow_ring")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_neon_ring"), "neon_ring")
        self.cmb_pointer_cursor.addItem(LanguageManager.tr("cursor_style_dot"), "dot")
        self.cmb_pointer_cursor.addItem("Yıldız (Star)", "star")
        self.cmb_pointer_cursor.addItem("Hedef / Sniper (Target)", "target")
        self.cmb_pointer_cursor.addItem("Radar Dalgaları (Radar)", "radar")
        self.cmb_pointer_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("pointer"))
        grid.addWidget(self.cmb_pointer_cursor, 3, 1)

        # 5. Metin Kutusu
        lbl_text = QLabel(LanguageManager.tr("cursor_text_lbl"))
        lbl_text.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_text, 4, 0)
        self.cmb_text_cursor = QComboBox()
        self.cmb_text_cursor.addItem(LanguageManager.tr("cursor_style_macos_ibeam"), "macos_ibeam")
        self.cmb_text_cursor.addItem(LanguageManager.tr("cursor_style_vscode_ibeam"), "vscode_ibeam")
        self.cmb_text_cursor.addItem("Vice City Neon Yazı", "vice_city_ibeam")
        self.cmb_text_cursor.addItem(LanguageManager.tr("cursor_style_classic_ibeam"), "classic_ibeam")
        self.cmb_text_cursor.addItem(LanguageManager.tr("cursor_style_badge_ibeam"), "badge_ibeam")
        self.cmb_text_cursor.addItem("Tüy Kalem (Feather)", "feather")
        self.cmb_text_cursor.addItem("Kalın Daktilo (Typewriter)", "typewriter")
        self.cmb_text_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("text"))
        grid.addWidget(self.cmb_text_cursor, 4, 1)

        # 6. Seçim Aracı
        lbl_sel = QLabel(LanguageManager.tr("cursor_selection_lbl"))
        lbl_sel.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_sel, 5, 0)
        self.cmb_sel_cursor = QComboBox()
        self.cmb_sel_cursor.addItem(LanguageManager.tr("cursor_style_macos_reticle"), "macos_reticle")
        self.cmb_sel_cursor.addItem("Vice City Neon Nişangah", "vice_city_reticle")
        self.cmb_sel_cursor.addItem(LanguageManager.tr("cursor_style_fine_cross"), "fine_cross")
        self.cmb_sel_cursor.addItem(LanguageManager.tr("cursor_style_standard_cross"), "standard_cross")
        self.cmb_sel_cursor.addItem("Kement (Lasso)", "lasso")
        self.cmb_sel_cursor.addItem("Kesik Çizgili Kutu (Marquee)", "marquee")
        self.cmb_sel_cursor.addItem("İşaret Parmağı (Hand Pointer)", "hand")
        self.cmb_sel_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("selection"))
        grid.addWidget(self.cmb_sel_cursor, 5, 1)

        # 7. Cetvel
        lbl_ruler = QLabel("Cetvel İmleci")
        lbl_ruler.setStyleSheet("font-weight: 500;")
        grid.addWidget(lbl_ruler, 6, 0)
        self.cmb_ruler_cursor = QComboBox()
        self.cmb_ruler_cursor.addItem("Çapraz Hizalama (Crosshair)", "ruler_crosshair")
        self.cmb_ruler_cursor.addItem("Klasik Cetvel (Classic Ruler)", "classic_ruler")
        self.cmb_ruler_cursor.addItem("Gönye (Draft Triangle)", "draft_triangle")
        self.cmb_ruler_cursor.addItem("İletki (Protractor)", "protractor")
        self.cmb_ruler_cursor.currentIndexChanged.connect(lambda: self._on_tool_cursor_changed("ruler"))
        grid.addWidget(self.cmb_ruler_cursor, 6, 1)

        layout.addWidget(card_tools)

        # Kart 3: Canlı İnteraktif Önizleme
        card_preview = QFrame()
        card_preview.setProperty("class", "card")
        cp_layout = QVBoxLayout(card_preview)
        cp_layout.setContentsMargins(12, 10, 12, 10)
        cp_layout.setSpacing(8)

        cp_top = QHBoxLayout()
        cp_title = QLabel(LanguageManager.tr("cursor_preview_title"))
        cp_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        cp_top.addWidget(cp_title)
        cp_top.addStretch()

        self.preview_selected_tool = "pen"
        self.preview_tool_btns = {}
        tool_icons = [
            ("pen", "Kalem"),
            ("highlighter", "Fosforlu"),
            ("eraser", "Silgi"),
            ("pointer", "Lazer"),
            ("text", "Metin"),
            ("selection", "Seçim"),
            ("ruler", "Cetvel")
        ]
        for t_key, t_label in tool_icons:
            btn = QPushButton(t_label)
            btn.setCheckable(True)
            btn.setChecked(t_key == "pen")
            btn.setStyleSheet("""
                QPushButton { background: rgba(255, 255, 255, 0.06); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; padding: 4px 8px; font-size: 11px; }
                QPushButton:hover { background: rgba(255, 255, 255, 0.12); color: #ffffff; border-color: rgba(255, 255, 255, 0.25); }
                QPushButton:checked { background: rgba(56, 189, 248, 0.22); color: #38bdf8; border: 1px solid #38bdf8; font-weight: bold; }
            """)
            btn.clicked.connect(lambda checked, tk=t_key: self._set_preview_tool(tk))
            cp_top.addWidget(btn)
            self.preview_tool_btns[t_key] = btn

        cp_layout.addLayout(cp_top)

        hint = QLabel(LanguageManager.tr("cursor_preview_hint"))
        hint.setStyleSheet(" font-size: 11px;")
        cp_layout.addWidget(hint)

        self.preview_box = CursorPreviewBox(card_preview)
        cp_layout.addWidget(self.preview_box)

        layout.addWidget(card_preview)

        # Kart 4: Seçenekler & Sıfırla
        card_opts = QFrame()
        card_opts.setProperty("class", "card")
        co_layout = QVBoxLayout(card_opts)
        co_layout.setContentsMargins(12, 8, 12, 8)
        co_layout.setSpacing(12)

        self.chk_cursor_color = QCheckBox(LanguageManager.tr("cursor_opt_show_color"))
        self.chk_cursor_color.setChecked(True)
        self.chk_cursor_color.toggled.connect(self._update_cursor_preview)
        co_layout.addWidget(self.chk_cursor_color)

        self.chk_cursor_contrast = QCheckBox(LanguageManager.tr("cursor_opt_contrast_shadow"))
        self.chk_cursor_contrast.setChecked(True)
        self.chk_cursor_contrast.toggled.connect(self._update_cursor_preview)
        co_layout.addWidget(self.chk_cursor_contrast)

        self.chk_auto_cursor_theme = QCheckBox(LanguageManager.tr("cursor_opt_auto_theme"))
        self.chk_auto_cursor_theme.setChecked(True)
        co_layout.addWidget(self.chk_auto_cursor_theme)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_reset_cur = QPushButton(LanguageManager.tr("cursor_btn_reset"))
        btn_reset_cur.setObjectName("SecondaryBtn")
        btn_reset_cur.clicked.connect(self._reset_cursors_to_apple)
        btn_row.addWidget(btn_reset_cur)
        
        co_layout.addLayout(btn_row)

        layout.addWidget(card_opts)
        layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout_main.addWidget(scroll)

    # ----------------------------------------------------
    # SEKME: YAZILIM GÜNCELLEMELERİ (UPDATES)
    # ----------------------------------------------------
    def _build_updates_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        lbl_title = QLabel(LanguageManager.tr("updates_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # Kart 1: Sürüm Bilgisi ve Manuel Denetim
        card_status = QFrame()
        card_status.setProperty("class", "card")
        card_status_layout = QVBoxLayout(card_status)
        card_status_layout.setSpacing(12)

        from src.core.updater import CURRENT_VERSION, UpdateChecker
        self.lbl_update_ver = QLabel(LanguageManager.tr("updates_current_version", version=CURRENT_VERSION))
        self.lbl_update_ver.setStyleSheet("font-size: 14px; font-weight: 600; color: #38bdf8;")
        card_status_layout.addWidget(self.lbl_update_ver)

        last_time = self.settings.value("last_update_check_time", "")
        last_str = LanguageManager.tr("updates_last_checked", time=last_time) if last_time else LanguageManager.tr("updates_never_checked")
        self.lbl_update_last = QLabel(last_str)
        self.lbl_update_last.setStyleSheet("font-size: 12px; color: #94a3b8;")
        card_status_layout.addWidget(self.lbl_update_last)

        h_btn_box = QHBoxLayout()
        self.btn_check_updates = QPushButton(LanguageManager.tr("updates_btn_check"))
        self.btn_check_updates.setIcon(ModernIconFactory.icon_update())
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_updates.setObjectName("PrimaryBtn")
        self.btn_check_updates.clicked.connect(self._on_manual_check_updates)
        h_btn_box.addWidget(self.btn_check_updates)
        h_btn_box.addStretch()
        card_status_layout.addLayout(h_btn_box)

        layout.addWidget(card_status)

        # Kart 2: Otomatik Güncelleme Seçenekleri
        card_opts = QFrame()
        card_opts.setProperty("class", "card")
        card_opts_layout = QVBoxLayout(card_opts)
        card_opts_layout.setSpacing(10)

        self.chk_auto_update = QCheckBox(LanguageManager.tr("updates_auto_check"))
        self.chk_auto_update.setChecked(True)
        card_opts_layout.addWidget(self.chk_auto_update)

        h_freq = QHBoxLayout()
        h_freq.addWidget(QLabel(LanguageManager.tr("updates_frequency_label")))
        self.cmb_update_freq = QComboBox()
        self.cmb_update_freq.addItem(LanguageManager.tr("updates_freq_startup"), "startup")
        self.cmb_update_freq.addItem(LanguageManager.tr("updates_freq_daily"), "daily")
        self.cmb_update_freq.addItem(LanguageManager.tr("updates_freq_weekly"), "weekly")
        h_freq.addWidget(self.cmb_update_freq)
        h_freq.addStretch()
        card_opts_layout.addLayout(h_freq)

        card_opts_layout.addSpacing(8)
        lbl_token = QLabel(LanguageManager.tr("updates_token_label"))
        lbl_token.setStyleSheet("font-size: 12px; font-weight: 500;")
        card_opts_layout.addWidget(lbl_token)

        self.txt_github_token = QLineEdit()
        self.txt_github_token.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.txt_github_token.setPlaceholderText("ghp_... (Opsiyonel)")
        card_opts_layout.addWidget(self.txt_github_token)

        lbl_token_desc = QLabel(LanguageManager.tr("updates_token_tip"))
        lbl_token_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        card_opts_layout.addWidget(lbl_token_desc)

        layout.addWidget(card_opts)
        layout.addStretch()

    def _on_manual_check_updates(self):
        self.btn_check_updates.setEnabled(False)
        self.btn_check_updates.setText(LanguageManager.tr("updates_checking"))
        token = self.txt_github_token.text().strip()
        from src.core.updater import UpdateChecker
        self._manual_checker = UpdateChecker(custom_token=token, parent=self)
        self._manual_checker.check_finished.connect(self._on_check_finished)
        self._manual_checker.check_failed.connect(self._on_check_failed)
        self._manual_checker.start()

    def _on_check_finished(self, update_info):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText(LanguageManager.tr("updates_btn_check"))
        last_time = self.settings.value("last_update_check_time", "")
        if last_time and hasattr(self, 'lbl_update_last'):
            self.lbl_update_last.setText(LanguageManager.tr("updates_last_checked", time=last_time))
        from src.ui.dialogs.update_dialog import UpdateDialog
        dlg = UpdateDialog(update_info, parent=self)
        dlg.exec()

    def _on_check_failed(self, err_msg):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText(LanguageManager.tr("updates_btn_check"))
        QMessageBox.warning(self, LanguageManager.tr("updates_error_title"), err_msg)

    def _set_cmb_data(self, cmb: QComboBox, data_val):
        idx = cmb.findData(data_val)
        if idx >= 0:
            cmb.setCurrentIndex(idx)

    def _on_cursor_preset_changed(self, idx):
        preset_key = self.cmb_cursor_preset.currentData()
        if preset_key in CURSOR_PRESETS:
            cfg = CURSOR_PRESETS[preset_key]
            self.cmb_pen_cursor.blockSignals(True)
            self.cmb_hl_cursor.blockSignals(True)
            self.cmb_eraser_cursor.blockSignals(True)
            self.cmb_pointer_cursor.blockSignals(True)
            self.cmb_text_cursor.blockSignals(True)
            self.cmb_sel_cursor.blockSignals(True)
            self.cmb_ruler_cursor.blockSignals(True)

            self._set_cmb_data(self.cmb_pen_cursor, cfg["pen"])
            self._set_cmb_data(self.cmb_hl_cursor, cfg["hl"])
            self._set_cmb_data(self.cmb_eraser_cursor, cfg["eraser"])
            self._set_cmb_data(self.cmb_pointer_cursor, cfg["pointer"])
            self._set_cmb_data(self.cmb_text_cursor, cfg["text"])
            self._set_cmb_data(self.cmb_sel_cursor, cfg["selection"])
            self._set_cmb_data(self.cmb_ruler_cursor, cfg.get("ruler", "ruler_crosshair"))

            self.cmb_pen_cursor.blockSignals(False)
            self.cmb_hl_cursor.blockSignals(False)
            self.cmb_eraser_cursor.blockSignals(False)
            self.cmb_pointer_cursor.blockSignals(False)
            self.cmb_text_cursor.blockSignals(False)
            self.cmb_sel_cursor.blockSignals(False)
            self.cmb_ruler_cursor.blockSignals(False)

            self._update_cursor_preview()

    def _on_tool_cursor_changed(self, tool):
        self.cmb_cursor_preset.blockSignals(True)
        self._set_cmb_data(self.cmb_cursor_preset, "custom")
        self.cmb_cursor_preset.blockSignals(False)
        self._update_cursor_preview()

    def _set_preview_tool(self, tool_key):
        self.preview_selected_tool = tool_key
        for k, btn in getattr(self, 'preview_tool_btns', {}).items():
            btn.setChecked(k == tool_key)
        self._update_cursor_preview()

    def _update_cursor_preview(self):
        if not hasattr(self, 'preview_box'):
            return
        t = getattr(self, 'preview_selected_tool', 'pen')
        color = "#0071E3" if t == "pen" else ("#FFD60A" if t == "highlighter" else "#FF2D55")
        
        style = None
        if t == "pen":
            style = self.cmb_pen_cursor.currentData()
        elif t == "highlighter":
            style = self.cmb_hl_cursor.currentData()
        elif t == "eraser":
            style = self.cmb_eraser_cursor.currentData()
        elif t == "pointer":
            style = self.cmb_pointer_cursor.currentData()
        elif t == "text":
            style = self.cmb_text_cursor.currentData()
        elif t == "selection":
            style = self.cmb_sel_cursor.currentData()

        cur = CursorFactory.get_cursor_for_tool(t, color=color, size=24, style=style)
        self.preview_box.set_preview_cursor(cur)

    def _reset_cursors_to_apple(self):
        self._set_cmb_data(self.cmb_cursor_preset, "apple")
        self._on_cursor_preset_changed(0)

    # ----------------------------------------------------
    # DEĞERLERİ YÜKLEME VE KAYDETME
    # ----------------------------------------------------
    def _load_saved_values(self):
        # 1. Tema
        saved_theme = self.settings.value("app_theme", "gray")
        if saved_theme in self.theme_radios:
            self.theme_radios[saved_theme].setChecked(True)
        else:
            self.rb_dark.setChecked(True)

        # 2. Klavye & Fare Kısayolları
        for action, default_seq in DEFAULT_SHORTCUTS.items():
            user_seq = self.shortcut_settings.value(f"key_{action}", default_seq)
            if action in self.shortcut_edits:
                self.shortcut_edits[action].setShortcutValue(user_seq)

        # 3. Yazar Bilgileri (Kullanıcı talebi: Default olarak bilgisayar kullanıcı adı ve bilgisayar adı gelsin)
        def_user, def_comp = get_default_author_info()
        saved_name = self.settings.value("author_name", None)
        saved_title = self.settings.value("author_title", None)
        saved_email = self.settings.value("author_email", "")

        # Eğer kayıtlı değer boşsa veya eski test verisiyse sistem varsayılanını yükle
        if saved_name is None or str(saved_name).strip() in ("", "Test Author"):
            author_name = def_user
        else:
            author_name = str(saved_name).strip()

        if saved_title is None or str(saved_title).strip() in ("", "Lead Architect"):
            author_title = def_comp
        else:
            author_title = str(saved_title).strip()

        if str(saved_email).strip() == "architect@example.com":
            saved_email = ""

        self.txt_author_name.setText(author_name)
        self.txt_author_title.setText(author_title)
        self.txt_author_email.setText(str(saved_email).strip())
        self.chk_save_metadata.setChecked(self.settings.value("save_author_to_pdf", True, type=bool))
        self.chk_use_notes.setChecked(self.settings.value("use_author_in_notes", True, type=bool))

        # 4. Dil
        current_lang = LanguageManager.current_lang
        if current_lang == "en":
            self.rb_lang_en.setChecked(True)
        else:
            self.rb_lang_tr.setChecked(True)

        # 5. Zoom Modu
        saved_zoom_mode = self.settings.value("default_zoom_mode", "last")
        self._set_cmb_data(self.cmb_zoom_mode, saved_zoom_mode)

        # Default Template
        saved_tpl = self.settings.value("default_page_template", "blank")
        self._set_cmb_data(self.cmb_default_template, saved_tpl)

        # Animations
        self.chk_enable_animations.setChecked(self.settings.value("enable_animations", True, type=bool))

        # 6. Toolbar Sıralaması
        raw_tb = self.settings.value("toolbar_order", None)
        saved_tb = None
        if raw_tb:
            try:
                if isinstance(raw_tb, str):
                    saved_tb = json.loads(raw_tb)
                elif isinstance(raw_tb, list):
                    saved_tb = list(raw_tb)
            except Exception:
                saved_tb = None

        if not saved_tb:
            saved_tb = list(DEFAULT_TOOLBAR_USER_ITEMS)

        # Deduplicate saved_tb while preserving order and filtering by valid meta items
        deduped = []
        for x in saved_tb:
            if x in TOOLBAR_ITEMS_META and x not in deduped:
                deduped.append(x)
        current_tb_order = deduped
        for k in DEFAULT_TOOLBAR_USER_ITEMS:
            if k not in current_tb_order:
                current_tb_order.append(k)

        self._populate_toolbar_list(current_tb_order)

        # 7. İmleç Ayarlarını Yükle
        saved_preset = self.settings.value("cursor_preset", "apple")
        idx_p = self.cmb_cursor_preset.findData(saved_preset)
        if idx_p >= 0:
            self.cmb_cursor_preset.setCurrentIndex(idx_p)

        self._set_cmb_data(self.cmb_pen_cursor, self.settings.value("cursor_pen", "apple_pencil"))
        self._set_cmb_data(self.cmb_hl_cursor, self.settings.value("cursor_hl", "apple_chisel"))
        self._set_cmb_data(self.cmb_eraser_cursor, self.settings.value("cursor_eraser", "apple_ring"))
        self._set_cmb_data(self.cmb_pointer_cursor, self.settings.value("cursor_pointer", "apple_laser"))
        self._set_cmb_data(self.cmb_text_cursor, self.settings.value("cursor_text", "macos_ibeam"))
        self._set_cmb_data(self.cmb_sel_cursor, self.settings.value("cursor_selection", "macos_reticle"))
        self.chk_cursor_color.setChecked(self.settings.value("cursor_show_active_color", True, type=bool))
        self.chk_cursor_contrast.setChecked(self.settings.value("cursor_high_contrast", True, type=bool))
        self.chk_auto_cursor_theme.setChecked(self.settings.value("auto_match_theme_cursor", True, type=bool))
        self._update_cursor_preview()

        # 8. Güncelleme Ayarlarını Yükle
        if hasattr(self, 'chk_auto_update'):
            self.chk_auto_update.setChecked(self.settings.value("auto_check_updates", True, type=bool))
        if hasattr(self, 'cmb_update_freq'):
            saved_freq = self.settings.value("update_frequency", "startup")
            self._set_cmb_data(self.cmb_update_freq, saved_freq)
        if hasattr(self, 'txt_github_token'):
            self.txt_github_token.setText(self.settings.value("github_token", ""))

    def apply_settings(self):
        # 1. Tema Kaydet & Uygula
        selected_theme = "gray"
        for code, rb in self.theme_radios.items():
            if rb.isChecked():
                selected_theme = code
                break
        
        self.settings.setValue("app_theme", selected_theme)
        if hasattr(self.main_window, 'apply_theme'):
            self.main_window.apply_theme(selected_theme)
            
        self.current_theme = selected_theme
        self._apply_dialog_style()

        # 2. Kısayolları Kaydet & Uygula
        for action, edit in self.shortcut_edits.items():
            seq_str = edit.shortcutValue() if hasattr(edit, 'shortcutValue') else edit.keySequence().toString()
            self.shortcut_settings.setValue(f"key_{action}", seq_str)
        
        if hasattr(self.main_window, 'reload_shortcuts'):
            self.main_window.reload_shortcuts()

        # 3. Yazar Bilgilerini Kaydet
        self.settings.setValue("author_name", self.txt_author_name.text().strip())
        self.settings.setValue("author_title", self.txt_author_title.text().strip())
        self.settings.setValue("author_email", self.txt_author_email.text().strip())
        self.settings.setValue("save_author_to_pdf", self.chk_save_metadata.isChecked())
        self.settings.setValue("use_author_in_notes", self.chk_use_notes.isChecked())

        # 4. Dil Kaydet & Uygula
        selected_lang = "en" if self.rb_lang_en.isChecked() else "tr"
        if selected_lang != LanguageManager.current_lang:
            if hasattr(self.main_window, 'change_language'):
                self.main_window.change_language(selected_lang)

        # 5. Zoom Modu
        zoom_mode = self.cmb_zoom_mode.currentData()
        self.settings.setValue("default_zoom_mode", zoom_mode)

        # Default Template
        tpl_mode = self.cmb_default_template.currentData()
        self.settings.setValue("default_page_template", tpl_mode)

        # Animations
        self.settings.setValue("enable_animations", self.chk_enable_animations.isChecked())

        # 6. Toolbar Düzenini Kaydet & Uygula
        reordered_items = []
        for i in range(self.list_toolbar.count()):
            it = self.list_toolbar.item(i)
            item_id = it.data(Qt.ItemDataRole.UserRole)
            if item_id and item_id not in reordered_items:
                reordered_items.append(item_id)
        if reordered_items:
            if reordered_items == DEFAULT_TOOLBAR_USER_ITEMS:
                self.settings.remove("toolbar_order")
            else:
                self.settings.setValue("toolbar_order", json.dumps(reordered_items))
            if hasattr(self.main_window, 'restore_toolbar_order'):
                self.main_window.restore_toolbar_order()

        # 7. İmleç Ayarlarını Kaydet & Uygula
        self.settings.setValue("cursor_preset", self.cmb_cursor_preset.currentData())
        self.settings.setValue("cursor_pen", self.cmb_pen_cursor.currentData())
        self.settings.setValue("cursor_hl", self.cmb_hl_cursor.currentData())
        self.settings.setValue("cursor_eraser", self.cmb_eraser_cursor.currentData())
        self.settings.setValue("cursor_pointer", self.cmb_pointer_cursor.currentData())
        self.settings.setValue("cursor_text", self.cmb_text_cursor.currentData())
        self.settings.setValue("cursor_selection", self.cmb_sel_cursor.currentData())
        self.settings.setValue("cursor_show_active_color", self.chk_cursor_color.isChecked())
        self.settings.setValue("cursor_high_contrast", self.chk_cursor_contrast.isChecked())
        self.settings.setValue("auto_match_theme_cursor", self.chk_auto_cursor_theme.isChecked())

        if hasattr(self.main_window, 'update_viewport_cursor'):
            self.main_window.update_viewport_cursor()

        # 8. Güncelleme Ayarlarını Kaydet
        if hasattr(self, 'chk_auto_update'):
            self.settings.setValue("auto_check_updates", self.chk_auto_update.isChecked())
        if hasattr(self, 'cmb_update_freq'):
            self.settings.setValue("update_frequency", self.cmb_update_freq.currentData())
        if hasattr(self, 'txt_github_token'):
            self.settings.setValue("github_token", self.txt_github_token.text().strip())

        # Görsel geribildirim
        if hasattr(self, 'btn_apply'):
            orig_txt = LanguageManager.tr("btn_apply_settings")
            self.btn_apply.setText(LanguageManager.tr("settings_applied_feedback"))
            QTimer.singleShot(1400, lambda: self.btn_apply.setText(orig_txt))

    def save_settings(self):
        self.apply_settings()
        self.accept()


# Geriye dönük uyumluluk takma adları (Backward compatibility aliases)
ModernSettingsDialog = AuraSettingsDialog
SettingsDialog = AuraSettingsDialog
AuraShortcutButton = ModernShortcutButton
AuraShortcutEdit = ModernShortcutEdit
