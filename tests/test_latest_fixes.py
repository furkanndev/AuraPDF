import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QMimeData
from PyQt6.QtGui import QColor, QDropEvent

# Initialize QApplication
app = QApplication.instance() or QApplication(sys.argv)

from src.ui.icons import ModernIconFactory
from src.ui.popups import ModernStampPalettePopup, POPUP_THEME_SPECS
from src.ui.dialog_theme import THEME_PALETTES, get_current_theme
from src.ui.dialogs.settings_dialog import ModernSettingsDialog
from src.ui.dialogs.stamp_dialog import render_stamp_png_bytes
from src.ui.modern_views import OrganizePagesListWidget, OrganizePagesWorkspace
from src.core.i18n import LanguageManager


class TestLatestFixes(unittest.TestCase):
    def test_print_icon_color_is_white(self):
        """Yazdır butonu renginin mor yerine beyaz olduğunu doğrula."""
        icon = ModernIconFactory.icon_print()
        self.assertFalse(icon.isNull())
        img = icon.pixmap(24, 24).toImage()
        found_white = False
        found_purple = False
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                if c.alpha() > 150:
                    if c.red() > 240 and c.green() > 240 and c.blue() > 240:
                        found_white = True
                    if c.red() > 150 and c.blue() > 200 and c.green() < 120:
                        found_purple = True
        self.assertTrue(found_white)
        self.assertFalse(found_purple)

    def test_theme_cleanup(self):
        """Açık ve koyu siyah temaların tamamen kaldırıldığını, gri temanın varsayılan olduğunu doğrula."""
        dlg = ModernSettingsDialog()
        # Ensure 'light' and 'dark' are not options in theme choices
        self.assertNotIn("light", dlg.theme_radios)
        self.assertNotIn("dark", dlg.theme_radios)
        self.assertIn("gray", dlg.theme_radios)
        self.assertIn("apple", dlg.theme_radios)

        # Ensure fallback aliases safely return 'gray'
        self.assertEqual(THEME_PALETTES["light"], THEME_PALETTES["gray"])
        self.assertEqual(THEME_PALETTES["dark"], THEME_PALETTES["gray"])
        self.assertEqual(POPUP_THEME_SPECS["light"], POPUP_THEME_SPECS["gray"])
        self.assertEqual(POPUP_THEME_SPECS["dark"], POPUP_THEME_SPECS["gray"])

    def test_in_place_custom_stamp_creation(self):
        """Damga oluşturmanın ayrı pencere yerine pop-up içinde sekme olduğunu ve renk eşleşmesini doğrula."""
        popup = ModernStampPalettePopup()
        self.assertTrue(hasattr(popup, 'btn_tab_preset'))
        self.assertTrue(hasattr(popup, 'btn_tab_custom'))
        self.assertTrue(hasattr(popup, 'stack'))

        # Switch to custom tab
        popup.switch_to_custom_tab()
        self.assertEqual(popup.stack.currentIndex(), 1)
        self.assertTrue(popup.btn_tab_custom.isChecked())

        # Select custom color
        popup._select_custom_color("#2563eb")
        self.assertEqual(popup._custom_color, "#2563eb")

        # Verify preview frame has paper white background (#ffffff)
        self.assertIn("#ffffff", popup.preview_frame.styleSheet())
        self.assertFalse(popup.lbl_custom_preview.pixmap().isNull())

        # Verify generated stamp bytes with matching color
        stamp_data = render_stamp_png_bytes("ONAYLANDI", "#2563eb", is_dynamic=False)
        self.assertTrue(len(stamp_data) > 0)

    def test_organize_pages_drag_and_drop(self):
        """Sayfa organizasyonunda mouse ile sürükle-bırak yapılandırmasını doğrula."""
        list_widget = OrganizePagesListWidget()
        self.assertTrue(list_widget.dragEnabled())
        self.assertTrue(list_widget.acceptDrops())
        self.assertNotEqual(list_widget.movement(), list_widget.Movement.Static)
        self.assertEqual(list_widget.movement(), list_widget.Movement.Snap)


if __name__ == "__main__":
    unittest.main()
