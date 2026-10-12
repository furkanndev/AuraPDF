import json
import uuid
import math
import hashlib
import random
from typing import Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QPushButton, QSlider, QFrame, QColorDialog, 
                             QFontComboBox, QComboBox, QCheckBox, QApplication, QInputDialog, QMessageBox,
                             QStackedWidget, QScrollArea, QButtonGroup, QLineEdit)
from PyQt6.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath, QTextCursor, QFontMetricsF, QPixmap, QImage)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QTimer, QSettings, QEvent
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
    "vice_city": {
        "main_bg": "#160024", "main_text": "#fdf2f8", "tb_bg": "#240e3b", "tb_border": "#3d1663",
        "btn_hover": "#381458", "accent": "#ff2a85", "page_bg": "#2c1047", "page_border": "#ff2a85",
        "tab_bg": "#1e0a32", "tab_hover": "#351357", "tab_border": "#3d1663", "tab_text": "#e2d1f0",
        "view_bg": "#0d0017"
    },
    "apple": {
        "main_bg": "#0e1014", "main_text": "#f5f5f7", "tb_bg": "#1a1d24", "tb_border": "#2e3340",
        "btn_hover": "#2e3340", "accent": "#38bdf8", "page_bg": "#1e222b", "page_border": "#3b4252",
        "tab_bg": "#14171d", "tab_hover": "#222730", "tab_border": "#2e3340", "tab_text": "#cbd5e1",
        "view_bg": "#08090b"
    }
}
POPUP_THEME_SPECS["light"] = POPUP_THEME_SPECS["gray"]
POPUP_THEME_SPECS["dark"] = POPUP_THEME_SPECS["gray"]

def get_popup_theme_spec(theme_name: str = "gray") -> dict:
    """Temaya uygun popup stil özelliklerini döner; custom temada dinamik üretir."""
    if theme_name in ("light", "dark", "navy"):
        theme_name = "gray"
    if theme_name == "custom":
        try:
            from src.ui.modern_views import get_modern_theme_colors
            c = get_modern_theme_colors("custom")
            spec = {
                "main_bg": c["bg"], "main_text": c["text"], "tb_bg": c["surface"], "tb_border": c["border"],
                "btn_hover": c["surface_hover"], "accent": c["accent"], "page_bg": c["card_bg"], "page_border": c["card_border"],
                "tab_bg": c["tab_bg"], "tab_hover": c["surface_hover"], "tab_border": c["border"], "tab_text": c["tab_text"],
                "view_bg": c["bg"]
            }
            POPUP_THEME_SPECS["custom"] = spec
            return spec
        except Exception:
            pass
    return POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS["gray"])

POPUP_THEME_SPECS["custom"] = get_popup_theme_spec("custom")

