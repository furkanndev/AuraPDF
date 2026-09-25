import os
import math
import tempfile
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtWidgets import (QGraphicsItem, QMenu, QInputDialog,
                             QLineEdit, QMessageBox, QDialog, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QStyle)
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
                         QPixmap, QImage, QPainterPath, QLinearGradient)
from PyQt6.QtCore import (Qt, QRectF, QPointF, QUrl)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class ResizeHandle:
    """Köşe ve kenar boyutlandırma tutamacı tanımı."""
    HANDLE_SIZE = 8.0

    def __init__(self, name: str, cursor_shape: Qt.CursorShape):
        self.name = name
        self.cursor_shape = cursor_shape

    def rect(self, bounds: QRectF) -> QRectF:
        s = self.HANDLE_SIZE
        hs = s / 2.0
        x, y, w, h = bounds.x(), bounds.y(), bounds.width(), bounds.height()
        cx = x + w / 2.0
        cy = y + h / 2.0

        if self.name == "tl": return QRectF(x - hs, y - hs, s, s)
        elif self.name == "t": return QRectF(cx - hs, y - hs, s, s)
        elif self.name == "tr": return QRectF(x + w - hs, y - hs, s, s)
        elif self.name == "r": return QRectF(x + w - hs, cy - hs, s, s)
        elif self.name == "br": return QRectF(x + w - hs, y + h - hs, s, s)
        elif self.name == "b": return QRectF(cx - hs, y + h - hs, s, s)
        elif self.name == "bl": return QRectF(x - hs, y + h - hs, s, s)
        elif self.name == "l": return QRectF(x - hs, cy - hs, s, s)
        return QRectF()


HANDLES = [
    ResizeHandle("tl", Qt.CursorShape.SizeFDiagCursor),
    ResizeHandle("t", Qt.CursorShape.SizeVerCursor),
    ResizeHandle("tr", Qt.CursorShape.SizeBDiagCursor),
    ResizeHandle("r", Qt.CursorShape.SizeHorCursor),
    ResizeHandle("br", Qt.CursorShape.SizeFDiagCursor),
    ResizeHandle("b", Qt.CursorShape.SizeVerCursor),
    ResizeHandle("bl", Qt.CursorShape.SizeBDiagCursor),
    ResizeHandle("l", Qt.CursorShape.SizeHorCursor),
]


