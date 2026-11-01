"""
AuraPDF - Kalem Çizim Motoru
============================
Kurşun kalem izini görsel doku yerine sayfa koordinatlarındaki grafit
parçacıklarıyla, fırçayı ise hıza duyarlı dolgu şeridiyle üretir. İkisi de
vektöreldir; yakınlaştırma ve ekran ölçeği (DPI) değişse de netlik korunur.
"""

import math
import random
from typing import List, Optional, Sequence, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem

PARTICLES_PER_AREA = 3.6
MAX_PARTICLES_PER_STEP = 28
STEP_LENGTH = 0.6
UNDERLAY_ALPHA = 0.36
UNDERLAY_WIDTH = 0.8
TOOTH_THRESHOLD = 0.3
GRAIN_SIZES = (0.55, 0.8, 1.15)
GRAIN_ALPHAS = (0.5, 0.74, 0.96)
MIN_DOT_LENGTH = 0.9


def _paper_tooth(x: float, y: float) -> float:
    """Sayfaya sabit kağıt dokusu: Aynı noktaya gelen izler aynı boşlukları bırakır."""
    return (math.sin(x * 1.37 + y * 0.61) * math.cos(y * 1.13 - x * 0.47)
            + math.sin(x * 2.9 - y * 2.3) * 0.6 + 1.6) / 3.2


def stroke_seed(points: Sequence[QPointF]) -> int:
    """Çizimin parçacık deseni her açılışta aynı kalsın diye noktalardan tohum üretir."""
    if not points:
        return 1
    first, last = points[0], points[-1]
    return (int(first.x() * 10) * 73856093) ^ (int(first.y() * 10) * 19349663) ^ (int(last.x() * 10) * 83492791)


