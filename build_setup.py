import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

def build():
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
    os.makedirs(KURULUM_DIR, exist_ok=True)

    iscc_cmd = [iscc_path, ISS_SCRIPT]
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

    setup_src = os.path.join(KURULUM_DIR, "AuraPDF_Setup.exe")
    if not os.path.isfile(setup_src):
        print(f"[HATA] Beklenen setup bulunamadi: {setup_src}")
        sys.exit(1)

    target_desktop = os.path.join(DESKTOP_DIR, "AuraPDF_Setup.exe")
    try:
        if os.path.isdir(DESKTOP_DIR):
            shutil.copyfile(setup_src, target_desktop)
            print(f"Masaustune de kopyalandi: {target_desktop}")
    except Exception as e:
        print("Desktop kopyalama uyarisi:", e)

    size_mb = os.path.getsize(setup_src) / (1024 * 1024)
    print("\n" + "=" * 60)
    print(f"[BASARILI] AuraPDF_Setup.exe basariyla olusturuldu! ({size_mb:.2f} MB)")
    print(f"Hedef Kurulum Dosyasi: {setup_src}")
    print("=" * 60)

if __name__ == "__main__":
    build()
