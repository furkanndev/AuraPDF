import os
import math
import uuid
import hashlib
import random
import pymupdf as fitz
from typing import List, Dict, Optional, Any
import urllib.parse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                             QGraphicsTextItem, QMessageBox, QGraphicsItem, QMenu, QInputDialog,
                             QGraphicsItemGroup, QGraphicsPathItem, QApplication, QLineEdit,
                             QTextEdit, QCheckBox, QRadioButton, QComboBox, QGraphicsProxyWidget)
from PyQt6.QtGui import (QImage, QPixmap, QPen, QColor, QPainter, QPainterPath, QPainterPathStroker,
                         QBrush, QLinearGradient, QRadialGradient, QFont,
                         QFontMetrics, QFontMetricsF, QTransform, QDesktopServices)
from PyQt6.QtCore import (Qt, QRectF, QPointF, QPoint, QTimer, QLineF, QEvent, QSettings, QUrl)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.cursors import CursorFactory
from src.ui.widgets import EditableInlineTextItem
from src.document.media_items import PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem


def build_fountain_pen_path(raw_pts: List[QPointF], base_width: float = 6.0, min_width: float = 1.8) -> QPainterPath:
    path = QPainterPath()
    if not raw_pts:
        return path
    if len(raw_pts) == 1:
        path.addEllipse(raw_pts[0], max(0.5, base_width / 2.0), max(0.5, base_width / 2.0))
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
        w = max(min_width, min(base_width * 2.5, base_width * (0.32 + 1.65 * (down_factor ** 1.15))))

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


_PENCIL_FILL_TEXTURE_CACHE = {}

def get_graphite_fill_texture(color: QColor, alpha_base: float = 1.0) -> QPixmap:
    r, g, b = color.red(), color.green(), color.blue()
    effective_alpha = min(color.alphaF(), float(alpha_base))
    key = (r, g, b, round(effective_alpha, 2))
    if key in _PENCIL_FILL_TEXTURE_CACHE:
        return _PENCIL_FILL_TEXTURE_CACHE[key]

    size = 64
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    base_alpha = max(15, min(255, int(95 * effective_alpha)))
    img.fill(QColor(r, g, b, base_alpha))

    tp = QPainter(img)
    rng = random.Random(1337)
    grain_density = 0.55

    for y in range(size):
        for x in range(size):
            f1 = math.sin(x * 0.45) * math.cos(y * 0.45)
            f2 = math.sin(x * 0.9 + y * 0.7) * 0.5
            noise = (f1 + f2 + 1.5) / 3.0
            speckle = rng.random()
            val = noise * 0.45 + speckle * 0.55
            if val > (1.0 - grain_density):
                grain_a = int(60 + (val - (1.0 - grain_density)) / grain_density * 180)
                tp.setPen(QColor(r, g, b, min(245, int(grain_a * effective_alpha))))
                tp.drawPoint(x, y)
    tp.end()
    pix = QPixmap.fromImage(img)
    _PENCIL_FILL_TEXTURE_CACHE[key] = pix
    return pix


