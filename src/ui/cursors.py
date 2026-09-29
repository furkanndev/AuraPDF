from PyQt6.QtGui import (QCursor, QPixmap, QPainter, QColor, QPen, QBrush, 
                          QRadialGradient, QLinearGradient, QPainterPath, QPolygonF, QFont)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSettings
from typing import Optional, Union

# --- KULLANICI HAZIR İMLEÇ SETLERİ (CURSOR STYLE PRESETS) ---
CURSOR_PRESETS = {
    "apple": {
        "pen": "apple_pencil", "hl": "apple_chisel", "eraser": "apple_ring",
        "pointer": "apple_laser", "text": "macos_ibeam", "selection": "macos_reticle", "ruler": "ruler_crosshair"
    },
    "figma": {
        "pen": "figma_pen", "hl": "figma_marker", "eraser": "apple_ring",
        "pointer": "figma_pointer", "text": "macos_ibeam", "selection": "macos_reticle", "ruler": "ruler_crosshair"
    },
    "canva": {
        "pen": "canva_magic_pen", "hl": "flat_brush", "eraser": "sponge",
        "pointer": "canva_sparkle", "text": "feather", "selection": "lasso", "ruler": "draft_triangle"
    },
    "notion": {
        "pen": "notion_pen", "hl": "notion_marker", "eraser": "square",
        "pointer": "target", "text": "typewriter", "selection": "fine_cross", "ruler": "classic_ruler"
    },
    "vscode": {
        "pen": "vscode_pen", "hl": "notion_marker", "eraser": "cad_cross",
        "pointer": "vscode_pointer", "text": "vscode_ibeam", "selection": "fine_cross", "ruler": "draft_triangle"
    },
    "google_docs": {
        "pen": "docs_pen", "hl": "classic_marker", "eraser": "apple_ring",
        "pointer": "docs_pointer", "text": "classic_ibeam", "selection": "standard_cross", "ruler": "classic_ruler"
    },
    "vice_city": {
        "pen": "vice_city_pen", "hl": "vice_city_marker", "eraser": "vice_city_cube",
        "pointer": "vice_city_neon", "text": "vice_city_ibeam", "selection": "vice_city_reticle", "ruler": "ruler_crosshair"
    },
    "classic": {
        "pen": "classic_pen", "hl": "classic_marker", "eraser": "cad_cross",
        "pointer": "dot", "text": "classic_ibeam", "selection": "fine_cross", "ruler": "classic_ruler"
    },
    "precision": {
        "pen": "crosshair", "hl": "crosshair", "eraser": "dot",
        "pointer": "neon_ring", "text": "macos_ibeam", "selection": "macos_reticle", "ruler": "draft_triangle"
    },
    "system": {
        "pen": "arrow", "hl": "arrow", "eraser": "cad_cross",
        "pointer": "dot", "text": "classic_ibeam", "selection": "standard_cross", "ruler": "protractor"
    },
    "artist": {
        "pen": "brush_pen", "hl": "flat_brush", "eraser": "sponge",
        "pointer": "apple_glow_ring", "text": "feather", "selection": "lasso", "ruler": "ruler_crosshair"
    },
    "calligraphy": {
        "pen": "fountain_pen", "hl": "thick_marker", "eraser": "cleaning_brush",
        "pointer": "star", "text": "feather", "selection": "hand", "ruler": "classic_ruler"
    },
    "pixel_art": {
        "pen": "pixel", "hl": "thick_marker", "eraser": "solid_block",
        "pointer": "target", "text": "typewriter", "selection": "marquee", "ruler": "draft_triangle"
    },
    "neon": {
        "pen": "dot", "hl": "flat_brush", "eraser": "square",
        "pointer": "neon_ring", "text": "badge_ibeam", "selection": "macos_reticle", "ruler": "protractor"
    },
    "draftsman": {
        "pen": "classic_pen", "hl": "thick_marker", "eraser": "cad_cross",
        "pointer": "dot", "text": "classic_ibeam", "selection": "standard_cross", "ruler": "draft_triangle"
    },
    "minimalist": {
        "pen": "dot", "hl": "arrow", "eraser": "dot",
        "pointer": "apple_laser", "text": "macos_ibeam", "selection": "fine_cross", "ruler": "ruler_crosshair"
    },
    "heavy_duty": {
        "pen": "brush_pen", "hl": "thick_marker", "eraser": "solid_block",
        "pointer": "target", "text": "badge_ibeam", "selection": "marquee", "ruler": "classic_ruler"
    },
    "stealth": {
        "pen": "crosshair", "hl": "crosshair", "eraser": "dot",
        "pointer": "radar", "text": "macos_ibeam", "selection": "fine_cross", "ruler": "protractor"
    },
    "creative": {
        "pen": "fountain_pen", "hl": "flat_brush", "eraser": "sponge",
        "pointer": "star", "text": "feather", "selection": "lasso", "ruler": "draft_triangle"
    },
    "tactical": {
        "pen": "pixel", "hl": "classic_marker", "eraser": "square",
        "pointer": "target", "text": "typewriter", "selection": "marquee", "ruler": "classic_ruler"
    },
    "legacy": {
        "pen": "arrow", "hl": "arrow", "eraser": "cad_cross",
        "pointer": "arrow", "text": "classic_ibeam", "selection": "hand", "ruler": "classic_ruler"
    }
}


# --- TEMALARLA İMLEÇ SETLERİNİN AKILLI EŞLEŞTİRİLMESİ ---
THEME_CURSOR_MAPPINGS = {
    "dark": "apple",
    "vice_city": "vice_city",
    "gray": "apple",
    "navy": "apple",
    "emerald": "google_docs",
    "purple": "figma",
    "crimson": "canva",
    "nord": "vscode",
}

def get_recommended_preset_for_theme(theme_name: str) -> str:
    """Aktif temaya en uygun popüler imleç setini döner (Varsayılan: Apple)."""
    return THEME_CURSOR_MAPPINGS.get(theme_name, "apple")


