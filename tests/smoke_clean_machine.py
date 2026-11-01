"""
AuraPDF - "Temiz Makine" Duman Testi (Clean-Machine Smoke Test)
===============================================================

Uygulamayi HIC ayari olmayan yeni bir bilgisayardaymis gibi baslatir ve temel
akislari otomatik olarak dener. Gercek kullanici ayarlarina (Windows kayit
defteri HKCU\\Software\\AuraPDF) DOKUNMAZ: tum QSettings cagrilari gecici bir
INI dosyasina yonlendirilir.

Kontrol edilenler:
  * Bos ayarlarla ilk acilis (ilk kurulum senaryosu)
  * Turkce karakter + bosluk iceren klasor yolundaki PDF'i acma
  * 8 tema x 2 dil gecisi
  * Tum arac diyaloglarinin acilip kapanabilmesi (otomatik kapatici ile)
  * Kaydetme -> diskten yeniden okuma, sayfa sayisi ve meta veri kontrolu
  * Pencere yeniden boyutlandirma ve sekme kapatma (arka plan render thread'i ile yaris)
  * Slot icinde yakalanmayan istisnalar (PyQt6'da normalde uygulamayi oldurur)

Calistirma (proje kok dizininde):
    python tests/smoke_clean_machine.py            # pencere gorunur
    set QT_QPA_PLATFORM=offscreen && python tests/smoke_clean_machine.py   # gorunmez

Sonuc: konsolda PASS/FAIL tablosu + tests/smoke_report.json
"""

import json
import os
import shutil
import sys
import tempfile
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

WORK = tempfile.mkdtemp(prefix="aurapdf_smoke_")
SETTINGS_DIR = os.path.join(WORK, "settings")
DOC_DIR = os.path.join(WORK, "Test Klasörü ğüşıöç")
os.makedirs(SETTINGS_DIR, exist_ok=True)
os.makedirs(DOC_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# 1. QSettings izolasyonu: uygulama import edilmeden ONCE yapilmali
# --------------------------------------------------------------------------
import PyQt6.QtCore as _QtCore  # noqa: E402

_RealQSettings = _QtCore.QSettings


class _IsolatedQSettings(_RealQSettings):
    def __init__(self, *args, **kwargs):
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
            ini = os.path.join(SETTINGS_DIR, f"{args[0]}_{args[1]}.ini")
            super().__init__(ini, _RealQSettings.Format.IniFormat)
        elif len(args) == 1 and isinstance(args[0], str):
            ini = os.path.join(SETTINGS_DIR, f"{args[0]}.ini")
            super().__init__(ini, _RealQSettings.Format.IniFormat)
        else:
            super().__init__(*args, **kwargs)


_QtCore.QSettings = _IsolatedQSettings

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QDialog, QFileDialog, QInputDialog, QMessageBox,
)

import fitz  # noqa: E402

# --------------------------------------------------------------------------
# 2. Yakalanmayan istisnalari topla (PyQt6 varsayilani: abort)
# --------------------------------------------------------------------------
UNCAUGHT = []


def _hook(exc_type, exc, tb):
    UNCAUGHT.append("".join(traceback.format_exception(exc_type, exc, tb)))


sys.excepthook = _hook

# --------------------------------------------------------------------------
# 3. Engelleyici diyaloglari etkisizlestir
# --------------------------------------------------------------------------
_SB = QMessageBox.StandardButton
QMessageBox.question = staticmethod(lambda *a, **k: _SB.No)
QMessageBox.warning = staticmethod(lambda *a, **k: _SB.Ok)
QMessageBox.information = staticmethod(lambda *a, **k: _SB.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: _SB.Ok)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))

