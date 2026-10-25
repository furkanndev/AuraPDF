import unittest
import os
import fitz
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor

from src.core.i18n import LanguageManager
from src.document.media_items import PDFTableItem, PDFAudioItem
from src.ui.dialogs.media_dialogs import TableInsertDialog, MiniAudioWaveformVisualizer, AudioRecordDialog
from src.ui.widgets import EditableInlineTextItem

app = QApplication.instance() or QApplication([])

class TestAudioTableAlignmentExport(unittest.TestCase):
    def test_i18n_zero_diff(self):
        """TR ve EN dil sözlükleri arasında sıfır fark olduğunu teyit eder."""
        tr_keys = set(LanguageManager.TRANSLATIONS['tr'].keys())
        en_keys = set(LanguageManager.TRANSLATIONS['en'].keys())
        self.assertEqual(len(tr_keys - en_keys), 0)
        self.assertEqual(len(en_keys - tr_keys), 0)

    def test_table_item_alignment(self):
        """PDFTableItem alignment set ve align_to_page metodlarının çalıştığını test eder."""
        record = {
            "type": "table",
            "page": 0,
            "x": 50.0,
            "y": 50.0,
            "w": 180.0,
            "h": 80.0,
            "rows": 2,
            "cols": 2,
            "cell_data": [["A", "B"], ["C", "D"]],
            "alignment": "center"
        }
        item = PDFTableItem(None, record)
        self.assertEqual(item.alignment, "center")

        item.set_alignment("right")
        self.assertEqual(item.alignment, "right")
        self.assertEqual(item.record["alignment"], "right")

        item.set_alignment("left")
        self.assertEqual(item.alignment, "left")

    def test_table_item_per_cell_alignment(self):
        """PDFTableItem her hücreye özel hizalama özelliklerinin çalıştığını test eder."""
        record = {
            "type": "table",
            "page": 0,
            "x": 50.0,
            "y": 50.0,
            "w": 180.0,
            "h": 80.0,
            "rows": 2,
            "cols": 2,
            "cell_data": [["A", "B"], ["C", "D"]],
            "alignment": "center"
        }
        item = PDFTableItem(None, record)
        self.assertEqual(item.get_cell_alignment(0, 0), "center")
        self.assertEqual(item.get_cell_alignment(0, 1), "center")

        # Tek hücreyi hizala
        item.set_cell_alignment(0, 0, "left")
        self.assertEqual(item.get_cell_alignment(0, 0), "left")
        self.assertEqual(item.get_cell_alignment(0, 1), "center")

        # Sütunu hizala
        item.set_col_alignment(1, "right")
        self.assertEqual(item.get_cell_alignment(0, 1), "right")
        self.assertEqual(item.get_cell_alignment(1, 1), "right")
        self.assertEqual(item.get_cell_alignment(0, 0), "left")

        # Satır ekleme ve silmede cell_alignments boyutlarının korunduğunu test et
        item.add_row(1)
        self.assertEqual(len(item.cell_alignments), 3)
        self.assertEqual(len(item.cell_alignments[1]), 2)
        item.delete_row(1)
        self.assertEqual(len(item.cell_alignments), 2)

        # Sütun ekleme ve silmede boyutların korunduğunu test et
        item.add_col(1)
        self.assertEqual(len(item.cell_alignments[0]), 3)
        item.delete_col(1)
        self.assertEqual(len(item.cell_alignments[0]), 2)

        # Senkronizasyon kontrolü
        item._sync_record()
        self.assertIn("cell_alignments", item.record)
        self.assertEqual(item.record["cell_alignments"][0][0], "left")

    def test_floating_hud_alignment_qmenu(self):
        """TextFloatingFormatHUD içindeki QMenu ve hizalama menüsünün çökmeden üretildiğini test eder."""
        from src.ui.popups import TextFloatingFormatHUD
        from PyQt6.QtWidgets import QWidget
        parent_w = QWidget()
        hud = TextFloatingFormatHUD(parent_w, None)
        self.assertIsNotNone(hud.btn_align)

    def test_inline_text_font_scaling(self):
        """EditableInlineTextItem fontunun base_render_dpi ile piksel bazlı ölçeklendiğini test eder."""
        class MockTabDoc:
            base_render_dpi = 1.5
            drawings = []
            view = None

        tab_doc = MockTabDoc()
        item = EditableInlineTextItem(tab_doc, 0, QPointF(10, 10), font_family="Arial", font_size=14, text="Test String")
        # fontPixelSize should be 14 * 1.5 = 21
        self.assertEqual(item.font().pixelSize(), 21)

        frags = item.get_fragments()
        self.assertTrue(len(frags) > 0)
        # Should be converted back to 14 pt in fragments
        self.assertAlmostEqual(frags[0][0]["font_size"], 14.0, places=1)

    def test_mini_waveform_visualizer(self):
        """MiniAudioWaveformVisualizer bileşeninin canlı seviyelerle çalıştığını test eder."""
        vis = MiniAudioWaveformVisualizer()
        vis.set_level(0.5, active=True)
        self.assertTrue(vis.is_active)
        self.assertEqual(len(vis.heights), 5)

        vis.set_level(0.0, active=False)
        self.assertFalse(vis.is_active)

    def test_polyline_export_open_stroke(self):
        """Çizgilerin Edge ve harici okuyucularda kapalı çokgen (closed loop) olmamasını test eder."""
        doc = fitz.open()
        page = doc.new_page(width=600, height=800)

        # PyMuPDF shape ile finish(closePath=False)
        shape = page.new_shape()
        shape.draw_polyline([fitz.Point(100, 100), fitz.Point(200, 150), fitz.Point(300, 100)])
        shape.finish(color=(1, 0, 0), width=2.0, closePath=False)
        shape.commit()

        # Doküman byte stream'inde 'h' (closepath) operatörü polyline için OLMAMALIDIR
        stream = page.read_contents().decode("latin1", errors="ignore")
        # Ensure it does not close path
        self.assertNotIn("h S", stream)
        self.assertNotIn("h s", stream)
        doc.close()

if __name__ == "__main__":
    unittest.main()
