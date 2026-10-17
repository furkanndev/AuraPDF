"""
AuraPDF - Windows Shell Entegrasyonu (PDF Önizleme ve Küçük Resim Sağ-Alt Logo Rozeti)
========================================================================================
Windows Dosya Gezgini'nde (Explorer) PDF dosyalarının ilk sayfasının yüksek çözünürlüklü
küçük resim (thumbnail) olarak görüntülenmesini ve sağ alt köşesinde AuraPDF uygulama
logosunun (DefaultIcon rozeti) yer almasını sağlar.
"""

import os
import sys
import shutil

THUMBNAIL_PROVIDER_CLSID = "{D8BB9942-93BD-412D-87E4-33FAB214DC1A}"
IID_ITHUMBNAIL_PROVIDER = "{e357fccd-a995-4576-b01f-234630154e96}"


def get_bundled_provider_path() -> str | None:
    """Paketlenmiş veya proje dizinindeki PdfThumbnailProvider.dll yolunu bulur."""
    candidates = []

    # 1. PyInstaller MEIPASS
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "assets", "PdfThumbnailProvider.dll"))
        candidates.append(os.path.join(sys._MEIPASS, "PdfThumbnailProvider.dll"))

    # 2. Çalıştırılabilir dosya yanı
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    candidates.append(os.path.join(exe_dir, "PdfThumbnailProvider.dll"))
    candidates.append(os.path.join(exe_dir, "assets", "PdfThumbnailProvider.dll"))

    # 3. Proje kaynak dizini (Development)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(project_root, "assets", "PdfThumbnailProvider.dll"))
    candidates.append(os.path.join(project_root, "dist", "AuraPDF", "PdfThumbnailProvider.dll"))

    # 4. Program Files kurulumu
    candidates.append(r"C:\Program Files\AuraPDF\PdfThumbnailProvider.dll")

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)

    return None


def ensure_pdf_shell_integration() -> bool:
    """
    Windows Dosya Gezgini için PDF önizleme (Thumbnail Provider) ve
    sağ-alt AuraPDF logo rozeti (ShowTypeOverlay) ayarlarını doğrular ve etkinleştirir.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        import ctypes

        # 1. Hedef DLL konumunu belirle (Kullanıcı AppData klasörü - Yönetici yetkisi gerektirmez)
        local_appdata = os.path.expandvars(r"%LOCALAPPDATA%\AuraPDF")
        os.makedirs(local_appdata, exist_ok=True)
        target_dll = os.path.join(local_appdata, "PdfThumbnailProvider.dll")

        # Eğer hedef DLL yoksa veya güncellenmesi gerekiyorsa kopyala
        source_dll = get_bundled_provider_path()
        if source_dll and (not os.path.isfile(target_dll) or os.path.getsize(source_dll) != os.path.getsize(target_dll)):
            try:
                shutil.copy2(source_dll, target_dll)
            except Exception:
                pass

        active_dll = target_dll if os.path.isfile(target_dll) else source_dll
        if not active_dll or not os.path.isfile(active_dll):
            return False

        changed = False

        def set_reg_val(root, subkey, name, val):
            nonlocal changed
            try:
                with winreg.CreateKey(root, subkey) as k:
                    try:
                        current, _ = winreg.QueryValueEx(k, name)
                        if current == val:
                            return
                    except Exception:
                        pass
                    winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
                    changed = True
            except Exception:
                pass

        def set_reg_dword(root, subkey, name, val):
            nonlocal changed
            try:
                with winreg.CreateKey(root, subkey) as k:
                    try:
                        current, _ = winreg.QueryValueEx(k, name)
                        if current == val:
                            return
                    except Exception:
                        pass
                    winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)
                    changed = True
            except Exception:
                pass

        # 2. COM CLSID Kaydı (HKCU\Software\Classes\CLSID\{D8BB9942-93BD-412D-87E4-33FAB214DC1A})
        clsid_path = f"Software\\Classes\\CLSID\\{THUMBNAIL_PROVIDER_CLSID}"
        set_reg_val(winreg.HKEY_CURRENT_USER, clsid_path, "", "AuraPDF Thumbnail Provider")
        set_reg_val(winreg.HKEY_CURRENT_USER, clsid_path, "DisplayName", "AuraPDF Thumbnail Provider")
        set_reg_val(winreg.HKEY_CURRENT_USER, f"{clsid_path}\\InprocServer32", "", active_dll)
        set_reg_val(winreg.HKEY_CURRENT_USER, f"{clsid_path}\\InprocServer32", "ThreadingModel", "Apartment")

        # 3. ShellEx Thumbnail Handler İlişkilendirmesi
        # AuraPDF ProgID, .pdf uzantısı ve SystemFileAssociations
        for assoc_base in [
            r"Software\Classes\AuraPDF.AssocFile.PDF",
            r"Software\Classes\.pdf",
            r"Software\Classes\SystemFileAssociations\.pdf",
        ]:
            set_reg_val(
                winreg.HKEY_CURRENT_USER,
                f"{assoc_base}\\ShellEx\\{IID_ITHUMBNAIL_PROVIDER}",
                "",
                THUMBNAIL_PROVIDER_CLSID,
            )

        # 4. Windows Gezgini Sağ-Alt Logo Rozetini (Type Overlay) Etkinleştir
        # ShowTypeOverlay = 1: Küçük resmin sağ alt köşesinde uygulama simgesini gösterir
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "ShowTypeOverlay",
            1,
        )

        # 5. Değişiklik varsa Shell bildirimini gönder
        if changed:
            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
            except Exception:
                pass

        return True

    except Exception:
        return False
