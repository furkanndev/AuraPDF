# -*- coding: utf-8 -*-
"""
AuraPDF - Kısayol Yardımcısı & Fare Tuşu Yönetimi (Shortcut Helper)
Klavye ve fare kısayollarının serileştirilmesi, ayrıştırılması,
arayüzde gösterimi ve olay eşleştirmelerini yönetir.
"""

from typing import Optional, Tuple, Dict, Any, List
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeySequence
from src.core.i18n import LanguageManager


MOUSE_BUTTON_MAP: Dict[str, Qt.MouseButton] = {
    "Middle": Qt.MouseButton.MiddleButton,
    "XButton1": Qt.MouseButton.XButton1,  # Yan Geri Tuşu (Thumb / Back)
    "XButton2": Qt.MouseButton.XButton2,  # Yan İleri Tuşu (Thumb / Forward)
    "Right": Qt.MouseButton.RightButton,
    "Left": Qt.MouseButton.LeftButton,
}

REVERSE_MOUSE_BUTTON_MAP: Dict[Qt.MouseButton, str] = {
    v: k for k, v in MOUSE_BUTTON_MAP.items()
}


def is_mouse_shortcut(shortcut_str: Optional[str]) -> bool:
    """Verilen kısayol metninin bir fare kısayolu olup olmadığını belirler."""
    if not shortcut_str or not isinstance(shortcut_str, str):
        return False
    return "Mouse:" in shortcut_str


def clean_modifiers(mods: Any) -> Qt.KeyboardModifier:
    """NumLock, CapsLock vb. gereksiz bayrakları eleyerek sadece Ctrl, Shift, Alt filtreler."""
    clean = Qt.KeyboardModifier.NoModifier
    if mods & Qt.KeyboardModifier.ControlModifier:
        clean |= Qt.KeyboardModifier.ControlModifier
    if mods & Qt.KeyboardModifier.ShiftModifier:
        clean |= Qt.KeyboardModifier.ShiftModifier
    if mods & Qt.KeyboardModifier.AltModifier:
        clean |= Qt.KeyboardModifier.AltModifier
    return clean


def parse_mouse_shortcut(shortcut_str: str) -> Optional[Tuple[Qt.MouseButton, Qt.KeyboardModifier]]:
    """
    'Ctrl+Mouse:Middle' veya 'Mouse:XButton1' gibi bir metni
    (Qt.MouseButton, Qt.KeyboardModifier) ikilisine dönüştürür.
    """
    if not is_mouse_shortcut(shortcut_str):
        return None
    
    parts = shortcut_str.split('+')
    button_part = parts[-1].strip()
    if not button_part.startswith("Mouse:"):
        return None
    
    btn_key = button_part.replace("Mouse:", "").strip()
    btn = MOUSE_BUTTON_MAP.get(btn_key)
    if not btn:
        return None
    
    mods = Qt.KeyboardModifier.NoModifier
    for m in parts[:-1]:
        m_str = m.strip()
        if m_str == "Ctrl":
            mods |= Qt.KeyboardModifier.ControlModifier
        elif m_str == "Shift":
            mods |= Qt.KeyboardModifier.ShiftModifier
        elif m_str == "Alt":
            mods |= Qt.KeyboardModifier.AltModifier
    
    return btn, mods


def build_mouse_shortcut_string(btn: Qt.MouseButton, mods: Any) -> Optional[str]:
    """Fare tuşu ve modifier'lardan kanonik kısayol stringi üretir ('Ctrl+Mouse:XButton1')."""
    btn_key = REVERSE_MOUSE_BUTTON_MAP.get(btn)
    if not btn_key:
        return None
    
    mod_parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        mod_parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        mod_parts.append("Shift")
    if mods & Qt.KeyboardModifier.AltModifier:
        mod_parts.append("Alt")
    
    mod_parts.append(f"Mouse:{btn_key}")
    return "+".join(mod_parts)


def format_shortcut_display(shortcut_str: Optional[str]) -> str:
    """Kısayol metnini kullanıcı arayüzünde şık ve anlaşılır bir etikete dönüştürür."""
    if not shortcut_str or not shortcut_str.strip():
        return LanguageManager.tr("shortcut_none")
    
    if is_mouse_shortcut(shortcut_str):
        parts = shortcut_str.split('+')
        btn_key = parts[-1].replace("Mouse:", "").strip()
        
        btn_labels = {
            "Middle": LanguageManager.tr("shortcut_mouse_middle"),
            "XButton1": LanguageManager.tr("shortcut_mouse_xbutton1"),
            "XButton2": LanguageManager.tr("shortcut_mouse_xbutton2"),
            "Right": LanguageManager.tr("shortcut_mouse_right"),
            "Left": LanguageManager.tr("shortcut_mouse_left"),
        }
        btn_text = btn_labels.get(btn_key, btn_key)
        
        mods = parts[:-1]
        if mods:
            return f"🖱️ {' + '.join(mods)} + {btn_text}"
        return f"🖱️ {btn_text}"
    
    # Standart klavye kısayolu
    return shortcut_str


def get_mouse_preset_options() -> List[Tuple[str, str]]:
    """
    Açılır menüden doğrudan seçilebilecek yaygın fare kısayolları listesi.
    (Kanonik Değer, Görüntüleme Metni)
    """
    presets = [
        ("Mouse:Middle", LanguageManager.tr("shortcut_mouse_middle")),
        ("Mouse:XButton1", LanguageManager.tr("shortcut_mouse_xbutton1")),
        ("Mouse:XButton2", LanguageManager.tr("shortcut_mouse_xbutton2")),
        ("Ctrl+Mouse:Middle", f"Ctrl + {LanguageManager.tr('shortcut_mouse_middle')}"),
        ("Shift+Mouse:Middle", f"Shift + {LanguageManager.tr('shortcut_mouse_middle')}"),
        ("Ctrl+Mouse:XButton1", f"Ctrl + {LanguageManager.tr('shortcut_mouse_xbutton1')}"),
        ("Ctrl+Mouse:XButton2", f"Ctrl + {LanguageManager.tr('shortcut_mouse_xbutton2')}"),
        ("Alt+Mouse:Middle", f"Alt + {LanguageManager.tr('shortcut_mouse_middle')}"),
    ]
    return presets
