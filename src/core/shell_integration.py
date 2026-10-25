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


def get_bundled_file_path(filename: str) -> str | None:
    """Paketlenmiş veya proje dizinindeki belirtilen dosyanın yolunu bulur."""
    candidates = []

    # 1. PyInstaller MEIPASS
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "assets", filename))
        candidates.append(os.path.join(sys._MEIPASS, filename))

    # 2. Çalıştırılabilir dosya yanı
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    candidates.append(os.path.join(exe_dir, filename))
    candidates.append(os.path.join(exe_dir, "assets", filename))

    # 3. Proje kaynak dizini (Development)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(os.path.join(project_root, "assets", filename))
    candidates.append(os.path.join(project_root, filename))
    candidates.append(os.path.join(project_root, "dist", "AuraPDF", filename))
    candidates.append(os.path.join(project_root, "dist", "AuraPDF", "_internal", "assets", filename))

    # 4. Program Files kurulumu
    candidates.append(os.path.join(r"C:\Program Files\AuraPDF", filename))
    candidates.append(os.path.join(r"C:\Program Files\AuraPDF\assets", filename))

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)

    return None


def ensure_pdf_shell_integration(force: bool = False) -> bool:
    """
    Windows Dosya Gezgini için PDF önizleme (Thumbnail Provider) ve
    sağ-alt AuraPDF logo rozeti (ShowTypeOverlay) ayarlarını doğrular ve etkinleştirir.
    Geliştirme ortamında (main.py doğrudan çalıştırıldığında) sisteme müdahale etmez;
    yalnızca derlenmiş/kurulu sürümde (sys.frozen) veya force=True durumunda çalışır.
    """
    if sys.platform != "win32":
        return False

    if not force and not getattr(sys, "frozen", False):
        return False

    try:
        import winreg
        import ctypes

        # 1. Hedef klasörü belirle (Kullanıcı AppData klasörü - Yönetici yetkisi gerektirmez)
        local_appdata = os.path.expandvars(r"%LOCALAPPDATA%\AuraPDF")
        os.makedirs(local_appdata, exist_ok=True)

        target_dll = os.path.join(local_appdata, "PdfThumbnailProvider.dll")
        target_exe = os.path.join(local_appdata, "PowerToys.PdfThumbnailProvider.exe")
        target_ico = os.path.join(local_appdata, "app_icon.ico")

        # Gerekli dosyaları senkronize et (DLL, Thumbnail Helper EXE ve Uygulama İkonu)
        files_to_sync = [
            ("PdfThumbnailProvider.dll", target_dll),
            ("PowerToys.PdfThumbnailProvider.exe", target_exe),
            ("app_icon.ico", target_ico),
        ]

        for fname, dst in files_to_sync:
            src = get_bundled_file_path(fname)
            if src and (not os.path.isfile(dst) or os.path.getsize(src) != os.path.getsize(dst)):
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass

        active_dll = target_dll if os.path.isfile(target_dll) else get_bundled_file_path("PdfThumbnailProvider.dll")
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
        set_reg_dword(winreg.HKEY_CURRENT_USER, clsid_path, "DisableProcessIsolation", 1)
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

        # 4. AuraPDF DefaultIcon (Önizleme sağ-alt logosunun AuraPDF logosu olması için)
        active_ico = target_ico if os.path.isfile(target_ico) else get_bundled_file_path("app_icon.ico")
        if active_ico and os.path.isfile(active_ico):
            set_reg_val(
                winreg.HKEY_CURRENT_USER,
                r"Software\Classes\AuraPDF.AssocFile.PDF\DefaultIcon",
                "",
                f"{active_ico},0",
            )

        # 5. Windows Gezgini Sağ-Alt Logo Rozetini (Type Overlay) Etkinleştir
        # ShowTypeOverlay = 1: Küçük resmin sağ alt köşesinde uygulama simgesini gösterir
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "ShowTypeOverlay",
            1,
        )

        # 6. Değişiklik varsa Shell bildirimini gönder
        if changed:
            try:
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
            except Exception:
                pass

        return True

    except Exception:
        return False


def remove_pdf_shell_integration() -> bool:
    """
    Windows Dosya Gezgini için eklenmiş olan PDF Thumbnail Provider ve
    AuraPDF ShellEx ilişkilendirmelerini temizler.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        import ctypes

        def delete_reg_tree(root, subkey):
            try:
                with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as k:
                    while True:
                        try:
                            child = winreg.EnumKey(k, 0)
                            delete_reg_tree(root, f"{subkey}\\{child}")
                        except OSError:
                            break
                winreg.DeleteKey(root, subkey)
                return True
            except FileNotFoundError:
                return True
            except Exception:
                return False

        # 1. COM CLSID Kaydını temizle
        clsid_path = f"Software\\Classes\\CLSID\\{THUMBNAIL_PROVIDER_CLSID}"
        delete_reg_tree(winreg.HKEY_CURRENT_USER, clsid_path)

        # 2. AuraPDF ProgID kaydını temizle
        delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\AuraPDF.AssocFile.PDF")

        # 3. .pdf ve SystemFileAssociations altındaki ShellEx Thumbnail Handler kayıtlarını temizle
        for assoc_base in [
            r"Software\Classes\.pdf",
            r"Software\Classes\SystemFileAssociations\.pdf",
        ]:
            thumb_key = f"{assoc_base}\\ShellEx\\{IID_ITHUMBNAIL_PROVIDER}"
            delete_reg_tree(winreg.HKEY_CURRENT_USER, thumb_key)
            # Eğer ShellEx altı boş kaldıysa ShellEx anahtarını da temizle
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{assoc_base}\\ShellEx")
            except Exception:
                pass

        # 4. Local AppData altındaki DLL ve kopyalanmış araçları temizle
        try:
            local_appdata = os.path.expandvars(r"%LOCALAPPDATA%\AuraPDF")
            for fname in ["PdfThumbnailProvider.dll", "PowerToys.PdfThumbnailProvider.exe", "app_icon.ico"]:
                fpath = os.path.join(local_appdata, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
        except Exception:
            pass

        # 5. Shell değişikliğini Windows Gezgini'ne bildir
        try:
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
        except Exception:
            pass

        return True

    except Exception:
        return False

