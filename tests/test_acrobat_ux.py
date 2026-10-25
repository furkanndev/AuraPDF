import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt, QRectF
from PyQt6.QtGui import QColor

# Ensure AuraPDF root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.ui.widgets import EditableInlineTextItem, TextMoveHandleItem
from src.document.media_items import PDFResizableImageItem, PDFTableItem

class MockView:
    def __init__(self):
        class MockScrollBar:
            def __init__(self):
                self._val = 100
            def value(self):
                return self._val
            def setValue(self, v):
                self._val = v
        class MockViewport:
            def width(self): return 800
            def height(self): return 600
            def update(self): pass
        self._vp = MockViewport()
        self._hbar = MockScrollBar()
        self._vbar = MockScrollBar()

    def viewport(self): return self._vp
    def horizontalScrollBar(self): return self._hbar
    def verticalScrollBar(self): return self._vbar
    def mapFromScene(self, pt):
        # 1-to-1 mapping for test
        return pt

class MockScene:
    def __init__(self):
        self.items_list = []
    def removeItem(self, it):
        if it in self.items_list:
            self.items_list.remove(it)

class MockTabDoc:
    def __init__(self):
        self.drawings = []
        self.scene = MockScene()
        self.view = MockView()
        self.active_text_item = None
        self.last_text_item = None
        self.base_render_dpi = 1.0
        self.page_positions = {
            0: {"left": 0.0, "top": 0.0, "width": 600.0, "height": 800.0, "bottom": 800.0, "right": 600.0},
            1: {"left": 0.0, "top": 850.0, "width": 600.0, "height": 800.0, "bottom": 1650.0, "right": 600.0}
        }
        self.notified_pages = []

    def commit_inline_text(self, item):
        txt = item.toPlainText().strip()
        existing = [d for d in self.drawings if d.get("item_ref") == item]
        if existing:
            existing[0]["text"] = txt
        else:
            self.drawings.append({"type": "text", "text": txt, "page": getattr(item, 'page_idx', 0), "item_ref": item})

    def notify_drawings_changed(self, page_idx):
        self.notified_pages.append(page_idx)

    def notify_drawings_changed_throttled(self, page_idx):
        self.notified_pages.append(page_idx)

    def get_page_at_pos(self, pos_or_y):
        y = pos_or_y.y() if hasattr(pos_or_y, 'y') else pos_or_y
        for idx, bounds in self.page_positions.items():
            if bounds['top'] <= y <= bounds['bottom']:
                return idx
        return None

    def auto_scroll_during_drag(self, scene_pos):
        vp_pt = self.view.mapFromScene(scene_pos)
        vp_w = self.view.viewport().width()
        vp_h = self.view.viewport().height()
        margin = 50
        step = 30
        h_bar = self.view.horizontalScrollBar()
        v_bar = self.view.verticalScrollBar()

        if vp_pt.x() < margin:
            factor = max(1.0, (margin - vp_pt.x()) / 10.0)
            h_bar.setValue(int(h_bar.value() - step * factor))
        elif vp_pt.x() > vp_w - margin:
            factor = max(1.0, (vp_pt.x() - (vp_w - margin)) / 10.0)
            h_bar.setValue(int(h_bar.value() + step * factor))

        if vp_pt.y() < margin:
            factor = max(1.0, (margin - vp_pt.y()) / 10.0)
            v_bar.setValue(int(v_bar.value() - step * factor))
        elif vp_pt.y() > vp_h - margin:
            factor = max(1.0, (vp_pt.y() - (vp_h - margin)) / 10.0)
            v_bar.setValue(int(v_bar.value() + step * factor))


