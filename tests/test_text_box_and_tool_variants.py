"""Metin kutusu önizlemesi, GIF kaynak birleştirme ve kalem türü ikonlarının testleri."""
import json
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QGraphicsScene

from src.ui import dialogs
from src.ui.dialogs import media_dialogs
from src.ui.dialogs.media_dialogs import GifSearchWorker, _merge_gif_sources, _tenor_page_results
from src.ui.icons import AuraIconFactory
from src.ui.popups import TextSettingsPopup
from src.ui.widgets import EditableInlineTextItem

app = QApplication.instance() or QApplication([])


class FakeDoc:
    view = None
    base_render_dpi = 1.5
    page_positions = {}
    active_text_item = None
    last_text_item = None

    def commit_inline_text(self, item):
        pass


class TextBoxTests(unittest.TestCase):
    def make_item(self, text="Merhaba dunya"):
        self.scene = QGraphicsScene()
        item = EditableInlineTextItem(FakeDoc(), 0, QPointF(10, 10), text=text, color=QColor("#000000"))
        self.scene.addItem(item)
        return item

    def test_selection_strikeout_reads_whole_selection(self):
        item = self.make_item()
        cur = item.textCursor()
        cur.setPosition(0)
        cur.setPosition(4, cur.MoveMode.KeepAnchor)
        item.setTextCursor(cur)
        item.apply_format_to_selection(strikeout=True)
        self.assertTrue(item.get_selection_format()["strikeout"])

    def test_formatting_selected_box_stays_out_of_edit_mode(self):
        item = self.make_item()
        item.setSelected(True)
        item.apply_format_to_selection(bold=True)
        self.assertEqual(int(item.textInteractionFlags().value), 0)

    def test_second_click_enters_editing_first_only_selects(self):
        item = self.make_item()
        item._was_selected_on_press = False
        item._on_box_clicked(QPointF(20, 8), mock.MagicMock(__and__=lambda s, o: 0))
        self.assertEqual(int(item.textInteractionFlags().value), 0)
        item._was_selected_on_press = True
        item._on_box_clicked(QPointF(20, 8), mock.MagicMock(__and__=lambda s, o: 0))
        self.assertNotEqual(int(item.textInteractionFlags().value), 0)

    def test_leave_editing_keeps_box_selected(self):
        item = self.make_item()
        item.enable_editing()
        item.leave_editing()
        self.assertTrue(item.isSelected())
        self.assertEqual(int(item.textInteractionFlags().value), 0)


class PreviewTests(unittest.TestCase):
    def test_preview_receives_strikeout_and_background(self):
        popup = TextSettingsPopup()
        popup.btn_strike.setChecked(True)
        popup._on_box_bg_selected("#fff59d")
        self.assertTrue(popup.preview.strikeout)
        self.assertEqual(popup.preview.box_bg_color, "#fff59d")
        popup.preview.grab()


class PenPreviewTests(unittest.TestCase):
    def test_stroke_preview_paints_without_error(self):
        from src.ui.popups import StrokePreviewWidget
        errors = []
        with mock.patch.object(sys, "excepthook", lambda *exc: errors.append(exc)):
            StrokePreviewWidget().grab()
        self.assertEqual(errors, [])


class GifSourceTests(unittest.TestCase):
    def tenor_page(self):
        cache = {"universal": {"search": {"kedi-low-all": {"results": [
            {"media_formats": {"tinygif": {"url": "t.gif"}, "mediumgif": {"url": "m.gif"}}}]}}}}
        return f'<script id="store-cache" type="text/x-cache" nonce="x">{json.dumps(cache)}</script>'

    def test_tenor_page_parsing(self):
        self.assertEqual(_tenor_page_results(self.tenor_page()), [("t.gif", "m.gif")])
        self.assertEqual(_tenor_page_results("<html></html>"), [])

    def test_merge_alternates_and_dedupes(self):
        a, b, c = ("a", "a"), ("b", "b"), ("c", "c")
        self.assertEqual(_merge_gif_sources([a, b], [c, a]), [a, c, b])

    def run_worker(self, offset, total=120):
        emitted = []
        payload = {"data": [{"images": {"original": {"url": "g.gif"}}}],
                   "pagination": {"count": 50, "total_count": total}}
        worker = GifSearchWorker("kedi", offset=offset)
        worker.results_ready.connect(lambda *args: emitted.append(args))
        with mock.patch.object(media_dialogs, "_giphy_request", return_value=payload) as request, \
                mock.patch.object(media_dialogs, "_tenor_search", return_value=[("t", "m")]) as tenor:
            worker.run()
        return emitted[0], request, tenor

    def test_first_page_searches_raw_query_and_tenor(self):
        (_, results, _, next_offset), request, tenor = self.run_worker(0)
        self.assertEqual(request.call_args_list[0].kwargs["q"], "kedi")
        self.assertIn(("t", "m"), results)
        self.assertEqual(next_offset, 50)
        tenor.assert_called_once()

    def test_later_page_uses_giphy_offset_and_detects_end(self):
        (_, _, _, next_offset), request, tenor = self.run_worker(100)
        self.assertEqual(request.call_args.kwargs["offset"], 100)
        self.assertIsNone(next_offset)
        tenor.assert_not_called()


class IconTests(unittest.TestCase):
    def test_variant_icons_render(self):
        for method in (AuraIconFactory.icon_pen_pencil, AuraIconFactory.icon_pen_fountain,
                       AuraIconFactory.icon_pen_brush, AuraIconFactory.icon_marker):
            self.assertFalse(method("#0284c7").pixmap(24, 24).toImage().isNull())


if __name__ == "__main__":
    unittest.main()
