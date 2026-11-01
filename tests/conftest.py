"""
AuraPDF - pytest ortak ayarları
===============================
Testler kullanıcının gerçek AuraPDF ayarlarını (kayıt defteri) okumasın veya değiştirmesin diye
QSettings, uygulama modülleri içe aktarılmadan önce geçici bir INI dosyasına yönlendirilir.
"""

import os
import tempfile

import PyQt6.QtCore as QtCore

_APP_KEYS = ("AuraPDF", "PDFViewer")
_INI = os.path.join(tempfile.mkdtemp(prefix="aurapdf_test_settings_"), "settings.ini")
_RealQSettings = QtCore.QSettings


class IsolatedQSettings(_RealQSettings):
    """AuraPDF/PDFViewer ayarlarını geçici INI'ye yönlendirir; diğer kullanımlara dokunmaz."""

    def __init__(self, *args, **kwargs):
        if tuple(args[:2]) == _APP_KEYS:
            super().__init__(_INI, _RealQSettings.Format.IniFormat)
        else:
            super().__init__(*args, **kwargs)


QtCore.QSettings = IsolatedQSettings
