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
                             QFileDialog, QMenu, QStackedLayout, QStackedWidget, QSizePolicy, QLayout, QDialog, QApplication, QSplitter)
from PyQt6.QtGui import (QIcon, QIntValidator, QShortcut, QKeySequence, QColor, QPen, QBrush, QPixmap, QImage, QCursor)
from PyQt6.QtCore import Qt, QPoint, QSettings, QTimer, QEvent, QFileSystemWatcher, pyqtSignal

from src.core.i18n import LanguageManager
from src.core.shortcut_helper import (
    is_mouse_shortcut,
    parse_mouse_shortcut,
    clean_modifiers,
)
from src.ui.icons import ModernIconFactory, AuraIconFactory
from src.ui.cursors import CursorFactory
from src.ui.widgets import (DraggableToolButton, ReorderableToolBar, ModernTabWidget, AuraTabWidget,
                            ThumbnailsDock, ModernSearchBar, AuraSearchBar, FullscreenSlideToolbar,
                            FullscreenReadingHUD)
from src.ui.popups import (SelectionSettingsPopup, TextSettingsPopup, ToolSettingsPopup, 
                           FloatingHUDPreview, PointerSettingsPopup, HighlighterRulerPopup, 
                           CursorPopup, RulerMeasurementPopup, ModernStampPalettePopup)
from src.ui.dialogs.document_properties_dialog import ModernDocumentPropertiesDialog, AuraDocumentPropertiesDialog
from src.document.tab_document import PDFTabDocument
from src.ui.modern_views import (
    ModernTabBarWidget, ModernTabHoverPreview, ModernHeaderBar, ModernAllToolsPanel,
    OrganizePagesWorkspace, ModernRightSidebar, ModernUtilityRail,
    ModernCommandPaletteDialog, get_modern_theme_colors,
    ModernLeftSidebar, ModernExportDrawer, ModernEditDrawer,
    HomeDashboardWorkspace, FloatingQuickToolsCapsule,
    ModernPinnedQuickToolsBar, ModernSecondaryDocPane
)


