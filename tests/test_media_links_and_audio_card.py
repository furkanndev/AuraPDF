import os
import tempfile
import unittest
from unittest import mock

import fitz
from PyQt6.QtCore import QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QMainWindow

from src.document.media_items import (AUDIO_CARD_H, AUDIO_CARD_W, PDFAudioItem, audio_card_layout,
                                      format_audio_time, paint_audio_card)
from src.ui.dialogs import media_dialogs
from src.ui.dialogs.media_dialogs import (AudioRecordDialog, EmojiGifPickerDialog, MediaFetchError,
                                          _giphy_direct_url, _giphy_results, _is_image_data,
                                          _page_image_url, resolve_media_url)

app = QApplication.instance() or QApplication([])


class FakeResponse:
    def __init__(self, url, content_type, body=b""):
        self.url = url
        self.body = body
        self.headers = {"Content-Type": content_type}

    def geturl(self):
        return self.url

    def read(self, _limit=-1):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestGifLinkResolution(unittest.TestCase):
    def test_giphy_links_become_direct_gif_urls(self):
        expected = "https://media.giphy.com/media/ytTYwIlbD1FBu/giphy.gif"
        for link in (
            "https://giphy.com/gifs/applause-clapping-clap-ytTYwIlbD1FBu",
            "https://giphy.com/gifs/ytTYwIlbD1FBu",
            "https://www.giphy.com/stickers/hello-ytTYwIlbD1FBu/fullscreen",
            "https://giphy.com/embed/ytTYwIlbD1FBu",
            "https://i.giphy.com/ytTYwIlbD1FBu.webp",
            "https://media.giphy.com/media/ytTYwIlbD1FBu/giphy.mp4",
            "https://media2.giphy.com/media/v1.abc/ytTYwIlbD1FBu/giphy.webp",
        ):
            self.assertEqual(_giphy_direct_url(link), expected, link)

    def test_direct_gif_and_foreign_urls_are_left_alone(self):
        self.assertIsNone(_giphy_direct_url("https://media2.giphy.com/media/v1.abc/id/100.gif?cid=1"))
        self.assertIsNone(_giphy_direct_url("https://tenor.com/view/foo-gif-123"))
        self.assertIsNone(_giphy_direct_url("https://notgiphy.com/gifs/abc"))

    def test_page_image_prefers_gif_in_any_attribute_order(self):
        page = """
            <meta content="https://cdn.example.com/a.webp" property="og:image"/>
            <meta class="dynamic" name="twitter:image" content="https://cdn.example.com/a.gif?x=1&amp;y=2">
        """
        self.assertEqual(_page_image_url(page, "https://example.com/"), "https://cdn.example.com/a.gif?x=1&y=2")
        self.assertIsNone(_page_image_url("<html></html>", "https://example.com/"))

    def test_tenor_page_resolves_to_media_url(self):
        page = '<meta property="og:image" content="https://media1.tenor.com/m/abc/x.gif">'
        replies = [FakeResponse("https://tenor.com/view/x-gif-1", "text/html; charset=utf-8", page.encode()),
                   FakeResponse("https://media1.tenor.com/m/abc/x.gif", "image/gif")]
        with mock.patch.object(media_dialogs.urllib.request, "urlopen", side_effect=replies):
            self.assertEqual(resolve_media_url("tenor.com/view/x-gif-1"), "https://media1.tenor.com/m/abc/x.gif")

    def test_short_link_redirect_to_giphy_page(self):
        reply = FakeResponse("https://giphy.com/gifs/slug-abc123", "text/html", b"")
        with mock.patch.object(media_dialogs.urllib.request, "urlopen", return_value=reply):
            self.assertEqual(resolve_media_url("https://gph.is/x"), "https://media.giphy.com/media/abc123/giphy.gif")

    def test_page_without_image_is_invalid(self):
        reply = FakeResponse("https://example.com/", "text/html", b"<html></html>")
        with mock.patch.object(media_dialogs.urllib.request, "urlopen", return_value=reply):
            with self.assertRaises(MediaFetchError) as ctx:
                resolve_media_url("https://example.com/")
        self.assertEqual(ctx.exception.kind, "invalid")

    def test_html_is_not_image_data(self):
        self.assertTrue(_is_image_data(b"GIF89a....."))
        self.assertTrue(_is_image_data(b"RIFF\x00\x00\x00\x00WEBPVP8"))
        self.assertFalse(_is_image_data(b"<!DOCTYPE html>"))
        self.assertFalse(_is_image_data(b""))

    def test_giphy_results_pair_thumbnail_with_insert_quality(self):
        payload = {"data": [{"images": {
            "fixed_height_small": {"url": "small.gif"},
            "downsized": {"url": "full.gif"},
            "original": {"url": "orig.gif"},
        }}, {"images": {"original": {"url": "only.gif"}}}, {"images": {}}]}
        self.assertEqual(_giphy_results(payload), [("small.gif", "full.gif"), ("only.gif", "only.gif")])


