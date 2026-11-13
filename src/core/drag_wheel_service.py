"""
AuraPDF - Sistem Geneli Sürükle-Bırak Tekerleği (Sistem Tepsisi Yardımcısı)
==========================================================================
AuraPDF kapalıyken bile çalışır: `AuraPDF.exe --tray` ile başlatılan bu küçük
yardımcı sistem tepsisinde durur. Masaüstünde veya Dosya Gezgini'nde bir dosya
Ctrl + Alt basılıyken sürüklenmeye başlandığında imlecin altında eylem tekerleği
açılır. Sürüklenen dosya PDF ise tekerlek görünür; kullanıcı dosyayı
Birleştir / Böl / Word / PowerPoint / Excel dilimlerinden birine bırakır ve
AuraPDF ilgili eylemle (gerekirse kendiliğinden açılarak) devam eder.

Sistem kancası (hook) kullanılmaz: yalnızca tuş ve fare düğmesi durumu hafif bir
zamanlayıcıyla yoklanır; bu hem antivirüs uyarılarını hem de girdi gecikmesini önler.
"""

import os
import subprocess
import sys
from typing import List, Optional

from PyQt6.QtCore import QObject, QPoint, QSettings, QTimer
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from src.core.drag_wheel_config import load_config
from src.core.i18n import LanguageManager

TRAY_MUTEX_NAME = "Local" + chr(92) + "AuraPDF_DragWheel_Tray_Mutex"
AUTOSTART_VALUE = "AuraPDFDragWheel"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Tekerleğin tetiklenebileceği pencere sınıfları: Gezgin, masaüstü
_ALLOWED_WINDOW_CLASSES = ("CabinetWClass", "Progman", "WorkerW", "ExploreWClass")
_DRAG_START_PX = 8

# Windows süreç oluşturma bayrakları (subprocess modülünde yalnızca Windows'ta bulunur)
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200

_VK_LBUTTON = 0x01
_VK_CONTROL = 0x11
_VK_MENU = 0x12
_VK_SHIFT = 0x10
_VK_MBUTTON = 0x04


class DragTracker:
    """Sol düğmeyle sürükleme + tetikleyici (tuş kombinasyonu veya orta düğme) durum makinesi.

    Tetikleyici sürükleme başladıktan sonra da basılabilir; pencere sınıfı yalnızca düğmeye
    basıldığı anda denetlenir (test edilebilir, saf mantık)."""

    def __init__(self, threshold: int = _DRAG_START_PX):
        self.threshold = threshold
        self.start: Optional[tuple] = None
        self.armed_pos_ok = False
        self.shown = False

    def update(self, trigger_active: bool, left: bool, pos: tuple, allowed_window: bool) -> str:
        """Döner: 'show' (tekerleği aç), 'hide' (kapat) veya '' (işlem yok)."""
        if not left:
            was_shown = self.shown
            self.start = None
            self.armed_pos_ok = False
            self.shown = False
            return "hide" if was_shown else ""
        if self.start is None:
            # Düğmeye yeni basıldı: yalnızca Gezgin/masaüstü üzerindeyse izle
            self.start = pos
            self.armed_pos_ok = allowed_window
            return ""
        if self.shown or not self.armed_pos_ok or not trigger_active:
            return ""
        dx = pos[0] - self.start[0]
        dy = pos[1] - self.start[1]
        if (dx * dx + dy * dy) ** 0.5 >= self.threshold:
            self.shown = True
            return "show"
        return ""


def trigger_active(trigger: str) -> bool:
    """Ayarlı tetikleyici şu an basılı mı?"""
    if trigger == "middle":
        return _key_down(_VK_MBUTTON)
    ctrl = _key_down(_VK_CONTROL)
    if trigger == "ctrl_shift":
        return ctrl and _key_down(_VK_SHIFT)
    return ctrl and _key_down(_VK_MENU)


def _key_down(vk: int) -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def _cursor_root_window_class() -> str:
    """İmlecin altındaki üst düzey pencerenin sınıf adını döner (fiziksel piksel koordinatı)."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        hwnd = user32.WindowFromPoint(pt)
        if not hwnd:
            return ""
        root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
        buf = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(root or hwnd, buf, 128)
        return buf.value
    except Exception:
        return ""


def app_launch_command() -> List[str]:
    """AuraPDF'i başlatan komut: kurulu sürümde exe, geliştirmede python + main.py."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "main.py")
    return [sys.executable, main_py]


MAIN_SERVER_NAME = "AuraPDF_SingleInstance_App_Server"  # main.py ile aynı olmalı


def allow_foreground(pid: Optional[int] = None) -> None:
    """Bırakma girdisini alan süreç olarak, hedef sürecin pencereyi öne getirmesine izin verir.

    Aksi halde Windows arka plan süreçten başlayan uygulamanın penceresini göstermez
    (görev çubuğunda yanıp söner)."""
    try:
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF if pid is None else int(pid))
    except Exception:
        pass