class PDFTableItem(QGraphicsItem):
    """
    PDF üzerine eklenen ve doğrudan PDF sayfası üzerinden serbestçe boyutlandırılabilen,
    hücreleri çift tıklanarak düzenlenebilen etkileşimli tablo bileşeni.
    """
    def __init__(self, tab_doc, record: Dict[str, Any]):
        super().__init__()
        self.tab_doc = tab_doc
        self.record = record

        self.rows = max(1, int(record.get("rows", 3)))
        self.cols = max(1, int(record.get("cols", 3)))
        self.cell_data: List[List[str]] = record.get("cell_data") or [
            ["" for _ in range(self.cols)] for _ in range(self.rows)
        ]
        # Eksik hücre verilerini normalize et
        while len(self.cell_data) < self.rows:
            self.cell_data.append(["" for _ in range(self.cols)])
        for r in range(self.rows):
            while len(self.cell_data[r]) < self.cols:
                self.cell_data[r].append("")

        dpi = getattr(tab_doc, 'base_render_dpi', 1.5)
        self.w = float(record.get("w", 220.0)) * dpi
        self.h = float(record.get("h", 100.0)) * dpi

        # Stil özellikleri
        self.border_color = QColor(record.get("border_color", "#7c3aed"))
        self.header_bg = QColor(record.get("header_bg", "#7c3aed"))
        self.cell_bg = QColor(record.get("cell_bg", "#ffffff"))
        raw_alt = record.get("alt_cell_bg")
        if raw_alt:
            self.alt_cell_bg = QColor(raw_alt)
        else:
            self.alt_cell_bg = self.cell_bg.darker(106) if self.cell_bg.lightness() > 128 else self.cell_bg.lighter(118)
        self.text_color = QColor(record.get("text_color", "#1e1b4b"))
        self.header_text_color = QColor(record.get("header_text_color", "#ffffff"))
        self.font_size = float(record.get("font_size", 11.0))
        self.font_family = str(record.get("font_family", "Arial"))
        self.bold = bool(record.get("bold", False))
        self.italic = bool(record.get("italic", False))
        self.underline = bool(record.get("underline", False))
        self.has_header = bool(record.get("has_header", True))

        self.setZValue(15)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._active_handle: Optional[str] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_bounds: Optional[QRectF] = None
        self._inline_editor: Optional[QLineEdit] = None
        self._editing_cell: Optional[Tuple[int, int]] = None

    def boundingRect(self) -> QRectF:
        pad = 8.0
        return QRectF(-pad, -pad, self.w + pad * 2, self.h + pad * 2)

    def tableRect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        row_h = self.h / max(1, self.rows)
        col_w = self.w / max(1, self.cols)

        # 1. Hücre arka planları
        for r in range(self.rows):
            for c in range(self.cols):
                rx = round(c * col_w)
                ry = round(r * row_h)
                rw = round((c + 1) * col_w) - rx
                rh = round((r + 1) * row_h) - ry
                cell_rect = QRectF(rx, ry, rw, rh)

                if r == 0 and self.has_header:
                    bg = self.header_bg
                elif r % 2 == 1:
                    bg = self.alt_cell_bg
                else:
                    bg = self.cell_bg

                painter.fillRect(cell_rect, bg)

        # 2. Hücre çerçeve çizgileri (Net, belirgin ve tam seçilen kenarlık renginde)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setBrush(Qt.BrushStyle.NoBrush)  # ÖNEMLİ: Arka planı asla beyazla ezmesin
        grid_pen = QPen(self.border_color, 2.0, Qt.PenStyle.SolidLine)
        grid_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(grid_pen)

        # Her hücrenin kendi sınır çizgilerini çiz
        for r in range(self.rows):
            for c in range(self.cols):
                rx = round(c * col_w)
                ry = round(r * row_h)
                rw = round((c + 1) * col_w) - rx
                rh = round((r + 1) * row_h) - ry
                painter.drawRect(QRectF(rx, ry, rw, rh))

        # Dış sınır çerçevesi (Kenarlık renginde, belirgin)
        outer_pen = QPen(self.border_color, 2.5, Qt.PenStyle.SolidLine)
        outer_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(outer_pen)
        painter.drawRect(QRectF(0, 0, round(self.w), round(self.h)))

        # 3. Hücre metinleri
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = QFont(self.font_family, int(max(6, self.font_size)))
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)

        header_font = QFont(self.font_family, int(max(6, self.font_size)), QFont.Weight.Bold if not self.bold else QFont.Weight.Black)
        header_font.setItalic(self.italic)
        header_font.setUnderline(self.underline)

        for r in range(self.rows):
            is_hdr = (r == 0 and self.has_header)
            painter.setFont(header_font if is_hdr else font)

            # Kontrast korumalı metin rengi
            if is_hdr:
                h_pen = self.header_text_color
                if self.header_bg.lightness() < 130 and h_pen.lightness() < 100:
                    h_pen = QColor("#ffffff")
                elif self.header_bg.lightness() >= 130 and h_pen.lightness() > 180:
                    h_pen = QColor("#0f172a")
                painter.setPen(h_pen)
            else:
                c_pen = self.text_color
                row_bg = self.alt_cell_bg if r % 2 == 1 else self.cell_bg
                if row_bg.lightness() > 160 and c_pen.lightness() > 200:
                    c_pen = QColor("#0f172a")
                elif row_bg.lightness() <= 100 and c_pen.lightness() < 60:
                    c_pen = QColor("#f8fafc")
                painter.setPen(c_pen)

            for c in range(self.cols):
                if self._editing_cell == (r, c):
                    continue  # Düzenlenen hücreyi editor çiziyor
                txt = self.cell_data[r][c]
                if txt:
                    rect = QRectF(c * col_w + 4, r * row_h + 2, col_w - 8, row_h - 4)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, txt)

        # 4. Seçim ve Boyutlandırma Tutamaçları
        if self.isSelected():
            # Dış mavi vurgu çizgisi
            sel_pen = QPen(QColor("#38bdf8"), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(-1.5, -1.5, self.w + 3, self.h + 3))

            # 8 Tutamaç (Handle)
            handle_pen = QPen(QColor("#0284c7"), 1.2)
            handle_brush = QBrush(QColor("#ffffff"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            bounds = self.tableRect()
            for h in HANDLES:
                painter.drawRect(h.rect(bounds))

        painter.restore()

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        bounds = self.tableRect()
        for h in HANDLES:
            if h.rect(bounds).contains(pos):
                return h.name
        return None

    def hoverMoveEvent(self, event):
        h_name = self._get_handle_at(event.pos())
        if h_name:
            for h in HANDLES:
                if h.name == h_name:
                    self.setCursor(h.cursor_shape)
                    return
        elif self.tableRect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor if self.isSelected() else Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange and value:
            if hasattr(self.tab_doc, 'active_text_item'):
                self.tab_doc.active_text_item = self
            if hasattr(self.tab_doc, 'last_text_item'):
                self.tab_doc.last_text_item = self
            main_win = getattr(self.tab_doc, 'main_window', None)
            if main_win and hasattr(main_win, 'text_popup') and main_win.text_popup.isVisible():
                main_win.text_popup.sync_with_item_selection(self)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.tab_doc:
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0))
            if p_info:
                page_left = p_info.get('left', 0.0)
                page_top = p_info['top']
                page_w = p_info['width']
                page_h = p_info['height']
                min_x = page_left
                max_x = page_left + max(0.0, page_w - self.w)
                min_y = page_top
                max_y = page_top + max(0.0, page_h - self.h)
                clamped_x = max(min_x, min(value.x(), max_x))
                clamped_y = max(min_y, min(value.y(), max_y))
                return QPointF(clamped_x, clamped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
        return super().itemChange(change, value)

    def get_selection_format(self) -> Dict[str, Any]:
        return {
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "font_size": self.font_size,
            "color": self.text_color,
            "font_family": self.font_family,
        }

    def apply_format_to_selection(self, *, bold=None, italic=None, underline=None, font_size=None, color=None, font_family=None):
        changed = False
        if bold is not None:
            self.bold = bool(bold)
            changed = True
        if italic is not None:
            self.italic = bool(italic)
            changed = True
        if underline is not None:
            self.underline = bool(underline)
            changed = True
        if font_size is not None and font_size > 0:
            self.font_size = float(font_size)
            changed = True
        if color is not None:
            col = QColor(color) if not isinstance(color, QColor) else color
            if col.isValid():
                self.text_color = col
                if hasattr(self, '_editing_cell') and self._editing_cell and self._editing_cell[0] == 0 and self.has_header:
                    self.header_text_color = col
                elif self.header_bg.lightness() > 140:
                    self.header_text_color = col
                changed = True
        if font_family is not None:
            self.font_family = str(font_family)
            changed = True
        if changed:
            self._sync_record()
            self.update()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def mousePressEvent(self, event):
        if hasattr(self.tab_doc, 'active_text_item'):
            self.tab_doc.active_text_item = self
        if hasattr(self.tab_doc, 'last_text_item'):
            self.tab_doc.last_text_item = self
        main_win = getattr(self.tab_doc, 'main_window', None)
        if main_win and hasattr(main_win, 'text_popup') and main_win.text_popup.isVisible():
            main_win.text_popup.sync_with_item_selection(self)

        if event.button() == Qt.MouseButton.LeftButton:
            h_name = self._get_handle_at(event.pos())
            if h_name:
                self._active_handle = h_name
                self._drag_start_pos = event.scenePos()
                self._drag_start_bounds = QRectF(self.pos().x(), self.pos().y(), self.w, self.h)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle and self._drag_start_pos and self._drag_start_bounds:
            delta = event.scenePos() - self._drag_start_pos
            orig = self._drag_start_bounds

            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info['top'] if p_info else 0.0
            page_w = p_info['width'] if p_info else 10000.0
            page_h = p_info['height'] if p_info else 10000.0

            new_x = orig.x()
            new_y = orig.y()
            new_w = orig.width()
            new_h = orig.height()

            min_w = max(40.0, self.cols * 18.0)
            min_h = max(24.0, self.rows * 14.0)

            h = self._active_handle
            if "r" in h:
                new_w = max(min_w, orig.width() + delta.x())
            if "l" in h:
                diff = min(orig.width() - min_w, delta.x())
                new_x = orig.x() + diff
                new_w = orig.width() - diff
            if "b" in h:
                new_h = max(min_h, orig.height() + delta.y())
            if "t" in h:
                diff = min(orig.height() - min_h, delta.y())
                new_y = orig.y() + diff
                new_h = orig.height() - diff

            # PDF Sayfa sınırları dışına taşmayı engelle
            new_x = max(page_left, min(new_x, page_left + max(0.0, page_w - min_w)))
            new_y = max(page_top, min(new_y, page_top + max(0.0, page_h - min_h)))
            new_w = max(min_w, min(new_w, max(min_w, page_left + page_w - new_x)))
            new_h = max(min_h, min(new_h, max(min_h, page_top + page_h - new_y)))

            self.prepareGeometryChange()
            self.setPos(new_x, new_y)
            self.w = new_w
            self.h = new_h
            self.update()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            self._drag_start_pos = None
            self._drag_start_bounds = None
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._sync_record()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def mouseDoubleClickEvent(self, event):
        """Çift tıklandığında tıklanan hücreyi düzenle."""
        pos = event.pos()
        if not self.tableRect().contains(pos):
            return

        row_h = self.h / max(1, self.rows)
        col_w = self.w / max(1, self.cols)
        r = int(pos.y() // row_h)
        c = int(pos.x() // col_w)

        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.start_cell_editing(r, c)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def start_cell_editing(self, r: int, c: int):
        self.finish_cell_editing()
        self._editing_cell = (r, c)

        view = getattr(self.tab_doc, 'view', None)
        if not view:
            return

        row_h = self.h / max(1, self.rows)
        col_w = self.w / max(1, self.cols)
        cell_rect_item = QRectF(c * col_w, r * row_h, col_w, row_h)
        cell_scene_rect = self.mapRectToScene(cell_rect_item)
        view_rect = view.mapFromScene(cell_scene_rect).boundingRect()

        editor = QLineEdit(view.viewport())
        editor.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                color: #ffffff;
                border: 2px solid #38bdf8;
                border-radius: 3px;
                padding: 2px 4px;
                font-family: Arial;
                font-size: 12px;
            }
        """)
        editor.setText(self.cell_data[r][c])
        editor.setGeometry(view_rect.adjusted(1, 1, -1, -1))
        editor.selectAll()
        editor.setFocus()

        editor.returnPressed.connect(self.finish_cell_editing)
        editor.editingFinished.connect(self.finish_cell_editing)

        self._inline_editor = editor
        editor.show()

    def finish_cell_editing(self):
        if self._inline_editor and self._editing_cell:
            r, c = self._editing_cell
            new_text = self._inline_editor.text().strip()
            self.cell_data[r][c] = new_text
            self._inline_editor.deleteLater()
            self._inline_editor = None
            self._editing_cell = None
            self._sync_record()
            self.update()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def contextMenuEvent(self, event):
        pos = event.pos()
        row_h = self.h / max(1, self.rows)
        col_w = self.w / max(1, self.cols)
        click_r = int(pos.y() // row_h) if self.h > 0 else 0
        click_c = int(pos.x() // col_w) if self.w > 0 else 0

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1e1e24; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2563eb; }
        """)

        act_style = menu.addAction("Metin ve Renk Ayarları...")
        act_edit = menu.addAction("Hücreyi Düzenle")
        menu.addSeparator()
        act_add_row = menu.addAction("Satır Ekle (Aşağıya)")
        act_del_row = menu.addAction("Satır Sil")
        act_add_col = menu.addAction("Sütun Ekle (Sağa)")
        act_del_col = menu.addAction("Sütun Sil")
        menu.addSeparator()
        act_del_table = menu.addAction("Tabloyu Sil")

        action = menu.exec(event.screenPos())
        if action == act_style:
            from src.ui.dialogs.media_dialogs import TableStyleDialog
            dlg = TableStyleDialog(self, parent=None)
            dlg.exec()
        elif action == act_edit:
            self.start_cell_editing(max(0, min(click_r, self.rows - 1)), max(0, min(click_c, self.cols - 1)))
        elif action == act_add_row:
            self.add_row(click_r + 1)
        elif action == act_del_row:
            self.delete_row(click_r)
        elif action == act_add_col:
            self.add_col(click_c + 1)
        elif action == act_del_col:
            self.delete_col(click_c)
        elif action == act_del_table:
            self.delete_self()

    def add_row(self, at_idx: int):
        at_idx = max(0, min(at_idx, self.rows))
        self.prepareGeometryChange()
        self.rows += 1
        self.cell_data.insert(at_idx, ["" for _ in range(self.cols)])
        added_h = max(20.0, self.h / (self.rows - 1))
        p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
        if p_info:
            page_top = p_info.get('top', 0.0)
            page_h = p_info.get('height', 10000.0)
            target_h = min(self.h + added_h, page_h)
            cur_y = self.pos().y()
            if cur_y + target_h > page_top + page_h:
                new_y = max(page_top, page_top + page_h - target_h)
                self.setPos(self.pos().x(), new_y)
            self.h = target_h
        else:
            self.h += added_h
        self._sync_record()
        self.update()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def delete_row(self, at_idx: int):
        if self.rows <= 1:
            QMessageBox.information(None, "Bilgi", "Tabloda en az 1 satır bulunmalıdır.")
            return
        at_idx = max(0, min(at_idx, self.rows - 1))
        self.prepareGeometryChange()
        row_h = self.h / self.rows
        self.rows -= 1
        self.cell_data.pop(at_idx)
        self.h = max(24.0, self.h - row_h)
        self._sync_record()
        self.update()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def add_col(self, at_idx: int):
        at_idx = max(0, min(at_idx, self.cols))
        self.prepareGeometryChange()
        self.cols += 1
        for r in range(self.rows):
            self.cell_data[r].insert(at_idx, "")
        added_w = max(40.0, self.w / (self.cols - 1))
        p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
        if p_info:
            page_left = p_info.get('left', 0.0)
            page_w = p_info.get('width', 10000.0)
            target_w = min(self.w + added_w, page_w)
            cur_x = self.pos().x()
            if cur_x + target_w > page_left + page_w:
                new_x = max(page_left, page_left + page_w - target_w)
                self.setPos(new_x, self.pos().y())
            self.w = target_w
        else:
            self.w += added_w
        self._sync_record()
        self.update()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def delete_col(self, at_idx: int):
        if self.cols <= 1:
            QMessageBox.information(None, "Bilgi", "Tabloda en az 1 sütun bulunmalıdır.")
            return
        at_idx = max(0, min(at_idx, self.cols - 1))
        self.prepareGeometryChange()
        col_w = self.w / self.cols
        self.cols -= 1
        for r in range(self.rows):
            self.cell_data[r].pop(at_idx)
        self.w = max(40.0, self.w - col_w)
        self._sync_record()
        self.update()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def delete_self(self):
        if self.tab_doc and self.record in self.tab_doc.drawings:
            self.tab_doc.drawings.remove(self.record)
            if self.scene():
                self.scene().removeItem(self)
            self.tab_doc.push_undo_action({"type": "erase", "deleted_items": [self.record]})
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def _sync_record(self):
        dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        p_info = self.tab_doc.page_positions.get(self.record.get("page", 0)) if self.tab_doc else None
        page_left = p_info.get('left', 0.0) if p_info else 0.0
        page_top = p_info.get('top', 0.0) if p_info else 0.0
        page_pdf_w = (p_info['width'] / dpi) if p_info else 10000.0
        page_pdf_h = (p_info['height'] / dpi) if p_info else 10000.0

        pos = self.pos()
        item_w = min(self.w / dpi, page_pdf_w)
        item_h = min(self.h / dpi, page_pdf_h)
        item_x = max(0.0, min((pos.x() - page_left) / dpi, max(0.0, page_pdf_w - item_w)))
        item_y = max(0.0, min((pos.y() - page_top) / dpi, max(0.0, page_pdf_h - item_h)))

        self.record["x"] = item_x
        self.record["y"] = item_y
        self.record["w"] = item_w
        self.record["h"] = item_h
        self.record["rows"] = self.rows
        self.record["cols"] = self.cols
        self.record["cell_data"] = [list(row) for row in self.cell_data]
        self.record["font_size"] = self.font_size
        self.record["font_family"] = self.font_family
        self.record["bold"] = self.bold
        self.record["italic"] = self.italic
        self.record["underline"] = self.underline
        self.record["border_color"] = self.border_color.name()
        self.record["header_bg"] = self.header_bg.name()
        self.record["cell_bg"] = self.cell_bg.name()
        self.record["alt_cell_bg"] = self.alt_cell_bg.name()
        self.record["text_color"] = self.text_color.name()
        self.record["header_text_color"] = self.header_text_color.name()
        self.record["item_ref"] = self


class PDFResizableImageItem(QGraphicsItem):
    """
    Kullanıcının doğrudan PDF üzerinde serbestçe boyutlandırabildiği ve taşıyabildiği
    görsel (bilgisayardan / URL) ve emoji/GIF bileşeni.
    """
    def __init__(self, tab_doc, record: Dict[str, Any]):
        super().__init__()
        self.tab_doc = tab_doc
        self.record = record

        dpi = getattr(tab_doc, 'base_render_dpi', 1.5)
        self.w = float(record.get("w", 120.0)) * dpi
        self.h = float(record.get("h", 120.0)) * dpi

        self.pixmap = QPixmap()
        img_bytes = record.get("image_bytes")
        if img_bytes:
            img = QImage()
            img.loadFromData(img_bytes)
            self.pixmap = QPixmap.fromImage(img)

        self.aspect_ratio = (self.w / max(1.0, self.h)) if self.h > 0 else 1.0
        if not self.pixmap.isNull() and self.pixmap.height() > 0:
            self.aspect_ratio = self.pixmap.width() / self.pixmap.height()

        self.keep_aspect_ratio = bool(record.get("keep_aspect", True))

        # Animasyonlu GIF desteği (QMovie)
        self.movie = None
        self._movie_buf = None
        self._movie_ba = None
        if img_bytes and (img_bytes.startswith(b"GIF87a") or img_bytes.startswith(b"GIF89a")):
            try:
                from PyQt6.QtGui import QMovie
                from PyQt6.QtCore import QBuffer, QByteArray
                self._movie_ba = QByteArray(img_bytes)
                self._movie_buf = QBuffer(self._movie_ba)
                self._movie_buf.open(QBuffer.OpenModeFlag.ReadOnly)
                self.movie = QMovie(self._movie_buf, QByteArray(b"GIF"))
                if self.movie.isValid():
                    self.movie.frameChanged.connect(self._on_movie_frame)
                    self.movie.start()
            except Exception:
                self.movie = None

        self.setZValue(14)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._active_handle: Optional[str] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_bounds: Optional[QRectF] = None

    def boundingRect(self) -> QRectF:
        pad = 8.0
        return QRectF(-pad, -pad, self.w + pad * 2, self.h + pad * 2)

    def imageRect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if not self.pixmap.isNull():
            painter.drawPixmap(QRectF(0, 0, self.w, self.h).toRect(), self.pixmap)
        else:
            painter.fillRect(QRectF(0, 0, self.w, self.h), QColor("#334155"))
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(QRectF(0, 0, self.w, self.h), Qt.AlignmentFlag.AlignCenter, "Görsel")

        # Seçim ve Tutamaçlar
        if self.isSelected():
            sel_pen = QPen(QColor("#38bdf8"), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(-1.0, -1.0, self.w + 2, self.h + 2))

            handle_pen = QPen(QColor("#0284c7"), 1.2)
            handle_brush = QBrush(QColor("#ffffff"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            bounds = self.imageRect()
            for h in HANDLES:
                painter.drawRect(h.rect(bounds))

        painter.restore()

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        bounds = self.imageRect()
        for h in HANDLES:
            if h.rect(bounds).contains(pos):
                return h.name
        return None

    def hoverMoveEvent(self, event):
        h_name = self._get_handle_at(event.pos())
        if h_name:
            for h in HANDLES:
                if h.name == h_name:
                    self.setCursor(h.cursor_shape)
                    return
        elif self.imageRect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor if self.isSelected() else Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.tab_doc:
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0))
            if p_info:
                page_left = p_info.get('left', 0.0)
                page_top = p_info.get('top', 0.0)
                page_w = p_info.get('width', 10000.0)
                page_h = p_info.get('height', 10000.0)
                min_x = page_left
                max_x = page_left + max(0.0, page_w - self.w)
                min_y = page_top
                max_y = page_top + max(0.0, page_h - self.h)
                clamped_x = max(min_x, min(value.x(), max_x))
                clamped_y = max(min_y, min(value.y(), max_y))
                return QPointF(clamped_x, clamped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h_name = self._get_handle_at(event.pos())
            if h_name:
                self._active_handle = h_name
                self._drag_start_pos = event.scenePos()
                self._drag_start_bounds = QRectF(self.pos().x(), self.pos().y(), self.w, self.h)
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        if self._active_handle and self._drag_start_pos and self._drag_start_bounds:
            delta = event.scenePos() - self._drag_start_pos
            orig = self._drag_start_bounds

            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info.get('top', 0.0) if p_info else 0.0
            page_w = p_info.get('width', 10000.0) if p_info else 10000.0
            page_h = p_info.get('height', 10000.0) if p_info else 10000.0

            new_x = orig.x()
            new_y = orig.y()
            new_w = orig.width()
            new_h = orig.height()

            min_s = 20.0
            h = self._active_handle

            # En-boy oranı koruma: özellik ve Shift tuşu ile dinamik kontrol
            keep_aspect = self.keep_aspect_ratio and not bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

            if keep_aspect:
                if "r" in h:
                    new_w = max(min_s, orig.width() + delta.x())
                    if self.aspect_ratio > 0:
                        new_h = new_w / self.aspect_ratio
                elif "l" in h:
                    diff = min(orig.width() - min_s, delta.x())
                    new_x = orig.x() + diff
                    new_w = orig.width() - diff
                    if self.aspect_ratio > 0:
                        new_h = new_w / self.aspect_ratio

                if "b" in h and not ("r" in h):
                    new_h = max(min_s, orig.height() + delta.y())
                    if self.aspect_ratio > 0:
                        new_w = new_h * self.aspect_ratio
                elif "t" in h and not ("l" in h):
                    diff = min(orig.height() - min_s, delta.y())
                    new_y = orig.y() + diff
                    new_h = orig.height() - diff
                    if self.aspect_ratio > 0:
                        new_w = new_h * self.aspect_ratio
            else:
                # Serbest boyutlandırma: Genişlik ve yükseklik birbirinden bağımsız değiştirilebilir
                if "r" in h:
                    new_w = max(min_s, orig.width() + delta.x())
                elif "l" in h:
                    diff = min(orig.width() - min_s, delta.x())
                    new_x = orig.x() + diff
                    new_w = orig.width() - diff

                if "b" in h:
                    new_h = max(min_s, orig.height() + delta.y())
                elif "t" in h:
                    diff = min(orig.height() - min_s, delta.y())
                    new_y = orig.y() + diff
                    new_h = orig.height() - diff

                if new_h > 0:
                    self.aspect_ratio = new_w / new_h

            # PDF Sayfa sınırları dışına taşmayı engelle
            if new_x < page_left:
                excess = page_left - new_x
                new_x = page_left
                new_w = max(min_s, new_w - excess)
                if keep_aspect and self.aspect_ratio > 0:
                    new_h = new_w / self.aspect_ratio
            if new_y < page_top:
                excess = page_top - new_y
                new_y = page_top
                new_h = max(min_s, new_h - excess)
                if keep_aspect and self.aspect_ratio > 0:
                    new_w = new_h * self.aspect_ratio

            if keep_aspect and self.aspect_ratio > 0:
                if new_x + new_w > page_left + page_w:
                    new_w = max(min_s, page_left + page_w - new_x)
                    new_h = new_w / self.aspect_ratio
                if new_y + new_h > page_top + page_h:
                    new_h = max(min_s, page_top + page_h - new_y)
                    new_w = new_h * self.aspect_ratio
            else:
                new_w = max(min_s, min(new_w, max(min_s, page_left + page_w - new_x)))
                new_h = max(min_s, min(new_h, max(min_s, page_top + page_h - new_y)))

            new_x = max(page_left, min(new_x, page_left + max(0.0, page_w - min_s)))
            new_y = max(page_top, min(new_y, page_top + max(0.0, page_h - min_s)))

            self.prepareGeometryChange()
            self.setPos(new_x, new_y)
            self.w = max(min_s, new_w)
            self.h = max(min_s, new_h)
            self.update()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            self._drag_start_pos = None
            self._drag_start_bounds = None
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._sync_record()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1e1e24; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2563eb; }
        """)
        act_aspect = menu.addAction("En-Boy Oranını Koru")
        act_aspect.setCheckable(True)
        act_aspect.setChecked(self.keep_aspect_ratio)

        menu.addSeparator()
        act_reset = menu.addAction("Orijinal Boyuta Dön")
        act_del = menu.addAction("Görseli Sil")

        action = menu.exec(event.screenPos())
        if action == act_aspect:
            self.keep_aspect_ratio = act_aspect.isChecked()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
        elif action == act_reset:
            if not self.pixmap.isNull():
                self.prepareGeometryChange()
                dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
                p_info = self.tab_doc.page_positions.get(self.record.get("page", 0)) if self.tab_doc else None
                page_left = p_info.get('left', 0.0) if p_info else 0.0
                page_top = p_info.get('top', 0.0) if p_info else 0.0
                page_w = p_info.get('width', 10000.0) if p_info else 10000.0
                page_h = p_info.get('height', 10000.0) if p_info else 10000.0

                if self.pixmap.height() > 0:
                    self.aspect_ratio = self.pixmap.width() / self.pixmap.height()

                init_w = float(self.record.get("init_pdf_w", 0.0))
                init_h = float(self.record.get("init_pdf_h", 0.0))
                if init_w > 10.0 and init_h > 10.0:
                    target_w = init_w * dpi
                    target_h = init_h * dpi
                else:
                    max_w = min(float(self.pixmap.width()) * 0.75, (page_w / dpi) - 40.0, 320.0)
                    target_w = max_w * dpi
                    target_h = target_w / max(0.01, self.aspect_ratio)

                target_w = min(target_w, page_w)
                target_h = min(target_h, page_h)
                cur_x = self.pos().x()
                cur_y = self.pos().y()
                clamped_x = max(page_left, min(cur_x, page_left + max(0.0, page_w - target_w)))
                clamped_y = max(page_top, min(cur_y, page_top + max(0.0, page_h - target_h)))
                self.setPos(clamped_x, clamped_y)
                self.w = target_w
                self.h = target_h
                self._sync_record()
                self.update()
                if hasattr(self.tab_doc, 'notify_drawings_changed'):
                    self.tab_doc.notify_drawings_changed(self.record.get("page"))
        elif action == act_del:
            self.delete_self()

    def _on_movie_frame(self, frame_no: int):
        if not getattr(self, 'movie', None):
            return
        try:
            if not self.scene():
                return
            cur = self.movie.currentPixmap()
            if not cur.isNull():
                self.pixmap = cur
                self.update()
        except Exception:
            pass

    def stop_movie(self):
        if getattr(self, 'movie', None):
            try:
                self.movie.stop()
                self.movie.frameChanged.disconnect(self._on_movie_frame)
            except Exception:
                pass
            try:
                self.movie.deleteLater()
            except Exception:
                pass
            self.movie = None
        if getattr(self, '_movie_buf', None):
            try:
                if self._movie_buf.isOpen():
                    self._movie_buf.close()
            except Exception:
                pass
            self._movie_buf = None
        self._movie_ba = None

    def delete_self(self):
        self.stop_movie()
        if self.tab_doc and self.record in self.tab_doc.drawings:
            self.tab_doc.drawings.remove(self.record)
            if self.scene():
                self.scene().removeItem(self)
            self.tab_doc.push_undo_action({"type": "erase", "deleted_items": [self.record]})
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def _sync_record(self):
        dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        p_info = self.tab_doc.page_positions.get(self.record.get("page", 0)) if self.tab_doc else None
        page_left = p_info.get('left', 0.0) if p_info else 0.0
        page_top = p_info.get('top', 0.0) if p_info else 0.0
        page_pdf_w = (p_info['width'] / dpi) if p_info else 10000.0
        page_pdf_h = (p_info['height'] / dpi) if p_info else 10000.0

        pos = self.pos()
        item_w = min(self.w / dpi, page_pdf_w)
        item_h = min(self.h / dpi, page_pdf_h)
        item_x = max(0.0, min((pos.x() - page_left) / dpi, max(0.0, page_pdf_w - item_w)))
        item_y = max(0.0, min((pos.y() - page_top) / dpi, max(0.0, page_pdf_h - item_h)))

        self.record["x"] = item_x
        self.record["y"] = item_y
        self.record["w"] = item_w
        self.record["h"] = item_h
        self.record["keep_aspect"] = self.keep_aspect_ratio
        self.record["item_ref"] = self


class PDFAudioItem(QGraphicsItem):
    """
    PDF üzerine yerleştirilen şık, modern etkileşimli ve boyutlandırılabilir ses kayıt kartı.
    Viewer üzerinden tıklandığında sesi çalar. Köşelerden ve kenarlardan serbestçe boyutlandırılabilir.
    """
    _PLAYER: Optional[QMediaPlayer] = None
    _AUDIO_OUTPUT: Optional[QAudioOutput] = None

    def __init__(self, tab_doc, record: Dict[str, Any]):
        super().__init__()
        self.tab_doc = tab_doc
        self.record = record

        dpi = getattr(tab_doc, 'base_render_dpi', 1.5)
        self.w = max(130.0, float(record.get("w", 180.0)) * dpi)
        self.h = max(38.0, float(record.get("h", 48.0)) * dpi)
        self.title = str(record.get("title", "Ses Kaydı"))
        self.duration_sec = float(record.get("duration_sec", 0.0))
        self.audio_bytes = record.get("audio_bytes", b"")
        self.is_playing = False
        self._temp_file_path: Optional[str] = None

        # Boyutlandırma durumu
        self._active_handle: Optional[str] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_bounds: Optional[QRectF] = None

        self.setZValue(15)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        pad = 8.0
        return QRectF(-pad, -pad, self.w + pad * 2, self.h + pad * 2)

    def cardRect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def play_button_rect(self) -> QRectF:
        btn_d = min(32.0, max(20.0, self.h - 12.0))
        btn_y = (self.h - btn_d) / 2.0
        return QRectF(8.0, btn_y, btn_d, btn_d)

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        bounds = self.cardRect()
        for h in HANDLES:
            if h.rect(bounds).contains(pos):
                return h.name
        return None

    def hoverMoveEvent(self, event):
        h_name = self._get_handle_at(event.pos())
        if h_name:
            for h in HANDLES:
                if h.name == h_name:
                    self.setCursor(h.cursor_shape)
                    return
        elif self.play_button_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.cardRect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor if self.isSelected() else Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # Kart Arka Planı (Koyu cam/mor gradyan)
        grad = QLinearGradient(0, 0, self.w, self.h)
        grad.setColorAt(0.0, QColor("#1e1b4b"))
        grad.setColorAt(1.0, QColor("#0f172a"))
        painter.setPen(QPen(QColor("#6366f1"), 1.4))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(self.cardRect(), 8.0, 8.0)

        # Oynat / Durdur Butonu
        btn_r = self.play_button_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#6366f1" if not self.is_playing else "#ec4899")))
        painter.drawEllipse(btn_r)

        # Play / Pause İkonu
        painter.setBrush(QBrush(QColor("#ffffff")))
        if not self.is_playing:
            poly = QPainterPath()
            cx = btn_r.center().x()
            cy = btn_r.center().y()
            s = btn_r.width() * 0.35
            poly.moveTo(cx - s * 0.5, cy - s * 0.8)
            poly.lineTo(cx + s * 0.8, cy)
            poly.lineTo(cx - s * 0.5, cy + s * 0.8)
            poly.closeSubpath()
            painter.drawPath(poly)
        else:
            cx = btn_r.center().x()
            cy = btn_r.center().y()
            pw = max(2.5, btn_r.width() * 0.12)
            ph = btn_r.height() * 0.45
            painter.drawRect(QRectF(cx - pw * 1.5, cy - ph / 2.0, pw, ph))
            painter.drawRect(QRectF(cx + pw * 0.5, cy - ph / 2.0, pw, ph))

        # Başlık ve Süre Metni (Taşmaları önlemek için elidedText kullanılır)
        text_x = btn_r.right() + 8.0
        avail_w = max(20.0, self.w - text_x - 8.0)

        title_font = QFont("Arial", 10, QFont.Weight.Bold)
        fm_title = QFontMetrics(title_font)
        elided_title = fm_title.elidedText(self.title, Qt.TextElideMode.ElideRight, int(avail_w))

        mins = int(self.duration_sec // 60)
        secs = int(self.duration_sec % 60)
        dur_str = f"{mins:02d}:{secs:02d}" if self.duration_sec > 0 else "Ses Dosyası"
        dur_font = QFont("Arial", 8)
        fm_dur = QFontMetrics(dur_font)
        elided_dur = fm_dur.elidedText(dur_str, Qt.TextElideMode.ElideRight, int(avail_w))

        if self.h >= 44.0:
            painter.setFont(title_font)
            painter.setPen(QColor("#f8fafc"))
            painter.drawText(QRectF(text_x, btn_r.top(), avail_w, btn_r.height() * 0.55),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

            painter.setFont(dur_font)
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(QRectF(text_x, btn_r.top() + btn_r.height() * 0.5, avail_w, btn_r.height() * 0.5),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_dur)
        else:
            # Daha basık kartlarda tek satırda başlık ve süreyi göster
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#f8fafc"))
            comb = f"{elided_title} ({dur_str})"
            painter.drawText(QRectF(text_x, 0, avail_w, self.h),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, comb)

        # Seçim ve boyutlandırma tutamaçları
        if self.isSelected():
            sel_pen = QPen(QColor("#38bdf8"), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.cardRect().adjusted(-2, -2, 2, 2), 10.0, 10.0)

            handle_pen = QPen(QColor("#0284c7"), 1.2)
            handle_brush = QBrush(QColor("#ffffff"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            bounds = self.cardRect()
            for h in HANDLES:
                painter.drawRect(h.rect(bounds))

        painter.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.tab_doc:
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0))
            if p_info:
                page_left = p_info.get('left', 0.0)
                page_top = p_info['top']
                page_w = p_info['width']
                page_h = p_info['height']
                min_x = page_left
                max_x = page_left + max(0.0, page_w - self.w)
                min_y = page_top
                max_y = page_top + max(0.0, page_h - self.h)
                clamped_x = max(min_x, min(value.x(), max_x))
                clamped_y = max(min_y, min(value.y(), max_y))
                return QPointF(clamped_x, clamped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h_name = self._get_handle_at(event.pos())
            if h_name:
                self._active_handle = h_name
                self._drag_start_pos = event.scenePos()
                self._drag_start_bounds = QRectF(self.pos().x(), self.pos().y(), self.w, self.h)
                event.accept()
                return

            if self.play_button_rect().contains(event.pos()):
                self.toggle_playback()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle and self._drag_start_pos and self._drag_start_bounds:
            delta = event.scenePos() - self._drag_start_pos
            orig = self._drag_start_bounds

            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info.get('top', 0.0) if p_info else 0.0
            page_w = p_info.get('width', 10000.0) if p_info else 10000.0
            page_h = p_info.get('height', 10000.0) if p_info else 10000.0

            new_x = orig.x()
            new_y = orig.y()
            new_w = orig.width()
            new_h = orig.height()

            min_w = 130.0
            min_h = 38.0
            h = self._active_handle

            if "r" in h:
                new_w = max(min_w, orig.width() + delta.x())
            elif "l" in h:
                diff = min(orig.width() - min_w, delta.x())
                new_x = orig.x() + diff
                new_w = orig.width() - diff

            if "b" in h:
                new_h = max(min_h, orig.height() + delta.y())
            elif "t" in h:
                diff = min(orig.height() - min_h, delta.y())
                new_y = orig.y() + diff
                new_h = orig.height() - diff

            # PDF Sayfa sınırları dışına taşmayı engelle
            new_x = max(page_left, min(new_x, page_left + max(0.0, page_w - min_w)))
            new_y = max(page_top, min(new_y, page_top + max(0.0, page_h - min_h)))
            new_w = max(min_w, min(new_w, max(min_w, page_left + page_w - new_x)))
            new_h = max(min_h, min(new_h, max(min_h, page_top + page_h - new_y)))

            self.prepareGeometryChange()
            self.setPos(new_x, new_y)
            self.w = new_w
            self.h = new_h
            self.update()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            self._drag_start_pos = None
            self._drag_start_bounds = None
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._sync_record()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def toggle_playback(self):
        if not self.audio_bytes:
            return

        if PDFAudioItem._PLAYER is None:
            PDFAudioItem._AUDIO_OUTPUT = QAudioOutput()
            PDFAudioItem._PLAYER = QMediaPlayer()
            PDFAudioItem._PLAYER.setAudioOutput(PDFAudioItem._AUDIO_OUTPUT)

        if self.is_playing:
            PDFAudioItem._PLAYER.stop()
            self.is_playing = False
            self.update()
        else:
            try:
                if not self._temp_file_path or not os.path.exists(self._temp_file_path):
                    ext = self.record.get("format", "wav")
                    tf = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
                    tf.write(self.audio_bytes)
                    tf.close()
                    self._temp_file_path = tf.name

                PDFAudioItem._PLAYER.setSource(QUrl.fromLocalFile(self._temp_file_path))
                PDFAudioItem._AUDIO_OUTPUT.setVolume(1.0)
                PDFAudioItem._PLAYER.play()
                self.is_playing = True
                self.update()

                def on_status_changed(status):
                    if status == QMediaPlayer.MediaStatus.EndOfMedia:
                        self.is_playing = False
                        self.update()
                PDFAudioItem._PLAYER.mediaStatusChanged.connect(on_status_changed)
            except Exception as e:
                print(f"Playback error: {e}")

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1e1e24; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2563eb; }
        """)
        act_play = menu.addAction("Durdur" if self.is_playing else "Oynat")
        act_reset = menu.addAction("Varsayılan Boyuta Dön (180x48)")
        menu.addSeparator()
        act_del = menu.addAction("Ses Kaydını Sil")

        action = menu.exec(event.screenPos())
        if action == act_play:
            self.toggle_playback()
        elif action == act_reset:
            self.prepareGeometryChange()
            dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info.get('top', 0.0) if p_info else 0.0
            page_w = p_info.get('width', 10000.0) if p_info else 10000.0
            page_h = p_info.get('height', 10000.0) if p_info else 10000.0

            target_w = min(180.0 * dpi, page_w)
            target_h = min(48.0 * dpi, page_h)
            cur_x = self.pos().x()
            cur_y = self.pos().y()
            clamped_x = max(page_left, min(cur_x, page_left + max(0.0, page_w - target_w)))
            clamped_y = max(page_top, min(cur_y, page_top + max(0.0, page_h - target_h)))
            self.setPos(clamped_x, clamped_y)
            self.w = target_w
            self.h = target_h
            self._sync_record()
            self.update()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
        elif action == act_del:
            self.delete_self()

    def delete_self(self):
        if self.is_playing and PDFAudioItem._PLAYER:
            PDFAudioItem._PLAYER.stop()
            self.is_playing = False
        if self.tab_doc and self.record in self.tab_doc.drawings:
            self.tab_doc.drawings.remove(self.record)
            if self.scene():
                self.scene().removeItem(self)
            self.tab_doc.push_undo_action({"type": "erase", "deleted_items": [self.record]})
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def _sync_record(self):
        dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
        page_left = p_info.get('left', 0.0) if p_info else 0.0
        page_top = p_info.get('top', 0.0) if p_info else 0.0
        page_pdf_w = (p_info['width'] / dpi) if p_info else 10000.0
        page_pdf_h = (p_info['height'] / dpi) if p_info else 10000.0

        pos = self.pos()
        item_w = min(self.w / dpi, page_pdf_w)
        item_h = min(self.h / dpi, page_pdf_h)
        item_x = max(0.0, min((pos.x() - page_left) / dpi, max(0.0, page_pdf_w - item_w)))
        item_y = max(0.0, min((pos.y() - page_top) / dpi, max(0.0, page_pdf_h - item_h)))

        self.record["x"] = item_x
        self.record["y"] = item_y
        self.record["w"] = item_w
        self.record["h"] = item_h
        self.record["item_ref"] = self


