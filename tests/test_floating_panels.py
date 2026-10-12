import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QSettings, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent

app = QApplication.instance() or QApplication(sys.argv)

from src.ui.icons import ModernIconFactory
from src.core.i18n import LanguageManager
from src.ui.widgets import FullscreenReadingHUD, FullscreenSlideToolbar
from src.ui.modern_views import FloatingQuickToolsCapsule


class MockMainWindow(QWidget):
    """Hafif test penceresi."""
    def __init__(self):
        super().__init__()
        self.resize(1920, 1080)
        self.current_tool = "select"
        self.capsule_docked_to_left = True
        self.capsule_docked_to_right = False
        self.capsule_docked_to_top = False
        self.fullscreen_toolbar = None
        self.fullscreen_reading_hud = None

    def isFullScreen(self):
        return True

    def get_current_tab_doc(self):
        return None

    def update_floating_capsule_pos(self):
        pass

    def ensure_distinct_fullscreen_edges(self, moved_widget, target_edge: str):
        if moved_widget is getattr(self, 'fullscreen_toolbar', None):
            other_widget = getattr(self, 'fullscreen_reading_hud', None)
        else:
            other_widget = getattr(self, 'fullscreen_toolbar', None)

        if other_widget is None:
            return

        other_edge = getattr(other_widget, 'edge', None)
        if other_edge == target_edge:
            old_edge = getattr(moved_widget, 'edge', None)
            all_edges = ['left', 'bottom', 'right', 'top']
            if old_edge and old_edge != target_edge:
                swap_to_edge = old_edge
            else:
                available = [e for e in all_edges if e != target_edge]
                swap_to_edge = available[0]

            other_widget._apply_edge_layout(swap_to_edge)
            other_widget.edge = swap_to_edge


