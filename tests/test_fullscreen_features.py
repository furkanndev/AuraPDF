import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QPoint

app = QApplication.instance() or QApplication(sys.argv)

from src.ui.icons import ModernIconFactory
from src.core.i18n import LanguageManager
from src.ui.widgets import FullscreenReadingHUD
from src.viewer import AuraPDFViewer


class TestFullscreenFeatures(unittest.TestCase):
    def setUp(self):
        self.viewer = AuraPDFViewer()

    def tearDown(self):
        self.viewer.close()

    def test_icons_exist(self):
        """HUD butonları için gereken tüm ikonların varlığını ve geçerliliğini test et."""
        self.assertFalse(ModernIconFactory.icon_first_page().isNull())
        self.assertFalse(ModernIconFactory.icon_last_page().isNull())
        self.assertFalse(ModernIconFactory.icon_move_left().isNull())
        self.assertFalse(ModernIconFactory.icon_move_right().isNull())
        self.assertFalse(ModernIconFactory.icon_view_single().isNull())
        self.assertFalse(ModernIconFactory.icon_view_double().isNull())
        self.assertFalse(ModernIconFactory.icon_reading_mode().isNull())
        self.assertFalse(ModernIconFactory.icon_reading_dark().isNull())
        self.assertFalse(ModernIconFactory.icon_reading_sepia().isNull())
        self.assertFalse(ModernIconFactory.icon_fit_width().isNull())
        self.assertFalse(ModernIconFactory.icon_fit_page().isNull())
        self.assertFalse(ModernIconFactory.icon_close().isNull())

    def test_fullscreen_hud_initialized(self):
        """FullscreenReadingHUD bileşeninin başlatıldığını ve tüm öğelerini içerdiğini doğrula."""
        hud = self.viewer.fullscreen_reading_hud
        self.assertIsNotNone(hud)
        self.assertIsInstance(hud, FullscreenReadingHUD)
        self.assertTrue(hasattr(hud, 'btn_first'))
        self.assertTrue(hasattr(hud, 'btn_prev'))
        self.assertTrue(hasattr(hud, 'txt_page'))
        self.assertTrue(hasattr(hud, 'lbl_total'))
        self.assertTrue(hasattr(hud, 'btn_next'))
        self.assertTrue(hasattr(hud, 'btn_last'))
        self.assertTrue(hasattr(hud, 'btn_single'))
        self.assertTrue(hasattr(hud, 'btn_double'))
        self.assertTrue(hasattr(hud, 'btn_color_light'))
        self.assertTrue(hasattr(hud, 'btn_color_dark'))
        self.assertTrue(hasattr(hud, 'btn_color_sepia'))
        self.assertTrue(hasattr(hud, 'btn_fit_width'))
        self.assertTrue(hasattr(hud, 'btn_fit_page'))
        self.assertTrue(hasattr(hud, 'btn_close'))

    def test_fullscreen_page_osd(self):
        """show_fullscreen_page_osd metodunun çalıştığını ve metnini doğru biçimlendirdiğini doğrula."""
        # Force simulate fullscreen
        self.viewer.showFullScreen()
        self.viewer.show_fullscreen_page_osd(3, 25)
        self.assertIsNotNone(self.viewer._fs_page_label)
        self.assertTrue(self.viewer._fs_page_label.isVisible())
        self.assertIn("3", self.viewer._fs_page_label.text())
        self.assertIn("25", self.viewer._fs_page_label.text())

        # Test zoom OSD positioning with page OSD present
        self.viewer.show_fullscreen_zoom_osd(125)
        self.assertIsNotNone(self.viewer._fs_zoom_label)
        self.assertTrue(self.viewer._fs_zoom_label.isVisible())
        # Zoom OSD should sit above page OSD
        self.assertLess(self.viewer._fs_zoom_label.y(), self.viewer._fs_page_label.y())

    def test_i18n_fullscreen_keys(self):
        """HUD ve OSD için eklenen tüm anahtarların TR ve EN karşılıklarını doğrula."""
        keys = [
            "fs_hud_first_page",
            "fs_hud_prev_page",
            "fs_hud_next_page",
            "fs_hud_last_page",
            "fs_hud_hide",
            "fs_page_osd"
        ]
        for lang in ["tr", "en"]:
            LanguageManager.set_language(lang)
            for k in keys:
                val = LanguageManager.tr(k, curr=1, total=10)
                self.assertNotEqual(val, k, f"Key {k} should have a translation in {lang}")


if __name__ == "__main__":
    unittest.main()
