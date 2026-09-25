from typing import Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QPushButton, QSlider, QFrame, QColorDialog, 
                             QFontComboBox, QComboBox, QCheckBox, QApplication, QInputDialog, QMessageBox)
from PyQt6.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath, QTextCursor, QFontMetricsF)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, QSettings
from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory

# --- 0. POPUP TEMA ŞABLONLARI ---
POPUP_THEME_SPECS = {
    "gray": {
        "main_bg": "#2b2d30", "main_text": "#f1f5f9", "tb_bg": "#35383c", "tb_border": "#444850",
        "btn_hover": "#444850", "accent": "#60a5fa", "page_bg": "#3e4247", "page_border": "#555b62",
        "tab_bg": "#2b2d30", "tab_hover": "#3a3d42", "tab_border": "#444850", "tab_text": "#cbd5e1",
        "view_bg": "#1e1f22"
    },
    "navy": {
        "main_bg": "#0f172a", "main_text": "#e2e8f0", "tb_bg": "#1e293b", "tb_border": "#334155",
        "btn_hover": "#334155", "accent": "#38bdf8", "page_bg": "#1e293b", "page_border": "#475569",
        "tab_bg": "#0f172a", "tab_hover": "#1e293b", "tab_border": "#334155", "tab_text": "#94a3b8",
        "view_bg": "#090d16"
    },
    "emerald": {
        "main_bg": "#091a14", "main_text": "#ecfdf5", "tb_bg": "#112a21", "tb_border": "#1a3d30",
        "btn_hover": "#1a3d30", "accent": "#10b981", "page_bg": "#13382c", "page_border": "#214e3e",
        "tab_bg": "#0c2019", "tab_hover": "#16382c", "tab_border": "#1e4738", "tab_text": "#a7f3d0",
        "view_bg": "#050f0c"
    },
    "purple": {
        "main_bg": "#150d22", "main_text": "#faf5ff", "tb_bg": "#201435", "tb_border": "#321f52",
        "btn_hover": "#321f52", "accent": "#a855f7", "page_bg": "#271941", "page_border": "#3f2766",
        "tab_bg": "#180f27", "tab_hover": "#291a43", "tab_border": "#3a255e", "tab_text": "#d8b4fe",
        "view_bg": "#0c0714"
    },
    "crimson": {
        "main_bg": "#1d0b10", "main_text": "#fff1f2", "tb_bg": "#2d1118", "tb_border": "#441924",
        "btn_hover": "#441924", "accent": "#f43f5e", "page_bg": "#37151e", "page_border": "#551e2c",
        "tab_bg": "#200c12", "tab_hover": "#37151e", "tab_border": "#4e1c28", "tab_text": "#fecdd3",
        "view_bg": "#110609"
    },
    "nord": {
        "main_bg": "#181e29", "main_text": "#f0f6fc", "tb_bg": "#222b3a", "tb_border": "#313e54",
        "btn_hover": "#313e54", "accent": "#38bdf8", "page_bg": "#2a3649", "page_border": "#3e4f6a",
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

# --- 0. POPUP TABAN SINIFI ---
class BaseSettingsPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        settings = QSettings("AuraPDF", "PDFViewer")
        current_th = settings.value("app_theme", "dark")
        spec = POPUP_THEME_SPECS.get(current_th, POPUP_THEME_SPECS["dark"])
        self.apply_theme(current_th, spec)

    def show_below(self, button_widget):
        point = button_widget.mapToGlobal(QPoint(0, button_widget.height() + 4))
        self.move(point)
        self.show()

    def show_at(self, global_pos: QPoint):
        self.adjustSize()
        w = max(self.width(), self.sizeHint().width())
        h = max(self.height(), self.sizeHint().height())
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None
        x = global_pos.x() + 2
        y = global_pos.y() + 2
        if screen_geo:
            if x + w > screen_geo.right() - 8:
                x = max(screen_geo.left() + 8, global_pos.x() - w - 2)
            if y + h > screen_geo.bottom() - 8:
                y = max(screen_geo.top() + 8, global_pos.y() - h - 2)
        self.move(x, y)
        self.show()

    def apply_theme(self, theme_name, spec):
        self.setStyleSheet(f"""
            QWidget, QWidget#RulerCard, QWidget#MeasurementCard {{
                background-color: {spec['tb_bg']};
                color: {spec['main_text']};
                font-size: 12px;
                border: 1px solid {spec['tb_border']};
                border-radius: 8px;
            }}
            QLabel {{
                color: {spec['main_text']};
                font-weight: bold;
                border: none;
                background: transparent;
            }}
            QLabel#SectionHeader, QLabel#FieldLabel, QLabel#Desc, QLabel#Title {{
                color: {spec['main_text']};
                font-size: 11px;
                font-weight: bold;
                border: none;
                background: transparent;
            }}
            QLabel#Tip, QLabel#TipLabel {{
                color: {spec['tab_text']};
                font-size: 10px;
                font-style: italic;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                background-color: {spec['main_bg']};
                color: {spec['main_text']};
                border: 1px solid {spec['tb_border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {spec['btn_hover']};
                color: #ffffff;
                border-color: {spec['accent']};
            }}
            QPushButton:checked, QPushButton[checked="true"] {{
                background-color: {spec['accent']};
                color: #ffffff;
                border: 1px solid {spec['accent']};
                font-weight: bold;
            }}
            QPushButton#FormatBtn, QPushButton.segment-btn, QPushButton#ToggleBtn {{
                background-color: {spec['main_bg']};
                color: {spec['tab_text']};
                border: 1px solid {spec['tb_border']};
                border-radius: 6px;
                padding: 4px 6px;
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
            QPushButton#FormatBtn:hover, QPushButton.segment-btn:hover, QPushButton#ToggleBtn:hover {{
                background-color: {spec['btn_hover']};
                color: {spec['main_text']};
                border-color: {spec['accent']};
            }}
            QPushButton#FormatBtn:checked, QPushButton#FormatBtn[checked="true"],
            QPushButton.segment-btn[checked="true"], QPushButton#ToggleBtn:checked {{
                background-color: {spec['accent']};
                color: #ffffff;
                border: 1px solid {spec['accent']};
                font-weight: bold;
            }}
            QPushButton#ClearBtn {{
                background-color: #2e1d20;
                color: #f87171;
                border: 1px solid #4d252a;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton#ClearBtn:hover {{
                background-color: #441f25;
                border-color: #ef4444;
                color: #ffffff;
            }}
            QComboBox {{
                background-color: {spec['main_bg']};
                color: {spec['main_text']};
                border: 1px solid {spec['tb_border']};
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                min-height: 24px;
            }}
            QComboBox:focus {{
                border-color: {spec['accent']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {spec['tb_bg']};
                color: {spec['main_text']};
                selection-background-color: {spec['accent']};
                selection-color: #ffffff;
                border: 1px solid {spec['tb_border']};
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 24px;
                padding: 3px 6px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {spec['page_border']};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {spec['accent']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {spec['accent']};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                border: 1px solid #ffffff;
            }}
            QCheckBox {{
                spacing: 6px;
                border: none;
                font-weight: normal;
                color: {spec['main_text']};
                background: transparent;
            }}
            QFrame#Divider {{
                background-color: {spec['tb_border']};
                max-height: 1px;
                border: none;
            }}
            QMenu {{
                background-color: {spec['tb_bg']};
                color: {spec['main_text']};
                border: 1px solid {spec['tb_border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QMenu::item:selected {{
                background-color: {spec['accent']};
                color: #ffffff;
            }}
        """)


# --- 3. SEÇİM AYARLARI POPUP'I (SEGMENTED BUTON GRUBU) ---
class SelectionSettingsPopup(BaseSettingsPopup):
    """
    Seçim ve Ölçüm Ayarları Açılır Penceresi (Selection & Measurement Tools).
    - Standart İmleç (Select), El Aracı (Pan), Dikdörtgen, Kement, Yer Değiştirme
    - Ölçüm Modu: Cetvel & Boyut Ölçümü (Acrobat Pro)
    - Cetvel Birimi, Belge Ölçeği ve Ölçümleri Temizleme kontrolleri
    """
    def __init__(self, parent=None, on_mode_change=None):
        super().__init__(parent)
        self.main_window = parent
        self.on_mode_change = on_mode_change
        self.current_mode = "rect"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 1. BÖLÜM: SEÇİM & GEZİNME ARAÇLARI
        self.lbl_sec_sel = QLabel(LanguageManager.tr("sel_mode"))
        self.lbl_sec_sel.setObjectName("SectionHeader")
        layout.addWidget(self.lbl_sec_sel)

        self.btn_select = QPushButton(" ↖ " + LanguageManager.tr("cursor_arrow"))
        self.btn_select.setIcon(ModernIconFactory.icon_cursor())
        self.btn_select.setCheckable(True)
        self.btn_select.clicked.connect(lambda: self._select_mode("select"))

        self.btn_pan = QPushButton(" ✋ " + LanguageManager.tr("cursor_pan"))
        self.btn_pan.setIcon(ModernIconFactory.icon_select_pan())
        self.btn_pan.setCheckable(True)
        self.btn_pan.clicked.connect(lambda: self._select_mode("pan"))

        self.btn_rect = QPushButton(LanguageManager.tr("sel_rect"))
        self.btn_rect.setIcon(ModernIconFactory.icon_select_rect())
        self.btn_rect.setCheckable(True)
        self.btn_rect.setChecked(True)
        self.btn_rect.clicked.connect(lambda: self._select_mode("rect"))

        self.btn_lasso = QPushButton(LanguageManager.tr("sel_lasso"))
        self.btn_lasso.setIcon(ModernIconFactory.icon_select_lasso())
        self.btn_lasso.setCheckable(True)
        self.btn_lasso.clicked.connect(lambda: self._select_mode("lasso"))

        self.btn_move = QPushButton(LanguageManager.tr("sel_move"))
        self.btn_move.setIcon(ModernIconFactory.icon_select_move())
        self.btn_move.setCheckable(True)
        self.btn_move.clicked.connect(lambda: self._select_mode("move"))

        layout.addWidget(self.btn_select)
        layout.addWidget(self.btn_pan)
        layout.addWidget(self.btn_rect)
        layout.addWidget(self.btn_lasso)
        layout.addWidget(self.btn_move)

        # Ayırıcı Çizgi
        sep = QFrame()
        sep.setObjectName("Divider")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # 2. BÖLÜM: ÖLÇÜM CETVELİ (ACROBAT PRO)
        self.lbl_sec_ruler = QLabel(LanguageManager.tr("sel_ruler_options"))
        self.lbl_sec_ruler.setObjectName("SectionHeader")
        layout.addWidget(self.lbl_sec_ruler)

        self.btn_ruler = QPushButton(LanguageManager.tr("sel_ruler"))
        self.btn_ruler.setIcon(ModernIconFactory.icon_ruler())
        self.btn_ruler.setCheckable(True)
        self.btn_ruler.clicked.connect(lambda: self._select_mode("ruler"))
        layout.addWidget(self.btn_ruler)

        # Cetvel Seçenekleri Paneli
        self.box_ruler_opts = QWidget()
        l_ro = QVBoxLayout(self.box_ruler_opts)
        l_ro.setContentsMargins(0, 2, 0, 2)
        l_ro.setSpacing(6)

        # Birim Seçimi
        h_unit = QHBoxLayout()
        h_unit.setSpacing(6)
        self.lbl_unit = QLabel(LanguageManager.tr("ruler_unit_lbl"))
        self.lbl_unit.setStyleSheet("font-size: 11px; font-weight: normal; color: #94a3b8;")
        h_unit.addWidget(self.lbl_unit)

        self.cmb_unit = QComboBox()
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_cm"), "cm")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_mm"), "mm")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_in"), "in")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_pt"), "pt")
        self.cmb_unit.currentIndexChanged.connect(self._on_unit_changed)
        h_unit.addWidget(self.cmb_unit, stretch=1)
        l_ro.addLayout(h_unit)

        # Ölçek Seçimi
        h_scale = QHBoxLayout()
        h_scale.setSpacing(6)
        self.lbl_scale = QLabel(LanguageManager.tr("ruler_scale_lbl"))
        self.lbl_scale.setStyleSheet("font-size: 11px; font-weight: normal; color: #94a3b8;")
        h_scale.addWidget(self.lbl_scale)

        self.cmb_scale = QComboBox()
        self.cmb_scale.addItem("1:1 (Varsayılan)", 1.0)
        self.cmb_scale.addItem("1:2", 2.0)
        self.cmb_scale.addItem("1:5", 5.0)
        self.cmb_scale.addItem("1:10", 10.0)
        self.cmb_scale.addItem("1:20", 20.0)
        self.cmb_scale.addItem("1:50", 50.0)
        self.cmb_scale.addItem("1:100", 100.0)
        self.cmb_scale.addItem("2:1", 0.5)
        self.cmb_scale.currentIndexChanged.connect(self._on_scale_changed)
        h_scale.addWidget(self.cmb_scale, stretch=1)
        l_ro.addLayout(h_scale)

        # Ölçümleri Temizle Butonu
        self.btn_clear_ruler = QPushButton(LanguageManager.tr("ruler_clear_all"))
        self.btn_clear_ruler.setObjectName("ClearBtn")
        self.btn_clear_ruler.setIcon(ModernIconFactory.icon_eraser())
        self.btn_clear_ruler.clicked.connect(self._on_clear_ruler_clicked)
        l_ro.addWidget(self.btn_clear_ruler)

        # İpucu Etiketi
        self.lbl_tip = QLabel(LanguageManager.tr("ruler_tip"))
        self.lbl_tip.setObjectName("TipLabel")
        self.lbl_tip.setWordWrap(True)
        l_ro.addWidget(self.lbl_tip)

        layout.addWidget(self.box_ruler_opts)
        self.box_ruler_opts.setVisible(False)
        self.setFixedWidth(280)

    def _on_unit_changed(self):
        unit = self.cmb_unit.currentData() or "cm"
        parent_mw = self.parent() or self.main_window
        if parent_mw:
            parent_mw.measurement_unit = unit
            if hasattr(parent_mw, 'get_current_tab_doc'):
                if tab_doc := parent_mw.get_current_tab_doc():
                    scale_ratio = getattr(parent_mw, 'measurement_scale', 1.0)
                    tab_doc.update_measurement_settings(unit, scale_ratio)

    def _on_scale_changed(self):
        scale_ratio = float(self.cmb_scale.currentData() or 1.0)
        parent_mw = self.parent() or self.main_window
        if parent_mw:
            parent_mw.measurement_scale = scale_ratio
            if hasattr(parent_mw, 'get_current_tab_doc'):
                if tab_doc := parent_mw.get_current_tab_doc():
                    unit = getattr(parent_mw, 'measurement_unit', 'cm')
                    tab_doc.update_measurement_settings(unit, scale_ratio)

    def _on_clear_ruler_clicked(self):
        parent_mw = self.parent() or self.main_window
        if parent_mw and hasattr(parent_mw, 'get_current_tab_doc'):
            if tab_doc := parent_mw.get_current_tab_doc():
                tab_doc.clear_all_measurements()

    def retranslate_ui(self):
        self.lbl_sec_sel.setText(LanguageManager.tr("sel_mode"))
        if hasattr(self, 'btn_select'):
            self.btn_select.setText(" ↖ " + LanguageManager.tr("cursor_arrow"))
        if hasattr(self, 'btn_pan'):
            self.btn_pan.setText(" ✋ " + LanguageManager.tr("cursor_pan"))
        self.btn_rect.setText(LanguageManager.tr("sel_rect"))
        self.btn_lasso.setText(LanguageManager.tr("sel_lasso"))
        self.btn_move.setText(LanguageManager.tr("sel_move"))
        self.lbl_sec_ruler.setText(LanguageManager.tr("sel_ruler_options"))
        self.btn_ruler.setText(LanguageManager.tr("sel_ruler"))
        self.lbl_unit.setText(LanguageManager.tr("ruler_unit_lbl"))
        self.lbl_scale.setText(LanguageManager.tr("ruler_scale_lbl"))
        self.btn_clear_ruler.setText(LanguageManager.tr("ruler_clear_all"))
        self.lbl_tip.setText(LanguageManager.tr("ruler_tip"))

        self.cmb_unit.blockSignals(True)
        self.cmb_unit.setItemText(0, LanguageManager.tr("ruler_unit_cm"))
        self.cmb_unit.setItemText(1, LanguageManager.tr("ruler_unit_mm"))
        self.cmb_unit.setItemText(2, LanguageManager.tr("ruler_unit_in"))
        self.cmb_unit.setItemText(3, LanguageManager.tr("ruler_unit_pt"))
        self.cmb_unit.blockSignals(False)

    def _select_mode(self, mode):
        self.current_mode = mode
        if hasattr(self, 'btn_select'):
            self.btn_select.setChecked(mode == "select")
        if hasattr(self, 'btn_pan'):
            self.btn_pan.setChecked(mode == "pan")
        self.btn_rect.setChecked(mode == "rect")
        self.btn_lasso.setChecked(mode == "lasso")
        self.btn_move.setChecked(mode == "move")
        self.btn_ruler.setChecked(mode == "ruler")
        self.box_ruler_opts.setVisible(mode == "ruler")
        self.adjustSize()

        for btn in (getattr(self, 'btn_select', None), getattr(self, 'btn_pan', None),
                    self.btn_rect, self.btn_lasso, self.btn_move, self.btn_ruler):
            if btn:
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        if self.on_mode_change:
            self.on_mode_change(mode)

        if mode != "ruler":
            self.close()

    def refresh_state(self):
        parent_mw = self.parent() or self.main_window
        if parent_mw:
            curr_tool = getattr(parent_mw, 'current_tool', 'select')
            if curr_tool == 'ruler':
                self.current_mode = 'ruler'
                if hasattr(self, 'btn_select'): self.btn_select.setChecked(False)
                if hasattr(self, 'btn_pan'): self.btn_pan.setChecked(False)
                self.btn_rect.setChecked(False)
                self.btn_lasso.setChecked(False)
                self.btn_move.setChecked(False)
                self.btn_ruler.setChecked(True)
                self.box_ruler_opts.setVisible(True)
            elif curr_tool == 'select':
                self.current_mode = 'select'
                if hasattr(self, 'btn_select'): self.btn_select.setChecked(True)
                if hasattr(self, 'btn_pan'): self.btn_pan.setChecked(False)
                self.btn_rect.setChecked(False)
                self.btn_lasso.setChecked(False)
                self.btn_move.setChecked(False)
                self.btn_ruler.setChecked(False)
                self.box_ruler_opts.setVisible(False)
            elif curr_tool == 'pan':
                self.current_mode = 'pan'
                if hasattr(self, 'btn_select'): self.btn_select.setChecked(False)
                if hasattr(self, 'btn_pan'): self.btn_pan.setChecked(True)
                self.btn_rect.setChecked(False)
                self.btn_lasso.setChecked(False)
                self.btn_move.setChecked(False)
                self.btn_ruler.setChecked(False)
                self.box_ruler_opts.setVisible(False)
            else:
                mode = getattr(parent_mw, 'selection_shape_mode', 'rect')
                self.current_mode = mode
                if hasattr(self, 'btn_select'): self.btn_select.setChecked(False)
                if hasattr(self, 'btn_pan'): self.btn_pan.setChecked(False)
                self.btn_rect.setChecked(mode == "rect")
                self.btn_lasso.setChecked(mode == "lasso")
                self.btn_move.setChecked(mode == "move")
                self.btn_ruler.setChecked(False)
                self.box_ruler_opts.setVisible(False)
            self.adjustSize()

            for btn in (getattr(self, 'btn_select', None), getattr(self, 'btn_pan', None),
                        self.btn_rect, self.btn_lasso, self.btn_move, self.btn_ruler):
                if btn:
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)


