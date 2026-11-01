"""
AuraPDF - Arayüz Hareket Motoru
===============================
Pencere açılışı, buton geri bildirimi, sayfa geçişi ve tema değişimi
animasyonlarını uygulama genelinde tek bir olay süzgeciyle yönetir.
"""

import math

from PyQt6.QtCore import (QAbstractAnimation, QEasingCurve, QElapsedTimer, QEvent, QObject,
                          QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation, QRectF, QSettings,
                          Qt, QThread, QTimer, pyqtProperty)
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (QApplication, QDialog, QGraphicsOpacityEffect, QGraphicsView, QLabel,
                             QMenu, QMessageBox, QPushButton, QStackedWidget, QToolButton, QWidget)

from src.core.i18n import LanguageManager
from src.ui.ui_style import MOTION_PROFILES
from src.ui.ui_style import active_style as get_interface_style


def _keeps_running_thread(dialog: QDialog) -> bool:
    threads = dialog.findChildren(QThread) + [v for v in vars(dialog).values() if isinstance(v, QThread)]
    return any(thread.isRunning() for thread in threads)


def install_dialog_release():
    """Ana pencereye bağlı diyalogların kapandıktan sonra bellekte birikmesini önler."""
    run_dialog = QDialog.exec

    def exec_and_release(dialog, *args):
        result = run_dialog(dialog, *args)
        # deleteLater bu olay döngüsüne dönülene dek bekler; çağıran sonuçları yine okuyabilir.
        if dialog.parent() is not None and not _keeps_running_thread(dialog):
            dialog.deleteLater()
        return result

    QDialog.exec = exec_and_release