class AuraPencilStrokeItem(QGraphicsPathItem):
    """Hafif bir alt ton ve üzerine serpilen grafit parçacıklarından oluşan kurşun kalem izi."""

    def __init__(self, path: QPainterPath, color: QColor, width: float, dash_pattern: Optional[List[float]] = None, seed: int = 1):
        super().__init__()
        self.base_color = QColor(color)
        self.stroke_width = max(0.6, float(width))
        self.dash_pattern = dash_pattern
        self._rng = random.Random(seed)
        self._grains = [QPolygonF() for _ in range(len(GRAIN_SIZES) * len(GRAIN_ALPHAS))]
        self._pens = self._build_pens()
        self._walked = 0.0
        self._done_counts: List[int] = []
        self._extent = self.stroke_width
        self.setPen(self._underlay_pen())
        self.setPath(path)

    def _build_pens(self) -> List[QPen]:
        pens = []
        base_alpha = self.base_color.alphaF()
        for size in GRAIN_SIZES:
            for alpha in GRAIN_ALPHAS:
                col = QColor(self.base_color)
                col.setAlphaF(base_alpha * alpha)
                pens.append(QPen(col, size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        return pens

    def _underlay_pen(self) -> QPen:
        col = QColor(self.base_color)
        col.setAlphaF(self.base_color.alphaF() * UNDERLAY_ALPHA)
        pen = QPen(col, self.stroke_width * UNDERLAY_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        if self.dash_pattern:
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern(self.dash_pattern)
        return pen

    def _dash_is_on(self, walked: float) -> bool:
        if not self.dash_pattern:
            return True
        cycle = sum(max(p, MIN_DOT_LENGTH / 2.0) for p in self.dash_pattern) * self.stroke_width
        pos = walked % cycle
        for index, length in enumerate(self.dash_pattern):
            span = max(length, MIN_DOT_LENGTH / 2.0) * self.stroke_width
            if pos < span:
                return index % 2 == 0
            pos -= span
        return False

    def _scatter(self, x: float, y: float, nx: float, ny: float):
        half = self.stroke_width / 2.0
        count = min(MAX_PARTICLES_PER_STEP, max(1, int(PARTICLES_PER_AREA * self.stroke_width * STEP_LENGTH + 0.5)))
        rng = self._rng
        for _ in range(count):
            # Kenarlara doğru seyrelen dağılım, grafitin pürüzlü kenarını oluşturur
            spread = (rng.random() + rng.random() - 1.0) * half * 1.25
            px = x + nx * spread + (rng.random() - 0.5) * STEP_LENGTH
            py = y + ny * spread + (rng.random() - 0.5) * STEP_LENGTH
            if _paper_tooth(px, py) < TOOTH_THRESHOLD + abs(spread) / max(half, 0.1) * 0.22:
                continue
            bucket = rng.randrange(len(GRAIN_SIZES)) * len(GRAIN_ALPHAS) + rng.randrange(len(GRAIN_ALPHAS))
            self._grains[bucket].append(QPointF(px, py))

    def _add_segment(self, a: QPointF, b: QPointF):
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy)
        if length < 0.001:
            return
        ux, uy = dx / length, dy / length
        steps = max(1, int(length / STEP_LENGTH))
        for i in range(steps):
            t = (i + self._rng.random()) / steps
            walked = self._walked + length * t
            if self._dash_is_on(walked):
                self._scatter(a.x() + dx * t, a.y() + dy * t, -uy, ux)
        self._walked += length

    def setPath(self, path: QPainterPath):
        """Canlı çizimde yalnızca yeni eklenen bölüm için parçacık üretir."""
        polygons = path.toSubpathPolygons()
        if len(polygons) < len(self._done_counts):
            self._done_counts = self._done_counts[:len(polygons)]
        for index, polygon in enumerate(polygons):
            if index >= len(self._done_counts):
                self._done_counts.append(0)
            start = max(0, self._done_counts[index] - 1)
            for i in range(start, polygon.count() - 1):
                self._add_segment(polygon.at(i), polygon.at(i + 1))
            self._done_counts[index] = polygon.count()
        super().setPath(path)

    def finalize(self):
        """Çizim bittiğinde kaydırma performansı için aygıt çözünürlüğünde önbelleğe alır."""
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        margin = self.stroke_width
        return super().boundingRect().adjusted(-margin, -margin, margin, margin)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for polygon, pen in zip(self._grains, self._pens):
            if polygon.count():
                painter.setPen(pen)
                painter.drawPoints(polygon)
        painter.restore()


def build_brush_path(points: Sequence[QPointF], base_width: float, unit: float = 1.0) -> QPainterPath:
    """Fırça darbesi: Yavaş yerde kalınlaşır, hızlı yerde incelir, uçları sivrilerek biter."""
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    if not points:
        return path
    if len(points) == 1:
        path.addEllipse(points[0], base_width / 2.0, base_width / 2.0)
        return path

    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(b.x() - a.x(), b.y() - a.y()))
    total = max(lengths[-1], 1e-6)
    taper = min(total * 0.22, base_width * 2.2)

    left: List[QPointF] = []
    right: List[QPointF] = []
    pressure = 1.0
    for i, point in enumerate(points):
        prev_pt = points[max(0, i - 1)]
        next_pt = points[min(len(points) - 1, i + 1)]
        dx, dy = next_pt.x() - prev_pt.x(), next_pt.y() - prev_pt.y()
        seg = math.hypot(dx, dy) or 1e-6
        speed = min(1.0, (seg / 2.0) / max(base_width * 0.9, 1e-6))
        pressure += ((1.22 - 0.42 * speed) - pressure) * 0.3
        edge = min(lengths[i], total - lengths[i]) / max(taper, 1e-6)
        width = base_width * pressure * (0.3 + 0.7 * min(1.0, edge))
        nx, ny = -dy / seg * width / 2.0, dx / seg * width / 2.0
        left.append(QPointF(point.x() + nx, point.y() + ny))
        right.append(QPointF(point.x() - nx, point.y() - ny))

    outline = left + right[::-1]
    path.moveTo(outline[0])
    for a, b in zip(outline[1:], outline[2:]):
        path.quadTo(a, QPointF((a.x() + b.x()) / 2.0, (a.y() + b.y()) / 2.0))
    path.lineTo(outline[-1])
    path.closeSubpath()
    return path