class InternalVideoPlayerDialog(QDialog):
    """
    Belgeye eklenmiş videoları doğrudan uygulama içinde oynatan modern dahili video oynatıcı.
    Oynat/Duraklat, ilerleme arama çubuğu, ses seviyesi ve tam ekran kontrolleri sunar.
    """
    def __init__(self, video_url_or_path: str, title: str = "Video Oynatıcı", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Video Oynatıcı - {title}")
        self.resize(720, 520)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1e293b;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0284c7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #38bdf8;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #7dd3fc;
            }
        """)

        self.video_url_or_path = video_url_or_path
        self.title_text = title

        # Multimedya oynatıcı ve ses çıkışı
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Video Ekranı
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 8px; border: 1px solid #1e293b;")
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget, 1)

        # İlerleme (Seek) Çubuğu ve Süre
        progress_box = QHBoxLayout()
        progress_box.setSpacing(8)

        self.lbl_current_time = QLabel("00:00")
        self.lbl_current_time.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: monospace;")
        progress_box.addWidget(self.lbl_current_time)

        self.slider_progress = QSlider(Qt.Orientation.Horizontal)
        self.slider_progress.setRange(0, 0)
        self.slider_progress.sliderMoved.connect(self._set_position)
        progress_box.addWidget(self.slider_progress, 1)

        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: monospace;")
        progress_box.addWidget(self.lbl_total_time)
        layout.addLayout(progress_box)

        # Kontrol Butonları Çubuğu
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.btn_play_pause = QPushButton("▶ Oynat")
        self.btn_play_pause.setStyleSheet("background-color: #0284c7; color: #ffffff; min-width: 80px;")
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        ctrl_layout.addWidget(self.btn_play_pause)

        self.btn_stop = QPushButton("⏹ Durdur")
        self.btn_stop.clicked.connect(self._stop_video)
        ctrl_layout.addWidget(self.btn_stop)

        ctrl_layout.addSpacing(10)

        # Ses Seviyesi Kontrolleri
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedWidth(36)
        self.btn_mute.clicked.connect(self._toggle_mute)
        ctrl_layout.addWidget(self.btn_mute)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(80)
        self.audio_output.setVolume(0.8)
        self.slider_volume.setFixedWidth(100)
        self.slider_volume.valueChanged.connect(self._set_volume)
        ctrl_layout.addWidget(self.slider_volume)

        ctrl_layout.addStretch()

        # Harici Tarayıcı / Oynatıcı Butonu
        self.btn_external = QPushButton("Harici / Tarayıcıda Aç")
        self.btn_external.setStyleSheet("background-color: transparent; color: #38bdf8; border: 1px solid #0284c7; font-size: 11px;")
        self.btn_external.clicked.connect(self._open_external)
        ctrl_layout.addWidget(self.btn_external)

        self.btn_fullscreen = QPushButton("⛶ Tam Ekran")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        ctrl_layout.addWidget(self.btn_fullscreen)

        layout.addLayout(ctrl_layout)

        # Sinyal bağlantıları
        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # Videoyu yükle ve başlat
        self._load_and_play()

    def _load_and_play(self):
        if not self.video_url_or_path:
            return
        if os.path.exists(self.video_url_or_path):
            self.player.setSource(QUrl.fromLocalFile(self.video_url_or_path))
        else:
            self.player.setSource(QUrl(self.video_url_or_path))
        self.player.play()

    def _toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _stop_video(self):
        self.player.stop()

    def _toggle_mute(self):
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        self.btn_mute.setText("🔇" if not is_muted else "🔊")

    def _set_volume(self, val: int):
        vol = max(0.0, min(1.0, float(val) / 100.0))
        self.audio_output.setVolume(vol)
        if self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.btn_mute.setText("🔊")

    def _set_position(self, position: int):
        self.player.setPosition(position)

    def _position_changed(self, position: int):
        if not self.slider_progress.isSliderDown():
            self.slider_progress.setValue(position)
        self.lbl_current_time.setText(self._format_time(position))

    def _duration_changed(self, duration: int):
        self.slider_progress.setRange(0, duration)
        self.lbl_total_time.setText(self._format_time(duration))

    def _playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("⏸ Duraklat")
            self.btn_play_pause.setStyleSheet("background-color: #ea580c; color: #ffffff; min-width: 80px;")
        else:
            self.btn_play_pause.setText("▶ Oynat")
            self.btn_play_pause.setStyleSheet("background-color: #0284c7; color: #ffffff; min-width: 80px;")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶ Tam Ekran")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("⛶ Normale Dön")

    def _open_external(self):
        import webbrowser
        try:
            if self.video_url_or_path.startswith("http://") or self.video_url_or_path.startswith("https://"):
                webbrowser.open(self.video_url_or_path)
            elif os.path.exists(self.video_url_or_path):
                os.startfile(self.video_url_or_path)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Harici oynatıcı açılamadı: {e}")

    def _on_player_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.btn_external.setText("Tarayıcıda Aç (Önerilen)")
            self.btn_external.setStyleSheet("background-color: #dc2626; color: #ffffff; font-weight: bold; font-size: 11px;")

    def _format_time(self, ms: int) -> str:
        secs = ms // 1000
        mins = secs // 60
        secs = secs % 60
        return f"{mins:02d}:{secs:02d}"

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)


class PDFVideoItem(QGraphicsItem):
    """
    PDF üzerine yerleştirilen şık, modern ve boyutlandırılabilir video önizleme kartı.
    Tıklandığında veya çift tıklandığında dahili modern video oynatıcıda (QVideoWidget) oynatır.
    Tutamaçlarla serbestçe veya en-boy oranı korunarak boyutlandırılabilir.
    """
    _ACTIVE_PLAYER_DIALOG: Optional[InternalVideoPlayerDialog] = None

    def __init__(self, tab_doc, record: Dict[str, Any]):
        super().__init__()
        self.tab_doc = tab_doc
        self.record = record

        dpi = getattr(tab_doc, 'base_render_dpi', 1.5)
        self.w = max(120.0, float(record.get("w", 200.0)) * dpi)
        self.h = max(70.0, float(record.get("h", 120.0)) * dpi)
        self.video_url = str(record.get("video_url", ""))
        self.title = str(record.get("title", "Video"))
        self.keep_aspect_ratio = bool(record.get("keep_aspect", True))
        self.aspect_ratio = self.w / max(1.0, self.h)

        self.thumbnail_pixmap = QPixmap()
        thumb_bytes = record.get("thumbnail_bytes")
        if thumb_bytes:
            img = QImage()
            img.loadFromData(thumb_bytes)
            self.thumbnail_pixmap = QPixmap.fromImage(img)

        # Boyutlandırma durumu
        self._active_handle: Optional[str] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_bounds: Optional[QRectF] = None

        self.setZValue(15)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        pad = 8.0
        return QRectF(-pad, -pad, self.w + pad * 2, self.h + pad * 2)

    def cardRect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def play_button_center(self) -> QPointF:
        return QPointF(self.w / 2.0, self.h / 2.0)

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        bounds = self.cardRect()
        for h in HANDLES:
            if h.rect(bounds).contains(pos):
                return h.name
        return None

    def hoverMoveEvent(self, event):
        h_name = self._get_handle_at(event.pos())
        if h_name:
            for h in HANDLES:
                if h.name == h_name:
                    self.setCursor(h.cursor_shape)
                    return
        else:
            cx = self.w / 2.0
            cy = self.h / 2.0
            dist = math.hypot(event.pos().x() - cx, event.pos().y() - cy)
            if dist <= 26.0:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self.cardRect().contains(event.pos()):
                self.setCursor(Qt.CursorShape.SizeAllCursor if self.isSelected() else Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Kart arkaplanı ve kapak resmi
        clip_path = QPainterPath()
        clip_path.addRoundedRect(self.cardRect(), 8.0, 8.0)
        painter.setClipPath(clip_path)

        if not self.thumbnail_pixmap.isNull():
            painter.drawPixmap(self.cardRect().toRect(), self.thumbnail_pixmap)
        else:
            grad = QLinearGradient(0, 0, self.w, self.h)
            grad.setColorAt(0.0, QColor("#18181b"))
            grad.setColorAt(1.0, QColor("#09090b"))
            painter.fillRect(self.cardRect(), grad)

        # Koyu film efekti katmanı
        painter.fillRect(self.cardRect(), QColor(0, 0, 0, 70))

        # Ortada büyük Play butonu
        cx = self.w / 2.0
        cy = self.h / 2.0
        btn_r = min(26.0, max(16.0, min(self.w, self.h) * 0.22))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.drawEllipse(QPointF(cx, cy), btn_r, btn_r)

        # Play üçgeni
        tri = QPainterPath()
        tri_size = btn_r * 0.45
        tri.moveTo(cx - tri_size * 0.5, cy - tri_size * 0.8)
        tri.lineTo(cx + tri_size * 0.8, cy)
        tri.lineTo(cx - tri_size * 0.5, cy + tri_size * 0.8)
        tri.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#38bdf8")))
        painter.drawPath(tri)

        # Alt başlık bandı
        painter.setClipRect(self.cardRect())
        banner_h = min(26.0, max(18.0, self.h * 0.24))
        banner_rect = QRectF(0, self.h - banner_h, self.w, banner_h)
        painter.fillRect(banner_rect, QColor(15, 23, 42, 220))

        title_font = QFont("Arial", 9, QFont.Weight.Bold)
        fm = QFontMetrics(title_font)
        elided_title = fm.elidedText(self.title, Qt.TextElideMode.ElideRight, int(self.w - 16))
        painter.setPen(QColor("#f8fafc"))
        painter.setFont(title_font)
        painter.drawText(banner_rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

        painter.restore()

        # Seçim ve boyutlandırma tutamaçları
        if self.isSelected():
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            sel_pen = QPen(QColor("#38bdf8"), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.cardRect().adjusted(-2, -2, 2, 2), 10.0, 10.0)

            handle_pen = QPen(QColor("#0284c7"), 1.2)
            handle_brush = QBrush(QColor("#ffffff"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            bounds = self.cardRect()
            for h in HANDLES:
                painter.drawRect(h.rect(bounds))
            painter.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.tab_doc:
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0))
            if p_info:
                page_left = p_info.get('left', 0.0)
                page_top = p_info['top']
                page_w = p_info['width']
                page_h = p_info['height']
                min_x = page_left
                max_x = page_left + max(0.0, page_w - self.w)
                min_y = page_top
                max_y = page_top + max(0.0, page_h - self.h)
                clamped_x = max(min_x, min(value.x(), max_x))
                clamped_y = max(min_y, min(value.y(), max_y))
                return QPointF(clamped_x, clamped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h_name = self._get_handle_at(event.pos())
            if h_name:
                self._active_handle = h_name
                self._drag_start_pos = event.scenePos()
                self._drag_start_bounds = QRectF(self.pos().x(), self.pos().y(), self.w, self.h)
                event.accept()
                return

            cx = self.w / 2.0
            cy = self.h / 2.0
            dist = math.hypot(event.pos().x() - cx, event.pos().y() - cy)
            if dist <= 26.0:
                self.play_internal_video()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_internal_video()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle and self._drag_start_pos and self._drag_start_bounds:
            delta = event.scenePos() - self._drag_start_pos
            orig = self._drag_start_bounds

            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info['top'] if p_info else 0.0
            page_w = p_info['width'] if p_info else 10000.0
            page_h = p_info['height'] if p_info else 10000.0

            new_x = orig.x()
            new_y = orig.y()
            new_w = orig.width()
            new_h = orig.height()

            min_w = 120.0
            min_h = 70.0
            h = self._active_handle

            keep_aspect = self.keep_aspect_ratio and not bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

            if keep_aspect and self.aspect_ratio > 0:
                if "r" in h:
                    new_w = max(min_w, orig.width() + delta.x())
                    new_h = max(min_h, new_w / self.aspect_ratio)
                elif "l" in h:
                    diff = min(orig.width() - min_w, delta.x())
                    new_x = orig.x() + diff
                    new_w = orig.width() - diff
                    new_h = max(min_h, new_w / self.aspect_ratio)

                if "b" in h and not ("r" in h):
                    new_h = max(min_h, orig.height() + delta.y())
                    new_w = max(min_w, new_h * self.aspect_ratio)
                elif "t" in h and not ("l" in h):
                    diff = min(orig.height() - min_h, delta.y())
                    new_y = orig.y() + diff
                    new_h = orig.height() - diff
                    new_w = max(min_w, new_h * self.aspect_ratio)
            else:
                if "r" in h:
                    new_w = max(min_w, orig.width() + delta.x())
                elif "l" in h:
                    diff = min(orig.width() - min_w, delta.x())
                    new_x = orig.x() + diff
                    new_w = orig.width() - diff

                if "b" in h:
                    new_h = max(min_h, orig.height() + delta.y())
                elif "t" in h:
                    diff = min(orig.height() - min_h, delta.y())
                    new_y = orig.y() + diff
                    new_h = orig.height() - diff

                if new_h > 0:
                    self.aspect_ratio = new_w / new_h

            # PDF Sayfa sınırları dışına taşmayı engelle
            if new_x < page_left:
                excess = page_left - new_x
                new_x = page_left
                new_w = max(min_w, new_w - excess)
                if keep_aspect and self.aspect_ratio > 0:
                    new_h = new_w / self.aspect_ratio
            if new_y < page_top:
                excess = page_top - new_y
                new_y = page_top
                new_h = max(min_h, new_h - excess)
                if keep_aspect and self.aspect_ratio > 0:
                    new_w = new_h * self.aspect_ratio

            if keep_aspect and self.aspect_ratio > 0:
                if new_x + new_w > page_left + page_w:
                    new_w = max(min_w, page_left + page_w - new_x)
                    new_h = new_w / self.aspect_ratio
                if new_y + new_h > page_top + page_h:
                    new_h = max(min_h, page_top + page_h - new_y)
                    new_w = new_h * self.aspect_ratio
            else:
                new_w = max(min_w, min(new_w, max(min_w, page_left + page_w - new_x)))
                new_h = max(min_h, min(new_h, max(min_h, page_top + page_h - new_y)))

            new_x = max(page_left, min(new_x, page_left + max(0.0, page_w - min_w)))
            new_y = max(page_top, min(new_y, page_top + max(0.0, page_h - min_h)))

            self.prepareGeometryChange()
            self.setPos(new_x, new_y)
            self.w = max(min_w, new_w)
            self.h = max(min_h, new_h)
            self.update()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed_throttled'):
                self.tab_doc.notify_drawings_changed_throttled(self.record.get("page"))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            self._drag_start_pos = None
            self._drag_start_bounds = None
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._sync_record()
        if hasattr(self.tab_doc, 'notify_drawings_changed'):
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def play_internal_video(self):
        """Videoyu doğrudan dahili modern video oynatıcı penceresinde açar."""
        if not self.video_url:
            return
        if PDFVideoItem._ACTIVE_PLAYER_DIALOG:
            try:
                PDFVideoItem._ACTIVE_PLAYER_DIALOG.close()
            except Exception:
                pass
        parent_widget = getattr(self.tab_doc, 'main_window', None)
        dlg = InternalVideoPlayerDialog(self.video_url, title=self.title, parent=parent_widget)
        PDFVideoItem._ACTIVE_PLAYER_DIALOG = dlg
        dlg.show()

    def open_video(self):
        """Harici oynatıcı veya tarayıcıda açar."""
        if not self.video_url:
            return
        import webbrowser
        try:
            if self.video_url.startswith("http://") or self.video_url.startswith("https://"):
                webbrowser.open(self.video_url)
            elif os.path.exists(self.video_url):
                os.startfile(self.video_url)
        except Exception as e:
            print(f"Cannot open video: {e}")

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1e1e24; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #2563eb; }
        """)
        act_internal = menu.addAction("Videoyu Dahili Oynat")
        act_open = menu.addAction("Harici Oynatıcıda / Tarayıcıda Aç")
        menu.addSeparator()
        act_aspect = menu.addAction("En-Boy Oranını Koru")
        act_aspect.setCheckable(True)
        act_aspect.setChecked(self.keep_aspect_ratio)
        act_reset = menu.addAction("Varsayılan Boyuta Dön (200x120)")
        menu.addSeparator()
        act_del = menu.addAction("Videoyu Sil")

        action = menu.exec(event.screenPos())
        if action == act_internal:
            self.play_internal_video()
        elif action == act_open:
            self.open_video()
        elif action == act_aspect:
            self.keep_aspect_ratio = act_aspect.isChecked()
            self._sync_record()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
        elif action == act_reset:
            self.prepareGeometryChange()
            dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
            p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
            page_left = p_info.get('left', 0.0) if p_info else 0.0
            page_top = p_info.get('top', 0.0) if p_info else 0.0
            page_w = p_info.get('width', 10000.0) if p_info else 10000.0
            page_h = p_info.get('height', 10000.0) if p_info else 10000.0

            target_w = min(200.0 * dpi, page_w)
            target_h = min(120.0 * dpi, page_h)
            cur_x = self.pos().x()
            cur_y = self.pos().y()
            clamped_x = max(page_left, min(cur_x, page_left + max(0.0, page_w - target_w)))
            clamped_y = max(page_top, min(cur_y, page_top + max(0.0, page_h - target_h)))
            self.setPos(clamped_x, clamped_y)
            self.w = target_w
            self.h = target_h
            self.aspect_ratio = self.w / max(1.0, self.h)
            self._sync_record()
            self.update()
            if hasattr(self.tab_doc, 'notify_drawings_changed'):
                self.tab_doc.notify_drawings_changed(self.record.get("page"))
        elif action == act_del:
            self.delete_self()

    def delete_self(self):
        if self.tab_doc and self.record in self.tab_doc.drawings:
            self.tab_doc.drawings.remove(self.record)
            if self.scene():
                self.scene().removeItem(self)
            self.tab_doc.push_undo_action({"type": "erase", "deleted_items": [self.record]})
            self.tab_doc.notify_drawings_changed(self.record.get("page"))

    def _sync_record(self):
        dpi = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        p_info = getattr(self.tab_doc, 'page_positions', {}).get(self.record.get("page", 0)) if self.tab_doc else None
        page_left = p_info.get('left', 0.0) if p_info else 0.0
        page_top = p_info.get('top', 0.0) if p_info else 0.0
        page_pdf_w = (p_info['width'] / dpi) if p_info else 10000.0
        page_pdf_h = (p_info['height'] / dpi) if p_info else 10000.0

        pos = self.pos()
        item_w = min(self.w / dpi, page_pdf_w)
        item_h = min(self.h / dpi, page_pdf_h)
        item_x = max(0.0, min((pos.x() - page_left) / dpi, max(0.0, page_pdf_w - item_w)))
        item_y = max(0.0, min((pos.y() - page_top) / dpi, max(0.0, page_pdf_h - item_h)))

        self.record["x"] = item_x
        self.record["y"] = item_y
        self.record["w"] = item_w
        self.record["h"] = item_h
        self.record["keep_aspect"] = self.keep_aspect_ratio
        self.record["item_ref"] = self
