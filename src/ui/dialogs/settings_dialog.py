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
from PyQt6.QtCore import Qt, QSettings, QRectF, QPointF, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QColor, QKeySequence, QPainter, QPen, QBrush
from PyQt6.QtCore import QSize

from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet, apply_dialog_theme, ModernInfoCard
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

FLOATING_TOOLBAR_ITEMS_META = {
    "select": ("tb_item_cursor", ModernIconFactory.icon_cursor),
    "selection": ("tb_item_selection", lambda: ModernIconFactory.icon_select_rect("#38bdf8")),
    "pointer": ("tb_item_pointer", lambda: ModernIconFactory.icon_pointer("#ef4444")),
    "highlighter": ("tb_item_hl", lambda: ModernIconFactory.icon_highlighter("#eab308")),
    "comment": ("quick_tool_comment", lambda: ModernIconFactory.icon_comments("#f97316")),
    "text": ("tb_item_text", lambda: ModernIconFactory.icon_text_tool("#ec4899")),
    "insert": ("tb_item_insert", lambda: ModernIconFactory.icon_insert("#10b981")),
    "pen": ("tb_item_pen", lambda: ModernIconFactory.icon_pen("#0284c7")),
    "eraser": ("tb_item_eraser", lambda: ModernIconFactory.icon_eraser("#ef4444")),
}

DEFAULT_FLOATING_TOOLBAR_ORDER = [
    "select", "selection", "pen", "highlighter", "eraser", "text", "insert", "comment", "pointer"
]