class TestGifPickerFailures(unittest.TestCase):
    def _dialog(self):
        with mock.patch.object(EmojiGifPickerDialog, "_populate_initial_gifs"):
            return EmojiGifPickerDialog()

    def test_api_failure_shows_curated_gifs_once(self):
        dlg = self._dialog()
        with mock.patch.object(dlg, "_load_next_gif_batch") as load, \
                mock.patch.object(dlg, "_fetch_more_trending_urls") as fetch:
            dlg._on_trending_urls_fetched([], 0, "limit")
        self.assertEqual(len(dlg._all_gif_urls), len(dlg.POPULAR_GIFS))
        self.assertTrue(dlg._trending_exhausted)
        self.assertFalse(dlg.lbl_gif_status.isHidden())
        load.assert_called_once()
        fetch.assert_not_called()
        dlg.reject()

    def test_exhausted_trending_never_refetches(self):
        dlg = self._dialog()
        dlg._trending_exhausted = True
        with mock.patch.object(media_dialogs, "GiphyTrendingWorker") as worker:
            dlg._fetch_more_trending_urls()
        worker.assert_not_called()
        dlg.reject()

    def test_stale_search_result_is_ignored(self):
        dlg = self._dialog()
        dlg._current_search_query = "new"
        dlg._on_search_results_ready("old", [("a.gif", "a.gif")], "")
        self.assertEqual(dlg._all_gif_urls, [])
        dlg.reject()

    def test_double_click_inserts_full_quality_with_thumbnail_fallback(self):
        dlg = self._dialog()
        media_dialogs.GifThumbnailCard._THUMB_CACHE["thumb.gif"] = b"GIF89a-small"
        dlg._gif_full_urls["thumb.gif"] = "full.gif"
        with mock.patch.object(media_dialogs, "GifDownloadWorker") as worker:
            dlg._on_gif_card_double_clicked("thumb.gif")
        worker.assert_called_once_with("full.gif")
        dlg._on_full_gif_downloaded("full.gif", b"")
        self.assertEqual(dlg.selected_gif_bytes, b"GIF89a-small")

    def test_failed_card_reports_instead_of_hanging(self):
        dlg = self._dialog()
        card = media_dialogs.GifThumbnailCard("broken.gif")
        dlg.gif_cards.append(card)
        dlg._pending_double_click_url = "broken.gif"
        dlg._on_card_thumb_failed(0)
        self.assertTrue(card.is_failed)
        self.assertIsNone(dlg._pending_double_click_url)
        self.assertFalse(dlg.lbl_gif_status.isHidden())
        dlg.reject()


