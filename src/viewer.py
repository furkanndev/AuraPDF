from typing import List, Dict, Optional, Any
import os
import sys
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_CURRENT_DIR)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)
import shutil
import pymupdf as fitz
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QToolButton, QMessageBox, 
                             QFileDialog, QMenu, QStackedLayout, QSizePolicy, QLayout, QDialog, QApplication)
from PyQt6.QtGui import (QIcon, QIntValidator, QShortcut, QKeySequence, QColor, QPen, QBrush)
from PyQt6.QtCore import Qt, QPoint, QSettings, QTimer, QEvent, QFileSystemWatcher

from src.core.i18n import LanguageManager
from src.core.speech_engine import AuraSpeechEngine
from src.core.shortcut_helper import (
    is_mouse_shortcut,
    parse_mouse_shortcut,
    clean_modifiers,
)
from src.ui.icons import ModernIconFactory
from src.ui.cursors import CursorFactory
from src.ui.widgets import (DraggableToolButton, ReorderableToolBar, ModernTabWidget, 
                            ThumbnailsDock, ModernSearchBar, FullscreenSlideToolbar)
from src.ui.popups import (SelectionSettingsPopup, TextSettingsPopup, ToolSettingsPopup, 
                           FloatingHUDPreview, PointerSettingsPopup, HighlighterRulerPopup, 
                           CursorPopup, RulerMeasurementPopup)
from src.ui.dialogs.document_properties_dialog import ModernDocumentPropertiesDialog
from src.document.tab_document import PDFTabDocument
from src.ui.ribbon_bar import ModernCategoryBar, CATEGORY_ITEMS


