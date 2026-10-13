import os
import sys
import subprocess
import shutil
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.core.updater import CURRENT_VERSION

DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
ICON_PATH = os.path.join(BASE_DIR, "app_icon.ico")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")
ISS_SCRIPT = os.path.join(BASE_DIR, "installer.iss")
KURULUM_DIR = os.path.join(BASE_DIR, "Kurulum")
DESKTOP_DIR = r"C:\Users\MRF4 ROG\Desktop"

ISCC_CANDIDATES = [
    r"C:\Users\MRF4 ROG\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    shutil.which("ISCC.exe") or ""
]

def find_iscc():
    for c in ISCC_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    return None

def get_current_git_branch() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                             cwd=BASE_DIR, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def get_setup_target_info() -> tuple[str, str, str]:
    """
    Aktif git branch'e ve CURRENT_VERSION'a göre hedef alt klasor (Basic / Pro),
    Inno Setup cikti dosya adi (OutputFileName) ve surumunu belirler.
    - Pro branch'inda ise: Kurulum/Pro/AuraPDF_Pro v<surum>.exe
    - Basic branch'inda ise: Kurulum/Basic/AuraPDF_Basic v<surum>.exe
    """
    branch = get_current_git_branch().lower()
    raw_ver = str(CURRENT_VERSION).strip()

    # Surum numarasini yakala (orn: '2.2', '1.1')
    digits = re.findall(r'\d+(?:\.\d+)*', raw_ver)
    ver_num = digits[0] if digits else "2.2"
    formatted_ver = f"v{ver_num}" if not ver_num.startswith("v") else ver_num

    if "basic" in branch or "basic" in raw_ver.lower():
        sub_folder = "Basic"
        output_filename = f"AuraPDF_Basic {formatted_ver}"
        version_str = f"Basic {formatted_ver}"
    else:
        # Varsayilan veya Pro
        sub_folder = "Pro"
        output_filename = f"AuraPDF_Pro {formatted_ver}"
        version_str = f"Pro {formatted_ver}"

    return sub_folder, output_filename, version_str

def build(skip_pyinstaller: bool = False):
    branch_name = get_current_git_branch()
    sub_folder, output_filename, version_str = get_setup_target_info()
    target_kurulum_dir = os.path.join(KURULUM_DIR, sub_folder)

    print(f"Aktif Git Dali: {branch_name or 'Bilinmiyor'}")
    print(f"Hedef Kurulum Klasoru: {target_kurulum_dir}")
    print(f"Hedef Kurulum Paketi: {output_filename}.exe")

    exe_path = os.path.join(DIST_DIR, "AuraPDF", "AuraPDF.exe")
    if not skip_pyinstaller or not os.path.isfile(exe_path):
        print("=" * 60)
        print("1. PyInstaller ile AuraPDF.exe derleniyor...")
        print("=" * 60)

        pyinstaller_cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", "AuraPDF",
            "--onedir",
            "--windowed",
            "--noconfirm",
            "--clean",
            f"--icon={ICON_PATH}",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            f"--add-data={os.path.join(BASE_DIR, 'src')};src",
            f"--add-data={os.path.join(BASE_DIR, 'assets')};assets",
            f"--add-data={ICON_PATH};.",
            "--collect-all", "pdf2docx",
            "--collect-all", "docx",
            "--collect-all", "pymupdf",
            "--collect-all", "pptx",
            "--collect-all", "openpyxl",
            "--collect-all", "rapidocr_onnxruntime",
            "--collect-all", "onnxruntime",
            "--hidden-import", "PyQt6",
            "--hidden-import", "PyQt6.QtCore",
            "--hidden-import", "PyQt6.QtGui",
            "--hidden-import", "PyQt6.QtWidgets",
            "--hidden-import", "PyQt6.QtNetwork",
            "--hidden-import", "PyQt6.QtPrintSupport",
            "--hidden-import", "PyQt6.QtMultimedia",
            "--hidden-import", "PyQt6.QtMultimediaWidgets",
            "--hidden-import", "pdf2docx",
            "--hidden-import", "docx",
            "--hidden-import", "pptx",
            "--hidden-import", "openpyxl",
            "--hidden-import", "fitz",
            "--hidden-import", "rapidocr_onnxruntime",
            "--hidden-import", "onnxruntime",
            MAIN_SCRIPT
        ]

        print("Komut:", " ".join(pyinstaller_cmd))
        res = subprocess.run(pyinstaller_cmd, cwd=BASE_DIR)
        if res.returncode != 0:
            print("[HATA] PyInstaller derlemesi basarisiz oldu!")
            sys.exit(res.returncode)
    else:
        print("=" * 60)
        print("1. Mevcut AuraPDF.exe kullaniliyor (PyInstaller derlemesi atlandi)...")
        print("=" * 60)

    exe_path = os.path.join(DIST_DIR, "AuraPDF", "AuraPDF.exe")
    if not os.path.isfile(exe_path):
        print(f"[HATA] Beklenen exe bulunamadi: {exe_path}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("2. Inno Setup ile Setup.exe olusturuluyor...")
    print("=" * 60)

    iscc_path = find_iscc()
    if not iscc_path:
        print("[HATA] Inno Setup derleyicisi (ISCC.exe) bulunamadi!")
        sys.exit(1)

    print(f"ISCC Yolu: {iscc_path}")
    os.makedirs(target_kurulum_dir, exist_ok=True)

    iscc_cmd = [
        iscc_path,
        f"/DMyAppVersion={version_str}",
        f"/DOutputFileName={output_filename}",
        f"/DOutputDir={target_kurulum_dir}",
        f"/DMyAppIcon={ICON_PATH}",
        ISS_SCRIPT
    ]
    print("Komut:", " ".join(iscc_cmd))
    success = False
    import time
    for attempt in range(1, 4):
        res = subprocess.run(iscc_cmd, cwd=BASE_DIR)
        if res.returncode == 0:
            success = True
            break
        print(f"[UYARI] Inno Setup derlemesi basarisiz oldu (Deneme {attempt}/3), 2 saniye sonra tekrar deneniyor...")
        time.sleep(2)
    if not success:
        print("[HATA] Inno Setup derlemesi tum denemelere ragmen basarisiz oldu!")
        sys.exit(1)

    setup_filename = f"{output_filename}.exe"
    setup_src = os.path.join(target_kurulum_dir, setup_filename)
    if not os.path.isfile(setup_src):
        alt_root_setup = os.path.join(KURULUM_DIR, setup_filename)
        if os.path.isfile(alt_root_setup):
            shutil.move(alt_root_setup, setup_src)
        else:
            print(f"[HATA] Beklenen setup bulunamadi: {setup_src}")
            sys.exit(1)

    target_desktop = os.path.join(DESKTOP_DIR, os.path.basename(setup_src))
    try:
        if os.path.isdir(DESKTOP_DIR):
            shutil.copyfile(setup_src, target_desktop)
            print(f"Masaustune de kopyalandi: {target_desktop}")
            try:
                import ctypes
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
            except Exception:
                pass
    except Exception as e:
        print("Desktop kopyalama uyarisi:", e)

    size_mb = os.path.getsize(setup_src) / (1024 * 1024)
    print("\n" + "=" * 60)
    print(f"[BASARILI] {os.path.basename(setup_src)} basariyla olusturuldu! ({size_mb:.2f} MB)")
    print(f"Hedef Kurulum Dosyasi: {setup_src}")
    print("=" * 60)

if __name__ == "__main__":
    skip_py = "--iss-only" in sys.argv or "--no-pyinstaller" in sys.argv
    build(skip_pyinstaller=skip_py)
