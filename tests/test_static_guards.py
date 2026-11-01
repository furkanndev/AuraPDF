"""
AuraPDF - Statik Koruma Testleri (Static Guard Tests)
=====================================================

PyQt6 / PyMuPDF GEREKTIRMEZ. Sadece Python standart kutuphanesi ile calisir,
bu yuzden her makinede (CI dahil) birkac saniyede kosar.

Amac: Kod tabaninda ekleme/silme sonrasi kalan "sessiz" kiriklari yakalamak:
  1. Silinmis modullere / isimlere yapilan importlar (fonksiyon icindeki tembel importlar dahil)
  2. Ayni sinifta iki kez tanimlanmis metotlar (ikincisi birinciyi sessizce ezer)
  3. TR / EN ceviri sozlugu esitligi ve kodda kullanilip sozlukte olmayan anahtarlar
  4. Ayni ceviri anahtarinin farkli metinlerle tekrar tanimlanmasi
  5. hasattr/getattr ile hic tanimlanmamis bir nitelige bakilmasi (olu kod yolu)
  6. main.py __all__ / _LAZY_EXPORTS tutarliligi

Calistirma:
    python -m unittest tests.test_static_guards -v
"""

import ast
import collections
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")


def _iter_py_files():
    for dp, dns, fs in os.walk(SRC):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for f in fs:
            if f.endswith(".py"):
                yield os.path.join(dp, f)
    yield os.path.join(ROOT, "main.py")


def _module_name(path):
    rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
    if rel.endswith(".__init__"):
        rel = rel[: -len(".__init__")]
    return rel


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


TREES = {p: _parse(p) for p in _iter_py_files()}
MODULES = {_module_name(p): p for p in TREES}


def _top_level_names(tree):
    """Modulun ust seviyede (try/if bloklari dahil) tanimladigi isimler."""
    names = set()

    def visit(body):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in targets:
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            names.add(x.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    names.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.Try):
                visit(n.body)
                visit(n.orelse)
                visit(n.finalbody)
                for h in n.handlers:
                    visit(h.body)
            elif isinstance(n, ast.If):
                visit(n.body)
                visit(n.orelse)

    visit(tree.body)
    return names


TOP_NAMES = {m: _top_level_names(TREES[p]) for m, p in MODULES.items()}


class ImportIntegrityTests(unittest.TestCase):
    def test_all_internal_imports_resolve(self):
        problems = []
        for path, tree in TREES.items():
            mod = _module_name(path)
            pkg = mod if path.endswith("__init__.py") else mod.rsplit(".", 1)[0]
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom):
                    if n.level:
                        base = pkg.split(".")
                        base = base[: len(base) - (n.level - 1)]
                        target = ".".join(base + ([n.module] if n.module else []))
                    else:
                        target = n.module or ""
                    if not (target == "src" or target.startswith("src.")):
                        continue
                    if target not in MODULES:
                        problems.append(f"{os.path.relpath(path, ROOT)}:{n.lineno} modul yok: {target}")
                        continue
                    for a in n.names:
                        if a.name == "*":
                            continue
                        if a.name not in TOP_NAMES[target] and f"{target}.{a.name}" not in MODULES:
                            problems.append(
                                f"{os.path.relpath(path, ROOT)}:{n.lineno} isim yok: {target}.{a.name}"
                            )
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name.startswith("src") and a.name not in MODULES:
                            problems.append(f"{os.path.relpath(path, ROOT)}:{n.lineno} modul yok: {a.name}")
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_main_lazy_exports_and_all(self):
        tree = TREES[os.path.join(ROOT, "main.py")]
        lazy, all_names = {}, []
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                if n.targets[0].id == "_LAZY_EXPORTS":
                    lazy = ast.literal_eval(n.value)
                elif n.targets[0].id == "__all__":
                    all_names = ast.literal_eval(n.value)
        problems = []
        for key, (mod, attr) in lazy.items():
            if attr not in TOP_NAMES.get(mod, set()):
                problems.append(f"_LAZY_EXPORTS[{key!r}] -> {mod}.{attr} bulunamadi")
        main_names = TOP_NAMES["main"]
        for name in all_names:
            if name not in lazy and name not in main_names:
                problems.append(f"__all__ icindeki {name!r} cozulemiyor (from main import * AttributeError verir)")
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


