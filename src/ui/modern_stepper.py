"""
AuraPDF - Modern Sayı Arttırma / Azaltma Bileşeni (Modern Stepper / SpinBox)
Adobe Acrobat ve modern işletim sistemleri tarzında; solunda azaltma (-), ortasında
düzenlenebilir değer/yüzde, sağında arttırma (+) butonları bulunan, tüm temalarla
tam uyumlu pill-stepper widget'ı.
"""
from typing import Optional, Union
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QToolButton, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QIntValidator, QDoubleValidator, QWheelEvent, QKeyEvent

from src.ui.dialog_theme import get_current_theme, THEME_PALETTES


class ModernSpinBox(QFrame):
    """
    Standart QSpinBox yerine geçen modern pill-stepper bileşeni.
    [ - ]     Değer     [ + ]
    """
    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        min_val: int = 0,
        max_val: int = 100,
        default_val: int = 0,
        step: int = 1,
        suffix: str = "",
        prefix: str = "",
        parent: Optional[QFrame] = None
    ):
        super().__init__(parent)
        self._min = int(min_val)
        self._max = int(max_val)
        self._value = int(default_val)
        self._step = int(step)
        self._suffix = suffix
        self._prefix = prefix
        self._decimals = 0
        self._block_signals = False

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(28)
        self.setMinimumWidth(80)

        self._build_ui()
        self.apply_theme()
        self._update_display()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sol Azaltma Butonu (-)
        self.btn_minus = QToolButton(self)
        self.btn_minus.setText("−")
        self.btn_minus.setFixedSize(24, 26)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.setAutoRepeat(True)
        self.btn_minus.setAutoRepeatDelay(350)
        self.btn_minus.setAutoRepeatInterval(80)
        self.btn_minus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_minus.clicked.connect(self.stepDown)
        layout.addWidget(self.btn_minus)

        # 2. Orta Düzenlenebilir Metin Kutusu
        self.edit = QLineEdit(self)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.edit.setFixedHeight(26)
        self.edit.installEventFilter(self)
        self.edit.returnPressed.connect(self._commit_text)
        self.edit.editingFinished.connect(self._commit_text)
        layout.addWidget(self.edit)

        # 3. Sağ Arttırma Butonu (+)
        self.btn_plus = QToolButton(self)
        self.btn_plus.setText("+")
        self.btn_plus.setFixedSize(24, 26)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setAutoRepeat(True)
        self.btn_plus.setAutoRepeatDelay(350)
        self.btn_plus.setAutoRepeatInterval(80)
        self.btn_plus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_plus.clicked.connect(self.stepUp)
        layout.addWidget(self.btn_plus)

    def apply_theme(self, theme_name: Optional[str] = None):
        """Aktif temaya göre renk ve stil paletini uygular."""
        if not theme_name:
            theme_name = get_current_theme(self.parent())

        pal = THEME_PALETTES.get(theme_name, THEME_PALETTES["dark"])
        accent = pal.get("accent", "#388bfd")
        border = pal.get("border", "#3c3c3c")
        card_bg = pal.get("card", "#1e1e1e")
        text = pal.get("text", "#f8fafc")

        # Container Frame Stili
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame:hover {{
                border-color: rgba(255, 255, 255, 0.28);
            }}
            QFrame:focus-within {{
                border-color: {accent};
            }}
        """)

        # Azaltma Butonu Stili
        btn_minus_style = f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                color: {text};
                font-weight: bold;
                font-size: 13px;
                padding: 0;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }}
            QToolButton:pressed {{
                background-color: rgba(255, 255, 255, 0.20);
            }}
            QToolButton:disabled {{
                color: rgba(255, 255, 255, 0.2);
                background-color: transparent;
            }}
        """
        self.btn_minus.setStyleSheet(btn_minus_style)

        # Arttırma Butonu Stili
        btn_plus_style = f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                color: {text};
                font-weight: bold;
                font-size: 13px;
                padding: 0;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }}
            QToolButton:pressed {{
                background-color: rgba(255, 255, 255, 0.20);
            }}
            QToolButton:disabled {{
                color: rgba(255, 255, 255, 0.2);
                background-color: transparent;
            }}
        """
        self.btn_plus.setStyleSheet(btn_plus_style)

        # Orta Giriş Kutusu Stili
        edit_style = f"""
            QLineEdit {{
                background-color: transparent;
                border: none;
                color: {accent};
                font-weight: bold;
                font-size: 11px;
                padding: 0 2px;
            }}
            QLineEdit:disabled {{
                color: rgba(255, 255, 255, 0.25);
            }}
        """
        self.edit.setStyleSheet(edit_style)

    # --- DEĞER VE FORMATLAMA İŞLEMLERİ ---
    def _format_value(self, val: Union[int, float]) -> str:
        if self._decimals > 0:
            num_str = f"{val:.{self._decimals}f}"
        else:
            num_str = str(int(val))
        return f"{self._prefix}{num_str}{self._suffix}"

    def _update_display(self):
        if not self.edit.hasFocus():
            self.edit.setText(self._format_value(self._value))
        self.btn_minus.setEnabled(self.isEnabled() and self._value > self._min)
        self.btn_plus.setEnabled(self.isEnabled() and self._value < self._max)

    def _commit_text(self):
        raw = self.edit.text().strip()
        # Prefix ve suffix'i ayıkla
        if self._prefix and raw.startswith(self._prefix):
            raw = raw[len(self._prefix):]
        if self._suffix and raw.endswith(self._suffix.strip()):
            raw = raw[:-len(self._suffix.strip())]

        raw = raw.replace("%", "").replace("pt", "").replace("px", "").strip()
        try:
            val = float(raw) if self._decimals > 0 else int(float(raw))
            self.setValue(val)
        except ValueError:
            self._update_display()

    # --- QSpinBox İLE 100% UYUMLU API ---
    def value(self) -> int:
        return int(self._value)

    def setValue(self, val: Union[int, float]):
        clamped = max(self._min, min(self._max, int(round(val))))
        if clamped != self._value:
            self._value = clamped
            self._update_display()
            if not self._block_signals:
                self.valueChanged.emit(int(self._value))
        else:
            self._update_display()

    def setRange(self, min_val: int, max_val: int):
        self._min = int(min_val)
        self._max = int(max_val)
        self.setValue(self._value)

    def setMinimum(self, min_val: int):
        self.setRange(min_val, self._max)

    def setMaximum(self, max_val: int):
        self.setRange(self._min, max_val)

    def minimum(self) -> int:
        return self._min

    def maximum(self) -> int:
        return self._max

    def setSingleStep(self, step: int):
        self._step = max(1, int(step))

    def singleStep(self) -> int:
        return self._step

    def setPrefix(self, prefix: str):
        self._prefix = prefix
        self._update_display()

    def blockSignals(self, b: bool) -> bool:
        self._block_signals = b
        return super().blockSignals(b)

    def setSpecialValueText(self, text: str):
        self._special_value_text = text
        self._update_display()

    def specialValueText(self) -> str:
        return getattr(self, '_special_value_text', "")

    def suffix(self) -> str:
        return self._suffix

    def cleanText(self) -> str:
        return str(self._value)

    def text(self) -> str:
        return self._format_value(self._value)

    def stepUp(self):
        self.setValue(self._value + self._step)

    def stepDown(self):
        self.setValue(self._value - self._step)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.edit.setEnabled(enabled)
        self.btn_minus.setEnabled(enabled and self._value > self._min)
        self.btn_plus.setEnabled(enabled and self._value < self._max)

    def setButtonSymbols(self, _):
        # QSpinBox uyumluluğu için no-op
        pass

    def selectAll(self):
        self.edit.selectAll()

    # --- ETKİLEŞİM VE OLAY YÖNETİMİ ---
    def wheelEvent(self, event: QWheelEvent):
        if not self.isEnabled():
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.stepUp()
        elif delta < 0:
            self.stepDown()
        event.accept()

    def eventFilter(self, obj, event: QEvent) -> bool:
        if obj == self.edit:
            if event.type() == QEvent.Type.KeyPress:
                key_event: QKeyEvent = event
                if key_event.key() == Qt.Key.Key_Up:
                    self.stepUp()
                    return True
                elif key_event.key() == Qt.Key.Key_Down:
                    self.stepDown()
                    return True
            elif event.type() == QEvent.Type.FocusIn:
                # Odaklandığında saf sayıyı göster ve seç
                raw_num = str(self._value) if self._decimals == 0 else f"{self._value:.{self._decimals}f}"
                self.edit.setText(raw_num)
                QTimer.singleShot(0, self.edit.selectAll)
            elif event.type() == QEvent.Type.FocusOut:
                self._commit_text()
        return super().eventFilter(obj, event)


class ModernDoubleSpinBox(ModernSpinBox):
    """
    Ondalıklı sayılar için Modern Stepper (QDoubleSpinBox alternatifi).
    """
    valueChanged = pyqtSignal(float)

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 100.0,
        default_val: float = 0.0,
        step: float = 1.0,
        decimals: int = 1,
        suffix: str = "",
        prefix: str = "",
        parent: Optional[QFrame] = None
    ):
        super().__init__(
            min_val=int(min_val),
            max_val=int(max_val),
            default_val=int(default_val),
            step=int(step),
            suffix=suffix,
            prefix=prefix,
            parent=parent
        )
        self._min = float(min_val)
        self._max = float(max_val)
        self._value = float(default_val)
        self._step = float(step)
        self._decimals = int(decimals)
        self._update_display()

    def value(self) -> float:
        return float(self._value)

    def setValue(self, val: Union[int, float]):
        clamped = max(self._min, min(self._max, float(val)))
        if abs(clamped - self._value) > 1e-9:
            self._value = clamped
            self._update_display()
            if not self._block_signals:
                self.valueChanged.emit(float(self._value))
        else:
            self._update_display()

    def setRange(self, min_val: float, max_val: float):
        self._min = float(min_val)
        self._max = float(max_val)
        self.setValue(self._value)

    def setMinimum(self, min_val: float):
        self.setRange(min_val, self._max)

    def setMaximum(self, max_val: float):
        self.setRange(self._min, max_val)

    def setDecimals(self, d: int):
        self._decimals = max(0, int(d))
        self._update_display()

    def decimals(self) -> int:
        return self._decimals

    def setSingleStep(self, step: float):
        self._step = float(step)


# Takma Adlar (Aliases)
AuraSpinBox = ModernSpinBox
AuraDoubleSpinBox = ModernDoubleSpinBox
