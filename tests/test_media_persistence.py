import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPainterPath
from PyQt6.QtCore import QPointF, Qt
import pymupdf as fitz

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.viewer import AuraPDFViewer
from src.document.media_items import PDFTableItem, PDFResizableImageItem
from src.ui.widgets import EditableInlineTextItem


class TestMediaPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setQuitOnLastWindowClosed(False)

    def test_save_and_reload_drawings_and_media(self):
        viewer = AuraPDFViewer()
        viewer.show()

        # Step 1: Create a blank document
        viewer.new_blank_document("blank")
        tab_doc = viewer.get_current_tab_doc()
        self.assertIsNotNone(tab_doc)
        self.assertEqual(len(tab_doc.doc), 1)

        # Step 2: Add pen drawing
        pen_item = {
            "type": "polyline",
            "page": 0,
            "points": [[100.0, 100.0], [150.0, 120.0], [200.0, 100.0]],
            "color": (0.0, 0.0, 1.0),
            "width": 2.5,
            "alpha": 1.0,
            "line_style": "solid",
            "pen_type": "solid"
        }
        tab_doc.drawings.append(pen_item)
        tab_doc.restore_drawing_item(pen_item)

        # Step 3: Add highlighter markup
        hl_item = {
            "type": "text_markup",
            "page": 0,
            "markup_type": "highlight",
            "rects": [[50.0, 80.0, 250.0, 100.0]],
            "color": (1.0, 1.0, 0.0),
            "alpha": 0.4,
            "width": 2.0
        }
        tab_doc.drawings.append(hl_item)
        tab_doc.restore_drawing_item(hl_item)

        # Step 4: Add image (create small 20x20 PNG)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
        img_bytes = pix.tobytes("png")
        tab_doc.add_image_media(img_bytes, title="Test Image", page_idx=0, pos=QPointF(200, 300), default_w=80.0, default_h=80.0)

        # Step 5: Add table (2 rows, 2 cols)
        tab_doc.add_table(rows=2, cols=2, has_header=True, page_idx=0, pos=QPointF(100, 400))

        # Step 6: Add inline text box
        text_item = {
            "type": "text",
            "page": 0,
            "x": 80.0,
            "y": 200.0,
            "w": 150.0,
            "h": 30.0,
            "text": "Editable Test Text Box",
            "font_size": 16,
            "color": QColor(255, 0, 0)
        }
        tab_doc.drawings.append(text_item)
        tab_doc.render_text_item(text_item)

        test_file = os.path.abspath("test_media_persist.pdf")
        with open(test_file, "wb") as f:
            f.write(tab_doc.doc.tobytes())

        try:
            # Step 7: Save to disk
            tab_doc.file_path = test_file
            viewer.save_pdf()

            self.assertTrue(os.path.exists(test_file))
            print("[PASS] Document saved successfully to", test_file)

            # Step 8: Reopen saved document
            viewer.add_pdf_tab(test_file)
            tab_doc2 = viewer.get_current_tab_doc()
            self.assertIsNotNone(tab_doc2)

            print(f"[INFO] Reloaded drawings count: {len(tab_doc2.drawings)}")
            types_loaded = [d.get("type") for d in tab_doc2.drawings]
            print(f"[INFO] Loaded drawing types: {types_loaded}")

            # Verify that all 5 types were restored!
            self.assertIn("polyline", types_loaded)
            self.assertIn("text_markup", types_loaded)
            self.assertIn("image", types_loaded)
            self.assertIn("table", types_loaded)
            self.assertIn("text", types_loaded)

            # Check that item_refs are live and interactive on scene
            table_rec = next(d for d in tab_doc2.drawings if d["type"] == "table")
            self.assertIsNotNone(table_rec.get("item_ref"))
            self.assertIsInstance(table_rec["item_ref"], PDFTableItem)

            img_rec = next(d for d in tab_doc2.drawings if d["type"] == "image")
            self.assertIsNotNone(img_rec.get("item_ref"))
            self.assertIsInstance(img_rec["item_ref"], PDFResizableImageItem)

            text_rec = next(d for d in tab_doc2.drawings if d["type"] == "text")
            self.assertIsNotNone(text_rec.get("item_ref"))
            self.assertIsInstance(text_rec["item_ref"], EditableInlineTextItem)
            self.assertEqual(text_rec["item_ref"].toPlainText(), "Editable Test Text Box")

            # Step 9: Test editing text
            text_rec["item_ref"].setPlainText("Updated text in box")
            self.assertEqual(text_rec["item_ref"].toPlainText(), "Updated text in box")

            # Step 10: Test selecting and deleting table
            table_item = table_rec["item_ref"]
            table_item.setSelected(True)
            self.assertTrue(table_item.isSelected())
            tab_doc2.delete_selected_items()
            self.assertNotIn(table_rec, tab_doc2.drawings)
            print("[PASS] Table selected and deleted successfully!")

            # Step 11: Test selecting and deleting image
            img_item = img_rec["item_ref"]
            img_item.setSelected(True)
            self.assertTrue(img_item.isSelected())
            tab_doc2.delete_selected_items()
            self.assertNotIn(img_rec, tab_doc2.drawings)
            print("[PASS] Image selected and deleted successfully!")

            # Step 12: Test selecting and deleting text box
            txt_item = text_rec["item_ref"]
            txt_item.setSelected(True)
            tab_doc2.delete_selected_items()
            self.assertNotIn(text_rec, tab_doc2.drawings)
            print("[PASS] Text box selected and deleted successfully!")

            # Step 13: Test eraser erasing pen stroke
            tab_doc2.erase_at(QPointF(150, 120))
            # Either partially erased or fully erased
            print("[PASS] Eraser executed on pen stroke without crash!")

            # Clean up
            for idx in range(viewer.tab_widget.count()):
                w = viewer.tab_widget.widget(idx)
                if hasattr(w, 'set_modified'):
                    w.set_modified(False)
            viewer.hide()

        finally:
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception:
                    pass


if __name__ == '__main__':
    unittest.main()