def build_payload(action: str, paths: List[str]) -> str:
    """Çalışan AuraPDF örneğine gönderilen IPC iletisi (main.py ile uyumlu)."""
    lines = list(paths) if action == "open" else [f"__WHEEL__:{action}"] + list(paths)
    return chr(10).join(lines)


def send_to_running_app(action: str, paths: List[str]) -> bool:
    """Çalışan bir AuraPDF örneği varsa eylemi ona iletir; yoksa False döner."""
    try:
        from PyQt6.QtNetwork import QLocalSocket
        sock = QLocalSocket()
        sock.connectToServer(MAIN_SERVER_NAME)
        if not sock.waitForConnected(120):
            return False
        allow_foreground(None)
        sock.write(build_payload(action, paths).encode("utf-8"))
        sock.flush()
        sock.waitForBytesWritten(1000)
        sock.disconnectFromServer()
        return True
    except Exception:
        return False


def spawn_app_with_action(action: str, paths: List[str]) -> "subprocess.Popen":
    """Tam uygulamayı (veya çalışan örneğini) seçilen eylemle yeni süreç olarak başlatır."""
    cmd = app_launch_command()
    if action == "open":
        cmd += list(paths)
    else:
        cmd += ["--wheel", action] + list(paths)
    flags = 0
    if os.name == "nt":
        flags = _DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(cmd, creationflags=flags, close_fds=True)
    allow_foreground(proc.pid)
    return proc


# ----------------------------------------------------------------------------- otomatik başlatma
def autostart_command() -> str:
    return " ".join(f'"{c}"' for c in app_launch_command()) + " --tray"


