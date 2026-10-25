import os
import math
import uuid
import hashlib
import random
import json
import base64
import pymupdf as fitz
from typing import List, Dict, Optional, Any, Tuple
import urllib.parse
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                             QGraphicsTextItem, QMessageBox, QGraphicsItem, QMenu, QInputDialog,
                             QGraphicsItemGroup, QGraphicsPathItem, QApplication, QLineEdit,
                             QTextEdit, QPlainTextEdit, QSpinBox, QCheckBox, QRadioButton, QComboBox, QGraphicsProxyWidget,
                             QGraphicsPixmapItem)
from PyQt6.QtGui import (QImage, QPixmap, QPen, QColor, QPainter, QPainterPath, QPainterPathStroker,
                         QBrush, QLinearGradient, QRadialGradient, QFont,
                         QFontMetrics, QFontMetricsF, QTransform, QDesktopServices, QCursor, QPolygonF)
from PyQt6.QtCore import (Qt, QRectF, QPointF, QPoint, QTimer, QLineF, QEvent, QSettings, QUrl,
                          QThread, pyqtSignal as _pyqtSignal, QMutex, QMutexLocker, QBuffer, QIODevice)

from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.cursors import CursorFactory
from src.ui.widgets import EditableInlineTextItem
from src.document.media_items import PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem


def apply_smart_dark_invert(pix: fitz.Pixmap, page: fitz.Page, mat: fitz.Matrix) -> None:
    """Sayfa pixmap'ine akıllı gece modu uygular; metin ve arka planı tersine çevirirken
    sayfa içindeki resim, grafik ve fotoğrafların doğal renklerini korur."""
    pix.invert_irect()
    try:
        images = page.get_image_info(xrefs=True)
        for img_info in images:
            bbox = img_info.get("bbox")
            if bbox:
                irect = (fitz.Rect(bbox) * mat).round()
                irect = irect.intersect(pix.irect)
                if not irect.is_empty:
                    pix.invert_irect(irect)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PyMuPDF motorunu maksimum keskinlik ve anti-aliasing ile başlat
try:
    if hasattr(fitz, 'TOOLS'):
        fitz.TOOLS.set_aa_level(8)
        fitz.TOOLS.set_small_glyph_heights(True)
except Exception:
    pass


# ---------------------------------------------------------------------------
# Async PDF Render Worker - ana thread'i bloklamadan sayfaları render eder
# ---------------------------------------------------------------------------
class _PageRenderWorker(QThread):
    """Arka planda PDF sayfalarını yüksek hassasiyetle render edip thread-safe QImage olarak ana thread'e gönderir."""
    page_rendered = _pyqtSignal(int, object, float, float)  # (page_idx, QImage, job_zoom, job_dpr)
    finished_all  = _pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex  = QMutex()
        self._jobs: list = []
        self._abort = False

    def schedule(self, jobs: list):
        """jobs: [(page_idx, matrix, color_mode, doc_ptr, annots_flag, zoom, dpr)] listesi."""
        with QMutexLocker(self._mutex):
            self._jobs = list(jobs)
            self._abort = False

    def abort(self):
        with QMutexLocker(self._mutex):
            self._abort = True
            self._jobs.clear()

    def run(self):
        while True:
            with QMutexLocker(self._mutex):
                if not self._jobs or self._abort:
                    break
                job = self._jobs.pop(0)

            page_idx = job[0]
            mat = job[1]
            mode = job[2]
            doc = job[3]
            annots_flag = job[4] if len(job) > 4 else True
            job_zoom = float(job[5]) if len(job) > 5 else 1.0
            job_dpr = float(job[6]) if len(job) > 6 else 1.0

            try:
                pix = doc[page_idx].get_pixmap(matrix=mat, annots=annots_flag, alpha=False)
                if mode == 'dark':
                    apply_smart_dark_invert(pix, doc[page_idx], mat)
                # Bellek güvenliği için tampon belleği kopyala (dangling pointer ve bozulma koruması)
                qimg = QImage(pix.samples, pix.width, pix.height,
                              pix.stride, QImage.Format.Format_RGB888).copy()
                if mode == 'sepia':
                    p_sepia = QPainter(qimg)
                    p_sepia.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_Multiply)
                    p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                    p_sepia.end()

                # GUI thread'ine thread-safe QImage nesnesi gönder
                self.page_rendered.emit(page_idx, qimg, job_zoom, job_dpr)
            except Exception:
                pass
        self.finished_all.emit()


def build_smooth_path(pts: List[QPointF]) -> QPainterPath:
    """Noktaları C1-sürekli quadratik Bezier eğrileriyle birleştirerek ultra pürüzsüz ve yüksek çözünürlüklü vektör çizim yolu üretir."""
    path = QPainterPath()
    if not pts:
        return path
    if len(pts) == 1:
        path.moveTo(pts[0])
        path.lineTo(pts[0].x() + 0.05, pts[0].y() + 0.05)
        return path
    if len(pts) == 2:
        path.moveTo(pts[0])
        path.lineTo(pts[1])
        return path

    path.moveTo(pts[0])
    for i in range(len(pts) - 1):
        p_curr = pts[i]
        p_next = pts[i + 1]
        mid = QPointF((p_curr.x() + p_next.x()) / 2.0, (p_curr.y() + p_next.y()) / 2.0)
        path.quadTo(p_curr, mid)
    path.lineTo(pts[-1])
    return path


