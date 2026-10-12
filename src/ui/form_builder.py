import math
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QGraphicsItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QWidget, QMenu, QMessageBox
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QCursor, QPainterPath
)
from PyQt6.QtCore import Qt, QRectF, QPointF

import fitz
from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme


class FormResizeHandle:
    """Form alanı boyutlandırma tutamacı."""
    HANDLE_SIZE = 6.5

    def __init__(self, name: str, cursor_shape: Qt.CursorShape):
        self.name = name
        self.cursor_shape = cursor_shape

    def rect(self, bounds: QRectF, compact: bool = False) -> QRectF:
        s = 4.5 if compact else self.HANDLE_SIZE
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


FORM_HANDLES = [
    FormResizeHandle("tl", Qt.CursorShape.SizeFDiagCursor),
    FormResizeHandle("t", Qt.CursorShape.SizeVerCursor),
    FormResizeHandle("tr", Qt.CursorShape.SizeBDiagCursor),
    FormResizeHandle("r", Qt.CursorShape.SizeHorCursor),
    FormResizeHandle("br", Qt.CursorShape.SizeFDiagCursor),
    FormResizeHandle("b", Qt.CursorShape.SizeVerCursor),
    FormResizeHandle("bl", Qt.CursorShape.SizeBDiagCursor),
    FormResizeHandle("l", Qt.CursorShape.SizeHorCursor),
]


