"""
AuraPDF - İkon Seti Koruma Testleri
===================================
Galeride ad ile ikonların çakışmamasını, setlerin ayrı siluet üretmesini ve
set adlarının iki dilde de bulunmasını korur.

Çalıştırma:
    python -m unittest tests.test_icon_sets -v
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from src.core.i18n import LanguageManager
from src.ui.dialogs.settings_dialog import AuraIconSetGallery
from src.ui.icon_glyphs import GLYPHS, ICON_SETS, COLORFUL_GLYPHS, get_icon_set, glyph_icon, restore_icon_set, set_icon_set

BASE_SETS = [name for name in ICON_SETS if not name.endswith("_mono")]
RENDER_SIZE = 64
MIN_PIXEL_DIFFERENCE = 0.04


def _render(glyph: str, icon_set: str) -> bytes:
    state = get_icon_set()
    set_icon_set(icon_set)
    image = QImage(QSize(RENDER_SIZE, RENDER_SIZE), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    glyph_icon(glyph, "#2563eb").paint(painter, 0, 0, RENDER_SIZE, RENDER_SIZE)
    painter.end()
    restore_icon_set(state)
    return image.bits().asstring(image.sizeInBytes())


def _difference(first: bytes, second: bytes) -> float:
    changed = sum(1 for i in range(3, len(first), 4) if abs(first[i] - second[i]) > 40)
    return changed / (RENDER_SIZE * RENDER_SIZE)


class IconSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_title_and_icons_never_overlap(self):
        gallery = AuraIconSetGallery({name: name for name in ICON_SETS})
        for width in (240, 320, 420, 560, 760, 1000):
            gallery.resize(width, gallery.height())
            for index in range(len(ICON_SETS)):
                title = gallery._title_rect(index)
                card = gallery._card_rect(index)
                self.assertTrue(card.contains(title), f"genislik {width}: ad karttan tasiyor")
                icons = gallery._icon_rects(index)
                self.assertTrue(icons, f"genislik {width}: hic ikon sigmadi")
                for rect in icons:
                    self.assertFalse(rect.intersects(title), f"genislik {width}: ad ile ikon cakisiyor")
                    self.assertTrue(card.contains(rect), f"genislik {width}: ikon karttan tasiyor")

    def test_samples_are_visually_distinct_and_keep_color(self):
        names = [glyph for glyph, _color in AuraIconSetGallery.SAMPLES]
        self.assertEqual(len(set(names)), len(names))
        for glyph in names:
            self.assertIn(glyph, GLYPHS)
            self.assertIn(glyph, COLORFUL_GLYPHS)
        for i, first in enumerate(names):
            for second in names[i + 1:]:
                self.assertGreater(_difference(_render(first, "modern"), _render(second, "modern")),
                                   MIN_PIXEL_DIFFERENCE, f"{first} ve {second} birbirine fazla benziyor")

    def test_sets_render_different_shapes(self):
        for glyph in ("comments", "lock"):
            images = {name: _render(glyph, name) for name in BASE_SETS}
            for i, first in enumerate(BASE_SETS):
                for second in BASE_SETS[i + 1:]:
                    self.assertGreater(_difference(images[first], images[second]), MIN_PIXEL_DIFFERENCE,
                                       f"{glyph}: {first} ve {second} ayni gorunuyor")

    def test_every_set_has_tr_and_en_title(self):
        keys = [f"settings_icon_style_{name}" for name in BASE_SETS] + ["settings_icon_variant_color", "settings_icon_variant_mono"]
        for code in ("tr", "en"):
            LanguageManager.set_language(code)
            for key in keys:
                self.assertNotEqual(LanguageManager.tr(key), key, f"[{code}] eksik: {key}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
