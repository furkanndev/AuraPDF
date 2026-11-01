"""
AuraPDF merkezi günlük (log) modülü.

Günlükler kullanıcının yazma izni olan bir klasöre yazılır:
  Windows : %LOCALAPPDATA%\\AuraPDF\\logs\\aurapdf.log
  Diğer   : ~/.local/state/AuraPDF/logs/aurapdf.log

Program Files altına kurulu sürümde uygulama klasörü yazılamaz; bu yüzden
günlükler asla uygulama klasörüne yazılmaz.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_LOGGER_NAME = "AuraPDF"


def get_log_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
        path = os.path.join(base, "AuraPDF", "logs")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
        path = os.path.join(base, "AuraPDF", "logs")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        import tempfile
        path = os.path.join(tempfile.gettempdir(), "AuraPDF", "logs")
        os.makedirs(path, exist_ok=True)
    return path


def get_log_path(name: str = "aurapdf.log") -> str:
    return os.path.join(get_log_dir(), name)


def _build_logger() -> logging.Logger:
    log = logging.getLogger(_LOGGER_NAME)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s")
    try:
        fh = RotatingFileHandler(get_log_path(), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        log.addHandler(logging.NullHandler())
    # Pencereli (PyInstaller --windowed) sürümde sys.stderr None olur
    if sys.stderr is not None:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        sh.setLevel(logging.WARNING)
        log.addHandler(sh)
    log.propagate = False
    return log


logger = _build_logger()

__all__ = ["logger", "get_log_dir", "get_log_path"]