OLD_TO_FLOATING_KEY_MAP = {
    "btn_cursor": "select",
    "btn_selection": "selection",
    "btn_pointer": "pointer",
    "btn_hl": "highlighter",
    "btn_pen": "pen",
    "btn_eraser": "eraser",
    "btn_text": "text",
    "btn_insert": "insert",
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


def get_effective_author_name() -> str:
    """Kullanıcının belirlediği yazar adını, yoksa işletim sistemi oturum kullanıcı adını döner."""
    settings = QSettings("AuraPDF", "PDFViewer")
    author = str(settings.value("author_name", "") or "").strip()
    if not author or author.lower() in ("kullanıcı", "kullanici", "user", "test author", "admin"):
        username, _ = get_default_author_info()
        if username and username.strip():
            author = username.strip()
    return author or "AuraPDF User"


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
        self.btn_clear.setIcon(ModernIconFactory.icon_close("#ef4444"))
        self.btn_clear.setIconSize(QSize(12, 12))
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


class ThemeOptionCard(QFrame):
    """
    Modern temayı, başlığını, açıklamasını ve renk paleti önizleme haplarını
    içeren interaktif, tıklanabilir ve odaklanılabilir şık kart bileşeni.
    """
    def __init__(self, theme_code, title, desc, palette_colors, radio_btn, parent=None):
        super().__init__(parent)
        self.theme_code = theme_code
        self.radio_btn = radio_btn
        self.palette_colors = palette_colors
        self.setObjectName("ThemeOptionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(14)

        # Radyo butonu (Metin kart etiketinde gösterilecektir)
        self.radio_btn.setText("")
        h_layout.addWidget(self.radio_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Başlık ve açıklama
        v_info = QVBoxLayout()
        v_info.setSpacing(3)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.lbl_desc.setWordWrap(True)
        v_info.addWidget(self.lbl_title)
        v_info.addWidget(self.lbl_desc)
        h_layout.addLayout(v_info, 1)

        # Renk paleti önizleme hapları
        self.pills_layout = QHBoxLayout()
        self.pills_layout.setSpacing(5)
        self._pills = []
        for col in palette_colors:
            pill = QFrame()
            pill.setFixedSize(16, 16)
            pill.setStyleSheet(
                f"background-color: {col}; border-radius: 8px; border: 1.5px solid rgba(255, 255, 255, 0.25);"
            )
            self._pills.append(pill)
            self.pills_layout.addWidget(pill)
        h_layout.addLayout(self.pills_layout, 0)

        self.radio_btn.toggled.connect(self.update_card_style)
        self.update_card_style()

    def update_palette_pills(self, colors: list):
        self.palette_colors = list(colors)
        for pill, col in zip(self._pills, colors):
            pill.setStyleSheet(
                f"background-color: {col}; border-radius: 8px; border: 1.5px solid rgba(255, 255, 255, 0.25);"
            )
        self.update_card_style()

    def update_card_style(self):
        is_checked = self.radio_btn.isChecked()
        accent_color = self.palette_colors[-1] if self.palette_colors else "#38bdf8"
        if is_checked:
            self.setStyleSheet(f"""
                QFrame#ThemeOptionCard {{
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1.5px solid {accent_color};
                    border-radius: 9px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame#ThemeOptionCard {{
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 9px;
                }}
                QFrame#ThemeOptionCard:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.22);
                }}
            """)

    def mousePressEvent(self, event):
        self.radio_btn.setChecked(True)
        super().mousePressEvent(event)


class ThemeMiniPreviewCard(QFrame):
    """
    Kullanıcının seçtiği renk paletini gerçek bir AuraPDF penceresi şeklinde
    canlı olarak simüle eden ultra-modern minyatür önizleme bileşeni.
    """
    def __init__(self, colors: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeMiniPreviewCard")
        self.setFixedHeight(105)
        self._colors = dict(colors)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build_ui()

    def update_preview(self, colors: dict):
        self._colors = dict(colors)
        self._apply_mockup_styles()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)

        # 1. Mini Başlık Çubuğu
        self.mini_titlebar = QFrame()
        self.mini_titlebar.setFixedHeight(26)
        h_tb = QHBoxLayout(self.mini_titlebar)
        h_tb.setContentsMargins(8, 0, 8, 0)
        h_tb.setSpacing(6)

        # 3 Pencere Noktası
        h_dots = QHBoxLayout()
        h_dots.setSpacing(3)
        for dcol in ("#ef4444", "#f59e0b", "#10b981"):
            dot = QFrame()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background-color: {dcol}; border-radius: 3px;")
            h_dots.addWidget(dot)
        h_tb.addLayout(h_dots)

        # Mini Sekme
        self.mini_active_tab = QFrame()
        self.mini_active_tab.setFixedHeight(18)
        h_mtab = QHBoxLayout(self.mini_active_tab)
        h_mtab.setContentsMargins(8, 0, 8, 0)
        h_mtab.setSpacing(4)
        self.lbl_mtab = QLabel("AuraPDF Belgesi.pdf")
        self.lbl_mtab.setStyleSheet("font-size: 9.5px; font-weight: 600;")
        h_mtab.addWidget(self.lbl_mtab)
        h_tb.addWidget(self.mini_active_tab)

        h_tb.addStretch(1)

        # Canlı Önizleme Rozeti
        badge_live = QFrame()
        h_bl = QHBoxLayout(badge_live)
        h_bl.setContentsMargins(5, 2, 5, 2)
        h_bl.setSpacing(4)
        dot_live = QLabel("●")
        dot_live.setStyleSheet("color: #10b981; font-size: 8px;")
        h_bl.addWidget(dot_live)
        lbl_bl = QLabel(LanguageManager.tr("theme_preview_badge"))
        lbl_bl.setStyleSheet("font-size: 9px; font-weight: 700; color: #94a3b8;")
        h_bl.addWidget(lbl_bl)
        h_tb.addWidget(badge_live)

        v.addWidget(self.mini_titlebar)

        # 2. Gövde: Sol Mini Çekmece + Tuval
        self.mini_body = QFrame()
        h_body = QHBoxLayout(self.mini_body)
        h_body.setContentsMargins(0, 0, 0, 0)
        h_body.setSpacing(0)

        # Sol Mini Araç Çubuğu
        self.mini_sidebar = QFrame()
        self.mini_sidebar.setFixedWidth(30)
        v_sb = QVBoxLayout(self.mini_sidebar)
        v_sb.setContentsMargins(4, 6, 4, 6)
        v_sb.setSpacing(4)

        self.mini_tool_active = QFrame()
        self.mini_tool_active.setFixedSize(22, 16)
        v_sb.addWidget(self.mini_tool_active)

        self.mini_tool_idle = QFrame()
        self.mini_tool_idle.setFixedSize(22, 14)
        v_sb.addWidget(self.mini_tool_idle)
        v_sb.addStretch(1)
        h_body.addWidget(self.mini_sidebar)

        # Mini Tuval & Belge Alanı
        self.mini_canvas = QFrame()
        v_can = QVBoxLayout(self.mini_canvas)
        v_can.setContentsMargins(12, 8, 12, 8)
        v_can.setSpacing(5)

        # Mini Belge Kartı
        self.mini_doc_card = QFrame()
        v_doc = QVBoxLayout(self.mini_doc_card)
        v_doc.setContentsMargins(8, 6, 8, 6)
        v_doc.setSpacing(4)

        self.lbl_doc_title = QLabel("AuraPDF Modern Arayüz")
        self.lbl_doc_title.setStyleSheet("font-size: 10px; font-weight: 700;")
        v_doc.addWidget(self.lbl_doc_title)

        # Vurgulu Çizgi
        self.mini_doc_line = QFrame()
        self.mini_doc_line.setFixedHeight(2)
        v_doc.addWidget(self.mini_doc_line)

        # Eylem Düğmesi
        h_btn = QHBoxLayout()
        h_btn.setContentsMargins(0, 0, 0, 0)
        self.mini_btn = QLabel("  Belgeyi Aç  ")
        self.mini_btn.setFixedHeight(16)
        self.mini_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mini_btn.setStyleSheet("font-size: 9px; font-weight: 700; border-radius: 4px;")
        h_btn.addWidget(self.mini_btn)
        h_btn.addStretch(1)
        v_doc.addLayout(h_btn)

        v_can.addWidget(self.mini_doc_card)
        h_body.addWidget(self.mini_canvas, 1)

        v.addWidget(self.mini_body, 1)
        self._apply_mockup_styles()

    def _apply_mockup_styles(self):
        c_acc = self._colors.get("accent", "#38bdf8")
        c_bg = self._colors.get("bg", "#14171d")
        c_surf = self._colors.get("surface", "#1e222b")
        c_text = self._colors.get("text", "#f1f5f9")
        c_border = self._colors.get("border", "#2e3442")

        self.setStyleSheet(f"""
            QFrame#ThemeMiniPreviewCard {{
                background-color: {c_bg};
                border: 1.5px solid {c_border};
                border-radius: 10px;
            }}
        """)
        self.mini_titlebar.setStyleSheet(f"""
            background-color: {c_surf};
            border-top-left-radius: 9px;
            border-top-right-radius: 9px;
            border-bottom: 1px solid {c_border};
        """)
        self.mini_active_tab.setStyleSheet(f"""
            background-color: {c_bg};
            border: 1px solid {c_border};
            border-top: 2px solid {c_acc};
            border-radius: 4px;
        """)
        self.lbl_mtab.setStyleSheet(f"color: {c_text}; font-size: 9.5px; font-weight: 600; border: none; background: transparent;")

        self.mini_sidebar.setStyleSheet(f"""
            background-color: {c_surf};
            border-right: 1px solid {c_border};
            border-bottom-left-radius: 9px;
        """)
        self.mini_tool_active.setStyleSheet(f"""
            background-color: {c_acc};
            border-radius: 4px;
        """)
        self.mini_tool_idle.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
        """)

        self.mini_canvas.setStyleSheet(f"""
            background-color: {c_bg};
            border-bottom-right-radius: 9px;
        """)
        self.mini_doc_card.setStyleSheet(f"""
            background-color: {c_surf};
            border: 1px solid {c_border};
            border-radius: 6px;
        """)
        self.lbl_doc_title.setStyleSheet(f"color: {c_text}; font-size: 10px; font-weight: 700; border: none; background: transparent;")
        self.mini_doc_line.setStyleSheet(f"background-color: {c_acc}; border: none;")

        is_acc_dark = QColor(c_acc).lightness() < 140
        btn_txt_col = "#ffffff" if is_acc_dark else "#0f172a"
        self.mini_btn.setStyleSheet(f"""
            background-color: {c_acc};
            color: {btn_txt_col};
            font-size: 9px;
            font-weight: 700;
            border-radius: 4px;
            border: none;
            padding: 0 4px;
        """)


class ModernColorSlotCard(QFrame):
    """
    Tek bir renk bileşeni için (Vurgu, Arka Plan, Yüzey, Metin)
    büyük renk çemberi, HEX etiketi ve 'Değiştir' butonuna sahip şık kart.
    """
    colorChanged = pyqtSignal(str, str)  # (key, hex_color)

    def __init__(self, key: str, title: str, desc: str, initial_hex: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.current_hex = initial_hex.upper()
        self.setObjectName("ModernColorSlotCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)

        # 1. Renk Yuvarlak Önizlemesi
        self.swatch = QFrame()
        self.swatch.setFixedSize(30, 30)
        h.addWidget(self.swatch)

        # 2. Başlık ve Açıklama
        v_info = QVBoxLayout()
        v_info.setSpacing(1)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #f8fafc;")
        v_info.addWidget(lbl_t)

        lbl_d = QLabel(desc)
        lbl_d.setStyleSheet("font-size: 9.5px; color: #94a3b8;")
        lbl_d.setWordWrap(True)
        v_info.addWidget(lbl_d)
        h.addLayout(v_info, 1)

        # 3. İnteraktif HEX Butonu & İkon
        self.btn_hex = QPushButton(f" {self.current_hex}")
        self.btn_hex.setIcon(ModernIconFactory.icon_brush())
        self.btn_hex.setIconSize(QSize(12, 12))
        self.btn_hex.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.btn_hex.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hex.setToolTip(LanguageManager.tr("theme_btn_pick_color"))
        self.btn_hex.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                padding: 3px 6px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.16);
                border-color: #38bdf8;
                color: #38bdf8;
            }
        """)
        self.btn_hex.clicked.connect(self._open_picker)
        h.addWidget(self.btn_hex)

        # Geriye dönük referanslar
        self.btn_edit = self.btn_hex
        self.lbl_hex = self.btn_hex

        self._update_swatch()

    def set_color(self, hex_col: str):
        self.current_hex = hex_col.upper()
        self.lbl_hex.setText(self.current_hex)
        self._update_swatch()

    def _update_swatch(self):
        c = QColor(self.current_hex)
        border_col = "#ffffff" if c.lightness() < 128 else "#000000"
        self.swatch.setStyleSheet(f"""
            background-color: {self.current_hex};
            border: 2px solid {border_col};
            border-radius: 15px;
        """)
        self.setStyleSheet("""
            QFrame#ModernColorSlotCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QFrame#ModernColorSlotCard:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border-color: rgba(255, 255, 255, 0.18);
            }
        """)

    def mousePressEvent(self, event):
        self._open_picker()
        super().mousePressEvent(event)

    def _open_picker(self):
        from src.ui.dialogs.modern_color_picker import ModernColorPickerDialog
        chosen = ModernColorPickerDialog.get_color(
            initial_color=self.current_hex,
            role_title=self.title,
            parent=self.window()
        )
        if chosen:
            self.set_color(chosen)
            self.colorChanged.emit(self.key, chosen)


class ModernThemeStudioCard(QFrame):
    """
    Canlı Vurgu Önayarları, 4 Renk Yuvası, Canlı Uygulama Önizlemesi
    ve Sıfırlama / Aktif Temadan Kopyalama aksiyonlarını barındıran komple modern stüdyo paneli.
    """
    colorsChanged = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernThemeStudioCard")
        from src.ui.modern_views import get_custom_theme_colors
        self._colors = get_custom_theme_colors()

        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(12, 12, 12, 12)
        main_v.setSpacing(10)

        # 1. Stüdyo Başlık Şeridi
        h_head = QHBoxLayout()
        h_head.setContentsMargins(0, 0, 0, 0)
        h_head.setSpacing(10)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_palette_grid("#38bdf8").pixmap(20, 20))
        h_head.addWidget(lbl_icon)

        v_t = QVBoxLayout()
        v_t.setSpacing(2)
        lbl_title = QLabel(LanguageManager.tr("theme_studio_title"))
        lbl_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #f8fafc;")
        v_t.addWidget(lbl_title)

        lbl_desc = QLabel(LanguageManager.tr("theme_studio_desc"))
        lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        v_t.addWidget(lbl_desc)
        h_head.addLayout(v_t, 1)

        lbl_badge = QLabel("STUDIO")
        lbl_badge.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
        """)
        h_head.addWidget(lbl_badge)
        main_v.addLayout(h_head)

        # 2. Hızlı Vurgu Önayarları ve Hızlı Aksiyonlar
        v_acc = QVBoxLayout()
        v_acc.setSpacing(5)

        lbl_acc_title = QLabel(LanguageManager.tr("theme_accent_presets_title"))
        lbl_acc_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #cbd5e1;")
        v_acc.addWidget(lbl_acc_title)

        h_acc_bar = QHBoxLayout()
        h_acc_bar.setContentsMargins(0, 0, 0, 0)
        h_acc_bar.setSpacing(8)

        accent_presets = [
            ("#38bdf8", "Sky Cyan"),
            ("#6366f1", "Electric Indigo"),
            ("#10b981", "Forest Emerald"),
            ("#a855f7", "Royal Purple"),
            ("#ff2a85", "Cyber Fuchsia"),
            ("#f43f5e", "Crimson Flame"),
            ("#f59e0b", "Sunset Amber"),
            ("#14b8a6", "Teal Mint"),
            ("#64748b", "Apple Titanium"),
            ("#f97316", "Coral Orange"),
        ]
        self._preset_btns = []
        for c_hex, c_tip in accent_presets:
            btn_p = QPushButton()
            btn_p.setFixedSize(20, 20)
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.setToolTip(f"{c_tip} ({c_hex})")
            btn_p.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c_hex};
                    border: 1.5px solid rgba(255, 255, 255, 0.3);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            btn_p.clicked.connect(lambda checked, col=c_hex: self._on_accent_preset_clicked(col))
            self._preset_btns.append(btn_p)
            h_acc_bar.addWidget(btn_p)

        h_acc_bar.addStretch(1)

        # Hızlı Aksiyon Butonları (Kopyala & Sıfırla)
        self.btn_copy_active = QPushButton(" " + LanguageManager.tr("theme_btn_copy_active"))
        self.btn_copy_active.setIcon(ModernIconFactory.icon_paste())
        self.btn_copy_active.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_active.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                color: #cbd5e1;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        h_acc_bar.addWidget(self.btn_copy_active)

        self.btn_reset = QPushButton(" " + LanguageManager.tr("theme_btn_reset_defaults"))
        self.btn_reset.setIcon(ModernIconFactory.icon_recovery())
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                color: #cbd5e1;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border-color: #ef4444;
                color: #ffffff;
            }
        """)
        h_acc_bar.addWidget(self.btn_reset)

        v_acc.addLayout(h_acc_bar)
        main_v.addLayout(v_acc)

        # 3. 4 Renk Yuvası Kartları (2x2 Grid)
        grid_slots = QGridLayout()
        grid_slots.setHorizontalSpacing(10)
        grid_slots.setVerticalSpacing(8)

        self.slot_accent = ModernColorSlotCard(
            "accent",
            LanguageManager.tr("theme_color_accent"),
            LanguageManager.tr("theme_color_accent_desc"),
            self._colors.get("accent", "#38bdf8"),
            self
        )
        self.slot_accent.colorChanged.connect(self._on_slot_color_changed)
        grid_slots.addWidget(self.slot_accent, 0, 0)

        self.slot_bg = ModernColorSlotCard(
            "bg",
            LanguageManager.tr("theme_color_bg"),
            LanguageManager.tr("theme_color_bg_desc"),
            self._colors.get("bg", "#14171d"),
            self
        )
        self.slot_bg.colorChanged.connect(self._on_slot_color_changed)
        grid_slots.addWidget(self.slot_bg, 0, 1)

        self.slot_surface = ModernColorSlotCard(
            "surface",
            LanguageManager.tr("theme_color_surface"),
            LanguageManager.tr("theme_color_surface_desc"),
            self._colors.get("surface", "#1e222b"),
            self
        )
        self.slot_surface.colorChanged.connect(self._on_slot_color_changed)
        grid_slots.addWidget(self.slot_surface, 1, 0)

        self.slot_text = ModernColorSlotCard(
            "text",
            LanguageManager.tr("theme_color_text"),
            LanguageManager.tr("theme_color_text_desc"),
            self._colors.get("text", "#f1f5f9"),
            self
        )
        self.slot_text.colorChanged.connect(self._on_slot_color_changed)
        grid_slots.addWidget(self.slot_text, 1, 1)

        main_v.addLayout(grid_slots)

        # 4. Canlı Minyatür Uygulama Önizlemesi
        self.preview_card = ThemeMiniPreviewCard(self._colors, self)
        main_v.addWidget(self.preview_card)

        self.setStyleSheet("""
            QFrame#ModernThemeStudioCard {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 12px;
            }
        """)

    def _on_accent_preset_clicked(self, hex_col: str):
        self._on_slot_color_changed("accent", hex_col)

    def _on_slot_color_changed(self, key: str, hex_col: str):
        self._colors[key] = hex_col
        if key == "accent":
            self.slot_accent.set_color(hex_col)
        elif key == "bg":
            self.slot_bg.set_color(hex_col)
        elif key == "surface":
            self.slot_surface.set_color(hex_col)
            self._colors["border"] = QColor(hex_col).lighter(120).name()
        elif key == "text":
            self.slot_text.set_color(hex_col)

        self.preview_card.update_preview(self._colors)
        self.colorsChanged.emit(dict(self._colors))

    def set_all_colors(self, new_colors: dict):
        self._colors.update(new_colors)
        if "accent" in self._colors:
            self.slot_accent.set_color(self._colors["accent"])
        if "bg" in self._colors:
            self.slot_bg.set_color(self._colors["bg"])
        if "surface" in self._colors:
            self.slot_surface.set_color(self._colors["surface"])
        if "text" in self._colors:
            self.slot_text.set_color(self._colors["text"])
        self.preview_card.update_preview(self._colors)
        self.colorsChanged.emit(dict(self._colors))

    def get_colors(self) -> dict:
        return dict(self._colors)

    def save_to_settings(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        import json
        settings.setValue("custom_theme_colors", json.dumps(self._colors))


class LangOptionCard(QFrame):
    """
    Dil seçimini modern ve şık bir kart formatında sunan bileşen.
    """
    def __init__(self, title, desc, radio_btn, parent=None):
        super().__init__(parent)
        self.radio_btn = radio_btn
        self.setObjectName("LangOptionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(14, 12, 14, 12)
        h_layout.setSpacing(14)

        self.radio_btn.setText("")
        h_layout.addWidget(self.radio_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        v_info = QVBoxLayout()
        v_info.setSpacing(3)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.lbl_desc.setWordWrap(True)
        v_info.addWidget(self.lbl_title)
        v_info.addWidget(self.lbl_desc)
        h_layout.addLayout(v_info, 1)

        self.radio_btn.toggled.connect(self.update_card_style)
        self.update_card_style()

    def update_card_style(self):
        is_checked = self.radio_btn.isChecked()
        if is_checked:
            self.setStyleSheet("""
                QFrame#LangOptionCard {{
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1.5px solid #38bdf8;
                    border-radius: 9px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame#LangOptionCard {{
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 9px;
                }}
                QFrame#LangOptionCard:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.22);
                }}
            """)

    def mousePressEvent(self, event):
        self.radio_btn.setChecked(True)
        super().mousePressEvent(event)


class AuraSettingsDialog(QDialog):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.settings = QSettings("AuraPDF", "PDFViewer")
        self.shortcut_settings = QSettings("AuraPDF", "Shortcuts")
        
        self.setWindowTitle(LanguageManager.tr("settings_title"))
        self.setWindowIcon(ModernIconFactory.icon_settings())
        self.resize(1000, 750)
        self.setMinimumSize(900, 660)
        self.setSizeGripEnabled(True)
        
        # Seçili temanın rengine göre stil
        self.current_theme = self.settings.value("app_theme", "gray")
        self._init_ui()
        self._load_saved_values()
        self._apply_dialog_style()

    def _apply_dialog_style(self):
        from src.ui.dialog_theme import apply_dialog_theme, get_theme_palette, get_current_theme
        theme = get_current_theme(self.main_window or self)
        pal = get_theme_palette(self.main_window or self)
        extra_css = f"""
            QListWidget#SettingsSidebar {{
                background-color: transparent;
                border: none;
                outline: none;
                padding: 6px 0px;
            }}
            QListWidget#SettingsSidebar::item {{
                background-color: transparent;
                border: 1px solid transparent;
                margin: 3px 4px;
                border-radius: 9px;
                padding: 10px 14px;
                color: {pal['muted']};
                font-size: 13px;
                font-weight: 600;
            }}
            QListWidget#SettingsSidebar::item:hover {{
                background-color: {pal['card']};
                border-color: {pal['border']};
                color: {pal['text']};
            }}
            QListWidget#SettingsSidebar::item:selected {{
                background-color: {pal['accent']};
                border-color: {pal['accent']};
                color: #ffffff;
                font-weight: bold;
            }}
            QStackedWidget {{
                background-color: {pal['bg']};
                border: 1px solid {pal['border']};
                border-radius: 12px;
            }}
            QFrame#SettingsCard, QFrame.card, QFrame[class="card"] {{
                background-color: {pal['card']};
                border: 1px solid {pal['border']};
                border-radius: 10px;
                padding: 16px 18px;
            }}
            QFrame#SettingsCardSep {{
                background-color: {pal['border']};
            }}
            QLabel {{
                color: {pal['text']};
            }}
            QComboBox {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 30px;
            }}
            QComboBox:hover {{
                border-color: {pal['accent']};
            }}
            QLineEdit {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 30px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {pal['accent']};
            }}
            QRadioButton {{
                color: {pal['text']};
                font-size: 13px;
                font-weight: 500;
            }}
            QCheckBox {{
                color: {pal['text']};
                font-size: 13px;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {pal['accent']};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 9px 24px;
                font-size: 13px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {pal['accent_hover']};
            }}
            QPushButton#SecondaryBtn {{
                background-color: {pal['card']};
                color: {pal['text']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {pal['border']};
            }}
            QPushButton#CancelBtn {{
                background-color: transparent;
                color: {pal['muted']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#CancelBtn:hover {{
                color: {pal['text']};
                background-color: {pal['card']};
            }}
            QPushButton#DangerBtn {{
                background-color: #ef4444;
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
            }}
            QPushButton#DangerBtn:hover {{
                background-color: #dc2626;
            }}
        """
        apply_dialog_theme(self, self.main_window or self, extra_css=extra_css)
        for card in getattr(self, 'theme_cards', []):
            card.update_card_style()
        for card in getattr(self, 'lang_cards', []):
            card.update_card_style()

    def _create_setting_row(self, title_text: str, widget: QWidget, desc_text: str = None) -> QWidget:
        """Ayarlar paneli için metin sol, kontrol sağ şeklinde hizalanmış geniş ve okunaklı satır üretir."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(16)

        v_lbl = QVBoxLayout()
        v_lbl.setSpacing(3)
        lbl_t = QLabel(title_text)
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 600;")
        v_lbl.addWidget(lbl_t)
        if desc_text:
            lbl_d = QLabel(desc_text)
            lbl_d.setStyleSheet("font-size: 11px; color: #94a3b8;")
            lbl_d.setWordWrap(True)
            v_lbl.addWidget(lbl_d)
        row_layout.addLayout(v_lbl, 1)

        widget.setMinimumWidth(210)
        widget.setMaximumWidth(270)
        row_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        main_split = QHBoxLayout()
        root_layout.addLayout(main_split, 1)

        # Sidebar (QListWidget)
        from PyQt6.QtWidgets import QListWidget, QStackedWidget, QListWidgetItem
        self.sidebar = QListWidget(self)
        self.sidebar.setFixedWidth(225)
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setSpacing(4)
        self.sidebar.setIconSize(QSize(18, 18))
        main_split.addWidget(self.sidebar)

        # Content Area (QStackedWidget)
        self.stacked_widget = QStackedWidget(self)
        main_split.addWidget(self.stacked_widget, 1)

        # Pages with vector icons
        pages = [
            (LanguageManager.tr("settings_tab_general"), ModernIconFactory.icon_settings(), self._build_general_tab),
            (LanguageManager.tr("settings_tab_theme"), ModernIconFactory.icon_view_single(), self._build_theme_tab),
            (LanguageManager.tr("settings_tab_shortcuts"), ModernIconFactory.icon_info(), self._build_shortcuts_tab),
            (LanguageManager.tr("settings_tab_author"), ModernIconFactory.icon_edit_content(), self._build_author_tab),
            (LanguageManager.tr("settings_tab_lang"), ModernIconFactory.icon_contents(), self._build_lang_tab),
            (LanguageManager.tr("settings_tab_toolbar"), ModernIconFactory.icon_toolbox(), self._build_toolbar_tab),
            (LanguageManager.tr("cursor_settings_title"), ModernIconFactory.icon_cursor(), self._build_cursor_tab),
            (LanguageManager.tr("settings_tab_updates"), ModernIconFactory.icon_update(), self._build_updates_tab)
        ]
        
        for name, icon, build_func in pages:
            item = QListWidgetItem(icon, f"  {name}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setSizeHint(QSize(0, 46))
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
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        # 1. Zoom Modu
        self.cmb_zoom_mode = QComboBox()
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_last"), "last")
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_100"), "100")
        self.cmb_zoom_mode.addItem(LanguageManager.tr("zoom_mode_fit"), "fit")
        row_zoom = self._create_setting_row(
            LanguageManager.tr("default_zoom_mode_lbl"),
            self.cmb_zoom_mode,
            "Belge açıldığında uygulanacak varsayılan görünüm ve yakınlaştırma ölçeği."
        )
        card_layout.addWidget(row_zoom)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setObjectName("SettingsCardSep")
        card_layout.addWidget(sep1)

        # 2. Sayfa Şablonu
        self.cmb_default_template = QComboBox()
        self.cmb_default_template.addItem(LanguageManager.tr("style_blank_title"), "blank")
        self.cmb_default_template.addItem(LanguageManager.tr("style_lined_title"), "lined")
        self.cmb_default_template.addItem(LanguageManager.tr("style_grid_title"), "grid")
        self.cmb_default_template.addItem(LanguageManager.tr("style_dotted_title"), "dotted")
        self.cmb_default_template.addItem(LanguageManager.tr("style_cornell_title"), "cornell")
        self.cmb_default_template.addItem(LanguageManager.tr("style_music_title"), "music")
        self.cmb_default_template.addItem(LanguageManager.tr("style_dark_title"), "dark")
        self.cmb_default_template.addItem(LanguageManager.tr("style_cover_title"), "cover")
        row_template = self._create_setting_row(
            LanguageManager.tr("default_page_template_lbl"),
            self.cmb_default_template,
            "Yeni not ve çizim sayfası oluştururken kullanılacak varsayılan kağıt stili."
        )
        card_layout.addWidget(row_template)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setObjectName("SettingsCardSep")
        card_layout.addWidget(sep2)

        # 3. Font Boyutu
        self.cmb_app_font_size = QComboBox()
        self.cmb_app_font_size.addItem(LanguageManager.tr("font_size_small", size=9), 9)
        self.cmb_app_font_size.addItem(LanguageManager.tr("font_size_standard", size=10), 10)
        self.cmb_app_font_size.addItem(LanguageManager.tr("font_size_medium", size=11), 11)
        self.cmb_app_font_size.addItem(LanguageManager.tr("font_size_large", size=12), 12)
        self.cmb_app_font_size.addItem(LanguageManager.tr("font_size_xlarge", size=14), 14)
        row_font = self._create_setting_row(
            LanguageManager.tr("settings_app_font_size_lbl"),
            self.cmb_app_font_size,
            "Uygulama menüleri, panelleri ve butonlarındaki genel yazı boyutu."
        )
        card_layout.addWidget(row_font)

        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setObjectName("SettingsCardSep")
        card_layout.addWidget(sep3)

        # 4. Yan Panel & Araç Çubuğu Düzeni
        self.cmb_panel_layout = QComboBox()
        self.cmb_panel_layout.addItem(LanguageManager.tr("settings_panel_layout_tools_right"), "tools_right_nav_left")
        self.cmb_panel_layout.addItem(LanguageManager.tr("settings_panel_layout_tools_left"), "tools_left_nav_right")
        row_panel_layout = self._create_setting_row(
            LanguageManager.tr("settings_panel_layout_lbl"),
            self.cmb_panel_layout,
            LanguageManager.tr("settings_panel_layout_desc")
        )
        card_layout.addWidget(row_panel_layout)
        sep4 = QFrame()
        sep4.setFixedHeight(1)
        sep4.setObjectName("SettingsCardSep")
        card_layout.addWidget(sep4)

        # 5. Sekme Önizlemesi (Fare ile üzerine gelindiğinde)
        self.chk_tab_hover_preview = QCheckBox()
        self.chk_tab_hover_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_tab_hover_preview.toggled.connect(self._on_tab_preview_toggled)
        row_tab_preview = self._create_setting_row(
            LanguageManager.tr("settings_show_tab_hover_preview"),
            self.chk_tab_hover_preview,
            LanguageManager.tr("settings_show_tab_hover_preview_desc")
        )
        card_layout.addWidget(row_tab_preview)

        layout.addWidget(card)

        # Fabrika Ayarlarına Sıfırlama Kartı
        card_reset = QFrame()
        card_reset.setObjectName("SettingsCard")
        card_reset_layout = QVBoxLayout(card_reset)
        card_reset_layout.setContentsMargins(16, 14, 16, 14)
        card_reset_layout.setSpacing(10)

        lbl_reset_title = QLabel(LanguageManager.tr("reset_all_section_title"))
        lbl_reset_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        card_reset_layout.addWidget(lbl_reset_title)

        lbl_reset_desc = QLabel(LanguageManager.tr("reset_all_section_desc"))
        lbl_reset_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
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
        self.settings.sync()
        self.shortcut_settings.sync()

        # 2. Temayı Gray (Varsayılan) olarak seç
        if "gray" in self.theme_radios:
            self.theme_radios["gray"].setChecked(True)
        self.current_theme = "gray"
        self._apply_dialog_style()

        if hasattr(self, 'theme_studio_card') and hasattr(self.theme_studio_card, 'set_all_colors'):
            default_custom = {
                "accent": "#38bdf8",
                "bg": "#14171d",
                "surface": "#1e222b",
                "text": "#f1f5f9",
                "border": "#2e3442"
            }
            try:
                self.theme_studio_card.set_all_colors(default_custom)
            except Exception:
                pass

        # Dil (Varsayılan: Türkçe)
        if hasattr(self, 'rb_lang_tr'):
            self.rb_lang_tr.setChecked(True)

        # 3. Tüm UI alanlarını temizlenmiş QSettings varsayılanları üzerinden yeniden yükle
        self._load_saved_values()

        # Yan panel & araç çubuğu düzenini kesin olarak varsayılan "tools_right_nav_left" yap
        if hasattr(self, 'cmb_panel_layout'):
            self._set_cmb_data(self.cmb_panel_layout, "tools_right_nav_left")

        # 4. Kapsül ve araç çubuğu ana pencere durumlarını sıfırla
        if self.main_window:
            if hasattr(self.main_window, 'undock_capsule'):
                self.main_window.undock_capsule()
            if hasattr(self.main_window, 'reset_toolbar_order'):
                self.main_window.reset_toolbar_order()
            if hasattr(self.main_window, 'update_panels_layout'):
                self.main_window.update_panels_layout("tools_right_nav_left")
            if hasattr(self.main_window, 'floating_capsule') and self.main_window.floating_capsule:
                self.main_window.floating_capsule.user_moved = False
                if hasattr(self.main_window, 'update_floating_capsule_pos'):
                    self.main_window.update_floating_capsule_pos()

        # 5. Kaydet & Ana Uygulamaya Uygula
        self.apply_settings()

        # 6. Bildirim
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
        lbl_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        self.theme_group = QButtonGroup(self)

        from src.ui.modern_views import get_custom_theme_colors
        custom_cfg = get_custom_theme_colors()
        custom_pills = [custom_cfg.get("surface", "#1e222b"), custom_cfg.get("bg", "#14171d"), custom_cfg.get("accent", "#38bdf8")]

        themes_info = [
            ("gray", "theme_gray", "theme_gray_desc", ["#2b2d30", "#35383c", "#60a5fa"], 0),
            ("emerald", "theme_emerald", "theme_emerald_desc", ["#091a14", "#112a21", "#34d399"], 1),
            ("purple", "theme_purple", "theme_purple_desc", ["#150d22", "#201435", "#c084fc"], 2),
            ("crimson", "theme_crimson", "theme_crimson_desc", ["#1d0b10", "#2d1118", "#fb7185"], 3),
            ("nord", "theme_nord", "theme_nord_desc", ["#181e29", "#222b3a", "#38bdf8"], 4),
            ("vice_city", "theme_vice_city", "theme_vice_city_desc", ["#160024", "#240e3b", "#ff2a85"], 5),
            ("apple", "theme_apple", "theme_apple_desc", ["#0e1014", "#1a1d24", "#38bdf8"], 6),
            ("custom", "theme_custom", "theme_custom_desc", custom_pills, 7),
        ]

        self.theme_radios = {}
        self.theme_cards = []
        for code, title_key, desc_key, colors, group_id in themes_info:
            rb = QRadioButton()
            self.theme_group.addButton(rb, group_id)
            self.theme_radios[code] = rb

            theme_card = ThemeOptionCard(
                theme_code=code,
                title=LanguageManager.tr(title_key),
                desc=LanguageManager.tr(desc_key),
                palette_colors=colors,
                radio_btn=rb,
                parent=card
            )
            if code == "custom":
                self.theme_card_custom = theme_card
            self.theme_cards.append(theme_card)
            card_layout.addWidget(theme_card)

        # Referanslar (Geriye dönük uyumluluk)
        self.rb_gray = self.theme_radios["gray"]
        self.rb_light = self.rb_gray
        self.rb_dark = self.rb_gray
        self.rb_emerald = self.theme_radios["emerald"]
        self.rb_purple = self.theme_radios["purple"]
        self.rb_crimson = self.theme_radios["crimson"]
        self.rb_nord = self.theme_radios["nord"]
        self.rb_vice_city = self.theme_radios["vice_city"]
        self.rb_apple = self.theme_radios["apple"]
        self.rb_custom = self.theme_radios["custom"]

        layout.addWidget(card)

        # 2. Modern Tema ve Renk Stüdyosu (Özelleştirme Paneli)
        self.theme_studio_card = ModernThemeStudioCard(parent=self)
        self.theme_studio_card.colorsChanged.connect(self._on_studio_colors_changed)
        self.theme_studio_card.btn_reset.clicked.connect(self._on_studio_reset_defaults)
        self.theme_studio_card.btn_copy_active.clicked.connect(self._on_studio_copy_active_theme)
        layout.addWidget(self.theme_studio_card)

        # Özel tema seçildiğinde stüdyo paneline otomatik odaklan
        self.theme_radios["custom"].toggled.connect(
            lambda chk: scroll.ensureWidgetVisible(self.theme_studio_card) if chk else None
        )

        layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout_main.addWidget(scroll)

    def _on_studio_colors_changed(self, colors: dict):
        if "custom" in self.theme_radios:
            self.theme_radios["custom"].setChecked(True)
        if hasattr(self, 'theme_card_custom'):
            surf = colors.get("surface", "#1e222b")
            bg = colors.get("bg", "#14171d")
            acc = colors.get("accent", "#38bdf8")
            self.theme_card_custom.update_palette_pills([surf, bg, acc])

    def _on_studio_reset_defaults(self):
        default_custom = {
            "accent": "#38bdf8",
            "bg": "#14171d",
            "surface": "#1e222b",
            "text": "#f1f5f9",
            "border": "#2e3442"
        }
        self.theme_studio_card.set_all_colors(default_custom)
        if "custom" in self.theme_radios:
            self.theme_radios["custom"].setChecked(True)

    def _on_studio_copy_active_theme(self):
        from src.ui.modern_views import get_modern_theme_colors
        active_code = "gray"
        for code, rb in self.theme_radios.items():
            if rb.isChecked() and code != "custom":
                active_code = code
                break
        pal = get_modern_theme_colors(active_code)
        new_cols = {
            "accent": pal.get("accent", "#38bdf8"),
            "bg": pal.get("bg", "#14171d"),
            "surface": pal.get("surface", "#1e222b"),
            "text": pal.get("text", "#f1f5f9"),
            "border": pal.get("border", "#2e3442")
        }
        self.theme_studio_card.set_all_colors(new_cols)
        if "custom" in self.theme_radios:
            self.theme_radios["custom"].setChecked(True)

    # ----------------------------------------------------
    # SEKME: KLAVYE KISAYOLLARI (YENİ)
    # ----------------------------------------------------
    def _build_shortcuts_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        h_head = QHBoxLayout()
        h_head.setContentsMargins(0, 0, 0, 0)
        lbl_title = QLabel(LanguageManager.tr("shortcuts_section_title"))
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        h_head.addWidget(lbl_title, stretch=1)

        self.btn_open_shortcuts_guide = QPushButton(" " + LanguageManager.tr("shortcuts_dialog_title") + " (F1)")
        self.btn_open_shortcuts_guide.setIcon(ModernIconFactory.icon_info("#38bdf8"))
        self.btn_open_shortcuts_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_shortcuts_guide.setStyleSheet("""
            QPushButton {
                background: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
                color: #38bdf8;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.25);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        self.btn_open_shortcuts_guide.clicked.connect(self._open_shortcuts_guide_dialog)
        h_head.addWidget(self.btn_open_shortcuts_guide)
        layout.addLayout(h_head)

        lbl_desc = QLabel(LanguageManager.tr("shortcuts_section_desc"))
        lbl_desc.setStyleSheet(" font-size: 12px;")
        layout.addWidget(lbl_desc)

        card_hint = ModernInfoCard(text=LanguageManager.tr("shortcut_hint"), parent=self)
        layout.addWidget(card_hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        card = QFrame()
        card.setObjectName("SettingsCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)

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

    def _open_shortcuts_guide_dialog(self):
        from src.ui.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
        dlg = KeyboardShortcutsDialog(self)
        dlg.exec()

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
        lbl_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(14)

        def_user, def_comp = get_default_author_info()

        # Ad Soyad / Yazar Adı
        lbl_name = QLabel(LanguageManager.tr("author_name_lbl"))
        lbl_name.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.txt_author_name = QLineEdit()
        self.txt_author_name.setPlaceholderText(def_user or LanguageManager.tr("author_name_placeholder"))
        card_layout.addWidget(lbl_name)
        card_layout.addWidget(self.txt_author_name)

        # Unvan / Şirket
        lbl_t = QLabel(LanguageManager.tr("author_title_lbl"))
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.txt_author_title = QLineEdit()
        self.txt_author_title.setPlaceholderText(def_comp or LanguageManager.tr("author_title_placeholder"))
        card_layout.addWidget(lbl_t)
        card_layout.addWidget(self.txt_author_title)

        # E-posta
        lbl_e = QLabel(LanguageManager.tr("author_email_lbl"))
        lbl_e.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.txt_author_email = QLineEdit()
        self.txt_author_email.setPlaceholderText(LanguageManager.tr("author_email_placeholder"))
        card_layout.addWidget(lbl_e)
        card_layout.addWidget(self.txt_author_email)

        card_layout.addSpacing(6)
        self.chk_save_metadata = QCheckBox(LanguageManager.tr("author_save_metadata_chk"))
        card_layout.addWidget(self.chk_save_metadata)

        self.chk_use_notes = QCheckBox(LanguageManager.tr("author_use_notes_chk"))
        card_layout.addWidget(self.chk_use_notes)

        card_layout.addSpacing(6)
        # Varsayılan Bilgisayar Bilgilerini Yükle Butonu
        reset_bar = QHBoxLayout()
        self.btn_reset_author = QPushButton(" " + LanguageManager.tr("btn_reset_author_info"))
        self.btn_reset_author.setIcon(ModernIconFactory.icon_undo())
        self.btn_reset_author.setObjectName("SecondaryBtn")
        self.btn_reset_author.setCursor(Qt.CursorShape.PointingHandCursor)
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
        lbl_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(lbl_desc)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        self.lang_group = QButtonGroup(self)
        self.lang_cards = []

        self.rb_lang_tr = QRadioButton()
        self.lang_group.addButton(self.rb_lang_tr, 1)
        card_tr = LangOptionCard(
            title="Türkçe (Turkish)",
            desc="Uygulama arayüzü ve menüleri Türkçe olarak kullanılır.",
            radio_btn=self.rb_lang_tr,
            parent=card
        )
        self.lang_cards.append(card_tr)
        card_layout.addWidget(card_tr)

        self.rb_lang_en = QRadioButton()
        self.lang_group.addButton(self.rb_lang_en, 2)
        card_en = LangOptionCard(
            title="English (İngilizce)",
            desc="Application interface and menus are displayed in English.",
            radio_btn=self.rb_lang_en,
            parent=card
        )
        self.lang_cards.append(card_en)
        card_layout.addWidget(card_en)

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
        card.setObjectName("SettingsCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
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
            meta = FLOATING_TOOLBAR_ITEMS_META.get(k) or TOOLBAR_ITEMS_META.get(k)
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
        self._populate_toolbar_list(DEFAULT_FLOATING_TOOLBAR_ORDER)

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
        card_preset.setObjectName("SettingsCard")
        p_layout = QHBoxLayout(card_preset)
        p_layout.setContentsMargins(14, 12, 14, 12)
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
        card_tools.setObjectName("SettingsCard")
        grid = QGridLayout(card_tools)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

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
        card_preview.setObjectName("SettingsCard")
        cp_layout = QVBoxLayout(card_preview)
        cp_layout.setContentsMargins(14, 12, 14, 12)
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
        card_opts.setObjectName("SettingsCard")
        co_layout = QVBoxLayout(card_opts)
        co_layout.setContentsMargins(14, 12, 14, 12)
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
        card_status.setObjectName("SettingsCard")
        card_status_layout = QVBoxLayout(card_status)
        card_status_layout.setContentsMargins(16, 14, 16, 14)
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
        card_opts.setObjectName("SettingsCard")
        card_opts_layout = QVBoxLayout(card_opts)
        card_opts_layout.setContentsMargins(16, 14, 16, 14)
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

        card_token_hint = ModernInfoCard(text=LanguageManager.tr("updates_token_tip"), parent=self)
        card_opts_layout.addWidget(card_token_hint)

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
        try:
            if cmb:
                idx = cmb.findData(data_val)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
        except Exception:
            pass

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
            self.rb_gray.setChecked(True)

        if hasattr(self, 'theme_studio_card') and hasattr(self, 'theme_card_custom'):
            colors = self.theme_studio_card.get_colors()
            surf = colors.get("surface", "#1e222b")
            bg = colors.get("bg", "#14171d")
            acc = colors.get("accent", "#38bdf8")
            self.theme_card_custom.update_palette_pills([surf, bg, acc])

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

        # Uygulama Font Boyutu
        if hasattr(self, 'cmb_app_font_size'):
            saved_fs = int(self.settings.value("app_font_size", 10))
            self._set_cmb_data(self.cmb_app_font_size, saved_fs)

        # Panel Yerleşimi
        if hasattr(self, 'cmb_panel_layout'):
            saved_layout = self.settings.value("sidebar_layout", "tools_right_nav_left")
            self._set_cmb_data(self.cmb_panel_layout, saved_layout)

        # Sekme Önizlemesi (Varsayılan: Kapalı)
        if hasattr(self, 'chk_tab_hover_preview'):
            self.chk_tab_hover_preview.setChecked(self.settings.value("show_tab_preview", False, type=bool))

        tb_version = self.settings.value("floating_tools_order_version", 0, type=int)
        raw_tb = self.settings.value("floating_tools_order", None)
        saved_tb = []
        if raw_tb and tb_version >= 2:
            try:
                if isinstance(raw_tb, str):
                    parsed = json.loads(raw_tb)
                elif isinstance(raw_tb, list):
                    parsed = list(raw_tb)
                else:
                    parsed = []
                for x in parsed:
                    x = OLD_TO_FLOATING_KEY_MAP.get(x, x)
                    if x in FLOATING_TOOLBAR_ITEMS_META and x not in saved_tb:
                        saved_tb.append(x)
            except Exception:
                saved_tb = []

        if not saved_tb or tb_version < 2:
            saved_tb = list(DEFAULT_FLOATING_TOOLBAR_ORDER)
            self.settings.setValue("floating_tools_order", json.dumps(DEFAULT_FLOATING_TOOLBAR_ORDER))
            self.settings.setValue("floating_tools_order_version", 2)
        else:
            for k in DEFAULT_FLOATING_TOOLBAR_ORDER:
                if k not in saved_tb:
                    saved_tb.append(k)

        self._populate_toolbar_list(saved_tb)

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

    def _on_tab_preview_toggled(self, checked: bool):
        self.settings.setValue("show_tab_preview", checked)
        self.settings.sync()
        if hasattr(self.main_window, 'show_tab_preview_enabled'):
            self.main_window.show_tab_preview_enabled = checked
        if not checked and hasattr(self.main_window, '_do_hide_tab_preview'):
            self.main_window._do_hide_tab_preview()

    load_settings = _load_saved_values

    def apply_settings(self):
        # 1. Tema Kaydet & Uygula
        selected_theme = "gray"
        for code, rb in self.theme_radios.items():
            if rb.isChecked():
                selected_theme = code
                break
        
        if selected_theme == "custom" and hasattr(self, 'theme_studio_card'):
            self.theme_studio_card.save_to_settings()

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
        self.settings.setValue("language", selected_lang)
        if selected_lang != LanguageManager.current_lang:
            if hasattr(self.main_window, 'change_language'):
                self.main_window.change_language(selected_lang)

        # 5. Zoom Modu
        zoom_mode = self.cmb_zoom_mode.currentData()
        self.settings.setValue("default_zoom_mode", zoom_mode)

        # Default Template
        tpl_mode = self.cmb_default_template.currentData()
        self.settings.setValue("default_page_template", tpl_mode)

        # Uygulama Font Boyutu
        if hasattr(self, 'cmb_app_font_size'):
            font_size = self.cmb_app_font_size.currentData()
            if font_size:
                self.settings.setValue("app_font_size", int(font_size))
                if hasattr(self.main_window, 'apply_app_font_size'):
                    self.main_window.apply_app_font_size(int(font_size))
                else:
                    app = QApplication.instance()
                    if app:
                        f = app.font()
                        f.setPointSize(int(font_size))
                        app.setFont(f)

        # Panel Yerleşimi
        if hasattr(self, 'cmb_panel_layout'):
            panel_layout = self.cmb_panel_layout.currentData()
            if panel_layout:
                self.settings.setValue("sidebar_layout", panel_layout)
                if hasattr(self.main_window, 'update_panels_layout'):
                    self.main_window.update_panels_layout(panel_layout)

        # Sekme Önizlemesi
        if hasattr(self, 'chk_tab_hover_preview'):
            is_preview = self.chk_tab_hover_preview.isChecked()
            self.settings.setValue("show_tab_preview", is_preview)
            self.settings.sync()
            if hasattr(self.main_window, 'show_tab_preview_enabled'):
                self.main_window.show_tab_preview_enabled = is_preview

        # 6. Toolbar Düzenini Kaydet & Uygula
        reordered_items = []
        for i in range(self.list_toolbar.count()):
            it = self.list_toolbar.item(i)
            item_id = it.data(Qt.ItemDataRole.UserRole)
            if item_id and item_id not in reordered_items:
                reordered_items.append(item_id)
        if reordered_items:
            self.settings.setValue("floating_tools_order", json.dumps(reordered_items))
            self.settings.setValue("floating_tools_order_version", 2)
            if hasattr(self.main_window, 'apply_floating_tools_order'):
                self.main_window.apply_floating_tools_order(reordered_items)
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
        if hasattr(self, 'btn_apply') and self.btn_apply:
            orig_txt = LanguageManager.tr("btn_apply_settings")
            self.btn_apply.setText(LanguageManager.tr("settings_applied_feedback"))
            def _safe_reset_apply():
                try:
                    if hasattr(self, 'btn_apply') and self.btn_apply:
                        self.btn_apply.setText(orig_txt)
                except (RuntimeError, Exception):
                    pass
            QTimer.singleShot(1400, _safe_reset_apply)

    def save_settings(self):
        self.apply_settings()
        self.accept()


# Geriye dönük uyumluluk takma adları (Backward compatibility aliases)
ModernSettingsDialog = AuraSettingsDialog
SettingsDialog = AuraSettingsDialog
AuraShortcutButton = ModernShortcutButton
AuraShortcutEdit = ModernShortcutEdit