class CursorPopup(BaseSettingsPopup):
    def __init__(self, parent=None, on_mode_change=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.on_mode_change = on_mode_change
        self.current_mode = "select"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.lbl_title = QLabel(LanguageManager.tr("cursor_mode_title"))
        layout.addWidget(self.lbl_title)

        self.btn_arrow = QPushButton(LanguageManager.tr("cursor_arrow"))
        self.btn_arrow.setIcon(ModernIconFactory.icon_cursor())
        self.btn_arrow.setCheckable(True)
        self.btn_arrow.setChecked(True)

        self.btn_pan = QPushButton(LanguageManager.tr("cursor_pan"))
        self.btn_pan.setIcon(ModernIconFactory.icon_select_pan())
        self.btn_pan.setCheckable(True)

        self.btn_arrow.clicked.connect(lambda: self._select_mode("select"))
        self.btn_pan.clicked.connect(lambda: self._select_mode("pan"))

        layout.addWidget(self.btn_arrow)
        layout.addWidget(self.btn_pan)

    def retranslate_ui(self):
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setText(LanguageManager.tr("cursor_mode_title"))
        if hasattr(self, 'btn_arrow'):
            self.btn_arrow.setText(LanguageManager.tr("cursor_arrow"))
        if hasattr(self, 'btn_pan'):
            self.btn_pan.setText(LanguageManager.tr("cursor_pan"))

    def _select_mode(self, mode):
        self.current_mode = mode
        self.btn_arrow.setChecked(mode == "select")
        self.btn_pan.setChecked(mode == "pan")

        for btn in (self.btn_arrow, self.btn_pan):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if self.on_mode_change:
            self.on_mode_change(mode)
        self.close()

    def refresh_state(self):
        parent_mw = self.parent()
        if parent_mw and hasattr(parent_mw, 'cursor_mode'):
            mode = parent_mw.cursor_mode
            self.current_mode = mode
            self.btn_arrow.setChecked(mode == "select")
            self.btn_pan.setChecked(mode == "pan")
            for btn in (self.btn_arrow, self.btn_pan):
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def show_below(self, button_widget):
        self.refresh_state()
        super().show_below(button_widget)

    def show_at(self, global_pos: QPoint):
        self.refresh_state()
        super().show_at(global_pos)


# --- 4. METİN AYARLARI POPUP'I & RENK PALETİ ---
class SwatchButton(QPushButton):
    def __init__(self, color_hex="#ffffff", is_custom=False, parent=None, on_edit_callback=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.is_custom = is_custom
        self.is_active = False
        self.on_edit_callback = on_edit_callback
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_color(self, hex_val):
        self.color_hex = hex_val
        self.update()

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        col = QColor(self.color_hex)
        p.setBrush(QBrush(col))
        
        if self.is_custom:
            radius = 5.0
            if self.is_active:
                p.setPen(QPen(QColor(255, 255, 255), 2.5))
                p.drawRoundedRect(rect, radius, radius)
                p.setPen(QPen(QColor(56, 139, 253), 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius + 1.5, radius + 1.5)
            else:
                p.setPen(QPen(QColor(255, 255, 255, 140), 1.5))
                p.drawRoundedRect(rect, radius, radius)
            
            # Subtle indicator inside custom box to denote user-customizable color box
            mark_col = QColor(0, 0, 0, 180) if col.lightnessF() > 0.6 else QColor(255, 255, 255, 200)
            p.setPen(QPen(mark_col, 1.5))
            cx, cy = rect.center().x(), rect.center().y()
            p.drawLine(QPointF(cx - 3, cy), QPointF(cx + 3, cy))
            p.drawLine(QPointF(cx, cy - 3), QPointF(cx, cy + 3))
        else:
            if self.is_active:
                p.setPen(QPen(QColor(255, 255, 255), 2.5))
                p.drawEllipse(rect)
                p.setPen(QPen(QColor(56, 139, 253), 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 70), 1.2))
                p.drawEllipse(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.on_edit_callback:
                self.on_edit_callback(self)
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_edit_callback:
                self.on_edit_callback(self)
                return
        super().mouseDoubleClickEvent(event)


class ModernColorPaletteWidget(QWidget):
    def __init__(self, tool_name: str, default_palette: list, default_custom: str, default_active: str, on_color_changed=None, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.on_color_changed = on_color_changed
        self.settings = QSettings("AuraPDF", "PDFViewer")

        # Load palette
        saved_palette = self.settings.value(f"colors/{tool_name}_palette", None)
        if saved_palette and isinstance(saved_palette, str) and "," in saved_palette:
            self.palette = saved_palette.split(",")
        else:
            self.palette = list(default_palette)

        # Load custom color
        self.custom_color = str(self.settings.value(f"colors/{tool_name}_custom", default_custom))

        # Load active color
        self.active_color = str(self.settings.value(f"colors/{tool_name}_active", default_active))

        self.swatch_buttons = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Preset swatches
        for hex_code in self.palette:
            btn = SwatchButton(hex_code, is_custom=False, parent=self, on_edit_callback=self._on_edit_preset)
            btn.setToolTip(LanguageManager.tr("color_preset_tooltip", hex_val=hex_code))
            btn.clicked.connect(lambda _, b=btn: self._on_preset_clicked(b))
            layout.addWidget(btn)
            self.swatch_buttons.append(btn)

        # Custom color swatch box (shows the last chosen custom color)
        self.btn_custom = SwatchButton(self.custom_color, is_custom=True, parent=self, on_edit_callback=self._on_edit_custom)
        self.btn_custom.setToolTip(LanguageManager.tr("custom_color_tooltip", hex_val=self.custom_color))
        self.btn_custom.clicked.connect(self._on_custom_clicked)
        layout.addWidget(self.btn_custom)
        self.swatch_buttons.append(self.btn_custom)

        # Color picker button
        self.btn_picker = QPushButton("...")
        self.btn_picker.setFixedSize(24, 24)
        self.btn_picker.setToolTip(LanguageManager.tr("color_picker_tooltip"))
        self.btn_picker.setStyleSheet("""
            QPushButton {
                background-color: #383838;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 11px;
                color: #eee;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #484848;
                border-color: #777;
            }
        """)
        self.btn_picker.clicked.connect(self._open_picker_dialog)
        layout.addWidget(self.btn_picker)

        self._refresh_active_state()

    def retranslate_ui(self):
        for btn in self.swatch_buttons:
            if not btn.is_custom:
                btn.setToolTip(LanguageManager.tr("color_preset_tooltip", hex_val=btn.color_hex))
        if hasattr(self, 'btn_custom'):
            self.btn_custom.setToolTip(LanguageManager.tr("custom_color_tooltip", hex_val=self.custom_color))
        if hasattr(self, 'btn_picker'):
            self.btn_picker.setToolTip(LanguageManager.tr("color_picker_tooltip"))

    def _refresh_active_state(self):
        active_norm = self.active_color.lower()
        matched = False
        if self.custom_color.lower() == active_norm:
            self.btn_custom.set_active(True)
            matched = True
        else:
            self.btn_custom.set_active(False)

        for btn in self.swatch_buttons:
            if btn.is_custom:
                continue
            is_match = (btn.color_hex.lower() == active_norm) and not matched
            btn.set_active(is_match)
            if is_match:
                matched = True

    def _on_preset_clicked(self, btn):
        self.active_color = btn.color_hex
        self.settings.setValue(f"colors/{self.tool_name}_active", self.active_color)
        self._refresh_active_state()
        if self.on_color_changed:
            self.on_color_changed(QColor(self.active_color))

    def _on_custom_clicked(self):
        if self.btn_custom.is_active:
            self._open_picker_dialog()
        else:
            self.active_color = self.custom_color
            self.settings.setValue(f"colors/{self.tool_name}_active", self.active_color)
            self._refresh_active_state()
            if self.on_color_changed:
                self.on_color_changed(QColor(self.active_color))

    def _on_edit_custom(self, btn):
        self._open_picker_dialog()

    def _on_edit_preset(self, btn):
        initial = QColor(btn.color_hex)
        col = QColorDialog.getColor(initial, self, LanguageManager.tr("color_dialog_title"))
        if col.isValid():
            hex_val = col.name()
            idx = self.palette.index(btn.color_hex) if btn.color_hex in self.palette else -1
            if idx != -1:
                self.palette[idx] = hex_val
                self.settings.setValue(f"colors/{self.tool_name}_palette", ",".join(self.palette))
            btn.set_color(hex_val)
            btn.setToolTip(LanguageManager.tr("color_preset_tooltip", hex_val=hex_val))
            self._on_preset_clicked(btn)

    def _open_picker_dialog(self):
        initial = QColor(self.custom_color)
        col = QColorDialog.getColor(initial, self, LanguageManager.tr("color_dialog_title"))
        if col.isValid():
            self.set_custom_color(col.name())

    def set_custom_color(self, hex_val: str, notify: bool = True):
        self.custom_color = hex_val
        self.active_color = hex_val
        self.settings.setValue(f"colors/{self.tool_name}_custom", self.custom_color)
        self.settings.setValue(f"colors/{self.tool_name}_active", self.active_color)
        self.btn_custom.set_color(self.custom_color)
        self.btn_custom.setToolTip(LanguageManager.tr("custom_color_tooltip", hex_val=self.custom_color))
        self._refresh_active_state()
        if notify and self.on_color_changed:
            self.on_color_changed(QColor(self.active_color))

    def set_color_external(self, color_or_hex, notify: bool = True):
        hex_val = color_or_hex if isinstance(color_or_hex, str) else color_or_hex.name()
        if hex_val.lower() in [c.lower() for c in self.palette]:
            self.active_color = hex_val
            self.settings.setValue(f"colors/{self.tool_name}_active", self.active_color)
            self._refresh_active_state()
            if notify and self.on_color_changed:
                self.on_color_changed(QColor(self.active_color))
        else:
            self.set_custom_color(hex_val, notify=notify)


class TextPreviewWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 54)
        self.setStyleSheet("background-color: transparent; border: none; border-radius: 6px;")
        self.color = QColor(0, 0, 0)
        self.font_size = 14
        self.font_family = "Arial"
        self.bold = False
        self.italic = False
        self.underline = False

    def update_style(self, color, font_size, font_family, bold=False, italic=False, underline=False):
        self.color = color
        self.font_size = font_size
        self.font_family = font_family
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.update()

    def retranslate_ui(self):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = float(self.width())
        h = float(self.height())

        # Clean document canvas sheet (solid background with subtle border, no split line)
        p.setPen(QPen(QColor("#cbd5e1"), 1.0))
        p.setBrush(QBrush(QColor("#f8fafc")))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 6.0, 6.0)

        display_size = max(10, min(int(self.font_size), 20))
        font = QFont(self.font_family, display_size)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        p.setFont(font)

        sample = LanguageManager.tr("sample_text")
        text_rect = QRectF(12.0, 0.0, w - 24.0, h)

        # If text color is very light (e.g. white, light yellow), draw a soft contrast shadow/halo
        # so it is crystal clear on the light paper background without needing awkward split screens!
        if self.color.lightnessF() > 0.65:
            halo_color = QColor(30, 41, 59, 150)
            p.setPen(halo_color)
            for dx, dy in ((-1.0, 0.0), (1.0, 0.0), (0.0, -1.0), (0.0, 1.0), (-1.0, -1.0), (1.0, 1.0)):
                p.drawText(text_rect.translated(dx, dy), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, sample)

        p.setPen(self.color)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, sample)
        p.end()



class TextSettingsPopup(BaseSettingsPopup):
    def __init__(self, parent=None, tool_name="text"):
        super().__init__(parent)
        self.tool_name = tool_name
        # Note: self.setStyleSheet is handled dynamically by BaseSettingsPopup.apply_theme

        self.font_size = 14
        self.font_family = "Arial"
        self.bold = False
        self.italic = False
        self.underline = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # --- YAZI TİPİ BÖLÜMÜ ---
        lbl_sec_font = QLabel(LanguageManager.tr("text_sec_font"))
        lbl_sec_font.setObjectName("SectionHeader")
        layout.addWidget(lbl_sec_font)

        self.lbl_family = QLabel(LanguageManager.tr("font_family"))
        layout.addWidget(self.lbl_family)
        self.cmb_family = QComboBox()
        self.cmb_family.addItems(["Arial", "Times New Roman", "Courier New", "Segoe UI", "Calibri", "Georgia", "Verdana"])
        self.cmb_family.currentTextChanged.connect(self._on_family_change)
        layout.addWidget(self.cmb_family)

        self.lbl_size = QLabel(LanguageManager.tr("font_size"))
        layout.addWidget(self.lbl_size)
        size_box = QHBoxLayout()
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(8, 72)
        self.slider_size.setValue(self.font_size)
        self.lbl_size_val = QLabel(f"{self.font_size} pt")
        self.lbl_size_val.setFixedWidth(40)
        size_box.addWidget(self.slider_size)
        size_box.addWidget(self.lbl_size_val)
        layout.addLayout(size_box)
        self.slider_size.valueChanged.connect(self._on_size_change)

        # --- BİÇİM BÖLÜMÜ (Kalın / İtalik / Altı Çizili) ---
        lbl_sec_style = QLabel(LanguageManager.tr("text_sec_style"))
        lbl_sec_style.setObjectName("SectionHeader")
        layout.addWidget(lbl_sec_style)

        fmt_box = QHBoxLayout()
        fmt_box.setSpacing(6)

        self.btn_bold = QPushButton("B")
        self.btn_bold.setObjectName("FormatBtn")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(36, 28)
        font_b = self.btn_bold.font()
        font_b.setBold(True)
        font_b.setPointSize(11)
        self.btn_bold.setFont(font_b)
        self.btn_bold.clicked.connect(self._on_format_change)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setObjectName("FormatBtn")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(36, 28)
        font_i = self.btn_italic.font()
        font_i.setItalic(True)
        font_i.setPointSize(11)
        self.btn_italic.setFont(font_i)
        self.btn_italic.clicked.connect(self._on_format_change)

        self.btn_underline = QPushButton("U")
        self.btn_underline.setObjectName("FormatBtn")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(36, 28)
        font_u = self.btn_underline.font()
        font_u.setUnderline(True)
        font_u.setPointSize(11)
        self.btn_underline.setFont(font_u)
        self.btn_underline.clicked.connect(self._on_format_change)

        self.btn_link = QPushButton()
        self.btn_link.setObjectName("FormatBtn")
        self.btn_link.setIcon(ModernIconFactory.icon_link())
        self.btn_link.setFixedSize(36, 28)
        self.btn_link.setToolTip("Metne Web Bağlantısı (Hyperlink) Ekle")
        self.btn_link.clicked.connect(self._on_add_link_clicked)

        fmt_box.addWidget(self.btn_bold)
        fmt_box.addWidget(self.btn_italic)
        fmt_box.addWidget(self.btn_underline)
        fmt_box.addWidget(self.btn_link)
        fmt_box.addStretch()
        layout.addLayout(fmt_box)

        # --- RENK BÖLÜMÜ ---
        lbl_sec_color = QLabel(LanguageManager.tr("text_sec_color"))
        lbl_sec_color.setObjectName("SectionHeader")
        layout.addWidget(lbl_sec_color)

        self.lbl_color = QLabel(LanguageManager.tr("font_color"))
        layout.addWidget(self.lbl_color)
        default_pal = ["#000000", "#ffffff", "#e53935", "#1e88e5", "#43a047", "#fdd835"]
        self.palette_widget = ModernColorPaletteWidget(
            tool_name=self.tool_name,
            default_palette=default_pal,
            default_custom="#000000",
            default_active="#000000",
            on_color_changed=self._on_palette_color_changed,
            parent=self
        )
        if self.palette_widget.active_color.lower() in ("#ffffff", "#fff"):
            self.palette_widget.set_custom_color("#000000")
        layout.addWidget(self.palette_widget)
        self.color = QColor(self.palette_widget.active_color)

        # --- ÖNİZLEME ---
        self.lbl_preview = QLabel(LanguageManager.tr("preview"))
        layout.addWidget(self.lbl_preview)
        self.preview = TextPreviewWidget()
        layout.addWidget(self.preview)
        self.update_preview()

    def retranslate_ui(self):
        if hasattr(self, 'lbl_size'):
            self.lbl_size.setText(LanguageManager.tr("font_size"))
        if hasattr(self, 'lbl_family'):
            self.lbl_family.setText(LanguageManager.tr("font_family"))
        if hasattr(self, 'lbl_color'):
            self.lbl_color.setText(LanguageManager.tr("font_color"))
        if hasattr(self, 'lbl_preview'):
            self.lbl_preview.setText(LanguageManager.tr("preview"))
        if hasattr(self, 'palette_widget'):
            self.palette_widget.retranslate_ui()
        if hasattr(self, 'preview'):
            self.preview.retranslate_ui()

    def show_below(self, button_widget):
        it = self._get_target_text_item()
        if it and hasattr(self, 'sync_with_item_selection'):
            self.sync_with_item_selection(it)
        super().show_below(button_widget)

    def _get_target_text_item(self):
        main_win = self.parent()
        if not main_win:
            return None
        tab_doc = getattr(main_win, 'get_current_tab_doc', lambda: None)()
        if not tab_doc:
            return None
        return getattr(tab_doc, 'active_text_item', None) or getattr(tab_doc, 'last_text_item', None)

    def _on_format_change(self):
        self.bold = self.btn_bold.isChecked()
        self.italic = self.btn_italic.isChecked()
        self.underline = self.btn_underline.isChecked()
        for btn in (self.btn_bold, self.btn_italic, self.btn_underline):
            btn.setProperty("checked", btn.isChecked())
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.update_preview()
        it = self._get_target_text_item()
        if it and hasattr(it, 'apply_format_to_selection'):
            it.apply_format_to_selection(bold=self.bold, italic=self.italic, underline=self.underline)

    def _on_palette_color_changed(self, col):
        if getattr(self, '_is_syncing', False):
            return
        self.color = col
        self.update_preview()
        it = self._get_target_text_item()
        if it and hasattr(it, 'apply_format_to_selection'):
            it.apply_format_to_selection(color=col)

    def _on_size_change(self, val):
        self.font_size = val
        self.lbl_size_val.setText(f"{val} pt")
        self.update_preview()
        it = self._get_target_text_item()
        if it and hasattr(it, 'apply_format_to_selection'):
            it.apply_format_to_selection(font_size=val)

    def _on_family_change(self, fam):
        self.font_family = fam
        self.update_preview()
        it = self._get_target_text_item()
        if it and hasattr(it, 'apply_format_to_selection'):
            it.apply_format_to_selection(font_family=fam)

    def set_quick_color(self, hex_code):
        if hasattr(self, 'palette_widget'):
            self.palette_widget.set_color_external(hex_code)
        else:
            self.color = QColor(hex_code)
            self.update_preview()
        it = self._get_target_text_item()
        if it and hasattr(it, 'apply_format_to_selection'):
            it.apply_format_to_selection(color=self.color)

    def choose_custom_color(self):
        if hasattr(self, 'palette_widget'):
            self.palette_widget._open_picker_dialog()

    def update_preview(self):
        self.preview.update_style(self.color, self.font_size, self.font_family,
                                  self.bold, self.italic, self.underline)

    def sync_with_item_selection(self, item):
        if not item or not hasattr(item, 'get_selection_format'):
            return
        self._is_syncing = True
        try:
            fmt = item.get_selection_format()
            if not fmt:
                return
            if "bold" in fmt:
                self.bold = bool(fmt["bold"])
                self.btn_bold.setChecked(self.bold)
            if "italic" in fmt:
                self.italic = bool(fmt["italic"])
                self.btn_italic.setChecked(self.italic)
            if "underline" in fmt:
                self.underline = bool(fmt["underline"])
                self.btn_underline.setChecked(self.underline)
            for btn in (self.btn_bold, self.btn_italic, self.btn_underline):
                btn.setProperty("checked", btn.isChecked())
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            if "font_size" in fmt and fmt["font_size"] > 0:
                self.font_size = int(round(fmt["font_size"]))
                self.slider_size.blockSignals(True)
                self.slider_size.setValue(self.font_size)
                self.slider_size.blockSignals(False)
                self.lbl_size_val.setText(f"{self.font_size} pt")
            if "color" in fmt and isinstance(fmt["color"], QColor) and fmt["color"].isValid():
                self.color = fmt["color"]
                if hasattr(self, 'palette_widget'):
                    self.palette_widget.blockSignals(True)
                    self.palette_widget.set_color_external(self.color.name(), notify=False)
                    self.palette_widget.blockSignals(False)
            if "font_family" in fmt and fmt["font_family"]:
                idx = self.cmb_family.findText(fmt["font_family"])
                if idx >= 0:
                    self.cmb_family.blockSignals(True)
                    self.cmb_family.setCurrentIndex(idx)
                    self.cmb_family.blockSignals(False)
            self.update_preview()
        finally:
            self._is_syncing = False

    def _on_add_link_clicked(self):
        main_win = self.parent()
        tab_doc = None
        if hasattr(main_win, 'get_current_tab_doc'):
            tab_doc = main_win.get_current_tab_doc()
        active_item = (getattr(tab_doc, 'active_text_item', None) or 
                       getattr(tab_doc, 'last_text_item', None)) if tab_doc else None

        if active_item:
            cur = active_item.textCursor()
            char_range = None
            if not cur.hasSelection():
                cur.select(QTextCursor.SelectionType.WordUnderCursor)
                if cur.selectedText().strip():
                    active_item.setTextCursor(cur)

            if cur.hasSelection():
                raw_sel = cur.selectedText()
                lead_spaces = len(raw_sel) - len(raw_sel.lstrip())
                trail_spaces = len(raw_sel) - len(raw_sel.rstrip())
                s_start = cur.selectionStart() + lead_spaces
                s_end = cur.selectionEnd() - trail_spaces
                if s_start < s_end:
                    char_range = (s_start, s_end)
                    sel_text = raw_sel.strip()
                else:
                    sel_text = cur.selectedText().strip()
            else:
                sel_text = ""

            active_item.open_link_dialog(prefill_word=sel_text, char_range=char_range)
        else:
            QMessageBox.information(
                self,
                "Bağlantı (Hyperlink) Ekle",
                "Lütfen önce sayfada bağlantı eklemek istediğiniz metin kutusunu tıklayın veya seçin."
            )


# --- 6.5 KAYAN HIZLI BİÇİMLENDİRME ÇUBUĞU (FLOATING RICH TEXT HUD) ---
class TextFloatingFormatHUD(QFrame):
    """
    Kullanıcı metin ekleme aracında bir kelimenin veya cümlenin içindeki belirli harfleri seçtiğinde,
    seçimin hemen üzerinde beliren ve harf düzeyinde kalınlık (B), italik (I), altı çizili (U),
    yazı boyutu (−/+) ve renk (A) değişimini anında uygulayan şık mini biçimlendirme çubuğu.
    """
    def __init__(self, parent=None, tab_doc=None):
        super().__init__(parent)
        self.tab_doc = tab_doc
        self.target_text_item = None
        self.current_color = QColor("#000000")
        self.current_size = 14
        self.setObjectName("TextFloatingFormatHUD")

        settings = QSettings("AuraPDF", "PDFViewer")
        current_th = settings.value("app_theme", "dark")
        self.apply_theme(current_th)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # 1. BOLD
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedSize(28, 26)
        self.btn_bold.setStyleSheet("font-weight: 900; font-size: 13px;")
        self.btn_bold.setToolTip("Kalın (Ctrl+B)")
        self.btn_bold.clicked.connect(self._on_bold_clicked)
        layout.addWidget(self.btn_bold)

        # 2. ITALIC
        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedSize(28, 26)
        self.btn_italic.setStyleSheet("font-style: italic; font-size: 13px;")
        self.btn_italic.setToolTip("İtalik (Ctrl+I)")
        self.btn_italic.clicked.connect(self._on_italic_clicked)
        layout.addWidget(self.btn_italic)

        # 3. UNDERLINE
        self.btn_underline = QPushButton("U")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedSize(28, 26)
        self.btn_underline.setStyleSheet("text-decoration: underline; font-size: 13px;")
        self.btn_underline.setToolTip("Altı Çizili (Ctrl+U)")
        self.btn_underline.clicked.connect(self._on_underline_clicked)
        layout.addWidget(self.btn_underline)

        sep1 = QFrame()
        sep1.setObjectName("Separator")
        layout.addWidget(sep1)

        # 4. FONT SIZE DECREASE
        self.btn_dec_size = QPushButton("−")
        self.btn_dec_size.setFixedSize(24, 26)
        self.btn_dec_size.setToolTip("Yazı Boyutunu Küçült (Ctrl+[)")
        self.btn_dec_size.clicked.connect(self._on_dec_size_clicked)
        layout.addWidget(self.btn_dec_size)

        # 5. FONT SIZE DISPLAY
        self.lbl_size = QLabel("14 pt")
        self.lbl_size.setFixedWidth(36)
        self.lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_size)

        # 6. FONT SIZE INCREASE
        self.btn_inc_size = QPushButton("+")
        self.btn_inc_size.setFixedSize(24, 26)
        self.btn_inc_size.setToolTip("Yazı Boyutunu Büyüt (Ctrl+])")
        self.btn_inc_size.clicked.connect(self._on_inc_size_clicked)
        layout.addWidget(self.btn_inc_size)

        sep2 = QFrame()
        sep2.setObjectName("Separator")
        layout.addWidget(sep2)

        # 7. COLOR BUTTON WITH QUICK PALETTE MENU
        self.btn_color = QPushButton("A")
        self.btn_color.setFixedSize(30, 26)
        self.btn_color.setToolTip("Metin Rengi")
        self.btn_color.clicked.connect(self._on_color_button_clicked)
        layout.addWidget(self.btn_color)

        # 8. HYPERLINK BUTTON
        self.btn_link = QPushButton()
        self.btn_link.setIcon(ModernIconFactory.icon_link())
        self.btn_link.setFixedSize(28, 26)
        self.btn_link.setToolTip("Bağlantı (Hyperlink) Ekle / Düzenle")
        self.btn_link.clicked.connect(self._on_link_clicked)
        layout.addWidget(self.btn_link)

        # Odak kaybını önle: Butonlara tıklandığında metin seçimi kaybolmasın
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in (self.btn_bold, self.btn_italic, self.btn_underline,
                    self.btn_dec_size, self.btn_inc_size, self.btn_color, self.btn_link):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.hide()

    def apply_theme(self, theme_name: str = "dark", spec: Optional[dict] = None):
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("dark", {}))
        main_bg = spec.get("main_bg", "#18181b")
        tb_bg = spec.get("tb_bg", "#27272a")
        tb_border = spec.get("tb_border", "#3f3f46")
        main_text = spec.get("main_text", "#f4f4f5")
        btn_hover = spec.get("btn_hover", "#3f3f46")
        accent = spec.get("accent", "#0284c7")

        self.setStyleSheet(f"""
            QFrame#TextFloatingFormatHUD {{
                background-color: {tb_bg};
                border: 1px solid {tb_border};
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {main_bg};
                color: {main_text};
                border: 1px solid {tb_border};
                border-radius: 4px;
                font-size: 12px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: #ffffff;
            }}
            QPushButton[checked="true"], QPushButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent};
                font-weight: bold;
            }}
            QLabel {{
                color: {main_text};
                font-size: 11px;
                font-weight: bold;
                border: none;
                background: transparent;
            }}
            QFrame#Separator {{
                background-color: {tb_border};
                width: 1px;
                max-width: 1px;
                margin: 3px 2px;
            }}
        """)

    def _update_color_button_style(self, color):
        col_hex = color.name() if isinstance(color, QColor) else str(color)
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                color: {col_hex};
                font-weight: bold;
                font-size: 13px;
                border-bottom: 3px solid {col_hex};
                border-radius: 4px;
                background-color: #27272a;
            }}
            QPushButton:hover {{
                background-color: #3f3f46;
            }}
        """)

    def attach_to_text_item(self, item):
        self.target_text_item = item

    def update_ui_from_selection(self):
        if not self.target_text_item:
            return
        fmt = self.target_text_item.get_selection_format()
        if not fmt:
            return

        is_bold = bool(fmt.get("bold", False))
        is_italic = bool(fmt.get("italic", False))
        is_underline = bool(fmt.get("underline", False))

        self.btn_bold.setChecked(is_bold)
        self.btn_italic.setChecked(is_italic)
        self.btn_underline.setChecked(is_underline)

        for btn in (self.btn_bold, self.btn_italic, self.btn_underline):
            btn.setProperty("checked", btn.isChecked())
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        fs = int(round(fmt.get("font_size", 14)))
        self.current_size = fs
        self.lbl_size.setText(f"{fs} pt")

        col = fmt.get("color", QColor("#000000"))
        if isinstance(col, QColor) and col.isValid():
            self.current_color = col
            self._update_color_button_style(col)

    def reposition_above_selection(self):
        if not self.target_text_item or not self.tab_doc or not hasattr(self.tab_doc, 'view') or not self.tab_doc.view:
            return
        view = self.tab_doc.view
        viewport = view.viewport()

        cur = self.target_text_item.textCursor()
        if not cur.hasSelection() and getattr(self.target_text_item, '_last_selection_range', None):
            st, en = self.target_text_item._last_selection_range
            cur.setPosition(st)
            cur.setPosition(en, QTextCursor.MoveMode.KeepAnchor)
        try:
            doc = self.target_text_item.document()
            layout = doc.documentLayout()
            blk = cur.block()
            blk_rect = layout.blockBoundingRect(blk)
            font = cur.charFormat().font()
            if font.pointSize() <= 0:
                font = self.target_text_item.font()
            fm = QFontMetricsF(font)
            txt = blk.text()
            st_in_block = max(0, cur.selectionStart() - blk.position())
            en_in_block = max(st_in_block, min(len(txt), cur.selectionEnd() - blk.position()))
            x0 = fm.horizontalAdvance(txt[:st_in_block])
            w_sel = max(10.0, fm.horizontalAdvance(txt[st_in_block:en_in_block]))
            sel_rect = QRectF(blk_rect.x() + x0, blk_rect.y(), w_sel, blk_rect.height())
        except Exception:
            sel_rect = self.target_text_item.boundingRect()

        scene_rect = self.target_text_item.mapToScene(sel_rect).boundingRect()
        view_rect = view.mapFromScene(scene_rect).boundingRect()

        self.adjustSize()
        w = self.width()
        h = self.height()

        target_x = int(view_rect.center().x() - (w // 2))
        target_y = int(view_rect.top() - h - 10)

        # If too close to top of viewport, place below selection
        if target_y < 10:
            target_y = int(view_rect.bottom() + 10)

        # Clamp horizontal
        target_x = max(10, min(target_x, viewport.width() - w - 10))

        self.move(target_x, target_y)

    def _on_bold_clicked(self):
        if self.target_text_item:
            self.target_text_item.apply_format_to_selection(bold=self.btn_bold.isChecked())

    def _on_italic_clicked(self):
        if self.target_text_item:
            self.target_text_item.apply_format_to_selection(italic=self.btn_italic.isChecked())

    def _on_underline_clicked(self):
        if self.target_text_item:
            self.target_text_item.apply_format_to_selection(underline=self.btn_underline.isChecked())

    def _on_dec_size_clicked(self):
        new_size = max(8, self.current_size - 2)
        if self.target_text_item:
            self.target_text_item.apply_format_to_selection(font_size=new_size)

    def _on_inc_size_clicked(self):
        new_size = min(120, self.current_size + 2)
        if self.target_text_item:
            self.target_text_item.apply_format_to_selection(font_size=new_size)

    def _on_color_button_clicked(self):
        from PyQt6.QtWidgets import QMenu, QWidgetAction
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        menu.setStyleSheet("""
            QMenu {
                background-color: #242426;
                color: #f1f5f9;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        pal_widget = QWidget()
        pal_layout = QGridLayout(pal_widget)
        pal_layout.setContentsMargins(4, 4, 4, 4)
        pal_layout.setSpacing(5)

        swatches = ["#000000", "#ffffff", "#e53935", "#1e88e5", "#43a047", "#fdd835", "#fb8c00", "#8e24aa"]
        for idx, hex_col in enumerate(swatches):
            btn = QPushButton()
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_col};
                    border: 1px solid {'#888888' if hex_col.lower() in ('#000000', '#ffffff') else '#444444'};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #38bdf8;
                }}
            """)
            btn.clicked.connect(lambda _, c=hex_col: (self._apply_color(QColor(c)), menu.close()))
            pal_layout.addWidget(btn, idx // 4, idx % 4)

        # Custom color button
        btn_custom = QPushButton("Özel Renk...")
        btn_custom.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_custom.setStyleSheet("""
            QPushButton {
                background-color: #2f2f35;
                color: #f1f5f9;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                font-size: 11px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                background-color: #3f3f46;
            }
        """)
        btn_custom.clicked.connect(lambda: (menu.close(), self._open_custom_color_dialog()))
        pal_layout.addWidget(btn_custom, 2, 0, 1, 4)

        act = QWidgetAction(menu)
        act.setDefaultWidget(pal_widget)
        menu.addAction(act)
        menu.exec(self.btn_color.mapToGlobal(QPoint(0, self.btn_color.height() + 4)))

    def _apply_color(self, col):
        if self.target_text_item and col.isValid():
            self.target_text_item.apply_format_to_selection(color=col)
            self._update_color_button_style(col)

    def _open_custom_color_dialog(self):
        col = QColorDialog.getColor(self.current_color, self, "Metin Rengi Seç")
        if col.isValid():
            self._apply_color(col)

    def _on_link_clicked(self):
        if self.target_text_item:
            self.target_text_item.open_link_dialog()


# --- 7. ÇİZİM AYAR PENCERELERİ ---
class StrokePreviewWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 48)
        self.setStyleSheet("background-color: transparent; border: none; border-radius: 6px;")
        self.color = QColor(255, 235, 59, 120)
        self.thickness = 20
        self.is_eraser = False
        self.eraser_mode = "stroke"
        self.line_style = "solid"

    def update_style(self, color, thickness, is_eraser=False, eraser_mode="stroke", line_style="solid", is_hl=False):
        self.color = color
        self.thickness = thickness
        self.is_eraser = is_eraser
        self.eraser_mode = eraser_mode
        self.line_style = line_style
        self.is_hl = is_hl
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())

        # Clean document canvas sheet (no split line cutting the stroke)
        p.setPen(QPen(QColor("#cbd5e1"), 1.0))
        p.setBrush(QBrush(QColor("#f8fafc")))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 6.0, 6.0)

        mid_y = h / 2.0
        start_x, end_x = 18.0, w - 18.0

        if self.is_eraser:
            if self.eraser_mode == "stroke":
                pen = QPen(QColor("#94a3b8"), min(self.thickness, 24), Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))
            else:
                r = min(self.thickness / 2.0, 14.0)
                p.setPen(QPen(QColor("#64748b"), 1.5, Qt.PenStyle.DashLine))
                p.setBrush(QBrush(QColor(148, 163, 184, 80)))
                p.drawEllipse(QPointF(w / 2.0, mid_y), r, r)
        else:
            style = Qt.PenStyle.SolidLine
            cap = Qt.PenCapStyle.SquareCap if getattr(self, 'is_hl', False) else Qt.PenCapStyle.RoundCap
            join = Qt.PenJoinStyle.BevelJoin if getattr(self, 'is_hl', False) else Qt.PenJoinStyle.RoundJoin
            is_arrow = (self.line_style == "arrow")

            if self.line_style == "dash":
                style = Qt.PenStyle.DashLine
            elif self.line_style == "dot":
                style = Qt.PenStyle.DotLine
            elif self.line_style == "dashdot":
                style = Qt.PenStyle.DashDotLine
            elif self.line_style == "calligraphy":
                cap = Qt.PenCapStyle.FlatCap
                join = Qt.PenJoinStyle.MiterJoin

            # Soft contrast under-stroke if color is bright (e.g. yellow highlighter, white)
            if self.color.lightnessF() > 0.65:
                under_col = QColor(40, 50, 70, 40)
                under_pen = QPen(under_col, min(self.thickness + 2.0, 32.0), style, cap, join)
                p.setPen(under_pen)
                if is_arrow:
                    arrow_len = max(8.0, min(18.0, self.thickness * 2.2 + 6.0))
                    line_end_x = max(start_x + 10.0, end_x - arrow_len * 0.7)
                    p.drawLine(QPointF(start_x, mid_y), QPointF(line_end_x, mid_y))
                elif self.line_style == "calligraphy":
                    path = QPainterPath()
                    path.moveTo(start_x, mid_y + 4.0)
                    path.cubicTo(start_x + 45.0, mid_y - 8.0, end_x - 45.0, mid_y + 8.0, end_x, mid_y - 4.0)
                    p.strokePath(path, under_pen)
                else:
                    p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))

            pen = QPen(self.color, min(self.thickness, 30), style, cap, join)
            p.setPen(pen)

            if is_arrow:
                arrow_len = max(8.0, min(18.0, self.thickness * 2.2 + 6.0))
                line_end_x = max(start_x + 10.0, end_x - arrow_len * 0.7)
                p.drawLine(QPointF(start_x, mid_y), QPointF(line_end_x, mid_y))

                # Arrowhead wings
                p.setPen(QPen(self.color, max(2.0, min(self.thickness * 0.85, 7.0)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawLine(QPointF(end_x, mid_y), QPointF(end_x - arrow_len, mid_y - arrow_len * 0.55))
                p.drawLine(QPointF(end_x, mid_y), QPointF(end_x - arrow_len, mid_y + arrow_len * 0.55))
            elif self.line_style == "calligraphy":
                path = QPainterPath()
                path.moveTo(start_x, mid_y + 4.0)
                path.cubicTo(start_x + 45.0, mid_y - 8.0, end_x - 45.0, mid_y + 8.0, end_x, mid_y - 4.0)
                p.strokePath(path, pen)
            else:
                p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))

        p.end()


class ToolSettingsPopup(BaseSettingsPopup):
    def __init__(self, parent=None, has_color=True, has_opacity=True, is_eraser=False, is_hl=False, on_change_callback=None, tool_name=None):
        super().__init__(parent)
        self.on_change_callback = on_change_callback
        self.has_color = has_color
        self.has_opacity = has_opacity
        self.is_eraser = is_eraser
        self.is_hl = is_hl
        self.tool_name = tool_name or ("highlighter" if is_hl else ("eraser" if is_eraser else "pen"))
        self.eraser_mode = "stroke"
        self.line_style = "solid"
        self.snap_straight = False
        # Note: self.setStyleSheet is handled dynamically by BaseSettingsPopup.apply_theme

        if self.is_hl:
            self.thickness = 18
            self.opacity = 40
        elif self.tool_name == "pen":
            self.thickness = 3
            self.opacity = 100
        elif self.is_eraser:
            self.thickness = 24
            self.opacity = 100
        else:
            self.thickness = 18
            self.opacity = 40

        self.color = QColor(255, 235, 59, int(self.opacity * 2.55))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        if self.is_eraser:
            self.lbl_mode = QLabel(LanguageManager.tr("eraser_mode"))
            layout.addWidget(self.lbl_mode)
            mode_box = QHBoxLayout()
            self.btn_mode_stroke = QPushButton(LanguageManager.tr("eraser_stroke"))
            self.btn_mode_stroke.setProperty("class", "segment-btn")
            self.btn_mode_stroke.setCheckable(True)
            self.btn_mode_stroke.setChecked(True)

            self.btn_mode_area = QPushButton(LanguageManager.tr("eraser_area"))
            self.btn_mode_area.setProperty("class", "segment-btn")
            self.btn_mode_area.setCheckable(True)

            self.btn_mode_stroke.clicked.connect(lambda: self._set_eraser_mode("stroke"))
            self.btn_mode_area.clicked.connect(lambda: self._set_eraser_mode("area"))

            mode_box.addWidget(self.btn_mode_stroke)
            mode_box.addWidget(self.btn_mode_area)
            layout.addLayout(mode_box)

        if self.tool_name == "pen":
            lbl_key = "pen_style_label"
            self.lbl_style = QLabel(LanguageManager.tr(lbl_key))
            layout.addWidget(self.lbl_style)

            grid_styles = QGridLayout()
            grid_styles.setSpacing(5)

            self.style_buttons = {}
            styles_data = [
                ("solid", LanguageManager.tr("pen_style_solid")),
                ("dash", LanguageManager.tr("pen_style_dash")),
                ("dot", LanguageManager.tr("pen_style_dot")),
                ("dashdot", LanguageManager.tr("pen_style_dashdot")),
                ("arrow", LanguageManager.tr("pen_style_arrow")),
                ("calligraphy", LanguageManager.tr("pen_style_calligraphy")),
            ]

            for idx, (st_key, st_text) in enumerate(styles_data):
                btn_st = QPushButton(st_text)
                btn_st.setProperty("class", "segment-btn")
                btn_st.setCheckable(True)
                if st_key == self.line_style:
                    btn_st.setChecked(True)
                btn_st.clicked.connect(lambda _, k=st_key: self._set_line_style(k))
                row = idx // 3
                col = idx % 3
                grid_styles.addWidget(btn_st, row, col)
                self.style_buttons[st_key] = btn_st

            layout.addLayout(grid_styles)

        if self.tool_name in ("pen", "highlighter"):

            snap_key = "ruler_lock" if self.is_hl else "pen_ruler_lock"
            self.chk_snap = QCheckBox(LanguageManager.tr(snap_key))
            self.chk_snap.setChecked(self.snap_straight)
            self.chk_snap.toggled.connect(self._on_snap_toggled)
            layout.addWidget(self.chk_snap)

        self.lbl_thick = QLabel(LanguageManager.tr("thickness"))
        layout.addWidget(self.lbl_thick)
        thick_box = QHBoxLayout()
        self.slider_thick = QSlider(Qt.Orientation.Horizontal)
        self.slider_thick.setRange(1, 70)
        self.slider_thick.setValue(self.thickness)
        self.lbl_thick_val = QLabel(f"{self.thickness} px")
        self.lbl_thick_val.setFixedWidth(40)
        thick_box.addWidget(self.slider_thick)
        thick_box.addWidget(self.lbl_thick_val)
        layout.addLayout(thick_box)
        self.slider_thick.valueChanged.connect(self._on_thick_change)

        if self.has_opacity:
            self.lbl_opac = QLabel(LanguageManager.tr("opacity_label"))
            layout.addWidget(self.lbl_opac)
            opac_box = QHBoxLayout()
            self.slider_opac = QSlider(Qt.Orientation.Horizontal)
            self.slider_opac.setRange(10, 100)
            self.slider_opac.setValue(self.opacity)
            self.lbl_opac_val = QLabel(LanguageManager.tr("percent_format", val=self.opacity))
            self.lbl_opac_val.setFixedWidth(40)
            opac_box.addWidget(self.slider_opac)
            opac_box.addWidget(self.lbl_opac_val)
            layout.addLayout(opac_box)
            self.slider_opac.valueChanged.connect(self._on_opac_change)

        if self.has_color:
            self.lbl_color = QLabel(LanguageManager.tr("color_label"))
            layout.addWidget(self.lbl_color)
            if self.is_hl:
                default_pal = ["#ffeb3b", "#00e676", "#29b6f6", "#ff5252", "#ab47bc", "#ff9800"]
                def_custom = "#ffeb3b"
                def_active = "#ffeb3b"
            else:
                default_pal = ["#000000", "#388bfd", "#e53935", "#2ea043", "#f1e05a", "#a371f7"]
                def_custom = "#388bfd"
                def_active = "#388bfd"

            self.palette_widget = ModernColorPaletteWidget(
                tool_name=self.tool_name,
                default_palette=default_pal,
                default_custom=def_custom,
                default_active=def_active,
                on_color_changed=self._on_palette_color_changed,
                parent=self
            )
            layout.addWidget(self.palette_widget)

            # Initialize color from palette widget
            initial_hex = self.palette_widget.active_color
            alpha = int(self.opacity * 2.55) if self.has_opacity else 255
            self.color = QColor(initial_hex)
            self.color.setAlpha(alpha)

        self.lbl_preview = QLabel(LanguageManager.tr("preview"))
        layout.addWidget(self.lbl_preview)
        self.preview = StrokePreviewWidget()
        layout.addWidget(self.preview)
        self.update_preview()

        if self.is_eraser:
            self.btn_clear_all = QPushButton(LanguageManager.tr("clear_all_drawings"))
            self.btn_clear_all.setObjectName("ClearBtn")
            self.btn_clear_all.clicked.connect(self._on_clear_all_drawings)
            layout.addWidget(self.btn_clear_all)

    def _on_clear_all_drawings(self):
        self.close()
        p = self.parent()
        if hasattr(p, 'clear_all_drawings'):
            p.clear_all_drawings()

    def retranslate_ui(self):
        if hasattr(self, 'lbl_mode'):
            self.lbl_mode.setText(LanguageManager.tr("eraser_mode"))
        if hasattr(self, 'btn_mode_stroke'):
            self.btn_mode_stroke.setText(LanguageManager.tr("eraser_stroke"))
        if hasattr(self, 'btn_mode_area'):
            self.btn_mode_area.setText(LanguageManager.tr("eraser_area"))
        if hasattr(self, 'lbl_style'):
            if self.tool_name == "pen":
                self.lbl_style.setText(LanguageManager.tr("pen_style_label"))
        if hasattr(self, 'style_buttons'):
            btn_texts = {
                "solid": LanguageManager.tr("pen_style_solid"),
                "dash": LanguageManager.tr("pen_style_dash"),
                "dot": LanguageManager.tr("pen_style_dot"),
                "dashdot": LanguageManager.tr("pen_style_dashdot"),
                "arrow": LanguageManager.tr("pen_style_arrow"),
                "calligraphy": LanguageManager.tr("pen_style_calligraphy"),
            }
            for k, btn in self.style_buttons.items():
                if k in btn_texts:
                    btn.setText(btn_texts[k])
        if hasattr(self, 'lbl_thick'):
            self.lbl_thick.setText(LanguageManager.tr("thickness"))
        if hasattr(self, 'lbl_opac'):
            self.lbl_opac.setText(LanguageManager.tr("opacity_label"))
        if hasattr(self, 'lbl_opac_val'):
            self.lbl_opac_val.setText(LanguageManager.tr("percent_format", val=self.opacity))
        if hasattr(self, 'lbl_color'):
            self.lbl_color.setText(LanguageManager.tr("color_label"))
        if hasattr(self, 'lbl_preview'):
            self.lbl_preview.setText(LanguageManager.tr("preview"))
        if hasattr(self, 'btn_clear_all'):
            self.btn_clear_all.setText(LanguageManager.tr("clear_all_drawings"))
        if hasattr(self, 'chk_snap'):
            snap_txt = LanguageManager.tr("pen_ruler_lock") if self.tool_name == "pen" else LanguageManager.tr("ruler_lock")
            self.chk_snap.setText(snap_txt)
        if hasattr(self, 'palette_widget'):
            self.palette_widget.retranslate_ui()

    def _set_eraser_mode(self, mode):
        self.eraser_mode = mode
        self.btn_mode_stroke.setChecked(mode == "stroke")
        self.btn_mode_area.setChecked(mode == "area")
        for btn in (self.btn_mode_stroke, self.btn_mode_area):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def _set_line_style(self, style_key):
        self.line_style = style_key
        for k, btn in getattr(self, 'style_buttons', {}).items():
            btn.setChecked(k == style_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_snap_toggled(self, checked):
        self.snap_straight = checked
        p = self.parent()
        if hasattr(p, 'sync_ruler_state'):
            p.sync_ruler_state()

    def _on_palette_color_changed(self, col):
        alpha = int(self.opacity * 2.55) if self.has_opacity else 255
        self.color = QColor(col.red(), col.green(), col.blue(), alpha)
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def set_thickness(self, new_val):
        self.thickness = max(1, min(int(new_val), 70))
        self.slider_thick.blockSignals(True)
        self.slider_thick.setValue(self.thickness)
        self.slider_thick.blockSignals(False)
        self.lbl_thick_val.setText(f"{self.thickness} px")
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_thick_change(self, val):
        self.thickness = val
        self.lbl_thick_val.setText(f"{val} px")
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_opac_change(self, val):
        self.opacity = val
        self.lbl_opac_val.setText(LanguageManager.tr("percent_format", val=val))
        self.color.setAlpha(int(val * 2.55))
        self.update_preview()

    def set_quick_color(self, hex_code):
        if hasattr(self, 'palette_widget'):
            self.palette_widget.set_color_external(hex_code)
        else:
            alpha = int(self.opacity * 2.55) if self.has_opacity else 255
            self.color = QColor(hex_code)
            self.color.setAlpha(alpha)
            self.update_preview()

    def choose_custom_color(self):
        if hasattr(self, 'palette_widget'):
            self.palette_widget._open_picker_dialog()

    def update_preview(self):
        self.preview.update_style(
            self.color, self.thickness, self.is_eraser, self.eraser_mode, 
            getattr(self, 'line_style', 'solid'), is_hl=self.is_hl
        )

    def show_at(self, global_pos: QPoint):
        if hasattr(self, 'chk_snap'):
            self.chk_snap.blockSignals(True)
            self.chk_snap.setChecked(self.snap_straight)
            self.chk_snap.blockSignals(False)
        self.update_preview()
        super().show_at(global_pos)


class FloatingHUDPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(140, 70)
        self.color = QColor(255, 235, 59, 120)
        self.thickness = 18
        self.is_eraser = False
        self.bg_color = QColor(25, 25, 25, 220)
        self.border_color = QColor(255, 255, 255, 60)
        self.text_color = QColor(240, 240, 240)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        settings = QSettings("AuraPDF", "PDFViewer")
        current_th = settings.value("app_theme", "dark")
        self.apply_theme(current_th)

    def apply_theme(self, theme_name: str, spec: dict = None):
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("dark", {}))
        if spec:
            tb_bg = QColor(spec.get('tb_bg', '#1c1c1c'))
            self.bg_color = QColor(tb_bg.red(), tb_bg.green(), tb_bg.blue(), 230)
            self.border_color = QColor(spec.get('tb_border', '#404040'))
            self.text_color = QColor(spec.get('main_text', '#e0e0e0'))
            self.update()

    def show_preview(self, pos, color, thickness, is_eraser=False, eraser_mode="stroke", line_style="solid"):
        self.color = color
        self.thickness = thickness
        self.is_eraser = is_eraser
        self.line_style = line_style
        self.move(pos.x() + 20, pos.y() - 35)
        self.show()
        self.update()
        self.hide_timer.start(1000)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(getattr(self, 'bg_color', QColor(25, 25, 25, 220))))
        p.setPen(QPen(getattr(self, 'border_color', QColor(255, 255, 255, 60)), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        p.setPen(getattr(self, 'text_color', QColor(240, 240, 240)))
        text = LanguageManager.tr("hud_eraser", px=self.thickness) if self.is_eraser else f"{self.thickness} px"
        p.drawText(QRectF(0, 8, self.width(), 16), Qt.AlignmentFlag.AlignCenter, text)
        
        mid_y = 44
        if self.is_eraser:
            r = min(self.thickness / 2, 20)
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5, Qt.PenStyle.DashLine))
            p.setBrush(QBrush(QColor(200, 200, 200, 80)))
            p.drawEllipse(QPointF(self.width() / 2, mid_y), r, r)
        else:
            style = Qt.PenStyle.SolidLine
            cap = Qt.PenCapStyle.RoundCap
            join = Qt.PenJoinStyle.RoundJoin
            line_st = getattr(self, 'line_style', 'solid')
            if line_st == "dash":
                style = Qt.PenStyle.DashLine
            elif line_st == "dot":
                style = Qt.PenStyle.DotLine
            elif line_st == "dashdot":
                style = Qt.PenStyle.DashDotLine
            elif line_st == "calligraphy":
                cap = Qt.PenCapStyle.FlatCap
                join = Qt.PenJoinStyle.MiterJoin

            p.setPen(QPen(self.color, min(self.thickness, 26), style, cap, join))
            p.drawLine(QPointF(20, mid_y), QPointF(self.width() - 20, mid_y))


# --- 7. LAZER İŞARETÇİ AYARLARI PANELİ (POINTER SETTINGS POPUP) ---
class PointerSettingsPopup(BaseSettingsPopup):
    def __init__(self, parent=None, on_change_callback=None, tool_name="pointer"):
        super().__init__(parent)
        self.on_change_callback = on_change_callback
        self.tool_name = tool_name

        self.mode = "single"  # "single" or "rainbow"
        self.fade_seconds = 0.5  # Default fade duration: 0.5s
        self.thickness = 3  # Default thickness: 3px

        # Note: self.setStyleSheet is handled dynamically by BaseSettingsPopup.apply_theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Mod Seçimi (Tek Renk vs Rainbow)
        self.lbl_mode = QLabel(LanguageManager.tr("pointer_mode"))
        layout.addWidget(self.lbl_mode)

        h_mode = QHBoxLayout()
        h_mode.setSpacing(6)
        self.btn_mode_single = QPushButton(LanguageManager.tr("pointer_mode_single"))
        self.btn_mode_single.setProperty("class", "segment-btn")
        self.btn_mode_single.setCheckable(True)
        self.btn_mode_single.setChecked(True)
        self.btn_mode_single.clicked.connect(lambda: self._set_mode("single"))

        self.btn_mode_rainbow = QPushButton(LanguageManager.tr("pointer_mode_rainbow"))
        self.btn_mode_rainbow.setProperty("class", "segment-btn")
        self.btn_mode_rainbow.setCheckable(True)
        self.btn_mode_rainbow.clicked.connect(lambda: self._set_mode("rainbow"))

        h_mode.addWidget(self.btn_mode_single)
        h_mode.addWidget(self.btn_mode_rainbow)
        layout.addLayout(h_mode)

        # 2. Hızlı Renkler & Özel Renk (Tek Renk modu için)
        self.color_container = QWidget()
        self.color_container.setStyleSheet("background: transparent; border: none;")
        v_col = QVBoxLayout(self.color_container)
        v_col.setContentsMargins(0, 0, 0, 0)
        v_col.setSpacing(6)

        default_pal = ["#ff1744", "#ff9100", "#ffea00", "#00e676", "#2979ff", "#d500f9"]
        self.palette_widget = ModernColorPaletteWidget(
            tool_name=self.tool_name,
            default_palette=default_pal,
            default_custom="#ff1744",
            default_active="#ff1744",
            on_color_changed=self._on_palette_color_changed,
            parent=self.color_container
        )
        v_col.addWidget(self.palette_widget)
        layout.addWidget(self.color_container)

        self.color = QColor(self.palette_widget.active_color)

        # 3. Kaybolma Süresi Slider'ı
        h_fade = QHBoxLayout()
        self.lbl_fade_title = QLabel(LanguageManager.tr("pointer_fade_time"))
        self.lbl_fade_val = QLabel(LanguageManager.tr("pointer_fade_time_val", sec=f"{self.fade_seconds:.1f}"))
        self.lbl_fade_val.setStyleSheet("color: #ffffff; font-weight: bold; border: none;")
        h_fade.addWidget(self.lbl_fade_title)
        h_fade.addStretch()
        h_fade.addWidget(self.lbl_fade_val)
        layout.addLayout(h_fade)

        self.slider_fade = QSlider(Qt.Orientation.Horizontal)
        self.slider_fade.setRange(5, 50)  # 0.5 to 5.0 seconds
        self.slider_fade.setValue(int(self.fade_seconds * 10))
        self.slider_fade.valueChanged.connect(self._on_fade_change)
        layout.addWidget(self.slider_fade)

        # 4. Çizgi Kalınlığı Slider'ı
        h_thick = QHBoxLayout()
        self.lbl_thick_title = QLabel(LanguageManager.tr("pointer_thickness"))
        self.lbl_thick_val = QLabel(f"{self.thickness} px")
        self.lbl_thick_val.setStyleSheet("color: #ffffff; font-weight: bold; border: none;")
        h_thick.addWidget(self.lbl_thick_title)
        h_thick.addStretch()
        h_thick.addWidget(self.lbl_thick_val)
        layout.addLayout(h_thick)

        self.slider_thick = QSlider(Qt.Orientation.Horizontal)
        self.slider_thick.setRange(1, 30)
        self.slider_thick.setValue(self.thickness)
        self.slider_thick.valueChanged.connect(self._on_thick_change)
        layout.addWidget(self.slider_thick)

    def _on_palette_color_changed(self, col):
        self.color = col
        if self.on_change_callback:
            self.on_change_callback()

    def _set_mode(self, mode):
        self.mode = mode
        self.btn_mode_single.setChecked(mode == "single")
        self.btn_mode_rainbow.setChecked(mode == "rainbow")
        self.color_container.setVisible(mode == "single")
        self.adjustSize()
        if self.on_change_callback:
            self.on_change_callback()

    def _set_quick_color(self, hex_code):
        if hasattr(self, 'palette_widget'):
            self.palette_widget.set_color_external(hex_code)
        else:
            self.color = QColor(hex_code)
            if self.on_change_callback:
                self.on_change_callback()

    def _choose_custom_color(self):
        if hasattr(self, 'palette_widget'):
            self.palette_widget._open_picker_dialog()

    def _on_fade_change(self, val):
        self.fade_seconds = val / 10.0
        self.lbl_fade_val.setText(LanguageManager.tr("pointer_fade_time_val", sec=f"{self.fade_seconds:.1f}"))

    def set_thickness(self, new_val):
        self.thickness = max(1, min(int(new_val), 30))
        self.slider_thick.blockSignals(True)
        self.slider_thick.setValue(self.thickness)
        self.slider_thick.blockSignals(False)
        self.lbl_thick_val.setText(f"{self.thickness} px")
        if self.on_change_callback:
            self.on_change_callback()

    def _on_thick_change(self, val):
        self.thickness = val
        self.lbl_thick_val.setText(f"{val} px")
        if self.on_change_callback:
            self.on_change_callback()

    def retranslate_ui(self):
        self.lbl_mode.setText(LanguageManager.tr("pointer_mode"))
        self.btn_mode_single.setText(LanguageManager.tr("pointer_mode_single"))
        self.btn_mode_rainbow.setText(LanguageManager.tr("pointer_mode_rainbow"))
        self.lbl_fade_title.setText(LanguageManager.tr("pointer_fade_time"))
        self.lbl_fade_val.setText(LanguageManager.tr("pointer_fade_time_val", sec=f"{self.fade_seconds:.1f}"))
        self.lbl_thick_title.setText(LanguageManager.tr("pointer_thickness"))
        self.lbl_thick_val.setText(f"{self.thickness} px")
        if hasattr(self, 'palette_widget'):
            self.palette_widget.retranslate_ui()


class HighlighterRulerPopup(BaseSettingsPopup):
    """
    Highlighter seçiliyken PDF üzerinde sağ tıklandığında açılan
    mini cetvel kilidi (düz çizgi) kontrol ekranı.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        # Note: self.setStyleSheet is handled dynamically by BaseSettingsPopup.apply_theme

        card = QWidget(self)
        card.setObjectName("RulerCard")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Title row
        h_title = QHBoxLayout()
        self.lbl_title = QLabel(LanguageManager.tr("ruler_lock"))
        self.lbl_title.setObjectName("Title")
        h_title.addWidget(self.lbl_title)
        h_title.addStretch()
        layout.addLayout(h_title)

        self.lbl_desc = QLabel(LanguageManager.tr("ruler_lock_desc"))
        self.lbl_desc.setObjectName("Desc")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # Toggle button
        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("ToggleBtn")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.btn_toggle)

        # Tip
        self.lbl_tip = QLabel(LanguageManager.tr("ruler_lock_tip"))
        self.lbl_tip.setObjectName("Tip")
        self.lbl_tip.setWordWrap(True)
        layout.addWidget(self.lbl_tip)

        self.setFixedWidth(270)
        self.refresh_state()

    def retranslate_ui(self):
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setText(LanguageManager.tr("ruler_lock"))
        if hasattr(self, 'lbl_desc'):
            self.lbl_desc.setText(LanguageManager.tr("ruler_lock_desc"))
        if hasattr(self, 'lbl_tip'):
            self.lbl_tip.setText(LanguageManager.tr("ruler_lock_tip"))
        self.refresh_state()

    def refresh_state(self):
        is_snap = getattr(self.main_window.hl_popup, 'snap_straight', False)
        self.btn_toggle.blockSignals(True)
        self.btn_toggle.setChecked(is_snap)
        self.btn_toggle.blockSignals(False)
        if is_snap:
            self.btn_toggle.setText("✔  " + LanguageManager.tr("ruler_lock_status_on"))
        else:
            self.btn_toggle.setText("○  " + LanguageManager.tr("ruler_lock_status_off"))

    def _on_toggle_clicked(self):
        new_state = self.btn_toggle.isChecked()
        p = self.parent() or self.main_window
        if hasattr(p, 'set_ruler_snap'):
            p.set_ruler_snap(new_state)
        else:
            self.main_window.hl_popup.snap_straight = new_state
            if hasattr(self.main_window.hl_popup, 'chk_snap'):
                self.main_window.hl_popup.chk_snap.blockSignals(True)
                self.main_window.hl_popup.chk_snap.setChecked(new_state)
                self.main_window.hl_popup.chk_snap.blockSignals(False)
        self.refresh_state()

    def show_at(self, global_pos: QPoint):
        self.refresh_state()
        super().show_at(global_pos)