class EditableZoomWidget(QWidget):
    zoomChanged = pyqtSignal(str)
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
        self.apply_theme(getattr(main_window, 'current_theme', 'gray'))

    def apply_theme(self, theme_name: str = "gray"):
        if theme_name in ("light", "dark", "navy"):
            theme_name = "nord" if theme_name == "navy" else "gray"
        palette = {
            "gray": {"btn": "#3b3f45", "btn_hover": "#4b5159", "lbl": "#2b2d30", "border": "#525862", "border_inner": "#444850", "accent": "#60a5fa", "text": "#ffffff"},
            "emerald": {"btn": "#112a21", "btn_hover": "#1a3d30", "lbl": "#091a14", "border": "#1a3d30", "border_inner": "#112a21", "accent": "#10b981", "text": "#ecfdf5"},
            "purple": {"btn": "#201435", "btn_hover": "#2f1d4d", "lbl": "#150d22", "border": "#321f52", "border_inner": "#201435", "accent": "#a855f7", "text": "#faf5ff"},
            "crimson": {"btn": "#2d1118", "btn_hover": "#401923", "lbl": "#1d0b10", "border": "#441924", "border_inner": "#2d1118", "accent": "#f43f5e", "text": "#fff1f2"},
            "nord": {"btn": "#222b3a", "btn_hover": "#2f3b4f", "lbl": "#181e29", "border": "#313e54", "border_inner": "#222b3a", "accent": "#38bdf8", "text": "#f0f6fc"},
            "vice_city": {"btn": "#240e3b", "btn_hover": "#381458", "lbl": "#160024", "border": "#ff2a85", "border_inner": "#240e3b", "accent": "#00f0ff", "text": "#ffffff"},
            "apple": {"btn": "#262a34", "btn_hover": "#333846", "lbl": "#16181f", "border": "#3a4050", "border_inner": "#262a34", "accent": "#38bdf8", "text": "#f5f5f7"},
        }
        palette["light"] = palette["gray"]
        palette["dark"] = palette["gray"]
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
                color: {p['text']};
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
                color: {p['text']};
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
        self.zoomChanged.emit(text)

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
class AuraPDFViewer(QMainWindow):
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

        self.tab_widget = AuraTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        self.floating_hud = FloatingHUDPreview()
        self.search_bar = AuraSearchBar(self)
        self.fullscreen_toolbar = FullscreenSlideToolbar(self)
        self.fullscreen_reading_hud = FullscreenReadingHUD(self)
        if self.fullscreen_toolbar.edge == self.fullscreen_reading_hud.edge:
            if self.fullscreen_reading_hud.edge == 'bottom':
                self.fullscreen_toolbar._apply_edge_layout('left')
                self.fullscreen_toolbar.edge = 'left'
            else:
                self.fullscreen_reading_hud._apply_edge_layout('bottom')
                self.fullscreen_reading_hud.edge = 'bottom'

        # --- V3 SİSTEM YÖNETİCİLERİ ---
        self.closed_tabs_history = []
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_watched_file_changed)

        self._init_popups()
        self._init_docks()
        self._init_toolbar()
        self._init_modern_ui()
        self._init_shortcuts()
        # Varsayılan görünüm teması gri olsun (Sürüm göçü)
        th_version = settings.value("app_theme_default_version", 0, type=int)
        if th_version < 4 or not settings.contains("app_theme"):
            saved_th = settings.value("app_theme", "gray")
            if th_version < 4 or saved_th in ("light", "dark"):
                settings.setValue("app_theme", "gray")
            settings.setValue("app_theme_default_version", 4)
        self.apply_theme(settings.value("app_theme", "gray"))
        self.retranslate_ui()
        self.update_viewport_cursor()

        # Olay filtresini arayüz tamamen kurulduktan sonra bağla
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self)

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
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_as_pdf)
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.print_pdf)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self.close_tab(self.tab_widget.currentIndex()))

        # V3 Kısayolları (Görünüm Geçmişi, Sekme Kurtarma, Seslendirme, Özellikler, Sığdırma)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.nav_back)
        QShortcut(QKeySequence("Alt+Right"), self, activated=self.nav_forward)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self.reopen_last_closed_tab)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.fit_to_page)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=self.reset_zoom_100)
        QShortcut(QKeySequence("Ctrl+2"), self, activated=self.fit_to_width)
        QShortcut(QKeySequence(Qt.Key.Key_PageUp), self, activated=self.prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_PageDown), self, activated=self.next_page)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.open_document_properties_dialog)
        QShortcut(QKeySequence("F1"), self, activated=self.open_shortcuts_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self.open_compress_dialog)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._open_command_palette)

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
        etype = event.type()
        if etype not in (
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.MouseMove,
        ):
            return super().eventFilter(obj, event)

        # 0. Orta Tuşla Sekme Kapatma (Middle Click Tab Close)
        if etype == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.MiddleButton:
            if hasattr(self, 'tab_widget') and self.tab_widget:
                tab_bar = self.tab_widget.tabBar()
                if tab_bar and obj == tab_bar:
                    tab_idx = tab_bar.tabAt(event.position().toPoint() if hasattr(event, 'position') else event.pos())
                    if tab_idx >= 0:
                        self.close_tab(tab_idx)
                        return True

        # 0B. Merkez Panel Boyut Değişimi -> Kapsül Konumlandırma
        if etype in (QEvent.Type.Resize, QEvent.Type.Move):
            if hasattr(self, 'central_stack') and obj == self.central_stack:
                if (hasattr(self, 'floating_capsule') and self.floating_capsule and self.floating_capsule.isVisible()) or \
                   (hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar and self.top_pinned_tools_bar.isVisible()):
                    self.update_floating_capsule_pos()

        # 1. Fare Kısayolları (Mouse Shortcuts) Kontrolü
        if etype == QEvent.Type.MouseButtonPress:
            if self.handle_mouse_shortcut(event):
                event.accept()
                return True

        if etype == QEvent.Type.MouseMove and self.isFullScreen():
            if hasattr(event, 'globalPosition'):
                global_pos = event.globalPosition().toPoint()
            elif hasattr(event, 'globalPos'):
                global_pos = event.globalPos()
            else:
                global_pos = event.pos()
            win_pos = self.mapFromGlobal(global_pos)

            if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
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

            if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                hud = self.fullscreen_reading_hud
                hud_edge = getattr(hud, 'edge', 'bottom')
                near_hud = False
                if hud_edge == 'left':
                    near_hud = (win_pos.x() <= 35 and 0 <= win_pos.y() <= self.height())
                elif hud_edge == 'right':
                    near_hud = (win_pos.x() >= self.width() - 35 and 0 <= win_pos.y() <= self.height())
                elif hud_edge == 'top':
                    near_hud = (win_pos.y() <= 35 and 0 <= win_pos.x() <= self.width())
                elif hud_edge == 'bottom':
                    near_hud = (win_pos.y() >= self.height() - 35 and 0 <= win_pos.x() <= self.width())

                if near_hud:
                    if not hud.is_slid_in:
                        hud.slide_in()
        return super().eventFilter(obj, event)

    def ensure_distinct_fullscreen_edges(self, moved_widget, target_edge: str):
        """
        Tam ekran modundaki yüzen araç çubuklarının (FullscreenSlideToolbar ve FullscreenReadingHUD)
        aynı kenara sabitlenmesini engeller.
        Eğer hedef kenarda diğer çubuk bulunuyorsa, diğer çubuk boş kenara (veya taşınan
        çubuğun önceki kenarına) otomatik ve pürüzsüz biçimde aktarılır (Mutual Swap).
        """
        if moved_widget is getattr(self, 'fullscreen_toolbar', None):
            other_widget = getattr(self, 'fullscreen_reading_hud', None)
        else:
            other_widget = getattr(self, 'fullscreen_toolbar', None)

        if other_widget is None:
            return

        other_edge = getattr(other_widget, 'edge', None)
        if other_edge == target_edge:
            old_edge = getattr(moved_widget, 'edge', None)
            all_edges = ['left', 'bottom', 'right', 'top']
            if old_edge and old_edge != target_edge:
                swap_to_edge = old_edge
            else:
                available = [e for e in all_edges if e != target_edge]
                swap_to_edge = available[0]

            other_widget._apply_edge_layout(swap_to_edge)
            settings = QSettings("AuraPDF", "PDFViewer")
            setting_key = "fullscreen_toolbar_edge" if other_widget is getattr(self, 'fullscreen_toolbar', None) else "fullscreen_hud_edge"
            settings.setValue(setting_key, swap_to_edge)
            if self.isFullScreen():
                other_widget.slide_in()
                other_widget.hide_timer.start(3000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'search_bar') and self.search_bar.isVisible():
            self.search_bar.reposition()
        if hasattr(self, 'fullscreen_toolbar') and self.isFullScreen():
            self.fullscreen_toolbar.reposition()
        if hasattr(self, 'fullscreen_reading_hud') and self.isFullScreen():
            self.fullscreen_reading_hud.reposition()
        if (hasattr(self, 'floating_capsule') and self.floating_capsule and self.floating_capsule.isVisible()) or \
           (hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar and self.top_pinned_tools_bar.isVisible()):
            self.update_floating_capsule_pos()
        if hasattr(self, '_fs_page_label') and self._fs_page_label and self._fs_page_label.isVisible():
            px = max(10, self.width() - self._fs_page_label.width() - 36)
            py = max(10, self.height() - self._fs_page_label.height() - 36)
            self._fs_page_label.move(px, py)
        if hasattr(self, '_fs_zoom_label') and self._fs_zoom_label and self._fs_zoom_label.isVisible():
            margin_y = 36
            if hasattr(self, '_fs_page_label') and self._fs_page_label and self._fs_page_label.isVisible():
                margin_y += self._fs_page_label.height() + 10
            x = max(10, self.width() - self._fs_zoom_label.width() - 36)
            y = max(10, self.height() - self._fs_zoom_label.height() - margin_y)
            self._fs_zoom_label.move(x, y)

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
                if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                    self.fullscreen_reading_hud.hide_fullscreen_mode()
                if hasattr(self, '_fs_page_label') and self._fs_page_label:
                    self._fs_page_label.hide()
                if hasattr(self, 'btn_fullscreen') and self.btn_fullscreen:
                    self.btn_fullscreen.blockSignals(True)
                    self.btn_fullscreen.setChecked(False)
                    self.btn_fullscreen.blockSignals(False)
                self.tab_widget.tabBar().show()
                sb = self.statusBar()
                if sb and getattr(self, '_statusbar_was_visible', True):
                    sb.show()
                if getattr(self, '_sidebar_was_visible', False) and hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                    self.thumbnails_dock.show()
                if getattr(self, '_left_sidebar_was_visible', False) and hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar:
                    self.modern_left_sidebar.show()
                if getattr(self, '_right_sidebar_was_visible', False) and hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                    self.modern_right_sidebar.show()
            elif not was_fs and is_fs:
                if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                    self.fullscreen_toolbar.show_fullscreen_mode()
                if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                    self.fullscreen_reading_hud.slide_in()
                tab_doc = self.get_current_tab_doc()
                if tab_doc and tab_doc.doc and len(tab_doc.doc) > 0:
                    self.show_fullscreen_page_osd(tab_doc.current_page_idx + 1, len(tab_doc.doc))
                if hasattr(self, 'btn_fullscreen') and self.btn_fullscreen:
                    self.btn_fullscreen.blockSignals(True)
                    self.btn_fullscreen.setChecked(True)
                    self.btn_fullscreen.blockSignals(False)
                if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                    self.thumbnails_dock.hide()
                if hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar:
                    self.modern_left_sidebar.hide()
                if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                    self.modern_right_sidebar.hide()
                if hasattr(self, 'modern_utility_rail') and self.modern_utility_rail:
                    self.modern_utility_rail.hide()
                if hasattr(self, 'floating_capsule') and self.floating_capsule:
                    self.floating_capsule.hide()
                if hasattr(self, 'modern_tab_bar') and self.modern_tab_bar:
                    self.modern_tab_bar.hide()
                if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
                    self.modern_header_bar.hide()
                if hasattr(self, 'toolbar'):
                    self.toolbar.hide()
                sb = self.statusBar()
                if sb:
                    sb.hide()
        elif event.type() == QEvent.Type.DevicePixelRatioChange:
            tab_doc = self.get_current_tab_doc()
            if tab_doc and hasattr(tab_doc, 'rerender_visible_pages'):
                tab_doc.rerender_timer.start(100)
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_screen_hooked', False):
            wh = self.windowHandle()
            if wh:
                try:
                    wh.screenChanged.connect(self._on_screen_changed)
                    self._screen_hooked = True
                except Exception:
                    pass

    def _on_screen_changed(self, screen):
        tab_doc = self.get_current_tab_doc()
        if tab_doc and hasattr(tab_doc, 'rerender_visible_pages'):
            tab_doc.rerender_timer.start(100)

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
        focus_w = QApplication.focusWidget()
        if focus_w:
            # Ekler (attachments) paneli açıksa ve odak ekler listesindeyse, seçili eki sil
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                att_list = getattr(self.modern_right_sidebar, 'list_attachments', None)
                if att_list and (focus_w == att_list or att_list.isAncestorOf(focus_w)):
                    if hasattr(self.modern_right_sidebar, '_delete_selected_attachments'):
                        self.modern_right_sidebar._delete_selected_attachments()
                    return
            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                dock_att = getattr(self.thumbnails_dock, 'list_attachments', None)
                if dock_att and (focus_w == dock_att or dock_att.isAncestorOf(focus_w)):
                    if hasattr(self.thumbnails_dock, '_delete_selected_attachments'):
                        self.thumbnails_dock._delete_selected_attachments()
                    return
            from PyQt6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox
            if isinstance(focus_w, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox)):
                return
            if getattr(focus_w, 'is_text_input', False):
                return
        if doc := self.get_current_tab_doc():
            if getattr(doc, 'direct_edit_editor', None):
                return
            if getattr(doc, 'active_text_item', None):
                it = doc.active_text_item
                if hasattr(it, 'textInteractionFlags') and (it.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction) and it.hasFocus():
                    return
            doc.delete_selected_items()

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

    def toggle_toolbar_visibility(self):
        if hasattr(self, 'floating_capsule') and self.floating_capsule:
            self.floating_capsule.setVisible(not self.floating_capsule.isVisible())

    def _init_docks(self):
        self.thumbnails_dock = ThumbnailsDock(self)
        self.thumbnails_dock.setObjectName("ThumbnailsDock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.thumbnails_dock)
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
        self.stamp_popup = ModernStampPalettePopup(
            parent=self,
            on_stamp_selected=self._on_quick_stamp_selected,
            on_open_custom_dialog=self._open_custom_stamp_dialog
        )
        self.measurement_unit = "cm"
        self.measurement_scale = 1.0

    def set_cursor_mode(self, mode):
        self.cursor_mode = mode
        if hasattr(self, 'btn_cursor') and self.btn_cursor:
            if mode == 'select':
                self.btn_cursor.setIcon(ModernIconFactory.icon_cursor())
            elif mode == 'pan':
                self.btn_cursor.setIcon(ModernIconFactory.icon_select_pan())
        if hasattr(self, 'floating_capsule') and self.floating_capsule:
            self.floating_capsule.update_cursor_mode(mode)
        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
            self.top_pinned_tools_bar.update_cursor_mode(mode)
        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
            self.left_pinned_tools_bar.update_cursor_mode(mode)
        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
            self.right_pinned_tools_bar.update_cursor_mode(mode)
        if mode == 'select':
            self.set_tool_state('select')
        elif mode == 'pan':
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
            if hasattr(self, 'floating_capsule') and self.floating_capsule:
                self.floating_capsule.update_selection_mode('ruler')
            if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
                self.top_pinned_tools_bar.update_selection_mode('ruler')
            if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
                self.left_pinned_tools_bar.update_selection_mode('ruler')
            if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
                self.right_pinned_tools_bar.update_selection_mode('ruler')
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
        if hasattr(self, 'floating_capsule') and self.floating_capsule:
            self.floating_capsule.update_selection_mode(mode)
        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
            self.top_pinned_tools_bar.update_selection_mode(mode)
        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
            self.left_pinned_tools_bar.update_selection_mode(mode)
        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
            self.right_pinned_tools_bar.update_selection_mode(mode)
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
        self.toolbar = ReorderableToolBar("Aura Toolbar", self)
        self.toolbar.setObjectName("AuraToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.hide()

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
        self.btn_selection.setIcon(ModernIconFactory.icon_select_rect())
        self.btn_selection.setText(" ⌵")
        self.btn_selection.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_selection.setCheckable(True)
        self.btn_selection.clicked.connect(self.handle_selection_button_click)
        self.btn_selection.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_selection.customContextMenuRequested.connect(lambda pos: self.selection_popup.show_below(self.btn_selection))
        self._add_toolbar_widget(self.btn_selection, "btn_selection")

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

        self.btn_direct_edit = DraggableToolButton()
        self.btn_direct_edit.setIcon(ModernIconFactory.icon_edit_content())
        self.btn_direct_edit.setToolTip(LanguageManager.tr("direct_edit_tool_tip"))
        self.btn_direct_edit.setCheckable(True)
        self.btn_direct_edit.clicked.connect(lambda: self.handle_tool_click('direct_edit', self.btn_direct_edit, None))
        self._add_toolbar_widget(self.btn_direct_edit, "btn_direct_edit")

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
        self.act_read_light = read_menu.addAction(LanguageManager.tr("reading_mode_light"))
        self.act_read_light.triggered.connect(lambda: self.set_reading_color_mode("normal"))
        self.act_read_dark = read_menu.addAction(LanguageManager.tr("reading_mode_dark"))
        self.act_read_dark.triggered.connect(lambda: self.set_reading_color_mode("dark"))
        self.act_read_sepia = read_menu.addAction(LanguageManager.tr("reading_mode_sepia"))
        self.act_read_sepia.triggered.connect(lambda: self.set_reading_color_mode("sepia"))
        self.btn_reading_mode.setMenu(read_menu)
        self._add_toolbar_widget(self.btn_reading_mode, "btn_reading_mode")

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

        self.restore_toolbar_order()
        self.update_undo_redo_state()

        if hasattr(self, 'toolbar'):
            self.toolbar.hide()

    def _init_modern_ui(self):
        """Adobe Acrobat yeni nesil modern arayüzünü (Sekmeler, Header, Araçlar, Organize, Sağ Çekmece, Ray) kurar."""
        self.tab_widget.tabBar().hide()

        # 1. Doküman Sekmeleri Çubuğu (En üst satır: Home + Yeni Sekme + Sekmeler)
        self.modern_tab_bar = ModernTabBarWidget(self)
        self.modern_tab_bar.tabCloseRequested.connect(self.close_tab)
        self.modern_tab_bar.currentChanged.connect(self._on_modern_tab_changed)
        self.modern_tab_bar.newTabRequested.connect(self.open_pdf)
        self.modern_tab_bar.homeRequested.connect(self.switch_to_home_view)
        self.modern_tab_bar.helpRequested.connect(self.open_shortcuts_dialog)
        self.tab_hover_preview = ModernTabHoverPreview(self)
        self._pending_hover_tab = None
        self._tab_hover_timer = QTimer(self)
        self._tab_hover_timer.setSingleShot(True)
        self._tab_hover_timer.timeout.connect(self._show_pending_tab_preview)
        self._tab_hide_timer = QTimer(self)
        self._tab_hide_timer.setSingleShot(True)
        self._tab_hide_timer.timeout.connect(self._do_hide_tab_preview)

        self.modern_tab_bar.tabHoverEntered.connect(self._on_tab_hover_entered)
        self.modern_tab_bar.tabHoverLeft.connect(self._on_tab_hover_left)

        # 2. Üst Gezinme ve Eylem Çubuğu
        self.modern_header_bar = ModernHeaderBar(self)
        self.modern_header_bar.modeChanged.connect(self._on_header_mode_changed)
        self.modern_header_bar.menuRequested.connect(self._show_main_menu)
        self.modern_header_bar.searchRequested.connect(self._open_command_palette)
        self.modern_header_bar.helpRequested.connect(self.open_shortcuts_dialog)
        self.modern_header_bar.printRequested.connect(self.print_pdf)
        self.modern_header_bar.saveRequested.connect(self.save_pdf)
        if hasattr(self.modern_header_bar, 'settingsRequested'):
            self.modern_header_bar.settingsRequested.connect(self.open_settings_dialog)
        if hasattr(self.modern_header_bar, 'fullscreenRequested'):
            self.modern_header_bar.fullscreenRequested.connect(self.toggle_fullscreen)
        self._pending_ai_action = None

        self.modern_header_bar.pageJumpRequested.connect(self._on_rail_page_jump)
        self.modern_header_bar.prevPageRequested.connect(self.prev_page)
        self.modern_header_bar.nextPageRequested.connect(self.next_page)
        self.modern_header_bar.zoomInRequested.connect(self.zoom_in)
        self.modern_header_bar.zoomOutRequested.connect(self.zoom_out)
        self.modern_header_bar.fitPageRequested.connect(self.toggle_fit_page_width)
        self.modern_header_bar.rotateRequested.connect(self.rotate_current_page)
        self.modern_header_bar.zoomSetRequested.connect(self._on_zoom_input_submitted)
        self.modern_header_bar.multiviewRequested.connect(self.toggle_multiview)

        # 3. Sol Çekmece Yığını: Tüm Araçlar / Export / Edit / Read
        self.modern_left_sidebar = ModernLeftSidebar(main_window=self, parent=self)
        self.modern_left_sidebar.toolTriggered.connect(self._on_all_tools_panel_action)
        self.modern_left_sidebar.exportTriggered.connect(self._on_export_drawer_action)
        self.modern_left_sidebar.editTriggered.connect(self._on_edit_drawer_action)
        self.modern_left_sidebar.readTriggered.connect(self._on_read_drawer_action)
        self.modern_left_sidebar.fillSignTriggered.connect(self._on_fill_sign_tool_triggered)
        self.modern_left_sidebar.prepareFormTriggered.connect(self._on_prepare_form_action)
        self.modern_left_sidebar.closeRequested.connect(self._close_left_sidebar)
        self.modern_tools_panel = self.modern_left_sidebar.all_tools_panel

        # 4. Merkez Yığın: Ana Sayfa (0) vs Doküman Görünümü (1) vs Organize Et (2)
        self.home_workspace = HomeDashboardWorkspace(main_window=self, parent=self)
        self.home_workspace.openFileRequested.connect(self.open_pdf)
        self.home_workspace.fileSelected.connect(self.add_pdf_tab)
        self.home_workspace.toolRequested.connect(self._on_home_tool_requested)

        self.organize_workspace = OrganizePagesWorkspace(main_window=self, parent=self)
        self.organize_workspace.closeRequested.connect(self._close_organize_workspace)
        self.organize_workspace.openPageRequested.connect(self._on_organize_open_page)
        self.organize_workspace.documentModified.connect(self._on_organize_doc_modified)

        # 4A. Multiview ve Belge Bölünmüş Alanı (Document Splitter: Sol TabWidget, Sağ Secondary Pane)
        self.document_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.document_splitter.setObjectName("DocumentSplitter")
        self.document_splitter.setChildrenCollapsible(False)
        self.document_splitter.addWidget(self.tab_widget)

        self.secondary_split_pane = ModernSecondaryDocPane(main_window=self, parent=self)
        self.secondary_split_pane.closeRequested.connect(self.close_multiview)
        self.secondary_split_pane.swapRequested.connect(self.swap_multiview_documents)
        self.secondary_split_pane.syncScrollToggled.connect(self._on_multiview_sync_scroll_toggled)
        self.document_splitter.addWidget(self.secondary_split_pane)
        self.secondary_split_pane.hide()

        self.central_stack = QStackedWidget(self)
        self.central_stack.addWidget(self.home_workspace)
        self.central_stack.addWidget(self.document_splitter)
        self.central_stack.addWidget(self.organize_workspace)

        # 4B. Yüzen Hızlı Araç Kapsülü (FloatingQuickToolsCapsule)
        self.floating_capsule = FloatingQuickToolsCapsule(parent=self, main_window=self)
        self.floating_capsule.toolSelectedWithWidget.connect(self._on_floating_tool_selected)
        self.floating_capsule.pinToTopRequested.connect(self.dock_capsule_to_top)
        self.floating_capsule.pinToLeftRequested.connect(self.dock_capsule_to_left)
        self.floating_capsule.pinToRightRequested.connect(self.dock_capsule_to_right)
        self.floating_capsule.hide()
        dock_pos = QSettings("AuraPDF", "PDFViewer").value("capsule_dock_position", "float", type=str)
        self.capsule_docked_to_top = (dock_pos == "top") or QSettings("AuraPDF", "PDFViewer").value("capsule_docked_to_top", False, type=bool)
        self.capsule_docked_to_left = (dock_pos == "left") or QSettings("AuraPDF", "PDFViewer").value("capsule_docked_to_left", False, type=bool)
        self.capsule_docked_to_right = (dock_pos == "right") or QSettings("AuraPDF", "PDFViewer").value("capsule_docked_to_right", False, type=bool)

        # 4C. Üst ve Yan Araç Çubuklarına Sabitlenebilir Kapsüller
        self.top_pinned_tools_bar = ModernPinnedQuickToolsBar(self)
        self.top_pinned_tools_bar.toolSelectedWithWidget.connect(self._on_floating_tool_selected)
        self.top_pinned_tools_bar.unpinRequested.connect(self.undock_capsule_from_top)
        self.top_pinned_tools_bar.hide()

        self.left_pinned_tools_bar = ModernPinnedQuickToolsBar(self, orientation=Qt.Orientation.Vertical)
        self.left_pinned_tools_bar.hide()
        self.left_pinned_tools_bar.unpinRequested.connect(self.undock_capsule_from_left)
        self.left_pinned_tools_bar.toolSelectedWithWidget.connect(self._on_floating_tool_selected)

        # 4D. Sağ Araç Çubuğuna Sabitlenebilir Dikey Kapsül (Right Pinned Toolbar)
        self.right_pinned_tools_bar = ModernPinnedQuickToolsBar(self, orientation=Qt.Orientation.Vertical)
        self.right_pinned_tools_bar.hide()
        self.right_pinned_tools_bar.unpinRequested.connect(self.undock_capsule_from_right)
        self.right_pinned_tools_bar.toolSelectedWithWidget.connect(self._on_floating_tool_selected)

        self.top_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
        self.left_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
        self.right_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)

        self.central_stack.installEventFilter(self)
        if hasattr(self, 'tab_widget') and hasattr(self.tab_widget, 'tabBar') and self.tab_widget.tabBar():
            self.tab_widget.tabBar().installEventFilter(self)

        # 5. Sağ Çekmece: Yer İmleri / Yorumlar
        self.modern_right_sidebar = ModernRightSidebar(main_window=self, parent=self)
        self.modern_right_sidebar.closeRequested.connect(self._close_right_sidebar)
        self.modern_right_sidebar.bookmarkClicked.connect(self._on_bookmark_clicked)
        self.modern_right_sidebar.thumbnailClicked.connect(self._on_bookmark_clicked)

        # 6. En Sağ Dikey İkon Rayı
        self.modern_utility_rail = ModernUtilityRail(self)
        self.modern_utility_rail.railItemToggled.connect(self._on_utility_rail_toggled)
        self.modern_utility_rail.fullscreenRequested.connect(self.toggle_fullscreen)

        # Ana Kök Yerleşim
        self.modern_root_widget = QWidget(self)
        self.modern_root_layout = QVBoxLayout(self.modern_root_widget)
        self.modern_root_layout.setContentsMargins(0, 0, 0, 0)
        self.modern_root_layout.setSpacing(0)

        self.modern_root_layout.addWidget(self.modern_tab_bar)
        self.modern_root_layout.addWidget(self.modern_header_bar)

        self.body_container = QWidget(self)
        self.body_layout = QHBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        self.update_panels_layout()

        self.modern_root_layout.addWidget(self.body_container, stretch=1)
        self.setCentralWidget(self.modern_root_widget)

        # Sayfa / Zoom güncellemelerini ray'e bağla
        if hasattr(self, 'txt_page') and self.txt_page:
            self.txt_page.textChanged.connect(self._sync_rail_page)
        if hasattr(self, 'lbl_zoom') and hasattr(self.lbl_zoom, 'zoomChanged'):
            self.lbl_zoom.zoomChanged.connect(lambda txt: self.modern_header_bar.txt_zoom.setText(txt.strip()))

        # Başlangıç durumu:
        self.central_stack.setCurrentWidget(self.home_workspace)
        self.modern_tab_bar.set_home_active(True)
        self.modern_left_sidebar.set_page("all_tools")
        self.modern_right_sidebar.hide()
        self.modern_utility_rail.hide()
        if hasattr(self, 'toolbar'):
            self.toolbar.hide()

    def update_floating_capsule_pos(self):
        if hasattr(self, 'top_pinned_tools_bar') and getattr(self, 'capsule_docked_to_top', False) and self.top_pinned_tools_bar.isVisible():
            if hasattr(self, 'central_stack'):
                self.top_pinned_tools_bar.adjustSize()
                c_rect = self.central_stack.rect()
                pt = self.central_stack.mapTo(self, QPoint((c_rect.width() - self.top_pinned_tools_bar.width()) // 2, 8))
                self.top_pinned_tools_bar.move(pt)
                self.top_pinned_tools_bar.raise_()

        if hasattr(self, 'floating_capsule') and hasattr(self, 'central_stack'):
            if getattr(self, 'capsule_docked_to_top', False) or getattr(self, 'capsule_docked_to_left', False) or getattr(self, 'capsule_docked_to_right', False):
                return

            p_rect = self.rect()
            p_w = max(100, p_rect.width())
            p_h = max(100, p_rect.height())
            cap_w = self.floating_capsule.width() if self.floating_capsule.width() > 0 else 52
            cap_h = self.floating_capsule.height() if self.floating_capsule.height() > 0 else 436
            max_x = max(0, p_w - cap_w)
            max_y = max(0, p_h - cap_h)

            settings = QSettings("AuraPDF", "PDFViewer")
            if settings.contains("capsule_float_x") and settings.contains("capsule_float_y"):
                self.floating_capsule.user_moved = True
                if settings.contains("capsule_float_rx") and settings.contains("capsule_float_ry"):
                    rx = settings.value("capsule_float_rx", type=float)
                    ry = settings.value("capsule_float_ry", type=float)
                    cur_x = int(rx * p_w)
                    cur_y = int(ry * p_h)
                else:
                    cur_x = settings.value("capsule_float_x", self.floating_capsule.x(), type=int)
                    cur_y = settings.value("capsule_float_y", self.floating_capsule.y(), type=int)
            elif getattr(self.floating_capsule, 'user_moved', False):
                cur_x = self.floating_capsule.x()
                cur_y = self.floating_capsule.y()
            else:
                pt = self.central_stack.mapTo(self, QPoint(14, 24))
                cur_x = pt.x()
                cur_y = pt.y()

            target_x = max(0, min(cur_x, max_x))
            target_y = max(0, min(cur_y, max_y))
            self.floating_capsule.move(target_x, target_y)
            self.floating_capsule.raise_()

    def dock_capsule_to_top(self):
        """Hareketli araç çubuğunu üst araç çubuğuna sabitler."""
        self.capsule_docked_to_top = True
        self.capsule_docked_to_left = False
        self.capsule_docked_to_right = False
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("capsule_docked_to_top", True)
        settings.setValue("capsule_docked_to_left", False)
        settings.setValue("capsule_docked_to_right", False)
        settings.setValue("capsule_dock_position", "top")
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.hide()
        if hasattr(self, 'left_pinned_tools_bar'):
            self.left_pinned_tools_bar.hide()
        if hasattr(self, 'right_pinned_tools_bar'):
            self.right_pinned_tools_bar.hide()
        if hasattr(self, 'top_pinned_tools_bar'):
            if hasattr(self, 'floating_capsule'):
                self.top_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                self.top_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
            if self.tab_widget.count() > 0 and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                self.top_pinned_tools_bar.show()
                self.update_floating_capsule_pos()

    def dock_capsule_to_left(self):
        """Hareketli araç çubuğunu sol araç çubuğuna sabitler."""
        self.capsule_docked_to_top = False
        self.capsule_docked_to_left = True
        self.capsule_docked_to_right = False
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("capsule_docked_to_top", False)
        settings.setValue("capsule_docked_to_left", True)
        settings.setValue("capsule_docked_to_right", False)
        settings.setValue("capsule_dock_position", "left")
        if hasattr(self, 'top_pinned_tools_bar'):
            self.top_pinned_tools_bar.hide()
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.hide()
        if hasattr(self, 'right_pinned_tools_bar'):
            self.right_pinned_tools_bar.hide()
        if hasattr(self, 'left_pinned_tools_bar'):
            if hasattr(self, 'floating_capsule'):
                self.left_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                self.left_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
            if self.tab_widget.count() > 0 and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                self.left_pinned_tools_bar.show()

    def dock_capsule_to_right(self):
        """Hareketli araç çubuğunu sağ araç çubuğuna sabitler."""
        self.capsule_docked_to_top = False
        self.capsule_docked_to_left = False
        self.capsule_docked_to_right = True
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("capsule_docked_to_top", False)
        settings.setValue("capsule_docked_to_left", False)
        settings.setValue("capsule_docked_to_right", True)
        settings.setValue("capsule_dock_position", "right")
        if hasattr(self, 'top_pinned_tools_bar'):
            self.top_pinned_tools_bar.hide()
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.hide()
        if hasattr(self, 'left_pinned_tools_bar'):
            self.left_pinned_tools_bar.hide()
        if hasattr(self, 'right_pinned_tools_bar'):
            if hasattr(self, 'floating_capsule'):
                self.right_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                self.right_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
            if self.tab_widget.count() > 0 and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                self.right_pinned_tools_bar.show()

    def undock_capsule_from_top(self):
        self.undock_capsule()

    def undock_capsule_from_left(self):
        self.undock_capsule()

    def undock_capsule_from_right(self):
        self.undock_capsule()

    def undock_capsule(self):
        """Sabitlenmiş araçları serbest yüzen hareketli moda döndürür."""
        self.capsule_docked_to_top = False
        self.capsule_docked_to_left = False
        self.capsule_docked_to_right = False
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("capsule_docked_to_top", False)
        settings.setValue("capsule_docked_to_left", False)
        settings.setValue("capsule_docked_to_right", False)
        settings.setValue("capsule_dock_position", "float")
        active_tool = "select"
        if hasattr(self, 'top_pinned_tools_bar'):
            if self.top_pinned_tools_bar.isVisible():
                active_tool = self.top_pinned_tools_bar.active_tool
            self.top_pinned_tools_bar.hide()
        if hasattr(self, 'left_pinned_tools_bar'):
            if self.left_pinned_tools_bar.isVisible():
                active_tool = self.left_pinned_tools_bar.active_tool
            self.left_pinned_tools_bar.hide()
        if hasattr(self, 'right_pinned_tools_bar'):
            if self.right_pinned_tools_bar.isVisible():
                active_tool = self.right_pinned_tools_bar.active_tool
            self.right_pinned_tools_bar.hide()
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.set_active_tool(active_tool)
            if self.tab_widget.count() > 0 and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                self.update_floating_capsule_pos()
                self.floating_capsule.show()
                self.floating_capsule.raise_()

    def update_panels_layout(self, layout_mode: Optional[str] = None):
        """Tüm Araçlar paneli ile Gezinme / Yardımcı Ray panellerinin ekran yerleşimini (Sol / Sağ) ayarlar."""
        if layout_mode is None:
            settings = QSettings("AuraPDF", "PDFViewer")
            layout_mode = settings.value("sidebar_layout", "tools_right_nav_left", type=str)
        self.sidebar_layout_mode = layout_mode

        if getattr(self, 'body_layout', None) is not None:
            # Önce mevcut bileşenleri yerleşimden çıkar
            for w in [
                getattr(self, 'modern_utility_rail', None),
                getattr(self, 'modern_right_sidebar', None),
                getattr(self, 'left_pinned_tools_bar', None),
                getattr(self, 'central_stack', None),
                getattr(self, 'right_pinned_tools_bar', None),
                getattr(self, 'modern_left_sidebar', None)
            ]:
                if w is not None:
                    self.body_layout.removeWidget(w)

            # İstenen sıralamayla yeniden ekle
            if layout_mode == "tools_right_nav_left":
                # Solda Gezinme Rayı & Çekmecesi, Sağda Tüm Araçlar
                self.body_layout.addWidget(self.modern_utility_rail)
                self.body_layout.addWidget(self.modern_right_sidebar)
                self.body_layout.addWidget(self.left_pinned_tools_bar)
                self.body_layout.addWidget(self.central_stack, stretch=1)
                self.body_layout.addWidget(self.right_pinned_tools_bar)
                self.body_layout.addWidget(self.modern_left_sidebar)

                if hasattr(self, 'modern_utility_rail') and hasattr(self.modern_utility_rail, 'set_dock_side'):
                    self.modern_utility_rail.set_dock_side("left")
                if hasattr(self, 'modern_right_sidebar') and hasattr(self.modern_right_sidebar, 'set_dock_side'):
                    self.modern_right_sidebar.set_dock_side("left")
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'set_dock_side'):
                    self.modern_left_sidebar.set_dock_side("right")
            else:
                # Varsayılan: Solda Tüm Araçlar, Sağda Gezinme Rayı & Çekmecesi
                self.body_layout.addWidget(self.modern_left_sidebar)
                self.body_layout.addWidget(self.left_pinned_tools_bar)
                self.body_layout.addWidget(self.central_stack, stretch=1)
                self.body_layout.addWidget(self.right_pinned_tools_bar)
                self.body_layout.addWidget(self.modern_right_sidebar)
                self.body_layout.addWidget(self.modern_utility_rail)

                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'set_dock_side'):
                    self.modern_left_sidebar.set_dock_side("left")
                if hasattr(self, 'modern_right_sidebar') and hasattr(self.modern_right_sidebar, 'set_dock_side'):
                    self.modern_right_sidebar.set_dock_side("right")
                if hasattr(self, 'modern_utility_rail') and hasattr(self.modern_utility_rail, 'set_dock_side'):
                    self.modern_utility_rail.set_dock_side("right")

            if hasattr(self, '_center_active_document'):
                self._center_active_document()

    def sync_modern_tabs(self):
        """Modern üst sekme çubuğunu AuraTabWidget içeriği ile tam senkronize eder."""
        if not hasattr(self, 'modern_tab_bar') or not hasattr(self, 'tab_widget'):
            return
        target_count = self.tab_widget.count()
        curr_count = self.modern_tab_bar.count()
        if curr_count != target_count:
            while self.modern_tab_bar.count() > 0:
                self.modern_tab_bar.remove_tab(0)
            for i in range(target_count):
                title = self.tab_widget.tabText(i)
                self.modern_tab_bar.add_tab(title)
        else:
            for i in range(target_count):
                self.modern_tab_bar.set_tab_text(i, self.tab_widget.tabText(i))
        if target_count > 0:
            self.modern_tab_bar.set_current_index(self.tab_widget.currentIndex())
        else:
            self.switch_to_home_view()

    def _on_modern_tab_changed(self, index: int):
        self._do_hide_tab_preview()
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)
            self.switch_to_document_view()
            if hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.organize_workspace.load_document()
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                if self.modern_right_sidebar.current_panel == "thumbnails":
                    self.modern_right_sidebar.load_thumbnails()
                elif self.modern_right_sidebar.current_panel == "bookmarks":
                    self.modern_right_sidebar.load_bookmarks()
                elif self.modern_right_sidebar.current_panel == "comments":
                    self.modern_right_sidebar.load_comments()

    def _on_header_mode_changed(self, mode: str):
        if self.isFullScreen():
            return
        is_on_home = hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.home_workspace
        if mode == "all_tools":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("all_tools")
            if not is_on_home and self.tab_widget.count() > 0:
                self.switch_to_document_view()
            else:
                self.switch_to_home_view()
        elif mode == "read":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("read")
            if not is_on_home and self.tab_widget.count() > 0:
                self.switch_to_document_view()
            else:
                self.switch_to_home_view()
        elif mode == "edit":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("edit")
            if not is_on_home and self.tab_widget.count() > 0:
                self.switch_to_document_view()
            else:
                self.switch_to_home_view()
        elif mode == "convert":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("export")
            if not is_on_home and self.tab_widget.count() > 0:
                self.switch_to_document_view()
            else:
                self.switch_to_home_view()
        elif mode == "esign":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("esign")
            if not is_on_home and self.tab_widget.count() > 0:
                self.switch_to_document_view()
            else:
                self.switch_to_home_view()

    def _on_tab_hover_entered(self, index: int, pos: QPoint):
        if hasattr(self, '_tab_hide_timer'):
            self._tab_hide_timer.stop()

        # 1. Kullanıcı tercihi kapalıysa önizleme kartı açma
        settings = QSettings("AuraPDF", "PDFViewer")
        if not settings.value("show_tab_preview", False, type=bool):
            self._do_hide_tab_preview()
            return

        self._pending_hover_tab = (index, pos)
        if hasattr(self, 'tab_hover_preview') and self.tab_hover_preview.isVisible():
            self._show_pending_tab_preview()
        elif hasattr(self, '_tab_hover_timer'):
            # Hızlı ve akıcı kart belirmesi için 280ms bekleme
            self._tab_hover_timer.start(280)

    def _show_pending_tab_preview(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        if not settings.value("show_tab_preview", False, type=bool):
            self._do_hide_tab_preview()
            return
        if not getattr(self, '_pending_hover_tab', None):
            return
        index, pos = self._pending_hover_tab
        if not hasattr(self, 'tab_widget') or not (0 <= index < self.tab_widget.count()):
            return
        tab_doc = self.tab_widget.widget(index)
        if not tab_doc or not getattr(tab_doc, 'doc', None) or len(tab_doc.doc) == 0:
            return
        try:
            curr_page = getattr(tab_doc, 'current_page_idx', 0)
            if curr_page < 0 or curr_page >= len(tab_doc.doc):
                curr_page = 0
            qpix = None
            if hasattr(tab_doc, 'get_page_preview_pixmap'):
                qpix = tab_doc.get_page_preview_pixmap(curr_page, 190.0, 230.0)

            if not qpix or qpix.isNull():
                page = tab_doc.doc[curr_page]
                rect = page.rect
                target_w = 190.0
                target_h = 230.0
                scale = min(target_w / max(rect.width, 1.0), target_h / max(rect.height, 1.0))
                scale = max(0.05, min(scale, 1.5))
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                qpix = QPixmap.fromImage(qimg)

            title = self.tab_widget.tabText(index) or getattr(tab_doc, 'custom_title', '')
            if title:
                title = title.lstrip("*").strip()
            elif getattr(tab_doc, 'file_path', None):
                title = os.path.basename(tab_doc.file_path)
            if not title:
                title = LanguageManager.tr("untitled")

            total_pages = len(tab_doc.doc)
            page_text = LanguageManager.tr("tab_hover_page_info", curr=curr_page + 1, total=total_pages)

            if hasattr(self, 'tab_hover_preview'):
                self.tab_hover_preview.apply_theme(self.current_theme)
                self.tab_hover_preview.show_preview(title, page_text, qpix, pos)
        except Exception:
            pass

    def _on_tab_hover_left(self, index: int):
        if hasattr(self, '_tab_hover_timer'):
            self._tab_hover_timer.stop()
        if hasattr(self, '_tab_hide_timer'):
            self._tab_hide_timer.start(120)

    def _do_hide_tab_preview(self):
        self._pending_hover_tab = None
        if hasattr(self, 'tab_hover_preview'):
            self.tab_hover_preview.hide()

    def switch_to_home_view(self):
        if hasattr(self, 'home_workspace'):
            self.home_workspace.load_recent_files()
            self.central_stack.setCurrentWidget(self.home_workspace)
        if hasattr(self, 'modern_tab_bar'):
            self.modern_tab_bar.set_home_active(True)
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.hide()
        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'pinned_tools_capsule'):
            if hasattr(self, 'top_pinned_tools_bar'): self.top_pinned_tools_bar.hide()
        if hasattr(self, 'left_pinned_tools_bar'):
            self.left_pinned_tools_bar.hide()
        if hasattr(self, 'right_pinned_tools_bar'):
            self.right_pinned_tools_bar.hide()
        if hasattr(self, 'toolbar'):
            self.toolbar.hide()
        if hasattr(self, 'modern_right_sidebar'):
            self.modern_right_sidebar.hide()
        if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
            self.thumbnails_dock.hide()
        if hasattr(self, 'modern_utility_rail'):
            self.modern_utility_rail.hide()

    def update_zoom_display(self, zoom_percent: int):
        if hasattr(self, 'lbl_zoom') and self.lbl_zoom:
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=zoom_percent)} ")
        if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
            self.modern_header_bar.update_zoom_info(zoom_percent)
        if self.isFullScreen():
            self.show_fullscreen_zoom_osd(zoom_percent)

    def show_fullscreen_zoom_osd(self, zoom_percent: int):
        """Tam ekranda yakınlaştırma yapıldığında sağ altta şık bir rozet gösterir ve yumuşakça kaybolur."""
        from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt

        if hasattr(self, '_fs_zoom_timer') and self._fs_zoom_timer:
            try:
                self._fs_zoom_timer.stop()
            except Exception:
                pass

        if hasattr(self, '_fs_zoom_anim') and self._fs_zoom_anim:
            try:
                self._fs_zoom_anim.stop()
            except Exception:
                pass

        if not hasattr(self, '_fs_zoom_label') or not self._fs_zoom_label:
            lbl = QLabel(self)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._fs_zoom_label = lbl
            effect = QGraphicsOpacityEffect(lbl)
            lbl.setGraphicsEffect(effect)
            self._fs_zoom_effect = effect
        else:
            lbl = self._fs_zoom_label
            effect = self._fs_zoom_effect

        lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 220);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.20);
                padding: 10px 22px;
                border-radius: 20px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)

        text = LanguageManager.tr("percent_format", val=zoom_percent)
        lbl.setText(f"{text}")
        lbl.adjustSize()

        margin_x = 36
        margin_y = 36
        if hasattr(self, '_fs_page_label') and self._fs_page_label and self._fs_page_label.isVisible():
            margin_y += self._fs_page_label.height() + 10
        x = max(10, self.width() - lbl.width() - margin_x)
        y = max(10, self.height() - lbl.height() - margin_y)
        lbl.move(x, y)
        effect.setOpacity(1.0)
        lbl.show()
        lbl.raise_()

        from PyQt6.QtCore import QSettings
        enable_anim = QSettings("AuraPDF", "PDFViewer").value("enable_animations", True, type=bool)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(500 if enable_anim else 0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(lambda: lbl.hide() if effect.opacity() == 0.0 else None)
        self._fs_zoom_anim = anim

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(anim.start)
        self._fs_zoom_timer = timer
        timer.start(1200)

    def show_fullscreen_page_osd(self, curr_page: int, total_pages: int, custom_label: str = None):
        """Tam ekranda sayfa değiştiğinde sağ altta sayfa numarasını ve toplam sayıyı gösterir ve yumuşakça kaybolur."""
        from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt, QSettings

        if not self.isFullScreen():
            return

        if hasattr(self, '_fs_page_timer') and self._fs_page_timer:
            try:
                self._fs_page_timer.stop()
            except Exception:
                pass

        if hasattr(self, '_fs_page_anim') and self._fs_page_anim:
            try:
                self._fs_page_anim.stop()
            except Exception:
                pass

        if not hasattr(self, '_fs_page_label') or not self._fs_page_label:
            lbl = QLabel(self)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._fs_page_label = lbl
            effect = QGraphicsOpacityEffect(lbl)
            lbl.setGraphicsEffect(effect)
            self._fs_page_effect = effect
        else:
            lbl = self._fs_page_label
            effect = self._fs_page_effect

        lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 225);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.22);
                padding: 10px 22px;
                border-radius: 20px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
        """)

        text = LanguageManager.tr("fs_page_osd", curr=curr_page, total=total_pages)
        if custom_label:
            text = f"{text} ({custom_label})"
        lbl.setText(text)
        lbl.adjustSize()

        margin_x = 36
        margin_y = 36
        x = max(10, self.width() - lbl.width() - margin_x)
        y = max(10, self.height() - lbl.height() - margin_y)
        lbl.move(x, y)

        if hasattr(self, '_fs_zoom_label') and self._fs_zoom_label and self._fs_zoom_label.isVisible():
            zoom_x = max(10, self.width() - self._fs_zoom_label.width() - margin_x)
            zoom_y = max(10, y - self._fs_zoom_label.height() - 10)
            self._fs_zoom_label.move(zoom_x, zoom_y)

        effect.setOpacity(1.0)
        lbl.show()
        lbl.raise_()

        enable_anim = QSettings("AuraPDF", "PDFViewer").value("enable_animations", True, type=bool)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(500 if enable_anim else 0)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(lambda: lbl.hide() if effect.opacity() == 0.0 else None)
        self._fs_page_anim = anim

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(anim.start)
        self._fs_page_timer = timer
        timer.start(1800)

    def open_search_bar(self):
        if hasattr(self, 'search_bar'):
            self.search_bar.show()
            self.search_bar.txt_find.setFocus()
            self.search_bar.txt_find.selectAll()

    def open_compare_dialog(self):
        self.open_pdf_compare_dialog()

    def show_doc_properties(self):
        self.open_document_properties_dialog()

    def switch_to_document_view(self):
        if self.tab_widget.count() > 0:
            target_widget = getattr(self, 'document_splitter', self.tab_widget)
            self.central_stack.setCurrentWidget(target_widget)
            if hasattr(self, 'modern_tab_bar'):
                self.modern_tab_bar.set_home_active(False)
            if self.isFullScreen():
                if hasattr(self, 'floating_capsule'):
                    self.floating_capsule.hide()
                if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'pinned_tools_capsule'):
                    if hasattr(self, 'top_pinned_tools_bar'): self.top_pinned_tools_bar.hide()
                if hasattr(self, 'left_pinned_tools_bar'):
                    self.left_pinned_tools_bar.hide()
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.hide()
                if hasattr(self, 'modern_right_sidebar'):
                    self.modern_right_sidebar.hide()
                if hasattr(self, 'modern_left_sidebar'):
                    self.modern_left_sidebar.hide()
                return
            if getattr(self, 'capsule_docked_to_top', False):
                if hasattr(self, 'floating_capsule'):
                    self.floating_capsule.hide()
                if hasattr(self, 'left_pinned_tools_bar'):
                    self.left_pinned_tools_bar.hide()
                if hasattr(self, 'right_pinned_tools_bar'):
                    self.right_pinned_tools_bar.hide()
                if hasattr(self, 'top_pinned_tools_bar'):
                    if hasattr(self, 'floating_capsule'):
                        self.top_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                        self.top_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
                    self.top_pinned_tools_bar.show()
                    self.update_floating_capsule_pos()
            elif getattr(self, 'capsule_docked_to_left', False):
                if hasattr(self, 'floating_capsule'):
                    self.floating_capsule.hide()
                if hasattr(self, 'top_pinned_tools_bar'):
                    self.top_pinned_tools_bar.hide()
                if hasattr(self, 'right_pinned_tools_bar'):
                    self.right_pinned_tools_bar.hide()
                if hasattr(self, 'left_pinned_tools_bar'):
                    if hasattr(self, 'floating_capsule'):
                        self.left_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                        self.left_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
                    self.left_pinned_tools_bar.show()
            elif getattr(self, 'capsule_docked_to_right', False):
                if hasattr(self, 'floating_capsule'):
                    self.floating_capsule.hide()
                if hasattr(self, 'top_pinned_tools_bar'):
                    self.top_pinned_tools_bar.hide()
                if hasattr(self, 'left_pinned_tools_bar'):
                    self.left_pinned_tools_bar.hide()
                if hasattr(self, 'right_pinned_tools_bar'):
                    if hasattr(self, 'floating_capsule'):
                        self.right_pinned_tools_bar.set_tools_order(self.floating_capsule.tool_order)
                        self.right_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
                    self.right_pinned_tools_bar.show()
            else:
                if hasattr(self, 'top_pinned_tools_bar'):
                    self.top_pinned_tools_bar.hide()
                if hasattr(self, 'left_pinned_tools_bar'):
                    self.left_pinned_tools_bar.hide()
                if hasattr(self, 'right_pinned_tools_bar'):
                    self.right_pinned_tools_bar.hide()
                if hasattr(self, 'floating_capsule'):
                    self.update_floating_capsule_pos()
                    self.floating_capsule.show()
                    self.floating_capsule.raise_()
            if hasattr(self, 'toolbar'):
                self.toolbar.hide()
            if hasattr(self, 'modern_utility_rail'):
                self.modern_utility_rail.show()
                if hasattr(self, 'modern_right_sidebar'):
                    active_id = getattr(self.modern_utility_rail, 'active_rail_id', None)
                    if active_id and active_id in ("bookmarks", "comments", "thumbnails", "attachments", "accessibility"):
                        self.modern_right_sidebar.show()
                        self.modern_right_sidebar.set_panel(active_id)
                    else:
                        self.modern_right_sidebar.hide()
            tab_doc = self.get_current_tab_doc()
            if tab_doc:
                self.update_zoom_display(int(tab_doc.zoom_level * 100))
            if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
                if self.modern_left_sidebar.edit_drawer.active_edit_id == "organize":
                    self.modern_left_sidebar.edit_drawer.clear_active_state()
        else:
            self.switch_to_home_view()

    def switch_to_organize_view(self):
        if self.tab_widget.count() > 0:
            self.central_stack.setCurrentWidget(self.organize_workspace)
            self.organize_workspace.load_document(force=True)
            self.modern_left_sidebar.set_active_tool("organize_pages")
            if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
                self.modern_left_sidebar.edit_drawer.set_active_tool("organize")
            if hasattr(self, 'floating_capsule'):
                self.floating_capsule.hide()
            if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'pinned_tools_capsule'):
                if hasattr(self, 'top_pinned_tools_bar'): self.top_pinned_tools_bar.hide()
            if hasattr(self, 'left_pinned_tools_bar'):
                self.left_pinned_tools_bar.hide()
            if hasattr(self, 'toolbar'):
                self.toolbar.hide()
            if hasattr(self, 'modern_utility_rail'):
                self.modern_utility_rail.show()
                if hasattr(self, 'modern_right_sidebar'):
                    active_id = getattr(self.modern_utility_rail, 'active_rail_id', None)
                    if active_id and active_id in ("bookmarks", "comments", "thumbnails", "attachments", "accessibility"):
                        self.modern_right_sidebar.show()
                        self.modern_right_sidebar.set_panel(active_id)
                    else:
                        self.modern_right_sidebar.hide()
        else:
            self.switch_to_home_view()

    open_organize_pages_workspace = switch_to_organize_view

    def _on_floating_tool_selected(self, tool_id: str, widget=None):
        if hasattr(self, 'floating_capsule') and self.floating_capsule:
            self.floating_capsule.set_active_tool(tool_id)
        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
            self.top_pinned_tools_bar.set_active_tool(tool_id)
        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
            self.left_pinned_tools_bar.set_active_tool(tool_id)
        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
            self.right_pinned_tools_bar.set_active_tool(tool_id)

        popup_pos = None
        if widget:
            parent_bar = widget.parent()
            is_horiz = getattr(parent_bar, 'orientation', None) == Qt.Orientation.Horizontal
            if is_horiz:
                popup_pos = widget.mapToGlobal(QPoint(0, widget.height() + 6))
            else:
                popup_pos = widget.mapToGlobal(QPoint(widget.width() + 6, 0))

        if tool_id == "select":
            mode = getattr(self, 'cursor_mode', 'select')
            self.set_tool_state(mode)
            if hasattr(self, 'cursor_popup') and popup_pos:
                self.cursor_popup.show_at(popup_pos)
        elif tool_id == "selection":
            mode = getattr(self, 'selection_shape_mode', 'rect')
            if mode == 'ruler':
                self.set_tool_state('ruler')
            else:
                self.set_selection_mode(mode)
            if hasattr(self, 'selection_popup') and popup_pos:
                self.selection_popup.show_at(popup_pos)
        elif tool_id == "pointer":
            self.set_tool_state('pointer')
            if hasattr(self, 'pointer_popup') and popup_pos:
                self.pointer_popup.show_at(popup_pos)
        elif tool_id == "highlighter":
            self.set_tool_state('highlighter')
            if hasattr(self, 'hl_popup') and popup_pos:
                self.hl_popup.show_at(popup_pos)
        elif tool_id == "comment":
            self.set_tool_state('comment')
            if hasattr(self, 'modern_right_sidebar'):
                self.modern_right_sidebar.show()
                self.modern_right_sidebar.set_panel("comments")
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.set_active_rail_item("comments")
        elif tool_id == "text":
            self.set_tool_state('text')
            if hasattr(self, 'text_popup') and popup_pos:
                self.text_popup.show_at(popup_pos)
        elif tool_id == "insert":
            if hasattr(self, 'btn_insert') and hasattr(self.btn_insert, 'menu') and self.btn_insert.menu():
                menu = self.btn_insert.menu()
                menu.exec(popup_pos if popup_pos else QCursor.pos())
            self.set_tool_state(self.current_tool)
        elif tool_id == "pen":
            self.set_tool_state('pen')
            if hasattr(self, 'pen_popup') and popup_pos:
                self.pen_popup.show_at(popup_pos)
        elif tool_id == "eraser":
            self.set_tool_state('eraser')
            if hasattr(self, 'eraser_popup') and popup_pos:
                self.eraser_popup.show_at(popup_pos)
        elif tool_id == "accessibility":
            self.toggle_accessibility_mode()

    def _on_home_tool_requested(self, tool_id: str):
        if tool_id == "organize_pages":
            if self.tab_widget.count() > 0:
                self.switch_to_organize_view()
            else:
                self.open_pdf()
        elif tool_id == "add_comments":
            if self.tab_widget.count() > 0:
                self.switch_to_document_view()
                if hasattr(self, 'modern_left_sidebar'):
                    self.modern_left_sidebar.hide()
                self.set_tool_state('comment')
                if hasattr(self, 'modern_right_sidebar'):
                    self.modern_right_sidebar.show()
                    self.modern_right_sidebar.set_panel("comments")
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.set_active_rail_item("comments")
            else:
                self.open_pdf()
        elif tool_id == "prepare_form":
            if self.tab_widget.count() > 0:
                self.switch_to_document_view()
                self.modern_left_sidebar.show()
                self.modern_left_sidebar.set_page("prepare_form")
                if hasattr(self.modern_left_sidebar, 'prepare_form_drawer'):
                    self.modern_left_sidebar.prepare_form_drawer.refresh_fields_list()
            else:
                self.open_pdf()
        elif tool_id == "edit_pdf":
            self.modern_left_sidebar.show()
            self.modern_left_sidebar.set_page("edit")
            self.modern_header_bar.set_mode("edit")
        elif tool_id == "protect_pdf":
            self.open_encrypt_dialog()
        elif tool_id == "merge_pdf":
            self.open_merge_dialog()
        elif tool_id == "compress_pdf":
            self.open_compress_dialog()
        elif tool_id == "ocr_pdf":
            self.open_pdf_ocr_dialog()
        elif tool_id == "convert_word":
            self.open_word_dialog()
        elif tool_id.startswith("ai_"):
            action = tool_id.replace("ai_", "")
            self.open_ai_assistant_dialog(action=action)
        elif tool_id == "ai_assistant":
            self.open_ai_assistant_dialog(action="summary")

    def _on_export_drawer_action(self, action_id: str):
        try:
            if action_id == "word":
                self.open_word_dialog()
            elif action_id == "xlsx":
                self.open_excel_dialog()
            elif action_id == "pptx":
                self.open_pptx_dialog()
            elif action_id == "png":
                self._export_current_page_as_image()
            elif action_id == "all_images":
                self._export_all_images_action()
            elif action_id == "html":
                self._export_as_html_action()
            elif action_id == "rtf":
                self._export_as_rtf_action()
            elif action_id == "txt":
                self._export_as_txt_action()
            elif action_id == "eps":
                self.open_word_dialog()
        finally:
            if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'export_drawer'):
                self.modern_left_sidebar.export_drawer.clear_active_state()

    def _on_edit_drawer_action(self, action_id: str):
        try:
            if action_id == "rotate":
                if self.tab_widget.count() > 0:
                    if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
                        self.organize_workspace.rotate_selected_cw()
                    else:
                        self.rotate_current_page()
                else:
                    self.open_pdf()
            elif action_id == "delete":
                if self.tab_widget.count() > 0:
                    if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
                        self.organize_workspace.delete_selected_pages()
                    else:
                        self.delete_pages_action()
                else:
                    self.open_pdf()
            elif action_id == "organize":
                if self.tab_widget.count() > 0:
                    if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
                        self.switch_to_document_view()
                    else:
                        self.switch_to_organize_view()
                else:
                    self.open_pdf()
            elif action_id == "extract":
                if self.tab_widget.count() > 0:
                    if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
                        self.organize_workspace.extract_pages_action()
                    else:
                        self.extract_pages_action()
                else:
                    self.open_pdf()
            elif action_id == "insert":
                if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
                    self.organize_workspace.insert_page_action()
                else:
                    self.show_new_page_dialog(default_placement="after_current")
            elif action_id in ("gif", "add_gif"):
                self.show_insert_emoji_dialog()
            elif action_id == "edit_text_images":
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.open_pdf_content_editor()
                else:
                    self.open_pdf()
            elif action_id == "text":
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.set_tool_state('text')
                else:
                    self.open_pdf()
            elif action_id == "image":
                self.show_insert_image_dialog()
            elif action_id in ("header_footer", "bates"):
                self.open_page_number_dialog()
            elif action_id == "watermark":
                self.open_watermark_dialog()
            elif action_id == "background":
                self.open_background_dialog()
            elif action_id == "link":
                self.show_toolbox_menu()
            elif action_id == "attach":
                if self.tab_widget.count() == 0 or not self.get_current_tab_doc():
                    self.open_pdf()
                    return
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.show()
                    self.modern_utility_rail.set_active_rail_item("attachments")
                if hasattr(self, 'modern_right_sidebar'):
                    self.modern_right_sidebar.show()
                    self.modern_right_sidebar.set_panel("attachments")
                    self.modern_right_sidebar._add_attachment_action()
        finally:
            is_in_organize = hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace
            if is_in_organize:
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
                    self.modern_left_sidebar.edit_drawer.set_active_tool("organize")
            elif action_id in ("text", "edit_text_images"):
                if self.tab_widget.count() == 0:
                    if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
                        self.modern_left_sidebar.edit_drawer.clear_active_state()
            else:
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
                    self.modern_left_sidebar.edit_drawer.clear_active_state()

    def delete_pages_action(self):
        """PDF Düzenle çekmecesinden sayfaları güvenli silme diyaloğu."""
        if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
            self.organize_workspace.delete_selected_pages()
            return

        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_tab"))
            return
        total = len(tab_doc.doc)
        if total <= 1:
            QMessageBox.warning(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_cannot_delete_last_page"))
            return
        curr_page = tab_doc.current_page_idx + 1

        msg_box = QMessageBox(self)
        from src.ui.dialog_theme import apply_dialog_theme
        apply_dialog_theme(msg_box, self)
        msg_box.setWindowTitle(LanguageManager.tr("drawer_edit_delete"))
        msg_box.setText(LanguageManager.tr("delete_page_prompt", page=curr_page, total=total))

        btn_curr = msg_box.addButton(LanguageManager.tr("delete_current_page_btn"), QMessageBox.ButtonRole.ActionRole)
        btn_org = msg_box.addButton(LanguageManager.tr("organize_pages_btn"), QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton(LanguageManager.tr("cancel"), QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()
        if clicked == btn_curr:
            tab_doc.delete_page(curr_page - 1)
            self._on_organize_doc_modified()
        elif clicked == btn_org:
            self.switch_to_organize_view()

    def extract_pages_action(self):
        """PDF Düzenle çekmecesinden sayfaları dışa aktarma (PDF olarak çıkarma) eylemi."""
        if hasattr(self, 'central_stack') and hasattr(self, 'organize_workspace') and self.central_stack.currentWidget() == self.organize_workspace:
            self.organize_workspace.extract_pages_action()
            return

        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_tab"))
            return

        total = len(tab_doc.doc)
        curr_page = tab_doc.current_page_idx + 1

        msg_box = QMessageBox(self)
        from src.ui.dialog_theme import apply_dialog_theme
        apply_dialog_theme(msg_box, self)
        msg_box.setWindowTitle(LanguageManager.tr("drawer_edit_extract"))
        msg_box.setText(LanguageManager.tr("extract_page_prompt", page=curr_page, total=total))

        btn_curr = msg_box.addButton(LanguageManager.tr("extract_current_page_btn"), QMessageBox.ButtonRole.ActionRole)
        btn_org = msg_box.addButton(LanguageManager.tr("organize_pages_btn"), QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton(LanguageManager.tr("cancel"), QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()
        if clicked == btn_curr:
            path, _ = QFileDialog.getSaveFileName(
                self, LanguageManager.tr("organize_extract_pages"),
                f"page_{curr_page}.pdf", "PDF (*.pdf)"
            )
            if path:
                try:
                    new_doc = fitz.open()
                    new_doc.insert_pdf(tab_doc.doc, from_page=curr_page - 1, to_page=curr_page - 1)
                    new_doc.save(path)
                    new_doc.close()
                    QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("organize_extract_success", path=path))
                except Exception as e:
                    QMessageBox.critical(self, LanguageManager.tr("app_title"), f"{LanguageManager.tr('error')}: {e}")
        elif clicked == btn_org:
            self.switch_to_organize_view()

    def _export_current_page_as_image(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        p_idx = getattr(tab_doc, 'current_page', 0)
        save_path, _ = QFileDialog.getSaveFileName(self, "PNG Olarak Dışa Aktar", f"page_{p_idx + 1}.png", "PNG Images (*.png)")
        if save_path:
            pix = tab_doc.doc[p_idx].get_pixmap(dpi=150)
            pix.save(save_path)
            QMessageBox.information(self, LanguageManager.tr("app_title"), f"Sayfa başarıyla kaydedildi:\n{save_path}")

    def _export_all_images_action(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        folder = QFileDialog.getExistingDirectory(self, "Tüm Resimleri Dışa Aktar")
        if not folder:
            return
        count = 0
        for p_idx, page in enumerate(tab_doc.doc):
            for img_idx, img in enumerate(page.get_images()):
                try:
                    xref = img[0]
                    base_image = tab_doc.doc.extract_image(xref)
                    ext = base_image["ext"]
                    out_path = os.path.join(folder, f"page_{p_idx+1}_img_{img_idx+1}.{ext}")
                    with open(out_path, "wb") as f:
                        f.write(base_image["image"])
                    count += 1
                except Exception:
                    pass
        QMessageBox.information(self, LanguageManager.tr("app_title"), f"{count} resim başarıyla dışa aktarıldı.")

    def _export_as_txt_action(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Metin Olarak Dışa Aktar", "document.txt", "Text Files (*.txt)")
        if save_path:
            full_text = "".join(p.get_text() + "\n\n" for p in tab_doc.doc)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            QMessageBox.information(self, LanguageManager.tr("app_title"), f"Metin başarıyla kaydedildi:\n{save_path}")

    def _export_as_html_action(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "HTML Olarak Dışa Aktar", "document.html", "HTML Files (*.html)")
        if save_path:
            html_text = "<html><head><meta charset='utf-8'></head><body>\n"
            for p_idx, page in enumerate(tab_doc.doc):
                html_text += f"<div class='page' style='margin-bottom:30px; border-bottom:1px solid #ccc;'><h3>Sayfa {p_idx+1}</h3>\n"
                html_text += page.get_text("html") + "\n</div>\n"
            html_text += "</body></html>"
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html_text)
            QMessageBox.information(self, LanguageManager.tr("app_title"), f"HTML başarıyla kaydedildi:\n{save_path}")

    def _export_as_rtf_action(self):
        self._export_as_txt_action()

    def _show_main_menu(self, global_pos: Optional[QPoint] = None):
        if global_pos is None or not isinstance(global_pos, QPoint):
            if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'btn_menu'):
                btn = self.modern_header_bar.btn_menu
                global_pos = btn.mapToGlobal(QPoint(0, btn.height()))
            else:
                global_pos = self.mapToGlobal(QPoint(10, 50))
        menu = QMenu(self)
        theme = getattr(self, 'current_theme', 'gray')
        c = get_modern_theme_colors(theme)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 24px 7px 12px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
            }}
            QMenu::item:selected {{
                background-color: {c['surface_hover']};
                color: {c['accent']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {c['border']};
                margin: 4px 6px;
            }}
        """)
        act_new = menu.addAction(ModernIconFactory.icon_new_document(), "  " + LanguageManager.tr("menu_file_new_tab"))
        act_new.triggered.connect(lambda: self.show_new_page_dialog(force_new_doc=True))

        act_open = menu.addAction(ModernIconFactory.icon_folder(), "  " + LanguageManager.tr("open_file") + "\tCtrl+O")
        act_open.triggered.connect(self.open_pdf)

        act_save = menu.addAction(ModernIconFactory.icon_save(), "  " + LanguageManager.tr("save_btn") + "\tCtrl+S")
        act_save.triggered.connect(self.save_pdf)

        act_save_as = menu.addAction(ModernIconFactory.icon_save(), "  " + LanguageManager.tr("save_as") + "\tCtrl+Shift+S")
        act_save_as.triggered.connect(self.save_as_pdf)

        act_print = menu.addAction(ModernIconFactory.icon_print(), "  " + LanguageManager.tr("print_btn") + "\tCtrl+P")
        act_print.triggered.connect(self.print_pdf)

        act_props = menu.addAction(ModernIconFactory.icon_doc_properties(), "  " + LanguageManager.tr("doc_properties") + "\tCtrl+D")
        act_props.triggered.connect(self.open_document_properties_dialog)

        menu.addSeparator()

        act_org = menu.addAction(ModernIconFactory.icon_organize(), "  " + LanguageManager.tr("tool_organize_pages"))
        act_org.triggered.connect(self.switch_to_organize_view)

        act_edit = menu.addAction(ModernIconFactory.icon_edit_content(), "  " + LanguageManager.tr("tool_edit_pdf"))
        act_edit.triggered.connect(self.open_pdf_content_editor)

        act_comp = menu.addAction(ModernIconFactory.icon_compress(), "  " + LanguageManager.tr("tool_compress_pdf"))
        act_comp.triggered.connect(self.open_compress_dialog)

        act_ocr = menu.addAction(ModernIconFactory.icon_ocr(), "  " + LanguageManager.tr("tool_scan_ocr"))
        act_ocr.triggered.connect(self.open_pdf_ocr_dialog)

        act_merge = menu.addAction(ModernIconFactory.icon_combine_files(), "  " + LanguageManager.tr("tool_combine_files"))
        act_merge.triggered.connect(self.open_merge_dialog)

        menu.addSeparator()

        act_set = menu.addAction(ModernIconFactory.icon_settings(), "  " + LanguageManager.tr("settings_title"))
        act_set.triggered.connect(self.open_settings_dialog)

        act_sc = menu.addAction(ModernIconFactory.icon_info(), "  " + LanguageManager.tr("shortcuts_title") + "\tF1")
        act_sc.triggered.connect(self.open_shortcuts_dialog)

        act_upd = menu.addAction(ModernIconFactory.icon_update(), "  " + LanguageManager.tr("menu_help_check_updates"))
        act_upd.triggered.connect(self.check_updates_background)

        menu.addSeparator()

        act_exit = menu.addAction(ModernIconFactory.icon_close(), "  " + LanguageManager.tr("menu_file_exit"))
        act_exit.triggered.connect(self.close)

        menu.exec(global_pos)

    def _open_command_palette(self):
        dlg = ModernCommandPaletteDialog(self)
        dlg.commandTriggered.connect(self._on_command_palette_executed)
        dlg.move(self.geometry().center().x() - dlg.width() // 2, self.geometry().top() + 80)
        dlg.show()
        dlg.activateWindow()
        dlg.txt_search.setFocus()
        dlg.exec()

    def _on_command_palette_executed(self, cid: str):
        self._on_all_tools_panel_action(cid)

    def _on_all_tools_panel_action(self, tool_id: str):
        try:
            if tool_id == "organize_pages":
                self.switch_to_organize_view()
            elif tool_id == "edit_pdf":
                self.switch_to_document_view()
                self.open_pdf_content_editor()
            elif tool_id == "combine_files":
                self.open_merge_dialog()
            elif tool_id == "compress_pdf":
                self.open_compress_dialog()
            elif tool_id == "scan_ocr":
                self.open_pdf_ocr_dialog()
            elif tool_id == "protect_pdf":
                self.open_encrypt_dialog()
            elif tool_id == "redact_pdf":
                self.open_pdf_redaction_dialog()
            elif tool_id in ("fill_sign", "esign"):
                self.modern_left_sidebar.show()
                self.modern_left_sidebar.set_page("esign")
                self.modern_header_bar.set_mode("esign")
            elif tool_id == "prepare_form":
                self.switch_to_document_view()
                self.modern_left_sidebar.show()
                self.modern_left_sidebar.set_page("prepare_form")
                if hasattr(self.modern_left_sidebar, 'prepare_form_drawer'):
                    self.modern_left_sidebar.prepare_form_drawer.refresh_fields_list()
            elif tool_id == "export_pdf":
                self.open_word_dialog()
            elif tool_id == "create_pdf":
                self.show_new_page_dialog(force_new_doc=True)
            elif tool_id == "add_comments":
                self.switch_to_document_view()
                if hasattr(self, 'modern_left_sidebar'):
                    self.modern_left_sidebar.hide()
                self.set_tool_state('comment')
                if hasattr(self, 'modern_right_sidebar'):
                    self.modern_right_sidebar.show()
                    self.modern_right_sidebar.set_panel("comments")
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.set_active_rail_item("comments")
            elif tool_id == "add_stamp":
                self.open_stamp_dialog()
            elif tool_id == "add_gif":
                self.show_insert_emoji_dialog()
            elif tool_id == "view_more":
                self.show_toolbox_menu()
            elif tool_id == "print_production":
                self.print_pdf()
            elif tool_id == "measure_objects":
                self.switch_to_document_view()
                self.set_tool_state('ruler')
            elif tool_id == "compare_files":
                self.open_pdf_compare_dialog()
            elif tool_id == "prepare_accessibility":
                self.open_document_properties_dialog()
            elif tool_id == "search_index":
                self.toggle_search_bar()
            elif tool_id == "print":
                self.print_pdf()
            elif tool_id == "save":
                self.save_pdf()
            elif tool_id == "settings":
                self.open_settings_dialog()
            elif tool_id == "shortcuts":
                self.open_shortcuts_dialog()
        finally:
            if tool_id != "organize_pages":
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'all_tools_panel'):
                    self.modern_left_sidebar.all_tools_panel.clear_active_state()


    def _on_read_drawer_action(self, action_id: str):
        if action_id == "view_single":
            self.set_page_view_mode("single")
        elif action_id == "view_double":
            self.set_page_view_mode("double")
        elif action_id == "view_fullscreen":
            self.toggle_fullscreen()
        elif action_id == "color_normal":
            self.set_reading_color_mode("normal")
        elif action_id == "color_dark":
            self.set_reading_color_mode("dark")
        elif action_id == "color_sepia":
            self.set_reading_color_mode("sepia")

    def open_stamp_dialog(self, trigger_widget=None):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return
        if not hasattr(self, 'stamp_popup') or not self.stamp_popup:
            from src.ui.popups import ModernStampPalettePopup
            self.stamp_popup = ModernStampPalettePopup(
                parent=self,
                on_stamp_selected=self._on_quick_stamp_selected,
                on_open_custom_dialog=self._open_custom_stamp_dialog
            )
            if hasattr(self, 'current_theme'):
                self.stamp_popup.apply_theme(self.current_theme)

        if trigger_widget and isinstance(trigger_widget, QWidget) and trigger_widget.isVisible():
            self.stamp_popup.show_below(trigger_widget)
        else:
            self.stamp_popup.show_at(QCursor.pos())

    def _on_quick_stamp_selected(self, stamp_bytes: bytes, stamp_name: str, def_w: float = 160.0, def_h: float = 60.0):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        tab_doc.add_image_media(
            stamp_bytes,
            title=f"{LanguageManager.tr('stamp')}: {stamp_name}",
            default_w=def_w,
            default_h=def_h
        )
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"{LanguageManager.tr('stamp')}: {stamp_name} {LanguageManager.tr('stamp_applied_msg')}")

    def _open_custom_stamp_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        if not hasattr(self, 'stamp_popup') or not self.stamp_popup:
            from src.ui.popups import ModernStampPalettePopup
            self.stamp_popup = ModernStampPalettePopup(
                parent=self,
                on_stamp_selected=self._on_quick_stamp_selected,
                on_open_custom_dialog=self._open_custom_stamp_dialog
            )
        if hasattr(self.stamp_popup, 'switch_to_custom_tab'):
            self.stamp_popup.switch_to_custom_tab()
        self.stamp_popup.show_at(QCursor.pos())

    def insert_gif_media(self):
        self.show_insert_emoji_dialog()

    def _on_fill_sign_tool_triggered(self, tool_id: str):
        try:
            if tool_id == "add_text":
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.set_tool_state('text')
                else:
                    self.open_pdf()
            elif tool_id in ("checkmark", "cross", "dot", "line", "date"):
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.insert_symbol_stamp(tool_id)
                else:
                    self.open_pdf()
            elif tool_id == "signature":
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.open_signature_dialog()
                else:
                    self.open_pdf()
            elif tool_id == "initials":
                if self.tab_widget.count() > 0:
                    self.switch_to_document_view()
                    self.open_initials_dialog()
                else:
                    self.open_pdf()
        finally:
            if self.tab_widget.count() == 0:
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'fill_sign_drawer'):
                    self.modern_left_sidebar.fill_sign_drawer.clear_active_state()
            elif tool_id in ("signature", "initials"):
                if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'fill_sign_drawer'):
                    self.modern_left_sidebar.fill_sign_drawer.clear_active_state()

    def _on_prepare_form_action(self, action_id: str):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return

        drawer = getattr(self.modern_left_sidebar, 'prepare_form_drawer', None)

        if action_id in ("form_text", "form_checkbox", "form_radio", "form_combobox", "form_signature"):
            field_type = action_id.replace("form_", "")
            tab_doc.start_form_field_placement(field_type)
            msg = LanguageManager.tr("form_click_to_place")
            self.show_osd_message(msg)
        elif action_id == "form_edit_selected":
            sel_item = None
            for it in getattr(tab_doc, 'form_designer_items', []):
                if it.isSelected():
                    sel_item = it
                    break
            if not sel_item and drawer and hasattr(drawer, 'list_fields'):
                cur = drawer.list_fields.currentItem()
                if cur:
                    data = cur.data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict):
                        for it in getattr(tab_doc, 'form_designer_items', []):
                            if it.field_name == data.get('name') and it.page_idx == data.get('page'):
                                sel_item = it
                                break
            if sel_item:
                sel_item.open_properties_dialog()
        elif action_id == "form_delete_selected":
            if drawer and hasattr(drawer, 'list_fields'):
                cur_item = drawer.list_fields.currentItem()
                if cur_item:
                    data = cur_item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict) and 'name' in data and 'page' in data:
                        tab_doc.delete_form_field(data['page'], data['name'])
                        drawer.refresh_fields_list()
                        self.show_osd_message(LanguageManager.tr("form_field_deleted"))
        elif action_id == "form_clear":
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                LanguageManager.tr("confirm"),
                LanguageManager.tr("form_action_clear") + "?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                tab_doc.clear_all_form_fields()
                if drawer:
                    drawer.refresh_fields_list()
                self.show_osd_message(LanguageManager.tr("form_cleared_msg"))
        elif action_id == "form_export":
            from PyQt6.QtWidgets import QFileDialog
            import json
            path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("form_action_export"), "form_data.json", "JSON Files (*.json)")
            if path:
                try:
                    fields = tab_doc.get_all_form_fields()
                    data = {f['name']: f.get('value', '') for f in fields}
                    with open(path, "w", encoding="utf-8") as fp:
                        json.dump(data, fp, ensure_ascii=False, indent=2)
                    self.show_osd_message(LanguageManager.tr("form_data_exported"))
                except Exception as e:
                    from src.core.logger import logger
                    logger.error(f"Error exporting form data: {e}")
        elif action_id == "form_import":
            from PyQt6.QtWidgets import QFileDialog
            import json
            path, _ = QFileDialog.getOpenFileName(self, LanguageManager.tr("form_action_import"), "", "JSON Files (*.json)")
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    for page in tab_doc.doc:
                        for widget in page.widgets():
                            if widget.field_name in data:
                                widget.field_value = str(data[widget.field_name])
                                widget.update()
                    if getattr(tab_doc, 'is_form_design_mode', False):
                        tab_doc.enter_form_design_mode()
                    else:
                        tab_doc._load_interactive_form_widgets()
                    tab_doc.set_modified(True)
                    tab_doc.rerender_visible_pages()
                    if drawer:
                        drawer.refresh_fields_list()
                    self.show_osd_message(LanguageManager.tr("form_data_imported"))
                except Exception as e:
                    from src.core.logger import logger
                    logger.error(f"Error importing form data: {e}")

    def open_date_stamp_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return
        try:
            from src.ui.dialogs.stamp_dialog import DateStampDialog
            dlg = DateStampDialog(self)
            if dlg.exec() and dlg.result_bytes:
                pix = QPixmap()
                pix.loadFromData(dlg.result_bytes)
                tab_doc.start_stamp_placement(
                    dlg.result_bytes,
                    title=dlg.result_title,
                    default_w=dlg.default_w,
                    default_h=dlg.default_h,
                    pixmap=pix,
                    symbol_type="date"
                )
        except Exception:
            self.insert_symbol_stamp("date")

    def insert_symbol_stamp(self, symbol_type: str):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return

        from PyQt6.QtCore import QBuffer, QIODevice, QPointF, QRectF
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QFont
        from datetime import datetime

        if symbol_type == "checkmark":
            pix = QPixmap(80, 80)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            col = QColor("#0f172a")
            p.setPen(QPen(col, 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(14, 42)
            path.lineTo(32, 60)
            path.lineTo(66, 18)
            p.drawPath(path)
            p.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buf, "PNG")
            tab_doc.start_stamp_placement(bytes(buf.data()), title="Checkmark", default_w=28.0, default_h=28.0, pixmap=pix, symbol_type="checkmark")

        elif symbol_type == "cross":
            pix = QPixmap(80, 80)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            col = QColor("#0f172a")
            p.setPen(QPen(col, 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(20, 20), QPointF(60, 60))
            p.drawLine(QPointF(60, 20), QPointF(20, 60))
            p.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buf, "PNG")
            tab_doc.start_stamp_placement(bytes(buf.data()), title="Cross", default_w=28.0, default_h=28.0, pixmap=pix, symbol_type="cross")

        elif symbol_type == "dot":
            pix = QPixmap(60, 60)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setBrush(QBrush(QColor("#0f172a")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(15, 15, 30, 30))
            p.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buf, "PNG")
            tab_doc.start_stamp_placement(bytes(buf.data()), title="Dot", default_w=18.0, default_h=18.0, pixmap=pix, symbol_type="dot")

        elif symbol_type == "line":
            pix = QPixmap(160, 40)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            col = QColor("#0f172a")
            p.setPen(QPen(col, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(10, 20), QPointF(150, 20))
            p.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buf, "PNG")
            tab_doc.start_stamp_placement(bytes(buf.data()), title="Line", default_w=55.0, default_h=12.0, pixmap=pix, symbol_type="line")

        elif symbol_type == "date":
            date_fmt = "%d.%m.%Y"
            if hasattr(self, 'settings'):
                saved_fmt = self.settings.value("date_stamp_format", "%d.%m.%Y")
                if saved_fmt and isinstance(saved_fmt, str):
                    date_fmt = saved_fmt
            try:
                date_str = datetime.now().strftime(date_fmt)
            except Exception:
                date_str = datetime.now().strftime("%d.%m.%Y")

            from PyQt6.QtGui import QFontMetrics
            font = QFont("Segoe UI", 16, QFont.Weight.Medium)
            fm = QFontMetrics(font)
            txt_w = max(100, fm.horizontalAdvance(date_str) + 24)
            txt_h = max(36, fm.height() + 12)

            pix = QPixmap(txt_w, txt_h)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            p.setPen(QColor("#0f172a"))
            p.setFont(font)
            p.drawText(QRectF(0, 0, txt_w, txt_h), Qt.AlignmentFlag.AlignCenter, date_str)
            p.end()

            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            pix.save(buf, "PNG")
            calc_w = max(65.0, float(txt_w) * 0.75)
            calc_h = max(20.0, float(txt_h) * 0.75)
            tab_doc.start_stamp_placement(
                bytes(buf.data()),
                title=LanguageManager.tr("stamp_date_title", date=date_str),
                default_w=calc_w,
                default_h=calc_h,
                pixmap=pix,
                symbol_type="date"
            )

    def open_initials_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return
        from src.ui.dialogs.settings_dialog import get_effective_author_name
        author_name = get_effective_author_name()
        initials = "".join([part[0].upper() for part in author_name.split() if part])[:3] if author_name else ""
        try:
            from src.ui.dialogs.pdf_signature_dialog import PDFSignatureDialog
            dlg = PDFSignatureDialog(self, default_name=initials)
            dlg.setWindowTitle(LanguageManager.tr("sign_dialog_initials"))
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image is not None:
                tab_doc.add_signature(dlg.result_image)
                QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("sign_placed_success"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, LanguageManager.tr("error"), f"Paraf eklenirken bir hata oluştu: {e}")

    def _close_organize_workspace(self):
        if hasattr(self, 'organize_workspace'):
            self.organize_workspace.cancel_rendering()
        if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
            self.modern_left_sidebar.edit_drawer.clear_active_state()
        self.switch_to_document_view()

    def _on_organize_open_page(self, page_index: int):
        if hasattr(self, 'organize_workspace'):
            self.organize_workspace.cancel_rendering()
        tab_doc = self.get_current_tab_doc()
        if tab_doc:
            tab_doc.go_to_page(page_index)
        if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'edit_drawer'):
            self.modern_left_sidebar.edit_drawer.clear_active_state()
        self.switch_to_document_view()

    def _on_organize_doc_modified(self):
        tab_doc = self.get_current_tab_doc()
        if tab_doc and tab_doc.doc:
            try:
                tab_doc.set_modified(True)
                is_tab_visible = getattr(self, 'central_stack', None) and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None))
                if is_tab_visible:
                    tab_doc.render_all_pages()
                tab_doc.update_tab_title()
                total = len(tab_doc.doc)
                curr = getattr(tab_doc, 'current_page_idx', 0)
                if hasattr(self, 'lbl_total') and self.lbl_total:
                    self.lbl_total.setText(LanguageManager.tr("page_of", total=total))
                if hasattr(self, 'txt_page') and self.txt_page:
                    self.txt_page.setText(str(curr + 1))
                if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
                    self.modern_header_bar.update_page_info(curr + 1, total)
                if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar and self.modern_right_sidebar.isVisible():
                    self.modern_right_sidebar.load_thumbnails()
                if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock and self.thumbnails_dock.isVisible():
                    tab_doc.notify_thumbnails_updated(curr)
                if hasattr(self, 'organize_workspace') and self.organize_workspace:
                    self.organize_workspace.load_document(force=True)
            except Exception as e:
                import traceback
                traceback.print_exc()

    def toggle_accessibility_mode(self):
        if hasattr(self, 'modern_right_sidebar'):
            if self.modern_right_sidebar.isVisible() and self.modern_right_sidebar.current_panel == "accessibility":
                self.modern_right_sidebar.hide()
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.set_active_rail_item("none")
            else:
                self.modern_right_sidebar.show()
                self.modern_right_sidebar.set_panel("accessibility")
                if hasattr(self, 'modern_utility_rail'):
                    self.modern_utility_rail.set_active_rail_item("accessibility")
        self._center_active_document()

    def _on_utility_rail_toggled(self, rail_id: str):
        if self.isFullScreen():
            return
        if rail_id == "none":
            self.modern_right_sidebar.hide()
            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                self.thumbnails_dock.hide()
        elif rail_id == "accessibility":
            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                self.thumbnails_dock.hide()
            self.toggle_accessibility_mode()
        elif rail_id in ("bookmarks", "comments", "thumbnails", "attachments"):
            if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                self.thumbnails_dock.hide()
            self.modern_right_sidebar.show()
            self.modern_right_sidebar.set_panel(rail_id)
        self._center_active_document()

    def _on_rail_page_jump(self, page_index: int):
        tab_doc = self.get_current_tab_doc()
        if tab_doc and tab_doc.doc:
            total = len(tab_doc.doc)
            clamped = max(0, min(page_index - 1, total - 1))
            tab_doc.go_to_page(clamped)
            self.modern_header_bar.update_page_info(clamped + 1, total)
            if hasattr(self, 'txt_page') and self.txt_page and not self.txt_page.hasFocus():
                self.txt_page.setText(str(clamped + 1))
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.select_page(clamped)

    def _sync_rail_page(self, txt: str):
        if hasattr(self, 'modern_utility_rail') and self.modern_utility_rail:
            tab_doc = self.get_current_tab_doc()
            total = len(tab_doc.doc) if tab_doc and tab_doc.doc else 1
            curr = int(txt) - 1 if txt and txt.isdigit() else 0
            self.modern_header_bar.update_page_info(curr + 1, total)

    def _center_active_document(self):
        """Panel açılıp kapandığında açık belgenin ekranın yatayında tam ortalanmasını sağlar."""
        tab_doc = self.get_current_tab_doc()
        if tab_doc and hasattr(tab_doc, 'center_current_page_horizontal'):
            tab_doc.center_current_page_horizontal()
            QTimer.singleShot(60, tab_doc.center_current_page_horizontal)

    def _close_right_sidebar(self):
        self.modern_right_sidebar.hide()
        if hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
            self.thumbnails_dock.hide()
        self.modern_utility_rail.set_active_rail_item(None)
        self._center_active_document()

    def _close_left_sidebar(self):
        if hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar:
            self.modern_left_sidebar.clear_all_active_states()
            self.modern_left_sidebar.hide()
        if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
            self.modern_header_bar.set_mode(None, notify=False)
        self._center_active_document()

    def _on_bookmark_clicked(self, page_index: int):
        tab_doc = self.get_current_tab_doc()
        if tab_doc:
            tab_doc.go_to_page(page_index)
            if hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.switch_to_document_view()
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.select_page(page_index)

    def toggle_fullscreen(self, checked=None):
        going_fullscreen = not self.isFullScreen()

        if hasattr(self, 'btn_fullscreen') and self.btn_fullscreen:
            self.btn_fullscreen.blockSignals(True)
            self.btn_fullscreen.setChecked(going_fullscreen)
            self.btn_fullscreen.blockSignals(False)

        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'btn_fullscreen') and self.modern_header_bar.btn_fullscreen:
            self.modern_header_bar.btn_fullscreen.blockSignals(True)
            self.modern_header_bar.btn_fullscreen.setChecked(going_fullscreen)
            self.modern_header_bar.btn_fullscreen.blockSignals(False)

        if going_fullscreen:
            # 1. Mevcut pencere durumunu ve geometrisini kaydet
            self._was_maximized = self.isMaximized()
            self._normal_geometry = self.saveGeometry()
            self._normal_state = self.saveState()

            # 2. Yan panelleri, çekmeceleri ve durum çubuğunu kaydet ve gizle
            self._sidebar_was_visible = hasattr(self, 'thumbnails_dock') and self.thumbnails_dock and self.thumbnails_dock.isVisible()
            if self._sidebar_was_visible:
                self.thumbnails_dock.hide()

            self._left_sidebar_was_visible = hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar and self.modern_left_sidebar.isVisible()
            if self._left_sidebar_was_visible:
                self.modern_left_sidebar.hide()

            self._right_sidebar_was_visible = hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar and self.modern_right_sidebar.isVisible()
            if self._right_sidebar_was_visible:
                self.modern_right_sidebar.hide()

            sb = self.statusBar()
            if sb:
                self._statusbar_was_visible = sb.isVisible()
                sb.hide()
            else:
                self._statusbar_was_visible = False

            # 3. Sekme çubuğunu, üst barları ve rayı gizle
            self.tab_widget.tabBar().hide()
            if hasattr(self, 'toolbar'):
                self.toolbar.hide()
            if hasattr(self, 'modern_tab_bar'):
                self.modern_tab_bar.hide()
            if hasattr(self, 'modern_header_bar'):
                self.modern_header_bar.hide()
            if hasattr(self, 'modern_utility_rail'):
                self.modern_utility_rail.hide()
            if hasattr(self, 'floating_capsule'):
                self.floating_capsule.hide()
            if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'pinned_tools_capsule'):
                if hasattr(self, 'top_pinned_tools_bar'): self.top_pinned_tools_bar.hide()
            if hasattr(self, 'left_pinned_tools_bar'):
                self.left_pinned_tools_bar.hide()
            if hasattr(self, 'right_pinned_tools_bar'):
                self.right_pinned_tools_bar.hide()

            # 4. Tam ekrana geç
            self.showFullScreen()

            # 5. Tam ekran kayar araç çubuğunu aç ve okuma HUD panelini göster
            if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                self.fullscreen_toolbar.show_fullscreen_mode()
            if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                self.fullscreen_reading_hud.slide_in()
            tab_doc = self.get_current_tab_doc()
            if tab_doc and tab_doc.doc and len(tab_doc.doc) > 0:
                self.show_fullscreen_page_osd(tab_doc.current_page_idx + 1, len(tab_doc.doc))

            self.show_osd_message(LanguageManager.tr("fullscreen_exit_hint"))
        else:
            if hasattr(self, '_fs_zoom_label') and self._fs_zoom_label:
                self._fs_zoom_label.hide()
            if hasattr(self, '_fs_page_label') and self._fs_page_label:
                self._fs_page_label.hide()
            # 1. Tam ekran kayar araç çubuğunu ve okuma HUD panelini gizle
            if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar is not None:
                self.fullscreen_toolbar.hide_fullscreen_mode()
            if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                self.fullscreen_reading_hud.hide_fullscreen_mode()

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

            # 3. Yan panel, çekmeceler, sekme çubuğu ve durum çubuğunu geri yükle
            if getattr(self, '_sidebar_was_visible', False) and hasattr(self, 'thumbnails_dock') and self.thumbnails_dock:
                self.thumbnails_dock.show()

            if getattr(self, '_left_sidebar_was_visible', False) and hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar:
                self.modern_left_sidebar.show()

            if getattr(self, '_right_sidebar_was_visible', False) and hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                self.modern_right_sidebar.show()

            self.tab_widget.tabBar().hide()
            if hasattr(self, 'modern_tab_bar'):
                self.modern_tab_bar.show()
            if hasattr(self, 'modern_header_bar'):
                self.modern_header_bar.show()
            if hasattr(self, 'toolbar'):
                self.toolbar.hide()
            if hasattr(self, 'modern_utility_rail') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() != getattr(self, 'home_workspace', None):
                self.modern_utility_rail.show()
            if hasattr(self, 'central_stack') and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                if getattr(self, 'capsule_docked_to_top', False):
                    if hasattr(self, 'top_pinned_tools_bar'):
                        self.top_pinned_tools_bar.show()
                        self.update_floating_capsule_pos()
                elif getattr(self, 'capsule_docked_to_left', False):
                    if hasattr(self, 'left_pinned_tools_bar'):
                        self.left_pinned_tools_bar.show()
                elif getattr(self, 'capsule_docked_to_right', False):
                    if hasattr(self, 'right_pinned_tools_bar'):
                        self.right_pinned_tools_bar.show()
                elif hasattr(self, 'floating_capsule'):
                    self.floating_capsule.show()
                    self.update_floating_capsule_pos()

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

    def show_settings_context_menu(self, pos=None):
        menu = QMenu(self)
        from src.ui.dialog_theme import apply_dialog_theme
        apply_dialog_theme(menu, self)

        act_settings = menu.addAction(ModernIconFactory.icon_settings(), "  " + LanguageManager.tr("settings_title"))
        act_settings.triggered.connect(lambda: self.open_settings_dialog())

        act_shortcuts = menu.addAction(ModernIconFactory.icon_info(), "  " + LanguageManager.tr("shortcuts_dialog_title") + "\tF1")
        act_shortcuts.triggered.connect(self.open_shortcuts_dialog)

        menu.addSeparator()

        act_updates = menu.addAction(ModernIconFactory.icon_update(), "  " + LanguageManager.tr("updates_section_title"))
        act_updates.triggered.connect(lambda: self.open_settings_dialog(initial_tab="updates"))

        if pos is None:
            if hasattr(self, 'btn_settings'):
                point = self.btn_settings.mapToGlobal(QPoint(0, self.btn_settings.height() + 4))
            else:
                point = QCursor.pos()
        elif isinstance(pos, QPoint):
            point = pos
        else:
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
        if theme_name in ("light", "dark", "navy"):
            theme_name = "nord" if theme_name == "navy" else "gray"
        self.current_theme = theme_name
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("app_theme", theme_name)

        theme_specs = {
            "gray": {
                "main_bg": "#2b2d30", "main_text": "#f8fafc", "tb_bg": "#35383c", "tb_border": "#222427",
                "btn_hover": "#42464b", "accent": "#60a5fa", "page_bg": "#42464b", "page_border": "#525860",
                "tab_bg": "#32353a", "tab_hover": "#3e4248", "tab_border": "#40444a", "tab_text": "#cbd5e1",
                "view_bg": "#222426"
            },
            "navy": {
                "main_bg": "#0f172a", "main_text": "#e2e8f0", "tb_bg": "#1e293b", "tb_border": "#0f172a",
                "btn_hover": "#334155", "accent": "#38bdf8", "page_bg": "#334155", "page_border": "#475569",
                "tab_bg": "#1e293b", "tab_hover": "#334155", "tab_border": "#334155", "tab_text": "#cbd5e1",
                "view_bg": "#090d16"
            },
            "emerald": {
                "main_bg": "#091a14", "main_text": "#ecfdf5", "tb_bg": "#112a21", "tb_border": "#06120e",
                "btn_hover": "#1a4032", "accent": "#34d399", "page_bg": "#183c2f", "page_border": "#1a3d30",
                "tab_bg": "#112a21", "tab_hover": "#183c2f", "tab_border": "#1a3d30", "tab_text": "#a7f3d0",
                "view_bg": "#06120e"
            },
            "purple": {
                "main_bg": "#150d22", "main_text": "#faf5ff", "tb_bg": "#201435", "tb_border": "#0e0817",
                "btn_hover": "#321f52", "accent": "#c084fc", "page_bg": "#2f1d4d", "page_border": "#321f52",
                "tab_bg": "#201435", "tab_hover": "#2f1d4d", "tab_border": "#321f52", "tab_text": "#e9d5ff",
                "view_bg": "#0e0817"
            },
            "crimson": {
                "main_bg": "#1d0b10", "main_text": "#fff1f2", "tb_bg": "#2d1118", "tb_border": "#13070a",
                "btn_hover": "#441924", "accent": "#fb7185", "page_bg": "#401923", "page_border": "#441924",
                "tab_bg": "#2d1118", "tab_hover": "#401923", "tab_border": "#441924", "tab_text": "#fecdd3",
                "view_bg": "#13070a"
            },
            "nord": {
                "main_bg": "#181e29", "main_text": "#f0f6fc", "tb_bg": "#222b3a", "tb_border": "#11161e",
                "btn_hover": "#2f3b4f", "accent": "#38bdf8", "page_bg": "#2f3b4f", "page_border": "#313e54",
                "tab_bg": "#222b3a", "tab_hover": "#2f3b4f", "tab_border": "#313e54", "tab_text": "#cbd5e1",
                "view_bg": "#11161e"
            },
            "vice_city": {
                "main_bg": "#160024", "main_text": "#fdf2f8", "tb_bg": "#240e3b", "tb_border": "#3d1663",
                "btn_hover": "#381458", "accent": "#ff2a85", "page_bg": "#2c1047", "page_border": "#ff2a85",
                "tab_bg": "#1e0a32", "tab_hover": "#351357", "tab_border": "#3d1663", "tab_text": "#f5d0fe",
                "view_bg": "#0d0017"
            },
            "apple": {
                "main_bg": "#0e1014", "main_text": "#f5f5f7", "tb_bg": "#1a1d24", "tb_border": "#222630",
                "btn_hover": "#252932", "accent": "#38bdf8", "page_bg": "#252932", "page_border": "#2d323e",
                "tab_bg": "#121419", "tab_hover": "#252932", "tab_border": "#2d323e", "tab_text": "#cbd5e1",
                "view_bg": "#0a0c0f"
            }
        }
        if theme_name == "custom":
            c = get_modern_theme_colors("custom")
            spec = {
                "main_bg": c["bg"],
                "main_text": c["text"],
                "tb_bg": c["surface"],
                "tb_border": c["border"],
                "btn_hover": c["surface_hover"],
                "accent": c["accent"],
                "page_bg": c["card_bg"],
                "page_border": c["card_border"],
                "tab_bg": c["tab_bg"],
                "tab_hover": c["surface_hover"],
                "tab_border": c["border"],
                "tab_text": c["tab_text"],
                "view_bg": c["bg"]
            }
            try:
                from src.ui.popups import POPUP_THEME_SPECS
                POPUP_THEME_SPECS["custom"] = spec
            except Exception:
                pass
        else:
            spec = theme_specs.get(theme_name, theme_specs["gray"])
        view_bg = spec["view_bg"]

        fs = self.settings.value("app_font_size", 10, type=int) if hasattr(self, 'settings') else 10
        if fs <= 0:
            fs = 10

        self.setStyleSheet(f"""
                QMainWindow {{ background-color: {spec['main_bg']}; color: {spec['main_text']}; }}
                QToolBar {{ background-color: {spec['tb_bg']}; border-bottom: 1px solid {spec['tb_border']}; spacing: 4px; padding: 4px 6px; }}
                QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px 6px; color: {spec['main_text']}; }}
                QToolButton:hover {{ background-color: {spec['btn_hover']}; }}
                QToolButton:checked {{ background-color: {spec['btn_hover']}; border-bottom: 2.5px solid {spec['accent']}; border-radius: 2px; }}
                QToolButton:disabled {{ background: transparent; border: 1px solid transparent; opacity: 0.35; color: #555555; }}
                QLineEdit#PageInput {{ background-color: {spec['page_bg']}; color: {spec['main_text']}; border: 1.2px solid {spec['page_border']}; border-radius: 3px; padding: 2px 4px; font-weight: bold; }}
                QLabel {{ color: {spec['main_text']}; font-size: {fs}pt; }}
                QTabWidget::pane {{ border: none; background-color: {view_bg}; }}
                QTabBar::tab {{ background-color: {spec['tab_bg']}; color: {spec['tab_text']}; padding: 7px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: 1px solid {spec['tab_border']}; border-bottom: none; }}
                QTabBar::tab:hover {{ background-color: {spec['tab_hover']}; color: {spec['main_text']}; }}
                QTabBar::tab:selected {{ background-color: {spec['main_bg']}; color: {spec['main_text']}; border-top: 2px solid {spec['accent']}; font-weight: bold; }}
                QMenu {{ background-color: {spec['tb_bg']}; color: {spec['main_text']}; border: 1px solid {spec['tb_border']}; border-radius: 8px; padding: 4px; }}
                QMenu::item {{ padding: 6px 20px; border-radius: 4px; font-size: {fs}pt; }}
                QMenu::item:selected {{ background-color: {spec['accent']}; color: #ffffff; font-weight: bold; }}
                QMenu::separator {{ height: 1px; background-color: {spec['tb_border']}; margin: 4px 6px; }}
                QScrollBar:vertical {{ background: {view_bg}; width: 8px; margin: 0px; border-radius: 4px; }}
                QScrollBar::handle:vertical {{ background: {spec['page_border']}; min-height: 24px; border-radius: 4px; }}
                QScrollBar::handle:vertical:hover {{ background: {spec['accent']}; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar::horizontal {{ background: {view_bg}; height: 8px; margin: 0px; border-radius: 4px; }}
                QScrollBar::handle:horizontal {{ background: {spec['page_border']}; min-width: 24px; border-radius: 4px; }}
                QScrollBar::handle:horizontal:hover {{ background: {spec['accent']}; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            """)

        if hasattr(self, 'btn_insert') and hasattr(self.btn_insert, 'menu') and self.btn_insert.menu():
            self.btn_insert.menu().setStyleSheet(f"""
                QMenu {{
                    background-color: {spec['tb_bg']};
                    color: {spec['main_text']};
                    border: 1px solid {spec['tb_border']};
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
            getattr(self, 'stamp_popup', None),
        ]
        for p in popups:
            if p and hasattr(p, 'apply_theme'):
                p.apply_theme(theme_name, spec)

        if hasattr(self, 'fullscreen_toolbar') and self.fullscreen_toolbar and hasattr(self.fullscreen_toolbar, 'apply_theme'):
            self.fullscreen_toolbar.apply_theme(theme_name, spec)

        if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud and hasattr(self.fullscreen_reading_hud, 'apply_theme'):
            self.fullscreen_reading_hud.apply_theme(theme_name, spec)

        if hasattr(self, 'floating_capsule') and self.floating_capsule and hasattr(self.floating_capsule, 'apply_theme'):
            self.floating_capsule.apply_theme(theme_name)

        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar and hasattr(self.top_pinned_tools_bar, 'apply_theme'):
            self.top_pinned_tools_bar.apply_theme(theme_name)

        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar and hasattr(self.left_pinned_tools_bar, 'apply_theme'):
            self.left_pinned_tools_bar.apply_theme(theme_name)

        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar and hasattr(self.right_pinned_tools_bar, 'apply_theme'):
            self.right_pinned_tools_bar.apply_theme(theme_name)

        if hasattr(self, 'floating_hud') and self.floating_hud and hasattr(self.floating_hud, 'apply_theme'):
            self.floating_hud.apply_theme(theme_name, spec)

        if hasattr(self, 'tab_widget') and self.tab_widget:
            for idx in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(idx)
                if isinstance(widget, PDFTabDocument):
                    if hasattr(widget, 'view') and widget.view:
                        widget.view.setStyleSheet(f"background-color: {view_bg}; border: none;")
                    hud = getattr(widget, 'text_selection_hud', getattr(widget, 'floating_text_hud', None))
                    if hud and hasattr(hud, 'apply_theme'):
                        hud.apply_theme(theme_name, spec)

        if hasattr(self, 'modern_tab_bar'):
            self.modern_tab_bar.apply_theme(theme_name)
        if hasattr(self, 'modern_header_bar'):
            self.modern_header_bar.apply_theme(theme_name)
        if hasattr(self, 'modern_left_sidebar'):
            self.modern_left_sidebar.apply_theme(theme_name)
        elif hasattr(self, 'modern_tools_panel'):
            self.modern_tools_panel.apply_theme(theme_name)
        if hasattr(self, 'home_workspace'):
            self.home_workspace.apply_theme(theme_name)
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.apply_theme(theme_name)
        if hasattr(self, 'organize_workspace'):
            self.organize_workspace.apply_theme(theme_name)
        if hasattr(self, 'modern_right_sidebar'):
            self.modern_right_sidebar.apply_theme(theme_name)
        if hasattr(self, 'modern_utility_rail'):
            self.modern_utility_rail.apply_theme(theme_name)
        if hasattr(self, 'secondary_split_pane') and self.secondary_split_pane:
            self.secondary_split_pane.apply_theme(theme_name)
        if hasattr(self, 'document_splitter') and self.document_splitter:
            c = get_modern_theme_colors(theme_name)
            self.document_splitter.setStyleSheet(f"""
                QSplitter#DocumentSplitter::handle {{
                    background-color: {c['border']};
                    width: 3px;
                }}
                QSplitter#DocumentSplitter::handle:hover {{
                    background-color: {c['accent']};
                }}
            """)

    def change_language(self, lang: str):
        LanguageManager.set_language(lang)
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("language", lang)
        self.retranslate_ui()

    def apply_app_font_size(self, font_size: int):
        """Uygulama genelindeki tüm pencere, diyalog, menü ve bileşenlerin yazı boyutunu ölçeklendirir."""
        if font_size <= 0:
            font_size = 10
        self.app_font_size = font_size
        app = QApplication.instance()
        if app:
            f = app.font()
            f.setPointSize(font_size)
            app.setFont(f)
            app.setStyleSheet(f"""
                QWidget {{
                    font-size: {font_size}pt;
                }}
                QDialog {{
                    font-size: {font_size}pt;
                }}
                QMenu {{
                    font-size: {font_size}pt;
                }}
                QMenu::item {{
                    font-size: {font_size}pt;
                }}
                QToolTip {{
                    font-size: {max(9, font_size - 1)}pt;
                }}
            """)
        self.apply_theme(self.current_theme)
        if hasattr(self, 'modern_tab_bar'):
            self.modern_tab_bar.apply_theme(self.current_theme)
        if hasattr(self, 'modern_header_bar'):
            self.modern_header_bar.apply_theme(self.current_theme)
        if hasattr(self, 'modern_left_sidebar'):
            self.modern_left_sidebar.apply_theme(self.current_theme)
        if hasattr(self, 'modern_right_sidebar'):
            self.modern_right_sidebar.apply_theme(self.current_theme)
        if hasattr(self, 'modern_utility_rail'):
            self.modern_utility_rail.apply_theme(self.current_theme)
        if hasattr(self, 'floating_capsule'):
            self.floating_capsule.apply_theme(self.current_theme)
        if hasattr(self, 'top_pinned_tools_bar'):
            self.top_pinned_tools_bar.apply_theme(self.current_theme)
        if hasattr(self, 'left_pinned_tools_bar'):
            self.left_pinned_tools_bar.apply_theme(self.current_theme)
        if hasattr(self, 'right_pinned_tools_bar'):
            self.right_pinned_tools_bar.apply_theme(self.current_theme)
        if hasattr(self, 'tab_hover_preview'):
            self.tab_hover_preview.apply_theme(self.current_theme)

    def retranslate_ui(self):
        self.setWindowTitle(LanguageManager.tr("app_title"))

        if hasattr(self, 'btn_cursor'):
            tip = LanguageManager.tr("cursor_tool_tip") if getattr(self, 'cursor_mode', 'select') == 'select' else LanguageManager.tr("cursor_pan_tip")
            self.btn_cursor.setToolTip(tip)
        self.btn_contents.setToolTip(LanguageManager.tr("contents"))
        self.btn_undo.setToolTip(LanguageManager.tr("undo"))
        self.btn_redo.setToolTip(LanguageManager.tr("redo"))
        self.btn_selection.setToolTip(LanguageManager.tr("selection_tool_tip"))
        self.btn_hl.setToolTip(LanguageManager.tr("highlighter_tool_tip"))
        self.btn_pen.setToolTip(LanguageManager.tr("pen_tool_tip"))
        self.btn_text.setToolTip(LanguageManager.tr("text_tool_tip"))
        if hasattr(self, 'btn_direct_edit'):
            self.btn_direct_edit.setToolTip(LanguageManager.tr("direct_edit_tool_tip"))
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

        for popup_name in ('cursor_popup', 'hl_popup', 'pen_popup', 'eraser_popup', 'text_popup', 'selection_popup', 'pointer_popup', 'hl_ruler_popup', 'ruler_popup', 'stamp_popup'):
            if hasattr(self, popup_name):
                popup = getattr(self, popup_name)
                if hasattr(popup, 'retranslate_ui'):
                    popup.retranslate_ui()

        if (tab_doc := self.get_current_tab_doc()) and tab_doc.doc is not None:
            self.update_zoom_display(int(tab_doc.zoom_level * 100))
            self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
            tab_doc.update_tab_title()
        else:
            self.update_zoom_display(100)
            self.lbl_total.setText(LanguageManager.tr("page_of", total=0))
            self.setWindowTitle(LanguageManager.tr("app_title"))

        # Modern UI Bileşenlerinin Yeniden Çevirisi
        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'retranslate_ui'):
            self.modern_header_bar.retranslate_ui()
        if hasattr(self, 'modern_left_sidebar') and hasattr(self.modern_left_sidebar, 'retranslate_ui'):
            self.modern_left_sidebar.retranslate_ui()
        if hasattr(self, 'modern_tab_bar') and hasattr(self.modern_tab_bar, 'retranslate_ui'):
            self.modern_tab_bar.retranslate_ui()
        if hasattr(self, 'home_workspace') and hasattr(self.home_workspace, 'retranslate_ui'):
            self.home_workspace.retranslate_ui()
        if hasattr(self, 'organize_workspace') and hasattr(self.organize_workspace, 'retranslate_ui'):
            self.organize_workspace.retranslate_ui()
        if hasattr(self, 'modern_right_sidebar') and hasattr(self.modern_right_sidebar, 'retranslate_ui'):
            self.modern_right_sidebar.retranslate_ui()
        if hasattr(self, 'modern_utility_rail') and hasattr(self.modern_utility_rail, 'retranslate_ui'):
            self.modern_utility_rail.retranslate_ui()
        if hasattr(self, 'floating_capsule') and hasattr(self.floating_capsule, 'retranslate_ui'):
            self.floating_capsule.retranslate_ui()
        if hasattr(self, 'top_pinned_tools_bar') and hasattr(self.top_pinned_tools_bar, 'retranslate_ui'):
            self.top_pinned_tools_bar.retranslate_ui()
        if hasattr(self, 'left_pinned_tools_bar') and hasattr(self.left_pinned_tools_bar, 'retranslate_ui'):
            self.left_pinned_tools_bar.retranslate_ui()
        if hasattr(self, 'right_pinned_tools_bar') and hasattr(self.right_pinned_tools_bar, 'retranslate_ui'):
            self.right_pinned_tools_bar.retranslate_ui()
        if hasattr(self, 'secondary_split_pane') and hasattr(self.secondary_split_pane, 'retranslate_ui'):
            self.secondary_split_pane.retranslate_ui()

        self.tab_widget.update()

    def get_theme_view_bg(self, theme: str = None) -> str:
        if not theme:
            theme = getattr(self, 'current_theme', 'gray')
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
                    self.switch_to_document_view()
                    if hasattr(self, '_pending_ai_action') and self._pending_ai_action:
                        act = self._pending_ai_action
                        self._pending_ai_action = None
                        QTimer.singleShot(250, lambda p=widget.file_path, a=act: self.open_ai_assistant_dialog(file_path=p, action=a))
                    return
            tab_doc = PDFTabDocument(file_path, self)
            view_bg = self.get_theme_view_bg()
            tab_doc.view.setStyleSheet(f"background-color: {view_bg}; border: none;")
            tab_idx = self.tab_widget.addTab(tab_doc, os.path.basename(file_path))
            self.tab_widget.setCurrentIndex(tab_idx)
            tab_doc.update_tab_title()
            self.sync_modern_tabs()
            if hasattr(self, 'secondary_split_pane') and self.secondary_split_pane.isVisible():
                self.secondary_split_pane.refresh_open_documents_list()
            if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.organize_workspace.load_document()
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.load_bookmarks()
            self.update_zoom_display(int(tab_doc.zoom_level * 100))
            self.switch_to_document_view()

            # V3: Son açılanlara ekle ve dosya izleyiciye kaydet
            self.add_to_recent_files(file_path)
            if hasattr(self, 'file_watcher') and os.path.exists(file_path):
                self.file_watcher.addPath(norm_path)
            if hasattr(self, '_pending_ai_action') and self._pending_ai_action:
                act = self._pending_ai_action
                self._pending_ai_action = None
                QTimer.singleShot(250, lambda p=file_path, a=act: self.open_ai_assistant_dialog(file_path=p, action=a))
        except Exception as e:
            if str(e) == LanguageManager.tr("password_cancelled"):
                return
            QMessageBox.critical(self, LanguageManager.tr("error"), LanguageManager.tr("open_error", error=e))

    def close_tab(self, index):
        if hasattr(self, '_do_hide_tab_preview'):
            self._do_hide_tab_preview()
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

        # V4: Kapatılan sekme seslendiriliyorsa (TTS) güvenle durdur
        if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
            try:
                panel_acc = getattr(self.modern_right_sidebar, 'panel_accessibility', None)
                if panel_acc:
                    panel_acc.on_document_closed(widget)
                elif getattr(self.modern_right_sidebar, 'speech_engine', None):
                    se = self.modern_right_sidebar.speech_engine
                    if se and (se.is_speaking() or se.is_paused()) and (self.tab_widget.count() <= 1 or self.tab_widget.currentWidget() == widget):
                        se.stop()
            except Exception:
                pass

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
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                try:
                    self.modern_right_sidebar.clear_accessibility()
                except Exception:
                    pass
        self.update_undo_redo_state()
        self.sync_modern_tabs()
        if hasattr(self, 'secondary_split_pane') and self.secondary_split_pane.isVisible():
            if self.tab_widget.count() == 0:
                self.close_multiview()
            else:
                self.secondary_split_pane.refresh_open_documents_list()
        if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
            self.organize_workspace.load_document()
        if hasattr(self, 'modern_right_sidebar'):
            if self.tab_widget.count() == 0:
                self.modern_right_sidebar.clear_thumbnails()
                self.modern_right_sidebar.clear_accessibility()
            elif self.modern_right_sidebar.current_panel == "thumbnails":
                self.modern_right_sidebar.load_thumbnails()
            elif self.modern_right_sidebar.current_panel == "bookmarks":
                self.modern_right_sidebar.load_bookmarks()
            elif self.modern_right_sidebar.current_panel == "attachments":
                self.modern_right_sidebar.load_attachments()
            elif self.modern_right_sidebar.current_panel == "accessibility":
                panel_acc = getattr(self.modern_right_sidebar, 'panel_accessibility', None)
                if panel_acc:
                    panel_acc._sync_page_info()

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
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                if self.modern_right_sidebar.current_panel == "thumbnails":
                    self.modern_right_sidebar.load_thumbnails()
                    self.modern_right_sidebar.select_page(tab_doc.current_page_idx)
                elif self.modern_right_sidebar.current_panel == "bookmarks":
                    self.modern_right_sidebar.load_bookmarks()
                elif self.modern_right_sidebar.current_panel == "comments":
                    self.modern_right_sidebar.load_comments()
                elif self.modern_right_sidebar.current_panel == "attachments":
                    self.modern_right_sidebar.load_attachments()
                elif self.modern_right_sidebar.current_panel == "accessibility":
                    panel_acc = getattr(self.modern_right_sidebar, 'panel_accessibility', None)
                    if panel_acc:
                        se = getattr(panel_acc, 'speech_engine', None)
                        if not se or not se.is_speaking():
                            panel_acc._sync_page_info()
                            if getattr(panel_acc, '_source_mode', 'page') == "page":
                                panel_acc._load_current_page_text()
            self.update_viewport_cursor()
            if hasattr(self, 'search_bar') and self.search_bar.isVisible():
                self.search_bar.do_search(reset_index=True)
        elif self.tab_widget.count() == 0:
            if hasattr(self, 'modern_right_sidebar'):
                self.modern_right_sidebar.clear_thumbnails()
                self.modern_right_sidebar.clear_accessibility()
            self.txt_page.setText("0")
            self.lbl_total.setText(LanguageManager.tr("page_of", total=0))
            self.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=100)} ")
            self.thumbnails_dock.load_thumbnails_lazy()
            self.setWindowTitle(LanguageManager.tr("app_title"))
            if hasattr(self, 'search_bar') and self.search_bar.isVisible():
                self.search_bar.lbl_count.setText(LanguageManager.tr("search_no_results"))
        self.update_undo_redo_state()
        self.sync_modern_tabs()
        if hasattr(self, 'secondary_split_pane') and self.secondary_split_pane.isVisible():
            if self.tab_widget.count() == 0:
                self.close_multiview()
            else:
                self.secondary_split_pane.refresh_open_documents_list()
                if getattr(self.secondary_split_pane, 'is_sync_scroll_enabled', False):
                    self._connect_multiview_scroll_sync()
        if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
            self.modern_right_sidebar.load_bookmarks()
        if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
            self.organize_workspace.load_document()
        if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
            tab_doc = self.get_current_tab_doc()
            if tab_doc and tab_doc.doc:
                self.modern_header_bar.update_page_info(tab_doc.current_page_idx + 1, len(tab_doc.doc))
                self.modern_header_bar.update_zoom_info(int(round(tab_doc.zoom_level * 100)))
        if self.isFullScreen():
            tab_doc = self.get_current_tab_doc()
            if tab_doc and tab_doc.doc and len(tab_doc.doc) > 0:
                self.show_fullscreen_page_osd(tab_doc.current_page_idx + 1, len(tab_doc.doc))
                if hasattr(self, 'fullscreen_reading_hud') and self.fullscreen_reading_hud is not None:
                    self.fullscreen_reading_hud.update_state()

    def _on_zoom_input_submitted(self, val: int):
        if doc := self.get_current_tab_doc():
            doc.apply_zoom(val / 100.0)
            if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
                self.modern_header_bar.update_zoom_info(int(round(doc.zoom_level * 100)))
    def prev_page(self):
        if doc := self.get_current_tab_doc():
            new_idx = max(0, doc.current_page_idx - 1)
            doc.go_to_page(new_idx)
            if hasattr(self, 'modern_header_bar'):
                self.modern_header_bar.update_page_info(new_idx + 1, len(doc.doc))
    def next_page(self):
        if doc := self.get_current_tab_doc():
            new_idx = min(len(doc.doc) - 1, doc.current_page_idx + 1)
            doc.go_to_page(new_idx)
            if hasattr(self, 'modern_header_bar'):
                self.modern_header_bar.update_page_info(new_idx + 1, len(doc.doc))
    def jump_to_page(self):
        if (doc := self.get_current_tab_doc()) and self.txt_page.text().isdigit(): doc.go_to_page(int(self.txt_page.text()) - 1)
    def zoom_in(self):
        if doc := self.get_current_tab_doc(): doc.zoom_in()
    def zoom_out(self):
        if doc := self.get_current_tab_doc(): doc.zoom_out()
    def reset_zoom_100(self):
        if doc := self.get_current_tab_doc():
            doc.set_zoom(1.0)
            if hasattr(self, 'modern_header_bar') and self.modern_header_bar:
                self.modern_header_bar.update_zoom_info(100)
    def fit_to_width(self):
        if doc := self.get_current_tab_doc():
            doc.fit_to_width()
            doc._last_fit_mode = 'width'
            if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'btn_fit'):
                self.modern_header_bar.btn_fit.setToolTip(LanguageManager.tr("fit_to_page"))
                self.modern_header_bar.btn_fit.setIcon(ModernIconFactory.icon_fit_page())

    def fit_to_page(self):
        if doc := self.get_current_tab_doc():
            doc.fit_to_page()
            doc._last_fit_mode = 'page'
            if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'btn_fit'):
                self.modern_header_bar.btn_fit.setToolTip(LanguageManager.tr("fit_to_width"))
                self.modern_header_bar.btn_fit.setIcon(ModernIconFactory.icon_fit_width())

    def toggle_fit_page_width(self):
        if doc := self.get_current_tab_doc():
            if getattr(doc, '_last_fit_mode', 'page') == 'page':
                self.fit_to_width()
            else:
                self.fit_to_page()

    def nav_back(self):
        if doc := self.get_current_tab_doc(): doc.nav_back()

    def nav_forward(self):
        if doc := self.get_current_tab_doc(): doc.nav_forward()

    def set_reading_color_mode(self, mode: str):
        if doc := self.get_current_tab_doc(): doc.set_reading_color_mode(mode)

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

    def get_favorite_files(self) -> List[str]:
        settings = QSettings("AuraPDF", "Favorites")
        raw = settings.value("favorite_files", "[]")
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

    def is_favorite_file(self, file_path: str) -> bool:
        if not file_path:
            return False
        return os.path.abspath(file_path) in self.get_favorite_files()

    def add_to_favorite_files(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return
        file_path = os.path.abspath(file_path)
        current = self.get_favorite_files()
        if file_path not in current:
            current.insert(0, file_path)
            settings = QSettings("AuraPDF", "Favorites")
            import json
            settings.setValue("favorite_files", json.dumps(current))

    def remove_from_favorite_files(self, file_path: str):
        if not file_path:
            return
        file_path = os.path.abspath(file_path)
        current = self.get_favorite_files()
        if file_path in current:
            current.remove(file_path)
            settings = QSettings("AuraPDF", "Favorites")
            import json
            settings.setValue("favorite_files", json.dumps(current))

    def toggle_favorite_file(self, file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        file_path = os.path.abspath(file_path)
        current = self.get_favorite_files()
        if file_path in current:
            current.remove(file_path)
            is_fav = False
        else:
            current.insert(0, file_path)
            is_fav = True
        settings = QSettings("AuraPDF", "Favorites")
        import json
        settings.setValue("favorite_files", json.dumps(current))
        return is_fav

    def clear_favorite_files(self):
        settings = QSettings("AuraPDF", "Favorites")
        settings.remove("favorite_files")

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
            self.sync_modern_tabs()
            if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.organize_workspace.load_document()
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.load_bookmarks()
        except Exception:
            pass

    def rotate_current_page(self, angle: int = 90):
        tab_doc = self.get_current_tab_doc()
        if tab_doc and tab_doc.doc:
            curr_idx = getattr(tab_doc, 'current_page_idx', 0)
            tab_doc.rotate_page(curr_idx, angle)
            if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.organize_workspace.load_document(force=True)

    def rotate_all_pages(self):
        if doc := self.get_current_tab_doc():
            doc.rotate_all_pages()
            if hasattr(self, 'organize_workspace') and self.organize_workspace.isVisible():
                self.organize_workspace.load_document(force=True)

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
        tab_doc = self.get_current_tab_doc()
        mode = getattr(tab_doc, 'page_view_mode', 'single') if tab_doc else 'single'
        if hasattr(self, 'btn_view_mode') and self.btn_view_mode:
            if mode == 'double':
                self.btn_view_mode.setIcon(ModernIconFactory.icon_view_double())
            else:
                self.btn_view_mode.setIcon(ModernIconFactory.icon_view_single())
        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'update_view_mode_icon'):
            self.modern_header_bar.update_view_mode_icon(mode)

    # =========================================================================
    # MULTIVIEW (YAN YANA İKİ BELGE BÖLÜNMÜŞ GÖRÜNÜMÜ) METOTLARI
    # =========================================================================
    def toggle_multiview(self):
        """İki PDF belgesini yan yana bölünmüş ekranda görüntüleme modunu açar veya kapatır."""
        if not hasattr(self, 'secondary_split_pane') or not hasattr(self, 'document_splitter'):
            return
        if self.secondary_split_pane.isVisible():
            self.close_multiview()
        else:
            self.open_multiview()

    def open_multiview(self, second_file_path: Optional[str] = None):
        """İki belgeyi yan yana bölünmüş ekranda açar."""
        if self.tab_widget.count() == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("multiview_no_doc_warning"))
            return

        self.switch_to_document_view()

        # Splitter'ı 50% - 50% genişliğe ayarla
        self.secondary_split_pane.show()
        w = self.document_splitter.width()
        half_w = max(300, w // 2) if w > 0 else 500
        self.document_splitter.setSizes([half_w, half_w])

        # Eğer ikinci dosya belirtilmediyse, diğer açık sekmelerden birini otomatik seç
        if not second_file_path:
            cur_idx = self.tab_widget.currentIndex()
            if self.tab_widget.count() > 1:
                other_idx = (cur_idx + 1) % self.tab_widget.count()
                other_w = self.tab_widget.widget(other_idx)
                if other_w and getattr(other_w, 'file_path', None):
                    second_file_path = other_w.file_path

        if second_file_path and os.path.isfile(second_file_path):
            self.secondary_split_pane.load_document(second_file_path)
        else:
            self.secondary_split_pane.refresh_open_documents_list()

        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'set_multiview_active'):
            self.modern_header_bar.set_multiview_active(True)

    def close_multiview(self):
        """Multiview bölünmüş ekranını kapatır ve tekli belge görünümüne döner."""
        if hasattr(self, 'secondary_split_pane'):
            self.secondary_split_pane.close_document()
            self.secondary_split_pane.hide()
        if hasattr(self, 'modern_header_bar') and hasattr(self.modern_header_bar, 'set_multiview_active'):
            self.modern_header_bar.set_multiview_active(False)

    def swap_multiview_documents(self):
        """Sol (birincil) ve sağ (ikincil) belgelerin konumlarını yer değiştirir."""
        if not hasattr(self, 'secondary_split_pane') or not self.secondary_split_pane.isVisible():
            return
        sec_path = getattr(self.secondary_split_pane, 'file_path', None)
        prim_doc = self.get_current_tab_doc()
        prim_path = getattr(prim_doc, 'file_path', None) if prim_doc else None

        if not sec_path or not prim_path:
            return

        # 1. Sağdaki belgeyi sol taraftaki sekmelerde ara veya aç
        found_tab_idx = -1
        norm_sec = os.path.abspath(sec_path)
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            f_path = getattr(w, 'file_path', None)
            if f_path and os.path.abspath(f_path) == norm_sec:
                found_tab_idx = i
                break

        if found_tab_idx >= 0:
            self.tab_widget.setCurrentIndex(found_tab_idx)
        else:
            self.add_pdf_tab(sec_path)

        # 2. Önceki birincil belgeyi sağdaki ikincil panele yükle
        self.secondary_split_pane.load_document(prim_path)

    def _on_multiview_sync_scroll_toggled(self, enabled: bool):
        """Eşzamanlı kaydırma açıldığında veya kapandığında scrollbar sinyallerini bağlar/koparır."""
        self._connect_multiview_scroll_sync()

    def _connect_multiview_scroll_sync(self):
        if not hasattr(self, 'secondary_split_pane') or not self.secondary_split_pane.isVisible():
            return
        if not getattr(self.secondary_split_pane, 'is_sync_scroll_enabled', False):
            return
        prim_doc = self.get_current_tab_doc()
        sec_doc = getattr(self.secondary_split_pane, 'tab_doc', None)
        if not prim_doc or not sec_doc or not hasattr(prim_doc, 'view') or not hasattr(sec_doc, 'view'):
            return

        try:
            prim_bar = prim_doc.view.verticalScrollBar()
            prim_bar.valueChanged.disconnect(self._on_primary_doc_scrolled)
        except Exception:
            pass
        try:
            sec_bar = sec_doc.view.verticalScrollBar()
            sec_bar.valueChanged.disconnect(self._on_secondary_doc_scrolled)
        except Exception:
            pass

        prim_doc.view.verticalScrollBar().valueChanged.connect(self._on_primary_doc_scrolled)
        sec_doc.view.verticalScrollBar().valueChanged.connect(self._on_secondary_doc_scrolled)

    def _on_primary_doc_scrolled(self, val: int):
        if getattr(self, '_is_syncing_multiview_scroll', False):
            return
        if not hasattr(self, 'secondary_split_pane') or not self.secondary_split_pane.isVisible():
            return
        if not getattr(self.secondary_split_pane, 'is_sync_scroll_enabled', False):
            return
        prim_doc = self.get_current_tab_doc()
        sec_doc = getattr(self.secondary_split_pane, 'tab_doc', None)
        if not prim_doc or not sec_doc or not hasattr(sec_doc, 'view'):
            return

        v_prim = prim_doc.view.verticalScrollBar()
        v_sec = sec_doc.view.verticalScrollBar()
        max_prim = v_prim.maximum()
        max_sec = v_sec.maximum()
        if max_prim <= 0 or max_sec <= 0:
            return

        ratio = val / float(max_prim)
        self._is_syncing_multiview_scroll = True
        try:
            v_sec.setValue(int(ratio * max_sec))
        finally:
            self._is_syncing_multiview_scroll = False

    def _on_secondary_doc_scrolled(self, val: int):
        if getattr(self, '_is_syncing_multiview_scroll', False):
            return
        if not hasattr(self, 'secondary_split_pane') or not self.secondary_split_pane.isVisible():
            return
        if not getattr(self.secondary_split_pane, 'is_sync_scroll_enabled', False):
            return
        prim_doc = self.get_current_tab_doc()
        sec_doc = getattr(self.secondary_split_pane, 'tab_doc', None)
        if not prim_doc or not sec_doc or not hasattr(prim_doc, 'view'):
            return

        v_prim = prim_doc.view.verticalScrollBar()
        v_sec = sec_doc.view.verticalScrollBar()
        max_prim = v_prim.maximum()
        max_sec = v_sec.maximum()
        if max_prim <= 0 or max_sec <= 0:
            return

        ratio = val / float(max_sec)
        self._is_syncing_multiview_scroll = True
        try:
            v_prim.setValue(int(ratio * max_prim))
        finally:
            self._is_syncing_multiview_scroll = False

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
            self.sync_modern_tabs()
            self.switch_to_document_view()
            if hasattr(self, 'organize_workspace') and hasattr(self, 'central_stack') and self.central_stack.currentWidget() == self.organize_workspace:
                self.organize_workspace.load_document()
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.load_bookmarks()
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
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.load_thumbnails()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), str(e))

    def show_new_page_dialog(self, default_style: Optional[str] = None, force_new_doc: bool = False, default_placement: str = "after_current"):
        """Kullanıcının görsel şablon kartları arasından stil, yön, boyut ve konum
        seçerek sayfalar eklemesini veya yeni belge oluşturmasını sağlar."""
        try:
            if default_style is None:
                settings = QSettings("AuraPDF", "PDFViewer")
                default_style = settings.value("default_page_template", "blank")
            from src.ui.dialogs.new_page_dialog import NewPageDialog
            dlg = NewPageDialog(self, default_style=default_style, force_new_doc=force_new_doc, default_placement=default_placement)
            if dlg.exec():
                cfg = dlg.get_page_config()
                style = cfg.get("style", "blank")
                w = cfg.get("width")
                h = cfg.get("height")
                count = cfg.get("count", 1)
                placement = cfg.get("placement", "after_current")

                tab_doc = self.get_current_tab_doc()
                if force_new_doc or placement == "new_doc" or not tab_doc or tab_doc.doc is None or len(tab_doc.doc) == 0:
                    # Yeni belge oluştur
                    for i in range(count):
                        if i == 0:
                            self.new_blank_document(template_type=style, width=w, height=h, create_page=True)
                        else:
                            curr_tab = self.get_current_tab_doc()
                            if curr_tab and curr_tab.doc is not None:
                                is_last = (i == count - 1)
                                curr_tab.insert_blank_page(
                                    after_page=len(curr_tab.doc) - 1,
                                    width=w,
                                    height=h,
                                    style=style,
                                    rerender=is_last,
                                    notify_thumb=is_last
                                )
                else:
                    # Mevcut açık belgeye ekle
                    curr_idx = getattr(tab_doc, 'current_page_idx', 0)
                    if curr_idx is None or not isinstance(curr_idx, int):
                        curr_idx = 0
                    if placement == "before_current":
                        start_pos = max(-1, curr_idx - 1)
                    elif placement == "after_current":
                        start_pos = max(-1, min(curr_idx, len(tab_doc.doc) - 1))
                    else:  # "end"
                        start_pos = len(tab_doc.doc) - 1

                    for i in range(count):
                        is_last = (i == count - 1)
                        tab_doc.insert_blank_page(
                            after_page=start_pos + i,
                            width=w,
                            height=h,
                            style=style,
                            rerender=is_last,
                            notify_thumb=is_last
                        )

                    target_page = max(0, min(start_pos + count, len(tab_doc.doc) - 1))
                    try:
                        tab_doc.go_to_page(target_page)
                    except Exception:
                        pass
                    if hasattr(self, 'lbl_total') and self.lbl_total:
                        try:
                            self.lbl_total.setText(LanguageManager.tr("page_of", total=len(tab_doc.doc)))
                        except Exception:
                            pass
                    if hasattr(self, 'txt_page') and self.txt_page:
                        try:
                            self.txt_page.setText(str(target_page + 1))
                        except Exception:
                            pass
                    if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar:
                        try:
                            self.modern_right_sidebar.select_page(target_page)
                        except Exception:
                            pass
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
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.thumbnails_dock)
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

    def clear_page_drawings(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not getattr(tab_doc, 'drawings', None):
            return
        curr_page = getattr(tab_doc, 'current_page_idx', 0)
        has_drawings_on_page = any(d.get("page", 0) == curr_page for d in tab_doc.drawings)
        if not has_drawings_on_page:
            return
        reply = QMessageBox.question(
            self,
            LanguageManager.tr("clear_page_drawings"),
            LanguageManager.tr("confirm_clear_page_drawings"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            tab_doc.clear_page_drawings(curr_page)

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
        if hasattr(self, 'hl_ruler_popup'):
            self.hl_ruler_popup.refresh_state()

    def sync_ruler_state(self):
        is_snap = False
        if hasattr(self, 'hl_popup') and getattr(self.hl_popup, 'snap_straight', False):
            is_snap = True
        elif hasattr(self, 'pen_popup') and getattr(self.pen_popup, 'snap_straight', False):
            is_snap = True
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
            (getattr(self, 'btn_direct_edit', None), ('direct_edit',)),
            (getattr(self, 'btn_selection', None), ('selection_tool', 'ruler')), (getattr(self, 'btn_pointer', None), ('pointer',))
        ]:

            if btn is not None:
                btn.setChecked(tool_name in names)
        
        if hasattr(self, 'floating_capsule') and self.floating_capsule is not None:
            if tool_name in ('select', 'pan'):
                self.floating_capsule.set_active_tool('select')
            elif tool_name in ('selection_tool', 'ruler'):
                self.floating_capsule.set_active_tool('selection')
            elif tool_name == 'pointer':
                self.floating_capsule.set_active_tool('pointer')
            elif tool_name == 'highlighter':
                self.floating_capsule.set_active_tool('highlighter')
            elif tool_name in ('text', 'direct_edit'):
                self.floating_capsule.set_active_tool('text')
            elif tool_name == 'comment':
                self.floating_capsule.set_active_tool('comment')
            elif tool_name == 'pen':
                self.floating_capsule.set_active_tool('pen')
            elif tool_name == 'eraser':
                self.floating_capsule.set_active_tool('eraser')

        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
            if hasattr(self, 'floating_capsule') and self.floating_capsule:
                self.top_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
            if hasattr(self, 'floating_capsule') and self.floating_capsule:
                self.left_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)
        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
            if hasattr(self, 'floating_capsule') and self.floating_capsule:
                self.right_pinned_tools_bar.set_active_tool(self.floating_capsule.active_tool)

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

            if tool_name == 'direct_edit':
                tab_doc.enable_direct_text_edit(True)
            else:
                # Moddan açıkça çıkılmadığı sürece direct_edit_mode korunur.
                # Başka bir araca (çizim, görsel vb.) geçildiğinde sadece aktif yerinde metin kutusu kapatılır.
                if getattr(tab_doc, 'direct_edit_mode', False):
                    tab_doc.close_inplace_editor()
                    if getattr(tab_doc, 'direct_edit_hover_item', None):
                        tab_doc.direct_edit_hover_item.hide()

            if getattr(tab_doc, 'direct_edit_banner', None):
                tab_doc.direct_edit_banner.update_active_tool(tool_name)

        if hasattr(self, 'modern_left_sidebar') and self.modern_left_sidebar:
            if hasattr(self.modern_left_sidebar, 'fill_sign_drawer') and self.modern_left_sidebar.fill_sign_drawer.active_tool_id == 'add_text' and tool_name != 'text':
                self.modern_left_sidebar.fill_sign_drawer.clear_active_state()
            if hasattr(self.modern_left_sidebar, 'edit_drawer') and self.modern_left_sidebar.edit_drawer.active_edit_id:
                if self.modern_left_sidebar.edit_drawer.active_edit_id == 'text' and tool_name != 'text':
                    self.modern_left_sidebar.edit_drawer.clear_active_state()
                elif self.modern_left_sidebar.edit_drawer.active_edit_id == 'edit_text_images' and tool_name != 'direct_edit':
                    self.modern_left_sidebar.edit_drawer.clear_active_state()

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
            'comment': Qt.CursorShape.PointingHandCursor,
            'direct_edit': Qt.CursorShape.IBeamCursor,
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

    open_file_dialog = open_pdf

    def save_pdf(self):
        """Belgeyi mevcut dosyasının üzerine doğrudan ve atomik olarak kaydeder (Ctrl+S)."""
        self._perform_save(save_as=False)

    def save_as_pdf(self):
        """Belgeyi yeni bir dosya adı/konumu seçerek kaydeder (Farklı Kaydet / Ctrl+Shift+S)."""
        self._perform_save(save_as=True)

    def _perform_save(self, save_as: bool = False):
        if not (tab_doc := self.get_current_tab_doc()) or tab_doc.doc is None or len(tab_doc.doc) == 0:
            return QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("no_pdf_save"))

        existing_path = getattr(tab_doc, 'file_path', None)
        if save_as or not existing_path or not os.path.isfile(existing_path):
            if existing_path:
                default_name = existing_path
            elif getattr(tab_doc, 'custom_title', None):
                default_name = tab_doc.custom_title.lstrip("*").strip()
                if not default_name.lower().endswith(".pdf"):
                    default_name += ".pdf"
            else:
                default_name = LanguageManager.tr("untitled_doc")
                if not default_name.lower().endswith(".pdf"):
                    default_name += ".pdf"
            path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("save_dialog_title"), default_name, "PDF (*.pdf)")
            if not path:
                return
        else:
            path = existing_path

        try:
            # 1. Etkileşimli formları senkronize et
            if hasattr(tab_doc, 'sync_form_fields'):
                tab_doc.sync_form_fields()

            # 2. In-memory tab_doc.doc nesnesini KORUMAK için bağımsız export kopyası oluştur
            # tab_doc.export_drawings_to_pdf hedef dokümana kalıcı vektörel çizimler, resimler ve tablolar ekler.
            # Bağımsız export_doc kullanarak tab_doc.doc'u sahnede çift öğe oluşmaması için tertemiz tutuyoruz.
            export_doc = fitz.open(stream=tab_doc.doc.tobytes(), filetype="pdf")
            tab_doc.export_drawings_to_pdf(export_doc)

            # 3. Yazar üstverisi ayarlarını kontrol et ve gerekirse uygula
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
                        meta = export_doc.metadata or {}
                        meta["author"] = f"{author} ({title})" if title else author
                        export_doc.set_metadata(meta)
                    except Exception:
                        pass

            # 4. Diske güvenli ve atomik kaydetme
            target_path = os.path.abspath(path)
            temp_path = target_path + ".tmp_save"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            export_doc.save(temp_path, garbage=3, deflate=True)
            export_doc.close()

            # Kendi kaydımız sırasında dosya izleyicinin gereksiz harici bildirim tetiklemesini önle
            watched = False
            norm_target = os.path.abspath(target_path)
            if hasattr(self, 'file_watcher') and hasattr(self.file_watcher, 'files'):
                if norm_target in [os.path.abspath(f) for f in self.file_watcher.files()]:
                    try:
                        self.file_watcher.removePath(norm_target)
                        watched = True
                    except Exception:
                        pass

            try:
                if os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except Exception:
                        pass
                os.replace(temp_path, target_path)
            except Exception:
                # Fallback: doğrudan taşı veya kopyala
                if os.path.exists(temp_path):
                    import shutil
                    shutil.copy2(temp_path, target_path)
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

            if watched and hasattr(self, 'file_watcher'):
                try:
                    self.file_watcher.addPath(norm_target)
                except Exception:
                    pass

            tab_doc.file_path = target_path
            self.add_to_recent_files(target_path)

            tab_doc.clear_selection()
            tab_doc.save_undo_index = len(tab_doc.undo_stack)
            tab_doc.set_modified(False)
            tab_doc.update_tab_title()
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
            if hasattr(self, 'modern_right_sidebar') and self.modern_right_sidebar and self.modern_right_sidebar.isVisible():
                self.modern_right_sidebar.load_thumbnails()

            if save_as:
                QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("save_success"))
            else:
                if hasattr(self, 'statusBar') and self.statusBar():
                    self.statusBar().showMessage(LanguageManager.tr("save_success"), 3500)

        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('error')}: {str(e)}")

    def print_pdf(self):
        if not (tab_doc := self.get_current_tab_doc()) or tab_doc.doc is None or len(tab_doc.doc) == 0:
            return QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("no_pdf_print"))
        if hasattr(tab_doc, 'sync_form_fields'):
            try:
                tab_doc.sync_form_fields()
            except Exception:
                pass
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
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return
        try:
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
                    alt_cell_bg=data.get("alt_cell_bg", "#f5f3ff"),
                    alignment=data.get("alignment", "center")
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, LanguageManager.tr("error", default="Hata"), f"{LanguageManager.tr('error', default='Hata')}: {e}")

    def show_insert_emoji_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
                        title=dlg.txt_title.text().strip() or LanguageManager.tr("audio_record_title"),
                        duration_sec=dlg.duration_sec,
                        format=dlg.format
                    )
                else:
                    QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))

        def on_finished(result):
            if hasattr(self, '_audio_record_dialog') and self._audio_record_dialog == dlg:
                self._audio_record_dialog = None

        dlg.accepted.connect(on_accepted)
        dlg.finished.connect(on_finished)
        dlg.show()

    def show_insert_video_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
                QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("audio_file_add_error", error=str(e)))

    def insert_sticky_note(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or len(tab_doc.doc) == 0:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
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
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        if getattr(tab_doc, 'direct_edit_mode', False) and self.current_tool == 'direct_edit':
            tab_doc.exit_direct_text_edit()
        else:
            self.set_tool_state('direct_edit')

    def open_pdf_content_editor_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("no_active_doc_error"))
            return
        from src.ui.dialogs.pdf_content_editor_dialog import PDFContentEditorDialog
        dlg = PDFContentEditorDialog(self)
        dlg.exec()

    def open_signature_dialog(self):
        tab_doc = self.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("open_pdf_first_warning"))
            return
        from src.ui.dialogs.settings_dialog import get_effective_author_name
        author_name = get_effective_author_name()
        try:
            from src.ui.dialogs.pdf_signature_dialog import PDFSignatureDialog
            dlg = PDFSignatureDialog(self, default_name=author_name)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_image is not None:
                tab_doc.add_signature(dlg.result_image)
                QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("sign_placed_success"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, LanguageManager.tr("error"), LanguageManager.tr("sign_error_msg", error=str(e)))

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

    def open_ai_assistant_dialog(self, file_path: str = None, action: str = "summary"):
        """Aura AI Belge Asistani diyalogunu belirtilen belge ve eylemle açar."""
        target_path = file_path
        if not target_path:
            if hasattr(self, 'tab_widget') and self.tab_widget.count() > 0:
                cur_widget = self.tab_widget.currentWidget()
                if cur_widget and getattr(cur_widget, 'file_path', None) and os.path.exists(cur_widget.file_path):
                    target_path = cur_widget.file_path

        if not target_path or not os.path.exists(target_path):
            path, _ = QFileDialog.getOpenFileName(
                self,
                LanguageManager.tr("home_ai_btn_open"),
                "",
                "PDF Files (*.pdf)"
            )
            if path and os.path.isfile(path):
                self._pending_ai_action = action
                self.add_pdf_tab(path)
            return

        from src.ui.dialogs.ai_assistant_dialog import AuraAiAssistantDialog
        dlg = AuraAiAssistantDialog(target_path, initial_action=action, main_window=self, parent=self)
        dlg.show()

    def save_toolbar_order(self):
        if not hasattr(self, 'toolbar'):
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

    def reset_toolbar_order(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.remove("toolbar_order")
        self.restore_toolbar_order()

    def apply_floating_tools_order(self, order: list):
        if hasattr(self, 'floating_capsule') and self.floating_capsule:
            self.floating_capsule.set_tools_order(order)
            self.update_floating_capsule_pos()
        if hasattr(self, 'top_pinned_tools_bar') and self.top_pinned_tools_bar:
            self.top_pinned_tools_bar.set_tools_order(order)
            self.update_floating_capsule_pos()
        if hasattr(self, 'left_pinned_tools_bar') and self.left_pinned_tools_bar:
            self.left_pinned_tools_bar.set_tools_order(order)
        if hasattr(self, 'right_pinned_tools_bar') and self.right_pinned_tools_bar:
            self.right_pinned_tools_bar.set_tools_order(order)

    def set_classic_toolbar_mode(self, enabled: bool):
        if not hasattr(self, 'toolbar'):
            return
        if enabled:
            if self.toolBarArea(self.toolbar) == Qt.ToolBarArea.NoToolBarArea:
                self.addToolBar(self.toolbar)
            if hasattr(self, 'central_stack') and self.central_stack.currentWidget() in (self.tab_widget, getattr(self, 'document_splitter', None)):
                self.toolbar.show()
            self.restore_toolbar_order()
        else:
            self.removeToolBar(self.toolbar)
            self.toolbar.hide()

    def closeEvent(self, event):
        self.save_toolbar_order()
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument):
                widget.save_zoom_setting()
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, PDFTabDocument) and widget.is_modified:
                raw_fallback = getattr(widget, 'custom_title', None) or f"{LanguageManager.tr('untitled')}.pdf"
                fallback_name = str(raw_fallback).lstrip("*").strip()
                if not fallback_name.lower().endswith(".pdf"):
                    fallback_name += ".pdf"
                base_name = os.path.basename(widget.file_path) if widget.file_path else fallback_name
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
        if hasattr(self, '_audio_record_dialog') and self._audio_record_dialog is not None:
            try:
                self._audio_record_dialog.close()
            except Exception:
                pass
        if hasattr(self, 'modern_right_sidebar') and getattr(self.modern_right_sidebar, 'speech_engine', None):
            try:
                self.modern_right_sidebar.speech_engine.stop()
            except Exception:
                pass
        super().closeEvent(event)

# AuraPDF Marka İsimlendirmesi ile Geriye Dönük Uyumluluk Takma Adı (Alias)
ModernPDFViewer = AuraPDFViewer