class AuraBusyIndicator(QWidget):
    """Süren işin adımını yanıp sönen üç çubukla, biten işi onay işaretiyle gösteren durum satırı."""
    FRAME_MS = 33
    BAR_COUNT = 3
    BAR_PERIOD_MS = 900

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setMinimumWidth(240)
        self._text = ""
        self._done = False
        self._accent = QColor("#60a5fa")
        self._ink = QColor("#f8fafc")
        self._last_frame = 0
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self.update)
        self._card = None
        self.hide()

    def set_colors(self, accent: str, ink: str):
        self._accent = QColor(accent)
        self._ink = QColor(ink)
        self.update()

    def float_over(self, window: QWidget, card: str):
        """Göstergeyi, verilen pencerenin üstünde stil zincirine bağlı olmayan bir bildirime çevirir."""
        self._card = QColor(card)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(300, 48)
        area = window.frameGeometry()
        self.move(area.center().x() - 150, area.top() + 72)

    def start(self, text: str):
        self._text = text
        self._done = False
        self._clock.restart()
        self._last_frame = 0
        self.show()
        self._timer.start()

    def set_step(self, text: str):
        self._text = text
        self.repaint()

    def pulse(self):
        """Ana iş parçacığı meşgulken bile çubukların yanıp sönmesini sürdürür."""
        now = self._clock.elapsed()
        if self.isVisible() and now - self._last_frame >= self.FRAME_MS:
            # Yeniden çizimin ürettiği olaylar buraya dönmesin diye zaman önce işaretlenir.
            self._last_frame = now
            self.repaint()

    def finish(self, text: str):
        self._text = text
        self._done = True
        self._timer.stop()
        self.repaint()

    def stop(self):
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        self._last_frame = self._clock.elapsed()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._card is not None:
            p.setPen(QPen(self._accent, 1))
            p.setBrush(self._card)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
            p.translate(14, 12)
        if self._done:
            p.setPen(QPen(self._accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline([QPointF(5, 12.5), QPointF(9.5, 17), QPointF(17, 7.5)])
        else:
            # Üç dikdörtgen sırayla parlayıp söner; hareket kapalıysa sabit durur.
            p.setPen(Qt.PenStyle.NoPen)
            for index in range(self.BAR_COUNT):
                wave = 1.0
                if AuraMotion.enabled:
                    wave = 0.5 + 0.5 * math.sin(self._last_frame / self.BAR_PERIOD_MS * math.tau - index * 1.1)
                bar = QColor(self._accent)
                bar.setAlphaF(0.22 + 0.78 * wave)
                p.setBrush(bar)
                p.drawRoundedRect(QRectF(1 + index * 7, 5, 5, 14), 1.5, 1.5)
        p.setPen(self._ink)
        text_rect = QRectF(28, 0, self.width() - 56, 24)
        text = p.fontMetrics().elidedText(self._text, Qt.TextElideMode.ElideRight, int(text_rect.width()))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.end()


class _ButtonOverlay(QWidget):
    """Buton üzerinde yumuşak üzerine gelme ve basma dalgası çizen saydam katman."""

    def __init__(self, button: QWidget):
        super().__init__(button)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._hover = 0.0
        self._ripple = 0.0
        self._origin = QPointF()
        self._hover_anim = QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.finished.connect(self._hide_if_idle)
        self._ripple_anim = QPropertyAnimation(self, b"ripple", self)
        self._ripple_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._ripple_anim.setStartValue(0.0)
        self._ripple_anim.setEndValue(1.0)
        self._ripple_anim.finished.connect(self._hide_if_idle)

    @pyqtProperty(float)
    def hover(self):
        return self._hover

    @hover.setter
    def hover(self, value):
        self._hover = value
        self.update()

    @pyqtProperty(float)
    def ripple(self):
        return self._ripple

    @ripple.setter
    def ripple(self, value):
        self._ripple = value
        self.update()

    def _sync_geometry(self):
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

    def _hide_if_idle(self):
        if self._hover <= 0.0 and self._ripple_anim.state() != QAbstractAnimation.State.Running:
            self.hide()

    def animate_hover(self, target: float, profile: dict):
        self._sync_geometry()
        self._hover_anim.stop()
        self._hover_anim.setDuration(profile["hover_ms"])
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def start_ripple(self, origin: QPointF, profile: dict):
        self._sync_geometry()
        self._origin = origin
        self._ripple_anim.stop()
        self._ripple_anim.setDuration(profile["ripple_ms"])
        self._ripple_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        tint = QColor(AuraMotion.tint)
        radius = MOTION_PROFILES[get_interface_style()]["radius"]
        rect = QRectF(self.rect())
        if self._hover > 0.0:
            tint.setAlphaF(0.08 * self._hover)
            painter.setBrush(tint)
            painter.drawRoundedRect(rect, radius, radius)
        if 0.0 < self._ripple < 1.0:
            tint.setAlphaF(0.20 * (1.0 - self._ripple))
            painter.setBrush(tint)
            reach = (self.width() ** 2 + self.height() ** 2) ** 0.5 * self._ripple
            painter.setClipRect(rect)
            painter.drawEllipse(self._origin, reach, reach)
        painter.end()


class AuraMotion(QObject):
    """Tüm arayüz stillerinde ortak çalışan, ayarlardan kapatılabilen hareket katmanı."""

    enabled = True
    tint = "#ffffff"
    busy_pulse = None  # Ana iş parçacığı meşgulken olay akışından beslenen ilerleme göstergesi
    _instance = None
    _WATCHED = {
        QEvent.Type.Show, QEvent.Type.Enter, QEvent.Type.Leave,
        QEvent.Type.MouseButtonPress, QEvent.Type.Polish,
    }

    @classmethod
    def install(cls, app: QApplication):
        if cls._instance is None:
            cls.enabled = QSettings("AuraPDF", "PDFViewer").value("ui_animations", True, type=bool)
            cls._instance = cls(app)
            app.installEventFilter(cls._instance)
            install_dialog_release()
            # Python kapanırken Qt olaylarının bu süzgece ulaşması bellek hatasına yol açar.
            app.aboutToQuit.connect(lambda: app.removeEventFilter(cls._instance))

    @staticmethod
    def _profile() -> dict:
        return MOTION_PROFILES[get_interface_style()]

    def eventFilter(self, obj, event):
        if AuraMotion.busy_pulse:
            AuraMotion.busy_pulse()
        if event.type() == QEvent.Type.Show and isinstance(obj, QMessageBox):
            self._localize_message_box(obj)
        if not AuraMotion.enabled or event.type() not in self._WATCHED:
            return False
        try:
            kind = event.type()
            if kind == QEvent.Type.Show:
                if not event.spontaneous() and isinstance(obj, QWidget) and obj.isWindow()                         and not isinstance(obj, AuraBusyIndicator):
                    self._animate_window(obj)
            elif isinstance(obj, (QPushButton, QToolButton)):
                self._animate_button(obj, event)
            elif kind == QEvent.Type.Polish and isinstance(obj, QStackedWidget):
                obj.currentChanged.connect(lambda index, stack=obj: self._animate_page(stack, index))
        except RuntimeError:
            pass
        return False

    @staticmethod
    def _localize_message_box(box: QMessageBox):
        """Hazır mesaj kutusu düğmelerini uygulama diliyle yazar."""
        labels = {
            QMessageBox.StandardButton.Save: "msg_btn_save", QMessageBox.StandardButton.Discard: "msg_btn_discard",
            QMessageBox.StandardButton.Cancel: "msg_btn_cancel", QMessageBox.StandardButton.Yes: "msg_btn_yes",
            QMessageBox.StandardButton.No: "msg_btn_no", QMessageBox.StandardButton.Ok: "msg_btn_ok",
            QMessageBox.StandardButton.Close: "msg_btn_close",
        }
        for kind, key in labels.items():
            button = box.button(kind)
            if button is not None:
                button.setText(LanguageManager.tr(key))

    def _animate_window(self, window: QWidget):
        is_popup = window.windowType() == Qt.WindowType.Popup or isinstance(window, QMenu)
        if not is_popup and not isinstance(window, QDialog):
            return
        profile = self._profile()
        group = QParallelAnimationGroup(window)
        fade = QPropertyAnimation(window, b"windowOpacity", group)
        fade.setDuration(profile["open_ms"])
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(fade)
        window.setWindowOpacity(0.0)
        if not is_popup and profile["lift"]:
            end = window.pos()
            slide = QPropertyAnimation(window, b"pos", group)
            slide.setDuration(profile["open_ms"])
            slide.setStartValue(end + QPoint(0, profile["lift"]))
            slide.setEndValue(end)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(slide)
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _animate_button(self, button: QWidget, event):
        kind = event.type()
        if kind not in (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.MouseButtonPress):
            return
        if not button.isEnabled():
            return
        overlay = button.findChild(_ButtonOverlay, options=Qt.FindChildOption.FindDirectChildrenOnly)
        if overlay is None:
            if kind == QEvent.Type.Leave:
                return
            overlay = _ButtonOverlay(button)
        profile = self._profile()
        if kind == QEvent.Type.Enter:
            overlay.animate_hover(1.0, profile)
        elif kind == QEvent.Type.Leave:
            overlay.animate_hover(0.0, profile)
        else:
            overlay.start_ripple(event.position(), profile)

    def _animate_page(self, stack: QStackedWidget, index: int):
        page = stack.widget(index)
        # Belge görünümü pahalı olduğundan ve opaklık etkisini desteklemediğinden atlanır.
        if page is None or page.graphicsEffect() is not None or isinstance(page, QGraphicsView):
            return
        if page.findChild(QGraphicsView) is not None:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", effect)
        anim.setDuration(self._profile()["page_ms"])
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start()


def crossfade_window(window: QWidget):
    """Tema veya arayüz değişiminde eski görünümü yeni görünüm üzerinde eritir."""
    if not AuraMotion.enabled or not window.isVisible():
        return
    snapshot = QLabel(window)
    snapshot.setPixmap(window.grab())
    snapshot.setGeometry(window.rect())
    snapshot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    effect = QGraphicsOpacityEffect(snapshot)
    snapshot.setGraphicsEffect(effect)
    snapshot.show()
    snapshot.raise_()
    anim = QPropertyAnimation(effect, b"opacity", snapshot)
    anim.setDuration(MOTION_PROFILES[get_interface_style()]["open_ms"] + 120)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    anim.finished.connect(snapshot.deleteLater)
    anim.start()
