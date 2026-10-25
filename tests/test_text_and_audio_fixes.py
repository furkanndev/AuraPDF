import unittest
import sys
import os

from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow
from PyQt6.QtGui import QTextCursor, QTextOption, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF, QEvent

from src.core.i18n import LanguageManager
from src.core.hyperlink_detector import detect_hyperlink, is_valid_tc
from src.ui.widgets import EditableInlineTextItem
from src.ui.dialogs.media_dialogs import AudioRecordDialog


app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class MockTabDocument:
    def __init__(self):
        self.page_positions = {
            0: {
                'left': 50.0,
                'right': 550.0,
                'top': 20.0,
                'bottom': 700.0,
                'width': 500.0,
                'height': 680.0
            }
        }
        self.base_render_dpi = 1.5
        self.drawings = []
        self.active_text_item = None
        self.last_text_item = None

    def commit_inline_text(self, item):
        pass

    def notify_drawings_changed(self, page_idx):
        pass


class TestTextAndAudioFixes(unittest.TestCase):

    def setUp(self):
        self.tab_doc = MockTabDocument()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)

    def test_hyperlink_detector_rejects_plain_numbers(self):
        # Plain consecutive numbers should NEVER be detected as links
        self.assertIsNone(detect_hyperlink("123456"))
        self.assertIsNone(detect_hyperlink("12345678901"))
        self.assertIsNone(detect_hyperlink("5551234567"))
        self.assertIsNone(detect_hyperlink("98765432100"))
        self.assertIsNone(detect_hyperlink("12.345.678"))
        self.assertIsNone(detect_hyperlink("123,456,789"))

        # Valid URLs and emails should still be detected
        url_det = detect_hyperlink("https://aurapdf.com")
        self.assertIsNotNone(url_det)
        self.assertEqual(url_det['type'], 'url')

        email_det = detect_hyperlink("support@aurapdf.com")
        self.assertIsNotNone(email_det)
        self.assertEqual(email_det['type'], 'email')

        # Phone with explicit '+' prefix or formatted separators should be detected
        phone_det = detect_hyperlink("+90 555 123 45 67")
        self.assertIsNotNone(phone_det)
        self.assertEqual(phone_det['type'], 'phone')

        # TC Kimlik ONLY when explicitly labeled and checksum is valid
        self.assertIsNone(detect_hyperlink("TC: 12345678900"))  # Invalid checksum
        valid_sample_tc = "10000000146"
        self.assertTrue(is_valid_tc(valid_sample_tc))
        tc_det = detect_hyperlink(f"TC Kimlik: {valid_sample_tc}")
        self.assertIsNotNone(tc_det)
        self.assertEqual(tc_det['type'], 'tc')

    def test_formatting_bold_italic_underline_no_crash(self):
        item = EditableInlineTextItem(
            self.tab_doc, 0, QPointF(100.0, 100.0),
            font_family="Arial", font_size=14, text="Merhaba Dunya"
        )
        self.scene.addItem(item)
        self.tab_doc.active_text_item = item

        # Applying format to entire text (no selection) should NOT throw AttributeError
        try:
            item.apply_format_to_selection(bold=True)
            self.assertTrue(item.bold)
            item.apply_format_to_selection(italic=True)
            self.assertTrue(item.italic)
            item.apply_format_to_selection(underline=True)
            self.assertTrue(item.underline)
            item.apply_format_to_selection(bold=False, italic=False, underline=False)
            self.assertFalse(item.bold)
        except AttributeError as e:
            self.fail(f"apply_format_to_selection threw AttributeError: {e}")

        # Applying format to partial selection
        cur = item.textCursor()
        cur.setPosition(0)
        cur.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
        item.setTextCursor(cur)
        try:
            item.apply_format_to_selection(bold=True)
            frags = item.get_fragments()
            self.assertTrue(len(frags) > 0)
        except Exception as e:
            self.fail(f"apply_format_to_selection with selection threw exception: {e}")

    def test_dynamic_text_box_width_and_boundary_wrap(self):
        # Page right is at 550.0. Pos is at x=400.0. Margin is 12.0.
        # max_avail_w = (550.0 - 12.0) - 400.0 = 138.0
        item = EditableInlineTextItem(
            self.tab_doc, 0, QPointF(400.0, 100.0),
            font_family="Arial", font_size=14, text=""
        )
        self.scene.addItem(item)

        # Short text should have dynamic bounding box fitting the content
        item.setPlainText("Kisa")
        item._update_text_width_constraint()
        self.assertLess(item.boundingRect().width(), 100.0)

        # Long text that would overflow page right must be clamped and wrapped
        long_sentence = "Bu cumle cok uzundur ve sayfanin sag kenarini asacak sekilde devam etmektedir."
        item.setPlainText(long_sentence)
        item._update_text_width_constraint()
        # Ensure item bounds + x pos does not overflow page right
        item_right_in_scene = item.pos().x() + item.boundingRect().width() - 6.0
        self.assertLessEqual(item_right_in_scene, 550.0)

        # When text is shortened again, it should return to dynamic sizing
        item.setPlainText("Ok")
        item._update_text_width_constraint()
        self.assertLess(item.boundingRect().width(), 80.0)

    def test_audio_record_dialog_compact_mode_frameless_and_translations(self):
        parent_win = QMainWindow()
        dlg = AudioRecordDialog(parent_win)

        # Initially in full view mode
        self.assertFalse(dlg.is_compact)
        self.assertEqual(dlg.stack.currentWidget(), dlg.widget_full)

        # Toggle to compact mode
        dlg._toggle_compact_mode()
        self.assertTrue(dlg.is_compact)
        self.assertEqual(dlg.stack.currentWidget(), dlg.widget_mini)

        # Check window flags for frameless floating tool capsule
        flags = dlg.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowType.FramelessWindowHint))
        self.assertTrue(bool(flags & Qt.WindowType.Tool))
        self.assertTrue(bool(flags & Qt.WindowType.WindowStaysOnTopHint))

        # Check that compact widgets have proper tooltips from i18n
        self.assertEqual(dlg.mini_frame.toolTip(), LanguageManager.tr("audio_compact_drag_hint"))
        self.assertEqual(dlg.lbl_mini_time.toolTip(), LanguageManager.tr("audio_compact_time"))
        self.assertEqual(dlg.btn_mini_pause.toolTip(), LanguageManager.tr("audio_record_pause"))
        self.assertEqual(dlg.btn_mini_stop.toolTip(), LanguageManager.tr("audio_record_stop"))
        self.assertEqual(dlg.btn_mini_expand.toolTip(), LanguageManager.tr("audio_record_expand_tip"))
        self.assertEqual(dlg.btn_mini_cancel.toolTip(), LanguageManager.tr("btn_cancel"))

        # Toggle back to full view
        dlg._toggle_compact_mode()
        self.assertFalse(dlg.is_compact)
        self.assertEqual(dlg.stack.currentWidget(), dlg.widget_full)

        dlg.close()

    def test_i18n_tr_en_exact_symmetry(self):
        tr_keys = set(LanguageManager.TRANSLATIONS.get('tr', {}).keys())
        en_keys = set(LanguageManager.TRANSLATIONS.get('en', {}).keys())
        self.assertEqual(len(tr_keys - en_keys), 0)
        self.assertEqual(len(en_keys - tr_keys), 0)


if __name__ == '__main__':
    unittest.main()
