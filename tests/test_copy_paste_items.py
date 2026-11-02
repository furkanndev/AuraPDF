import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtCore import QPointF, Qt, QByteArray, QBuffer
import pymupdf as fitz

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.viewer import AuraPDFViewer
from src.document.media_items import PDFTableItem, PDFResizableImageItem, PDFAudioItem
from src.ui.widgets import EditableInlineTextItem


class TestCopyPasteItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.viewer = AuraPDFViewer()
        self.viewer.new_blank_document("blank")
        self.tab_doc = self.viewer.get_current_tab_doc()
        # Create a second page
        self.tab_doc.doc.new_page()
        self.tab_doc.render_all_pages()

    def tearDown(self):
        try:
            if hasattr(self, 'tab_doc') and self.tab_doc:
                self.tab_doc.is_modified = False
            for idx in range(self.viewer.tab_widget.count()):
                w = self.viewer.tab_widget.widget(idx)
                if hasattr(w, 'is_modified'):
                    w.is_modified = False
            self.viewer.close()
        except Exception:
            pass

    def test_text_box_copy_paste_across_pages(self):
        """Metin kutusunun başka sayfaya birebir kopyalanıp yapıştırılmasını test eder."""
        tab = self.tab_doc

        # Sayfa 0'a zengin metin kutusu ekle
        record = {
            "type": "text",
            "page": 0,
            "x": 60.0,
            "y": 80.0,
            "w": 180.0,
            "h": 50.0,
            "text": "Kopyalanacak Test Metni",
            "font_family": "Arial",
            "font_size": 16,
            "color": QColor(30, 144, 255),
            "bg_color": "#fef08a",
            "bold": True,
            "italic": False,
            "underline": False,
            "alignment": "center"
        }
        tab.drawings.append(record)
        tab.render_text_item(record)
        item = record.get("item_ref")
        self.assertIsNotNone(item)
        self.assertIsInstance(item, EditableInlineTextItem)

        # 1. Metin kutusunu kopyala
        copied = tab.copy_selected_item(item)
        self.assertTrue(copied)
        self.assertIsNotNone(tab._clipboard_item_data)
        self.assertEqual(tab._clipboard_item_data["type"], "text")
        self.assertIn("Test Metni", tab._clipboard_item_data["text"])

        # 2. Sayfa 1'e yapıştır (birebir aynı koordinatlarla)
        pasted = tab.paste_copied_item(page_idx=1)
        self.assertTrue(pasted)

        # Sayfa 1'deki yapıştırılan öğeyi bul
        page1_items = [d for d in tab.drawings if d.get("page") == 1]
        self.assertEqual(len(page1_items), 1)
        pasted_rec = page1_items[0]

        # Birebir koordinat ve stil kontrolü
        self.assertAlmostEqual(pasted_rec["x"], 60.0, places=1)
        self.assertAlmostEqual(pasted_rec["y"], 80.0, places=1)
        self.assertEqual(pasted_rec["text"], "Kopyalanacak Test Metni")
        self.assertEqual(pasted_rec["font_size"], 16)
        self.assertEqual(pasted_rec["bg_color"], "#fef08a")

        # Sahnedeki öğe kontrolü
        pasted_item = pasted_rec.get("item_ref")
        self.assertIsNotNone(pasted_item)
        self.assertIsInstance(pasted_item, EditableInlineTextItem)
        self.assertEqual(pasted_item.page_idx, 1)

    def test_same_page_paste_offset(self):
        """Aynı sayfaya yapıştırıldığında +15pt öteleme uygulanmasını test eder."""
        tab = self.tab_doc
        record = {
            "type": "text", "page": 0, "x": 50.0, "y": 50.0, "w": 100.0, "h": 40.0,
            "text": "Aynı Sayfa Metni", "font_size": 12, "color": QColor(0, 0, 0)
        }
        tab.drawings.append(record)
        tab.render_text_item(record)

        tab.copy_selected_item(record["item_ref"])
        tab.paste_copied_item(page_idx=0)

        page0_items = [d for d in tab.drawings if d.get("page") == 0]
        self.assertEqual(len(page0_items), 2)
        second_item = page0_items[1]
        self.assertAlmostEqual(second_item["x"], 65.0, places=1)  # 50 + 15
        self.assertAlmostEqual(second_item["y"], 65.0, places=1)  # 50 + 15

    def test_table_copy_paste_across_pages(self):
        """Tablonun tüm hücreleri, satır/sütun yapısıyla başka sayfaya kopyalanmasını test eder."""
        tab = self.tab_doc

        cell_data = [
            ["Başlık 1", "Başlık 2", "Başlık 3"],
            ["Veri A", "Veri B", "Veri C"],
            ["100", "200", "300"]
        ]
        table_rec = {
            "type": "table",
            "page": 0,
            "x": 70.0,
            "y": 120.0,
            "w": 300.0,
            "h": 150.0,
            "rows": 3,
            "cols": 3,
            "cell_data": cell_data,
            "cell_alignments": [["center"] * 3 for _ in range(3)],
            "border_color": "#334155",
            "bg_color": "#f8fafc",
            "header_bg_color": "#e2e8f0"
        }
        tab.drawings.append(table_rec)
        tab.render_table_item(table_rec)
        tbl_item = table_rec.get("item_ref")
        self.assertIsInstance(tbl_item, PDFTableItem)

        # Tabloyu kopyala
        copied = tab.copy_selected_item(tbl_item)
        self.assertTrue(copied)
        self.assertEqual(tab._clipboard_item_data["type"], "table")
        self.assertEqual(tab._clipboard_item_data["rows"], 3)
        self.assertEqual(tab._clipboard_item_data["cols"], 3)

        # Sayfa 1'e yapıştır
        tab.paste_copied_item(page_idx=1)
        pasted_tables = [d for d in tab.drawings if d.get("page") == 1 and d.get("type") == "table"]
        self.assertEqual(len(pasted_tables), 1)
        p_tbl = pasted_tables[0]

        # Birebir hücre verileri ve koordinatlar
        self.assertAlmostEqual(p_tbl["x"], 70.0, places=1)
        self.assertAlmostEqual(p_tbl["y"], 120.0, places=1)
        self.assertEqual(p_tbl["rows"], 3)
        self.assertEqual(p_tbl["cols"], 3)
        self.assertEqual(p_tbl["cell_data"][0][0], "Başlık 1")
        self.assertEqual(p_tbl["cell_data"][1][1], "Veri B")
        self.assertEqual(p_tbl["cell_data"][2][2], "300")
        self.assertIsInstance(p_tbl.get("item_ref"), PDFTableItem)

    def test_image_and_gif_copy_paste_across_pages(self):
        """Resim ve hareketli GIF öğelerinin başka sayfaya birebir kopyalanmasını test eder."""
        tab = self.tab_doc

        # Sahte bir PNG görüntüsü oluştur
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("red"))
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buf, "PNG")
        png_bytes = bytes(ba.data())

        img_rec = {
            "type": "image",
            "page": 0,
            "x": 45.0,
            "y": 95.0,
            "w": 120.0,
            "h": 120.0,
            "image_bytes": png_bytes,
            "is_gif": False,
            "title": "Test Resmi"
        }
        tab.drawings.append(img_rec)
        tab.render_image_item(img_rec)
        img_item = img_rec.get("item_ref")
        self.assertIsInstance(img_item, PDFResizableImageItem)

        # Kopyala & Sayfa 1'e yapıştır
        tab.copy_selected_item(img_item)
        tab.paste_copied_item(page_idx=1)

        pasted_imgs = [d for d in tab.drawings if d.get("page") == 1 and d.get("type") == "image"]
        self.assertEqual(len(pasted_imgs), 1)
        p_img = pasted_imgs[0]
        self.assertAlmostEqual(p_img["x"], 45.0, places=1)
        self.assertAlmostEqual(p_img["y"], 95.0, places=1)
        self.assertEqual(p_img["image_bytes"], png_bytes)
        self.assertIsInstance(p_img.get("item_ref"), PDFResizableImageItem)

        # GIF testi: GIF başlığı içeren sahte veri
        gif_header = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        gif_rec = {
            "type": "image",
            "page": 0,
            "x": 80.0,
            "y": 150.0,
            "w": 80.0,
            "h": 80.0,
            "image_bytes": gif_header,
            "is_gif": True,
            "title": "Test GIF"
        }
        tab.drawings.append(gif_rec)
        tab.render_image_item(gif_rec)
        gif_item = gif_rec.get("item_ref")

        tab.copy_selected_item(gif_item)
        self.assertTrue(tab._clipboard_item_data.get("is_gif"))
        tab.paste_copied_item(page_idx=1)

        pasted_gifs = [d for d in tab.drawings if d.get("page") == 1 and d.get("is_gif")]
        self.assertEqual(len(pasted_gifs), 1)
        self.assertEqual(pasted_gifs[0]["image_bytes"], gif_header)

    def test_audio_copy_paste_across_pages(self):
        """Ses kaydı / ses dosyası kartının başka sayfaya birebir kopyalanmasını test eder."""
        tab = self.tab_doc

        fake_audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00#TSSE\x00\x00\x00\x0f\x00\x00\x03Lavf60.16.100"
        audio_rec = {
            "type": "audio",
            "page": 0,
            "x": 100.0,
            "y": 200.0,
            "w": 180.0,
            "h": 48.0,
            "audio_bytes": fake_audio_bytes,
            "card_title": "Ses Kaydı 01",
            "duration": 42.5,
            "waveform_peaks": [0.2, 0.5, 0.8, 0.4, 0.9, 0.3],
            "audio_format": "mp3"
        }
        tab.drawings.append(audio_rec)
        tab.render_audio_item(audio_rec)
        aud_item = audio_rec.get("item_ref")
        self.assertIsInstance(aud_item, PDFAudioItem)

        # Kopyala & Sayfa 1'e yapıştır
        tab.copy_selected_item(aud_item)
        tab.paste_copied_item(page_idx=1)

        pasted_auds = [d for d in tab.drawings if d.get("page") == 1 and d.get("type") == "audio"]
        self.assertEqual(len(pasted_auds), 1)
        p_aud = pasted_auds[0]

        self.assertAlmostEqual(p_aud["x"], 100.0, places=1)
        self.assertAlmostEqual(p_aud["y"], 200.0, places=1)
        self.assertEqual(p_aud["card_title"], "Ses Kaydı 01")
        self.assertEqual(p_aud["duration"], 42.5)
        self.assertEqual(p_aud["audio_bytes"], fake_audio_bytes)
        self.assertEqual(p_aud["waveform_peaks"], [0.2, 0.5, 0.8, 0.4, 0.9, 0.3])
        self.assertIsInstance(p_aud.get("item_ref"), PDFAudioItem)

    def test_undo_redo_copy_paste(self):
        """Yapıştırılan öğenin Geri Al (Undo) ve İleri Al (Redo) desteğini test eder."""
        tab = self.tab_doc

        rec = {
            "type": "text", "page": 0, "x": 50.0, "y": 50.0, "w": 100.0, "h": 40.0,
            "text": "Undo Redo Metni", "font_size": 14, "color": QColor(0, 0, 0)
        }
        tab.drawings.append(rec)
        tab.render_text_item(rec)

        tab.copy_selected_item(rec["item_ref"])
        tab.paste_copied_item(page_idx=1)

        self.assertEqual(len([d for d in tab.drawings if d.get("page") == 1]), 1)

        # Undo
        tab.undo()
        self.assertEqual(len([d for d in tab.drawings if d.get("page") == 1]), 0)

        # Redo
        tab.redo()
        self.assertEqual(len([d for d in tab.drawings if d.get("page") == 1]), 1)


if __name__ == '__main__':
    unittest.main()