# --- 0. POPUP TABAN SINIFI ---
class BaseSettingsPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        settings = QSettings("AuraPDF", "PDFViewer")
        current_th = settings.value("app_theme", "gray")
        spec = get_popup_theme_spec(current_th)
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

    def apply_theme(self, theme_name="dark", spec=None):
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("dark", {}))
        self.setStyleSheet(f"""
            QWidget, QWidget#RulerCard, QWidget#MeasurementCard {{
                background-color: {spec['tb_bg']};
                color: {spec['main_text']};
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
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
            QLabel#PanelHeaderTitle {{
                color: {spec['main_text']};
                font-size: 13px;
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
                background-color: transparent;
                color: {spec['main_text']};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {spec['btn_hover']};
                color: #ffffff;
                border: 1px solid transparent;
            }}
            QPushButton:checked, QPushButton[checked="true"] {{
                background-color: {spec['accent']};
                color: #ffffff;
                border: 1px solid transparent;
                font-weight: bold;
            }}
            QPushButton#FormatBtn, QPushButton.segment-btn, QPushButton#ToggleBtn {{
                background-color: transparent;
                color: {spec['tab_text']};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 6px;
                font-weight: 500;
                font-size: 11px;
                text-align: center;
            }}
            QPushButton#FormatBtn:hover, QPushButton.segment-btn:hover, QPushButton#ToggleBtn:hover {{
                background-color: {spec['btn_hover']};
                color: {spec['main_text']};
                border: 1px solid transparent;
            }}
            QPushButton#FormatBtn:checked, QPushButton#FormatBtn[checked="true"],
            QPushButton.segment-btn[checked="true"], QPushButton#ToggleBtn:checked {{
                background-color: {spec['accent']};
                color: #ffffff;
                border: 1px solid transparent;
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
                background-color: rgba(255, 255, 255, 0.03);
                color: {spec['main_text']};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                min-height: 24px;
            }}
            QComboBox:focus {{
                border: 1px solid {spec['accent']};
                background-color: rgba(255, 255, 255, 0.05);
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
                border: 1px solid rgba(255, 255, 255, 0.1);
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
        self.btn_rect.setChecked(mode == "rect")
        self.btn_lasso.setChecked(mode == "lasso")
        self.btn_move.setChecked(mode == "move")
        self.btn_ruler.setChecked(mode == "ruler")
        self.box_ruler_opts.setVisible(mode == "ruler")
        self.adjustSize()

        for btn in (self.btn_rect, self.btn_lasso, self.btn_move, self.btn_ruler):
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

        # --- PANEL BAŞLIĞI: METİN KUTUSU ---
        head_box = QHBoxLayout()
        head_box.setContentsMargins(0, 0, 0, 2)
        self.lbl_panel_title = QLabel(LanguageManager.tr("panel_text"))
        self.lbl_panel_title.setObjectName("PanelHeaderTitle")
        self.lbl_panel_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f1f5f9; border: none; background: transparent;")
        head_box.addWidget(self.lbl_panel_title)
        head_box.addStretch()
        layout.addLayout(head_box)

        # --- YAZI TİPİ BÖLÜMÜ ---
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
        if hasattr(self, 'lbl_panel_title'):
            self.lbl_panel_title.setText(LanguageManager.tr("panel_text"))
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
        current_th = settings.value("app_theme", "gray")
        if current_th == "navy":
            current_th = "gray"
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
                border: 1px solid rgba(255, 255, 255, 0.1);
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
                border: 1px solid rgba(255, 255, 255, 0.1);
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


# --- 7. ÇİZİM AYAR PENCERELERİ & FAVORİLER ---

DEFAULT_PEN_PRESETS = []
DEFAULT_HL_PRESETS = []


def build_fountain_pen_path(raw_pts, base_width=6.0):
    path = QPainterPath()
    if not raw_pts:
        return path
    if len(raw_pts) == 1:
        path.addEllipse(raw_pts[0], max(0.8, base_width / 2.0), max(0.8, base_width / 2.0))
        return path

    nib_angle = math.radians(40.0)
    left_pts = []
    right_pts = []
    n = len(raw_pts)

    for i in range(n):
        pt = raw_pts[i]
        if i == 0:
            dx = raw_pts[1].x() - pt.x()
            dy = raw_pts[1].y() - pt.y()
        elif i == n - 1:
            dx = pt.x() - raw_pts[i - 1].x()
            dy = pt.y() - raw_pts[i - 1].y()
        else:
            dx = raw_pts[i + 1].x() - raw_pts[i - 1].x()
            dy = raw_pts[i + 1].y() - raw_pts[i - 1].y()

        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-4:
            dx = 1.0
            dy = 0.0
            seg_len = 1.0

        theta = math.atan2(dy, dx)
        down_factor = max(0.0, dy / seg_len)

        # Flex fountain pen: downstroke expands with dy > 0, upstroke stays fine hairline
        w = max(1.8, min(base_width * 2.5, base_width * (0.32 + 1.65 * (down_factor ** 1.15))))

        nx = (-math.sin(theta) * 0.45 - math.sin(nib_angle) * 0.55) * (w / 2.0)
        ny = (math.cos(theta) * 0.45 + math.cos(nib_angle) * 0.55) * (w / 2.0)

        left_pts.append(QPointF(pt.x() + nx, pt.y() + ny))
        right_pts.append(QPointF(pt.x() - nx, pt.y() - ny))

    path.moveTo(left_pts[0])
    for lp in left_pts[1:]:
        path.lineTo(lp)
    for rp in reversed(right_pts):
        path.lineTo(rp)
    path.closeSubpath()
    return path


_PENCIL_TEXTURE_CACHE = {}
_PENCIL_FRINGE_CACHE = {}

_PENCIL_TEX_SIZE = 64
_PENCIL_BODY_INTENSITIES = bytearray(_PENCIL_TEX_SIZE * _PENCIL_TEX_SIZE)
_PENCIL_FRINGE_INTENSITIES = bytearray(_PENCIL_TEX_SIZE * _PENCIL_TEX_SIZE)

# Precalculate multi-frequency paper tooth noise once at module load
_rng = random.Random(777)
for _py in range(_PENCIL_TEX_SIZE):
    for _px in range(_PENCIL_TEX_SIZE):
        _idx = _py * _PENCIL_TEX_SIZE + _px
        _n1 = math.sin(_px * 0.22 + _py * 0.15) * math.cos(_py * 0.22 - _px * 0.1)
        _n2 = math.sin(_px * 0.55 + _py * 0.35) * math.sin(_py * 0.55)
        _speckle = _rng.random()
        _tooth = (_n1 * 0.3 + _n2 * 0.2 + 0.5) * 0.4 + _speckle * 0.6

        if _tooth > 0.22:
            _norm_t = (_tooth - 0.22) / 0.78
            _PENCIL_BODY_INTENSITIES[_idx] = int(min(255, 85 + (_norm_t ** 1.1) * 170))

        if _tooth > 0.45 and _rng.random() > 0.25:
            _norm_f = (_tooth - 0.45) / 0.55
            _PENCIL_FRINGE_INTENSITIES[_idx] = int(min(150, 35 + _norm_f * 115))


def _build_fast_pencil_pixmap(r: int, g: int, b: int, eff_alpha: float, intensities: bytearray) -> QPixmap:
    size = _PENCIL_TEX_SIZE
    buf = bytearray(size * size * 4)
    lut_b = bytearray(256)
    lut_g = bytearray(256)
    lut_r = bytearray(256)
    lut_a = bytearray(256)
    for raw_a in range(256):
        a = int(raw_a * eff_alpha)
        if a > 255: a = 255
        lut_a[raw_a] = a
        af_val = a / 255.0
        lut_b[raw_a] = int(b * af_val)
        lut_g[raw_a] = int(g * af_val)
        lut_r[raw_a] = int(r * af_val)

    buf_view = memoryview(buf)
    for i, raw_a in enumerate(intensities):
        if raw_a > 0:
            offset = i * 4
            buf_view[offset] = lut_b[raw_a]
            buf_view[offset + 1] = lut_g[raw_a]
            buf_view[offset + 2] = lut_r[raw_a]
            buf_view[offset + 3] = lut_a[raw_a]

    img = QImage(buf, size, size, size * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()
    return QPixmap.fromImage(img)


def get_graphite_lead_texture(color: QColor, alpha_scale: float = 1.0) -> QPixmap:
    r, g, b = color.red(), color.green(), color.blue()
    eff_alpha = min(1.0, max(0.04, color.alphaF() * float(alpha_scale)))
    key = (r, g, b, round(eff_alpha, 3))
    if key in _PENCIL_TEXTURE_CACHE:
        return _PENCIL_TEXTURE_CACHE[key]
    pix = _build_fast_pencil_pixmap(r, g, b, eff_alpha, _PENCIL_BODY_INTENSITIES)
    _PENCIL_TEXTURE_CACHE[key] = pix
    return pix


def get_graphite_fringe_texture(color: QColor, alpha_scale: float = 1.0) -> QPixmap:
    r, g, b = color.red(), color.green(), color.blue()
    eff_alpha = min(1.0, max(0.04, color.alphaF() * float(alpha_scale)))
    key = (r, g, b, round(eff_alpha, 3))
    if key in _PENCIL_FRINGE_CACHE:
        return _PENCIL_FRINGE_CACHE[key]
    pix = _build_fast_pencil_pixmap(r, g, b, eff_alpha, _PENCIL_FRINGE_INTENSITIES)
    _PENCIL_FRINGE_CACHE[key] = pix
    return pix


class StrokePreviewWidget(QFrame):
    def __init__(self, parent=None, width=210, height=48):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setStyleSheet("background-color: transparent; border: none; border-radius: 6px;")
        self.color = QColor(255, 235, 59, 120)
        self.thickness = 20
        self.is_eraser = False
        self.eraser_mode = "stroke"
        self.line_style = "solid"
        self.is_hl = False

    def update_style(self, color, thickness, is_eraser=False, eraser_mode="stroke", line_style="solid", is_hl=False, pen_type="solid"):
        self.color = color
        self.thickness = thickness
        self.is_eraser = is_eraser
        self.eraser_mode = eraser_mode
        self.line_style = line_style
        self.is_hl = is_hl
        self.pen_type = pen_type
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
        start_x, end_x = max(12.0, w * 0.08), min(w - 12.0, w * 0.92)

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
            is_pencil = (getattr(self, 'pen_type', 'solid') == "pencil" or self.line_style == "pencil")

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
            max_stroke_thick = max(1.0, min(float(self.thickness), h - 8.0))
            if self.color.lightnessF() > 0.65 and not is_pencil and self.line_style != "calligraphy":
                under_col = QColor(40, 50, 70, 40)
                under_pen = QPen(under_col, min(max_stroke_thick + 2.0, h - 4.0), style, cap, join)
                p.setPen(under_pen)
                if is_arrow:
                    arrow_len = max(8.0, min(18.0, max_stroke_thick * 2.2 + 6.0))
                    line_end_x = max(start_x + 10.0, end_x - arrow_len * 0.7)
                    p.drawLine(QPointF(start_x, mid_y), QPointF(line_end_x, mid_y))
                else:
                    p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))

            if self.line_style == "calligraphy":
                fp_pts = []
                steps = 50
                w_span = end_x - start_x
                for s in range(steps + 1):
                    t = s / float(steps)
                    px = start_x + t * w_span
                    py = mid_y - 6.0 * math.sin(t * 2.0 * math.pi)
                    fp_pts.append(QPointF(px, py))
                fp_path = build_fountain_pen_path(fp_pts, base_width=max_stroke_thick)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(self.color))
                p.drawPath(fp_path)
            elif is_pencil:
                base_c = QColor(self.color)
                tex = get_graphite_lead_texture(base_c)
                tex_fringe = get_graphite_fringe_texture(base_c)

                if self.line_style in ("pencil", "solid"):
                    pencil_pts = []
                    steps = 60
                    w_span = end_x - start_x
                    for s in range(steps + 1):
                        t = s / float(steps)
                        px = start_x + t * w_span
                        py = mid_y - 4.5 * math.sin(t * 2.0 * math.pi)
                        pencil_pts.append(QPointF(px, py))

                    p_lead = QPainterPath()
                    p_lead.moveTo(pencil_pts[0])
                    for i, pt in enumerate(pencil_pts[1:]):
                        jx = ((i * 17) % 7 - 3) * 0.05 * max_stroke_thick
                        jy = ((i * 23) % 7 - 3) * 0.05 * max_stroke_thick
                        p_lead.lineTo(pt.x() + jx, pt.y() + jy)

                    pen_fringe = QPen(QBrush(tex_fringe), max_stroke_thick * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_lead, pen_fringe)

                    pen_lead = QPen(QBrush(tex), max_stroke_thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_lead, pen_lead)

                    pen_core = QPen(QBrush(tex), max(0.6, max_stroke_thick * 0.58), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_lead, pen_core)

                elif self.line_style == "arrow":
                    arrow_len = max(8.0, min(18.0, max_stroke_thick * 2.2 + 6.0))
                    p_arrow = QPainterPath()
                    p_arrow.moveTo(QPointF(start_x, mid_y))
                    p_arrow.lineTo(QPointF(end_x, mid_y))
                    p_arrow.moveTo(QPointF(end_x - arrow_len, mid_y - arrow_len * 0.55))
                    p_arrow.lineTo(QPointF(end_x, mid_y))
                    p_arrow.lineTo(QPointF(end_x - arrow_len, mid_y + arrow_len * 0.55))

                    pen_fringe = QPen(QBrush(tex_fringe), max_stroke_thick * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_arrow, pen_fringe)

                    pen_lead = QPen(QBrush(tex), max_stroke_thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_arrow, pen_lead)

                else:
                    # Dash, Dot, DashDot (single clean graphite textured path)
                    p_line = QPainterPath()
                    p_line.moveTo(QPointF(start_x, mid_y))
                    p_line.lineTo(QPointF(end_x, mid_y))

                    pen_tex = QPen(QBrush(tex), max_stroke_thick, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    if self.line_style == "dash":
                        pen_tex.setDashPattern([2.2, 1.5])
                    elif self.line_style == "dot":
                        pen_tex.setDashPattern([0.01, 1.9])
                    elif self.line_style == "dashdot":
                        pen_tex.setDashPattern([2.2, 1.4, 0.01, 1.4])
                    p.strokePath(p_line, pen_tex)

            elif is_arrow:
                pen = QPen(self.color, max_stroke_thick, style, cap, join)
                p.setPen(pen)
                arrow_len = max(8.0, min(18.0, max_stroke_thick * 2.2 + 6.0))
                line_end_x = max(start_x + 10.0, end_x - arrow_len * 0.7)
                p.drawLine(QPointF(start_x, mid_y), QPointF(line_end_x, mid_y))
                # Arrowhead wings
                p.setPen(QPen(self.color, max(2.0, min(max_stroke_thick * 0.85, 7.0)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawLine(QPointF(end_x, mid_y), QPointF(end_x - arrow_len, mid_y - arrow_len * 0.55))
                p.drawLine(QPointF(end_x, mid_y), QPointF(end_x - arrow_len, mid_y + arrow_len * 0.55))
            elif self.line_style == "brush":
                pen = QPen(self.color, max_stroke_thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))
            else:
                pen = QPen(self.color, max_stroke_thick, style, cap, join)
                p.setPen(pen)
                p.drawLine(QPointF(start_x, mid_y), QPointF(end_x, mid_y))

        p.end()


class ModernToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accent_color = QColor("#3b82f6")

    def apply_theme(self, theme_name: str, spec: dict):
        if spec and "accent" in spec:
            self.accent_color = QColor(spec["accent"])
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        checked = self.isChecked()
        bg_col = self.accent_color if checked else QColor(255, 255, 255, 45)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg_col))
        p.drawRoundedRect(QRectF(0, 1, 40, 20), 10, 10)
        
        thumb_x = 21.0 if checked else 3.0
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QRectF(thumb_x, 3.0, 16.0, 16.0))
        p.end()


class ModernValueSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_accent = QColor("#38bdf8")
        self.theme_thumb = QColor("#505663")

    def apply_theme(self, theme_name: str, spec: dict):
        if spec:
            if "accent" in spec:
                self.theme_accent = QColor(spec["accent"])
            if "page_bg" in spec:
                self.theme_thumb = QColor(spec["page_bg"])
            elif "tb_bg" in spec:
                self.theme_thumb = QColor(spec["tb_bg"])
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        val_range = max(1, self.maximum() - self.minimum())
        ratio = max(0.0, min(1.0, (self.value() - self.minimum()) / val_range))
        
        thumb_r = 13.0
        track_margin = thumb_r + 2.0
        track_w = max(1.0, w - track_margin * 2.0)
        track_h = 14.0
        track_y = (h - track_h) / 2.0
        track_rect = QRectF(track_margin, track_y, track_w, track_h)
        radius = track_h / 2.0

        # Inactive capsule track matching screenshot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 25)))
        p.drawRoundedRect(track_rect, radius, radius)

        # Subtle tick dots along track
        dot_count = 10
        p.setBrush(QBrush(QColor(255, 255, 255, 50)))
        for i in range(1, dot_count):
            dot_x = track_margin + (track_w / dot_count) * i
            p.drawEllipse(QPointF(dot_x, h / 2.0), 1.5, 1.5)
        
        # Circle thumb with number inside
        thumb_x = track_margin + track_w * ratio
        p.setBrush(QBrush(self.theme_thumb))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
        p.drawEllipse(QPointF(thumb_x, h / 2.0), thumb_r, thumb_r)
        
        p.setPen(QPen(QColor("#ffffff")))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(thumb_x - thumb_r, h / 2.0 - thumb_r, thumb_r * 2.0, thumb_r * 2.0), 
                   Qt.AlignmentFlag.AlignCenter, str(self.value()))
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_val_from_mouse(event.pos().x())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_val_from_mouse(event.pos().x())
        super().mouseMoveEvent(event)

    def _update_val_from_mouse(self, x):
        thumb_r = 13.0
        track_margin = thumb_r + 2.0
        track_w = max(1.0, float(self.width()) - track_margin * 2.0)
        ratio = max(0.0, min(1.0, (float(x) - track_margin) / track_w))
        new_val = int(round(self.minimum() + ratio * (self.maximum() - self.minimum())))
        self.setValue(new_val)


class ModernOpacitySlider(QSlider):
    """
    Boya Yoğunluğu (Opacity/Alpha) kaydırıcısı:
    - Kapsül formunda koyu saydamlık dama tahtası (checkerboard pattern)
    - Seçili aktif renge göre soldan sağa lineer opaklık gradyanı
    - Aktif renkle boyanmış ve içinde yüzde değerini gösteren dairesel tutamaç
    """
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.active_color = QColor("#10b981")

    def set_active_color(self, color: QColor):
        if color:
            self.active_color = QColor(color.red(), color.green(), color.blue(), 255)
            self.update()

    def apply_theme(self, theme_name: str, spec: dict):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        val_range = max(1, self.maximum() - self.minimum())
        ratio = max(0.0, min(1.0, (self.value() - self.minimum()) / val_range))

        thumb_r = 13.0
        track_margin = thumb_r + 2.0
        track_w = max(1.0, w - track_margin * 2.0)
        track_h = 14.0
        track_y = (h - track_h) / 2.0
        track_rect = QRectF(track_margin, track_y, track_w, track_h)
        radius = track_h / 2.0

        # 1. Kapsül maskeleme (Clip path)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius, radius)
        p.save()
        p.setClipPath(track_path)

        # 2. Saydamlık hissi veren koyu dama tahtası deseni
        sq_size = 4.0
        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(track_rect, QColor(16, 20, 26))
        p.setBrush(QBrush(QColor(32, 40, 52)))
        
        start_x = track_rect.left()
        end_x = track_rect.right()
        start_y = track_rect.top()
        end_y = track_rect.bottom()
        
        x = start_x
        col_idx = 0
        while x < end_x:
            y = start_y
            row_idx = col_idx % 2
            while y < end_y:
                if row_idx % 2 == 1:
                    p.drawRect(QRectF(x, y, min(sq_size, end_x - x), min(sq_size, end_y - y)))
                y += sq_size
                row_idx += 1
            x += sq_size
            col_idx += 1

        # 3. Aktif renk gradyanı: solda saydam (%5), sağda tam opak (%100)
        r = self.active_color.red()
        g = self.active_color.green()
        b = self.active_color.blue()
        grad = QLinearGradient(track_rect.left(), 0, track_rect.right(), 0)
        grad.setColorAt(0.0, QColor(r, g, b, 5))
        grad.setColorAt(0.25, QColor(r, g, b, 55))
        grad.setColorAt(0.70, QColor(r, g, b, 190))
        grad.setColorAt(1.0, QColor(r, g, b, 255))
        p.setBrush(QBrush(grad))
        p.drawRect(track_rect)
        p.restore()

        # 4. İnce kapsül dış kenarlık
        p.setPen(QPen(QColor(255, 255, 255, 25), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(track_rect, radius, radius)

        # 5. Aktif renkli dairesel tutamaç ve kontrast kontrollü metin
        thumb_x = track_margin + track_w * ratio
        p.setBrush(QBrush(self.active_color))
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
        p.drawEllipse(QPointF(thumb_x, h / 2.0), thumb_r, thumb_r)

        lum = (r * 299 + g * 587 + b * 114) / 1000
        txt_col = QColor("#0f172a") if lum > 175 else QColor("#ffffff")
        p.setPen(QPen(txt_col))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(thumb_x - thumb_r, h / 2.0 - thumb_r, thumb_r * 2.0, thumb_r * 2.0),
                   Qt.AlignmentFlag.AlignCenter, str(self.value()))
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_val_from_mouse(event.pos().x())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_val_from_mouse(event.pos().x())
        super().mouseMoveEvent(event)

    def _update_val_from_mouse(self, x):
        thumb_r = 13.0
        track_margin = thumb_r + 2.0
        track_w = max(1.0, float(self.width()) - track_margin * 2.0)
        ratio = max(0.0, min(1.0, (float(x) - track_margin) / track_w))
        new_val = int(round(self.minimum() + ratio * (self.maximum() - self.minimum())))
        self.setValue(new_val)


class LineStylePill(QPushButton):
    def __init__(self, style_key: str, label: str = "", on_click=None, parent=None):
        super().__init__(parent)
        self.style_key = style_key
        self.label = label
        self.on_click = on_click
        self.setCheckable(True)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_checked_bg = QColor("#3e4450")
        self.theme_checked_border = QColor(255, 255, 255, 90)
        if label:
            self.setToolTip(label)
        if on_click:
            self.clicked.connect(lambda: self.on_click(self.style_key))

    def apply_theme(self, theme_name: str, spec: dict):
        if spec:
            self.theme_checked_bg = QColor(spec.get("page_bg", "#3e4450"))
            self.theme_checked_border = QColor(spec.get("accent", "#60a5fa"))
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0

        if self.isChecked():
            p.setPen(QPen(self.theme_checked_border, 1.4))
            p.setBrush(QBrush(self.theme_checked_bg))
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 18)))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 14.0, 14.0)

        stroke_col = QColor("#ffffff") if self.isChecked() else QColor("#cbd5e1")
        if self.style_key == "solid":
            p.setPen(QPen(stroke_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx - 12.0, cy), QPointF(cx + 12.0, cy))
        elif self.style_key == "calligraphy":
            path = QPainterPath()
            path.moveTo(cx - 12.0, cy + 2.0)
            path.cubicTo(cx - 4.0, cy - 4.0, cx + 4.0, cy + 4.0, cx + 12.0, cy - 2.0)
            p.setPen(QPen(stroke_col, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.strokePath(path, p.pen())
        elif self.style_key == "pencil":
            p.setPen(QPen(QColor(stroke_col.red(), stroke_col.green(), stroke_col.blue(), 180), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx - 12.0, cy), QPointF(cx + 12.0, cy))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(stroke_col))
            for i in range(-10, 11, 4):
                p.drawEllipse(QPointF(cx + i, cy + ((i * 7) % 3 - 1) * 0.7), 0.7, 0.7)
        elif self.style_key == "brush":
            p.setPen(QPen(stroke_col, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(QPointF(cx - 12.0, cy), QPointF(cx + 12.0, cy))
        elif self.style_key == "dash":
            p.setPen(QPen(stroke_col, 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx - 12.0, cy), QPointF(cx - 3.0, cy))
            p.drawLine(QPointF(cx + 3.0, cy), QPointF(cx + 12.0, cy))
        elif self.style_key == "dot":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(stroke_col))
            for i in range(5):
                p.drawEllipse(QPointF(cx - 10.0 + i * 5.0, cy), 1.5, 1.5)
        elif self.style_key == "arrow":
            p.setPen(QPen(stroke_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx - 12.0, cy), QPointF(cx + 8.0, cy))
            p.drawLine(QPointF(cx + 8.0, cy), QPointF(cx + 4.0, cy - 3.5))
            p.drawLine(QPointF(cx + 8.0, cy), QPointF(cx + 4.0, cy + 3.5))
        p.end()


class CircularColorSwatch(QPushButton):
    def __init__(self, color_hex: str, on_click=None, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.on_click = on_click
        self.is_active = False
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color_hex)
        if on_click:
            self.clicked.connect(lambda: self.on_click(self.color_hex))

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = QColor(self.color_hex)
        rect = QRectF(1.0, 1.0, 24.0, 24.0)
        cx, cy = 13.0, 13.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(col))
        p.drawEllipse(rect)

        if self.is_active:
            p.setPen(QPen(QColor(255, 255, 255, 180), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(0.5, 0.5, 25.0, 25.0))

            check_path = QPainterPath()
            check_path.moveTo(cx - 4.5, cy + 0.5)
            check_path.lineTo(cx - 1.0, cy + 4.0)
            check_path.lineTo(cx + 4.5, cy - 3.5)

            if col.lightnessF() > 0.65:
                p.setPen(QPen(QColor(0, 0, 0, 180), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawPath(check_path)
            p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(check_path)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)
        p.end()


class PenRackItem(QWidget):
    def __init__(self, pen_type: str, label: str = "", on_click=None, parent=None):
        super().__init__(parent)
        self.pen_type = pen_type
        self.label = label
        self.on_click = on_click
        self.is_active = False
        self.is_hovered = False
        self.active_color = QColor("#e60214")
        self.setFixedSize(50, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if label:
            self.setToolTip(label)

    def set_active(self, active: bool, color = None):
        self.is_active = active
        if color is not None:
            if isinstance(color, str):
                self.active_color = QColor(color)
            elif isinstance(color, QColor):
                self.active_color = color
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
            if self.on_click:
                self.on_click(self.pen_type)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = float(self.width()) / 2.0
        if self.is_active:
            base_y = 4.0
        elif self.is_hovered:
            base_y = 7.0
        else:
            base_y = 10.0

        active_col = self.active_color if isinstance(self.active_color, QColor) else QColor(self.active_color)
        
        # Flourish dotted arc above active pen (as in reference image)
        if self.is_active:
            p.setPen(QPen(active_col, 1.4, Qt.PenStyle.DotLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            arc_path = QPainterPath()
            arc_path.moveTo(cx - 10.0, base_y - 2.0)
            arc_path.cubicTo(cx - 5.0, base_y - 9.0, cx + 5.0, base_y - 1.0, cx + 11.0, base_y - 7.0)
            p.drawPath(arc_path)

        if self.pen_type == "calligraphy":
            self._paint_fountain_pen(p, cx, base_y)
        elif self.pen_type == "highlighter":
            self._paint_chisel_pen(p, cx, base_y)
        elif self.pen_type == "marker":
            self._paint_marker_pen(p, cx, base_y)
        elif self.pen_type == "solid":
            self._paint_felt_pen(p, cx, base_y)
        elif self.pen_type in ("pencil", "dash"):
            self._paint_pencil(p, cx, base_y)
        else: # brush or arrow
            self._paint_brush_pen(p, cx, base_y)
        p.end()

    def _paint_marker_pen(self, p, cx, base_y):
        barrel_col = QColor("#1e293b") if not self.is_active else QColor("#334155")
        p.setPen(Qt.PenStyle.NoPen)
        # Geniş marker gövdesi
        p.setBrush(QBrush(barrel_col))
        p.drawRoundedRect(QRectF(cx - 7.5, base_y + 22.0, 15.0, 42.0), 3.0, 3.0)
        
        # Renk indikatör şeridi
        tip_col = self.active_color if isinstance(self.active_color, QColor) else QColor(self.active_color)
        p.setBrush(QBrush(tip_col))
        p.drawRect(QRectF(cx - 7.5, base_y + 36.0, 15.0, 4.0))

        # Yaka / Konik manşon
        p.setBrush(QBrush(QColor("#0f172a")))
        p.drawRoundedRect(QRectF(cx - 6.5, base_y + 16.0, 13.0, 7.0), 1.5, 1.5)

        # Yuvarlak keçeli uç (Bullet tip)
        p.setBrush(QBrush(tip_col))
        tip_path = QPainterPath()
        tip_path.moveTo(cx - 3.5, base_y + 16.0)
        tip_path.lineTo(cx - 3.5, base_y + 9.0)
        tip_path.quadTo(cx, base_y + 2.0, cx + 3.5, base_y + 9.0)
        tip_path.lineTo(cx + 3.5, base_y + 16.0)
        tip_path.closeSubpath()
        p.drawPath(tip_path)

    def _paint_fountain_pen(self, p, cx, base_y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#334155")))
        p.drawRoundedRect(QRectF(cx - 6.0, base_y + 26.0, 12.0, 38.0), 3.0, 3.0)
        p.setBrush(QBrush(QColor("#0f172a")))
        p.drawRoundedRect(QRectF(cx - 7.0, base_y + 22.0, 14.0, 6.0), 1.5, 1.5)
        
        nib = QPainterPath()
        nib.moveTo(cx - 7.0, base_y + 22.0)
        nib.lineTo(cx - 8.0, base_y + 14.0)
        nib.lineTo(cx, base_y + 3.0)
        nib.lineTo(cx + 8.0, base_y + 14.0)
        nib.lineTo(cx + 7.0, base_y + 22.0)
        nib.closeSubpath()
        nib_col = self.active_color if self.is_active else QColor("#cbd5e1")
        p.setBrush(QBrush(nib_col))
        p.drawPath(nib)
        
        p.setPen(QPen(QColor(0, 0, 0, 140), 1.2))
        p.drawLine(QPointF(cx, base_y + 3.0), QPointF(cx, base_y + 16.0))
        p.drawEllipse(QPointF(cx, base_y + 16.0), 1.2, 1.2)

    def _paint_chisel_pen(self, p, cx, base_y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#334155")))
        p.drawRoundedRect(QRectF(cx - 7.0, base_y + 24.0, 14.0, 40.0), 2.0, 2.0)
        
        ring_col = self.active_color if self.is_active else QColor("#06b6d4")
        p.setBrush(QBrush(ring_col))
        p.drawRoundedRect(QRectF(cx - 8.0, base_y + 20.0, 16.0, 5.0), 1.5, 1.5)
        
        chisel = QPainterPath()
        chisel.moveTo(cx - 6.0, base_y + 20.0)
        chisel.lineTo(cx - 5.0, base_y + 8.0)
        chisel.lineTo(cx + 4.0, base_y + 4.0)
        chisel.lineTo(cx + 6.0, base_y + 6.0)
        chisel.lineTo(cx + 6.0, base_y + 20.0)
        chisel.closeSubpath()
        p.setBrush(QBrush(ring_col))
        p.drawPath(chisel)

    def _paint_felt_pen(self, p, cx, base_y):
        barrel_col = self.active_color if self.is_active else QColor("#475569")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(barrel_col))
        p.drawRoundedRect(QRectF(cx - 6.5, base_y + 22.0, 13.0, 42.0), 3.0, 3.0)
        
        p.setBrush(QBrush(QColor("#64748b")))
        p.drawRoundedRect(QRectF(cx - 6.0, base_y + 16.0, 12.0, 7.0), 1.5, 1.5)
        
        cone = QPainterPath()
        cone.moveTo(cx - 5.0, base_y + 16.0)
        cone.lineTo(cx - 1.8, base_y + 7.0)
        cone.lineTo(cx + 1.8, base_y + 7.0)
        cone.lineTo(cx + 5.0, base_y + 16.0)
        cone.closeSubpath()
        p.setBrush(QBrush(QColor("#94a3b8")))
        p.drawPath(cone)
        
        p.setBrush(QBrush(barrel_col))
        p.drawRoundedRect(QRectF(cx - 1.5, base_y + 3.0, 3.0, 5.0), 1.0, 1.0)

    def _paint_pencil(self, p, cx, base_y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1e293b")))
        p.drawRoundedRect(QRectF(cx - 6.0, base_y + 28.0, 12.0, 36.0), 2.0, 2.0)
        p.setBrush(QBrush(QColor("#0f172a")))
        p.drawRect(QRectF(cx - 6.0, base_y + 24.0, 12.0, 5.0))
        
        wood = QPainterPath()
        wood.moveTo(cx - 6.0, base_y + 24.0)
        wood.lineTo(cx, base_y + 7.0)
        wood.lineTo(cx + 6.0, base_y + 24.0)
        wood.closeSubpath()
        p.setBrush(QBrush(QColor("#d4b886")))
        p.drawPath(wood)
        
        graphite = QPainterPath()
        graphite.moveTo(cx - 2.5, base_y + 14.0)
        graphite.lineTo(cx, base_y + 7.0)
        graphite.lineTo(cx + 2.5, base_y + 14.0)
        graphite.closeSubpath()
        tip_col = self.active_color if self.is_active else QColor("#1e293b")
        p.setBrush(QBrush(tip_col))
        p.drawPath(graphite)

    def _paint_brush_pen(self, p, cx, base_y):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#334155")))
        p.drawRoundedRect(QRectF(cx - 6.0, base_y + 28.0, 12.0, 36.0), 2.0, 2.0)
        
        brush_col = self.active_color if self.is_active else QColor("#f43f5e")
        p.setBrush(QBrush(brush_col))
        p.drawRoundedRect(QRectF(cx - 6.5, base_y + 24.0, 13.0, 5.0), 1.5, 1.5)
        
        p.setBrush(QBrush(QColor("#94a3b8")))
        p.drawRoundedRect(QRectF(cx - 5.5, base_y + 18.0, 11.0, 7.0), 1.5, 1.5)
        
        hair = QPainterPath()
        hair.moveTo(cx - 5.0, base_y + 18.0)
        hair.cubicTo(cx - 6.5, base_y + 12.0, cx - 1.5, base_y + 5.0, cx, base_y + 3.0)
        hair.cubicTo(cx + 1.5, base_y + 5.0, cx + 6.5, base_y + 12.0, cx + 5.0, base_y + 18.0)
        hair.closeSubpath()
        p.setBrush(QBrush(brush_col))
        p.drawPath(hair)


class ToolPresetCard(QFrame):
    def __init__(self, preset: dict, is_hl: bool, is_active: bool, on_select, on_delete, parent=None, spec: dict = None):
        super().__init__(parent)
        self.preset = preset
        self.is_hl = is_hl
        self.is_active = is_active
        self.on_select = on_select
        self.on_delete = on_delete
        self.current_spec = spec or POPUP_THEME_SPECS.get("gray", {})
        self.setObjectName("ToolPresetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()
        self.update_active_state(is_active)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self.preview = StrokePreviewWidget(parent=self, width=280, height=34)
        c = QColor(self.preset.get("color", "#000000"))
        opac = int(self.preset.get("opacity", 100))
        c.setAlpha(int(opac * 2.55))
        thick = int(self.preset.get("thickness", 3))
        st = self.preset.get("line_style", "solid")
        self.preview.update_style(
            color=c,
            thickness=thick,
            is_eraser=False,
            eraser_mode="stroke",
            line_style=st,
            is_hl=self.is_hl
        )
        self.preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.preview)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(2, 0, 2, 0)
        info_row.setSpacing(4)

        desc = self._format_desc()
        text_col = self.current_spec.get('tab_text', '#94a3b8')
        self.lbl_info = QLabel(desc, parent=self)
        self.lbl_info.setStyleSheet(f"font-size: 11px; color: {text_col}; font-weight: normal; border: none; background: transparent;")
        info_row.addWidget(self.lbl_info)

        info_row.addStretch()

        self.lbl_active = QLabel("✓", parent=self)
        self.lbl_active.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; border: none; background: transparent;")
        self.lbl_active.setVisible(self.is_active)
        info_row.addWidget(self.lbl_active)

        self.btn_del = QPushButton(parent=self)
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setIcon(ModernIconFactory.icon_trash(color=text_col))
        self.btn_del.setToolTip(LanguageManager.tr("delete_preset_tip"))
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.25);
            }
        """)
        self.btn_del.clicked.connect(self._on_delete_clicked)
        info_row.addWidget(self.btn_del)

        layout.addLayout(info_row)

    def _format_desc(self) -> str:
        thick = self.preset.get("thickness", 3)
        opac = self.preset.get("opacity", 100)
        st = self.preset.get("line_style", "solid")
        snap = self.preset.get("snap_straight", False)

        style_names = {
            "solid": LanguageManager.tr("pen_style_solid"),
            "dash": LanguageManager.tr("pen_style_dash"),
            "dot": LanguageManager.tr("pen_style_dot"),
            "dashdot": LanguageManager.tr("pen_style_dashdot"),
            "arrow": LanguageManager.tr("pen_style_arrow"),
            "calligraphy": LanguageManager.tr("pen_style_calligraphy"),
        }
        st_name = style_names.get(st, st)
        if self.is_hl:
            text = f"{thick}px • %{opac}"
        else:
            text = f"{thick}px • {st_name}"
        if snap:
            snap_lbl = LanguageManager.tr("straighten_lines")
            text += f" • {snap_lbl}"
        return text

    def apply_theme(self, theme_name: str, spec: dict = None):
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("gray", {}))
        self.current_spec = spec
        if hasattr(self, 'lbl_info'):
            self.lbl_info.setStyleSheet(f"font-size: 11px; color: {spec.get('tab_text', '#94a3b8')}; font-weight: normal; border: none; background: transparent;")
        if hasattr(self, 'btn_del'):
            self.btn_del.setIcon(ModernIconFactory.icon_trash(color=spec.get('tab_text', '#94a3b8')))
        self.update_active_state(self.is_active)

    def update_active_state(self, is_active: bool):
        self.is_active = is_active
        self.lbl_active.setVisible(is_active)
        spec = getattr(self, 'current_spec', {})
        accent = spec.get('accent', '#3b82f6')
        tb_border = spec.get('tb_border', 'rgba(255, 255, 255, 0.08)')
        btn_hover = spec.get('btn_hover', 'rgba(255, 255, 255, 0.08)')
        if is_active:
            self.setStyleSheet(f"""
                QFrame#ToolPresetCard {{
                    background-color: rgba(59, 130, 246, 0.15);
                    border: 1.5px solid {accent};
                    border-radius: 10px;
                }}
                QFrame#ToolPresetCard:hover {{
                    background-color: rgba(59, 130, 246, 0.22);
                    border: 1.5px solid {accent};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ToolPresetCard {{
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid {tb_border};
                    border-radius: 10px;
                }}
                QFrame#ToolPresetCard:hover {{
                    background-color: {btn_hover};
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.on_select:
                self.on_select(self.preset)
        super().mousePressEvent(event)

    def _on_delete_clicked(self):
        if self.on_delete:
            self.on_delete(self.preset.get("id"))


class ToolSettingsPopup(BaseSettingsPopup):
    def __init__(self, parent=None, has_color=True, has_opacity=True, is_eraser=False, is_hl=False, on_change_callback=None, tool_name=None):
        self.on_change_callback = on_change_callback
        self.has_color = has_color
        self.has_opacity = has_opacity
        self.is_eraser = is_eraser
        self.is_hl = is_hl
        self.tool_name = tool_name or ("highlighter" if is_hl else ("eraser" if is_eraser else "pen"))
        self.eraser_mode = "stroke"
        self.line_style = "solid"
        self.snap_straight = False
        self.preset_cards = []
        self.rack_items = {}
        self.style_container = None
        self.current_pen_type = "solid"
        self.pen_settings = self._load_pen_settings()
        self.hl_settings = self._load_hl_settings()
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self._anchor_widget = None

        if self.is_hl:
            settings = QSettings("AuraPDF", "PDFViewer")
            self.hl_type = settings.value("active_hl_type", "highlighter")
            if self.hl_type not in self.hl_settings:
                self.hl_type = "highlighter"
            cfg = self.hl_settings.get(self.hl_type, {})
            self.thickness = cfg.get("thickness", 18 if self.hl_type == "highlighter" else 12)
            self.opacity = cfg.get("opacity", 40 if self.hl_type == "highlighter" else 60)
            self.line_style = cfg.get("line_style", "solid" if self.hl_type == "highlighter" else "marker")
            saved_col = cfg.get("color", "#EBDF00" if self.hl_type == "highlighter" else "#16C44B")
            self.color = QColor(saved_col)
            self.color.setAlpha(int(self.opacity * 2.55))
        elif self.tool_name == "pen":
            settings = QSettings("AuraPDF", "PDFViewer")
            self.current_pen_type = settings.value("active_pen_type", "solid")
            if self.current_pen_type not in self.pen_settings:
                self.current_pen_type = "solid"
            cfg = self.pen_settings.get(self.current_pen_type, {})
            default_thick = 6 if self.current_pen_type == "calligraphy" else (3 if self.current_pen_type == "pencil" else (8 if self.current_pen_type == "brush" else 2))
            self.thickness = cfg.get("thickness", default_thick)
            self.opacity = cfg.get("opacity", 100)
            saved_st = cfg.get("line_style", self.current_pen_type)
            if self.current_pen_type == "calligraphy":
                self.line_style = "calligraphy"
            elif self.current_pen_type == "brush":
                self.line_style = "brush"
            elif self.current_pen_type == "pencil":
                self.line_style = saved_st if saved_st in ("pencil", "dash", "dot", "arrow") else "pencil"
            elif self.current_pen_type == "solid":
                self.line_style = saved_st if saved_st in ("solid", "dash", "dot", "arrow") else "solid"
            else:
                self.line_style = saved_st
            saved_col = cfg.get("color", "#e60214")
            self.color = QColor(saved_col)
            self.color.setAlpha(int(self.opacity * 2.55) if self.has_opacity else 255)
        elif self.is_eraser:
            self.thickness = 24
            self.opacity = 100
            self.color = QColor(255, 235, 59, 255)
        else:
            self.thickness = 18
            self.opacity = 40
            self.color = QColor(255, 235, 59, int(self.opacity * 2.55))

        # Modern tablet floating card appearance
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("SleekToolPopup")

        # Container card layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("SleekCardFrame")
        self.card_frame.setStyleSheet("""
            QFrame#SleekCardFrame {
                background-color: #212327;
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 18px;
            }
            QToolTip {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        root_layout.addWidget(self.card_frame)

        layout = QVBoxLayout(self.card_frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        if self.tool_name in ("pen", "highlighter"):
            self.setFixedWidth(330)
            self.presets = self._load_presets_from_settings()
            self._presets_dirty = False

            # --- TOP HEADER: Title ... Close ---
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 4)
            header_layout.setSpacing(6)

            self.lbl_title = QLabel(self._get_title_for_tab(0))
            self.lbl_title.setObjectName("ToolPanelTitle")
            self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f5f9; border: none; background: transparent;")
            header_layout.addWidget(self.lbl_title)

            header_layout.addStretch()

            self.btn_close = QPushButton()
            self.btn_close.setFixedSize(28, 28)
            self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_close.setIcon(ModernIconFactory.icon_close("#94a3b8"))
            self.btn_close.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: none;
                    border-radius: 14px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.15);
                }
            """)
            self.btn_close.clicked.connect(self.close)
            header_layout.addWidget(self.btn_close)

            layout.addLayout(header_layout)

            # Navigation buttons (to be added to bottom footer)
            self.btn_mode_pens = QPushButton()
            self.btn_mode_pens.setFixedSize(30, 30)
            self.btn_mode_pens.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_mode_pens.setIcon(ModernIconFactory.icon_pen_rack("#e2e8f0"))
            self.btn_mode_pens.setToolTip(LanguageManager.tr("tab_customize"))
            self.btn_mode_pens.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.btn_mode_pens.clicked.connect(lambda: self._set_active_tab(0))

            # Starred Pen Button: Toggles / opens the list of favorite pens and options
            self.btn_fav_list = QPushButton()
            self.btn_fav_list.setFixedSize(30, 30)
            self.btn_fav_list.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_fav_list.setIcon(ModernIconFactory.icon_pen_star(color="#cbd5e1", star_color="#facc15"))
            self.btn_fav_list.setToolTip(LanguageManager.tr("fav_pen_list_tip"))
            self.btn_fav_list.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.btn_fav_list.clicked.connect(self._toggle_favorites_tab)
            self.btn_mode_star = self.btn_fav_list  # Backward-compatible alias

            # Star Button: Directly adds or removes active settings to/from favorites
            self.btn_add_fav = QPushButton()
            self.btn_add_fav.setFixedSize(30, 30)
            self.btn_add_fav.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_add_fav.setIcon(ModernIconFactory.icon_star(filled=False, color="#94a3b8"))
            self.btn_add_fav.setToolTip(LanguageManager.tr("add_to_fav_tip"))
            self.btn_add_fav.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.btn_add_fav.clicked.connect(self._on_star_add_clicked)

            # Stacked widget for pages: Page 0 = Pen Setup, Page 1 = Favorites
            self.stack = QStackedWidget(self)

            # === PAGE 0: MAIN TOOL SETTINGS ===
            self.page_customize = QWidget()
            cust_layout = QVBoxLayout(self.page_customize)
            cust_layout.setContentsMargins(0, 0, 0, 0)
            cust_layout.setSpacing(10)

            # 1. Pen Rack Row
            pen_rack_box = QHBoxLayout()
            pen_rack_box.setContentsMargins(0, 4, 0, 2)
            pen_rack_box.setSpacing(4)

            if self.is_hl:
                pen_rack_box.addStretch()
                pen_types = [
                    ("highlighter", LanguageManager.tr("pen_highlighter")),
                    ("marker", LanguageManager.tr("pen_marker")),
                ]
                for p_type, p_label in pen_types:
                    item = PenRackItem(p_type, label=p_label, on_click=self._on_rack_pen_selected, parent=self.page_customize)
                    pen_rack_box.addWidget(item)
                    self.rack_items[p_type] = item
                pen_rack_box.addStretch()
            else:
                pen_types = [
                    ("calligraphy", LanguageManager.tr("pen_fountain")),
                    ("solid", LanguageManager.tr("pen_ballpoint")),
                    ("pencil", LanguageManager.tr("pen_pencil")),
                    ("brush", LanguageManager.tr("pen_brush")),
                ]
                for p_type, p_label in pen_types:
                    item = PenRackItem(p_type, label=p_label, on_click=self._on_rack_pen_selected, parent=self.page_customize)
                    pen_rack_box.addWidget(item)
                    self.rack_items[p_type] = item
            cust_layout.addLayout(pen_rack_box)

            # Subtle horizontal divider line
            self.div_line = QFrame()
            self.div_line.setFixedHeight(1)
            self.div_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
            cust_layout.addWidget(self.div_line)

            # 2. Thickness Control Row: [ - ] [ Value Slider with number in thumb ] [ + ]
            thick_row = QHBoxLayout()
            thick_row.setContentsMargins(0, 0, 0, 0)
            thick_row.setSpacing(8)

            btn_thick_minus = QPushButton()
            btn_thick_minus.setFixedSize(28, 28)
            btn_thick_minus.setIcon(ModernIconFactory.icon_minus("#cbd5e1"))
            btn_thick_minus.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thick_minus.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            btn_thick_minus.clicked.connect(lambda: self.slider_thick.setValue(max(self.slider_thick.minimum(), self.slider_thick.value() - 1)))
            thick_row.addWidget(btn_thick_minus)

            self.slider_thick = ModernValueSlider(Qt.Orientation.Horizontal, parent=self.page_customize)
            self.slider_thick.setRange(1, 50 if not self.is_hl else 70)
            self.slider_thick.setValue(self.thickness)
            self.slider_thick.valueChanged.connect(self._on_thick_change)
            thick_row.addWidget(self.slider_thick)

            btn_thick_plus = QPushButton()
            btn_thick_plus.setFixedSize(28, 28)
            btn_thick_plus.setIcon(ModernIconFactory.icon_plus("#cbd5e1"))
            btn_thick_plus.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thick_plus.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            btn_thick_plus.clicked.connect(lambda: self.slider_thick.setValue(min(self.slider_thick.maximum(), self.slider_thick.value() + 1)))
            thick_row.addWidget(btn_thick_plus)
            cust_layout.addLayout(thick_row)

            # 3. Paint Intensity / Opacity Control Row: [ - ] [ Opacity Slider with checkerboard & gradient ] [ + ]
            if self.has_opacity:
                opac_row = QHBoxLayout()
                opac_row.setContentsMargins(0, 0, 0, 0)
                opac_row.setSpacing(8)

                btn_opac_minus = QPushButton()
                btn_opac_minus.setFixedSize(28, 28)
                btn_opac_minus.setIcon(ModernIconFactory.icon_minus("#cbd5e1"))
                btn_opac_minus.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_opac_minus.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-radius: 14px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                    }
                """)
                btn_opac_minus.clicked.connect(lambda: self.slider_opac.setValue(max(self.slider_opac.minimum(), self.slider_opac.value() - 5)))
                opac_row.addWidget(btn_opac_minus)

                self.slider_opac = ModernOpacitySlider(Qt.Orientation.Horizontal, parent=self.page_customize)
                self.slider_opac.setRange(5, 100)
                self.slider_opac.setValue(self.opacity)
                self.slider_opac.set_active_color(self.color)
                self.slider_opac.valueChanged.connect(self._on_opac_change)
                opac_row.addWidget(self.slider_opac)

                btn_opac_plus = QPushButton()
                btn_opac_plus.setFixedSize(28, 28)
                btn_opac_plus.setIcon(ModernIconFactory.icon_plus("#cbd5e1"))
                btn_opac_plus.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_opac_plus.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-radius: 14px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                    }
                """)
                btn_opac_plus.clicked.connect(lambda: self.slider_opac.setValue(min(self.slider_opac.maximum(), self.slider_opac.value() + 5)))
                opac_row.addWidget(btn_opac_plus)
                cust_layout.addLayout(opac_row)

            # 4. Straighten lines (Çizgileri Düzleştir) Toggle Row
            snap_row = QHBoxLayout()
            snap_row.setContentsMargins(4, 4, 4, 2)
            snap_row.setSpacing(8)

            self.lbl_snap = QLabel(LanguageManager.tr("straighten_lines"))
            self.lbl_snap.setStyleSheet("font-size: 13px; color: #f1f5f9; font-weight: normal; border: none; background: transparent;")
            snap_row.addWidget(self.lbl_snap)
            snap_row.addStretch()

            self.switch_snap = ModernToggleSwitch(parent=self.page_customize)
            self.switch_snap.setChecked(self.snap_straight)
            self.switch_snap.toggled.connect(self._on_snap_toggled)
            self.chk_snap = self.switch_snap  # Compatibility alias for viewer sync
            snap_row.addWidget(self.switch_snap)
            cust_layout.addLayout(snap_row)

            # 5. Line Style Pills Row (Only for Pen)
            self.style_buttons = {}
            self.style_container = None
            if not self.is_hl:
                self.style_container = QWidget(parent=self.page_customize)
                style_row = QHBoxLayout(self.style_container)
                style_row.setContentsMargins(0, 0, 0, 0)
                style_row.setSpacing(6)
                line_style_defs = [
                    ("solid", LanguageManager.tr("pen_style_solid")),
                    ("calligraphy", LanguageManager.tr("pen_style_calligraphy")),
                    ("dash", LanguageManager.tr("pen_style_dash")),
                    ("dot", LanguageManager.tr("pen_style_dot")),
                    ("arrow", LanguageManager.tr("pen_style_arrow")),
                ]
                for st_key, st_label in line_style_defs:
                    pill = LineStylePill(st_key, label=st_label, on_click=self._set_line_style, parent=self.style_container)
                    pill.setChecked(st_key == self.line_style)
                    style_row.addWidget(pill)
                    self.style_buttons[st_key] = pill
                cust_layout.addWidget(self.style_container)
                self._update_line_styles_visibility()

            # 5. Color Swatches Row with Eyedropper & Palette buttons
            colors_row = QHBoxLayout()
            colors_row.setContentsMargins(0, 4, 0, 0)
            colors_row.setSpacing(6)

            # Both Pen and Highlighter use the same palette of fixed colors
            swatch_colors = ["#e60214", "#151515", "#7289FF", "#16C44B", "#EBDF00", "#ffffff", "#64748b"]

            self.swatch_widgets = []
            active_hex = self.color.name(QColor.NameFormat.HexRgb).lower()
            for hex_code in swatch_colors:
                sw = CircularColorSwatch(hex_code, on_click=self._on_swatch_clicked, parent=self.page_customize)
                sw.set_active(hex_code.lower() == active_hex)
                colors_row.addWidget(sw)
                self.swatch_widgets.append(sw)

            colors_row.addStretch()

            # Eyedropper / Screen picker button
            self.btn_eyedropper = QPushButton()
            self.btn_eyedropper.setFixedSize(26, 26)
            self.btn_eyedropper.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_eyedropper.setIcon(ModernIconFactory.icon_eyedropper("#cbd5e1"))
            self.btn_eyedropper.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 13px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.18);
                }
            """)
            self.btn_eyedropper.clicked.connect(self._open_eyedropper_picker)
            colors_row.addWidget(self.btn_eyedropper)

            # Palette grid button (open full color dialog)
            self.btn_palette = QPushButton()
            self.btn_palette.setFixedSize(26, 26)
            self.btn_palette.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_palette.setIcon(ModernIconFactory.icon_palette_grid())
            self.btn_palette.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 13px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            self.btn_palette.clicked.connect(self._open_palette_dialog)
            colors_row.addWidget(self.btn_palette)

            cust_layout.addLayout(colors_row)

            # Live Stroke Preview for instant feedback
            self.preview = StrokePreviewWidget(parent=self.page_customize, width=296, height=36)
            cust_layout.addWidget(self.preview)

            # === PAGE 1: FAVORITES / SAVED PENS ===
            self.page_favorites = QWidget()
            fav_layout = QVBoxLayout(self.page_favorites)
            fav_layout.setContentsMargins(0, 0, 0, 0)
            fav_layout.setSpacing(10)

            self.fav_scroll = QScrollArea()
            self.fav_scroll.setWidgetResizable(True)
            self.fav_scroll.setFixedHeight(275)
            self.fav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.fav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.fav_scroll.viewport().setStyleSheet("background: transparent; border: none;")
            self.fav_scroll.setStyleSheet("""
                QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
                    border: none;
                    background: transparent;
                }
                QScrollBar:vertical {
                    width: 5px;
                    background: transparent;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 2.5px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(255, 255, 255, 0.4);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            self.presets_container = QWidget()
            self.presets_container.setStyleSheet("background: transparent; border: none;")
            self.presets_container_layout = QVBoxLayout(self.presets_container)
            self.presets_container_layout.setContentsMargins(0, 0, 4, 0)
            self.presets_container_layout.setSpacing(6)
            self.fav_scroll.setWidget(self.presets_container)
            fav_layout.addWidget(self.fav_scroll)

            self.stack.addWidget(self.page_customize)
            self.stack.addWidget(self.page_favorites)
            layout.addWidget(self.stack)

            # --- BOTTOM FOOTER: Navigation & Favorites Buttons ---
            self.footer_div = QFrame()
            self.footer_div.setFixedHeight(1)
            self.footer_div.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
            layout.addWidget(self.footer_div)

            footer_layout = QHBoxLayout()
            footer_layout.setContentsMargins(0, 2, 0, 0)
            footer_layout.setSpacing(8)

            footer_layout.addWidget(self.btn_mode_pens)
            footer_layout.addWidget(self.btn_fav_list)
            footer_layout.addWidget(self.btn_add_fav)
            footer_layout.addStretch()
            layout.addLayout(footer_layout)

            self._rebuild_presets_list()
            self._update_pen_rack()
            self.update_preview()

        elif self.is_eraser:
            self.setFixedWidth(280)
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(0, 0, 0, 4)

            self.lbl_eraser_title = QLabel(LanguageManager.tr("panel_eraser"))
            self.lbl_eraser_title.setObjectName("EraserPanelTitle")
            self.lbl_eraser_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f5f9; border: none; background: transparent;")
            header_layout.addWidget(self.lbl_eraser_title)

            header_layout.addStretch()

            self.btn_close = QPushButton()
            self.btn_close.setFixedSize(26, 26)
            self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_close.setIcon(ModernIconFactory.icon_close("#94a3b8"))
            self.btn_close.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: none;
                    border-radius: 13px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.15);
                }
            """)
            self.btn_close.clicked.connect(self.close)
            header_layout.addWidget(self.btn_close)
            layout.addLayout(header_layout)

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

            thick_row = QHBoxLayout()
            thick_row.setSpacing(8)

            btn_thick_minus = QPushButton()
            btn_thick_minus.setFixedSize(28, 28)
            btn_thick_minus.setIcon(ModernIconFactory.icon_minus("#cbd5e1"))
            btn_thick_minus.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thick_minus.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 14px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); }")
            btn_thick_minus.clicked.connect(lambda: self.slider_thick.setValue(max(self.slider_thick.minimum(), self.slider_thick.value() - 2)))
            thick_row.addWidget(btn_thick_minus)

            self.slider_thick = ModernValueSlider(Qt.Orientation.Horizontal, parent=self)
            self.slider_thick.setRange(5, 70)
            self.slider_thick.setValue(self.thickness)
            self.slider_thick.valueChanged.connect(self._on_thick_change)
            thick_row.addWidget(self.slider_thick)

            btn_thick_plus = QPushButton()
            btn_thick_plus.setFixedSize(28, 28)
            btn_thick_plus.setIcon(ModernIconFactory.icon_plus("#cbd5e1"))
            btn_thick_plus.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_thick_plus.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 14px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); }")
            btn_thick_plus.clicked.connect(lambda: self.slider_thick.setValue(min(self.slider_thick.maximum(), self.slider_thick.value() + 2)))
            thick_row.addWidget(btn_thick_plus)
            layout.addLayout(thick_row)

            self.preview = StrokePreviewWidget(parent=self, width=248, height=36)
            layout.addWidget(self.preview)
            self.update_preview()

            self.btn_clear_all = QPushButton(LanguageManager.tr("clear_all_drawings"))
            self.btn_clear_all.setObjectName("ClearBtn")
            self.btn_clear_all.clicked.connect(self._on_clear_all_drawings)
            layout.addWidget(self.btn_clear_all)

        settings = QSettings("AuraPDF", "PDFViewer")
        current_th = settings.value("app_theme", "gray")
        if current_th == "navy":
            current_th = "gray"
        spec = POPUP_THEME_SPECS.get(current_th, POPUP_THEME_SPECS["gray"])
        self.apply_theme(current_th, spec)

    def apply_theme(self, theme_name: str = "gray", spec: dict = None):
        if theme_name == "navy":
            theme_name = "gray"
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("gray", {}))
        self.current_spec = spec
        self.current_theme = theme_name

        tb_bg = spec.get("tb_bg", "#212327")
        tb_border = spec.get("tb_border", "rgba(255, 255, 255, 0.09)")
        main_text = spec.get("main_text", "#f1f5f9")
        btn_hover = spec.get("btn_hover", "rgba(255, 255, 255, 0.1)")
        accent = spec.get("accent", "#38bdf8")
        tab_text = spec.get("tab_text", "#94a3b8")

        if hasattr(self, 'card_frame') and self.card_frame:
            self.card_frame.setStyleSheet(f"""
                QFrame#SleekCardFrame {{
                    background-color: {tb_bg};
                    border: 1px solid {tb_border};
                    border-radius: 18px;
                }}
                QToolTip {{
                    background-color: {tb_bg};
                    color: {main_text};
                    border: 1px solid {tb_border};
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                }}
            """)

        if hasattr(self, 'div_line') and self.div_line:
            self.div_line.setStyleSheet(f"background-color: {tb_border}; border: none;")

        if hasattr(self, 'lbl_snap') and self.lbl_snap:
            self.lbl_snap.setStyleSheet(f"font-size: 13px; color: {main_text}; font-weight: normal; border: none; background: transparent;")

        if hasattr(self, 'lbl_title') and self.lbl_title:
            self.lbl_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {main_text}; border: none; background: transparent;")

        if hasattr(self, 'lbl_eraser_title') and self.lbl_eraser_title:
            self.lbl_eraser_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {main_text}; border: none; background: transparent;")

        if hasattr(self, 'footer_div') and self.footer_div:
            self.footer_div.setStyleSheet(f"background-color: {tb_border}; border: none;")

        if hasattr(self, 'slider_thick') and hasattr(self.slider_thick, 'apply_theme'):
            self.slider_thick.apply_theme(theme_name, spec)

        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'apply_theme'):
            self.slider_opac.apply_theme(theme_name, spec)

        if hasattr(self, 'switch_snap') and hasattr(self.switch_snap, 'apply_theme'):
            self.switch_snap.apply_theme(theme_name, spec)

        for pill in getattr(self, 'style_buttons', {}).values():
            if hasattr(pill, 'apply_theme'):
                pill.apply_theme(theme_name, spec)

        for card in getattr(self, 'preset_cards', []):
            if hasattr(card, 'apply_theme'):
                card.apply_theme(theme_name, spec)

        if hasattr(self, 'btn_close') and self.btn_close:
            self.btn_close.setIcon(ModernIconFactory.icon_close(tab_text))

        if hasattr(self, 'btn_mode_pens') and self.btn_mode_pens:
            self.btn_mode_pens.setIcon(ModernIconFactory.icon_pen_rack(main_text))

        if getattr(self, 'is_eraser', False):
            segment_style = f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: {main_text};
                    border: 1px solid {tb_border};
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
                QPushButton:checked {{
                    background-color: {accent};
                    color: #ffffff;
                    border: 1px solid {accent};
                    font-weight: bold;
                }}
            """
            if hasattr(self, 'btn_mode_stroke') and self.btn_mode_stroke:
                self.btn_mode_stroke.setStyleSheet(segment_style)
            if hasattr(self, 'btn_mode_area') and self.btn_mode_area:
                self.btn_mode_area.setStyleSheet(segment_style)
            if hasattr(self, 'btn_clear_all') and self.btn_clear_all:
                self.btn_clear_all.setStyleSheet(f"""
                    QPushButton#ClearBtn {{
                        background-color: rgba(239, 68, 68, 0.12);
                        color: #f87171;
                        border: 1px solid rgba(239, 68, 68, 0.3);
                        border-radius: 8px;
                        padding: 7px 12px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                    QPushButton#ClearBtn:hover {{
                        background-color: #ef4444;
                        color: #ffffff;
                    }}
                """)

        curr_tab = self.stack.currentIndex() if hasattr(self, 'stack') else 0
        self._set_active_tab(curr_tab)
        self._update_star_btn_state()

    def _toggle_favorites_tab(self):
        if not hasattr(self, 'stack'):
            return
        new_idx = 1 if self.stack.currentIndex() == 0 else 0
        self._set_active_tab(new_idx)

    def _get_title_for_tab(self, idx: int) -> str:
        if idx == 1:
            return LanguageManager.tr("panel_fav_hl") if self.is_hl else LanguageManager.tr("panel_fav_pens")
        return LanguageManager.tr("panel_highlighter") if self.is_hl else LanguageManager.tr("panel_pen")

    def _set_active_tab(self, idx: int):
        if not hasattr(self, 'stack'):
            return
        if idx == 1 and getattr(self, '_presets_dirty', False):
            self._rebuild_presets_list()
            self._presets_dirty = False
        self.stack.setCurrentIndex(idx)
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setText(self._get_title_for_tab(idx))
        spec = getattr(self, 'current_spec', {})
        btn_hover = spec.get('btn_hover', 'rgba(255, 255, 255, 0.12)')
        accent = spec.get('accent', '#38bdf8')
        main_text = spec.get('main_text', '#e2e8f0')

        if hasattr(self, 'btn_mode_pens'):
            if idx == 0:
                self.btn_mode_pens.setStyleSheet(f"""
                    QPushButton {{
                        background: {btn_hover};
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 6px;
                        padding: 0px;
                    }}
                """)
            else:
                self.btn_mode_pens.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        border-radius: 6px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background: {btn_hover};
                    }}
                """)

        if hasattr(self, 'btn_fav_list'):
            if idx == 1:
                self.btn_fav_list.setStyleSheet(f"""
                    QPushButton {{
                        background: {btn_hover};
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 6px;
                        padding: 0px;
                    }}
                """)
                self.btn_fav_list.setIcon(ModernIconFactory.icon_pen_star(color=accent, star_color="#facc15"))
            else:
                self.btn_fav_list.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        border-radius: 6px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background: {btn_hover};
                    }}
                """)
                self.btn_fav_list.setIcon(ModernIconFactory.icon_pen_star(color=main_text, star_color="#facc15"))

        if idx == 1:
            self._update_preset_cards_active_state()

    def _on_star_add_clicked(self):
        matching = next((p for p in getattr(self, 'presets', []) if self._matches_active_settings(p)), None)
        if matching:
            self._delete_preset(matching.get("id"))
        else:
            self._save_current_as_preset()
        self._update_star_btn_state()

    def _update_star_btn_state(self):
        if not hasattr(self, 'btn_add_fav'):
            return
        is_fav = any(self._matches_active_settings(p) for p in getattr(self, 'presets', []))
        if is_fav:
            self.btn_add_fav.setIcon(ModernIconFactory.icon_star(filled=True, color="#facc15"))
            self.btn_add_fav.setToolTip(LanguageManager.tr("already_in_fav_tip"))
        else:
            spec = getattr(self, 'current_spec', {})
            col = spec.get('tab_text', '#94a3b8')
            self.btn_add_fav.setIcon(ModernIconFactory.icon_star(filled=False, color=col))
            self.btn_add_fav.setToolTip(LanguageManager.tr("add_to_fav_tip"))

    def _load_pen_settings(self) -> dict:
        defaults = {
            "calligraphy": {"thickness": 6, "opacity": 100, "line_style": "calligraphy", "color": "#151515"},
            "solid": {"thickness": 2, "opacity": 100, "line_style": "solid", "color": "#e60214"},
            "pencil": {"thickness": 3, "opacity": 100, "line_style": "pencil", "color": "#2c2c2e"},
            "brush": {"thickness": 8, "opacity": 100, "line_style": "brush", "color": "#7289FF"},
        }
        settings = QSettings("AuraPDF", "PDFViewer")
        raw = settings.value("pen_type_settings", None)
        if raw and isinstance(raw, str):
            try:
                data = json.loads(raw)
                for k, v in data.items():
                    if k in defaults and isinstance(v, dict):
                        defaults[k].update(v)
            except Exception:
                pass
        return defaults

    def _save_pen_settings(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        try:
            settings.setValue("pen_type_settings", json.dumps(self.pen_settings))
        except Exception:
            pass

    def _load_hl_settings(self) -> dict:
        defaults = {
            "highlighter": {"thickness": 18, "opacity": 40, "line_style": "solid", "color": "#EBDF00"},
            "marker": {"thickness": 12, "opacity": 60, "line_style": "marker", "color": "#16C44B"},
        }
        settings = QSettings("AuraPDF", "PDFViewer")
        raw = settings.value("hl_type_settings", None)
        if raw and isinstance(raw, str):
            try:
                data = json.loads(raw)
                for k, v in data.items():
                    if k in defaults and isinstance(v, dict):
                        defaults[k].update(v)
            except Exception:
                pass
        return defaults

    def _save_hl_settings(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        try:
            settings.setValue("hl_type_settings", json.dumps(self.hl_settings))
        except Exception:
            pass

    def _update_line_styles_visibility(self):
        if self.is_hl or not hasattr(self, 'style_container') or self.style_container is None:
            return

        p_type = getattr(self, 'current_pen_type', 'solid')

        # 1. Dolma kalem seçildiğinde çizgi stilleri seçeneği çıkmasın
        # 4. Fırça kalemde hiçbir stil çıkmasın
        if p_type in ("calligraphy", "brush"):
            self.style_container.setVisible(False)
            return

        # 2. Tükenmez kalem seçeneğinde ise de kaligrafi uç çıkmasın
        # 3. Kurşun kalemde ise kaligrafi çıkmasın
        self.style_container.setVisible(True)
        if "calligraphy" in self.style_buttons:
            self.style_buttons["calligraphy"].setVisible(False)
        if "solid" in self.style_buttons:
            self.style_buttons["solid"].setVisible(True)
        if "dash" in self.style_buttons:
            self.style_buttons["dash"].setVisible(True)
        if "dot" in self.style_buttons:
            self.style_buttons["dot"].setVisible(True)
        if "arrow" in self.style_buttons:
            self.style_buttons["arrow"].setVisible(True)

        active_key = "solid" if self.line_style in ("pencil", "solid") else self.line_style
        for k, btn in self.style_buttons.items():
            btn.setChecked(k == active_key)
            btn.update()

    def _on_rack_pen_selected(self, pen_type: str):
        if self.is_hl:
            self.hl_type = pen_type
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("active_hl_type", pen_type)
            cfg = self.hl_settings.get(pen_type, {})
            self.thickness = cfg.get("thickness", 18 if pen_type == "highlighter" else 12)
            self.opacity = cfg.get("opacity", 40 if pen_type == "highlighter" else 60)
            self.line_style = cfg.get("line_style", "solid" if pen_type == "highlighter" else "marker")
            saved_col = cfg.get("color", "#EBDF00" if pen_type == "highlighter" else "#16C44B")
            self.color = QColor(saved_col)
            self.color.setAlpha(int(self.opacity * 2.55))

            if hasattr(self, 'slider_thick'):
                self.slider_thick.blockSignals(True)
                self.slider_thick.setValue(self.thickness)
                self.slider_thick.blockSignals(False)
            if hasattr(self, 'slider_opac') and self.has_opacity:
                self.slider_opac.blockSignals(True)
                self.slider_opac.setValue(self.opacity)
                self.slider_opac.blockSignals(False)
                if hasattr(self.slider_opac, 'set_active_color'):
                    self.slider_opac.set_active_color(self.color)
            self._update_swatches_state()
            self._update_pen_rack()
            self.update_preview()
            self._update_star_btn_state()
            if self.on_change_callback:
                self.on_change_callback()
            return

        self.current_pen_type = pen_type
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("active_pen_type", pen_type)
        cfg = self.pen_settings.get(pen_type, {})
        default_thick = 6 if pen_type == "calligraphy" else (3 if pen_type == "pencil" else (8 if pen_type == "brush" else 2))
        self.thickness = cfg.get("thickness", default_thick)
        self.opacity = cfg.get("opacity", 100)
        saved_st = cfg.get("line_style", pen_type)
        saved_col = cfg.get("color", "#e60214")
        self.color = QColor(saved_col)
        self.color.setAlpha(int(self.opacity * 2.55) if self.has_opacity else 255)

        if pen_type == "calligraphy":
            self.line_style = "calligraphy"
        elif pen_type == "brush":
            self.line_style = "brush"
        elif pen_type == "pencil":
            self.line_style = saved_st if saved_st in ("pencil", "dash", "dot", "arrow") else "pencil"
        elif pen_type == "solid":
            self.line_style = saved_st if saved_st in ("solid", "dash", "dot", "arrow") else "solid"

        if hasattr(self, 'slider_thick'):
            self.slider_thick.blockSignals(True)
            self.slider_thick.setValue(self.thickness)
            self.slider_thick.blockSignals(False)
        if hasattr(self, 'slider_opac') and self.has_opacity:
            self.slider_opac.blockSignals(True)
            self.slider_opac.setValue(self.opacity)
            self.slider_opac.blockSignals(False)
            if hasattr(self.slider_opac, 'set_active_color'):
                self.slider_opac.set_active_color(self.color)

        self._update_swatches_state()
        self._update_line_styles_visibility()
        self._update_pen_rack()
        self.update_preview()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def _update_pen_rack(self):
        for p_type, item in getattr(self, 'rack_items', {}).items():
            is_active = False
            if self.is_hl:
                is_active = (p_type == getattr(self, 'hl_type', 'highlighter'))
            else:
                is_active = (p_type == getattr(self, 'current_pen_type', 'solid'))
            item.set_active(is_active, self.color)

    def _on_swatch_clicked(self, hex_val: str):
        alpha = int(self.opacity * 2.55) if self.has_opacity else 255
        self.color = QColor(hex_val)
        self.color.setAlpha(alpha)
        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["color"] = hex_val
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["color"] = hex_val
                self._save_pen_settings()
        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'set_active_color'):
            self.slider_opac.set_active_color(self.color)
        self._update_swatches_state()
        self._update_pen_rack()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def _update_swatches_state(self):
        active_hex = self.color.name(QColor.NameFormat.HexRgb).lower()
        for sw in getattr(self, 'swatch_widgets', []):
            sw.set_active(sw.color_hex.lower() == active_hex)

    def _open_eyedropper_picker(self):
        col = QColorDialog.getColor(self.color, self, LanguageManager.tr("color_label"))
        if col.isValid():
            self._on_swatch_clicked(col.name(QColor.NameFormat.HexRgb))

    def _open_palette_dialog(self):
        col = QColorDialog.getColor(self.color, self, LanguageManager.tr("color_label"))
        if col.isValid():
            self._on_swatch_clicked(col.name(QColor.NameFormat.HexRgb))

    def _load_presets_from_settings(self) -> list:
        settings = QSettings("AuraPDF", "PDFViewer")
        key = f"tool_presets_{self.tool_name}"
        raw = settings.value(key, None)
        if raw is not None and isinstance(raw, str) and raw.strip():
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [p for p in data if not str(p.get("id", "")).startswith("pen-default-") and not str(p.get("id", "")).startswith("hl-default-")]
            except Exception:
                pass
        return []

    def _save_presets_to_settings(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        key = f"tool_presets_{self.tool_name}"
        try:
            settings.setValue(key, json.dumps(self.presets))
        except Exception:
            pass

    def _save_current_as_preset(self):
        hex_col = self.color.name(QColor.NameFormat.HexRgb)
        st = getattr(self, 'line_style', 'solid')
        snap = getattr(self, 'snap_straight', False)

        already_saved = any(self._matches_active_settings(p) for p in getattr(self, 'presets', []))
        if not already_saved:
            new_preset = {
                "id": str(uuid.uuid4()),
                "color": hex_col,
                "thickness": self.thickness,
                "opacity": self.opacity if self.has_opacity else 100,
                "line_style": st,
                "snap_straight": snap,
            }
            self.presets.insert(0, new_preset)
            self._save_presets_to_settings()
            self._presets_dirty = True
            if hasattr(self, 'stack') and self.stack.currentIndex() == 1:
                self._rebuild_presets_list()
                self._presets_dirty = False

        self._show_preset_saved_feedback()
        self._update_star_btn_state()

    def _show_preset_saved_feedback(self):
        if hasattr(self, 'btn_add_fav'):
            self.btn_add_fav.setIcon(ModernIconFactory.icon_star(filled=True, color="#facc15"))

    def _delete_preset(self, preset_id: str):
        self.presets = [p for p in self.presets if p.get("id") != preset_id]
        self._save_presets_to_settings()
        self._presets_dirty = True
        if hasattr(self, 'stack') and self.stack.currentIndex() == 1:
            self._rebuild_presets_list()
            self._presets_dirty = False
        self._update_star_btn_state()

    def _apply_preset(self, preset: dict):
        hex_col = preset.get("color", "#000000")
        thick = int(preset.get("thickness", 3))
        opac = int(preset.get("opacity", 100))
        line_st = preset.get("line_style", "solid")
        snap = bool(preset.get("snap_straight", False))

        self.thickness = thick
        if hasattr(self, 'slider_thick'):
            self.slider_thick.blockSignals(True)
            self.slider_thick.setValue(thick)
            self.slider_thick.blockSignals(False)

        if self.has_opacity and hasattr(self, 'slider_opac'):
            self.opacity = opac
            self.slider_opac.blockSignals(True)
            self.slider_opac.setValue(opac)
            self.slider_opac.blockSignals(False)

        alpha = int(self.opacity * 2.55) if self.has_opacity else 255
        self.color = QColor(hex_col)
        self.color.setAlpha(alpha)

        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'set_active_color'):
            self.slider_opac.set_active_color(self.color)

        self._set_line_style(line_st)
        if not self.is_hl:
            if line_st == "calligraphy":
                self.current_pen_type = "calligraphy"
            elif line_st == "brush":
                self.current_pen_type = "brush"
            elif line_st == "pencil":
                self.current_pen_type = "pencil"
            elif line_st in ("solid", "dash", "dot", "arrow"):
                self.current_pen_type = "solid"
            self._update_line_styles_visibility()

        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["thickness"] = self.thickness
                self.hl_settings[self.hl_type]["opacity"] = self.opacity
                self.hl_settings[self.hl_type]["color"] = hex_col
                self.hl_settings[self.hl_type]["line_style"] = self.line_style
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["thickness"] = self.thickness
                self.pen_settings[self.current_pen_type]["opacity"] = self.opacity
                self.pen_settings[self.current_pen_type]["color"] = hex_col
                self.pen_settings[self.current_pen_type]["line_style"] = self.line_style
                self._save_pen_settings()

        if hasattr(self, 'switch_snap'):
            self.snap_straight = snap
            self.switch_snap.blockSignals(True)
            self.switch_snap.setChecked(snap)
            self.switch_snap.blockSignals(False)
            p = self.parent()
            if hasattr(p, 'sync_ruler_state'):
                p.sync_ruler_state()

        self._update_swatches_state()
        self._update_pen_rack()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()

        if self.on_change_callback:
            self.on_change_callback()

    def _matches_active_settings(self, preset: dict) -> bool:
        hex_col = self.color.name(QColor.NameFormat.HexRgb).lower()
        preset_col = str(preset.get("color", "")).lower()
        if hex_col != preset_col:
            return False
        if int(preset.get("thickness", -1)) != int(self.thickness):
            return False
        if self.has_opacity and int(preset.get("opacity", -1)) != int(self.opacity):
            return False
        if self.tool_name == "pen":
            if preset.get("line_style", "solid") != getattr(self, "line_style", "solid"):
                return False
        return True

    def _update_preset_cards_active_state(self):
        for card in getattr(self, 'preset_cards', []):
            card.update_active_state(self._matches_active_settings(card.preset))

    def _rebuild_presets_list(self):
        if not hasattr(self, 'presets_container_layout'):
            return

        while self.presets_container_layout.count():
            item = self.presets_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()

        self.preset_cards = []

        if not self.presets:
            empty_box = QWidget(parent=self.presets_container)
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(10, 30, 10, 30)
            empty_layout.setSpacing(6)

            spec = getattr(self, 'current_spec', {})
            text_col = spec.get('tab_text', '#94a3b8')

            lbl_empty = QLabel(LanguageManager.tr("no_presets_yet"), parent=empty_box)
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {text_col};")
            empty_layout.addWidget(lbl_empty)

            lbl_hint = QLabel(LanguageManager.tr("no_presets_hint"), parent=empty_box)
            lbl_hint.setWordWrap(True)
            lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_hint.setStyleSheet(f"font-size: 11px; color: {text_col};")
            empty_layout.addWidget(lbl_hint)

            self.presets_container_layout.addWidget(empty_box)
            return

        for p in self.presets:
            is_active = self._matches_active_settings(p)
            card = ToolPresetCard(
                preset=p,
                is_hl=self.is_hl,
                is_active=is_active,
                on_select=self._apply_preset,
                on_delete=self._delete_preset,
                parent=self.presets_container,
                spec=getattr(self, 'current_spec', None)
            )
            self.presets_container_layout.addWidget(card)
            self.preset_cards.append(card)

        self.presets_container_layout.addStretch()

    def _on_clear_all_drawings(self):
        self.close()
        p = self.parent()
        if hasattr(p, 'clear_all_drawings'):
            p.clear_all_drawings()

    def retranslate_ui(self):
        if hasattr(self, 'lbl_title') and hasattr(self, 'stack'):
            self.lbl_title.setText(self._get_title_for_tab(self.stack.currentIndex()))
        if hasattr(self, 'lbl_eraser_title'):
            self.lbl_eraser_title.setText(LanguageManager.tr("panel_eraser"))
        if hasattr(self, 'btn_fav_save_current'):
            self.btn_fav_save_current.setText(LanguageManager.tr("save_preset_btn"))
        if hasattr(self, 'lbl_fav_title'):
            self.lbl_fav_title.setText(LanguageManager.tr("tab_favorites"))
        if hasattr(self, 'btn_fav_list'):
            self.btn_fav_list.setToolTip(LanguageManager.tr("fav_pen_list_tip"))
        if hasattr(self, 'btn_mode_pens'):
            self.btn_mode_pens.setToolTip(LanguageManager.tr("tab_customize"))
        if hasattr(self, 'lbl_snap'):
            self.lbl_snap.setText(LanguageManager.tr("straighten_lines"))
        if hasattr(self, 'btn_mode_stroke'):
            self.btn_mode_stroke.setText(LanguageManager.tr("eraser_stroke"))
        if hasattr(self, 'btn_mode_area'):
            self.btn_mode_area.setText(LanguageManager.tr("eraser_area"))
        if hasattr(self, 'btn_clear_all'):
            self.btn_clear_all.setText(LanguageManager.tr("clear_all_drawings"))
        if hasattr(self, 'presets_container'):
            self._rebuild_presets_list()
        self._update_star_btn_state()

    def _set_eraser_mode(self, mode):
        self.eraser_mode = mode
        self.btn_mode_stroke.setChecked(mode == "stroke")
        self.btn_mode_area.setChecked(mode == "area")
        self.update_preview()
        if self.on_change_callback:
            self.on_change_callback()

    def _set_line_style(self, style_key):
        if getattr(self, 'current_pen_type', 'solid') == "pencil":
            self.line_style = "pencil" if style_key == "solid" else style_key
        else:
            self.line_style = style_key

        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["line_style"] = self.line_style
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings'):
                p_type = getattr(self, 'current_pen_type', 'solid')
                if p_type not in self.pen_settings:
                    self.pen_settings[p_type] = {}
                self.pen_settings[p_type]["line_style"] = self.line_style
                self._save_pen_settings()

        active_key = "solid" if self.line_style in ("pencil", "solid") else self.line_style
        for k, btn in getattr(self, 'style_buttons', {}).items():
            btn.setChecked(k == active_key)
            btn.update()
        self._update_pen_rack()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_snap_toggled(self, checked):
        self.snap_straight = checked
        p = self.parent()
        if hasattr(p, 'sync_ruler_state'):
            p.sync_ruler_state()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()

    def set_thickness(self, new_val):
        self.thickness = max(1, min(int(new_val), 70))
        if hasattr(self, 'slider_thick'):
            self.slider_thick.blockSignals(True)
            self.slider_thick.setValue(self.thickness)
            self.slider_thick.blockSignals(False)
        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["thickness"] = self.thickness
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["thickness"] = self.thickness
                self._save_pen_settings()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_thick_change(self, val):
        self.thickness = val
        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["thickness"] = val
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["thickness"] = val
                self._save_pen_settings()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def _on_opac_change(self, val):
        self.opacity = val
        self.color.setAlpha(int(val * 2.55))
        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["opacity"] = val
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["opacity"] = val
                self._save_pen_settings()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def set_quick_color(self, hex_code):
        alpha = int(self.opacity * 2.55) if self.has_opacity else 255
        self.color = QColor(hex_code)
        self.color.setAlpha(alpha)
        if self.is_hl:
            if hasattr(self, 'hl_settings') and hasattr(self, 'hl_type'):
                if self.hl_type not in self.hl_settings:
                    self.hl_settings[self.hl_type] = {}
                self.hl_settings[self.hl_type]["color"] = hex_code
                self._save_hl_settings()
        else:
            if hasattr(self, 'pen_settings') and hasattr(self, 'current_pen_type'):
                if self.current_pen_type not in self.pen_settings:
                    self.pen_settings[self.current_pen_type] = {}
                self.pen_settings[self.current_pen_type]["color"] = hex_code
                self._save_pen_settings()
        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'set_active_color'):
            self.slider_opac.set_active_color(self.color)
        self._update_swatches_state()
        self._update_pen_rack()
        self.update_preview()
        self._update_preset_cards_active_state()
        self._update_star_btn_state()
        if self.on_change_callback:
            self.on_change_callback()

    def choose_custom_color(self):
        self._open_palette_dialog()

    def update_preview(self):
        p_type = getattr(self, 'current_pen_type', 'solid') if not self.is_hl else 'highlighter'
        self.preview.update_style(
            self.color, self.thickness, self.is_eraser, self.eraser_mode, 
            getattr(self, 'line_style', 'solid'), is_hl=self.is_hl, pen_type=p_type
        )

    def show_below(self, button_widget):
        self._anchor_widget = button_widget
        point = button_widget.mapToGlobal(QPoint(0, button_widget.height() + 4))
        self.move(point)
        if hasattr(self, 'switch_snap'):
            self.switch_snap.blockSignals(True)
            self.switch_snap.setChecked(self.snap_straight)
            self.switch_snap.blockSignals(False)
        self._update_swatches_state()
        self._update_pen_rack()
        self._update_line_styles_visibility()
        self.update_preview()
        self._update_preset_cards_active_state()
        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'set_active_color'):
            self.slider_opac.set_active_color(self.color)
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.instance().installEventFilter(self)

    def show_at(self, global_pos: QPoint):
        self._anchor_widget = None
        if hasattr(self, 'switch_snap'):
            self.switch_snap.blockSignals(True)
            self.switch_snap.setChecked(self.snap_straight)
            self.switch_snap.blockSignals(False)
        self._update_swatches_state()
        self._update_pen_rack()
        self._update_line_styles_visibility()
        self.update_preview()
        self._update_preset_cards_active_state()
        if hasattr(self, 'slider_opac') and hasattr(self.slider_opac, 'set_active_color'):
            self.slider_opac.set_active_color(self.color)
        super().show_at(global_pos)
        self.raise_()
        self.activateWindow()
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.NonClientAreaMouseButtonPress):
            if isinstance(obj, QWidget) and (self.isAncestorOf(obj) or obj == self):
                return False
            if QApplication.activeModalWidget() is not None:
                return False
            if hasattr(event, 'globalPosition'):
                click_pos = event.globalPosition().toPoint()
            elif hasattr(event, 'globalPos'):
                click_pos = event.globalPos()
            else:
                from PyQt6.QtGui import QCursor
                click_pos = QCursor.pos()
            if self.frameGeometry().contains(click_pos):
                return False
            if getattr(self, '_anchor_widget', None) and self._anchor_widget.isVisible():
                btn_topleft = self._anchor_widget.mapToGlobal(QPoint(0, 0))
                btn_rect = QRect(btn_topleft, self._anchor_widget.size())
                if btn_rect.contains(click_pos):
                    return False
            self.close()
            return False
        return super().eventFilter(obj, event)


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
        current_th = settings.value("app_theme", "gray")
        if current_th == "navy":
            current_th = "gray"
        self.apply_theme(current_th)

    def apply_theme(self, theme_name: str, spec: dict = None):
        if theme_name == "navy":
            theme_name = "gray"
        if not spec:
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("gray", {}))
        if spec:
            tb_bg = QColor(spec.get('tb_bg', '#1c1c1c'))
            self.bg_color = QColor(tb_bg.red(), tb_bg.green(), tb_bg.blue(), 230)
            self.border_color = QColor(spec.get('tb_border', '#404040'))
            self.text_color = QColor(spec.get('main_text', '#e0e0e0'))
            self.update()

    def show_preview(self, pos, color, thickness, is_eraser=False, eraser_mode="stroke", line_style="solid", pen_type="solid"):
        self.color = color
        self.thickness = thickness
        self.is_eraser = is_eraser
        self.line_style = line_style
        self.pen_type = pen_type
        self.move(int(pos.x()) + 20, int(pos.y()) - 35)
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
            elif line_st == "brush":
                cap = Qt.PenCapStyle.RoundCap
                join = Qt.PenJoinStyle.RoundJoin

            is_pencil = (getattr(self, 'pen_type', 'solid') == "pencil" or line_st == "pencil")
            if is_pencil:
                thick_val = float(min(self.thickness, 26))
                base_c = QColor(self.color)
                tex = get_graphite_lead_texture(base_c)
                tex_fringe = get_graphite_fringe_texture(base_c)

                if line_st == "arrow":
                    arrow_len = max(8.0, min(16.0, thick_val * 2.0 + 4.0))
                    p_arrow = QPainterPath()
                    p_arrow.moveTo(QPointF(20.0, mid_y))
                    p_arrow.lineTo(QPointF(self.width() - 20.0, mid_y))
                    p_arrow.moveTo(QPointF(self.width() - 20.0 - arrow_len, mid_y - arrow_len * 0.55))
                    p_arrow.lineTo(QPointF(self.width() - 20.0, mid_y))
                    p_arrow.lineTo(QPointF(self.width() - 20.0 - arrow_len, mid_y + arrow_len * 0.55))

                    pen_fringe = QPen(QBrush(tex_fringe), thick_val * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_arrow, pen_fringe)

                    pen_lead = QPen(QBrush(tex), thick_val, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_arrow, pen_lead)
                elif line_st in ("dash", "dot", "dashdot"):
                    p_line = QPainterPath()
                    p_line.moveTo(QPointF(20.0, mid_y))
                    p_line.lineTo(QPointF(self.width() - 20.0, mid_y))
                    pen_tex = QPen(QBrush(tex), thick_val, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    if line_st == "dash":
                        pen_tex.setDashPattern([2.2, 1.5])
                    elif line_st == "dot":
                        pen_tex.setDashPattern([0.01, 1.9])
                    elif line_st == "dashdot":
                        pen_tex.setDashPattern([2.2, 1.4, 0.01, 1.4])
                    p.strokePath(p_line, pen_tex)
                else:
                    pencil_pts = [QPointF(20.0, mid_y), QPointF(self.width() - 20.0, mid_y)]
                    p_base = QPainterPath()
                    p_base.moveTo(pencil_pts[0])
                    p_base.lineTo(pencil_pts[1])

                    pen_fringe = QPen(QBrush(tex_fringe), thick_val * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_base, pen_fringe)

                    pen_lead = QPen(QBrush(tex), thick_val, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_base, pen_lead)

                    pen_core = QPen(QBrush(tex), max(0.6, thick_val * 0.58), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    p.strokePath(p_base, pen_core)
            else:
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

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.btn_mode_single = QPushButton(LanguageManager.tr("pointer_mode_single"))
        self.btn_mode_single.setCheckable(True)
        self.btn_mode_single.setChecked(True)
        self.btn_mode_single.clicked.connect(lambda: self._set_mode("single"))
        self.mode_group.addButton(self.btn_mode_single, 0)

        self.btn_mode_rainbow = QPushButton(LanguageManager.tr("pointer_mode_rainbow"))
        self.btn_mode_rainbow.setCheckable(True)
        self.btn_mode_rainbow.clicked.connect(lambda: self._set_mode("rainbow"))
        self.mode_group.addButton(self.btn_mode_rainbow, 1)

        h_mode.addWidget(self.btn_mode_single)
        h_mode.addWidget(self.btn_mode_rainbow)
        layout.addLayout(h_mode)

        # 2. Hızlı Renkler & Özel Renk (Tek Renk modu için)
        self.color_container = QWidget()
        self.color_container.setStyleSheet("background: transparent; border: none;")
        v_col = QVBoxLayout(self.color_container)
        v_col.setContentsMargins(0, 0, 0, 0)
        v_col.setSpacing(6)

        default_pal = ["#e60214", "#151515", "#7289FF", "#16C44B", "#EBDF00", "#ffffff", "#64748b"]
        self.palette_widget = ModernColorPaletteWidget(
            tool_name=self.tool_name,
            default_palette=default_pal,
            default_custom="#e60214",
            default_active="#e60214",
            on_color_changed=self._on_palette_color_changed,
            parent=self.color_container
        )
        v_col.addWidget(self.palette_widget)
        layout.addWidget(self.color_container)

        self.color = QColor(self.palette_widget.active_color)
        self._update_mode_buttons_style()

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

    def _update_mode_buttons_style(self):
        if not hasattr(self, 'btn_mode_single') or not hasattr(self, 'btn_mode_rainbow'):
            return
        accent_col = "#0284c7"
        active_style = f"""
            QPushButton {{
                background-color: {accent_col};
                color: #ffffff;
                border: 1px solid {accent_col};
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
                font-size: 11px;
            }}
        """
        inactive_style = """
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 500;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }}
        """
        mode = getattr(self, 'mode', 'single')
        if mode == "single":
            self.btn_mode_single.setStyleSheet(active_style)
            self.btn_mode_rainbow.setStyleSheet(inactive_style)
        else:
            self.btn_mode_single.setStyleSheet(inactive_style)
            self.btn_mode_rainbow.setStyleSheet(active_style)

    def apply_theme(self, theme_name: str, spec: dict = None):
        super().apply_theme(theme_name, spec)
        self._update_mode_buttons_style()

    def _on_palette_color_changed(self, col):
        self.color = col
        if self.on_change_callback:
            self.on_change_callback()

    def _set_mode(self, mode):
        self.mode = mode
        self.btn_mode_single.blockSignals(True)
        self.btn_mode_rainbow.blockSignals(True)
        self.btn_mode_single.setChecked(mode == "single")
        self.btn_mode_rainbow.setChecked(mode == "rainbow")
        self.btn_mode_single.blockSignals(False)
        self.btn_mode_rainbow.blockSignals(False)
        self._update_mode_buttons_style()

        self.color_container.setVisible(mode == "single")
        self.adjustSize()
        if self.on_change_callback:
            self.on_change_callback()
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


class PDFTextSelectionHUD(QFrame):
    """
    Kullanıcı PDF sayfasındaki metinleri seçtiğinde beliren,
    seçili metni kopyalama, vurgulama, altını çizme, üstünü çizme,
    arama, çeviri ve seslendirme işlemlerini sunan modern floating HUD.
    """
    def __init__(self, parent=None, tab_doc=None):
        super().__init__(parent)
        self.tab_doc = tab_doc
        self.setObjectName("PDFTextSelectionHUD")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)

        self.setStyleSheet("""
            #PDFTextSelectionHUD {
                background-color: rgba(28, 28, 32, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
            }
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 4px 6px;
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
                color: #38bdf8;
            }
            QPushButton:pressed {
                background: rgba(2, 132, 199, 0.3);
            }
            QFrame#Separator {
                background: rgba(255, 255, 255, 0.12);
                width: 1px;
                max-width: 1px;
                margin: 4px 2px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        # 1. Kopyala
        self.btn_copy = QPushButton("📋 " + LanguageManager.tr("copy") if hasattr(LanguageManager, 'tr') else "📋 Kopyala")
        self.btn_copy.setToolTip(LanguageManager.tr("text_copied_to_clipboard") + " (Ctrl+C)")
        self.btn_copy.clicked.connect(self._on_copy)
        layout.addWidget(self.btn_copy)

        sep1 = QFrame()
        sep1.setObjectName("Separator")
        layout.addWidget(sep1)

        # 2. Vurgula (Highlight)
        self.btn_hl = QPushButton("🟡 " + LanguageManager.tr("text_markup_highlight"))
        self.btn_hl.setToolTip(LanguageManager.tr("text_markup_highlight"))
        self.btn_hl.clicked.connect(self._on_highlight)
        layout.addWidget(self.btn_hl)

        # 3. Altı Çizili (Underline)
        self.btn_ul = QPushButton("✍️ " + LanguageManager.tr("text_markup_underline"))
        self.btn_ul.setToolTip(LanguageManager.tr("text_markup_underline"))
        self.btn_ul.clicked.connect(self._on_underline)
        layout.addWidget(self.btn_ul)

        # 4. Üstü Çizili (Strikeout)
        self.btn_so = QPushButton("<s> " + LanguageManager.tr("text_markup_strikeout"))
        self.btn_so.setToolTip(LanguageManager.tr("text_markup_strikeout"))
        self.btn_so.clicked.connect(self._on_strikeout)
        layout.addWidget(self.btn_so)

        sep2 = QFrame()
        sep2.setObjectName("Separator")
        layout.addWidget(sep2)

        # 5. Web'de Ara
        self.btn_search = QPushButton("🔍 " + LanguageManager.tr("text_search_google"))
        self.btn_search.setToolTip(LanguageManager.tr("text_search_google"))
        self.btn_search.clicked.connect(self._on_search)
        layout.addWidget(self.btn_search)

        # 6. Çevir
        self.btn_translate = QPushButton("🌐 " + LanguageManager.tr("text_translate_google"))
        self.btn_translate.setToolTip(LanguageManager.tr("text_translate_google"))
        self.btn_translate.clicked.connect(self._on_translate)
        layout.addWidget(self.btn_translate)

    def _on_copy(self):
        if self.tab_doc and hasattr(self.tab_doc, 'copy_selected_text'):
            self.tab_doc.copy_selected_text()
        self.hide()

    def _on_highlight(self):
        if self.tab_doc and hasattr(self.tab_doc, 'highlight_selected_text'):
            self.tab_doc.highlight_selected_text()
        self.hide()

    def _on_underline(self):
        if self.tab_doc and hasattr(self.tab_doc, 'underline_selected_text'):
            self.tab_doc.underline_selected_text()
        self.hide()

    def _on_strikeout(self):
        if self.tab_doc and hasattr(self.tab_doc, 'strikeout_selected_text'):
            self.tab_doc.strikeout_selected_text()
        self.hide()

    def _on_search(self):
        if self.tab_doc and hasattr(self.tab_doc, 'search_selected_text'):
            self.tab_doc.search_selected_text()
        self.hide()

    def _on_translate(self):
        if self.tab_doc and hasattr(self.tab_doc, 'translate_selected_text'):
            self.tab_doc.translate_selected_text()
        self.hide()

    def show_at_pos(self, viewport_pos: QPoint):
        self.adjustSize()
        x = viewport_pos.x() - self.width() // 2
        y = viewport_pos.y() - self.height() - 10
        # Clamp to viewport bounds
        if self.parent():
            x = max(10, min(x, self.parent().width() - self.width() - 10))
            if y < 10:
                y = viewport_pos.y() + 25
        self.move(x, y)
        self.show()
        self.raise_()