class AuraFormFieldDesignerItem(QGraphicsItem):
    """
    Form Hazırlama (Prepare Form) modunda PDF sayfası üzerinde doğrudan
    seçilebilen, taşınabilen, boyutlandırılabilen profesyonel form alanı öğesi.
    """
    def __init__(self, tab_doc, page_idx: int, widget_data: Dict[str, Any]):
        super().__init__()
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.field_name = widget_data.get("name", "Field")
        self.field_type = widget_data.get("type", "text").lower()
        self.field_value = widget_data.get("value", "")
        self.tooltip = widget_data.get("tooltip", "")
        self.is_readonly = bool(widget_data.get("readonly", False))
        self.is_required = bool(widget_data.get("required", False))
        self.is_multiline = bool(widget_data.get("multiline", False))
        self.choices: List[str] = list(widget_data.get("choices", []))
        self.font_size = float(widget_data.get("font_size", 11.0))
        self.setToolTip(f"{self.field_name} ({self.field_type})")

        scale = getattr(tab_doc, 'base_render_dpi', 1.5)
        p_info = tab_doc.page_positions.get(page_idx, {})
        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)

        rect = widget_data.get("rect")
        if isinstance(rect, fitz.Rect):
            self.w = max(18.0, rect.width * scale)
            self.h = max(18.0, rect.height * scale)
            self.setPos(rect.x0 * scale + page_left, rect.y0 * scale + page_top)
        else:
            self.w = 160.0
            self.h = 28.0
            self.setPos(page_left + 100.0, page_top + 100.0)

        self.setZValue(30)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)

        self._active_handle: Optional[str] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_bounds: Optional[QRectF] = None
        self._initial_pos: Optional[QPointF] = None

    def boundingRect(self) -> QRectF:
        pad = 12.0
        return QRectF(-pad, -pad, self.w + pad * 2.0, self.h + pad * 2.0)

    def fieldRect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def _is_compact(self) -> bool:
        return self.w <= 34.0 or self.h <= 34.0

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        if not self.isSelected():
            return None
        bounds = self.fieldRect()
        is_compact = self._is_compact()
        for h in FORM_HANDLES:
            if is_compact and len(h.name) == 1:
                # Küçük alanlarda kenar orta tutamaçlarını atla, yalnızca köşeler
                continue
            if h.rect(bounds, compact=is_compact).contains(pos):
                return h.name
        return None

    def hoverMoveEvent(self, event):
        h_name = self._get_handle_at(event.pos())
        if h_name:
            for h in FORM_HANDLES:
                if h.name == h_name:
                    self.setCursor(h.cursor_shape)
                    return
        elif self.fieldRect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor if self.isSelected() else Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            h_name = self._get_handle_at(event.pos())
            if h_name:
                self._active_handle = h_name
                self._drag_start_pos = event.scenePos()
                self._drag_start_bounds = QRectF(0, 0, self.w, self.h)
                self._initial_pos = self.pos()
                event.accept()
                return

        super().mousePressEvent(event)
        self._notify_selection()

    def mouseMoveEvent(self, event):
        if self._active_handle and self._drag_start_pos and self._drag_start_bounds and self._initial_pos:
            delta = event.scenePos() - self._drag_start_pos
            orig_rect = self._drag_start_bounds
            x0 = self._initial_pos.x()
            y0 = self._initial_pos.y()
            w = orig_rect.width()
            h = orig_rect.height()

            handle = self._active_handle
            min_dim = 16.0 if self.field_type in ("checkbox", "radio") else 18.0
            if "r" in handle:
                w = max(min_dim, orig_rect.width() + delta.x())
            if "b" in handle:
                h = max(min_dim, orig_rect.height() + delta.y())
            if "l" in handle:
                diff_x = delta.x()
                if orig_rect.width() - diff_x >= min_dim:
                    x0 = self._initial_pos.x() + diff_x
                    w = orig_rect.width() - diff_x
            if "t" in handle:
                diff_y = delta.y()
                if orig_rect.height() - diff_y >= min_dim:
                    y0 = self._initial_pos.y() + diff_y
                    h = orig_rect.height() - diff_y

            # Sayfa sınırları içinde tut
            p_info = self.tab_doc.page_positions.get(self.page_idx, {})
            if p_info:
                p_left = p_info.get('left', 0.0)
                p_top = p_info.get('top', 0.0)
                p_w = p_info.get('width', 595.0)
                p_h = p_info.get('height', 842.0)
                x0 = max(p_left, min(x0, p_left + p_w - min_dim))
                y0 = max(p_top, min(y0, p_top + p_h - min_dim))
                w = min(w, (p_left + p_w) - x0)
                h = min(h, (p_top + p_h) - y0)

            self.prepareGeometryChange()
            self.w = max(min_dim, w)
            self.h = max(min_dim, h)
            self.setPos(x0, y0)
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            self._sync_geometry_to_pymupdf()
            event.accept()
            if self.scene():
                self.scene().update()
            return
        super().mouseReleaseEvent(event)
        self._sync_geometry_to_pymupdf()
        if self.scene():
            self.scene().update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.tab_doc:
            p_info = self.tab_doc.page_positions.get(self.page_idx)
            if p_info:
                page_left = p_info.get('left', 0.0)
                page_top = p_info.get('top', 0.0)
                page_w = p_info.get('width', 595.0)
                page_h = p_info.get('height', 842.0)
                min_x = page_left
                max_x = page_left + max(0.0, page_w - self.w)
                min_y = page_top
                max_y = page_top + max(0.0, page_h - self.h)
                clamped_x = max(min_x, min(value.x(), max_x))
                clamped_y = max(min_y, min(value.y(), max_y))
                return QPointF(clamped_x, clamped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange and value:
            self._notify_selection()
        return super().itemChange(change, value)

    def _notify_selection(self):
        main_win = getattr(self.tab_doc, 'main_window', None)
        if main_win and hasattr(main_win, 'modern_left_sidebar'):
            drawer = getattr(main_win.modern_left_sidebar, 'prepare_form_drawer', None)
            if drawer and hasattr(drawer, 'select_field_in_list'):
                drawer.select_field_in_list(self.field_name, self.page_idx)

    def _sync_geometry_to_pymupdf(self):
        """Mevcut sahne koordinatlarını PyMuPDF widget rect değerine yazar."""
        if not self.tab_doc or not self.tab_doc.doc:
            return
        if self.page_idx >= len(self.tab_doc.doc):
            return

        p_info = self.tab_doc.page_positions.get(self.page_idx, {})
        scale = getattr(self.tab_doc, 'base_render_dpi', 1.5)
        page_left = p_info.get('left', 0.0)
        page_top = p_info.get('top', 0.0)

        pdf_x0 = (self.pos().x() - page_left) / scale
        pdf_y0 = (self.pos().y() - page_top) / scale
        pdf_x1 = pdf_x0 + (self.w / scale)
        pdf_y1 = pdf_y0 + (self.h / scale)
        new_rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)

        try:
            page = self.tab_doc.doc[self.page_idx]
            for w in page.widgets():
                if w.field_name == self.field_name:
                    w.rect = new_rect
                    w.update()
                    break
            self.tab_doc.set_modified(True)
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        self.open_properties_dialog()
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #1e293b; color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)
        act_props = menu.addAction(ModernIconFactory.icon_settings(), LanguageManager.tr("form_action_edit_selected"))
        act_dup = menu.addAction(ModernIconFactory.icon_add_page(), LanguageManager.tr("form_field_duplicate"))
        act_del = menu.addAction(ModernIconFactory.icon_trash("#ef4444"), LanguageManager.tr("form_action_delete_selected"))

        chosen = menu.exec(event.screenPos())
        if chosen == act_props:
            self.open_properties_dialog()
        elif chosen == act_dup:
            if self.tab_doc and hasattr(self.tab_doc, 'duplicate_form_field'):
                self.tab_doc.duplicate_form_field(self)
        elif chosen == act_del:
            if self.tab_doc and hasattr(self.tab_doc, 'delete_form_field'):
                self.tab_doc.delete_form_field(self.page_idx, self.field_name)

    def open_properties_dialog(self):
        main_win = getattr(self.tab_doc, 'main_window', None)
        dlg = AuraFormFieldPropertiesDialog(designer_item=self, parent=main_win)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.update()
            if main_win and hasattr(main_win, 'modern_left_sidebar'):
                drawer = getattr(main_win.modern_left_sidebar, 'prepare_form_drawer', None)
                if drawer:
                    drawer.refresh_fields_list()

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        is_sel = self.isSelected()
        f_rect = self.fieldRect()

        # 1. Gövde Arka Planı (Şeffaf modern vurgulama)
        fill_color = QColor(2, 132, 199, 36) if is_sel else QColor(147, 51, 234, 20)
        painter.fillRect(f_rect, fill_color)

        # 2. Kenarlık Çerçevesi
        border_col = QColor("#0284c7") if is_sel else QColor("#9333ea")
        pen_style = Qt.PenStyle.SolidLine if is_sel else Qt.PenStyle.DashLine
        pen = QPen(border_col, 1.8 if is_sel else 1.2, pen_style)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawRect(f_rect)

        is_compact = self._is_compact()

        # 3. İçerik Önizleme
        if self.field_type == "checkbox":
            box_s = min(16.0, max(12.0, min(self.w - 4.0, self.h - 4.0)))
            cx = (self.w - box_s) / 2.0
            cy = (self.h - box_s) / 2.0
            cb_rect = QRectF(cx, cy, box_s, box_s)
            painter.setPen(QPen(border_col, 1.4))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(cb_rect, 2.5, 2.5)
            if self.field_value:
                painter.setBrush(QBrush(border_col))
                painter.drawRoundedRect(cb_rect.adjusted(2.5, 2.5, -2.5, -2.5), 1.5, 1.5)

        elif self.field_type == "radio":
            rad_s = min(16.0, max(12.0, min(self.w - 4.0, self.h - 4.0)))
            cx = (self.w - rad_s) / 2.0
            cy = (self.h - rad_s) / 2.0
            rb_rect = QRectF(cx, cy, rad_s, rad_s)
            painter.setPen(QPen(border_col, 1.4))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(rb_rect)
            if self.field_value:
                painter.setBrush(QBrush(border_col))
                painter.drawEllipse(rb_rect.adjusted(3.0, 3.0, -3.0, -3.0))

        elif self.field_type == "text":
            display_txt = str(self.field_value if self.field_value else self.field_name)
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QPen(QColor(15, 23, 42, 220) if self.field_value else QColor(100, 116, 139, 200)))
            content_rect = f_rect.adjusted(6, 2, -6, -2)
            align = Qt.AlignmentFlag.AlignLeft | (Qt.AlignmentFlag.AlignTop if self.is_multiline else Qt.AlignmentFlag.AlignVCenter)
            painter.drawText(content_rect, align, display_txt)

        elif self.field_type == "combobox":
            cur_txt = str(self.field_value or (self.choices[0] if self.choices else self.field_name))
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QPen(QColor(15, 23, 42, 220) if self.field_value else QColor(100, 116, 139, 200)))
            content_rect = f_rect.adjusted(6, 2, -22, -2)
            painter.drawText(content_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, cur_txt)
            arrow_x = self.w - 14.0
            arrow_y = self.h / 2.0
            path = QPainterPath()
            path.moveTo(arrow_x - 3.5, arrow_y - 2.0)
            path.lineTo(arrow_x + 3.5, arrow_y - 2.0)
            path.lineTo(arrow_x, arrow_y + 3.0)
            path.closeSubpath()
            painter.setBrush(QBrush(border_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)

        elif self.field_type == "signature":
            painter.setPen(QPen(QColor(100, 116, 139, 160), 1.0, Qt.PenStyle.DashLine))
            line_y = self.h - 10.0
            painter.drawLine(QPointF(8.0, line_y), QPointF(self.w - 8.0, line_y))
            painter.setPen(QPen(border_col))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(f_rect.adjusted(6, 2, -6, -12), Qt.AlignmentFlag.AlignCenter, LanguageManager.tr("form_field_signature"))

        # 4. Yeterince geniş/yüksek alanlarda sağ üstte rozet etiketi göster
        if not is_compact and self.h >= 32.0 and self.w >= 60.0:
            type_abbr = {
                "text": "T",
                "checkbox": "✓",
                "radio": "●",
                "combobox": "▼",
                "signature": "✍"
            }.get(self.field_type, "F")
            tag_text = f"[{type_abbr}] {self.field_name}"
            font = QFont("Segoe UI", 7, QFont.Weight.Bold)
            painter.setFont(font)
            fm = QFontMetrics(font)
            tw = min(fm.horizontalAdvance(tag_text) + 8.0, self.w - 8.0)
            tag_rect = QRectF(self.w - tw - 4.0, 2.0, tw, 13.0)
            tag_bg = QColor(2, 132, 199, 210) if is_sel else QColor(147, 51, 234, 180)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(tag_bg))
            painter.drawRoundedRect(tag_rect, 3.0, 3.0)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag_text)

        # 5. Boyutlandırma Tutamaçları (Yalnızca Seçiliyken)
        if is_sel:
            bounds = self.fieldRect()
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(border_col, 1.4))
            for h in FORM_HANDLES:
                if is_compact and len(h.name) == 1:
                    continue
                painter.drawRect(h.rect(bounds, compact=is_compact))

        painter.restore()


