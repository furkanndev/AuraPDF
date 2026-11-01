"""
AuraPDF - Arayüz Stili Yöneticisi
=================================
Klasik, Atölye, Grafit ve Şerit arayüzlerinin renk, biçim, tema uyumu ve
hareket profillerini tek noktada tanımlar.
"""

import re
from typing import Dict, List, Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.icon_glyphs import set_glyph_style

DEFAULT_STYLE = "classic"

STYLE_FONTS = {"atolye": "Corbel", "grafit": "Bahnschrift", "serit": "Calibri"}

# Her arayüzün araç, panel, sekme ve tam ekran yerleşimi; klasik arayüz kullanıcı ayarlarını izler.
STYLE_LAYOUTS = {
    "atolye": {"panels": "tools_left_nav_right", "dock": "left", "tools_bar": "capsule", "tabs": "top",
               "body_margin": 0, "body_spacing": 0, "fs_toolbar": "top", "fs_hud": "bottom", "tools_panel": True},
    "grafit": {"panels": "tools_right_nav_left", "dock": "top", "tools_bar": "dock", "tabs": "top",
               "body_margin": 12, "body_spacing": 10, "fs_toolbar": "bottom", "fs_hud": "right", "tools_panel": False},
    "serit": {"panels": "tools_right_nav_left", "dock": "top", "tools_bar": "ribbon", "tabs": "bottom",
              "body_margin": 0, "body_spacing": 0, "fs_toolbar": "left", "fs_hud": "top", "tools_panel": True},
}

STYLE_THEME_COLORS: Dict[str, Dict[str, str]] = {
    "atolye_ink": {
        "bg": "#f4f6f8", "tab_bar_bg": "#e6eaee", "surface": "#ffffff", "surface_hover": "#e9edf1",
        "surface_active": "#dfe4e9", "border": "#cdd5dd", "border_subtle": "#e6eaee", "text": "#1d2733",
        "text_muted": "#4b5563", "accent": "#24507a", "accent_hover": "#1b3f61",
        "accent_light": "rgba(36, 80, 122, 0.12)", "danger": "#b42318", "tab_bg": "#e6eaee",
        "tab_active": "#ffffff", "tab_text": "#4b5563", "tab_active_text": "#1d2733",
        "badge_bg": "#e9edf1", "card_bg": "#ffffff", "card_border": "#cdd5dd", "view_bg": "#dfe4e9",
        "on_accent": "#ffffff",
    },
    "grafit_amber": {
        "bg": "#17181a", "tab_bar_bg": "#1f2022", "surface": "#26272a", "surface_hover": "#34363a",
        "surface_active": "#3a3c40", "border": "#3a3c40", "border_subtle": "#2c2d30", "text": "#ecebe7",
        "text_muted": "#b5b4af", "accent": "#d2b071", "accent_hover": "#e0c389",
        "accent_light": "rgba(210, 176, 113, 0.18)", "danger": "#e08a7d", "tab_bg": "#1f2022",
        "tab_active": "#34363a", "tab_text": "#b5b4af", "tab_active_text": "#ecebe7",
        "badge_bg": "#34363a", "card_bg": "#26272a", "card_border": "#45474b", "view_bg": "#111214",
        "on_accent": "#17181a",
    },
    "kiremit_gece": {
        "bg": "#262624", "tab_bar_bg": "#1f1e1d", "surface": "#30302e", "surface_hover": "#3a3a37",
        "surface_active": "#44433f", "border": "#44433f", "border_subtle": "#353532", "text": "#faf9f5",
        "text_muted": "#c2c0b6", "accent": "#d97757", "accent_hover": "#e39078",
        "accent_light": "rgba(217, 119, 87, 0.18)", "danger": "#f08a7a", "tab_bg": "#1f1e1d",
        "tab_active": "#30302e", "tab_text": "#c2c0b6", "tab_active_text": "#faf9f5",
        "badge_bg": "#3a3a37", "card_bg": "#30302e", "card_border": "#4d4c47", "view_bg": "#1a1918",
        "on_accent": "#1f1e1d",
    },
    "kiremit_gun": {
        "bg": "#f5f4ed", "tab_bar_bg": "#ebe9df", "surface": "#fffefb", "surface_hover": "#efeee5",
        "surface_active": "#e6e3d8", "border": "#ddd9cc", "border_subtle": "#ebe9df", "text": "#141413",
        "text_muted": "#5e5d59", "accent": "#b9532f", "accent_hover": "#a04525",
        "accent_light": "rgba(185, 83, 47, 0.14)", "danger": "#b42318", "tab_bg": "#ebe9df",
        "tab_active": "#fffefb", "tab_text": "#5e5d59", "tab_active_text": "#141413",
        "badge_bg": "#efeee5", "card_bg": "#fffefb", "card_border": "#ddd9cc", "view_bg": "#e6e3d8",
        "on_accent": "#ffffff",
    },
    "serit_sage": {
        "bg": "#eef0ee", "tab_bar_bg": "#dfe4e0", "surface": "#ffffff", "surface_hover": "#e7ebe8",
        "surface_active": "#dcebe5", "border": "#cfd6d1", "border_subtle": "#dfe4e0", "text": "#20261f",
        "text_muted": "#4e5a52", "accent": "#2f5d50", "accent_hover": "#244a40",
        "accent_light": "rgba(47, 93, 80, 0.14)", "danger": "#a8321f", "tab_bg": "#dfe4e0",
        "tab_active": "#ffffff", "tab_text": "#4e5a52", "tab_active_text": "#20261f",
        "badge_bg": "#e7ebe8", "card_bg": "#ffffff", "card_border": "#cfd6d1", "view_bg": "#dfe4e0",
        "on_accent": "#ffffff",
    },
}

