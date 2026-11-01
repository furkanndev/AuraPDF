"""
AuraPDF - Shell Entegrasyonu Testleri
=====================================
PDF simgesinin hangi ProgID'den geldiğini belirleyen mantığı ve kaldırma sonrası
varsayılan uygulama seçiminin temizlenmesini korur. Gerçek kayıt defterine dokunmaz.

Çalıştırma:
    python -m unittest tests.test_shell_integration -v
"""

import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core import shell_integration as shell

AURA = "AuraPDF.AssocFile.PDF"
EDGE = "MSEdgePDF"


class FakeRegistry:
    """Yalnızca HKCU altında anahtar/değer ağacı tutan basit winreg yerine geçer."""

    HKEY_CURRENT_USER = "HKCU"
    HKEY_LOCAL_MACHINE = "HKLM"
    KEY_ALL_ACCESS = 0xF003F

    def __init__(self, tree):
        self.tree = {path.lower(): dict(values) for path, values in tree.items()}

    class _Key:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def OpenKey(self, root, subkey, reserved=0, access=0):
        path = subkey.lower()
        if path not in self.tree:
            raise FileNotFoundError(subkey)
        return self._Key(path)

    def QueryValueEx(self, key, name):
        values = self.tree[key.path]
        if name not in values:
            raise FileNotFoundError(name)
        return values[name], 1

    def EnumKey(self, key, index):
        children = sorted(p for p in self.tree if p.startswith(key.path + "\\") and "\\" not in p[len(key.path) + 1:])
        if index >= len(children):
            raise OSError
        return children[index].rsplit("\\", 1)[1]

    def DeleteKey(self, root, subkey):
        self.tree.pop(subkey.lower())


class DefaultViewerTests(unittest.TestCase):
    def check(self, effective, choices):
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(shell, "_query_effective_progid", return_value=effective), \
                mock.patch.object(shell, "_read_user_choice_progids", return_value=choices):
            return shell.is_aurapdf_default_viewer()

    def test_progid_detection(self):
        self.assertTrue(shell.is_aurapdf_progid(AURA))
        self.assertTrue(shell.is_aurapdf_progid("aurapdf.document"))
        self.assertFalse(shell.is_aurapdf_progid(EDGE))
        self.assertFalse(shell.is_aurapdf_progid(""))
        self.assertFalse(shell.is_aurapdf_progid(None))

    def test_windows_effective_choice_wins_over_legacy_user_choice(self):
        # Windows 11: UserChoiceLatest AuraPDF, eski UserChoice Edge. Gezgin AuraPDF simgesini gösterir.
        self.assertTrue(self.check(AURA, [EDGE]))
        self.assertFalse(self.check(EDGE, [AURA]))

    def test_user_choice_fallback_prefers_latest(self):
        self.assertTrue(self.check("", [AURA, EDGE]))
        self.assertFalse(self.check("", [EDGE, AURA]))
        self.assertFalse(self.check("", []))


class DanglingChoiceTests(unittest.TestCase):
    BASE = shell.FILE_EXTS_PDF.lower()

    def run_clear(self, tree):
        registry = FakeRegistry(tree)
        with mock.patch.object(sys, "platform", "win32"), mock.patch.dict(sys.modules, {"winreg": registry}):
            registry.HKEY_CURRENT_USER = "HKCU"
            result = shell.clear_dangling_user_choice()
        return result, registry.tree

    def test_removes_choices_that_point_to_aurapdf(self):
        tree = {
            self.BASE: {},
            self.BASE + r"\userchoicelatest": {},
            self.BASE + r"\userchoicelatest\progid": {"ProgId": AURA},
            self.BASE + r"\userchoice": {"ProgId": AURA},
        }
        cleared, left = self.run_clear(tree)
        self.assertTrue(cleared)
        self.assertEqual(sorted(left), [self.BASE])

    def test_keeps_choices_of_other_applications(self):
        tree = {
            self.BASE + r"\userchoicelatest": {},
            self.BASE + r"\userchoicelatest\progid": {"ProgId": EDGE},
            self.BASE + r"\userchoice": {"ProgId": EDGE},
        }
        cleared, left = self.run_clear(tree)
        self.assertFalse(cleared)
        self.assertEqual(len(left), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