class ClassDefinitionTests(unittest.TestCase):
    def test_no_duplicate_methods_in_class(self):
        problems = []
        for path, tree in TREES.items():
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                seen = {}
                for item in cls.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        decos = {ast.unparse(d) for d in item.decorator_list}
                        # property setter/getter ciftleri mesrudur
                        if any(d.endswith(".setter") or d.endswith(".deleter") for d in decos):
                            continue
                        if item.name in seen:
                            problems.append(
                                f"{os.path.relpath(path, ROOT)}: {cls.name}.{item.name} "
                                f"satir {seen[item.name]} tanimi, satir {item.lineno} tarafindan eziliyor"
                            )
                        seen[item.name] = item.lineno
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_no_duplicate_module_functions(self):
        problems = []
        for path, tree in TREES.items():
            seen = {}
            for item in tree.body:
                if isinstance(item, (ast.FunctionDef, ast.ClassDef)):
                    if item.name in seen:
                        problems.append(
                            f"{os.path.relpath(path, ROOT)}: {item.name} satir {seen[item.name]} ve {item.lineno}"
                        )
                    seen[item.name] = item.lineno
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


def _load_translations():
    tree = TREES[os.path.join(SRC, "core", "i18n.py")]
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TRANSLATIONS":
            out = {}
            for k, v in zip(n.value.keys, n.value.values):
                pairs = [(kk.value, getattr(vv, "value", None), kk.lineno) for kk, vv in zip(v.keys, v.values)]
                out[k.value] = pairs
            return out
    raise AssertionError("TRANSLATIONS bulunamadi")


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _load_translations()
        cls.tr = {k: v for k, v, _ in cls.raw["tr"]}
        cls.en = {k: v for k, v, _ in cls.raw["en"]}

    def test_tr_en_parity(self):
        only_tr = sorted(set(self.tr) - set(self.en))
        only_en = sorted(set(self.en) - set(self.tr))
        self.assertEqual((only_tr, only_en), ([], []))

    def test_no_conflicting_duplicate_keys(self):
        problems = []
        for lang, pairs in self.raw.items():
            seen = collections.defaultdict(list)
            for k, v, line in pairs:
                seen[k].append((line, v))
            for k, occ in seen.items():
                if len(occ) > 1 and len({v for _, v in occ}) > 1:
                    lines = ", ".join(str(line) for line, _ in occ)
                    problems.append(f"[{lang}] {k!r} satir {lines}: farkli metinler, sonuncusu gecerli")
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_used_keys_exist(self):
        missing = collections.defaultdict(list)
        for path, tree in TREES.items():
            for n in ast.walk(tree):
                if (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "tr"
                    and ast.unparse(n.func.value) == "LanguageManager"
                    and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)
                ):
                    key = n.args[0].value
                    if key not in self.tr or key not in self.en:
                        missing[key].append(f"{os.path.relpath(path, ROOT)}:{n.lineno}")
        self.assertEqual(dict(missing), {})


TURKISH_CHARS = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
UI_SINKS = {
    "setText", "setWindowTitle", "setToolTip", "setPlaceholderText", "QLabel", "QPushButton",
    "addItem", "QCheckBox", "QRadioButton", "QGroupBox", "information", "warning", "critical",
    "question", "setStatusTip", "addAction", "QAction", "show_osd_message", "setTitle", "addTab",
    "setHeaderLabels", "emit",
}

# Arayuze giden gomulu Turkce metin kalmadi; yenisi eklenirse test kirilir (regresyon korumasi).
HARDCODED_TR_BUDGET = int(os.environ.get("AURAPDF_HARDCODED_TR_BUDGET", "0"))


class HardcodedStringTests(unittest.TestCase):
    def test_hardcoded_turkish_ui_strings_within_budget(self):
        hits = []
        for path, tree in TREES.items():
            if path.endswith(os.path.join("core", "i18n.py")):
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                if name not in UI_SINKS:
                    continue
                for a in n.args:
                    for s in ast.walk(a):
                        if isinstance(s, ast.Constant) and isinstance(s.value, str) and TURKISH_CHARS.search(s.value):
                            hits.append(f"{os.path.relpath(path, ROOT)}:{n.lineno}: {s.value[:50]!r}")
        if hits:
            print(f"\n[bilgi] Kodda gomulu Turkce arayuz metni: {len(hits)} adet. Ilk 10:")
            for h in hits[:10]:
                print("   ", h)
        self.assertLessEqual(len(hits), HARDCODED_TR_BUDGET)