STYLE_THEME_SPECS = {
    code: {
        "main_bg": c["bg"], "main_text": c["text"], "tb_bg": c["surface"], "tb_border": c["border"],
        "btn_hover": c["surface_hover"], "accent": c["accent"], "page_bg": c["surface_hover"],
        "page_border": c["card_border"], "tab_bg": c["tab_bg"], "tab_hover": c["surface_hover"],
        "tab_border": c["border"], "tab_text": c["tab_text"], "view_bg": c["view_bg"],
    }
    for code, c in STYLE_THEME_COLORS.items()
}

STYLE_DIALOG_PALETTES = {
    code: {
        "bg": c["bg"], "card": c["surface"], "border": c["border"], "accent": c["accent"],
        "accent_hover": c["accent_hover"], "text": c["text"], "muted": c["text_muted"],
    }
    for code, c in STYLE_THEME_COLORS.items()
}

STYLE_PAGE_CONTROL_PALETTES = {
    code: {
        "btn": c["surface"], "btn_hover": c["surface_hover"], "lbl": c["bg"], "border": c["border"],
        "border_inner": c["border_subtle"], "accent": c["accent"], "text": c["text"],
    }
    for code, c in STYLE_THEME_COLORS.items()
}

# Her arayüzde yalnızca görsel olarak uyumlu temalar gösterilir; ilk tema varsayılandır.
STYLE_THEMES: Dict[str, List[str]] = {
    "classic": ["gray", "emerald", "purple", "crimson", "nord", "vice_city", "apple", "kiremit_gece", "kiremit_gun", "custom"],
    "atolye": ["atolye_ink", "serit_sage", "kiremit_gun", "kiremit_gece", "custom"],
    "grafit": ["grafit_amber", "kiremit_gece", "custom"],
    "serit": ["serit_sage", "atolye_ink", "nord", "emerald", "kiremit_gun", "kiremit_gece", "custom"],
}

_STYLE_SHAPES = {
    "atolye": {"btn": 6, "input": 6, "menu": 8, "tab": 6, "tool": 6, "height": 30},
    "grafit": {"btn": 12, "input": 10, "menu": 14, "tab": 8, "tool": 12, "height": 34},
    "serit": {"btn": 3, "input": 3, "menu": 3, "tab": 2, "tool": 3, "height": 26},
}

MOTION_PROFILES = {
    "classic": {"open_ms": 170, "lift": 8, "hover_ms": 120, "ripple_ms": 320, "page_ms": 170, "radius": 4},
    "atolye": {"open_ms": 190, "lift": 8, "hover_ms": 130, "ripple_ms": 340, "page_ms": 190, "radius": 6},
    "grafit": {"open_ms": 240, "lift": 16, "hover_ms": 170, "ripple_ms": 420, "page_ms": 230, "radius": 12},
    "serit": {"open_ms": 110, "lift": 0, "hover_ms": 80, "ripple_ms": 220, "page_ms": 100, "radius": 3},
}