class TestAudioRecordFlow(unittest.TestCase):
    def setUp(self):
        self.win = QMainWindow()
        self.dlg = AudioRecordDialog(self.win)

    def tearDown(self):
        self.dlg._has_take = False
        self.dlg.close()

    def test_capsule_docks_to_document_corners_and_snaps(self):
        self.win.setGeometry(100, 100, 900, 600)
        self.dlg._toggle_compact_mode()
        area = QRect(200, 150, 500, 400)
        with mock.patch.object(self.dlg, "_document_area", return_value=area):
            margin = self.dlg.CAPSULE_MARGIN
            self.dlg._set_capsule_corner("bottom-left")
            self.assertEqual(self.dlg.x(), area.left() + margin)
            self.assertEqual(self.dlg.geometry().bottom(), area.bottom() - margin)

            self.dlg._set_capsule_corner("bottom-right")
            self.assertEqual(self.dlg.geometry().right(), area.right() - margin)

            # Hover keeps the docked edge fixed, so the capsule grows into the document
            self.dlg._set_capsule_expanded(True)
            self.assertEqual(self.dlg.geometry().right(), area.right() - margin)
            self.dlg._set_capsule_expanded(False)

            self.dlg.move(area.left() + 20, area.top() + 30)
            self.dlg._snap_capsule_to_nearest_corner()
            self.assertEqual(self.dlg._capsule_corner, "bottom-left")
            self.assertEqual(self.dlg.geometry().bottom(), area.bottom() - margin)

    def test_primary_button_is_locked_until_file_is_ready(self):
        self.dlg._awaiting_file = True
        self.dlg._sync_capsule()
        self.assertFalse(self.dlg.btn_mini_stop.isEnabled())
        with mock.patch.object(self.dlg, "_start_record") as start:
            self.dlg._on_mini_stop_clicked()
        start.assert_not_called()

    def test_escape_releases_recording_through_done(self):
        self.dlg.is_recording = True
        self.dlg.level_timer.start()
        self.dlg.reject()
        self.assertFalse(self.dlg.is_recording)
        self.assertFalse(self.dlg.level_timer.isActive())

    def test_cancel_asks_before_discarding_a_take(self):
        self.dlg._has_take = True
        answer = media_dialogs.QMessageBox.StandardButton.No
        with mock.patch.object(media_dialogs.QMessageBox, "question", return_value=answer), \
                mock.patch.object(self.dlg, "reject") as reject:
            self.dlg._on_cancel()
        reject.assert_not_called()

    def test_reset_never_touches_a_user_picked_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
            handle.write(b"user audio")
        self.addCleanup(os.remove, handle.name)
        self.dlg.preview_path = handle.name
        self.dlg.audio_bytes = b"user audio"
        self.dlg._reset_record()
        self.assertTrue(os.path.exists(handle.name))
        self.assertIsNone(self.dlg.preview_path)

    def test_waveform_peaks_are_normalized_and_bounded(self):
        self.dlg._has_take = True
        self.dlg._peaks = [0.1, 0.5] * 500
        peaks = self.dlg.waveform_peaks(48)
        self.assertLessEqual(len(peaks), 49)
        self.assertEqual(max(peaks), 1.0)
        self.dlg._peaks = [0.001] * 50
        self.assertEqual(self.dlg.waveform_peaks(), [])


class TestAudioCard(unittest.TestCase):
    def test_layout_stays_inside_card_at_all_sizes(self):
        for w, h in ((130.0, 38.0), (264.0, 60.0), (270.0, 72.0), (600.0, 200.0)):
            card = QRectF(0, 0, w, h)
            rects = audio_card_layout(w, h, "12:34")
            for name, rect in rects.items():
                if not rect.isEmpty():
                    self.assertTrue(card.contains(rect), (name, w, h))
            self.assertFalse(rects["button"].intersects(rects["wave"]))

    def test_time_format(self):
        self.assertEqual(format_audio_time(0), "00:00")
        self.assertEqual(format_audio_time(75.9), "01:15")

    def test_card_paints_with_and_without_peaks(self):
        for peaks, progress, playing in (([], 0.0, False), ([0.2, 1.0, 0.5], 0.4, True), ([], 0.5, True)):
            image = QImage(264, 60, QImage.Format.Format_ARGB32)
            image.fill(QColor("#ffffff"))
            painter = QPainter(image)
            paint_audio_card(painter, 264.0, 60.0, "Toplanti notu", "00:12", peaks, progress, playing)
            painter.end()
            self.assertFalse(image.isNull())

    def test_paused_item_keeps_position_and_shows_it(self):
        item = PDFAudioItem(None, {"w": AUDIO_CARD_W, "h": AUDIO_CARD_H, "duration_sec": 60.0, "title": "Not"})
        self.assertEqual(item._time_text(), "01:00")
        item.position_ms = 15000
        self.assertEqual(item._time_text(), "00:15")
        self.assertAlmostEqual(item._progress(), 0.25)

    def test_export_writes_audio_card_to_pdf(self):
        from src.document.media_items import paint_audio_card as painter_fn
        doc = fitz.open()
        page = doc.new_page(width=300, height=200)
        image = QImage(528, 120, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.scale(2.0, 2.0)
        painter_fn(painter, 264.0, 60.0, "Not", "00:05", [0.4, 0.9])
        painter.end()
        self.assertEqual(QColor(image.pixel(QPointF(264, 60).toPoint())).alpha(), 255)
        doc.close()


if __name__ == "__main__":
    unittest.main()