class BookmarkRibbonItem(QGraphicsItem):
    """
    Sayfa üzerinde yer imi ekleme/kaldırma kurdelesi (Bookmark Ribbon).
    Sayfanın sağ üst köşesinde zarif bir kurdele olarak konumlanır.
    """
    WIDTH = 26.0
    HEIGHT = 40.0
    NOTCH = 9.0

    def __init__(self, tab_doc: 'PDFTabDocument', page_idx: int, x: float, y: float, is_bookmarked: bool = False):
        super().__init__()
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.is_bookmarked = is_bookmarked
        self.is_hovered = False
        self.setPos(x, y)
        self.setZValue(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self._update_tooltip()

    def _update_tooltip(self):
        p_num = self.page_idx + 1
        if self.is_bookmarked:
            self.setToolTip(f"Sayfa {p_num} yer imlerine ekli (Kaldırmak için tıklayın)")
        else:
            self.setToolTip(f"Sayfa {p_num}'i yer imlerine ekle")

    def set_bookmarked(self, val: bool):
        if self.is_bookmarked != val:
            self.is_bookmarked = val
            self._update_tooltip()
            self.update()

    def set_hovered(self, val: bool):
        if self.is_hovered != val:
            self.is_hovered = val
            self.update()

    def toggle_bookmark(self):
        if self.is_bookmarked:
            self.tab_doc.toggle_page_bookmark(self.page_idx)
        else:
            self.tab_doc.add_custom_page_bookmark(self.page_idx)

    def boundingRect(self) -> QRectF:
        return QRectF(-3, -2, self.WIDTH + 6, self.HEIGHT + 6)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        w, h, notch = self.WIDTH, self.HEIGHT, self.NOTCH
        path.moveTo(0, 0)
        path.lineTo(w, 0)
        path.lineTo(w, h)
        path.lineTo(w / 2.0, h - notch)
        path.lineTo(0, h)
        path.closeSubpath()
        return path

    def paint(self, painter: QPainter, option, widget=None):
        # Küçük resim veya dışa aktarımda sadece ekliyse çizilsin, boş kurdele sadece ekranda görünsün
        if widget is None and not self.is_bookmarked:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.WIDTH
        h = self.HEIGHT
        notch = self.NOTCH

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(w, 0)
        path.lineTo(w, h)
        path.lineTo(w / 2.0, h - notch)
        path.lineTo(0, h)
        path.closeSubpath()

        if self.is_bookmarked:
            # 1. Alt gölge
            shadow_path = QPainterPath()
            shadow_path.moveTo(1, 1)
            shadow_path.lineTo(w + 1, 1)
            shadow_path.lineTo(w + 1, h + 2)
            shadow_path.lineTo(w / 2.0 + 1, h - notch + 2)
            shadow_path.lineTo(1, h + 2)
            shadow_path.closeSubpath()
            painter.fillPath(shadow_path, QColor(0, 0, 0, 45))

            # 2. Canlı kırmızı gövde gradient
            grad = QLinearGradient(0, 0, w, h)
            if self.is_hovered:
                grad.setColorAt(0.0, QColor("#fb7185"))
                grad.setColorAt(1.0, QColor("#e11d48"))
            else:
                grad.setColorAt(0.0, QColor("#ef4444"))
                grad.setColorAt(1.0, QColor("#be123c"))

            painter.setPen(QPen(QColor("#881337"), 1.2))
            painter.setBrush(QBrush(grad))
            painter.drawPath(path)

            # 3. Üst kenar katlantı efekti (Sayfa kenarından sarkma hissi)
            painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
            painter.drawLine(QPointF(1, 1), QPointF(w - 1, 1))

            # 4. İç zarif yer imi ikonu
            icon_path = QPainterPath()
            iw, ih = w * 0.44, h * 0.42
            ix, iy = (w - iw) / 2.0, 7.0
            inotch = notch * 0.42
            icon_path.moveTo(ix, iy)
            icon_path.lineTo(ix + iw, iy)
            icon_path.lineTo(ix + iw, iy + ih)
            icon_path.lineTo(ix + iw / 2.0, iy + ih - inotch)
            icon_path.lineTo(ix, iy + ih)
            icon_path.closeSubpath()

            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.2))
            painter.setBrush(QBrush(QColor(255, 255, 255, 45)))
            painter.drawPath(icon_path)

        else:
            if self.is_hovered:
                painter.setPen(QPen(QColor("#f43f5e"), 1.4, Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(QColor(244, 63, 94, 70)))
                painter.drawPath(path)

                cx, cy = w / 2.0, 15.0
                painter.setPen(QPen(QColor("#f43f5e"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - 4, cy), QPointF(cx + 4, cy))
                painter.drawLine(QPointF(cx, cy - 4), QPointF(cx, cy + 4))
            else:
                painter.setPen(QPen(QColor(160, 160, 175, 170), 1.2, Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(QColor(230, 230, 240, 90)))
                painter.drawPath(path)

                cx, cy = w / 2.0, 15.0
                painter.setPen(QPen(QColor(140, 140, 155, 160), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - 3.5, cy), QPointF(cx + 3.5, cy))
                painter.drawLine(QPointF(cx, cy - 3.5), QPointF(cx, cy + 3.5))

        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.screenPos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.boundingRect().contains(event.pos()):
                self.toggle_bookmark()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)

        target_page_1_based = self.page_idx + 1

        if self.is_bookmarked:
            act_add_sub = menu.addAction(ModernIconFactory.icon_bookmark(), "Bu Sayfaya Alt Yer İmi Ekle...")
            act_rename = menu.addAction(ModernIconFactory.icon_bookmark(), "Yer İmini Yeniden Adlandır...")
            act_remove = menu.addAction("Yer İmini Kaldır")
            chosen = menu.exec(global_pos)
            if chosen == act_add_sub:
                self.tab_doc.add_custom_page_bookmark(self.page_idx)
            elif chosen == act_rename:
                self.tab_doc.rename_page_bookmark(self.page_idx)
            elif chosen == act_remove:
                self.tab_doc.toggle_page_bookmark(self.page_idx)
        else:
            act_add = menu.addAction(ModernIconFactory.icon_bookmark(), f"Sayfa {target_page_1_based}'i Yer İmlerine Ekle")
            act_add_custom = menu.addAction("Özel Başlıkla Yer İmi Ekle...")
            chosen = menu.exec(global_pos)
            if chosen == act_add:
                self.tab_doc.toggle_page_bookmark(self.page_idx)
            elif chosen == act_add_custom:
                self.tab_doc.add_custom_page_bookmark(self.page_idx)


class AuraLaserPointerItem(QGraphicsItem):
    """
    Ultra-modern, premium laser pointer graphic preview item.
    Renders:
    - Multi-layer luminous bloom (diffuse ambient glow)
    - High-tech outer precision halo ring with 4 delicate micro-notches
    - Intense neon energy core
    - Pure white laser diode center pinpoint
    - Supports dynamic Iridescent Rainbow cycling and Single Color modes
    """
    def __init__(self, radius=16.0):
        super().__init__()
        self.radius = radius
        self.mode = "single"
        self.color = QColor("#ff1744")
        self.hue = 0.0
        self.setZValue(999)

    def boundingRect(self):
        r = self.radius + 6.0
        return QRectF(-r, -r, r * 2.0, r * 2.0)

    def update_settings(self, mode, color, hue):
        self.mode = mode
        self.color = color
        self.hue = hue
        from PyQt6.QtCore import QSettings
        self.style = QSettings("AuraPDF", "PDFViewer").value("cursor_pointer", "apple_laser")
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.radius
        style = getattr(self, 'style', 'apple_laser')

        if self.mode == "rainbow":
            base_col = QColor.fromHsvF(self.hue, 0.95, 1.0)
            halo_col = QColor.fromHsvF((self.hue + 0.15) % 1.0, 0.9, 1.0)
            ring_col = QColor.fromHsvF((self.hue + 0.3) % 1.0, 0.85, 1.0)
        else:
            base_col = self.color
            halo_col = QColor(base_col.red(), base_col.green(), base_col.blue())
            ring_col = QColor(base_col.red(), base_col.green(), base_col.blue())

        if style == "dot":
            # Minimalist Tek Nokta
            painter.setPen(QPen(QColor(0, 0, 0, 80), 1.0))
            painter.setBrush(QBrush(base_col))
            painter.drawEllipse(QRectF(-4.5, -4.5, 9.0, 9.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.drawEllipse(QRectF(-1.8, -1.8, 3.6, 3.6))
            return

        # 1. Dış yumuşak optik hale (Apple Ambient Bloom)
        bloom_grad = QRadialGradient(0, 0, r)
        bloom_grad.setColorAt(0.0, QColor(halo_col.red(), halo_col.green(), halo_col.blue(), 125))
        bloom_grad.setColorAt(0.5, QColor(halo_col.red(), halo_col.green(), halo_col.blue(), 45))
        bloom_grad.setColorAt(1.0, QColor(halo_col.red(), halo_col.green(), halo_col.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bloom_grad))
        painter.drawEllipse(QRectF(-r, -r, r * 2.0, r * 2.0))

        if style == "neon_ring":
            # 2. Neon çentikli halka
            ring_r = r * 0.72
            ring_pen = QPen(QColor(ring_col.red(), ring_col.green(), ring_col.blue(), 190), 1.2)
            ring_pen.setCosmetic(True)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-ring_r, -ring_r, ring_r * 2.0, ring_r * 2.0))

            tick_pen = QPen(QColor(255, 255, 255, 220), 1.2)
            tick_pen.setCosmetic(True)
            painter.setPen(tick_pen)
            tick_len = 2.5
            painter.drawLine(QPointF(0, -ring_r - tick_len), QPointF(0, -ring_r + 1.0))
            painter.drawLine(QPointF(0, ring_r - 1.0), QPointF(0, ring_r + tick_len))
            painter.drawLine(QPointF(-ring_r - tick_len, 0), QPointF(-ring_r + 1.0, 0))
            painter.drawLine(QPointF(ring_r - 1.0, 0), QPointF(ring_r + tick_len, 0))
        elif style == "apple_glow_ring":
            # Apple Halka
            ring_r = r * 0.65
            painter.setPen(QPen(QColor(ring_col.red(), ring_col.green(), ring_col.blue(), 210), 1.4))
            painter.setBrush(QBrush(QColor(ring_col.red(), ring_col.green(), ring_col.blue(), 35)))
            painter.drawEllipse(QRectF(-ring_r, -ring_r, ring_r * 2.0, ring_r * 2.0))

        # 3. İnce kontrast dış sınır
        core_r = r * 0.40 if style != "apple_glow_ring" else r * 0.28
        painter.setPen(QPen(QColor(0, 0, 0, 60), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(-core_r - 0.5, -core_r - 0.5, (core_r + 0.5) * 2.0, (core_r + 0.5) * 2.0))

        # 4. Canlı Apple lazer enerji çekirdeği
        core_grad = QRadialGradient(0, 0, core_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        core_grad.setColorAt(0.38, QColor(base_col.red(), base_col.green(), base_col.blue(), 255))
        core_grad.setColorAt(0.85, QColor(base_col.red(), base_col.green(), base_col.blue(), 210))
        core_grad.setColorAt(1.0, QColor(base_col.red(), base_col.green(), base_col.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QRectF(-core_r, -core_r, core_r * 2.0, core_r * 2.0))

        # 5. Parlak beyaz diyot merkezi
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        painter.drawEllipse(QRectF(-1.8, -1.8, 3.6, 3.6))

ModernLaserPointerItem = AuraLaserPointerItem


class AuraMeasurementItem(QGraphicsItem):
    """
    Adobe Acrobat Pro tarzı etkileşimli ve hassas ölçüm cetveli görseli.
    - İki nokta arasında boyut çizgisi (dimension line) çizer.
    - Uçlarda mimari / teknik resim dik sınırlayıcı çentikleri (|) ve hassas hedef noktaları (o) bulunur.
    - Çizgi üzerinde veya merkezinde şık, buzlu cam / koyu yüksek kontrastlı rozet etiketi ile:
      Örn: "14.25 cm  •  0.0°" gerçek fiziksel PDF ölçüsünü gösterir.
    - PDF koordinat sisteminde 1 pt = 2.54 / 72 cm (≈ 0.0352778 cm) standardını kullanır.
    """
    def __init__(self, p1: QPointF, p2: QPointF, base_render_dpi: float = 1.5,
                 unit: str = "cm", scale_ratio: float = 1.0, page_idx: int = 0):
        super().__init__()
        self.p1 = p1
        self.p2 = p2
        self.base_render_dpi = base_render_dpi
        self.unit = unit
        self.scale_ratio = scale_ratio
        self.page_idx = page_idx
        self.setZValue(990)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_endpoints(self, p1: QPointF, p2: QPointF):
        self.prepareGeometryChange()
        self.p1 = p1
        self.p2 = p2
        self.update()

    def set_unit_and_scale(self, unit: str, scale_ratio: float):
        self.unit = unit
        self.scale_ratio = scale_ratio
        self.update()

    def get_measurement_data(self) -> Dict[str, Any]:
        dx_pt = (self.p2.x() - self.p1.x()) / self.base_render_dpi
        dy_pt = (self.p2.y() - self.p1.y()) / self.base_render_dpi
        dist_pt = math.hypot(dx_pt, dy_pt)
        
        # PDF Point dönüşümleri (1 inç = 72 pt = 2.54 cm = 25.4 mm)
        if self.unit == "mm":
            val = dist_pt * (25.4 / 72.0) * self.scale_ratio
            unit_str = "mm"
            val_str = f"{val:.1f} {unit_str}"
        elif self.unit == "in":
            val = (dist_pt / 72.0) * self.scale_ratio
            unit_str = "in"
            val_str = f"{val:.2f} {unit_str}"
        elif self.unit == "pt":
            val = dist_pt * self.scale_ratio
            unit_str = "pt"
            val_str = f"{val:.1f} {unit_str}"
        else:  # "cm" varsayılan
            val = dist_pt * (2.54 / 72.0) * self.scale_ratio
            unit_str = "cm"
            val_str = f"{val:.2f} {unit_str}"

        angle_rad = math.atan2(self.p2.y() - self.p1.y(), self.p2.x() - self.p1.x())
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360.0

        return {
            "dist_pt": dist_pt,
            "val": val,
            "unit": unit_str,
            "val_str": val_str,
            "angle_deg": angle_deg,
            "dx_pt": dx_pt,
            "dy_pt": dy_pt
        }

    def _get_badge_rect(self) -> QRectF:
        p1 = self.p1
        p2 = self.p2
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        data = self.get_measurement_data()
        label_text = f"{data['val_str']}  •  {data['angle_deg']:.1f}°"

        font = QFont("Segoe UI")
        font.setPixelSize(12)
        font.setBold(True)
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(label_text)
        badge_w = max(60.0, float(text_rect.width() + 22))
        badge_h = max(24.0, float(text_rect.height() + 8))

        mid_x = (p1.x() + p2.x()) / 2.0
        mid_y = (p1.y() + p2.y()) / 2.0

        if length > 0.001:
            nx = -dy / length
            ny = dx / length
            badge_cx = mid_x + nx * (badge_h * 0.75 + 5.0)
            badge_cy = mid_y + ny * (badge_h * 0.75 + 5.0)
        else:
            badge_cx = mid_x
            badge_cy = mid_y - 20.0

        return QRectF(badge_cx - badge_w / 2.0, badge_cy - badge_h / 2.0, badge_w, badge_h)

    def boundingRect(self) -> QRectF:
        x_min = min(self.p1.x(), self.p2.x()) - 80
        y_min = min(self.p1.y(), self.p2.y()) - 80
        x_max = max(self.p1.x(), self.p2.x()) + 80
        y_max = max(self.p1.y(), self.p2.y()) + 80
        base_rect = QRectF(x_min, y_min, max(1.0, x_max - x_min), max(1.0, y_max - y_min))
        badge_rect = self._get_badge_rect()
        return base_rect.united(badge_rect.adjusted(-10, -10, 10, 10))

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self.p1)
        path.lineTo(self.p2)
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroke_path = stroker.createStroke(path)
        stroke_path.addEllipse(self.p1, 9.0, 9.0)
        stroke_path.addEllipse(self.p2, 9.0, 9.0)
        stroke_path.addRoundedRect(self._get_badge_rect(), 6.0, 6.0)
        return stroke_path

    def delete_self(self):
        scene = self.scene()
        views = scene.views() if scene else []
        for v in views:
            p = v.parent()
            if hasattr(p, 'measurements') and self in p.measurements:
                p.measurements.remove(self)
                p.view.viewport().update()
                break
        if scene:
            scene.removeItem(self)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1c1c1e; color: #f1f5f9; border: 1px solid #333338; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #dc2626; color: #ffffff; }
        """)
        act_del = menu.addAction("Ölçümü Sil / Kaldır")
        chosen = menu.exec(event.screenPos())
        if chosen == act_del:
            self.delete_self()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_self()
            event.accept()
            return
        super().keyPressEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        p1 = self.p1
        p2 = self.p2
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        is_sel = self.isSelected()

        # 1. Renkler ve kalemler
        line_color = QColor("#38bdf8") if is_sel else QColor("#0ea5e9")
        shadow_color = QColor(0, 0, 0, 110)

        # Seçili durum parlaması
        if is_sel:
            glow_pen = QPen(QColor(56, 189, 248, 80), 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(p1, p2)

        # Gölge hattı
        shadow_pen = QPen(shadow_color, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(shadow_pen)
        painter.drawLine(p1 + QPointF(0.5, 0.8), p2 + QPointF(0.5, 0.8))

        # Ana boyut çizgisi
        dim_pen = QPen(line_color, 2.2 if is_sel else 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(dim_pen)
        painter.drawLine(p1, p2)

        # 2. İki uçtaki dik sınırlayıcı çentikler (|)
        nx = 0.0
        ny = -1.0
        if length > 0.001:
            nx = -dy / length
            ny = dx / length
            tick_half = 7.0 if is_sel else 6.5

            for pt in (p1, p2):
                t1 = QPointF(pt.x() + nx * tick_half, pt.y() + ny * tick_half)
                t2 = QPointF(pt.x() - nx * tick_half, pt.y() - ny * tick_half)
                painter.setPen(shadow_pen)
                painter.drawLine(t1 + QPointF(0.5, 0.8), t2 + QPointF(0.5, 0.8))
                painter.setPen(dim_pen)
                painter.drawLine(t1, t2)

        # 3. Başlangıç ve bitiş merkez hedef noktaları
        for pt in (p1, p2):
            if is_sel:
                painter.setPen(QPen(QColor(56, 189, 248, 180), 1.5))
                painter.setBrush(QBrush(QColor(56, 189, 248, 60)))
                painter.drawEllipse(pt, 5.5, 5.5)

            painter.setPen(QPen(QColor(15, 23, 42, 220), 1.2))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(pt, 3.2, 3.2)
            painter.setBrush(QBrush(line_color))
            painter.drawEllipse(pt, 1.4, 1.4)

        # 4. Yüzen Akıllı Bilgi Rozeti (Emojisiz, minimalist)
        data = self.get_measurement_data()
        label_text = f"{data['val_str']}  •  {data['angle_deg']:.1f}°"

        badge_rect = self._get_badge_rect()

        # Rozet gölgesi
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 90)))
        painter.drawRoundedRect(badge_rect.translated(1.0, 1.8), 6.0, 6.0)

        # Rozet gövdesi
        badge_border = QColor("#38bdf8") if is_sel else QColor(56, 189, 248, 220)
        painter.setPen(QPen(badge_border, 2.0 if is_sel else 1.2))
        painter.setBrush(QBrush(QColor(15, 23, 42, 240)))
        painter.drawRoundedRect(badge_rect, 6.0, 6.0)

        # Rozet metni
        badge_font = QFont("Segoe UI")
        badge_font.setPixelSize(12)
        badge_font.setBold(True)
        painter.setFont(badge_font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, label_text)

ModernMeasurementItem = AuraMeasurementItem


# --- 9. TEKİL SEKME BELGE YÖNETİCİSİ (TAB DOCUMENT) ---
class PDFTabDocument(QWidget):
    def __init__(self, file_path: Optional[str], main_window: 'AuraPDFViewer', initial_style: Optional[str] = None, initial_width: Optional[float] = None, initial_height: Optional[float] = None, create_initial_page: bool = False):
        super().__init__()
        self.file_path = file_path
        self.main_window = main_window
        if file_path and os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            self.doc = fitz.open("pdf", file_bytes)

            if self.doc.is_encrypted:
                from PyQt6.QtWidgets import QMessageBox, QDialog
                from src.ui.dialogs.toolbox_dialogs import extract_pdf_hint, PDFPasswordDialog
                hint = extract_pdf_hint(file_path)
                authenticated = False
                while self.doc.is_encrypted and not authenticated:
                    dlg = PDFPasswordDialog(main_window, file_path, hint)
                    if dlg.exec() != QDialog.DialogCode.Accepted:
                        self.doc.close()
                        self.doc = None
                        raise Exception(LanguageManager.tr("password_cancelled"))

                    if dlg.recovered_file and os.path.isfile(dlg.recovered_file):
                        self.doc.close()
                        self.file_path = dlg.recovered_file
                        self.doc = fitz.open(self.file_path)
                        authenticated = True
                        break

                    pw = dlg.get_password()
                    if self.doc.authenticate(pw) > 0:
                        authenticated = True
                    else:
                        QMessageBox.warning(
                            main_window,
                            LanguageManager.tr("error"),
                            LanguageManager.tr("wrong_password")
                        )
        else:
            self.doc = fitz.open()
            if create_initial_page:
                w = initial_width if initial_width is not None else 595.32
                h = initial_height if initial_height is not None else 841.92
                new_p = self.doc.new_page(width=w, height=h)
                if initial_style and initial_style != "blank":
                    self._draw_page_template(new_p, w, h, initial_style)
                self.is_modified = True
            else:
                self.is_modified = False

        self.base_render_dpi = 1.5
        self.zoom_level = self.get_saved_zoom_level()
        self.current_page_idx = 0
        self.PAGE_MARGIN = 20
        self.page_view_mode = "single"  # "single" veya "double"

        self.page_positions: Dict[int, Dict[str, Any]] = {}
        self.drawings: List[Dict[str, Any]] = []
        self.undo_stack: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []
        self.is_modified = (file_path is None)
        self.save_undo_index = 0
        self.bookmark_ribbon_items: Dict[int, BookmarkRibbonItem] = {}
        self._last_hovered_ribbon: Optional[BookmarkRibbonItem] = None

        # Page numbering tracking
        self.pre_numbering_bytes = None
        self.page_numbering_settings = None
        self.has_page_numbers = False
        if self.doc and hasattr(self.doc, 'embfile_names') and 'aurapdf_pagenum.json' in self.doc.embfile_names():
            try:
                import json
                pdata = json.loads(self.doc.embfile_get('aurapdf_pagenum.json').decode('utf-8'))
                self.has_page_numbers = True
                self.page_numbering_settings = pdata.get('settings', {})
            except Exception:
                pass

        # Watermark tracking
        self.pre_watermark_bytes = None
        self.watermark_settings = None
        self.has_watermark = False
        if self.doc and hasattr(self.doc, 'embfile_names') and 'aurapdf_watermark.json' in self.doc.embfile_names():
            try:
                import json
                wdata = json.loads(self.doc.embfile_get('aurapdf_watermark.json').decode('utf-8'))
                self.has_watermark = True
                self.watermark_settings = wdata.get('settings', {})
            except Exception:
                pass

        if not self.has_watermark and self.doc:
            try:
                for p_idx in range(min(len(self.doc), 5)):
                    page = self.doc[p_idx]
                    for xref in page.get_contents():
                        stream_bytes = self.doc.xref_stream(xref)
                        if stream_bytes and b"% AuraPDF Watermark Stream" in stream_bytes:
                            self.has_watermark = True
                            break
                    if self.has_watermark:
                        break
            except Exception:
                pass

        # Drawing states
        self.current_path = None
        self.current_path_item = None
        self.current_stroke_pts = []
        self.active_drawing_page = None
        self.stroke_start_pos = None

        self.active_text_item = None
        self.selection_item = None
        self.selection_start_pt = None
        self.selection_path = None
        self.selected_drawings = []
        self.selection_highlight_items = []
        self.is_moving_selection = False
        self.move_start_pos = None
        self.move_last_pos = None
        self.move_initial_states = []
        self.is_panning = False
        self.pan_last_viewport_pos = None
        self.laser_pointer_item = None
        self.pointer_last_pos = None
        self.pointer_trail_items = []
        self.pointer_hue = 0.0
        self.active_fade_controllers = []
        self.pointer_trail_opacity = 1.0

        # Doğrudan Belge Üzerinde Metin Düzenleme (RevPDF Stili)
        self.direct_edit_mode = False
        self.direct_edit_editor = None
        self.direct_edit_hover_item = None
        self.direct_edit_banner = None
        self._page_text_blocks_cache = {}

        # Metin Arama (Search)
        self.search_results = []
        self.search_current_idx = -1
        self.search_highlight_items = []
        self.search_active_item = None

        # Ölçüm Cetveli Durumu (Adobe Acrobat Pro Measuring Tool)
        self.measurements: List[ModernMeasurementItem] = []
        self.active_measurement_item: Optional[ModernMeasurementItem] = None
        self.measurement_start_pos: Optional[QPointF] = None
        self.measurement_unit: str = "cm"
        self.measurement_scale: float = 1.0

        self.pointer_delay_timer = QTimer(self)
        self.pointer_delay_timer.setSingleShot(True)
        self.pointer_delay_timer.timeout.connect(self._on_pointer_delay_timeout)

        self.pointer_fade_timer = QTimer(self)
        self.pointer_fade_timer.setInterval(35)
        self.pointer_fade_timer.timeout.connect(self._on_pointer_fade_step)

        # --- V3 YENİ ÖZELLİKLER (V3 NEW FEATURES) ---
        self.reading_color_mode: str = "normal"  # "normal", "dark", "sepia"
        self.nav_history: List[tuple] = []  # [(page_idx, scroll_y), ...]
        self.nav_history_idx: int = -1
        self._nav_recording_disabled: bool = False

        # Metin Seçimi ve İşaretleme (Text Selection & Markup)
        self.selected_text: str = ""
        self.selected_text_rects: List[tuple] = []
        self.selected_text_items: List[QGraphicsItem] = []
        self.is_selecting_text: bool = False
        self.text_selection_start: Optional[QPointF] = None
        self.text_selection_page_idx: Optional[int] = None
        self.text_selection_hud = None

        # Etkileşimli Form Alanları (AcroForms)
        self.interactive_form_proxies: List[QGraphicsProxyWidget] = []

        self._setup_ui()
        self._load_annotations_from_doc()
        self.render_pages_init()
        if self.zoom_level != 1.0:
            self.view.scale(self.zoom_level, self.zoom_level)
        self.rerender_visible_pages()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.view.setStyleSheet("background-color: #181818; border: none;")
        self.view.setAcceptDrops(True)
        self.view.viewport().setAcceptDrops(True)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        layout.addWidget(self.view)

        self.view.viewport().installEventFilter(self)
        self.view.installEventFilter(self)
        self.view.verticalScrollBar().valueChanged.connect(self.on_scroll_change)

        self.rerender_timer = QTimer(self)
        self.rerender_timer.setSingleShot(True)
        self.rerender_timer.timeout.connect(self.rerender_visible_pages)

    @staticmethod
    def _parse_da_string(da_str: str):
        col = (0.1, 0.1, 0.1)
        fs = 14.0
        font = "Arial"
        if not da_str:
            return col, fs, font
        parts = da_str.split()
        i = 0
        while i < len(parts):
            if parts[i] == 'rg' and i >= 3:
                try:
                    col = (float(parts[i-3]), float(parts[i-2]), float(parts[i-1]))
                except Exception:
                    pass
            elif parts[i] == 'g' and i >= 1:
                try:
                    g = float(parts[i-1])
                    col = (g, g, g)
                except Exception:
                    pass
            elif parts[i] == 'Tf' and i >= 2:
                try:
                    fs = max(8.0, float(parts[i-1]))
                    raw_font = parts[i-2].lstrip('/')
                    font = "Arial" if "Helv" in raw_font else raw_font
                except Exception:
                    pass
            i += 1
        return col, fs, font

    def _load_annotations_from_doc(self):
        """
        PDF dosyasındaki mevcut ISO standartlarındaki Mürekkep, Çizim ve Metin Kutusu
        (Ink / Pen / Highlighter / Line / Polyline / FreeText) ek açıklamalarını okur ve
        AuraPDF içinde taşınabilir, seçilebilir, düzenlenebilir ve silinebilir
        vektörel nesneler (self.drawings) olarak sahneye yükler.
        Ayrıca ek açıklamaları in-memory dokümanda gizler (PDF_ANNOT_IS_HIDDEN),
        böylece get_pixmap arka planında statik hayalet çizgi/metin oluşmaz.
        """
        if self.doc is None:
            return
        MANAGED_TYPES = (
            fitz.PDF_ANNOT_INK,
            fitz.PDF_ANNOT_LINE,
            fitz.PDF_ANNOT_POLY_LINE,
            fitz.PDF_ANNOT_HIGHLIGHT,
            fitz.PDF_ANNOT_FREE_TEXT,
            fitz.PDF_ANNOT_POLYGON
        )
        for p_idx in range(len(self.doc)):
            try:
                page = self.doc[p_idx]
                for annot in list(page.annots()):
                    a_type = annot.type[0]
                    if a_type not in MANAGED_TYPES:
                        continue

                    if a_type == fitz.PDF_ANNOT_FREE_TEXT:
                        content = annot.info.get("content", "") or ""
                        if not content.strip():
                            try:
                                content = annot.get_text() or ""
                            except Exception:
                                pass
                        content = content.strip()
                        if not content:
                            continue

                        da_str = ""
                        try:
                            key_res = self.doc.xref_get_key(annot.xref, "DA")
                            if key_res and key_res[0] == "string":
                                da_str = key_res[1]
                        except Exception:
                            pass

                        da_col, da_fs, da_font = self._parse_da_string(da_str)
                        if da_col == (0.1, 0.1, 0.1) and annot.colors:
                            col_list = annot.colors.get('stroke') or annot.colors.get('fill')
                            if col_list and len(col_list) >= 3:
                                da_col = (float(col_list[0]), float(col_list[1]), float(col_list[2]))

                        vis_rect = annot.rect * page.rotation_matrix
                        vis_rect.normalize()

                        r = max(0.0, min(1.0, float(da_col[0])))
                        g = max(0.0, min(1.0, float(da_col[1])))
                        b = max(0.0, min(1.0, float(da_col[2])))
                        new_item = {
                            "type": "text",
                            "page": p_idx,
                            "text": content,
                            "font_size": int(da_fs),
                            "font_family": da_font,
                            "color": QColor.fromRgbF(r, g, b),
                            "x": float(vis_rect.x0),
                            "y": float(vis_rect.y0),
                            "w": float(vis_rect.width),
                            "h": float(vis_rect.height),
                            "source_annot": True
                        }
                        self.drawings.append(new_item)

                        # In-memory dokümanda ek açıklamayı gizle
                        try:
                            annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                            annot.update()
                        except Exception:
                            pass
                        continue

                    # Renk çözümleme
                    col_list = annot.colors.get('stroke') if annot.colors else None
                    if not col_list and annot.colors:
                        col_list = annot.colors.get('fill')
                    if col_list and len(col_list) >= 3:
                        col = (float(col_list[0]), float(col_list[1]), float(col_list[2]))
                    elif col_list and len(col_list) == 1:
                        col = (float(col_list[0]), float(col_list[0]), float(col_list[0]))
                    else:
                        col = (0.0, 0.0, 0.0)

                    # Opaklık çözümleme
                    opacity = annot.opacity
                    if opacity is None or opacity < 0:
                        opacity = 0.4 if a_type == fitz.PDF_ANNOT_HIGHLIGHT else 1.0
                    else:
                        opacity = float(opacity)

                    # Çizgi kalınlığı (PDF puntosundan ekran DPI'ına)
                    border = annot.border or {}
                    pdf_width = float(border.get('width', 2.0))
                    if a_type == fitz.PDF_ANNOT_HIGHLIGHT:
                        pdf_width = max(pdf_width, annot.rect.height)
                    width = pdf_width * self.base_render_dpi

                    # Çizgi deseni (dashes)
                    dashes = border.get('dashes')
                    line_style = "solid"
                    if dashes:
                        if len(dashes) == 2:
                            line_style = "dash" if dashes[0] > 4 else "dot"
                        elif len(dashes) == 4:
                            line_style = "dashdot"

                    strokes_to_add = []
                    arrow_head = None

                    if a_type == fitz.PDF_ANNOT_INK:
                        vertices = annot.vertices or []
                        if len(vertices) == 2 and len(vertices[1]) == 3:
                            pts_main = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in vertices[0]]
                            pts_ah = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in vertices[1]]
                            if pts_main and pts_ah:
                                p_last = pts_main[-1]
                                p_ah_tip = pts_ah[1]
                                if math.hypot(p_last.x - p_ah_tip.x, p_last.y - p_ah_tip.y) < 5.0:
                                    line_style = "arrow"
                                    strokes_to_add.append((pts_main, [(pt.x, pt.y) for pt in pts_ah]))
                                else:
                                    strokes_to_add.append((pts_main, None))
                                    strokes_to_add.append((pts_ah, None))
                        else:
                            for stroke in vertices:
                                if not stroke:
                                    continue
                                pts_stroke = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in stroke]
                                strokes_to_add.append((pts_stroke, None))

                    elif a_type == fitz.PDF_ANNOT_POLYGON:
                        raw_v = annot.vertices or []
                        if raw_v:
                            pts = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in raw_v]
                            path = QPainterPath()
                            path.moveTo(pts[0].x, pts[0].y)
                            for pt in pts[1:]:
                                path.lineTo(pt.x, pt.y)
                            path.closeSubpath()
                            new_item = {
                                "type": "filled_path",
                                "page": p_idx,
                                "rel_path": path,
                                "color": col,
                                "alpha": opacity,
                                "source_annot": True
                            }
                            self.drawings.append(new_item)
                            try:
                                annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                                annot.update()
                            except: pass
                            continue

                    elif a_type in (fitz.PDF_ANNOT_LINE, fitz.PDF_ANNOT_POLY_LINE):
                        raw_v = annot.vertices or []
                        if raw_v:
                            pts_stroke = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in raw_v]
                            strokes_to_add.append((pts_stroke, None))

                    elif a_type == fitz.PDF_ANNOT_HIGHLIGHT:
                        r = annot.rect
                        p_start = fitz.Point(r.x0, (r.y0 + r.y1) / 2) * page.rotation_matrix
                        p_end = fitz.Point(r.x1, (r.y0 + r.y1) / 2) * page.rotation_matrix
                        strokes_to_add.append(([p_start, p_end], None))

                    for stroke_pts, ah in strokes_to_add:
                        pts_coords = [(pt.x, pt.y) for pt in stroke_pts]
                        new_item = {
                            "type": "polyline",
                            "page": p_idx,
                            "points": pts_coords,
                            "color": col,
                            "alpha": opacity,
                            "width": width,
                            "line_style": line_style,
                            "arrow_head": ah,
                            "source_annot": True
                        }
                        self.drawings.append(new_item)

                    # In-memory dokümanda ek açıklamayı gizle
                    try:
                        annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                        annot.update()
                    except Exception:
                        pass
            except Exception as e:
                import traceback
                traceback.print_exc()

    def hide_managed_annotations(self, doc: Optional[fitz.Document] = None):
        """
        In-memory dokümandaki çizim/metin ek açıklamalarının flag'ine PDF_ANNOT_IS_HIDDEN ekler.
        Böylece get_pixmap arka planında statik hayalet çizgi/metinler oluşmaz;
        çizimler ve metinler yalnızca self.drawings üzerinden sahnede etkileşimli kalır.
        """
        target_doc = doc if doc is not None else self.doc
        if target_doc is None:
            return
        MANAGED_TYPES = (
            fitz.PDF_ANNOT_INK,
            fitz.PDF_ANNOT_LINE,
            fitz.PDF_ANNOT_POLY_LINE,
            fitz.PDF_ANNOT_HIGHLIGHT,
            fitz.PDF_ANNOT_FREE_TEXT
        )
        for page in target_doc:
            try:
                for annot in list(page.annots()):
                    if annot.type[0] in MANAGED_TYPES:
                        annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                        annot.update()
            except Exception:
                pass

    def close_document(self):
        self.save_zoom_setting()
        self.clear_search_highlights()
        self.hide_laser_pointer()
        if hasattr(self, 'active_fade_controllers') and self.active_fade_controllers:
            for c in self.active_fade_controllers:
                try:
                    if dt := c.get("delay_timer"):
                        dt.stop()
                except Exception:
                    pass
                try:
                    if ft := c.get("fade_timer"):
                        ft.stop()
                except Exception:
                    pass
            self.active_fade_controllers.clear()
        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        try:
            self.view.viewport().removeEventFilter(self)
        except Exception:
            pass
        try:
            self.view.removeEventFilter(self)
        except Exception:
            pass
        if hasattr(self, 'doc') and self.doc is not None:
            try:
                if not getattr(self.doc, 'is_closed', False):
                    self.doc.close()
            except Exception:
                pass
            self.doc = None
        if hasattr(self, 'drawings') and self.drawings:
            for d in self.drawings:
                it = d.get('item_ref')
                if it and hasattr(it, 'stop_movie'):
                    try:
                        it.stop_movie()
                    except Exception:
                        pass
                d['item_ref'] = None
        if hasattr(self, 'scene') and self.scene:
            self.scene.clear()
        if hasattr(self, 'page_positions'):
            self.page_positions.clear()
        if hasattr(self, 'drawings'):
            self.drawings.clear()
        if hasattr(self, 'undo_stack'):
            self.undo_stack.clear()
        if hasattr(self, 'redo_stack'):
            self.redo_stack.clear()
        try:
            self.close_inplace_editor()
            if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
                self.direct_edit_banner.hide()
                self.direct_edit_banner.deleteLater()
                self.direct_edit_banner = None
            if hasattr(self, 'direct_edit_hover_item') and self.direct_edit_hover_item:
                if self.direct_edit_hover_item.scene() == self.scene:
                    self.scene.removeItem(self.direct_edit_hover_item)
                self.direct_edit_hover_item = None
            if hasattr(self, '_page_text_blocks_cache'):
                self._page_text_blocks_cache.clear()
        except Exception:
            pass
        import gc
        gc.collect()

    def closeEvent(self, event):
        self.close_document()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.rerender_visible_pages()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rerender_visible_pages()
        if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
            self.direct_edit_banner.reposition()
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.reposition()

    # --- DRY (Don't Repeat Yourself) Uygulaması: PDF'e aktarım mantığı ---
    def export_drawings_to_pdf(self, target_doc: fitz.Document, page_mapping: Optional[List[int]] = None):
        """
        Sahnedeki çizimleri hedef PDF dosyasına standart PDF Ink ek açıklamaları (Ink Annotations) olarak aktarır.
        Bu sayede hem Microsoft Edge ve Adobe Acrobat gibi harici okuyucular hem de farklı bilgisayardaki AuraPDF
        çizimleri tanır ve silebilir.
        Eğer page_mapping verilirse, orijinal sayfaları hedef dokümanın yeni indekslerine eşler.
        """
        # 1. Hedef sayfalardaki mevcut ink ek açıklamalarını temizle (self.drawings tek doğru kaynaktır)
        pages_to_clean = set()
        if page_mapping is not None:
            for orig_p in page_mapping:
                idx = page_mapping.index(orig_p)
                if idx < len(target_doc):
                    pages_to_clean.add(idx)
        else:
            pages_to_clean = set(range(len(target_doc)))

        MANAGED_TYPES = (fitz.PDF_ANNOT_INK, fitz.PDF_ANNOT_LINE, fitz.PDF_ANNOT_POLY_LINE, fitz.PDF_ANNOT_HIGHLIGHT, fitz.PDF_ANNOT_FREE_TEXT, fitz.PDF_ANNOT_POLYGON)
        for p_idx in pages_to_clean:
            try:
                page = target_doc[p_idx]
                for annot in list(page.annots()):
                    if annot.type[0] in MANAGED_TYPES:
                        page.delete_annot(annot)
            except Exception:
                pass

        # 2. self.drawings içerisindeki çizimleri PDF Ink ek açıklaması olarak kaydet
        for d in self.drawings:
            orig_page = d.get("page", 0)
            
            # Eğer belirli sayfalar yazdırılıyorsa/kaydediliyorsa
            if page_mapping is not None:
                if orig_page not in page_mapping:
                    continue
                target_page_idx = page_mapping.index(orig_page)
            else:
                target_page_idx = orig_page

            if target_page_idx >= len(target_doc):
                continue
                
            page = target_doc[target_page_idx]
            
            if d.get("type") in ("polyline", "pencil"):
                raw_pts = d.get("points", [])
                if not raw_pts:
                    continue
                # Transform visible screen coordinates to unrotated PDF coordinates using derotation_matrix
                pts = [[(fitz.Point(x, y) * page.derotation_matrix).x, (fitz.Point(x, y) * page.derotation_matrix).y] for x, y in raw_pts]
                if len(pts) == 1:
                    pts.append([pts[0][0] + 0.1, pts[0][1] + 0.1])
                strokes = [pts]

                line_style = d.get("line_style", "solid")
                if line_style == "arrow" and d.get("arrow_head"):
                    raw_ah = d.get("arrow_head", [])
                    ah_pts = [[(fitz.Point(x, y) * page.derotation_matrix).x, (fitz.Point(x, y) * page.derotation_matrix).y] for x, y in raw_ah]
                    if len(ah_pts) >= 2:
                        strokes.append(ah_pts)

                pdf_width = max(0.5, d.get("width", 2.0) / self.base_render_dpi)
                dashes = None
                alpha_val = float(d.get("alpha", 1.0))
                is_pencil = (d.get("type") == "pencil" or d.get("pen_type") == "pencil" or line_style == "pencil")
                if is_pencil:
                    alpha_val = min(1.0, alpha_val * 0.78)
                    pdf_width = max(0.5, (d.get("width", 3.0) * 0.85) / self.base_render_dpi)

                if line_style == "dash":
                    dashes = [6, 4]
                elif line_style == "dot":
                    dashes = [2, 3]
                elif line_style == "dashdot":
                    dashes = [6, 3, 2, 3]

                col = d.get("color", (0.0, 0.0, 0.0))
                if isinstance(col, (tuple, list)) and len(col) >= 3:
                    stroke_col = (float(col[0]), float(col[1]), float(col[2]))
                elif isinstance(col, QColor):
                    stroke_col = (col.redF(), col.greenF(), col.blueF())
                else:
                    stroke_col = (0.0, 0.0, 0.0)

                try:
                    annot = page.add_ink_annot(strokes)
                    annot.set_colors(stroke=stroke_col)
                    annot.set_border(width=pdf_width, dashes=dashes if dashes else (), style="D" if dashes else "S")
                    annot.set_opacity(alpha_val)
                    annot.update()
                except Exception as e:
                    import traceback
                    traceback.print_exc()

            elif d.get("type") == "filled_path":
                rel_path = d.get("rel_path")
                if not rel_path or rel_path.isEmpty():
                    continue
                polys = rel_path.toFillPolygons()
                
                col = d.get("color", (0.0, 0.0, 0.0))
                if isinstance(col, (tuple, list)) and len(col) >= 3:
                    stroke_col = (float(col[0]), float(col[1]), float(col[2]))
                elif isinstance(col, QColor):
                    stroke_col = (col.redF(), col.greenF(), col.blueF())
                else:
                    stroke_col = (0.0, 0.0, 0.0)

                for poly in polys:
                    pts = []
                    for pt in poly:
                        p = fitz.Point(pt.x(), pt.y()) * page.derotation_matrix
                        pts.append([p.x, p.y])
                    if len(pts) > 2:
                        try:
                            annot = page.add_polygon_annot(pts)
                            annot.set_colors(stroke=stroke_col, fill=stroke_col)
                            annot.set_border(width=0)
                            alpha_val = float(d.get("alpha", 1.0))
                            if d.get("line_style") == "pencil":
                                alpha_val = min(1.0, alpha_val * 0.78)
                            annot.set_opacity(alpha_val)
                            annot.update()
                        except Exception:
                            pass

            elif d.get("type") == "text":
                content = d.get("text", "") or ""
                if not content.strip():
                    continue

                col = d.get("color", QColor(0, 0, 0))
                if isinstance(col, QColor):
                    rgb = (col.redF(), col.greenF(), col.blueF())
                elif isinstance(col, (tuple, list)) and len(col) >= 3:
                    rgb = (float(col[0]), float(col[1]), float(col[2]))
                else:
                    rgb = (0.0, 0.0, 0.0)

                fs = float(d.get("font_size", 14))

                it = d.get("item_ref")
                p_info = self.page_positions.get(orig_page)
                page_left = p_info.get('left', 0.0) if p_info else 0.0
                page_top = p_info.get('top', 0.0) if p_info else 0.0

                if it and hasattr(it, 'pos') and hasattr(it, 'boundingRect'):
                    rel_x = (it.pos().x() - page_left) / self.base_render_dpi
                    rel_y = (it.pos().y() - page_top) / self.base_render_dpi
                    br = it.boundingRect()
                    w_pt = max(60.0, br.width() / self.base_render_dpi)
                    h_pt = max(24.0, br.height() / self.base_render_dpi)
                else:
                    rel_x = float(d.get("x", 50.0))
                    rel_y = float(d.get("y", 50.0))
                    w_pt = float(d.get("w", max(80.0, len(content) * fs * 0.7)))
                    h_pt = float(d.get("h", max(24.0, fs * 1.6)))

                vis_rect = fitz.Rect(rel_x, rel_y, rel_x + w_pt, rel_y + h_pt)
                pdf_rect = (vis_rect * page.derotation_matrix)
                pdf_rect.normalize()

                try:
                    frags = d.get("fragments")
                    if not frags and it and hasattr(it, 'get_fragments'):
                        frags = it.get_fragments()

                    flat_frags = [f for blk in (frags or []) for f in blk if f.get("text")]
                    has_multi_style = False
                    if len(flat_frags) > 1:
                        f0 = flat_frags[0]
                        c0 = f0.get("color")
                        c0_rgb = (c0.redF(), c0.greenF(), c0.blueF()) if isinstance(c0, QColor) else (c0 if isinstance(c0, (tuple, list)) and len(c0) >= 3 else (0.0, 0.0, 0.0))
                        for f in flat_frags[1:]:
                            c = f.get("color")
                            c_rgb = (c.redF(), c.greenF(), c.blueF()) if isinstance(c, QColor) else (c if isinstance(c, (tuple, list)) and len(c) >= 3 else (0.0, 0.0, 0.0))
                            if (abs(float(f.get("font_size", 14)) - float(f0.get("font_size", 14))) > 0.5 or
                                bool(f.get("bold")) != bool(f0.get("bold")) or
                                bool(f.get("italic")) != bool(f0.get("italic")) or
                                c_rgb != c0_rgb or
                                bool(f.get("underline")) != bool(f0.get("underline")) or
                                bool(f.get("href")) != bool(f0.get("href"))):
                                has_multi_style = True
                                break

                    if has_multi_style:
                        # Harf düzeyinde farklı renk/kalınlık/boyut içeren zengin metinleri vektörel olarak aktar
                        font_reg = fitz.Font("Helvetica")
                        font_bold = fitz.Font("Helvetica-Bold")
                        font_it = fitz.Font("Helvetica-Oblique")
                        font_bi = fitz.Font("Helvetica-BoldOblique")

                        if getattr(font_reg, "buffer", None):
                            page.insert_font(fontname="F_AURA_REG", fontbuffer=font_reg.buffer)
                        if getattr(font_bold, "buffer", None):
                            page.insert_font(fontname="F_AURA_BOLD", fontbuffer=font_bold.buffer)
                        if getattr(font_it, "buffer", None):
                            page.insert_font(fontname="F_AURA_ITALIC", fontbuffer=font_it.buffer)
                        if getattr(font_bi, "buffer", None):
                            page.insert_font(fontname="F_AURA_BI", fontbuffer=font_bi.buffer)

                        curr_y = rel_y + (4.0 / self.base_render_dpi)
                        rot = page.rotation

                        for blk in frags:
                            blk_frags = [f for f in blk if f.get("text")]
                            if not blk_frags:
                                curr_y += float(d.get("font_size", 14)) * 1.25
                                continue

                            blk_max_fs = max((float(f.get("font_size", 14)) for f in blk_frags), default=float(d.get("font_size", 14)))
                            line_baseline_y = curr_y + blk_max_fs * 0.85
                            curr_x = rel_x + (4.0 / self.base_render_dpi)

                            for frag in blk_frags:
                                frag_txt = frag["text"]
                                f_sz = float(frag.get("font_size", blk_max_fs))
                                f_bold = frag.get("bold", False)
                                f_italic = frag.get("italic", False)
                                f_under = frag.get("underline", False)
                                f_href = frag.get("href", "")

                                f_col = frag.get("color")
                                if isinstance(f_col, QColor):
                                    f_rgb = (f_col.redF(), f_col.greenF(), f_col.blueF())
                                elif isinstance(f_col, (tuple, list)) and len(f_col) >= 3:
                                    f_rgb = (float(f_col[0]), float(f_col[1]), float(f_col[2]))
                                else:
                                    f_rgb = (0.0, 0.0, 0.0)

                                if f_bold and f_italic:
                                    fname = "F_AURA_BI"
                                    ffont = font_bi
                                elif f_bold:
                                    fname = "F_AURA_BOLD"
                                    ffont = font_bold
                                elif f_italic:
                                    fname = "F_AURA_ITALIC"
                                    ffont = font_it
                                else:
                                    fname = "F_AURA_REG"
                                    ffont = font_reg

                                try:
                                    frag_w = ffont.text_length(frag_txt, fontsize=f_sz)
                                except Exception:
                                    frag_w = fitz.get_text_length(frag_txt, fontsize=f_sz)

                                vis_pt = fitz.Point(curr_x, line_baseline_y)
                                pdf_pt = vis_pt * page.derotation_matrix
                                try:
                                    page.insert_text(pdf_pt, frag_txt, fontname=fname, fontsize=f_sz, color=f_rgb, rotate=rot)
                                except Exception:
                                    page.insert_text(pdf_pt, frag_txt, fontname="helv", fontsize=f_sz, color=f_rgb, rotate=rot)

                                if f_under or f_href:
                                    try:
                                        u_col = (0.10, 0.45, 0.91) if f_href else f_rgb
                                        u_p1 = fitz.Point(curr_x, line_baseline_y + 1.5) * page.derotation_matrix
                                        u_p2 = fitz.Point(curr_x + frag_w, line_baseline_y + 1.5) * page.derotation_matrix
                                        page.draw_line(u_p1, u_p2, color=u_col, width=max(0.7, f_sz * 0.05))
                                    except Exception:
                                        pass

                                if f_href:
                                    try:
                                        link_vrect = fitz.Rect(curr_x, line_baseline_y - f_sz * 0.85, curr_x + frag_w, line_baseline_y + f_sz * 0.2)
                                        link_prect = (link_vrect * page.derotation_matrix).normalize()
                                        page.insert_link({"kind": fitz.LINK_URI, "from": link_prect, "uri": f_href})
                                    except Exception:
                                        pass

                                curr_x += frag_w

                            curr_y += blk_max_fs * 1.25
                    else:
                        is_bold = d.get("bold", False)
                        is_italic = d.get("italic", False)
                        if is_bold and is_italic:
                            fname = "hebo"   # Helvetica Bold — closest available; pymupdf FreeText limited
                        elif is_bold:
                            fname = "hebo"
                        elif is_italic:
                            fname = "heit"
                        else:
                            fname = "helv"
                        annot = page.add_freetext_annot(
                            pdf_rect,
                            content,
                            fontsize=fs,
                            fontname=fname,
                            text_color=rgb,
                            fill_color=None
                        )
                        annot.set_border(width=0)
                        annot.update()
                        
                        link_url = d.get("link_url", "")
                        link_text = d.get("link_text", "")
                        link_range = d.get("link_range", None)
                        if link_url:
                            try:
                                target_rect = pdf_rect
                                if link_text:
                                    matches = page.search_for(link_text, clip=pdf_rect)
                                    if matches:
                                        match_idx = 0
                                        if link_range and isinstance(link_range, (list, tuple)) and len(link_range) == 2:
                                            full_content = d.get("text", "")
                                            match_idx = full_content[:int(link_range[0])].count(link_text)
                                        if match_idx < len(matches):
                                            target_rect = matches[match_idx]
                                        else:
                                            target_rect = matches[0]
                                        try:
                                            p1 = fitz.Point(target_rect.x0, target_rect.y1 - 0.5)
                                            p2 = fitz.Point(target_rect.x1, target_rect.y1 - 0.5)
                                            page.draw_line(p1, p2, color=(0.10, 0.45, 0.91), width=1.0)
                                        except Exception:
                                            pass
                                page.insert_link({"kind": fitz.LINK_URI, "from": target_rect, "uri": link_url})
                            except Exception as elink:
                                pass

                except Exception as e:
                    import traceback
                    traceback.print_exc()
            elif d.get("type") == "image":
                img_x = d["x"]
                img_y = d["y"]
                img_w = float(d.get("w", 100.0))
                img_h = float(d.get("h", 100.0))
                if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                    p_info = self.page_positions.get(orig_page)
                    if p_info:
                        pos = d["item_ref"].pos()
                        page_left = p_info.get('left', 0.0)
                        page_top = p_info['top']
                        img_x = (pos.x() - page_left) / self.base_render_dpi
                        img_y = (pos.y() - page_top) / self.base_render_dpi
                        if hasattr(d["item_ref"], 'w') and hasattr(d["item_ref"], 'h'):
                            img_w = d["item_ref"].w / self.base_render_dpi
                            img_h = d["item_ref"].h / self.base_render_dpi

                page_pdf_w = page.rect.width
                page_pdf_h = page.rect.height
                img_w = max(1.0, min(img_w, page_pdf_w))
                img_h = max(1.0, min(img_h, page_pdf_h))
                img_x = max(0.0, min(img_x, max(0.0, page_pdf_w - img_w)))
                img_y = max(0.0, min(img_y, max(0.0, page_pdf_h - img_h)))

                img_rect = (fitz.Rect(img_x, img_y, img_x + img_w, img_y + img_h) * page.derotation_matrix).normalize()
                try:
                    page.insert_image(img_rect, stream=d["image_bytes"], rotate=page.rotation, overlay=True)
                except Exception:
                    pass

            elif d.get("type") == "table":
                t_x = d["x"]
                t_y = d["y"]
                t_w = float(d.get("w", 200.0))
                t_h = float(d.get("h", 100.0))
                if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                    p_info = self.page_positions.get(orig_page)
                    if p_info:
                        pos = d["item_ref"].pos()
                        page_left = p_info.get('left', 0.0)
                        page_top = p_info['top']
                        t_x = (pos.x() - page_left) / self.base_render_dpi
                        t_y = (pos.y() - page_top) / self.base_render_dpi
                        if hasattr(d["item_ref"], 'w') and hasattr(d["item_ref"], 'h'):
                            t_w = d["item_ref"].w / self.base_render_dpi
                            t_h = d["item_ref"].h / self.base_render_dpi

                page_pdf_w = page.rect.width
                page_pdf_h = page.rect.height
                t_w = max(1.0, min(t_w, page_pdf_w))
                t_h = max(1.0, min(t_h, page_pdf_h))
                t_x = max(0.0, min(t_x, max(0.0, page_pdf_w - t_w)))
                t_y = max(0.0, min(t_y, max(0.0, page_pdf_h - t_h)))

                rows = max(1, int(d.get("rows", 3)))
                cols = max(1, int(d.get("cols", 3)))
                cell_data = d.get("cell_data", [])
                has_header = bool(d.get("has_header", True))

                def _parse_rgb(c_val, default):
                    if isinstance(c_val, QColor) and c_val.isValid():
                        return (c_val.redF(), c_val.greenF(), c_val.blueF())
                    if isinstance(c_val, str) and c_val.startswith("#"):
                        c = QColor(c_val)
                        if c.isValid():
                            return (c.redF(), c.greenF(), c.blueF())
                    return default

                border_rgb = _parse_rgb(d.get("border_color"), (0.77, 0.71, 0.99))
                hdr_bg_rgb = _parse_rgb(d.get("header_bg"), (0.49, 0.23, 0.93))
                cell_bg_rgb = _parse_rgb(d.get("cell_bg"), (1.0, 1.0, 1.0))
                alt_bg_rgb = _parse_rgb(d.get("alt_cell_bg"), (0.96, 0.95, 1.0))
                text_rgb = _parse_rgb(d.get("text_color"), (0.12, 0.11, 0.29))
                hdr_text_rgb = _parse_rgb(d.get("header_text_color"), (1.0, 1.0, 1.0))

                cell_w = t_w / cols
                cell_h = t_h / rows
                fs = max(6.0, float(d.get("font_size", 10.0)))

                for r in range(rows):
                    is_hdr = (r == 0 and has_header)
                    for c in range(cols):
                        cx = t_x + c * cell_w
                        cy = t_y + r * cell_h
                        vis_rect = fitz.Rect(cx, cy, cx + cell_w, cy + cell_h)
                        cell_pdf_rect = (vis_rect * page.derotation_matrix).normalize()

                        fill = hdr_bg_rgb if is_hdr else (alt_bg_rgb if r % 2 == 1 else cell_bg_rgb)
                        try:
                            page.draw_rect(cell_pdf_rect, color=border_rgb, fill=fill, width=1.4)
                        except Exception:
                            pass

                        txt = ""
                        if r < len(cell_data) and c < len(cell_data[r]):
                            txt = str(cell_data[r][c] or "").strip()
                        if txt:
                            try:
                                txt_rect = fitz.Rect(cx + 2, cy + 2, cx + cell_w - 2, cy + cell_h - 2)
                                txt_pdf_rect = (txt_rect * page.derotation_matrix).normalize()
                                page.insert_textbox(txt_pdf_rect, txt, fontsize=fs, align=fitz.TEXT_ALIGN_CENTER,
                                                    color=hdr_text_rgb if is_hdr else text_rgb)
                            except Exception:
                                pass

            elif d.get("type") == "audio":
                a_x = d["x"]
                a_y = d["y"]
                a_w = float(d.get("w", 180.0))
                a_h = float(d.get("h", 48.0))
                if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                    p_info = self.page_positions.get(orig_page)
                    if p_info:
                        pos = d["item_ref"].pos()
                        page_left = p_info.get('left', 0.0)
                        page_top = p_info['top']
                        a_x = (pos.x() - page_left) / self.base_render_dpi
                        a_y = (pos.y() - page_top) / self.base_render_dpi
                        if hasattr(d["item_ref"], 'w') and hasattr(d["item_ref"], 'h'):
                            a_w = d["item_ref"].w / self.base_render_dpi
                            a_h = d["item_ref"].h / self.base_render_dpi

                page_pdf_w = page.rect.width
                page_pdf_h = page.rect.height
                a_w = max(1.0, min(a_w, page_pdf_w))
                a_h = max(1.0, min(a_h, page_pdf_h))
                a_x = max(0.0, min(a_x, max(0.0, page_pdf_w - a_w)))
                a_y = max(0.0, min(a_y, max(0.0, page_pdf_h - a_h)))

                badge_pix = QPixmap(int(a_w * 2), int(a_h * 2))
                badge_pix.fill(Qt.GlobalColor.transparent)
                bp = QPainter(badge_pix)
                bp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                bp.setBrush(QBrush(QColor("#1e1b4b")))
                bp.setPen(QPen(QColor("#6366f1"), 2.0))
                bp.drawRoundedRect(QRectF(1, 1, badge_pix.width() - 2, badge_pix.height() - 2), 12.0, 12.0)
                bp.setBrush(QBrush(QColor("#6366f1")))
                bp.setPen(Qt.PenStyle.NoPen)
                bp.drawEllipse(QRectF(14, 14, 60, 60))
                bp.setPen(QColor("#f8fafc"))
                bp.setFont(QFont("Arial", 16, QFont.Weight.Bold))
                bp.drawText(QRectF(90, 14, badge_pix.width() - 100, 32), Qt.AlignmentFlag.AlignVCenter, d.get("title", "Ses Kaydı"))
                bp.setPen(QColor("#94a3b8"))
                bp.setFont(QFont("Arial", 13))
                bp.drawText(QRectF(90, 48, badge_pix.width() - 100, 30), Qt.AlignmentFlag.AlignVCenter, "AuraPDF Ses Kaydı")
                bp.end()

                from PyQt6.QtCore import QBuffer, QIODevice
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                badge_pix.save(buf, "PNG")
                badge_bytes = bytes(buf.data())

                card_rect = (fitz.Rect(a_x, a_y, a_x + a_w, a_y + a_h) * page.derotation_matrix).normalize()
                try:
                    page.insert_image(card_rect, stream=badge_bytes, rotate=page.rotation, overlay=True)
                except Exception:
                    pass

                if d.get("audio_bytes"):
                    try:
                        filename = f"{d.get('title', 'ses')}.{d.get('format', 'wav')}"
                        page.add_file_annot(card_rect.tl, d["audio_bytes"], filename=filename, desc=d.get("title", "Ses Kaydı"))
                    except Exception:
                        pass

            elif d.get("type") == "video":
                v_x = d["x"]
                v_y = d["y"]
                v_w = float(d.get("w", 200.0))
                v_h = float(d.get("h", 120.0))
                if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                    p_info = self.page_positions.get(orig_page)
                    if p_info:
                        pos = d["item_ref"].pos()
                        page_left = p_info.get('left', 0.0)
                        page_top = p_info['top']
                        v_x = (pos.x() - page_left) / self.base_render_dpi
                        v_y = (pos.y() - page_top) / self.base_render_dpi
                        if hasattr(d["item_ref"], 'w') and hasattr(d["item_ref"], 'h'):
                            v_w = d["item_ref"].w / self.base_render_dpi
                            v_h = d["item_ref"].h / self.base_render_dpi

                page_pdf_w = page.rect.width
                page_pdf_h = page.rect.height
                v_w = max(1.0, min(v_w, page_pdf_w))
                v_h = max(1.0, min(v_h, page_pdf_h))
                v_x = max(0.0, min(v_x, max(0.0, page_pdf_w - v_w)))
                v_y = max(0.0, min(v_y, max(0.0, page_pdf_h - v_h)))

                v_rect = (fitz.Rect(v_x, v_y, v_x + v_w, v_y + v_h) * page.derotation_matrix).normalize()
                thumb = d.get("thumbnail_bytes")
                if thumb:
                    try:
                        page.insert_image(v_rect, stream=thumb, rotate=page.rotation, overlay=True)
                    except Exception:
                        pass

                v_url = d.get("video_url", "")
                if v_url:
                    try:
                        page.insert_link({"kind": fitz.LINK_URI, "from": v_rect, "uri": v_url})
                    except Exception:
                        pass

    # --- Sahne Yönetimi ve Silme İşlemleri ---
    def clear_selection_highlights(self):
        for it in self.selection_highlight_items:
            if it.scene() == self.scene:
                self.scene.removeItem(it)
        self.selection_highlight_items.clear()

    def clear_selection(self):
        if self.selection_item and self.selection_item.scene() == self.scene:
            self.scene.removeItem(self.selection_item)
        self.selection_item = None
        self.clear_selection_highlights()
        self.selected_drawings.clear()

    def highlight_selected_items(self):
        self.clear_selection_highlights()
        pen = QPen(QColor("#0078d4"), 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        brush = QBrush(QColor(0, 120, 212, 35))

        for d in self.selected_drawings:
            it = d.get("item_ref")
            if it:
                rect = it.sceneBoundingRect().adjusted(-4, -4, 4, 4)
                box = self.scene.addRect(rect, pen, brush)
                box.setZValue(it.zValue() + 0.1)
                self.selection_highlight_items.append(box)

                # Modern corner grips
                handle_r = 3.5
                handle_pen = QPen(QColor("#ffffff"), 1.2)
                handle_brush = QBrush(QColor("#0078d4"))
                for pt in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                    h_item = self.scene.addEllipse(pt.x() - handle_r, pt.y() - handle_r, handle_r * 2, handle_r * 2, handle_pen, handle_brush)
                    h_item.setZValue(it.zValue() + 0.2)
                    self.selection_highlight_items.append(h_item)

    def _snapshot_drawing_state(self, d):
        s = {
            "page": d.get("page", 0),
            "type": d.get("type", "polyline")
        }
        if "points" in d:
            s["points"] = [tuple(pt) for pt in d["points"]]
        if "arrow_head" in d and d["arrow_head"]:
            s["arrow_head"] = [tuple(pt) for pt in d["arrow_head"]]
        if "rel_path" in d and d["rel_path"]:
            s["rel_path"] = QPainterPath(d["rel_path"])
        if "x" in d:
            s["x"] = d["x"]
        if "y" in d:
            s["y"] = d["y"]
        if "w" in d:
            s["w"] = d["w"]
        if "h" in d:
            s["h"] = d["h"]
        if "text" in d:
            s["text"] = d["text"]
        return s

    def _apply_drawing_state(self, d, state):
        d["page"] = state.get("page", 0)
        if "points" in state:
            d["points"] = [list(pt) for pt in state["points"]]
        if "arrow_head" in state:
            d["arrow_head"] = [list(pt) for pt in state["arrow_head"]] if state["arrow_head"] else None
        if "rel_path" in state and state["rel_path"]:
            d["rel_path"] = QPainterPath(state["rel_path"])
        if "x" in state:
            d["x"] = state["x"]
        if "y" in state:
            d["y"] = state["y"]
        if "w" in state:
            d["w"] = state["w"]
        if "h" in state:
            d["h"] = state["h"]
        if "text" in state:
            d["text"] = state["text"]

    def delete_selected_items(self):
        # 1. Seçili ölçüm cetvellerini sil
        deleted_measurements = []
        for m in list(getattr(self, 'measurements', [])):
            if hasattr(m, 'isSelected') and m.isSelected():
                try:
                    if m.scene() == self.scene:
                        self.scene.removeItem(m)
                except Exception:
                    pass
                self.measurements.remove(m)
                deleted_measurements.append(m)
        if deleted_measurements:
            self.view.viewport().update()

        # 2. Seçili çizim ve notları sil
        if not self.selected_drawings:
            return
        deleted = []
        for item_data in list(self.selected_drawings):
            if item_data in self.drawings:
                self.drawings.remove(item_data)
                deleted.append(item_data)
                if item_data.get("item_ref"):
                    self.scene.removeItem(item_data["item_ref"])

        self.clear_selection()
        if deleted:
            self.push_undo_action({"type": "erase", "deleted_items": deleted})
            self.notify_drawings_changed()

    def notify_drawings_changed_throttled(self, page_idx: Optional[int] = None):
        if not hasattr(self, '_thumb_throttle_timer'):
            self._thumb_throttle_timer = QTimer(self)
            self._thumb_throttle_timer.setSingleShot(True)
            self._thumb_throttle_timer.setInterval(50)
            self._thumb_throttle_page = None
            def do_update():
                p = self._thumb_throttle_page
                self._thumb_throttle_page = None
                self.notify_drawings_changed(p)
            self._thumb_throttle_timer.timeout.connect(do_update)
        self._thumb_throttle_page = page_idx
        if not self._thumb_throttle_timer.isActive():
            self._thumb_throttle_timer.start()

    def notify_drawings_changed(self, page_idx: Optional[int] = None):
        if hasattr(self, '_thumb_throttle_timer') and self._thumb_throttle_timer.isActive():
            self._thumb_throttle_timer.stop()
        if hasattr(self.main_window, 'thumbnails_dock'):
            dock = self.main_window.thumbnails_dock
            if dock:
                if not dock.is_loaded and dock.isVisible():
                    dock.load_thumbnails_lazy()
                elif dock.is_loaded:
                    if page_idx is not None:
                        dock.update_thumbnail(page_idx)
                    else:
                        dock.update_all_thumbnails()

    def clear_all_drawings(self):
        if not self.drawings: return
        deleted = list(self.drawings)
        for d in deleted:
            if d.get("item_ref"):
                self.scene.removeItem(d["item_ref"])
        self.drawings.clear()
        self.clear_selection()
        self.push_undo_action({"type": "erase", "deleted_items": deleted})
        self.notify_drawings_changed()

    def update_laser_pointer(self, pos: QPointF):
        popup = getattr(self.main_window, 'pointer_popup', None)
        mode = popup.mode if popup else "single"
        color = popup.color if popup else QColor("#ff1744")

        if mode == "rainbow":
            self.pointer_hue = (self.pointer_hue + 0.04) % 1.0

        if not self.laser_pointer_item or not isinstance(self.laser_pointer_item, ModernLaserPointerItem):
            if self.laser_pointer_item and self.laser_pointer_item.scene() == self.scene:
                self.scene.removeItem(self.laser_pointer_item)
            self.laser_pointer_item = ModernLaserPointerItem()
            self.scene.addItem(self.laser_pointer_item)

        self.laser_pointer_item.update_settings(mode, color, self.pointer_hue)
        self.laser_pointer_item.setVisible(True)
        self.laser_pointer_item.setPos(pos)

    def hide_laser_pointer(self):
        if self.laser_pointer_item:
            self.laser_pointer_item.setVisible(False)

    def _cancel_pointer_fadeout(self):
        """Kullanıcı çizmeye/yazmaya devam ettiğinde kaybolma zamanlayıcılarını durdurur ve opaklığı yeniler."""
        if hasattr(self, 'pointer_delay_timer') and self.pointer_delay_timer.isActive():
            self.pointer_delay_timer.stop()
        if hasattr(self, 'pointer_fade_timer') and self.pointer_fade_timer.isActive():
            self.pointer_fade_timer.stop()
        self.active_fade_controllers.clear()
        self.pointer_trail_opacity = 1.0
        for it in self.pointer_trail_items:
            try:
                it.setOpacity(1.0)
            except Exception:
                pass

    def _schedule_pointer_fadeout(self, delay_ms: Optional[int] = None):
        """Fare bırakıldığında, ayarlı süre boyunca yeni çizim gelmezse kaybolmayı başlatır."""
        if not self.pointer_trail_items:
            self.active_fade_controllers.clear()
            return
        if delay_ms is None:
            popup = getattr(self.main_window, 'pointer_popup', None)
            delay_ms = int((popup.fade_seconds if popup else 0.5) * 1000)
        self._cancel_pointer_fadeout()
        controller = {"items": list(self.pointer_trail_items), "opacity": 1.0}
        self.active_fade_controllers.append(controller)
        self.pointer_delay_timer.start(max(100, delay_ms))

    def _on_pointer_delay_timeout(self):
        """Bekleme süresi doldu, akıcı kaybolma animasyonunu (fade-out) başlat."""
        if not self.pointer_trail_items:
            self.active_fade_controllers.clear()
            return
        self.pointer_trail_opacity = 1.0
        self.pointer_fade_timer.start()

    def _on_pointer_fade_step(self):
        """Adım adım opaklığı düşür ve tamamlandığında sahneden sil."""
        self.pointer_trail_opacity -= 0.08
        if self.pointer_trail_opacity <= 0.05:
            self.pointer_fade_timer.stop()
            self._clear_pointer_trail_items()
        else:
            for it in self.pointer_trail_items:
                try:
                    it.setOpacity(self.pointer_trail_opacity)
                except Exception:
                    pass

    def _clear_pointer_trail_items(self):
        """Tüm geçici lazer çizgilerini sahneden temizler."""
        if hasattr(self, 'pointer_delay_timer') and self.pointer_delay_timer.isActive():
            self.pointer_delay_timer.stop()
        if hasattr(self, 'pointer_fade_timer') and self.pointer_fade_timer.isActive():
            self.pointer_fade_timer.stop()
        self.active_fade_controllers.clear()
        for it in self.pointer_trail_items:
            try:
                if it.scene() == self.scene:
                    self.scene.removeItem(it)
            except Exception:
                pass
        self.pointer_trail_items.clear()
        self.pointer_trail_opacity = 1.0

    def _start_trail_fadeout(self, items: list = None, delay_ms: int = None):
        self._schedule_pointer_fadeout(delay_ms)

    # --- Belge Değişiklik Durumu (Dirty State) ---
    def set_modified(self, modified: bool = True):
        if self.is_modified != modified:
            self.is_modified = modified
            self.update_tab_title()

    def update_tab_title(self):
        if not getattr(self, 'file_path', None):
            base_name = getattr(self, 'custom_title', None) or LanguageManager.tr("untitled_doc")
        else:
            base_name = os.path.basename(self.file_path)

        prefix = "*" if getattr(self, 'is_modified', False) else ""
        display_name = f"{prefix}{base_name}"

        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tab_widget') and self.main_window.tab_widget is not None:
            idx = self.main_window.tab_widget.indexOf(self)
            if idx >= 0:
                self.main_window.tab_widget.setTabText(idx, display_name)
                if hasattr(self.main_window, 'modern_tab_bar'):
                    self.main_window.modern_tab_bar.set_tab_text(idx, display_name)

        if hasattr(self, 'main_window') and hasattr(self.main_window, 'get_current_tab_doc'):
            if self.main_window.get_current_tab_doc() == self:
                app_title = LanguageManager.tr("app_title")
                self.main_window.setWindowTitle(f"{display_name} - {app_title}")

    # --- Geri / İleri Al (Undo/Redo) ---
    def push_undo_action(self, action_dict):
        if not hasattr(self, 'undo_stack') or self.undo_stack is None:
            self.undo_stack = []
        if not hasattr(self, 'redo_stack') or self.redo_stack is None:
            self.redo_stack = []
        self.undo_stack.append(action_dict)
        self.redo_stack.clear()
        self.set_modified(True)
        if hasattr(self.main_window, 'update_undo_redo_state'):
            self.main_window.update_undo_redo_state()

    def undo(self):
        if not hasattr(self, 'undo_stack') or not self.undo_stack: return
        if not hasattr(self, 'redo_stack') or self.redo_stack is None:
            self.redo_stack = []
        action = self.undo_stack.pop()

        if action["type"] == "add":
            item_data = action["data"]
            if item_data in self.drawings: self.drawings.remove(item_data)
            if item_data.get("item_ref"): self.scene.removeItem(item_data["item_ref"])
            self.redo_stack.append(action)

        elif action["type"] == "edit_text":
            record = action["record"]
            record["text"] = action["old_text"]
            if "old_html" in action and action["old_html"]:
                record["html"] = action["old_html"]
                if record.get("item_ref"): record["item_ref"].setHtml(action["old_html"])
            elif record.get("item_ref"):
                record["item_ref"].setPlainText(action["old_text"])
            if "old_fragments" in action:
                record["fragments"] = action["old_fragments"]
            self.redo_stack.append(action)

        elif action["type"] == "erase":
            for d in action["deleted_items"]:
                d_id = d.get("id")
                existing = next((x for x in self.drawings if (d_id and x.get("id") == d_id) or x is d), None)
                if not existing:
                    self.drawings.append(d)
                    self.restore_drawing_item(d)
            self.redo_stack.append(action)

        elif action["type"] == "area_erase":
            for d in self.drawings:
                it = d.get("item_ref")
                if it and it.scene() == self.scene:
                    self.scene.removeItem(it)
            self.drawings = [dict(d) for d in action["old_drawings"]]
            for d in self.drawings:
                self.restore_drawing_item(d)
            self.redo_stack.append(action)

        elif action["type"] == "move_items":
            for d, old_s in zip(action["items"], action["old_states"]):
                if d in self.drawings:
                    self._apply_drawing_state(d, old_s)
                    if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                        self.scene.removeItem(d["item_ref"])
                    self.restore_drawing_item(d)
            self.selected_drawings = [d for d in action["items"] if d in self.drawings]
            self.highlight_selected_items()
            self.redo_stack.append(action)

        elif action["type"] in ("reorder_pages", "insert_blank_page", "watermark", "change_page_style"):
            if "old_bytes" in action:
                self.doc.close()
                if action["old_bytes"]:
                    self.doc = fitz.open("pdf", action["old_bytes"])
                else:
                    self.doc = fitz.open()
                self.hide_managed_annotations()
                self.drawings = [dict(d) for d in action["old_drawings"]]
                self.render_pages_init()
                self.rerender_visible_pages()
                curr_p = max(0, min(action.get("old_page", 0), len(self.doc) - 1)) if len(self.doc) > 0 else 0
                self.current_page_idx = curr_p
                if len(self.doc) > 0:
                    self.go_to_page(curr_p)
                if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                    self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
                if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                    self.main_window.txt_page.setText(str(curr_p + 1 if len(self.doc) > 0 else 0))
                if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                    if self.main_window.thumbnails_dock.isVisible():
                        self.main_window.thumbnails_dock.load_thumbnails_lazy()
                        if len(self.doc) > 0:
                            self.main_window.thumbnails_dock.select_page(curr_p)
            else:
                self._apply_page_order(action["old_order"])
            if "old_has_page_numbers" in action:
                self.has_page_numbers = action["old_has_page_numbers"]
                self.page_numbering_settings = action.get("old_page_numbering_settings")
                self.pre_numbering_bytes = action.get("old_pre_numbering_bytes")
            if "old_has_watermark" in action:
                self.has_watermark = action["old_has_watermark"]
                self.watermark_settings = action.get("old_watermark_settings")
                self.pre_watermark_bytes = action.get("old_pre_watermark_bytes")
            self.redo_stack.append(action)
        elif action["type"] == "bookmark":
            self.doc.set_toc(action["old_toc"])
            self.update_bookmark_ribbons()
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                self.main_window.thumbnails_dock.load_bookmarks()
            self.redo_stack.append(action)
        elif action["type"] == "direct_text_edit":
            if "old_bytes" in action:
                self.close_inplace_editor()
                self.doc.close()
                self.doc = fitz.open("pdf", action["old_bytes"])
                if hasattr(self, '_page_text_blocks_cache'):
                    self._page_text_blocks_cache.clear()
                self.rerender_visible_pages(force=True)
            self.redo_stack.append(action)
        self.notify_drawings_changed()
        self.set_modified(len(self.undo_stack) != self.save_undo_index)
        if hasattr(self.main_window, 'update_undo_redo_state'):
            self.main_window.update_undo_redo_state()

    def redo(self):
        if not hasattr(self, 'redo_stack') or not self.redo_stack: return
        action = self.redo_stack.pop()

        if action["type"] == "add":
            item_data = action["data"]
            self.drawings.append(item_data)
            self.restore_drawing_item(item_data)
            self.undo_stack.append(action)

        elif action["type"] == "edit_text":
            record = action["record"]
            record["text"] = action["new_text"]
            if "new_html" in action and action["new_html"]:
                record["html"] = action["new_html"]
                if record.get("item_ref"): record["item_ref"].setHtml(action["new_html"])
            elif record.get("item_ref"):
                record["item_ref"].setPlainText(action["new_text"])
            if "new_fragments" in action:
                record["fragments"] = action["new_fragments"]
            self.undo_stack.append(action)

        elif action["type"] == "erase":
            for d in action["deleted_items"]:
                d_id = d.get("id")
                found = next((x for x in self.drawings if (d_id and x.get("id") == d_id) or x is d or x.get("item_ref") == d.get("item_ref")), None)
                if found:
                    if found in self.drawings:
                        self.drawings.remove(found)
                    it = found.get("item_ref") or d.get("item_ref")
                    if it and it.scene() == self.scene:
                        self.scene.removeItem(it)
                else:
                    it = d.get("item_ref")
                    if it and it.scene() == self.scene:
                        self.scene.removeItem(it)
            self.undo_stack.append(action)

        elif action["type"] == "area_erase":
            for d in self.drawings:
                it = d.get("item_ref")
                if it and it.scene() == self.scene:
                    self.scene.removeItem(it)
            self.drawings = [dict(d) for d in action["new_drawings"]]
            for d in self.drawings:
                self.restore_drawing_item(d)
            self.undo_stack.append(action)

        elif action["type"] == "move_items":
            for d, new_s in zip(action["items"], action["new_states"]):
                if d in self.drawings:
                    self._apply_drawing_state(d, new_s)
                    if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                        self.scene.removeItem(d["item_ref"])
                    self.restore_drawing_item(d)
            self.selected_drawings = [d for d in action["items"] if d in self.drawings]
            self.highlight_selected_items()
            self.undo_stack.append(action)

        elif action["type"] in ("reorder_pages", "insert_blank_page", "watermark", "change_page_style"):
            if "new_bytes" in action:
                self.doc.close()
                if action["new_bytes"]:
                    self.doc = fitz.open("pdf", action["new_bytes"])
                else:
                    self.doc = fitz.open()
                self.hide_managed_annotations()
                self.drawings = [dict(d) for d in action["new_drawings"]]
                self.render_pages_init()
                self.rerender_visible_pages()
                curr_p = max(0, min(action.get("new_page", 0), len(self.doc) - 1)) if len(self.doc) > 0 else 0
                self.current_page_idx = curr_p
                if len(self.doc) > 0:
                    self.go_to_page(curr_p)
                if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                    self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
                if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                    self.main_window.txt_page.setText(str(curr_p + 1 if len(self.doc) > 0 else 0))
                if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                    if self.main_window.thumbnails_dock.isVisible():
                        self.main_window.thumbnails_dock.load_thumbnails_lazy()
                        if len(self.doc) > 0:
                            self.main_window.thumbnails_dock.select_page(curr_p)
            else:
                self._apply_page_order(action["new_order"])
            if "new_has_page_numbers" in action:
                self.has_page_numbers = action["new_has_page_numbers"]
                self.page_numbering_settings = action.get("new_page_numbering_settings")
                self.pre_numbering_bytes = action.get("new_pre_numbering_bytes")
            if "new_has_watermark" in action:
                self.has_watermark = action["new_has_watermark"]
                self.watermark_settings = action.get("new_watermark_settings")
                self.pre_watermark_bytes = action.get("new_pre_watermark_bytes")
            self.undo_stack.append(action)
        elif action["type"] == "bookmark":
            self.doc.set_toc(action["new_toc"])
            self.update_bookmark_ribbons()
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                self.main_window.thumbnails_dock.load_bookmarks()
            self.undo_stack.append(action)
        elif action["type"] == "direct_text_edit":
            if "new_bytes" in action:
                self.close_inplace_editor()
                self.doc.close()
                self.doc = fitz.open("pdf", action["new_bytes"])
                if hasattr(self, '_page_text_blocks_cache'):
                    self._page_text_blocks_cache.clear()
                self.rerender_visible_pages(force=True)
            self.undo_stack.append(action)
        self.notify_drawings_changed()
        self.set_modified(len(self.undo_stack) != self.save_undo_index)
        if hasattr(self.main_window, 'update_undo_redo_state'):
            self.main_window.update_undo_redo_state()

    def reorder_pages(self, new_order: List[int], rotations: Optional[List[int]] = None, push_undo: bool = True):
        if self.doc is None or not new_order or len(new_order) > len(self.doc):
            return
        order_changed = (new_order != list(range(len(self.doc))))
        rotations_changed = False
        if rotations is not None and len(rotations) == len(new_order):
            for i, rot in enumerate(rotations):
                page_idx = new_order[i] if order_changed else i
                if rot is not None and self.doc[page_idx].rotation != (rot % 360):
                    rotations_changed = True
                    break

        if not order_changed and not rotations_changed:
            return

        old_bytes = self.doc.tobytes()
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        if order_changed:
            self._apply_page_order(new_order)
        if rotations is not None and len(rotations) == len(self.doc):
            for i, rot in enumerate(rotations):
                if rot is not None:
                    self.doc[i].set_rotation(rot % 360)
            self.render_pages_init()
            self.rerender_visible_pages()
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                if self.main_window.thumbnails_dock.isVisible():
                    self.main_window.thumbnails_dock.load_thumbnails_lazy()
                    self.main_window.thumbnails_dock.select_page(self.current_page_idx)

        if push_undo:
            action = {
                "type": "reorder_pages",
                "old_bytes": old_bytes,
                "old_drawings": old_drawings,
                "old_page": old_page,
                "new_bytes": self.doc.tobytes(),
                "new_drawings": [dict(d) for d in self.drawings],
                "new_page": self.current_page_idx,
                "new_order": list(new_order)
            }
            self.push_undo_action(action)
        self.set_modified(True)

    def delete_page(self, page_idx: int):
        if self.doc is None or len(self.doc) == 0:
            return
        if not (0 <= page_idx < len(self.doc)):
            return

        old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        self.doc.delete_page(page_idx)

        new_drawings = []
        for d in self.drawings:
            p = d.get("page", 0)
            if p == page_idx:
                continue
            if p > page_idx:
                d["page"] = p - 1
            new_drawings.append(d)
        self.drawings = new_drawings

        self.render_pages_init()
        self.rerender_visible_pages()
        new_page = max(0, min(old_page, len(self.doc) - 1)) if len(self.doc) > 0 else 0
        self.current_page_idx = new_page
        if len(self.doc) > 0:
            self.go_to_page(new_page)

        if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
            self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
        if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
            self.main_window.txt_page.setText(str(self.current_page_idx + 1 if len(self.doc) > 0 else 0))
        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            if self.main_window.thumbnails_dock.isVisible():
                self.main_window.thumbnails_dock.load_thumbnails_lazy()
                if len(self.doc) > 0:
                    self.main_window.thumbnails_dock.select_page(self.current_page_idx)

        new_bytes = b""
        try:
            if len(self.doc) > 0:
                new_bytes = self.doc.tobytes()
        except Exception:
            new_bytes = b""

        action = {
            "type": "reorder_pages",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": new_bytes,
            "new_drawings": [dict(d) for d in self.drawings],
            "new_page": self.current_page_idx,
            "new_order": list(range(len(self.doc)))
        }
        self.push_undo_action(action)
        self.set_modified(True)

    def insert_pdf_at(self, file_path: str, after_page: Optional[int] = None):
        if self.doc is None:
            return
        try:
            src_doc = fitz.open(file_path)
            if after_page is None or after_page < 0:
                insert_idx = len(self.doc)
            else:
                insert_idx = max(0, min(after_page + 1, len(self.doc)))

            old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
            old_drawings = [dict(d) for d in self.drawings]
            old_page = self.current_page_idx

            self.doc.insert_pdf(src_doc, start_at=insert_idx)
            num_inserted = len(src_doc)

            for d in self.drawings:
                if d.get("page", 0) >= insert_idx:
                    d["page"] += num_inserted

            self.render_pages_init()
            self.rerender_visible_pages()
            self.go_to_page(insert_idx)

            if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
            if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                self.main_window.txt_page.setText(str(insert_idx + 1))
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                if self.main_window.thumbnails_dock.isVisible():
                    self.main_window.thumbnails_dock.load_thumbnails_lazy()
                    self.main_window.thumbnails_dock.select_page(self.current_page_idx)

            action = {
                "type": "reorder_pages",
                "old_bytes": old_bytes,
                "old_drawings": old_drawings,
                "old_page": old_page,
                "new_bytes": self.doc.tobytes(),
                "new_drawings": [dict(d) for d in self.drawings],
                "new_page": self.current_page_idx,
                "new_order": list(range(len(self.doc)))
            }
            self.push_undo_action(action)
            self.set_modified(True)
        except Exception as e:
            raise e

    def _draw_page_template(self, new_p, width: float, height: float, style: str):
        if not style or style == "blank":
            return
        shape = new_p.new_shape()
        if style in ("lined", "lines"):
            y = 50
            while y < height - 50:
                shape.draw_line(fitz.Point(50, y), fitz.Point(width - 50, y))
                y += 25
            shape.finish(color=(0.8, 0.8, 0.8), width=1)
        elif style == "grid":
            x = 50
            while x < width - 50:
                shape.draw_line(fitz.Point(x, 50), fitz.Point(x, height - 50))
                x += 20
            y = 50
            while y < height - 50:
                shape.draw_line(fitz.Point(50, y), fitz.Point(width - 50, y))
                y += 20
            shape.finish(color=(0.85, 0.85, 0.85), width=1)
        elif style == "dotted":
            x = 50
            while x < width - 50:
                y = 50
                while y < height - 50:
                    shape.draw_circle(fitz.Point(x, y), 0.8)
                    y += 20
                x += 20
            shape.finish(color=(0.7, 0.7, 0.7), fill=(0.7, 0.7, 0.7))
        elif style == "cornell":
            shape.draw_line(fitz.Point(150, 100), fitz.Point(150, height - 50))
            shape.draw_line(fitz.Point(50, 100), fitz.Point(width - 50, 100))
            shape.finish(color=(0.9, 0.6, 0.6), width=2)
            shape2 = new_p.new_shape()
            y = 125
            while y < height - 50:
                shape2.draw_line(fitz.Point(155, y), fitz.Point(width - 50, y))
                y += 25
            shape2.finish(color=(0.85, 0.85, 0.85), width=1)
            shape2.commit()
        elif style in ("music", "staff"):
            y = 70
            while y < height - 70:
                for line_idx in range(5):
                    ly = y + line_idx * 7
                    shape.draw_line(fitz.Point(50, ly), fitz.Point(width - 50, ly))
                y += 65
            shape.finish(color=(0.35, 0.35, 0.35), width=0.8)
        elif style in ("dark", "black"):
            shape.draw_rect(new_p.rect)
            shape.finish(color=(0.08, 0.09, 0.11), fill=(0.08, 0.09, 0.11))
            shape2 = new_p.new_shape()
            y = 50
            while y < height - 50:
                shape2.draw_line(fitz.Point(50, y), fitz.Point(width - 50, y))
                y += 25
            shape2.finish(color=(0.18, 0.20, 0.24), width=0.7)
            shape2.commit()
        elif style == "cover":
            shape.draw_rect(new_p.rect)
            shape.finish(color=(0.12, 0.16, 0.22), fill=(0.12, 0.16, 0.22))
            shape2 = new_p.new_shape()
            shape2.draw_rect(fitz.Rect(40, 40, width - 40, height - 40))
            shape2.finish(color=(0.9, 0.8, 0.6), width=3)
            shape2.commit()
        shape.commit()

    def insert_blank_page(self, after_page: Optional[int] = None, width: Optional[float] = None, height: Optional[float] = None, style: str = "blank"):
        """Mevcut dokümana belirtilen sayfanın ardına boş bir sayfa ekler.
        Mevcut sayfa boyut ve rotasyonuyla birebir uyumlu sayfa oluşturur."""
        if self.doc is None:
            return
        if after_page is None:
            after_page = self.current_page_idx
        insert_idx = max(0, min(after_page + 1, len(self.doc)))

        # Mevcut sayfalarla uyumlu boyut ve rotasyon belirle
        ref_rot = 0
        if len(self.doc) > 0:
            ref_idx = max(0, min(after_page, len(self.doc) - 1))
            ref_page = self.doc[ref_idx]
            if width is None:
                width = ref_page.mediabox.width
            if height is None:
                height = ref_page.mediabox.height
            ref_rot = ref_page.rotation

        if width is None:
            width = 595.32
        if height is None:
            height = 841.92

        old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        # Yeni boş sayfa ekle
        new_p = self.doc.new_page(pno=insert_idx, width=width, height=height)
        if ref_rot:
            new_p.set_rotation(ref_rot)

        if style != "blank":
            self._draw_page_template(new_p, width, height, style)

        # Çizim indekslerini güncelle
        for d in self.drawings:
            if d.get("page", 0) >= insert_idx:
                d["page"] += 1

        self.pre_watermark_bytes = None

        self.render_pages_init()
        self.rerender_visible_pages()
        self.go_to_page(insert_idx)

        if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
            self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
        if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
            self.main_window.txt_page.setText(str(insert_idx + 1))

        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            if self.main_window.thumbnails_dock.isVisible():
                self.main_window.thumbnails_dock.load_thumbnails_lazy()
                self.main_window.thumbnails_dock.select_page(insert_idx)

        self.push_undo_action({
            "type": "insert_blank_page",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": self.doc.tobytes(),
            "new_drawings": [dict(d) for d in self.drawings],
            "new_page": insert_idx,
            "insert_idx": insert_idx
        })
        self.set_modified(True)

    def change_page_style(self, page_idx: int, new_style: str, all_pages: bool = False):
        """Mevcut sayfanın veya belgedeki tüm sayfaların şablonunu (Düz, Çizgili, Kareli, Cornell vb.)
        değiştirir. Kullanıcı çizimleri, metinleri ve notları korunur."""
        if self.doc is None or len(self.doc) == 0:
            return

        old_bytes = self.doc.tobytes()
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        target_pages = list(range(len(self.doc))) if all_pages else [page_idx]

        for p in target_pages:
            if p < 0 or p >= len(self.doc):
                continue
            cur_p = self.doc[p]
            w = cur_p.mediabox.width
            h = cur_p.mediabox.height
            rot = cur_p.rotation

            # Yeni şablonlu sayfayı p+1 konumuna ekle
            new_p = self.doc.new_page(pno=p + 1, width=w, height=h)
            if rot:
                new_p.set_rotation(rot)
            if new_style and new_style != "blank":
                self._draw_page_template(new_p, w, h, new_style)

            # Eski sayfayı sil (böylece new_p sayfa indeksini p yapar)
            self.doc.delete_page(p)

        self.hide_managed_annotations()
        self.render_pages_init()
        self.rerender_visible_pages()
        curr_p = max(0, min(self.current_page_idx, len(self.doc) - 1))
        self.go_to_page(curr_p)

        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            if self.main_window.thumbnails_dock.isVisible():
                self.main_window.thumbnails_dock.load_thumbnails_lazy()
                self.main_window.thumbnails_dock.select_page(curr_p)

        self.push_undo_action({
            "type": "change_page_style",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": self.doc.tobytes(),
            "new_drawings": [dict(d) for d in self.drawings],
            "new_page": curr_p,
            "style": new_style,
            "all_pages": all_pages
        })
        self.set_modified(True)

    def _apply_page_order(self, order: List[int]):
        if getattr(self, 'active_text_item', None):
            if hasattr(self.active_text_item, 'toPlainText'):
                if self.active_text_item.toPlainText().strip():
                    self.commit_inline_text(self.active_text_item)
                else:
                    self.scene.removeItem(self.active_text_item)
                    self.active_text_item = None
            elif hasattr(self.active_text_item, 'clearFocus'):
                self.active_text_item.clearFocus()
                self.active_text_item = None

        prev_current_page = self.current_page_idx
        self.doc.select(order)

        old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(order)}
        remaining_drawings = []
        for d in self.drawings:
            if "page" in d:
                if d["page"] in old_to_new:
                    d["page"] = old_to_new[d["page"]]
                    remaining_drawings.append(d)
            else:
                remaining_drawings.append(d)
        self.drawings = remaining_drawings

        self.render_pages_init()
        self.rerender_visible_pages()

        new_curr = old_to_new.get(prev_current_page, min(prev_current_page, len(self.doc) - 1))
        new_curr = max(0, min(new_curr, len(self.doc) - 1))
        self.go_to_page(new_curr)

        if hasattr(self.main_window, 'thumbnails_dock'):
            dock = self.main_window.thumbnails_dock
            if dock and dock.isVisible():
                dock.load_thumbnails_lazy()
                dock.select_page(new_curr)

    def _render_pencil_item(self, pts: List[QPointF], d: dict) -> QGraphicsItemGroup:
        group = self.scene.createItemGroup([])
        if not pts:
            return group
        if len(pts) == 1:
            pts = [pts[0], QPointF(pts[0].x() + 0.3, pts[0].y() + 0.3)]

        base_w = float(d.get("width", 2.8))
        col = d.get("color", (0.15, 0.15, 0.15))
        if isinstance(col, QColor):
            base_col = QColor(col)
        elif isinstance(col, (tuple, list)) and len(col) >= 3:
            base_col = QColor.fromRgbF(float(col[0]), float(col[1]), float(col[2]))
        else:
            base_col = QColor("#242424")

        alpha_base = float(d.get("alpha", 1.0))
        base_col.setAlphaF(alpha_base)

        tex = get_graphite_lead_texture(base_col)
        tex_fringe = get_graphite_fringe_texture(base_col)
        line_style = d.get("line_style", "solid")

        # 1. Main textured graphite lead path with micro-jitter
        p_lead = QPainterPath()
        p_lead.moveTo(pts[0])
        if line_style in ("solid", "pencil") and len(pts) > 2:
            for i, pt in enumerate(pts[1:]):
                jx = ((i * 17) % 7 - 3) * 0.05 * base_w
                jy = ((i * 23) % 7 - 3) * 0.05 * base_w
                p_lead.lineTo(pt.x() + jx, pt.y() + jy)
        else:
            for pt in pts[1:]:
                p_lead.lineTo(pt)

        # 2. Arrow head support for pencil
        if line_style == "arrow":
            ah_pts = []
            raw_ah = d.get("arrow_head")
            if raw_ah and len(raw_ah) >= 3:
                p_info = self.page_positions.get(d.get("page"))
                if p_info:
                    p_left = p_info.get('left', 0.0)
                    p_top = p_info['top']
                    ah_pts = [QPointF(x * self.base_render_dpi + p_left, y * self.base_render_dpi + p_top) for x, y in raw_ah]
            if not ah_pts and len(pts) >= 2:
                p_end = pts[-1]
                p_prev = pts[-2] if len(pts) == 2 else pts[max(0, len(pts) - 5)]
                dx = p_end.x() - p_prev.x()
                dy = p_end.y() - p_prev.y()
                dist = math.hypot(dx, dy)
                if dist > 2.0:
                    angle = math.atan2(dy, dx)
                    arrow_len = max(9.0, min(26.0, base_w * 2.2 + 6.0))
                    spread = 0.50
                    left_pt = QPointF(p_end.x() - arrow_len * math.cos(angle - spread), p_end.y() - arrow_len * math.sin(angle - spread))
                    right_pt = QPointF(p_end.x() - arrow_len * math.cos(angle + spread), p_end.y() - arrow_len * math.sin(angle + spread))
                    ah_pts = [left_pt, p_end, right_pt]

            if len(ah_pts) >= 3:
                p_lead.moveTo(ah_pts[0])
                p_lead.lineTo(ah_pts[1])
                p_lead.lineTo(ah_pts[2])

            pen_fringe = QPen(QBrush(tex_fringe), base_w * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            item_fringe = self.scene.addPath(p_lead, pen_fringe)
            group.addToGroup(item_fringe)

            pen_tex = QPen(QBrush(tex), base_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            item_lead = self.scene.addPath(p_lead, pen_tex)
            group.addToGroup(item_lead)
            group.setCacheMode(QGraphicsItemGroup.CacheMode.DeviceCoordinateCache)
            return group

        # 3. Dashed, Dotted, DashDot lines (clean textured graphite with compact handwriting scale)
        if line_style in ("dash", "dot", "dashdot"):
            pen_tex = QPen(QBrush(tex), base_w, Qt.PenStyle.CustomDashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            if line_style == "dash":
                pen_tex.setDashPattern([2.2, 1.5])
            elif line_style == "dot":
                pen_tex.setDashPattern([0.01, 1.9])
            elif line_style == "dashdot":
                pen_tex.setDashPattern([2.2, 1.4, 0.01, 1.4])
            item_lead = self.scene.addPath(p_lead, pen_tex)
            group.addToGroup(item_lead)
            group.setCacheMode(QGraphicsItemGroup.CacheMode.DeviceCoordinateCache)
            return group

        # 4. Solid pencil line: Soft dusty fringe + Rich textured lead + Concentrated core
        pen_fringe = QPen(QBrush(tex_fringe), base_w * 1.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        item_fringe = self.scene.addPath(p_lead, pen_fringe)
        group.addToGroup(item_fringe)

        pen_tex = QPen(QBrush(tex), base_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        item_lead = self.scene.addPath(p_lead, pen_tex)
        group.addToGroup(item_lead)

        pen_core = QPen(QBrush(tex), max(0.6, base_w * 0.58), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        item_core = self.scene.addPath(p_lead, pen_core)
        group.addToGroup(item_core)
        group.setCacheMode(QGraphicsItemGroup.CacheMode.DeviceCoordinateCache)

        return group

    def restore_drawing_item(self, d):
        if "id" not in d:
            d["id"] = uuid.uuid4().hex[:12]
        p_info = self.page_positions.get(d["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        if d.get("type") == "pencil" or d.get("pen_type") == "pencil" or (d.get("type") == "polyline" and d.get("line_style") == "pencil"):
            pts = [QPointF(x * self.base_render_dpi + page_left, y * self.base_render_dpi + page_top) for x, y in d.get("points", [])]
            if not pts: return
            item = self._render_pencil_item(pts, d)
            d["item_ref"] = item
        elif d["type"] == "polyline":
            pts = [QPointF(x * self.base_render_dpi + page_left, y * self.base_render_dpi + page_top) for x, y in d["points"]]
            if not pts: return

            line_style = d.get("line_style", "solid")
            col = d["color"]
            if isinstance(col, QColor):
                pen_col = QColor(col)
                pen_col.setAlphaF(float(d.get("alpha", 1.0)))
            elif isinstance(col, (tuple, list)) and len(col) >= 3:
                pen_col = QColor.fromRgbF(float(col[0]), float(col[1]), float(col[2]), float(d.get("alpha", 1.0)))
            else:
                pen_col = QColor(0, 0, 0, int(float(d.get("alpha", 1.0)) * 255))

            if line_style == 'calligraphy':
                rel_pts = [QPointF(x, y) for x, y in d["points"]]
                rel_w = float(d.get("width", 6.0)) / self.base_render_dpi
                min_w_rel = 1.8 / self.base_render_dpi
                rel_path = build_fountain_pen_path(rel_pts, base_width=rel_w, min_width=min_w_rel)
                transform = QTransform()
                transform.translate(page_left, page_top)
                transform.scale(self.base_render_dpi, self.base_render_dpi)
                scene_path = transform.map(rel_path)
                item = self.scene.addPath(scene_path, QPen(Qt.PenStyle.NoPen), QBrush(pen_col))
                d["item_ref"] = item
                return

            path = QPainterPath(pts[0])
            for pt in pts[1:]: path.lineTo(pt)

            if line_style == "arrow" and d.get("arrow_head"):
                ah = [QPointF(x * self.base_render_dpi + page_left, y * self.base_render_dpi + page_top) for x, y in d["arrow_head"]]
                if len(ah) >= 3:
                    path.moveTo(ah[0])
                    path.lineTo(ah[1])
                    path.lineTo(ah[2])

            pen_style = Qt.PenStyle.SolidLine
            cap = Qt.PenCapStyle.RoundCap
            join = Qt.PenJoinStyle.RoundJoin
            if line_style == 'dash':
                pen_style = Qt.PenStyle.DashLine
            elif line_style == 'dot':
                pen_style = Qt.PenStyle.DotLine
            elif line_style == 'dashdot':
                pen_style = Qt.PenStyle.DashDotLine

            pen = QPen(pen_col, d["width"], pen_style, cap, join)
            d["pen"] = pen
            item = self.scene.addPath(path, pen)
            d["item_ref"] = item
        elif d["type"] == "filled_path":
            rel_path = d.get("rel_path")
            if not rel_path: return
            transform = QTransform()
            transform.translate(page_left, page_top)
            transform.scale(self.base_render_dpi, self.base_render_dpi)
            scene_path = transform.map(rel_path)
            
            col = d["color"]
            if isinstance(col, QColor):
                fill_col = QColor(col)
                fill_col.setAlphaF(float(d.get("alpha", 1.0)))
            elif isinstance(col, (tuple, list)) and len(col) >= 3:
                fill_col = QColor.fromRgbF(float(col[0]), float(col[1]), float(col[2]), float(d.get("alpha", 1.0)))
            else:
                fill_col = QColor(0, 0, 0, int(float(d.get("alpha", 1.0)) * 255))
            
            if d.get("line_style") == "pencil":
                fill_tex = get_graphite_fill_texture(fill_col, float(d.get("alpha", 1.0)))
                item = self.scene.addPath(scene_path, QPen(Qt.PenStyle.NoPen), QBrush(fill_tex))
            else:
                item = self.scene.addPath(scene_path, QPen(Qt.PenStyle.NoPen), QBrush(fill_col))
            d["item_ref"] = item
        elif d["type"] == "text":
            self.render_text_item(d)
        elif d["type"] == "image":
            self.render_image_item(d)
        elif d["type"] == "table":
            self.render_table_item(d)
        elif d["type"] == "audio":
            self.render_audio_item(d)
        elif d["type"] == "video":
            self.render_video_item(d)

    # --- Render & Zoom ---
    def render_pages_init(self):
        if self.doc is None: return
        self.laser_pointer_item = None
        if hasattr(self, 'drawings') and self.drawings:
            for d in self.drawings:
                it = d.get('item_ref')
                if it and hasattr(it, 'stop_movie'):
                    try:
                        it.stop_movie()
                    except Exception:
                        pass
                d['item_ref'] = None
        self.scene.clear()
        self.page_positions.clear()

        brush_col = QColor(255, 255, 255)
        pen_col = QColor(40, 40, 40)
        mode = getattr(self, 'reading_color_mode', 'normal')
        if mode == 'dark':
            brush_col = QColor(24, 24, 26)
            pen_col = QColor(50, 50, 56)
        elif mode == 'sepia':
            brush_col = QColor(246, 238, 220)
            pen_col = QColor(90, 77, 63)

        if self.page_view_mode == "double":
            y_offset = 15
            num_pages = len(self.doc)
            i = 0
            while i < num_pages:
                p_rect1 = self.doc[i].rect
                w1, h1 = p_rect1.width * self.base_render_dpi, p_rect1.height * self.base_render_dpi

                bg_rect1 = self.scene.addRect(0, y_offset, w1, h1, QPen(pen_col, 1), QBrush(brush_col))
                bg_rect1.setZValue(-2)
                bg_rect1.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                pix_item1 = self.scene.addPixmap(QPixmap())
                pix_item1.setPos(0, y_offset)
                pix_item1.setZValue(-1)

                self.page_positions[i] = {
                    'item': pix_item1, 'bg_rect': bg_rect1,
                    'left': 0.0, 'right': w1,
                    'top': y_offset, 'bottom': y_offset + h1,
                    'height': h1, 'width': w1, 'rendered_zoom': 0.0
                }

                row_h = h1
                if i + 1 < num_pages:
                    p_rect2 = self.doc[i + 1].rect
                    w2, h2 = p_rect2.width * self.base_render_dpi, p_rect2.height * self.base_render_dpi
                    x2 = w1 + self.PAGE_MARGIN

                    bg_rect2 = self.scene.addRect(x2, y_offset, w2, h2, QPen(pen_col, 1), QBrush(brush_col))
                    bg_rect2.setZValue(-2)
                    bg_rect2.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                    pix_item2 = self.scene.addPixmap(QPixmap())
                    pix_item2.setPos(x2, y_offset)
                    pix_item2.setZValue(-1)

                    self.page_positions[i + 1] = {
                        'item': pix_item2, 'bg_rect': bg_rect2,
                        'left': float(x2), 'right': float(x2 + w2),
                        'top': y_offset, 'bottom': y_offset + h2,
                        'height': h2, 'width': w2, 'rendered_zoom': 0.0
                    }
                    row_h = max(h1, h2)
                    i += 2
                else:
                    i += 1

                y_offset += row_h + self.PAGE_MARGIN
        else:
            y_offset = 15
            for idx in range(len(self.doc)):
                p_rect = self.doc[idx].rect
                w, h = p_rect.width * self.base_render_dpi, p_rect.height * self.base_render_dpi

                bg_rect = self.scene.addRect(0, y_offset, w, h, QPen(pen_col, 1), QBrush(brush_col))
                bg_rect.setZValue(-2)
                bg_rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                pix_item = self.scene.addPixmap(QPixmap())
                pix_item.setPos(0, y_offset)
                pix_item.setZValue(-1)

                self.page_positions[idx] = {
                    'item': pix_item, 'bg_rect': bg_rect,
                    'left': 0.0, 'right': w,
                    'top': y_offset, 'bottom': y_offset + h,
                    'height': h, 'width': w, 'rendered_zoom': 0.0
                }
                y_offset += h + self.PAGE_MARGIN

        for record in self.drawings:
            self.restore_drawing_item(record)
        self.init_bookmark_ribbons()
        self._load_interactive_form_widgets()
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20, -10, 20, 20))

    def init_bookmark_ribbons(self):
        self.bookmark_ribbon_items = {}
        if not self.doc or not self.page_positions:
            return

        try:
            toc = self.doc.get_toc(simple=False)
            bookmarked_pages = {
                entry[2] - 1 for entry in toc
                if len(entry) > 2 and isinstance(entry[2], int) and entry[2] >= 1
            }
        except Exception:
            bookmarked_pages = set()

        for idx, pinfo in self.page_positions.items():
            rx = pinfo['right'] - BookmarkRibbonItem.WIDTH - 24.0
            ry = pinfo['top']
            ribbon = BookmarkRibbonItem(self, idx, rx, ry, is_bookmarked=(idx in bookmarked_pages))
            self.scene.addItem(ribbon)
            self.bookmark_ribbon_items[idx] = ribbon

    def update_bookmark_ribbons(self):
        if not hasattr(self, 'bookmark_ribbon_items') or not self.doc:
            return
        try:
            toc = self.doc.get_toc(simple=False)
            bookmarked_pages = {
                entry[2] - 1 for entry in toc
                if len(entry) > 2 and isinstance(entry[2], int) and entry[2] >= 1
            }
        except Exception:
            bookmarked_pages = set()

        for idx, ribbon in self.bookmark_ribbon_items.items():
            ribbon.set_bookmarked(idx in bookmarked_pages)

    def toggle_page_bookmark(self, page_idx: int):
        if self.doc is None or page_idx < 0 or page_idx >= len(self.doc):
            return

        try:
            toc = self.doc.get_toc(simple=False)
            old_toc = [list(entry) for entry in toc]
            target_page_1_based = page_idx + 1

            matching_indices = [
                i for i, entry in enumerate(toc)
                if len(entry) > 2 and isinstance(entry[2], int) and entry[2] == target_page_1_based
            ]

            if matching_indices:
                for i in reversed(matching_indices):
                    del toc[i]
                msg = f"Sayfa {target_page_1_based} yer imlerinden kaldırıldı"
            else:
                insert_idx = len(toc)
                for i, entry in enumerate(toc):
                    p_num = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 0
                    if p_num > target_page_1_based:
                        insert_idx = i
                        break
                toc.insert(insert_idx, [1, f"Sayfa {target_page_1_based}", target_page_1_based])
                msg = f"Sayfa {target_page_1_based} yer imlerine eklendi"

            self.doc.set_toc(toc)
            self.set_modified(True)

            self.push_undo_action({
                "type": "bookmark",
                "old_toc": old_toc,
                "new_toc": [list(e) for e in toc]
            })

            self.update_bookmark_ribbons()

            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                self.main_window.thumbnails_dock.load_bookmarks()

            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(msg, 3000)

        except Exception as e:
            print(f"Yer imi değiştirme hatası: {e}")

    def rename_page_bookmark(self, page_idx: int):
        if self.doc is None or page_idx < 0 or page_idx >= len(self.doc):
            return
        target_page_1_based = page_idx + 1
        toc = self.doc.get_toc(simple=False)
        old_title = f"Sayfa {target_page_1_based}"
        for entry in toc:
            if len(entry) > 2 and entry[2] == target_page_1_based:
                old_title = str(entry[1] or "")
                break

        title, ok = QInputDialog.getText(self, "Yer İmini Yeniden Adlandır", "Başlık:", text=old_title)
        if not ok or not title.strip():
            return

        old_toc = [list(entry) for entry in toc]
        found = False
        for entry in toc:
            if len(entry) > 2 and entry[2] == target_page_1_based:
                entry[1] = title.strip()
                found = True
                break
        if not found:
            toc.append([1, title.strip(), target_page_1_based])

        self.doc.set_toc(toc)
        self.set_modified(True)
        self.push_undo_action({
            "type": "bookmark",
            "old_toc": old_toc,
            "new_toc": [list(e) for e in toc]
        })
        self.update_bookmark_ribbons()
        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_bookmarks()

    def add_custom_page_bookmark(self, page_idx: int):
        if self.doc is None or page_idx < 0 or page_idx >= len(self.doc):
            return
        target_page_1_based = page_idx + 1

        toc = self.doc.get_toc(simple=False)
        old_toc = [list(entry) for entry in toc]

        existing_indices = [
            i for i, entry in enumerate(toc)
            if len(entry) > 2 and isinstance(entry[2], int) and entry[2] == target_page_1_based
        ]

        if existing_indices:
            prompt_title = "Alt Yer İmi Ekle"
            prompt_label = f"Sayfa {target_page_1_based} için Alt Yer İmi Başlığı:"
            default_title = f"Sayfa {target_page_1_based} - Not {len(existing_indices)}"
        else:
            prompt_title = "Özel Yer İmi Ekle"
            prompt_label = "Başlık:"
            default_title = f"Sayfa {target_page_1_based}"

        title, ok = QInputDialog.getText(self, prompt_title, prompt_label, text=default_title)
        if not ok or not title.strip():
            return

        if existing_indices:
            last_idx = existing_indices[-1]
            parent_level = toc[existing_indices[0]][0] if isinstance(toc[existing_indices[0]][0], int) else 1
            new_level = parent_level + 1
            insert_idx = last_idx + 1
        else:
            new_level = 1
            insert_idx = len(toc)
            for i, entry in enumerate(toc):
                p_num = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 0
                if p_num > target_page_1_based:
                    insert_idx = i
                    break

        toc.insert(insert_idx, [new_level, title.strip(), target_page_1_based])

        self.doc.set_toc(toc)
        self.set_modified(True)
        self.push_undo_action({
            "type": "bookmark",
            "old_toc": old_toc,
            "new_toc": [list(e) for e in toc]
        })
        self.update_bookmark_ribbons()
        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_bookmarks()

    def rerender_visible_pages(self, force: bool = False):
        if self.doc is None or not self.page_positions: return

        visible_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        buffer_top, buffer_bottom = visible_rect.top() - 800, visible_rect.bottom() + 800
        target_scale = self.base_render_dpi * self.zoom_level
        mat = fitz.Matrix(target_scale, target_scale)

        mode = getattr(self, 'reading_color_mode', 'normal')

        for idx, pinfo in self.page_positions.items():
            if not (pinfo['bottom'] < buffer_top or pinfo['top'] > buffer_bottom):
                if force or abs(pinfo.get('rendered_zoom', 0.0) - self.zoom_level) > 0.05 or pinfo['item'].pixmap().isNull():
                    pix = self.doc[idx].get_pixmap(matrix=mat)
                    if mode == 'dark':
                        pix.invert_irect()
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    if mode == 'sepia':
                        p_sepia = QPainter(qimg)
                        p_sepia.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                        p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                        p_sepia.end()

                    pinfo['item'].setPixmap(QPixmap.fromImage(qimg))
                    pinfo['item'].setScale(1.0 / self.zoom_level)
                    pinfo['rendered_zoom'] = self.zoom_level
            elif pinfo.get('rendered_zoom', 0.0) > 0.0:
                dist = min(abs(pinfo['bottom'] - visible_rect.top()), abs(pinfo['top'] - visible_rect.bottom()))
                if dist > 2500:
                    pinfo['item'].setPixmap(QPixmap())
                    pinfo['rendered_zoom'] = 0.0

    def set_reading_color_mode(self, mode: str):
        if mode not in ("normal", "dark", "sepia"):
            mode = "normal"
        self.reading_color_mode = mode
        bg_col = QColor(255, 255, 255)
        border_col = QColor(40, 40, 40)
        scene_bg = "#181818"
        if mode == "dark":
            bg_col = QColor(24, 24, 26)
            border_col = QColor(50, 50, 56)
            scene_bg = "#0f0f10"
        elif mode == "sepia":
            bg_col = QColor(246, 238, 220)
            border_col = QColor(90, 77, 63)
            scene_bg = "#221e1a"

        self.view.setStyleSheet(f"background-color: {scene_bg}; border: none;")
        for idx, pinfo in self.page_positions.items():
            if 'bg_rect' in pinfo and pinfo['bg_rect']:
                pinfo['bg_rect'].setBrush(QBrush(bg_col))
                pinfo['bg_rect'].setPen(QPen(border_col, 1))

        self.rerender_visible_pages(force=True)

    def reload_from_disk(self):
        if not self.file_path or not os.path.isfile(self.file_path):
            return
        try:
            with open(self.file_path, "rb") as f:
                b = f.read()
            if self.doc and not getattr(self.doc, 'is_closed', False):
                self.doc.close()
            self.doc = fitz.open("pdf", b)
            for d in self.drawings:
                it = d.get("item_ref")
                if it and it.scene() == self.scene:
                    self.scene.removeItem(it)
            self.drawings.clear()
            self.clear_selection()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.save_undo_index = 0
            self.set_modified(False)
            self._load_annotations_from_doc()
            self.render_pages_init()
            self.rerender_visible_pages(force=True)
            if hasattr(self.main_window, 'update_undo_redo_state'):
                self.main_window.update_undo_redo_state()
        except Exception:
            pass

    def get_saved_zoom_level(self) -> float:
        try:
            settings = QSettings("AuraPDF", "PDFViewer")
            if getattr(self, 'file_path', None):
                norm = os.path.abspath(self.file_path)
                raw = settings.value("file_zoom_levels", "{}")
                import json
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                if norm in data:
                    val = float(data[norm])
                    return max(0.4, min(round(val, 2), 4.0))
            last_z = settings.value("last_zoom_level", None)
            if last_z is not None:
                return max(0.4, min(round(float(last_z), 2), 4.0))
        except Exception:
            pass
        return 1.0

    def save_zoom_setting(self):
        try:
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("last_zoom_level", float(round(self.zoom_level, 2)))
            if getattr(self, 'file_path', None):
                norm = os.path.abspath(self.file_path)
                raw = settings.value("file_zoom_levels", "{}")
                import json
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                data[norm] = float(round(self.zoom_level, 2))
                if len(data) > 1000:
                    data = dict(list(data.items())[-1000:])
                settings.setValue("file_zoom_levels", json.dumps(data))
        except Exception:
            pass

    def apply_zoom(self, new_level):
        new_level = max(0.4, min(round(new_level, 2), 4.0))
        if new_level == self.zoom_level: return
        self.view.scale(new_level / self.zoom_level, new_level / self.zoom_level)
        self.zoom_level = new_level
        if hasattr(self.main_window, 'update_zoom_display'):
            self.main_window.update_zoom_display(int(self.zoom_level * 100))
        elif hasattr(self.main_window, 'lbl_zoom'):
            self.main_window.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(self.zoom_level * 100))} ")
        self.rerender_timer.start(250)
        self.save_zoom_setting()
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.reposition()
        if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
            self.direct_edit_banner.reposition()

    def zoom_in(self): self.apply_zoom(self.zoom_level + 0.15)
    def zoom_out(self): self.apply_zoom(self.zoom_level - 0.15)
    def fit_to_width(self):
        if not self.page_positions or self.doc is None:
            return
        if self.page_view_mode == "double":
            p0 = self.page_positions.get(0, {})
            p1 = self.page_positions.get(1, {})
            total_w = p0.get('width', 595.0) + (p1.get('width', 595.0) + self.PAGE_MARGIN if p1 else 0)
            viewport_w = self.view.viewport().width() - 40
            if total_w > 0 and viewport_w > 100:
                target_zoom = viewport_w / total_w
                self.apply_zoom(target_zoom)
        else:
            first_page_w = self.page_positions[0]['width']
            viewport_w = self.view.viewport().width() - 40
            if first_page_w > 0 and viewport_w > 100:
                target_zoom = viewport_w / first_page_w
                self.apply_zoom(target_zoom)

    def fit_to_page(self):
        if not self.page_positions or self.doc is None:
            return
        cur_p = self.page_positions.get(self.current_page_idx, self.page_positions.get(0, {}))
        pw = cur_p.get('width', 595.0)
        ph = cur_p.get('height', 842.0)
        viewport_w = self.view.viewport().width() - 40
        viewport_h = self.view.viewport().height() - 40
        if pw > 0 and ph > 0 and viewport_w > 100 and viewport_h > 100:
            target_zoom = min(viewport_w / pw, viewport_h / ph)
            self.apply_zoom(target_zoom)
            self.go_to_page(self.current_page_idx)

    def on_scroll_change(self):
        self.update_current_page_indicator()
        self.rerender_timer.start(150)
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.reposition()
        if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
            self.direct_edit_banner.reposition()

    # --- Metin Arama (Search Engine & Highlights) ---
    def perform_search(self, query: str, case_sensitive: bool = False) -> int:
        self.clear_search_highlights()
        if not query or self.doc is None:
            return 0

        self.search_results = []
        for page_idx in range(len(self.doc)):
            page = self.doc[page_idx]
            rects = page.search_for(query)
            if not rects:
                continue

            pinfo = self.page_positions.get(page_idx)
            page_top = pinfo['top'] if pinfo else 0

            for r in rects:
                if case_sensitive:
                    txt = page.get_text("text", clip=r).strip()
                    if query not in txt:
                        continue

                sx0 = r.x0 * self.base_render_dpi
                sy0 = r.y0 * self.base_render_dpi + page_top
                sw = (r.x1 - r.x0) * self.base_render_dpi
                sh = (r.y1 - r.y0) * self.base_render_dpi
                scene_rect = QRectF(sx0, sy0, sw, sh)
                self.search_results.append((page_idx, r, scene_rect))

                # Background highlight rectangle
                h_item = self.scene.addRect(
                    scene_rect.adjusted(-1, -1, 1, 1),
                    QPen(QColor(251, 192, 45, 140), 1),
                    QBrush(QColor(255, 235, 59, 90))
                )
                h_item.setZValue(5)
                self.search_highlight_items.append(h_item)

        if self.search_results:
            self._focus_search_match(0)

        return len(self.search_results)

    def _focus_search_match(self, idx: int):
        if idx < 0 or idx >= len(self.search_results):
            return
        self.search_current_idx = idx
        page_idx, r, scene_rect = self.search_results[idx]

        # Active match glowing highlight
        if self.search_active_item and self.search_active_item.scene() == self.scene:
            self.scene.removeItem(self.search_active_item)

        self.search_active_item = self.scene.addRect(
            scene_rect.adjusted(-2, -2, 2, 2),
            QPen(QColor(230, 81, 0, 240), 2),
            QBrush(QColor(255, 152, 0, 160))
        )
        self.search_active_item.setZValue(6)

        self.view.centerOn(scene_rect.center())

        if self.current_page_idx != page_idx:
            self.current_page_idx = page_idx
            self.main_window.txt_page.setText(str(page_idx + 1))
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock.isVisible():
                self.main_window.thumbnails_dock.select_page(page_idx)

    def next_search_match(self) -> int:
        if not self.search_results:
            return -1
        new_idx = (self.search_current_idx + 1) % len(self.search_results)
        self._focus_search_match(new_idx)
        return new_idx

    def prev_search_match(self) -> int:
        if not self.search_results:
            return -1
        new_idx = (self.search_current_idx - 1) % len(self.search_results)
        self._focus_search_match(new_idx)
        return new_idx

    def clear_search_highlights(self):
        if hasattr(self, 'search_highlight_items'):
            for item in self.search_highlight_items:
                if item and item.scene() == self.scene:
                    self.scene.removeItem(item)
            self.search_highlight_items.clear()
        if hasattr(self, 'search_active_item') and self.search_active_item:
            if self.search_active_item.scene() == self.scene:
                self.scene.removeItem(self.search_active_item)
            self.search_active_item = None
        self.search_results = []
        self.search_current_idx = -1

    # --- Metin İşlemleri ---
    def create_inline_text(self, scene_pos, page_idx):
        if self.active_text_item: self.active_text_item.clearFocus()
        p_info = self.page_positions.get(page_idx)
        if not p_info: return
        page_left = p_info.get('left', 0.0)
        clamped_x = max(page_left, min(scene_pos.x(), page_left + p_info['width'] - 60))
        clamped_y = max(p_info['top'], min(scene_pos.y(), p_info['bottom'] - 30))
        popup = self.main_window.text_popup
        item = EditableInlineTextItem(
            self, page_idx, QPointF(clamped_x, clamped_y),
            popup.font_family,
            popup.font_size,
            popup.color,
            bold=getattr(popup, 'bold', False),
            italic=getattr(popup, 'italic', False),
            underline=getattr(popup, 'underline', False),
        )
        self.scene.addItem(item)
        self.active_text_item = item

    def commit_inline_text(self, item):
        content = item.toPlainText().strip()
        
        # Manuel atanmış bağlantı kontrolü (Kullanıcı metne veya kelimeye özel bir URL bağlamışsa)
        is_manual = getattr(item, 'manual_link', False) or (bool(getattr(item, 'link_url', '')) and getattr(item, 'link_url', '') != content)
        
        if is_manual and getattr(item, 'link_url', ''):
            item.manual_link = True
            link_text = getattr(item, 'link_text', '')
            link_range = getattr(item, 'link_range', None)
            if link_text and link_text in content:
                item.format_link_substring(link_text, item.link_url, char_range=link_range)
            elif getattr(item, 'link_url', ''):
                if link_text and link_text not in content:
                    item.clear_link_formatting()
                else:
                    item.format_entire_text_as_link(item.link_url)
        else:
            # Otomatik URL / E-Posta / Telefon / T.C. Kimlik Algılama
            from src.core.hyperlink_detector import detect_hyperlink
            detected = detect_hyperlink(content)
            if detected:
                item.link_url = detected["url"]
                item.link_type = detected["type"]
                item.link_raw = detected["raw"]
                item.setToolTip(detected["tooltip"])
                if item.link_url:
                    item.format_entire_text_as_link(item.link_url)
                elif not getattr(item, 'underline', False):
                    item.underline = True
                    item._apply_font()
            elif item.link_url or getattr(item, 'manual_link', False) or getattr(item, 'link_text', ''):
                item.clear_link_formatting()
                
        p_info = self.page_positions[item.page_idx]
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)
        rel_x, rel_y = (item.pos().x() - page_left) / self.base_render_dpi, (item.pos().y() - page_top) / self.base_render_dpi
        br = item.boundingRect()
        w_pt = max(40.0, br.width() / self.base_render_dpi)
        h_pt = max(20.0, br.height() / self.base_render_dpi)

        existing = [d for d in self.drawings if d.get("item_ref") == item]
        new_html = item.toHtml() if hasattr(item, 'toHtml') else ""
        frags = item.get_fragments() if hasattr(item, 'get_fragments') else None

        if existing:
            record = existing[0]
            changed = (
                record.get("text") != content or 
                record.get("html") != new_html or
                record.get("fragments") != frags or
                record.get("link_url") != getattr(item, 'link_url', "") or
                record.get("link_text") != getattr(item, 'link_text', "") or
                record.get("link_range") != getattr(item, 'link_range', None) or
                record.get("bold") != getattr(item, 'bold', False) or
                record.get("italic") != getattr(item, 'italic', False) or
                record.get("underline") != getattr(item, 'underline', False) or
                record.get("font_size") != item.font_size or
                record.get("color") != item.text_color
            )
            if changed:
                old_val = record.get("text", "")
                old_html = record.get("html", "")
                old_frags = record.get("fragments", None)
                record["text"] = content
                record["html"] = new_html
                record["fragments"] = frags
                record["font_size"] = item.font_size
                record["font_family"] = item.font_family
                record["color"] = item.text_color
                record["bold"] = getattr(item, 'bold', False)
                record["italic"] = getattr(item, 'italic', False)
                record["underline"] = getattr(item, 'underline', False)
                record["link_url"] = getattr(item, 'link_url', "")
                record["link_type"] = getattr(item, 'link_type', "")
                record["link_raw"] = getattr(item, 'link_raw', "")
                record["link_text"] = getattr(item, 'link_text', "")
                record["link_range"] = getattr(item, 'link_range', None)
                record["manual_link"] = getattr(item, 'manual_link', False)
                record["x"] = rel_x
                record["y"] = rel_y
                record["w"] = w_pt
                record["h"] = h_pt
                self.push_undo_action({
                    "type": "edit_text", "record": record,
                    "old_text": old_val, "new_text": content,
                    "old_html": old_html, "new_html": new_html,
                    "old_fragments": old_frags, "new_fragments": frags
                })
        else:
            item_data = {
                "type": "text", "page": item.page_idx, "text": content,
                "html": new_html, "fragments": frags,
                "font_size": item.font_size, "font_family": item.font_family,
                "color": item.text_color, "x": rel_x, "y": rel_y,
                "w": w_pt, "h": h_pt, "item_ref": item,
                "bold": getattr(item, 'bold', False),
                "italic": getattr(item, 'italic', False),
                "underline": getattr(item, 'underline', False),
                "link_url": getattr(item, 'link_url', ""),
                "link_type": getattr(item, 'link_type', ""),
                "link_raw": getattr(item, 'link_raw', ""),
                "link_text": getattr(item, 'link_text', ""),
                "link_range": getattr(item, 'link_range', None),
                "manual_link": getattr(item, 'manual_link', False),
            }
            self.drawings.append(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
        self.notify_drawings_changed(item.page_idx)
        self.last_text_item = item
        if not (item.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction):
            self.active_text_item = None
        else:
            self.active_text_item = item

    # --- Doğrudan Belge Üzerinde Metin Düzenleme (RevPDF Stili) ---
    def enable_direct_text_edit(self, enable: bool = True):
        self.direct_edit_mode = enable
        if enable:
            if self.direct_edit_hover_item is None:
                from src.ui.direct_text_editor import DirectEditHoverItem
                self.direct_edit_hover_item = DirectEditHoverItem()
                self.scene.addItem(self.direct_edit_hover_item)
            if self.direct_edit_banner is None:
                from src.ui.direct_text_editor import DirectEditBanner
                self.direct_edit_banner = DirectEditBanner(self)
            self.direct_edit_banner.show()
            self.direct_edit_banner.reposition()
            self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.close_inplace_editor()
            if self.direct_edit_hover_item and self.direct_edit_hover_item.scene() == self.scene:
                self.direct_edit_hover_item.hide()
            if self.direct_edit_banner:
                self.direct_edit_banner.hide()
            self.main_window.update_viewport_cursor()

    def exit_direct_text_edit(self):
        self.enable_direct_text_edit(False)
        self.main_window.set_tool_state('select')

    def close_inplace_editor(self):
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.hide()
            self.direct_edit_editor.deleteLater()
            self.direct_edit_editor = None

    def get_page_text_blocks(self, page_idx: int) -> List[Dict[str, Any]]:
        if not self.doc or page_idx >= len(self.doc):
            return []
        if page_idx not in self._page_text_blocks_cache:
            from src.ui.direct_text_editor import extract_page_text_blocks
            self._page_text_blocks_cache[page_idx] = extract_page_text_blocks(self.doc[page_idx])
        return self._page_text_blocks_cache[page_idx]

    def open_inplace_editor_at_block(self, page_idx: int, blk: dict):
        self.close_inplace_editor()
        from src.ui.direct_text_editor import DirectTextInplaceEditor
        editor = DirectTextInplaceEditor(
            self, page_idx, blk["bbox"], blk["text"],
            font_size=blk["font_size"], color_rgb=blk["color_rgb"],
            bold=blk["bold"], italic=blk["italic"], is_new=False
        )
        self.direct_edit_editor = editor
        editor.show()

    def open_inplace_editor_for_new_text(self, page_idx: int, click_pos: QPointF):
        self.close_inplace_editor()
        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return
        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.base_render_dpi
        pdf_x = max(20.0, (click_pos.x() - page_left) / dpi)
        pdf_y = max(20.0, (click_pos.y() - page_top) / dpi)
        pdf_rect = fitz.Rect(pdf_x, pdf_y, min(p_info['width'] / dpi - 20, pdf_x + 180), min(p_info['height'] / dpi - 20, pdf_y + 35))

        from src.ui.direct_text_editor import DirectTextInplaceEditor
        editor = DirectTextInplaceEditor(
            self, page_idx, pdf_rect, "",
            font_size=12.0, color_rgb=(0.0, 0.0, 0.0),
            bold=False, italic=False, is_new=True
        )
        self.direct_edit_editor = editor
        editor.show()

    def commit_direct_text_edit(self, page_idx: int, orig_bbox: fitz.Rect, new_text: str,
                                font_size: float, color_rgb: tuple, bold: bool, italic: bool, is_new: bool = False):
        if not self.doc or page_idx >= len(self.doc):
            return
        page = self.doc[page_idx]
        old_bytes = self.doc.tobytes()

        from src.ui.direct_text_editor import get_unicode_font_path, find_fitting_box

        try:
            # 1. Eski metin alanını kalıcı olarak temizle (redact)
            if not is_new:
                clean_rect = fitz.Rect(orig_bbox)
                clean_rect.x0 = max(0.0, clean_rect.x0 - 1.2)
                clean_rect.y0 = max(0.0, clean_rect.y0 - 1.2)
                clean_rect.x1 = min(page.rect.width, clean_rect.x1 + 1.2)
                clean_rect.y1 = min(page.rect.height, clean_rect.y1 + 1.2)
                page.add_redact_annot(clean_rect, fill=(1, 1, 1))
                page.apply_redactions()

            # 2. Yeni metni yaz
            if new_text.strip():
                fontfile = get_unicode_font_path(bold=bold, italic=italic)
                fontname = "f_arial_u"
                try:
                    page.insert_font(fontname=fontname, fontfile=fontfile)
                except Exception:
                    pass

                fit_rect, fit_fs = find_fitting_box(page, orig_bbox, new_text, target_fs=font_size, fontfile=fontfile, fontname=fontname)
                if not is_new and fit_rect.y1 > clean_rect.y1:
                    extra_r = fitz.Rect(fit_rect.x0, clean_rect.y1, fit_rect.x1, fit_rect.y1)
                    page.add_redact_annot(extra_r, fill=(1, 1, 1))
                    page.apply_redactions()

                res = page.insert_textbox(
                    fit_rect, new_text,
                    fontsize=fit_fs,
                    fontname=fontname,
                    fontfile=fontfile,
                    color=color_rgb
                )
                if res < 0:
                    page.insert_text(
                        fitz.Point(fit_rect.x0, fit_rect.y0 + fit_fs),
                        new_text,
                        fontsize=fit_fs,
                        fontname=fontname,
                        fontfile=fontfile,
                        color=color_rgb
                    )

            new_bytes = self.doc.tobytes()
            self.push_undo_action({
                "type": "direct_text_edit",
                "old_bytes": old_bytes,
                "new_bytes": new_bytes,
                "page_idx": page_idx
            })

            self._page_text_blocks_cache.pop(page_idx, None)
            self.set_modified(True)
            self.rerender_visible_pages(force=True)
            self.close_inplace_editor()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(LanguageManager.tr("direct_edit_success"), 3500)

        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('direct_edit_failed')}\n{e}")

    def delete_direct_text_block(self, page_idx: int, orig_bbox: fitz.Rect):
        if not self.doc or page_idx >= len(self.doc):
            return
        page = self.doc[page_idx]
        old_bytes = self.doc.tobytes()
        try:
            clean_rect = fitz.Rect(orig_bbox)
            clean_rect.x0 = max(0.0, clean_rect.x0 - 1.2)
            clean_rect.y0 = max(0.0, clean_rect.y0 - 1.2)
            clean_rect.x1 = min(page.rect.width, clean_rect.x1 + 1.2)
            clean_rect.y1 = min(page.rect.height, clean_rect.y1 + 1.2)
            page.add_redact_annot(clean_rect, fill=(1, 1, 1))
            page.apply_redactions()

            new_bytes = self.doc.tobytes()
            self.push_undo_action({
                "type": "direct_text_edit",
                "old_bytes": old_bytes,
                "new_bytes": new_bytes,
                "page_idx": page_idx
            })
            self._page_text_blocks_cache.pop(page_idx, None)
            self.set_modified(True)
            self.rerender_visible_pages(force=True)
            self.close_inplace_editor()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(LanguageManager.tr("direct_edit_deleted"), 3500)
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('direct_edit_delete_failed')}\n{e}")

    def _handle_direct_edit_mouse_move(self, pos: QPointF):
        if not self.direct_edit_hover_item:
            from src.ui.direct_text_editor import DirectEditHoverItem
            self.direct_edit_hover_item = DirectEditHoverItem()
            self.scene.addItem(self.direct_edit_hover_item)

        page_idx = self.get_page_at_pos(pos)
        if page_idx is None:
            self.direct_edit_hover_item.hide()
            self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            return

        p_info = self.page_positions.get(page_idx)
        if not p_info:
            self.direct_edit_hover_item.hide()
            return

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.base_render_dpi

        if self.direct_edit_editor:
            self.direct_edit_hover_item.hide()
            return

        pdf_x = (pos.x() - page_left) / dpi
        pdf_y = (pos.y() - page_top) / dpi
        pdf_pt = fitz.Point(pdf_x, pdf_y)

        blocks = self.get_page_text_blocks(page_idx)
        hit_blk = None
        for blk in blocks:
            if pdf_pt in blk["bbox"]:
                hit_blk = blk
                break

        if hit_blk:
            r = hit_blk["bbox"]
            sx0 = page_left + r.x0 * dpi
            sy0 = page_top + r.y0 * dpi
            sw = (r.x1 - r.x0) * dpi
            sh = (r.y1 - r.y0) * dpi
            self.direct_edit_hover_item.setRect(QRectF(sx0 - 2, sy0 - 2, sw + 4, sh + 4))
            self.direct_edit_hover_item.show()
            self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.direct_edit_hover_item.hide()
            self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    def _handle_direct_edit_mouse_press(self, pos: QPointF, vp_pos: QPoint) -> bool:
        if self.direct_edit_editor and self.direct_edit_editor.geometry().contains(vp_pos):
            return False

        page_idx = self.get_page_at_pos(pos)
        if page_idx is None:
            self.close_inplace_editor()
            return True

        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return True

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.base_render_dpi

        pdf_x = (pos.x() - page_left) / dpi
        pdf_y = (pos.y() - page_top) / dpi
        pdf_pt = fitz.Point(pdf_x, pdf_y)

        blocks = self.get_page_text_blocks(page_idx)
        hit_blk = None
        for blk in blocks:
            if pdf_pt in blk["bbox"]:
                hit_blk = blk
                break

        if hit_blk:
            self.open_inplace_editor_at_block(page_idx, hit_blk)
            return True
        else:
            if self.direct_edit_editor:
                self.close_inplace_editor()
            else:
                self.open_inplace_editor_for_new_text(page_idx, pos)
            return True

    def render_text_item(self, record):
        p_info = self.page_positions.get(record["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        col = record.get("color", QColor(230, 230, 230))
        if isinstance(col, (tuple, list)) and len(col) >= 3:
            r = max(0.0, min(1.0, float(col[0])))
            g = max(0.0, min(1.0, float(col[1])))
            b = max(0.0, min(1.0, float(col[2])))
            col = QColor.fromRgbF(r, g, b)
        elif not isinstance(col, QColor):
            col = QColor(0, 0, 0)

        initial_text = "" if record.get("html") else record.get("text", "")
        item = EditableInlineTextItem(
            self, record["page"], 
            QPointF(record["x"] * self.base_render_dpi + page_left, record["y"] * self.base_render_dpi + page_top),
            record.get("font_family", "Arial"), record.get("font_size", 14), col, initial_text,
            bold=record.get("bold", False),
            italic=record.get("italic", False),
            underline=record.get("underline", False),
        )
        if record.get("html"):
            item.setHtml(record["html"])

        from src.core.hyperlink_detector import detect_hyperlink
        if record.get("link_url") or record.get("manual_link"):
            item.link_url = record.get("link_url", "")
            item.link_type = record.get("link_type", "url")
            item.link_raw = record.get("link_raw", "")
            item.link_text = record.get("link_text", "")
            item.link_range = record.get("link_range", None)
            item.manual_link = record.get("manual_link", False)
            if item.link_type == "tc":
                item.setToolTip(f"T.C. Kimlik No: {item.link_raw or record.get('text', '')}\n(Tıklayarak panoya kopyalayın)")
            elif item.link_url:
                if item.link_text:
                    item.setToolTip(f"Bağlantı: {item.link_url}\n('{item.link_text}' üzerine tıklayarak siteye gidin)")
                    if not record.get("html"):
                        item.format_link_substring(item.link_text, item.link_url, char_range=item.link_range)
                else:
                    item.setToolTip(f"Bağlantı: {item.link_url}\n(Tıklayarak siteye gidin)")
                    if not record.get("html"):
                        item.format_entire_text_as_link(item.link_url)
        elif not record.get("html"):
            detected = detect_hyperlink(record.get("text", ""))
            if detected:
                item.link_url = detected["url"]
                item.link_type = detected["type"]
                item.link_raw = detected["raw"]
                item.setToolTip(detected["tooltip"])
                record["link_url"] = detected["url"]
                record["link_type"] = detected["type"]
                record["link_raw"] = detected["raw"]
                if item.link_url:
                    item.format_entire_text_as_link(item.link_url)
                elif not getattr(item, 'underline', False):
                    item.underline = True
                    item._apply_font()
        item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.scene.addItem(item)
        record["item_ref"] = item

    def render_image_item(self, record):
        p_info = self.page_positions.get(record["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        item = PDFResizableImageItem(self, record)
        item_x = record["x"] * self.base_render_dpi + page_left
        item_y = record["y"] * self.base_render_dpi + page_top
        item.setPos(item_x, item_y)
        self.scene.addItem(item)
        record["item_ref"] = item

    def render_table_item(self, record):
        p_info = self.page_positions.get(record["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        item = PDFTableItem(self, record)
        item_x = record["x"] * self.base_render_dpi + page_left
        item_y = record["y"] * self.base_render_dpi + page_top
        item.setPos(item_x, item_y)
        self.scene.addItem(item)
        record["item_ref"] = item

    def render_audio_item(self, record):
        p_info = self.page_positions.get(record["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        item = PDFAudioItem(self, record)
        item_x = record["x"] * self.base_render_dpi + page_left
        item_y = record["y"] * self.base_render_dpi + page_top
        item.setPos(item_x, item_y)
        self.scene.addItem(item)
        record["item_ref"] = item

    def render_video_item(self, record):
        p_info = self.page_positions.get(record["page"])
        if not p_info: return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)

        item = PDFVideoItem(self, record)
        item_x = record["x"] * self.base_render_dpi + page_left
        item_y = record["y"] * self.base_render_dpi + page_top
        item.setPos(item_x, item_y)
        self.scene.addItem(item)
        record["item_ref"] = item

    def add_table(self, rows: int = 3, cols: int = 3, has_header: bool = True,
                  border_color: str = "#c4b5fd", header_bg: str = "#7c3aed",
                  cell_bg: str = "#ffffff", text_color: str = "#1e1b4b",
                  header_text_color: str = "#ffffff", alt_cell_bg: Optional[str] = None,
                  page_idx: Optional[int] = None, pos: Optional[QPointF] = None):
        """Belgeye boyutlandırılabilir ve düzenlenebilir tablo ekler."""
        if self.doc is None or len(self.doc) == 0:
            return
        try:
            if page_idx is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                for p_i, p_b in self.page_positions.items():
                    if p_b['top'] <= center_y <= p_b['bottom']:
                        page_idx = p_i
                        break
                if page_idx is None:
                    page_idx = self.current_page_idx
            p_info = self.page_positions.get(page_idx)
            if not p_info:
                return

            page_top = p_info['top']
            page_left = p_info.get('left', 0.0)
            page_pdf_w = p_info['width'] / self.base_render_dpi
            page_pdf_h = p_info['height'] / self.base_render_dpi

            table_pdf_w = min(max(20.0, page_pdf_w - 40.0), max(180.0, cols * 70.0))
            table_pdf_w = max(40.0, min(table_pdf_w, page_pdf_w))
            table_pdf_h = max(24.0, min(rows * 26.0, page_pdf_h))

            if pos is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                if p_info['top'] <= center_y <= p_info['bottom']:
                    pdf_y = (center_y - page_top) / self.base_render_dpi - table_pdf_h / 2.0
                else:
                    pdf_y = 60.0
                pdf_x = (page_pdf_w - table_pdf_w) / 2.0
            else:
                pdf_x = (pos.x() - page_left) / self.base_render_dpi
                pdf_y = (pos.y() - page_top) / self.base_render_dpi

            pdf_x = max(0.0, min(pdf_x, max(0.0, page_pdf_w - table_pdf_w)))
            pdf_y = max(0.0, min(pdf_y, max(0.0, page_pdf_h - table_pdf_h)))

            cell_data = [["" for _ in range(cols)] for _ in range(rows)]
            if has_header and rows > 0:
                for c in range(cols):
                    cell_data[0][c] = f"Başlık {c + 1}"

            if not alt_cell_bg:
                c_cell = QColor(cell_bg)
                alt_cell_bg = c_cell.darker(106).name() if c_cell.lightness() > 128 else c_cell.lighter(118).name()

            item_data = {
                "type": "table",
                "page": page_idx,
                "x": pdf_x,
                "y": pdf_y,
                "w": table_pdf_w,
                "h": table_pdf_h,
                "rows": rows,
                "cols": cols,
                "has_header": has_header,
                "border_color": border_color,
                "header_bg": header_bg,
                "cell_bg": cell_bg,
                "alt_cell_bg": alt_cell_bg,
                "text_color": text_color,
                "header_text_color": header_text_color,
                "font_size": 11.0,
                "font_family": "Arial",
                "cell_data": cell_data
            }

            self.drawings.append(item_data)
            self.render_table_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)

            it = item_data.get("item_ref")
            if it:
                it.setSelected(True)
                self.active_text_item = it
                self.last_text_item = it
                if hasattr(self.main_window, 'text_popup') and self.main_window.text_popup:
                    self.main_window.text_popup.sync_with_item_selection(it)
            if hasattr(self.main_window, 'set_tool_state'):
                self.main_window.set_tool_state('select')
        except Exception as e:
            import traceback
            traceback.print_exc()

    def add_image_media(self, image_bytes: bytes, title: str = "Görsel",
                         page_idx: Optional[int] = None, pos: Optional[QPointF] = None,
                         default_w: Optional[float] = None, default_h: Optional[float] = None,
                         keep_aspect: bool = True):
        """Belgeye boyutlandırılabilir görsel veya emoji ekler."""
        if self.doc is None or not image_bytes:
            return
        try:
            if page_idx is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                for p_i, p_b in self.page_positions.items():
                    if p_b['top'] <= center_y <= p_b['bottom']:
                        page_idx = p_i
                        break
                if page_idx is None:
                    page_idx = self.current_page_idx
            p_info = self.page_positions.get(page_idx)
            if not p_info:
                return

            page_top = p_info['top']
            page_left = p_info.get('left', 0.0)
            page_pdf_w = p_info['width'] / self.base_render_dpi
            page_pdf_h = p_info['height'] / self.base_render_dpi

            img = QImage()
            img.loadFromData(image_bytes)
            if img.isNull():
                return

            orig_w = max(1, img.width())
            orig_h = max(1, img.height())
            aspect = orig_h / orig_w

            if default_w is not None and default_h is not None:
                pdf_w = min(default_w, page_pdf_w)
                pdf_h = min(default_h, page_pdf_h)
            else:
                max_pdf_w = min(260.0, max(20.0, page_pdf_w - 40.0))
                pdf_w = min(max_pdf_w, orig_w / 2.0)
                pdf_h = pdf_w * aspect
                if pdf_h > page_pdf_h - 40.0:
                    pdf_h = max(20.0, page_pdf_h - 40.0)
                    pdf_w = pdf_h / aspect

            pdf_w = max(10.0, min(pdf_w, page_pdf_w))
            pdf_h = max(10.0, min(pdf_h, page_pdf_h))

            if pos is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                if p_info['top'] <= center_y <= p_info['bottom']:
                    pdf_y = (center_y - page_top) / self.base_render_dpi - pdf_h / 2.0
                else:
                    pdf_y = 60.0
                pdf_x = (page_pdf_w - pdf_w) / 2.0
            else:
                pdf_x = (pos.x() - page_left) / self.base_render_dpi
                pdf_y = (pos.y() - page_top) / self.base_render_dpi

            pdf_x = max(0.0, min(pdf_x, max(0.0, page_pdf_w - pdf_w)))
            pdf_y = max(0.0, min(pdf_y, max(0.0, page_pdf_h - pdf_h)))

            item_data = {
                "type": "image",
                "page": page_idx,
                "x": pdf_x,
                "y": pdf_y,
                "w": pdf_w,
                "h": pdf_h,
                "init_pdf_w": pdf_w,
                "init_pdf_h": pdf_h,
                "orig_w": orig_w,
                "orig_h": orig_h,
                "keep_aspect": keep_aspect,
                "image_bytes": image_bytes,
                "title": title
            }

            self.drawings.append(item_data)
            self.render_image_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)

            it = item_data.get("item_ref")
            if it:
                it.setSelected(True)
            if hasattr(self.main_window, 'set_tool_state'):
                self.main_window.set_tool_state('select')
        except Exception as e:
            import traceback
            traceback.print_exc()

    def add_emoji(self, emoji_str: str, page_idx: Optional[int] = None, pos: Optional[QPointF] = None):
        """Belgeye yüksek çözünürlüklü emoji çıkartması ekler."""
        if not emoji_str:
            return
        pix = QPixmap(140, 140)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = QFont("Segoe UI Emoji", 76)
        p.setFont(font)
        p.drawText(QRectF(0, 0, 140, 140), Qt.AlignmentFlag.AlignCenter, emoji_str)
        p.end()

        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        self.add_image_media(bytes(buf.data()), title=f"Emoji {emoji_str}", page_idx=page_idx, pos=pos, default_w=50.0, default_h=50.0)

    def add_audio(self, audio_bytes: bytes, title: str = "Ses Notu", duration_sec: float = 0.0,
                  format: str = "wav", page_idx: Optional[int] = None, pos: Optional[QPointF] = None):
        """Belgeye etkileşimli ses kayıt kartı ekler."""
        if self.doc is None or not audio_bytes:
            return
        try:
            if page_idx is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                for p_i, p_b in self.page_positions.items():
                    if p_b['top'] <= center_y <= p_b['bottom']:
                        page_idx = p_i
                        break
                if page_idx is None:
                    page_idx = self.current_page_idx
            p_info = self.page_positions.get(page_idx)
            if not p_info:
                return

            page_top = p_info['top']
            page_left = p_info.get('left', 0.0)
            page_pdf_w = p_info['width'] / self.base_render_dpi
            page_pdf_h = p_info['height'] / self.base_render_dpi
            card_pdf_w = min(180.0, page_pdf_w)
            card_pdf_h = min(48.0, page_pdf_h)

            if pos is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                if p_info['top'] <= center_y <= p_info['bottom']:
                    pdf_y = (center_y - page_top) / self.base_render_dpi - card_pdf_h / 2.0
                else:
                    pdf_y = 60.0
                pdf_x = (page_pdf_w - card_pdf_w) / 2.0
            else:
                pdf_x = (pos.x() - page_left) / self.base_render_dpi
                pdf_y = (pos.y() - page_top) / self.base_render_dpi

            pdf_x = max(0.0, min(pdf_x, max(0.0, page_pdf_w - card_pdf_w)))
            pdf_y = max(0.0, min(pdf_y, max(0.0, page_pdf_h - card_pdf_h)))

            item_data = {
                "type": "audio",
                "page": page_idx,
                "x": pdf_x,
                "y": pdf_y,
                "w": card_pdf_w,
                "h": card_pdf_h,
                "audio_bytes": audio_bytes,
                "title": title,
                "duration_sec": duration_sec,
                "format": format
            }

            self.drawings.append(item_data)
            self.render_audio_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)

            it = item_data.get("item_ref")
            if it:
                it.setSelected(True)
            if hasattr(self.main_window, 'set_tool_state'):
                self.main_window.set_tool_state('select')
        except Exception as e:
            import traceback
            traceback.print_exc()

    def add_video(self, video_url_or_path: str, thumbnail_bytes: Optional[bytes] = None,
                  title: str = "Video", page_idx: Optional[int] = None, pos: Optional[QPointF] = None):
        """Belgeye etkileşimli video önizleme kartı ekler."""
        if self.doc is None or not video_url_or_path:
            return
        try:
            if page_idx is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                for p_i, p_b in self.page_positions.items():
                    if p_b['top'] <= center_y <= p_b['bottom']:
                        page_idx = p_i
                        break
                if page_idx is None:
                    page_idx = self.current_page_idx
            p_info = self.page_positions.get(page_idx)
            if not p_info:
                return

            page_top = p_info['top']
            page_left = p_info.get('left', 0.0)
            page_pdf_w = p_info['width'] / self.base_render_dpi
            page_pdf_h = p_info['height'] / self.base_render_dpi
            video_pdf_w = min(200.0, page_pdf_w)
            video_pdf_h = min(120.0, page_pdf_h)

            if pos is None:
                center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
                if p_info['top'] <= center_y <= p_info['bottom']:
                    pdf_y = (center_y - page_top) / self.base_render_dpi - video_pdf_h / 2.0
                else:
                    pdf_y = 60.0
                pdf_x = (page_pdf_w - video_pdf_w) / 2.0
            else:
                pdf_x = (pos.x() - page_left) / self.base_render_dpi
                pdf_y = (pos.y() - page_top) / self.base_render_dpi

            pdf_x = max(0.0, min(pdf_x, max(0.0, page_pdf_w - video_pdf_w)))
            pdf_y = max(0.0, min(pdf_y, max(0.0, page_pdf_h - video_pdf_h)))

            item_data = {
                "type": "video",
                "page": page_idx,
                "x": pdf_x,
                "y": pdf_y,
                "w": video_pdf_w,
                "h": video_pdf_h,
                "video_url": video_url_or_path,
                "thumbnail_bytes": thumbnail_bytes,
                "title": title
            }

            self.drawings.append(item_data)
            self.render_video_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)

            it = item_data.get("item_ref")
            if it:
                it.setSelected(True)
            if hasattr(self.main_window, 'set_tool_state'):
                self.main_window.set_tool_state('select')
        except Exception as e:
            import traceback
            traceback.print_exc()

    def add_signature(self, image: QImage, page_idx: Optional[int] = None, pos: Optional[QPointF] = None):
        """Belgeye imza ekler."""
        if self.doc is None or image is None or image.isNull():
            return
        try:
            if page_idx is None:
                page_idx = self.current_page_idx
            p_info = self.page_positions.get(page_idx)
            if not p_info:
                return

            page_top = p_info['top']
            page_left = p_info.get('left', 0.0)
            page_pdf_w = p_info['width'] / self.base_render_dpi
            page_pdf_h = p_info['height'] / self.base_render_dpi

            max_pdf_w = min(160.0, max(20.0, page_pdf_w - 40.0))
            orig_w = max(1, image.width())
            orig_h = max(1, image.height())
            aspect = orig_h / orig_w
            pdf_w = min(max_pdf_w, orig_w / 2.0)
            pdf_h = pdf_w * aspect
            if pdf_h > page_pdf_h - 40.0:
                pdf_h = max(20.0, page_pdf_h - 40.0)
                pdf_w = pdf_h / aspect

            pdf_w = max(10.0, min(pdf_w, page_pdf_w))
            pdf_h = max(10.0, min(pdf_h, page_pdf_h))

            if pos is None:
                pdf_x = page_pdf_w - pdf_w - 40.0
                pdf_y = page_pdf_h - pdf_h - 60.0
            else:
                pdf_x = (pos.x() - page_left) / self.base_render_dpi
                pdf_y = (pos.y() - page_top) / self.base_render_dpi

            pdf_x = max(0.0, min(pdf_x, max(0.0, page_pdf_w - pdf_w)))
            pdf_y = max(0.0, min(pdf_y, max(0.0, page_pdf_h - pdf_h)))

            from PyQt6.QtCore import QBuffer, QIODevice
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buf, "PNG")
            image_bytes = bytes(buf.data())

            item_data = {
                "type": "image",
                "page": page_idx,
                "x": pdf_x,
                "y": pdf_y,
                "w": pdf_w,
                "h": pdf_h,
                "image_bytes": image_bytes
            }

            self.drawings.append(item_data)
            self.render_image_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)
        except Exception as e:
            import traceback
            traceback.print_exc()

    # --- Sayfa Yönetimi ---
    @property
    def current_page(self) -> int:
        return getattr(self, 'current_page_idx', 0)

    @current_page.setter
    def current_page(self, page_idx: int):
        self.current_page_idx = page_idx

    def record_nav_position(self):
        if getattr(self, '_nav_recording_disabled', False) or self.doc is None:
            return
        pos = (self.current_page_idx, self.view.verticalScrollBar().value())
        if self.nav_history and 0 <= self.nav_history_idx < len(self.nav_history):
            last = self.nav_history[self.nav_history_idx]
            if last[0] == pos[0] and abs(last[1] - pos[1]) < 40:
                return
        self.nav_history = self.nav_history[:self.nav_history_idx + 1]
        self.nav_history.append(pos)
        if len(self.nav_history) > 60:
            self.nav_history.pop(0)
        self.nav_history_idx = len(self.nav_history) - 1

    def nav_back(self):
        if self.nav_history_idx > 0:
            self._nav_recording_disabled = True
            try:
                self.nav_history_idx -= 1
                page, scroll_y = self.nav_history[self.nav_history_idx]
                self.go_to_page(page)
                self.view.verticalScrollBar().setValue(scroll_y)
            finally:
                self._nav_recording_disabled = False

    def nav_forward(self):
        if self.nav_history_idx < len(self.nav_history) - 1:
            self._nav_recording_disabled = True
            try:
                self.nav_history_idx += 1
                page, scroll_y = self.nav_history[self.nav_history_idx]
                self.go_to_page(page)
                self.view.verticalScrollBar().setValue(scroll_y)
            finally:
                self._nav_recording_disabled = False

    def go_to_page(self, page_idx):
        if self.doc is not None and 0 <= page_idx < len(self.doc):
            self.record_nav_position()
            self.current_page_idx = page_idx
            if page_idx in self.page_positions:
                self.view.verticalScrollBar().setValue(int(self.page_positions[page_idx]['top'] * self.zoom_level))
                if self.page_view_mode == "double":
                    self.view.horizontalScrollBar().setValue(int(self.page_positions[page_idx].get('left', 0.0) * self.zoom_level))
            self.record_nav_position()
            self.update_current_page_indicator()

    def scroll_to_page(self, page_idx):
        self.go_to_page(page_idx)

    def get_page_at_pos(self, pos_or_y):
        if hasattr(pos_or_y, 'x') and hasattr(pos_or_y, 'y'):
            x, y = pos_or_y.x(), pos_or_y.y()
            for idx, bounds in self.page_positions.items():
                left = bounds.get('left', 0.0)
                right = bounds.get('right', bounds['width'])
                if left <= x <= right and bounds['top'] <= y <= bounds['bottom']:
                    return idx
            return None
        else:
            scene_y = pos_or_y
            for idx, bounds in self.page_positions.items():
                if bounds['top'] <= scene_y <= bounds['bottom']:
                    return idx
            return None

    def update_current_page_indicator(self):
        if self.doc is None or not self.page_positions: return
        center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
        for idx, bounds in self.page_positions.items():
            if bounds['top'] <= center_y <= bounds['bottom']:
                self.current_page_idx = idx
                break
        if self == self.main_window.get_current_tab_doc():
            if getattr(self.main_window, 'txt_page', None) and not self.main_window.txt_page.hasFocus():
                self.main_window.txt_page.setText(str(self.current_page_idx + 1))
            if getattr(self.main_window, 'thumbnails_dock', None) and hasattr(self.main_window.thumbnails_dock, 'select_page'):
                self.main_window.thumbnails_dock.select_page(self.current_page_idx)

    def rotate_all_pages(self):
        if self.doc is None: return
        for page in self.doc: page.set_rotation((page.rotation + 90) % 360)
        self.render_pages_init()
        self.rerender_visible_pages()
        self.main_window.thumbnails_dock.is_loaded = False
        if self.main_window.thumbnails_dock.isVisible():
            self.main_window.thumbnails_dock.load_thumbnails_lazy()

    def erase_at(self, pos, prev_pos=None):
        radius = max(3.0, self.main_window.eraser_popup.thickness / 2.0)
        page_bg_items = [p['bg_rect'] for p in self.page_positions.values()] + [p['item'] for p in self.page_positions.values()]

        # Hızlı fare hareketlerinde çizgilerin atlanmaması için prev_pos ile pos arasında örnekleme noktaları üret
        sample_points = [pos]
        if prev_pos is not None and (prev_pos.x() != pos.x() or prev_pos.y() != pos.y()):
            move_dist = math.hypot(pos.x() - prev_pos.x(), pos.y() - prev_pos.y())
            step_size = max(3.0, radius * 0.6)
            steps = max(1, int(move_dist / step_size))
            sample_points = [
                QPointF(
                    prev_pos.x() + (pos.x() - prev_pos.x()) * (i / steps),
                    prev_pos.y() + (pos.y() - prev_pos.y()) * (i / steps)
                )
                for i in range(steps + 1)
            ]

        def _dist_pt_to_seg(px, py, ax, ay, bx, by):
            abx = bx - ax
            aby = by - ay
            l2 = abx * abx + aby * aby
            if l2 == 0.0:
                return math.hypot(px - ax, py - ay)
            t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / l2))
            return math.hypot(px - (ax + t * abx), py - (ay + t * aby))

        eraser_mode = getattr(self.main_window.eraser_popup, 'eraser_mode', 'stroke')

        if eraser_mode == "stroke":
            deleted = []

            # 1. Qt Scene Hit Testing
            for s_pt in sample_points:
                erase_rect = QRectF(s_pt.x() - radius, s_pt.y() - radius, radius * 2, radius * 2)
                for it in list(self.scene.items(erase_rect)):
                    if it in page_bg_items:
                        continue
                    # Check parentItem in case item is inside a QGraphicsItemGroup (pencil)
                    target_it = it
                    while target_it.parentItem() is not None:
                        target_it = target_it.parentItem()
                    found = next((d for d in self.drawings if d.get("item_ref") == target_it or d.get("item_ref") == it), None)
                    if found and found not in deleted:
                        # Ekle butonundaki işlevler (tablo, resim/gif, ses dosyası, ses kaydı, video, metin) silgi ile silinemez
                        if found.get("type") in ("table", "image", "audio", "video", "text"):
                            continue
                        ref = found.get("item_ref")
                        if ref and ref.scene() == self.scene:
                            self.scene.removeItem(ref)
                        elif it.scene() == self.scene:
                            self.scene.removeItem(it)
                        deleted.append(found)
                        if found in self.drawings:
                            self.drawings.remove(found)
                    elif found is None and isinstance(it, QGraphicsPathItem):
                        # Medya/tablo nesnelerinin alt çocuk parçalarını koru
                        p_check = it
                        is_protected_child = False
                        while p_check is not None:
                            if any(d.get("item_ref") == p_check and d.get("type") in ("table", "image", "audio", "video", "text") for d in self.drawings):
                                is_protected_child = True
                                break
                            p_check = p_check.parentItem()
                        if is_protected_child:
                            continue

                        # Askıda kalmış veya referansı kopmuş yetim çizgi parçalarını temizle
                        is_sys_item = (
                            it == getattr(self, 'selection_item', None) or
                            it == getattr(self, 'laser_pointer_item', None) or
                            it in getattr(self, 'pointer_trail_items', []) or
                            it in getattr(self, 'selection_highlight_items', [])
                        )
                        if not is_sys_item and it.scene() == self.scene:
                            self.scene.removeItem(it)

            # 2. Geometrik Mesafe ve Kesişim Kontrolü (İnce çizgiler, hızlı fare ve filled_path için %100 silme garantisi)
            for d in list(self.drawings):
                if d in deleted:
                    continue
                if d.get("type") in ("table", "image", "audio", "video", "text"):
                    continue
                p_idx = d.get("page", 0)
                p_info = self.page_positions.get(p_idx)
                if not p_info:
                    continue
                page_top = p_info['top']
                page_left = p_info.get('left', 0.0)

                hit = False
                if d.get("type") in ("polyline", "pencil") and d.get("points"):
                    d_width = d.get("width", 2.0)
                    hit_radius = radius + (d_width / 2.0) + 8.0  # Rahat ve akıcı silme payı
                    pts = [(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + page_top) for rx, ry in d["points"]]
                    for s_pt in sample_points:
                        sx, sy = s_pt.x(), s_pt.y()
                        for i in range(len(pts) - 1):
                            if _dist_pt_to_seg(sx, sy, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) <= hit_radius:
                                hit = True
                                break
                        if hit:
                            break
                        if len(pts) == 1 and math.hypot(sx - pts[0][0], sy - pts[0][1]) <= hit_radius:
                            hit = True
                            break
                        if d.get("arrow_head"):
                            ah = [(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + page_top) for rx, ry in d["arrow_head"]]
                            for i in range(len(ah) - 1):
                                if _dist_pt_to_seg(sx, sy, ah[i][0], ah[i][1], ah[i+1][0], ah[i+1][1]) <= hit_radius:
                                    hit = True
                                    break
                            if hit:
                                break

                elif d.get("type") == "filled_path" and d.get("rel_path"):
                    transform = QTransform()
                    transform.translate(page_left, page_top)
                    transform.scale(self.base_render_dpi, self.base_render_dpi)
                    scene_path = transform.map(d["rel_path"])
                    hit_radius = radius + 6.0
                    for s_pt in sample_points:
                        check_rect = QRectF(s_pt.x() - hit_radius, s_pt.y() - hit_radius, hit_radius * 2, hit_radius * 2)
                        if scene_path.intersects(check_rect) or scene_path.contains(s_pt):
                            hit = True
                            break

                if hit:
                    deleted.append(d)
                    if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                        self.scene.removeItem(d["item_ref"])
                    if d in self.drawings:
                        self.drawings.remove(d)

            if deleted:
                self.push_undo_action({"type": "erase", "deleted_items": deleted})
                page_idx = self.get_page_at_pos(pos)
                self.notify_drawings_changed(page_idx)
                self.scene.update()
                self.view.viewport().update()

        elif eraser_mode == "area":
            new_drawings = []
            erased_any = False
            
            eraser_path = QPainterPath()
            if len(sample_points) == 1:
                eraser_path.addEllipse(sample_points[0], radius, radius)
            else:
                base_path = QPainterPath(sample_points[0])
                for sp in sample_points[1:]:
                    base_path.lineTo(sp)
                stroker = QPainterPathStroker()
                stroker.setWidth(radius * 2.0)
                stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
                stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                eraser_path = stroker.createStroke(base_path)
                
            for record in self.drawings:
                if record["type"] in ("text", "image", "table", "audio", "video"):
                    new_drawings.append(record)
                    continue

                page_idx = record.get("page", 0)
                p_info = self.page_positions.get(page_idx)
                if not p_info:
                    new_drawings.append(record)
                    continue
                top_y = p_info['top']
                page_left = p_info.get('left', 0.0)

                item = record.get("item_ref")
                if not item:
                    new_drawings.append(record)
                    continue

                # Genişletilmiş tolerans ile kesişim kontrolü
                if not item.sceneBoundingRect().adjusted(-6, -6, 6, 6).intersects(eraser_path.boundingRect()):
                    new_drawings.append(record)
                    continue

                st = record.get("line_style", "solid")
                pen = record.get("pen")
                is_dashed = (st in ("dash", "dot", "dashdot")) or bool(
                    pen and (
                        pen.style() in (Qt.PenStyle.DashLine, Qt.PenStyle.DotLine, Qt.PenStyle.DashDotLine)
                        or (pen.dashPattern() and pen.style() != Qt.PenStyle.SolidLine)
                    )
                )
                stroke_width = pen.widthF() if pen else float(record.get("width", 2.0) or 2.0)

                if record["type"] in ("polyline", "pencil"):
                    pts = record.get("points", [])
                    if not pts:
                        new_drawings.append(record)
                        continue
                    path = QPainterPath()
                    sx = pts[0][0] * self.base_render_dpi + page_left
                    sy = pts[0][1] * self.base_render_dpi + top_y
                    path.moveTo(sx, sy)
                    if len(pts) == 1:
                        path.lineTo(sx + 0.1, sy + 0.1)
                    else:
                        for px, py in pts[1:]:
                            path.lineTo(px * self.base_render_dpi + page_left, py * self.base_render_dpi + top_y)
                    
                    if record.get("arrow_head"):
                        ah = [(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + top_y) for rx, ry in record["arrow_head"]]
                        if len(ah) >= 3:
                            path.moveTo(ah[0][0], ah[0][1])
                            path.lineTo(ah[1][0], ah[1][1])
                            path.lineTo(ah[2][0], ah[2][1])

                    stroker = QPainterPathStroker()
                    if pen:
                        stroker.setWidth(pen.widthF())
                        stroker.setCapStyle(pen.capStyle())
                        stroker.setJoinStyle(pen.joinStyle())
                        if st == "dash":
                            stroker.setDashPattern(Qt.PenStyle.DashLine)
                        elif st == "dot":
                            stroker.setDashPattern(Qt.PenStyle.DotLine)
                        elif st == "dashdot":
                            stroker.setDashPattern(Qt.PenStyle.DashDotLine)
                        elif pen.style() != Qt.PenStyle.SolidLine:
                            stroker.setDashPattern(pen.style())
                        elif pen.dashPattern():
                            stroker.setDashPattern(pen.dashPattern())
                    else:
                        stroker.setWidth(stroke_width)
                        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
                        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                        if st == "dash":
                            stroker.setDashPattern(Qt.PenStyle.DashLine)
                        elif st == "dot":
                            stroker.setDashPattern(Qt.PenStyle.DotLine)
                        elif st == "dashdot":
                            stroker.setDashPattern(Qt.PenStyle.DashDotLine)
                        elif st == "calligraphy":
                            stroker.setCapStyle(Qt.PenCapStyle.FlatCap)
                            stroker.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

                    target_path = stroker.createStroke(path)
                elif record["type"] == "filled_path":
                    transform = QTransform()
                    transform.translate(page_left, top_y)
                    transform.scale(self.base_render_dpi, self.base_render_dpi)
                    target_path = transform.map(record["rel_path"])
                else:
                    new_drawings.append(record)
                    continue

                if not target_path.intersects(eraser_path):
                    new_drawings.append(record)
                    continue
                    
                new_path = target_path.subtracted(eraser_path)
                
                if new_path == target_path:
                    new_drawings.append(record)
                    continue
                
                erased_any = True
                if item.scene() == self.scene:
                    self.scene.removeItem(item)
                
                # Mikroskobik piksel kalıntılarını temizle (0.6px altı yok sayılır)
                br = new_path.boundingRect()
                if new_path.isEmpty() or (br.width() < 0.6 and br.height() < 0.6):
                    continue
                
                # new_path içindeki bağlantısız parçaları bağımsız şekillere (component) ayır
                polys = new_path.toSubpathPolygons()
                components = [] 
                if is_dashed:
                    bridge_tol = stroke_width * 1.25 + 1.0
                    dilated_stroker = QPainterPathStroker()
                    dilated_stroker.setWidth(bridge_tol * 2.0)
                    dash_comps = []
                    for poly in polys:
                        p_path = QPainterPath()
                        p_path.addPolygon(poly)
                        p_br = p_path.boundingRect()
                        p_dilated = None
                        intersecting = []
                        for i, comp in enumerate(dash_comps):
                            if not comp['br_expanded'].intersects(p_br):
                                continue
                            if p_dilated is None:
                                p_dilated = dilated_stroker.createStroke(p_path)
                                p_dilated.addPath(p_path)
                            if comp['dilated'].intersects(p_path) or p_dilated.intersects(comp['path']):
                                intersecting.append(i)
                        if not intersecting:
                            if p_dilated is None:
                                p_dilated = dilated_stroker.createStroke(p_path)
                                p_dilated.addPath(p_path)
                            dash_comps.append({
                                'polys': [poly],
                                'path': p_path,
                                'dilated': p_dilated,
                                'br': p_br,
                                'br_expanded': p_br.adjusted(-bridge_tol, -bridge_tol, bridge_tol, bridge_tol)
                            })
                        else:
                            if p_dilated is None:
                                p_dilated = dilated_stroker.createStroke(p_path)
                                p_dilated.addPath(p_path)
                            base_idx = intersecting[0]
                            dash_comps[base_idx]['polys'].append(poly)
                            dash_comps[base_idx]['path'].addPath(p_path)
                            dash_comps[base_idx]['dilated'].addPath(p_dilated)
                            dash_comps[base_idx]['br'] = dash_comps[base_idx]['br'].united(p_br)
                            dash_comps[base_idx]['br_expanded'] = dash_comps[base_idx]['br'].adjusted(-bridge_tol, -bridge_tol, bridge_tol, bridge_tol)
                            for idx in reversed(intersecting[1:]):
                                dash_comps[base_idx]['polys'].extend(dash_comps[idx]['polys'])
                                dash_comps[base_idx]['path'].addPath(dash_comps[idx]['path'])
                                dash_comps[base_idx]['dilated'].addPath(dash_comps[idx]['dilated'])
                                dash_comps[base_idx]['br'] = dash_comps[base_idx]['br'].united(dash_comps[idx]['br'])
                                dash_comps[base_idx]['br_expanded'] = dash_comps[base_idx]['br'].adjusted(-bridge_tol, -bridge_tol, bridge_tol, bridge_tol)
                                dash_comps.pop(idx)
                    components = [c['polys'] for c in dash_comps]
                else:
                    for poly in polys:
                        p = QPainterPath()
                        p.addPolygon(poly)
                        intersecting_indices = []
                        for i, comp_polys in enumerate(components):
                            comp_path = QPainterPath()
                            for cp in comp_polys:
                                comp_path.addPolygon(cp)
                            if comp_path.intersects(p) or comp_path.contains(p) or p.contains(comp_path):
                                intersecting_indices.append(i)
                        if not intersecting_indices:
                            components.append([poly])
                        else:
                            base_idx = intersecting_indices[0]
                            components[base_idx].append(poly)
                            for idx in reversed(intersecting_indices[1:]):
                                components[base_idx].extend(components[idx])
                                components.pop(idx)
                
                inv_transform = QTransform()
                inv_transform.translate(page_left, top_y)
                inv_transform.scale(self.base_render_dpi, self.base_render_dpi)
                inv_transform, invertible = inv_transform.inverted()
                if not invertible:
                    continue
                    
                col = record.get("color", (0, 0, 0))
                if isinstance(col, QColor):
                    fill_col = QColor(col)
                    fill_col.setAlphaF(float(record.get("alpha", 1.0)))
                elif isinstance(col, (tuple, list)) and len(col) >= 3:
                    fill_col = QColor.fromRgbF(float(col[0]), float(col[1]), float(col[2]), float(record.get("alpha", 1.0)))
                else:
                    fill_col = QColor(0, 0, 0)
                
                is_pencil = (record.get("type") == "pencil" or st == "pencil")

                for comp_polys in components:
                    comp_path = QPainterPath()
                    comp_path.setFillRule(Qt.FillRule.WindingFill)
                    for cp in comp_polys:
                        comp_path.addPolygon(cp)
                        
                    comp_br = comp_path.boundingRect()
                    if comp_path.isEmpty() or (comp_br.width() < 0.6 and comp_br.height() < 0.6):
                        continue
                        
                    rel_path = inv_transform.map(comp_path)
                    if is_pencil:
                        fill_tex = get_graphite_fill_texture(fill_col, float(record.get("alpha", 1.0)))
                        new_item = self.scene.addPath(comp_path, QPen(Qt.PenStyle.NoPen), QBrush(fill_tex))
                    else:
                        new_item = self.scene.addPath(comp_path, QPen(Qt.PenStyle.NoPen), QBrush(fill_col))
                    
                    new_rec = record.copy()
                    new_rec.pop("source_annot", None)
                    new_rec.pop("points", None)
                    new_rec.pop("arrow_head", None)
                    if is_pencil:
                        new_rec["line_style"] = "pencil"
                    elif not is_dashed:
                        new_rec.pop("line_style", None)
                    else:
                        new_rec["line_style"] = st
                    new_rec.update({
                        "id": uuid.uuid4().hex[:12],
                        "type": "filled_path",
                        "rel_path": rel_path,
                        "item_ref": new_item,
                        "color": col,
                        "width": stroke_width
                    })
                    new_drawings.append(new_rec)

            if erased_any:
                self.area_erase_had_changes = True
                self.drawings = new_drawings
                page_idx = self.get_page_at_pos(pos)
                self.notify_drawings_changed(page_idx)
                self.scene.update()
                self.view.viewport().update()

    # --- MODÜLER FARE YÖNETİMİ ---
    def eventFilter(self, source, event):
        if not hasattr(self, 'doc') or self.doc is None:
            return super().eventFilter(source, event)

        if source in (self.view.viewport(), self.view):
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
                    if pdf_urls:
                        self.main_window.handle_dropped_urls(pdf_urls)
                        event.acceptProposedAction()
                        return True

        if source != self.view.viewport() or self.doc is None:
            return super().eventFilter(source, event)

        tool = self.main_window.current_tool

        # Zoom & Tool adjustments via mouse wheel
        if event.type() == event.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                delta = event.angleDelta().y() or event.angleDelta().x()
                if delta != 0:
                    step = 2 if delta > 0 else -2
                    g_pos = self.view.viewport().mapToGlobal(event.position().toPoint())
                    if tool == 'pen':
                        p = self.main_window.pen_popup
                        p.set_thickness(p.thickness + (1 if delta > 0 else -1))
                        self.main_window.floating_hud.show_preview(g_pos, p.color, p.thickness, False, "stroke", getattr(p, 'line_style', 'solid'), getattr(p, 'current_pen_type', 'solid'))
                    elif tool == 'highlighter':
                        p = self.main_window.hl_popup
                        p.set_thickness(p.thickness + step)
                        self.main_window.floating_hud.show_preview(g_pos, p.color, p.thickness)
                    elif tool == 'eraser':
                        p = self.main_window.eraser_popup
                        p.set_thickness(p.thickness + step)
                        self.main_window.floating_hud.show_preview(g_pos, QColor(), p.thickness, True, p.eraser_mode)
                    elif tool == 'pointer':
                        p = self.main_window.pointer_popup
                        p.set_thickness(p.thickness + (1 if delta > 0 else -1))
                        self.main_window.floating_hud.show_preview(g_pos, p.color, p.thickness)
                    self.main_window.update_viewport_cursor()
                return True
            elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
                return True

        if tool == 'direct_edit' or getattr(self, 'direct_edit_mode', False):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    if self.direct_edit_editor:
                        self.close_inplace_editor()
                        return True
                    else:
                        self.exit_direct_text_edit()
                        return True

            elif event.type() == QEvent.Type.MouseMove and not (event.buttons() & Qt.MouseButton.LeftButton):
                pos = self.view.mapToScene(event.pos())
                self._handle_direct_edit_mouse_move(pos)
                return True

            elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = self.view.mapToScene(event.pos())
                return self._handle_direct_edit_mouse_press(pos, event.pos())

            return super().eventFilter(source, event)

        if tool == 'select':
            # 1. Klavye Kısayolları (Ctrl+C ile panoya kopyalama)
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    if getattr(self, 'selected_text', ''):
                        self.copy_selected_text()
                        return True

            # 2. Fare Gezinme (Hover): Köprüleri (Hyperlinks) algıla ve I-Beam/El imleci göster
            elif event.type() == QEvent.Type.MouseMove and not (event.buttons() & Qt.MouseButton.LeftButton):
                pos = self.view.mapToScene(event.pos())
                self._handle_select_hover(pos)

            # 3. Fare Tıklama (Press): Köprü tıklaması veya metin seçimi başlatma
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = self.view.mapToScene(event.pos())
                    # Önce tıklanabilir bağlantı var mı kontrol et
                    if self._handle_link_click(pos):
                        return True
                    # Çizim veya medya nesnesi tıklandıysa standart seçime bırak
                    items = self.scene.items(pos)
                    from src.document.media_items import (PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem)
                    if any(isinstance(it, (BookmarkRibbonItem, PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem)) for it in items):
                        self.clear_text_selection()
                        return super().eventFilter(source, event)
                    # Metin seçimini başlat
                    self._start_text_selection(pos)
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    if getattr(self, 'selected_text', ''):
                        self._show_text_context_menu(self.view.viewport().mapToGlobal(event.pos()))
                        return True

            # 4. Fare Sürükleme (Move with Left Button): Metin seçimi güncelleme
            elif event.type() == QEvent.Type.MouseMove and (event.buttons() & Qt.MouseButton.LeftButton):
                if getattr(self, 'is_selecting_text', False):
                    pos = self.view.mapToScene(event.pos())
                    self._update_text_selection(pos)
                    return True

            # 5. Fare Bırakma (Release): Metin seçimini tamamla ve mini çubuğu göster
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if getattr(self, 'is_selecting_text', False):
                    pos = self.view.mapToScene(event.pos())
                    self._finish_text_selection(pos, event.pos())
                    return True

            return super().eventFilter(source, event)

        if tool == 'pointer':
            if event.type() == QEvent.Type.MouseMove:
                pos = self.view.mapToScene(event.pos())
                p_idx = self.get_page_at_pos(pos)
                if p_idx is None:
                    self.hide_laser_pointer()
                    self.pointer_last_pos = None
                    return False

                self.update_laser_pointer(pos)
                if (event.buttons() & Qt.MouseButton.LeftButton) and self.pointer_last_pos is not None:
                    popup = getattr(self.main_window, 'pointer_popup', None)
                    thick = popup.thickness if popup else 3
                    if popup and popup.mode == "rainbow":
                        col = QColor.fromHsvF(self.pointer_hue, 1.0, 1.0, 0.9)
                        self.pointer_hue = (self.pointer_hue + 0.04) % 1.0
                    else:
                        base_col = popup.color if popup else QColor("#ff1744")
                        col = QColor(base_col.red(), base_col.green(), base_col.blue(), 230)

                    pen = QPen(col, thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                    line_item = self.scene.addLine(QLineF(self.pointer_last_pos, pos), pen)
                    line_item.setZValue(998)
                    self.pointer_trail_items.append(line_item)
                    self.pointer_last_pos = pos
                    return True
                return False
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._cancel_pointer_fadeout()
                    pos = self.view.mapToScene(event.pos())
                    p_idx = self.get_page_at_pos(pos)
                    if p_idx is not None:
                        self.pointer_last_pos = pos
                        self.update_laser_pointer(pos)
                    else:
                        self.pointer_last_pos = None
                        self.hide_laser_pointer()
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    g_pos = self.view.viewport().mapToGlobal(event.pos())
                    if self.show_tool_quick_menu(g_pos, 'pointer'):
                        return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.pointer_last_pos = None
                    self._schedule_pointer_fadeout()
                return True
            elif event.type() == QEvent.Type.Leave:
                self.hide_laser_pointer()
                self.pointer_last_pos = None
                if getattr(self, '_last_hovered_ribbon', None):
                    self._last_hovered_ribbon.set_hovered(False)
                    self._last_hovered_ribbon = None
                return False

        # Fare olaylarını alt fonksiyonlara yönlendir (Daha temiz kod)
        if event.type() == event.Type.MouseButtonPress:
            if hasattr(self.main_window, 'handle_mouse_shortcut') and self.main_window.handle_mouse_shortcut(event):
                event.accept()
                return True
            if event.button() == Qt.MouseButton.LeftButton:
                pos = self.view.mapToScene(event.pos())
                if any(isinstance(it, BookmarkRibbonItem) for it in self.scene.items(pos)):
                    return super().eventFilter(source, event)
                return self._handle_mouse_press(event, tool)
            elif event.button() == Qt.MouseButton.RightButton:
                pos = self.view.mapToScene(event.pos())
                for it in self.scene.items(pos):
                    if isinstance(it, BookmarkRibbonItem):
                        g_pos = self.view.viewport().mapToGlobal(event.pos())
                        it.show_context_menu(g_pos)
                        return True
                g_pos = self.view.viewport().mapToGlobal(event.pos())
                if self.show_tool_quick_menu(g_pos, tool):
                    return True
        elif event.type() == event.Type.MouseMove:
            if event.buttons() & Qt.MouseButton.LeftButton:
                if self.current_path_item is not None:
                    return self._handle_mouse_move(event, tool)
                pos = self.view.mapToScene(event.pos())
                if self.bookmark_ribbon_items and any(isinstance(it, BookmarkRibbonItem) for it in self.scene.items(pos)):
                    return super().eventFilter(source, event)
                return self._handle_mouse_move(event, tool)
            else:
                self._handle_mouse_hover(event, tool)
        elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self.current_path_item is not None:
                return self._handle_mouse_release(event, tool)
            pos = self.view.mapToScene(event.pos())
            if self.bookmark_ribbon_items and any(isinstance(it, BookmarkRibbonItem) for it in self.scene.items(pos)):
                return super().eventFilter(source, event)
            return self._handle_mouse_release(event, tool)

        return super().eventFilter(source, event)

    # --- V3 METİN SEÇİMİ, KÖPRÜ VE ETKİLEŞİMLİ FORM YÖNETİMİ ---
    def _handle_select_hover(self, scene_pos: QPointF):
        if not self.doc:
            return
        p_idx = self.get_page_at_pos(scene_pos)
        if p_idx is None or p_idx >= len(self.doc):
            self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            self.view.setToolTip("")
            return

        pinfo = self.page_positions.get(p_idx, {})
        scale = self.base_render_dpi
        pleft, ptop = pinfo.get('left', 0.0), pinfo.get('top', 0.0)
        pdf_pt = fitz.Point((scene_pos.x() - pleft) / scale, (scene_pos.y() - ptop) / scale)

        # 1. Köprü Kontrolü (Hyperlinks)
        try:
            page = self.doc[p_idx]
            links = page.get_links()
            for l in links:
                if l['from'].contains(pdf_pt):
                    self.view.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                    tip = l.get('uri') or f"Sayfa {l.get('page', 0) + 1}'e git"
                    self.view.setToolTip(tip)
                    return
        except Exception:
            pass

        # 2. Metin İmleci (I-Beam Cursor)
        self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self.view.setToolTip("")

    def _handle_link_click(self, scene_pos: QPointF) -> bool:
        if not self.doc:
            return False
        p_idx = self.get_page_at_pos(scene_pos)
        if p_idx is None or p_idx >= len(self.doc):
            return False

        pinfo = self.page_positions.get(p_idx, {})
        scale = self.base_render_dpi
        pleft, ptop = pinfo.get('left', 0.0), pinfo.get('top', 0.0)
        pdf_pt = fitz.Point((scene_pos.x() - pleft) / scale, (scene_pos.y() - ptop) / scale)

        try:
            page = self.doc[p_idx]
            for l in page.get_links():
                if l['from'].contains(pdf_pt):
                    if l.get('uri'):
                        QDesktopServices.openUrl(QUrl(l['uri']))
                        return True
                    elif l.get('page') is not None:
                        self.record_nav_position()
                        self.go_to_page(l['page'])
                        return True
        except Exception:
            pass
        return False

    def _start_text_selection(self, scene_pos: QPointF):
        self.clear_text_selection()
        p_idx = self.get_page_at_pos(scene_pos)
        if p_idx is not None and self.doc and 0 <= p_idx < len(self.doc):
            self.is_selecting_text = True
            self.text_selection_start = scene_pos
            self.text_selection_page_idx = p_idx

    def _update_text_selection(self, scene_pos: QPointF):
        if not getattr(self, 'is_selecting_text', False) or self.text_selection_page_idx is None:
            return
        p_idx = self.text_selection_page_idx
        if not self.doc or p_idx >= len(self.doc):
            return

        pinfo = self.page_positions.get(p_idx, {})
        scale = self.base_render_dpi
        pleft, ptop = pinfo.get('left', 0.0), pinfo.get('top', 0.0)

        pt_start = fitz.Point((self.text_selection_start.x() - pleft) / scale, (self.text_selection_start.y() - ptop) / scale)
        pt_end = fitz.Point((scene_pos.x() - pleft) / scale, (scene_pos.y() - ptop) / scale)

        try:
            words = self.doc[p_idx].get_text("words")
        except Exception:
            words = []
        if not words:
            return

        def word_dist(pt, w):
            cx = (w[0] + w[2]) / 2.0
            cy = (w[1] + w[3]) / 2.0
            return (pt.x - cx)**2 + (pt.y - cy)**2

        i1 = min(range(len(words)), key=lambda i: word_dist(pt_start, words[i]))
        i2 = min(range(len(words)), key=lambda i: word_dist(pt_end, words[i]))
        start_i, end_i = min(i1, i2), max(i1, i2)
        sel_words = words[start_i:end_i + 1]

        for it in self.selected_text_items:
            if it.scene() == self.scene:
                self.scene.removeItem(it)
        self.selected_text_items.clear()
        self.selected_text_rects.clear()

        lines_dict = {}
        for w in sel_words:
            lines_dict.setdefault((w[5], w[6]), []).append(w)

        lines_text = []
        for (b_no, l_no), line_w in lines_dict.items():
            lines_text.append(" ".join(w[4] for w in line_w))
            lx0 = min(w[0] for w in line_w)
            ly0 = min(w[1] for w in line_w)
            lx1 = max(w[2] for w in line_w)
            ly1 = max(w[3] for w in line_w)
            pdf_rect = fitz.Rect(lx0, ly0, lx1, ly1)
            scene_rect = QRectF(lx0 * scale + pleft, ly0 * scale + ptop, (lx1 - lx0) * scale, (ly1 - ly0) * scale)

            rect_item = self.scene.addRect(
                scene_rect,
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(2, 132, 199, 90))
            )
            rect_item.setZValue(6)
            self.selected_text_items.append(rect_item)
            self.selected_text_rects.append((p_idx, scene_rect, pdf_rect))

        self.selected_text = "\n".join(lines_text)

    def _finish_text_selection(self, scene_pos: QPointF, viewport_pos: QPoint):
        self.is_selecting_text = False
        if getattr(self, 'selected_text', '').strip():
            if not hasattr(self, 'text_selection_hud') or self.text_selection_hud is None:
                from src.ui.popups import PDFTextSelectionHUD
                self.text_selection_hud = PDFTextSelectionHUD(self.view.viewport(), self)
            self.text_selection_hud.show_at_pos(viewport_pos)
        else:
            self.clear_text_selection()

    def _show_text_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)

        act_copy = menu.addAction(ModernIconFactory.icon_cursor(), LanguageManager.tr("copy") + " (Ctrl+C)")
        act_hl = menu.addAction(ModernIconFactory.icon_highlighter(), LanguageManager.tr("text_markup_highlight"))
        act_ul = menu.addAction(LanguageManager.tr("text_markup_underline"))
        act_so = menu.addAction(LanguageManager.tr("text_markup_strikeout"))
        menu.addSeparator()
        act_search = menu.addAction(ModernIconFactory.icon_search(), LanguageManager.tr("text_search_google"))
        act_trans = menu.addAction(LanguageManager.tr("text_translate_google"))

        chosen = menu.exec(global_pos)
        if chosen == act_copy:
            self.copy_selected_text()
        elif chosen == act_hl:
            self.highlight_selected_text()
        elif chosen == act_ul:
            self.underline_selected_text()
        elif chosen == act_so:
            self.strikeout_selected_text()
        elif chosen == act_search:
            self.search_selected_text()
        elif chosen == act_trans:
            self.translate_selected_text()

    def clear_text_selection(self):
        for it in getattr(self, 'selected_text_items', []):
            if it.scene() == self.scene:
                self.scene.removeItem(it)
        self.selected_text_items = []
        self.selected_text_rects = []
        self.selected_text = ""
        if getattr(self, 'text_selection_hud', None):
            self.text_selection_hud.hide()

    def copy_selected_text(self):
        if self.selected_text:
            QApplication.clipboard().setText(self.selected_text)
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(LanguageManager.tr("text_copied_to_clipboard"), 3000)
            elif hasattr(self.main_window, 'show_osd_message'):
                self.main_window.show_osd_message(LanguageManager.tr("text_copied_to_clipboard"))

    def highlight_selected_text(self, color=(1.0, 0.9, 0.2)):
        if not self.selected_text_rects or not self.doc:
            return
        pages = {}
        for p_idx, s_rect, pdf_rect in self.selected_text_rects:
            pages.setdefault(p_idx, []).append(pdf_rect)
        for p_idx, rects in pages.items():
            try:
                page = self.doc[p_idx]
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=color)
                annot.update()
            except Exception:
                pass
        self.set_modified(True)
        self.clear_text_selection()
        self.rerender_visible_pages(force=True)
        if hasattr(self.main_window, 'dock_thumbs') and self.main_window.dock_thumbs:
            self.main_window.dock_thumbs.load_comments()
        elif hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_comments()

    def underline_selected_text(self, color=(0.1, 0.5, 0.9)):
        if not self.selected_text_rects or not self.doc:
            return
        pages = {}
        for p_idx, s_rect, pdf_rect in self.selected_text_rects:
            pages.setdefault(p_idx, []).append(pdf_rect)
        for p_idx, rects in pages.items():
            try:
                page = self.doc[p_idx]
                annot = page.add_underline_annot(rects)
                annot.set_colors(stroke=color)
                annot.update()
            except Exception:
                pass
        self.set_modified(True)
        self.clear_text_selection()
        self.rerender_visible_pages(force=True)
        if hasattr(self.main_window, 'dock_thumbs') and self.main_window.dock_thumbs:
            self.main_window.dock_thumbs.load_comments()
        elif hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_comments()

    def strikeout_selected_text(self, color=(0.9, 0.2, 0.2)):
        if not self.selected_text_rects or not self.doc:
            return
        pages = {}
        for p_idx, s_rect, pdf_rect in self.selected_text_rects:
            pages.setdefault(p_idx, []).append(pdf_rect)
        for p_idx, rects in pages.items():
            try:
                page = self.doc[p_idx]
                annot = page.add_strikeout_annot(rects)
                annot.set_colors(stroke=color)
                annot.update()
            except Exception:
                pass
        self.set_modified(True)
        self.clear_text_selection()
        self.rerender_visible_pages(force=True)
        if hasattr(self.main_window, 'dock_thumbs') and self.main_window.dock_thumbs:
            self.main_window.dock_thumbs.load_comments()
        elif hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_comments()

    def search_selected_text(self):
        if not self.selected_text:
            return
        q = urllib.parse.quote(self.selected_text.strip())
        QDesktopServices.openUrl(QUrl(f"https://www.google.com/search?q={q}"))

    def translate_selected_text(self):
        if not self.selected_text:
            return
        q = urllib.parse.quote(self.selected_text.strip())
        QDesktopServices.openUrl(QUrl(f"https://translate.google.com/?sl=auto&tl=tr&text={q}"))
    def _load_interactive_form_widgets(self):
        for p in getattr(self, 'interactive_form_proxies', []):
            try:
                if p.scene() == self.scene:
                    self.scene.removeItem(p)
            except Exception:
                pass
        self.interactive_form_proxies = []
        self._interactive_field_widgets = []

        if not self.doc:
            return

        for p_idx in range(len(self.doc)):
            page = self.doc[p_idx]
            pinfo = self.page_positions.get(p_idx)
            if not pinfo:
                continue
            pleft = pinfo.get('left', 0.0)
            ptop = pinfo.get('top', 0.0)
            scale = self.base_render_dpi

            try:
                for w in page.widgets():
                    r = w.rect
                    sx = r.x0 * scale + pleft
                    sy = r.y0 * scale + ptop
                    sw = max(24.0, (r.x1 - r.x0) * scale)
                    sh = max(16.0, (r.y1 - r.y0) * scale)

                    if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                        is_multi = sh > 36.0 or bool(getattr(w, 'is_multiline', False))
                        if is_multi:
                            txt_edit = QTextEdit()
                            txt_edit.setPlainText(str(w.field_value or ""))
                            txt_edit.setStyleSheet("""
                                QTextEdit {
                                    background-color: rgba(255, 255, 255, 0.95);
                                    color: #111827;
                                    border: 1.5px solid #0284c7;
                                    border-radius: 3px;
                                    padding: 2px 4px;
                                    font-size: 11px;
                                }
                                QTextEdit:focus {
                                    border: 2px solid #38bdf8;
                                    background-color: #ffffff;
                                }
                            """)
                            txt_edit.setGeometry(0, 0, int(sw), int(sh))
                            def make_text_updater(p_num, f_name, editor):
                                return lambda: self._on_form_field_changed(p_num, f_name, editor.toPlainText())
                            txt_edit.textChanged.connect(make_text_updater(p_idx, w.field_name, txt_edit))
                            proxy = self.scene.addWidget(txt_edit)
                            proxy.setPos(sx, sy)
                            proxy.setZValue(4)
                            self.interactive_form_proxies.append(proxy)
                            self._interactive_field_widgets.append({
                                'page_idx': p_idx,
                                'field_name': w.field_name,
                                'widget': txt_edit,
                                'type': 'multiline'
                            })
                        else:
                            txt_edit = QLineEdit(str(w.field_value or ""))
                            txt_edit.setStyleSheet("""
                                QLineEdit {
                                    background-color: rgba(255, 255, 255, 0.95);
                                    color: #111827;
                                    border: 1.5px solid #0284c7;
                                    border-radius: 3px;
                                    padding: 2px 4px;
                                    font-size: 11px;
                                }
                                QLineEdit:focus {
                                    border: 2px solid #38bdf8;
                                    background-color: #ffffff;
                                }
                            """)
                            txt_edit.setGeometry(0, 0, int(sw), int(sh))
                            def make_line_updater(p_num, f_name):
                                return lambda val: self._on_form_field_changed(p_num, f_name, val)
                            txt_edit.textChanged.connect(make_line_updater(p_idx, w.field_name))
                            proxy = self.scene.addWidget(txt_edit)
                            proxy.setPos(sx, sy)
                            proxy.setZValue(4)
                            self.interactive_form_proxies.append(proxy)
                            self._interactive_field_widgets.append({
                                'page_idx': p_idx,
                                'field_name': w.field_name,
                                'widget': txt_edit,
                                'type': 'text'
                            })

                    elif w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                        chk = QCheckBox()
                        chk.setChecked(bool(w.field_value))
                        chk.setStyleSheet("""
                            QCheckBox::indicator {
                                width: 16px;
                                height: 16px;
                                border: 1.5px solid #0284c7;
                                border-radius: 3px;
                                background-color: rgba(255, 255, 255, 0.95);
                            }
                            QCheckBox::indicator:checked {
                                background-color: #0284c7;
                            }
                        """)
                        def make_chk_updater(p_num, f_name):
                            return lambda state: self._on_form_field_changed(p_num, f_name, bool(state))
                        chk.stateChanged.connect(make_chk_updater(p_idx, w.field_name))
                        proxy = self.scene.addWidget(chk)
                        proxy.setPos(sx, sy)
                        proxy.setZValue(4)
                        self.interactive_form_proxies.append(proxy)
                        self._interactive_field_widgets.append({
                            'page_idx': p_idx,
                            'field_name': w.field_name,
                            'widget': chk,
                            'type': 'checkbox'
                        })

                    elif w.field_type == getattr(fitz, 'PDF_WIDGET_TYPE_RADIOBUTTON', 4):
                        rb = QRadioButton()
                        rb.setChecked(bool(w.field_value))
                        rb.setStyleSheet("""
                            QRadioButton::indicator {
                                width: 16px;
                                height: 16px;
                                border: 1.5px solid #0284c7;
                                border-radius: 8px;
                                background-color: rgba(255, 255, 255, 0.95);
                            }
                            QRadioButton::indicator:checked {
                                background-color: #0284c7;
                            }
                        """)
                        def make_rb_updater(p_num, f_name):
                            return lambda state: self._on_form_field_changed(p_num, f_name, bool(state))
                        rb.toggled.connect(make_rb_updater(p_idx, w.field_name))
                        proxy = self.scene.addWidget(rb)
                        proxy.setPos(sx, sy)
                        proxy.setZValue(4)
                        self.interactive_form_proxies.append(proxy)
                        self._interactive_field_widgets.append({
                            'page_idx': p_idx,
                            'field_name': w.field_name,
                            'widget': rb,
                            'type': 'radio'
                        })

                    elif w.field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX:
                        cmb = QComboBox()
                        try:
                            choices = w.choice_values or []
                            for c in choices:
                                cmb.addItem(str(c))
                            if w.field_value:
                                cmb.setCurrentText(str(w.field_value))
                        except Exception:
                            pass
                        cmb.setStyleSheet("""
                            QComboBox {
                                background-color: rgba(255, 255, 255, 0.95);
                                color: #111827;
                                border: 1.5px solid #0284c7;
                                border-radius: 3px;
                                padding: 2px 4px;
                                font-size: 11px;
                            }
                        """)
                        cmb.setGeometry(0, 0, int(sw), int(sh))
                        def make_cmb_updater(p_num, f_name):
                            return lambda txt: self._on_form_field_changed(p_num, f_name, txt)
                        cmb.currentTextChanged.connect(make_cmb_updater(p_idx, w.field_name))
                        proxy = self.scene.addWidget(cmb)
                        proxy.setPos(sx, sy)
                        proxy.setZValue(4)
                        self.interactive_form_proxies.append(proxy)
                        self._interactive_field_widgets.append({
                            'page_idx': p_idx,
                            'field_name': w.field_name,
                            'widget': cmb,
                            'type': 'combo'
                        })
            except Exception:
                pass

    def _on_form_field_changed(self, page_idx, field_name, val):
        if not self.doc or page_idx >= len(self.doc):
            return
        try:
            page = self.doc[page_idx]
            for w in page.widgets():
                if w.field_name == field_name:
                    w.field_value = val
                    w.update()
                    break
            self.set_modified(True)
        except Exception:
            pass

    def sync_form_fields(self):
        """Kullanıcının form alanlarına girdiği son değerleri PyMuPDF widget yapılarına kaydeder."""
        if not self.doc:
            return
        entries = getattr(self, '_interactive_field_widgets', [])
        for entry in entries:
            p_idx = entry.get('page_idx')
            f_name = entry.get('field_name')
            widget = entry.get('widget')
            if p_idx is None or p_idx >= len(self.doc) or not widget or not f_name:
                continue

            val = None
            if isinstance(widget, QLineEdit):
                val = widget.text()
            elif isinstance(widget, QTextEdit):
                val = widget.toPlainText()
            elif isinstance(widget, (QCheckBox, QRadioButton)):
                val = widget.isChecked()
            elif isinstance(widget, QComboBox):
                val = widget.currentText()

            if val is not None:
                try:
                    page = self.doc[p_idx]
                    for w in page.widgets():
                        if w.field_name == f_name:
                            w.field_value = val
                            w.update()
                            break
                except Exception:
                    pass

    def _handle_mouse_hover(self, event, tool):
        pos = self.view.mapToScene(event.pos())
        hovered_ribbon = None
        for it in self.scene.items(pos):
            if isinstance(it, BookmarkRibbonItem):
                hovered_ribbon = it
                break

        last_hov = getattr(self, '_last_hovered_ribbon', None)
        if last_hov != hovered_ribbon:
            if last_hov:
                last_hov.set_hovered(False)
            self._last_hovered_ribbon = hovered_ribbon
            if hovered_ribbon:
                hovered_ribbon.set_hovered(True)
            elif hasattr(self, 'main_window') and hasattr(self.main_window, 'update_viewport_cursor'):
                self.main_window.update_viewport_cursor()

        if hovered_ribbon:
            self.view.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            return

        if tool == 'selection_tool':
            sel_mode = getattr(self.main_window, 'selection_shape_mode', 'rect')
            if sel_mode == 'move':
                self.view.viewport().setCursor(CursorFactory.get_move_cursor())
            elif sel_mode == 'pan':
                self.view.viewport().setCursor(CursorFactory.get_pan_cursor())
            elif self.selected_drawings:
                pos = self.view.mapToScene(event.pos())
                is_over_sel = any(
                    d.get("item_ref") and d["item_ref"].sceneBoundingRect().adjusted(-4, -4, 4, 4).contains(pos)
                    for d in self.selected_drawings
                )
                if is_over_sel:
                    self.view.viewport().setCursor(CursorFactory.get_move_cursor())
                else:
                    self.view.viewport().setCursor(CursorFactory.get_selection_cursor(sel_mode))

    def show_tool_quick_menu(self, global_pos: QPoint, tool: str) -> bool:
        popup_map = {
            'highlighter': getattr(self.main_window, 'hl_popup', None),
            'pen': getattr(self.main_window, 'pen_popup', None),
            'eraser': getattr(self.main_window, 'eraser_popup', None),
            'text': getattr(self.main_window, 'text_popup', None),
            'selection_tool': getattr(self.main_window, 'selection_popup', None),
            'pointer': getattr(self.main_window, 'pointer_popup', None),
            'ruler': getattr(self.main_window, 'ruler_popup', None),
        }
        popup = popup_map.get(tool)
        if popup and hasattr(popup, 'show_at'):
            popup.show_at(global_pos)
            return True
        return False

    def show_highlighter_quick_menu(self, global_pos: QPoint):
        self.show_tool_quick_menu(global_pos, 'highlighter')

    def _handle_mouse_press(self, event, tool):
        pos = self.view.mapToScene(event.pos())

        page_idx = self.get_page_at_pos(pos)

        if tool == 'pan':
            self.is_panning = True
            self.pan_last_viewport_pos = event.pos()
            self.view.viewport().setCursor(CursorFactory.get_closed_hand_cursor())
            return True

        if tool == 'ruler':
            if page_idx is not None:
                self.start_measurement(pos, page_idx)
            return True

        if tool == 'selection_tool':
            sel_mode = getattr(self.main_window, 'selection_shape_mode', 'rect')

            # 1. El Aracı / Sayfayı Taşıma (Pan)
            if sel_mode == 'pan':
                self.is_panning = True
                self.pan_last_viewport_pos = event.pos()
                self.view.viewport().setCursor(CursorFactory.get_closed_hand_cursor())
                return True

            # 2. Yer Değiştirme (Move) Modu
            if sel_mode == 'move':
                clicked_sel = None
                if self.selected_drawings:
                    for d in self.selected_drawings:
                        it = d.get("item_ref")
                        if it and it.sceneBoundingRect().adjusted(-6, -6, 6, 6).contains(pos):
                            clicked_sel = d
                            break

                if clicked_sel:
                    self.is_moving_selection = True
                    self.move_start_pos = pos
                    self.move_last_pos = pos
                    self.move_initial_states = [self._snapshot_drawing_state(d) for d in self.selected_drawings]
                    return True

                hit_drawing = None
                for d in reversed(self.drawings):
                    it = d.get("item_ref")
                    if it and it.sceneBoundingRect().adjusted(-6, -6, 6, 6).contains(pos):
                        hit_drawing = d
                        break

                if hit_drawing:
                    self.selected_drawings = [hit_drawing]
                    self.highlight_selected_items()
                    self.is_moving_selection = True
                    self.move_start_pos = pos
                    self.move_last_pos = pos
                    self.move_initial_states = [self._snapshot_drawing_state(d) for d in self.selected_drawings]
                    return True

                self.clear_selection()
                self.selection_start_pt = pos
                pen = QPen(QColor("#388bfd"), 1.5, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(56, 139, 253, 35))
                self.selection_item = self.scene.addRect(QRectF(pos, pos), pen, brush)
                self.selection_item.setZValue(25)
                return True

            # 3. Rect / Lasso Seçim Modları
            if self.selected_drawings:
                clicked_on_selection = False
                for d in self.selected_drawings:
                    it = d.get("item_ref")
                    if it and it.sceneBoundingRect().adjusted(-6, -6, 6, 6).contains(pos):
                        clicked_on_selection = True
                        break
                if clicked_on_selection:
                    self.is_moving_selection = True
                    self.move_start_pos = pos
                    self.move_last_pos = pos
                    self.move_initial_states = [self._snapshot_drawing_state(d) for d in self.selected_drawings]
                    return True

            self.clear_selection()
            self.selection_start_pt = pos
            pen = QPen(QColor("#388bfd"), 1.5, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(56, 139, 253, 35))
            if sel_mode == 'rect':
                self.selection_item = self.scene.addRect(QRectF(pos, pos), pen, brush)
            else:
                self.selection_path = QPainterPath(pos)
                self.selection_item = self.scene.addPath(self.selection_path, pen, brush)
            self.selection_item.setZValue(25)
            return True

        if tool in ('select', 'text'):
            text_items = [it for it in self.scene.items(pos) if isinstance(it, EditableInlineTextItem)]
            if text_items:
                text_items[0].enable_editing()
                return True

        # Sayfa dışına tıklandıysa çizim veya metin başlatma!
        if page_idx is None:
            self.active_drawing_page = None
            self.current_path = None
            self.current_path_item = None
            self.stroke_start_pos = None
            if tool == 'eraser':
                self.eraser_last_pos = pos
                if getattr(self.main_window.eraser_popup, 'eraser_mode', 'stroke') == 'area':
                    self.area_erase_initial_drawings = [dict(d) for d in self.drawings]
                    self.area_erase_had_changes = False
                self.erase_at(pos, prev_pos=None)
            return True

        if tool == 'text':
            self.create_inline_text(pos, page_idx)
        elif tool == 'eraser':
            self.active_drawing_page = page_idx
            self.eraser_last_pos = pos
            if getattr(self.main_window.eraser_popup, 'eraser_mode', 'stroke') == 'area':
                self.area_erase_initial_drawings = [dict(d) for d in self.drawings]
                self.area_erase_had_changes = False
            self.erase_at(pos, prev_pos=None)
        elif tool in ['pen', 'highlighter']:
            self.active_drawing_page = page_idx
            self.stroke_start_pos = pos
            pen = self.main_window.get_current_pen()
            should_snap = (tool == 'highlighter' and self.main_window.hl_popup.snap_straight) or (tool == 'pen' and getattr(self.main_window.pen_popup, 'snap_straight', False)) or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            
            p_info = self.page_positions[page_idx]
            page_left = p_info.get('left', 0.0)
            top_y = p_info['top']

            popup = self.main_window.pen_popup if tool == 'pen' else self.main_window.hl_popup
            line_style = getattr(popup, 'line_style', 'solid')
            p_type = getattr(popup, 'current_pen_type', 'solid') if tool == 'pen' else 'highlighter'
            is_pencil = (tool == 'pen' and (p_type == 'pencil' or line_style == 'pencil'))

            rel_x = (pos.x() - page_left) / self.base_render_dpi
            rel_y = (pos.y() - top_y) / self.base_render_dpi
            self.current_stroke_pts = [(rel_x, rel_y)]

            if tool == 'pen' and line_style == 'calligraphy':
                rel_path = build_fountain_pen_path([QPointF(rel_x, rel_y)], base_width=float(popup.thickness) / self.base_render_dpi, min_width=1.8 / self.base_render_dpi)
                transform = QTransform()
                transform.translate(page_left, top_y)
                transform.scale(self.base_render_dpi, self.base_render_dpi)
                self.current_path = transform.map(rel_path)
                self.current_path_item = self.scene.addPath(self.current_path, QPen(Qt.PenStyle.NoPen), QBrush(popup.color))
            elif is_pencil:
                p_col = QColor(popup.color)
                tex = get_graphite_lead_texture(p_col)
                pencil_pen = QPen(QBrush(tex), popup.thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                if line_style == 'dash':
                    pencil_pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pencil_pen.setDashPattern([2.2, 1.5])
                elif line_style == 'dot':
                    pencil_pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pencil_pen.setDashPattern([0.01, 1.9])
                elif line_style == 'dashdot':
                    pencil_pen.setStyle(Qt.PenStyle.CustomDashLine)
                    pencil_pen.setDashPattern([2.2, 1.4, 0.01, 1.4])
                self.current_path = QPainterPath(pos)
                self.current_path_item = self.scene.addPath(self.current_path, pencil_pen)
            else:
                self.current_path = QPainterPath(pos)
                self.current_path_item = self.scene.addPath(self.current_path, pen)
        return True

    def _handle_mouse_move(self, event, tool):
        pos = self.view.mapToScene(event.pos())

        if tool == 'ruler':
            if self.active_measurement_item is not None:
                has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.update_measurement(pos, has_shift=has_shift)
            return True

        if tool in ('pan', 'selection_tool'):
            if self.is_panning and self.pan_last_viewport_pos is not None:
                delta = event.pos() - self.pan_last_viewport_pos
                self.pan_last_viewport_pos = event.pos()
                h_bar = self.view.horizontalScrollBar()
                v_bar = self.view.verticalScrollBar()
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
                return True
            if tool == 'pan':
                return True

            if self.is_moving_selection and self.move_last_pos is not None:
                delta_x = pos.x() - self.move_last_pos.x()
                delta_y = pos.y() - self.move_last_pos.y()
                self.move_last_pos = pos
                for d in self.selected_drawings:
                    it = d.get("item_ref")
                    if it:
                        it.moveBy(delta_x, delta_y)
                for h_it in self.selection_highlight_items:
                    h_it.moveBy(delta_x, delta_y)
                return True

            if self.selection_item:
                if self.main_window.selection_shape_mode == 'rect' and self.selection_start_pt:
                    self.selection_item.setRect(QRectF(self.selection_start_pt, pos).normalized())
                elif self.main_window.selection_shape_mode == 'lasso' and self.selection_path:
                    self.selection_path.lineTo(pos)
                    self.selection_item.setPath(self.selection_path)
                elif self.selection_start_pt:
                    self.selection_item.setRect(QRectF(self.selection_start_pt, pos).normalized())
                return True

            return True

        if tool == 'eraser':
            prev_p = getattr(self, 'eraser_last_pos', None)
            self.erase_at(pos, prev_pos=prev_p)
            self.eraser_last_pos = pos
            return True

        if self.current_path_item and self.active_drawing_page is not None:
            p_info = self.page_positions.get(self.active_drawing_page)
            if not p_info:
                return True
            top_y = p_info['top']
            bottom_y = p_info['bottom']
            page_left = p_info.get('left', 0.0)
            width = p_info['width']

            # Sayfa sınırları dışına taşmayı engelle (Clamp)
            clamped_x = max(page_left, min(pos.x(), page_left + width))
            clamped_y = max(top_y, min(pos.y(), bottom_y))
            clamped_pos = QPointF(clamped_x, clamped_y)

            is_hl_snap = (tool == 'highlighter' and self.main_window.hl_popup.snap_straight)
            is_pen_snap = (tool == 'pen' and getattr(self.main_window.pen_popup, 'snap_straight', False))
            has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            should_snap = is_hl_snap or is_pen_snap or has_shift

            popup = self.main_window.pen_popup if tool == 'pen' else self.main_window.hl_popup
            line_style = getattr(popup, 'line_style', 'solid')

            if should_snap and self.stroke_start_pos:
                snap_path = QPainterPath()
                snap_path.moveTo(self.stroke_start_pos)
                if tool == 'highlighter' and not has_shift:
                    snap_end_x = clamped_pos.x()
                    snap_end_y = self.stroke_start_pos.y()
                else:
                    snap_end_x = clamped_pos.x()
                    snap_end_y = clamped_pos.y()
                snap_end_pt = QPointF(snap_end_x, snap_end_y)
                snap_path.lineTo(snap_end_pt)
                self.current_stroke_pts = [
                    ((self.stroke_start_pos.x() - page_left) / self.base_render_dpi, (self.stroke_start_pos.y() - top_y) / self.base_render_dpi),
                    ((snap_end_x - page_left) / self.base_render_dpi, (snap_end_y - top_y) / self.base_render_dpi)
                ]
                if tool == 'pen' and line_style == 'calligraphy':
                    rel_pts = [QPointF(rx, ry) for rx, ry in self.current_stroke_pts]
                    rel_path = build_fountain_pen_path(rel_pts, base_width=float(popup.thickness) / self.base_render_dpi, min_width=1.8 / self.base_render_dpi)
                    transform = QTransform()
                    transform.translate(page_left, top_y)
                    transform.scale(self.base_render_dpi, self.base_render_dpi)
                    self.current_path = transform.map(rel_path)
                    self.current_path_item.setPath(self.current_path)
                else:
                    self.current_path = snap_path
                    self.current_path_item.setPath(snap_path)
            elif self.current_path:
                if self.current_stroke_pts:
                    last_rx, last_ry = self.current_stroke_pts[-1]
                    last_sx, last_sy = last_rx * self.base_render_dpi + page_left, last_ry * self.base_render_dpi + top_y
                    dist = math.hypot(clamped_pos.x() - last_sx, clamped_pos.y() - last_sy)
                else:
                    dist = 999.0

                is_pencil = (tool == 'pen' and (getattr(popup, 'current_pen_type', 'solid') == 'pencil' or line_style == 'pencil'))
                zoom = getattr(self, 'zoom_level', 1.0) or 1.0
                min_step = (1.5 / max(0.25, zoom)) if is_pencil else (0.8 / max(0.25, zoom))
                if dist >= min_step:
                    self.current_stroke_pts.append(((clamped_pos.x() - page_left) / self.base_render_dpi, (clamped_pos.y() - top_y) / self.base_render_dpi))
                    if tool == 'pen' and line_style == 'calligraphy':
                        rel_pts = [QPointF(rx, ry) for rx, ry in self.current_stroke_pts]
                        rel_path = build_fountain_pen_path(rel_pts, base_width=float(popup.thickness) / self.base_render_dpi, min_width=1.8 / self.base_render_dpi)
                        transform = QTransform()
                        transform.translate(page_left, top_y)
                        transform.scale(self.base_render_dpi, self.base_render_dpi)
                        self.current_path = transform.map(rel_path)
                        self.current_path_item.setPath(self.current_path)
                    else:
                        self.current_path.lineTo(clamped_pos)
                        self.current_path_item.setPath(self.current_path)
        return True

    def _handle_mouse_release(self, event, tool):
        pos = self.view.mapToScene(event.pos())

        if tool == 'ruler':
            if self.active_measurement_item is not None:
                has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.finish_measurement(pos, has_shift=has_shift)
            return True

        if tool in ('pan', 'selection_tool'):
            if self.is_panning:
                self.is_panning = False
                self.pan_last_viewport_pos = None
                self.view.viewport().setCursor(CursorFactory.get_pan_cursor())
                return True
            if tool == 'pan':
                return True

            if self.is_moving_selection:
                self.is_moving_selection = False
                rel_pos = self.view.mapToScene(event.pos())
                total_dx = (rel_pos.x() - self.move_start_pos.x()) if self.move_start_pos else 0.0
                total_dy = (rel_pos.y() - self.move_start_pos.y()) if self.move_start_pos else 0.0

                if (abs(total_dx) >= 2.0 or abs(total_dy) >= 2.0) and self.move_initial_states:
                    new_states = []
                    for i, d in enumerate(self.selected_drawings):
                        init_s = self.move_initial_states[i]
                        orig_page = init_s.get("page", 0)
                        orig_p_info = self.page_positions.get(orig_page)
                        if not orig_p_info:
                            new_states.append(self._snapshot_drawing_state(d))
                            continue

                        orig_page_left = orig_p_info.get('left', 0.0)
                        orig_page_top = orig_p_info['top']

                        if init_s.get("type") in ("polyline", "pencil") and "points" in init_s:
                            pts_scene = [
                                QPointF(rx * self.base_render_dpi + orig_page_left + total_dx,
                                        ry * self.base_render_dpi + orig_page_top + total_dy)
                                for rx, ry in init_s["points"]
                            ]
                            center_pt = pts_scene[0] if pts_scene else QPointF(orig_page_left, orig_page_top)
                            target_page = self.get_page_at_pos(center_pt)
                            if target_page is None:
                                target_page = orig_page
                            target_p_info = self.page_positions.get(target_page, orig_p_info)
                            target_page_left = target_p_info.get('left', 0.0)
                            target_page_top = target_p_info['top']

                            d["page"] = target_page
                            d["points"] = [
                                ((p.x() - target_page_left) / self.base_render_dpi,
                                 (p.y() - target_page_top) / self.base_render_dpi)
                                for p in pts_scene
                            ]
                            if init_s.get("arrow_head"):
                                ah_scene = [
                                    QPointF(rx * self.base_render_dpi + orig_page_left + total_dx,
                                            ry * self.base_render_dpi + orig_page_top + total_dy)
                                    for rx, ry in init_s["arrow_head"]
                                ]
                                d["arrow_head"] = [
                                    ((p.x() - target_page_left) / self.base_render_dpi,
                                     (p.y() - target_page_top) / self.base_render_dpi)
                                    for p in ah_scene
                                ]

                        elif init_s.get("type") in ("text", "image"):
                            orig_x = init_s.get("x", 0.0)
                            orig_y = init_s.get("y", 0.0)
                            item_scene_x = orig_x * self.base_render_dpi + orig_page_left + total_dx
                            item_scene_y = orig_y * self.base_render_dpi + orig_page_top + total_dy
                            center_pt = QPointF(item_scene_x, item_scene_y)
                            target_page = self.get_page_at_pos(center_pt)
                            if target_page is None:
                                target_page = orig_page
                            target_p_info = self.page_positions.get(target_page, orig_p_info)
                            target_page_left = target_p_info.get('left', 0.0)
                            target_page_top = target_p_info['top']

                            d["page"] = target_page
                            d["x"] = (item_scene_x - target_page_left) / self.base_render_dpi
                            d["y"] = (item_scene_y - target_page_top) / self.base_render_dpi

                        elif init_s.get("type") == "filled_path" and "rel_path" in init_s:
                            orig_transform = QTransform()
                            orig_transform.translate(orig_page_left, orig_page_top)
                            orig_transform.scale(self.base_render_dpi, self.base_render_dpi)
                            scene_path = orig_transform.map(init_s["rel_path"])

                            move_transform = QTransform()
                            move_transform.translate(total_dx, total_dy)
                            moved_scene_path = move_transform.map(scene_path)

                            center_pt = moved_scene_path.boundingRect().center()
                            target_page = self.get_page_at_pos(center_pt)
                            if target_page is None:
                                target_page = orig_page
                            target_p_info = self.page_positions.get(target_page, orig_p_info)
                            target_page_left = target_p_info.get('left', 0.0)
                            target_page_top = target_p_info['top']

                            target_inv = QTransform()
                            target_inv.translate(target_page_left, target_page_top)
                            target_inv.scale(self.base_render_dpi, self.base_render_dpi)
                            target_inv, invertible = target_inv.inverted()
                            if invertible:
                                d["page"] = target_page
                                d["rel_path"] = target_inv.map(moved_scene_path)

                        new_states.append(self._snapshot_drawing_state(d))

                    self.push_undo_action({
                        "type": "move_items",
                        "items": list(self.selected_drawings),
                        "old_states": self.move_initial_states,
                        "new_states": new_states
                    })

                    for d in self.selected_drawings:
                        if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                            self.scene.removeItem(d["item_ref"])
                        self.restore_drawing_item(d)

                    self.highlight_selected_items()
                    self.notify_drawings_changed()
                else:
                    for d in self.selected_drawings:
                        it = d.get("item_ref")
                        if it:
                            it.moveBy(-total_dx, -total_dy)
                    self.highlight_selected_items()

                self.move_start_pos = None
                self.move_last_pos = None
                self.move_initial_states = []
                return True

            if self.selection_item:
                if self.main_window.selection_shape_mode == 'lasso' and self.selection_path:
                    self.selection_path.closeSubpath()
                    self.selection_item.setPath(self.selection_path)

                sel_shape = self.selection_item.shape()
                sel_poly = sel_shape.toFillPolygon()
                sel_rect = self.selection_item.sceneBoundingRect()
                self.selected_drawings = []

                # Single-click selection if mouse wasn't dragged much
                is_single_click = (sel_rect.width() < 4 and sel_rect.height() < 4)
                release_pos = self.view.mapToScene(event.pos())

                for d in self.drawings:
                    it = d.get("item_ref")
                    if not it: continue

                    is_selected = False
                    if is_single_click:
                        if it.sceneBoundingRect().adjusted(-5, -5, 5, 5).contains(release_pos):
                            is_selected = True
                    else:
                        if self.selection_item.collidesWithItem(it):
                            is_selected = True
                        elif sel_rect.intersects(it.sceneBoundingRect()):
                            is_selected = True
                        elif sel_shape.intersects(it.shape()):
                            is_selected = True
                        elif d.get("type") == "polyline" and d.get("points"):
                            p_info = self.page_positions.get(d["page"], {})
                            page_top = p_info.get('top', 0)
                            page_left = p_info.get('left', 0.0)
                            for rx, ry in d["points"]:
                                pt = QPointF(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + page_top)
                                if sel_poly.containsPoint(pt, Qt.FillRule.OddEvenFill):
                                    is_selected = True
                                    break
                        elif d.get("type") in ("text", "image"):
                            if sel_poly.containsPoint(it.sceneBoundingRect().center(), Qt.FillRule.OddEvenFill):
                                is_selected = True

                    if is_selected:
                        self.selected_drawings.append(d)
                        if is_single_click:
                            break

                self.scene.removeItem(self.selection_item)
                self.selection_item = self.selection_start_pt = self.selection_path = None
                self.highlight_selected_items()
                return True

        if tool == 'eraser':
            if getattr(self, 'area_erase_had_changes', False):
                initial = getattr(self, 'area_erase_initial_drawings', None)
                if initial is not None:
                    self.push_undo_action({
                        "type": "area_erase",
                        "old_drawings": initial,
                        "new_drawings": [dict(d) for d in self.drawings]
                    })
                self.area_erase_had_changes = False
                self.area_erase_initial_drawings = None
                self.notify_drawings_changed()
            self.eraser_last_pos = None
            return True

        if tool in ['pen', 'highlighter'] and self.current_path_item and self.active_drawing_page is not None:
            if len(self.current_stroke_pts) == 1:
                p_info = self.page_positions.get(self.active_drawing_page)
                top_y = p_info['top'] if p_info else 0
                page_left = p_info.get('left', 0.0) if p_info else 0.0
                rx, ry = self.current_stroke_pts[0]
                self.current_stroke_pts.append((rx + 0.2, ry + 0.2))
                if self.current_path:
                    self.current_path.lineTo(QPointF(rx * self.base_render_dpi + page_left + 0.2, ry * self.base_render_dpi + top_y + 0.2))
                    self.current_path_item.setPath(self.current_path)

            if len(self.current_stroke_pts) > 1:
                p_info = self.page_positions.get(self.active_drawing_page)
                top_y = p_info['top'] if p_info else 0
                page_left = p_info.get('left', 0.0) if p_info else 0.0
                parent_item = p_info.get('bg_rect') if p_info else None

                popup = self.main_window.pen_popup if tool == 'pen' else self.main_window.hl_popup
                line_style = getattr(popup, 'line_style', 'solid')
                p_type = getattr(popup, 'current_pen_type', 'solid') if tool == 'pen' else 'highlighter'
                is_pencil = (tool == 'pen' and (p_type == 'pencil' or line_style == 'pencil'))

                is_hl_snap = (tool == 'highlighter' and self.main_window.hl_popup.snap_straight)
                is_pen_snap = (tool == 'pen' and getattr(self.main_window.pen_popup, 'snap_straight', False))
                has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                should_snap = is_hl_snap or is_pen_snap or has_shift
                if should_snap and self.stroke_start_pos:
                    start_pt = QPointF(self.current_stroke_pts[0][0] * self.base_render_dpi + page_left, self.current_stroke_pts[0][1] * self.base_render_dpi + top_y)
                    if tool == 'highlighter' and not has_shift:
                        end_y = self.current_stroke_pts[0][1] * self.base_render_dpi + top_y
                    else:
                        end_y = self.current_stroke_pts[1][1] * self.base_render_dpi + top_y
                    end_pt = QPointF(self.current_stroke_pts[1][0] * self.base_render_dpi + page_left, end_y)

                    if tool == 'pen' and line_style == 'calligraphy':
                        rel_pts = [QPointF(self.current_stroke_pts[0][0], self.current_stroke_pts[0][1]),
                                   QPointF(self.current_stroke_pts[1][0], (end_y - top_y) / self.base_render_dpi)]
                        rel_path = build_fountain_pen_path(rel_pts, base_width=float(popup.thickness) / self.base_render_dpi, min_width=1.8 / self.base_render_dpi)
                        transform = QTransform()
                        transform.translate(page_left, top_y)
                        transform.scale(self.base_render_dpi, self.base_render_dpi)
                        self.current_path = transform.map(rel_path)
                        self.current_path_item.setPath(self.current_path)
                    else:
                        self.scene.removeItem(self.current_path_item)
                        self.current_path = QPainterPath(start_pt)
                        self.current_path.lineTo(end_pt)
                        if is_pencil:
                            tex = get_graphite_lead_texture(QColor(popup.color))
                            p_pen = QPen(QBrush(tex), popup.thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                            if line_style == 'dash':
                                p_pen.setStyle(Qt.PenStyle.CustomDashLine)
                                p_pen.setDashPattern([2.2, 1.5])
                            elif line_style == 'dot':
                                p_pen.setStyle(Qt.PenStyle.CustomDashLine)
                                p_pen.setDashPattern([0.01, 1.9])
                            elif line_style == 'dashdot':
                                p_pen.setStyle(Qt.PenStyle.CustomDashLine)
                                p_pen.setDashPattern([2.2, 1.4, 0.01, 1.4])
                            self.current_path_item = self.scene.addPath(self.current_path, p_pen)
                        else:
                            self.current_path_item = self.scene.addPath(self.current_path, self.main_window.get_current_pen())

                arrow_head = None
                if line_style == 'arrow' and len(self.current_stroke_pts) >= 2:
                    p_end = self.current_stroke_pts[-1]
                    p_prev = self.current_stroke_pts[-2] if len(self.current_stroke_pts) == 2 else self.current_stroke_pts[max(0, len(self.current_stroke_pts) - 5)]
                    dx = (p_end[0] - p_prev[0]) * self.base_render_dpi
                    dy = (p_end[1] - p_prev[1]) * self.base_render_dpi
                    dist = math.hypot(dx, dy)
                    if dist > 2.0:
                        angle = math.atan2(dy, dx)
                        arrow_len = max(9.0, min(26.0, popup.thickness * 2.2 + 6.0))
                        spread = 0.50
                        end_sx = p_end[0] * self.base_render_dpi + page_left
                        end_sy = p_end[1] * self.base_render_dpi + top_y
                        left_sx = end_sx - arrow_len * math.cos(angle - spread)
                        left_sy = end_sy - arrow_len * math.sin(angle - spread)
                        right_sx = end_sx - arrow_len * math.cos(angle + spread)
                        right_sy = end_sy - arrow_len * math.sin(angle + spread)

                        self.current_path.moveTo(QPointF(left_sx, left_sy))
                        self.current_path.lineTo(QPointF(end_sx, end_sy))
                        self.current_path.lineTo(QPointF(right_sx, right_sy))
                        self.current_path_item.setPath(self.current_path)

                        arrow_head = [
                            ((left_sx - page_left) / self.base_render_dpi, (left_sy - top_y) / self.base_render_dpi),
                            (p_end[0], p_end[1]),
                            ((right_sx - page_left) / self.base_render_dpi, (right_sy - top_y) / self.base_render_dpi)
                        ]

                if tool == 'pen' and line_style == 'calligraphy':
                    rel_pts = [QPointF(rx, ry) for rx, ry in self.current_stroke_pts]
                    rel_path = build_fountain_pen_path(rel_pts, base_width=float(popup.thickness) / self.base_render_dpi, min_width=1.8 / self.base_render_dpi)
                    transform = QTransform()
                    transform.translate(page_left, top_y)
                    transform.scale(self.base_render_dpi, self.base_render_dpi)
                    scene_path = transform.map(rel_path)
                    self.current_path_item.setPath(scene_path)

                    new_item = {
                        "id": uuid.uuid4().hex[:12],
                        "type": "filled_path",
                        "page": self.active_drawing_page,
                        "points": self.current_stroke_pts,
                        "color": (popup.color.redF(), popup.color.greenF(), popup.color.blueF()),
                        "alpha": popup.color.alphaF(),
                        "width": popup.thickness,
                        "line_style": "calligraphy",
                        "rel_path": rel_path,
                        "path": self.current_path,
                        "item_ref": self.current_path_item
                    }
                    self.drawings.append(new_item)
                    self.push_undo_action({"type": "add", "data": new_item})
                    self.notify_drawings_changed(self.active_drawing_page)

                elif is_pencil:
                    if self.current_path_item and self.current_path_item.scene() == self.scene:
                        self.scene.removeItem(self.current_path_item)

                    scene_pts = [QPointF(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + top_y) for rx, ry in self.current_stroke_pts]
                    actual_style = "solid" if line_style == "pencil" else line_style
                    new_item = {
                        "id": uuid.uuid4().hex[:12],
                        "type": "pencil",
                        "pen_type": "pencil",
                        "page": self.active_drawing_page,
                        "points": self.current_stroke_pts,
                        "color": (popup.color.redF(), popup.color.greenF(), popup.color.blueF()),
                        "alpha": popup.color.alphaF(),
                        "width": popup.thickness,
                        "line_style": actual_style,
                        "arrow_head": arrow_head,
                    }
                    group_item = self._render_pencil_item(scene_pts, new_item)
                    new_item["item_ref"] = group_item
                    self.drawings.append(new_item)
                    self.push_undo_action({"type": "add", "data": new_item})
                    self.notify_drawings_changed(self.active_drawing_page)

                else:
                    new_item = {
                        "id": uuid.uuid4().hex[:12],
                        "type": "polyline", "page": self.active_drawing_page, "points": self.current_stroke_pts,
                        "color": (popup.color.redF(), popup.color.greenF(), popup.color.blueF()),
                        "alpha": popup.color.alphaF(), "width": popup.thickness,
                        "line_style": line_style,
                        "arrow_head": arrow_head,
                        "path": self.current_path, "pen": self.main_window.get_current_pen(), "item_ref": self.current_path_item
                    }
                    self.drawings.append(new_item)
                    self.push_undo_action({"type": "add", "data": new_item})
                    self.notify_drawings_changed(self.active_drawing_page)
            else:
                if self.current_path_item:
                    self.scene.removeItem(self.current_path_item)

            self.current_path = self.current_path_item = self.active_drawing_page = self.stroke_start_pos = None
            return True

        return True

    # --- ETKİLEŞİMLİ ÖLÇÜM CETVELİ (ADOBE ACROBAT PRO MEASURING TOOL) ---
    def start_measurement(self, pos: QPointF, page_idx: int):
        self.measurement_start_pos = pos
        unit = getattr(self.main_window, 'measurement_unit', getattr(self, 'measurement_unit', 'cm'))
        scale_ratio = getattr(self.main_window, 'measurement_scale', getattr(self, 'measurement_scale', 1.0))
        item = ModernMeasurementItem(pos, pos, self.base_render_dpi, unit, scale_ratio, page_idx)
        self.scene.addItem(item)
        self.active_measurement_item = item

    def update_measurement(self, pos: QPointF, has_shift: bool = False):
        if not self.active_measurement_item or not self.measurement_start_pos:
            return
        p1 = self.measurement_start_pos
        if has_shift:
            dx = pos.x() - p1.x()
            dy = pos.y() - p1.y()
            dist = math.hypot(dx, dy)
            if dist > 0.001:
                step = math.pi / 4.0  # 45 derece
                angle = round(math.atan2(dy, dx) / step) * step
                pos = QPointF(p1.x() + dist * math.cos(angle), p1.y() + dist * math.sin(angle))

        self.active_measurement_item.set_endpoints(p1, pos)

    def finish_measurement(self, pos: QPointF, has_shift: bool = False):
        if not self.active_measurement_item or not self.measurement_start_pos:
            return
        self.update_measurement(pos, has_shift=has_shift)
        p1 = self.measurement_start_pos
        p2 = self.active_measurement_item.p2
        # Çok küçük tıklamaları (4 pikselden az) tekil tık sayıp temizle
        if math.hypot(p2.x() - p1.x(), p2.y() - p1.y()) < 4.0:
            self.scene.removeItem(self.active_measurement_item)
            self.active_measurement_item = None
            self.measurement_start_pos = None
            return

        self.measurements.append(self.active_measurement_item)
        self.active_measurement_item = None
        self.measurement_start_pos = None
        self.view.viewport().update()

    def clear_all_measurements(self):
        for item in list(self.measurements):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.measurements.clear()
        if self.active_measurement_item:
            try:
                self.scene.removeItem(self.active_measurement_item)
            except Exception:
                pass
            self.active_measurement_item = None
        self.measurement_start_pos = None
        self.view.viewport().update()

    def update_measurement_settings(self, unit: str, scale_ratio: float):
        self.measurement_unit = unit
        self.measurement_scale = scale_ratio
        for item in self.measurements:
            item.set_unit_and_scale(unit, scale_ratio)
        if self.active_measurement_item:
            self.active_measurement_item.set_unit_and_scale(unit, scale_ratio)
        self.view.viewport().update()