# --- GELİŞMİŞ & ÖZELLEŞTİRİLEBİLİR İMLEÇ MOTORU (CUSTOMIZABLE CURSOR ENGINE) ---
class CursorFactory:
    """
    AuraPDF Apple tarzı, minimalist ve kullanıcı tarafından özelleştirilebilir imleç motoru.
    - Ayarlar menüsünden araç bazında imleç tipi (Apple Pencil, Klasik Kalem, Hassas Artı, Nokta, Sistem Oku vb.) seçilebilir.
    - Anti-aliasing ve retina netliğinde vektörel çizimler sunar.
    - Hem beyaz hem koyu PDF sayfalarında kusursuz kontrast sağlayan dual-tone konturlar ve hafif derinlik gölgeleri içerir.
    """

    @staticmethod
    def _get_setting(key: str, default: str) -> str:
        try:
            val = QSettings("AuraPDF", "PDFViewer").value(key, default)
            return str(val) if val else default
        except Exception:
            return default

    @staticmethod
    def _parse_color(col: Optional[Union[QColor, str]], default: str) -> QColor:
        if isinstance(col, QColor) and col.isValid():
            return col
        if isinstance(col, str) and col.strip():
            c = QColor(col.strip())
            if c.isValid():
                return c
        return QColor(default)

    # -------------------------------------------------------------
    # 1. ÇİZİM KALEMİ İMLECİ (PEN CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_pen_cursor(color: Optional[Union[QColor, str]] = None, size: int = 32, style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_pen", "apple_pencil")
        show_active_color = QSettings("AuraPDF", "PDFViewer").value("cursor_show_active_color", True, type=bool)

        if chosen_style == "vice_city_pen":
            pix = CursorFactory._draw_vice_city_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "figma_pen":
            pix = CursorFactory._draw_figma_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "canva_magic_pen":
            pix = CursorFactory._draw_canva_magic_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "notion_pen":
            pix = CursorFactory._draw_notion_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "vscode_pen":
            pix = CursorFactory._draw_vscode_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "docs_pen":
            pix = CursorFactory._draw_docs_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "arrow": return QCursor(Qt.CursorShape.ArrowCursor)
        if chosen_style == "crosshair": return CursorFactory._make_crosshair_cursor(size=28)
        if chosen_style == "dot": return CursorFactory._make_dot_cursor(color=color if show_active_color else None)
        if chosen_style in ("classic_pen", "fountain_pen"):
            pix = CursorFactory._draw_classic_pen_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "pixel": return CursorFactory._make_dot_cursor(color=color if show_active_color else None, radius=1.5, total_size=8)
        if chosen_style == "brush_pen":
            pix = CursorFactory._draw_apple_pencil_pix(color if show_active_color else None, int(size * 1.5))
            return QCursor(pix, 1, 1)

        pix = CursorFactory._draw_apple_pencil_pix(color if show_active_color else None, size)
        return QCursor(pix, 1, 1)

    @staticmethod
    def _draw_apple_pencil_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        ink = CursorFactory._parse_color(color, "#0071E3")

        # 1. Yumuşak derinlik gölgesi
        p.save()
        p.translate(1.2, 1.5)
        shadow = QPainterPath()
        shadow.moveTo(1.5, 1.5)
        shadow.lineTo(6.5, 3.0)
        shadow.lineTo(21.0, 17.5)
        shadow.quadTo(23.0, 19.5, 21.0, 21.5)
        shadow.quadTo(19.5, 23.0, 17.5, 21.0)
        shadow.lineTo(3.0, 6.5)
        shadow.closeSubpath()
        p.fillPath(shadow, QColor(0, 0, 0, 48))
        p.restore()

        # 2. Gövde (Mat seramik beyaz)
        body = QPainterPath()
        body.moveTo(5.5, 3.5)
        body.lineTo(19.0, 17.0)
        body.quadTo(21.0, 19.0, 19.5, 20.5)
        body.quadTo(19.0, 21.0, 17.0, 19.5)
        body.lineTo(3.5, 5.5)
        body.closeSubpath()

        b_grad = QLinearGradient(3.5, 5.5, 19.0, 19.0)
        b_grad.setColorAt(0.0, QColor("#FFFFFF"))
        b_grad.setColorAt(0.65, QColor("#F5F5F7"))
        b_grad.setColorAt(1.0, QColor("#E5E5EA"))
        p.setPen(QPen(QColor(45, 45, 48, 220), 0.85))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        # 3. Metalik Halka
        band = QPainterPath()
        band.moveTo(14.0, 12.0)
        band.lineTo(17.0, 15.0)
        band.lineTo(16.0, 16.0)
        band.lineTo(13.0, 13.0)
        band.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#8E8E93")))
        p.drawPath(band)

        # 4. Koni Uç
        cone = QPainterPath()
        cone.moveTo(1.2, 1.2)
        cone.lineTo(5.5, 3.5)
        cone.lineTo(3.5, 5.5)
        cone.closeSubpath()
        p.setPen(QPen(QColor(55, 55, 60, 220), 0.8))
        p.setBrush(QBrush(QColor("#ECECF0")))
        p.drawPath(cone)

        # 5. Mikro Hassas Uç
        tip = QPainterPath()
        tip.moveTo(1.0, 1.0)
        tip.lineTo(3.0, 1.8)
        tip.lineTo(1.8, 3.0)
        tip.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(25, 25, 28, 255)))
        p.drawPath(tip)

        # 6. Mücevher Renk Noktası
        p.setPen(QPen(QColor(255, 255, 255, 240), 0.75))
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(17.8, 17.8), 2.2, 2.2)

        p.end()
        return pix

    @staticmethod
    def _draw_classic_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gölge
        p.save()
        p.translate(1.0, 1.2)
        s = QPainterPath()
        s.moveTo(1.0, 1.0)
        s.lineTo(8.0, 2.5)
        s.lineTo(19.0, 13.5)
        s.lineTo(13.5, 19.0)
        s.lineTo(2.5, 8.0)
        s.closeSubpath()
        p.fillPath(s, QColor(0, 0, 0, 45))
        p.restore()

        # Klasik siyah dolmakalem ucu
        b = QPainterPath()
        b.moveTo(1.2, 1.2)
        b.lineTo(7.5, 2.5)
        b.lineTo(18.0, 13.0)
        b.lineTo(13.0, 18.0)
        b.lineTo(2.5, 7.5)
        b.closeSubpath()
        p.setPen(QPen(QColor(30, 30, 35, 225), 0.9))
        p.setBrush(QBrush(QColor("#242426")))
        p.drawPath(b)

        # Altın sarısı / seçili renkli hat
        accent_col = CursorFactory._parse_color(color, "#F1C40F")
        p.setPen(QPen(accent_col, 1.0))
        p.drawLine(QPointF(1.2, 1.2), QPointF(5.5, 5.5))
        p.setBrush(QBrush(accent_col))
        p.drawEllipse(QPointF(6.0, 6.0), 1.4, 1.4)

        p.end()
        return pix

    @staticmethod
    def _draw_vice_city_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.save()
        p.translate(1.0, 1.0)
        shadow = QPainterPath()
        shadow.moveTo(1.5, 1.5)
        shadow.lineTo(7.0, 3.5)
        shadow.lineTo(21.0, 17.5)
        shadow.quadTo(23.5, 20.0, 21.0, 22.0)
        shadow.quadTo(19.5, 23.5, 17.5, 21.0)
        shadow.lineTo(3.5, 7.0)
        shadow.closeSubpath()
        p.fillPath(shadow, QColor(255, 42, 133, 90))
        p.restore()

        body = QPainterPath()
        body.moveTo(5.5, 3.5)
        body.lineTo(19.0, 17.0)
        body.quadTo(21.0, 19.0, 19.5, 20.5)
        body.quadTo(19.0, 21.0, 17.0, 19.5)
        body.lineTo(3.5, 5.5)
        body.closeSubpath()

        b_grad = QLinearGradient(3.5, 5.5, 19.0, 19.0)
        b_grad.setColorAt(0.0, QColor('#FF2A85'))
        b_grad.setColorAt(0.5, QColor('#9B00E8'))
        b_grad.setColorAt(1.0, QColor('#00F0FF'))

        p.setPen(QPen(QColor(20, 0, 35, 230), 0.9))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        band = QPainterPath()
        band.moveTo(13.5, 11.5)
        band.lineTo(16.5, 14.5)
        band.lineTo(15.5, 15.5)
        band.lineTo(12.5, 12.5)
        band.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#FFE600')))
        p.drawPath(band)

        cone = QPainterPath()
        cone.moveTo(1.2, 1.2)
        cone.lineTo(5.5, 3.5)
        cone.lineTo(3.5, 5.5)
        cone.closeSubpath()
        p.setPen(QPen(QColor(20, 0, 35, 220), 0.8))
        p.setBrush(QBrush(QColor('#240E3B')))
        p.drawPath(cone)

        tip = QPainterPath()
        tip.moveTo(1.0, 1.0)
        tip.lineTo(3.2, 1.8)
        tip.lineTo(1.8, 3.2)
        tip.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#00F0FF')))
        p.drawPath(tip)

        ink = CursorFactory._parse_color(color, '#FF2A85')
        p.setPen(QPen(QColor('#FFFFFF'), 0.8))
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(18.0, 18.0), 2.2, 2.2)

        p.end()
        return pix

    # -------------------------------------------------------------
    # 2. VURGULAYICI / FOSFORLU KALEM İMLECİ (HIGHLIGHTER CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_highlighter_cursor(color: Optional[Union[QColor, str]] = None, size: int = 32, style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_hl", "apple_chisel")
        show_active_color = QSettings("AuraPDF", "PDFViewer").value("cursor_show_active_color", True, type=bool)

        if chosen_style == "vice_city_marker":
            pix = CursorFactory._draw_vice_city_marker_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "figma_marker":
            pix = CursorFactory._draw_figma_marker_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "notion_marker":
            pix = CursorFactory._draw_notion_marker_pix(color if show_active_color else None, size)
            return QCursor(pix, 1, 1)
        if chosen_style == "arrow": return QCursor(Qt.CursorShape.ArrowCursor)
        if chosen_style == "crosshair": return CursorFactory._make_crosshair_cursor(size=28)
        if chosen_style in ("classic_marker", "thick_marker"):
            pix = CursorFactory._draw_classic_marker_pix(color if show_active_color else None, int(size * 1.2) if chosen_style == "thick_marker" else size)
            return QCursor(pix, 1, 1)
        if chosen_style == "flat_brush":
            pix = CursorFactory._draw_apple_chisel_pix(color if show_active_color else None, int(size * 1.5))
            return QCursor(pix, 1, 1)

        pix = CursorFactory._draw_apple_chisel_pix(color if show_active_color else None, size)
        return QCursor(pix, 1, 1)

    @staticmethod
    def _draw_apple_chisel_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        hl_col = CursorFactory._parse_color(color, "#FFD60A")
        hl_tip_col = QColor(hl_col.red(), hl_col.green(), hl_col.blue(), 230)

        # 1. Ortam gölgesi
        p.save()
        p.translate(1.2, 1.5)
        shadow = QPainterPath()
        shadow.moveTo(1.5, 1.5)
        shadow.lineTo(6.5, 1.5)
        shadow.lineTo(21.0, 16.0)
        shadow.lineTo(16.0, 21.0)
        shadow.lineTo(1.5, 6.5)
        shadow.closeSubpath()
        p.fillPath(shadow, QColor(0, 0, 0, 42))
        p.restore()

        # 2. Buzlu cam gövde
        body = QPainterPath()
        body.moveTo(7.0, 5.0)
        body.lineTo(19.0, 17.0)
        body.lineTo(15.5, 20.5)
        body.lineTo(3.5, 8.5)
        body.closeSubpath()

        b_grad = QLinearGradient(3.5, 8.5, 19.0, 17.0)
        b_grad.setColorAt(0.0, QColor(255, 255, 255, 245))
        b_grad.setColorAt(0.6, QColor(242, 242, 247, 235))
        b_grad.setColorAt(1.0, QColor(220, 220, 230, 225))
        p.setPen(QPen(QColor(50, 50, 55, 200), 0.85))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        # 3. Metalik Halka
        band = QPainterPath()
        band.moveTo(15.0, 13.0)
        band.lineTo(18.0, 16.0)
        band.lineTo(16.8, 17.2)
        band.lineTo(13.8, 14.2)
        band.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#8E8E93")))
        p.drawPath(band)

        # 4. Kesik Uç (Beveled Chisel Blade)
        chisel = QPainterPath()
        chisel.moveTo(1.2, 1.2)
        chisel.lineTo(6.0, 1.2)
        chisel.lineTo(7.0, 5.0)
        chisel.lineTo(3.5, 8.5)
        chisel.lineTo(1.2, 4.5)
        chisel.closeSubpath()

        p.setPen(QPen(QColor(55, 55, 60, 190), 0.8))
        p.setBrush(QBrush(hl_tip_col))
        p.drawPath(chisel)

        # 5. Kesik bıçak kılavuz çizgisi
        p.setPen(QPen(QColor(30, 30, 35, 235), 1.1))
        p.drawLine(QPointF(1.2, 1.2), QPointF(5.5, 1.2))

        p.end()
        return pix

    @staticmethod
    def _draw_classic_marker_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        hl_col = CursorFactory._parse_color(color, "#FFEB3B")

        # Klasik sarı/renkli fosforlu gövde
        b = QPainterPath()
        b.moveTo(6.0, 5.0)
        b.lineTo(20.0, 19.0)
        b.lineTo(17.0, 22.0)
        b.lineTo(3.0, 8.0)
        b.closeSubpath()
        p.setPen(QPen(QColor(40, 40, 45, 220), 0.9))
        p.setBrush(QBrush(hl_col))
        p.drawPath(b)

        # Siyah uç tabanı ve kesik uç
        tip = QPainterPath()
        tip.moveTo(1.2, 1.2)
        tip.lineTo(6.0, 1.2)
        tip.lineTo(6.0, 5.0)
        tip.lineTo(3.0, 8.0)
        tip.lineTo(1.2, 4.0)
        tip.closeSubpath()
        p.setBrush(QBrush(QColor("#242426")))
        p.drawPath(tip)

        p.end()
        return pix

    @staticmethod
    def _draw_vice_city_marker_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        tip = QPainterPath()
        tip.moveTo(1.0, 1.0)
        tip.lineTo(6.5, 1.0)
        tip.lineTo(1.0, 6.5)
        tip.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#00F0FF')))
        p.drawPath(tip)

        body = QPainterPath()
        body.moveTo(5.0, 3.5)
        body.lineTo(19.0, 17.5)
        body.lineTo(16.5, 20.0)
        body.lineTo(2.5, 6.0)
        body.closeSubpath()
        grad = QLinearGradient(3.0, 3.0, 18.0, 18.0)
        grad.setColorAt(0.0, QColor('#FF2A85'))
        grad.setColorAt(1.0, QColor('#7928CA'))
        p.setPen(QPen(QColor(20, 0, 35, 230), 0.9))
        p.setBrush(QBrush(grad))
        p.drawPath(body)

        p.setPen(QPen(QColor('#00F0FF'), 1.2))
        p.drawLine(QPointF(7.0, 11.5), QPointF(11.5, 7.0))
        p.end()
        return pix

    # -------------------------------------------------------------
    # 3. SİLGİ İMLECİ (ERASER CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_eraser_cursor(size: int = 24, mode: str = "stroke", style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_eraser", "apple_ring")

        s = max(14, min(int(size), 72))
        pad = 6
        total = s + pad * 2
        center = total / 2.0

        if chosen_style == "vice_city_cube":
            pix = CursorFactory._draw_vice_city_cube_pix(s)
            return QCursor(pix, int(center), int(center))
        if chosen_style == "dot": return CursorFactory._make_dot_cursor(radius=3.0, total_size=int(total))
        if chosen_style == "sponge": return CursorFactory._make_dot_cursor(radius=s/2.0, total_size=int(total))
        if chosen_style in ("square", "solid_block"):
            pix = CursorFactory._draw_square_eraser_pix(s, pad, "fill" if chosen_style=="solid_block" else mode)
            return QCursor(pix, int(center), int(center))
        if chosen_style == "cad_cross":
            pix = CursorFactory._draw_cad_eraser_pix(s, pad, mode)
            return QCursor(pix, int(center), int(center))
        if chosen_style == "cleaning_brush":
            pix = CursorFactory._draw_apple_ring_eraser_pix(int(s*1.2), pad, "fill")
            return QCursor(pix, int(center), int(center))

        pix = CursorFactory._draw_apple_ring_eraser_pix(s, pad, mode)
        return QCursor(pix, int(center), int(center))

    @staticmethod
    def _draw_apple_ring_eraser_pix(s: int, pad: int, mode: str) -> QPixmap:
        total = s + pad * 2
        pix = QPixmap(total, total)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = total / 2.0
        radius = s / 2.0

        # Dış yumuşak gölge
        p.setPen(QPen(QColor(0, 0, 0, 55), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(center, center), radius + 0.5, radius + 0.5)

        # Koyu kontrast kontur
        p.setPen(QPen(QColor(20, 20, 25, 185), 1.6))
        p.drawEllipse(QPointF(center, center), radius, radius)

        # Beyaz iç halka ve cam dolgu
        p.setPen(QPen(QColor(255, 255, 255, 245), 1.2))
        fill = QColor(255, 255, 255, 45) if mode == "stroke" else QColor(255, 69, 58, 35)
        p.setBrush(QBrush(fill))
        p.drawEllipse(QPointF(center, center), radius - 0.5, radius - 0.5)

        # Merkez mikro hedef noktası
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 180)))
        p.drawEllipse(QPointF(center, center), 1.6, 1.6)
        p.setBrush(QBrush(QColor(255, 255, 255, 255)))
        p.drawEllipse(QPointF(center, center), 1.0, 1.0)

        p.end()
        return pix

    @staticmethod
    def _draw_cad_eraser_pix(s: int, pad: int, mode: str) -> QPixmap:
        total = s + pad * 2
        pix = QPixmap(total, total)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = total / 2.0
        radius = s / 2.0

        line_style = Qt.PenStyle.DashLine if mode == "stroke" else Qt.PenStyle.SolidLine
        fill_color = QColor(230, 230, 230, 100) if mode == "stroke" else QColor(255, 180, 180, 100)

        p.setPen(QPen(QColor(40, 40, 40, 220), 1.5, line_style))
        p.setBrush(QBrush(fill_color))
        p.drawEllipse(QPointF(center, center), radius, radius)

        # Merkez haç
        p.setPen(QPen(QColor(40, 40, 40, 190), 1.0))
        p.drawLine(QPointF(center - 3.5, center), QPointF(center + 3.5, center))
        p.drawLine(QPointF(center, center - 3.5), QPointF(center, center + 3.5))

        p.end()
        return pix

    @staticmethod
    def _draw_square_eraser_pix(s: int, pad: int, mode: str) -> QPixmap:
        total = s + pad * 2
        pix = QPixmap(total, total)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = total / 2.0
        half = s / 2.0
        rect = QRectF(c - half, c - half, s, s)

        # Gölge
        p.setPen(QPen(QColor(0, 0, 0, 55), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 3, 3)

        # Koyu kontur
        p.setPen(QPen(QColor(20, 20, 25, 185), 1.6))
        p.drawRoundedRect(rect, 3, 3)

        # Beyaz iç çerçeve ve cam dolgusu
        p.setPen(QPen(QColor(255, 255, 255, 245), 1.2))
        fill = QColor(255, 255, 255, 45) if mode == "stroke" else QColor(255, 69, 58, 35)
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 2.5, 2.5)

        # Merkez mikro nokta
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 180)))
        p.drawEllipse(QPointF(c, c), 1.6, 1.6)
        p.setBrush(QBrush(QColor(255, 255, 255, 255)))
        p.drawEllipse(QPointF(c, c), 1.0, 1.0)

        p.end()
        return pix

    @staticmethod
    def _draw_vice_city_cube_pix(s: int = 24) -> QPixmap:
        size = max(32, s + 12)
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = size / 2.0
        hw = max(7.0, s / 2.0)
        r = QRectF(c - hw, c - hw, hw * 2, hw * 2)
        p.setPen(QPen(QColor('#FF2A85'), 2.0))
        p.setBrush(QBrush(QColor(36, 14, 59, 215)))
        p.drawRoundedRect(r, 3, 3)

        p.setPen(QPen(QColor('#00F0FF'), 1.4))
        p.drawLine(QPointF(c, c - hw), QPointF(c + hw, c))
        p.drawLine(QPointF(c + hw, c), QPointF(c, c + hw))
        p.drawLine(QPointF(c, c + hw), QPointF(c - hw, c))
        p.drawLine(QPointF(c - hw, c), QPointF(c, c - hw))
        p.end()
        return pix

    # -------------------------------------------------------------
    # 4. LAZER İŞARETÇİ İMLECİ (LASER POINTER CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_pointer_cursor(color: Optional[Union[QColor, str]] = None, style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_pointer", "apple_laser")

        if chosen_style == "vice_city_neon":
            pix = CursorFactory._draw_vice_city_pointer_pix()
            return QCursor(pix, 16, 16)
        if chosen_style == "figma_pointer":
            pix = CursorFactory._draw_figma_pointer_pix(color)
            return QCursor(pix, 1, 1)
        if chosen_style == "canva_sparkle":
            pix = CursorFactory._draw_canva_sparkle_pix(color)
            return QCursor(pix, 16, 16)
        if chosen_style == "vscode_pointer":
            pix = CursorFactory._draw_vscode_pointer_pix(color)
            return QCursor(pix, 2, 2)
        if chosen_style == "docs_pointer":
            pix = CursorFactory._draw_docs_pointer_pix(color)
            return QCursor(pix, 16, 16)
        if chosen_style in ("apple_glow_ring", "radar"):
            pix = CursorFactory._draw_apple_glow_ring_pix(color)
            return QCursor(pix, 16, 16)

        if chosen_style in ("neon_ring", "target"):
            pix = CursorFactory._draw_neon_ring_pointer_pix(color)
            return QCursor(pix, 16, 16)

        if chosen_style == "arrow":
            return QCursor(Qt.CursorShape.ArrowCursor)

        if chosen_style == "dot":
            pix = CursorFactory._draw_compact_dot_pointer_pix(color)
            return QCursor(pix, 16, 16)

        if chosen_style == "star":
            return QCursor(Qt.CursorShape.CrossCursor)

        pix = CursorFactory._draw_apple_laser_pix(color)
        return QCursor(pix, 16, 16)

    @staticmethod
    def _draw_apple_laser_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = size / 2.0
        core_col = CursorFactory._parse_color(color, "#FF2D55")

        # 1. Yumuşak optik hale (Apple Keynote diffuse bloom)
        g_glow = QRadialGradient(c, c, 12.5)
        g_glow.setColorAt(0.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 130))
        g_glow.setColorAt(0.45, QColor(core_col.red(), core_col.green(), core_col.blue(), 55))
        g_glow.setColorAt(1.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g_glow))
        p.drawEllipse(QPointF(c, c), 12.5, 12.5)

        # 2. İnce yüksek kontrast dış halka (açık/koyu sayfalarda kusursuz görünürlük)
        p.setPen(QPen(QColor(0, 0, 0, 60), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(c, c), 5.6, 5.6)

        # 3. Canlı lazer çekirdeği (Apple Luminous Core)
        g_core = QRadialGradient(c, c, 5.0)
        g_core.setColorAt(0.0, QColor(255, 255, 255, 255))
        g_core.setColorAt(0.35, core_col)
        g_core.setColorAt(1.0, QColor(max(0, core_col.red() - 25), max(0, core_col.green() - 25), max(0, core_col.blue() - 25), 230))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g_core))
        p.drawEllipse(QPointF(c, c), 4.8, 4.8)

        # 4. Saf beyaz foton/diyot merkezi
        p.setBrush(QBrush(QColor(255, 255, 255, 255)))
        p.drawEllipse(QPointF(c, c), 1.8, 1.8)

        p.end()
        return pix

    @staticmethod
    def _draw_apple_glow_ring_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        """Apple iPadOS / Sunum halka lazer imleci (buzlu cam halka ve parlak merkez)"""
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = size / 2.0
        core_col = CursorFactory._parse_color(color, "#FF2D55")

        # Dış gölge
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 45)))
        p.drawEllipse(QPointF(c + 0.5, c + 0.5), 8.5, 8.5)

        # Buzlu cam / yarı saydam halka gövdesi
        p.setPen(QPen(QColor(core_col.red(), core_col.green(), core_col.blue(), 210), 1.4))
        p.setBrush(QBrush(QColor(core_col.red(), core_col.green(), core_col.blue(), 35)))
        p.drawEllipse(QPointF(c, c), 8.0, 8.0)

        # Merkez lazer noktası
        p.setPen(QPen(QColor(255, 255, 255, 230), 0.8))
        p.setBrush(QBrush(core_col))
        p.drawEllipse(QPointF(c, c), 3.2, 3.2)

        # Beyaz diyot ucu
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 255)))
        p.drawEllipse(QPointF(c, c), 1.4, 1.4)

        p.end()
        return pix

    @staticmethod
    def _draw_neon_ring_pointer_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = size / 2.0
        core_col = CursorFactory._parse_color(color, "#FF1744")

        # Neon halka ve 4 çentik
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.2))
        p.drawEllipse(QPointF(c, c), 6.5, 6.5)

        p.setPen(QPen(core_col, 1.5))
        p.drawLine(QPointF(c, 7), QPointF(c, 9))
        p.drawLine(QPointF(c, 23), QPointF(c, 25))
        p.drawLine(QPointF(7, c), QPointF(9, c))
        p.drawLine(QPointF(23, c), QPointF(25, c))

        # Çekirdek nokta
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core_col))
        p.drawEllipse(QPointF(c, c), 3.5, 3.5)
        p.setBrush(QBrush(QColor(255, 255, 255, 255)))
        p.drawEllipse(QPointF(c, c), 1.8, 1.8)

        p.end()
        return pix

    @staticmethod
    def _draw_compact_dot_pointer_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = size / 2.0
        core_col = CursorFactory._parse_color(color, "#FF2D55")

        p.setPen(QPen(QColor(255, 255, 255, 240), 1.0))
        p.setBrush(QBrush(core_col))
        p.drawEllipse(QPointF(c, c), 4.0, 4.0)

        p.end()
        return pix

    @staticmethod
    def _draw_vice_city_pointer_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = 16.0, 16.0
        p.setPen(QPen(QColor('#FF2A85'), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 11.0, 11.0)
        p.setPen(QPen(QColor('#00F0FF'), 1.5))
        p.drawEllipse(QPointF(cx, cy), 5.5, 5.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.drawEllipse(QPointF(cx, cy), 2.0, 2.0)
        p.end()
        return pix

    # -------------------------------------------------------------
    # 5. METİN İMLECİ (TEXT CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_text_cursor(style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_text", "macos_ibeam")

        if chosen_style == "vice_city_ibeam":
            pix = CursorFactory._draw_vice_city_ibeam_pix()
            return QCursor(pix, 16, 16)
        if chosen_style == "vscode_ibeam":
            pix = CursorFactory._draw_vscode_ibeam_pix()
            return QCursor(pix, 16, 16)
        if chosen_style in ("classic_ibeam", "typewriter"): return QCursor(Qt.CursorShape.IBeamCursor)
        if chosen_style == "feather": return QCursor(Qt.CursorShape.UpArrowCursor)
        if chosen_style == "badge_ibeam":
            pix = CursorFactory._draw_badge_ibeam_pix()
            return QCursor(pix, 16, 16)

        pix = CursorFactory._draw_macos_ibeam_pix()
        return QCursor(pix, 16, 16)

    @staticmethod
    def _draw_macos_ibeam_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = 16.0
        # Beyaz dış kontur
        p.setPen(QPen(QColor(255, 255, 255, 245), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c - 4.5, 7.5), QPointF(c + 4.5, 7.5))
        p.drawLine(QPointF(c, 7.5), QPointF(c, 24.5))
        p.drawLine(QPointF(c - 4.5, 24.5), QPointF(c + 4.5, 24.5))

        # Koyu çekirdek çizgi
        p.setPen(QPen(QColor(22, 22, 26, 235), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c - 4.5, 7.5), QPointF(c + 4.5, 7.5))
        p.drawLine(QPointF(c, 7.5), QPointF(c, 24.5))
        p.drawLine(QPointF(c - 4.5, 24.5), QPointF(c + 4.5, 24.5))

        p.end()
        return pix

    @staticmethod
    def _draw_badge_ibeam_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = 13.0
        # I-Beam
        p.setPen(QPen(QColor(255, 255, 255, 240), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c - 3.5, 8), QPointF(c + 3.5, 8))
        p.drawLine(QPointF(c, 8), QPointF(c, 24))
        p.drawLine(QPointF(c - 3.5, 24), QPointF(c + 3.5, 24))

        p.setPen(QPen(QColor(20, 20, 25, 235), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c - 3.5, 8), QPointF(c + 3.5, 8))
        p.drawLine(QPointF(c, 8), QPointF(c, 24))
        p.drawLine(QPointF(c - 3.5, 24), QPointF(c + 3.5, 24))

        # 'A' rozeti
        badge_rect = QRectF(19, 7, 10, 10)
        p.setPen(QPen(QColor(255, 255, 255, 240), 0.8))
        p.setBrush(QBrush(QColor("#0071E3")))
        p.drawRoundedRect(badge_rect, 2, 2)

        p.setPen(QPen(QColor(255, 255, 255), 1.0))
        font = p.font()
        font.setPixelSize(8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "A")

        p.end()
        return pix

    @staticmethod
    def _draw_vice_city_ibeam_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = 16.0
        p.setPen(QPen(QColor(0, 0, 0, 180), 3.0))
        p.drawLine(QPointF(cx - 5, 5), QPointF(cx + 5, 5))
        p.drawLine(QPointF(cx, 5), QPointF(cx, 21))
        p.drawLine(QPointF(cx - 5, 21), QPointF(cx + 5, 21))
        p.setPen(QPen(QColor('#FF2A85'), 1.8))
        p.drawLine(QPointF(cx, 5), QPointF(cx, 21))
        p.setPen(QPen(QColor('#00F0FF'), 1.8))
        p.drawLine(QPointF(cx - 4, 5), QPointF(cx + 4, 5))
        p.drawLine(QPointF(cx - 4, 21), QPointF(cx + 4, 21))
        p.end()
        return pix

    # -------------------------------------------------------------
    # 6. SEÇİM ARACI İMLECİ (SELECTION TOOL CURSOR)
    # -------------------------------------------------------------
    @staticmethod
    def get_selection_cursor(mode: str = "rect", style: Optional[str] = None) -> QCursor:
        if mode == "move": return CursorFactory.get_move_cursor()
        elif mode == "pan": return CursorFactory.get_pan_cursor()

        chosen_style = style or CursorFactory._get_setting("cursor_selection", "macos_reticle")

        if chosen_style == "vice_city_reticle":
            pix = CursorFactory._draw_vice_city_reticle_pix()
            return QCursor(pix, 16, 16)
        if chosen_style == "standard_cross": return QCursor(Qt.CursorShape.CrossCursor)
        if chosen_style in ("fine_cross", "marquee"): return CursorFactory._make_crosshair_cursor(size=32)
        if chosen_style == "hand": return QCursor(Qt.CursorShape.OpenHandCursor)

        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = 16.0
        if mode == "lasso" or chosen_style == "lasso":
            p.setPen(QPen(QColor(0, 0, 0, 70), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, 6), QPointF(c, 12))
            p.drawLine(QPointF(c, 20), QPointF(c, 26))
            p.drawLine(QPointF(6, c), QPointF(12, c))
            p.drawLine(QPointF(20, c), QPointF(26, c))

            p.setPen(QPen(QColor(255, 255, 255, 240), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, 6), QPointF(c, 12))
            p.drawLine(QPointF(c, 20), QPointF(c, 26))
            p.drawLine(QPointF(6, c), QPointF(12, c))
            p.drawLine(QPointF(20, c), QPointF(26, c))

            p.setPen(QPen(QColor(20, 20, 24, 235), 0.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, 6), QPointF(c, 12))
            p.drawLine(QPointF(c, 20), QPointF(c, 26))
            p.drawLine(QPointF(6, c), QPointF(12, c))
            p.drawLine(QPointF(20, c), QPointF(26, c))

            # Lasso rozeti
            lasso_path = QPainterPath()
            lasso_path.addEllipse(QPointF(22, 22), 4.5, 3.2)
            p.setPen(QPen(QColor(255, 255, 255, 240), 1.8))
            p.drawPath(lasso_path)
            p.setPen(QPen(QColor(0, 113, 227, 240), 1.0, Qt.PenStyle.DashLine))
            p.drawPath(lasso_path)
        else:
            # macOS Screenshot Retikülü
            p.setPen(QPen(QColor(0, 0, 0, 75), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, c - 9), QPointF(c, c - 3))
            p.drawLine(QPointF(c, c + 3), QPointF(c, c + 9))
            p.drawLine(QPointF(c - 9, c), QPointF(c - 3, c))
            p.drawLine(QPointF(c + 3, c), QPointF(c + 9, c))
            p.drawEllipse(QPointF(c, c), 4.5, 4.5)

            p.setPen(QPen(QColor(255, 255, 255, 240), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, c - 9), QPointF(c, c - 3))
            p.drawLine(QPointF(c, c + 3), QPointF(c, c + 9))
            p.drawLine(QPointF(c - 9, c), QPointF(c - 3, c))
            p.drawLine(QPointF(c + 3, c), QPointF(c + 9, c))
            p.drawEllipse(QPointF(c, c), 4.5, 4.5)

            p.setPen(QPen(QColor(22, 22, 26, 235), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(c, c - 9), QPointF(c, c - 3))
            p.drawLine(QPointF(c, c + 3), QPointF(c, c + 9))
            p.drawLine(QPointF(c - 9, c), QPointF(c - 3, c))
            p.drawLine(QPointF(c + 3, c), QPointF(c + 9, c))
            p.drawEllipse(QPointF(c, c), 4.5, 4.5)

        p.end()
        return QCursor(pix, 16, 16)

    @staticmethod
    def _draw_vice_city_reticle_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = 16.0, 16.0
        p.setPen(QPen(QColor('#FF2A85'), 1.8))
        d, arm = 9.0, 4.0
        p.drawLine(QPointF(cx - d, cy - d), QPointF(cx - d + arm, cy - d))
        p.drawLine(QPointF(cx - d, cy - d), QPointF(cx - d, cy - d + arm))
        p.drawLine(QPointF(cx + d, cy - d), QPointF(cx + d - arm, cy - d))
        p.drawLine(QPointF(cx + d, cy - d), QPointF(cx + d, cy - d + arm))
        p.drawLine(QPointF(cx - d, cy + d), QPointF(cx - d + arm, cy + d))
        p.drawLine(QPointF(cx - d, cy + d), QPointF(cx - d, cy - d + arm))
        p.drawLine(QPointF(cx + d, cy + d), QPointF(cx + d - arm, cy + d))
        p.drawLine(QPointF(cx + d, cy + d), QPointF(cx + d, cy - d + arm))
        p.setPen(QPen(QColor('#00F0FF'), 1.4))
        p.drawLine(QPointF(cx - 3, cy), QPointF(cx + 3, cy))
        p.drawLine(QPointF(cx, cy - 3), QPointF(cx, cy + 3))
        p.end()
        return pix

    # -------------------------------------------------------------
    # 7. GENEL YARDIMCI VEKTÖREL İMLEÇLER
    # -------------------------------------------------------------
    @staticmethod
    def _make_crosshair_cursor(size: int = 32) -> QCursor:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = size / 2.0
        # Beyaz dış hat
        p.setPen(QPen(QColor(255, 255, 255, 240), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c, c - 8), QPointF(c, c - 2))
        p.drawLine(QPointF(c, c + 2), QPointF(c, c + 8))
        p.drawLine(QPointF(c - 8, c), QPointF(c - 2, c))
        p.drawLine(QPointF(c + 2, c), QPointF(c + 8, c))

        # Koyu iç hat
        p.setPen(QPen(QColor(20, 20, 25, 235), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c, c - 8), QPointF(c, c - 2))
        p.drawLine(QPointF(c, c + 2), QPointF(c, c + 8))
        p.drawLine(QPointF(c - 8, c), QPointF(c - 2, c))
        p.drawLine(QPointF(c + 2, c), QPointF(c + 2, c))

        p.end()
        return QCursor(pix, int(c), int(c))

    @staticmethod
    def _make_dot_cursor(color: Optional[Union[QColor, str]] = None, radius: float = 2.5, total_size: int = 24) -> QCursor:
        pix = QPixmap(total_size, total_size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = total_size / 2.0
        col = CursorFactory._parse_color(color, "#1D1D1F")

        p.setPen(QPen(QColor(255, 255, 255, 240), 1.2))
        p.setBrush(QBrush(col))
        p.drawEllipse(QPointF(c, c), radius, radius)

        p.end()
        return QCursor(pix, int(c), int(c))

    @staticmethod
    def get_move_cursor() -> QCursor:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = 16.0
        p.setPen(QPen(QColor(0, 0, 0, 70), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c, 5), QPointF(c, 27))
        p.drawLine(QPointF(5, c), QPointF(27, c))

        p.setPen(QPen(QColor(255, 255, 255, 240), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c, 5), QPointF(c, 27))
        p.drawLine(QPointF(5, c), QPointF(27, c))

        p.setPen(QPen(QColor(25, 25, 30, 235), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(c, 5), QPointF(c, 27))
        p.drawLine(QPointF(5, c), QPointF(27, c))

        for angle in (0, 90, 180, 270):
            p.save()
            p.translate(c, c)
            p.rotate(angle)
            arrow = QPolygonF([QPointF(0, -11), QPointF(-3, -8), QPointF(3, -8)])
            p.setPen(QPen(QColor(25, 25, 30, 235), 0.8))
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawPolygon(arrow)
            p.restore()

        p.end()
        return QCursor(pix, 16, 16)

    @staticmethod
    def get_pan_cursor() -> QCursor:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        hand = QPainterPath()
        hand.moveTo(11, 10)
        hand.lineTo(11, 5)
        hand.quadTo(12.5, 3.5, 14, 5)
        hand.lineTo(14, 10)
        hand.lineTo(14, 4)
        hand.quadTo(15.5, 2.5, 17, 4)
        hand.lineTo(17, 10)
        hand.lineTo(17, 6)
        hand.quadTo(18.5, 4.5, 20, 6)
        hand.lineTo(20, 12)
        hand.lineTo(20, 9)
        hand.quadTo(21.5, 7.5, 23, 9)
        hand.lineTo(23, 17)
        hand.quadTo(23, 23, 19, 26)
        hand.lineTo(13, 26)
        hand.quadTo(8, 24, 8, 19)
        hand.lineTo(8, 14)
        hand.quadTo(6, 12, 7.5, 10.5)
        hand.quadTo(9, 9, 11, 13)
        hand.closeSubpath()

        p.save()
        p.translate(1.0, 1.2)
        p.fillPath(hand, QColor(0, 0, 0, 45))
        p.restore()

        p.setPen(QPen(QColor(30, 30, 35, 220), 0.9))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawPath(hand)

        p.end()
        return QCursor(pix, 14, 12)

    @staticmethod
    def get_closed_hand_cursor() -> QCursor:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        fist = QPainterPath()
        fist.moveTo(11, 12)
        fist.quadTo(12, 8, 14, 10)
        fist.quadTo(15, 8, 17, 10)
        fist.quadTo(18, 8, 20, 10)
        fist.quadTo(21, 9, 22.5, 11.5)
        fist.lineTo(22.5, 16)
        fist.quadTo(22.5, 22, 18, 24)
        fist.lineTo(13, 24)
        fist.quadTo(9, 22, 9, 17)
        fist.quadTo(8, 12, 11, 12)
        fist.closeSubpath()

        p.save()
        p.translate(1.0, 1.2)
        p.fillPath(fist, QColor(0, 0, 0, 45))
        p.restore()

        p.setPen(QPen(QColor(30, 30, 35, 220), 0.9))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawPath(fist)

        p.end()
        return QCursor(pix, 15, 15)

    @staticmethod
    def get_ruler_cursor(style: Optional[str] = None) -> QCursor:
        chosen_style = style or CursorFactory._get_setting("cursor_ruler", "ruler_crosshair")
        
        if chosen_style == "classic_ruler": return QCursor(Qt.CursorShape.SizeAllCursor)
        if chosen_style == "draft_triangle": return QCursor(Qt.CursorShape.UpArrowCursor)
        if chosen_style == "protractor": return QCursor(Qt.CursorShape.CrossCursor)
        
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Hassas artı merkezi (12, 12)
        cx, cy = 12.0, 12.0
        
        # Gölge / kontrast hattı (Siyah)
        p.setPen(QPen(QColor(0, 0, 0, 180), 2.2))
        p.drawLine(QPointF(cx - 9, cy), QPointF(cx - 2, cy))
        p.drawLine(QPointF(cx + 2, cy), QPointF(cx + 9, cy))
        p.drawLine(QPointF(cx, cy - 9), QPointF(cx, cy - 2))
        p.drawLine(QPointF(cx, cy + 2), QPointF(cx, cy + 9))

        # Beyaz iç hat
        p.setPen(QPen(QColor(255, 255, 255, 245), 1.2))
        p.drawLine(QPointF(cx - 8, cy), QPointF(cx - 2, cy))
        p.drawLine(QPointF(cx + 2, cy), QPointF(cx + 8, cy))
        p.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy - 2))
        p.drawLine(QPointF(cx, cy + 2), QPointF(cx, cy + 8))

        # Merkez açık mavi aksan noktası
        p.setPen(QPen(QColor(14, 165, 233, 230), 1.2))
        p.drawPoint(QPointF(cx, cy))

        # 2. Sağ alt mini cetvel ikonu
        rx, ry, rw, rh = 16.0, 16.0, 14.0, 9.0
        p.setPen(QPen(QColor(0, 0, 0, 160), 1.0))
        p.setBrush(QBrush(QColor(30, 41, 59, 230)))
        p.drawRoundedRect(QRectF(rx, ry, rw, rh), 2.0, 2.0)

        # Üst çentikler
        p.setPen(QPen(QColor(56, 189, 248, 230), 1.0))
        p.drawLine(QPointF(rx + 2.5, ry + 1.5), QPointF(rx + 2.5, ry + 5.0))
        p.drawLine(QPointF(rx + 5.5, ry + 1.5), QPointF(rx + 5.5, ry + 3.5))
        p.drawLine(QPointF(rx + 8.5, ry + 1.5), QPointF(rx + 8.5, ry + 5.0))
        p.drawLine(QPointF(rx + 11.5, ry + 1.5), QPointF(rx + 11.5, ry + 3.5))

        p.end()
        return QCursor(pix, int(cx), int(cy))

    # -------------------------------------------------------------
    # 8. ÖNİZLEME VE AYARLAR İÇİN PİKSEL RESMİ ALMA
    # -------------------------------------------------------------
    @staticmethod
    def get_cursor_for_tool(tool: str, color=None, size: int = 24, style: Optional[str] = None) -> QCursor:
        """Belirtilen araç ve stile uygun QCursor nesnesini döner."""
        if tool == "pen":
            return CursorFactory.get_pen_cursor(color=color, style=style)
        elif tool == "highlighter":
            return CursorFactory.get_highlighter_cursor(color=color, style=style)
        elif tool == "eraser":
            return CursorFactory.get_eraser_cursor(size=size, style=style)
        elif tool == "pointer":
            return CursorFactory.get_pointer_cursor(color=color, style=style)
        elif tool == "text":
            return CursorFactory.get_text_cursor(style=style)
        elif tool in ("selection_tool", "selection"):
            return CursorFactory.get_selection_cursor(mode="rect", style=style)
        elif tool == "pan":
            return CursorFactory.get_pan_cursor()
        elif tool == "ruler":
            return CursorFactory.get_ruler_cursor(style=style)
        return QCursor(Qt.CursorShape.ArrowCursor)

    # -------------------------------------------------------------
    # 9. POPÜLER SİTE VE PLATFORMLARDAN ESİNLENEN VEKTÖREL ÇİZİMLER
    # -------------------------------------------------------------
    @staticmethod
    def _draw_figma_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        ink = CursorFactory._parse_color(color, "#A855F7")

        # 1. Gölge
        p.save()
        p.translate(1.2, 1.2)
        shadow = QPainterPath()
        shadow.moveTo(1.5, 1.5)
        shadow.lineTo(6.5, 2.5)
        shadow.lineTo(19.0, 15.0)
        shadow.lineTo(15.0, 19.0)
        shadow.lineTo(2.5, 6.5)
        shadow.closeSubpath()
        p.fillPath(shadow, QColor(0, 0, 0, 45))
        p.restore()

        # 2. Figma Metal Nib (Fountain / Vector Pen Tool)
        nib = QPainterPath()
        nib.moveTo(1.2, 1.2)
        nib.lineTo(6.0, 2.8)
        nib.lineTo(12.0, 8.8)
        nib.lineTo(8.8, 12.0)
        nib.lineTo(2.8, 6.0)
        nib.closeSubpath()

        nib_grad = QLinearGradient(1.2, 1.2, 12.0, 12.0)
        nib_grad.setColorAt(0.0, QColor("#F8FAFC"))
        nib_grad.setColorAt(0.5, QColor("#CBD5E1"))
        nib_grad.setColorAt(1.0, QColor("#94A3B8"))
        p.setPen(QPen(QColor("#334155"), 0.9))
        p.setBrush(QBrush(nib_grad))
        p.drawPath(nib)

        # Nib slit & Breather hole
        p.setPen(QPen(QColor("#1E293B"), 0.9))
        p.drawLine(QPointF(1.2, 1.2), QPointF(5.5, 5.5))
        p.setPen(QPen(QColor("#334155"), 0.8))
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(5.5, 5.5), 1.3, 1.3)

        # 3. Stylus Gövdesi (Figma Koyu Kömür & Mor Aksan)
        body = QPainterPath()
        body.moveTo(10.5, 7.5)
        body.lineTo(20.0, 17.0)
        body.quadTo(22.0, 19.0, 20.5, 20.5)
        body.quadTo(19.0, 22.0, 17.0, 20.0)
        body.lineTo(7.5, 10.5)
        body.closeSubpath()

        body_grad = QLinearGradient(7.5, 7.5, 20.0, 20.0)
        body_grad.setColorAt(0.0, QColor("#27272A"))
        body_grad.setColorAt(0.7, QColor("#18181B"))
        body_grad.setColorAt(1.0, QColor("#09090B"))
        p.setPen(QPen(QColor("#52525B"), 0.8))
        p.setBrush(QBrush(body_grad))
        p.drawPath(body)

        p.setPen(QPen(ink, 1.5))
        p.drawLine(QPointF(9.5, 11.5), QPointF(11.5, 9.5))

        p.end()
        return pix

    @staticmethod
    def _draw_figma_marker_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        hl_col = CursorFactory._parse_color(color, "#C084FC")

        p.save()
        p.translate(1.0, 1.2)
        s_path = QPainterPath()
        s_path.moveTo(1.5, 1.5)
        s_path.lineTo(7.5, 2.0)
        s_path.lineTo(19.0, 13.5)
        s_path.lineTo(13.5, 19.0)
        s_path.lineTo(2.0, 7.5)
        s_path.closeSubpath()
        p.fillPath(s_path, QColor(0, 0, 0, 40))
        p.restore()

        body = QPainterPath()
        body.moveTo(5.0, 5.0)
        body.lineTo(18.0, 18.0)
        body.lineTo(15.0, 21.0)
        body.lineTo(2.0, 8.0)
        body.closeSubpath()

        p.setPen(QPen(QColor("#475569"), 0.8))
        p.setBrush(QBrush(QColor("#F1F5F9")))
        p.drawPath(body)

        tip = QPainterPath()
        tip.moveTo(1.2, 1.2)
        tip.lineTo(6.5, 3.5)
        tip.lineTo(3.5, 6.5)
        tip.closeSubpath()

        p.setPen(QPen(QColor(0, 0, 0, 80), 0.7))
        p.setBrush(QBrush(hl_col))
        p.drawPath(tip)

        p.end()
        return pix

    @staticmethod
    def _draw_figma_pointer_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ptr_col = CursorFactory._parse_color(color, "#A855F7")

        arrow = QPainterPath()
        arrow.moveTo(1.0, 1.0)
        arrow.lineTo(1.0, 15.0)
        arrow.lineTo(4.5, 11.5)
        arrow.lineTo(8.5, 18.5)
        arrow.lineTo(11.0, 17.0)
        arrow.lineTo(7.0, 10.0)
        arrow.lineTo(12.0, 10.0)
        arrow.closeSubpath()

        p.save()
        p.translate(1.0, 1.2)
        p.fillPath(arrow, QColor(0, 0, 0, 60))
        p.restore()

        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.setBrush(QBrush(ptr_col))
        p.drawPath(arrow)

        badge = QPainterPath()
        badge.addRoundedRect(QRectF(9.0, 12.0, 18.0, 10.0), 3.0, 3.0)
        p.setPen(QPen(QColor("#FFFFFF"), 0.9))
        p.setBrush(QBrush(ptr_col))
        p.drawPath(badge)

        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(9.0, 12.0, 18.0, 10.0), Qt.AlignmentFlag.AlignCenter, "YOU")

        p.end()
        return pix

    @staticmethod
    def _draw_canva_magic_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        body = QPainterPath()
        body.moveTo(4.5, 4.5)
        body.lineTo(18.0, 18.0)
        body.lineTo(16.0, 20.0)
        body.lineTo(2.5, 6.5)
        body.closeSubpath()

        b_grad = QLinearGradient(2.5, 2.5, 18.0, 18.0)
        b_grad.setColorAt(0.0, QColor("#F43F5E"))
        b_grad.setColorAt(0.5, QColor("#8B5CF6"))
        b_grad.setColorAt(1.0, QColor("#EC4899"))

        p.setPen(QPen(QColor("#FFFFFF"), 0.8))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        band = QPainterPath()
        band.moveTo(4.5, 4.5)
        band.lineTo(6.5, 6.5)
        band.lineTo(5.5, 7.5)
        band.lineTo(3.5, 5.5)
        band.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FBBF24")))
        p.drawPath(band)

        def draw_sparkle(cx, cy, r_outer, r_inner, col):
            sp = QPainterPath()
            sp.moveTo(cx, cy - r_outer)
            sp.quadTo(cx, cy, cx + r_inner, cy)
            sp.lineTo(cx + r_outer, cy)
            sp.quadTo(cx, cy, cx, cy + r_inner)
            sp.lineTo(cx, cy + r_outer)
            sp.quadTo(cx, cy, cx - r_inner, cy)
            sp.lineTo(cx - r_outer, cy)
            sp.quadTo(cx, cy, cx, cy - r_inner)
            sp.closeSubpath()
            p.setPen(QPen(QColor("#FFFFFF"), 0.6))
            p.setBrush(QBrush(col))
            p.drawPath(sp)

        draw_sparkle(2.0, 2.0, 4.0, 1.0, QColor("#FDE047"))
        draw_sparkle(9.0, 2.5, 2.2, 0.6, QColor("#A7F3D0"))
        draw_sparkle(2.5, 9.0, 2.2, 0.6, QColor("#F472B6"))

        p.end()
        return pix

    @staticmethod
    def _draw_canva_sparkle_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        core_col = CursorFactory._parse_color(color, "#F43F5E")
        cx, cy = 16.0, 16.0

        rad = QRadialGradient(cx, cy, 14.0)
        c_glow = QColor(core_col)
        c_glow.setAlpha(80)
        rad.setColorAt(0.0, c_glow)
        rad.setColorAt(1.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rad))
        p.drawEllipse(QPointF(cx, cy), 14.0, 14.0)

        sp = QPainterPath()
        r_out = 11.0
        r_in = 2.5
        sp.moveTo(cx, cy - r_out)
        sp.quadTo(cx, cy, cx + r_in, cy)
        sp.lineTo(cx + r_out, cy)
        sp.quadTo(cx, cy, cx, cy + r_in)
        sp.lineTo(cx, cy + r_out)
        sp.quadTo(cx, cy, cx - r_in, cy)
        sp.lineTo(cx - r_out, cy)
        sp.quadTo(cx, cy, cx, cy - r_in)
        sp.closeSubpath()

        p.setPen(QPen(QColor("#FFFFFF"), 1.0))
        p.setBrush(QBrush(core_col))
        p.drawPath(sp)

        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(cx, cy), 2.2, 2.2)

        p.end()
        return pix

    @staticmethod
    def _draw_notion_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ink = CursorFactory._parse_color(color, "#3B82F6")

        body = QPainterPath()
        body.moveTo(3.0, 3.0)
        body.lineTo(19.0, 19.0)
        body.lineTo(17.5, 20.5)
        body.lineTo(1.5, 4.5)
        body.closeSubpath()

        p.setPen(QPen(QColor("#000000"), 0.8))
        p.setBrush(QBrush(QColor("#27272A")))
        p.drawPath(body)

        p.setPen(QPen(QColor("#FFFFFF"), 0.8))
        p.drawLine(QPointF(6.0, 7.5), QPointF(16.0, 17.5))

        p.setPen(QPen(QColor("#18181B"), 1.0))
        p.drawLine(QPointF(1.0, 1.0), QPointF(3.5, 3.5))

        p.setPen(QPen(QColor("#FFFFFF"), 0.6))
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(1.2, 1.2), 1.2, 1.2)

        p.end()
        return pix

    @staticmethod
    def _draw_notion_marker_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        hl_col = CursorFactory._parse_color(color, "#60A5FA")

        block = QPainterPath()
        block.addRoundedRect(QRectF(1.0, 1.0, 14.0, 7.0), 2.0, 2.0)
        p.save()
        p.rotate(45.0)
        p.translate(2.0, -4.0)
        p.setPen(QPen(QColor("#FFFFFF"), 1.0))
        p.setBrush(QBrush(hl_col))
        p.drawPath(block)
        p.restore()

        p.end()
        return pix

    @staticmethod
    def _draw_vscode_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ink = CursorFactory._parse_color(color, "#007ACC")

        body = QPainterPath()
        body.moveTo(3.5, 3.5)
        body.lineTo(19.0, 19.0)
        body.lineTo(16.5, 21.5)
        body.lineTo(1.0, 6.0)
        body.closeSubpath()

        b_grad = QLinearGradient(1.0, 1.0, 19.0, 19.0)
        b_grad.setColorAt(0.0, QColor("#007ACC"))
        b_grad.setColorAt(0.6, QColor("#1E1E1E"))
        b_grad.setColorAt(1.0, QColor("#252526"))

        p.setPen(QPen(QColor("#38BDF8"), 0.8))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        tip = QPainterPath()
        tip.moveTo(1.0, 1.0)
        tip.lineTo(4.5, 2.5)
        tip.lineTo(2.5, 4.5)
        tip.closeSubpath()

        p.setPen(QPen(QColor("#FFFFFF"), 0.8))
        p.setBrush(QBrush(ink))
        p.drawPath(tip)

        p.end()
        return pix

    @staticmethod
    def _draw_vscode_ibeam_pix() -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = 16.0
        p.setPen(QPen(QColor(0, 0, 0, 220), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, 6.0), QPointF(cx, 26.0))
        p.drawLine(QPointF(cx - 5.0, 6.0), QPointF(cx + 5.0, 6.0))
        p.drawLine(QPointF(cx - 5.0, 6.0), QPointF(cx - 5.0, 9.0))
        p.drawLine(QPointF(cx + 5.0, 6.0), QPointF(cx + 5.0, 9.0))
        p.drawLine(QPointF(cx - 5.0, 26.0), QPointF(cx + 5.0, 26.0))
        p.drawLine(QPointF(cx - 5.0, 26.0), QPointF(cx - 5.0, 23.0))
        p.drawLine(QPointF(cx + 5.0, 26.0), QPointF(cx + 5.0, 23.0))

        p.setPen(QPen(QColor("#00F0FF"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, 6.0), QPointF(cx, 26.0))
        p.drawLine(QPointF(cx - 5.0, 6.0), QPointF(cx + 5.0, 6.0))
        p.drawLine(QPointF(cx - 5.0, 6.0), QPointF(cx - 5.0, 8.5))
        p.drawLine(QPointF(cx + 5.0, 6.0), QPointF(cx + 5.0, 8.5))
        p.drawLine(QPointF(cx - 5.0, 26.0), QPointF(cx + 5.0, 26.0))
        p.drawLine(QPointF(cx - 5.0, 26.0), QPointF(cx - 5.0, 23.5))
        p.drawLine(QPointF(cx + 5.0, 26.0), QPointF(cx + 5.0, 23.5))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(cx, 16.0), 1.2, 1.2)

        p.end()
        return pix

    @staticmethod
    def _draw_vscode_pointer_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        core_col = CursorFactory._parse_color(color, "#007ACC")

        chevron = QPainterPath()
        chevron.moveTo(2.0, 2.0)
        chevron.lineTo(12.0, 9.0)
        chevron.lineTo(2.0, 16.0)
        chevron.lineTo(5.0, 9.0)
        chevron.closeSubpath()

        p.save()
        p.translate(1.0, 1.0)
        p.fillPath(chevron, QColor(0, 0, 0, 80))
        p.restore()

        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.setBrush(QBrush(core_col))
        p.drawPath(chevron)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#38BDF8")))
        p.drawRoundedRect(QRectF(14.0, 14.0, 8.0, 3.0), 1.0, 1.0)

        p.end()
        return pix

    @staticmethod
    def _draw_docs_pen_pix(color: Optional[Union[QColor, str]] = None, size: int = 32) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ink = CursorFactory._parse_color(color, "#1A73E8")

        body = QPainterPath()
        body.moveTo(4.0, 4.0)
        body.lineTo(19.0, 19.0)
        body.quadTo(21.0, 21.0, 19.0, 22.0)
        body.quadTo(18.0, 22.0, 16.0, 20.0)
        body.lineTo(2.0, 6.0)
        body.closeSubpath()

        b_grad = QLinearGradient(2.0, 2.0, 19.0, 19.0)
        b_grad.setColorAt(0.0, QColor("#1A73E8"))
        b_grad.setColorAt(0.7, QColor("#1557B0"))
        b_grad.setColorAt(1.0, QColor("#0D47A1"))

        p.setPen(QPen(QColor("#FFFFFF"), 0.8))
        p.setBrush(QBrush(b_grad))
        p.drawPath(body)

        p.setPen(QPen(QColor("#E8EAED"), 1.2))
        p.drawLine(QPointF(12.0, 10.0), QPointF(18.0, 16.0))

        cone = QPainterPath()
        cone.moveTo(1.0, 1.0)
        cone.lineTo(4.5, 2.8)
        cone.lineTo(2.8, 4.5)
        cone.closeSubpath()
        p.setPen(QPen(QColor("#5F6368"), 0.8))
        p.setBrush(QBrush(QColor("#DADCE0")))
        p.drawPath(cone)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(1.2, 1.2), 1.2, 1.2)

        p.end()
        return pix

    @staticmethod
    def _draw_docs_pointer_pix(color: Optional[Union[QColor, str]] = None) -> QPixmap:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = 16.0, 16.0
        colors = [QColor("#4285F4"), QColor("#EA4335"), QColor("#FBBC05"), QColor("#34A853")]
        r = 10.0
        p.setPen(QPen(QColor(0, 0, 0, 120), 3.0))
        p.drawEllipse(QPointF(cx, cy), r, r)

        for i, col in enumerate(colors):
            p.setPen(QPen(col, 2.0))
            start_angle = i * 90 * 16
            span_angle = 80 * 16
            p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), start_angle, span_angle)

        p.setPen(QPen(QColor("#FFFFFF"), 0.8))
        p.setBrush(QBrush(QColor("#1A73E8")))
        p.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

        p.end()
        return pix