class ModernStampPalettePopup(BaseSettingsPopup):
    """
    Hızlı ve modern açılır damga paleti (Acrobat Pro & modern PDF okuyucu tarzı).
    Ayrı modal diyalog penceresi açmadan, doğrudan palet içerisindeki sekmelerden
    hem hazır damgaları hem de canlı önizlemeli özel damgaları oluşturmayı sağlar.
    """
    def __init__(self, parent=None, on_stamp_selected=None, on_open_custom_dialog=None):
        self.on_stamp_selected = on_stamp_selected
        self.on_open_custom_dialog = on_open_custom_dialog
        self._preset_btns = []
        self._custom_color = "#16a34a"
        self._color_chip_btns = []
        super().__init__(parent)
        self.setObjectName("ModernStampPalettePopup")
        self.setFixedWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1. Başlık ve Sekme Değiştirici
        h_head = QHBoxLayout()
        h_head.setContentsMargins(0, 0, 0, 0)
        h_head.setSpacing(8)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_stamp("#38bdf8").pixmap(16, 16))
        h_head.addWidget(lbl_icon)

        self.lbl_head_title = QLabel(LanguageManager.tr("stamp_quick_palette_title"))
        self.lbl_head_title.setObjectName("SectionHeader")
        self.lbl_head_title.setStyleSheet("font-size: 13px; font-weight: 700;")
        h_head.addWidget(self.lbl_head_title)
        h_head.addStretch(1)

        layout.addLayout(h_head)

        # 2. Modern Segmented Tab Switcher (Hazır Damgalar / Özel Damga)
        h_tabs = QHBoxLayout()
        h_tabs.setSpacing(4)
        h_tabs.setContentsMargins(0, 2, 0, 4)

        self.btn_tab_preset = QPushButton(LanguageManager.tr("stamp_tab_preset"))
        self.btn_tab_preset.setCheckable(True)
        self.btn_tab_preset.setChecked(True)
        self.btn_tab_preset.setFixedHeight(28)
        self.btn_tab_preset.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_custom = QPushButton(LanguageManager.tr("stamp_tab_custom"))
        self.btn_tab_custom.setCheckable(True)
        self.btn_tab_custom.setChecked(False)
        self.btn_tab_custom.setFixedHeight(28)
        self.btn_tab_custom.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_group.addButton(self.btn_tab_preset, 0)
        self._tab_group.addButton(self.btn_tab_custom, 1)
        self._tab_group.idClicked.connect(self._on_tab_switched)

        self._style_tabs()
        h_tabs.addWidget(self.btn_tab_preset)
        h_tabs.addWidget(self.btn_tab_custom)
        layout.addLayout(h_tabs)

        # 3. Yığın Alanı (QStackedWidget)
        self.stack = QStackedWidget(self)

        # --- SAYFA 0: HAZIR DAMGALAR ---
        page_preset = QWidget()
        l_preset = QVBoxLayout(page_preset)
        l_preset.setContentsMargins(0, 0, 0, 0)
        l_preset.setSpacing(8)

        self.lbl_std_sec = QLabel(LanguageManager.tr("stamp_cat_standard"))
        self.lbl_std_sec.setObjectName("FieldLabel")
        self.lbl_std_sec.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.85;")
        l_preset.addWidget(self.lbl_std_sec)

        grid_stamps = QGridLayout()
        grid_stamps.setHorizontalSpacing(8)
        grid_stamps.setVerticalSpacing(8)

        self.presets = [
            ("stamp_approved", "#16a34a"),      # ONAYLANDI / APPROVED
            ("stamp_confidential", "#dc2626"),  # GİZLİ / CONFIDENTIAL
            ("stamp_draft", "#2563eb"),         # TASLAK / DRAFT
            ("stamp_final", "#7c3aed"),         # NİHAİ / FINAL
            ("stamp_void", "#b91c1c"),          # İPTAL EDİLDİ / VOID
            ("stamp_completed", "#0d9488"),     # TAMAMLANDI / COMPLETED
            ("stamp_sign_here", "#d97706"),     # BURAYI İMZALAYIN / SIGN HERE
            ("stamp_urgent", "#ea580c"),        # ACİL / URGENT
        ]

        self._preset_btns.clear()
        for idx, (key, col_hex) in enumerate(self.presets):
            btn = QPushButton(LanguageManager.tr(key).upper())
            btn.setObjectName("StampPresetBtn")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton#StampPresetBtn {{
                    background-color: {col_hex}18;
                    color: {col_hex};
                    border: 1.5px solid {col_hex}80;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 800;
                    text-align: center;
                    padding: 4px 6px;
                }}
                QPushButton#StampPresetBtn:hover {{
                    background-color: {col_hex}35;
                    border: 1.5px solid {col_hex};
                    color: #ffffff;
                }}
            """)
            btn.clicked.connect(lambda _, k=key, c=col_hex: self._on_preset_clicked(k, c, False))
            self._preset_btns.append((btn, key, col_hex))
            grid_stamps.addWidget(btn, idx // 2, idx % 2)

        l_preset.addLayout(grid_stamps)

        sep = QFrame()
        sep.setObjectName("Divider")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); max-height: 1px;")
        l_preset.addWidget(sep)

        self.lbl_dyn_sec = QLabel(LanguageManager.tr("stamp_cat_dynamic"))
        self.lbl_dyn_sec.setObjectName("FieldLabel")
        self.lbl_dyn_sec.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.85;")
        l_preset.addWidget(self.lbl_dyn_sec)

        h_dyn = QHBoxLayout()
        h_dyn.setSpacing(8)

        self.btn_dyn_approved = QPushButton(f"{LanguageManager.tr('stamp_approved').upper()}")
        self.btn_dyn_approved.setObjectName("StampDynamicBtn")
        self.btn_dyn_approved.setIcon(ModernIconFactory.icon_stamp("#22c55e"))
        self.btn_dyn_approved.setFixedHeight(30)
        self.btn_dyn_approved.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dyn_approved.setStyleSheet("""
            QPushButton#StampDynamicBtn {
                background-color: rgba(22, 163, 74, 0.12);
                color: #22c55e;
                border: 1px dashed #22c55e;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 700;
                padding: 4px;
                text-align: center;
            }
            QPushButton#StampDynamicBtn:hover {
                background-color: rgba(22, 163, 74, 0.25);
                color: #ffffff;
            }
        """)
        self.btn_dyn_approved.clicked.connect(lambda: self._on_preset_clicked("stamp_approved", "#16a34a", True))
        h_dyn.addWidget(self.btn_dyn_approved)

        import datetime
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")
        self.btn_date_today = QPushButton(f"{LanguageManager.tr('date_stamp')}: {today_str}")
        self.btn_date_today.setObjectName("StampDateBtn")
        self.btn_date_today.setIcon(ModernIconFactory.icon_page_number())
        self.btn_date_today.setFixedHeight(30)
        self.btn_date_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_date_today.setStyleSheet("""
            QPushButton#StampDateBtn {
                background-color: rgba(56, 189, 248, 0.12);
                color: #38bdf8;
                border: 1px dashed #38bdf8;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 700;
                padding: 4px;
                text-align: center;
            }
            QPushButton#StampDateBtn:hover {
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
            }
        """)
        self.btn_date_today.clicked.connect(self._on_date_stamp_clicked)
        h_dyn.addWidget(self.btn_date_today)

        l_preset.addLayout(h_dyn)
        self.stack.addWidget(page_preset)

        # --- SAYFA 1: ÖZEL DAMGA OLUŞTURUCU (PENCERESİZ İÇERİK) ---
        page_custom = QWidget()
        l_custom = QVBoxLayout(page_custom)
        l_custom.setContentsMargins(0, 0, 0, 0)
        l_custom.setSpacing(8)

        lbl_custom_txt = QLabel(LanguageManager.tr("stamp_custom_text_label"))
        lbl_custom_txt.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.9;")
        l_custom.addWidget(lbl_custom_txt)

        self.txt_custom = QLineEdit()
        self.txt_custom.setText(LanguageManager.tr("stamp_approved"))
        self.txt_custom.setFixedHeight(30)
        self.txt_custom.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 5px;
                padding: 0 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit:focus {
                border: 1.5px solid #38bdf8;
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.txt_custom.textChanged.connect(self._update_custom_preview)
        l_custom.addWidget(self.txt_custom)

        lbl_col = QLabel(LanguageManager.tr("stamp_custom_color_label"))
        lbl_col.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.9;")
        l_custom.addWidget(lbl_col)

        h_chips = QHBoxLayout()
        h_chips.setSpacing(6)
        color_choices = [
            ("#16a34a", "Yeşil"),
            ("#dc2626", "Kırmızı"),
            ("#2563eb", "Mavi"),
            ("#7c3aed", "Mor"),
            ("#ea580c", "Turuncu"),
            ("#0d9488", "Teal"),
            ("#0f172a", "Lacivert / Koyu"),
        ]
        self._color_chip_btns.clear()
        for col_hex, _ in color_choices:
            btn_chip = QPushButton()
            btn_chip.setFixedSize(24, 24)
            btn_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_chip.clicked.connect(lambda _, ch=col_hex: self._select_custom_color(ch))
            self._color_chip_btns.append((btn_chip, col_hex))
            h_chips.addWidget(btn_chip)
        h_chips.addStretch(1)
        l_custom.addLayout(h_chips)
        self._refresh_color_chip_styles()

        self.chk_custom_dynamic = QCheckBox(LanguageManager.tr("stamp_dynamic_toggle"))
        self.chk_custom_dynamic.setStyleSheet("font-size: 11px;")
        self.chk_custom_dynamic.toggled.connect(self._update_custom_preview)
        l_custom.addWidget(self.chk_custom_dynamic)

        lbl_prev = QLabel(LanguageManager.tr("stamp_custom_preview"))
        lbl_prev.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.9;")
        l_custom.addWidget(lbl_prev)

        # 1:1 Belge beyazı kağıt simülasyonu (Böylece seçilen renk belgede birebir aynı görünür)
        self.preview_frame = QFrame()
        self.preview_frame.setFixedHeight(82)
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.16);
                border-radius: 6px;
            }
        """)
        l_pf = QVBoxLayout(self.preview_frame)
        l_pf.setContentsMargins(4, 4, 4, 4)
        l_pf.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_custom_preview = QLabel()
        self.lbl_custom_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_pf.addWidget(self.lbl_custom_preview)
        l_custom.addWidget(self.preview_frame)

        self.btn_apply_custom = QPushButton(LanguageManager.tr("stamp_apply_btn"))
        self.btn_apply_custom.setObjectName("PrimaryBtn")
        self.btn_apply_custom.setFixedHeight(32)
        self.btn_apply_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_custom.setStyleSheet("""
            QPushButton#PrimaryBtn {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_apply_custom.clicked.connect(self._apply_custom_stamp)
        l_custom.addWidget(self.btn_apply_custom)

        self.stack.addWidget(page_custom)
        layout.addWidget(self.stack)

        self._update_custom_preview()

    def _style_tabs(self):
        active_style = """
            background-color: rgba(56, 189, 248, 0.22);
            color: #38bdf8;
            border: 1px solid #38bdf8;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 10px;
        """
        inactive_style = """
            background-color: rgba(255, 255, 255, 0.05);
            color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 10px;
        """
        self.btn_tab_preset.setStyleSheet(active_style if self.btn_tab_preset.isChecked() else inactive_style)
        self.btn_tab_custom.setStyleSheet(active_style if self.btn_tab_custom.isChecked() else inactive_style)

    def _on_tab_switched(self, btn_id: int):
        self.stack.setCurrentIndex(btn_id)
        self._style_tabs()
        if btn_id == 1:
            self._update_custom_preview()

    def switch_to_custom_tab(self):
        self.btn_tab_custom.setChecked(True)
        self._on_tab_switched(1)

    def _select_custom_color(self, color_hex: str):
        self._custom_color = color_hex
        self._refresh_color_chip_styles()
        self._update_custom_preview()

    def _refresh_color_chip_styles(self):
        for btn, ch in self._color_chip_btns:
            is_sel = (ch.lower() == self._custom_color.lower())
            border = "2px solid #ffffff" if is_sel else "1.5px solid rgba(0,0,0,0.3)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ch};
                    border: {border};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid #38bdf8;
                }}
            """)

    def _update_custom_preview(self):
        text = self.txt_custom.text().strip() or LanguageManager.tr("stamp_approved")
        is_dynamic = self.chk_custom_dynamic.isChecked()
        author_name = "Kullanici"
        if self.parent() and hasattr(self.parent(), 'settings'):
            author_name = str(self.parent().settings.value("author_name", "Kullanici") or "Kullanici").strip()

        scale = 1.0
        w = int(220 * scale)
        h = int(72 * scale)
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        col = QColor(self._custom_color)
        p.translate(w / 2.0, h / 2.0)
        p.rotate(-3.5)
        p.translate(-w / 2.0, -h / 2.0)

        # Arka plan yumuşak damga dolgusu (1:1 belge ile birebir aynı)
        p.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 20)))
        p.setPen(QPen(col, 2.4 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(QRectF(6 * scale, 6 * scale, (220 - 12) * scale, (72 - 12) * scale), 5 * scale, 5 * scale)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col, 1.0 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(QRectF(10 * scale, 10 * scale, (220 - 20) * scale, (72 - 20) * scale), 3 * scale, 3 * scale)

        if not is_dynamic:
            font = QFont("Arial Black", int(13 * scale), QFont.Weight.Black)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2 * scale)
            p.setFont(font)
            p.setPen(col)
            rect_text = QRectF(12 * scale, 12 * scale, (220 - 24) * scale, (72 - 24) * scale)
            p.drawText(rect_text, Qt.AlignmentFlag.AlignCenter, text.upper())
        else:
            font_title = QFont("Arial Black", int(11 * scale), QFont.Weight.Black)
            font_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0 * scale)
            p.setFont(font_title)
            p.setPen(col)
            rect_title = QRectF(12 * scale, 10 * scale, (220 - 24) * scale, 28 * scale)
            p.drawText(rect_title, Qt.AlignmentFlag.AlignCenter, text.upper())

            p.setPen(QPen(col, 0.8 * scale, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(18 * scale, 40 * scale), QPointF((220 - 18) * scale, 40 * scale))

            font_sub = QFont("Segoe UI", int(7.0 * scale), QFont.Weight.Bold)
            p.setFont(font_sub)
            p.setPen(col)
            import datetime
            now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            info_str = f"{author_name}  •  {now_str}"
            rect_sub = QRectF(12 * scale, 42 * scale, (220 - 24) * scale, 20 * scale)
            p.drawText(rect_sub, Qt.AlignmentFlag.AlignCenter, info_str)

        p.end()
        self.lbl_custom_preview.setPixmap(pix)

    def _apply_custom_stamp(self):
        from src.ui.dialogs.stamp_dialog import render_stamp_png_bytes
        text = self.txt_custom.text().strip() or LanguageManager.tr("stamp_approved")
        is_dynamic = self.chk_custom_dynamic.isChecked()
        author_name = "Kullanici"
        if self.parent() and hasattr(self.parent(), 'settings'):
            author_name = str(self.parent().settings.value("author_name", "Kullanici") or "Kullanici").strip()

        data = render_stamp_png_bytes(
            text=text,
            color_hex=self._custom_color,
            is_dynamic=is_dynamic,
            author_name=author_name
        )
        self.hide()
        if self.on_stamp_selected:
            self.on_stamp_selected(data, text, 160.0, 60.0)

    def _on_preset_clicked(self, text_key: str, color_hex: str, is_dynamic: bool):
        from src.ui.dialogs.stamp_dialog import render_stamp_png_bytes
        text = LanguageManager.tr(text_key)
        author_name = "Kullanici"
        if self.parent() and hasattr(self.parent(), 'settings'):
            author_name = str(self.parent().settings.value("author_name", "Kullanici") or "Kullanici").strip()
        data = render_stamp_png_bytes(
            text=text,
            color_hex=color_hex,
            is_dynamic=is_dynamic,
            author_name=author_name
        )
        self.hide()
        if self.on_stamp_selected:
            self.on_stamp_selected(data, text, 160.0, 60.0)

    def _on_date_stamp_clicked(self):
        from src.ui.dialogs.stamp_dialog import render_date_stamp_bytes
        import datetime
        now_str = datetime.datetime.now().strftime("%d.%m.%Y")
        data = render_date_stamp_bytes(text=now_str, color_hex="#0284c7")
        self.hide()
        if self.on_stamp_selected:
            self.on_stamp_selected(data, f"{LanguageManager.tr('date_stamp')} {now_str}", 130.0, 42.0)

    def retranslate_ui(self):
        if hasattr(self, 'lbl_head_title'):
            self.lbl_head_title.setText(LanguageManager.tr("stamp_quick_palette_title"))
        if hasattr(self, 'btn_tab_preset'):
            self.btn_tab_preset.setText(LanguageManager.tr("stamp_tab_preset"))
        if hasattr(self, 'btn_tab_custom'):
            self.btn_tab_custom.setText(LanguageManager.tr("stamp_tab_custom"))
        if hasattr(self, 'lbl_std_sec'):
            self.lbl_std_sec.setText(LanguageManager.tr("stamp_cat_standard"))
        if hasattr(self, 'lbl_dyn_sec'):
            self.lbl_dyn_sec.setText(LanguageManager.tr("stamp_cat_dynamic"))
        if hasattr(self, 'btn_dyn_approved'):
            self.btn_dyn_approved.setText(f"{LanguageManager.tr('stamp_approved').upper()}")
        if hasattr(self, 'btn_date_today'):
            import datetime
            today_str = datetime.datetime.now().strftime("%d.%m.%Y")
            self.btn_date_today.setText(f"{LanguageManager.tr('date_stamp')}: {today_str}")
        if hasattr(self, 'chk_custom_dynamic'):
            self.chk_custom_dynamic.setText(LanguageManager.tr("stamp_dynamic_toggle"))
        if hasattr(self, 'btn_apply_custom'):
            self.btn_apply_custom.setText(LanguageManager.tr("stamp_apply_btn"))
        for btn, key, _ in self._preset_btns:
            btn.setText(LanguageManager.tr(key).upper())