class AuraFormFieldGhostItem(QGraphicsItem):
    """Yeni form alanı yerleştirilirken fareyi takip eden hayalet önizleme."""
    def __init__(self, field_type: str, w: float = 160.0, h: float = 28.0):
        super().__init__()
        self.field_type = field_type
        self.w = w
        self.h = h
        self.setZValue(99)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self._tag_text = LanguageManager.tr("form_click_to_place")
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        fm = QFontMetrics(font)
        self._pill_tw = max(180.0, float(fm.horizontalAdvance(self._tag_text) + 20.0))

    def boundingRect(self) -> QRectF:
        pill_x = (self.w - self._pill_tw) / 2.0
        min_x = min(0.0, pill_x) - 10.0
        max_x = max(self.w, pill_x + self._pill_tw) + 10.0
        min_y = -10.0
        max_y = self.h + 30.0
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        f_rect = QRectF(0, 0, self.w, self.h)

        # Şeffaf mavi dolgu & kesikli kenarlık
        painter.fillRect(f_rect, QColor(2, 132, 199, 45))
        painter.setPen(QPen(QColor("#0284c7"), 1.8, Qt.PenStyle.DashLine))
        painter.drawRect(f_rect)

        # Alan türüne göre iç simge/önizleme
        if self.field_type == "checkbox":
            box_s = min(15.0, min(self.w - 4.0, self.h - 4.0))
            cb_rect = QRectF((self.w - box_s) / 2.0, (self.h - box_s) / 2.0, box_s, box_s)
            painter.setPen(QPen(QColor("#0284c7"), 1.4))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawRoundedRect(cb_rect, 2.0, 2.0)
        elif self.field_type == "radio":
            rad_s = min(15.0, min(self.w - 4.0, self.h - 4.0))
            rb_rect = QRectF((self.w - rad_s) / 2.0, (self.h - rad_s) / 2.0, rad_s, rad_s)
            painter.setPen(QPen(QColor("#0284c7"), 1.4))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawEllipse(rb_rect)
        elif self.field_type == "text":
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QPen(QColor(2, 132, 199, 180)))
            painter.drawText(f_rect.adjusted(6, 2, -6, -2), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, LanguageManager.tr("form_field_text"))

        # Bilgilendirme hapı (Hap etiket)
        pill_x = (self.w - self._pill_tw) / 2.0
        pill_rect = QRectF(pill_x, self.h + 3.0, self._pill_tw, 16.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 225)))
        painter.drawRoundedRect(pill_rect, 8.0, 8.0)

        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, self._tag_text)
        painter.restore()