def is_autostart_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, AUTOSTART_VALUE)
            return True
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Windows ile birlikte başlatmayı HKCU altında açar/kapatır. Yalnızca kurulu sürümde etkilidir."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            if enabled:
                winreg.SetValueEx(k, AUTOSTART_VALUE, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, AUTOSTART_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


# ----------------------------------------------------------------------------- hizmet
class DragWheelService(QObject):
    """Tuş/fare durumunu yoklar ve bağımsız tekerlek penceresini yönetir."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from src.ui.drag_wheel import AuraDragWheelOverlay
        self._tracker = DragTracker()
        self._cfg = load_config()
        self._queue: List[tuple] = []
        self._child = None
        self._overlay = AuraDragWheelOverlay(None, on_choice=self._on_choice)
        self._timer = QTimer(self)
        self._timer.setInterval(35)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        # Ayarlardan kapatılırsa yardımcı kendiliğinden kapanır (arka planda kalıntı bırakmaz)
        self._setting_timer = QTimer(self)
        self._setting_timer.setInterval(1500)
        self._setting_timer.timeout.connect(self._check_setting)
        self._setting_timer.start()

    def _check_setting(self):
        """Ayarlar değişmişse (eylem listesi, tetikleyici, boyut) yeniden yükler; kapatılmışsa çıkar."""
        try:
            cfg = load_config()
        except Exception:
            return
        if not cfg["enabled"]:
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            return
        self._cfg = cfg

    def _poll(self):
        try:
            left = _key_down(_VK_LBUTTON)
            allowed = False
            if left and self._tracker.start is None:
                allowed = _cursor_root_window_class() in _ALLOWED_WINDOW_CLASSES
            pos = QCursor.pos()
            act = self._tracker.update(trigger_active(self._cfg["trigger"]) if left else False,
                                       left, (pos.x(), pos.y()), allowed)
            if act == "show":
                self._overlay.apply_config(self._cfg)
                self._overlay.present_at_cursor(QPoint(pos.x(), pos.y()))
            elif act == "hide":
                # Bırakma olayı önce işlenir; kısa gecikmeyle kalan örtüyü kapat
                QTimer.singleShot(250, self._hide_if_idle)
        except Exception:
            pass

    def _hide_if_idle(self):
        try:
            if self._overlay.isVisible() and not _key_down(_VK_LBUTTON):
                self._overlay.dismiss()
        except RuntimeError:
            pass

    def _on_choice(self, action: str, paths: List[str]):
        """Eylemi sıraya alır; çalışan örneğe iletir, yoksa tek bir yeni süreç başlatır.

        Uygulama henüz açılırken gelen ikinci bir eylem için yeni süreç başlatılmaz
        (yinelenen süreç/kalıntı önlenir); açılış bitene kadar iletmeyi yeniden dener."""
        self._queue.append((action, list(paths)))
        self._drain(0)

    def _drain(self, attempt: int):
        try:
            while self._queue:
                action, paths = self._queue[0]
                if send_to_running_app(action, paths):
                    self._queue.pop(0)
                    continue
                child_alive = self._child is not None and self._child.poll() is None
                if child_alive and attempt < 100:
                    # Açılmakta olan uygulama sunucusunu henüz dinlemiyor; biraz sonra tekrar dene
                    QTimer.singleShot(300, lambda a=attempt + 1: self._drain(a))
                    return
                self._queue.pop(0)
                self._child = spawn_app_with_action(action, paths)
                attempt = 0
        except Exception:
            self._queue.clear()

    def stop(self):
        try:
            self._timer.stop()
        except Exception:
            pass
        try:
            self._overlay.dismiss()
        except Exception:
            pass


def drag_wheel_enabled() -> bool:
    """Ayarlar > Genel'deki 'Sürükle-bırak eylem tekerleği' seçeneği (varsayılan açık)."""
    try:
        st = QSettings("AuraPDF", "PDFViewer")
        st.sync()
        return str(st.value("drag_wheel_enabled", True)).lower() not in ("false", "0")
    except Exception:
        return True


def apply_drag_wheel_setting(enabled: bool) -> None:
    """Ayar değiştiğinde çağrılır: otomatik başlatmayı günceller, açılıyorsa yardımcıyı başlatır.

    Kapatılırken çalışan yardımcı ayarı kendisi görüp çıkar (bkz. DragWheelService)."""
    set_autostart(enabled)
    if enabled:
        try:
            subprocess.Popen(app_launch_command() + ["--tray"], close_fds=True,
                             creationflags=_DETACHED_PROCESS if os.name == "nt" else 0)
        except Exception:
            pass


def helper_running(name: str = TRAY_MUTEX_NAME) -> bool:
    """Tepsi yardımcısı çalışıyor mu? (Tek örnek kilidi başka bir süreçte tutuluyorsa evet.)"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenMutexW.restype = ctypes.c_void_p
        handle = kernel32.OpenMutexW(0x00100000, False, name)  # SYNCHRONIZE
        if handle:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return True
        return kernel32.GetLastError() == 5  # erişim reddedildi: kilit var
    except Exception:
        return False


def ensure_helper_running() -> None:
    """Ayar açıksa ve yardımcı çalışmıyorsa başlatır.

    Kullanıcı yardımcıyı tepsiden kapatmış olsa bile AuraPDF her açıldığında tekerlek geri gelir."""
    try:
        if drag_wheel_enabled() and not helper_running():
            subprocess.Popen(app_launch_command() + ["--tray"], close_fds=True,
                             creationflags=_DETACHED_PROCESS if os.name == "nt" else 0)
    except Exception:
        pass


def _acquire_single_instance_mutex(name: str = TRAY_MUTEX_NAME):
    """Yardımcının tek örnek kilidini alır. Başka bir örnek varsa None döner."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, name)
        err = kernel32.GetLastError()
        if not handle or err in (183, 5):  # ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED
            return None
        return handle
    except Exception:
        return object()  # kilit alınamıyorsa yine de çalış


def run_tray_app(app) -> int:
    """`--tray` kipi: pencere açmadan tepside çalışır. Zaten çalışıyorsa hemen çıkar."""
    from PyQt6.QtWidgets import QApplication
    from src.ui.icons import AuraIconFactory

    if not drag_wheel_enabled():
        return 0  # kullanıcı özelliği ayarlardan kapatmış

    # Tek örnek: adlandırılmış mutex. Başka bir süreç (farklı yetkiyle de olsa) tutuyorsa çık.
    mutex = _acquire_single_instance_mutex()
    if mutex is None:
        return 0

    settings = QSettings("AuraPDF", "PDFViewer")
    LanguageManager.set_language(settings.value("language", "tr"))
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        return 0

    service = DragWheelService(app)
    tray = QSystemTrayIcon(AuraIconFactory.icon_app(), app)
    tray.setToolTip(LanguageManager.tr("tray_tooltip"))

    menu = QMenu()
    act_open = QAction(LanguageManager.tr("tray_open"), menu)
    def _open_app():
        if not send_to_running_app("open", []):
            subprocess.Popen(app_launch_command(), close_fds=True,
                             creationflags=_DETACHED_PROCESS if os.name == "nt" else 0)
    act_open.triggered.connect(_open_app)
    menu.addAction(act_open)

    act_auto = QAction(LanguageManager.tr("tray_autostart"), menu)
    act_auto.setCheckable(True)
    act_auto.setChecked(is_autostart_enabled())
    act_auto.setEnabled(bool(getattr(sys, "frozen", False)))
    act_auto.toggled.connect(lambda on: set_autostart(bool(on)))
    menu.addAction(act_auto)

    menu.addSeparator()
    act_quit = QAction(LanguageManager.tr("tray_quit"), menu)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.show()

    # Nesneleri uygulama ömrü boyunca canlı tut
    app._aura_tray_refs = (service, tray, menu, mutex)
    code = app.exec()
    service.stop()
    tray.hide()
    return code