app = QApplication.instance() or QApplication(sys.argv)

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append({"step": name, "ok": bool(ok), "detail": str(detail)[:2000]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {str(detail)[:200]}" if detail and not ok else ""))


def pump(ms=150):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def step(name):
    def deco(fn):
        def run(*a, **k):
            before = len(UNCAUGHT)
            try:
                fn(*a, **k)
                pump(120)
                new = UNCAUGHT[before:]
                record(name, not new, new[-1] if new else "")
            except Exception:
                record(name, False, traceback.format_exc())
        return run
    return deco


# Acik kalan modal diyaloglari otomatik kapat
def _auto_close():
    w = QApplication.activeModalWidget()
    if w is not None:
        try:
            if isinstance(w, QDialog):
                w.reject()
            else:
                w.close()
        except Exception:
            pass


closer = QTimer()
closer.timeout.connect(_auto_close)
closer.start(300)


def make_sample_pdf(path):
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"AuraPDF smoke test - sayfa {i + 1}", fontsize=18)
        page.insert_text((72, 110), "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", fontsize=11)
    doc.set_metadata({"author": "Orijinal Yazar", "title": "Smoke Test"})
    doc.save(path)
    doc.close()


def main():
    sample = os.path.join(DOC_DIR, "örnek belge (1).pdf")
    make_sample_pdf(sample)

    from src.core.i18n import LanguageManager
    from src.viewer import AuraPDFViewer
    from src.document.tab_document import PDFTabDocument

    ctx = {}

    @step("Ilk acilis (bos ayarlar)")
    def s_start():
        v = AuraPDFViewer()
        v.resize(1280, 800)
        v.show()
        ctx["v"] = v

    s_start()
    v = ctx.get("v")
    if v is None:
        return finish()

    @step("Turkce karakterli yoldan PDF acma")
    def s_open():
        v.add_pdf_tab(sample)
        pump(800)
        td = v.get_current_tab_doc()
        assert isinstance(td, PDFTabDocument), "sekme olusmadi"
        assert td.doc is not None and len(td.doc) == 3, f"sayfa sayisi: {None if td.doc is None else len(td.doc)}"

    s_open()

    themes = ["dark", "gray", "emerald", "purple", "crimson", "nord", "vice_city", "apple"]
    for lang in ("en", "tr"):
        for th in themes:
            @step(f"Tema/dil: {th}/{lang}")
            def s_theme(th=th, lang=lang):
                v.change_language(lang)
                v.apply_theme(th)

            s_theme()

    dialogs = [
        "open_settings_dialog", "open_document_properties_dialog", "open_compress_dialog",
        "open_shortcuts_dialog", "open_pdf_compare_dialog", "open_pdf_redaction_dialog",
        "open_pdf_ocr_dialog", "open_pdf_content_editor_dialog", "open_signature_dialog",
        "open_organize_dialog", "open_merge_dialog", "open_split_dialog", "open_page_number_dialog",
        "open_watermark_dialog", "open_background_dialog", "open_encrypt_dialog",
        "open_recovery_dialog", "open_word_dialog", "open_pptx_dialog", "open_excel_dialog",
        "open_stamp_dialog", "open_date_stamp_dialog", "open_initials_dialog",
        "open_ai_assistant_dialog",
    ]
    for name in dialogs:
        @step(f"Diyalog: {name}")
        def s_dlg(name=name):
            fn = getattr(v, name, None)
            assert fn is not None, "metot yok"
            fn()

        s_dlg()

    for fmt in ("epub", "mobi"):
        @step(f"Diyalog: open_ebook_dialog({fmt})")
        def s_ebook(fmt=fmt):
            v.open_ebook_dialog(fmt)

        s_ebook()

    @step("Pencere yeniden boyutlandirma")
    def s_resize():
        for w, h in ((900, 600), (1600, 1000), (1280, 800)):
            v.resize(w, h)
            pump(200)

    s_resize()

    @step("Kaydet + diskten dogrula")
    def s_save():
        td = v.get_current_tab_doc()
        td.set_modified(True)
        v.save_pdf()
        pump(300)
        d = fitz.open(sample)
        try:
            assert len(d) == 3, f"kayit sonrasi sayfa sayisi {len(d)}"
            author = (d.metadata or {}).get("author", "")
        finally:
            d.close()
        ctx["author_after_save"] = author
        assert not os.path.exists(sample + ".tmp_save"), ".tmp_save dosyasi geride kaldi"

    s_save()

    author = ctx.get("author_after_save")
    if author is not None:
        record(
            "Meta veri: kayit orijinal yazari korudu",
            author == "Orijinal Yazar",
            f"Kayittan sonra Author = {author!r} (orijinal: 'Orijinal Yazar')",
        )

    @step("Sesli okuma motoru (EMA yoksa sistem TTS yedegi)")
    def s_tts():
        from src.core.speech_engine import AuraSpeechEngine, HAS_SYSTEM_TTS, is_ema_installed
        eng = AuraSpeechEngine()
        ready = eng.is_model_ready()
        ctx["tts"] = f"EMA={is_ema_installed()} SystemTTS={HAS_SYSTEM_TTS} ready={ready}"
        assert ready, "Hicbir konusma motoru hazir degil: " + ctx["tts"]
        eng.stop()

    s_tts()

    @step("Gunluk klasoru yazilabilir")
    def s_logs():
        from src.core.logger import get_log_dir, logger
        logger.info("smoke test")
        d = get_log_dir()
        assert os.path.isdir(d) and os.access(d, os.W_OK), d

    s_logs()

    @step("Hizli sekme ac/kapat (render thread yarisi)")
    def s_race():
        for _ in range(5):
            v.add_pdf_tab(sample)
            pump(40)
            td = v.get_current_tab_doc()
            if td is not None:
                td.set_modified(False)
            v.close_tab(v.tab_widget.currentIndex())
            pump(40)

    s_race()

    @step("Tum sekmeleri kapat")
    def s_close():
        while v.tab_widget.count():
            w = v.tab_widget.widget(0)
            if isinstance(w, PDFTabDocument):
                w.set_modified(False)
            before = v.tab_widget.count()
            v.close_tab(0)
            pump(50)
            if v.tab_widget.count() == before:
                break

    s_close()

    LanguageManager.set_language("tr")
    return finish()


def finish():
    closer.stop()
    passed = sum(r["ok"] for r in RESULTS)
    report = {
        "python": sys.version,
        "platform": sys.platform,
        "work_dir": WORK,
        "passed": passed,
        "failed": len(RESULTS) - passed,
        "results": RESULTS,
        "uncaught_exceptions": UNCAUGHT,
    }
    out = os.path.join(ROOT, "tests", "smoke_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\n" + "=" * 60)
    print(f"Sonuc: {passed}/{len(RESULTS)} adim basarili. Rapor: {out}")
    if UNCAUGHT:
        print(f"Yakalanmayan istisna sayisi: {len(UNCAUGHT)} (ayrintilar raporda)")
    shutil.rmtree(WORK, ignore_errors=True)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    code = main()
    os._exit(code)
