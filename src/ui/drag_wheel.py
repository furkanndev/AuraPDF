"""
AuraPDF - Sürükle-Bırak Eylem Tekerleği
=======================================
Dosya gezgininden / masaüstünden bir PDF dosyası Ctrl tuşu basılıyken pencerenin
üzerine sürüklendiğinde imlecin çevresinde dairesel bir eylem tekerleği açılır.
Kullanıcı dosyayı tekerlekteki bir dilime bırakarak Birleştir, Böl veya
Word / PowerPoint / Excel'e Dönüştür işlemini doğrudan o dosyayla başlatır.
Orta daireye bırakmak dosyayı her zamanki gibi yeni sekmede açar.
"""

import math
import os
from typing import Callable, List, Optional

from PyQt6.QtCore import Qt, QEvent, QObject, QPointF, QRectF, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QGuiApplication
from PyQt6.QtWidgets import QWidget

from src.core import drag_wheel_config as wheel_cfg
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_theme_palette
from src.ui.icons import AuraIconFactory

_GAP_DEG = 2.4


def _segments_for(actions) -> tuple:
    """Eylem kodlarından (kod, i18n anahtarı, ikon metodu) üçlülerini üretir."""
    return tuple((code,) + tuple(wheel_cfg.CATALOG[code]) for code in actions if code in wheel_cfg.CATALOG)


def extract_pdf_paths(mime) -> List[str]:
    """Sürüklenen veriden var olan PDF dosya yollarını döner."""
    paths: List[str] = []
    try:
        if mime is not None and mime.hasUrls():
            for u in mime.urls():
                p = u.toLocalFile()
                if p and p.lower().endswith(".pdf") and os.path.isfile(p):
                    paths.append(os.path.normpath(p))
    except Exception:
        return []
    return paths


def run_wheel_action(viewer, action: str, paths: List[str]) -> None:
    """Seçilen tekerlek eylemini bırakılan dosya(lar)la başlatır."""
    if not paths:
        return
    if action == "open":
        viewer.handle_dropped_urls([_PathUrl(p) for p in paths])
        return
    if action == "merge":
        QTimer.singleShot(60, _raise_active_modal)
        viewer.open_merge_dialog(list(paths))
        return

    src = paths[0]
    base = os.path.splitext(src)[0]
    from src.ui.dialogs import toolbox_dialogs as td

    if action == "split":
        dlg = td.PDFSplitDialog(viewer)
        dlg.txt_source.setText(src)
        dlg.txt_dest.setText(os.path.dirname(src))
    elif action == "word":
        dlg = td.PDFToWordDialog(viewer)
        dlg.txt_source.setText(src)
        dlg.txt_dest.setText(f"{base}.docx")
    elif action == "pptx":
        dlg = td.PDFToPowerPointDialog(viewer)
        dlg.txt_source.setText(src)
        dlg.txt_dest.setText(f"{base}.pptx")
    elif action == "excel":
        dlg = td.PDFToExcelDialog(viewer)
        dlg.txt_source.setText(src)
        dlg.txt_dest.setText(f"{base}.xlsx")
    elif action == "epub":
        dlg = td.PDFToEbookDialog(viewer, "epub")
        dlg.txt_source.setText(src)
        dlg.txt_dest.setText(f"{base}.epub")
    elif action == "compress":
        from src.ui.dialogs.pdf_compress_dialog import PDFCompressDialog
        dlg = PDFCompressDialog(viewer, default_input_path=src)
    elif action == "protect":
        dlg = td.PDFEncryptDialog(viewer)
        dlg.txt_protect_src.setText(src)
        dlg.txt_protect_dst.setText(f"{base}_sifreli.pdf")
    else:
        return
    # Tepsi yardımcısından başlatıldığında pencere arkada kalmasın
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()
    force_foreground(dlg)
    dlg.exec()