def get_interface_style() -> str:
    """Kayıtlı arayüz stilini döner; tanınmayan değerlerde klasik arayüze düşer."""
    try:
        style = QSettings("AuraPDF", "PDFViewer").value("interface_style", DEFAULT_STYLE, type=str)
    except Exception:
        style = DEFAULT_STYLE
    return style if style in STYLE_THEMES else DEFAULT_STYLE


def panel_layout_key(style: str) -> str:
    """Panel düzeni her arayüz için ayrı saklanır; klasik arayüz eski anahtarı korur."""
    return "sidebar_layout" if style == DEFAULT_STYLE else f"sidebar_layout_{style}"


def get_panel_layout(style: str) -> str:
    """Arayüzün kayıtlı panel düzenini, yoksa o arayüzün varsayılanını döner."""
    default = STYLE_LAYOUTS.get(style, {}).get("panels", "tools_right_nav_left")
    return QSettings("AuraPDF", "PDFViewer").value(panel_layout_key(style), default, type=str)


_active_style = None
_active_colors: Dict[str, str] = {}
_RULE = re.compile(r"([^{}]*)\{([^{}]*)\}")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
_TEXT_COLOR = re.compile(r"((?<![-\w])color:\s*)(#[0-9a-fA-F]{3,8}\b|white\b)")
_TEXT_RGBA = re.compile(r"((?<![-\w])color:\s*)rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\s*\)")
_WHITE_RGBA = re.compile(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([\d.]+)\s*\)")
_LIGHT_TEXTS = {"#fff", "#ffffff", "white", "#f8fafc", "#f1f5f9", "#f0f0f0", "#e2e8f0", "#e0e0e0", "#eee"}
_MUTED_TEXTS = {"#94a3b8", "#cbd5e1", "#a1a1aa", "#9ca3af"}
# Kullanıcı renkleriyle karışmaması için yalnızca arayüzde kullanılan koyu yüzey değerleri listelenir.
_DARK_SURFACES = {
    "#1e1e20", "#27272a", "#2b2b30", "#242426", "#2f2f35", "#212327", "#1e1e24", "#1f1f23", "#1c1c1e",
    "#202022", "#232d3d", "#18181a", "#242428", "#2c2c32", "#1e3a5f", "#26262b", "#2e1d20", "#2d2d30",
    "#1e202a", "#16181f", "#1a1d24", "#0e1014", "#383838", "#484848",
}
_ACCENT_LITERALS = {"#0284c7": "accent", "#0369a1": "accent_hover", "#0a84ff": "accent"}
_DARK_RGBA = re.compile(r"(background(?:-color)?:\s*)rgba\(\s*[1-5]?\d\s*,\s*[1-5]?\d\s*,\s*[1-5]?\d\s*,\s*[\d.]+\s*\)")
_classic_family = None
_raw_setter = None
_progress_hook = None
_restyle_skip = None
_RADIUS = re.compile(r"(border(?:-(?:top|bottom)-(?:left|right))?-radius:\s*)(\d+(?:\.\d+)?)px")
_PADDING = re.compile(r"(?<![-\w])(padding:\s*)((?:\d+(?:\.\d+)?px\s*){1,4})")
_FAMILY = re.compile(r"font-family:[^;}]*(?:Segoe|Inter|system-ui|sans-serif)[^;}]*")
_RAW_PROPERTY = "auraRawStyleSheet"


def active_style() -> str:
    """Olay ve boyama döngülerinde kayıt defterine gitmeden geçerli stili döner."""
    global _active_style
    if _active_style is None:
        _active_style = get_interface_style()
    return _active_style


def get_ink_color() -> str:
    """Elle boyanan arayüz öğeleri için geçerli temanın metin rengini döner."""
    return _active_colors.get("text", "#f8fafc")


def get_ink_tint(alpha: int) -> QColor:
    """Kaydırıcı izi ve kapalı düğme gibi soluk yüzeyler için metin renginin saydam tonunu döner."""
    tint = QColor(get_ink_color())
    tint.setAlpha(alpha)
    return tint


