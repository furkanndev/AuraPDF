"""
AuraPDF - Arayüz Regresyon Testleri
===================================
Sekme başlığı rengini ve sayfa stili penceresindeki radyo düğmesi metnini korur.

Çalıştırma:
    python -m unittest tests.test_ui_regressions -v
"""

import os
import re
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

from src.ui.aura_views import AuraTabBarWidget
from src.ui.dialogs.new_page_dialog import NewPageDialog

MIN_TITLE_LIGHTNESS = 0.7


class UiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_new_tab_title_is_drawn_in_active_theme_color(self):
        bar = AuraTabBarWidget()
        bar.apply_theme("gray")
        bar.show()
        bar.add_tab("Report.pdf")
        bar.set_current_index(0)
        self.app.processEvents()
        image = bar.items[0].lbl_title.grab().toImage()
        brightest = max(image.pixelColor(x, y).lightnessF() for x in range(image.width()) for y in range(image.height()))
        self.assertGreater(brightest, MIN_TITLE_LIGHTNESS)
        bar.close()

    def test_checked_radio_indicator_keeps_its_size(self):
        style = NewPageDialog(None).styleSheet()
        size = re.search(r"QRadioButton::indicator \{\s*width: (\d+)px;.*?border: (\d+)px", style, re.S)
        checked = re.search(r"QRadioButton::indicator:checked \{\s*width: (\d+)px;.*?border: (\d+)px", style, re.S)
        self.assertIsNotNone(checked, "secili gosterge kendi boyutunu tanimlamali")
        self.assertEqual(int(size[1]) + 2 * int(size[2]), int(checked[1]) + 2 * int(checked[2]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
