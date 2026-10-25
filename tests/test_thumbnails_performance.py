import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint
import pymupdf as fitz

from src.core.i18n import LanguageManager
from src.document.tab_document import PDFTabDocument
from src.ui.modern_views import ModernRightSidebar
from src.ui.widgets import ThumbnailsDock

class MockMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_tab_doc = None
        self.modern_right_sidebar = None
        self.thumbnails_dock = None
        self.organize_workspace = None
        self.dialog_shown = False

    def get_current_tab_doc(self):
        return self.current_tab_doc

    def show_new_page_dialog(self):
        self.dialog_shown = True

class TestThumbnailsPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_sidebar_thumbnails_performance_and_insertion(self):
        # 1. 10 sayfalık örnek belge oluştur (İçindekiler / Yer imleri dahil)
        doc = fitz.open()
        for i in range(10):
            p = doc.new_page(width=595, height=842)
            p.insert_text((50, 50), f"AuraPDF Page {i + 1}")
        doc.set_toc([[1, "Bölüm 1", 1], [1, "Bölüm 2", 5], [1, "Bölüm 3", 9]])

        main_win = MockMainWindow()
        main_win.show()
        tab_doc = PDFTabDocument(file_path=None, main_window=main_win)
        tab_doc.doc = doc
        tab_doc.current_page_idx = 0
        main_win.current_tab_doc = tab_doc

        sidebar = ModernRightSidebar(main_window=main_win)
        main_win.modern_right_sidebar = sidebar
        sidebar.show()
        sidebar.set_panel("thumbnails")
        sidebar.load_thumbnails()

        self.assertTrue(sidebar.is_loaded)
        self.assertEqual(sidebar.list_thumbnails.count(), 10)

        # 2. Kuyruk işleme hız testi (10 sayfa ultra hızlı tamamlanmalı)
        t0 = time.perf_counter()
        iters = 0
        while sidebar._thumb_render_queue and iters < 20:
            sidebar._process_thumb_render_queue()
            iters += 1
        t1 = time.perf_counter()
        elapsed = t1 - t0
        print(f"\n[ModernRightSidebar] 10 pages thumbnail queue duration: {elapsed * 1000:.2f} ms")
        self.assertEqual(len(sidebar._thumb_render_queue), 0)
        self.assertLess(elapsed, 0.5)

        # 3. Yer imi önbelleği doğrulaması
        bms = sidebar.get_bookmarked_pages()
        self.assertIn(0, bms)
        self.assertIn(4, bms)
        self.assertIn(8, bms)
        self.assertIsNotNone(sidebar._bookmarked_pages_cache)

        # Fare hareketi sırasında TOC C-fonksiyonunun tekrar çağrılmadığını doğrula
        toc_call_count = 0
        orig_get_toc = tab_doc.doc.get_toc
        def counted_get_toc(*args, **kwargs):
            nonlocal toc_call_count
            toc_call_count += 1
            return orig_get_toc(*args, **kwargs)
        tab_doc.doc.get_toc = counted_get_toc

        for y in range(50):
            sidebar._is_pos_on_bookmark_ribbon(QPoint(50, y * 5))

        self.assertEqual(toc_call_count, 0)

        # 4. Sayfa ekleme ve PDF ekleme testleri
        sidebar._on_add_blank_page_clicked(after_page=3)
        self.assertEqual(tab_doc.current_page_idx, 3)
        self.assertTrue(main_win.dialog_shown)

        old_count = len(tab_doc.doc)
        tab_doc.insert_blank_page(after_page=3, style="blank")
        self.assertEqual(len(tab_doc.doc), old_count + 1)
        self.assertEqual(sidebar.list_thumbnails.count(), old_count + 1)

        # Alt PDF ekle
        sub_pdf = os.path.abspath("temp_test_insert.pdf")
        sub_doc = fitz.open()
        sub_doc.new_page(width=595, height=842)
        sub_doc.new_page(width=595, height=842)
        sub_doc.save(sub_pdf)
        sub_doc.close()

        try:
            ins_count = tab_doc.insert_pdf_at(sub_pdf, after_page=3)
            self.assertEqual(ins_count, 2)
            self.assertEqual(len(tab_doc.doc), old_count + 3)
            self.assertEqual(sidebar.list_thumbnails.count(), old_count + 3)

            # Kuyruğu tamamla
            iters = 0
            while sidebar._thumb_render_queue and iters < 20:
                sidebar._process_thumb_render_queue()
                iters += 1
            self.assertEqual(len(sidebar._thumb_render_queue), 0)
        finally:
            if os.path.exists(sub_pdf):
                try: os.remove(sub_pdf)
                except Exception: pass
            main_win.close()

    def test_dock_thumbnails_speed(self):
        doc = fitz.open()
        for i in range(5):
            doc.new_page(width=595, height=842)
        doc.set_toc([[1, "Kısım 1", 2]])

        main_win = MockMainWindow()
        main_win.show()
        tab_doc = PDFTabDocument(file_path=None, main_window=main_win)
        tab_doc.doc = doc
        tab_doc.current_page_idx = 0
        main_win.current_tab_doc = tab_doc

        dock = ThumbnailsDock(main_window=main_win)
        main_win.thumbnails_dock = dock
        dock.show()
        dock.load_thumbnails_lazy()

        self.assertTrue(dock.is_loaded)
        self.assertEqual(dock.list_widget.count(), 5)

        t0 = time.perf_counter()
        iters = 0
        while dock._render_queue and iters < 20:
            dock._process_render_queue()
            iters += 1
        t1 = time.perf_counter()
        elapsed = t1 - t0
        print(f"[ThumbnailsDock] 5 pages dock thumbnail queue duration: {elapsed * 1000:.2f} ms")
        self.assertEqual(len(dock._render_queue), 0)
        self.assertLess(elapsed, 0.3)

        bms = dock.get_bookmarked_pages()
        self.assertIn(1, bms)
        self.assertIsNotNone(dock._bookmarked_pages_cache)
        main_win.close()

if __name__ == '__main__':
    unittest.main()