def _on_accent(colors: dict) -> str:
    """Vurgu rengi üzerinde okunacak yazı rengini seçer; özel temada vurguya göre hesaplar."""
    if "on_accent" in colors:
        return colors["on_accent"]
    return "#17181a" if QColor(colors.get("accent", "#000000")).lightness() > 150 else "#ffffff"


def _is_light_surface(colors: dict) -> bool:
    return QColor(colors.get("surface", "#000000")).lightness() > 128


def _recolor_rule(selector: str, body: str, colors: dict) -> str:
    """Tek bir kuraldaki koyu temaya bağlı sabit renkleri geçerli tema renkleriyle değiştirir."""
    has_text = _TEXT_COLOR.search(body) is not None
    active_state = ":hover" in selector or ":selected" in selector or ":pressed" in selector
    surface = colors["surface_hover"] if active_state else colors["surface"]

    def swap_hex(match):
        value = match.group(0).lower()
        if value in _DARK_SURFACES:
            return colors["border"] if body[:match.start()].rfind("border") > body[:match.start()].rfind(";") else surface
        if value in _ACCENT_LITERALS and has_text:
            return colors[_ACCENT_LITERALS[value]]
        return match.group(0)

    body = _HEX.sub(swap_hex, body)
    body = _DARK_RGBA.sub(lambda m: f"{m.group(1)}{surface}", body)
    fills = (colors["accent"], colors["accent_hover"])
    on_fill = any(re.search(rf"(?<![-\w])background(?:-color)?:\s*{re.escape(fill)}", body, re.I) for fill in fills)

    def swap_text(match):
        value = match.group(2).lower()
        if on_fill:
            return f"{match.group(1)}{_on_accent(colors)}"
        if value in _LIGHT_TEXTS:
            return f"{match.group(1)}{colors['text']}"
        if value in _MUTED_TEXTS:
            return f"{match.group(1)}{colors['text_muted']}"
        return match.group(0)

    body = _TEXT_COLOR.sub(swap_text, body)
    if _is_light_surface(colors):
        ink = QColor(colors["text"])
        tone = f"{ink.red()}, {ink.green()}, {ink.blue()}"
        body = _TEXT_RGBA.sub(lambda m: f"{m.group(1)}rgba({tone}, {m.group(2)})", body)
        body = _WHITE_RGBA.sub(lambda m: f"rgba({tone}, {min(float(m.group(1)) * 1.6, 0.5):.3f})", body)
    return body


def recolor_stylesheet(css: str, colors: dict) -> str:
    """Stil kodunu kural kural geçerli temaya uyarlar."""
    if "{" not in css:
        return _recolor_rule("", css, colors)
    return _RULE.sub(lambda m: f"{m.group(1)}{{{_recolor_rule(m.group(1), m.group(2), colors)}}}", css)


def shape_stylesheet(css: str, style: str = "") -> str:
    """Bileşenin kendi stil kodundaki renk, köşe, boşluk ve yazı tipini arayüze uyarlar."""
    style = style or active_style()
    if not css:
        return css
    if _active_colors and (style != DEFAULT_STYLE or _is_light_surface(_active_colors)):
        css = recolor_stylesheet(css, _active_colors)
    if style == DEFAULT_STYLE:
        return css

    def radius(match):
        value = float(match.group(2))
        if style == "grafit":
            # Qt, yüksekliğin yarısını aşan köşe yarıçapını yok sayar; bu yüzden büyütme sınırlıdır.
            value = min(value * 1.6, 16) if 2 < value < 16 else value
        else:
            value = min(value, 8 if style == "atolye" else 2)
        return f"{match.group(1)}{value:g}px"

    scale = {"atolye": 1.0, "grafit": 1.2, "serit": 0.8}[style]

    def padding(match):
        parts = [f"{round(float(p[:-2]) * scale)}px" for p in match.group(2).split()]
        return f"{match.group(1)}{' '.join(parts)} "

    css = _PADDING.sub(padding, _RADIUS.sub(radius, css))
    return _FAMILY.sub(f"font-family: '{STYLE_FONTS[style]}'", css)


def install_stylesheet_shaper():
    """Tüm bileşenlerin stil kodlarını, özgün halini saklayarak arayüz biçimlendiricisinden geçirir."""
    global _raw_setter
    if _raw_setter is not None:
        return
    _raw_setter = QWidget.setStyleSheet

    def set_shaped(widget, css):
        widget.setProperty(_RAW_PROPERTY, css)
        _raw_setter(widget, shape_stylesheet(css))
        if _progress_hook:
            _progress_hook()

    QWidget.setStyleSheet = set_shaped


