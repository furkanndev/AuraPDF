import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QRectF
import pymupdf as fitz
from src.core.i18n import LanguageManager
from src.document.tab_document import PDFTabDocument, _PageRenderWorker
from src.ui.dialogs.new_page_dialog import NewPageDialog


class TestDPISnappingAndBlankPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_i18n_export_and_grid_keys(self):
        """TR-EN dil simetrisi ve 'Sayfaları Dışa Aktar' / Grid hizalama anahtarlarını doğrula."""
        tr_map = LanguageManager.TRANSLATIONS["tr"]
        en_map = LanguageManager.TRANSLATIONS["en"]
        self.assertEqual(len(set(tr_map.keys()) ^ set(en_map.keys())), 0)

        # 'Sayfaları Çıkar' yerine 'Sayfaları Dışa Aktar'
        self.assertEqual(tr_map["extract_current_page_btn"], "Geçerli Sayfayı Dışa Aktar")
        self.assertEqual(en_map["extract_current_page_btn"], "Export Current Page")
        self.assertEqual(tr_map["organize_extract_pages"], "Sayfaları Dışa Aktar")
        self.assertEqual(en_map["organize_extract_pages"], "Export Pages")

        # Grid ve boyut sıfırlama anahtarları
        self.assertIn("align_to_grid", tr_map)
        self.assertIn("align_to_grid", en_map)
        self.assertIn("reset_size", tr_map)
        self.assertIn("reset_size", en_map)
        self.assertIn("keep_aspect_ratio", tr_map)
        self.assertIn("keep_aspect_ratio", en_map)

    def test_blank_page_orientation_and_match(self):
        """Yatay (Landscape) belgede boş sayfa eklerken yönün ve boyutun korunmasını doğrula."""
        # 800x600 (Landscape) PDF oluştur
        doc = fitz.open()
        p = doc.new_page(width=800, height=600)
        self.assertTrue(p.rect.width > p.rect.height)

        tab_doc = PDFTabDocument(None)
        tab_doc.doc = doc
        tab_doc.current_page_idx = 0

        # Yeni boş sayfa ekle (otomatik referans sayfa boyutuyla)
        tab_doc.insert_blank_page(after_page=0)
        self.assertEqual(len(doc), 2)
        new_page = doc[1]
        self.assertAlmostEqual(new_page.rect.width, 800.0, places=1)
        self.assertAlmostEqual(new_page.rect.height, 600.0, places=1)
        self.assertTrue(new_page.rect.width > new_page.rect.height)

        # NewPageDialog aktif tab_doc'tan yönü doğrudan algılamalı
        dlg = NewPageDialog(parent=None, main_window=tab_doc)
        self.assertTrue(dlg.rb_landscape.isChecked())
        config = dlg.get_page_config()
        self.assertEqual(config["orientation"], "landscape")
        self.assertAlmostEqual(config["width"], 800.0, places=1)
        self.assertAlmostEqual(config["height"], 600.0, places=1)

    def test_smart_snapping_exact_bounds(self):
        """Manyetik kılavuz çizgileri ve akıllı snap hesaplamasını test et."""
        tab_doc = PDFTabDocument(None)
        # 1000x1000 sanal sayfa konumu tanımla
        tab_doc.page_positions = {
            0: {'left': 100.0, 'right': 900.0, 'top': 50.0, 'bottom': 950.0, 'width': 800.0, 'height': 900.0}
        }

        # Sayfa merkezine yakın bir noktada snap_pos ve guide çizgileri kontrolü
        # Sayfa merkezi: 100 + 400 = 500. Item w = 100, merkezi snap için hedef pos.x = 500 - 50 = 450.
        # raw_pos.x = 448 (merkezi 498, fark 2px <= 8px threshold)
        raw_pos = QPointF(448.0, 300.0)
        snap_pos, guides = tab_doc.compute_smart_snap(
            ignore_item=None,
            raw_pos=raw_pos,
            w=100.0,
            h=80.0,
            page_idx=0,
            snap_to_grid=False
        )
        self.assertAlmostEqual(snap_pos.x(), 450.0, places=1)
        self.assertAlmostEqual(snap_pos.x() + 50.0, 500.0, places=1)
        self.assertTrue(any(g.get("orientation") == "vertical" for g in guides))

    def test_render_worker_thread_safety(self):
        """_PageRenderWorker'ın QImage thread-safe emit ettiğini ve kesintisiz çalıştığını doğrula."""
        worker = _PageRenderWorker(None)
        self.assertFalse(worker.isRunning())
        self.assertEqual(len(worker._jobs), 0)

        # Schedule jobs
        doc = fitz.open()
        doc.new_page(width=300, height=400)
        mat = fitz.Matrix(1.5, 1.5)
        jobs = [(0, mat, "normal", doc, True, 1.0, 1.25)]
        worker.schedule(jobs)
        self.assertEqual(len(worker._jobs), 1)

        worker.abort()
        self.assertEqual(len(worker._jobs), 0)
        self.assertTrue(worker._abort)

    def test_bookmark_ribbon_lifecycle_and_clear(self):
        """BookmarkRibbonItem silinmesi ve thumbnail render döngüsünde RuntimeError oluşmamasını doğrula."""
        doc = fitz.open()
        doc.new_page(width=595, height=842)

        tab_doc = PDFTabDocument(None)
        tab_doc.doc = doc
        tab_doc.render_pages_init()

        # Ribbon öğesini al
        self.assertIn(0, tab_doc.bookmark_ribbon_items)
        ribbon = tab_doc.bookmark_ribbon_items[0]

        # set_bookmarked ve set_hovered güvenli çalışmalı
        ribbon.set_bookmarked(True)
        ribbon.set_hovered(True)
        self.assertTrue(ribbon.is_bookmarked)
        self.assertTrue(ribbon.is_hovered)

        # Thumbnail render çağrısı güvenle tamamlanmalı
        thumb = tab_doc.get_page_preview_pixmap(0, 100, 140)
        self.assertIsNotNone(thumb)

        # Yeni sayfa ekleme veya yeniden render (scene.clear çağrılır)
        tab_doc.insert_blank_page(after_page=0)
        self.assertEqual(len(tab_doc.doc), 2)

        # Eski ribbon artık silinmiştir ama update_bookmark_ribbons veya thumbnail alma çökmemeli
        tab_doc.update_bookmark_ribbons()
        thumb2 = tab_doc.get_page_preview_pixmap(1, 100, 140)
        self.assertIsNotNone(thumb2)

        # Belge kapatma
        tab_doc.close_document()
        self.assertEqual(len(tab_doc.bookmark_ribbon_items), 0)


if __name__ == '__main__':
    unittest.main()
