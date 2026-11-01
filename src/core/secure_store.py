"""
AuraPDF - API anahtarı gibi gizli değerleri kullanıcı hesabına bağlı olarak saklar.

Windows'ta DPAPI (CryptProtectData) kullanılır: şifreli değer yalnızca aynı
Windows kullanıcı hesabında çözülebilir. Kayıt defterinde düz metin tutulmaz.
Diğer platformlarda (veya DPAPI kullanılamazsa) değer olduğu gibi saklanır.

Saklama biçimi:  "dpapi:<base64>"  — önekli olmayan değerler eski sürümlerden
kalan düz metin kabul edilir ve okunduğunda otomatik olarak şifrelenir.
"""

import base64
import sys

_PREFIX = "dpapi:"


def _dpapi(data: bytes, encrypt: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    CRYPTPROTECT_UI_FORBIDDEN = 0x01
    if encrypt:
        ok = crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None,
                                      CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None,
                                        CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not ok:
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def protect(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if sys.platform != "win32":
        return value
    try:
        enc = _dpapi(value.encode("utf-8"), True)
        return _PREFIX + base64.b64encode(enc).decode("ascii")
    except Exception:
        return value


def unprotect(stored: str) -> str:
    stored = (stored or "").strip()
    if not stored.startswith(_PREFIX):
        return stored
    if sys.platform != "win32":
        return ""
    try:
        raw = base64.b64decode(stored[len(_PREFIX):])
        return _dpapi(raw, False).decode("utf-8")
    except Exception:
        return ""


def is_protected(stored: str) -> bool:
    return (stored or "").startswith(_PREFIX)


def read_secret(settings, key: str) -> str:
    """QSettings'ten gizli değeri okur; eski düz metin değeri bulursa şifreleyip geri yazar."""
    try:
        stored = str(settings.value(key, "", type=str) or "")
    except Exception:
        stored = ""
    if stored and not is_protected(stored) and sys.platform == "win32":
        try:
            settings.setValue(key, protect(stored))
        except Exception:
            pass
        return stored.strip()
    return unprotect(stored)


def write_secret(settings, key: str, value: str) -> None:
    settings.setValue(key, protect(value))