def force_foreground(widget) -> None:
    """Pencereyi, arka plandan başlatılmış olsa bile öne getirir.

    Windows, o an girdi almayan bir sürecin pencereyi öne getirmesini engeller (görev
    çubuğunda yanıp söner). Ön plandaki pencerenin iş parçacığına geçici bağlanılarak aşılır."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = int(widget.winId())
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        my_thread = kernel32.GetCurrentThreadId()
        attached = bool(fg_thread and fg_thread != my_thread and user32.AttachThreadInput(my_thread, fg_thread, True))
        try:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(my_thread, fg_thread, False)
    except Exception:
        pass


def _raise_active_modal() -> None:
    """Açık modal pencereyi öne getirir (başka bir süreçten tetiklenen eylemler için)."""
    try:
        from PyQt6.QtWidgets import QApplication
        w = QApplication.activeModalWidget()
        if w is not None:
            w.raise_()
            w.activateWindow()
            force_foreground(w)
    except Exception:
        pass


class _PathUrl:
    """handle_dropped_urls'in beklediği toLocalFile() arayüzünü sağlayan hafif sarmalayıcı."""

    def __init__(self, path: str):
        self._path = path

    def toLocalFile(self) -> str:
        return self._path


class AuraDragWheelOverlay(QWidget):
    """Ana pencerenin üzerinde açılan, bırakma hedefi olan dairesel eylem tekerleği."""

    def __init__(self, viewer=None, on_choice: Optional[Callable[[str, List[str]], None]] = None):
        """viewer verilirse ana pencerenin üzerinde örtü olarak çalışır; verilmezse
        (sistem tepsisi yardımcısı) imlecin altında açılan bağımsız, üstte duran küçük pencere olur.

        on_choice(eylem, dosyalar): bırakma sonrası çağrılır; verilmezse viewer üzerinde çalıştırılır.
        """
        standalone = viewer is None
        if standalone:
            super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                             Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        else:
            super().__init__(viewer)
        self._viewer = viewer
        self._standalone = standalone
        self._on_choice = on_choice
        self._armed = not standalone  # bağımsız modda PDF doğrulanana dek neredeyse görünmez
        self._segments = _segments_for(wheel_cfg.DEFAULT_ACTIONS)
        self._outer_r, self._inner_r = wheel_cfg.SIZES[wheel_cfg.DEFAULT_SIZE]
        self._center = QPointF(0, 0)
        self._hover: Optional[str] = None
        self._paths: List[str] = []
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()

    # ------------------------------------------------------------------ ayar
    def apply_config(self, cfg: Optional[dict] = None) -> None:
        """Eylem listesini ve boyutu ayarlardan (veya verilen sözlükten) yükler."""
        cfg = cfg or wheel_cfg.load_config()
        self._segments = _segments_for(cfg["actions"])
        self._outer_r, self._inner_r = wheel_cfg.SIZES.get(cfg["size"], wheel_cfg.SIZES[wheel_cfg.DEFAULT_SIZE])

    # ------------------------------------------------------------------ gösterim
    def present_at_cursor(self, global_pos) -> None:
        """Bağımsız mod: tekerleği imlecin altında, yine de PDF doğrulanana dek görünmez açar."""
        self.apply_config()
        side = int((self._outer_r + 40) * 2)
        self._armed = False
        self._paths = []
        self._hover = None
        self.setFixedSize(side, side + 30)
        self._center = QPointF(side / 2.0, side / 2.0)
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = min(max(global_pos.x() - side // 2, geo.left()), geo.right() - side)
        y = min(max(global_pos.y() - side // 2, geo.top()), geo.bottom() - side - 30)
        # Ekran kenarına sıkışırsa merkez imleçten kayar
        self._center = QPointF(global_pos.x() - x, global_pos.y() - y)
        self.move(x, y)
        self.show()
        self.raise_()
        self.update()

    def present(self, global_pos, paths: List[str]) -> None:
        self.apply_config()
        self._paths = list(paths)
        self.setGeometry(self._viewer.rect())
        local = self.mapFromGlobal(global_pos) if self.isVisible() else self._viewer.mapFromGlobal(global_pos)
        margin = self._outer_r + 12
        cx = min(max(local.x(), margin), max(margin, self.width() - margin))
        cy = min(max(local.y(), margin), max(margin, self.height() - margin))
        self._center = QPointF(cx, cy)
        self._hover = None
        self.raise_()
        self.show()
        self.update()

    def dismiss(self) -> None:
        self._hover = None
        self._paths = []
        if self._standalone:
            self._armed = False
        self.hide()

    # ------------------------------------------------------------------ geometri
    def _hit_test(self, pos) -> Optional[str]:
        dx = pos.x() - self._center.x()
        dy = pos.y() - self._center.y()
        dist = math.hypot(dx, dy)
        if dist <= self._inner_r:
            return "open"
        if dist > self._outer_r + 24:
            return None
        step = 360.0 / len(self._segments)
        # Saat yönünde, üstten başlayarak; ilk dilim tam tepede ortalanır
        ang = (math.degrees(math.atan2(dy, dx)) + 90.0 + step / 2.0) % 360.0
        return self._segments[int(ang // step) % len(self._segments)][0]

    # ------------------------------------------------------------------ sürükle-bırak
    def dragEnterEvent(self, event):
        paths = extract_pdf_paths(event.mimeData())
        if paths:
            self._paths = paths
            if self._standalone and not self._armed:
                self._armed = True
                self.update()
            event.acceptProposedAction()
        else:
            event.ignore()
            if self._standalone:
                self.dismiss()

    def dragMoveEvent(self, event):
        pos = event.position()
        hov = self._hit_test(pos)
        if hov != self._hover:
            self._hover = hov
            self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.dismiss()
        event.accept()

    def dropEvent(self, event):
        paths = extract_pdf_paths(event.mimeData()) or list(self._paths)
        action = self._hit_test(event.position())
        event.acceptProposedAction()
        self.dismiss()
        if not action or not paths:
            return
        # Sürükleme kaynağı (Gezgin) donmasın diye diyalog olay döngüsüne bırakıldıktan sonra açılır
        viewer = self._viewer
        cb = self._on_choice
        if cb is not None:
            QTimer.singleShot(0, lambda: cb(action, paths))
        else:
            QTimer.singleShot(0, lambda: run_wheel_action(viewer, action, paths))

    # ------------------------------------------------------------------ çizim
    def paintEvent(self, _event):
        p0 = QPainter(self)
        if self._standalone and not self._armed:
            # Neredeyse saydam ama tıklama/bırakma hedefi olarak algılanan alan
            p0.fillRect(self.rect(), QColor(0, 0, 0, 3))
            p0.end()
            return
        p0.end()
        pal = get_theme_palette(self._viewer)
        card = QColor(pal.get("card", "#35383c"))
        bg = QColor(pal.get("bg", "#2b2d30"))
        border = QColor(pal.get("border", "#444850"))
        accent = QColor(pal.get("accent", "#60a5fa"))
        text = QColor(pal.get("text", "#f8fafc"))
        muted = QColor(pal.get("muted", "#cbd5e1"))

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if not self._standalone:
            veil = QColor(bg)
            veil.setAlpha(120)
            p.fillRect(self.rect(), veil)

        c = self._center
        outer = QRectF(c.x() - self._outer_r, c.y() - self._outer_r, self._outer_r * 2, self._outer_r * 2)
        inner = QRectF(c.x() - self._inner_r, c.y() - self._inner_r, self._inner_r * 2, self._inner_r * 2)
        step = 360.0 / len(self._segments)

        # Qt açıları saat yönünün tersine ve 3 yönünden başlar; ilk dilim tam tepede ortalanır
        for i, (code, key, icon_name) in enumerate(self._segments):
            mid_cw = i * step  # tepeden saat yönünde derece
            start_qt = 90.0 - mid_cw + step / 2.0 - _GAP_DEG / 2.0
            span_qt = -(step - _GAP_DEG)

            path = QPainterPath()
            path.arcMoveTo(outer, start_qt)
            path.arcTo(outer, start_qt, span_qt)
            path.arcTo(inner, start_qt + span_qt, -span_qt)
            path.closeSubpath()

            hot = (self._hover == code)
            fill = QColor(accent) if hot else QColor(card)
            fill.setAlpha(235 if hot else 225)
            p.setPen(QPen(accent if hot else border, 1.6 if hot else 1.0))
            p.setBrush(QBrush(fill))
            p.drawPath(path)

            # İkon + etiket dilimin orta yarıçapında
            rad = math.radians(mid_cw - 90.0)
            rm = (self._outer_r + self._inner_r) / 2.0 + 6
            mx = c.x() + rm * math.cos(rad)
            my = c.y() + rm * math.sin(rad)
            try:
                icon = getattr(AuraIconFactory, icon_name)()
                pm = icon.pixmap(36, 36)
                p.drawPixmap(int(mx - 18), int(my - 30), pm)
            except Exception:
                pass
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSizeF(max(8.5, f.pointSizeF() - 0.5))
            p.setFont(f)
            p.setPen(QColor("#ffffff") if hot else text)
            # Çok dilimli/küçük tekerlekte komşu etiketler çakışmasın: genişlik yay uzunluğuyla sınırlı
            arc_w = 2.0 * math.pi * rm / len(self._segments)
            tw = max(52.0, min(108.0, arc_w - 4.0))
            label = p.fontMetrics().elidedText(LanguageManager.tr(key), Qt.TextElideMode.ElideRight, int(tw))
            p.drawText(QRectF(mx - tw / 2.0, my + 8, tw, 22), Qt.AlignmentFlag.AlignCenter, label)

        # Orta daire: normal aç
        hot_c = (self._hover == "open")
        centre_fill = QColor(accent) if hot_c else QColor(card)
        centre_fill.setAlpha(245)
        p.setPen(QPen(accent if hot_c else border, 1.6 if hot_c else 1.0))
        p.setBrush(QBrush(centre_fill))
        p.drawEllipse(inner.adjusted(4, 4, -4, -4))
        f = QFont(self.font())
        f.setBold(True)
        f.setPointSizeF(max(8.5, f.pointSizeF() - 0.5))
        p.setFont(f)
        p.setPen(QColor("#ffffff") if hot_c else text)
        p.drawText(inner, Qt.AlignmentFlag.AlignCenter, LanguageManager.tr("drag_wheel_open"))

        # İpucu: tekerleğin altında
        hint = LanguageManager.tr("drag_wheel_hint")
        if len(self._paths) > 1:
            hint = LanguageManager.tr("drag_wheel_multi_hint", count=len(self._paths))
        f2 = QFont(self.font())
        f2.setPointSizeF(max(8.5, f2.pointSizeF() - 1))
        p.setFont(f2)
        p.setPen(muted)
        p.drawText(QRectF(c.x() - 220, c.y() + self._outer_r + 6, 440, 24), Qt.AlignmentFlag.AlignCenter, hint)
        p.end()


class DragWheelController(QObject):
    """Uygulama genelinde PDF sürüklemesi + Ctrl kombinasyonunu izleyip tekerleği açar."""

    def __init__(self, viewer):
        super().__init__(viewer)
        self._viewer = viewer
        self._overlay = AuraDragWheelOverlay(viewer)

    def eventFilter(self, obj, event):
        try:
            et = event.type()
            if et not in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                return False
            if not isinstance(obj, QWidget) or obj.window() is not self._viewer:
                return False
            if obj is self._overlay:
                return False
            ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier) or \
                bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
            if not ctrl:
                return False
            paths = extract_pdf_paths(event.mimeData())
            if not paths:
                return False
            if not self._overlay.isVisible():
                self._overlay.present(obj.mapToGlobal(event.position().toPoint()), paths)
            event.acceptProposedAction()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False