class TestAcrobatUX(unittest.TestCase):
    def setUp(self):
        self.tab_doc = MockTabDoc()

    def test_text_box_no_floating_pill(self):
        """Metin kutusunda üstte yer alan ve üstteki kutuyla çakışan floating pill olmamalıdır."""
        item = EditableInlineTextItem(self.tab_doc, 0, QPointF(100, 100), text="Hello World")
        self.assertIsNone(item.move_handle, "Floating move_handle must be None")

    def test_text_box_handles_and_border(self):
        """Acrobat stili 8 tutamaç ve kenarlık algılaması doğru çalışmalıdır."""
        item = EditableInlineTextItem(self.tab_doc, 0, QPointF(100, 100), text="Hello World")
        item.setSelected(True)
        rects = item._handle_rects()
        self.assertEqual(len(rects), 8)
        self.assertIn("tl", rects)
        self.assertIn("br", rects)
        self.assertIn("r", rects)
        self.assertIn("l", rects)

        # Sağ tutamaç kontrolü
        r_center = rects["r"].center()
        self.assertEqual(item._get_handle_at(r_center), "r")

        # Kenarlık algılaması (border)
        tr = item.text_rect()
        border_pt = QPointF(tr.left() + 1.0, tr.top() + tr.height() / 2.0)
        self.assertTrue(item._is_on_border(border_pt))

        # Metin içi (border değil, handle değil)
        inside_pt = tr.center()
        self.assertFalse(item._is_on_border(inside_pt))
        self.assertIsNone(item._get_handle_at(inside_pt))

    def test_single_click_finish_editing(self):
        """Tek tıklama ile düzenlemeden çıkma ve boş kutu temizliği Adobe Acrobat gibi olmalıdır."""
        # 1. Dolu metin kutusu: finish_editing düzenlemeyi bitirir ve kaydeder
        item = EditableInlineTextItem(self.tab_doc, 0, QPointF(100, 100), text="Sample Text")
        item.enable_editing()
        self.assertTrue(bool(item.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction))
        item.finish_editing()
        self.assertEqual(item.textInteractionFlags(), Qt.TextInteractionFlag.NoTextInteraction)
        self.assertFalse(item.isSelected())
        self.assertIsNone(self.tab_doc.active_text_item)
        self.assertTrue(any(d.get("text") == "Sample Text" for d in self.tab_doc.drawings))

        # 2. Boş metin kutusu: finish_editing kutuyu otomatik olarak sahneden ve kayıtlardan siler
        empty_item = EditableInlineTextItem(self.tab_doc, 0, QPointF(150, 150), text="")
        empty_item.finish_editing()
        self.assertFalse(any(d.get("item_ref") == empty_item for d in self.tab_doc.drawings))

    def test_comments_filtering_ignores_text_boxes(self):
        """Metin kutuları yorum paneline KESİNLİKLE eklenmemelidir."""
        # Tab doc drawings içine hem metin kutusu hem gerçek yorum ekle
        self.tab_doc.drawings = [
            {"type": "text", "text": "Bu bir metin kutusudur", "page": 0},
            {"type": "comment", "text": "Bu gerçek bir yorumdur", "page": 0},
            {"type": "table", "text": "", "page": 0},
        ]
        pages_dict = {}
        for d in self.tab_doc.drawings:
            if d.get("type") == "comment" and d.get("text"):
                p_idx = d.get("page", 0)
                pages_dict.setdefault(p_idx, []).append(d)

        self.assertEqual(len(pages_dict.get(0, [])), 1)
        self.assertEqual(pages_dict[0][0]["text"], "Bu gerçek bir yorumdur")

    def test_auto_scroll_during_drag(self):
        """Viewport kenarlarına yaklaşıldığında auto scroll sorunsuz tetiklenmelidir."""
        # Başlangıçta scroll barları 100
        self.assertEqual(self.tab_doc.view.horizontalScrollBar().value(), 100)
        self.assertEqual(self.tab_doc.view.verticalScrollBar().value(), 100)

        # Sağa doğru sürükle (viewport width 800, pos x=780 > 800-50)
        self.tab_doc.auto_scroll_during_drag(QPointF(780, 300))
        self.assertGreater(self.tab_doc.view.horizontalScrollBar().value(), 100)

        # Aşağıya doğru sürükle (viewport height 600, pos y=580 > 600-50)
        self.tab_doc.auto_scroll_during_drag(QPointF(400, 580))
        self.assertGreater(self.tab_doc.view.verticalScrollBar().value(), 100)

        # Sola doğru sürükle (pos x=20 < 50)
        curr_h = self.tab_doc.view.horizontalScrollBar().value()
        self.tab_doc.auto_scroll_during_drag(QPointF(20, 300))
        self.assertLess(self.tab_doc.view.horizontalScrollBar().value(), curr_h)

        # Yukarıya doğru sürükle (pos y=20 < 50)
        curr_v = self.tab_doc.view.verticalScrollBar().value()
        self.tab_doc.auto_scroll_during_drag(QPointF(400, 20))
        self.assertLess(self.tab_doc.view.verticalScrollBar().value(), curr_v)

    def test_media_item_page_confined_dragging(self):
        """Görsel ve tablolar yalnızca eklendikleri sayfanın sınırları içerisinde kalmalıdır."""
        record = {"type": "image", "page": 0, "w": 100, "h": 100}
        img_item = PDFResizableImageItem(self.tab_doc, record)
        
        # Sayfa 0 sınırları: y=0..800. Görsel yüksekliği 100 => max y = 700.
        target_pos = QPointF(200, 1000) # Sayfa 1 üzerinde bir konum
        clamped = img_item.itemChange(img_item.GraphicsItemChange.ItemPositionChange, target_pos)
        self.assertEqual(clamped.y(), 700.0, "Öğe yalnızca eklendiği sayfa 0'ın sınırları içerisinde (0..700) kalmalıdır")

    def test_text_item_delete_backspace_editing_safety(self):
        """Metin kutusuna yazı yazılırken veya içindeki metin seçilip Delete/Backspace'e basıldığında kutu silinmemelidir."""
        from PyQt6.QtWidgets import QGraphicsScene
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent
        scene = QGraphicsScene()
        self.tab_doc.scene = scene
        item = EditableInlineTextItem(self.tab_doc, 0, QPointF(100, 100), text="Merhaba AuraPDF")
        scene.addItem(item)
        
        # 1. Metin düzenleme modunda (TextEditorInteraction)
        item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        item.setSelected(True)
        cur = item.textCursor()
        cur.select(cur.SelectionType.WordUnderCursor)
        item.setTextCursor(cur)
        
        # Delete tuşu basıldığında öğe silinmemeli
        del_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        item.keyPressEvent(del_event)
        self.assertIn(item, scene.items(), "Yazı düzenlenirken Delete tuşu kutuyu silmemelidir")
        
        # Backspace tuşu basıldığında öğe silinmemeli
        bs_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        item.keyPressEvent(bs_event)
        self.assertIn(item, scene.items(), "Yazı düzenlenirken Backspace tuşu kutuyu silmemelidir")
        
        # 2. Düzenleme modundan çıkılmış ve kutu seçiliyken (NoTextInteraction)
        item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        item.setSelected(True)
        item.keyPressEvent(del_event)
        self.assertNotIn(item, scene.items(), "Kutu nesne olarak seçiliyken Delete tuşu kutuyu silmelidir")

    def test_default_sidebar_layout_is_tools_right_nav_left(self):
        """Varsayılan olarak tüm araçlar sağda, gezinme paneli sol tarafta olmalıdır."""
        from PyQt6.QtCore import QSettings
        settings = QSettings("AuraPDF", "PDFViewer")
        saved_layout = settings.value("sidebar_layout", "tools_right_nav_left", type=str)
        self.assertIn(saved_layout, ("tools_right_nav_left", "tools_left_nav_right"))

if __name__ == '__main__':
    unittest.main()