def smooth_points_for_pdf(pts: List[List[float]]) -> List[List[float]]:
    """PDF için polylineları Bezier ara noktalarıyla yumuşatarak köşeli piksel/merdiven görüntüsünü yok eder."""
    if len(pts) <= 2:
        return pts
    smoothed = [pts[0]]
    for i in range(len(pts) - 1):
        p0 = pts[i]
        p1 = pts[i + 1]
        mid = [(p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0]
        prev_mid = smoothed[-1]
        for t in (0.33, 0.66):
            bx = (1.0 - t)**2 * prev_mid[0] + 2.0 * (1.0 - t) * t * p0[0] + (t**2) * mid[0]
            by = (1.0 - t)**2 * prev_mid[1] + 2.0 * (1.0 - t) * t * p0[1] + (t**2) * mid[1]
            smoothed.append([bx, by])
        smoothed.append(mid)
    smoothed.append(pts[-1])
    return smoothed


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
    Sayfanın sağ üst köşesinde sayfa boyutuna orantılı zarif bir kurdele olarak konumlanır.
    """
    WIDTH = 26.0
    HEIGHT = 40.0
    NOTCH = 9.0
    BASE_WIDTH = 26.0
    BASE_HEIGHT = 40.0
    BASE_NOTCH = 9.0
    BASE_MARGIN = 22.0

    def __init__(
        self,
        tab_doc: 'PDFTabDocument',
        page_idx: int,
        x: float,
        y: float,
        is_bookmarked: bool = False,
        scale: float = 1.0
    ):
        super().__init__()
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.is_bookmarked = is_bookmarked
        self.is_hovered = False
        self.scale = max(0.35, min(1.35, float(scale)))

        self.width = self.BASE_WIDTH * self.scale
        self.height = self.BASE_HEIGHT * self.scale
        self.notch = self.BASE_NOTCH * self.scale

        # Geriye dönük uyumluluk
        self.WIDTH = self.width
        self.HEIGHT = self.height
        self.NOTCH = self.notch

        self.setPos(x, y)
        self.setZValue(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self._update_tooltip()

    def _update_tooltip(self):
        try:
            p_num = self.page_idx + 1
            if self.is_bookmarked:
                self.setToolTip(LanguageManager.tr("bookmark_ribbon_remove_tip", page=p_num))
            else:
                self.setToolTip(LanguageManager.tr("bookmark_ribbon_add_tip", page=p_num))
        except Exception:
            pass

    def set_bookmarked(self, val: bool):
        try:
            if self.is_bookmarked != val:
                self.is_bookmarked = val
                self._update_tooltip()
                self.update()
        except Exception:
            pass

    def set_hovered(self, val: bool):
        try:
            if self.is_hovered != val:
                self.is_hovered = val
                self.update()
        except Exception:
            pass

    def hoverEnterEvent(self, event):
        self.set_hovered(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.set_hovered(False)
        super().hoverLeaveEvent(event)

    def toggle_bookmark(self):
        if self.is_bookmarked:
            self.tab_doc.toggle_page_bookmark(self.page_idx)
        else:
            self.tab_doc.add_custom_page_bookmark(self.page_idx)

    def boundingRect(self) -> QRectF:
        pad = max(2.0, 3.0 * self.scale)
        return QRectF(-pad, -pad, self.width + pad * 2, self.height + pad * 2)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        w, h, notch = self.width, self.height, self.notch
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

        w = self.width
        h = self.height
        notch = self.notch
        s = self.scale

        # Path caching - her repaint'te yeniden oluşturmak yerine cache kullan
        if not hasattr(self, '_cached_path') or self._cached_path is None:
            self._cached_path = QPainterPath()
            self._cached_path.moveTo(0, 0)
            self._cached_path.lineTo(w, 0)
            self._cached_path.lineTo(w, h)
            self._cached_path.lineTo(w / 2.0, h - notch)
            self._cached_path.lineTo(0, h)
            self._cached_path.closeSubpath()

            self._cached_shadow_path = QPainterPath()
            shadow_off = max(1.0, 1.8 * s)
            self._cached_shadow_path.moveTo(1, 1)
            self._cached_shadow_path.lineTo(w + 1, 1)
            self._cached_shadow_path.lineTo(w + 1, h + shadow_off)
            self._cached_shadow_path.lineTo(w / 2.0 + 1, h - notch + shadow_off)
            self._cached_shadow_path.lineTo(1, h + shadow_off)
            self._cached_shadow_path.closeSubpath()

            iw, ih = w * 0.44, h * 0.42
            ix = (w - iw) / 2.0
            iy = max(2.5, 7.0 * s)
            inotch = notch * 0.42
            self._cached_icon_path = QPainterPath()
            self._cached_icon_path.moveTo(ix, iy)
            self._cached_icon_path.lineTo(ix + iw, iy)
            self._cached_icon_path.lineTo(ix + iw, iy + ih)
            self._cached_icon_path.lineTo(ix + iw / 2.0, iy + ih - inotch)
            self._cached_icon_path.lineTo(ix, iy + ih)
            self._cached_icon_path.closeSubpath()

        path = self._cached_path

        if self.is_bookmarked:
            # 1. Alt gölge
            painter.fillPath(self._cached_shadow_path, QColor(0, 0, 0, 45))

            # 2. Canlı kırmızı gövde gradient
            grad = QLinearGradient(0, 0, w, h)
            if self.is_hovered:
                grad.setColorAt(0.0, QColor("#fb7185"))
                grad.setColorAt(1.0, QColor("#e11d48"))
            else:
                grad.setColorAt(0.0, QColor("#ef4444"))
                grad.setColorAt(1.0, QColor("#be123c"))

            pen_w = max(0.8, 1.2 * s)
            painter.setPen(QPen(QColor("#881337"), pen_w))
            painter.setBrush(QBrush(grad))
            painter.drawPath(path)

            # 3. Üst kenar katlantı efekti (Sayfa kenarından sarkma hissi)
            painter.setPen(QPen(QColor(255, 255, 255, 90), max(0.6, 1.0 * s)))
            painter.drawLine(QPointF(1, 1), QPointF(w - 1, 1))

            # 4. İç zarif yer imi ikonu
            painter.setPen(QPen(QColor(255, 255, 255, 220), max(0.8, 1.2 * s)))
            painter.setBrush(QBrush(QColor(255, 255, 255, 45)))
            painter.drawPath(self._cached_icon_path)

        else:
            if self.is_hovered:
                painter.setPen(QPen(QColor("#f43f5e"), max(1.0, 1.4 * s), Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(QColor(244, 63, 94, 70)))
                painter.drawPath(path)

                cx = w / 2.0
                cy = max(5.0, 15.0 * s)
                cross_size = max(2.0, 4.0 * s)
                painter.setPen(QPen(QColor("#f43f5e"), max(1.0, 1.6 * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - cross_size, cy), QPointF(cx + cross_size, cy))
                painter.drawLine(QPointF(cx, cy - cross_size), QPointF(cx, cy + cross_size))
            else:
                painter.setPen(QPen(QColor(160, 160, 175, 170), max(0.8, 1.2 * s), Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(QColor(230, 230, 240, 90)))
                painter.drawPath(path)

                cx = w / 2.0
                cy = max(5.0, 15.0 * s)
                cross_size = max(1.8, 3.5 * s)
                painter.setPen(QPen(QColor(140, 140, 155, 160), max(0.8, 1.3 * s), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - cross_size, cy), QPointF(cx + cross_size, cy))
                painter.drawLine(QPointF(cx, cy - cross_size), QPointF(cx, cy + cross_size))

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
            act_add_sub = menu.addAction(ModernIconFactory.icon_bookmark(), LanguageManager.tr("bookmark_ribbon_add_sub"))
            act_rename = menu.addAction(ModernIconFactory.icon_bookmark(), LanguageManager.tr("bookmark_ribbon_rename"))
            act_remove = menu.addAction(LanguageManager.tr("bookmark_ribbon_remove"))
            chosen = menu.exec(global_pos)
            if chosen == act_add_sub:
                self.tab_doc.add_custom_page_bookmark(self.page_idx)
            elif chosen == act_rename:
                self.tab_doc.rename_page_bookmark(self.page_idx)
            elif chosen == act_remove:
                self.tab_doc.toggle_page_bookmark(self.page_idx)
        else:
            act_add = menu.addAction(ModernIconFactory.icon_bookmark(), LanguageManager.tr("bookmark_ribbon_add_page", page=target_page_1_based))
            act_add_custom = menu.addAction(LanguageManager.tr("bookmark_ribbon_add_custom"))
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
    def __init__(self, file_path: Optional[str] = None, main_window: Optional['AuraPDFViewer'] = None, initial_style: Optional[str] = None, initial_width: Optional[float] = None, initial_height: Optional[float] = None, create_initial_page: bool = False):
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
        self.is_form_design_mode: bool = False
        self.form_designer_items: list = []
        self.pending_form_field_type: Optional[str] = None
        self._form_ghost_item = None

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
        self.space_pan_active = False
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

        # Yorum Sürükleme (Draggable Comments)
        self._dragged_comment_annot = None
        self._dragged_comment_page = None
        self._dragged_comment_start_scene_pos = None
        self._dragged_comment_start_rect = None
        self._dragged_comment_is_dragging = False
        self._comment_drag_ghost_item = None

        # E-İmza & Damga Yerleştirme Modu (Interactive Stamp Cursor Placement)
        self.pending_stamp = None
        self._stamp_ghost_item = None

        # Etkileşimli Form Alanları (AcroForms)
        self.interactive_form_proxies: List[QGraphicsProxyWidget] = []

        self._setup_ui()
        self._load_annotations_from_doc()
        self.render_pages_init()
        if self.zoom_level != 1.0:
            self.view.scale(self.zoom_level, self.zoom_level)
        self.rerender_visible_pages()
        QTimer.singleShot(0, lambda: self.go_to_page(self.current_page_idx) if hasattr(self, 'current_page_idx') else None)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Antialiasing, yüksek DPI pürüzsüz pixmap ve metin keskinliği render hint'leri
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.view.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        if hasattr(QPainter.RenderHint, 'LosslessImageRendering'):
            self.view.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        # SmartViewportUpdate: Değişen bölgeleri ve hareketli öğeleri pürüzsüz günceller, yırtılma ve hayalet kalıntıları önler
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        # Sürükleme optimizasyonu
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Hayalet kalıntıları (ghost artifacts) önlemek ve kristal netlik sağlamak için CacheNone kullanılır
        self.view.setCacheMode(QGraphicsView.CacheModeFlag.CacheNone)
        self.view.setOptimizationFlag(
            QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, False)
        self.view.setStyleSheet("background-color: #181818; border: none;")
        self.view.setAcceptDrops(True)
        self.view.viewport().setAcceptDrops(True)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        layout.addWidget(self.view)

        self.view.viewport().installEventFilter(self)
        self.view.installEventFilter(self)
        self.view.verticalScrollBar().valueChanged.connect(self.on_scroll_change)

        # Ana render timer - scroll/zoom sonrası tetiklenir
        self.rerender_timer = QTimer(self)
        self.rerender_timer.setSingleShot(True)
        self.rerender_timer.timeout.connect(self.rerender_visible_pages)

        # Async render worker
        self._render_worker = _PageRenderWorker(self)
        self._render_worker.page_rendered.connect(self._on_page_rendered)

        # Zoom ayarı kaydetme için debounce timer (her zoom'da disk I/O yapmamak için)
        self._zoom_save_timer = QTimer(self)
        self._zoom_save_timer.setSingleShot(True)
        self._zoom_save_timer.setInterval(1500)
        self._zoom_save_timer.timeout.connect(self._do_save_zoom_setting)

        # Scroll debounce - hızlı scroll'da gereksiz render'ı önler
        self._scroll_pending = False

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
            fitz.PDF_ANNOT_UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT,
            fitz.PDF_ANNOT_FREE_TEXT,
            fitz.PDF_ANNOT_POLYGON
        )

        has_aurapdf_drawings = (
            self.doc is not None and
            hasattr(self.doc, 'embfile_names') and
            'aurapdf_drawings.json' in self.doc.embfile_names()
        )

        if has_aurapdf_drawings:
            # 1. In-memory dokümanda AuraPDF çizim/medya akışlarını sustur (böylece get_pixmap temiz arka plan üretir)
            for p in self.doc:
                try:
                    for x in p.get_contents():
                        st = self.doc.xref_stream(x)
                        if st and b'% AuraPDF Drawing Stream' in st:
                            self.doc.update_stream(x, b"")
                except Exception:
                    pass

            # 2. In-memory dokümanda standart ek açıklamaların get_pixmap ile çift çizilmesini önlemek için gizle
            for p in self.doc:
                try:
                    for a in list(p.annots()):
                        if a.type[0] in MANAGED_TYPES and not (a.flags & fitz.PDF_ANNOT_IS_HIDDEN):
                            a.set_flags(a.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                            a.update()
                except Exception:
                    pass

            # 3. aurapdf_drawings.json'dan tüm çizim, resim, tablo, metin kutusu ve medya nesnelerini geri yükle
            try:
                raw_bytes = self.doc.embfile_get('aurapdf_drawings.json')
                payload = json.loads(raw_bytes.decode('utf-8'))
                self.drawings.clear()
                for s in payload.get("drawings", []):
                    rec = self._deserialize_drawing_record(s)
                    if rec:
                        self.drawings.append(rec)
            except Exception as e:
                print("Error loading aurapdf_drawings.json:", e)

            return

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

                    elif a_type in (fitz.PDF_ANNOT_HIGHLIGHT, fitz.PDF_ANNOT_UNDERLINE, fitz.PDF_ANNOT_STRIKE_OUT):
                        if a_type == fitz.PDF_ANNOT_HIGHLIGHT:
                            markup_type = "highlight"
                            m_color = col if col != (0.0, 0.0, 0.0) else (1.0, 0.9, 0.2)
                            m_alpha = opacity if opacity > 0 else 0.38
                        elif a_type == fitz.PDF_ANNOT_UNDERLINE:
                            markup_type = "underline"
                            m_color = col if col != (0.0, 0.0, 0.0) else (0.1, 0.5, 0.9)
                            m_alpha = opacity if opacity > 0 else 1.0
                        else:
                            markup_type = "strikeout"
                            m_color = col if col != (0.0, 0.0, 0.0) else (0.9, 0.2, 0.2)
                            m_alpha = opacity if opacity > 0 else 1.0

                        v = annot.vertices or []
                        rects = []
                        if len(v) >= 4 and len(v) % 4 == 0:
                            quads = [v[i:i+4] for i in range(0, len(v), 4)]
                            for q in quads:
                                pts = [fitz.Point(pt[0], pt[1]) * page.rotation_matrix for pt in q]
                                rects.append([
                                    min(pt.x for pt in pts),
                                    min(pt.y for pt in pts),
                                    max(pt.x for pt in pts),
                                    max(pt.y for pt in pts)
                                ])
                        else:
                            r = annot.rect * page.rotation_matrix
                            r.normalize()
                            rects.append([r.x0, r.y0, r.x1, r.y1])

                        new_item = {
                            "id": uuid.uuid4().hex[:12],
                            "type": "text_markup",
                            "markup_type": markup_type,
                            "page": p_idx,
                            "rects": rects,
                            "color": m_color,
                            "alpha": m_alpha,
                            "width": 2.0,
                            "source_annot": True
                        }
                        self.drawings.append(new_item)
                        try:
                            annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                            annot.update()
                        except Exception:
                            pass
                        continue

                    for stroke_pts, ah in strokes_to_add:
                        pts_coords = [(pt.x, pt.y) for pt in stroke_pts]
                        info = annot.info or {}
                        is_pencil_annot = (info.get("subject") == "pencil" or info.get("title") == "AuraPencil")
                        new_item = {
                            "type": "pencil" if is_pencil_annot else "polyline",
                            "page": p_idx,
                            "points": pts_coords,
                            "color": col,
                            "alpha": opacity,
                            "width": width,
                            "line_style": line_style,
                            "arrow_head": ah,
                            "source_annot": True
                        }
                        if is_pencil_annot:
                            new_item["pen_type"] = "pencil"
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
            fitz.PDF_ANNOT_UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT,
            fitz.PDF_ANNOT_FREE_TEXT,
            fitz.PDF_ANNOT_POLYGON
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
        # Zoom ayarını hemen diske yaz (debounce geç kalabilir)
        try:
            if hasattr(self, '_zoom_save_timer') and self._zoom_save_timer:
                self._zoom_save_timer.stop()
        except Exception:
            pass
        self._do_save_zoom_setting()

        # Sesli okuma (TTS) aktifse ve bu belge okunuyorsa güvenle durdur
        try:
            mw = getattr(self, 'main_window', None)
            if mw and hasattr(mw, 'modern_right_sidebar') and mw.modern_right_sidebar:
                panel_acc = getattr(mw.modern_right_sidebar, 'panel_accessibility', None)
                if panel_acc:
                    panel_acc.on_document_closed(self)
                else:
                    se = getattr(mw.modern_right_sidebar, 'speech_engine', None)
                    if se and (se.is_speaking() or se.is_paused()):
                        tw = getattr(mw, 'tab_widget', None)
                        if tw is None or tw.count() <= 1:
                            se.stop()
        except Exception:
            pass

        self.clear_search_highlights()
        self.hide_laser_pointer()
        self._cleanup_comment_drag()
        self.clear_pending_stamp()
        self.cancel_form_field_placement()
        self.clear_form_designer_items()

        # Async render worker'ı güvenli şekilde durdur
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                self._render_worker.abort()
                if self._render_worker.isRunning():
                    self._render_worker.quit()
                    self._render_worker.wait(500)
            except Exception:
                pass

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
        if hasattr(self, 'bookmark_ribbon_items'):
            self.bookmark_ribbon_items.clear()
        self._last_hovered_ribbon = None
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
            if hasattr(self, '_alignment_guide_item') and self._alignment_guide_item:
                if self.scene and self._alignment_guide_item.scene() == self.scene:
                    self.scene.removeItem(self._alignment_guide_item)
                self._alignment_guide_item = None
            if hasattr(self, '_page_text_blocks_cache'):
                self._page_text_blocks_cache.clear()
        except Exception:
            pass
        import gc
        gc.collect()

    def show_alignment_guides(self, guides: list):
        """Kullanıcı metin kutusunu taşırken oluşan hizalama kılavuzlarını sahnede gösterir."""
        if not guides:
            self.clear_alignment_guides()
            return
        if not hasattr(self, '_alignment_guide_item') or self._alignment_guide_item is None:
            from src.ui.widgets import AlignmentGuideItem
            self._alignment_guide_item = AlignmentGuideItem()
            if self.scene:
                self.scene.addItem(self._alignment_guide_item)
        elif self.scene and self._alignment_guide_item.scene() != self.scene:
            try:
                self.scene.addItem(self._alignment_guide_item)
            except Exception:
                pass
        self._alignment_guide_item.set_guides(guides)

    def clear_alignment_guides(self):
        """Sahnede aktif hizalama kılavuz çizgileri varsa gizler ve temizler."""
        if hasattr(self, '_alignment_guide_item') and self._alignment_guide_item is not None:
            self._alignment_guide_item.clear()

    def compute_smart_snap(
        self,
        ignore_item: Any,
        raw_pos: QPointF,
        w: float,
        h: float,
        page_idx: int,
        snap_to_grid: bool = True
    ) -> Tuple[QPointF, List[Dict[str, Any]]]:
        """
        Metin kutuları ve görseller için gelişmiş akıllı hizalama ve manyetik yapışma (Smart Snapping & Guides).
        - Aynı sayfadaki diğer metin kutuları ve resimlerle kenar ve merkez hizalama
        - Sayfa merkez çizgileri (yatay & dikey) hizalama
        - Sayfa kılavuz ızgarasına (Grid) akıllı yapışma
        """
        p_info = self.page_positions.get(page_idx)
        margin = 8.0
        if p_info:
            page_left = float(p_info.get('left', 0.0))
            page_right = float(p_info.get('right', page_left + p_info.get('width', 600.0)))
            page_top = float(p_info.get('top', 0.0))
            page_bottom = float(p_info.get('bottom', page_top + p_info.get('height', 800.0)))
            page_w = float(p_info.get('width', page_right - page_left))
            page_h = float(p_info.get('height', page_bottom - page_top))

            max_x = max(page_left + margin, page_right - w - margin)
            max_y = max(page_top + margin, page_bottom - h - margin)
            clamped_x = max(page_left + margin, min(raw_pos.x(), max_x))
            clamped_y = max(page_top + margin, min(raw_pos.y(), max_y))
        else:
            page_left = 0.0
            page_right = 600.0
            page_top = 0.0
            page_bottom = 800.0
            page_w = 600.0
            page_h = 800.0
            clamped_x = raw_pos.x()
            clamped_y = raw_pos.y()

        guides = []
        SNAP_THRESHOLD = 8.0

        cand_left = clamped_x
        cand_cx = clamped_x + w / 2.0
        cand_right = clamped_x + w

        cand_top = clamped_y
        cand_cy = clamped_y + h / 2.0
        cand_bottom = clamped_y + h

        best_snap_x = None
        best_diff_x = SNAP_THRESHOLD + 1.0
        snap_x_guide = None

        best_snap_y = None
        best_diff_y = SNAP_THRESHOLD + 1.0
        snap_y_guide = None

        # 1. Aynı sayfadaki diğer nesneleri topla (metin kutuları ve eklenen resimler)
        other_items = []
        if self.scene:
            for it in self.scene.items():
                if it is ignore_item:
                    continue
                parent_text = getattr(ignore_item, 'parent_text_item', None)
                if parent_text and it is parent_text:
                    continue
                if getattr(it, 'parent_text_item', None) is ignore_item:
                    continue

                if it.__class__.__name__ == 'EditableInlineTextItem':
                    if getattr(it, 'page_idx', None) == page_idx:
                        other_items.append(it)
                elif it.__class__.__name__ in ('PDFResizableImageItem', 'PDFTableItem', 'PDFAudioItem', 'PDFVideoItem'):
                    p_num = getattr(it, 'page_idx', None)
                    if p_num is None:
                        rec = getattr(it, 'record', {})
                        p_num = rec.get('page', 0)
                    if p_num == page_idx:
                        other_items.append(it)
                elif getattr(it, 'page_idx', None) == page_idx:
                    if hasattr(it, 'sceneBoundingRect'):
                        other_items.append(it)

        # 2. Diğer nesneler ile kenar ve merkez hizalama
        for o_item in other_items:
            cls_name = o_item.__class__.__name__
            if cls_name in ('PDFResizableImageItem', 'PDFTableItem', 'PDFAudioItem', 'PDFVideoItem'):
                o_w = float(getattr(o_item, 'w', 0.0))
                o_h = float(getattr(o_item, 'h', 0.0))
                o_pos = o_item.pos()
                o_left = float(o_pos.x())
                o_top = float(o_pos.y())
                o_right = o_left + o_w
                o_bottom = o_top + o_h
                o_cx = o_left + o_w / 2.0
                o_cy = o_top + o_h / 2.0
            elif cls_name == 'EditableInlineTextItem':
                br = o_item.boundingRect()
                o_pos = o_item.pos()
                o_left = float(o_pos.x())
                o_top = float(o_pos.y())
                o_w = float(br.width())
                o_h = float(br.height())
                o_right = o_left + o_w
                o_bottom = o_top + o_h
                o_cx = o_left + o_w / 2.0
                o_cy = o_top + o_h / 2.0
            else:
                o_rect = o_item.sceneBoundingRect()
                o_left = o_rect.left()
                o_cx = o_rect.center().x()
                o_right = o_rect.right()
                o_top = o_rect.top()
                o_cy = o_rect.center().y()
                o_bottom = o_rect.bottom()

            # --- Yatay Hizalama (Dikey Çizgi Üretir) ---
            # Sol - Sol
            diff = abs(cand_left - o_left)
            if diff < best_diff_x:
                best_diff_x = diff
                best_snap_x = o_left
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": o_left,
                    "start": min(cand_top, o_top) - 15.0,
                    "end": max(cand_bottom, o_bottom) + 15.0,
                    "points": [QPointF(o_left, o_top), QPointF(o_left, o_bottom)]
                }
            # Merkez - Merkez
            diff = abs(cand_cx - o_cx)
            if diff < best_diff_x:
                best_diff_x = diff
                best_snap_x = o_cx - w / 2.0
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": o_cx,
                    "start": min(cand_top, o_top) - 15.0,
                    "end": max(cand_bottom, o_bottom) + 15.0,
                    "points": [QPointF(o_cx, o_cy)]
                }
            # Sağ - Sağ
            diff = abs(cand_right - o_right)
            if diff < best_diff_x:
                best_diff_x = diff
                best_snap_x = o_right - w
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": o_right,
                    "start": min(cand_top, o_top) - 15.0,
                    "end": max(cand_bottom, o_bottom) + 15.0,
                    "points": [QPointF(o_right, o_top), QPointF(o_right, o_bottom)]
                }
            # Sol - Sağ
            diff = abs(cand_left - o_right)
            if diff < best_diff_x:
                best_diff_x = diff
                best_snap_x = o_right
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": o_right,
                    "start": min(cand_top, o_top) - 15.0,
                    "end": max(cand_bottom, o_bottom) + 15.0,
                    "points": [QPointF(o_right, o_top)]
                }
            # Sağ - Sol
            diff = abs(cand_right - o_left)
            if diff < best_diff_x:
                best_diff_x = diff
                best_snap_x = o_left - w
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": o_left,
                    "start": min(cand_top, o_top) - 15.0,
                    "end": max(cand_bottom, o_bottom) + 15.0,
                    "points": [QPointF(o_left, o_top)]
                }

            # --- Dikey Hizalama (Yatay Çizgi Üretir) ---
            # Üst - Üst
            diff = abs(cand_top - o_top)
            if diff < best_diff_y:
                best_diff_y = diff
                best_snap_y = o_top
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": o_top,
                    "start": min(cand_left, o_left) - 15.0,
                    "end": max(cand_right, o_right) + 15.0,
                    "points": [QPointF(o_left, o_top), QPointF(o_right, o_top)]
                }
            # Merkez - Merkez
            diff = abs(cand_cy - o_cy)
            if diff < best_diff_y:
                best_diff_y = diff
                best_snap_y = o_cy - h / 2.0
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": o_cy,
                    "start": min(cand_left, o_left) - 15.0,
                    "end": max(cand_right, o_right) + 15.0,
                    "points": [QPointF(o_cx, o_cy)]
                }
            # Alt - Alt
            diff = abs(cand_bottom - o_bottom)
            if diff < best_diff_y:
                best_diff_y = diff
                best_snap_y = o_bottom - h
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": o_bottom,
                    "start": min(cand_left, o_left) - 15.0,
                    "end": max(cand_right, o_right) + 15.0,
                    "points": [QPointF(o_left, o_bottom), QPointF(o_right, o_bottom)]
                }
            # Üst - Alt
            diff = abs(cand_top - o_bottom)
            if diff < best_diff_y:
                best_diff_y = diff
                best_snap_y = o_bottom
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": o_bottom,
                    "start": min(cand_left, o_left) - 15.0,
                    "end": max(cand_right, o_right) + 15.0,
                    "points": [QPointF(o_left, o_bottom)]
                }
            # Alt - Üst
            diff = abs(cand_bottom - o_top)
            if diff < best_diff_y:
                best_diff_y = diff
                best_snap_y = o_top - h
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": o_top,
                    "start": min(cand_left, o_left) - 15.0,
                    "end": max(cand_right, o_right) + 15.0,
                    "points": [QPointF(o_left, o_top)]
                }

        # 3. Sayfa merkezine yapışma desteği
        if p_info:
            page_cx = page_left + page_w / 2.0
            diff = abs(cand_cx - page_cx)
            if diff < best_diff_x and diff <= SNAP_THRESHOLD:
                best_diff_x = diff
                best_snap_x = page_cx - w / 2.0
                snap_x_guide = {
                    "orientation": "vertical",
                    "coord": page_cx,
                    "start": page_top + 10.0,
                    "end": page_bottom - 10.0,
                    "points": []
                }

            page_cy = page_top + page_h / 2.0
            diff = abs(cand_cy - page_cy)
            if diff < best_diff_y and diff <= SNAP_THRESHOLD:
                best_diff_y = diff
                best_snap_y = page_cy - h / 2.0
                snap_y_guide = {
                    "orientation": "horizontal",
                    "coord": page_cy,
                    "start": page_left + 10.0,
                    "end": page_right - 10.0,
                    "points": []
                }

        # 4. Kılavuz Izgarasına (Grid) Akıllı Manyetik Yapışma Desteği
        GRID_SNAP_THRESHOLD = 6.0
        grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
        if snap_to_grid:
            if best_snap_x is None:
                dist_x = cand_left - page_left
                near_x = page_left + round(dist_x / grid_step) * grid_step
                diff_gx = abs(cand_left - near_x)
                if diff_gx <= GRID_SNAP_THRESHOLD:
                    best_snap_x = near_x
                    best_diff_x = diff_gx
                    snap_x_guide = {
                        "orientation": "vertical",
                        "coord": near_x,
                        "start": min(cand_top, page_top) - 10.0,
                        "end": max(cand_bottom, page_bottom) + 10.0,
                        "points": [QPointF(near_x, cand_top), QPointF(near_x, cand_bottom)]
                    }

            if best_snap_y is None:
                dist_y = cand_top - page_top
                near_y = page_top + round(dist_y / grid_step) * grid_step
                diff_gy = abs(cand_top - near_y)
                if diff_gy <= GRID_SNAP_THRESHOLD:
                    best_snap_y = near_y
                    best_diff_y = diff_gy
                    snap_y_guide = {
                        "orientation": "horizontal",
                        "coord": near_y,
                        "start": min(cand_left, page_left) - 10.0,
                        "end": max(cand_right, page_right) + 10.0,
                        "points": [QPointF(cand_left, near_y), QPointF(cand_right, near_y)]
                    }

        # 5. Manyetik yapışmayı uygula ve kılavuzları oluştur
        if best_snap_x is not None and best_diff_x <= SNAP_THRESHOLD:
            clamped_x = best_snap_x
            if snap_x_guide:
                snap_x_guide["points"].extend([
                    QPointF(snap_x_guide["coord"], clamped_y),
                    QPointF(snap_x_guide["coord"], clamped_y + h / 2.0),
                    QPointF(snap_x_guide["coord"], clamped_y + h)
                ])
                guides.append(snap_x_guide)

        if best_snap_y is not None and best_diff_y <= SNAP_THRESHOLD:
            clamped_y = best_snap_y
            if snap_y_guide:
                snap_y_guide["points"].extend([
                    QPointF(clamped_x, snap_y_guide["coord"]),
                    QPointF(clamped_x + w / 2.0, snap_y_guide["coord"]),
                    QPointF(clamped_x + w, snap_y_guide["coord"])
                ])
                guides.append(snap_y_guide)

        return QPointF(clamped_x, clamped_y), guides

    def compute_smart_snap_resize(
        self,
        ignore_item: Any,
        handle: str,
        cand_x: float,
        cand_y: float,
        cand_w: float,
        cand_h: float,
        orig_bounds: QRectF,
        page_idx: int,
        min_w: float = 40.0,
        min_h: float = 24.0,
        snap_to_grid: bool = True
    ) -> Tuple[float, float, float, float, List[Dict[str, Any]]]:
        """
        Tablo, görsel veya şekil boyutlandırma sırasında akıllı hizalama kılavuzları ve manyetik yapışma.
        Boyutlandırılan kenarlar (sağ, sol, üst, alt) sayfadaki diğer öğeler, sayfa sınırları ve grid ile hizalanır.
        """
        p_info = self.page_positions.get(page_idx) if hasattr(self, 'page_positions') else None
        margin = 8.0
        if p_info:
            page_left = float(p_info.get('left', 0.0))
            page_right = float(p_info.get('right', page_left + p_info.get('width', 600.0)))
            page_top = float(p_info.get('top', 0.0))
            page_bottom = float(p_info.get('bottom', page_top + p_info.get('height', 800.0)))
            page_w = float(p_info.get('width', page_right - page_left))
            page_h = float(p_info.get('height', page_bottom - page_top))
        else:
            page_left = 0.0
            page_right = 600.0
            page_top = 0.0
            page_bottom = 800.0
            page_w = 600.0
            page_h = 800.0

        guides = []
        SNAP_THRESHOLD = 8.0

        new_x = cand_x
        new_y = cand_y
        new_w = cand_w
        new_h = cand_h

        # 1. Aynı sayfadaki diğer nesneleri topla
        other_items = []
        if self.scene:
            for it in self.scene.items():
                if it is ignore_item:
                    continue
                parent_text = getattr(ignore_item, 'parent_text_item', None)
                if parent_text and it is parent_text:
                    continue
                if getattr(it, 'parent_text_item', None) is ignore_item:
                    continue
                if it.__class__.__name__ == 'EditableInlineTextItem':
                    if getattr(it, 'page_idx', None) == page_idx:
                        other_items.append(it)
                elif it.__class__.__name__ in ('PDFResizableImageItem', 'PDFTableItem', 'PDFAudioItem', 'PDFVideoItem'):
                    p_num = getattr(it, 'page_idx', None)
                    if p_num is None:
                        rec = getattr(it, 'record', {})
                        p_num = rec.get('page', 0)
                    if p_num == page_idx:
                        other_items.append(it)

        # Diğer nesnelerin sınırlarını çıkar
        other_rects = []
        for o_item in other_items:
            cls_name = o_item.__class__.__name__
            if cls_name in ('PDFResizableImageItem', 'PDFTableItem', 'PDFAudioItem', 'PDFVideoItem'):
                o_w = float(getattr(o_item, 'w', 0.0))
                o_h = float(getattr(o_item, 'h', 0.0))
                o_pos = o_item.pos()
                o_l = float(o_pos.x())
                o_t = float(o_pos.y())
                other_rects.append((o_l, o_t, o_l + o_w, o_t + o_h, o_l + o_w / 2.0, o_t + o_h / 2.0))
            elif cls_name == 'EditableInlineTextItem':
                br = o_item.boundingRect()
                o_pos = o_item.pos()
                o_l = float(o_pos.x())
                o_t = float(o_pos.y())
                o_w = float(br.width())
                o_h = float(br.height())
                other_rects.append((o_l, o_t, o_l + o_w, o_t + o_h, o_l + o_w / 2.0, o_t + o_h / 2.0))

        # --- YATAY BOYUTLANDIRMA SNAP (DİKEY ÇİZGİLER) ---
        if "r" in handle:
            cand_r = new_x + new_w
            best_diff_r = SNAP_THRESHOLD + 1.0
            best_snap_r = None
            snap_r_guide = None

            for o_l, o_t, o_r, o_b, o_cx, o_cy in other_rects:
                for target_x, pts in ((o_l, [QPointF(o_l, o_t), QPointF(o_l, o_b)]),
                                      (o_r, [QPointF(o_r, o_t), QPointF(o_r, o_b)]),
                                      (o_cx, [QPointF(o_cx, o_cy)])):
                    diff = abs(cand_r - target_x)
                    if diff < best_diff_r:
                        best_diff_r = diff
                        best_snap_r = target_x
                        snap_r_guide = {
                            "orientation": "vertical",
                            "coord": target_x,
                            "start": min(new_y, o_t) - 15.0,
                            "end": max(new_y + new_h, o_b) + 15.0,
                            "points": pts
                        }

            if p_info:
                page_cx = page_left + page_w / 2.0
                diff = abs(cand_r - page_cx)
                if diff < best_diff_r and diff <= SNAP_THRESHOLD:
                    best_diff_r = diff
                    best_snap_r = page_cx
                    snap_r_guide = {
                        "orientation": "vertical",
                        "coord": page_cx,
                        "start": page_top + 10.0,
                        "end": page_bottom - 10.0,
                        "points": []
                    }

            if snap_to_grid and best_snap_r is None:
                grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
                dist_r = cand_r - page_left
                near_r = page_left + round(dist_r / grid_step) * grid_step
                diff_gr = abs(cand_r - near_r)
                if diff_gr <= 6.0:
                    best_diff_r = diff_gr
                    best_snap_r = near_r
                    snap_r_guide = {
                        "orientation": "vertical",
                        "coord": near_r,
                        "start": min(new_y, page_top) - 10.0,
                        "end": max(new_y + new_h, page_bottom) + 10.0,
                        "points": [QPointF(near_r, new_y), QPointF(near_r, new_y + new_h)]
                    }

            if best_snap_r is not None and best_diff_r <= SNAP_THRESHOLD:
                new_w = max(min_w, best_snap_r - new_x)
                if snap_r_guide:
                    snap_r_guide["points"].extend([
                        QPointF(best_snap_r, new_y),
                        QPointF(best_snap_r, new_y + new_h / 2.0),
                        QPointF(best_snap_r, new_y + new_h)
                    ])
                    guides.append(snap_r_guide)

        elif "l" in handle:
            cand_l = new_x
            best_diff_l = SNAP_THRESHOLD + 1.0
            best_snap_l = None
            snap_l_guide = None

            for o_l, o_t, o_r, o_b, o_cx, o_cy in other_rects:
                for target_x, pts in ((o_l, [QPointF(o_l, o_t), QPointF(o_l, o_b)]),
                                      (o_r, [QPointF(o_r, o_t), QPointF(o_r, o_b)]),
                                      (o_cx, [QPointF(o_cx, o_cy)])):
                    diff = abs(cand_l - target_x)
                    if diff < best_diff_l:
                        best_diff_l = diff
                        best_snap_l = target_x
                        snap_l_guide = {
                            "orientation": "vertical",
                            "coord": target_x,
                            "start": min(new_y, o_t) - 15.0,
                            "end": max(new_y + new_h, o_b) + 15.0,
                            "points": pts
                        }

            if p_info:
                page_cx = page_left + page_w / 2.0
                diff = abs(cand_l - page_cx)
                if diff < best_diff_l and diff <= SNAP_THRESHOLD:
                    best_diff_l = diff
                    best_snap_l = page_cx
                    snap_l_guide = {
                        "orientation": "vertical",
                        "coord": page_cx,
                        "start": page_top + 10.0,
                        "end": page_bottom - 10.0,
                        "points": []
                    }

            if snap_to_grid and best_snap_l is None:
                grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
                dist_l = cand_l - page_left
                near_l = page_left + round(dist_l / grid_step) * grid_step
                diff_gl = abs(cand_l - near_l)
                if diff_gl <= 6.0:
                    best_diff_l = diff_gl
                    best_snap_l = near_l
                    snap_l_guide = {
                        "orientation": "vertical",
                        "coord": near_l,
                        "start": min(new_y, page_top) - 10.0,
                        "end": max(new_y + new_h, page_bottom) + 10.0,
                        "points": [QPointF(near_l, new_y), QPointF(near_l, new_y + new_h)]
                    }

            if best_snap_l is not None and best_diff_l <= SNAP_THRESHOLD:
                orig_r = orig_bounds.x() + orig_bounds.width()
                new_x = min(best_snap_l, orig_r - min_w)
                new_w = orig_r - new_x
                if snap_l_guide:
                    snap_l_guide["points"].extend([
                        QPointF(new_x, new_y),
                        QPointF(new_x, new_y + new_h / 2.0),
                        QPointF(new_x, new_y + new_h)
                    ])
                    guides.append(snap_l_guide)

        # --- DİKEY BOYUTLANDIRMA SNAP (YATAY ÇİZGİLER) ---
        if "b" in handle:
            cand_b = new_y + new_h
            best_diff_b = SNAP_THRESHOLD + 1.0
            best_snap_b = None
            snap_b_guide = None

            for o_l, o_t, o_r, o_b, o_cx, o_cy in other_rects:
                for target_y, pts in ((o_t, [QPointF(o_l, o_t), QPointF(o_r, o_t)]),
                                      (o_b, [QPointF(o_l, o_b), QPointF(o_r, o_b)]),
                                      (o_cy, [QPointF(o_cx, o_cy)])):
                    diff = abs(cand_b - target_y)
                    if diff < best_diff_b:
                        best_diff_b = diff
                        best_snap_b = target_y
                        snap_b_guide = {
                            "orientation": "horizontal",
                            "coord": target_y,
                            "start": min(new_x, o_l) - 15.0,
                            "end": max(new_x + new_w, o_r) + 15.0,
                            "points": pts
                        }

            if p_info:
                page_cy = page_top + page_h / 2.0
                diff = abs(cand_b - page_cy)
                if diff < best_diff_b and diff <= SNAP_THRESHOLD:
                    best_diff_b = diff
                    best_snap_b = page_cy
                    snap_b_guide = {
                        "orientation": "horizontal",
                        "coord": page_cy,
                        "start": page_left + 10.0,
                        "end": page_right - 10.0,
                        "points": []
                    }

            if snap_to_grid and best_snap_b is None:
                grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
                dist_b = cand_b - page_top
                near_b = page_top + round(dist_b / grid_step) * grid_step
                diff_gb = abs(cand_b - near_b)
                if diff_gb <= 6.0:
                    best_diff_b = diff_gb
                    best_snap_b = near_b
                    snap_b_guide = {
                        "orientation": "horizontal",
                        "coord": near_b,
                        "start": min(new_x, page_left) - 10.0,
                        "end": max(new_x + new_w, page_right) + 10.0,
                        "points": [QPointF(new_x, near_b), QPointF(new_x + new_w, near_b)]
                    }

            if best_snap_b is not None and best_diff_b <= SNAP_THRESHOLD:
                new_h = max(min_h, best_snap_b - new_y)
                if snap_b_guide:
                    snap_b_guide["points"].extend([
                        QPointF(new_x, best_snap_b),
                        QPointF(new_x + new_w / 2.0, best_snap_b),
                        QPointF(new_x + new_w, best_snap_b)
                    ])
                    guides.append(snap_b_guide)

        elif "t" in handle:
            cand_t = new_y
            best_diff_t = SNAP_THRESHOLD + 1.0
            best_snap_t = None
            snap_t_guide = None

            for o_l, o_t, o_r, o_b, o_cx, o_cy in other_rects:
                for target_y, pts in ((o_t, [QPointF(o_l, o_t), QPointF(o_r, o_t)]),
                                      (o_b, [QPointF(o_l, o_b), QPointF(o_r, o_b)]),
                                      (o_cy, [QPointF(o_cx, o_cy)])):
                    diff = abs(cand_t - target_y)
                    if diff < best_diff_t:
                        best_diff_t = diff
                        best_snap_t = target_y
                        snap_t_guide = {
                            "orientation": "horizontal",
                            "coord": target_y,
                            "start": min(new_x, o_l) - 15.0,
                            "end": max(new_x + new_w, o_r) + 15.0,
                            "points": pts
                        }

            if p_info:
                page_cy = page_top + page_h / 2.0
                diff = abs(cand_t - page_cy)
                if diff < best_diff_t and diff <= SNAP_THRESHOLD:
                    best_diff_t = diff
                    best_snap_t = page_cy
                    snap_t_guide = {
                        "orientation": "horizontal",
                        "coord": page_cy,
                        "start": page_left + 10.0,
                        "end": page_right - 10.0,
                        "points": []
                    }

            if snap_to_grid and best_snap_t is None:
                grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
                dist_t = cand_t - page_top
                near_t = page_top + round(dist_t / grid_step) * grid_step
                diff_gt = abs(cand_t - near_t)
                if diff_gt <= 6.0:
                    best_diff_t = diff_gt
                    best_snap_t = near_t
                    snap_t_guide = {
                        "orientation": "horizontal",
                        "coord": near_t,
                        "start": min(new_x, page_left) - 10.0,
                        "end": max(new_x + new_w, page_right) + 10.0,
                        "points": [QPointF(new_x, near_t), QPointF(new_x + new_w, near_t)]
                    }

            if best_snap_t is not None and best_diff_t <= SNAP_THRESHOLD:
                orig_b = orig_bounds.y() + orig_bounds.height()
                new_y = min(best_snap_t, orig_b - min_h)
                new_h = orig_b - new_y
                if snap_t_guide:
                    snap_t_guide["points"].extend([
                        QPointF(new_x, new_y),
                        QPointF(new_x + new_w / 2.0, new_y),
                        QPointF(new_x + new_w, new_y)
                    ])
                    guides.append(snap_t_guide)

        return new_x, new_y, new_w, new_h, guides

    def snap_item_to_grid(self, item: Any, page_idx: int):
        """Seçili metin kutusunu veya görseli en yakın ızgara çizgisine hizalar."""
        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return
        page_left = float(p_info.get('left', 0.0))
        page_top = float(p_info.get('top', 0.0))
        grid_step = 20.0 * getattr(self, 'base_render_dpi', 1.5)
        cur_pos = item.pos()
        new_x = page_left + round((cur_pos.x() - page_left) / grid_step) * grid_step
        new_y = page_top + round((cur_pos.y() - page_top) / grid_step) * grid_step
        item.setPos(QPointF(new_x, new_y))

        # PDFResizableImageItem veya görsel nesneleri güncelle
        if hasattr(item, '_sync_record'):
            item._sync_record()
        elif hasattr(item, 'parent_text_item') and hasattr(item.parent_text_item, '_sync_record'):
            item.parent_text_item._sync_record()

        # EditableInlineTextItem veya TextMoveHandleItem için metni dokümana kaydet
        target_text = item if item.__class__.__name__ == 'EditableInlineTextItem' else getattr(item, 'parent_text_item', None)
        if target_text and hasattr(self, 'commit_inline_text'):
            self.commit_inline_text(target_text)
            if hasattr(target_text, 'update_move_handle_position'):
                target_text.update_move_handle_position()

        if hasattr(self, 'notify_drawings_changed'):
            self.notify_drawings_changed(page_idx)
        if hasattr(self, 'view') and self.view:
            self.view.viewport().update()

    def closeEvent(self, event):
        self.close_document()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.rerender_visible_pages()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.center_current_page_horizontal()
        self.rerender_visible_pages()
        if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
            self.direct_edit_banner.reposition()
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.reposition()

    def center_current_page_horizontal(self):
        """Panel açılıp kapandığında veya pencere boyutu değiştiğinde açık sayfanın yatayda tam ortalanmasını sağlar."""
        if not hasattr(self, 'view') or not self.view or not hasattr(self, 'doc') or not self.doc:
            return
        if not hasattr(self, 'page_positions') or not self.page_positions:
            return
        try:
            p_idx = getattr(self, 'current_page_idx', 0)
            if p_idx not in self.page_positions:
                p_idx = min(self.page_positions.keys(), key=lambda k: abs(k - p_idx)) if self.page_positions else 0
            if p_idx in self.page_positions:
                p_info = self.page_positions[p_idx]
                page_center_x = p_info.get('left', 0.0) + p_info.get('width', 0.0) / 2.0
            else:
                s_rect = self.scene.sceneRect()
                page_center_x = s_rect.center().x()

            vp = self.view.viewport()
            if not vp or vp.width() <= 0 or vp.height() <= 0:
                return
            current_center_scene = self.view.mapToScene(vp.rect().center())
            self.view.centerOn(page_center_x, current_center_scene.y())
        except Exception:
            pass

    def _serialize_drawing_record(self, d: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Çizim veya medya kaydını JSON serileştirilebilir güvenli bir sözlüğe dönüştürür."""
        if not d or not isinstance(d, dict):
            return None
        d_type = d.get("type")
        if not d_type:
            return None

        orig_page = int(d.get("page", 0))
        p_info = self.page_positions.get(orig_page) if hasattr(self, 'page_positions') else None
        page_left = p_info.get('left', 0.0) if p_info else 0.0
        page_top = p_info.get('top', 0.0) if p_info else 0.0

        # Canlı sahnede aktifse güncel x, y, w, h konumlarını al
        it = d.get("item_ref")
        cur_x = float(d.get("x", 0.0))
        cur_y = float(d.get("y", 0.0))
        cur_w = float(d.get("w", 100.0))
        cur_h = float(d.get("h", 100.0))

        if it and hasattr(it, 'pos') and hasattr(it, 'scene') and it.scene() == self.scene:
            try:
                pos = it.pos()
                cur_x = (pos.x() - page_left) / self.base_render_dpi
                cur_y = (pos.y() - page_top) / self.base_render_dpi
                if hasattr(it, 'w') and hasattr(it, 'h'):
                    cur_w = it.w / self.base_render_dpi
                    cur_h = it.h / self.base_render_dpi
                elif hasattr(it, 'boundingRect'):
                    br = it.boundingRect()
                    cur_w = br.width() / self.base_render_dpi
                    cur_h = br.height() / self.base_render_dpi
            except Exception:
                pass

        def _col_to_list(col):
            if isinstance(col, QColor):
                return [round(col.redF(), 4), round(col.greenF(), 4), round(col.blueF(), 4)]
            elif isinstance(col, (tuple, list)) and len(col) >= 3:
                return [round(float(col[0]), 4), round(float(col[1]), 4), round(float(col[2]), 4)]
            elif isinstance(col, str) and col.startswith("#"):
                c = QColor(col)
                if c.isValid():
                    return [round(c.redF(), 4), round(c.greenF(), 4), round(c.blueF(), 4)]
            return [0.0, 0.0, 0.0]

        res = {
            "type": d_type,
            "page": orig_page,
            "x": cur_x,
            "y": cur_y,
            "w": cur_w,
            "h": cur_h
        }
        if "id" in d:
            res["id"] = d["id"]

        if d_type in ("polyline", "pencil"):
            res["points"] = [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in d.get("points", [])]
            if d.get("arrow_head"):
                res["arrow_head"] = [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in d["arrow_head"]]
            res["color"] = _col_to_list(d.get("color"))
            res["width"] = float(d.get("width", 2.0))
            res["alpha"] = float(d.get("alpha", 1.0))
            res["line_style"] = str(d.get("line_style", "solid"))
            res["pen_type"] = str(d.get("pen_type", "solid"))

        elif d_type == "filled_path":
            res["color"] = _col_to_list(d.get("color"))
            res["alpha"] = float(d.get("alpha", 1.0))
            res["line_style"] = str(d.get("line_style", "solid"))
            polys = []
            if d.get("rel_path"):
                try:
                    for poly in d["rel_path"].toFillPolygons():
                        polys.append([[round(float(pt.x()), 3), round(float(pt.y()), 3)] for pt in poly])
                except Exception:
                    polys = []
            res["polygons"] = polys

        elif d_type == "text_markup":
            res["markup_type"] = str(d.get("markup_type", "highlight"))
            res["rects"] = [[round(float(coord), 3) for coord in r] for r in d.get("rects", [])]
            res["color"] = _col_to_list(d.get("color"))
            res["alpha"] = float(d.get("alpha", 0.38 if res["markup_type"] == "highlight" else 1.0))
            res["width"] = float(d.get("width", 2.0))

        elif d_type == "text":
            text_str = str(d.get("text", ""))
            html_str = str(d.get("html", ""))
            if it and hasattr(it, 'scene') and it.scene() == self.scene:
                try:
                    if hasattr(it, 'toPlainText'):
                        text_str = it.toPlainText()
                    if hasattr(it, 'toHtml'):
                        html_str = it.toHtml()
                except Exception:
                    pass
            res["text"] = text_str
            res["html"] = html_str
            res["font_family"] = str(d.get("font_family", "Arial"))
            res["font_size"] = float(d.get("font_size", 14.0))
            res["color"] = _col_to_list(d.get("color"))
            res["bold"] = bool(d.get("bold", False))
            res["italic"] = bool(d.get("italic", False))
            res["underline"] = bool(d.get("underline", False))
            res["alignment"] = str(d.get("alignment", "left"))
            res["link_url"] = str(d.get("link_url", ""))
            res["link_type"] = str(d.get("link_type", "url"))
            res["link_raw"] = str(d.get("link_raw", ""))
            res["link_text"] = str(d.get("link_text", ""))
            res["link_range"] = d.get("link_range")
            res["manual_link"] = bool(d.get("manual_link", False))
            if d.get("fragments"):
                safe_fragments = []
                for line in d["fragments"]:
                    if isinstance(line, list):
                        safe_line = []
                        for frag in line:
                            if isinstance(frag, dict):
                                sf = dict(frag)
                                if "color" in sf:
                                    sf["color"] = _col_to_list(sf["color"])
                                safe_line.append(sf)
                            else:
                                safe_line.append(frag)
                        safe_fragments.append(safe_line)
                    else:
                        safe_fragments.append(line)
                res["fragments"] = safe_fragments

        elif d_type == "image":
            raw_bytes = d.get("image_bytes")
            if not raw_bytes and it and hasattr(it, 'pixmap') and not it.pixmap.isNull():
                try:
                    from PyQt6.QtCore import QBuffer, QIODevice
                    buf = QBuffer()
                    buf.open(QIODevice.OpenModeFlag.WriteOnly)
                    it.pixmap.save(buf, "PNG")
                    raw_bytes = bytes(buf.data())
                except Exception:
                    raw_bytes = None
            if raw_bytes:
                res["image_bytes"] = base64.b64encode(raw_bytes).decode('ascii')
            res["title"] = str(d.get("title", "Görsel"))
            res["keep_aspect"] = bool(d.get("keep_aspect", True))
            res["orig_w"] = int(d.get("orig_w", 100))
            res["orig_h"] = int(d.get("orig_h", 100))
            res["init_pdf_w"] = float(d.get("init_pdf_w", cur_w))
            res["init_pdf_h"] = float(d.get("init_pdf_h", cur_h))

        elif d_type == "table":
            c_data = d.get("cell_data", [])
            if it and hasattr(it, 'cell_data') and hasattr(it, 'scene') and it.scene() == self.scene:
                try:
                    c_data = [list(row) for row in it.cell_data]
                except Exception:
                    pass
            def _col_to_hex(val, default="#000000"):
                if isinstance(val, QColor):
                    return val.name()
                if isinstance(val, str):
                    return val
                return default

            res["rows"] = int(d.get("rows", 3))
            res["cols"] = int(d.get("cols", 3))
            res["has_header"] = bool(d.get("has_header", True))
            res["border_color"] = _col_to_hex(d.get("border_color"), "#c4b5fd")
            res["header_bg"] = _col_to_hex(d.get("header_bg"), "#7c3aed")
            res["cell_bg"] = _col_to_hex(d.get("cell_bg"), "#ffffff")
            res["alt_cell_bg"] = _col_to_hex(d.get("alt_cell_bg"), "")
            res["text_color"] = _col_to_hex(d.get("text_color"), "#1e1b4b")
            res["header_text_color"] = _col_to_hex(d.get("header_text_color"), "#ffffff")
            res["font_size"] = float(d.get("font_size", 11.0))
            res["font_family"] = str(d.get("font_family", "Arial"))
            res["alignment"] = str(d.get("alignment", "center"))
            res["cell_alignments"] = d.get("cell_alignments", [])
            res["cell_data"] = c_data

        elif d_type == "audio":
            if d.get("audio_bytes"):
                res["audio_bytes"] = base64.b64encode(d["audio_bytes"]).decode('ascii')
            res["title"] = str(d.get("title", "Ses Notu"))
            res["duration_sec"] = float(d.get("duration_sec", 0.0))
            res["format"] = str(d.get("format", "wav"))

        elif d_type == "video":
            if d.get("video_bytes"):
                res["video_bytes"] = base64.b64encode(d["video_bytes"]).decode('ascii')
            res["title"] = str(d.get("title", "Video"))

        return res

    def _deserialize_drawing_record(self, d: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Serileştirilmiş sözlükten canlı çalışma zamanı çizim kaydını yeniden kurar."""
        if not d or not isinstance(d, dict):
            return None
        d_type = d.get("type")
        if not d_type:
            return None

        col_list = d.get("color", [0.0, 0.0, 0.0])
        r = max(0.0, min(1.0, float(col_list[0])))
        g = max(0.0, min(1.0, float(col_list[1])))
        b = max(0.0, min(1.0, float(col_list[2])))

        rec = {
            "type": d_type,
            "page": int(d.get("page", 0)),
            "x": float(d.get("x", 0.0)),
            "y": float(d.get("y", 0.0)),
            "w": float(d.get("w", 100.0)),
            "h": float(d.get("h", 100.0)),
        }
        if "id" in d:
            rec["id"] = d["id"]

        if d_type in ("polyline", "pencil"):
            rec["points"] = [list(pt) for pt in d.get("points", [])]
            rec["arrow_head"] = [list(pt) for pt in d["arrow_head"]] if d.get("arrow_head") else None
            rec["color"] = (r, g, b)
            rec["width"] = float(d.get("width", 2.0))
            rec["alpha"] = float(d.get("alpha", 1.0))
            rec["line_style"] = str(d.get("line_style", "solid"))
            rec["pen_type"] = str(d.get("pen_type", "solid"))

        elif d_type == "filled_path":
            rec["color"] = (r, g, b)
            rec["alpha"] = float(d.get("alpha", 1.0))
            rec["line_style"] = str(d.get("line_style", "solid"))
            path = QPainterPath()
            for poly in d.get("polygons", []):
                if poly and len(poly) > 1:
                    path.moveTo(float(poly[0][0]), float(poly[0][1]))
                    for pt in poly[1:]:
                        path.lineTo(float(pt[0]), float(pt[1]))
                    path.closeSubpath()
            rec["rel_path"] = path

        elif d_type == "text_markup":
            rec["markup_type"] = str(d.get("markup_type", "highlight"))
            rec["rects"] = [[float(coord) for coord in r_box] for r_box in d.get("rects", [])]
            rec["color"] = (r, g, b)
            rec["alpha"] = float(d.get("alpha", 0.38 if rec["markup_type"] == "highlight" else 1.0))
            rec["width"] = float(d.get("width", 2.0))

        elif d_type == "text":
            rec["text"] = str(d.get("text", ""))
            rec["html"] = str(d.get("html", ""))
            rec["font_family"] = str(d.get("font_family", "Arial"))
            rec["font_size"] = int(d.get("font_size", 14))
            rec["color"] = QColor.fromRgbF(r, g, b)
            rec["bold"] = bool(d.get("bold", False))
            rec["italic"] = bool(d.get("italic", False))
            rec["underline"] = bool(d.get("underline", False))
            rec["alignment"] = str(d.get("alignment", "left"))
            rec["link_url"] = str(d.get("link_url", ""))
            rec["link_type"] = str(d.get("link_type", "url"))
            rec["link_raw"] = str(d.get("link_raw", ""))
            rec["link_text"] = str(d.get("link_text", ""))
            rec["link_range"] = d.get("link_range")
            rec["manual_link"] = bool(d.get("manual_link", False))
            if d.get("fragments"):
                restored_fragments = []
                for line in d["fragments"]:
                    if isinstance(line, list):
                        restored_line = []
                        for frag in line:
                            if isinstance(frag, dict):
                                rf = dict(frag)
                                if "color" in rf:
                                    col_v = rf["color"]
                                    if isinstance(col_v, (list, tuple)) and len(col_v) >= 3:
                                        rf["color"] = QColor.fromRgbF(float(col_v[0]), float(col_v[1]), float(col_v[2]))
                                    elif isinstance(col_v, str) and col_v.startswith("#"):
                                        rf["color"] = QColor(col_v)
                                restored_line.append(rf)
                            else:
                                restored_line.append(frag)
                        restored_fragments.append(restored_line)
                    else:
                        restored_fragments.append(line)
                rec["fragments"] = restored_fragments

        elif d_type == "image":
            raw_b64 = d.get("image_bytes")
            rec["image_bytes"] = base64.b64decode(raw_b64.encode('ascii')) if raw_b64 else b""
            rec["title"] = str(d.get("title", "Görsel"))
            rec["keep_aspect"] = bool(d.get("keep_aspect", True))
            rec["orig_w"] = int(d.get("orig_w", 100))
            rec["orig_h"] = int(d.get("orig_h", 100))
            rec["init_pdf_w"] = float(d.get("init_pdf_w", rec["w"]))
            rec["init_pdf_h"] = float(d.get("init_pdf_h", rec["h"]))

        elif d_type == "table":
            rec["rows"] = int(d.get("rows", 3))
            rec["cols"] = int(d.get("cols", 3))
            rec["has_header"] = bool(d.get("has_header", True))
            rec["border_color"] = str(d.get("border_color", "#c4b5fd"))
            rec["header_bg"] = str(d.get("header_bg", "#7c3aed"))
            rec["cell_bg"] = str(d.get("cell_bg", "#ffffff"))
            rec["alt_cell_bg"] = str(d.get("alt_cell_bg", ""))
            rec["text_color"] = str(d.get("text_color", "#1e1b4b"))
            rec["header_text_color"] = str(d.get("header_text_color", "#ffffff"))
            rec["font_size"] = float(d.get("font_size", 11.0))
            rec["font_family"] = str(d.get("font_family", "Arial"))
            rec["alignment"] = str(d.get("alignment", "center"))
            rec["cell_alignments"] = d.get("cell_alignments", [])
            rec["cell_data"] = d.get("cell_data", [])

        elif d_type == "audio":
            raw_b64 = d.get("audio_bytes")
            rec["audio_bytes"] = base64.b64decode(raw_b64.encode('ascii')) if raw_b64 else b""
            rec["title"] = str(d.get("title", "Ses Notu"))
            rec["duration_sec"] = float(d.get("duration_sec", 0.0))
            rec["format"] = str(d.get("format", "wav"))

        elif d_type == "video":
            raw_b64 = d.get("video_bytes")
            rec["video_bytes"] = base64.b64decode(raw_b64.encode('ascii')) if raw_b64 else b""
            rec["title"] = str(d.get("title", "Video"))

        return rec

    # --- DRY (Don't Repeat Yourself) Uygulaması: PDF'e aktarım mantığı ---
    def export_drawings_to_pdf(self, target_doc: fitz.Document, page_mapping: Optional[List[int]] = None):
        """
        Sahnedeki çizimleri hedef PDF dosyasına standart PDF Ink ek açıklamaları (Ink Annotations) olarak aktarır.
        Bu sayede hem Microsoft Edge ve Adobe Acrobat gibi harici okuyucular hem de farklı bilgisayardaki AuraPDF
        çizimleri tanır ve silebilir.
        Eğer page_mapping verilirse, orijinal sayfaları hedef dokümanın yeni indekslerine eşler.
        """
        # Aktif metin kutusu veya hücre düzenleme varsa kaydetmeden önce tamamla
        if hasattr(self, 'active_text_item') and self.active_text_item:
            try:
                self.commit_inline_text(self.active_text_item)
            except Exception:
                pass
        if hasattr(self, 'scene') and self.scene:
            for it in self.scene.items():
                if hasattr(it, 'finish_cell_editing'):
                    try:
                        it.finish_cell_editing()
                    except Exception:
                        pass

        # Canlı sahnede taşınmış veya boyutlandırılmış nesnelerin self.drawings içindeki konumlarını senkronize et
        for d in self.drawings:
            it = d.get("item_ref")
            orig_p = d.get("page", 0)
            p_info = self.page_positions.get(orig_p) if hasattr(self, 'page_positions') else None
            if p_info and it and hasattr(it, 'pos') and hasattr(it, 'scene') and it.scene() == self.scene:
                try:
                    pos = it.pos()
                    page_left = p_info.get('left', 0.0)
                    page_top = p_info['top']
                    d["x"] = (pos.x() - page_left) / self.base_render_dpi
                    d["y"] = (pos.y() - page_top) / self.base_render_dpi
                    if hasattr(it, 'w') and hasattr(it, 'h'):
                        d["w"] = it.w / self.base_render_dpi
                        d["h"] = it.h / self.base_render_dpi
                    elif hasattr(it, 'boundingRect'):
                        br = it.boundingRect()
                        d["w"] = br.width() / self.base_render_dpi
                        d["h"] = br.height() / self.base_render_dpi
                    if hasattr(it, 'cell_data'):
                        d["cell_data"] = [list(row) for row in it.cell_data]
                    if hasattr(it, 'toPlainText'):
                        d["text"] = it.toPlainText()
                    if hasattr(it, 'toHtml'):
                        d["html"] = it.toHtml()
                except Exception:
                    pass

        # 1. Hedef sayfalardaki mevcut ink ek açıklamalarını temizle (self.drawings tek doğru kaynaktır)
        pages_to_clean = set()
        if page_mapping is not None:
            for orig_p in page_mapping:
                idx = page_mapping.index(orig_p)
                if idx < len(target_doc):
                    pages_to_clean.add(idx)
        else:
            pages_to_clean = set(range(len(target_doc)))

        MANAGED_TYPES = (
            fitz.PDF_ANNOT_INK,
            fitz.PDF_ANNOT_LINE,
            fitz.PDF_ANNOT_POLY_LINE,
            fitz.PDF_ANNOT_HIGHLIGHT,
            fitz.PDF_ANNOT_UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT,
            fitz.PDF_ANNOT_FREE_TEXT,
            fitz.PDF_ANNOT_POLYGON
        )
        for p_idx in pages_to_clean:
            try:
                page = target_doc[p_idx]
                for annot in list(page.annots()):
                    if annot.type[0] in MANAGED_TYPES:
                        page.delete_annot(annot)
            except Exception:
                pass

        # Hedef belgede daha önceden kalmış eski AuraPDF çizim akışlarını ve üstverisini temizle
        if hasattr(target_doc, 'embfile_names') and 'aurapdf_drawings.json' in target_doc.embfile_names():
            try:
                target_doc.embfile_del('aurapdf_drawings.json')
            except Exception:
                pass

        for p_idx in pages_to_clean:
            try:
                page = target_doc[p_idx]
                for x in page.get_contents():
                    st = target_doc.xref_stream(x)
                    if st and b'% AuraPDF Drawing Stream' in st:
                        target_doc.update_stream(x, b"")
            except Exception:
                pass

        # Çizimler eklenmeden önce mevcut içerik akışlarını kaydet
        before_xrefs = {}
        for p_idx in range(len(target_doc)):
            try:
                before_xrefs[p_idx] = list(target_doc[p_idx].get_contents())
            except Exception:
                before_xrefs[p_idx] = []

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
                strokes = [smooth_points_for_pdf(pts)]

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
                    if is_pencil:
                        annot.set_info(title="AuraPencil", subject="pencil")
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

                alpha_val = float(d.get("alpha", 1.0))
                if d.get("line_style") == "pencil":
                    alpha_val = min(1.0, alpha_val * 0.78)

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
                            annot.set_opacity(alpha_val)
                            annot.update()
                        except Exception:
                            pass

            elif d.get("type") == "text_markup":
                markup_type = d.get("markup_type", "highlight")
                rects = d.get("rects", [])
                if not rects:
                    continue
                pdf_rects = []
                for r in rects:
                    vis_rect = fitz.Rect(r[0], r[1], r[2], r[3])
                    pr = vis_rect * page.derotation_matrix
                    pr.normalize()
                    pdf_rects.append(pr)

                col = d.get("color", (1.0, 0.9, 0.2))
                if isinstance(col, (tuple, list)) and len(col) >= 3:
                    stroke_col = (float(col[0]), float(col[1]), float(col[2]))
                elif isinstance(col, QColor):
                    stroke_col = (col.redF(), col.greenF(), col.blueF())
                else:
                    stroke_col = (1.0, 0.9, 0.2)

                alpha_val = float(d.get("alpha", 0.38 if markup_type == "highlight" else 1.0))

                try:
                    if markup_type == "highlight":
                        annot = page.add_highlight_annot(pdf_rects)
                    elif markup_type == "underline":
                        annot = page.add_underline_annot(pdf_rects)
                    elif markup_type == "strikeout":
                        annot = page.add_strikeout_annot(pdf_rects)
                    else:
                        annot = page.add_highlight_annot(pdf_rects)

                    annot.set_colors(stroke=stroke_col)
                    annot.set_opacity(alpha_val)
                    annot.set_flags(fitz.PDF_ANNOT_IS_PRINT)
                    annot.update()
                except Exception as e:
                    import traceback
                    traceback.print_exc()

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
                    from src.ui.direct_text_editor import get_unicode_font_path

                    frags = None
                    if it and hasattr(it, 'get_fragments'):
                        frags = it.get_fragments()
                    if not frags:
                        frags = d.get("fragments")

                    # Eğer zengin metin fragment'ları yoksa, metni satırlara ve gerekirse kutu genişliğine böl
                    if not frags:
                        lines = content.split("\n")
                        frags = []
                        for raw_line in lines:
                            if w_pt > 20 and len(raw_line) > 1:
                                words = raw_line.split(" ")
                                cur_l = ""
                                for w in words:
                                    test_l = (cur_l + " " + w).strip()
                                    w_test = len(test_l) * fs * 0.55
                                    if w_test > (w_pt - 6.0) and cur_l:
                                        frags.append([{
                                            "text": cur_l,
                                            "font_size": fs,
                                            "bold": bool(d.get("bold", False)),
                                            "italic": bool(d.get("italic", False)),
                                            "underline": bool(d.get("underline", False)),
                                            "color": rgb,
                                            "href": d.get("link_url", "")
                                        }])
                                        cur_l = w
                                    else:
                                        cur_l = test_l
                                if cur_l:
                                    frags.append([{
                                        "text": cur_l,
                                        "font_size": fs,
                                        "bold": bool(d.get("bold", False)),
                                        "italic": bool(d.get("italic", False)),
                                        "underline": bool(d.get("underline", False)),
                                        "color": rgb,
                                        "href": d.get("link_url", "")
                                    }])
                            else:
                                frags.append([{
                                    "text": raw_line,
                                    "font_size": fs,
                                    "bold": bool(d.get("bold", False)),
                                    "italic": bool(d.get("italic", False)),
                                    "underline": bool(d.get("underline", False)),
                                    "color": rgb,
                                    "href": d.get("link_url", "")
                                }])

                    font_fam = d.get("font_family") or "Arial"
                    f_reg_path = get_unicode_font_path(font_fam, bold=False, italic=False)
                    f_bold_path = get_unicode_font_path(font_fam, bold=True, italic=False)
                    f_it_path = get_unicode_font_path(font_fam, bold=False, italic=True)
                    f_bi_path = get_unicode_font_path(font_fam, bold=True, italic=True)

                    if f_reg_path and os.path.isfile(f_reg_path):
                        try:
                            page.insert_font(fontname="F_AURA_REG", fontfile=f_reg_path)
                        except Exception:
                            pass
                    if f_bold_path and os.path.isfile(f_bold_path):
                        try:
                            page.insert_font(fontname="F_AURA_BOLD", fontfile=f_bold_path)
                        except Exception:
                            pass
                    if f_it_path and os.path.isfile(f_it_path):
                        try:
                            page.insert_font(fontname="F_AURA_ITALIC", fontfile=f_it_path)
                        except Exception:
                            pass
                    if f_bi_path and os.path.isfile(f_bi_path):
                        try:
                            page.insert_font(fontname="F_AURA_BI", fontfile=f_bi_path)
                        except Exception:
                            pass

                    font_reg = fitz.Font(fontfile=f_reg_path) if (f_reg_path and os.path.isfile(f_reg_path)) else fitz.Font("helv")
                    font_bold = fitz.Font(fontfile=f_bold_path) if (f_bold_path and os.path.isfile(f_bold_path)) else fitz.Font("hebo")
                    font_it = fitz.Font(fontfile=f_it_path) if (f_it_path and os.path.isfile(f_it_path)) else fitz.Font("heit")
                    font_bi = fitz.Font(fontfile=f_bi_path) if (f_bi_path and os.path.isfile(f_bi_path)) else fitz.Font("hebi")

                    curr_y = rel_y + (4.0 / self.base_render_dpi)
                    rot = page.rotation

                    for blk in frags:
                        blk_frags = [f for f in blk if f.get("text")]
                        if not blk_frags:
                            curr_y += float(d.get("font_size", 14)) * 1.25
                            continue

                        blk_max_fs = max((float(f.get("font_size", 14)) for f in blk_frags), default=float(d.get("font_size", 14)))
                        line_baseline_y = curr_y + blk_max_fs * 0.85
                        align_val = str(d.get("alignment", "left")).lower()
                        if align_val in ("center", "right", "hcenter"):
                            blk_total_w = 0.0
                            for frag in blk_frags:
                                f_txt = frag["text"]
                                f_s = float(frag.get("font_size", blk_max_fs))
                                f_b = frag.get("bold", False)
                                f_i = frag.get("italic", False)
                                f_fnt = (font_bi if (f_b and f_i) else font_bold if f_b else font_it if f_i else font_reg)
                                try:
                                    blk_total_w += f_fnt.text_length(f_txt, fontsize=f_s)
                                except Exception:
                                    blk_total_w += len(f_txt) * f_s * 0.55
                            if align_val in ("center", "hcenter"):
                                curr_x = rel_x + max(0.0, (w_pt - blk_total_w) / 2.0)
                            else:
                                curr_x = rel_x + max(0.0, w_pt - blk_total_w - (4.0 / self.base_render_dpi))
                        else:
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
                                fpath_cur = f_bi_path
                            elif f_bold:
                                fname = "F_AURA_BOLD"
                                ffont = font_bold
                                fpath_cur = f_bold_path
                            elif f_italic:
                                fname = "F_AURA_ITALIC"
                                ffont = font_it
                                fpath_cur = f_it_path
                            else:
                                fname = "F_AURA_REG"
                                ffont = font_reg
                                fpath_cur = f_reg_path

                            try:
                                frag_w = ffont.text_length(frag_txt, fontsize=f_sz)
                            except Exception:
                                frag_w = len(frag_txt) * f_sz * 0.55

                            vis_pt = fitz.Point(curr_x, line_baseline_y)
                            pdf_pt = vis_pt * page.derotation_matrix
                            try:
                                page.insert_text(pdf_pt, frag_txt, fontname=fname, fontfile=fpath_cur, fontsize=f_sz, color=f_rgb, rotate=rot)
                            except Exception:
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

                # Harici PDF okuyucularda (Adobe Acrobat, Edge vb.) resmin görünmeme sorununu önlemek için:
                # WebP, SVG, GIF, BMP vb. formatları PyMuPDF'in %100 desteklediği standart PNG baytlarına dönüştür
                clean_png = None
                raw_bytes = d.get("image_bytes")
                try:
                    q_img = QImage()
                    if raw_bytes:
                        q_img.loadFromData(raw_bytes)
                    if q_img.isNull() and d.get("item_ref") and hasattr(d["item_ref"], "pixmap") and not d["item_ref"].pixmap.isNull():
                        q_img = d["item_ref"].pixmap.toImage()
                    if not q_img.isNull():
                        from PyQt6.QtCore import QBuffer, QIODevice
                        buf = QBuffer()
                        buf.open(QIODevice.OpenModeFlag.WriteOnly)
                        if q_img.save(buf, "PNG"):
                            clean_png = bytes(buf.data())
                except Exception:
                    clean_png = None

                target_stream = clean_png if clean_png else raw_bytes
                if target_stream and img_rect.is_valid and not img_rect.is_empty:
                    inserted = False
                    try:
                        page.insert_image(img_rect, stream=target_stream, rotate=page.rotation, overlay=True)
                        inserted = True
                    except Exception:
                        pass
                    if not inserted:
                        try:
                            page.insert_image(img_rect, stream=target_stream, overlay=True)
                            inserted = True
                        except Exception:
                            pass
                    if not inserted and clean_png and raw_bytes and target_stream != raw_bytes:
                        try:
                            page.insert_image(img_rect, stream=raw_bytes, overlay=True)
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

                from src.ui.direct_text_editor import get_unicode_font_path
                font_fam = d.get("font_family") or "Arial"
                tbl_hdr_font_path = get_unicode_font_path(font_fam, bold=True, italic=False)
                tbl_reg_font_path = get_unicode_font_path(font_fam, bold=False, italic=False)

                # Standart sistem TrueType fontlarına güvenli fallback
                windir = os.environ.get("WINDIR", r"C:\Windows")
                fonts_dir = os.path.join(windir, "Fonts")
                if not (tbl_hdr_font_path and os.path.isfile(tbl_hdr_font_path)):
                    f_cand = os.path.join(fonts_dir, "arialbd.ttf")
                    if os.path.isfile(f_cand):
                        tbl_hdr_font_path = f_cand
                if not (tbl_reg_font_path and os.path.isfile(tbl_reg_font_path)):
                    f_cand = os.path.join(fonts_dir, "arial.ttf")
                    if os.path.isfile(f_cand):
                        tbl_reg_font_path = f_cand

                tbl_hdr_fname = "F_AURA_TBL_HDR"
                tbl_reg_fname = "F_AURA_TBL_REG"
                if tbl_hdr_font_path and os.path.isfile(tbl_hdr_font_path):
                    try:
                        page.insert_font(fontname=tbl_hdr_fname, fontfile=tbl_hdr_font_path)
                    except Exception:
                        pass
                if tbl_reg_font_path and os.path.isfile(tbl_reg_font_path):
                    try:
                        page.insert_font(fontname=tbl_reg_fname, fontfile=tbl_reg_font_path)
                    except Exception:
                        pass

                hdr_font_obj = None
                reg_font_obj = None
                if tbl_hdr_font_path and os.path.isfile(tbl_hdr_font_path):
                    try:
                        hdr_font_obj = fitz.Font(fontfile=tbl_hdr_font_path)
                    except Exception:
                        hdr_font_obj = None
                if tbl_reg_font_path and os.path.isfile(tbl_reg_font_path):
                    try:
                        reg_font_obj = fitz.Font(fontfile=tbl_reg_font_path)
                    except Exception:
                        reg_font_obj = None

                cell_w = t_w / cols
                cell_h = t_h / rows
                base_fs = max(6.0, float(d.get("font_size", 10.0)))

                def _calc_text_w(s: str, fobj, fs: float) -> float:
                    if not s:
                        return 0.0
                    if fobj:
                        try:
                            return fobj.text_length(s, fontsize=fs)
                        except Exception:
                            pass
                    return len(s) * fs * 0.55

                def _elide_line(s: str, fobj, fs: float, max_w: float) -> str:
                    if _calc_text_w(s, fobj, fs) <= max_w:
                        return s
                    ellipsis = "..."
                    if _calc_text_w(ellipsis, fobj, fs) > max_w:
                        return ""
                    low = 0
                    high = len(s)
                    best = ""
                    while low <= high:
                        mid = (low + high) // 2
                        cand = s[:mid].rstrip() + ellipsis
                        if _calc_text_w(cand, fobj, fs) <= max_w:
                            best = cand
                            low = mid + 1
                        else:
                            high = mid - 1
                    return best if best else ellipsis

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
                                cur_fname = tbl_hdr_fname if is_hdr else tbl_reg_fname
                                cur_fpath = tbl_hdr_font_path if is_hdr else tbl_reg_font_path
                                cur_fobj = hdr_font_obj if is_hdr else reg_font_obj
                                cur_col = hdr_text_rgb if is_hdr else text_rgb

                                avail_w = max(6.0, cell_w - 7.0)
                                avail_h = max(6.0, cell_h - 4.0)
                                fit_fs = base_fs

                                raw_lines = [l.strip() for l in txt.split("\n") if l.strip()]
                                if not raw_lines:
                                    continue

                                # Font boyutunu hücreye uyacak şekilde dinamik ölçeklendir (min 4.0 pt)
                                max_len = max((_calc_text_w(l, cur_fobj, fit_fs) for l in raw_lines), default=0.0)
                                if max_len > avail_w:
                                    fit_fs = max(4.0, fit_fs * (avail_w / max_len))

                                total_text_h = len(raw_lines) * (fit_fs * 1.25)
                                if total_text_h > avail_h:
                                    fit_fs = max(4.0, fit_fs * (avail_h / total_text_h))

                                line_h = fit_fs * 1.25
                                max_lines = max(1, int(avail_h // line_h))

                                # Tek satır metin hücreye sığmıyor ve dikey alan yetiyorsa akıllı sözcük sarma (word wrap)
                                lines = []
                                if len(raw_lines) == 1 and max_lines > 1 and _calc_text_w(raw_lines[0], cur_fobj, fit_fs) > avail_w:
                                    words = raw_lines[0].split()
                                    cur_line = ""
                                    for w in words:
                                        cand = f"{cur_line} {w}".strip() if cur_line else w
                                        if _calc_text_w(cand, cur_fobj, fit_fs) <= avail_w:
                                            cur_line = cand
                                        else:
                                            if cur_line:
                                                lines.append(cur_line)
                                                cur_line = w
                                            else:
                                                lines.append(w)
                                                cur_line = ""
                                            if len(lines) >= max_lines:
                                                break
                                    if cur_line and len(lines) < max_lines:
                                        lines.append(cur_line)
                                    if not lines:
                                        lines = raw_lines[:max_lines]
                                else:
                                    lines = raw_lines[:max_lines]

                                # Satır genişliği sınırı aşıyorsa AuraPDF UI'daki gibi elide et (...)
                                final_lines = []
                                for idx, l in enumerate(lines):
                                    if _calc_text_w(l, cur_fobj, fit_fs) > avail_w:
                                        elided = _elide_line(l, cur_fobj, fit_fs, avail_w)
                                        final_lines.append(elided)
                                    else:
                                        final_lines.append(l)

                                total_block_h = len(final_lines) * line_h
                                start_y = cy + (cell_h - total_block_h) / 2.0 + fit_fs * 0.85

                                tbl_align = str(d.get("alignment", "center")).lower()
                                cell_alignments = d.get("cell_alignments", [])
                                cell_align = tbl_align
                                if isinstance(cell_alignments, list) and r < len(cell_alignments) and c < len(cell_alignments[r]) and cell_alignments[r][c]:
                                    cell_align = str(cell_alignments[r][c]).lower()

                                for idx, l in enumerate(final_lines):
                                    calc_len = _calc_text_w(l, cur_fobj, fit_fs)

                                    if cell_align == "left":
                                        lx = cx + 3.5
                                    elif cell_align == "right":
                                        lx = cx + max(3.5, cell_w - calc_len - 3.5)
                                    else:
                                        lx = cx + (cell_w - calc_len) / 2.0

                                    # Sınır dışına taşmayı önlemek için güvenli kenar sınırlaması
                                    lx = max(cx + 1.5, min(lx, cx + max(1.5, cell_w - calc_len - 1.5)))
                                    ly = start_y + idx * line_h

                                    # Dikeyde aşırı taşmayı engelle
                                    if ly > (cy + cell_h + fit_fs * 0.5):
                                        continue

                                    vis_pt = fitz.Point(lx, ly)
                                    pdf_pt = vis_pt * page.derotation_matrix

                                    try:
                                        page.insert_text(pdf_pt, l, fontname=cur_fname, fontfile=cur_fpath,
                                                         fontsize=fit_fs, color=cur_col, rotate=page.rotation)
                                    except Exception:
                                        try:
                                            page.insert_text(pdf_pt, l, fontname=cur_fname, fontsize=fit_fs,
                                                             color=cur_col, rotate=page.rotation)
                                        except Exception:
                                            page.insert_text(pdf_pt, l, fontname="helv", fontsize=fit_fs,
                                                             color=cur_col, rotate=page.rotation)
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

                scale = 3.0
                bw = int(round(a_w * scale))
                bh = int(round(a_h * scale))
                badge_pix = QPixmap(bw, bh)
                badge_pix.fill(Qt.GlobalColor.transparent)
                bp = QPainter(badge_pix)
                bp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                bp.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

                # 1. Koyu cam / degrade arka plan
                grad = QLinearGradient(0, 0, bw, bh)
                grad.setColorAt(0.0, QColor("#1e1b4b"))
                grad.setColorAt(1.0, QColor("#0f172a"))
                bp.setPen(QPen(QColor("#6366f1"), 1.8 * scale))
                bp.setBrush(QBrush(grad))
                bp.drawRoundedRect(QRectF(1.0 * scale, 1.0 * scale, bw - 2.0 * scale, bh - 2.0 * scale), 8.0 * scale, 8.0 * scale)

                # 2. Oynat (Play) butonu
                btn_d = min(32.0 * scale, max(20.0 * scale, bh - 12.0 * scale))
                btn_y = (bh - btn_d) / 2.0
                btn_x = 8.0 * scale
                btn_r = QRectF(btn_x, btn_y, btn_d, btn_d)
                bp.setPen(Qt.PenStyle.NoPen)
                bp.setBrush(QBrush(QColor("#6366f1")))
                bp.drawEllipse(btn_r)

                # Beyaz üçgen oynat simgesi
                poly = QPainterPath()
                cx_btn = btn_r.center().x()
                cy_btn = btn_r.center().y()
                s_icon = btn_d * 0.35
                poly.moveTo(cx_btn - s_icon * 0.5, cy_btn - s_icon * 0.8)
                poly.lineTo(cx_btn + s_icon * 0.8, cy_btn)
                poly.lineTo(cx_btn - s_icon * 0.5, cy_btn + s_icon * 0.8)
                poly.closeSubpath()
                bp.fillPath(poly, QBrush(QColor("#ffffff")))

                # 3. Dinamik başlık ve süre metinleri (Taşma korumalı)
                text_x = btn_r.right() + 8.0 * scale
                avail_w = max(20.0 * scale, bw - text_x - 8.0 * scale)
                title_txt = str(d.get("title", "Ses Kaydı"))
                dur_sec = float(d.get("duration_sec", 0.0))
                mins = int(dur_sec // 60)
                secs = int(dur_sec % 60)
                dur_str = f"{mins:02d}:{secs:02d}" if dur_sec > 0 else LanguageManager.tr("audio_record_title", default="Ses Kaydı")

                title_font = QFont("Arial", int(round(10 * scale)), QFont.Weight.Bold)
                fm_title = QFontMetrics(title_font)
                elided_title = fm_title.elidedText(title_txt, Qt.TextElideMode.ElideRight, int(avail_w))

                dur_font = QFont("Arial", int(round(8 * scale)))
                fm_dur = QFontMetrics(dur_font)
                elided_dur = fm_dur.elidedText(dur_str, Qt.TextElideMode.ElideRight, int(avail_w))

                if bh >= 40.0 * scale:
                    bp.setFont(title_font)
                    bp.setPen(QColor("#f8fafc"))
                    bp.drawText(QRectF(text_x, btn_r.top(), avail_w, btn_r.height() * 0.55),
                                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

                    bp.setFont(dur_font)
                    bp.setPen(QColor("#94a3b8"))
                    bp.drawText(QRectF(text_x, btn_r.top() + btn_r.height() * 0.5, avail_w, btn_r.height() * 0.5),
                                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_dur)
                else:
                    bp.setFont(QFont("Arial", int(round(9 * scale)), QFont.Weight.Bold))
                    bp.setPen(QColor("#f8fafc"))
                    comb = f"{elided_title} ({dur_str})"
                    bp.drawText(QRectF(text_x, 0, avail_w, bh),
                                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, comb)
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
                        annot = page.add_file_annot(card_rect.tl, d["audio_bytes"], filename=filename, desc=d.get("title", "Ses Kaydı"))
                        if annot:
                            annot.set_opacity(0.0)
                            annot.set_flags(annot.flags | fitz.PDF_ANNOT_NO_VIEW)
                            annot.update()
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

        # 3. Yeni eklenen içerik akışlarını AuraPDF Çizim Akışı olarak etiketle
        for p_idx in range(len(target_doc)):
            try:
                current_xrefs = target_doc[p_idx].get_contents()
                old_xrefs = set(before_xrefs.get(p_idx, []))
                for x in current_xrefs:
                    if x not in old_xrefs:
                        st = target_doc.xref_stream(x)
                        if st and not st.startswith(b'% AuraPDF Drawing Stream'):
                            target_doc.update_stream(x, b'% AuraPDF Drawing Stream\n' + st)
            except Exception:
                pass

        # 4. Tüm çizim, resim, tablo ve medya nesnelerini aurapdf_drawings.json olarak belgeye göm
        try:
            serialized_list = []
            for d in self.drawings:
                s = self._serialize_drawing_record(d)
                if s:
                    if page_mapping is not None:
                        orig_p = s.get("page", 0)
                        if orig_p in page_mapping:
                            s["page"] = page_mapping.index(orig_p)
                        else:
                            continue
                    serialized_list.append(s)
            def _json_safe(obj):
                if isinstance(obj, QColor):
                    return [round(obj.redF(), 4), round(obj.greenF(), 4), round(obj.blueF(), 4)]
                if hasattr(obj, 'toTuple'):
                    return obj.toTuple()
                if hasattr(obj, 'x') and hasattr(obj, 'y'):
                    return [obj.x(), obj.y()]
                return str(obj)

            raw_data = json.dumps({"version": 1, "drawings": serialized_list}, ensure_ascii=False, default=_json_safe).encode('utf-8')
            if hasattr(target_doc, 'embfile_add'):
                target_doc.embfile_add(
                    "aurapdf_drawings.json",
                    raw_data,
                    filename="aurapdf_drawings.json",
                    ufilename="aurapdf_drawings.json",
                    desc="AuraPDF Drawings and Media Metadata"
                )
        except Exception as e:
            print("Error embedding aurapdf_drawings.json:", e)

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
        if getattr(self, 'active_text_item', None):
            try:
                self.active_text_item.finish_editing()
            except Exception:
                pass

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
        if "rects" in d:
            s["rects"] = [list(r) for r in d["rects"]]
        if "markup_type" in d:
            s["markup_type"] = d["markup_type"]
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
        if "rects" in state:
            d["rects"] = [list(r) for r in state["rects"]]
        if "markup_type" in state:
            d["markup_type"] = state["markup_type"]

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
        if deleted_measurements and hasattr(self, 'view') and self.view:
            self.view.viewport().update()

        # 2. Sahnedeki seçili tüm nesneleri (Resim, GIF, Tablo, Ses/Video, Metin Kutusu vb.) sil
        scene_selected = list(self.scene.selectedItems()) if self.scene else []
        handled_items = set()
        for item in scene_selected:
            if item in handled_items:
                continue
            handled_items.add(item)
            if hasattr(item, 'delete_self'):
                try:
                    item.delete_self()
                except Exception:
                    pass
            elif hasattr(item, 'parent_text_item') and hasattr(item.parent_text_item, 'delete_self'):
                try:
                    item.parent_text_item.delete_self()
                    handled_items.add(item.parent_text_item)
                except Exception:
                    pass

        # 3. Eğer aktif seçili metin kutusu varsa ve kullanıcı içinde harf yazmıyorsa sil
        active_txt = getattr(self, 'active_text_item', None)
        if active_txt and active_txt not in handled_items:
            flags = getattr(active_txt, 'textInteractionFlags', lambda: Qt.TextInteractionFlag.NoTextInteraction)()
            if not (flags & Qt.TextInteractionFlag.TextEditorInteraction) or active_txt.isSelected():
                try:
                    active_txt.delete_self()
                    handled_items.add(active_txt)
                except Exception:
                    pass

        # 4. Seçili çizim ve serbest el notlarını sil (Lasso seçimleri)
        if self.selected_drawings:
            deleted = []
            for item_data in list(self.selected_drawings):
                if item_data in self.drawings:
                    self.drawings.remove(item_data)
                    deleted.append(item_data)
                    if item_data.get("item_ref"):
                        try:
                            self.scene.removeItem(item_data["item_ref"])
                        except Exception:
                            pass

            self.clear_selection()
            if deleted:
                self.push_undo_action({"type": "erase", "deleted_items": deleted})
                self.notify_drawings_changed()

        if hasattr(self, 'view') and self.view:
            self.view.viewport().update()

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
        if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
            sidebar = self.main_window.modern_right_sidebar
            if getattr(sidebar, 'current_panel', '') == 'thumbnails' and sidebar.isVisible():
                if page_idx is not None:
                    sidebar.update_thumbnail(page_idx)
                else:
                    sidebar.update_all_thumbnails()

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

    def clear_page_drawings(self, page_idx: int):
        """Yalnızca belirtilen indeksteki sayfaya ait tüm çizim ve öğeleri temizler."""
        if not self.drawings:
            return
        deleted = [d for d in self.drawings if d.get("page", 0) == page_idx]
        if not deleted:
            return
        for d in deleted:
            if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                self.scene.removeItem(d["item_ref"])
        self.drawings = [d for d in self.drawings if d.get("page", 0) != page_idx]
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
            items = action["data"] if isinstance(action["data"], list) else [action["data"]]
            for item_data in items:
                if item_data in self.drawings:
                    self.drawings.remove(item_data)
                if item_data.get("item_ref") and item_data["item_ref"].scene() == self.scene:
                    self.scene.removeItem(item_data["item_ref"])
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
            if hasattr(self, '_render_worker') and self._render_worker:
                try:
                    if self._render_worker.isRunning():
                        self._render_worker.abort()
                        self._render_worker.wait()
                except Exception:
                    pass
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
                self.notify_thumbnails_updated(curr_p if len(self.doc) > 0 else None)
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
            items = action["data"] if isinstance(action["data"], list) else [action["data"]]
            for item_data in items:
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
            if hasattr(self, '_render_worker') and self._render_worker:
                try:
                    if self._render_worker.isRunning():
                        self._render_worker.abort()
                        self._render_worker.wait()
                except Exception:
                    pass
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
                self.notify_thumbnails_updated(curr_p if len(self.doc) > 0 else None)
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

        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx
        old_to_new = {old: new for new, old in enumerate(new_order)}
        old_order = [old_to_new[i] for i in range(len(new_order))]

        if order_changed:
            self._apply_page_order(new_order)
        if rotations is not None and len(rotations) == len(self.doc):
            for i, rot in enumerate(rotations):
                if rot is not None:
                    self.doc[i].set_rotation(rot % 360)
            if self.isVisible():
                self.render_pages_init()
                self.rerender_visible_pages()
            if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
                if self.main_window.thumbnails_dock.isVisible():
                    self.main_window.thumbnails_dock.load_thumbnails_lazy()
                    self.main_window.thumbnails_dock.select_page(self.current_page_idx)

        if push_undo:
            action = {
                "type": "reorder_pages",
                "old_order": old_order,
                "new_order": list(new_order),
                "old_drawings": old_drawings,
                "old_page": old_page,
                "new_drawings": [dict(d) for d in self.drawings],
                "new_page": self.current_page_idx,
            }
            self.push_undo_action(action)
        self.set_modified(True)

    def delete_page(self, page_idx: int):
        if self.doc is None or len(self.doc) == 0:
            return
        if not (0 <= page_idx < len(self.doc)):
            return

        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        self.doc.delete_page(page_idx)
        if hasattr(self, '_page_text_blocks_cache'):
            self._page_text_blocks_cache.clear()
        self.direct_edit_hover_item = None
        self.direct_edit_editor = None

        new_bytes = b""
        try:
            if len(self.doc) > 0:
                new_bytes = self.doc.tobytes()
        except Exception:
            new_bytes = b""

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
        self.notify_thumbnails_updated(self.current_page_idx if len(self.doc) > 0 else None)

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

    def _draw_page_template(self, new_p, width: Optional[float] = None, height: Optional[float] = None, style: str = "blank"):
        if not style or style == "blank" or new_p is None:
            return

        # Sayfanın gerçek görünür boyutlarını doğrudan new_p.rect üzerinden al
        # Bu sayede dikey, yatay (landscape) veya rotasyonlu sayfalarda (90, 270 vb.) şablon asla taşmaz veya kesilmez
        if hasattr(new_p, 'rect') and new_p.rect.width > 0 and new_p.rect.height > 0:
            w = float(new_p.rect.width)
            h = float(new_p.rect.height)
        else:
            w = float(width) if (width and width > 0) else 595.32
            h = float(height) if (height and height > 0) else 841.92

        if style in ("lined", "lines"):
            margin_x = 36.0
            top_margin = 54.0
            bottom_margin = 42.0
            step = 24.0
            num_lines = max(1, int((h - top_margin - bottom_margin) / step))
            start_y = top_margin
            
            shape = new_p.new_shape()
            for i in range(num_lines):
                y = start_y + i * step
                shape.draw_line(fitz.Point(margin_x, y), fitz.Point(w - margin_x, y))
            shape.finish(color=(0.80, 0.82, 0.85), width=0.75)
            shape.commit()

        elif style == "grid":
            step = 20.0
            min_margin_x = 32.0
            min_margin_y = 32.0
            num_x = max(1, int((w - 2 * min_margin_x) / step))
            num_y = max(1, int((h - 2 * min_margin_y) / step))
            grid_w = num_x * step
            grid_h = num_y * step
            start_x = (w - grid_w) / 2.0
            start_y = (h - grid_h) / 2.0
            end_x = start_x + grid_w
            end_y = start_y + grid_h

            shape = new_p.new_shape()
            # Dikey çizgiler (tam sınırlar arasında)
            for i in range(num_x + 1):
                x = start_x + i * step
                shape.draw_line(fitz.Point(x, start_y), fitz.Point(x, end_y))
            # Yatay çizgiler (tam sınırlar arasında)
            for j in range(num_y + 1):
                y = start_y + j * step
                shape.draw_line(fitz.Point(start_x, y), fitz.Point(end_x, y))
            shape.finish(color=(0.85, 0.86, 0.88), width=0.65)
            shape.commit()

        elif style == "dotted":
            step = 20.0
            min_margin_x = 32.0
            min_margin_y = 32.0
            num_x = max(1, int((w - 2 * min_margin_x) / step))
            num_y = max(1, int((h - 2 * min_margin_y) / step))
            grid_w = num_x * step
            grid_h = num_y * step
            start_x = (w - grid_w) / 2.0
            start_y = (h - grid_h) / 2.0

            shape = new_p.new_shape()
            for i in range(num_x + 1):
                x = start_x + i * step
                for j in range(num_y + 1):
                    y = start_y + j * step
                    shape.draw_circle(fitz.Point(x, y), 0.75)
            # Yalnızca dolgu (stroke yok); böylece Edge, Chrome ve Acrobat'ta kenarlık/hale oluşmaz
            shape.finish(color=None, fill=(0.60, 0.62, 0.66))
            shape.commit()

        elif style == "cornell":
            margin_x = 36.0
            cue_w = max(110.0, min(180.0, w * 0.28))
            cue_x = margin_x + cue_w
            header_y = 65.0
            footer_y = h - 75.0
            step = 22.0

            shape = new_p.new_shape()
            # Dikey ipucu sütunu çizgisi
            shape.draw_line(fitz.Point(cue_x, header_y), fitz.Point(cue_x, footer_y))
            # Üst başlık çizgisi
            shape.draw_line(fitz.Point(margin_x, header_y), fitz.Point(w - margin_x, header_y))
            # Alt özet çizgisi
            shape.draw_line(fitz.Point(margin_x, footer_y), fitz.Point(w - margin_x, footer_y))
            shape.finish(color=(0.88, 0.52, 0.52), width=1.5)
            shape.commit()

            # Sağ gövde çizgileri
            shape2 = new_p.new_shape()
            num_lines = max(1, int((footer_y - header_y - 10) / step))
            for i in range(1, num_lines + 1):
                y = header_y + i * step
                if y < footer_y - 4:
                    shape2.draw_line(fitz.Point(cue_x + 4, y), fitz.Point(w - margin_x, y))
            shape2.finish(color=(0.85, 0.86, 0.88), width=0.65)
            shape2.commit()

        elif style in ("music", "staff"):
            margin_x = 36.0
            staff_h = 4 * 7.5  # 30 pt
            gap = 48.0
            total_block = staff_h + gap
            margin_y = 50.0
            available_h = h - 2 * margin_y
            num_staves = max(1, int((available_h + gap) / total_block))
            total_music_h = num_staves * staff_h + (num_staves - 1) * gap
            start_y = (h - total_music_h) / 2.0

            shape = new_p.new_shape()
            for s_idx in range(num_staves):
                top_y = start_y + s_idx * total_block
                for l_idx in range(5):
                    ly = top_y + l_idx * 7.5
                    shape.draw_line(fitz.Point(margin_x, ly), fitz.Point(w - margin_x, ly))
            shape.finish(color=(0.32, 0.34, 0.38), width=0.75)
            shape.commit()

        elif style in ("dark", "black"):
            # 1. Tam sayfa koyu arka plan
            bg_shape = new_p.new_shape()
            bg_shape.draw_rect(fitz.Rect(0, 0, w, h))
            bg_shape.finish(color=None, fill=(0.09, 0.10, 0.12))
            bg_shape.commit()

            # 2. Gövde çizgileri
            margin_x = 36.0
            top_margin = 54.0
            bottom_margin = 42.0
            step = 24.0
            num_lines = max(1, int((h - top_margin - bottom_margin) / step))
            start_y = top_margin
            lines_shape = new_p.new_shape()
            for i in range(num_lines):
                y = start_y + i * step
                lines_shape.draw_line(fitz.Point(margin_x, y), fitz.Point(w - margin_x, y))
            lines_shape.finish(color=(0.20, 0.22, 0.26), width=0.75)
            lines_shape.commit()

        elif style == "cover":
            # 1. Kapak arka planı
            bg_shape = new_p.new_shape()
            bg_shape.draw_rect(fitz.Rect(0, 0, w, h))
            bg_shape.finish(color=None, fill=(0.12, 0.15, 0.20))
            bg_shape.commit()

            # 2. Zarif çift çerçeve
            frame_margin = 32.0
            frame_shape = new_p.new_shape()
            frame_shape.draw_rect(fitz.Rect(frame_margin, frame_margin, w - frame_margin, h - frame_margin))
            frame_shape.finish(color=(0.88, 0.76, 0.48), width=2.0)
            frame_shape.commit()

            inner_m = frame_margin + 6.0
            frame2 = new_p.new_shape()
            frame2.draw_rect(fitz.Rect(inner_m, inner_m, w - inner_m, h - inner_m))
            frame2.finish(color=(0.88, 0.76, 0.48), width=0.6)
            frame2.commit()

    def notify_thumbnails_updated(self, target_page: Optional[int] = None):
        """Sağ çekmecedeki modern sayfa önizlemelerini ve varsa kenetlenmiş dock'u günceller."""
        if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
            try:
                sidebar = self.main_window.modern_right_sidebar
                if sidebar.isVisible() and getattr(sidebar, 'current_panel', '') == 'thumbnails':
                    sidebar.load_thumbnails()
                    if target_page is not None and self.doc and len(self.doc) > 0 and 0 <= target_page < len(self.doc):
                        sidebar.select_page(target_page)
                else:
                    sidebar.is_loaded = False
            except Exception:
                pass

        if hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            try:
                dock = self.main_window.thumbnails_dock
                if dock.isVisible():
                    dock.load_thumbnails_lazy()
                    if target_page is not None and self.doc and len(self.doc) > 0 and 0 <= target_page < len(self.doc):
                        dock.select_page(target_page)
                else:
                    dock.is_loaded = False
            except Exception:
                pass

        if hasattr(self.main_window, 'organize_workspace') and self.main_window.organize_workspace and self.main_window.organize_workspace.isVisible():
            try:
                self.main_window.organize_workspace.load_document(force=True)
            except Exception:
                pass

    def duplicate_page(self, page_idx: int) -> bool:
        """Belirtilen sayfayı kopyalar ve ardına ekler (tüm çizimler ve ek açıklamalar dahil)."""
        if self.doc is None or not (0 <= page_idx < len(self.doc)):
            return False

        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        if getattr(self, 'active_text_item', None):
            try:
                if hasattr(self.active_text_item, 'finish_editing'):
                    self.active_text_item.finish_editing()
            except Exception:
                pass

        try:
            old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
            old_drawings = [dict(d) for d in self.drawings]
            old_page = self.current_page_idx

            insert_idx = page_idx + 1
            temp_doc = fitz.open()
            temp_doc.insert_pdf(self.doc, from_page=page_idx, to_page=page_idx)
            self.doc.insert_pdf(temp_doc, start_at=insert_idx)
            temp_doc.close()

            # Sayfa üzerindeki tüm çizimleri ve ek açıklamaları yeni sayfaya birebir kopyala
            duplicated_drawings = []
            if hasattr(self, 'drawings') and self.drawings:
                for d in self.drawings:
                    p = d.get("page", 0)
                    if p > page_idx:
                        d["page"] = p + 1
                    elif p == page_idx:
                        new_d = dict(d)
                        new_d["page"] = insert_idx
                        new_d["id"] = uuid.uuid4().hex[:12]
                        new_d["item_ref"] = None
                        if "points" in new_d and isinstance(new_d["points"], list):
                            new_d["points"] = [pt for pt in new_d["points"]]
                        if "arrow_head" in new_d and isinstance(new_d["arrow_head"], list):
                            new_d["arrow_head"] = [pt for pt in new_d["arrow_head"]]
                        if "color" in new_d and isinstance(new_d["color"], QColor):
                            new_d["color"] = QColor(new_d["color"])
                        duplicated_drawings.append(new_d)

                self.drawings.extend(duplicated_drawings)

            try:
                new_doc_bytes = self.doc.tobytes()
            except Exception:
                new_doc_bytes = b""

            self.set_modified(True)
            self.render_all_pages()
            self.go_to_page(insert_idx)

            if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
            if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                self.main_window.txt_page.setText(str(insert_idx + 1))

            self.notify_thumbnails_updated(insert_idx)

            self.push_undo_action({
                "type": "insert_blank_page",
                "old_bytes": old_bytes,
                "old_drawings": old_drawings,
                "old_page": old_page,
                "new_bytes": new_doc_bytes,
                "new_drawings": [dict(d) for d in self.drawings],
                "new_page": insert_idx,
                "insert_idx": insert_idx
            })
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def insert_pdf_at(self, pdf_path: str, after_page: Optional[int] = None, rerender: bool = True, notify_thumb: bool = True) -> int:
        """Harici bir PDF dosyasının tüm sayfalarını belirtilen sayfanın ardına güvenle ekler."""
        if self.doc is None or getattr(self.doc, 'is_closed', False) or not os.path.exists(pdf_path):
            return 0

        # Arka plan render worker'i ve render zamanlayicisini once durdur ve bekle (MuPDF islem guvenligi)
        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        # Aktif duzenleme veya metin kutusu varsa guvenle sonlandir
        if getattr(self, 'active_text_item', None):
            try:
                if hasattr(self.active_text_item, 'finish_editing'):
                    self.active_text_item.finish_editing()
                elif hasattr(self.active_text_item, 'toPlainText'):
                    if self.active_text_item.toPlainText().strip():
                        self.commit_inline_text(self.active_text_item)
                    else:
                        self.scene.removeItem(self.active_text_item)
                        self.active_text_item = None
                elif hasattr(self.active_text_item, 'clearFocus'):
                    self.active_text_item.clearFocus()
                    self.active_text_item = None
            except Exception:
                self.active_text_item = None

        if hasattr(self, '_page_text_blocks_cache'):
            try:
                self._page_text_blocks_cache.clear()
            except Exception:
                pass

        if after_page is None or after_page < 0:
            if after_page is None:
                curr_idx = getattr(self, 'current_page_idx', 0)
                after_page = curr_idx if (curr_idx is not None and curr_idx >= 0) else (len(self.doc) - 1)
            else:
                after_page = -1

        insert_idx = max(0, min(after_page + 1, len(self.doc)))

        try:
            old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
        except Exception:
            old_bytes = b""
        old_drawings = [dict(d) for d in self.drawings]
        old_page = getattr(self, 'current_page_idx', 0)

        try:
            ext_doc = fitz.open(pdf_path)
            if ext_doc.is_encrypted:
                from src.ui.dialogs.toolbox_dialogs import extract_pdf_hint, PDFPasswordDialog
                from PyQt6.QtWidgets import QDialog
                hint = extract_pdf_hint(pdf_path)
                authenticated = False
                while ext_doc.is_encrypted and not authenticated:
                    dlg = PDFPasswordDialog(self.main_window, pdf_path, hint)
                    if dlg.exec() != QDialog.DialogCode.Accepted:
                        ext_doc.close()
                        return 0
                    pw = dlg.get_password()
                    if ext_doc.authenticate(pw) > 0:
                        authenticated = True
                    else:
                        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                            self.main_window.statusBar().showMessage(LanguageManager.tr("wrong_password"), 3000)

            page_count = len(ext_doc)
            if page_count == 0:
                ext_doc.close()
                return 0

            self.doc.insert_pdf(ext_doc, start_at=insert_idx)
            ext_doc.close()
        except Exception as e:
            print(f"[Warning] Error opening or inserting PDF '{pdf_path}': {e}")
            return 0

        for d in self.drawings:
            if d.get("page", 0) >= insert_idx:
                d["page"] += page_count

        self.pre_watermark_bytes = None

        # Doküman baytlarını render worker başlamadan hemen önce, arka plan iş parçacığı çakışması olmadan güvenle al
        try:
            new_doc_bytes = self.doc.tobytes()
        except Exception:
            new_doc_bytes = b""

        if rerender:
            self.render_pages_init()
            self.rerender_visible_pages()
            self.go_to_page(insert_idx)

            if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
            if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                self.main_window.txt_page.setText(str(insert_idx + 1))

            if notify_thumb:
                self.notify_thumbnails_updated(insert_idx)

        self.push_undo_action({
            "type": "reorder_pages",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": new_doc_bytes,
            "new_drawings": [dict(d) for d in self.drawings],
            "new_page": insert_idx,
            "new_order": list(range(len(self.doc)))
        })
        self.set_modified(True)
        return page_count

    def insert_blank_page(self, after_page: Optional[int] = None, width: Optional[float] = None, height: Optional[float] = None, style: str = "blank", rerender: bool = True, notify_thumb: bool = True):
        """Mevcut dokümana belirtilen sayfanın ardına boş bir sayfa ekler.
        Mevcut sayfa boyut ve rotasyonuyla birebir uyumlu sayfa oluşturur."""
        if self.doc is None or getattr(self.doc, 'is_closed', False):
            return
        if after_page is None:
            after_page = self.current_page_idx
        insert_idx = max(0, min(after_page + 1, len(self.doc)))

        # Arka plan render worker'i ve render zamanlayicisini once durdur ve bekle (MuPDF islem guvenligi)
        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        # Aktif duzenleme veya metin kutusu varsa guvenle sonlandir
        if getattr(self, 'active_text_item', None):
            try:
                if hasattr(self.active_text_item, 'finish_editing'):
                    self.active_text_item.finish_editing()
                elif hasattr(self.active_text_item, 'toPlainText'):
                    if self.active_text_item.toPlainText().strip():
                        self.commit_inline_text(self.active_text_item)
                    else:
                        self.scene.removeItem(self.active_text_item)
                        self.active_text_item = None
                elif hasattr(self.active_text_item, 'clearFocus'):
                    self.active_text_item.clearFocus()
                    self.active_text_item = None
            except Exception:
                self.active_text_item = None

        if hasattr(self, 'drawings') and self.drawings:
            for d in self.drawings:
                it = d.get('item_ref')
                if it and hasattr(it, 'finish_cell_editing'):
                    try:
                        it.finish_cell_editing()
                    except Exception:
                        pass

        if hasattr(self, '_page_text_blocks_cache'):
            try:
                self._page_text_blocks_cache.clear()
            except Exception:
                pass

        # Mevcut sayfalarla uyumlu boyut ve gorsel yonu belirle
        ref_rot = 0
        if len(self.doc) > 0:
            ref_idx = max(0, min(after_page, len(self.doc) - 1))
            try:
                ref_page = self.doc[ref_idx]
                if width is None or height is None:
                    # Referans sayfanin gercek mediabox ve rotasyonunu birebir al (tam uyumlu sayfa)
                    width = float(ref_page.mediabox.width)
                    height = float(ref_page.mediabox.height)
                    ref_rot = ref_page.rotation
                else:
                    ref_rot = 0
            except Exception:
                ref_rot = 0

        if width is None or width <= 0:
            width = 595.32
        if height is None or height <= 0:
            height = 841.92

        try:
            old_bytes = self.doc.tobytes() if len(self.doc) > 0 else b""
        except Exception:
            old_bytes = b""
        old_drawings = [dict(d) for d in self.drawings]
        old_page = self.current_page_idx

        # Yeni bos sayfa ekle
        new_p = self.doc.new_page(pno=insert_idx, width=width, height=height)
        if ref_rot:
            try:
                new_p.set_rotation(ref_rot)
            except Exception:
                pass

        if style and style != "blank":
            try:
                self._draw_page_template(new_p, width, height, style)
            except Exception as e:
                print(f"[Warning] Error drawing page template: {e}")

        # Cizim indekslerini guncelle
        for d in self.drawings:
            if d.get("page", 0) >= insert_idx:
                d["page"] += 1

        self.pre_watermark_bytes = None

        # Doküman baytlarını render worker başlamadan hemen önce, arka plan iş parçacığı çakışması olmadan güvenle al
        try:
            new_doc_bytes = self.doc.tobytes()
        except Exception:
            new_doc_bytes = b""

        if rerender:
            self.render_pages_init()
            self.rerender_visible_pages()
            self.go_to_page(insert_idx)

            if hasattr(self.main_window, 'lbl_total') and self.main_window.lbl_total:
                self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
            if hasattr(self.main_window, 'txt_page') and self.main_window.txt_page:
                self.main_window.txt_page.setText(str(insert_idx + 1))

            if notify_thumb:
                self.notify_thumbnails_updated(insert_idx)

        self.push_undo_action({
            "type": "insert_blank_page",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": new_doc_bytes,
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

        # Arka plan render worker'i ve render zamanlayicisini once durdur ve bekle (MuPDF islem guvenligi)
        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        if getattr(self, 'active_text_item', None):
            try:
                if hasattr(self.active_text_item, 'finish_editing'):
                    self.active_text_item.finish_editing()
            except Exception:
                pass

        try:
            old_bytes = self.doc.tobytes()
        except Exception:
            old_bytes = b""
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
                try:
                    new_p.set_rotation(rot)
                except Exception:
                    pass
            if new_style and new_style != "blank":
                try:
                    self._draw_page_template(new_p, w, h, new_style)
                except Exception:
                    pass

            # Eski sayfayı sil (böylece new_p sayfa indeksini p yapar)
            self.doc.delete_page(p)

        try:
            new_bytes = self.doc.tobytes()
        except Exception:
            new_bytes = b""

        self.hide_managed_annotations()
        self.render_pages_init()
        self.rerender_visible_pages()
        curr_p = max(0, min(self.current_page_idx, len(self.doc) - 1))
        self.go_to_page(curr_p)
        self.notify_thumbnails_updated(curr_p)

        self.push_undo_action({
            "type": "change_page_style",
            "old_bytes": old_bytes,
            "old_drawings": old_drawings,
            "old_page": old_page,
            "new_bytes": new_bytes,
            "new_drawings": [dict(d) for d in self.drawings],
            "new_page": curr_p,
            "style": new_style,
            "all_pages": all_pages
        })
        self.set_modified(True)

    def _apply_page_order(self, order: List[int]):
        # Arka plan render worker'i varsa once durdur ve bekle (MuPDF islem guvenligi)
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait() # Indefinite wait guarantees worker stops before doc mutation
            except Exception:
                pass

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

        is_tab_visible = self.isVisible() and (
            self.main_window and hasattr(self.main_window, 'central_stack')
            and self.main_window.central_stack.currentWidget() in (getattr(self.main_window, 'tab_widget', None), getattr(self.main_window, 'document_splitter', None))
        )
        if is_tab_visible:
            self.render_pages_init()
            self.rerender_visible_pages()

        new_curr = old_to_new.get(prev_current_page, min(prev_current_page, len(self.doc) - 1))
        new_curr = max(0, min(new_curr, len(self.doc) - 1))
        self.current_page_idx = new_curr
        if is_tab_visible:
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

        line_style = d.get("line_style", "solid")

        # Pürüzsüz yüksek çözünürlüklü quadratik Bezier vektör yolu
        p_lead = build_smooth_path(pts)

        # 2. Ok ucu desteği (Arrow head)
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

        pen_style = Qt.PenStyle.SolidLine
        dash_pattern = None
        if line_style == "dash":
            pen_style = Qt.PenStyle.CustomDashLine
            dash_pattern = [2.2, 1.5]
        elif line_style == "dot":
            pen_style = Qt.PenStyle.CustomDashLine
            dash_pattern = [0.01, 1.9]
        elif line_style == "dashdot":
            pen_style = Qt.PenStyle.CustomDashLine
            dash_pattern = [2.2, 1.4, 0.01, 1.4]

        # 3 katmanlı zengin kurşun kalem grafit dokusu (vektörel ve kristal netlikte, pikselleşme yapmaz)
        col_fringe = QColor(base_col)
        col_fringe.setAlphaF(min(1.0, alpha_base * 0.28))
        pen_fringe = QPen(col_fringe, base_w * 1.35, pen_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if dash_pattern: pen_fringe.setDashPattern(dash_pattern)
        item_fringe = self.scene.addPath(p_lead, pen_fringe)
        group.addToGroup(item_fringe)

        col_lead = QColor(base_col)
        col_lead.setAlphaF(min(1.0, alpha_base * 0.72))
        pen_lead = QPen(col_lead, base_w, pen_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if dash_pattern: pen_lead.setDashPattern(dash_pattern)
        item_lead = self.scene.addPath(p_lead, pen_lead)
        group.addToGroup(item_lead)

        col_core = QColor(base_col)
        col_core.setAlphaF(min(1.0, alpha_base * 0.96))
        pen_core = QPen(col_core, max(0.6, base_w * 0.52), pen_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if dash_pattern: pen_core.setDashPattern(dash_pattern)
        item_core = self.scene.addPath(p_lead, pen_core)
        group.addToGroup(item_core)

        # Caching kapalı tutulur - böylece zoom yapıldığında pikseller esnemez, vektörel render edilir
        group.setCacheMode(QGraphicsItemGroup.CacheMode.NoCache)
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

            path = build_smooth_path(pts)

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
        elif d["type"] == "text_markup":
            if d.get("item_ref") and d["item_ref"].scene() == self.scene:
                try:
                    self.scene.removeItem(d["item_ref"])
                except Exception:
                    pass
                d["item_ref"] = None

            scale = self.base_render_dpi
            markup_type = d.get("markup_type", "highlight")
            rects = d.get("rects", [])
            col = d.get("color", (1.0, 0.9, 0.2))
            alpha = float(d.get("alpha", 0.38 if markup_type == "highlight" else 1.0))
            width = float(d.get("width", 2.0))

            if isinstance(col, QColor):
                qcolor = QColor(col)
                qcolor.setAlphaF(alpha)
            elif isinstance(col, (tuple, list)) and len(col) >= 3:
                qcolor = QColor.fromRgbF(float(col[0]), float(col[1]), float(col[2]), alpha)
            else:
                qcolor = QColor(255, 230, 0, int(alpha * 255))

            path = QPainterPath()
            if markup_type == "highlight":
                for r in rects:
                    sx = r[0] * scale + page_left
                    sy = r[1] * scale + page_top
                    sw = (r[2] - r[0]) * scale
                    sh = (r[3] - r[1]) * scale
                    path.addRect(QRectF(sx, sy, sw, sh))
                item = self.scene.addPath(path, QPen(Qt.PenStyle.NoPen), QBrush(qcolor))
            elif markup_type == "underline":
                pen = QPen(qcolor, max(1.5, width * scale * 0.7), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                for r in rects:
                    sx0 = r[0] * scale + page_left
                    sx1 = r[2] * scale + page_left
                    sy = (r[3] - 1.0) * scale + page_top
                    path.moveTo(sx0, sy)
                    path.lineTo(sx1, sy)
                item = self.scene.addPath(path, pen)
            elif markup_type == "strikeout":
                pen = QPen(qcolor, max(1.5, width * scale * 0.7), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                for r in rects:
                    sx0 = r[0] * scale + page_left
                    sx1 = r[2] * scale + page_left
                    sy = ((r[1] + r[3]) / 2.0) * scale + page_top
                    path.moveTo(sx0, sy)
                    path.lineTo(sx1, sy)
                item = self.scene.addPath(path, pen)
            else:
                return

            item.setZValue(5)
            item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            d["item_ref"] = item

    # --- Render & Zoom ---
    def render_pages_init(self):
        if self.doc is None: return

        # 1. Once arka plan render zamanlayici ve iscisini kesinlikle durdur ve bekle (MuPDF islem guvenligi)
        if hasattr(self, 'rerender_timer') and self.rerender_timer:
            try:
                self.rerender_timer.stop()
            except Exception:
                pass
        if hasattr(self, '_render_worker') and self._render_worker:
            try:
                if self._render_worker.isRunning():
                    self._render_worker.abort()
                    self._render_worker.wait()
            except Exception:
                pass

        # In-memory dokümanda ek açıklamaların get_pixmap ile çift çizilmesini önle
        MANAGED_TYPES = (
            fitz.PDF_ANNOT_INK,
            fitz.PDF_ANNOT_LINE,
            fitz.PDF_ANNOT_POLY_LINE,
            fitz.PDF_ANNOT_HIGHLIGHT,
            fitz.PDF_ANNOT_UNDERLINE,
            fitz.PDF_ANNOT_STRIKE_OUT,
            fitz.PDF_ANNOT_FREE_TEXT,
            fitz.PDF_ANNOT_POLYGON
        )
        for p in self.doc:
            try:
                for a in list(p.annots()):
                    if a.type[0] in MANAGED_TYPES and not (a.flags & fitz.PDF_ANNOT_IS_HIDDEN):
                        a.set_flags(a.flags | fitz.PDF_ANNOT_IS_HIDDEN)
                        a.update()
            except Exception:
                pass

        # In-memory dokümanda etiketli AuraPDF çizim/medya akışlarını sustur (temiz taban pixmap'i)
        for p in self.doc:
            try:
                for x in p.get_contents():
                    st = self.doc.xref_stream(x)
                    if st and b'% AuraPDF Drawing Stream' in st:
                        self.doc.update_stream(x, b"")
            except Exception:
                pass

        if getattr(self, 'active_text_item', None):
            try:
                if hasattr(self.active_text_item, 'finish_editing'):
                    self.active_text_item.finish_editing()
                elif hasattr(self.active_text_item, 'toPlainText'):
                    if self.active_text_item.toPlainText().strip():
                        self.commit_inline_text(self.active_text_item)
                    else:
                        self.scene.removeItem(self.active_text_item)
                        self.active_text_item = None
            except Exception:
                self.active_text_item = None

        self.laser_pointer_item = None
        self.direct_edit_hover_item = None
        self.direct_edit_editor = None
        if hasattr(self, 'drawings') and self.drawings:
            for d in self.drawings:
                it = d.get('item_ref')
                if it:
                    if hasattr(it, 'finish_cell_editing'):
                        try:
                            it.finish_cell_editing()
                        except Exception:
                            pass
                    if hasattr(it, 'stop_movie'):
                        try:
                            it.stop_movie()
                        except Exception:
                            pass
                d['item_ref'] = None

        # Sahne temizlenmeden once proxy widget'lari ve secim vurgularini guvenle temizle
        if hasattr(self, 'interactive_form_proxies'):
            for p in list(self.interactive_form_proxies):
                try:
                    if p.scene() == self.scene:
                        self.scene.removeItem(p)
                except Exception:
                    pass
            self.interactive_form_proxies.clear()
        if hasattr(self, '_interactive_field_widgets'):
            self._interactive_field_widgets.clear()

        if hasattr(self, 'selection_highlight_items'):
            for itm in list(self.selection_highlight_items):
                try:
                    if itm.scene() == self.scene:
                        self.scene.removeItem(itm)
                except Exception:
                    pass
            self.selection_highlight_items.clear()

        if hasattr(self, 'search_highlight_items'):
            for sitm in list(self.search_highlight_items):
                try:
                    if sitm.scene() == self.scene:
                        self.scene.removeItem(sitm)
                except Exception:
                    pass
            self.search_highlight_items.clear()

        if hasattr(self, 'bookmark_ribbon_items'):
            self.bookmark_ribbon_items.clear()
        self._last_hovered_ribbon = None
        self.selection_item = None
        self.current_path_item = None
        self.pointer_last_pos = None
        self.pointer_trail_items = []
        self._stamp_ghost_item = None
        self._form_ghost_item = None
        self._comment_drag_ghost_item = None
        self.search_active_item = None
        self.selected_text_items = []
        self.text_selection_hud = None
        self._alignment_guide_item = None
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

        num_pages = len(self.doc)
        if self.page_view_mode == "double":
            max_row_w = 0.0
            i = 0
            while i < num_pages:
                pr1 = self.doc[i].rect
                rw = pr1.width * self.base_render_dpi
                if i + 1 < num_pages:
                    pr2 = self.doc[i + 1].rect
                    rw += self.PAGE_MARGIN + (pr2.width * self.base_render_dpi)
                    i += 2
                else:
                    i += 1
                if rw > max_row_w:
                    max_row_w = rw
        else:
            max_row_w = max((self.doc[idx].rect.width * self.base_render_dpi for idx in range(num_pages)), default=595.0 * self.base_render_dpi)

        if self.page_view_mode == "double":
            y_offset = 15
            i = 0
            while i < num_pages:
                p_rect1 = self.doc[i].rect
                w1, h1 = p_rect1.width * self.base_render_dpi, p_rect1.height * self.base_render_dpi

                if i + 1 < num_pages:
                    p_rect2 = self.doc[i + 1].rect
                    w2, h2 = p_rect2.width * self.base_render_dpi, p_rect2.height * self.base_render_dpi
                    row_w = w1 + self.PAGE_MARGIN + w2
                    row_x_offset = max(0.0, (max_row_w - row_w) / 2.0)
                    x1 = row_x_offset
                    x2 = row_x_offset + w1 + self.PAGE_MARGIN

                    bg_rect1 = self.scene.addRect(x1, y_offset, w1, h1, QPen(pen_col, 1), QBrush(brush_col))
                    bg_rect1.setZValue(-2)
                    bg_rect1.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                    pix_item1 = self.scene.addPixmap(QPixmap())
                    pix_item1.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                    pix_item1.setPos(x1, y_offset)
                    pix_item1.setZValue(-1)

                    self.page_positions[i] = {
                        'item': pix_item1, 'bg_rect': bg_rect1,
                        'left': float(x1), 'right': float(x1 + w1),
                        'top': y_offset, 'bottom': y_offset + h1,
                        'height': h1, 'width': w1, 'rendered_zoom': 0.0
                    }

                    bg_rect2 = self.scene.addRect(x2, y_offset, w2, h2, QPen(pen_col, 1), QBrush(brush_col))
                    bg_rect2.setZValue(-2)
                    bg_rect2.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                    pix_item2 = self.scene.addPixmap(QPixmap())
                    pix_item2.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
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
                    row_x_offset = max(0.0, (max_row_w - w1) / 2.0)
                    bg_rect1 = self.scene.addRect(row_x_offset, y_offset, w1, h1, QPen(pen_col, 1), QBrush(brush_col))
                    bg_rect1.setZValue(-2)
                    bg_rect1.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                    pix_item1 = self.scene.addPixmap(QPixmap())
                    pix_item1.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                    pix_item1.setPos(row_x_offset, y_offset)
                    pix_item1.setZValue(-1)

                    self.page_positions[i] = {
                        'item': pix_item1, 'bg_rect': bg_rect1,
                        'left': float(row_x_offset), 'right': float(row_x_offset + w1),
                        'top': y_offset, 'bottom': y_offset + h1,
                        'height': h1, 'width': w1, 'rendered_zoom': 0.0
                    }
                    row_h = h1
                    i += 1

                y_offset += row_h + self.PAGE_MARGIN
        else:
            y_offset = 15
            for idx in range(num_pages):
                p_rect = self.doc[idx].rect
                w, h = p_rect.width * self.base_render_dpi, p_rect.height * self.base_render_dpi
                x_offset = max(0.0, (max_row_w - w) / 2.0)

                bg_rect = self.scene.addRect(x_offset, y_offset, w, h, QPen(pen_col, 1), QBrush(brush_col))
                bg_rect.setZValue(-2)
                bg_rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

                pix_item = self.scene.addPixmap(QPixmap())
                pix_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                pix_item.setPos(x_offset, y_offset)
                pix_item.setZValue(-1)

                self.page_positions[idx] = {
                    'item': pix_item, 'bg_rect': bg_rect,
                    'left': float(x_offset), 'right': float(x_offset + w),
                    'top': y_offset, 'bottom': y_offset + h,
                    'height': h, 'width': w, 'rendered_zoom': 0.0
                }
                y_offset += h + self.PAGE_MARGIN

        self._is_restoring_drawings = True
        try:
            for record in list(self.drawings):
                self.restore_drawing_item(record)
        finally:
            self._is_restoring_drawings = False
        self.init_bookmark_ribbons()
        self._load_interactive_form_widgets()
        if self.page_positions:
            max_right = max(p['right'] for p in self.page_positions.values())
            max_bottom = max(p['bottom'] for p in self.page_positions.values())
            self.scene.setSceneRect(-20, -10, max_right + 40, max_bottom + 20)
        else:
            self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20, -10, 20, 20))

    def init_bookmark_ribbons(self):
        if hasattr(self, 'bookmark_ribbon_items'):
            self.bookmark_ribbon_items.clear()
        self._last_hovered_ribbon = None
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
            pw = float(pinfo.get('width', 595.0))
            ph = float(pinfo.get('height', 842.0))
            eff_dim = min(pw, ph * 0.85)
            scale = max(0.35, min(1.35, eff_dim / 595.0))

            ribbon_w = BookmarkRibbonItem.BASE_WIDTH * scale
            margin_x = BookmarkRibbonItem.BASE_MARGIN * scale
            rx = pinfo['right'] - ribbon_w - margin_x
            ry = pinfo['top']
            ribbon = BookmarkRibbonItem(self, idx, rx, ry, is_bookmarked=(idx in bookmarked_pages), scale=scale)
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

        for idx, ribbon in list(self.bookmark_ribbon_items.items()):
            try:
                ribbon.set_bookmarked(idx in bookmarked_pages)
            except Exception:
                pass

        if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
            if hasattr(self.main_window.modern_right_sidebar, 'refresh_bookmark_indicators'):
                self.main_window.modern_right_sidebar.refresh_bookmark_indicators()

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
        """Görünür sayfaları arka plan thread'inde render eder.
        Küçük sayfa sayısı veya forced mod için senkron render uygulanır;
        büyük belgeler async worker'a devredilir.
        """
        if self.doc is None or not self.page_positions:
            return

        visible_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        # Buffer: viewport yüksekliğinin yarısı kadar ön-yükleme
        vp_h = self.view.viewport().height()
        buffer = max(600, vp_h * 0.6)
        buffer_top    = visible_rect.top()    - buffer
        buffer_bottom = visible_rect.bottom() + buffer
        # Uzak sayfaları temizleme eşiği
        unload_dist   = max(3000, vp_h * 2.5)

        # Viewport ekran piksel yoğunluğunu (High-DPI / Retina / Windows %125, %150, %200) tespit et
        dpr = 1.0
        try:
            if hasattr(self.view, 'devicePixelRatioF') and self.view.devicePixelRatioF() > 0:
                dpr = float(self.view.devicePixelRatioF())
            elif hasattr(self, 'devicePixelRatioF') and self.devicePixelRatioF() > 0:
                dpr = float(self.devicePixelRatioF())
            # Pencere veya ekran DPR'ını da kontrol et (özellikle ilk yüklemede unmapped view durumunda)
            win = self.window()
            if win and win.windowHandle() and win.windowHandle().screen():
                win_dpr = float(win.windowHandle().screen().devicePixelRatio())
                if win_dpr > dpr:
                    dpr = win_dpr
            elif QApplication.primaryScreen():
                prim_dpr = float(QApplication.primaryScreen().devicePixelRatio())
                if prim_dpr > dpr:
                    dpr = prim_dpr
        except Exception:
            dpr = 1.0
        if dpr < 1.0:
            dpr = 1.0
        self._current_dpr = dpr

        target_scale = self.base_render_dpi * self.zoom_level * dpr
        mat  = fitz.Matrix(target_scale, target_scale)
        mode = getattr(self, 'reading_color_mode', 'normal')
        zoom = self.zoom_level

        jobs_needed: list[tuple] = []

        for idx, pinfo in self.page_positions.items():
            page_top    = pinfo['top']
            page_bottom = pinfo['bottom']
            in_viewport = not (page_bottom < buffer_top or page_top > buffer_bottom)

            if in_viewport:
                needs_render = (
                    force
                    or pinfo['item'].pixmap().isNull()
                    or abs(pinfo.get('rendered_zoom', 0.0) - zoom) > 0.05
                    or abs(pinfo.get('rendered_dpr', 1.0) - dpr) > 0.05
                )
                if needs_render:
                    render_annots = not getattr(self, 'is_form_design_mode', False)
                    jobs_needed.append((idx, mat, mode, self.doc, render_annots, zoom, dpr))
            else:
                # Uzak sayfaların pixmap'ini serbest bırak (bellek tasarrufu)
                if pinfo.get('rendered_zoom', 0.0) > 0.0:
                    dist = min(
                        abs(page_bottom - visible_rect.top()),
                        abs(page_top    - visible_rect.bottom())
                    )
                    if dist > unload_dist:
                        pinfo['item'].setPixmap(QPixmap())
                        pinfo['rendered_zoom'] = 0.0

        if not jobs_needed:
            return

        # Az sayfa veya forced: senkron render (scroll animasyonu sırasında gecikme olmasın)
        SYNC_THRESHOLD = 3
        if force or len(jobs_needed) <= SYNC_THRESHOLD:
            for job in jobs_needed:
                idx, mat2, mode2, doc2 = job[0], job[1], job[2], job[3]
                annots_flag = job[4] if len(job) > 4 else not getattr(self, 'is_form_design_mode', False)
                job_zoom = job[5] if len(job) > 5 else zoom
                job_dpr = job[6] if len(job) > 6 else dpr
                try:
                    pix = doc2[idx].get_pixmap(matrix=mat2, annots=annots_flag, alpha=False)
                    if mode2 == 'dark':
                        apply_smart_dark_invert(pix, doc2[idx], mat2)
                    qimg = QImage(pix.samples, pix.width, pix.height,
                                  pix.stride, QImage.Format.Format_RGB888).copy()
                    if mode2 == 'sepia':
                        p_sepia = QPainter(qimg)
                        p_sepia.setCompositionMode(
                            QPainter.CompositionMode.CompositionMode_Multiply)
                        p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                        p_sepia.end()
                    qpix = QPixmap.fromImage(qimg)
                    if job_dpr > 1.0:
                        qpix.setDevicePixelRatio(job_dpr)
                    pinfo2 = self.page_positions.get(idx)
                    if pinfo2:
                        pinfo2['item'].setPixmap(qpix)
                        pinfo2['item'].setScale(1.0 / job_zoom)
                        pinfo2['rendered_zoom'] = job_zoom
                        pinfo2['rendered_dpr'] = job_dpr
                except Exception:
                    pass
        else:
            # Çok sayfalı render: async worker
            if hasattr(self, '_render_worker') and self._render_worker:
                try:
                    self._render_worker.schedule(jobs_needed)
                    if not self._render_worker.isRunning():
                        self._render_worker.start(QThread.Priority.LowPriority)
                except Exception:
                    pass

    def _on_page_rendered(self, idx: int, qimg, job_zoom: float = 1.0, job_dpr: float = 1.0):
        """Async worker'dan gelen render sonuçlarını UI thread'inde uygular."""
        if self.doc is None or getattr(self.doc, 'is_closed', False):
            return
        pinfo = self.page_positions.get(idx)
        if pinfo and pinfo.get('item'):
            try:
                item = pinfo['item']
                if item.scene() != self.scene:
                    return
                qpix = QPixmap.fromImage(qimg)
                if job_dpr > 1.0:
                    qpix.setDevicePixelRatio(job_dpr)
                item.setPixmap(qpix)
                item.setScale(1.0 / job_zoom)
                pinfo['rendered_zoom'] = job_zoom
                pinfo['rendered_dpr'] = job_dpr

                # Kullanıcı render sırasında zoom seviyesini veya DPI'ı değiştirdiyse yeniden tetikle
                if abs(self.zoom_level - job_zoom) > 0.05 or abs(getattr(self, '_current_dpr', 1.0) - job_dpr) > 0.05:
                    self.rerender_timer.start(80)
            except Exception:
                pass

    def rerender_page(self, page_idx: int):
        """Yalnızca belirtilen sayfayı hemen ve gecikmesiz senkron render eder."""
        if not self.doc or not hasattr(self, 'page_positions') or not self.page_positions or page_idx not in self.page_positions:
            return
        pinfo = self.page_positions[page_idx]
        dpr = getattr(self, '_current_dpr', 1.0)
        target_scale = self.base_render_dpi * self.zoom_level * dpr
        mat = fitz.Matrix(target_scale, target_scale)
        mode = getattr(self, 'reading_color_mode', 'normal')
        zoom = self.zoom_level
        render_annots = not getattr(self, 'is_form_design_mode', False)
        try:
            pix = self.doc[page_idx].get_pixmap(matrix=mat, annots=render_annots, alpha=False)
            if mode == 'dark':
                apply_smart_dark_invert(pix, self.doc[page_idx], mat)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            if mode == 'sepia':
                p_sepia = QPainter(qimg)
                p_sepia.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                p_sepia.end()
            qpix = QPixmap.fromImage(qimg)
            if dpr > 1.0:
                qpix.setDevicePixelRatio(dpr)
            pinfo['item'].setPixmap(qpix)
            pinfo['item'].setScale(1.0 / zoom)
            pinfo['rendered_zoom'] = zoom
            pinfo['rendered_dpr'] = dpr
            if hasattr(self, 'view') and self.view:
                self.view.viewport().update()
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        # Sekme ilk kez görünür olduğunda veya başka bir monitöre taşındığında netliği garanti et
        QTimer.singleShot(60, self._check_dpr_and_rerender)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_dpr_and_rerender()

    def _check_dpr_and_rerender(self):
        """Mevcut ekranın gerçek DPI değerini kontrol eder; değişiklik varsa sayfaları kristal netlikte yeniden render eder."""
        if not self.doc or not self.page_positions:
            return
        dpr = 1.0
        try:
            if hasattr(self.view, 'devicePixelRatioF') and self.view.devicePixelRatioF() > 0:
                dpr = float(self.view.devicePixelRatioF())
            elif hasattr(self, 'devicePixelRatioF') and self.devicePixelRatioF() > 0:
                dpr = float(self.devicePixelRatioF())
            win = self.window()
            if win and win.windowHandle() and win.windowHandle().screen():
                win_dpr = float(win.windowHandle().screen().devicePixelRatio())
                if win_dpr > dpr:
                    dpr = win_dpr
            elif QApplication.primaryScreen():
                prim_dpr = float(QApplication.primaryScreen().devicePixelRatio())
                if prim_dpr > dpr:
                    dpr = prim_dpr
        except Exception:
            pass
        if dpr < 1.0:
            dpr = 1.0
        if abs(getattr(self, '_current_dpr', 1.0) - dpr) > 0.05:
            self._current_dpr = dpr
            self.rerender_visible_pages(force=True)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self._check_dpr_and_rerender()

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
        """Zoom ayarını debounce ile kaydeder (disk I/O fırtınasını önler)."""
        if hasattr(self, '_zoom_save_timer') and self._zoom_save_timer:
            try:
                self._zoom_save_timer.start()  # restart debounce
            except RuntimeError:
                self._do_save_zoom_setting()
        else:
            self._do_save_zoom_setting()

    def _do_save_zoom_setting(self):
        """Gerçek disk yazma işlemi - yalnızca debounce sonrası çağrılır."""
        try:
            import json
            settings = QSettings("AuraPDF", "PDFViewer")
            settings.setValue("last_zoom_level", float(round(self.zoom_level, 2)))
            if getattr(self, 'file_path', None):
                norm = os.path.abspath(self.file_path)
                raw = settings.value("file_zoom_levels", "{}")
                data = json.loads(raw) if isinstance(raw, str) else dict(raw)
                data[norm] = float(round(self.zoom_level, 2))
                if len(data) > 1000:
                    data = dict(list(data.items())[-1000:])
                settings.setValue("file_zoom_levels", json.dumps(data))
        except Exception:
            pass

    def apply_zoom(self, new_level):
        new_level = max(0.2, min(round(new_level, 2), 5.0))
        if new_level == self.zoom_level: return
        self.view.scale(new_level / self.zoom_level, new_level / self.zoom_level)
        self.zoom_level = new_level
        if hasattr(self.main_window, 'update_zoom_display'):
            self.main_window.update_zoom_display(int(round(self.zoom_level * 100)))
        elif hasattr(self.main_window, 'lbl_zoom'):
            self.main_window.lbl_zoom.setText(f" {LanguageManager.tr('percent_format', val=int(round(self.zoom_level * 100)))} ")
        self.rerender_timer.start(250)
        self.save_zoom_setting()
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.reposition()
        if hasattr(self, 'direct_edit_banner') and self.direct_edit_banner:
            self.direct_edit_banner.reposition()

    def zoom_in(self): self.apply_zoom(self.zoom_level + 0.15)
    def zoom_out(self): self.apply_zoom(self.zoom_level - 0.15)
    def set_zoom(self, new_level: float): self.apply_zoom(new_level)
    def fit_to_width(self):
        if not self.page_positions or self.doc is None:
            return
        if self.page_view_mode == "double":
            cur_p = self.page_positions.get(self.current_page_idx, {})
            is_even = (self.current_page_idx % 2 == 0)
            other_idx = self.current_page_idx + 1 if is_even else self.current_page_idx - 1
            other_p = self.page_positions.get(other_idx, {})
            total_w = cur_p.get('width', 595.0) + (other_p.get('width', 0.0) + self.PAGE_MARGIN if other_p else 0)
            viewport_w = self.view.viewport().width() - 40
            if total_w > 0 and viewport_w > 100:
                target_zoom = viewport_w / total_w
                self.apply_zoom(target_zoom)
                self.go_to_page(self.current_page_idx)
        else:
            cur_p = self.page_positions.get(self.current_page_idx, self.page_positions.get(0, {}))
            page_w = cur_p.get('width', 595.0)
            viewport_w = self.view.viewport().width() - 40
            if page_w > 0 and viewport_w > 100:
                target_zoom = viewport_w / page_w
                self.apply_zoom(target_zoom)
                self.go_to_page(self.current_page_idx)

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
        # Scroll debounce: hızlı scroll sırasında gereksiz re-render'ı önle
        # 200ms timeout: scroll durduğunda tek bir render tetikle
        self.rerender_timer.start(200)
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
        if self.active_text_item:
            if hasattr(self.active_text_item, 'clearFocus'):
                self.active_text_item.clearFocus()
            self.active_text_item = None
        p_info = self.page_positions.get(page_idx)
        if not p_info: return
        page_left = p_info.get('left', 0.0)
        page_width = p_info['width']
        page_right = page_left + page_width

        # Sayfa sınırları içinde kalması için güvenli marjinler ve minimum genişlik
        margin = 15.0
        min_w = 120.0
        clamped_x = max(page_left + margin, min(scene_pos.x(), page_right - min_w - margin))
        clamped_y = max(p_info['top'] + margin, min(scene_pos.y(), p_info['bottom'] - 40.0 - margin))
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
        if not item or not hasattr(item, 'toPlainText'):
            return
        if getattr(self, '_is_restoring_drawings', False) or getattr(item, '_is_initializing', False):
            return
        content = item.toPlainText().strip()
        
        # Manuel atanmış bağlantı kontrolü (Kullanıcı metne veya kelimeye özel bir URL bağlamışsa)
        is_manual = getattr(item, 'manual_link', False) or (bool(getattr(item, 'link_url', '')) and getattr(item, 'link_url', '') != content)
        
        doc_has_anchor = False
        if hasattr(item, 'get_fragments'):
            for blk in item.get_fragments():
                for f in blk:
                    if f.get("href"):
                        doc_has_anchor = True
                        break
                if doc_has_anchor:
                    break

        if is_manual and getattr(item, 'link_url', ''):
            item.manual_link = True
            link_text = getattr(item, 'link_text', '')
            link_range = getattr(item, 'link_range', None)
            if link_text and link_text in content:
                if not doc_has_anchor:
                    item.format_link_substring(link_text, item.link_url, char_range=link_range)
            elif getattr(item, 'link_url', ''):
                if link_text and link_text not in content:
                    item.clear_link_formatting()
                elif not doc_has_anchor:
                    item.format_entire_text_as_link(item.link_url)
        else:
            # Otomatik URL / E-Posta / Telefon / T.C. Kimlik Algılama
            if not getattr(item, '_suppress_auto_link', False):
                from src.core.hyperlink_detector import detect_hyperlink
                detected = detect_hyperlink(content)
                if detected:
                    if not doc_has_anchor:
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
                
        p_info = self.page_positions.get(item.page_idx)
        if not p_info:
            return
        page_top = p_info['top']
        page_left = p_info.get('left', 0.0)
        rel_x = max(0.0, (item.pos().x() - page_left) / self.base_render_dpi)
        rel_y = max(0.0, (item.pos().y() - page_top) / self.base_render_dpi)
        br = item.boundingRect()

        # Sayfa sınırlarını aşmaması için PDF nokta ölçülerini sınırla
        p_rect = self.doc[item.page_idx].rect if (self.doc and 0 <= item.page_idx < len(self.doc)) else None
        max_w_pt = max(30.0, (p_rect.width - rel_x - 4.0)) if p_rect else 500.0
        max_h_pt = max(20.0, (p_rect.height - rel_y - 4.0)) if p_rect else 400.0
        w_pt = min(max(20.0, br.width() / self.base_render_dpi), max_w_pt)
        h_pt = min(max(15.0, br.height() / self.base_render_dpi), max_h_pt)

        existing = [d for d in self.drawings if d.get("item_ref") == item]
        new_html = item.toHtml() if hasattr(item, 'toHtml') else ""
        frags = item.get_fragments() if hasattr(item, 'get_fragments') else None

        if existing:
            record = existing[0]
            pos_changed = (
                abs(record.get("x", 0.0) - rel_x) > 0.01 or
                abs(record.get("y", 0.0) - rel_y) > 0.01
            )
            dim_changed = (
                abs(record.get("w", 0.0) - w_pt) > 0.01 or
                abs(record.get("h", 0.0) - h_pt) > 0.01
            )
            content_changed = (
                record.get("text") != content or 
                record.get("html") != new_html or
                record.get("fragments") != frags or
                record.get("link_url") != getattr(item, 'link_url', "") or
                record.get("link_text") != getattr(item, 'link_text', "") or
                record.get("link_range") != getattr(item, 'link_range', None) or
                record.get("bold") != getattr(item, 'bold', False) or
                record.get("italic") != getattr(item, 'italic', False) or
                record.get("underline") != getattr(item, 'underline', False) or
                record.get("alignment") != getattr(item, 'alignment_str', 'left') or
                record.get("font_size") != item.font_size or
                record.get("color") != item.text_color
            )
            if pos_changed or dim_changed or content_changed:
                old_val = record.get("text", "")
                old_html = record.get("html", "")
                old_frags = record.get("fragments", None)
                old_x = record.get("x", rel_x)
                old_y = record.get("y", rel_y)
                record["text"] = content
                record["html"] = new_html
                record["fragments"] = frags
                record["font_size"] = item.font_size
                record["font_family"] = item.font_family
                record["color"] = item.text_color
                record["bold"] = getattr(item, 'bold', False)
                record["italic"] = getattr(item, 'italic', False)
                record["underline"] = getattr(item, 'underline', False)
                record["alignment"] = getattr(item, 'alignment_str', 'left')
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
                    "old_fragments": old_frags, "new_fragments": frags,
                    "old_x": old_x, "new_x": rel_x,
                    "old_y": old_y, "new_y": rel_y
                })
                self.set_modified(True)
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
                "alignment": getattr(item, 'alignment_str', 'left'),
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
            if hasattr(self.main_window, 'current_tool'):
                self.direct_edit_banner.update_active_tool(self.main_window.current_tool)
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
        self.remove_direct_edit_camouflage()
        if hasattr(self, 'direct_edit_editor') and self.direct_edit_editor:
            self.direct_edit_editor.hide()
            self.direct_edit_editor.deleteLater()
            self.direct_edit_editor = None

    def create_direct_edit_camouflage(self, page_idx: int, orig_bbox: fitz.Rect, vector_underline_rect: fitz.Rect = None):
        """Metin düzenleme veya taşıma esnasında orijinal metnin sahne üzerinde temizlenmiş arka planla gizlenmesini sağlar."""
        self.remove_direct_edit_camouflage()
        if not self.doc or page_idx >= len(self.doc):
            return
        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.base_render_dpi

        try:
            tmp_doc = fitz.open()
            tmp_doc.insert_pdf(self.doc, from_page=page_idx, to_page=page_idx)
            tmp_page = tmp_doc[0]

            clean_rect = fitz.Rect(orig_bbox)
            clean_rect.x0 = max(0.0, clean_rect.x0 - 0.5)
            clean_rect.y0 = max(0.0, clean_rect.y0 - 0.5)
            clean_rect.x1 = min(tmp_page.rect.width, clean_rect.x1 + 0.5)
            clean_rect.y1 = min(tmp_page.rect.height, clean_rect.y1 + 0.5)
            tmp_page.add_redact_annot(clean_rect)
            tmp_page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                text=fitz.PDF_REDACT_TEXT_REMOVE
            )
            if vector_underline_rect:
                d_r = fitz.Rect(vector_underline_rect)
                d_r.x0 = max(0.0, d_r.x0 - 0.5)
                d_r.y0 = max(0.0, d_r.y0 - 0.5)
                d_r.x1 = min(tmp_page.rect.width, d_r.x1 + 0.5)
                d_r.y1 = min(tmp_page.rect.height, d_r.y1 + 0.5)
                tmp_page.add_redact_annot(d_r)
                tmp_page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                    text=fitz.PDF_REDACT_TEXT_NONE
                )

            mat = fitz.Matrix(dpi, dpi)
            pix = tmp_page.get_pixmap(clip=clean_rect, matrix=mat)
            tmp_doc.close()

            mode = getattr(self, 'reading_color_mode', 'normal')
            if mode == 'dark':
                pix.invert_irect()

            from PyQt6.QtGui import QImage, QPixmap
            from PyQt6.QtWidgets import QGraphicsPixmapItem
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            if mode == 'sepia':
                from PyQt6.QtGui import QPainter
                p_sepia = QPainter(qimg)
                p_sepia.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
                p_sepia.fillRect(qimg.rect(), QColor(246, 238, 220))
                p_sepia.end()

            item = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
            item.setPos(page_left + clean_rect.x0 * dpi, page_top + clean_rect.y0 * dpi)
            item.setZValue(90)
            self.scene.addItem(item)
            self._direct_edit_camo_item = item
        except Exception:
            self._direct_edit_camo_item = None

    def remove_direct_edit_camouflage(self):
        """Geçici arka plan kamuflaj öğesini sahneden güvenle kaldırır."""
        if hasattr(self, '_direct_edit_camo_item') and self._direct_edit_camo_item is not None:
            try:
                if self._direct_edit_camo_item.scene() == self.scene:
                    self.scene.removeItem(self._direct_edit_camo_item)
            except Exception:
                pass
            self._direct_edit_camo_item = None

    def get_page_text_blocks(self, page_idx: int) -> List[Dict[str, Any]]:
        if not self.doc or page_idx >= len(self.doc):
            return []
        if page_idx not in self._page_text_blocks_cache:
            from src.ui.direct_text_editor import extract_page_text_blocks
            self._page_text_blocks_cache[page_idx] = extract_page_text_blocks(self.doc[page_idx])
        return self._page_text_blocks_cache[page_idx]

    def open_inplace_editor_at_block(self, page_idx: int, blk: dict):
        self.close_inplace_editor()
        self.create_direct_edit_camouflage(page_idx, blk["bbox"], blk.get("vector_underline_rect", None))
        from src.ui.direct_text_editor import DirectTextInplaceEditor
        editor = DirectTextInplaceEditor(
            self, page_idx, blk["bbox"], blk["text"],
            font_size=blk["font_size"], color_rgb=blk["color_rgb"],
            bold=blk["bold"], italic=blk["italic"],
            underline=blk.get("underline", False),
            vector_underline_rect=blk.get("vector_underline_rect", None),
            font_name=blk.get("font_name", "Arial"), is_new=False
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
            bold=False, italic=False, underline=False,
            vector_underline_rect=None,
            font_name="Arial", is_new=True
        )
        self.direct_edit_editor = editor
        editor.show()

    def commit_direct_text_edit(self, page_idx: int, orig_bbox: fitz.Rect, new_text: str,
                                font_size: float, color_rgb: tuple, bold: bool, italic: bool,
                                underline: bool = False, vector_underline_rect: fitz.Rect = None,
                                font_name: str = "Arial", is_new: bool = False,
                                target_bbox: fitz.Rect = None, target_page_idx: int = None):
        if not self.doc or page_idx >= len(self.doc):
            return
        if target_page_idx is None:
            target_page_idx = page_idx
        if target_page_idx >= len(self.doc):
            target_page_idx = page_idx

        page = self.doc[page_idx]
        target_page = self.doc[target_page_idx]
        old_bytes = self.doc.tobytes()

        import os
        from src.ui.direct_text_editor import get_unicode_font_path, find_fitting_box

        try:
            # 1. Eski metin alanını kalıcı olarak temizle (redact)
            if not is_new:
                clean_rect = fitz.Rect(orig_bbox)
                clean_rect.x0 = max(0.0, clean_rect.x0 - 0.5)
                clean_rect.y0 = max(0.0, clean_rect.y0 - 0.5)
                clean_rect.x1 = min(page.rect.width, clean_rect.x1 + 0.5)
                clean_rect.y1 = min(page.rect.height, clean_rect.y1 + 0.5)
                page.add_redact_annot(clean_rect)
                # KRİTİK: images=0, graphics=0 sayesinde arka plan resimleri ve vektör şekilleri ASLA silinmez veya beyaza boyanmaz!
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                    text=fitz.PDF_REDACT_TEXT_REMOVE
                )
                if vector_underline_rect:
                    d_r = fitz.Rect(vector_underline_rect)
                    d_r.x0 = max(0.0, d_r.x0 - 0.5)
                    d_r.y0 = max(0.0, d_r.y0 - 0.5)
                    d_r.x1 = min(page.rect.width, d_r.x1 + 0.5)
                    d_r.y1 = min(page.rect.height, d_r.y1 + 0.5)
                    page.add_redact_annot(d_r)
                    page.apply_redactions(
                        images=fitz.PDF_REDACT_IMAGE_NONE,
                        graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                        text=fitz.PDF_REDACT_TEXT_NONE
                    )

            # 2. Yeni metni yaz (hedef sayfaya ve hedef konuma)
            if new_text.strip():
                fontfile = get_unicode_font_path(font_name=font_name, bold=bold, italic=italic)
                b_str = 'b' if bold else ''
                i_str = 'i' if italic else ''
                fontname = f"f_{font_name.lower().replace(' ', '_')[:5]}{b_str}{i_str}"
                try:
                    target_page.insert_font(fontname=fontname, fontfile=fontfile)
                except Exception:
                    pass

                dest_rect = target_bbox if target_bbox else orig_bbox
                fit_rect, fit_fs = find_fitting_box(target_page, dest_rect, new_text, target_fs=font_size, fontfile=fontfile, fontname=fontname)

                res = target_page.insert_textbox(
                    fit_rect, new_text,
                    fontsize=fit_fs,
                    fontname=fontname,
                    fontfile=fontfile,
                    color=color_rgb,
                    align=0
                )
                if res < 0:
                    target_page.insert_text(
                        fitz.Point(fit_rect.x0, fit_rect.y0 + fit_fs),
                        new_text,
                        fontsize=fit_fs,
                        fontname=fontname,
                        fontfile=fontfile,
                        color=color_rgb
                    )

                # 3. Eğer altı çizili ise veya orijinalde alt çizgi varsa yeni metin genişliğine göre alt çizgi çiz
                if underline:
                    try:
                        f_obj = fitz.Font(fontfile=fontfile) if (fontfile and os.path.isfile(fontfile)) else None
                        tw = f_obj.text_length(new_text, fontsize=fit_fs) if f_obj else len(new_text) * fit_fs * 0.55
                    except Exception:
                        tw = len(new_text) * fit_fs * 0.55

                    if vector_underline_rect and not target_bbox:
                        under_y = (vector_underline_rect.y0 + vector_underline_rect.y1) / 2.0
                    else:
                        under_y = min(target_page.rect.height - 1.0, fit_rect.y0 + fit_fs * 1.05)

                    target_page.draw_line(
                        fitz.Point(fit_rect.x0, under_y),
                        fitz.Point(fit_rect.x0 + tw, under_y),
                        color=color_rgb,
                        width=1.8
                    )

            new_bytes = self.doc.tobytes()
            self.push_undo_action({
                "type": "direct_text_edit",
                "old_bytes": old_bytes,
                "new_bytes": new_bytes,
                "page_idx": page_idx,
                "target_page_idx": target_page_idx
            })

            self._page_text_blocks_cache.pop(page_idx, None)
            if target_page_idx != page_idx:
                self._page_text_blocks_cache.pop(target_page_idx, None)

            self.remove_direct_edit_camouflage()
            self.set_modified(True)
            self.rerender_visible_pages(force=True)
            self.close_inplace_editor()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(LanguageManager.tr("direct_edit_success"), 3500)

        except Exception as e:
            self.remove_direct_edit_camouflage()
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('direct_edit_failed')}\n{e}")

    def delete_direct_text_block(self, page_idx: int, orig_bbox: fitz.Rect, vector_underline_rect: fitz.Rect = None):
        if not self.doc or page_idx >= len(self.doc):
            return
        page = self.doc[page_idx]
        old_bytes = self.doc.tobytes()
        try:
            clean_rect = fitz.Rect(orig_bbox)
            clean_rect.x0 = max(0.0, clean_rect.x0 - 0.5)
            clean_rect.y0 = max(0.0, clean_rect.y0 - 0.5)
            clean_rect.x1 = min(page.rect.width, clean_rect.x1 + 0.5)
            clean_rect.y1 = min(page.rect.height, clean_rect.y1 + 0.5)
            page.add_redact_annot(clean_rect)
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_NONE,
                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                text=fitz.PDF_REDACT_TEXT_REMOVE
            )
            if vector_underline_rect:
                d_r = fitz.Rect(vector_underline_rect)
                d_r.x0 = max(0.0, d_r.x0 - 0.5)
                d_r.y0 = max(0.0, d_r.y0 - 0.5)
                d_r.x1 = min(page.rect.width, d_r.x1 + 0.5)
                d_r.y1 = min(page.rect.height, d_r.y1 + 0.5)
                page.add_redact_annot(d_r)
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                    text=fitz.PDF_REDACT_TEXT_NONE
                )

            new_bytes = self.doc.tobytes()
            self.push_undo_action({
                "type": "direct_text_edit",
                "old_bytes": old_bytes,
                "new_bytes": new_bytes,
                "page_idx": page_idx
            })
            self._page_text_blocks_cache.pop(page_idx, None)
            self.remove_direct_edit_camouflage()
            self.set_modified(True)
            self.rerender_visible_pages(force=True)
            self.close_inplace_editor()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(LanguageManager.tr("direct_edit_deleted"), 3500)
        except Exception as e:
            self.remove_direct_edit_camouflage()
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('direct_edit_delete_failed')}\n{e}")

    def _safe_ensure_hover_item(self) -> bool:
        try:
            if self.direct_edit_hover_item is not None:
                sc = self.direct_edit_hover_item.scene()
                if sc == self.scene:
                    return True
        except (RuntimeError, Exception):
            self.direct_edit_hover_item = None

        try:
            from src.ui.direct_text_editor import DirectEditHoverItem
            self.direct_edit_hover_item = DirectEditHoverItem()
            if self.scene:
                self.scene.addItem(self.direct_edit_hover_item)
            return True
        except Exception:
            self.direct_edit_hover_item = None
            return False

    def _safe_hide_hover_item(self):
        try:
            if self.direct_edit_hover_item is not None:
                self.direct_edit_hover_item.hide()
        except (RuntimeError, Exception):
            self.direct_edit_hover_item = None

    def _handle_direct_edit_mouse_move(self, pos: QPointF):
        if not self._safe_ensure_hover_item():
            return

        page_idx = self.get_page_at_pos(pos)
        if page_idx is None:
            self._safe_hide_hover_item()
            self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            return

        p_info = self.page_positions.get(page_idx)
        if not p_info:
            self._safe_hide_hover_item()
            return

        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)
        dpi = self.base_render_dpi

        if self.direct_edit_editor:
            self._safe_hide_hover_item()
            return

        pdf_x = (pos.x() - page_left) / dpi
        pdf_y = (pos.y() - page_top) / dpi
        pdf_pt = fitz.Point(pdf_x, pdf_y)

        blocks = self.get_page_text_blocks(page_idx)
        hit_blk = None
        hit_candidates = []
        for blk in blocks:
            r = fitz.Rect(blk["bbox"])
            r_padded = fitz.Rect(r.x0 - 1.5, r.y0 - 1.5, r.x1 + 1.5, r.y1 + 1.5)
            if pdf_pt in r_padded:
                hit_candidates.append(blk)

        if hit_candidates:
            hit_blk = min(hit_candidates, key=lambda b: fitz.Rect(b["bbox"]).get_area())

        if hit_blk:
            r = hit_blk["bbox"]
            sx0 = page_left + r.x0 * dpi
            sy0 = page_top + r.y0 * dpi
            sw = (r.x1 - r.x0) * dpi
            sh = (r.y1 - r.y0) * dpi
            try:
                self.direct_edit_hover_item.setRect(QRectF(sx0 - 2, sy0 - 2, sw + 4, sh + 4))
                self.direct_edit_hover_item.show()
            except (RuntimeError, Exception):
                self.direct_edit_hover_item = None
            self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self._safe_hide_hover_item()
            self.view.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    def _handle_direct_edit_mouse_press(self, pos: QPointF, vp_pos: QPoint) -> bool:
        if self.direct_edit_editor:
            if hasattr(self.direct_edit_editor, 'contains_viewport_pos') and self.direct_edit_editor.contains_viewport_pos(vp_pos):
                return False
            elif self.direct_edit_editor.geometry().contains(vp_pos):
                return False

        had_active_editor = bool(self.direct_edit_editor)
        if had_active_editor:
            if hasattr(self.direct_edit_editor, 'has_uncommitted_changes') and self.direct_edit_editor.has_uncommitted_changes():
                self.direct_edit_editor.apply_changes()
            else:
                self.close_inplace_editor()

        page_idx = self.get_page_at_pos(pos)
        if page_idx is None:
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
        hit_candidates = []
        for blk in blocks:
            r = fitz.Rect(blk["bbox"])
            r_padded = fitz.Rect(r.x0 - 2.0, r.y0 - 2.0, r.x1 + 2.0, r.y1 + 2.0)
            if pdf_pt in r_padded:
                hit_candidates.append(blk)

        if hit_candidates:
            hit_blk = min(hit_candidates, key=lambda b: fitz.Rect(b["bbox"]).get_area())

        if hit_blk:
            self.open_inplace_editor_at_block(page_idx, hit_blk)
            return True
        elif not had_active_editor:
            self.open_inplace_editor_for_new_text(page_idx, pos)
            return True
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
            alignment=record.get("alignment", "left"),
        )
        record["item_ref"] = item
        if record.get("html"):
            item.setHtml(record["html"])
        item.set_alignment(record.get("alignment", "left"), commit=False)

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
                  page_idx: Optional[int] = None, pos: Optional[QPointF] = None,
                  alignment: str = "center"):
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

            rows = max(1, int(rows))
            cols = max(1, int(cols))

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
                "alignment": str(alignment).lower(),
                "cell_alignments": [[str(alignment).lower() for _ in range(cols)] for _ in range(rows)],
                "cell_data": cell_data
            }

            self.drawings.append(item_data)
            self.render_table_item(item_data)
            self.push_undo_action({"type": "add", "data": item_data})
            self.notify_drawings_changed(page_idx)

            it = item_data.get("item_ref")
            if it:
                it.setSelected(True)
                if hasattr(self, 'active_text_item') and self.active_text_item:
                    if hasattr(self.active_text_item, 'finish_editing'):
                        try:
                            self.active_text_item.finish_editing()
                        except Exception:
                            pass
                    self.active_text_item = None
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
                pdf_x = (pos.x() - page_left) / self.base_render_dpi - pdf_w / 2.0
                pdf_y = (pos.y() - page_top) / self.base_render_dpi - pdf_h / 2.0

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
                pdf_x = (pos.x() - page_left) / self.base_render_dpi - pdf_w / 2.0
                pdf_y = (pos.y() - page_top) / self.base_render_dpi - pdf_h / 2.0

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

    def get_comment_annot_at_pos(self, scene_pos: QPointF):
        """
        Belirtilen sahne koordinatında bir yorum (fitz.PDF_ANNOT_TEXT) varsa,
        (page_idx, annot, annot_rect) döndürür. Yoksa (None, None, None) döner.
        """
        if not self.doc:
            return None, None, None
        page_idx = self.get_page_at_pos(scene_pos)
        if page_idx is None or not (0 <= page_idx < len(self.doc)):
            return None, None, None
        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return None, None, None
        scale = self.base_render_dpi
        pleft = p_info.get('left', 0.0)
        ptop = p_info['top']
        pdf_x = (scene_pos.x() - pleft) / scale
        pdf_y = (scene_pos.y() - ptop) / scale
        pt = fitz.Point(pdf_x, pdf_y)
        try:
            page = self.doc[page_idx]
            for annot in page.annots():
                atype = annot.type[0] if isinstance(annot.type, (tuple, list)) else annot.type
                if atype == fitz.PDF_ANNOT_TEXT:
                    r = annot.rect
                    # Tıklama ve yakalama toleransı
                    hr = fitz.Rect(r.x0 - 10, r.y0 - 10, r.x1 + 10, r.y1 + 10)
                    if pt in hr:
                        return page_idx, annot, r
        except Exception:
            pass
        return None, None, None

    def _update_comment_drag_ghost(self, scene_pos: QPointF):
        """Yorum sürüklenirken fareyi takip eden şık yarı-saydam hayalet simgeyi günceller."""
        if not hasattr(self, '_comment_drag_ghost_item') or self._comment_drag_ghost_item is None:
            pix = QPixmap(36, 36)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setBrush(QBrush(QColor(245, 158, 11, 220)))  # Amber dolgu
            p.setPen(QPen(QColor("#ffffff"), 2.0))
            p.drawRoundedRect(QRectF(2, 2, 32, 32), 8, 8)
            bubble = QPainterPath()
            bubble.moveTo(10, 11)
            bubble.lineTo(26, 11)
            bubble.quadTo(28, 11, 28, 13)
            bubble.lineTo(28, 21)
            bubble.quadTo(28, 23, 26, 23)
            bubble.lineTo(16, 23)
            bubble.lineTo(12, 27)
            bubble.lineTo(12, 23)
            bubble.lineTo(10, 23)
            bubble.quadTo(8, 23, 8, 21)
            bubble.lineTo(8, 13)
            bubble.quadTo(8, 11, 10, 11)
            bubble.closeSubpath()
            p.setBrush(QBrush(QColor("#ffffff")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(bubble)
            p.end()

            self._comment_drag_ghost_item = QGraphicsPixmapItem(pix)
            self._comment_drag_ghost_item.setOpacity(0.88)
            self._comment_drag_ghost_item.setZValue(10001)
            self.scene.addItem(self._comment_drag_ghost_item)

        if self._comment_drag_ghost_item:
            br = self._comment_drag_ghost_item.boundingRect()
            self._comment_drag_ghost_item.setPos(scene_pos.x() - br.width() / 2.0, scene_pos.y() - br.height() / 2.0)

    def _finalize_comment_drag(self, scene_pos: QPointF):
        """Sürüklenen yorumu yeni bırakılan konuma taşır ve PDF annot koordinatlarını günceller."""
        if not self._dragged_comment_annot or self._dragged_comment_page is None or not self.doc:
            return
        page_idx = self._dragged_comment_page
        p_info = self.page_positions.get(page_idx)
        if not p_info:
            return
        scale = self.base_render_dpi
        pleft = p_info.get('left', 0.0)
        ptop = p_info['top']
        page = self.doc[page_idx]

        pdf_x = (scene_pos.x() - pleft) / scale
        pdf_y = (scene_pos.y() - ptop) / scale

        orig_rect = self._dragged_comment_start_rect or self._dragged_comment_annot.rect
        w = max(16.0, orig_rect.width)
        h = max(16.0, orig_rect.height)

        new_x0 = pdf_x - w / 2.0
        new_y0 = pdf_y - h / 2.0
        page_w = page.rect.width
        page_h = page.rect.height

        new_x0 = max(0.0, min(new_x0, page_w - w))
        new_y0 = max(0.0, min(new_y0, page_h - h))
        new_rect = fitz.Rect(new_x0, new_y0, new_x0 + w, new_y0 + h)

        try:
            target_annot = None
            if getattr(self, '_dragged_comment_xref', None):
                target_annot = page.load_annot(self._dragged_comment_xref)
            elif hasattr(self._dragged_comment_annot, 'xref'):
                target_annot = page.load_annot(self._dragged_comment_annot.xref)
            else:
                target_annot = self._dragged_comment_annot

            target_annot.set_rect(new_rect)
            target_annot.update()
            self.set_modified(True)
            self.render_all_pages()
            if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
                self.main_window.modern_right_sidebar.load_comments()
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(
                    LanguageManager.tr("comment_moved_msg", page=page_idx + 1), 3500
                )
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _cleanup_comment_drag(self):
        """Yorum sürükleme durumunu ve sahnedeki hayalet simgeyi temizler."""
        if hasattr(self, '_comment_drag_ghost_item') and self._comment_drag_ghost_item:
            try:
                self.scene.removeItem(self._comment_drag_ghost_item)
            except Exception:
                pass
            self._comment_drag_ghost_item = None
        self._dragged_comment_annot = None
        self._dragged_comment_xref = None
        self._dragged_comment_page = None
        self._dragged_comment_start_scene_pos = None
        self._dragged_comment_start_rect = None
        self._dragged_comment_is_dragging = False
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'update_viewport_cursor'):
            self.main_window.update_viewport_cursor()

    def _open_comment_dialog_for_annot(self, annot, vp_pos: QPoint):
        """Mevcut bir yorumu düzenlemek için AuraCommentInputDialog açar."""
        if not annot:
            return
        try:
            target_annot = annot
            if hasattr(annot, 'xref') and self.doc:
                for p_idx in range(len(self.doc)):
                    try:
                        p = self.doc[p_idx]
                        loaded = p.load_annot(annot.xref)
                        if loaded:
                            target_annot = loaded
                            break
                    except Exception:
                        pass
            info = target_annot.info or {}
            c_text = info.get("content", "") or target_annot.get_text() or ""
            from src.ui.dialogs.settings_dialog import get_effective_author_name
            c_auth = (info.get("title", "") or "").strip()
            if not c_auth or c_auth.lower() in ("kullanıcı", "kullanici", "user", "admin"):
                c_auth = get_effective_author_name()
            from src.ui.dialogs.comment_dialog import AuraCommentInputDialog
            dlg = AuraCommentInputDialog(self.window(), initial_text=c_text, initial_author=c_auth)
            g_pos = self.view.viewport().mapToGlobal(vp_pos)
            screen = QApplication.primaryScreen().availableGeometry()
            dx = min(g_pos.x() + 10, screen.right() - 400)
            dy = min(g_pos.y() + 10, screen.bottom() - 340)
            dlg.move(max(screen.left() + 20, dx), max(screen.top() + 20, dy))
            if dlg.exec():
                n_text, n_auth, hex_color = dlg.get_comment_data()
                if n_text:
                    target_annot.set_info(title=n_auth, content=n_text)
                    if hex_color:
                        qc = QColor(hex_color)
                        target_annot.set_colors(stroke=(qc.redF(), qc.greenF(), qc.blueF()))
                    target_annot.update()
                    self.set_modified(True)
                    self.render_all_pages()
                    if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
                        self.main_window.modern_right_sidebar.load_comments()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def start_stamp_placement(self, image_bytes: bytes, title: str = "Damga",
                              default_w: float = 30.0, default_h: float = 30.0,
                              pixmap: Optional[QPixmap] = None, symbol_type: str = "stamp"):
        """E-İmza veya sembol damgalarını fare imleci ile belgeye yerleştirme modunu başlatır."""
        self.clear_pending_stamp()
        self.pending_stamp = {
            'bytes': image_bytes,
            'title': title,
            'w': default_w,
            'h': default_h,
            'pixmap': pixmap,
            'type': symbol_type
        }
        if pixmap and not pixmap.isNull():
            target_w = max(16, int(default_w * self.base_render_dpi))
            target_h = max(16, int(default_h * self.base_render_dpi))
            scaled_pix = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._stamp_ghost_item = QGraphicsPixmapItem(scaled_pix)
            self._stamp_ghost_item.setOpacity(0.70)
            self._stamp_ghost_item.setZValue(10000)
            self.scene.addItem(self._stamp_ghost_item)
            vp_pos = self.view.mapFromGlobal(QCursor.pos())
            if self.view.viewport().rect().contains(vp_pos):
                s_pos = self.view.mapToScene(vp_pos)
                self._update_stamp_ghost(s_pos)

        self.view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
            hint = LanguageManager.tr("stamp_place_hint", title=title)
            self.main_window.statusBar().showMessage(hint, 10000)

    def _update_stamp_ghost(self, scene_pos: QPointF):
        """Damga yerleştirme hayalet öğesinin sahne konumunu günceller."""
        if hasattr(self, '_stamp_ghost_item') and self._stamp_ghost_item:
            br = self._stamp_ghost_item.boundingRect()
            self._stamp_ghost_item.setPos(scene_pos.x() - br.width() / 2.0, scene_pos.y() - br.height() / 2.0)

    def clear_pending_stamp(self):
        """Bekleyen damga yerleştirme modunu ve sahnedeki hayaleti iptal eder."""
        if hasattr(self, '_stamp_ghost_item') and self._stamp_ghost_item:
            try:
                self.scene.removeItem(self._stamp_ghost_item)
            except Exception:
                pass
            self._stamp_ghost_item = None
        self.pending_stamp = None
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'modern_left_sidebar') and hasattr(self.main_window.modern_left_sidebar, 'fill_sign_drawer'):
            self.main_window.modern_left_sidebar.fill_sign_drawer.clear_active_state()
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'update_viewport_cursor'):
            self.main_window.update_viewport_cursor()
        else:
            self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    # --- Sayfa Yönetimi ---
    @property
    def current_page(self) -> int:
        return getattr(self, 'current_page_idx', 0)

    @current_page.setter
    def current_page(self, page_idx: int):
        self.current_page_idx = page_idx

    @property
    def total_pages(self) -> int:
        return len(self.doc) if self.doc is not None else 0

    @total_pages.setter
    def total_pages(self, val: int):
        pass

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
                p_info = self.page_positions[page_idx]
                p_left = p_info.get('left', 0.0)
                p_width = p_info.get('width', 0.0)
                p_top = p_info.get('top', 0.0)
                page_center_x = p_left + p_width / 2.0
                vp_h = self.view.viewport().height()
                zoom = self.zoom_level if self.zoom_level > 0 else 1.0
                center_y = p_top + (vp_h / (2.0 * zoom))
                self.view.centerOn(page_center_x, center_y)
            self.record_nav_position()
            self.update_current_page_indicator()

    def scroll_to_page(self, page_idx):
        self.go_to_page(page_idx)

    def get_page_preview_pixmap(self, page_idx: int, max_width: float = 190.0, max_height: float = 230.0) -> Optional[QPixmap]:
        """Sayfanın canlı çizimler, notlar, vurgulayıcılar ve eklemeler dahil yüksek kaliteli küçük resim önizlemesini üretir."""
        if not self.doc or getattr(self.doc, 'is_closed', False):
            return None
        if page_idx < 0 or page_idx >= len(self.doc):
            return None

        # Sayfa boyutları
        pinfo = self.page_positions.get(page_idx) if hasattr(self, 'page_positions') else None
        if pinfo:
            pw = max(1.0, float(pinfo.get('width', 1.0)))
            ph = max(1.0, float(pinfo.get('height', 1.0)))
        else:
            try:
                page = self.doc[page_idx]
                pw = max(1.0, float(page.rect.width))
                ph = max(1.0, float(page.rect.height))
            except Exception:
                return None

        scale = min(max_width / pw, max_height / ph)
        scale = max(0.05, min(scale, 1.5))
        thumb_w = max(20, int(pw * scale))
        thumb_h = max(20, int(ph * scale))

        img = None

        # 1. Canlı çizimler, notlar ve ek açıklamalarla sahneden (QGraphicsScene) render et
        if pinfo and hasattr(self, 'scene') and self.scene:
            laser = getattr(self, 'laser_pointer_item', None)
            was_laser_vis = False
            try:
                if laser and laser.isVisible():
                    was_laser_vis = True
                    laser.setVisible(False)
            except Exception:
                laser = None

            sel_item = getattr(self, 'selection_item', None)
            was_sel_vis = False
            try:
                if sel_item and sel_item.isVisible():
                    was_sel_vis = True
                    sel_item.setVisible(False)
            except Exception:
                sel_item = None

            ribbon = None
            was_ribbon_vis = False
            try:
                ribbon = getattr(self, 'bookmark_ribbon_items', {}).get(page_idx, None)
                if ribbon and ribbon.isVisible():
                    was_ribbon_vis = True
                    ribbon.setVisible(False)
            except Exception:
                ribbon = None

            hover_item = getattr(self, 'direct_edit_hover_item', None)
            was_hover_vis = False
            try:
                if hover_item and hover_item.isVisible():
                    was_hover_vis = True
                    hover_item.setVisible(False)
            except Exception:
                hover_item = None

            sel_highlights = list(getattr(self, 'selection_highlight_items', []))
            vis_highlights = []
            for h_item in sel_highlights:
                try:
                    if h_item and h_item.isVisible():
                        h_item.setVisible(False)
                        vis_highlights.append(h_item)
                except Exception:
                    pass

            selected_items = self.scene.selectedItems() if self.scene else []
            for sit in selected_items:
                try:
                    sit.setSelected(False)
                except Exception:
                    pass

            src_rect = QRectF(pinfo.get('left', 0.0), pinfo['top'], pinfo['width'], pinfo['height'])

            try:
                pix_item = pinfo.get('item')
                has_valid_item_pix = False
                if pix_item:
                    try:
                        has_valid_item_pix = not pix_item.pixmap().isNull()
                    except (RuntimeError, AttributeError):
                        has_valid_item_pix = False

                if has_valid_item_pix:
                    # Sayfa sahnede aktif ve çizilmiş: Doğrudan sahneyi render et
                    img = QImage(thumb_w, thumb_h, QImage.Format.Format_ARGB32_Premultiplied)
                    img.fill(QColor(255, 255, 255))
                    painter = QPainter(img)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    self.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                    painter.end()
                else:
                    # Sayfa henüz ekranda çizilmemişse: PyMuPDF tabanını oluşturup sahnedeki çizimleri üstüne çiz
                    page = self.doc[page_idx]
                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    base_img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                    img = base_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)

                    bg_rect = pinfo.get('bg_rect')
                    was_bg_vis = False
                    try:
                        if bg_rect and bg_rect.isVisible():
                            was_bg_vis = True
                            bg_rect.setVisible(False)
                    except Exception:
                        bg_rect = None

                    was_pix_vis = False
                    try:
                        if pix_item and pix_item.isVisible():
                            was_pix_vis = True
                            pix_item.setVisible(False)
                    except Exception:
                        pix_item = None

                    painter = QPainter(img)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    try:
                        self.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                    finally:
                        painter.end()
                        if bg_rect and was_bg_vis:
                            try:
                                bg_rect.setVisible(True)
                            except Exception:
                                pass
                        if pix_item and was_pix_vis:
                            try:
                                pix_item.setVisible(True)
                            except Exception:
                                pass
            except Exception:
                img = None
            finally:
                if laser and was_laser_vis:
                    try:
                        laser.setVisible(True)
                    except Exception:
                        pass
                if sel_item and was_sel_vis:
                    try:
                        sel_item.setVisible(True)
                    except Exception:
                        pass
                if ribbon and was_ribbon_vis:
                    try:
                        ribbon.setVisible(True)
                    except Exception:
                        pass
                if hover_item and was_hover_vis:
                    try:
                        hover_item.setVisible(True)
                    except Exception:
                        pass
                for h_item in vis_highlights:
                    try:
                        h_item.setVisible(True)
                    except Exception:
                        pass
                for sit in selected_items:
                    try:
                        sit.setSelected(True)
                    except Exception:
                        pass

        # 2. Eğer sahneden render alınamadıysa PyMuPDF ile taban sayfayı render et
        if img is None:
            try:
                page = self.doc[page_idx]
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            except Exception:
                return None

        return QPixmap.fromImage(img)

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

    def auto_scroll_during_drag(self, scene_pos, page_idx=None):
        """
        Kullanıcı bir öğeyi (görsel, tablo, metin kutusu vb.) sürüklerken,
        fare imleci viewport sınırlarına (kenarlara 50px kala) yaklaştığında
        görünümü otomatik olarak o yönde kademeli ve yavaşça kaydırır.
        Özellikle yüksek zoom seviyelerinde veya sayfa sınırlarında kusursuz,
        kontrollü ve yavaş kaydırma deneyimi sağlar. İlgili sayfanın dışına taşmayı engeller.
        """
        if not hasattr(self, 'view') or not self.view:
            return
        vp = self.view.viewport()
        if not vp:
            return
        try:
            import time
            now = time.time()
            if now - getattr(self, '_last_drag_scroll_time', 0.0) < 0.025:
                return
            self._last_drag_scroll_time = now

            vp_pt = self.view.mapFromScene(scene_pos)
            vp_w = vp.width()
            vp_h = vp.height()
            margin = 50

            h_bar = self.view.horizontalScrollBar()
            v_bar = self.view.verticalScrollBar()

            page_bounds = None
            if page_idx is not None and hasattr(self, 'page_positions') and page_idx in self.page_positions:
                page_bounds = self.page_positions[page_idx]

            # Dikey kaydırma (Aşağı / Yukarı)
            if vp_pt.y() > vp_h - margin:
                can_scroll_down = True
                if page_bounds:
                    bottom_scene_y = self.view.mapToScene(QPoint(0, vp_h)).y()
                    page_bottom = page_bounds.get('bottom', page_bounds.get('top', 0) + page_bounds.get('height', 0))
                    if bottom_scene_y >= page_bottom + 20:
                        can_scroll_down = False
                if can_scroll_down:
                    depth = min(1.0, max(0.0, (vp_pt.y() - (vp_h - margin)) / float(margin)))
                    step = int(round(3 + depth * 7))
                    v_bar.setValue(v_bar.value() + step)

            elif vp_pt.y() < margin:
                can_scroll_up = True
                if page_bounds:
                    top_scene_y = self.view.mapToScene(QPoint(0, 0)).y()
                    page_top = page_bounds.get('top', 0)
                    if top_scene_y <= page_top - 20:
                        can_scroll_up = False
                if can_scroll_up:
                    depth = min(1.0, max(0.0, (margin - vp_pt.y()) / float(margin)))
                    step = int(round(3 + depth * 7))
                    v_bar.setValue(v_bar.value() - step)

            # Yatay kaydırma (Sağ / Sol)
            if vp_pt.x() > vp_w - margin:
                can_scroll_right = True
                if page_bounds:
                    right_scene_x = self.view.mapToScene(QPoint(vp_w, 0)).x()
                    page_right = page_bounds.get('right', page_bounds.get('left', 0) + page_bounds.get('width', 0))
                    if right_scene_x >= page_right + 20:
                        can_scroll_right = False
                if can_scroll_right:
                    depth = min(1.0, max(0.0, (vp_pt.x() - (vp_w - margin)) / float(margin)))
                    step = int(round(3 + depth * 7))
                    h_bar.setValue(h_bar.value() + step)

            elif vp_pt.x() < margin:
                can_scroll_left = True
                if page_bounds:
                    left_scene_x = self.view.mapToScene(QPoint(0, 0)).x()
                    page_left = page_bounds.get('left', 0)
                    if left_scene_x <= page_left - 20:
                        can_scroll_left = False
                if can_scroll_left:
                    depth = min(1.0, max(0.0, (margin - vp_pt.x()) / float(margin)))
                    step = int(round(3 + depth * 7))
                    h_bar.setValue(h_bar.value() - step)
        except Exception:
            pass

    def update_current_page_indicator(self):
        if self.doc is None or not self.page_positions: return
        center_y = self.view.mapToScene(self.view.viewport().rect().center()).y()
        new_page_idx = self.current_page_idx  # başlangıç değeri
        for idx, bounds in self.page_positions.items():
            if bounds['top'] <= center_y <= bounds['bottom']:
                new_page_idx = idx
                break

        # Sayfa değişmediyse UI güncellemelerini atla (scroll sırasında gereksiz işlemi önler)
        if new_page_idx == self.current_page_idx and self.current_page_idx >= 0:
            return
        self.current_page_idx = new_page_idx

        if self.main_window and hasattr(self.main_window, 'get_current_tab_doc') and self == self.main_window.get_current_tab_doc():
            if getattr(self.main_window, 'txt_page', None) and not self.main_window.txt_page.hasFocus():
                self.main_window.txt_page.setText(str(self.current_page_idx + 1))
            if getattr(self.main_window, 'thumbnails_dock', None) and hasattr(self.main_window.thumbnails_dock, 'select_page'):
                self.main_window.thumbnails_dock.select_page(self.current_page_idx)
            if getattr(self.main_window, 'modern_right_sidebar', None) and hasattr(self.main_window.modern_right_sidebar, 'select_page'):
                self.main_window.modern_right_sidebar.select_page(self.current_page_idx)
            total_p = len(self.doc) if self.doc is not None else 1
            if getattr(self.main_window, 'modern_header_bar', None):
                self.main_window.modern_header_bar.update_page_info(self.current_page_idx + 1, total_p)
            if hasattr(self.main_window, 'isFullScreen') and self.main_window.isFullScreen():
                lbl_str = None
                try:
                    if self.doc and hasattr(self.doc[self.current_page_idx], 'get_label'):
                        custom_lbl = self.doc[self.current_page_idx].get_label()
                        if custom_lbl and custom_lbl != str(self.current_page_idx + 1):
                            lbl_str = custom_lbl
                except Exception:
                    pass
                if hasattr(self.main_window, 'show_fullscreen_page_osd'):
                    self.main_window.show_fullscreen_page_osd(self.current_page_idx + 1, total_p, lbl_str)
                if hasattr(self.main_window, 'fullscreen_reading_hud') and self.main_window.fullscreen_reading_hud is not None:
                    self.main_window.fullscreen_reading_hud.update_state()

    def render_all_pages(self):
        """Tüm sayfaları yeniden başlatır, görünür olanları çizer ve arayüz göstergelerini günceller."""
        if self.doc is None:
            return

        if len(self.doc) > 0:
            if self.current_page_idx >= len(self.doc):
                self.current_page_idx = max(0, len(self.doc) - 1)
        else:
            self.current_page_idx = 0

        self.render_pages_init()
        self.rerender_visible_pages(force=True)

        if hasattr(self, 'update_tab_title'):
            try:
                self.update_tab_title()
            except Exception:
                pass

        if getattr(self.main_window, 'lbl_total', None):
            self.main_window.lbl_total.setText(LanguageManager.tr("page_of", total=len(self.doc)))
        if getattr(self.main_window, 'txt_page', None):
            self.main_window.txt_page.setText(str(self.current_page_idx + 1 if len(self.doc) > 0 else 0))
        if getattr(self.main_window, 'modern_header_bar', None):
            try:
                self.main_window.modern_header_bar.update_page_info(self.current_page_idx + 1, len(self.doc))
            except Exception:
                pass
        if getattr(self.main_window, 'modern_right_sidebar', None):
            try:
                if self.main_window.modern_right_sidebar.isVisible():
                    self.main_window.modern_right_sidebar.load_thumbnails()
            except Exception:
                pass
        if getattr(self.main_window, 'thumbnails_dock', None):
            try:
                self.main_window.thumbnails_dock.is_loaded = False
                if self.main_window.thumbnails_dock.isVisible():
                    self.main_window.thumbnails_dock.load_thumbnails_lazy()
            except Exception:
                pass

    def rotate_page(self, page_idx: int, angle: int = 90):
        """Belirtilen indeksteki tek sayfayı döndürür ve görünümü yeniler."""
        if self.doc is None or not (0 <= page_idx < len(self.doc)):
            return
        page = self.doc[page_idx]
        page.set_rotation((page.rotation + angle) % 360)
        self.set_modified(True)
        self.render_all_pages()

    def rotate_all_pages(self):
        """Belgedeki tüm sayfaları 90 derece saat yönünde döndürür ve görünümü yeniler."""
        if self.doc is None:
            return
        for page in self.doc:
            page.set_rotation((page.rotation + 90) % 360)
        self.set_modified(True)
        self.render_all_pages()

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

                elif d.get("type") == "text_markup":
                    scale = self.base_render_dpi
                    rects = d.get("rects", [])
                    markup_type = d.get("markup_type", "highlight")
                    hit_radius = radius + 6.0
                    for s_pt in sample_points:
                        check_rect = QRectF(s_pt.x() - hit_radius, s_pt.y() - hit_radius, hit_radius * 2, hit_radius * 2)
                        for r in rects:
                            sx0 = r[0] * scale + page_left
                            sy0 = r[1] * scale + page_top
                            sw = (r[2] - r[0]) * scale
                            sh = (r[3] - r[1]) * scale
                            if markup_type == "highlight":
                                m_rect = QRectF(sx0, sy0, sw, sh)
                            elif markup_type == "underline":
                                m_rect = QRectF(sx0, (r[3] - 2.0) * scale + page_top, sw, 4.0 * scale)
                            elif markup_type == "strikeout":
                                m_rect = QRectF(sx0, ((r[1] + r[3]) / 2.0 - 2.0) * scale + page_top, sw, 4.0 * scale)
                            else:
                                m_rect = QRectF(sx0, sy0, sw, sh)

                            if m_rect.intersects(check_rect):
                                hit = True
                                break
                        if hit:
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
                elif record["type"] == "text_markup":
                    if item and hasattr(item, 'path'):
                        target_path = item.path()
                    else:
                        target_path = QPainterPath()
                        for r in record.get("rects", []):
                            target_path.addRect(QRectF(
                                r[0] * self.base_render_dpi + page_left,
                                r[1] * self.base_render_dpi + top_y,
                                (r[2] - r[0]) * self.base_render_dpi,
                                (r[3] - r[1]) * self.base_render_dpi
                            ))
                else:
                    new_drawings.append(record)
                    continue

                if not target_path.intersects(eraser_path):
                    new_drawings.append(record)
                    continue

                if record["type"] == "text_markup":
                    erased_any = True
                    if item.scene() == self.scene:
                        self.scene.removeItem(item)
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
                        if self.main_window and hasattr(self.main_window, 'handle_dropped_urls'):
                            self.main_window.handle_dropped_urls(pdf_urls)
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
                    fw = QApplication.focusWidget()
                    focus_item = self.scene.focusItem() if hasattr(self, 'scene') and self.scene else None
                    is_scene_text_editing = False
                    if focus_item is not None:
                        if isinstance(focus_item, QGraphicsTextItem):
                            is_scene_text_editing = bool(focus_item.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction)
                    if not is_scene_text_editing and hasattr(self, 'active_text_item') and self.active_text_item is not None:
                        is_scene_text_editing = bool(getattr(self.active_text_item, 'textInteractionFlags', lambda: Qt.TextInteractionFlag.NoTextInteraction)() & Qt.TextInteractionFlag.TextEditorInteraction)

                    is_text_edit = (
                        isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)) or
                        is_scene_text_editing or
                        (getattr(self, 'direct_edit_editor', None) is not None and getattr(self.direct_edit_editor, 'isVisible', lambda: False)())
                    )
                    if not is_text_edit:
                        self.space_pan_active = True
                        self.view.viewport().setCursor(CursorFactory.get_pan_cursor())
                        return True
            elif event.type() == QEvent.Type.KeyRelease:
                if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
                    if getattr(self, 'space_pan_active', False):
                        self.space_pan_active = False
                        self.is_panning = False
                        self.pan_last_viewport_pos = None
                        if self.main_window and hasattr(self.main_window, 'update_viewport_cursor'):
                            self.main_window.update_viewport_cursor()
                        return True
            elif event.type() in (QEvent.Type.FocusOut, QEvent.Type.WindowDeactivate):
                if getattr(self, 'space_pan_active', False):
                    self.space_pan_active = False
                    self.is_panning = False
                    self.pan_last_viewport_pos = None
                    if self.main_window and hasattr(self.main_window, 'update_viewport_cursor'):
                        self.main_window.update_viewport_cursor()

        if source != self.view.viewport() or self.doc is None:
            return super().eventFilter(source, event)
        tool = getattr(self.main_window, 'current_tool', 'hand') if self.main_window else 'hand'

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

        # Klavyeden Escape tuşu ile bekleyen damga, metin kutusu veya yorum sürüklemeyi iptal et
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            if getattr(self, 'active_text_item', None):
                act_item = self.active_text_item
                act_item.clearFocus()
                act_item.setSelected(False)
                if hasattr(act_item, 'move_handle') and act_item.move_handle:
                    act_item.move_handle.hide()
                if hasattr(self, 'text_floating_hud') and self.text_floating_hud:
                    self.text_floating_hud.hide()
                self.active_text_item = None
                if hasattr(self, 'view') and self.view:
                    self.view.viewport().update()
                return True
            if getattr(self, 'pending_form_field_type', None):
                self.cancel_form_field_placement()
                return True
            if getattr(self, 'pending_stamp', None):
                self.clear_pending_stamp()
                return True
            if getattr(self, '_dragged_comment_annot', None):
                self._cleanup_comment_drag()
                return True

        # Bekleyen Form Alanı (Form Field) yerleştirme modu aktifse fare olaylarını yakala
        if getattr(self, 'pending_form_field_type', None):
            if event.type() == QEvent.Type.MouseMove:
                pos = self.view.mapToScene(event.pos())
                if getattr(self, '_form_ghost_item', None):
                    self._form_ghost_item.setPos(pos)
                return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = self.view.mapToScene(event.pos())
                    p_idx = self.get_page_at_pos(pos)
                    if p_idx is None:
                        p_idx = max(0, min(getattr(self, 'current_page_idx', 0), len(self.doc) - 1)) if self.doc else 0
                    if p_idx is not None and self.doc and p_idx < len(self.doc):
                        scale = self.base_render_dpi
                        p_info = self.page_positions.get(p_idx, {})
                        pdf_x0 = (pos.x() - p_info.get('left', 0.0)) / scale
                        pdf_y0 = (pos.y() - p_info.get('top', 0.0)) / scale
                        ghost_w = self._form_ghost_item.w if getattr(self, '_form_ghost_item', None) else 160.0
                        ghost_h = self._form_ghost_item.h if getattr(self, '_form_ghost_item', None) else 28.0
                        pw = ghost_w / scale
                        ph = ghost_h / scale
                        p_rect = self.doc[p_idx].rect
                        pdf_x0 = max(0.0, min(pdf_x0, p_rect.width - pw))
                        pdf_y0 = max(0.0, min(pdf_y0, p_rect.height - ph))
                        rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x0 + pw, pdf_y0 + ph)
                        f_type = self.pending_form_field_type
                        self.cancel_form_field_placement()
                        fname = self.add_acroform_field(f_type, page_idx=p_idx, rect=rect)
                        main_win = getattr(self, 'main_window', None)
                        if main_win and hasattr(main_win, 'modern_left_sidebar'):
                            drawer = getattr(main_win.modern_left_sidebar, 'prepare_form_drawer', None)
                            if drawer:
                                drawer.refresh_fields_list()
                                if fname:
                                    drawer.select_field_in_list(fname, p_idx)
                        return True
                elif event.button() == Qt.MouseButton.RightButton:
                    self.cancel_form_field_placement()
                    return True

        # Form Tasarım Modu aktifken Delete / Backspace ile silme
        if getattr(self, 'is_form_design_mode', False):
            if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                sel = [it for it in getattr(self, 'form_designer_items', []) if it.isSelected()]
                if sel:
                    for it in sel:
                        self.delete_form_field(it.page_idx, it.field_name)
                    return True

        # Seçili nesneleri (Resim, Metin Kutusu, Tablo, GIF, Ses/Video, Çizim) Delete / Backspace ile silme
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            active_txt = getattr(self, 'active_text_item', None)
            is_typing = False
            if active_txt:
                flags = getattr(active_txt, 'textInteractionFlags', lambda: Qt.TextInteractionFlag.NoTextInteraction)()
                if (flags != Qt.TextInteractionFlag.NoTextInteraction):
                    is_typing = True
            if not is_typing:
                has_scene_sel = bool(self.scene and self.scene.selectedItems())
                has_drawings_sel = bool(getattr(self, 'selected_drawings', None))
                has_measure_sel = any(getattr(m, 'isSelected', lambda: False)() for m in getattr(self, 'measurements', []))
                if has_scene_sel or has_drawings_sel or has_measure_sel:
                    self.delete_selected_items()
                    return True

        # Bekleyen Damga (Stamp) yerleştirme modu aktifse fare olaylarını yakala
        if getattr(self, 'pending_stamp', None):
            if event.type() == QEvent.Type.MouseMove:
                pos = self.view.mapToScene(event.pos())
                self._update_stamp_ghost(pos)
                return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = self.view.mapToScene(event.pos())
                    p_idx = self.get_page_at_pos(pos)
                    if p_idx is not None:
                        stamp = self.pending_stamp
                        self.add_image_media(
                            stamp['bytes'],
                            title=stamp.get('title', 'Görsel'),
                            page_idx=p_idx,
                            pos=pos,
                            default_w=stamp.get('w'),
                            default_h=stamp.get('h')
                        )
                        self.clear_pending_stamp()
                        return True
                elif event.button() == Qt.MouseButton.RightButton:
                    self.clear_pending_stamp()
                    return True

        if tool == 'direct_edit':
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
                try:
                    self._handle_direct_edit_mouse_move(pos)
                except Exception:
                    pass
                return True

            elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = self.view.mapToScene(event.pos())
                return self._handle_direct_edit_mouse_press(pos, event.pos())

            return super().eventFilter(source, event)

        if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
            pos = self.view.mapToScene(event.pos())
            _, c_annot, _ = self.get_comment_annot_at_pos(pos)
            if c_annot:
                self._open_comment_dialog_for_annot(c_annot, event.pos())
                return True

        if tool == 'select':
            # 1. Klavye Kısayolları (Ctrl+C ile panoya kopyalama)
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    if getattr(self, 'selected_text', ''):
                        self.copy_selected_text()
                        return True

            # 2. Fare Gezinme (Hover): Yorumları ve Köprüleri (Hyperlinks) algıla
            elif event.type() == QEvent.Type.MouseMove and not (event.buttons() & Qt.MouseButton.LeftButton):
                pos = self.view.mapToScene(event.pos())
                _, c_annot, _ = self.get_comment_annot_at_pos(pos)
                if c_annot:
                    self.view.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
                    return True
                self._handle_select_hover(pos)

            # 3. Fare Tıklama (Press): Yorum sürükleme, köprü tıklaması veya metin seçimi başlatma
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = self.view.mapToScene(event.pos())
                    # Yorum ikonu tıklandıysa doğrudan sürükleme başlat
                    c_p_idx, c_annot, c_rect = self.get_comment_annot_at_pos(pos)
                    if c_annot:
                        self._dragged_comment_annot = c_annot
                        self._dragged_comment_xref = getattr(c_annot, 'xref', None)
                        self._dragged_comment_page = c_p_idx
                        self._dragged_comment_start_scene_pos = pos
                        self._dragged_comment_start_rect = fitz.Rect(c_rect)
                        self._dragged_comment_is_dragging = False
                        self.view.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
                        return True

                    # Önce tıklanabilir bağlantı var mı kontrol et
                    if self._handle_link_click(pos):
                        return True
                    # Çizim, metin kutusu veya medya nesnesi tıklandıysa standart seçime/etkileşime bırak
                    items = self.scene.items(pos)
                    from src.document.media_items import (PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem)
                    from src.ui.widgets import TextMoveHandleItem
                    is_interactive_target = any(
                        isinstance(it, (EditableInlineTextItem, BookmarkRibbonItem, PDFTableItem, PDFResizableImageItem, PDFAudioItem, PDFVideoItem, TextMoveHandleItem))
                        or hasattr(it, 'parent_text_item')
                        or isinstance(getattr(it, 'parentItem', lambda: None)(), EditableInlineTextItem)
                        for it in items
                    )
                    if is_interactive_target:
                        self.clear_text_selection()
                        return super().eventFilter(source, event)
                    is_on_handle = bool(self.active_text_item and hasattr(self.active_text_item, 'move_handle') and self.active_text_item.move_handle in items)
                    if self.active_text_item and self.active_text_item not in items and not is_on_handle:
                        if hasattr(self.active_text_item, 'finish_editing'):
                            self.active_text_item.finish_editing()
                        else:
                            self.active_text_item.clearFocus()
                    # Metin seçimini başlat
                    self._start_text_selection(pos)
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    if getattr(self, '_dragged_comment_annot', None):
                        self._cleanup_comment_drag()
                        return True
                    if getattr(self, 'selected_text', ''):
                        self._show_text_context_menu(self.view.viewport().mapToGlobal(event.pos()))
                        return True

            # 4. Fare Sürükleme (Move with Left Button): Yorum taşıma veya metin seçimi güncelleme
            elif event.type() == QEvent.Type.MouseMove and (event.buttons() & Qt.MouseButton.LeftButton):
                pos = self.view.mapToScene(event.pos())
                if getattr(self, '_dragged_comment_annot', None):
                    diff = (pos - self._dragged_comment_start_scene_pos).manhattanLength()
                    if diff > 3:
                        self._dragged_comment_is_dragging = True
                    if self._dragged_comment_is_dragging:
                        self._update_comment_drag_ghost(pos)
                    return True
                if getattr(self, 'is_selecting_text', False):
                    self._update_text_selection(pos)
                    return True

            # 5. Fare Bırakma (Release): Yorum taşımayı tamamla veya metin seçimini bitir
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                pos = self.view.mapToScene(event.pos())
                if getattr(self, '_dragged_comment_annot', None):
                    if self._dragged_comment_is_dragging:
                        self._finalize_comment_drag(pos)
                    self._cleanup_comment_drag()
                    return True
                if getattr(self, 'is_selecting_text', False):
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
                    return True

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
                    try:
                        self._last_hovered_ribbon.set_hovered(False)
                    except Exception:
                        pass
                    self._last_hovered_ribbon = None
                return False

        # Fare olaylarını alt fonksiyonlara yönlendir (Daha temiz kod)
        if event.type() == event.Type.MouseButtonPress:
            if hasattr(self.main_window, 'handle_mouse_shortcut') and self.main_window.handle_mouse_shortcut(event):
                event.accept()
                return True
            if event.button() == Qt.MouseButton.LeftButton:
                pos = self.view.mapToScene(event.pos())
                from src.ui.widgets import TextMoveHandleItem
                try:
                    hit_items = self.scene.items(pos)
                    if any(isinstance(it, (BookmarkRibbonItem, TextMoveHandleItem)) or hasattr(it, 'parent_text_item') for it in hit_items):
                        return super().eventFilter(source, event)
                except Exception:
                    pass
                return self._handle_mouse_press(event, tool, source=source)
            elif event.button() == Qt.MouseButton.RightButton:
                pos = self.view.mapToScene(event.pos())
                try:
                    for it in self.scene.items(pos):
                        if isinstance(it, BookmarkRibbonItem):
                            g_pos = self.view.viewport().mapToGlobal(event.pos())
                            it.show_context_menu(g_pos)
                            return True
                except Exception:
                    pass
                g_pos = self.view.viewport().mapToGlobal(event.pos())
                if self.show_tool_quick_menu(g_pos, tool):
                    return True
        elif event.type() == event.Type.MouseMove:
            if event.buttons() & Qt.MouseButton.LeftButton:
                if self.scene.mouseGrabberItem() is not None:
                    return super().eventFilter(source, event)
                if self.current_path_item is not None:
                    return self._handle_mouse_move(event, tool)
                pos = self.view.mapToScene(event.pos())
                try:
                    if self.bookmark_ribbon_items and any(isinstance(it, BookmarkRibbonItem) for it in self.scene.items(pos)):
                        return super().eventFilter(source, event)
                except Exception:
                    pass
                return self._handle_mouse_move(event, tool)
            else:
                self._handle_mouse_hover(event, tool)
        elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self.scene.mouseGrabberItem() is not None:
                return super().eventFilter(source, event)
            if self.current_path_item is not None:
                return self._handle_mouse_release(event, tool)
            pos = self.view.mapToScene(event.pos())
            try:
                if self.bookmark_ribbon_items and any(isinstance(it, BookmarkRibbonItem) for it in self.scene.items(pos)):
                    return super().eventFilter(source, event)
            except Exception:
                pass
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

        act_copy = menu.addAction(ModernIconFactory.icon_copy(), LanguageManager.tr("copy") + " (Ctrl+C)")
        act_hl = menu.addAction(ModernIconFactory.icon_highlighter(), LanguageManager.tr("text_markup_highlight"))
        act_ul = menu.addAction(ModernIconFactory.icon_underline(), LanguageManager.tr("text_markup_underline"))
        act_so = menu.addAction(ModernIconFactory.icon_strikethrough(), LanguageManager.tr("text_markup_strikeout"))
        act_speak = menu.addAction(ModernIconFactory.icon_speech(), LanguageManager.tr("text_read_aloud"))
        menu.addSeparator()
        act_search = menu.addAction(ModernIconFactory.icon_search(), LanguageManager.tr("text_search_google"))
        act_trans = menu.addAction(ModernIconFactory.icon_translate(), LanguageManager.tr("text_translate_google"))

        chosen = menu.exec(global_pos)
        if chosen == act_copy:
            self.copy_selected_text()
        elif chosen == act_hl:
            self.highlight_selected_text()
        elif chosen == act_ul:
            self.underline_selected_text()
        elif chosen == act_so:
            self.strikeout_selected_text()
        elif chosen == act_speak:
            self.speak_selected_text()
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

    def add_text_markup(self, markup_type: str, color=None):
        if not self.selected_text_rects or not self.doc:
            return

        if color is None:
            if markup_type == "highlight":
                color = (1.0, 0.9, 0.2)
            elif markup_type == "underline":
                color = (0.1, 0.5, 0.9)
            elif markup_type == "strikeout":
                color = (0.9, 0.2, 0.2)
            else:
                color = (1.0, 0.9, 0.2)
        elif isinstance(color, QColor):
            color = (color.redF(), color.greenF(), color.blueF())

        alpha = 0.38 if markup_type == "highlight" else 1.0
        width = 2.0

        pages = {}
        for p_idx, s_rect, pdf_rect in self.selected_text_rects:
            pages.setdefault(p_idx, []).append(pdf_rect)

        created_items = []
        for p_idx, rects in pages.items():
            rect_coords = [[r.x0, r.y0, r.x1, r.y1] for r in rects]
            record = {
                "id": uuid.uuid4().hex[:12],
                "type": "text_markup",
                "markup_type": markup_type,
                "page": p_idx,
                "rects": rect_coords,
                "color": color,
                "alpha": alpha,
                "width": width,
                "item_ref": None
            }
            self.drawings.append(record)
            self.restore_drawing_item(record)
            created_items.append(record)
            self.notify_drawings_changed(p_idx)

        if created_items:
            self.push_undo_action({"type": "add", "data": created_items})
            self.set_modified(True)

        self.clear_text_selection()
        self.scene.update()
        self.view.viewport().update()

        if hasattr(self.main_window, 'dock_thumbs') and self.main_window.dock_thumbs:
            self.main_window.dock_thumbs.load_comments()
        elif hasattr(self.main_window, 'thumbnails_dock') and self.main_window.thumbnails_dock:
            self.main_window.thumbnails_dock.load_comments()

    def highlight_selected_text(self, color=(1.0, 0.9, 0.2)):
        self.add_text_markup("highlight", color)

    def underline_selected_text(self, color=(0.1, 0.5, 0.9)):
        self.add_text_markup("underline", color)

    def strikeout_selected_text(self, color=(0.9, 0.2, 0.2)):
        self.add_text_markup("strikeout", color)

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

    def speak_selected_text(self):
        if not getattr(self, 'selected_text', '').strip():
            return
        mw = getattr(self, 'main_window', None)
        if mw and hasattr(mw, 'modern_right_sidebar') and mw.modern_right_sidebar:
            panel_acc = getattr(mw.modern_right_sidebar, 'panel_accessibility', None)
            if panel_acc:
                panel_acc.speak_text(self.selected_text, source_doc=self)
            else:
                se = getattr(mw.modern_right_sidebar, 'speech_engine', None)
                if se:
                    se.speak(self.selected_text)

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
                        chk.setFixedSize(max(18, int(sw)), max(18, int(sh)))
                        chk.setCursor(Qt.CursorShape.PointingHandCursor)
                        ind_w = min(16, max(12, int(sw) - 2))
                        ind_h = min(16, max(12, int(sh) - 2))
                        chk.setStyleSheet(f"""
                            QCheckBox {{
                                background-color: rgba(255, 255, 255, 0.96);
                                border-radius: 3px;
                            }}
                            QCheckBox::indicator {{
                                width: {ind_w}px;
                                height: {ind_h}px;
                                border: 1.5px solid #0284c7;
                                border-radius: 3px;
                                background-color: #ffffff;
                            }}
                            QCheckBox::indicator:checked {{
                                background-color: #0284c7;
                            }}
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
                        rb.setFixedSize(max(18, int(sw)), max(18, int(sh)))
                        rb.setCursor(Qt.CursorShape.PointingHandCursor)
                        ind_w = min(16, max(12, int(sw) - 2))
                        ind_h = min(16, max(12, int(sh) - 2))
                        rb.setStyleSheet(f"""
                            QRadioButton {{
                                background-color: rgba(255, 255, 255, 0.96);
                                border-radius: {ind_w // 2}px;
                            }}
                            QRadioButton::indicator {{
                                width: {ind_w}px;
                                height: {ind_h}px;
                                border: 1.5px solid #0284c7;
                                border-radius: {ind_w // 2}px;
                                background-color: #ffffff;
                            }}
                            QRadioButton::indicator:checked {{
                                background-color: #0284c7;
                            }}
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

    def enter_form_design_mode(self):
        """Form hazırlama / tasarım modunu etkinleştirir."""
        self.is_form_design_mode = True
        for p in getattr(self, 'interactive_form_proxies', []):
            try:
                p.hide()
            except Exception:
                pass

        self.clear_form_designer_items()
        if not self.doc:
            return

        from src.ui.form_builder import AuraFormFieldDesignerItem
        for p_idx in range(len(self.doc)):
            page = self.doc[p_idx]
            p_info = self.page_positions.get(p_idx)
            if not p_info:
                continue
            for w in page.widgets():
                w_type = "text"
                if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    w_type = "checkbox"
                elif w.field_type == getattr(fitz, 'PDF_WIDGET_TYPE_RADIOBUTTON', 4):
                    w_type = "radio"
                elif w.field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX:
                    w_type = "combobox"
                elif w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    w_type = "signature"

                choices = []
                if hasattr(w, 'choice_values') and w.choice_values:
                    choices = list(w.choice_values)

                item = AuraFormFieldDesignerItem(
                    tab_doc=self,
                    page_idx=p_idx,
                    widget_data={
                        "name": w.field_name or f"Field_{w_type}_{p_idx}",
                        "type": w_type,
                        "value": w.field_value,
                        "tooltip": getattr(w, 'tooltip', ""),
                        "readonly": getattr(w, 'is_readonly', False),
                        "required": getattr(w, 'is_required', False),
                        "multiline": getattr(w, 'is_multiline', False),
                        "choices": choices,
                        "font_size": getattr(w, 'text_fontsize', 11.0),
                        "rect": w.rect
                    }
                )
                self.scene.addItem(item)
                self.form_designer_items.append(item)

        # Arka plan pixmap'lerini widget'lar OLMADAN yeniden çiz
        # Böylece öğeler taşındığında veya yeniden boyutlandırıldığında altta donmuş kalıntı kalmaz!
        self.rerender_visible_pages(force=True)

    def exit_form_design_mode(self):
        """Form hazırlama modundan çıkarak etkileşimli doldurma moduna döner."""
        self.is_form_design_mode = False
        self.cancel_form_field_placement()
        self.clear_form_designer_items()
        self._load_interactive_form_widgets()
        self.rerender_visible_pages(force=True)

    def clear_form_designer_items(self):
        for item in getattr(self, 'form_designer_items', []):
            try:
                if item.scene() == self.scene:
                    self.scene.removeItem(item)
            except Exception:
                pass
        self.form_designer_items = []

    def start_form_field_placement(self, field_type: str):
        """Yeni bir form alanı yerleştirmek için fare takip modunu başlatır."""
        if not self.is_form_design_mode:
            self.enter_form_design_mode()

        self.cancel_form_field_placement()
        self.pending_form_field_type = field_type

        dims = {
            "text": (160.0, 28.0),
            "checkbox": (22.0, 22.0),
            "radio": (22.0, 22.0),
            "combobox": (160.0, 28.0),
            "signature": (160.0, 48.0),
        }
        w, h = dims.get(field_type, (160.0, 28.0))

        from src.ui.form_builder import AuraFormFieldGhostItem
        ghost = AuraFormFieldGhostItem(field_type, w=w, h=h)
        self.scene.addItem(ghost)
        self._form_ghost_item = ghost

        self.view.setCursor(Qt.CursorShape.CrossCursor)
        self.view.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def cancel_form_field_placement(self):
        """Bekleyen form alanı yerleştirmesini iptal eder."""
        self.pending_form_field_type = None
        if getattr(self, '_form_ghost_item', None):
            try:
                if self._form_ghost_item.scene() == self.scene:
                    self.scene.removeItem(self._form_ghost_item)
            except Exception:
                pass
            self._form_ghost_item = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.view.viewport().update()

    def select_form_field_on_scene(self, field_name: str, page_idx: int):
        """Sahnedeki ilgili form alanı tasarım öğesini seçer ve odaklar."""
        for item in getattr(self, 'form_designer_items', []):
            if item.page_idx == page_idx and item.field_name == field_name:
                item.setSelected(True)
                self.view.ensureVisible(item)
            else:
                item.setSelected(False)

    def duplicate_form_field(self, designer_item):
        """Seçili form alanını çoğaltır."""
        if not self.doc or designer_item.page_idx >= len(self.doc):
            return
        p_idx = designer_item.page_idx
        page = self.doc[p_idx]
        scale = self.base_render_dpi
        pdf_w = designer_item.w / scale
        pdf_h = designer_item.h / scale

        p_info = self.page_positions.get(p_idx, {})
        orig_x = (designer_item.pos().x() - p_info.get('left', 0.0)) / scale
        orig_y = (designer_item.pos().y() - p_info.get('top', 0.0)) / scale
        p_rect = page.rect
        new_x = min(orig_x + 15.0, p_rect.width - pdf_w)
        new_y = min(orig_y + 35.0, p_rect.height - pdf_h)
        rect = fitz.Rect(new_x, new_y, new_x + pdf_w, new_y + pdf_h)

        fname = self.add_acroform_field(designer_item.field_type, page_idx=p_idx, rect=rect)
        if self.main_window and hasattr(self.main_window, 'modern_left_sidebar'):
            drawer = getattr(self.main_window.modern_left_sidebar, 'prepare_form_drawer', None)
            if drawer:
                drawer.refresh_fields_list()
                if fname:
                    drawer.select_field_in_list(fname, p_idx)

    def add_acroform_field(self, field_type: str, page_idx: Optional[int] = None, rect: Optional[fitz.Rect] = None, name: Optional[str] = None):
        """PDF sayfasına yeni bir etkileşimli form alanı ekler."""
        if not self.doc or len(self.doc) == 0:
            return None
        if page_idx is None:
            page_idx = max(0, min(self.current_page_idx, len(self.doc) - 1))
        page = self.doc[page_idx]

        p_rect = page.rect
        if rect is None:
            cx = p_rect.width / 2.0
            cy = p_rect.height / 3.0
            if field_type == "text":
                rect = fitz.Rect(cx - 80, cy, cx + 80, cy + 24)
            elif field_type in ("checkbox", "radio"):
                rect = fitz.Rect(cx - 10, cy, cx + 10, cy + 20)
            elif field_type == "combobox":
                rect = fitz.Rect(cx - 80, cy, cx + 80, cy + 24)
            elif field_type == "signature":
                rect = fitz.Rect(cx - 80, cy, cx + 80, cy + 45)
            else:
                rect = fitz.Rect(cx - 80, cy, cx + 80, cy + 24)

        existing_names = set()
        for p in self.doc:
            for w in p.widgets():
                if w.field_name:
                    existing_names.add(w.field_name)

        base_name = f"Field_{field_type.capitalize()}"
        idx = 1
        while f"{base_name}_{idx}" in existing_names:
            idx += 1
        final_name = name or f"{base_name}_{idx}"

        widget = fitz.Widget()
        widget.rect = rect
        widget.field_name = final_name

        if field_type == "text":
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_value = ""
        elif field_type == "checkbox":
            widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            widget.field_value = False
        elif field_type == "radio":
            widget.field_type = getattr(fitz, 'PDF_WIDGET_TYPE_RADIOBUTTON', 4)
            widget.field_value = False
        elif field_type == "combobox":
            widget.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
            widget.choice_values = ["Seçenek 1", "Seçenek 2", "Seçenek 3"]
            widget.field_value = "Seçenek 1"
        elif field_type == "signature":
            widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
        else:
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT

        try:
            page.add_widget(widget)
            self.set_modified(True)
            if self.is_form_design_mode:
                from src.ui.form_builder import AuraFormFieldDesignerItem
                choices = list(widget.choice_values) if hasattr(widget, 'choice_values') and widget.choice_values else []
                item = AuraFormFieldDesignerItem(
                    tab_doc=self,
                    page_idx=page_idx,
                    widget_data={
                        "name": final_name,
                        "type": field_type,
                        "value": widget.field_value,
                        "tooltip": getattr(widget, 'tooltip', ""),
                        "readonly": getattr(widget, 'is_readonly', False),
                        "required": getattr(widget, 'is_required', False),
                        "multiline": getattr(widget, 'is_multiline', False),
                        "choices": choices,
                        "font_size": getattr(widget, 'text_fontsize', 11.0),
                        "rect": widget.rect
                    }
                )
                self.scene.addItem(item)
                self.form_designer_items.append(item)
                item.setSelected(True)
            else:
                self._load_interactive_form_widgets()
            return final_name
        except Exception:
            return None

    def clear_all_form_fields(self):
        """Belgedeki tüm form alanlarının değerlerini sıfırlar."""
        if not self.doc:
            return
        for page in self.doc:
            for w in page.widgets():
                try:
                    if w.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                        w.field_value = ""
                    elif w.field_type in (fitz.PDF_WIDGET_TYPE_CHECKBOX, getattr(fitz, 'PDF_WIDGET_TYPE_RADIOBUTTON', 4)):
                        w.field_value = False
                    w.update()
                except Exception:
                    pass
        self.set_modified(True)
        for it in getattr(self, 'form_designer_items', []):
            if it.field_type == "text":
                it.field_value = ""
            elif it.field_type in ("checkbox", "radio"):
                it.field_value = False
            it.update()
        if self.scene:
            self.scene.update()
        if not self.is_form_design_mode:
            self._load_interactive_form_widgets()

    def delete_form_field(self, page_idx: int, field_name: str):
        """Belirtilen form alanını sayfadan siler."""
        if not self.doc or page_idx >= len(self.doc):
            return
        page = self.doc[page_idx]
        for w in page.widgets():
            if w.field_name == field_name:
                try:
                    page.delete_widget(w)
                    self.set_modified(True)
                except Exception:
                    pass
                break

        to_remove = [it for it in getattr(self, 'form_designer_items', []) if it.page_idx == page_idx and it.field_name == field_name]
        for it in to_remove:
            try:
                if it.scene() == self.scene:
                    self.scene.removeItem(it)
                self.form_designer_items.remove(it)
            except Exception:
                pass

        if self.scene:
            self.scene.update()

        if not self.is_form_design_mode:
            self._load_interactive_form_widgets()

        if self.main_window and hasattr(self.main_window, 'modern_left_sidebar'):
            drawer = getattr(self.main_window.modern_left_sidebar, 'prepare_form_drawer', None)
            if drawer:
                drawer.refresh_fields_list()

    def get_all_form_fields(self) -> list:
        """Belgedeki tüm form alanlarının listesini döndürür."""
        fields = []
        if not self.doc:
            return fields
        type_names = {
            fitz.PDF_WIDGET_TYPE_TEXT: "Text",
            fitz.PDF_WIDGET_TYPE_CHECKBOX: "Checkbox",
            getattr(fitz, 'PDF_WIDGET_TYPE_RADIOBUTTON', 4): "Radio",
            fitz.PDF_WIDGET_TYPE_COMBOBOX: "ComboBox",
            getattr(fitz, 'PDF_WIDGET_TYPE_LISTBOX', 3): "ListBox",
            fitz.PDF_WIDGET_TYPE_SIGNATURE: "Signature",
            fitz.PDF_WIDGET_TYPE_BUTTON: "Button",
        }
        for p_idx, page in enumerate(self.doc):
            for w in page.widgets():
                fields.append({
                    'page': p_idx,
                    'name': w.field_name or f"Field_{p_idx}",
                    'type': type_names.get(w.field_type, "Field"),
                    'value': w.field_value,
                    'rect': (w.rect.x0, w.rect.y0, w.rect.x1, w.rect.y1)
                })
        return fields

    def _handle_mouse_hover(self, event, tool):
        pos = self.view.mapToScene(event.pos())
        hovered_ribbon = None
        try:
            for it in self.scene.items(pos):
                if isinstance(it, BookmarkRibbonItem):
                    hovered_ribbon = it
                    break
        except Exception:
            hovered_ribbon = None

        last_hov = getattr(self, '_last_hovered_ribbon', None)
        if last_hov != hovered_ribbon:
            if last_hov:
                try:
                    last_hov.set_hovered(False)
                except Exception:
                    pass
            self._last_hovered_ribbon = hovered_ribbon
            if hovered_ribbon:
                try:
                    hovered_ribbon.set_hovered(True)
                except Exception:
                    pass
            elif hasattr(self, 'main_window') and hasattr(self.main_window, 'update_viewport_cursor'):
                self.main_window.update_viewport_cursor()

        if hovered_ribbon:
            self.view.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            return

        if tool == 'comment':
            _, c_annot, _ = self.get_comment_annot_at_pos(pos)
            if c_annot:
                self.view.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
            else:
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

    def _handle_mouse_press(self, event, tool, source=None):
        pos = self.view.mapToScene(event.pos())

        # Yorum ikonu tıklandıysa yorum sürüklemeyi başlat
        c_p_idx, c_annot, c_rect = self.get_comment_annot_at_pos(pos)
        if c_annot:
            self._dragged_comment_annot = c_annot
            self._dragged_comment_xref = getattr(c_annot, 'xref', None)
            self._dragged_comment_page = c_p_idx
            self._dragged_comment_start_scene_pos = pos
            self._dragged_comment_start_rect = fitz.Rect(c_rect)
            self._dragged_comment_is_dragging = False
            self.view.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
            return True

        page_idx = self.get_page_at_pos(pos)

        # Spacebar Pan, orta fare tuşu pan veya 'pan' aracı
        if getattr(self, 'space_pan_active', False) or event.button() == Qt.MouseButton.MiddleButton or tool == 'pan':
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

            # Doğrudan çizim/metin/tablo öğesine tıklandıysa öğeyi anında seç
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
            if sel_mode == 'rect':
                self.selection_item = self.scene.addRect(QRectF(pos, pos), pen, brush)
            else:
                self.selection_path = QPainterPath(pos)
                self.selection_item = self.scene.addPath(self.selection_path, pen, brush)
            self.selection_item.setZValue(25)
            return True

        if tool in ('select', 'text'):
            from src.ui.widgets import TextMoveHandleItem
            hit_items = self.scene.items(pos)
            if any(isinstance(it, TextMoveHandleItem) or hasattr(it, 'parent_text_item') for it in hit_items):
                return False
            text_items = [it for it in hit_items if isinstance(it, EditableInlineTextItem)]
            if not text_items:
                # Uzun ve çok satırlı metin kutularında satır araları ve kenarlık tıklamalarını kaçırmamak için
                for it in self.scene.items():
                    if isinstance(it, EditableInlineTextItem) and it.sceneBoundingRect().adjusted(-3, -3, 3, 3).contains(pos):
                        text_items = [it]
                        break
            if text_items:
                hit_txt = text_items[0]
                if self.active_text_item and self.active_text_item != hit_txt:
                    if hasattr(self.active_text_item, 'finish_editing'):
                        self.active_text_item.finish_editing()
                    else:
                        self.active_text_item.clearFocus()
                self.active_text_item = hit_txt
                self.last_text_item = hit_txt
                return False

            # Kullanıcı boş bir alana tıkladı:
            # Eğer aktif olarak düzenlenen bir metin kutusu varsa, önce düzenleme modunu temizce sonlandır!
            # Adobe Acrobat standardı: Dışarıya tek tıklama düzenlemeyi bitirir, kutu boşsa siler, hemen üzerine yeni bir metin kutusu açmaz!
            if self.active_text_item:
                act_item = self.active_text_item
                flags_fn = getattr(act_item, 'textInteractionFlags', None)
                is_editing = bool(flags_fn() & Qt.TextInteractionFlag.TextEditorInteraction) if callable(flags_fn) else False
                if hasattr(act_item, 'finish_editing'):
                    act_item.finish_editing()
                else:
                    if hasattr(act_item, 'clearFocus'):
                        act_item.clearFocus()
                    if hasattr(act_item, 'setSelected'):
                        act_item.setSelected(False)
                    self.active_text_item = None
                if is_editing:
                    # Kullanıcı metin kutusundan dışarı çıkmak için boş alana tıkladı;
                    # yeni bir kutu açılmasını engelle ve olayı tüket!
                    return True

        # Sayfa dışına tıklandıysa çizim veya metin başlatma!
        if page_idx is None:
            self.active_drawing_page = None
            self.current_path = None
            self.current_path_item = None
            self.stroke_start_pos = None
            if self.active_text_item:
                if hasattr(self.active_text_item, 'clearFocus'):
                    self.active_text_item.clearFocus()
            if tool == 'eraser':
                self.eraser_last_pos = pos
                if getattr(self.main_window.eraser_popup, 'eraser_mode', 'stroke') == 'area':
                    self.area_erase_initial_drawings = [dict(d) for d in self.drawings]
                    self.area_erase_had_changes = False
                self.erase_at(pos, prev_pos=None)
            return True

        if tool == 'comment':
            p_info = self.page_positions[page_idx]
            scale = self.base_render_dpi
            pleft = p_info.get('left', 0.0)
            ptop = p_info['top']
            pdf_x = (pos.x() - pleft) / scale
            pdf_y = (pos.y() - ptop) / scale
            try:
                page = self.doc[page_idx]
                from src.ui.dialogs.settings_dialog import get_effective_author_name
                from src.ui.dialogs.comment_dialog import AuraCommentInputDialog
                dlg = AuraCommentInputDialog(self.window(), initial_author=get_effective_author_name())

                g_pos = self.view.viewport().mapToGlobal(event.pos())
                screen = QApplication.primaryScreen().availableGeometry()
                dx = min(g_pos.x() + 10, screen.right() - 400)
                dy = min(g_pos.y() + 10, screen.bottom() - 340)
                dlg.move(max(screen.left() + 20, dx), max(screen.top() + 20, dy))

                if dlg.exec():
                    comment_text, author, hex_color = dlg.get_comment_data()
                    if comment_text:
                        annot = page.add_text_annot(fitz.Point(pdf_x, pdf_y), comment_text)
                        annot.set_info(title=author, content=comment_text)
                        qc = QColor(hex_color)
                        annot.set_colors(stroke=(qc.redF(), qc.greenF(), qc.blueF()))
                        annot.update()

                        self.set_modified(True)
                        if hasattr(self, 'rerender_page'):
                            self.rerender_page(page_idx)
                        elif hasattr(self, 'rerender_visible_pages'):
                            self.rerender_visible_pages(force=True)
                        if hasattr(self.main_window, 'modern_right_sidebar') and self.main_window.modern_right_sidebar:
                            self.main_window.modern_right_sidebar.load_comments()
                        if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                            self.main_window.statusBar().showMessage(LanguageManager.tr("comment_added_msg", page=page_idx + 1), 3500)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, LanguageManager.tr("error"), str(e))
            return True

        elif tool == 'text':
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
            pen = self.main_window.get_current_pen()
            should_snap = (tool == 'highlighter' and self.main_window.hl_popup.snap_straight) or (tool == 'pen' and getattr(self.main_window.pen_popup, 'snap_straight', False)) or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            
            p_info = self.page_positions[page_idx]
            page_left = p_info.get('left', 0.0)
            page_right = page_left + p_info['width']
            top_y = p_info['top']
            bottom_y = p_info['bottom']

            popup = self.main_window.pen_popup if tool == 'pen' else self.main_window.hl_popup
            line_style = getattr(popup, 'line_style', 'solid')
            p_type = getattr(popup, 'current_pen_type', 'solid') if tool == 'pen' else 'highlighter'
            is_pencil = (tool == 'pen' and (p_type == 'pencil' or line_style == 'pencil'))

            # Belgeden taşmaları kesin olarak engellemek için fosforlu kalemde yarım kalınlık payı bırakılır
            if tool == 'highlighter':
                half_t = max(1.0, float(popup.thickness) / 2.0)
                pos = QPointF(
                    max(page_left + half_t, min(pos.x(), page_right - half_t)),
                    max(top_y + half_t, min(pos.y(), bottom_y - half_t))
                )
            self.stroke_start_pos = pos

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

        if getattr(self, '_dragged_comment_annot', None):
            diff = (pos - self._dragged_comment_start_scene_pos).manhattanLength()
            if diff > 3:
                self._dragged_comment_is_dragging = True
            if self._dragged_comment_is_dragging:
                self._update_comment_drag_ghost(pos)
            return True

        if tool == 'ruler':
            if self.active_measurement_item is not None:
                has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.update_measurement(pos, has_shift=has_shift)
            return True

        # Öncelikli Pan hareketi (Spacebar Pan, orta tuş veya Pan aracı)
        if self.is_panning and self.pan_last_viewport_pos is not None:
            delta = event.pos() - self.pan_last_viewport_pos
            self.pan_last_viewport_pos = event.pos()
            h_bar = self.view.horizontalScrollBar()
            v_bar = self.view.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            return True

        if tool in ('pan', 'selection_tool'):
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

            popup = self.main_window.pen_popup if tool == 'pen' else self.main_window.hl_popup
            line_style = getattr(popup, 'line_style', 'solid')

            # Sayfa sınırları dışına taşmayı engelle (Clamp)
            if tool == 'highlighter':
                half_t = max(1.0, float(popup.thickness) / 2.0)
                clamped_x = max(page_left + half_t, min(pos.x(), page_left + width - half_t))
                clamped_y = max(top_y + half_t, min(pos.y(), bottom_y - half_t))
            else:
                clamped_x = max(page_left, min(pos.x(), page_left + width))
                clamped_y = max(top_y, min(pos.y(), bottom_y))
            clamped_pos = QPointF(clamped_x, clamped_y)

            is_hl_snap = (tool == 'highlighter' and self.main_window.hl_popup.snap_straight)
            is_pen_snap = (tool == 'pen' and getattr(self.main_window.pen_popup, 'snap_straight', False))
            has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            should_snap = is_hl_snap or is_pen_snap or has_shift

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
                        scene_pts = [QPointF(rx * self.base_render_dpi + page_left, ry * self.base_render_dpi + top_y) for rx, ry in self.current_stroke_pts]
                        self.current_path = build_smooth_path(scene_pts)
                        self.current_path_item.setPath(self.current_path)
        return True

    def _handle_mouse_release(self, event, tool):
        pos = self.view.mapToScene(event.pos())

        if getattr(self, '_dragged_comment_annot', None):
            if self._dragged_comment_is_dragging:
                self._finalize_comment_drag(pos)
                self._cleanup_comment_drag()
                return True
            else:
                annot = self._dragged_comment_annot
                self._cleanup_comment_drag()
                if tool == 'comment':
                    self._open_comment_dialog_for_annot(annot, event.pos())
                    return True
                return True

        if tool == 'ruler':
            if self.active_measurement_item is not None:
                has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.finish_measurement(pos, has_shift=has_shift)
            return True

        # Pan bırakma kontrolü
        if self.is_panning:
            self.is_panning = False
            self.pan_last_viewport_pos = None
            if getattr(self, 'space_pan_active', False) or tool == 'pan':
                self.view.viewport().setCursor(CursorFactory.get_pan_cursor())
            else:
                self.main_window.update_viewport_cursor()
            return True

        if tool in ('pan', 'selection_tool'):
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
                            target_page_right = target_page_left + target_p_info.get('width', 600.0)
                            target_page_bottom = target_p_info.get('bottom', target_page_top + 800.0)

                            it = d.get("item_ref")
                            it_w = it.boundingRect().width() if it else 50.0
                            it_h = it.boundingRect().height() if it else 30.0

                            m = 10.0
                            item_scene_x = max(target_page_left + m, min(item_scene_x, target_page_right - it_w - m))
                            item_scene_y = max(target_page_top + m, min(item_scene_y, target_page_bottom - it_h - m))
                            if it:
                                it.setPos(item_scene_x, item_scene_y)
                                if isinstance(it, EditableInlineTextItem):
                                    it.page_idx = target_page
                                    it._update_text_width_constraint()

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

                        elif init_s.get("type") == "text_markup" and "rects" in init_s:
                            scale = self.base_render_dpi
                            dx_pdf = total_dx / scale
                            dy_pdf = total_dy / scale
                            d["rects"] = [[r[0] + dx_pdf, r[1] + dy_pdf, r[2] + dx_pdf, r[3] + dy_pdf] for r in init_s["rects"]]

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
                        elif d.get("type") in ("text", "image", "table"):
                            box_rect = it.sceneBoundingRect()
                            if sel_poly.containsPoint(box_rect.center(), Qt.FillRule.OddEvenFill) or sel_rect.intersects(box_rect):
                                is_selected = True
                            else:
                                try:
                                    box_poly = QPolygonF(box_rect)
                                    if sel_poly.intersects(box_poly):
                                        is_selected = True
                                except Exception:
                                    pass

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
                    if tool == 'highlighter':
                        half_t = max(1.0, float(popup.thickness) / 2.0)
                        page_w = p_info['width']
                        bottom_y = p_info['bottom']
                        s_x = max(page_left + half_t, min(self.current_stroke_pts[0][0] * self.base_render_dpi + page_left, page_left + page_w - half_t))
                        s_y = max(top_y + half_t, min(self.current_stroke_pts[0][1] * self.base_render_dpi + top_y, bottom_y - half_t))
                        start_pt = QPointF(s_x, s_y)
                        if not has_shift:
                            end_y = s_y
                        else:
                            end_y = max(top_y + half_t, min(self.current_stroke_pts[1][1] * self.base_render_dpi + top_y, bottom_y - half_t))
                        e_x = max(page_left + half_t, min(self.current_stroke_pts[1][0] * self.base_render_dpi + page_left, page_left + page_w - half_t))
                        end_pt = QPointF(e_x, end_y)
                        self.current_stroke_pts = [
                            ((s_x - page_left) / self.base_render_dpi, (s_y - top_y) / self.base_render_dpi),
                            ((e_x - page_left) / self.base_render_dpi, (end_y - top_y) / self.base_render_dpi)
                        ]
                    else:
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