class TestFloatingPanels(unittest.TestCase):
    def setUp(self):
        self.win = MockMainWindow()
        self.win.show()

    def tearDown(self):
        self.win.close()
        # Clean settings
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.remove("fullscreen_hud_edge")
        settings.remove("fullscreen_hud_offset")
        settings.remove("fullscreen_toolbar_edge")
        settings.remove("fullscreen_toolbar_side")
        settings.remove("fullscreen_toolbar_offset")
        settings.remove("capsule_dock_position")
        settings.remove("capsule_float_x")
        settings.remove("capsule_float_y")

    def test_icons_valid(self):
        """icon_refresh ve icon_grip simgelerinin geçerli olduğunu doğrula."""
        icon_ref = ModernIconFactory.icon_refresh()
        self.assertFalse(icon_ref.isNull())
        icon_grip = ModernIconFactory.icon_grip()
        self.assertFalse(icon_grip.isNull())

    def test_fullscreen_hud_4_edges(self):
        """FullscreenReadingHUD'ın 4 kenara da (sağ, sol, yukarı, aşağı) yerleşebildiğini ve yön değiştirdiğini test et."""
        hud = FullscreenReadingHUD(self.win)
        self.win.fullscreen_reading_hud = hud

        win_w = self.win.width()
        win_h = self.win.height()

        # Alt kenar (yatay)
        hud.set_edge("bottom")
        self.assertEqual(hud.edge, "bottom")
        pos_bottom = hud.get_target_coords(visible=True)
        self.assertAlmostEqual(pos_bottom.x(), (win_w - hud.width()) // 2, delta=20)
        self.assertEqual(pos_bottom.y(), win_h - hud.height() - 16)

        # Üst kenar (yatay)
        hud.set_edge("top")
        self.assertEqual(hud.edge, "top")
        pos_top = hud.get_target_coords(visible=True)
        self.assertAlmostEqual(pos_top.x(), (win_w - hud.width()) // 2, delta=20)
        self.assertEqual(pos_top.y(), 16)

        # Sol kenar (dikey)
        hud.set_edge("left")
        self.assertEqual(hud.edge, "left")
        pos_left = hud.get_target_coords(visible=True)
        self.assertEqual(pos_left.x(), 16)
        self.assertAlmostEqual(pos_left.y(), (win_h - hud.height()) // 2, delta=20)

        # Sağ kenar (dikey)
        hud.set_edge("right")
        self.assertEqual(hud.edge, "right")
        pos_right = hud.get_target_coords(visible=True)
        self.assertEqual(pos_right.x(), win_w - hud.width() - 16)
        self.assertAlmostEqual(pos_right.y(), (win_h - hud.height()) // 2, delta=20)

    def test_distinct_fullscreen_edges_mutual_swap(self):
        """İki toolbar'ın asla aynı kenara sabitlenemediğini (Mutual Swap) doğrula."""
        tb = FullscreenSlideToolbar(self.win)
        hud = FullscreenReadingHUD(self.win)
        self.win.fullscreen_toolbar = tb
        self.win.fullscreen_reading_hud = hud

        tb.set_edge("left")
        hud.set_edge("bottom")
        self.assertEqual(tb.edge, "left")
        self.assertEqual(hud.edge, "bottom")
        self.assertNotEqual(tb.edge, hud.edge)

        # tb'yi hud'ın bulunduğu 'bottom' kenarına taşı -> hud otomatik olarak 'left'e geçmeli
        tb.set_edge("bottom")
        self.assertEqual(tb.edge, "bottom")
        self.assertEqual(hud.edge, "left")
        self.assertNotEqual(tb.edge, hud.edge)

        # hud'ı tb'nin bulunduğu 'bottom' kenarına taşı -> tb otomatik olarak 'left'e geçmeli
        hud.set_edge("bottom")
        self.assertEqual(hud.edge, "bottom")
        self.assertEqual(tb.edge, "left")
        self.assertNotEqual(tb.edge, hud.edge)

        # tb'yi boş olan 'top' kenarına taşı -> hud etkilenmez
        tb.set_edge("top")
        self.assertEqual(tb.edge, "top")
        self.assertEqual(hud.edge, "bottom")
        self.assertNotEqual(tb.edge, hud.edge)

        # hud'ı tb'nin bulunduğu 'top' kenarına taşı -> tb 'bottom'a geçmeli
        hud.set_edge("top")
        self.assertEqual(hud.edge, "top")
        self.assertEqual(tb.edge, "bottom")
        self.assertNotEqual(tb.edge, hud.edge)

    def test_fullscreen_toolbar_edge_offset_and_reset(self):
        """FullscreenSlideToolbar kenar ofseti ve merkeze sıfırlama işlevini doğrula."""
        tb = FullscreenSlideToolbar(self.win)
        self.win.fullscreen_toolbar = tb
        self.assertIsNotNone(tb.grip)

        # Varsayılan ofset 0.5 (merkez)
        self.assertEqual(tb.edge_offset_ratio, 0.5)

        # Ofseti değiştir ve hesapla
        tb.edge_offset_ratio = 0.25
        pos = tb.get_target_coords(visible=True)
        self.assertIsNotNone(pos)

        # Merkeze sıfırla
        tb.reset_to_center()
        self.assertEqual(tb.edge_offset_ratio, 0.5)

    def test_floating_capsule_free_floating_and_reset(self):
        """FloatingQuickToolsCapsule serbest gezinme ve kenar bırakma mantığını doğrula."""
        capsule = FloatingQuickToolsCapsule(parent=self.win)
        capsule.main_window = self.win

        # Ekranın ortasına taşı ve serbest bırak
        capsule.move(500, 300)
        capsule._check_dock_on_release()

        self.assertFalse(self.win.capsule_docked_to_left)
        self.assertFalse(self.win.capsule_docked_to_right)
        self.assertFalse(self.win.capsule_docked_to_top)
        self.assertTrue(capsule.user_moved)

        # Varsayılana sıfırlama testi
        capsule.reset_to_default_pos()
        self.assertFalse(capsule.user_moved)
        self.assertTrue(self.win.capsule_docked_to_left)


if __name__ == "__main__":
    unittest.main()