class DeadAttributeTests(unittest.TestCase):
    """hasattr(x, 'foo') ile kontrol edilen ama projede HIC tanimlanmayan nitelikler.

    Bu kontroller her zaman False doner; yani o kod yolu asla calismaz.
    Disaridaki kutuphanelere (fitz, Qt) ait nitelikler ALLOWLIST'te tutulur.
    """

    ALLOWLIST = {
        # PyMuPDF / fitz nitelikleri
        "embfile_names", "embfile_add", "is_closed", "get_label", "get_page_labels", "set_page_labels",
        "subset_fonts", "PDF_WIDGET_TYPE_RADIOBUTTON", "PDF_WIDGET_TYPE_LISTBOX",
        "page_count", "load_page",
        # Qt / dis nesneler
        "is_text_input",
    }

    def test_no_hasattr_on_never_defined_attributes(self):
        defined = set()
        for tree in TREES.values():
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined.add(n.name)
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                    defined.add(n.attr)
                elif isinstance(n, ast.ClassDef):
                    # sinif govdesindeki atamalar (pyqtSignal, sabitler) da niteliktir
                    for item in n.body:
                        if isinstance(item, (ast.Assign, ast.AnnAssign)):
                            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
                            for t in targets:
                                if isinstance(t, ast.Name):
                                    defined.add(t.id)
                elif (
                    isinstance(n, ast.Call)
                    and getattr(n.func, "id", None) == "setattr"
                    and len(n.args) >= 2
                    and isinstance(n.args[1], ast.Constant)
                ):
                    defined.add(n.args[1].value)
        problems = []
        for path, tree in TREES.items():
            for n in ast.walk(tree):
                if (
                    isinstance(n, ast.Call)
                    and getattr(n.func, "id", None) in ("hasattr", "getattr")
                    and len(n.args) >= 2
                    and isinstance(n.args[1], ast.Constant)
                    and isinstance(n.args[1].value, str)
                ):
                    attr = n.args[1].value
                    if attr in defined or attr in self.ALLOWLIST or attr.startswith("__"):
                        continue
                    if "_" not in attr.strip("_"):
                        continue  # camelCase Qt API'leri
                    problems.append(f"{os.path.relpath(path, ROOT)}:{n.lineno} {ast.unparse(n.args[0])}.{attr}")
        self.assertEqual(problems, [], "\nOlu kod yollari:\n" + "\n".join(sorted(problems)))


class BookmarkThemeGuardTests(unittest.TestCase):
    """Yer imi akislarinin temali AuraAddBookmarkDialog kullandigini dogrular.

    QInputDialog.getText ile acilan pencereler koyu temalarda butonlari goruntulenemez
    hale getirebilir. Bu test yeni bir QInputDialog cagrisinin sessizce girilmesini onler.
    """

    # Yer imi islemleri burada yapilir; diger dosyalarda (sifre sorma vb.) izinli.
    GUARDED_FILES = [
        os.path.join(SRC, "document", "tab_document.py"),
        os.path.join(SRC, "ui", "widgets.py"),
    ]
    # Dosyadaki izinli kullanim sayisi (sifre sorgulama vb. farkli amaclara)
    ALLOWED_COUNTS: dict[str, int] = {}

    def test_no_qinputdialog_in_bookmark_files(self):
        problems = []
        for path in self.GUARDED_FILES:
            if not os.path.isfile(path):
                continue
            tree = TREES.get(path)
            if tree is None:
                continue
            count = 0
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and n.attr == "getText":
                    if isinstance(n.value, ast.Name) and n.value.id == "QInputDialog":
                        count += 1
            allowed = self.ALLOWED_COUNTS.get(os.path.basename(path), 0)
            if count > allowed:
                problems.append(
                    f"{os.path.relpath(path, ROOT)}: QInputDialog.getText {count} kez kullaniliyor "
                    f"(izinli: {allowed}). AuraAddBookmarkDialog kullanin."
                )
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