class EditableZoomWidget(QWidget):
    """
    Toolbar üzerinde yakınlaştırma (zoom) bileşeni:
    - Solunda zoom oranına bitişik küçük azaltma (-) butonu
    - Ortasında çift tıklanabilir ve elle düzenlenebilir zoom yüzdesi göstergesi
    - Sağında zoom oranına bitişik küçük arttırma (+) butonu
    Segmented (bitişik) tasarımı sayesinde butonlar doğrudan zoom oranına temas eder.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedSize(86, 26)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        # 1. Sol Azaltma Butonu (-)
        self.btn_minus = QToolButton()
        self.btn_minus.setText("−")
        self.btn_minus.setFixedSize(18, 26)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.setToolTip(LanguageManager.tr("zoom_out"))
        self.btn_minus.clicked.connect(self.zoom_out)
        main_layout.addWidget(self.btn_minus)

        # 2. Orta Gösterge / Düzenleme Kutusu
        self.display_container = QWidget()
        self.display_container.setFixedSize(50, 26)
        self.stack_layout = QStackedLayout(self.display_container)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setStackingMode(QStackedLayout.StackingMode.StackOne)

        self.label = QLabel(" 100% ")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stack_layout.addWidget(self.label)

        self.edit = QLineEdit()
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit.setFixedWidth(50)
        self.edit.returnPressed.connect(self.commit_zoom)
        self.edit.editingFinished.connect(self.on_editing_finished)
        self.stack_layout.addWidget(self.edit)
        self.stack_layout.setCurrentWidget(self.label)
        main_layout.addWidget(self.display_container)

        # 3. Sağ Arttırma Butonu (+)
        self.btn_plus = QToolButton()
        self.btn_plus.setText("+")
        self.btn_plus.setFixedSize(18, 26)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setToolTip(LanguageManager.tr("zoom_in"))
        self.btn_plus.clicked.connect(self.zoom_in)
        main_layout.addWidget(self.btn_plus)

        self._is_editing = False
        self.apply_theme(getattr(main_window, 'current_theme', 'dark'))

    def apply_theme(self, theme_name: str = "gray"):
        palette = {
            "gray": {"btn": "#3b3f45", "btn_hover": "#4b5159", "lbl": "#2b2d30", "border": "#525862", "border_inner": "#444850", "accent": "#60a5fa", "text": "#ffffff"},

            "emerald": {"btn": "#112a21", "btn_hover": "#1a3d30", "lbl": "#091a14", "border": "#1a3d30", "border_inner": "#112a21", "accent": "#10b981", "text": "#ecfdf5"},
            "purple": {"btn": "#201435", "btn_hover": "#2f1d4d", "lbl": "#150d22", "border": "#321f52", "border_inner": "#201435", "accent": "#a855f7", "text": "#faf5ff"},
            "crimson": {"btn": "#2d1118", "btn_hover": "#401923", "lbl": "#1d0b10", "border": "#441924", "border_inner": "#2d1118", "accent": "#f43f5e", "text": "#fff1f2"},
            "nord": {"btn": "#222b3a", "btn_hover": "#2f3b4f", "lbl": "#181e29", "border": "#313e54", "border_inner": "#222b3a", "accent": "#38bdf8", "text": "#f0f6fc"},
            "dark": {"btn": "#262626", "btn_hover": "#363636", "lbl": "#181818", "border": "#404040", "border_inner": "#303030", "accent": "#388bfd", "text": "#ffffff"},
            "vice_city": {"btn": "#240e3b", "btn_hover": "#381458", "lbl": "#160024", "border": "#ff2a85", "border_inner": "#240e3b", "accent": "#00f0ff", "text": "#ffffff"},
        }
        p = palette.get(theme_name, palette["gray"])

        btn_base = f"""
            QToolButton {{
                background-color: {p['btn']};
                color: {p['text']};
                border: 1px solid {p['border']};
                font-weight: bold;
                font-size: 13px;
                padding: 0px;
            }}
            QToolButton:hover {{
                background-color: {p['btn_hover']};
                color: #ffffff;
            }}
            QToolButton:pressed {{
                background-color: {p['lbl']};
            }}
        """
        lbl_style = f"""
            QLabel {{
                background-color: {p['lbl']};
                color: {p['text']};
                border-top: 1px solid {p['border']};
                border-bottom: 1px solid {p['border']};
                border-left: 1px solid {p['border_inner']};
                border-right: 1px solid {p['border_inner']};
                border-radius: 0px;
                padding: 0px 2px;
                font-weight: bold;
                font-size: 11px;
            }}
            QLabel:hover {{
                background-color: {p['btn']};
                color: {p['accent']};
            }}
        """
        edit_style = f"""
            QLineEdit {{
                background-color: {p['lbl']};
                color: #ffffff;
                border: 1.5px solid {p['accent']};
                border-radius: 0px;
                padding: 0px 2px;
                font-weight: bold;
                font-size: 11px;
            }}
        """
        self.btn_minus.setStyleSheet(btn_base + """
            QToolButton {
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-right: none;
            }
        """)
        self.label.setStyleSheet(lbl_style)
        self.edit.setStyleSheet(edit_style)
        self.btn_plus.setStyleSheet(btn_base + """
            QToolButton {
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                border-left: none;
            }
        """)

    def zoom_in(self):
        if hasattr(self.main_window, 'zoom_in'):
            self.main_window.zoom_in()

    def zoom_out(self):
        if hasattr(self.main_window, 'zoom_out'):
            self.main_window.zoom_out()

    def setText(self, text: str):
        self.label.setText(text)

    def text(self) -> str:
        return self.label.text()

    def setToolTip(self, text: str):
        self.label.setToolTip(text)
        if hasattr(self, 'btn_minus'):
            self.btn_minus.setToolTip(LanguageManager.tr("zoom_out"))
        if hasattr(self, 'btn_plus'):
            self.btn_plus.setToolTip(LanguageManager.tr("zoom_in"))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            if not self.btn_minus.geometry().contains(pos) and not self.btn_plus.geometry().contains(pos):
                self.start_editing()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def start_editing(self):
        txt = self.label.text()
        digits = "".join([c for c in txt if c.isdigit() or c == '.'])
        self.edit.setText(digits if digits else "100")
        self._is_editing = True
        self.stack_layout.setCurrentWidget(self.edit)
        self.edit.setFocus()
        self.edit.selectAll()

    def commit_zoom(self):
        if not self._is_editing:
            return
        self._is_editing = False
        val_str = self.edit.text().replace("%", "").strip()
        try:
            val = float(val_str)
            val = max(10.0, min(1000.0, val))
            zoom_level = val / 100.0
            if tab_doc := self.main_window.get_current_tab_doc():
                tab_doc.apply_zoom(zoom_level)
            else:
                self.label.setText(f" {LanguageManager.tr('percent_format', val=int(val))} ")
        except (ValueError, Exception):
            pass
        self.stack_layout.setCurrentWidget(self.label)

    def on_editing_finished(self):
        if self._is_editing:
            self.commit_zoom()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._is_editing = False
            self.stack_layout.setCurrentWidget(self.label)
            return
        super().keyPressEvent(event)


# --- 12. ANA UYGULAMA ---
class ModernPDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_lang = settings.value("language", "tr")
        LanguageManager.set_language(saved_lang)

        self.setWindowTitle(LanguageManager.tr("app_title"))
        self.app_icon = ModernIconFactory.icon_app()
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(800, 600)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        self.setAcceptDrops(True)
        self.current_tool = 'select'
        self.selection_shape_mode = 'rect'
        self.new_doc_counter = 0

        self.tab_widget = ModernTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        self.floating_hud = FloatingHUDPreview()
        self.search_bar = ModernSearchBar(self)
        self.fullscreen_toolbar = FullscreenSlideToolbar(self)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self)

        # --- V3 SİSTEM YÖNETİCİLERİ ---
        self.closed_tabs_history = []
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_watched_file_changed)
        self.speech_engine = AuraSpeechEngine(self)
        self.speech_engine.state_changed.connect(self._on_speech_state_changed)

        self._init_popups()
        self._init_docks()
        self._init_toolbar()
        self._init_shortcuts()
        self.apply_theme(settings.value("app_theme", "gray"))
        self.retranslate_ui()
        self.update_viewport_cursor()

        # Oturumu Geri Yükle
        QTimer.singleShot(250, self.restore_previous_session)

        # Otomatik Güncelleme Denetimi (Başlangıç ve Periyodik Kontrol)
        QTimer.singleShot(3500, self.check_updates_background)
        self._periodic_update_timer = QTimer(self)
        self._periodic_update_timer.setInterval(4 * 3600 * 1000)  # Her 4 saatte bir kontrol
        self._periodic_update_timer.timeout.connect(self.check_updates_background)
        self._periodic_update_timer.start()

    def get_current_tab_doc(self) -> Optional[PDFTabDocument]:
        if not hasattr(self, 'tab_widget') or self.tab_widget is None:
            return None
        curr = self.tab_widget.currentWidget()
        return curr if isinstance(curr, PDFTabDocument) else None

    def _init_shortcuts(self):
        # Statik global kısayollar
        QShortcut(QKeySequence("Escape"), self, activated=self.exit_to_select_mode)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=lambda: self.show_new_page_dialog(force_new_doc=True))
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_pdf)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.toggle_search_bar)
        QShortcut(QKeySequence("F3"), self, activated=self.find_next)
        QShortcut(QKeySequence("Shift+F3"), self, activated=self.find_prev)
        QShortcut(QKeySequence("Delete"), self, activated=self.delete_selected_items)
        QShortcut(QKeySequence("Backspace"), self, activated=self.delete_selected_items)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.toggle_toolbar_visibility)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_pdf)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.print_pdf)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self.close_tab(self.tab_widget.currentIndex()))

        # V3 Kısayolları (Görünüm Geçmişi, Sekme Kurtarma, Seslendirme, Özellikler, Sığdırma)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.nav_back)
        QShortcut(QKeySequence("Alt+Right"), self, activated=self.nav_forward)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self.reopen_last_closed_tab)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.fit_to_page)
        QShortcut(QKeySequence("Ctrl+2"), self, activated=self.fit_to_width)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.open_document_properties_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+U"), self, activated=self.toggle_read_aloud)
        QShortcut(QKeySequence("F1"), self, activated=self.open_shortcuts_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self.open_compress_dialog)

        # Dinamik özelleştirilebilir araç ve fare kısayolları
        self.reload_shortcuts()

    def reload_shortcuts(self):
        if hasattr(self, '_dynamic_tool_shortcuts'):
            for sc in self._dynamic_tool_shortcuts:
                sc.setEnabled(False)
                sc.deleteLater()
        self._dynamic_tool_shortcuts = []
        self._mouse_shortcuts = []

        shortcut_settings = QSettings("AuraPDF", "Shortcuts")
        defaults = {
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
            "fullscreen": "F11"
        }

        tool_actions = {
            "pen": lambda: self._activate_tool_if_no_focus('pen'),
            "highlighter": lambda: self._activate_tool_if_no_focus('highlighter'),
            "eraser": lambda: self._activate_tool_if_no_focus('eraser'),
            "select": lambda: self._activate_tool_if_no_focus('select'),
            "selection_tool": lambda: self._activate_tool_if_no_focus('selection_tool'),
            "text": lambda: self._activate_tool_if_no_focus('text'),
            "pointer": lambda: self._activate_tool_if_no_focus('pointer'),
            "undo": self.undo,
            "redo": self.redo,
            "zoom_in": self.zoom_in,
            "zoom_out": self.zoom_out,
            "fit_width": self.fit_to_width,
            "fullscreen": self.toggle_fullscreen
        }

        for action, default_seq in defaults.items():
            key_seq = shortcut_settings.value(f"key_{action}", default_seq)
            if not key_seq:
                continue
            handler = tool_actions.get(action)
            if not handler:
                continue

            if is_mouse_shortcut(key_seq):
                parsed = parse_mouse_shortcut(key_seq)
                if parsed:
                    btn, mods = parsed
                    self._mouse_shortcuts.append({
                        "action": action,
                        "shortcut_str": key_seq,
                        "button": btn,
                        "modifiers": mods,
                        "handler": handler
                    })
            else:
                try:
                    sc = QShortcut(QKeySequence(key_seq), self, activated=handler)
                    self._dynamic_tool_shortcuts.append(sc)
                except Exception:
                    pass

    def handle_mouse_shortcut(self, event) -> bool:
        """Kayıtlı fare kısayollarını kontrol eder ve eşleşirse ilgili eylemi çalıştırır."""
        if not hasattr(self, '_mouse_shortcuts') or not self._mouse_shortcuts:
            return False

        # Aktif modal bir pencere varsa (ör. Ayarlar diyaloğu) araya girme
        if QApplication.activeModalWidget() is not None:
            return False

        # Kullanıcı metin kutusuna yazı yazıyorsa araya girme
        from PyQt6.QtWidgets import QLineEdit, QTextEdit
        fw = QApplication.focusWidget()
        if fw and isinstance(fw, (QLineEdit, QTextEdit)):
            return False

        btn = event.button()
        clean_mods = clean_modifiers(event.modifiers())

        for sc in self._mouse_shortcuts:
            if sc["button"] == btn and sc["modifiers"] == clean_mods:
                handler = sc["handler"]
                if handler:
                    handler()
                return True
        return False

    def _activate_tool_if_no_focus(self, tool_name):
        from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit
        fw = QApplication.focusWidget()
        if fw and isinstance(fw, (QLineEdit, QTextEdit)) and fw.isVisible():
            return
        self.set_tool_state(tool_name)

    def toggle_search_bar(self):
        if not hasattr(self, 'search_bar'): return
        if self.search_bar.isVisible():
            if self.search_bar.txt_search.hasFocus():
                self.search_bar.hide_search()
            else:
                self.search_bar.txt_search.setFocus()
                self.search_bar.txt_search.selectAll()
        else:
            self.search_bar.show_search()

    def find_next(self):
        if hasattr(self, 'search_bar'):
            if not self.search_bar.isVisible():
                self.search_bar.show_search()
            else:
                self.search_bar.find_next()

    def find_prev(self):
        if hasattr(self, 'search_bar'):
            if not self.search_bar.isVisible():
                self.search_bar.show_search()
            else:
                self.search_bar.find_prev()

    def eventFilter(self, obj, event):
        # 1. Fare Kısayolları (Mouse Shortcuts) Kontrolü
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.handle_mouse_shortcut(event):
                event.accept()
                return True

        if self.isFullScreen() and hasattr(self, 'fullscreen_toolbar'):
            if event.type() == QEvent.Type.MouseMove:
                if hasattr(event, 'globalPosition'):
                    global_pos = event.globalPosition().toPoint()
                elif hasattr(event, 'globalPos'):
                    global_pos = event.globalPos()
                else:
                    global_pos = event.pos()
                win_pos = self.mapFromGlobal(global_pos)
                edge = getattr(self.fullscreen_toolbar, 'edge', getattr(self.fullscreen_toolbar, 'side', 'left'))
                near_edge = False
                if edge == 'left':
                    near_edge = (win_pos.x() <= 35 and 0 <= win_pos.y() <= self.height())
                elif edge == 'right':
                    near_edge = (win_pos.x() >= self.width() - 35 and 0 <= win_pos.y() <= self.height())
                elif edge == 'top':
                    near_edge = (win_pos.y() <= 35 and 0 <= win_pos.x() <= self.width())
                elif edge == 'bottom':
                    near_edge = (win_pos.y() >= self.height() - 35 and 0 <= win_pos.x() <= self.width())

                if near_edge:
                    if not self.fullscreen_toolbar.is_slid_in:
                        self.fullscreen_toolbar.slide_in()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'search_bar') and self.search_bar.isVisible():
            self.search_bar.reposition()
        if hasattr(self, 'fullscreen_toolbar') and self.isFullScreen():
            self.fullscreen_toolbar.reposition()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.toggle_fullscreen()
                event.accept()
                return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            was_fs = bool(event.oldState() & Qt.WindowState.WindowFullScreen)
            is_fs = self.isFullScreen()
            if was_fs and not is_fs:
                if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                    self.fullscreen_toolbar.hide_fullscreen_mode()
                if hasattr(self, 'btn_fullscreen') and self.btn_fullscreen:
                    self.btn_fullscreen.blockSignals(True)
                    self.btn_fullscreen.setChecked(False)
                    self.btn_fullscreen.blockSignals(False)
                self.tab_widget.tabBar().show()
                self.toolbar.show()
                sb = self.statusBar()
                if sb and getattr(self, '_statusbar_was_visible', True):
                    sb.show()
                if getattr(self, '_sidebar_was_visible', False):
                    self.thumbnails_dock.show()
        super().changeEvent(event)

    def exit_to_select_mode(self):
        if self.isFullScreen():
            self.toggle_fullscreen()
            return

        if hasattr(self, 'search_bar') and self.search_bar.isVisible():
            self.search_bar.hide_search()
            return
        tab_doc = self.get_current_tab_doc()
        if tab_doc:
            tab_doc.clear_selection()
            if tab_doc.active_text_item:
                if hasattr(tab_doc.active_text_item, 'toPlainText'):
                    if not tab_doc.active_text_item.toPlainText().strip():
                        tab_doc.scene.removeItem(tab_doc.active_text_item)
                    else:
                        tab_doc.active_text_item.clearFocus()
                elif hasattr(tab_doc.active_text_item, 'clearFocus'):
                    tab_doc.active_text_item.clearFocus()
                tab_doc.active_text_item = None
        self.set_tool_state('select')

    def delete_selected_items(self):
        if doc := self.get_current_tab_doc(): doc.delete_selected_items()

    def undo(self):
        if doc := self.get_current_tab_doc():
            doc.undo()
        self.update_undo_redo_state()

    def redo(self):
        if doc := self.get_current_tab_doc():
            doc.redo()
        self.update_undo_redo_state()

    def update_undo_redo_state(self):
        tab_doc = self.get_current_tab_doc()
        can_undo = bool(tab_doc and getattr(tab_doc, 'undo_stack', None) and len(tab_doc.undo_stack) > 0)
        can_redo = bool(tab_doc and getattr(tab_doc, 'redo_stack', None) and len(tab_doc.redo_stack) > 0)
        if hasattr(self, 'btn_undo'):
            self.btn_undo.setEnabled(can_undo)
        if hasattr(self, 'btn_redo'):
            self.btn_redo.setEnabled(can_redo)

    def toggle_toolbar_visibility(self): self.toolbar.setVisible(not self.toolbar.isVisible())

    def _init_docks(self):
        self.thumbnails_dock = ThumbnailsDock(self)
        self.thumbnails_dock.setObjectName("ThumbnailsDock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.thumbnails_dock)
        self.thumbnails_dock.hide()

    def _init_popups(self):
        self.cursor_popup = CursorPopup(self, on_mode_change=self.set_cursor_mode)
        self.hl_popup = ToolSettingsPopup(self, True, True, False, True, on_change_callback=self.update_viewport_cursor, tool_name="highlighter")
        self.pen_popup = ToolSettingsPopup(self, True, True, on_change_callback=self.update_viewport_cursor, tool_name="pen")
        self.eraser_popup = ToolSettingsPopup(self, False, False, True, False, on_change_callback=self.update_viewport_cursor, tool_name="eraser")
        self.text_popup = TextSettingsPopup(self, tool_name="text")
        self.selection_popup = SelectionSettingsPopup(self, on_mode_change=self.set_selection_mode)
        self.pointer_popup = PointerSettingsPopup(self, on_change_callback=self.update_viewport_cursor, tool_name="pointer")
        self.hl_ruler_popup = HighlighterRulerPopup(self)
        self.ruler_popup = RulerMeasurementPopup(self)
        self.measurement_unit = "cm"
        self.measurement_scale = 1.0

    def set_cursor_mode(self, mode):
        self.cursor_mode = mode
        if mode == 'select':
            self.btn_cursor.setIcon(ModernIconFactory.icon_cursor())
            self.set_tool_state('select')
        elif mode == 'pan':
            self.btn_cursor.setIcon(ModernIconFactory.icon_select_pan())
            self.set_tool_state('pan')
        if hasattr(self, 'cursor_popup'):
            self.cursor_popup.hide()
        self.update_viewport_cursor()

    def set_selection_mode(self, mode):
        if mode == 'select':
            self.set_cursor_mode('select')
            if hasattr(self, 'selection_popup'):
                self.selection_popup.close()
            return
        if mode == 'pan':
            self.set_cursor_mode('pan')
            if hasattr(self, 'selection_popup'):
                self.selection_popup.close()
            return
        if mode == 'ruler':
            self.set_tool_state('ruler')
            if hasattr(self, 'btn_selection'):
                self.btn_selection.setIcon(ModernIconFactory.icon_ruler())
                self.btn_selection.setChecked(True)
            self.update_viewport_cursor()
            return
        self.selection_shape_mode = mode
        if hasattr(self, 'btn_selection'):
            if mode == 'rect':
                self.btn_selection.setIcon(ModernIconFactory.icon_select_rect())
            elif mode == 'lasso':
                self.btn_selection.setIcon(ModernIconFactory.icon_select_lasso())
            elif mode == 'move':
                self.btn_selection.setIcon(ModernIconFactory.icon_select_move())
            self.btn_selection.setChecked(True)
        self.set_tool_state('selection_tool')
        if hasattr(self, 'selection_popup'):
            self.selection_popup.close()
        self.update_viewport_cursor()

    def handle_selection_button_click(self):
        if self.current_tool in ('selection_tool', 'ruler'):
            if hasattr(self, 'selection_popup') and self.selection_popup.isVisible():
                self.selection_popup.close()
            elif hasattr(self, 'selection_popup'):
                self.selection_popup.show_below(self.btn_selection)
        else:
            if getattr(self, 'selection_popup', None) and getattr(self.selection_popup, 'current_mode', None) == 'ruler':
                self.set_tool_state('ruler')
            else:
                self.set_tool_state('selection_tool')

    def _add_toolbar_widget(self, widget, name: str):
        widget.setObjectName(name)
        action = self.toolbar.addWidget(widget)
        action.setObjectName(name)
        return action

    def _add_toolbar_separator(self, name: str):
        sep = self.toolbar.addSeparator()
        sep.setObjectName(name)
        return sep

    def _init_toolbar(self):
        # 0. Ribbon Kategori Çubuğu (Toolbar'ın üstündeki seçenekler çubuğu: Çizimler, Dosya, Ekle, vb.)
        self.category_bar = ModernCategoryBar(self)
        self.setMenuWidget(self.category_bar)
        self.category_bar.categoryChanged.connect(self.set_active_category)

        self.toolbar = ReorderableToolBar("Modern Toolbar", self)
        self.toolbar.setObjectName("ModernToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.btn_contents = DraggableToolButton()
        self.btn_contents.setIcon(ModernIconFactory.icon_contents())
        self.btn_contents.clicked.connect(self.toggle_contents_panel)
        self._add_toolbar_widget(self.btn_contents, "btn_contents")

        self.btn_undo = DraggableToolButton()
        self.btn_undo.setIcon(ModernIconFactory.icon_undo())
        self.btn_undo.clicked.connect(self.undo)
        self._add_toolbar_widget(self.btn_undo, "btn_undo")

        self.btn_redo = DraggableToolButton()
        self.btn_redo.setIcon(ModernIconFactory.icon_redo())
        self.btn_redo.clicked.connect(self.redo)
        self._add_toolbar_widget(self.btn_redo, "btn_redo")

        self.btn_nav_back = DraggableToolButton()
        self.btn_nav_back.setIcon(ModernIconFactory.icon_nav_back())
        self.btn_nav_back.setToolTip(LanguageManager.tr("nav_back"))
        self.btn_nav_back.clicked.connect(self.nav_back)
        self._add_toolbar_widget(self.btn_nav_back, "btn_nav_back")

        self.btn_nav_forward = DraggableToolButton()
        self.btn_nav_forward.setIcon(ModernIconFactory.icon_nav_forward())
        self.btn_nav_forward.setToolTip(LanguageManager.tr("nav_forward"))
        self.btn_nav_forward.clicked.connect(self.nav_forward)
        self._add_toolbar_widget(self.btn_nav_forward, "btn_nav_forward")

        self._add_toolbar_separator("sep_1")

        self.cursor_mode = 'select'
        self.btn_cursor = DraggableToolButton()
        self.btn_cursor.setIcon(ModernIconFactory.icon_cursor())
        self.btn_cursor.setText(" ⌵")
        self.btn_cursor.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_cursor.setCheckable(True)
        self.btn_cursor.setChecked(True)
        self.btn_cursor.clicked.connect(lambda: self.handle_tool_click(self.cursor_mode, self.btn_cursor, self.cursor_popup))
        self.btn_cursor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_cursor.customContextMenuRequested.connect(lambda pos: self.cursor_popup.show_below(self.btn_cursor))
        self._add_toolbar_widget(self.btn_cursor, "btn_cursor")

        self.btn_selection = DraggableToolButton()
        self.btn_selection.setText(" ⌵")
        self.btn_selection.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_selection.setCheckable(True)
        self.set_selection_mode(self.selection_shape_mode)
        self.btn_selection.clicked.connect(self.handle_selection_button_click)
        self.btn_selection.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_selection.customContextMenuRequested.connect(lambda pos: self.selection_popup.show_below(self.btn_selection))
        self._add_toolbar_widget(self.btn_selection, "btn_selection")

        self.btn_ruler = DraggableToolButton()
        self.btn_ruler.setObjectName("btn_ruler")
        self.btn_ruler.setIcon(ModernIconFactory.icon_ruler())
        self.btn_ruler.setText(" " + LanguageManager.tr("ruler_btn"))
        self.btn_ruler.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_ruler.setCheckable(True)
        self.btn_ruler.setToolTip(LanguageManager.tr("ruler_tool_tip"))
        self.btn_ruler.clicked.connect(self.handle_ruler_click)
        self.btn_ruler.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_ruler.customContextMenuRequested.connect(lambda pos: self.ruler_popup.show_below(self.btn_ruler))
        self._add_toolbar_widget(self.btn_ruler, "btn_ruler")

        self.btn_hl = DraggableToolButton()
        self.btn_hl.setIcon(ModernIconFactory.icon_highlighter())
        self.btn_hl.setText(" ⌵")
        self.btn_hl.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_hl.setCheckable(True)
        self.btn_hl.setChecked(False)
        self.btn_hl.clicked.connect(lambda: self.handle_tool_click('highlighter', self.btn_hl, self.hl_popup))
        self._add_toolbar_widget(self.btn_hl, "btn_hl")

        self.btn_pen = DraggableToolButton()
        self.btn_pen.setIcon(ModernIconFactory.icon_pen())
        self.btn_pen.setText(" ⌵")
        self.btn_pen.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_pen.setCheckable(True)
        self.btn_pen.clicked.connect(lambda: self.handle_tool_click('pen', self.btn_pen, self.pen_popup))
        self._add_toolbar_widget(self.btn_pen, "btn_pen")

        self.btn_text = DraggableToolButton()
        self.btn_text.setIcon(ModernIconFactory.icon_text_box())
        self.btn_text.setText(" ⌵")
        self.btn_text.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_text.setCheckable(True)
        self.btn_text.clicked.connect(lambda: self.handle_tool_click('text', self.btn_text, self.text_popup))
        self._add_toolbar_widget(self.btn_text, "btn_text")

        self.btn_insert = DraggableToolButton()
        self.btn_insert.setIcon(ModernIconFactory.icon_insert())
        self.btn_insert.setToolTip(LanguageManager.tr("insert_btn_tip"))
        self.btn_insert.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_insert.setStyleSheet("QToolButton::menu-indicator { image: none; }")

        insert_menu = QMenu(self.btn_insert)
        insert_menu.setStyleSheet("""
            QMenu {
                background-color: #1f1f23;
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 6px 4px;
            }
            QMenu::item {
                padding: 8px 22px 8px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                margin: 1px 4px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.1);
                margin: 4px 10px;
            }
        """)

        self.menu_insert_blank = None
        self.insert_blank_actions = []

        # 1. Voice recording
        act_voice_rec = insert_menu.addAction(ModernIconFactory.icon_menu_voice_recording(), "  " + LanguageManager.tr("insert_voice_recording"))
        act_voice_rec.triggered.connect(self.show_insert_audio_dialog)

        insert_menu.addSeparator()

        # 2. Image
        act_img = insert_menu.addAction(ModernIconFactory.icon_menu_image(), "  " + LanguageManager.tr("insert_image"))
        act_img.triggered.connect(lambda: self.show_insert_image_dialog(default_tab=0))

        # 3. Camera / Video
        act_camera = insert_menu.addAction(ModernIconFactory.icon_menu_camera(), "  " + LanguageManager.tr("insert_camera"))
        act_camera.triggered.connect(self.show_insert_video_dialog)

        # 4. Audio file
        act_audio_file = insert_menu.addAction(ModernIconFactory.icon_menu_audio(), "  " + LanguageManager.tr("insert_audio_file"))
        act_audio_file.triggered.connect(self.show_insert_audio_file_picker)

        # 5. GIF & Emoji
        act_drawing = insert_menu.addAction(ModernIconFactory.icon_menu_drawing(), "  " + LanguageManager.tr("insert_drawing"))
        act_drawing.triggered.connect(self.show_insert_emoji_dialog)

        # 6. Table
        act_table = insert_menu.addAction(ModernIconFactory.icon_menu_table(), "  " + LanguageManager.tr("insert_table"))
        act_table.triggered.connect(self.show_insert_table_dialog)

        self.act_voice_rec = act_voice_rec
        self.act_insert_img = act_img
        self.act_camera = act_camera
        self.act_audio_file = act_audio_file
        self.act_drawing = act_drawing
        self.act_insert_emoji = act_drawing
        self.act_insert_table = act_table

        self.btn_insert.setMenu(insert_menu)
        self._add_toolbar_widget(self.btn_insert, "btn_insert")

        self.btn_eraser = DraggableToolButton()
        self.btn_eraser.setIcon(ModernIconFactory.icon_eraser())
        self.btn_eraser.setText(" ⌵")
        self.btn_eraser.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_eraser.setCheckable(True)
        self.btn_eraser.clicked.connect(lambda: self.handle_tool_click('eraser', self.btn_eraser, self.eraser_popup))
        self._add_toolbar_widget(self.btn_eraser, "btn_eraser")

        self.btn_pointer = DraggableToolButton()
        self.btn_pointer.setIcon(ModernIconFactory.icon_pointer())
        self.btn_pointer.setText(" ⌵")
        self.btn_pointer.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_pointer.setCheckable(True)
        self.btn_pointer.clicked.connect(lambda: self.handle_tool_click('pointer', self.btn_pointer, self.pointer_popup))
        self._add_toolbar_widget(self.btn_pointer, "btn_pointer")

        self._add_toolbar_separator("sep_2")

        self.lbl_zoom = EditableZoomWidget(self)
        self._add_toolbar_widget(self.lbl_zoom, "lbl_zoom")

        self.btn_fit_page = DraggableToolButton()
        self.btn_fit_page.setObjectName("btn_fit_page")
        self.btn_fit_page.setIcon(ModernIconFactory.icon_fit_page())
        self.btn_fit_page.setToolTip(LanguageManager.tr("fit_to_page"))
        self.btn_fit_page.clicked.connect(self.fit_to_page)
        self._add_toolbar_widget(self.btn_fit_page, "btn_fit_page")

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._add_toolbar_widget(spacer_left, "spacer_left")

        page_widget = QWidget()
        page_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        page_box = QHBoxLayout(page_widget)
        page_box.setContentsMargins(0,0,0,0)
        page_box.setSpacing(4)
        self.txt_page = QLineEdit()
        self.txt_page.setObjectName("PageInput")
        self.txt_page.setFixedWidth(36)
        self.txt_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_page.setText("0")
        self.txt_page.setValidator(QIntValidator(1, 9999, self))
        self.txt_page.returnPressed.connect(self.jump_to_page)
        page_box.addWidget(self.txt_page)
        self.lbl_total = QLabel(LanguageManager.tr("page_of", total=0))
        page_box.addWidget(self.lbl_total)
        self._add_toolbar_widget(page_widget, "page_widget")

        self.btn_rotate = DraggableToolButton()
        self.btn_rotate.setIcon(ModernIconFactory.icon_rotate())
        self.btn_rotate.clicked.connect(self.rotate_all_pages)
        self._add_toolbar_widget(self.btn_rotate, "btn_rotate")

        # Sayfa Görünümü Butonu (Tekli / İkili Sayfa Görünümü - Sayfayı çevirmenin hemen sağında)
        self.btn_view_mode = DraggableToolButton()
        self.btn_view_mode.setObjectName("btn_view_mode")
        self.btn_view_mode.setIcon(ModernIconFactory.icon_view_single())
        self.btn_view_mode.setToolTip(LanguageManager.tr("view_mode_btn_tip"))
        self.btn_view_mode.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.btn_view_mode.clicked.connect(self.toggle_page_view_mode)

        view_menu = QMenu(self.btn_view_mode)
        view_menu.setStyleSheet("""
            QMenu { background-color: #242424; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #3b82f6; }
        """)
        self.act_view_single = view_menu.addAction(ModernIconFactory.icon_view_single(), LanguageManager.tr("view_mode_single"))
        self.act_view_single.triggered.connect(lambda: self.set_page_view_mode("single"))
        self.act_view_double = view_menu.addAction(ModernIconFactory.icon_view_double(), LanguageManager.tr("view_mode_double"))
        self.act_view_double.triggered.connect(lambda: self.set_page_view_mode("double"))
        self.btn_view_mode.setMenu(view_menu)
        self._add_toolbar_widget(self.btn_view_mode, "btn_view_mode")

        # Okuma Modu Butonu (Normal / Gece / Sepia)
        self.btn_reading_mode = DraggableToolButton()
        self.btn_reading_mode.setObjectName("btn_reading_mode")
        self.btn_reading_mode.setIcon(ModernIconFactory.icon_reading_mode())
        self.btn_reading_mode.setToolTip(LanguageManager.tr("reading_mode"))
        self.btn_reading_mode.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        read_menu = QMenu(self.btn_reading_mode)
        read_menu.setStyleSheet("""
            QMenu { background-color: #242424; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #3b82f6; }
        """)
        self.act_read_light = read_menu.addAction(LanguageManager.tr("reading_mode_light"))
        self.act_read_light.triggered.connect(lambda: self.set_reading_color_mode("normal"))
        self.act_read_dark = read_menu.addAction(LanguageManager.tr("reading_mode_dark"))
        self.act_read_dark.triggered.connect(lambda: self.set_reading_color_mode("dark"))
        self.act_read_sepia = read_menu.addAction(LanguageManager.tr("reading_mode_sepia"))
        self.act_read_sepia.triggered.connect(lambda: self.set_reading_color_mode("sepia"))
        self.btn_reading_mode.setMenu(read_menu)
        self._add_toolbar_widget(self.btn_reading_mode, "btn_reading_mode")

        # Sesli Okuma Butonu (Text-to-Speech)
        self.btn_speech = DraggableToolButton()
        self.btn_speech.setObjectName("btn_speech")
        self.btn_speech.setIcon(ModernIconFactory.icon_speech())
        self.btn_speech.setCheckable(True)
        self.btn_speech.setToolTip(LanguageManager.tr("speech_read_aloud"))
        self.btn_speech.clicked.connect(self.toggle_read_aloud)
        self._add_toolbar_widget(self.btn_speech, "btn_speech")

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._add_toolbar_widget(spacer_right, "spacer_right")

        self.btn_search = DraggableToolButton()
        self.btn_search.setIcon(ModernIconFactory.icon_search())
        self.btn_search.clicked.connect(self.toggle_search_bar)
        self._add_toolbar_widget(self.btn_search, "btn_search")

        self._add_toolbar_separator("sep_3")

        self.btn_print = DraggableToolButton()
        self.btn_print.setIcon(ModernIconFactory.icon_print())
        self.btn_print.clicked.connect(self.print_pdf)
        self._add_toolbar_widget(self.btn_print, "btn_print")

        self.btn_save = DraggableToolButton()
        self.btn_save.setIcon(ModernIconFactory.icon_save())
        self.btn_save.clicked.connect(self.save_pdf)
        self._add_toolbar_widget(self.btn_save, "btn_save")

        self.btn_open = DraggableToolButton()
        self.btn_open.setText(LanguageManager.tr("open"))
        self.btn_open.setToolTip(LanguageManager.tr("open"))
        self.btn_open.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.btn_open.clicked.connect(self.open_pdf)

        open_menu = QMenu(self.btn_open)
        open_menu.setStyleSheet("""
            QMenu { background-color: #242424; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #3b82f6; }
        """)
        self.act_open_direct = open_menu.addAction(LanguageManager.tr("open") + " (Ctrl+O)")
        self.act_open_direct.triggered.connect(self.open_pdf)

        self.recent_files_menu = open_menu.addMenu(LanguageManager.tr("recent_files"))
        self.update_recent_files_menu()

        self.act_reopen_tab = open_menu.addAction(LanguageManager.tr("reopen_closed_tab") + " (Ctrl+Shift+T)")
        self.act_reopen_tab.triggered.connect(self.reopen_last_closed_tab)

        open_menu.addSeparator()
        self.act_doc_props = open_menu.addAction(ModernIconFactory.icon_doc_properties(), LanguageManager.tr("doc_properties") + " (Ctrl+D)")
        self.act_doc_props.triggered.connect(self.open_document_properties_dialog)

        self.btn_open.setMenu(open_menu)
        self._add_toolbar_widget(self.btn_open, "btn_open")

        self.btn_toolbox = DraggableToolButton()
        self.btn_toolbox.setIcon(ModernIconFactory.icon_toolbox())
        self.btn_toolbox.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_toolbox.setText("")
        self.btn_toolbox.setToolTip(LanguageManager.tr("tools_tooltip"))
        self.btn_toolbox.clicked.connect(self.show_toolbox_menu)
        self._add_toolbar_widget(self.btn_toolbox, "btn_toolbox")

        self.btn_settings = DraggableToolButton()
        self.btn_settings.setIcon(ModernIconFactory.icon_settings())
        self.btn_settings.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_settings.setText("")
        self.btn_settings.setToolTip(LanguageManager.tr("settings_tooltip"))
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        self.btn_settings.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_settings.customContextMenuRequested.connect(self.show_settings_context_menu)
        self._add_toolbar_widget(self.btn_settings, "btn_settings")

        self.btn_fullscreen = DraggableToolButton()
        self.btn_fullscreen.setObjectName("btn_fullscreen")
        self.btn_fullscreen.setIcon(ModernIconFactory.icon_fullscreen())
        self.btn_fullscreen.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_fullscreen.setText("")
        self.btn_fullscreen.setToolTip(LanguageManager.tr("tb_item_fullscreen"))
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self._add_toolbar_widget(self.btn_fullscreen, "btn_fullscreen")

        # --- KATEGORİYE ÖZEL EK ARAÇLAR & BUTONLAR ---
        # 1. Dosya Kategorisi Butonları
        self.btn_save_as = DraggableToolButton()
        self.btn_save_as.setObjectName("btn_save_as")
        self.btn_save_as.setIcon(ModernIconFactory.icon_save())
        self.btn_save_as.setText(" " + LanguageManager.tr("save_as"))
        self.btn_save_as.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_save_as.setToolTip(LanguageManager.tr("save_as") + " (Ctrl+Shift+S)")
        self.btn_save_as.clicked.connect(self.save_pdf)
        self._add_toolbar_widget(self.btn_save_as, "btn_save_as")

        self.btn_doc_props = DraggableToolButton()
        self.btn_doc_props.setObjectName("btn_doc_props")
        self.btn_doc_props.setIcon(ModernIconFactory.icon_doc_properties())
        self.btn_doc_props.setText(" " + LanguageManager.tr("doc_properties"))
        self.btn_doc_props.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_doc_props.setToolTip(LanguageManager.tr("doc_properties") + " (Ctrl+D)")
        self.btn_doc_props.clicked.connect(self.open_document_properties_dialog)
        self._add_toolbar_widget(self.btn_doc_props, "btn_doc_props")

        self.btn_new_tab = DraggableToolButton()
        self.btn_new_tab.setObjectName("btn_new_tab")
        self.btn_new_tab.setIcon(ModernIconFactory.icon_new_document())
        self.btn_new_tab.setText(" " + LanguageManager.tr("new_document"))
        self.btn_new_tab.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_new_tab.setToolTip(LanguageManager.tr("new_document") + " (Ctrl+N)")
        self.btn_new_tab.clicked.connect(lambda: self.show_new_page_dialog(force_new_doc=True))
        self._add_toolbar_widget(self.btn_new_tab, "btn_new_tab")

        self.btn_close_tab = DraggableToolButton()
        self.btn_close_tab.setObjectName("btn_close_tab")
        self.btn_close_tab.setIcon(ModernIconFactory.icon_close())
        self.btn_close_tab.setText(" " + LanguageManager.tr("close_tab"))
        self.btn_close_tab.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_close_tab.setToolTip(LanguageManager.tr("close_tab") + " (Ctrl+W)")
        self.btn_close_tab.clicked.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        self._add_toolbar_widget(self.btn_close_tab, "btn_close_tab")

        # 2. Ekle Kategorisi Doğrudan Butonları
        self.btn_insert_img = DraggableToolButton()
        self.btn_insert_img.setObjectName("btn_insert_img")
        self.btn_insert_img.setIcon(ModernIconFactory.icon_image())
        self.btn_insert_img.setText(" " + LanguageManager.tr("insert_image").replace("...", ""))
        self.btn_insert_img.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_img.setToolTip(LanguageManager.tr("insert_image"))
        self.btn_insert_img.clicked.connect(lambda: self.show_insert_image_dialog(default_tab=0))
        self._add_toolbar_widget(self.btn_insert_img, "btn_insert_img")

        self.btn_insert_voice = DraggableToolButton()
        self.btn_insert_voice.setObjectName("btn_insert_voice")
        self.btn_insert_voice.setIcon(ModernIconFactory.icon_menu_voice_recording())
        self.btn_insert_voice.setText(" " + LanguageManager.tr("insert_voice_recording").replace("...", ""))
        self.btn_insert_voice.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_voice.setToolTip(LanguageManager.tr("insert_voice_recording"))
        self.btn_insert_voice.clicked.connect(self.show_insert_audio_dialog)
        self._add_toolbar_widget(self.btn_insert_voice, "btn_insert_voice")

        self.btn_insert_camera = DraggableToolButton()
        self.btn_insert_camera.setObjectName("btn_insert_camera")
        self.btn_insert_camera.setIcon(ModernIconFactory.icon_menu_camera())
        self.btn_insert_camera.setText(" " + LanguageManager.tr("insert_camera").replace("...", ""))
        self.btn_insert_camera.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_camera.setToolTip(LanguageManager.tr("insert_camera"))
        self.btn_insert_camera.clicked.connect(self.show_insert_video_dialog)
        self._add_toolbar_widget(self.btn_insert_camera, "btn_insert_camera")

        self.btn_insert_audio = DraggableToolButton()
        self.btn_insert_audio.setObjectName("btn_insert_audio")
        self.btn_insert_audio.setIcon(ModernIconFactory.icon_menu_audio())
        self.btn_insert_audio.setText(" " + LanguageManager.tr("insert_audio_file").replace("...", ""))
        self.btn_insert_audio.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_audio.setToolTip(LanguageManager.tr("insert_audio_file"))
        self.btn_insert_audio.clicked.connect(self.show_insert_audio_file_picker)
        self._add_toolbar_widget(self.btn_insert_audio, "btn_insert_audio")

        self.btn_insert_emoji = DraggableToolButton()
        self.btn_insert_emoji.setObjectName("btn_insert_emoji")
        self.btn_insert_emoji.setIcon(ModernIconFactory.icon_menu_drawing())
        self.btn_insert_emoji.setText(" " + LanguageManager.tr("insert_drawing").replace("...", ""))
        self.btn_insert_emoji.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_emoji.setToolTip(LanguageManager.tr("insert_drawing"))
        self.btn_insert_emoji.clicked.connect(self.show_insert_emoji_dialog)
        self._add_toolbar_widget(self.btn_insert_emoji, "btn_insert_emoji")

        self.btn_insert_table = DraggableToolButton()
        self.btn_insert_table.setObjectName("btn_insert_table")
        self.btn_insert_table.setIcon(ModernIconFactory.icon_table())
        self.btn_insert_table.setText(" " + LanguageManager.tr("insert_table").replace("...", ""))
        self.btn_insert_table.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_table.setToolTip(LanguageManager.tr("insert_table"))
        self.btn_insert_table.clicked.connect(self.show_insert_table_dialog)
        self._add_toolbar_widget(self.btn_insert_table, "btn_insert_table")

        self.btn_insert_blank = DraggableToolButton()
        self.btn_insert_blank.setObjectName("btn_insert_blank")
        self.btn_insert_blank.setIcon(ModernIconFactory.icon_add_page())
        self.btn_insert_blank.setText(" " + LanguageManager.tr("sidebar_btn_add_blank"))
        self.btn_insert_blank.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_insert_blank.setToolTip(LanguageManager.tr("sidebar_btn_add_blank"))
        self.btn_insert_blank.clicked.connect(self.show_new_page_dialog)
        self._add_toolbar_widget(self.btn_insert_blank, "btn_insert_blank")

        # 3. Araçlar (Tools) Kategorisi Doğrudan Butonları
        self.btn_tool_organize = DraggableToolButton()
        self.btn_tool_organize.setObjectName("btn_tool_organize")
        self.btn_tool_organize.setIcon(ModernIconFactory.icon_organize())
        self.btn_tool_organize.setText(" " + LanguageManager.tr("reorder_action").replace("...", ""))
        self.btn_tool_organize.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_organize.setToolTip(LanguageManager.tr("reorder_action"))
        self.btn_tool_organize.clicked.connect(lambda: self.open_organize_dialog(0))
        self._add_toolbar_widget(self.btn_tool_organize, "btn_tool_organize")

        self.btn_tool_merge = DraggableToolButton()
        self.btn_tool_merge.setObjectName("btn_tool_merge")
        self.btn_tool_merge.setIcon(ModernIconFactory.icon_merge())
        self.btn_tool_merge.setText(" " + LanguageManager.tr("merge_action").replace("...", ""))
        self.btn_tool_merge.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_merge.setToolTip(LanguageManager.tr("merge_action"))
        self.btn_tool_merge.clicked.connect(self.open_merge_dialog)
        self._add_toolbar_widget(self.btn_tool_merge, "btn_tool_merge")

        self.btn_tool_split = DraggableToolButton()
        self.btn_tool_split.setObjectName("btn_tool_split")
        self.btn_tool_split.setIcon(ModernIconFactory.icon_split())
        self.btn_tool_split.setText(" " + LanguageManager.tr("split_action").replace("...", ""))
        self.btn_tool_split.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_split.setToolTip(LanguageManager.tr("split_action"))
        self.btn_tool_split.clicked.connect(self.open_split_dialog)
        self._add_toolbar_widget(self.btn_tool_split, "btn_tool_split")

        self.btn_tool_word = DraggableToolButton()
        self.btn_tool_word.setObjectName("btn_tool_word")
        self.btn_tool_word.setIcon(ModernIconFactory.icon_word())
        self.btn_tool_word.setText(" Word")
        self.btn_tool_word.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_word.setToolTip(LanguageManager.tr("word_action"))
        self.btn_tool_word.clicked.connect(self.open_word_dialog)
        self._add_toolbar_widget(self.btn_tool_word, "btn_tool_word")

        self.btn_tool_excel = DraggableToolButton()
        self.btn_tool_excel.setObjectName("btn_tool_excel")
        self.btn_tool_excel.setIcon(ModernIconFactory.icon_excel())
        self.btn_tool_excel.setText(" Excel")
        self.btn_tool_excel.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_excel.setToolTip(LanguageManager.tr("excel_action"))
        self.btn_tool_excel.clicked.connect(self.open_excel_dialog)
        self._add_toolbar_widget(self.btn_tool_excel, "btn_tool_excel")

        self.btn_tool_ocr = DraggableToolButton()
        self.btn_tool_ocr.setObjectName("btn_tool_ocr")
        self.btn_tool_ocr.setIcon(ModernIconFactory.icon_ocr())
        self.btn_tool_ocr.setText(" OCR")
        self.btn_tool_ocr.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_ocr.setToolTip(LanguageManager.tr("ocr_action"))
        self.btn_tool_ocr.clicked.connect(self.open_pdf_ocr_dialog)
        self._add_toolbar_widget(self.btn_tool_ocr, "btn_tool_ocr")

        self.btn_tool_editor = DraggableToolButton()
        self.btn_tool_editor.setObjectName("btn_tool_editor")
        self.btn_tool_editor.setIcon(ModernIconFactory.icon_edit_content())
        self.btn_tool_editor.setText(" " + LanguageManager.tr("content_editor_action").replace("...", ""))
        self.btn_tool_editor.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_editor.setToolTip(LanguageManager.tr("content_editor_action"))
        self.btn_tool_editor.clicked.connect(self.open_pdf_content_editor)
        self._add_toolbar_widget(self.btn_tool_editor, "btn_tool_editor")

        self.btn_tool_sign = DraggableToolButton()
        self.btn_tool_sign.setObjectName("btn_tool_sign")
        self.btn_tool_sign.setIcon(ModernIconFactory.icon_sign())
        self.btn_tool_sign.setText(" " + LanguageManager.tr("sign_action").replace("...", ""))
        self.btn_tool_sign.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_sign.setToolTip(LanguageManager.tr("sign_action"))
        self.btn_tool_sign.clicked.connect(self.open_signature_dialog)
        self._add_toolbar_widget(self.btn_tool_sign, "btn_tool_sign")

        self.btn_tool_compare = DraggableToolButton()
        self.btn_tool_compare.setObjectName("btn_tool_compare")
        self.btn_tool_compare.setIcon(ModernIconFactory.icon_compare())
        self.btn_tool_compare.setText(" " + LanguageManager.tr("compare_action").replace("...", ""))
        self.btn_tool_compare.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_compare.setToolTip(LanguageManager.tr("compare_action"))
        self.btn_tool_compare.clicked.connect(self.open_pdf_compare_dialog)
        self._add_toolbar_widget(self.btn_tool_compare, "btn_tool_compare")

        self.btn_tool_redact = DraggableToolButton()
        self.btn_tool_redact.setObjectName("btn_tool_redact")
        self.btn_tool_redact.setIcon(ModernIconFactory.icon_redact())
        self.btn_tool_redact.setText(" " + LanguageManager.tr("redact_action").replace("...", ""))
        self.btn_tool_redact.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_redact.setToolTip(LanguageManager.tr("redact_action"))
        self.btn_tool_redact.clicked.connect(self.open_pdf_redaction_dialog)
        self._add_toolbar_widget(self.btn_tool_redact, "btn_tool_redact")

        self.btn_tool_encrypt = DraggableToolButton()
        self.btn_tool_encrypt.setObjectName("btn_tool_encrypt")
        self.btn_tool_encrypt.setIcon(ModernIconFactory.icon_lock())
        self.btn_tool_encrypt.setText(" " + LanguageManager.tr("encrypt_action").replace("...", ""))
        self.btn_tool_encrypt.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_encrypt.setToolTip(LanguageManager.tr("encrypt_action"))
        self.btn_tool_encrypt.clicked.connect(self.open_encrypt_dialog)
        self._add_toolbar_widget(self.btn_tool_encrypt, "btn_tool_encrypt")

        self.btn_tool_compress = DraggableToolButton()
        self.btn_tool_compress.setObjectName("btn_tool_compress")
        self.btn_tool_compress.setIcon(ModernIconFactory.icon_compress())
        self.btn_tool_compress.setText(" " + LanguageManager.tr("compress_action").replace("...", ""))
        self.btn_tool_compress.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tool_compress.setToolTip(LanguageManager.tr("compress_action"))
        self.btn_tool_compress.clicked.connect(self.open_compress_dialog)
        self._add_toolbar_widget(self.btn_tool_compress, "btn_tool_compress")

        # 4. Kategori Ayırıcıları (Separators)
        self._add_toolbar_separator("sep_file_1")
        self._add_toolbar_separator("sep_file_2")
        self._add_toolbar_separator("sep_home_1")
        self._add_toolbar_separator("sep_home_2")
        self._add_toolbar_separator("sep_home_3")
        self._add_toolbar_separator("sep_draw_1")
        self._add_toolbar_separator("sep_draw_2")
        self._add_toolbar_separator("sep_draw_3")
        self._add_toolbar_separator("sep_insert_1")
        self._add_toolbar_separator("sep_view_1")
        self._add_toolbar_separator("sep_view_2")
        self._add_toolbar_separator("sep_view_3")
        self._add_toolbar_separator("sep_tool_1")
        self._add_toolbar_separator("sep_tool_2")
        self._add_toolbar_separator("sep_tool_3")

        self.restore_toolbar_order()
        self.update_undo_redo_state()

        # Kaydedilmiş kategori sekmesini geri yükle ve toolbar'ı filtrele
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_cat = settings.value("active_toolbar_category", "cat_home")
        self.set_active_category(saved_cat)

    def _apply_action_order(self, order_list):
        """Toolbar aksiyonlarını belirtilen sıralamaya göre yeniden dizer."""
        if not hasattr(self, 'toolbar'):
            return
        current_actions = self.toolbar.actions()
        actions_map = {}
        for act in current_actions:
            name = act.objectName()
            if not name:
                w = self.toolbar.widgetForAction(act)
                if w and w.objectName():
                    name = w.objectName()
            if name:
                actions_map[name] = act

        new_order = [actions_map[name] for name in order_list if name in actions_map]
        for act in current_actions:
            if act not in new_order:
                new_order.append(act)

        if new_order != current_actions:
            for act in current_actions:
                self.toolbar.removeAction(act)
            for act in new_order:
                self.toolbar.addAction(act)

    def set_active_category(self, category: str):
        """Toolbar'ın üstündeki kategori çubuğundan seçilen kategoriye göre toolbar butonlarını filtreler ve sıralar."""
        if category not in CATEGORY_ITEMS:
            category = "cat_home"
        self.active_category = category
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("active_toolbar_category", category)

        if hasattr(self, 'category_bar') and self.category_bar:
            self.category_bar.set_active_category(category, trigger_signal=False)

        if category == "cat_all":
            from src.ui.dialogs.settings_dialog import build_full_toolbar_order, DEFAULT_TOOLBAR_LAYOUT
            raw = settings.value("toolbar_order", None)
            if not raw:
                final_order = list(DEFAULT_TOOLBAR_LAYOUT)
            else:
                import json
                try:
                    saved_order = json.loads(raw) if isinstance(raw, str) else list(raw)
                except Exception:
                    saved_order = []
                final_order = build_full_toolbar_order(saved_order)
            self._apply_action_order(final_order)

            default_set = set(DEFAULT_TOOLBAR_LAYOUT)
            for act in self.toolbar.actions():
                name = act.objectName()
                if not name:
                    w = self.toolbar.widgetForAction(act)
                    if w and w.objectName():
                        name = w.objectName()
                act.setVisible(bool(name and (name in default_set or name in ("sep_1", "sep_2", "sep_3", "spacer_left", "spacer_right"))))
        else:
            cat_order = CATEGORY_ITEMS.get(category, [])
            self._apply_action_order(cat_order)
            allowed = set(cat_order)
            for act in self.toolbar.actions():
                name = act.objectName()
                if not name:
                    w = self.toolbar.widgetForAction(act)
                    if w and w.objectName():
                        name = w.objectName()
                act.setVisible(bool(name and name in allowed))

        if not self.toolbar.isVisible() and getattr(self, 'category_bar', None) and not self.category_bar._is_collapsed:
            self.toolbar.show()

    def toggle_fullscreen(self, checked=None):
        going_fullscreen = not self.isFullScreen()

        if hasattr(self, 'btn_fullscreen') and self.btn_fullscreen:
            self.btn_fullscreen.blockSignals(True)
            self.btn_fullscreen.setChecked(going_fullscreen)
            self.btn_fullscreen.blockSignals(False)

        if going_fullscreen:
            # 1. Mevcut pencere durumunu ve geometrisini kaydet
            self._was_maximized = self.isMaximized()
            self._normal_geometry = self.saveGeometry()
            self._normal_state = self.saveState()

            # 2. Yan panel ve durum çubuğu durumlarını kaydet ve gizle
            self._sidebar_was_visible = self.thumbnails_dock.isVisible()
            if self._sidebar_was_visible:
                self.thumbnails_dock.hide()

            sb = self.statusBar()
            if sb:
                self._statusbar_was_visible = sb.isVisible()
                sb.hide()
            else:
                self._statusbar_was_visible = False

            # 3. Sekme çubuğunu, kategori çubuğunu ve ana araç çubuğunu gizle
            self.tab_widget.tabBar().hide()
            self.toolbar.hide()
            if hasattr(self, 'category_bar') and self.category_bar:
                self.category_bar.hide()

            # 4. Tam ekrana geç
            self.showFullScreen()

            # 5. Tam ekran kayar araç çubuğunu aç
            if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                self.fullscreen_toolbar.show_fullscreen_mode()

            self.show_osd_message("Tam ekrandan çıkmak için F11 veya Esc tuşuna basın")
        else:
            # 1. Tam ekran kayar araç çubuğunu gizle
            if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                self.fullscreen_toolbar.hide_fullscreen_mode()

            # 2. Pencereyi önceki durumuna (büyütülmüş veya normal) döndür
            if getattr(self, '_was_maximized', False):
                self.setWindowState((self.windowState() & ~Qt.WindowState.WindowFullScreen) | Qt.WindowState.WindowMaximized)
                self.showMaximized()
            else:
                self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
                self.showNormal()
                if hasattr(self, "_normal_geometry") and self._normal_geometry:
                    self.restoreGeometry(self._normal_geometry)

            if hasattr(self, "_normal_state") and self._normal_state:
                self.restoreState(self._normal_state)

            # 3. Yan panel, sekme çubuğu, ana araç çubuğu ve durum çubuğunu geri yükle
            if getattr(self, '_sidebar_was_visible', False):
                self.thumbnails_dock.show()

            self.tab_widget.tabBar().show()
            self.toolbar.show()
            if hasattr(self, 'category_bar') and self.category_bar:
                self.category_bar.show()

            sb = self.statusBar()
            if sb and getattr(self, '_statusbar_was_visible', True):
                sb.show()

    def show_osd_message(self, text):
        from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
        
        if hasattr(self, "_osd_label") and self._osd_label:
            try:
                self._osd_label.deleteLater()
            except RuntimeError:
                pass
            
        lbl = QLabel(text, self)
        lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        lbl.adjustSize()
        x = (self.width() - lbl.width()) // 2
        y = 50
        lbl.move(x, y)
        lbl.show()
        
        self._osd_label = lbl
        
        effect = QGraphicsOpacityEffect(lbl)
        lbl.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        from PyQt6.QtCore import QSettings
        enable_anim = QSettings("AuraPDF", "PDFViewer").value("enable_animations", True, type=bool)
        anim.setDuration(1500 if enable_anim else 0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        QTimer.singleShot(2000, anim.start)
        def on_anim_finished():
            try:
                lbl.deleteLater()
            except RuntimeError:
                pass
            if getattr(self, "_osd_label", None) == lbl:
                self._osd_label = None
                
        anim.finished.connect(on_anim_finished)
        self._osd_anim = anim

    def show_language_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #242424;
                color: #f0f0f0;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px 8px 12px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #1a73e8;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #3c3c3c;
                margin: 4px 8px;
            }
        """)

        act_tr = menu.addAction(LanguageManager.tr("lang_tr"))
        act_tr.setCheckable(True)
        act_tr.setChecked(LanguageManager.current_lang == "tr")

        act_en = menu.addAction(LanguageManager.tr("lang_en"))
        act_en.setCheckable(True)
        act_en.setChecked(LanguageManager.current_lang == "en")

        act_tr.triggered.connect(lambda: self.change_language("tr"))
        act_en.triggered.connect(lambda: self.change_language("en"))

        target = getattr(self, 'btn_settings', self)
        point = target.mapToGlobal(QPoint(0, target.height() + 4))
        menu.exec(point)

    def show_settings_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242424; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; font-size: 13px; }
            QMenu::item:selected { background-color: #3b82f6; }
        """)
        act_settings = menu.addAction(ModernIconFactory.icon_settings(), LanguageManager.tr("settings_title"))
        act_settings.triggered.connect(lambda: self.open_settings_dialog())

        act_updates = menu.addAction(ModernIconFactory.icon_update(), LanguageManager.tr("updates_section_title"))
        act_updates.triggered.connect(lambda: self.open_settings_dialog(initial_tab="updates"))

        target = getattr(self, 'btn_settings', self)
        point = target.mapToGlobal(pos)
        menu.exec(point)

    def open_settings_dialog(self, initial_tab: Optional[str] = None):
        from src.ui.dialogs.settings_dialog import ModernSettingsDialog
        dlg = ModernSettingsDialog(self)
        if initial_tab == "updates" and hasattr(dlg, 'sidebar'):
            dlg.sidebar.setCurrentRow(7)
        dlg.exec()

    def check_updates_background(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        if not settings.value("auto_check_updates", True, type=bool):
            return

        freq = settings.value("update_frequency", "startup")
        import time
        now_epoch = int(time.time())
        last_epoch = int(settings.value("last_update_check_epoch", 0))

        if freq == "daily" and (now_epoch - last_epoch) < 86400:
            return
        elif freq == "weekly" and (now_epoch - last_epoch) < 604800:
            return

        from src.core.updater import UpdateChecker
        self._bg_updater = UpdateChecker(parent=self)
        self._bg_updater.check_finished.connect(self._on_bg_update_finished)
        self._bg_updater.start()

    def _on_bg_update_finished(self, update_info):
        if getattr(update_info, 'has_update', False):
            from src.ui.dialogs.update_dialog import UpdateDialog
            dlg = UpdateDialog(update_info, parent=self)
            dlg.exec()

    def apply_theme(self, theme_name: str = "gray"):
        if theme_name == "navy":
            theme_name = "gray"
        self.current_theme = theme_name
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("app_theme", theme_name)

        theme_specs = {
            "gray": {
                "main_bg": "#2b2d30", "main_text": "#f1f5f9", "tb_bg": "#35383c", "tb_border": "#222427",
                "btn_hover": "#42464b", "accent": "#60a5fa", "page_bg": "#42464b", "page_border": "#525860",
                "tab_bg": "#32353a", "tab_hover": "#3e4248", "tab_border": "#40444a", "tab_text": "#cbd5e1",
                "view_bg": "#222426"
            },
            "navy": {
                "main_bg": "#0f172a", "main_text": "#e2e8f0", "tb_bg": "#1e293b", "tb_border": "#0f172a",
                "btn_hover": "#334155", "accent": "#38bdf8", "page_bg": "#334155", "page_border": "#475569",
                "tab_bg": "#1e293b", "tab_hover": "#334155", "tab_border": "#334155", "tab_text": "#94a3b8",
                "view_bg": "#090d16"
            },
            "emerald": {
                "main_bg": "#091a14", "main_text": "#ecfdf5", "tb_bg": "#112a21", "tb_border": "#06120e",
                "btn_hover": "#183c2f", "accent": "#10b981", "page_bg": "#183c2f", "page_border": "#1a3d30",
                "tab_bg": "#112a21", "tab_hover": "#183c2f", "tab_border": "#1a3d30", "tab_text": "#a7f3d0",
                "view_bg": "#06120e"
            },
            "purple": {
                "main_bg": "#150d22", "main_text": "#faf5ff", "tb_bg": "#201435", "tb_border": "#0e0817",
                "btn_hover": "#2f1d4d", "accent": "#a855f7", "page_bg": "#2f1d4d", "page_border": "#321f52",
                "tab_bg": "#201435", "tab_hover": "#2f1d4d", "tab_border": "#321f52", "tab_text": "#d8b4fe",
                "view_bg": "#0e0817"
            },
            "crimson": {
                "main_bg": "#1d0b10", "main_text": "#fff1f2", "tb_bg": "#2d1118", "tb_border": "#13070a",
                "btn_hover": "#401923", "accent": "#f43f5e", "page_bg": "#401923", "page_border": "#441924",
                "tab_bg": "#2d1118", "tab_hover": "#401923", "tab_border": "#441924", "tab_text": "#fecdd3",
                "view_bg": "#13070a"
            },
            "nord": {
                "main_bg": "#181e29", "main_text": "#f0f6fc", "tb_bg": "#222b3a", "tb_border": "#11161e",
                "btn_hover": "#2f3b4f", "accent": "#38bdf8", "page_bg": "#2f3b4f", "page_border": "#313e54",
                "tab_bg": "#222b3a", "tab_hover": "#2f3b4f", "tab_border": "#313e54", "tab_text": "#94a3b8",
                "view_bg": "#11161e"
            },
            "dark": {
                "main_bg": "#121212", "main_text": "#e0e0e0", "tb_bg": "#1c1c1c", "tb_border": "#141414",
                "btn_hover": "#2b2b2b", "accent": "#388bfd", "page_bg": "#2b2b2b", "page_border": "#404040",
                "tab_bg": "#202020", "tab_hover": "#2a2a2a", "tab_border": "#282828", "tab_text": "#aaaaaa",
                "view_bg": "#121212"
            },
            "vice_city": {
                "main_bg": "#160024", "main_text": "#fdf2f8", "tb_bg": "#240e3b", "tb_border": "#3d1663",
                "btn_hover": "#381458", "accent": "#ff2a85", "page_bg": "#2c1047", "page_border": "#ff2a85",
                "tab_bg": "#1e0a32", "tab_hover": "#351357", "tab_border": "#3d1663", "tab_text": "#e2d1f0",
                "view_bg": "#0d0017"
            }
        }
        spec = theme_specs.get(theme_name, theme_specs["gray"])
        view_bg = spec["view_bg"]

        self.setStyleSheet(f"""
                QMainWindow {{ background-color: {spec['main_bg']}; color: {spec['main_text']}; }}
                QToolBar {{ background-color: {spec['tb_bg']}; border-bottom: 1px solid {spec['tb_border']}; spacing: 4px; padding: 4px 6px; }}
                QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px 6px; color: {spec['main_text']}; }}
                QToolButton:hover {{ background-color: {spec['btn_hover']}; }}
                QToolButton:checked {{ background-color: {spec['btn_hover']}; border-bottom: 2.5px solid {spec['accent']}; border-radius: 2px; }}
                QToolButton:disabled {{ background: transparent; border: 1px solid transparent; opacity: 0.35; color: #555555; }}
                QLineEdit#PageInput {{ background-color: {spec['page_bg']}; color: #ffffff; border: 1.2px solid {spec['page_border']}; border-radius: 3px; padding: 2px 4px; font-weight: bold; }}
                QLabel {{ color: {spec['main_text']}; font-size: 13px; }}
                QTabWidget::pane {{ border: none; background-color: {view_bg}; }}
                QTabBar::tab {{ background-color: {spec['tab_bg']}; color: {spec['tab_text']}; padding: 7px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: 1px solid {spec['tab_border']}; border-bottom: none; }}
                QTabBar::tab:hover {{ background-color: {spec['tab_hover']}; color: #ffffff; }}
                QTabBar::tab:selected {{ background-color: {spec['main_bg']}; color: #ffffff; border-top: 2px solid {spec['accent']}; font-weight: bold; }}
                QMenu {{ background-color: {spec['tb_bg']}; color: {spec['main_text']}; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 4px; }}
                QMenu::item {{ padding: 6px 20px; border-radius: 4px; font-size: 12px; }}
                QMenu::item:selected {{ background-color: {spec['accent']}; color: #ffffff; font-weight: bold; }}
                QMenu::separator {{ height: 1px; background-color: {spec['tb_border']}; margin: 4px 6px; }}
                QScrollBar:vertical {{ background: {view_bg}; width: 8px; margin: 0px; border-radius: 4px; }}
                QScrollBar::handle:vertical {{ background: {spec['page_border']}; min-height: 24px; border-radius: 4px; }}
                QScrollBar::handle:vertical:hover {{ background: {spec['accent']}; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar:horizontal {{ background: {view_bg}; height: 8px; margin: 0px; border-radius: 4px; }}
                QScrollBar::handle:horizontal {{ background: {spec['page_border']}; min-width: 24px; border-radius: 4px; }}
                QScrollBar::handle:horizontal:hover {{ background: {spec['accent']}; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            """)

        if hasattr(self, 'category_bar') and self.category_bar:
            self.category_bar.apply_theme(spec)

        if hasattr(self, 'btn_insert') and hasattr(self.btn_insert, 'menu') and self.btn_insert.menu():
            self.btn_insert.menu().setStyleSheet(f"""
                QMenu {{
                    background-color: {spec['tb_bg']};
                    color: {spec['main_text']};
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 10px;
                    padding: 6px 4px;
                }}
                QMenu::item {{
                    padding: 8px 22px 8px 14px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                    margin: 1px 4px;
                }}
                QMenu::item:selected {{
                    background-color: {spec['accent']};
                    color: #ffffff;
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: {spec['tb_border']};
                    margin: 4px 10px;
                }}
            """)

        if hasattr(self, 'lbl_zoom') and hasattr(self.lbl_zoom, 'apply_theme'):
            self.lbl_zoom.apply_theme(theme_name)

        thumb_dock = getattr(self, 'thumbnails_dock', getattr(self, 'dock_thumbnails', None))
        if thumb_dock and hasattr(thumb_dock, 'apply_theme'):
            thumb_dock.apply_theme(theme_name, spec)

        if hasattr(self, 'search_bar') and self.search_bar and hasattr(self.search_bar, 'apply_theme'):
            self.search_bar.apply_theme(theme_name, spec)

        # Temaya göre popüler imleç setini otomatik eşleştirme (Kullanıcı tercihi açık ise)
        if settings.value("auto_match_theme_cursor", True, type=bool):
            from src.ui.cursors import get_recommended_preset_for_theme, CURSOR_PRESETS
            rec_preset = get_recommended_preset_for_theme(theme_name)
            if rec_preset in CURSOR_PRESETS:
                cfg = CURSOR_PRESETS[rec_preset]
                settings.setValue("cursor_preset", rec_preset)
                settings.setValue("cursor_pen", cfg["pen"])
                settings.setValue("cursor_hl", cfg["hl"])
                settings.setValue("cursor_eraser", cfg["eraser"])
                settings.setValue("cursor_pointer", cfg["pointer"])
                settings.setValue("cursor_text", cfg["text"])
                settings.setValue("cursor_selection", cfg["selection"])
                settings.setValue("cursor_ruler", cfg.get("ruler", "ruler_crosshair"))
                if hasattr(self, 'update_viewport_cursor'):
                    self.update_viewport_cursor()

        popups = [
            getattr(self, 'cursor_popup', None),
            getattr(self, 'hl_popup', None),
            getattr(self, 'pen_popup', None),
            getattr(self, 'eraser_popup', None),
            getattr(self, 'text_popup', None),
            getattr(self, 'selection_popup', None),
            getattr(self, 'pointer_popup', None),
            getattr(self, 'hl_ruler_popup', None),
            getattr(self, 'ruler_popup', None),
            getattr(self, 'link_popup', None),
        ]
        for p in popups:
            if p and hasattr(p, 'apply_theme'):
                p.apply_theme(theme_name, spec)

        if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar and hasattr(self.fullscreen_toolbar, 'apply_theme'):
            self.fullscreen_toolbar.apply_theme(theme_name, spec)

        if hasattr(self, 'floating_hud') and self.floating_hud and hasattr(self.floating_hud, 'apply_theme'):
            self.floating_hud.apply_theme(theme_name, spec)

        if hasattr(self, 'tab_widget') and self.tab_widget:
            for idx in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(idx)
                if isinstance(widget, PDFTabDocument):
                    if hasattr(widget, 'view') and widget.view:
                        widget.view.setStyleSheet(f"background-color: {view_bg}; border: none;")
                    if hasattr(widget, 'floating_text_hud') and widget.floating_text_hud and hasattr(widget.floating_text_hud, 'apply_theme'):
                        widget.floating_text_hud.apply_theme(theme_name, spec)

    def change_language(self, lang: str):
        LanguageManager.set_language(lang)
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("language", lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(LanguageManager.tr("app_title"))
        if hasattr(self, 'category_bar') and self.category_bar:
            self.category_bar.retranslate_ui()

        if hasattr(self, 'btn_save_as'):
            self.btn_save_as.setText(" " + LanguageManager.tr("save_as"))
            self.btn_save_as.setToolTip(LanguageManager.tr("save_as") + " (Ctrl+Shift+S)")
        if hasattr(self, 'btn_doc_props'):
            self.btn_doc_props.setText(" " + LanguageManager.tr("doc_properties"))
            self.btn_doc_props.setToolTip(LanguageManager.tr("doc_properties") + " (Ctrl+D)")
        if hasattr(self, 'btn_new_tab'):
            self.btn_new_tab.setText(" " + LanguageManager.tr("new_document"))
            self.btn_new_tab.setToolTip(LanguageManager.tr("new_document") + " (Ctrl+N)")
        if hasattr(self, 'btn_close_tab'):
            self.btn_close_tab.setText(" " + LanguageManager.tr("close_tab"))
            self.btn_close_tab.setToolTip(LanguageManager.tr("close_tab") + " (Ctrl+W)")

        if hasattr(self, 'btn_insert_img'):
            self.btn_insert_img.setText(" " + LanguageManager.tr("insert_image").replace("...", ""))
            self.btn_insert_img.setToolTip(LanguageManager.tr("insert_image"))
        if hasattr(self, 'btn_insert_voice'):
            self.btn_insert_voice.setText(" " + LanguageManager.tr("insert_voice_recording").replace("...", ""))
            self.btn_insert_voice.setToolTip(LanguageManager.tr("insert_voice_recording"))
        if hasattr(self, 'btn_insert_camera'):
            self.btn_insert_camera.setText(" " + LanguageManager.tr("insert_camera").replace("...", ""))
            self.btn_insert_camera.setToolTip(LanguageManager.tr("insert_camera"))
        if hasattr(self, 'btn_insert_audio'):
            self.btn_insert_audio.setText(" " + LanguageManager.tr("insert_audio_file").replace("...", ""))
            self.btn_insert_audio.setToolTip(LanguageManager.tr("insert_audio_file"))
        if hasattr(self, 'btn_insert_emoji'):
            self.btn_insert_emoji.setText(" " + LanguageManager.tr("insert_drawing").replace("...", ""))
            self.btn_insert_emoji.setToolTip(LanguageManager.tr("insert_drawing"))
        if hasattr(self, 'btn_insert_table'):
            self.btn_insert_table.setText(" " + LanguageManager.tr("insert_table").replace("...", ""))
            self.btn_insert_table.setToolTip(LanguageManager.tr("insert_table"))
        if hasattr(self, 'btn_insert_blank'):
            self.btn_insert_blank.setText(" " + LanguageManager.tr("sidebar_btn_add_blank"))
            self.btn_insert_blank.setToolTip(LanguageManager.tr("sidebar_btn_add_blank"))

        if hasattr(self, 'btn_tool_organize'):
            self.btn_tool_organize.setText(" " + LanguageManager.tr("reorder_action").replace("...", ""))
            self.btn_tool_organize.setToolTip(LanguageManager.tr("reorder_action"))
        if hasattr(self, 'btn_tool_merge'):
            self.btn_tool_merge.setText(" " + LanguageManager.tr("merge_action").replace("...", ""))
            self.btn_tool_merge.setToolTip(LanguageManager.tr("merge_action"))
        if hasattr(self, 'btn_tool_split'):
            self.btn_tool_split.setText(" " + LanguageManager.tr("split_action").replace("...", ""))
            self.btn_tool_split.setToolTip(LanguageManager.tr("split_action"))
        if hasattr(self, 'btn_tool_ocr'):
            self.btn_tool_ocr.setToolTip(LanguageManager.tr("ocr_action"))
        if hasattr(self, 'btn_tool_editor'):
            self.btn_tool_editor.setText(" " + LanguageManager.tr("content_editor_action").replace("...", ""))
            self.btn_tool_editor.setToolTip(LanguageManager.tr("content_editor_action"))
        if hasattr(self, 'btn_tool_sign'):
            self.btn_tool_sign.setText(" " + LanguageManager.tr("sign_action").replace("...", ""))
            self.btn_tool_sign.setToolTip(LanguageManager.tr("sign_action"))
        if hasattr(self, 'btn_tool_compare'):
            self.btn_tool_compare.setText(" " + LanguageManager.tr("compare_action").replace("...", ""))
            self.btn_tool_compare.setToolTip(LanguageManager.tr("compare_action"))
        if hasattr(self, 'btn_tool_redact'):
            self.btn_tool_redact.setText(" " + LanguageManager.tr("redact_action").replace("...", ""))
            self.btn_tool_redact.setToolTip(LanguageManager.tr("redact_action"))
        if hasattr(self, 'btn_tool_encrypt'):
            self.btn_tool_encrypt.setText(" " + LanguageManager.tr("encrypt_action").replace("...", ""))
            self.btn_tool_encrypt.setToolTip(LanguageManager.tr("encrypt_action"))
        if hasattr(self, 'btn_tool_compress'):
            self.btn_tool_compress.setText(" " + LanguageManager.tr("compress_action").replace("...", ""))
            self.btn_tool_compress.setToolTip(LanguageManager.tr("compress_action"))

        if hasattr(self, 'btn_cursor'):
            tip = LanguageManager.tr("cursor_tool_tip") if getattr(self, 'cursor_mode', 'select') == 'select' else LanguageManager.tr("cursor_pan_tip")
            self.btn_cursor.setToolTip(tip)
        self.btn_contents.setToolTip(LanguageManager.tr("contents"))
        self.btn_undo.setToolTip(LanguageManager.tr("undo"))
        self.btn_redo.setToolTip(LanguageManager.tr("redo"))
        self.btn_selection.setToolTip(LanguageManager.tr("selection_tool_tip"))
        self.btn_hl.setToolTip(LanguageManager.tr("highlighter_tool_tip"))
        self.btn_pen.setToolTip(LanguageManager.tr("pen_tool_tip"))
        if getattr(self, 'btn_ruler', None) is not None:
            self.btn_ruler.setToolTip(LanguageManager.tr("ruler_tool_tip"))
        self.btn_text.setToolTip(LanguageManager.tr("text_tool_tip"))
        self.btn_eraser.setToolTip(LanguageManager.tr("eraser_tool_tip"))
        self.btn_pointer.setToolTip(LanguageManager.tr("pointer_tool_tip"))
        self.lbl_zoom.setToolTip(LanguageManager.tr("zoom_edit_tip"))
        self.btn_rotate.setToolTip(LanguageManager.tr("rotate"))
        self.txt_page.setToolTip(LanguageManager.tr("page_input_tip"))
        if hasattr(self, 'btn_search'):
            self.btn_search.setToolTip(LanguageManager.tr("search_tooltip"))
        if hasattr(self, 'search_bar'):
            self.search_bar.txt_search.setPlaceholderText(LanguageManager.tr("search_placeholder"))
            self.search_bar.btn_prev.setToolTip(LanguageManager.tr("search_prev_tip"))
            self.search_bar.btn_next.setToolTip(LanguageManager.tr("search_next_tip"))
            self.search_bar.btn_case.setToolTip(LanguageManager.tr("search_case_tip"))
            self.search_bar.btn_close.setToolTip(LanguageManager.tr("search_close_tip"))
        self.btn_print.setToolTip(LanguageManager.tr("print"))
        self.btn_save.setToolTip(LanguageManager.tr("save"))
        if hasattr(self, 'btn_view_mode'):
            self.btn_view_mode.setToolTip(LanguageManager.tr("view_mode_btn_tip"))
        if hasattr(self, 'act_view_single'):
            self.act_view_single.setText(LanguageManager.tr("view_mode_single"))
        if hasattr(self, 'act_view_double'):
            self.act_view_double.setText(LanguageManager.tr("view_mode_double"))
        self.btn_open.setText(LanguageManager.tr("open"))
        self.btn_open.setToolTip(LanguageManager.tr("open"))
        if hasattr(self, 'btn_nav_back'):
            self.btn_nav_back.setToolTip(LanguageManager.tr("nav_back"))
        if hasattr(self, 'btn_nav_forward'):
            self.btn_nav_forward.setToolTip(LanguageManager.tr("nav_forward"))
        if hasattr(self, 'btn_fit_page'):
            self.btn_fit_page.setToolTip(LanguageManager.tr("fit_to_page"))
        if hasattr(self, 'btn_reading_mode'):
            self.btn_reading_mode.setToolTip(LanguageManager.tr("reading_mode"))
        if hasattr(self, 'act_read_light'):
            self.act_read_light.setText(LanguageManager.tr("reading_mode_light"))
        if hasattr(self, 'act_read_dark'):
            self.act_read_dark.setText(LanguageManager.tr("reading_mode_dark"))
        if hasattr(self, 'act_read_sepia'):
            self.act_read_sepia.setText(LanguageManager.tr("reading_mode_sepia"))
        if hasattr(self, 'btn_speech'):
            tip = LanguageManager.tr("speech_stop") if getattr(self, 'speech_engine', None) and self.speech_engine.is_speaking() else LanguageManager.tr("speech_read_aloud")
            self.btn_speech.setToolTip(tip)
        if hasattr(self, 'act_open_direct'):
            self.act_open_direct.setText(LanguageManager.tr("open") + " (Ctrl+O)")
        if hasattr(self, 'act_reopen_tab'):
            self.act_reopen_tab.setText(LanguageManager.tr("reopen_closed_tab") + " (Ctrl+Shift+T)")
        if hasattr(self, 'act_doc_props'):
            self.act_doc_props.setText(LanguageManager.tr("doc_properties") + " (Ctrl+D)")
        if hasattr(self, 'recent_files_menu'):
            self.recent_files_menu.setTitle(LanguageManager.tr("recent_files"))
            self.update_recent_files_menu()
        self.btn_toolbox.setText("")
        self.btn_toolbox.setToolTip(LanguageManager.tr("tools_tooltip"))
        if hasattr(self, 'btn_settings'):
            self.btn_settings.setToolTip(LanguageManager.tr("settings_tooltip"))
        if hasattr(self, 'btn_fullscreen'):
            self.btn_fullscreen.setToolTip(LanguageManager.tr("tb_item_fullscreen"))
        if hasattr(self, 'thumbnails_dock'):
            self.thumbnails_dock.retranslate_ui()

        if hasattr(self, 'btn_insert'):
            self.btn_insert.setToolTip(LanguageManager.tr("insert_btn_tip"))
        if getattr(self, 'menu_insert_blank', None):
            self.menu_insert_blank.setTitle("  " + LanguageManager.tr("insert_blank_page"))
        if hasattr(self, 'insert_blank_actions') and self.insert_blank_actions:
            for act, key in self.insert_blank_actions:
                act.setText(LanguageManager.tr(key))
        if hasattr(self, 'act_voice_rec'):
            self.act_voice_rec.setText("  " + LanguageManager.tr("insert_voice_recording"))
        if hasattr(self, 'act_insert_img'):
            self.act_insert_img.setText("  " + LanguageManager.tr("insert_image"))
        if hasattr(self, 'act_camera'):
            self.act_camera.setText("  " + LanguageManager.tr("insert_camera"))
        if hasattr(self, 'act_audio_file'):
            self.act_audio_file.setText("  " + LanguageManager.tr("insert_audio_file"))
        if hasattr(self, 'act_drawing'):
            self.act_drawing.setText("  " + LanguageManager.tr("insert_drawing"))
        if hasattr(self, 'act_insert_emoji'):
            self.act_insert_emoji.setText("  " + LanguageManager.tr("insert_drawing"))
        if hasattr(self, 'act_insert_table'):
            self.act_insert_table.setText("  " + LanguageManager.tr("insert_table"))
        if hasattr(self, 'act_insert_audio'):
            self.act_insert_audio.setText("  " + LanguageManager.tr("insert_voice_recording"))
        if hasattr(self, 'act_insert_video'):
            self.act_insert_video.setText("  " + LanguageManager.tr("insert_camera"))

        for popup_name in ('cursor_popup', 'hl_popup', 'pen_popup', 'eraser_popup', 'text_popup', 'selection_popup', 'pointer_popup', 'hl_ruler_popup', 'ruler_popup'):
            if hasattr(self, popup_name):
                popup = getattr(self, popup_name)
                if hasattr(popup, 'retranslate_ui'):
                    popup.retranslate_ui()

        if (tab_doc := self.get_current_tab_doc()) and tab_doc.doc is not None:
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(tab_doc.zoom_level * 100))} ")
            self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
            tab_doc.update_tab_title()
        else:
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=100)} ")
            self.lbl_total.setText(LanguageManager.tr("page_of", total=0))
            self.setWindowTitle(LanguageManager.tr("app_title"))

        self.tab_widget.update()

    def get_theme_view_bg(self, theme: str = None) -> str:
        if not theme:
            theme = getattr(self, 'current_theme', 'dark')
        bg_map = {
            "purple": "#0e0817", "crimson": "#13070a", "nord": "#11161e", "dark": "#121212",
            "vice_city": "#0d0017"
        }
        return bg_map.get(theme, "#121212")

    def add_pdf_tab(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            return
        try:
            norm_path = os.path.abspath(file_path)
            for idx in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(idx)
                if isinstance(widget, PDFTabDocument) and getattr(widget, 'file_path', None) and os.path.abspath(widget.file_path) == norm_path:
                    self.tab_widget.setCurrentIndex(idx)
                    return
            tab_doc = PDFTabDocument(file_path, self)
            view_bg = self.get_theme_view_bg()
            tab_doc.view.setStyleSheet(f"background-color: {view_bg}; border: none;")
            tab_idx = self.tab_widget.addTab(tab_doc, os.path.basename(file_path))
            self.tab_widget.setCurrentIndex(tab_idx)
            tab_doc.update_tab_title()
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(tab_doc.zoom_level * 100))} ")

            # V3: Son açılanlara ekle ve dosya izleyiciye kaydet
            self.add_to_recent_files(file_path)
            if hasattr(self, 'file_watcher') and os.path.exists(file_path):
                self.file_watcher.addPath(norm_path)
        except Exception as e:
            if str(e) == LanguageManager.tr("password_cancelled"):
                return
            QMessageBox.critical(self, LanguageManager.tr("error"), LanguageManager.tr("open_error", error=e))

    def close_tab(self, index):
        if index is None or not (0 <= index < self.tab_widget.count()):
            return
        widget = self.tab_widget.widget(index)
        if isinstance(widget, PDFTabDocument) and widget.is_modified:
            base_name = os.path.basename(widget.file_path) if widget.file_path else "Adsız.pdf"
            reply = QMessageBox.question(
                self,
                LanguageManager.tr("warning"),
                LanguageManager.tr("unsaved_changes_warn", filename=base_name),
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                self.tab_widget.setCurrentIndex(index)
                self.save_pdf()
                if widget.is_modified:
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        if isinstance(widget, PDFTabDocument):
            if widget.file_path and os.path.exists(widget.file_path):
                # V3: Son kapatılan sekme geçmişine ekle
                self.closed_tabs_history.append({
                    "path": widget.file_path,
                    "page": widget.current_page_idx,
                    "zoom": widget.zoom_level
                })
                if len(self.closed_tabs_history) > 20:
                    self.closed_tabs_history.pop(0)
                # Dosya izleyiciden çıkar (başka sekmede açık değilse)
                if hasattr(self, 'file_watcher') and widget.file_path:
                    norm_path = os.path.abspath(widget.file_path)
                    still_open = any(
                        i != index and isinstance(self.tab_widget.widget(i), PDFTabDocument) and 
                        getattr(self.tab_widget.widget(i), 'file_path', None) and
                        os.path.abspath(self.tab_widget.widget(i).file_path) == norm_path
                        for i in range(self.tab_widget.count())
                    )
                    if not still_open:
                        self.file_watcher.removePath(norm_path)
            widget.close_document()
        self.tab_widget.removeTab(index)
        if widget is not None:
            widget.deleteLater()
        if self.tab_widget.count() == 0:
            self.txt_page.setText("0")
            self.lbl_total.setText(LanguageManager.tr("page_of", total=0))
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=100)} ")
            self.thumbnails_dock.load_thumbnails_lazy()
            self.setWindowTitle(LanguageManager.tr("app_title"))
        self.update_undo_redo_state()

    def on_tab_changed(self, index):
        if (tab_doc := self.get_current_tab_doc()) and tab_doc.doc is not None:
            tab_doc.update_tab_title()
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(tab_doc.zoom_level * 100))} ")
            self.txt_page.setText(str(tab_doc.current_page_idx + 1))
            self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
            self.update_view_mode_button()
            if self.thumbnails_dock.isVisible():
                self.thumbnails_dock.load_thumbnails_lazy()
                self.thumbnails_dock.select_page(tab_doc.current_page_idx)
            else:
                self.thumbnails_dock.is_loaded = False
            self.update_viewport_cursor()
            if hasattr(self, 'search_bar') and self.search_bar.isVisible():
                self.search_bar.do_search(reset_index=True)
        elif self.tab_widget.count() == 0:
            self.txt_page.setText("0")
            self.lbl_total.setText(LanguageManager.tr("page_of", total=0))
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=100)} ")
            self.thumbnails_dock.load_thumbnails_lazy()
            self.setWindowTitle(LanguageManager.tr("app_title"))
            if hasattr(self, 'search_bar') and self.search_bar.isVisible():
                self.search_bar.lbl_count.setText(LanguageManager.tr("search_no_results"))
        self.update_undo_redo_state()

    def prev_page(self):
        if doc := self.get_current_tab_doc(): doc.go_to_page(doc.current_page_idx - 1)
    def next_page(self):
        if doc := self.get_current_tab_doc(): doc.go_to_page(doc.current_page_idx + 1)
    def jump_to_page(self):
        if (doc := self.get_current_tab_doc()) and self.txt_page.text().isdigit(): doc.go_to_page(int(self.txt_page.text()) - 1)
    def zoom_in(self):
        if doc := self.get_current_tab_doc(): doc.zoom_in()
    def zoom_out(self):
        if doc := self.get_current_tab_doc(): doc.zoom_out()
    def fit_to_width(self):
        if doc := self.get_current_tab_doc(): doc.fit_to_width()

    def fit_to_page(self):
        if doc := self.get_current_tab_doc(): doc.fit_to_page()

    def nav_back(self):
        if doc := self.get_current_tab_doc(): doc.nav_back()

    def nav_forward(self):
        if doc := self.get_current_tab_doc(): doc.nav_forward()

    def set_reading_color_mode(self, mode: str):
        if doc := self.get_current_tab_doc(): doc.set_reading_color_mode(mode)

    def toggle_read_aloud(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc:
            return
        if self.speech_engine.is_speaking():
            self.speech_engine.stop()
        else:
            text_to_speak = ""
            if hasattr(tab_doc, 'selected_text') and tab_doc.selected_text.strip():
                text_to_speak = tab_doc.selected_text.strip()
            elif tab_doc.doc and 0 <= tab_doc.current_page_idx < len(tab_doc.doc):
                try:
                    page = tab_doc.doc[tab_doc.current_page_idx]
                    text_to_speak = page.get_text().strip()
                except Exception:
                    text_to_speak = ""
            if text_to_speak:
                self.speech_engine.speak(text_to_speak)
            else:
                QMessageBox.information(self, LanguageManager.tr("speech_read_aloud"), LanguageManager.tr("no_text_to_read"))

    def _on_speech_state_changed(self, is_speaking: bool):
        if hasattr(self, 'btn_speech'):
            self.btn_speech.setChecked(is_speaking)
            tip = LanguageManager.tr("speech_stop") if is_speaking else LanguageManager.tr("speech_read_aloud")
            self.btn_speech.setToolTip(tip)

    def open_document_properties_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("doc_properties"), LanguageManager.tr("no_active_doc_error"))
            return
        dlg = ModernDocumentPropertiesDialog(tab_doc.doc, tab_doc.file_path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tab_doc.is_modified = True
            tab_doc.update_tab_title()

    def _on_watched_file_changed(self, path: str):
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument) and widget.file_path and os.path.abspath(widget.file_path) == os.path.abspath(path):
                if widget.is_modified:
                    return
                reply = QMessageBox.question(
                    self,
                    LanguageManager.tr("file_changed_external_title"),
                    LanguageManager.tr("file_changed_external_msg", filename=os.path.basename(path)),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    curr_page = widget.current_page_idx
                    curr_zoom = widget.zoom_level
                    widget.close_document()
                    self.tab_widget.removeTab(idx)
                    widget.deleteLater()
                    self.add_pdf_tab(path)
                    if new_doc := self.get_current_tab_doc():
                        new_doc.scroll_to_page(curr_page)
                        new_doc.apply_zoom(curr_zoom)
                break

    def get_recent_files(self) -> List[str]:
        settings = QSettings("AuraPDF", "History")
        raw = settings.value("recent_files", "[]")
        files = []
        if isinstance(raw, str):
            import json
            try:
                files = json.loads(raw)
            except Exception:
                files = []
        elif isinstance(raw, list):
            files = list(raw)
        return [f for f in files if isinstance(f, str) and os.path.exists(f)]

    def add_to_recent_files(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return
        file_path = os.path.abspath(file_path)
        current = self.get_recent_files()
        if file_path in current:
            current.remove(file_path)
        current.insert(0, file_path)
        current = current[:15]
        settings = QSettings("AuraPDF", "History")
        import json
        settings.setValue("recent_files", json.dumps(current))
        self.update_recent_files_menu()

    def clear_recent_files(self):
        settings = QSettings("AuraPDF", "History")
        settings.remove("recent_files")
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        if not hasattr(self, 'recent_files_menu') or self.recent_files_menu is None:
            return
        self.recent_files_menu.clear()
        recents = self.get_recent_files()
        if not recents:
            empty_act = self.recent_files_menu.addAction(LanguageManager.tr("no_recent_files"))
            empty_act.setEnabled(False)
        else:
            for fpath in recents:
                fname = os.path.basename(fpath)
                act = self.recent_files_menu.addAction(f"{fname}  ({fpath})")
                act.setToolTip(fpath)
                act.triggered.connect(lambda checked=False, p=fpath: self.add_pdf_tab(p))
            self.recent_files_menu.addSeparator()
            clear_act = self.recent_files_menu.addAction(ModernIconFactory.icon_trash(), LanguageManager.tr("clear_recent_files"))
            clear_act.triggered.connect(self.clear_recent_files)

    def reopen_last_closed_tab(self):
        if not self.closed_tabs_history:
            return
        last = self.closed_tabs_history.pop()
        path = last.get("path")
        if path and os.path.exists(path):
            self.add_pdf_tab(path)
            if tab_doc := self.get_current_tab_doc():
                page = last.get("page", 0)
                tab_doc.scroll_to_page(page)
                zoom = last.get("zoom")
                if zoom:
                    tab_doc.apply_zoom(zoom)

    def save_current_session(self):
        settings = QSettings("AuraPDF", "Session")
        open_tabs = []
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument) and widget.file_path and os.path.exists(widget.file_path):
                open_tabs.append({
                    "path": widget.file_path,
                    "page": widget.current_page_idx,
                    "zoom": widget.zoom_level
                })
        import json
        settings.setValue("last_session", json.dumps(open_tabs))
        settings.setValue("active_tab_index", self.tab_widget.currentIndex())

    def restore_previous_session(self):
        if self.tab_widget.count() > 0:
            return
        settings = QSettings("AuraPDF", "Session")
        raw = settings.value("last_session", "")
        if not raw:
            return
        import json
        try:
            tabs_data = json.loads(raw)
            if not isinstance(tabs_data, list):
                return
            for item in tabs_data:
                path = item.get("path")
                if path and os.path.exists(path):
                    self.add_pdf_tab(path)
                    page = item.get("page", 0)
                    if tab_doc := self.get_current_tab_doc():
                        tab_doc.scroll_to_page(page)
                        zoom = item.get("zoom")
                        if zoom:
                            tab_doc.apply_zoom(zoom)
            active_idx = int(settings.value("active_tab_index", 0))
            if 0 <= active_idx < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(active_idx)
        except Exception:
            pass
    def rotate_all_pages(self):
        if doc := self.get_current_tab_doc(): doc.rotate_all_pages()

    def set_page_view_mode(self, mode: str):
        if tab_doc := self.get_current_tab_doc():
            if tab_doc.page_view_mode != mode:
                tab_doc.page_view_mode = mode
                tab_doc.render_pages_init()
                tab_doc.rerender_visible_pages()
                tab_doc.fit_to_width()
                tab_doc.go_to_page(tab_doc.current_page_idx)
            self.update_view_mode_button()

    def toggle_page_view_mode(self):
        if tab_doc := self.get_current_tab_doc():
            new_mode = "double" if tab_doc.page_view_mode == "single" else "single"
            self.set_page_view_mode(new_mode)

    def update_view_mode_button(self):
        if hasattr(self, 'btn_view_mode'):
            tab_doc = self.get_current_tab_doc()
            mode = getattr(tab_doc, 'page_view_mode', 'single') if tab_doc else 'single'
            if mode == 'double':
                self.btn_view_mode.setIcon(ModernIconFactory.icon_view_double())
            else:
                self.btn_view_mode.setIcon(ModernIconFactory.icon_view_single())

    def on_new_doc_btn_clicked(self):
        self.show_new_page_dialog()

    def add_blank_page_at_bottom(self, template_type="blank"):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None:
            self.new_blank_document(template_type)
            return
        last_page = len(tab_doc.doc) - 1
        tab_doc.insert_blank_page(after_page=last_page, style=template_type)
        tab_doc.go_to_page(len(tab_doc.doc) - 1)
        if hasattr(self, 'lbl_total') and self.lbl_total:
            self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
        if hasattr(self, 'txt_page') and self.txt_page:
            self.txt_page.setText(str(len(tab_doc.doc)))
        self.statusBar().showMessage(LanguageManager.tr("blank_page_added", page=len(tab_doc.doc)), 3000)

    def new_blank_document(self, template_type=None, width=None, height=None, create_page=True):
        try:
            if template_type is None:
                settings = QSettings("AuraPDF", "PDFViewer")
                template_type = settings.value("default_page_template", "blank")
            self.new_doc_counter += 1
            tab_doc = PDFTabDocument(None, self, initial_style=template_type, initial_width=width, initial_height=height, create_initial_page=create_page)
            view_bg = self.get_theme_view_bg()
            tab_doc.view.setStyleSheet(f"background-color: {view_bg}; border: none;")
            title = LanguageManager.tr("untitled_numbered", n=self.new_doc_counter)
            tab_doc.custom_title = title
            tab_idx = self.tab_widget.addTab(tab_doc, title)
            self.tab_widget.setCurrentIndex(tab_idx)
            tab_doc.update_tab_title()
            self.update_view_mode_button()
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(tab_doc.zoom_level * 100))} ")
            total_pages = len(tab_doc.doc) if tab_doc.doc is not None else 0
            if hasattr(self, 'lbl_total') and self.lbl_total:
                self.lbl_total.setText(LanguageManager.tr("page_of", total=total_pages))
            if hasattr(self, 'txt_page') and self.txt_page:
                self.txt_page.setText(str(total_pages if total_pages > 0 else 0))
            if total_pages > 0:
                self.statusBar().showMessage(LanguageManager.tr("blank_page_added", page=total_pages), 3000)
            else:
                self.statusBar().showMessage(LanguageManager.tr("new_blank_doc_created"), 3000)
            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                self.thumbnails_dock.load_thumbnails_lazy()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def show_new_page_dialog(self, default_style: Optional[str] = None, force_new_doc: bool = False):
        """Kullanıcının görsel şablon kartları arasından stil, yön, boyut ve konum
        seçerek sayfalar eklemesini veya yeni belge oluşturmasını sağlar."""
        try:
            if default_style is None:
                settings = QSettings("AuraPDF", "PDFViewer")
                default_style = settings.value("default_page_template", "blank")
            from src.ui.dialogs.new_page_dialog import NewPageDialog
            dlg = NewPageDialog(self, default_style=default_style, force_new_doc=force_new_doc)
            if dlg.exec():
                cfg = dlg.get_page_config()
                style = cfg.get("style", "blank")
                w = cfg.get("width")
                h = cfg.get("height")
                count = cfg.get("count", 1)
                placement = cfg.get("placement", "end")

                tab_doc = self.get_current_tab_doc()
                if force_new_doc or placement == "new_doc" or not tab_doc or tab_doc.doc is None:
                    # Yeni belge oluştur
                    for i in range(count):
                        if i == 0:
                            self.new_blank_document(template_type=style, width=w, height=h, create_page=True)
                        else:
                            curr_tab = self.get_current_tab_doc()
                            if curr_tab and curr_tab.doc is not None:
                                curr_tab.insert_blank_page(after_page=len(curr_tab.doc) - 1, width=w, height=h, style=style)
                else:
                    # Mevcut açık belgeye ekle
                    if placement == "before_current":
                        start_pos = max(-1, tab_doc.current_page_idx - 1)
                    elif placement == "after_current":
                        start_pos = tab_doc.current_page_idx
                    else:  # "end"
                        start_pos = len(tab_doc.doc) - 1

                    for i in range(count):
                        tab_doc.insert_blank_page(after_page=start_pos + i, width=w, height=h, style=style)

                    target_page = min(start_pos + count, len(tab_doc.doc) - 1)
                    tab_doc.go_to_page(target_page)
                    if hasattr(self, 'lbl_total') and self.lbl_total:
                        self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
                    if hasattr(self, 'txt_page') and self.txt_page:
                        self.txt_page.setText(str(target_page + 1))
                    self.statusBar().showMessage(LanguageManager.tr("blank_page_added", page=target_page + 1), 3000)
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def show_change_page_style_dialog(self, page_idx: Optional[int] = None):
        """Mevcut sayfanın veya tüm sayfaların şablonunu değiştirmek için diyalog açar."""
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None or len(tab_doc.doc) == 0:
            QMessageBox.information(self, LanguageManager.tr("info"), LanguageManager.tr("no_active_tab"))
            return
        if page_idx is None:
            page_idx = tab_doc.current_page_idx

        try:
            from src.ui.dialogs.new_page_dialog import ChangePageStyleDialog
            dlg = ChangePageStyleDialog(self, current_page_idx=page_idx, total_pages=len(tab_doc.doc))
            if dlg.exec():
                new_style, all_pages = dlg.get_selected_style()
                tab_doc.change_page_style(page_idx, new_style, all_pages=all_pages)
                msg = LanguageManager.tr("page_style_changed_all", style=new_style) if all_pages else LanguageManager.tr("page_style_changed_single", page=page_idx + 1, style=new_style)
                self.statusBar().showMessage(msg, 3500)
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def toggle_contents_panel(self):
        is_now_vis = not self.thumbnails_dock.isVisible()
        self.thumbnails_dock.setVisible(is_now_vis)
        if is_now_vis:
            self.thumbnails_dock.load_thumbnails_lazy()
            if tab_doc := self.get_current_tab_doc():
                self.thumbnails_dock.select_page(tab_doc.current_page_idx)

    def clear_all_drawings(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.drawings:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("clear_all_drawings"),
            LanguageManager.tr("confirm_clear_drawings"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            tab_doc.clear_all_drawings()

    def handle_ruler_click(self):
        new_snap = self.btn_ruler.isChecked()
        self.set_ruler_snap(new_snap)
        if new_snap and self.current_tool not in ('pen', 'highlighter'):
            self.set_tool_state('pen')

    def set_ruler_snap(self, enabled: bool):
        if hasattr(self, 'hl_popup'):
            self.hl_popup.snap_straight = enabled
            if hasattr(self.hl_popup, 'chk_snap'):
                self.hl_popup.chk_snap.blockSignals(True)
                self.hl_popup.chk_snap.setChecked(enabled)
                self.hl_popup.chk_snap.blockSignals(False)
        if hasattr(self, 'pen_popup'):
            self.pen_popup.snap_straight = enabled
            if hasattr(self.pen_popup, 'chk_snap'):
                self.pen_popup.chk_snap.blockSignals(True)
                self.pen_popup.chk_snap.setChecked(enabled)
                self.pen_popup.chk_snap.blockSignals(False)
        if getattr(self, 'btn_ruler', None):
            self.btn_ruler.blockSignals(True)
            self.btn_ruler.setChecked(enabled)
            self.btn_ruler.blockSignals(False)
        if hasattr(self, 'hl_ruler_popup'):
            self.hl_ruler_popup.refresh_state()

    def sync_ruler_state(self):
        is_snap = False
        if hasattr(self, 'hl_popup') and getattr(self.hl_popup, 'snap_straight', False):
            is_snap = True
        elif hasattr(self, 'pen_popup') and getattr(self.pen_popup, 'snap_straight', False):
            is_snap = True
        if getattr(self, 'btn_ruler', None):
            self.btn_ruler.blockSignals(True)
            self.btn_ruler.setChecked(is_snap)
            self.btn_ruler.blockSignals(False)
        if hasattr(self, 'hl_ruler_popup'):
            self.hl_ruler_popup.refresh_state()

    def handle_tool_click(self, tool_name, btn_widget, popup_widget):
        if self.current_tool == tool_name:
            if popup_widget and popup_widget.isVisible():
                popup_widget.close()
                self.set_tool_state('select')
            elif popup_widget: popup_widget.show_below(btn_widget)
            else: self.set_tool_state('select')
        else: self.set_tool_state(tool_name)

    def set_tool_state(self, tool_name):
        self.current_tool = tool_name
        for btn, names in [
            (getattr(self, 'btn_cursor', None), ('select', 'pan')),
            (getattr(self, 'btn_hl', None), ('highlighter',)), (getattr(self, 'btn_pen', None), ('pen',)), 
            (getattr(self, 'btn_eraser', None), ('eraser',)), (getattr(self, 'btn_text', None), ('text',)), 
            (getattr(self, 'btn_selection', None), ('selection_tool', 'ruler')), (getattr(self, 'btn_pointer', None), ('pointer',))
        ]:

            if btn is not None:
                btn.setChecked(tool_name in names)
        
        if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
            self.fullscreen_toolbar.update_active_tool(tool_name)
        
        if hasattr(self, 'btn_selection') and self.btn_selection is not None:
            if tool_name == 'ruler':
                self.btn_selection.setIcon(ModernIconFactory.icon_ruler())
            elif tool_name == 'selection_tool':
                mode = getattr(self, 'selection_shape_mode', 'rect')
                if mode == 'rect':
                    self.btn_selection.setIcon(ModernIconFactory.icon_select_rect())
                elif mode == 'lasso':
                    self.btn_selection.setIcon(ModernIconFactory.icon_select_lasso())
                elif mode == 'move':
                    self.btn_selection.setIcon(ModernIconFactory.icon_select_move())

        if hasattr(self, 'selection_popup') and self.selection_popup is not None:
            self.selection_popup.refresh_state()

        tab_doc = self.get_current_tab_doc()
        if tab_doc:
            if getattr(tab_doc, 'current_path_item', None) is not None:
                if tab_doc.current_path_item.scene() == tab_doc.scene:
                    tab_doc.scene.removeItem(tab_doc.current_path_item)
                tab_doc.current_path_item = None
                tab_doc.current_path = None
                tab_doc.current_stroke_pts = []
                tab_doc.active_drawing_page = None
                tab_doc.stroke_start_pos = None

            if tool_name not in ('selection_tool', 'ruler'):
                tab_doc.clear_selection()
            if tool_name != 'pointer':
                tab_doc.hide_laser_pointer()
                tab_doc._clear_pointer_trail_items()
        self.update_viewport_cursor()

    def update_viewport_cursor(self):
        if not (tab_doc := self.get_current_tab_doc()): return
        vp = tab_doc.view.viewport()

        pen_col = getattr(self.pen_popup, 'color', None)
        hl_col = getattr(self.hl_popup, 'color', None)
        pointer_col = getattr(self.pointer_popup, 'color', None) if hasattr(self, 'pointer_popup') else None

        hl_type = getattr(self.hl_popup, 'hl_type', 'highlighter') if hasattr(self, 'hl_popup') else 'highlighter'
        hl_cursor_style = "figma_marker" if hl_type == 'marker' else None
        pointer_popup = getattr(self, 'pointer_popup', None)
        if pointer_popup and getattr(pointer_popup, 'mode', 'single') == 'rainbow':
            pointer_cursor = CursorFactory.get_pointer_cursor(QColor("#7289FF"))
        else:
            pointer_cursor = CursorFactory.get_pointer_cursor(pointer_col)

        cursors = {
            'select': Qt.CursorShape.ArrowCursor,
            'pan': CursorFactory.get_pan_cursor(),
            'pen': CursorFactory.get_pen_cursor(pen_col),
            'highlighter': CursorFactory.get_highlighter_cursor(hl_col, style=hl_cursor_style),
            'eraser': CursorFactory.get_eraser_cursor(self.eraser_popup.thickness, self.eraser_popup.eraser_mode),
            'text': CursorFactory.get_text_cursor(),
            'selection_tool': CursorFactory.get_selection_cursor(self.selection_shape_mode),
            'pointer': pointer_cursor,
            'ruler': CursorFactory.get_ruler_cursor()
        }
        vp.setCursor(cursors.get(self.current_tool, Qt.CursorShape.ArrowCursor))

    def get_current_pen(self):
        if self.current_tool == 'pen':
            st = getattr(self.pen_popup, 'line_style', 'solid')
            p_type = getattr(self.pen_popup, 'current_pen_type', 'solid')
            is_pencil = (p_type == 'pencil' or st == 'pencil')
            style = Qt.PenStyle.SolidLine
            cap = Qt.PenCapStyle.RoundCap
            join = Qt.PenJoinStyle.RoundJoin
            if st == 'dash':
                style = Qt.PenStyle.DashLine
            elif st == 'dot':
                style = Qt.PenStyle.DotLine
            elif st == 'dashdot':
                style = Qt.PenStyle.DashDotLine
            elif st == 'calligraphy':
                cap = Qt.PenCapStyle.FlatCap
                join = Qt.PenJoinStyle.MiterJoin
            elif st in ('pencil', 'brush') or is_pencil:
                cap = Qt.PenCapStyle.RoundCap
                join = Qt.PenJoinStyle.RoundJoin

            if is_pencil:
                from src.document.tab_document import get_graphite_lead_texture
                tex = get_graphite_lead_texture(self.pen_popup.color)
                pen = QPen(QBrush(tex), self.pen_popup.thickness, Qt.PenStyle.SolidLine, cap, join)
                if st == 'dash':
                    pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pen.setDashPattern([2.2, 1.5])
                elif st == 'dot':
                    pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pen.setDashPattern([0.01, 1.9])
                elif st == 'dashdot':
                    pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pen.setDashPattern([2.2, 1.4, 0.01, 1.4])
                return pen

            return QPen(self.pen_popup.color, self.pen_popup.thickness, style, cap, join)
        elif self.current_tool == 'highlighter':
            hl_type = getattr(self.hl_popup, 'hl_type', 'highlighter') if hasattr(self, 'hl_popup') else 'highlighter'
            st = getattr(self.hl_popup, 'line_style', 'solid')
            style = Qt.PenStyle.SolidLine
            if hl_type == 'marker':
                cap = Qt.PenCapStyle.RoundCap
                join = Qt.PenJoinStyle.RoundJoin
            else:
                cap = Qt.PenCapStyle.SquareCap
                join = Qt.PenJoinStyle.BevelJoin
            if st == 'dash':
                style = Qt.PenStyle.DashLine
            elif st == 'dot':
                style = Qt.PenStyle.DotLine
            elif st == 'dashdot':
                style = Qt.PenStyle.DashDotLine
            elif st == 'calligraphy':
                cap = Qt.PenCapStyle.FlatCap
                join = Qt.PenJoinStyle.MiterJoin
            return QPen(self.hl_popup.color, self.hl_popup.thickness, style, cap, join)
        return QPen()

    def open_pdf(self):
        if paths := QFileDialog.getOpenFileNames(self, LanguageManager.tr("open_dialog_title"), "", "PDF (*.pdf)")[0]:
            for path in paths: self.add_pdf_tab(path)

    def save_pdf(self):
        if not (tab_doc := self.get_current_tab_doc()) or tab_doc.doc is None or len(tab_doc.doc) == 0:
            return QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("no_pdf_save"))
        
        default_name = f"duzenlenmis_{os.path.basename(tab_doc.file_path)}" if getattr(tab_doc, 'file_path', None) else "Yeni_Belge.pdf"
        path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("save_dialog_title"), default_name, "PDF (*.pdf)")
        if not path:
            return

        try:
            # 1. Etkileşimli formları ve çizimleri PDF vektör akışına aktar
            if hasattr(tab_doc, 'sync_form_fields'):
                tab_doc.sync_form_fields()
            tab_doc.export_drawings_to_pdf(tab_doc.doc)

            # 2. Yazar üstverisi ayarlarını kontrol et ve gerekirse uygula
            settings = QSettings("AuraPDF", "PDFViewer")
            save_author = settings.value("save_author_to_pdf", True, type=bool)
            if save_author:
                author = str(settings.value("author_name", "") or "").strip()
                title = str(settings.value("author_title", "") or "").strip()
                if not author or author == "Test Author" or not title or title == "Lead Architect":
                    from src.ui.dialogs.settings_dialog import get_default_author_info
                    def_user, def_comp = get_default_author_info()
                    if not author or author == "Test Author":
                        author = def_user
                    if not title or title == "Lead Architect":
                        title = def_comp
                if author:
                    try:
                        meta = tab_doc.doc.metadata or {}
                        meta["author"] = f"{author} ({title})" if title else author
                        tab_doc.doc.set_metadata(meta)
                    except Exception:
                        pass

            # 3. Diske güvenli ve atomik kaydetme
            target_path = os.path.abspath(path)
            temp_path = target_path + ".tmp_save"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            tab_doc.doc.save(temp_path, garbage=4, deflate=True)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            os.replace(temp_path, target_path)

            tab_doc.file_path = target_path
            base_name = os.path.basename(target_path)
            tab_idx = self.tab_widget.indexOf(tab_doc)
            if tab_idx >= 0:
                self.tab_widget.setTabText(tab_idx, base_name)
                self.tab_widget.setTabToolTip(tab_idx, target_path)

            # 4. Bellekteki (in-memory) PDF dokümanındaki ink açıklamalarını gizle (PDF_ANNOT_IS_HIDDEN)
            # Böylece get_pixmap arka planında statik kopya çizilmez,
            # tab_doc.drawings içindeki etkileşimli vektör çizimler sahnede silinebilir ve taşınabilir kalır!
            MANAGED_TYPES = (fitz.PDF_ANNOT_INK, fitz.PDF_ANNOT_LINE, fitz.PDF_ANNOT_POLY_LINE, fitz.PDF_ANNOT_HIGHLIGHT, fitz.PDF_ANNOT_FREE_TEXT)
            for p in tab_doc.doc:
                try:
                    for a in list(p.annots()):
                        if a.type[0] in MANAGED_TYPES:
                            a.set_flags(a.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                            a.update()
                except Exception:
                    pass

            tab_doc.clear_selection()
            tab_doc.save_undo_index = len(tab_doc.undo_stack)
            tab_doc.set_modified(False)
            if hasattr(self, 'update_undo_redo_state'):
                self.update_undo_redo_state()

            # 5. Sayfa arka plan pixmap'lerini yenile
            tab_doc.rerender_visible_pages(force=True)

            # 6. Eğer bu dosya başka bir sekmede de açıksa, o sekmeyi de diski okuyarak güncelle
            for i in range(self.tab_widget.count()):
                w = self.tab_widget.widget(i)
                if isinstance(w, PDFTabDocument) and w != tab_doc and getattr(w, 'file_path', None):
                    if os.path.abspath(w.file_path) == target_path:
                        w.reload_from_disk()

            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock and self.thumbnails_dock.is_loaded:
                self.thumbnails_dock.load_thumbnails_lazy()

            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("save_success"))

        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('error')}: {str(e)}")

    def print_pdf(self):
        if not (tab_doc := self.get_current_tab_doc()) or tab_doc.doc is None or len(tab_doc.doc) == 0:
            return QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("no_pdf_print"))
        from src.ui.dialogs.print_dialog import ModernPrintDialog
        ModernPrintDialog(tab_doc, self).exec()

    def handle_dropped_urls(self, urls):
        for u in urls:
            path = u.toLocalFile() if hasattr(u, 'toLocalFile') else str(u)
            if path.lower().endswith('.pdf') and os.path.isfile(path):
                self.add_pdf_tab(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
            if pdf_urls:
                self.handle_dropped_urls(pdf_urls)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def show_insert_table_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        from src.ui.dialogs.media_dialogs import TableInsertDialog
        dlg = TableInsertDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            tab_doc.add_table(
                rows=data["rows"],
                cols=data["cols"],
                has_header=data["has_header"],
                border_color=data["border_color"],
                header_bg=data["header_bg"],
                cell_bg=data["cell_bg"],
                text_color=data.get("text_color", "#1e1b4b"),
                header_text_color=data.get("header_text_color", "#ffffff"),
                alt_cell_bg=data.get("alt_cell_bg", "#f5f3ff")
            )

    def show_insert_emoji_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        from src.ui.dialogs.media_dialogs import EmojiGifPickerDialog
        dlg = EmojiGifPickerDialog(self)
        if dlg.exec():
            if dlg.selected_emoji:
                tab_doc.add_emoji(dlg.selected_emoji)
            elif dlg.selected_gif_bytes:
                tab_doc.add_image_media(dlg.selected_gif_bytes, title="Çıkartma")

    def show_insert_image_dialog(self, default_tab=0):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        from src.ui.dialogs.media_dialogs import ImageInsertDialog
        dlg = ImageInsertDialog(self, default_tab=default_tab)
        if dlg.exec():
            if dlg.image_bytes:
                tab_doc.add_image_media(
                    dlg.image_bytes,
                    title="Görsel",
                    keep_aspect=getattr(dlg, 'keep_aspect_ratio', True)
                )

    def show_insert_audio_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return

        # Zaten açık bir ses kayıt penceresi varsa öne getir
        if hasattr(self, '_audio_record_dialog') and self._audio_record_dialog is not None:
            try:
                if self._audio_record_dialog.isVisible():
                    self._audio_record_dialog.showNormal()
                    self._audio_record_dialog.raise_()
                    self._audio_record_dialog.activateWindow()
                    return
            except Exception:
                pass

        from src.ui.dialogs.media_dialogs import AudioRecordDialog
        dlg = AudioRecordDialog(self)
        self._audio_record_dialog = dlg

        def on_accepted():
            if dlg.audio_bytes:
                target_tab = self.get_current_tab_doc() or tab_doc
                if target_tab and target_tab.doc and len(target_tab.doc) > 0:
                    target_tab.add_audio(
                        audio_bytes=dlg.audio_bytes,
                        title=dlg.txt_title.text().strip() or "Ses Notu",
                        duration_sec=dlg.duration_sec,
                        format=dlg.format
                    )
                else:
                    QMessageBox.warning(self, LanguageManager.tr("warning"), "Ses kaydını eklemek için açık bir PDF belgesi bulunamadı.")

        def on_finished(result):
            if hasattr(self, '_audio_record_dialog') and self._audio_record_dialog == dlg:
                self._audio_record_dialog = None

        dlg.accepted.connect(on_accepted)
        dlg.finished.connect(on_finished)
        dlg.show()

    def show_insert_video_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        from src.ui.dialogs.media_dialogs import VideoInsertDialog
        dlg = VideoInsertDialog(self)
        if dlg.exec():
            url_path, thumb_bytes, title = dlg.get_data()
            if url_path:
                tab_doc.add_video(
                    video_url_or_path=url_path,
                    thumbnail_bytes=thumb_bytes,
                    title=title or "Video"
                )

    def show_insert_audio_file_picker(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            LanguageManager.tr("insert_audio_file"),
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;All Files (*.*)"
        )
        if path and os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    audio_bytes = f.read()
                filename = os.path.basename(path)
                ext = os.path.splitext(filename)[1].lstrip('.').lower() or "mp3"
                tab_doc.add_audio(
                    audio_bytes=audio_bytes,
                    title=filename,
                    duration_sec=0.0,
                    format=ext
                )
            except Exception as e:
                QMessageBox.warning(self, LanguageManager.tr("warning"), f"Ses dosyası eklenemedi: {e}")

    def insert_sticky_note(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce bir PDF belgesi açın.")
            return
        self.set_tool_state('text')
        center_scene = tab_doc.view.mapToScene(tab_doc.view.viewport().rect().center())
        page_idx = tab_doc.current_page_idx
        for p_i, p_b in tab_doc.page_positions.items():
            if p_b['top'] <= center_scene.y() <= p_b['bottom']:
                page_idx = p_i
                break
        tab_doc.create_inline_text(center_scene, page_idx)

    def show_toolbox_menu(self):
        menu = QMenu(self)
        def add_section_label(m, text):
            from PyQt6.QtWidgets import QWidgetAction, QLabel
            label = QLabel(text)
            label.setStyleSheet("""
                font-size: 10px;
                font-weight: 700;
                color: #94a3b8;
                padding: 8px 14px 4px 14px;
                letter-spacing: 0.6px;
                background: transparent;
            """)
            action = QWidgetAction(m)
            action.setDefaultWidget(label)
            m.addAction(action)

        menu.setStyleSheet("""
            QMenu {
                background-color: #1c1c1e;
                color: #f1f5f9;
                border: 1px solid #333338;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::section {
                font-size: 10px;
                font-weight: 700;
                color: #94a3b8;
                padding: 8px 14px 4px 14px;
                letter-spacing: 0.6px;
            }
            QMenu::item {
                padding: 6px 22px 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2a2e;
                margin: 4px 6px;
            }
        """)

        # 1. Sayfa Yönetimi Grubu
        add_section_label(menu, LanguageManager.tr("toolbox_group_pages"))
        act_add_blank = menu.addAction(ModernIconFactory.icon_add_page(), LanguageManager.tr("add_blank_page_down"))
        act_add_blank.triggered.connect(lambda checked=False: self.show_new_page_dialog())

        act_new_blank = menu.addAction(ModernIconFactory.icon_new_document(), LanguageManager.tr("new_blank_doc_menu"))
        act_organize = menu.addAction(ModernIconFactory.icon_organize(), LanguageManager.tr("organize_action"))
        act_page_number = menu.addAction(ModernIconFactory.icon_page_number(), LanguageManager.tr("page_number_action"))
        act_merge = menu.addAction(ModernIconFactory.icon_merge(), LanguageManager.tr("merge_action"))
        act_split = menu.addAction(ModernIconFactory.icon_split(), LanguageManager.tr("split_action"))

        # 2. Düzenleme & İnceleme Grubu
        add_section_label(menu, LanguageManager.tr("toolbox_group_edit"))
        act_content_editor = menu.addAction(ModernIconFactory.icon_edit_content(), LanguageManager.tr("content_edit_action"))
        act_ocr = menu.addAction(ModernIconFactory.icon_ocr(), LanguageManager.tr("ocr_action"))
        act_redact = menu.addAction(ModernIconFactory.icon_redact(), LanguageManager.tr("redact_action"))
        act_compare = menu.addAction(ModernIconFactory.icon_compare(), LanguageManager.tr("compare_action"))
        act_sign = menu.addAction(ModernIconFactory.icon_sign(), LanguageManager.tr("sign_action"))

        # 3. Tasarım & Güvenlik Grubu
        add_section_label(menu, LanguageManager.tr("toolbox_group_security"))
        act_watermark = menu.addAction(ModernIconFactory.icon_watermark(), LanguageManager.tr("watermark_action"))
        act_background = menu.addAction(ModernIconFactory.icon_background(), LanguageManager.tr("background_action"))
        act_encrypt = menu.addAction(ModernIconFactory.icon_lock(), LanguageManager.tr("encrypt_action"))
        act_compress = menu.addAction(ModernIconFactory.icon_compress(), LanguageManager.tr("compress_action"))
        act_recovery = menu.addAction(ModernIconFactory.icon_recovery(), LanguageManager.tr("recovery_action"))

        # 4. Dönüştürme & Dışa Aktarma Grubu
        add_section_label(menu, LanguageManager.tr("toolbox_group_convert"))
        act_word = menu.addAction(ModernIconFactory.icon_word(), LanguageManager.tr("word_action"))
        act_pptx = menu.addAction(ModernIconFactory.icon_powerpoint(), LanguageManager.tr("pptx_action"))
        act_excel = menu.addAction(ModernIconFactory.icon_excel(), LanguageManager.tr("excel_action"))
        act_epub = menu.addAction(ModernIconFactory.icon_epub(), LanguageManager.tr("epub_action"))
        act_mobi = menu.addAction(ModernIconFactory.icon_mobi(), LanguageManager.tr("mobi_action"))

        # 5. Yardım & Kılavuz
        menu.addSeparator()
        act_shortcuts = menu.addAction(ModernIconFactory.icon_keyboard_shortcuts(), LanguageManager.tr("shortcuts_action"))

        act_new_blank.triggered.connect(lambda checked=False: self.show_new_page_dialog(force_new_doc=True))
        act_content_editor.triggered.connect(self.open_pdf_content_editor)
        act_ocr.triggered.connect(self.open_pdf_ocr_dialog)
        act_redact.triggered.connect(self.open_pdf_redaction_dialog)
        act_compare.triggered.connect(self.open_pdf_compare_dialog)
        act_sign.triggered.connect(self.open_signature_dialog)
        act_organize.triggered.connect(lambda: self.open_organize_dialog(0))
        act_page_number.triggered.connect(self.open_page_number_dialog)
        act_merge.triggered.connect(self.open_merge_dialog)
        act_split.triggered.connect(self.open_split_dialog)
        act_watermark.triggered.connect(self.open_watermark_dialog)
        act_background.triggered.connect(self.open_background_dialog)
        act_encrypt.triggered.connect(self.open_encrypt_dialog)
        act_compress.triggered.connect(self.open_compress_dialog)
        act_recovery.triggered.connect(self.open_recovery_dialog)
        act_word.triggered.connect(self.open_word_dialog)
        act_pptx.triggered.connect(self.open_pptx_dialog)
        act_excel.triggered.connect(self.open_excel_dialog)
        act_epub.triggered.connect(lambda: self.open_ebook_dialog("epub"))
        act_mobi.triggered.connect(lambda: self.open_ebook_dialog("mobi"))
        act_shortcuts.triggered.connect(self.open_shortcuts_dialog)

        point = self.btn_toolbox.mapToGlobal(QPoint(0, self.btn_toolbox.height() + 4))
        menu.exec(point)

    def open_compress_dialog(self):
        tab_doc = self.get_current_tab_doc()
        initial_file = getattr(tab_doc, 'file_path', "") if tab_doc else ""
        from src.ui.dialogs.pdf_compress_dialog import PDFCompressDialog
        dlg = PDFCompressDialog(self, default_input_path=initial_file)
        if dlg.exec() and getattr(dlg, 'compressed_pdf_path', None) and getattr(dlg, 'open_after_compress', True):
            if os.path.exists(dlg.compressed_pdf_path):
                self.add_pdf_tab(dlg.compressed_pdf_path)

    def open_shortcuts_dialog(self):
        from src.ui.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
        dlg = KeyboardShortcutsDialog(self)
        dlg.exec()

    def open_pdf_compare_dialog(self):
        from src.ui.dialogs.pdf_compare_dialog import PDFCompareDialog
        dlg = PDFCompareDialog(self)
        dlg.exec()

    def open_pdf_redaction_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), "Lütfen önce karartma yapmak istediğiniz bir PDF belgesi açın.")
            return
        from src.ui.dialogs.pdf_redaction_dialog import PDFRedactionDialog
        dlg = PDFRedactionDialog(self)
        dlg.exec()

    def open_pdf_ocr_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), "Lütfen önce OCR uygulamak istediğiniz bir PDF belgesi açın.")
            return
        from src.ui.dialogs.pdf_ocr_dialog import PDFScanOCRDialog
        dlg = PDFScanOCRDialog(self)
        dlg.exec()

    def open_pdf_content_editor(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), "Lütfen önce bir PDF belgesi açın.")
            return
        from src.ui.dialogs.pdf_content_editor_dialog import PDFContentEditorDialog
        dlg = PDFContentEditorDialog(self)
        dlg.exec()

    def open_signature_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen önce imzalamak istediğiniz bir PDF belgesi açın.")
            return
        settings = QSettings("AuraPDF", "PDFViewer")
        author_name = str(settings.value("author_name", "") or "").strip()
        if not author_name or author_name == "Test Author":
            from src.ui.dialogs.settings_dialog import get_default_author_info
            def_user, _ = get_default_author_info()
            author_name = def_user
        try:
            from src.ui.dialogs.pdf_signature_dialog import PDFSignatureDialog
            dlg = PDFSignatureDialog(self, default_name=author_name)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image is not None:
                tab_doc.add_signature(dlg.result_image)
                QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("sign_placed_success"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, LanguageManager.tr("error"), f"İmza eklenirken bir hata oluştu: {e}")

    def open_organize_dialog(self, initial_tab: int = 0):
        from src.ui.dialogs.toolbox_dialogs import PDFOrganizePagesDialog
        PDFOrganizePagesDialog(self, initial_tab=initial_tab).exec()

    def open_merge_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFMergeDialog
        PDFMergeDialog(self).exec()

    def open_split_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFSplitDialog
        PDFSplitDialog(self).exec()

    def open_reorder_dialog(self):
        self.open_organize_dialog(initial_tab=0)

    def open_page_number_dialog(self):
        self.open_organize_dialog(initial_tab=1)

    def open_watermark_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFWatermarkDialog
        PDFWatermarkDialog(self).exec()

    def open_background_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFBackgroundDialog
        PDFBackgroundDialog(self).exec()

    def open_encrypt_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFEncryptDialog
        PDFEncryptDialog(self).exec()

    def open_recovery_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFPasswordRecoveryDialog
        PDFPasswordRecoveryDialog(self).exec()

    def open_word_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFToWordDialog
        PDFToWordDialog(self).exec()

    def open_pptx_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFToPowerPointDialog
        PDFToPowerPointDialog(self).exec()

    def open_excel_dialog(self):
        from src.ui.dialogs.toolbox_dialogs import PDFToExcelDialog
        PDFToExcelDialog(self).exec()

    def open_ebook_dialog(self, format_type):
        from src.ui.dialogs.toolbox_dialogs import PDFToEbookDialog
        PDFToEbookDialog(self, format_type).exec()

    def save_toolbar_order(self):
        if not hasattr(self, 'toolbar'):
            return
        # Sadece tüm araçlar (klasik) modundayken toolbar sıralamasını kaydet
        if getattr(self, 'active_category', 'cat_all') != 'cat_all':
            return
        order = []
        for act in self.toolbar.actions():
            name = act.objectName()
            if not name:
                w = self.toolbar.widgetForAction(act)
                if w and w.objectName():
                    name = w.objectName()
            if name and name not in order:
                order.append(name)
        if order:
            from src.ui.dialogs.settings_dialog import DEFAULT_TOOLBAR_LAYOUT
            settings = QSettings("AuraPDF", "PDFViewer")
            if order == DEFAULT_TOOLBAR_LAYOUT:
                settings.remove("toolbar_order")
            else:
                import json
                settings.setValue("toolbar_order", json.dumps(order))

    def restore_toolbar_order(self):
        if not hasattr(self, 'toolbar'):
            return
        settings = QSettings("AuraPDF", "PDFViewer")
        raw = settings.value("toolbar_order", None)

        from src.ui.dialogs.settings_dialog import build_full_toolbar_order, DEFAULT_TOOLBAR_LAYOUT

        if not raw:
            final_order = list(DEFAULT_TOOLBAR_LAYOUT)
        else:
            import json
            try:
                if isinstance(raw, str):
                    saved_order = json.loads(raw)
                elif isinstance(raw, list):
                    saved_order = list(raw)
                else:
                    saved_order = []
            except Exception:
                saved_order = []
            final_order = build_full_toolbar_order(saved_order)

        current_actions = self.toolbar.actions()
        actions_map = {}
        for act in current_actions:
            name = act.objectName()
            if not name:
                w = self.toolbar.widgetForAction(act)
                if w and w.objectName():
                    name = w.objectName()
            if name:
                actions_map[name] = act

        ordered_actions = [actions_map[name] for name in final_order if name in actions_map]
        # Kategoriye özel ek butonları ve ayırıcıları da toolbar içinde koru
        for act in current_actions:
            if act not in ordered_actions:
                ordered_actions.append(act)

        if not ordered_actions:
            return

        for act in current_actions:
            self.toolbar.removeAction(act)

        for act in ordered_actions:
            self.toolbar.addAction(act)
            w = self.toolbar.widgetForAction(act)
            if w:
                w.show()

        # Mevcut aktif kategori filtresini tekrar uygula
        if hasattr(self, 'active_category'):
            self.set_active_category(self.active_category)

    def reset_toolbar_order(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.remove("toolbar_order")
        self.restore_toolbar_order()

    def closeEvent(self, event):
        self.save_toolbar_order()
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument):
                widget.save_zoom_setting()
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument) and widget.is_modified:
                base_name = os.path.basename(widget.file_path) if widget.file_path else "Adsız.pdf"
                reply = QMessageBox.question(
                    self,
                    LanguageManager.tr("warning"),
                    LanguageManager.tr("unsaved_changes_warn", filename=base_name),
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Save
                )
                if reply == QMessageBox.StandardButton.Save:
                    self.tab_widget.setCurrentIndex(idx)
                    self.save_pdf()
                    if widget.is_modified:
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
        self.save_current_session()
        if hasattr(self, 'speech_engine') and self.speech_engine:
            try:
                self.speech_engine.stop()
            except Exception:
                pass
        if hasattr(self, '_audio_record_dialog') and self._audio_record_dialog is not None:
            try:
                self._audio_record_dialog.close()
            except Exception:
                pass
        super().closeEvent(event)



