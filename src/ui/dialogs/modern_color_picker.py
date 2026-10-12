"""
AuraPDF - Modern Renk Seçici Diyaloğu (Modern Color Picker Dialog)
===================================================================
Klasik ve eski işletim sistemi renk diyalogları yerine;
- Akıcı ve modern kart estetiği
- Canlı ikili renk karşılaştırma önizlemesi (Orijinal vs Yeni)
- Doğrudan düzenlenebilir HEX kodu girişi
- Seçkin modern renk paletleri (Vurgu, Koyu Arka Plan, Yüzey & Nötr)
- R, G, B hassas ayar sürgüleri
- Tam 8 tema ve özel tema ile uyumlu (apply_dialog_theme)
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRegularExpression
from PyQt6.QtGui import QColor, QFont, QRegularExpressionValidator, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QSlider, QGridLayout, QToolButton, QColorDialog, QWidget
)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme, get_theme_palette


class ModernColorSwatchButton(QPushButton):
    """Modern yuvarlak renk hapı düğmesi."""
    def __init__(self, color_hex: str, size: int = 24, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color_hex.upper())
        self._is_active = False
        self._update_style()

    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()

    def _update_style(self):
        c = QColor(self.color_hex)
        border_col = "#ffffff" if c.lightness() < 128 else "#000000"
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color_hex};
                    border: 2.5px solid {border_col};
                    border-radius: {self.width() // 2}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color_hex};
                    border: 1.5px solid rgba(255, 255, 255, 0.22);
                    border-radius: {self.width() // 2}px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)


class ModernColorPickerDialog(QDialog):
    """
    AuraPDF için özel olarak tasarlanmış modern, şık ve kullanışlı renk seçici.
    """
    colorChanged = pyqtSignal(str)

    def __init__(self, initial_color: str = "#38bdf8", role_title: str = "", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle(LanguageManager.tr("theme_picker_dialog_title"))
        self.setFixedWidth(440)

        init_c = QColor(initial_color)
        if not init_c.isValid():
            init_c = QColor("#38bdf8")
        self._initial_hex = init_c.name().upper()
        self._current_color = init_c

        self._swatch_buttons: List[ModernColorSwatchButton] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Başlık ve Açıklama Şeridi
        h_head = QHBoxLayout()
        h_head.setContentsMargins(0, 0, 0, 0)
        h_head.setSpacing(10)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_palette_grid("#38bdf8").pixmap(18, 18))
        h_head.addWidget(lbl_icon)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        lbl_title = QLabel(LanguageManager.tr("theme_picker_dialog_title"))
        lbl_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        v_head.addWidget(lbl_title)

        sub_text = role_title or LanguageManager.tr("theme_studio_title")
        lbl_sub = QLabel(sub_text)
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        v_head.addWidget(lbl_sub)
        h_head.addLayout(v_head, 1)

        btn_close = QToolButton()
        btn_close.setIcon(ModernIconFactory.icon_close())
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background: transparent; border: none; border-radius: 4px;")
        btn_close.clicked.connect(self.reject)
        h_head.addWidget(btn_close)
        main_layout.addLayout(h_head)

        # 2. Canlı Önizleme ve HEX Kodu Kartı
        card_preview = QFrame()
        card_preview.setObjectName("PreviewCard")
        card_preview.setStyleSheet("""
            QFrame#PreviewCard {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        h_prev = QHBoxLayout(card_preview)
        h_prev.setContentsMargins(12, 8, 12, 8)
        h_prev.setSpacing(14)

        # Çift Renk Önizleme Kutusu (Önceki vs Yeni)
        self.frame_swatches_split = QFrame()
        self.frame_swatches_split.setFixedSize(76, 42)
        self.frame_swatches_split.setStyleSheet("""
            border-radius: 8px;
            border: 1.5px solid rgba(255, 255, 255, 0.25);
        """)
        h_split = QHBoxLayout(self.frame_swatches_split)
        h_split.setContentsMargins(0, 0, 0, 0)
        h_split.setSpacing(0)

        self.lbl_orig_swatch = QLabel()
        self.lbl_orig_swatch.setToolTip("Orijinal Renk")
        self.lbl_orig_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_orig_swatch.mousePressEvent = lambda e: self.set_color(self._initial_hex)
        h_split.addWidget(self.lbl_orig_swatch, 1)

        self.lbl_curr_swatch = QLabel()
        self.lbl_curr_swatch.setToolTip("Yeni Seçilen Renk")
        h_split.addWidget(self.lbl_curr_swatch, 1)

        h_prev.addWidget(self.frame_swatches_split)

        # HEX Girişi
        v_hex = QVBoxLayout()
        v_hex.setSpacing(2)
        lbl_hex_title = QLabel(LanguageManager.tr("theme_picker_hex_label"))
        lbl_hex_title.setStyleSheet("font-size: 10.5px; font-weight: 600; color: #94a3b8;")
        v_hex.addWidget(lbl_hex_title)

        h_hex_box = QHBoxLayout()
        h_hex_box.setSpacing(6)
        lbl_hash = QLabel("#")
        lbl_hash.setStyleSheet("font-size: 13px; font-weight: bold; color: #94a3b8;")
        h_hex_box.addWidget(lbl_hash)

        self.txt_hex = QLineEdit()
        self.txt_hex.setMaxLength(6)
        self.txt_hex.setFixedWidth(90)
        self.txt_hex.setFixedHeight(28)
        self.txt_hex.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.txt_hex.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 2px 6px;
                color: #ffffff;
                font-weight: 700;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        hex_regex = QRegularExpression("^[0-9A-Fa-f]{6}$")
        self.txt_hex.setValidator(QRegularExpressionValidator(hex_regex, self))
        self.txt_hex.textEdited.connect(self._on_hex_text_edited)
        h_hex_box.addWidget(self.txt_hex)
        h_hex_box.addStretch(1)
        v_hex.addLayout(h_hex_box)
        h_prev.addLayout(v_hex, 1)

        main_layout.addWidget(card_preview)

        # 3. Seçkin Renk Paleti Hapları (Küratörlü Grid)
        lbl_swatches = QLabel(LanguageManager.tr("theme_picker_swatches_title"))
        lbl_swatches.setStyleSheet("font-size: 11px; font-weight: 700; color: #cbd5e1; margin-top: 4px;")
        main_layout.addWidget(lbl_swatches)

        card_palettes = QFrame()
        card_palettes.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        v_pal = QVBoxLayout(card_palettes)
        v_pal.setContentsMargins(6, 6, 6, 6)
        v_pal.setSpacing(6)

        # 3 Sıra Seçkin Renkler
        palette_rows = [
            # 1. Sıra: Canlı Vurgu ve Neon Tonlar
            [
                "#38bdf8", "#0284c7", "#60a5fa", "#6366f1", "#8b5cf6",
                "#a855f7", "#c084fc", "#ff2a85", "#f43f5e", "#ef4444",
                "#f97316", "#f59e0b", "#10b981", "#14b8a6"
            ],
            # 2. Sıra: Koyu Çalışma Alanı ve Derin Tonlar
            [
                "#071410", "#090d16", "#0e1014", "#10091a", "#121212",
                "#14171d", "#160024", "#181e29", "#1a0a0f", "#1c1c1c",
                "#201435", "#232528", "#2b2d30", "#35383c"
            ],
            # 3. Sıra: Yüzey, Kart ve Tipografi Açık Tonları
            [
                "#0f172a", "#1e222b", "#1e293b", "#222b3a", "#262a34",
                "#334155", "#475569", "#64748b", "#94a3b8", "#cbd5e1",
                "#e2e8f0", "#f1f5f9", "#f8fafc", "#ffffff"
            ]
        ]

        for row_colors in palette_rows:
            h_row = QHBoxLayout()
            h_row.setContentsMargins(0, 0, 0, 0)
            h_row.setSpacing(6)
            for c_hex in row_colors:
                btn_sw = ModernColorSwatchButton(c_hex, size=21, parent=self)
                btn_sw.clicked.connect(lambda checked, col=c_hex: self.set_color(col))
                self._swatch_buttons.append(btn_sw)
                h_row.addWidget(btn_sw)
            v_pal.addLayout(h_row)

        main_layout.addWidget(card_palettes)

        # 4. RGB Hassas Ayar Sürgüleri
        card_sliders = QFrame()
        card_sliders.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px;
            }
        """)
        v_rgb = QVBoxLayout(card_sliders)
        v_rgb.setContentsMargins(8, 6, 8, 6)
        v_rgb.setSpacing(5)

        self._slider_r, self._lbl_val_r = self._build_rgb_row("R", "#ef4444", v_rgb)
        self._slider_g, self._lbl_val_g = self._build_rgb_row("G", "#10b981", v_rgb)
        self._slider_b, self._lbl_val_b = self._build_rgb_row("B", "#38bdf8", v_rgb)

        main_layout.addWidget(card_sliders)

        # 5. Gelişmiş Spektrum Butonu
        h_adv = QHBoxLayout()
        self.btn_advanced_spectrum = QPushButton(LanguageManager.tr("theme_picker_advanced"))
        self.btn_advanced_spectrum.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_advanced_spectrum.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #38bdf8;
                border: none;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
                padding: 2px 4px;
            }
            QPushButton:hover {
                color: #7dd3fc;
                text-decoration: underline;
            }
        """)
        self.btn_advanced_spectrum.clicked.connect(self._open_advanced_spectrum)
        h_adv.addWidget(self.btn_advanced_spectrum)
        h_adv.addStretch(1)
        main_layout.addLayout(h_adv)

        # 6. Alt Eylem Butonları (İptal / Seç)
        h_actions = QHBoxLayout()
        h_actions.setContentsMargins(0, 4, 0, 0)
        h_actions.setSpacing(10)
        h_actions.addStretch(1)

        self.btn_cancel = QPushButton(LanguageManager.tr("theme_picker_btn_cancel"))
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 7px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        h_actions.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(LanguageManager.tr("theme_picker_btn_select"))
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #ffffff;
                border: none;
                border-radius: 7px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        self.btn_apply.clicked.connect(self.accept)
        h_actions.addWidget(self.btn_apply)

        main_layout.addLayout(h_actions)

        # İlk renk değerini yükle
        self.set_color(self._initial_hex)
        apply_dialog_theme(self, parent)

    def _build_rgb_row(self, label_text: str, label_color: str, parent_layout):
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        lbl_badge = QLabel(label_text)
        lbl_badge.setFixedSize(16, 16)
        lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_badge.setStyleSheet(f"""
            background-color: {label_color};
            color: #ffffff;
            font-size: 10px;
            font-weight: bold;
            border-radius: 4px;
        """)
        h.addWidget(lbl_badge)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        slider.setFixedHeight(16)
        slider.setCursor(Qt.CursorShape.PointingHandCursor)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {label_color};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                border: 2px solid {label_color};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {label_color};
                border: 2px solid #ffffff;
            }}
        """)
        slider.valueChanged.connect(self._on_rgb_slider_changed)
        h.addWidget(slider, 1)

        lbl_val = QLabel("0")
        lbl_val.setFixedWidth(30)
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_val.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        h.addWidget(lbl_val)

        parent_layout.addLayout(h)
        return slider, lbl_val

    def set_color(self, hex_or_color):
        c = QColor(hex_or_color)
        if not c.isValid():
            return
        self._current_color = c
        hex_code = c.name().upper()[1:]

        # HEX inputunu güncelle (sinyalleri bloke ederek)
        self.txt_hex.blockSignals(True)
        self.txt_hex.setText(hex_code)
        self.txt_hex.blockSignals(False)

        # Sürgüleri güncelle
        self._slider_r.blockSignals(True)
        self._slider_g.blockSignals(True)
        self._slider_b.blockSignals(True)

        self._slider_r.setValue(c.red())
        self._slider_g.setValue(c.green())
        self._slider_b.setValue(c.blue())
        self._lbl_val_r.setText(str(c.red()))
        self._lbl_val_g.setText(str(c.green()))
        self._lbl_val_b.setText(str(c.blue()))

        self._slider_r.blockSignals(False)
        self._slider_g.blockSignals(False)
        self._slider_b.blockSignals(False)

        # Önizleme kutucuklarını güncelle
        self.lbl_orig_swatch.setStyleSheet(f"""
            background-color: {self._initial_hex};
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
        """)
        self.lbl_curr_swatch.setStyleSheet(f"""
            background-color: #{hex_code};
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        """)

        # Palet butonlarının aktiflik durumunu güncelle
        curr_full_hex = f"#{hex_code}".lower()
        for btn in self._swatch_buttons:
            btn.set_active(btn.color_hex.lower() == curr_full_hex)

        # Uygula butonunun rengini güncelle
        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: #{hex_code};
                color: {"#ffffff" if c.lightness() < 140 else "#0f172a"};
                border: none;
                border-radius: 7px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)

        self.colorChanged.emit(f"#{hex_code}")

    def _on_hex_text_edited(self, text: str):
        if len(text) == 6:
            c = QColor(f"#{text}")
            if c.isValid():
                self.set_color(c)

    def _on_rgb_slider_changed(self):
        r = self._slider_r.value()
        g = self._slider_g.value()
        b = self._slider_b.value()
        self._lbl_val_r.setText(str(r))
        self._lbl_val_g.setText(str(g))
        self._lbl_val_b.setText(str(b))
        self.set_color(QColor(r, g, b))

    def _open_advanced_spectrum(self):
        opts = QColorDialog.ColorDialogOption.DontUseNativeDialog
        chosen = QColorDialog.getColor(self._current_color, self, LanguageManager.tr("theme_picker_dialog_title"), opts)
        if chosen.isValid():
            self.set_color(chosen)

    def get_selected_hex(self) -> str:
        return self._current_color.name().upper()

    @classmethod
    def get_color(cls, initial_color: str = "#38bdf8", role_title: str = "", parent=None) -> Optional[str]:
        dlg = cls(initial_color=initial_color, role_title=role_title, parent=parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_selected_hex()
        return None