class RulerMeasurementPopup(BaseSettingsPopup):
    """
    Adobe Acrobat Pro tarzı ölçüm cetveli ayarları açılır penceresi.
    - Ölçüm birimi (cm, mm, in, pt)
    - Belge ölçeği (1:1, 1:5, 1:10, 1:20, 1:50, 1:100)
    - Tüm ölçümleri temizleme düğmesi
    - Klavye kullanım ipuçları
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        # Note: self.setStyleSheet is handled dynamically by BaseSettingsPopup.apply_theme

        card = QWidget(self)
        card.setObjectName("MeasurementCard")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Başlık
        self.lbl_title = QLabel(LanguageManager.tr("ruler_title"))
        self.lbl_title.setObjectName("Title")
        layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(LanguageManager.tr("ruler_desc"))
        self.lbl_desc.setObjectName("Desc")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # 1. Birim Seçimi
        h_unit = QHBoxLayout()
        self.lbl_unit = QLabel(LanguageManager.tr("ruler_unit_lbl"))
        self.lbl_unit.setObjectName("FieldLabel")
        h_unit.addWidget(self.lbl_unit)

        self.cmb_unit = QComboBox()
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_cm"), "cm")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_mm"), "mm")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_in"), "in")
        self.cmb_unit.addItem(LanguageManager.tr("ruler_unit_pt"), "pt")
        self.cmb_unit.currentIndexChanged.connect(self._on_unit_changed)
        h_unit.addWidget(self.cmb_unit, stretch=1)
        layout.addLayout(h_unit)

        # 2. Ölçek Seçimi
        h_scale = QHBoxLayout()
        self.lbl_scale = QLabel(LanguageManager.tr("ruler_scale_lbl"))
        self.lbl_scale.setObjectName("FieldLabel")
        h_scale.addWidget(self.lbl_scale)

        self.cmb_scale = QComboBox()
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_1"), 1.0)
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_5"), 5.0)
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_10"), 10.0)
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_20"), 20.0)
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_50"), 50.0)
        self.cmb_scale.addItem(LanguageManager.tr("ruler_scale_1_100"), 100.0)
        self.cmb_scale.currentIndexChanged.connect(self._on_scale_changed)
        h_scale.addWidget(self.cmb_scale, stretch=1)
        layout.addLayout(h_scale)

        # 3. Ölçümleri Temizle Düğmesi
        self.btn_clear = QPushButton(LanguageManager.tr("ruler_clear_all"))
        self.btn_clear.setObjectName("ClearBtn")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self.btn_clear)

        # 4. İpucu
        self.lbl_tip = QLabel(LanguageManager.tr("ruler_tip"))
        self.lbl_tip.setObjectName("Tip")
        self.lbl_tip.setWordWrap(True)
        layout.addWidget(self.lbl_tip)

        self.setFixedWidth(290)

    def _on_unit_changed(self):
        unit = self.cmb_unit.currentData() or "cm"
        self.main_window.measurement_unit = unit
        if tab_doc := self.main_window.get_current_tab_doc():
            scale_ratio = getattr(self.main_window, 'measurement_scale', 1.0)
            tab_doc.update_measurement_settings(unit, scale_ratio)

    def _on_scale_changed(self):
        scale_ratio = float(self.cmb_scale.currentData() or 1.0)
        self.main_window.measurement_scale = scale_ratio
        if tab_doc := self.main_window.get_current_tab_doc():
            unit = getattr(self.main_window, 'measurement_unit', 'cm')
            tab_doc.update_measurement_settings(unit, scale_ratio)

    def _on_clear_clicked(self):
        if tab_doc := self.main_window.get_current_tab_doc():
            tab_doc.clear_all_measurements()

    def retranslate_ui(self):
        self.lbl_title.setText(LanguageManager.tr("ruler_title"))
        self.lbl_desc.setText(LanguageManager.tr("ruler_desc"))
        self.lbl_unit.setText(LanguageManager.tr("ruler_unit_lbl"))
        self.lbl_scale.setText(LanguageManager.tr("ruler_scale_lbl"))
        self.btn_clear.setText(LanguageManager.tr("ruler_clear_all"))
        self.lbl_tip.setText(LanguageManager.tr("ruler_tip"))

        self.cmb_unit.blockSignals(True)
        self.cmb_unit.setItemText(0, LanguageManager.tr("ruler_unit_cm"))
        self.cmb_unit.setItemText(1, LanguageManager.tr("ruler_unit_mm"))
        self.cmb_unit.setItemText(2, LanguageManager.tr("ruler_unit_in"))
        self.cmb_unit.setItemText(3, LanguageManager.tr("ruler_unit_pt"))
        self.cmb_unit.blockSignals(False)

        self.cmb_scale.blockSignals(True)
        self.cmb_scale.setItemText(0, LanguageManager.tr("ruler_scale_1_1"))
        self.cmb_scale.setItemText(1, LanguageManager.tr("ruler_scale_1_5"))
        self.cmb_scale.setItemText(2, LanguageManager.tr("ruler_scale_1_10"))
        self.cmb_scale.setItemText(3, LanguageManager.tr("ruler_scale_1_20"))
        self.cmb_scale.setItemText(4, LanguageManager.tr("ruler_scale_1_50"))
        self.cmb_scale.setItemText(5, LanguageManager.tr("ruler_scale_1_100"))
        self.cmb_scale.blockSignals(False)

    def show_at(self, global_pos: QPoint):
        super().show_at(global_pos)