class AuraFormFieldPropertiesDialog(QDialog):
    """
    Form Alanı Özellikleri Düzenleme Diyaloğu.
    Ad, ipucu, varsayılan değer, yazı boyutu, salt okunur, zorunlu alan
    ve açılır liste seçenekleri bu ekrandan kusursuz yönetilir.
    """
    def __init__(self, designer_item: AuraFormFieldDesignerItem, parent=None):
        super().__init__(parent)
        self.item = designer_item
        self.setWindowTitle(LanguageManager.tr("form_props_title"))
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Genel Bilgiler Grubu
        grp_gen = QGroupBox(LanguageManager.tr("settings_general"))
        f_layout = QFormLayout(grp_gen)
        f_layout.setSpacing(10)

        self.txt_name = QLineEdit(self.item.field_name)
        f_layout.addRow(LanguageManager.tr("form_prop_name") + ":", self.txt_name)

        self.txt_tooltip = QLineEdit(self.item.tooltip)
        f_layout.addRow(LanguageManager.tr("form_prop_tooltip") + ":", self.txt_tooltip)

        lbl_type_val = QLabel(LanguageManager.tr(f"form_field_{self.item.field_type}"))
        lbl_type_val.setStyleSheet("font-weight: bold; color: #0284c7;")
        f_layout.addRow(LanguageManager.tr("form_prop_type") + ":", lbl_type_val)

        layout.addWidget(grp_gen)

        # Değer ve Görünüm Grubu
        grp_val = QGroupBox(LanguageManager.tr("display_mode"))
        f_val = QFormLayout(grp_val)
        f_val.setSpacing(10)

        if self.item.field_type == "text":
            self.txt_val = QLineEdit(str(self.item.field_value or ""))
            f_val.addRow(LanguageManager.tr("form_prop_value") + ":", self.txt_val)

            self.cmb_font_size = QComboBox()
            for s in ["8", "9", "10", "11", "12", "14", "16", "18", "24"]:
                self.cmb_font_size.addItem(s)
            curr_fs = str(int(round(self.item.font_size)))
            idx = self.cmb_font_size.findText(curr_fs)
            if idx >= 0:
                self.cmb_font_size.setCurrentIndex(idx)
            f_val.addRow(LanguageManager.tr("form_prop_font_size") + ":", self.cmb_font_size)

            self.chk_multiline = QCheckBox(LanguageManager.tr("form_prop_multiline"))
            self.chk_multiline.setChecked(self.item.is_multiline)
            f_val.addRow("", self.chk_multiline)

        elif self.item.field_type in ("checkbox", "radio"):
            self.chk_val = QCheckBox(LanguageManager.tr("form_prop_value"))
            self.chk_val.setChecked(bool(self.item.field_value))
            f_val.addRow("", self.chk_val)

        elif self.item.field_type == "combobox":
            self.list_choices = QListWidget()
            self.list_choices.setFixedHeight(90)
            for c in self.item.choices:
                self.list_choices.addItem(str(c))
            f_val.addRow(LanguageManager.tr("form_prop_choices") + ":", self.list_choices)

            h_opt = QHBoxLayout()
            self.txt_new_choice = QLineEdit()
            self.txt_new_choice.setPlaceholderText(LanguageManager.tr("form_prop_add_choice"))
            btn_add = QPushButton("+")
            btn_add.setFixedWidth(30)
            btn_add.clicked.connect(self._add_choice)
            btn_del = QPushButton("-")
            btn_del.setFixedWidth(30)
            btn_del.clicked.connect(self._remove_choice)
            h_opt.addWidget(self.txt_new_choice)
            h_opt.addWidget(btn_add)
            h_opt.addWidget(btn_del)
            f_val.addRow("", h_opt)

        self.chk_readonly = QCheckBox(LanguageManager.tr("form_prop_readonly"))
        self.chk_readonly.setChecked(self.item.is_readonly)
        f_val.addRow("", self.chk_readonly)

        self.chk_required = QCheckBox(LanguageManager.tr("form_prop_required"))
        self.chk_required.setChecked(self.item.is_required)
        f_val.addRow("", self.chk_required)

        layout.addWidget(grp_val)

        # Alt Butonlar
        h_btn = QHBoxLayout()
        h_btn.addStretch(1)

        btn_cancel = QPushButton(LanguageManager.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton(LanguageManager.tr("save_btn"))
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        h_btn.addWidget(btn_save)

        layout.addLayout(h_btn)
        apply_dialog_theme(self, parent)

    def _add_choice(self):
        txt = self.txt_new_choice.text().strip()
        if txt:
            self.list_choices.addItem(txt)
            self.txt_new_choice.clear()

    def _remove_choice(self):
        row = self.list_choices.currentRow()
        if row >= 0:
            self.list_choices.takeItem(row)

    def _on_save(self):
        new_name = self.txt_name.text().strip()
        if not new_name:
            QMessageBox.warning(self, LanguageManager.tr("error"), LanguageManager.tr("form_prop_name") + " boş bırakılamaz.")
            return

        # İsim çakışması kontrolü
        tab_doc = self.item.tab_doc
        if tab_doc and tab_doc.doc and new_name != self.item.field_name:
            for p in tab_doc.doc:
                for w in p.widgets():
                    if w.field_name == new_name:
                        QMessageBox.warning(self, LanguageManager.tr("error"), f"'{new_name}' adında bir alan zaten mevcut.")
                        return

        # Değerleri öğeye ve PyMuPDF'e aktar
        old_name = self.item.field_name
        self.item.field_name = new_name
        self.item.tooltip = self.txt_tooltip.text().strip()
        self.item.is_readonly = self.chk_readonly.isChecked()
        self.item.is_required = self.chk_required.isChecked()

        if hasattr(self, 'txt_val'):
            self.item.field_value = self.txt_val.text()
            if hasattr(self, 'cmb_font_size'):
                self.item.font_size = float(self.cmb_font_size.currentText())
            if hasattr(self, 'chk_multiline'):
                self.item.is_multiline = self.chk_multiline.isChecked()
        elif hasattr(self, 'chk_val'):
            self.item.field_value = self.chk_val.isChecked()
        elif hasattr(self, 'list_choices'):
            choices = [self.list_choices.item(i).text() for i in range(self.list_choices.count())]
            self.item.choices = choices
            if choices and (not self.item.field_value or self.item.field_value not in choices):
                self.item.field_value = choices[0]

        # PyMuPDF Widget nesnesini güncelle
        if tab_doc and tab_doc.doc and self.item.page_idx < len(tab_doc.doc):
            try:
                page = tab_doc.doc[self.item.page_idx]
                for w in page.widgets():
                    if w.field_name == old_name:
                        w.field_name = self.item.field_name
                        w.field_value = self.item.field_value
                        if hasattr(w, 'tooltip'):
                            w.tooltip = self.item.tooltip
                        if self.item.choices and hasattr(w, 'choice_values'):
                            w.choice_values = self.item.choices
                        if hasattr(self, 'cmb_font_size'):
                            w.text_fontsize = self.item.font_size
                        w.update()
                        break
                tab_doc.set_modified(True)
            except Exception:
                pass

        self.accept()
