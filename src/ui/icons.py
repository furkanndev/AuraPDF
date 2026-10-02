from PyQt6.QtGui import (QIcon, QPixmap, QPainter, QColor, QPen, QBrush, 
                         QPainterPath, QPolygonF, QLinearGradient, QRadialGradient, QFont)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSettings

import os
import sys
import math

def _find_app_icon_path(filename="app_icon.png"):
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), filename),
        os.path.abspath(f"src/assets/{filename}"),
        os.path.abspath(f"assets/{filename}"),
        os.path.abspath(filename),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, os.path.join(sys._MEIPASS, "src", "assets", filename))
        candidates.insert(1, os.path.join(sys._MEIPASS, "assets", filename))
        candidates.insert(2, os.path.join(sys._MEIPASS, filename))

    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# --- 5. VEKTÖREL İKON FABRİKASI ---
class ModernIconFactory:
    _cached_app_icon = None
    _cached_app_pixmap = None

    @classmethod
    def reset_app_icon_cache(cls):
        cls._cached_app_icon = None
        cls._cached_app_pixmap = None

    @staticmethod
    def _base():
        pix = QPixmap(26, 26)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        return pix, p

    _icon_cache = {}

    @classmethod
    def icon_app(cls) -> QIcon:
        if cls._cached_app_icon is not None and not cls._cached_app_icon.isNull():
            return cls._cached_app_icon

        # 1. Varsayılan ICO dosyası (16, 24, 32, 48, 64, 128, 256 mipmap çözünürlükleri içerir)
        ico_path = _find_app_icon_path("app_icon.ico")
        if ico_path and os.path.exists(ico_path):
            icon = QIcon(ico_path)
            if not icon.isNull():
                cls._cached_app_icon = icon
                return icon

        # 2. PNG dosyasından çoklu ölçeklendirme
        png_path = _find_app_icon_path("app_icon.png")
        if png_path and os.path.exists(png_path):
            base_pix = QPixmap(png_path)
            if not base_pix.isNull():
                icon = QIcon()
                for size in [16, 24, 32, 48, 64, 128, 256]:
                    scaled = base_pix.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    icon.addPixmap(scaled)
                cls._cached_app_icon = icon
                return icon

        # 3. Yedek (fallback) vektörel ikon
        icon = QIcon()
        for size in [16, 24, 32, 48, 64, 128, 256]:
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            grad = QLinearGradient(0, 0, size, size)
            grad.setColorAt(0.0, QColor("#1e293b"))
            grad.setColorAt(1.0, QColor("#0f172a"))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            corner = size * 0.22
            p.drawRoundedRect(QRectF(size * 0.05, size * 0.05, size * 0.9, size * 0.9), corner, corner)
            p.end()
            icon.addPixmap(pix)

        cls._cached_app_icon = icon
        return icon

    @classmethod
    def pixmap_app(cls, size: int = 256) -> QPixmap:
        icon = cls.icon_app()
        if not icon.isNull():
            return icon.pixmap(size, size)
        return QPixmap()


    @staticmethod
    def icon_toolbox():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawRoundedRect(3, 9, 20, 13, 3, 3)
        p.drawLine(3, 14, 23, 14)
        p.drawArc(8, 4, 10, 8, 0, 180 * 16)
        p.setBrush(QBrush(QColor("#388bfd")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(7, 12.5, 3, 3.5), 1, 1)
        p.drawRoundedRect(QRectF(16, 12.5, 3, 3.5), 1, 1)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_word():
        pix, p = ModernIconFactory._base()
        p.setBrush(QBrush(QColor("#2b579a")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(4, 3, 18, 20), 2.5, 2.5)
        p.setBrush(QBrush(QColor("#185abd")))
        p.drawRoundedRect(QRectF(3, 7, 10, 12), 2, 2)
        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(3, 6, 10, 14), Qt.AlignmentFlag.AlignCenter, "W")
        p.setPen(QPen(QColor("#ffffff"), 1.2))
        p.drawLine(15, 8, 19, 8)
        p.drawLine(15, 12, 19, 12)
        p.drawLine(15, 16, 19, 16)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_select_rect():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#388bfd"), 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        p.drawRoundedRect(3, 3, 20, 20, 3, 3)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_pen():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#ffffff"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
        path = QPainterPath()
        path.moveTo(4, 6); path.lineTo(6, 15); path.lineTo(10, 22); path.lineTo(14, 15); path.lineTo(16, 6)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    # ... İhtiyaç duyulan tüm ikon metotları ...
    @staticmethod
    def icon_contents():
        pix, p = ModernIconFactory._base()
        p.setBrush(QColor("#e0e0e0"))
        p.drawEllipse(3, 6, 2, 2); p.drawEllipse(3, 12, 2, 2); p.drawEllipse(3, 18, 2, 2)
        p.setPen(QPen(QColor("#e0e0e0"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(8, 7, 22, 7); p.drawLine(8, 13, 22, 13); p.drawLine(8, 19, 22, 19)
        p.end()
        return QIcon(pix)


    @staticmethod
    def icon_fullscreen():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
        p.drawLine(4, 9, 4, 4); p.drawLine(4, 4, 9, 4)
        p.drawLine(22, 9, 22, 4); p.drawLine(22, 4, 17, 4)
        p.drawLine(4, 17, 4, 22); p.drawLine(4, 22, 9, 22)
        p.drawLine(22, 17, 22, 22); p.drawLine(22, 22, 17, 22)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_select_lasso():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#388bfd"), 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        path = QPainterPath()
        path.moveTo(6, 12); path.cubicTo(6, 4, 20, 4, 20, 12); path.cubicTo(20, 20, 14, 22, 10, 18); path.lineTo(6, 22)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_select_move():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#388bfd"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Dikey çizgi ve ok uçları
        p.drawLine(13, 4, 13, 22)
        p.drawLine(10, 7, 13, 4); p.drawLine(16, 7, 13, 4)
        p.drawLine(10, 19, 13, 22); p.drawLine(16, 19, 13, 22)
        # Yatay çizgi ve ok uçları
        p.drawLine(4, 13, 22, 13)
        p.drawLine(7, 10, 4, 13); p.drawLine(7, 16, 4, 13)
        p.drawLine(19, 10, 22, 13); p.drawLine(19, 16, 22, 13)
        p.end()
        return QIcon(pix)

    @classmethod
    def icon_link(cls, color="#e2e8f0") -> QIcon:
        pix, p = cls._base()
        p.save()
        p.translate(13, 13)
        p.rotate(-45)
        pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(-9, -4, 9, 8, 4, 4)
        p.drawRoundedRect(0, -4, 9, 8, 4, 4)
        p.restore()
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_select_pan():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#388bfd"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor(56, 139, 253, 40)))
        path = QPainterPath()
        path.moveTo(8, 14)
        path.lineTo(8, 8)
        path.quadTo(9, 6, 10, 8)
        path.lineTo(10, 13)
        path.lineTo(10, 5)
        path.quadTo(11.5, 3.5, 13, 5)
        path.lineTo(13, 13)
        path.lineTo(13, 6)
        path.quadTo(14.5, 4.5, 16, 6)
        path.lineTo(16, 13)
        path.lineTo(16, 8)
        path.quadTo(17.5, 6.5, 19, 8)
        path.lineTo(19, 16)
        path.quadTo(19, 22, 13, 22)
        path.quadTo(8, 22, 8, 17)
        path.closeSubpath()
        p.drawPath(path)
        p.end()
        return QIcon(pix)


    @staticmethod
    def icon_highlighter():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#ffffff"), 1.2))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawPolygon(QPolygonF([QPointF(4, 9), QPointF(17, 9), QPointF(14, 15), QPointF(7, 15)]))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#ffd600")))
        p.drawPolygon(QPolygonF([QPointF(7, 16), QPointF(14, 16), QPointF(12, 22), QPointF(6, 20)]))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_text_box():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.4))
        p.drawRoundedRect(3, 3, 20, 20, 4, 4)
        p.drawLine(8, 8, 18, 8); p.drawLine(13, 8, 13, 18)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_eraser():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolygon(QPolygonF([QPointF(12, 4), QPointF(20, 12), QPointF(10, 22), QPointF(2, 14)]))
        p.drawLine(QPointF(6, 18), QPointF(16, 8)); p.drawLine(QPointF(9, 22), QPointF(18, 22))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_undo():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(7, 8, 14, 14, 0, 150 * 16)
        p.setBrush(QBrush(QColor("#e0e0e0")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(7, 4), QPointF(3, 9), QPointF(9, 12)]))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_redo():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(5, 8, 14, 14, 30 * 16, 150 * 16)
        p.setBrush(QBrush(QColor("#e0e0e0")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(19, 4), QPointF(23, 9), QPointF(17, 12)]))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_rotate():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.8))
        p.drawArc(4, 4, 18, 18, 45 * 16, 270 * 16)
        p.setBrush(QColor("#e0e0e0"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(15, 2), QPointF(22, 6), QPointF(16, 9)]))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_print():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.4))
        p.drawRoundedRect(4, 9, 18, 10, 2, 2)
        p.drawRect(7, 4, 12, 5); p.drawRect(7, 14, 12, 8)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_save():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.4))
        p.drawRoundedRect(4, 4, 18, 18, 2, 2)
        p.drawRect(7, 4, 12, 6); p.drawRect(7, 14, 12, 8)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_pointer():
        pix, p = ModernIconFactory._base()
        # Laser wand shaft
        p.setPen(QPen(QColor("#e0e0e0"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(5, 21), QPointF(13, 13))
        # Red tip
        p.setPen(QPen(QColor("#ff5252"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(13, 13), QPointF(16, 10))
        # Glowing dot
        p.setBrush(QBrush(QColor("#ff1744")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(17, 4, 7, 7))
        # Laser sparks
        p.setPen(QPen(QColor("#ff5252"), 1.2))
        p.drawLine(QPointF(20.5, 1), QPointF(20.5, 3))
        p.drawLine(QPointF(20.5, 12), QPointF(20.5, 14))
        p.drawLine(QPointF(14, 7.5), QPointF(16, 7.5))
        p.drawLine(QPointF(25, 7.5), QPointF(27, 7.5))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_cursor():
        pix, p = ModernIconFactory._base()
        path = QPainterPath()
        path.moveTo(5.5, 4.0)
        path.lineTo(5.5, 20.0)
        path.lineTo(10.2, 15.8)
        path.lineTo(14.0, 23.0)
        path.lineTo(17.0, 21.4)
        path.lineTo(13.2, 14.4)
        path.lineTo(19.0, 14.4)
        path.closeSubpath()
        p.setBrush(QBrush(QColor("#e0e0e0")))
        p.setPen(QPen(QColor("#1e1e1e"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_search():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QRectF(4.0, 4.0, 11.5, 11.5))
        p.drawLine(QPointF(12.5, 12.5), QPointF(20.0, 20.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_reorder():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#58a6ff"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # 3 horizontal page lines
        p.drawLine(3, 7, 15, 7)
        p.drawLine(3, 13, 15, 13)
        p.drawLine(3, 19, 15, 19)
        # Up arrow
        p.drawLine(20, 5, 20, 11)
        p.drawLine(17, 8, 20, 5); p.drawLine(23, 8, 20, 5)
        # Down arrow
        p.drawLine(20, 15, 20, 21)
        p.drawLine(17, 18, 20, 21); p.drawLine(23, 18, 20, 21)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_organize():
        pix, p = ModernIconFactory._base()
        # Back sheet
        p.setPen(QPen(QColor("#388bfd"), 1.2))
        p.setBrush(QBrush(QColor("#1e293b")))
        p.drawRoundedRect(QRectF(3.0, 5.0, 13.0, 16.0), 1.5, 1.5)

        # Front sheet
        p.setPen(QPen(QColor("#60a5fa"), 1.4))
        p.setBrush(QBrush(QColor("#0f172a")))
        p.drawRoundedRect(QRectF(9.0, 3.0, 14.0, 17.0), 1.5, 1.5)

        # Up/Down arrange indicators
        p.setPen(QPen(QColor("#388bfd"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(19.0, 7.0), QPointF(19.0, 11.0))
        p.drawLine(QPointF(17.5, 8.5), QPointF(19.0, 7.0))
        p.drawLine(QPointF(20.5, 8.5), QPointF(19.0, 7.0))

        # Bottom number badge
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#2563eb")))
        p.drawRoundedRect(QRectF(11.0, 13.0, 8.0, 5.0), 1.5, 1.5)
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(QFont("Segoe UI", 5, QFont.Weight.Bold))
        p.drawText(QRectF(11.0, 12.5, 8.0, 5.5), Qt.AlignmentFlag.AlignCenter, "#")

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_page_number():
        pix, p = ModernIconFactory._base()
        # Page sheet outline & background
        p.setPen(QPen(QColor("#58a6ff"), 1.4))
        p.setBrush(QBrush(QColor("#1e293b")))
        p.drawRoundedRect(QRectF(4.0, 3.0, 18.0, 20.0), 2.0, 2.0)

        # Subtle text lines on upper page
        p.setPen(QPen(QColor("#64748b"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(7.0, 7.5), QPointF(19.0, 7.5))
        p.drawLine(QPointF(7.0, 11.0), QPointF(16.0, 11.0))

        # Bottom number badge / pill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#388bfd")))
        p.drawRoundedRect(QRectF(7.5, 14.5, 11.0, 7.0), 2.0, 2.0)

        # "1" symbol
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        p.drawText(QRectF(7.5, 14.0, 11.0, 7.5), Qt.AlignmentFlag.AlignCenter, "1")

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_lock():
        pix, p = ModernIconFactory._base()
        # Shackle
        p.setPen(QPen(QColor('#e0e0e0'), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(7.5, 4.0, 11.0, 12.0), 0, 180 * 16)
        p.drawLine(QPointF(7.5, 10.0), QPointF(7.5, 13.0))
        p.drawLine(QPointF(18.5, 10.0), QPointF(18.5, 13.0))

        # Body
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#f59e0b')))
        p.drawRoundedRect(QRectF(5.0, 12.0, 16.0, 11.0), 2.5, 2.5)

        # Keyhole
        p.setBrush(QBrush(QColor('#1e1e1e')))
        p.drawEllipse(QRectF(11.5, 14.5, 3.0, 3.0))
        p.setPen(QPen(QColor('#1e1e1e'), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(13.0, 17.0), QPointF(13.0, 19.5))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_watermark():
        pix, p = ModernIconFactory._base()
        # Page background outline
        p.setPen(QPen(QColor('#707070'), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(QColor('#2a2a2a')))
        p.drawRoundedRect(QRectF(4.0, 3.5, 14.0, 19.0), 2.0, 2.0)
        
        # Diagonal watermark stamp
        p.save()
        p.translate(13.0, 13.0)
        p.rotate(-35)
        # Stamp outline
        p.setPen(QPen(QColor('#00e5ff'), 1.3, Qt.PenStyle.DashLine))
        p.setBrush(QBrush(QColor(0, 229, 255, 45)))
        p.drawRoundedRect(QRectF(-8.0, -4.0, 16.0, 8.0), 1.5, 1.5)
        
        # Stamp letter / symbol
        p.setFont(QFont("Arial", 5, QFont.Weight.Bold))
        p.setPen(QPen(QColor('#00e5ff')))
        p.drawText(QRectF(-8.0, -4.0, 16.0, 8.0), Qt.AlignmentFlag.AlignCenter, "W")
        p.restore()

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_background():
        pix, p = ModernIconFactory._base()
        # Back layer (colored background sheet)
        p.setPen(QPen(QColor('#388bfd'), 1.2))
        p.setBrush(QBrush(QColor('#1f3a5f')))
        p.drawRoundedRect(QRectF(8.0, 3.5, 14.0, 15.0), 2.0, 2.0)

        # Front layer (content sheet with transparent window)
        p.setPen(QPen(QColor('#ffffff'), 1.4))
        p.setBrush(QBrush(QColor('#252525')))
        p.drawRoundedRect(QRectF(4.0, 7.5, 14.0, 15.0), 2.0, 2.0)

        p.setPen(QPen(QColor('#888888'), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(7.0, 12.0), QPointF(14.0, 12.0))
        p.drawLine(QPointF(7.0, 15.0), QPointF(15.0, 15.0))
        p.drawLine(QPointF(7.0, 18.0), QPointF(11.0, 18.0))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_recovery():
        pix, p = ModernIconFactory._base()
        # Key head (circle with hole)
        p.setPen(QPen(QColor('#10b981'), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(QColor('#064e3b')))
        p.drawEllipse(QRectF(4.0, 5.0, 9.0, 9.0))
        p.drawEllipse(QRectF(7.0, 8.0, 3.0, 3.0))

        # Key shaft and bits
        p.setPen(QPen(QColor('#10b981'), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(11.5, 12.5), QPointF(20.5, 21.5))
        # Teeth
        p.drawLine(QPointF(17.5, 18.5), QPointF(20.5, 15.5))
        p.drawLine(QPointF(19.5, 20.5), QPointF(21.5, 18.5))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_merge():
        pix, p = ModernIconFactory._base()
        # Left sheet
        p.setPen(QPen(QColor('#388bfd'), 1.3))
        p.setBrush(QBrush(QColor('#1a2736')))
        p.drawRoundedRect(QRectF(3.0, 4.0, 11.0, 15.0), 1.5, 1.5)
        
        # Right sheet
        p.setPen(QPen(QColor('#58a6ff'), 1.3))
        p.setBrush(QBrush(QColor('#21344d')))
        p.drawRoundedRect(QRectF(11.0, 7.0, 11.0, 15.0), 1.5, 1.5)

        # Merge plus
        p.setPen(QPen(QColor('#ffffff'), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(6.0, 11.5), QPointF(10.0, 11.5))
        p.drawLine(QPointF(8.0, 9.5), QPointF(8.0, 13.5))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_split():
        pix, p = ModernIconFactory._base()
        # Left half sheet
        p.setPen(QPen(QColor('#f85149'), 1.3))
        p.setBrush(QBrush(QColor('#2e1919')))
        p.drawRoundedRect(QRectF(3.0, 4.0, 8.5, 18.0), 1.5, 1.5)

        # Right half sheet
        p.setPen(QPen(QColor('#f85149'), 1.3))
        p.setBrush(QBrush(QColor('#2e1919')))
        p.drawRoundedRect(QRectF(14.5, 4.0, 8.5, 18.0), 1.5, 1.5)

        # Scissor / split mark in center
        p.setPen(QPen(QColor('#ffffff'), 1.4, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(13.0, 5.0), QPointF(13.0, 21.0))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_epub():
        pix, p = ModernIconFactory._base()
        # Open book pages
        p.setPen(QPen(QColor('#f59e0b'), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor('#2b2210')))
        
        path = QPainterPath()
        path.moveTo(13.0, 19.0)
        path.lineTo(4.0, 17.0)
        path.lineTo(4.0, 6.0)
        path.quadTo(8.5, 7.5, 13.0, 6.0)
        path.quadTo(17.5, 7.5, 22.0, 6.0)
        path.lineTo(22.0, 17.0)
        path.lineTo(13.0, 19.0)
        p.drawPath(path)

        # Book spine center line
        p.setPen(QPen(QColor('#f59e0b'), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(13.0, 6.0), QPointF(13.0, 19.0))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_mobi():
        pix, p = ModernIconFactory._base()
        # E-Reader / Mobile device frame
        p.setPen(QPen(QColor('#a855f7'), 1.4))
        p.setBrush(QBrush(QColor('#1e142e')))
        p.drawRoundedRect(QRectF(5.0, 3.0, 16.0, 20.0), 2.5, 2.5)

        # Screen area
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#33224d')))
        p.drawRoundedRect(QRectF(7.0, 5.5, 12.0, 13.5), 1.0, 1.0)

        # Reading lines
        p.setPen(QPen(QColor('#c084fc'), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(9.0, 8.5), QPointF(16.0, 8.5))
        p.drawLine(QPointF(9.0, 11.5), QPointF(17.0, 11.5))
        p.drawLine(QPointF(9.0, 14.5), QPointF(14.0, 14.5))

        # Bottom home dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#a855f7')))
        p.drawEllipse(QRectF(12.0, 20.2, 2.0, 2.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_powerpoint():
        pix, p = ModernIconFactory._base()
        p.setBrush(QBrush(QColor("#a2361d")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(4, 3, 18, 20), 2.5, 2.5)
        p.setBrush(QBrush(QColor("#d24726")))
        p.drawRoundedRect(QRectF(3, 7, 10, 12), 2, 2)
        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(3, 6, 10, 14), Qt.AlignmentFlag.AlignCenter, "P")
        p.setPen(QPen(QColor("#ffffff"), 1.2))
        p.drawArc(14, 8, 6, 6, 0, 270 * 16)
        p.drawLine(14, 17, 19, 17)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_excel():
        pix, p = ModernIconFactory._base()
        p.setBrush(QBrush(QColor("#0e5a2f")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(4, 3, 18, 20), 2.5, 2.5)
        p.setBrush(QBrush(QColor("#107c41")))
        p.drawRoundedRect(QRectF(3, 7, 10, 12), 2, 2)
        p.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(3, 6, 10, 14), Qt.AlignmentFlag.AlignCenter, "X")
        p.setPen(QPen(QColor("#ffffff"), 1.0))
        p.drawRect(14, 7, 6, 10)
        p.drawLine(17, 7, 17, 17)
        p.drawLine(14, 12, 20, 12)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_view_single():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#38bdf8"), 1.5))
        p.setBrush(QBrush(QColor(56, 189, 248, 30)))
        p.drawRoundedRect(QRectF(7, 3, 12, 20), 2, 2)
        p.setPen(QPen(QColor("#94a3b8"), 1.0))
        p.drawLine(10, 8, 16, 8)
        p.drawLine(10, 12, 16, 12)
        p.drawLine(10, 16, 14, 16)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_view_double():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#38bdf8"), 1.2))
        p.setBrush(QBrush(QColor(56, 189, 248, 30)))
        p.drawRoundedRect(QRectF(2, 4, 10, 18), 1.5, 1.5)
        p.drawRoundedRect(QRectF(14, 4, 10, 18), 1.5, 1.5)
        p.setPen(QPen(QColor("#94a3b8"), 0.9))
        p.drawLine(4, 8, 9, 8)
        p.drawLine(4, 12, 9, 12)
        p.drawLine(16, 8, 21, 8)
        p.drawLine(16, 12, 21, 12)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_new_document():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#3b82f6"), 1.4))
        p.setBrush(QBrush(QColor(59, 130, 246, 25)))
        p.drawRoundedRect(QRectF(5, 3, 16, 20), 2, 2)
        p.setPen(QPen(QColor("#10b981"), 1.8))
        p.drawLine(13, 9, 13, 17)
        p.drawLine(9, 13, 17, 13)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_add_page():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#a855f7"), 1.4))
        p.setBrush(QBrush(QColor(168, 85, 247, 25)))
        p.drawRoundedRect(QRectF(4, 3, 14, 19), 2, 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#10b981")))
        p.drawEllipse(QRectF(15, 14, 9, 9))
        p.setPen(QPen(QColor("#ffffff"), 1.4))
        p.drawLine(19, 16, 19, 21)
        p.drawLine(17, 18, 21, 18)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_settings():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#e0e0e0"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(13, 13), 3.0, 3.0)
        for i in range(8):
            angle = i * (2 * math.pi / 8)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            p.drawLine(QPointF(13 + cos_a * 5.8, 13 + sin_a * 5.8),
                       QPointF(13 + cos_a * 8.8, 13 + sin_a * 8.8))
        p.drawEllipse(QPointF(13, 13), 5.8, 5.8)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_update():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#38bdf8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(4, 4, 18, 18, 45 * 16, 260 * 16)
        p.drawLine(15, 4, 18, 7)
        p.drawLine(15, 10, 18, 7)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_fullscreen():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#a8b2c1"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Top Left
        p.drawLine(QPointF(6, 11), QPointF(6, 6))
        p.drawLine(QPointF(6, 6), QPointF(11, 6))
        # Top Right
        p.drawLine(QPointF(15, 6), QPointF(20, 6))
        p.drawLine(QPointF(20, 6), QPointF(20, 11))
        # Bottom Right
        p.drawLine(QPointF(20, 15), QPointF(20, 20))
        p.drawLine(QPointF(20, 20), QPointF(15, 20))
        # Bottom Left
        p.drawLine(QPointF(11, 20), QPointF(6, 20))
        p.drawLine(QPointF(6, 20), QPointF(6, 15))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_sign():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#707070"), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(QColor("#242424")))
        p.drawRoundedRect(QRectF(4.0, 3.0, 13.0, 18.0), 2.0, 2.0)

        p.setPen(QPen(QColor("#388bfd"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(6.0, 16.5)
        path.cubicTo(8.0, 13.5, 10.0, 18.5, 12.0, 14.0)
        path.cubicTo(13.5, 17.5, 15.0, 14.5, 16.5, 16.0)
        p.drawPath(path)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#f59e0b")))
        nib = QPolygonF([QPointF(17.0, 11.0), QPointF(22.0, 6.0), QPointF(23.5, 7.5), QPointF(18.5, 12.5)])
        p.drawPolygon(nib)
        p.setBrush(QBrush(QColor("#ffffff")))
        tip = QPolygonF([QPointF(15.5, 14.0), QPointF(17.0, 11.0), QPointF(18.5, 12.5)])
        p.drawPolygon(tip)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_image():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#a0aec0"), 1.4))
        p.setBrush(QBrush(QColor("#1e293b")))
        p.drawRoundedRect(QRectF(3.5, 4.5, 19.0, 15.0), 2.5, 2.5)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#f59e0b")))
        p.drawEllipse(QRectF(7.0, 7.5, 4.0, 4.0))

        p.setBrush(QBrush(QColor("#388bfd")))
        poly = QPolygonF([QPointF(4.5, 18.0), QPointF(11.0, 11.5), QPointF(16.0, 16.0), QPointF(19.0, 13.0), QPointF(21.5, 18.0)])
        p.drawPolygon(poly)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_compare():
        pix, p = ModernIconFactory._base()
        # Page 1 (Left / Back)
        p.setPen(QPen(QColor("#3b82f6"), 1.3))
        p.setBrush(QBrush(QColor(59, 130, 246, 30)))
        p.drawRoundedRect(QRectF(3.0, 4.0, 9.0, 14.0), 1.5, 1.5)
        # Page 2 (Right / Back)
        p.setPen(QPen(QColor("#10b981"), 1.3))
        p.setBrush(QBrush(QColor(16, 185, 129, 30)))
        p.drawRoundedRect(QRectF(14.0, 4.0, 9.0, 14.0), 1.5, 1.5)
        # Compare arrows between them
        p.setPen(QPen(QColor("#f59e0b"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(10, 21, 16, 21)
        p.drawLine(14, 19, 16, 21)
        p.drawLine(14, 23, 16, 21)
        p.drawLine(16, 2, 10, 2)
        p.drawLine(12, 0, 10, 2)
        p.drawLine(12, 4, 10, 2)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_redact():
        pix, p = ModernIconFactory._base()
        # Document
        p.setPen(QPen(QColor("#94a3b8"), 1.3))
        p.setBrush(QBrush(QColor(30, 41, 59, 180)))
        p.drawRoundedRect(QRectF(4.0, 3.0, 15.0, 19.0), 2.0, 2.0)
        # Regular text lines
        p.setPen(QPen(QColor("#64748b"), 1.2))
        p.drawLine(7, 7, 13, 7)
        p.drawLine(7, 18, 15, 18)
        # Thick black / danger redaction bar
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#ef4444")))
        p.drawRoundedRect(QRectF(6.0, 10.5, 14.0, 5.0), 1.2, 1.2)
        p.setBrush(QBrush(QColor("#111827")))
        p.drawRoundedRect(QRectF(7.0, 11.5, 12.0, 3.0), 0.8, 0.8)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_ocr():
        pix, p = ModernIconFactory._base()
        # Document outline
        p.setPen(QPen(QColor("#94a3b8"), 1.3))
        p.setBrush(QBrush(QColor(15, 23, 42, 180)))
        p.drawRoundedRect(QRectF(4.0, 3.0, 18.0, 20.0), 2.0, 2.0)
        # Text scan lines
        p.setPen(QPen(QColor("#475569"), 1.2))
        p.drawLine(7, 7, 15, 7)
        p.drawLine(7, 11, 18, 11)
        p.drawLine(7, 15, 14, 15)
        # Cyan Scanner beam line
        p.setPen(QPen(QColor("#06b6d4"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(2, 13, 24, 13)
        # Corner brackets (scanning focus)
        p.setPen(QPen(QColor("#38bdf8"), 1.4))
        p.drawLine(3, 2, 6, 2); p.drawLine(3, 2, 3, 5)
        p.drawLine(23, 2, 20, 2); p.drawLine(23, 2, 23, 5)
        p.drawLine(3, 24, 6, 24); p.drawLine(3, 24, 3, 21)
        p.drawLine(23, 24, 20, 24); p.drawLine(23, 24, 23, 21)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_edit_content():
        pix, p = ModernIconFactory._base()
        # Page
        p.setPen(QPen(QColor("#94a3b8"), 1.3))
        p.setBrush(QBrush(QColor(30, 41, 59, 180)))
        p.drawRoundedRect(QRectF(3.5, 3.0, 16.0, 20.0), 2.0, 2.0)
        # Image box inside
        p.setPen(QPen(QColor("#38bdf8"), 1.0))
        p.setBrush(QBrush(QColor(56, 189, 248, 40)))
        p.drawRoundedRect(QRectF(6.0, 6.0, 7.0, 5.5), 1.0, 1.0)
        # Text line
        p.setPen(QPen(QColor("#cbd5e1"), 1.2))
        p.drawLine(6, 14, 14, 14)
        p.drawLine(6, 17, 12, 17)
        # Pencil in bottom right
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#f59e0b")))
        nib = QPolygonF([QPointF(15.0, 20.0), QPointF(21.0, 14.0), QPointF(23.0, 16.0), QPointF(17.0, 22.0)])
        p.drawPolygon(nib)
        p.setBrush(QBrush(QColor("#ffffff")))
        tip = QPolygonF([QPointF(13.5, 22.5), QPointF(15.0, 20.0), QPointF(17.0, 22.0)])
        p.drawPolygon(tip)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_ruler():
        pix, p = ModernIconFactory._base()
        p.save()
        p.translate(13, 13)
        p.rotate(-45)
        # Ruler body (semi-rounded drafting straightedge)
        p.setPen(QPen(QColor("#38bdf8"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor(56, 189, 248, 55)))
        p.drawRoundedRect(QRectF(-12, -4.5, 24, 9), 2.0, 2.0)
        # Long tick marks along top edge
        p.setPen(QPen(QColor("#ffffff"), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(-9, -4.5), QPointF(-9, -1.2))
        p.drawLine(QPointF(-3, -4.5), QPointF(-3, -1.2))
        p.drawLine(QPointF(3, -4.5), QPointF(3, -1.2))
        p.drawLine(QPointF(9, -4.5), QPointF(9, -1.2))
        # Short tick marks
        p.setPen(QPen(QColor("#cbd5e1"), 0.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(-6, -4.5), QPointF(-6, -2.5))
        p.drawLine(QPointF(0, -4.5), QPointF(0, -2.5))
        p.drawLine(QPointF(6, -4.5), QPointF(6, -2.5))
        p.restore()
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_thumbnails():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#94a3b8"), 1.2))
        p.setBrush(QBrush(QColor(148, 163, 184, 45)))
        p.drawRoundedRect(QRectF(4.0, 4.0, 7.5, 7.5), 1.5, 1.5)
        p.drawRoundedRect(QRectF(14.5, 4.0, 7.5, 7.5), 1.5, 1.5)
        p.drawRoundedRect(QRectF(4.0, 14.5, 7.5, 7.5), 1.5, 1.5)
        p.drawRoundedRect(QRectF(14.5, 14.5, 7.5, 7.5), 1.5, 1.5)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_bookmark():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#38bdf8"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor(56, 189, 248, 55)))
        path = QPainterPath()
        path.moveTo(6.5, 3.5)
        path.lineTo(19.5, 3.5)
        path.lineTo(19.5, 22.5)
        path.lineTo(13.0, 17.5)
        path.lineTo(6.5, 22.5)
        path.closeSubpath()
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_star(filled: bool = True, color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        cx, cy = 13.0, 13.0
        r_out = 9.0
        r_in = 4.2
        path = QPainterPath()
        for i in range(10):
            angle = -math.pi / 2.0 + i * (math.pi / 5.0)
            r = r_out if i % 2 == 0 else r_in
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        stroke_color = QColor(color or ('#facc15' if filled else '#cbd5e1'))
        fill_color = QColor(color or '#facc15') if filled else QColor(0, 0, 0, 0)
        p.setPen(QPen(stroke_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(fill_color))
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_trash(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or '#ef4444')
        p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(QPointF(6.0, 8.0), QPointF(20.0, 8.0))
        p.drawLine(QPointF(10.5, 8.0), QPointF(10.5, 6.0))
        p.drawLine(QPointF(10.5, 6.0), QPointF(15.5, 6.0))
        p.drawLine(QPointF(15.5, 6.0), QPointF(15.5, 8.0))
        body = QPainterPath()
        body.moveTo(7.5, 8.0)
        body.lineTo(8.5, 20.5)
        body.lineTo(17.5, 20.5)
        body.lineTo(18.5, 8.0)
        p.drawPath(body)
        p.drawLine(QPointF(11.0, 11.0), QPointF(11.0, 17.5))
        p.drawLine(QPointF(15.0, 11.0), QPointF(15.0, 17.5))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_close(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#94a3b8")
        p.setPen(QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(8.0, 8.0), QPointF(18.0, 18.0))
        p.drawLine(QPointF(18.0, 8.0), QPointF(8.0, 18.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_minus(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#cbd5e1")
        p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(7.0, 13.0), QPointF(19.0, 13.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_plus(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#cbd5e1")
        p.setPen(QPen(col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(7.0, 13.0), QPointF(19.0, 13.0))
        p.drawLine(QPointF(13.0, 7.0), QPointF(13.0, 19.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_eyedropper(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#cbd5e1")
        p.save()
        p.translate(13, 13)
        p.rotate(45)
        p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(-2.5, -4.0, 5.0, 10.0), 1.0, 1.0)
        p.setBrush(QBrush(col))
        p.drawRoundedRect(QRectF(-3.5, -9.0, 7.0, 5.0), 2.0, 2.0)
        tip = QPainterPath()
        tip.moveTo(-1.5, 6.0)
        tip.lineTo(0.0, 9.0)
        tip.lineTo(1.5, 6.0)
        p.drawPath(tip)
        p.restore()
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_palette_grid(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#475569"), 1.2))
        p.setBrush(QBrush(QColor(30, 41, 59, 120)))
        p.drawEllipse(QRectF(3.5, 3.5, 19.0, 19.0))
        colors = [
            "#ef4444", "#f97316", "#facc15",
            "#22c55e", "#06b6d4", "#3b82f6",
            "#a855f7", "#ec4899", "#f43f5e"
        ]
        p.setPen(Qt.PenStyle.NoPen)
        idx = 0
        for row in range(3):
            for col in range(3):
                cx = 8.5 + col * 4.5
                cy = 8.5 + row * 4.5
                p.setBrush(QBrush(QColor(colors[idx % len(colors)])))
                p.drawEllipse(QPointF(cx, cy), 1.6, 1.6)
                idx += 1
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_pen_rack(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#94a3b8")
        p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for offset_x in (6.5, 13.0, 19.5):
            path = QPainterPath()
            path.moveTo(offset_x - 2.5, 18.0)
            path.lineTo(offset_x - 2.5, 10.0)
            path.lineTo(offset_x, 5.0)
            path.lineTo(offset_x + 2.5, 10.0)
            path.lineTo(offset_x + 2.5, 18.0)
            p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_pen_star(color: str = None, star_color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#cbd5e1")
        st_col = QColor(star_color or color or "#cbd5e1")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        # Tilted pen shaft and nib (pointing to bottom-left)
        pen_path = QPainterPath()
        pen_path.moveTo(6.0, 18.0)
        pen_path.lineTo(6.5, 14.5)
        pen_path.lineTo(13.5, 6.0)
        pen_path.arcTo(QRectF(12.5, 4.0, 6.0, 5.0), 135, 180)
        pen_path.lineTo(11.0, 15.0)
        pen_path.lineTo(6.0, 18.0)
        p.drawPath(pen_path)

        # Star outline at the bottom right
        p.setPen(QPen(st_col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        cx, cy = 16.5, 16.5
        r_out, r_in = 4.6, 2.1
        star_path = QPainterPath()
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            angle = -math.pi / 2.0 + i * (math.pi / 5.0)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                star_path.moveTo(x, y)
            else:
                star_path.lineTo(x, y)
        star_path.closeSubpath()
        p.drawPath(star_path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_brush(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#38bdf8")
        # Handle (angled wooden handle from top-right towards center)
        p.setPen(QPen(QColor("#94a3b8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(20.0, 5.0), QPointF(14.0, 11.0))
        # Ferrule (silver collar)
        p.setPen(QPen(QColor("#cbd5e1"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        p.drawLine(QPointF(13.5, 11.5), QPointF(11.5, 13.5))
        # Brush head / bristles (accent colored)
        path = QPainterPath()
        path.moveTo(11.5, 13.5)
        path.lineTo(7.5, 17.5)
        path.quadTo(5.0, 20.0, 5.5, 20.5)
        path.quadTo(6.0, 21.0, 8.5, 18.5)
        path.lineTo(13.5, 11.5)
        path.closeSubpath()
        p.setBrush(QBrush(col))
        p.setPen(QPen(col, 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        # Small paint dab at the tip
        p.setBrush(QBrush(col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(4.0, 19.5, 3.0, 3.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_attachment():
        pix, p = ModernIconFactory._base()
        p.save()
        p.translate(13, 13)
        p.rotate(45)
        p.setPen(QPen(QColor("#a78bfa"), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        # Clean paperclip curve
        path.moveTo(-4.0, 4.0)
        path.lineTo(-4.0, -5.0)
        path.arcTo(QRectF(-4.0, -9.0, 8.0, 8.0), 180, -180)
        path.lineTo(4.0, 5.5)
        path.arcTo(QRectF(-2.0, 2.5, 6.0, 6.0), 0, -180)
        path.lineTo(1.0, -3.5)
        p.drawPath(path)
        p.restore()
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_dock_side(to_side="right", color=None):
        pix, p = ModernIconFactory._base()
        col = QColor(color) if color else QColor("#e2e8f0")
        accent = QColor("#38bdf8")

        # Display / window frame outline
        p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(3.5, 4.5, 19.0, 17.0), 3.0, 3.0)

        # Highlight dock panel and direction arrow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(accent))
        if to_side == "right":
            # Right-side dock highlight
            p.drawRoundedRect(QRectF(16.5, 5.5, 5.0, 15.0), 1.5, 1.5)
            # Arrow pointing right
            p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(7.5, 13.0)
            path.lineTo(13.0, 13.0)
            path.moveTo(11.0, 10.5)
            path.lineTo(13.0, 13.0)
            path.lineTo(11.0, 15.5)
            p.drawPath(path)
        else:
            # Left-side dock highlight
            p.drawRoundedRect(QRectF(4.5, 5.5, 5.0, 15.0), 1.5, 1.5)
            # Arrow pointing left
            p.setPen(QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(18.5, 13.0)
            path.lineTo(13.0, 13.0)
            path.moveTo(15.0, 10.5)
            path.lineTo(13.0, 13.0)
            path.lineTo(15.0, 15.5)
            p.drawPath(path)

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_insert():
        pix, p = ModernIconFactory._base()
        p.setPen(QPen(QColor("#38bdf8"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Crisp modern plus symbol
        p.drawLine(13, 6, 13, 20)
        p.drawLine(6, 13, 20, 13)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_table():
        pix, p = ModernIconFactory._base()
        col = QColor("#e2e8f0")
        accent = QColor("#38bdf8")
        # Outer table frame
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(4.0, 5.0, 18.0, 16.0), 2.0, 2.0)
        # Header separator
        p.setPen(QPen(accent, 1.5, Qt.PenStyle.SolidLine))
        p.drawLine(4, 10, 22, 10)
        # Middle row line
        p.setPen(QPen(col, 1.2, Qt.PenStyle.SolidLine))
        p.drawLine(4, 15, 22, 15)
        # Vertical column lines
        p.drawLine(10, 5, 10, 21)
        p.drawLine(16, 5, 16, 21)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_emoji(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#e2e8f0")
        accent = QColor("#f59e0b") if not color else col
        # Crisp modern vector outline circle
        p.setPen(QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(4.0, 4.0, 18.0, 18.0))
        # Eyes
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(accent))
        p.drawEllipse(QRectF(8.2, 9.2, 2.3, 2.5))
        p.drawEllipse(QRectF(15.5, 9.2, 2.3, 2.5))
        # Crisp vector smile curve
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(accent, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(8.5, 14.5)
        path.quadTo(13.0, 18.5, 17.5, 14.5)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_voice_recording(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(10.0, 4.0, 6.0, 11.0), 3.0, 3.0)
        path = QPainterPath()
        path.arcMoveTo(QRectF(7.0, 7.0, 12.0, 10.5), 190)
        path.arcTo(QRectF(7.0, 7.0, 12.0, 10.5), 190, 160)
        p.drawPath(path)
        p.drawLine(QPointF(13.0, 17.5), QPointF(13.0, 21.0))
        p.drawLine(QPointF(9.5, 21.0), QPointF(16.5, 21.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_image(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(3.5, 4.5, 19.0, 17.0), 3.0, 3.0)
        p.drawEllipse(QRectF(14.8, 7.5, 3.4, 3.4))
        m = QPainterPath()
        m.moveTo(3.5, 18.0)
        m.lineTo(8.5, 12.5)
        m.lineTo(13.0, 16.5)
        m.lineTo(16.0, 13.5)
        m.lineTo(22.5, 18.5)
        p.drawPath(m)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_camera(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(3.5, 7.5, 19.0, 14.0), 3.0, 3.0)
        p.drawRoundedRect(QRectF(8.0, 5.0, 5.0, 3.0), 1.0, 1.0)
        p.drawEllipse(QRectF(9.5, 11.0, 7.0, 7.0))
        p.setBrush(QBrush(col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(12.0, 13.5, 2.0, 2.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_scan(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(4.0, 8.5), QPointF(4.0, 5.0))
        p.drawLine(QPointF(4.0, 5.0), QPointF(7.5, 5.0))
        p.drawLine(QPointF(18.5, 5.0), QPointF(22.0, 5.0))
        p.drawLine(QPointF(22.0, 5.0), QPointF(22.0, 8.5))
        p.drawLine(QPointF(4.0, 17.5), QPointF(4.0, 21.0))
        p.drawLine(QPointF(4.0, 21.0), QPointF(7.5, 21.0))
        p.drawLine(QPointF(18.5, 21.0), QPointF(22.0, 21.0))
        p.drawLine(QPointF(22.0, 21.0), QPointF(22.0, 17.5))
        p.drawRoundedRect(QRectF(8.0, 8.0, 10.0, 10.0), 1.5, 1.5)
        p.drawLine(QPointF(10.5, 11.0), QPointF(15.5, 11.0))
        p.drawLine(QPointF(10.5, 14.0), QPointF(13.5, 14.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_audio(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(8.5, 17.0)
        p.rotate(-25)
        p.setBrush(QBrush(col))
        p.drawEllipse(QRectF(-3.2, -2.2, 6.4, 4.4))
        p.restore()
        p.drawLine(QPointF(11.5, 16.5), QPointF(11.5, 5.5))
        path = QPainterPath()
        path.moveTo(11.5, 5.5)
        path.cubicTo(16.5, 7.0, 18.0, 11.0, 17.0, 13.5)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_drawing(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(6.0, 12.0)
        path.cubicTo(4.0, 6.0, 12.0, 3.5, 18.0, 6.0)
        path.cubicTo(23.0, 8.0, 23.0, 16.0, 18.0, 19.5)
        path.cubicTo(14.0, 22.0, 12.0, 17.0, 9.0, 17.0)
        path.cubicTo(6.5, 17.0, 7.0, 15.0, 6.0, 12.0)
        p.drawPath(path)
        p.drawEllipse(QRectF(15.0, 13.5, 3.0, 3.0))
        p.drawEllipse(QRectF(9.0, 7.5, 2.0, 2.0))
        p.drawEllipse(QRectF(14.0, 7.0, 2.0, 2.0))
        p.drawEllipse(QRectF(8.0, 12.0, 2.0, 2.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_sticky_note(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(4.5, 7.0)
        path.quadTo(4.5, 4.5, 7.0, 4.5)
        path.lineTo(19.0, 4.5)
        path.quadTo(21.5, 4.5, 21.5, 7.0)
        path.lineTo(21.5, 14.5)
        path.lineTo(15.5, 20.5)
        path.lineTo(7.0, 20.5)
        path.quadTo(4.5, 20.5, 4.5, 18.0)
        path.closeSubpath()
        p.drawPath(path)
        flap = QPainterPath()
        flap.moveTo(15.5, 20.5)
        flap.lineTo(15.5, 15.0)
        flap.quadTo(15.5, 14.5, 16.0, 14.5)
        flap.lineTo(21.5, 14.5)
        p.drawPath(flap)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_menu_table(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        pen = QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(4.0, 5.0, 18.0, 16.0), 2.5, 2.5)
        p.drawLine(QPointF(4.0, 10.5), QPointF(22.0, 10.5))
        p.drawLine(QPointF(4.0, 15.5), QPointF(22.0, 15.5))
        p.drawLine(QPointF(10.0, 5.0), QPointF(10.0, 21.0))
        p.drawLine(QPointF(16.0, 5.0), QPointF(16.0, 21.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_mic():
        pix, p = ModernIconFactory._base()
        accent = QColor("#ec4899")
        col = QColor("#e2e8f0")
        # Mic capsule
        p.setPen(QPen(accent, 1.4, Qt.PenStyle.SolidLine))
        p.setBrush(QBrush(accent))
        p.drawRoundedRect(QRectF(9.5, 4.5, 7.0, 11.0), 3.5, 3.5)
        # Mic cradle arc
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        path = QPainterPath()
        path.arcMoveTo(QRectF(7.0, 7.0, 12.0, 11.0), 190)
        path.arcTo(QRectF(7.0, 7.0, 12.0, 11.0), 190, 160)
        p.drawPath(path)
        # Stand stem & base
        p.drawLine(13, 18, 13, 21)
        p.drawLine(9, 21, 17, 21)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_video():
        pix, p = ModernIconFactory._base()
        accent = QColor("#8b5cf6")
        col = QColor("#e2e8f0")
        # Camera body
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(4.0, 6.5, 13.0, 13.0), 2.5, 2.5)
        # Lens triangle
        path = QPainterPath()
        path.moveTo(17.5, 10.5)
        path.lineTo(22.0, 7.5)
        path.lineTo(22.0, 18.5)
        path.lineTo(17.5, 15.5)
        path.closeSubpath()
        p.setBrush(QBrush(accent))
        p.setPen(QPen(accent, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        # Play glyph inside camera body
        play = QPainterPath()
        play.moveTo(8.5, 10.0)
        play.lineTo(13.0, 13.0)
        play.lineTo(8.5, 16.0)
        play.closeSubpath()
        p.setBrush(QBrush(accent))
        p.drawPath(play)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_url():
        pix, p = ModernIconFactory._base()
        col = QColor("#38bdf8")
        # Globe outline
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(4.5, 4.5, 17.0, 17.0))
        # Equator
        p.drawLine(4, 13, 22, 13)
        # Longitude oval
        p.drawEllipse(QRectF(8.0, 4.5, 10.0, 17.0))
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_fit_page(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Outer document rectangle
        p.drawRoundedRect(QRectF(6.0, 3.5, 14.0, 19.0), 2.0, 2.0)
        # Inner fit arrows pointing inward
        p.drawLine(10, 8, 13, 8)
        p.drawLine(13, 8, 13, 11)
        p.drawLine(16, 18, 13, 18)
        p.drawLine(13, 18, 13, 15)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_speech(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#38bdf8")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(col))
        # Megaphone / Speaker body
        speaker = QPainterPath()
        speaker.moveTo(5, 10)
        speaker.lineTo(9, 10)
        speaker.lineTo(14, 6)
        speaker.lineTo(14, 20)
        speaker.lineTo(9, 16)
        speaker.lineTo(5, 16)
        speaker.closeSubpath()
        p.drawPath(speaker)
        # Sound waves
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(14.0, 9.0, 6.0, 8.0), -60 * 16, 120 * 16)
        p.drawArc(QRectF(15.5, 6.5, 9.0, 13.0), -60 * 16, 120 * 16)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_nav_back(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        p.setPen(QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(15, 6, 8, 13)
        p.drawLine(8, 13, 15, 20)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_nav_forward(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        p.setPen(QPen(col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(10, 6, 17, 13)
        p.drawLine(17, 13, 10, 20)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_reading_mode(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#fbbf24")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Open book or eyeglasses
        book = QPainterPath()
        book.moveTo(13, 8)
        book.lineTo(13, 20)
        # Left page
        book.moveTo(13, 8)
        book.quadTo(8, 6, 4, 8)
        book.lineTo(4, 18)
        book.quadTo(8, 16, 13, 18)
        # Right page
        book.moveTo(13, 8)
        book.quadTo(18, 6, 22, 8)
        book.lineTo(22, 18)
        book.quadTo(18, 16, 13, 18)
        p.drawPath(book)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_comments(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#38bdf8")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        bubble = QPainterPath()
        bubble.moveTo(5, 6)
        bubble.quadTo(5, 4.5, 7, 4.5)
        bubble.lineTo(19, 4.5)
        bubble.quadTo(21, 4.5, 21, 6)
        bubble.lineTo(21, 15)
        bubble.quadTo(21, 16.5, 19, 16.5)
        bubble.lineTo(11, 16.5)
        bubble.lineTo(7, 20.5)
        bubble.lineTo(7, 16.5)
        bubble.lineTo(6, 16.5)
        bubble.quadTo(5, 16.5, 5, 15)
        bubble.closeSubpath()
        p.drawPath(bubble)
        # Lines inside
        p.drawLine(8, 8, 17, 8)
        p.drawLine(8, 12, 14, 12)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_doc_properties(color: str = None) -> QIcon:
        pix, p = ModernIconFactory._base()
        col = QColor(color or "#f1f5f9")
        p.setPen(QPen(col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Document sheet
        doc = QPainterPath()
        doc.moveTo(6, 4)
        doc.lineTo(15, 4)
        doc.lineTo(20, 9)
        doc.lineTo(20, 21)
        doc.lineTo(6, 21)
        doc.closeSubpath()
        p.drawPath(doc)
        p.drawLine(15, 4, 15, 9)
        p.drawLine(15, 9, 20, 9)
        # Info 'i' symbol
        p.drawLine(13, 12, 13, 12)
        p.drawLine(13, 14, 13, 18)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_home(color=None):
        pix, p = ModernIconFactory._base()
        clr = QColor(color) if color else QColor("#e0e0e0")
        p.setPen(QPen(clr, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(4, 13); path.lineTo(13, 5); path.lineTo(22, 13)
        p.drawPath(path)
        p.drawRoundedRect(QRectF(6.5, 12.5, 13, 9), 1.5, 1.5)
        p.drawLine(13, 16, 13, 21)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_folder(color=None):
        pix, p = ModernIconFactory._base()
        clr = QColor(color) if color else QColor("#e0e0e0")
        p.setPen(QPen(clr, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(4, 8)
        path.lineTo(10, 8)
        path.lineTo(12, 10)
        path.lineTo(22, 10)
        path.lineTo(22, 20)
        path.lineTo(4, 20)
        path.closeSubpath()
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_all_grid(color=None):
        pix, p = ModernIconFactory._base()
        clr = QColor(color) if color else QColor("#e0e0e0")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(clr))
        p.drawRoundedRect(QRectF(4, 5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(10.75, 5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(17.5, 5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(4, 11.5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(10.75, 11.5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(17.5, 11.5, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(4, 18, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(10.75, 18, 4.5, 4.5), 1, 1)
        p.drawRoundedRect(QRectF(17.5, 18, 4.5, 4.5), 1, 1)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_chevron_up(color=None):
        pix, p = ModernIconFactory._base()
        clr = QColor(color) if color else QColor("#e0e0e0")
        p.setPen(QPen(clr, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(6, 16); path.lineTo(13, 9); path.lineTo(20, 16)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_chevron_down(color=None):
        pix, p = ModernIconFactory._base()
        clr = QColor(color) if color else QColor("#e0e0e0")
        p.setPen(QPen(clr, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(6, 10); path.lineTo(13, 17); path.lineTo(20, 10)
        p.drawPath(path)
        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_compress():
        pix, p = ModernIconFactory._base()
        # Document outline
        p.setPen(QPen(QColor('#94a3b8'), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(QColor('#1e293b')))
        p.drawRoundedRect(QRectF(4.0, 3.0, 18.0, 20.0), 2.0, 2.0)

        # Inward compression arrows
        p.setPen(QPen(QColor('#38bdf8'), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Top arrow pointing down
        p.drawLine(QPointF(13.0, 6.0), QPointF(13.0, 11.0))
        p.drawLine(QPointF(10.5, 8.5), QPointF(13.0, 11.0))
        p.drawLine(QPointF(15.5, 8.5), QPointF(13.0, 11.0))

        # Bottom arrow pointing up
        p.drawLine(QPointF(13.0, 20.0), QPointF(13.0, 15.0))
        p.drawLine(QPointF(10.5, 17.5), QPointF(13.0, 15.0))
        p.drawLine(QPointF(15.5, 17.5), QPointF(13.0, 15.0))

        # Center compression vise line
        p.setPen(QPen(QColor('#f59e0b'), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(8.0, 13.0), QPointF(18.0, 13.0))

        p.end()
        return QIcon(pix)

    @staticmethod
    def icon_keyboard_shortcuts():
        pix, p = ModernIconFactory._base()
        # Keyboard body
        p.setPen(QPen(QColor('#94a3b8'), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(QColor('#1e293b')))
        p.drawRoundedRect(QRectF(3.0, 6.0, 20.0, 14.0), 2.5, 2.5)

        # Key grid
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor('#38bdf8')))
        # Row 1 keys
        for x in (5.5, 9.5, 13.5, 17.5):
            p.drawRoundedRect(QRectF(x, 8.5, 2.5, 2.5), 0.5, 0.5)
        # Row 2 keys
        for x in (5.5, 9.5, 13.5, 17.5):
            p.drawRoundedRect(QRectF(x, 12.0, 2.5, 2.5), 0.5, 0.5)
        # Spacebar
        p.drawRoundedRect(QRectF(7.5, 15.5, 10.5, 2.0), 0.5, 0.5)

        p.end()
        return QIcon(pix)


def _wrap_icon_methods():
    for attr in dir(ModernIconFactory):
        if attr.startswith("icon_") and attr != "icon_app":
            orig = getattr(ModernIconFactory, attr)
            if callable(orig):
                def make_cached(fn, name):
                    def wrapper(*args, **kwargs):
                        cache = ModernIconFactory._icon_cache
                        if not args and not kwargs:
                            key = name
                        else:
                            key = (name, args, tuple(sorted(kwargs.items())))
                        if key not in cache:
                            cache[key] = fn(*args, **kwargs)
                        return cache[key]
                    return wrapper
                setattr(ModernIconFactory, attr, staticmethod(make_cached(orig, attr)))

_wrap_icon_methods()

# AuraPDF Marka İsimlendirmesi ile Geriye Dönük Uyumluluk Takma Adı (Alias)
AuraIconFactory = ModernIconFactory