def set_progress_hook(hook, skip=None) -> None:
    """Uzun stil uygulamasında göstergeyi canlı tutacak işlevi ve atlanacak bileşen koşulunu atar."""
    global _progress_hook, _restyle_skip
    _progress_hook = hook
    _restyle_skip = skip


def apply_interface_style(colors: Optional[dict] = None) -> bool:
    """Yazı tipi, ikon çizimi, renk ve bileşen biçimlerini kayıtlı arayüze geçirir."""
    global _active_style, _active_colors, _classic_family
    style = get_interface_style()
    style_changed = style != _active_style
    colors_changed = colors is not None and colors != _active_colors
    changed = style_changed or colors_changed
    _active_style = style
    if colors is not None:
        _active_colors = colors
    set_glyph_style(style)
    app = QApplication.instance()
    if app is None or not changed:
        return changed
    if style_changed:
        font = app.font()
        if _classic_family is None:
            _classic_family = font.family()
        font.setFamily(STYLE_FONTS.get(style, _classic_family))
        app.setFont(font)
    if _raw_setter is not None:
        for widget in QApplication.allWidgets():
            raw = widget.property(_RAW_PROPERTY)
            if raw and not (_restyle_skip and _restyle_skip(widget)):
                _raw_setter(widget, shape_stylesheet(raw, style))
                if _progress_hook:
                    _progress_hook()
    return changed


def resolve_theme_for_style(theme_name: str, style: str = "") -> str:
    """Tema seçili arayüzle uyumsuzsa o arayüzün varsayılan temasını döner."""
    allowed = STYLE_THEMES.get(style or get_interface_style(), STYLE_THEMES[DEFAULT_STYLE])
    return theme_name if theme_name in allowed else allowed[0]


def get_checked_tool_css(theme_name: str) -> str:
    """Tema metin rengindeki ikonların okunması için seçili aracı açık tonla ve kenarlıkla gösterir."""
    colors = STYLE_THEME_COLORS.get(theme_name)
    if not colors:
        return ""
    return f"""
        QToolButton:checked {{
            background-color: {colors['accent_light']};
            border: 1.5px solid {colors['accent']};
        }}
    """


def get_style_css(theme_name: str, style: str = "") -> str:
    """Seçili arayüzün biçim kurallarını ve tema vurgusunun metin rengini üretir."""
    css = ""
    on_accent = STYLE_THEME_COLORS.get(theme_name, {}).get("on_accent")
    if on_accent:
        css += f"""
            QMenu::item:selected {{ color: {on_accent}; }}
            QPushButton:default {{ color: {on_accent}; }}
        """
    if _active_colors:
        c = _active_colors
        fill = c.get("surface", c["bg"])
        css += f"""
            QComboBox QAbstractItemView {{ selection-color: {_on_accent(c)}; }}
            QMessageBox {{ background-color: {c['bg']}; }}
            QMessageBox QLabel {{ color: {c['text']}; background: transparent; }}
            QMessageBox QPushButton {{
                background-color: {fill};
                color: {c['text']};
                border: 1px solid {c.get('border', fill)};
                padding: 6px 16px;
                min-width: 76px;
                min-height: 20px;
            }}
            QMessageBox QPushButton:hover {{ background-color: {c.get('surface_hover', fill)}; border-color: {c['accent']}; }}
            QMessageBox QPushButton:focus {{ border: 1.5px solid {c['accent']}; }}
            QMessageBox QPushButton:default {{
                background-color: {c['accent']};
                color: {_on_accent(c)};
                border: 1px solid {c['accent']};
            }}
        """
    shape = _STYLE_SHAPES.get(style or get_interface_style())
    if shape:
        css += f"""
            QPushButton {{ border-radius: {shape['btn']}px; }}
            QToolButton {{ border-radius: {shape['tool']}px; }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{ border-radius: {shape['input']}px; }}
            QGroupBox {{ border-radius: {shape['input']}px; }}
            QMenu {{ border-radius: {shape['menu']}px; }}
            QTabBar::tab {{ border-top-left-radius: {shape['tab']}px; border-top-right-radius: {shape['tab']}px; }}
        """
    return css
