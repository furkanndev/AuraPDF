"""
AuraPDF - Sürükle-Bırak Tekerleği Ayarları
==========================================
Tekerlekte hangi eylemlerin hangi sırayla görüneceğini, tetikleyici tuşu ve boyutu
tanımlar. Hem uygulama hem sistem tepsisi yardımcısı aynı ayarları `QSettings`
üzerinden okur; böylece Ayarlar'da yapılan değişiklik yardımcıya da yansır.
"""

import json
from typing import Dict, List

from PyQt6.QtCore import QSettings

# Eylem kodu -> (i18n anahtarı, AuraIconFactory metodu). Sıra, ayar penceresindeki listenin sırasıdır.
CATALOG: Dict[str, tuple] = {
    "merge": ("drag_wheel_merge", "icon_merge"),
    "split": ("drag_wheel_split", "icon_split"),
    "word": ("drag_wheel_word", "icon_word"),
    "pptx": ("drag_wheel_pptx", "icon_powerpoint"),
    "excel": ("drag_wheel_excel", "icon_excel"),
    "epub": ("drag_wheel_epub", "icon_epub"),
    "compress": ("drag_wheel_compress", "icon_compress"),
    "protect": ("drag_wheel_protect", "icon_lock"),
}

DEFAULT_ACTIONS: List[str] = ["merge", "split", "word", "pptx", "excel"]
MIN_ACTIONS = 3
MAX_ACTIONS = 8

# Tetikleyici kodları. Gezgin'in kendi sürükleme tuşlarıyla (Ctrl/Shift/Alt) çakışma ve
# dil değiştirme kısayolu (Alt+Shift) nedeniyle yalnızca bu üçü sunulur.
TRIGGERS = ("ctrl_alt", "ctrl_shift", "middle")
DEFAULT_TRIGGER = "ctrl_alt"

# Boyut kodu -> (dış yarıçap, iç yarıçap)
SIZES: Dict[str, tuple] = {
    "small": (132.0, 42.0),
    "normal": (168.0, 52.0),
    "large": (208.0, 64.0),
}
DEFAULT_SIZE = "normal"

_KEY_ENABLED = "drag_wheel_enabled"
_KEY_ACTIONS = "drag_wheel_actions"
_KEY_TRIGGER = "drag_wheel_trigger"
_KEY_SIZE = "drag_wheel_size"


def sanitize_actions(raw) -> List[str]:
    """Geçersiz/yinelenen kodları ayıklar; sayı sınırın dışındaysa varsayılana döner."""
    seen: List[str] = []
    if isinstance(raw, (list, tuple)):
        for code in raw:
            if isinstance(code, str) and code in CATALOG and code not in seen:
                seen.append(code)
    if len(seen) < MIN_ACTIONS:
        return list(DEFAULT_ACTIONS)
    return seen[:MAX_ACTIONS]


def load_config() -> dict:
    """Kayıtlı ayarları (doğrulanmış olarak) döner."""
    st = QSettings("AuraPDF", "PDFViewer")
    try:
        st.sync()
    except Exception:
        pass
    try:
        actions = sanitize_actions(json.loads(str(st.value(_KEY_ACTIONS, ""))))
    except Exception:
        actions = list(DEFAULT_ACTIONS)
    trigger = str(st.value(_KEY_TRIGGER, DEFAULT_TRIGGER))
    if trigger not in TRIGGERS:
        trigger = DEFAULT_TRIGGER
    size = str(st.value(_KEY_SIZE, DEFAULT_SIZE))
    if size not in SIZES:
        size = DEFAULT_SIZE
    enabled = str(st.value(_KEY_ENABLED, True)).lower() not in ("false", "0")
    return {"enabled": enabled, "actions": actions, "trigger": trigger, "size": size}


def save_config(actions, trigger: str, size: str) -> None:
    """Eylem listesini, tetikleyiciyi ve boyutu kaydeder (geçersiz değerler varsayılana çekilir)."""
    st = QSettings("AuraPDF", "PDFViewer")
    st.setValue(_KEY_ACTIONS, json.dumps(sanitize_actions(actions)))
    st.setValue(_KEY_TRIGGER, trigger if trigger in TRIGGERS else DEFAULT_TRIGGER)
    st.setValue(_KEY_SIZE, size if size in SIZES else DEFAULT_SIZE)
    st.sync()
