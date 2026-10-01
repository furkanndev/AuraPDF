from typing import List, Dict, Optional, Any
import os
import tempfile
import pymupdf as fitz
from PyQt6.QtWidgets import (QToolButton, QToolBar, QGraphicsTextItem, 
                             QDockWidget, QTabWidget, QListWidget, QListWidgetItem, 
                             QWidget, QVBoxLayout, QLabel, QApplication, QAbstractItemView,
                             QFrame, QHBoxLayout, QVBoxLayout, QBoxLayout, QLineEdit, QMenu, QTreeWidget,
                             QTreeWidgetItem, QStackedWidget, QPushButton, QFileDialog,
                             QMessageBox, QInputDialog, QDialog, QGraphicsDropShadowEffect, QColorDialog,
                             QStyleOptionViewItem)
from PyQt6.QtGui import (QDrag, QColor, QFocusEvent, QPainter, QPixmap, QIcon, QFont, QImage,
                         QDesktopServices, QTextCursor, QTextCharFormat, QTextFormat, QCursor, QBrush, QAction,
                         QPainterPath, QPen, QLinearGradient)
from PyQt6.QtCore import (Qt, QMimeData, QPoint, QPointF, QSize, pyqtSignal, QEvent, QRect, QRectF, QTimer, QUrl,
                          QEasingCurve, QPropertyAnimation, QSettings)
from src.core.i18n import LanguageManager
from src.core.hyperlink_detector import detect_hyperlink
from src.ui.icons import ModernIconFactory

# --- 1. SÜRÜKLENEBİLİR TOOLBAR BUTONU & ÇUBUĞU ---
class DraggableToolButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos:
            if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(str(id(self)))
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                self.drag_start_pos = None
                return
        super().mouseMoveEvent(event)


class ReorderableToolBar(QToolBar):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    def contextMenuEvent(self, event):
        main_win = self.window()
        if hasattr(main_win, 'reset_toolbar_order'):
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #242424;
                    color: #f0f0f0;
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #1a73e8;
                    color: #ffffff;
                }
            """)
            act_reset = menu.addAction(LanguageManager.tr("reset_toolbar_action"))
            act_reset.triggered.connect(main_win.reset_toolbar_order)
            menu.exec(event.globalPos())
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
            return
        if event.mimeData().hasText():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
            return
        if event.mimeData().hasText():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
            if pdf_urls:
                main_win = self.window()
                if hasattr(main_win, 'handle_dropped_urls'):
                    main_win.handle_dropped_urls(pdf_urls)
                    event.acceptProposedAction()
                    return

        src_id = event.mimeData().text()
        pos = event.position().toPoint()
        target_action = self.actionAt(pos)

        src_action = None
        for act in self.actions():
            w = self.widgetForAction(act)
            if w and str(id(w)) == src_id:
                src_action = act
                break

        if src_action and src_action != target_action:
            self.removeAction(src_action)
            if target_action:
                self.insertAction(target_action, src_action)
            else:
                self.addAction(src_action)
            w = self.widgetForAction(src_action)
            if w:
                w.show()
            event.acceptProposedAction()
            main_win = self.window()
            if hasattr(main_win, 'save_toolbar_order'):
                main_win.save_toolbar_order()




# --- 1.5. MODERN HYPERLINK BAĞLANTI DİYALOĞU ---
class ModernLinkInputDialog(QDialog):
    """
    Kullanıcının metin kutusuna veya seçili metne tıklanabilir web bağlantısı (hyperlink)
    eklemesini sağlayan şık ve modern diyalog.
    """
    def __init__(self, parent=None, initial_text="", initial_url="", has_existing_link=False):
        super().__init__(parent)
        self.setWindowTitle("Bağlantı (Hyperlink) Ayarları")
        self.setFixedWidth(440)
        self.initial_text = initial_text or ""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e20;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #27272a;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 9px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0284c7;
                background-color: #2b2b30;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        # Başlık
        header = QLabel("Metne Web Bağlantısı (Hyperlink) Ekle")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(header)

        # Hedef URL Alanı
        lbl_url = QLabel("Yönlendirilecek Web Adresi (URL):")
        layout.addWidget(lbl_url)
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://www.google.com")
        self.txt_url.setText(initial_url or "https://")
        self.txt_url.returnPressed.connect(self.accept)
        layout.addWidget(self.txt_url)

        # Bilgilendirme / İpucu
        hint = QLabel("Bağlantı eklenen metin mavi ve altı çizili görünecektir. Tıklandığında hedef site açılır.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #94a3b8; font-style: italic; line-height: 1.4;")
        layout.addWidget(hint)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.remove_link = False
        if has_existing_link:
            self.btn_remove = QPushButton("Bağlantıyı Kaldır")
            self.btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: #451a1a;
                    color: #fca5a5;
                    border: 1px solid #7f1d1d;
                }
                QPushButton:hover {
                    background-color: #7f1d1d;
                    color: #ffffff;
                }
            """)
            self.btn_remove.clicked.connect(self._on_remove)
            btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3f3f46;
                color: #f1f5f9;
                border: 1px solid #52525b;
            }
            QPushButton:hover {
                background-color: #52525b;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_apply = QPushButton("Kaydet")
        btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_apply.clicked.connect(self.accept)
        btn_layout.addWidget(btn_apply)

        layout.addLayout(btn_layout)

        # Otomatik odaklanma
        QTimer.singleShot(50, self._focus_url)

    def _focus_url(self):
        self.txt_url.setFocus()
        if self.txt_url.text() == "https://":
            self.txt_url.setCursorPosition(len("https://"))
        else:
            self.txt_url.selectAll()

    def _on_remove(self):
        self.remove_link = True
        self.accept()

    def get_data(self):
        return {
            "word": getattr(self, "initial_text", "").strip(),
            "url": self.txt_url.text().strip(),
            "remove": self.remove_link
        }


# --- 2. DÜZENLENEBİLİR METİN KUTUSU ---
class EditableInlineTextItem(QGraphicsTextItem):
    def __init__(self, tab_doc, page_idx, pos, font_family="Arial", font_size=14, color=QColor(230, 230, 230), text="",
                 bold=False, italic=False, underline=False):
        super().__init__(text)
        self.tab_doc = tab_doc
        self.page_idx = page_idx
        self.font_family = font_family
        self.font_size = font_size if (isinstance(font_size, (int, float)) and font_size > 0) else 14
        self.text_color = color
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.link_url = ""
        self.link_type = None
        self.link_raw = ""
        self.link_text = ""
        self.link_range = None
        self.manual_link = False
        self._last_selection_range = None
        self.setPos(pos)
        self.setDefaultTextColor(color)
        self._apply_font()
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        if not text:
            self.enable_editing()
        else:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            self._detect_and_apply_link(text)

    def _apply_font(self):
        fs = self.font_size if (isinstance(self.font_size, (int, float)) and self.font_size > 0) else 14
        font = QFont(self.font_family, int(fs))
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        self.setFont(font)

    def apply_format_to_selection(self, *, bold=None, italic=None, underline=None, font_size=None, color=None, font_family=None):
        """
        Metin kutusu içinde seçilen harflerin veya aralığın kalınlığını, boyutunu,
        rengini veya yazı tipini SADECE seçili karakterler için uygular.
        """
        if not (self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction):
            self.enable_editing()

        cur = self.textCursor()
        # Eğer buton tıklaması sırasında seçim odağı kaybolmuşsa son seçilen aralığı geri yükle
        if not cur.hasSelection() and getattr(self, '_last_selection_range', None):
            st, en = self._last_selection_range
            doc_len = len(self.toPlainText())
            if 0 <= st < en <= doc_len:
                cur.setPosition(st)
                cur.setPosition(en, QTextCursor.MoveMode.KeepAnchor)

        fmt = QTextCharFormat()
        if bold is not None:
            fmt.setFontWeight(QFont.Weight.Bold.value if bold else QFont.Weight.Normal.value)
        if italic is not None:
            fmt.setFontItalic(bool(italic))
        if underline is not None:
            fmt.setFontUnderline(bool(underline))
        if font_size is not None and font_size > 0:
            fmt.setFontPointSize(float(font_size))
        if color is not None:
            c = QColor(color) if isinstance(color, str) else color
            if isinstance(c, QColor) and c.isValid():
                fmt.setForeground(QBrush(c))
        if font_family is not None and font_family:
            fmt.setFontFamily(str(font_family))

        if cur.hasSelection():
            cur.mergeCharFormat(fmt)
            self.setTextCursor(cur)
            self._last_selection_range = (cur.selectionStart(), cur.selectionEnd())
        else:
            cur_all = QTextCursor(self.document())
            cur_all.select(QTextCursor.SelectionType.Document)
            cur_all.mergeCharFormat(fmt)
            self.setCurrentCharFormat(fmt)

        self.prepareGeometryChange()
        self.document().adjustSize()
        self.setFocus()
        self.update()
        if hasattr(self.tab_doc, 'view') and self.tab_doc.view:
            self.tab_doc.view.viewport().update()

        self.tab_doc.commit_inline_text(self)
        hud = getattr(self.tab_doc, 'text_floating_hud', None)
        if hud and hud.isVisible():
            hud.update_ui_from_selection()
            hud.reposition_above_selection()

    def get_selection_format(self) -> dict:
        cur = self.textCursor()
        if not cur.hasSelection() and getattr(self, '_last_selection_range', None):
            st, en = self._last_selection_range
            if 0 <= st < en <= len(self.toPlainText()):
                cur.setPosition(st)
                cur.setPosition(en, QTextCursor.MoveMode.KeepAnchor)

        fmt = cur.charFormat()
        fs = fmt.fontPointSize()
        if fs <= 0:
            fs = self.font().pointSize() if self.font().pointSize() > 0 else self.font_size
        col = fmt.foreground().color()
        if not col.isValid() or col.alpha() == 0:
            col = self.text_color
        weight_val = fmt.fontWeight()
        if weight_val <= 0:
            is_bold = self.bold
        else:
            is_bold = (weight_val >= QFont.Weight.Bold.value) if isinstance(weight_val, int) else (weight_val >= QFont.Weight.Bold)
        fam = fmt.font().family() if hasattr(fmt, 'font') else ""
        return {
            "bold": bool(is_bold),
            "italic": fmt.fontItalic() if fmt.hasProperty(QTextFormat.Property.FontItalic) else self.italic,
            "underline": fmt.fontUnderline() if fmt.hasProperty(QTextFormat.Property.FontUnderline) else self.underline,
            "font_size": fs,
            "color": col,
            "font_family": fam or self.font_family
        }

    def get_fragments(self) -> list:
        """
        Metin belgesindeki tüm paragrafları ve her bir paragraf içindeki
        farklı biçimlendirilmiş harf parçalarını (fragments) döndürür.
        """
        frags = []
        doc = self.document()
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            block_frags = []
            while not it.atEnd():
                f = it.fragment()
                if f.isValid():
                    txt = f.text()
                    if txt:
                        fmt = f.charFormat()
                        fs = fmt.fontPointSize()
                        if fs <= 0:
                            fs = self.font_size
                        col = fmt.foreground().color()
                        if not col.isValid():
                            col = self.text_color
                        w_val = fmt.fontWeight()
                        f_bold = (w_val >= QFont.Weight.Bold.value) if isinstance(w_val, int) else (w_val >= QFont.Weight.Bold)
                        f_fam = fmt.font().family() if hasattr(fmt, 'font') else ""
                        block_frags.append({
                            "text": txt,
                            "font_size": float(fs),
                            "font_family": f_fam or self.font_family,
                            "bold": bool(f_bold),
                            "italic": fmt.fontItalic(),
                            "underline": fmt.fontUnderline(),
                            "color": col,
                            "href": fmt.anchorHref() if fmt.isAnchor() else ""
                        })
                it += 1
            frags.append(block_frags)
            block = block.next()
        return frags

    def show_floating_hud(self):
        if not hasattr(self.tab_doc, 'view') or not self.tab_doc.view:
            return
        hud = getattr(self.tab_doc, 'text_floating_hud', None)
        if hud is None:
            from src.ui.popups import TextFloatingFormatHUD
            hud = TextFloatingFormatHUD(self.tab_doc.view.viewport(), self.tab_doc)
            self.tab_doc.text_floating_hud = hud

        cur = self.textCursor()
        if not cur.hasSelection():
            hud.hide()
            return

        hud.attach_to_text_item(self)
        hud.update_ui_from_selection()
        hud.reposition_above_selection()
        hud.show()
        hud.raise_()

    def hide_floating_hud(self):
        hud = getattr(self.tab_doc, 'text_floating_hud', None)
        if hud and hud.isVisible():
            hud.hide()

    def _check_selection_and_update_hud(self):
        cur = self.textCursor()
        if cur.hasSelection():
            st = cur.selectionStart()
            en = cur.selectionEnd()
            if st < en:
                self._last_selection_range = (st, en)
                self.show_floating_hud()
                return
        self.hide_floating_hud()

    def _detect_and_apply_link(self, text):
        if getattr(self, 'manual_link', False):
            if getattr(self, 'link_text', ''):
                self.format_link_substring(self.link_text, self.link_url, char_range=getattr(self, 'link_range', None))
            elif getattr(self, 'link_url', ''):
                self.format_entire_text_as_link(self.link_url)
            return

        from src.core.hyperlink_detector import detect_hyperlink
        detected = detect_hyperlink(text)
        if detected:
            self.link_url = detected["url"]
            self.link_type = detected["type"]
            self.link_raw = detected["raw"]
            self.setToolTip(detected["tooltip"])
            if self.link_url:
                self.format_entire_text_as_link(self.link_url)
            elif not self.underline:
                self.underline = True
                self._apply_font()
        else:
            self.link_url = ""
            self.link_type = None
            self.link_raw = ""
            self.link_text = ""
            self.setToolTip("")

    def format_link_substring(self, substring: str, url: str, char_range: tuple = None):
        """
        Metin içindeki belirli bir kelimeyi veya seçilen aralığı hyperlink şeklinde
        mavi renkte (#1a73e8) ve altı çizili olarak biçimlendirir.
        Aynı kelimeden birden fazla olsa dahi SADECE seçilen aralıktaki kelime bağlantı yapılır.
        Diğer kelimeler orijinal renginde ve biçiminde kalır.
        """
        if not url:
            self.clear_link_formatting()
            return

        if not url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            url = 'https://' + url

        self.link_url = url
        self.link_type = "url"
        self.manual_link = True

        doc = self.document()
        full_text = doc.toPlainText()

        fs = self.font_size if (isinstance(self.font_size, (int, float)) and self.font_size > 0) else 14
        base_font = QFont(self.font_family, int(fs))
        base_font.setBold(self.bold)
        base_font.setItalic(self.italic)
        base_font.setUnderline(self.underline)

        # Sadece önceki bağlantı çıpalarını (anchor) kaldır, harf renklerini ve boyutlarını koru
        cur_clear = QTextCursor(doc)
        cur_clear.select(QTextCursor.SelectionType.Document)
        fmt_no_anchor = QTextCharFormat()
        fmt_no_anchor.setAnchor(False)
        fmt_no_anchor.setAnchorHref("")
        cur_clear.mergeCharFormat(fmt_no_anchor)

        link_fmt = QTextCharFormat()
        link_fmt.setAnchor(True)
        link_fmt.setAnchorHref(url)
        # Standart web hyperlink mavisi: #1a73e8
        link_fmt.setForeground(QBrush(QColor("#1a73e8")))
        link_fmt.setFontUnderline(True)

        target_span = None
        sub = substring.strip() if substring else ""

        # 1. Açıkça belirtilmiş char_range varsa ve metinle uyumluysa
        if char_range and isinstance(char_range, (list, tuple)) and len(char_range) == 2:
            st, en = int(char_range[0]), int(char_range[1])
            if 0 <= st < en <= len(full_text):
                span_text = full_text[st:en]
                if not sub or span_text.strip() == sub or span_text == sub:
                    target_span = (st, en)
                    sub = span_text.strip()

        # 2. Kaydedilmiş self.link_range varsa
        if not target_span and getattr(self, "link_range", None):
            lr = self.link_range
            if isinstance(lr, (list, tuple)) and len(lr) == 2:
                st, en = int(lr[0]), int(lr[1])
                if 0 <= st < en <= len(full_text):
                    span_text = full_text[st:en]
                    if not sub or span_text.strip() == sub or span_text == sub:
                        target_span = (st, en)
                        sub = span_text.strip()

        # 3. Eğer aralık kaymışsa veya sadece sub verilmişse: En yakın tek eşleşmeyi bul
        if not target_span and sub and sub in full_text:
            all_indices = []
            idx = 0
            while True:
                idx = full_text.find(sub, idx)
                if idx == -1:
                    break
                all_indices.append(idx)
                idx += len(sub)
            if all_indices:
                old_start = 0
                if char_range and isinstance(char_range, (list, tuple)):
                    old_start = int(char_range[0])
                elif getattr(self, "link_range", None):
                    old_start = int(self.link_range[0])
                best_idx = min(all_indices, key=lambda i: abs(i - old_start))
                target_span = (best_idx, best_idx + len(sub))

        cursor = QTextCursor(doc)
        if target_span:
            st, en = target_span
            cursor.setPosition(st)
            cursor.setPosition(en, QTextCursor.MoveMode.KeepAnchor)
            cursor.mergeCharFormat(link_fmt)
            self.link_range = (st, en)
            self.link_text = full_text[st:en]
            self.link_raw = self.link_text
            self.setToolTip(f"Bağlantı: {url}\n('{self.link_text}' üzerine tıklayarak siteye gidin)")
        else:
            # Tüm metin bağlantı
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.mergeCharFormat(link_fmt)
            self.link_range = (0, len(full_text))
            self.link_text = ""
            self.link_raw = url
            self.setToolTip(f"Bağlantı: {url}\n(Tıklayarak siteye gidin)")

    def format_entire_text_as_link(self, url: str):
        self.format_link_substring("", url, char_range=None)

    def clear_link_formatting(self):
        had_link = bool(self.link_url or self.manual_link or self.link_text or self.link_range)
        self.link_url = ""
        self.link_type = None
        self.link_raw = ""
        self.link_text = ""
        self.link_range = None
        self.manual_link = False
        self.setToolTip("")

        if not had_link:
            return

        # Sadece bağlantı çıpasını kaldır; kullanıcının özel harf renklerini/kalınlıklarını ASLA sıfırlama
        doc = self.document()
        cur = QTextCursor(doc)
        cur.select(QTextCursor.SelectionType.Document)
        fmt_no_anchor = QTextCharFormat()
        fmt_no_anchor.setAnchor(False)
        fmt_no_anchor.setAnchorHref("")
        cur.mergeCharFormat(fmt_no_anchor)

    def open_link_dialog(self, prefill_word="", char_range=None):
        cur = self.textCursor()
        target_range = char_range
        selected_text = prefill_word

        # Eğer bir seçim aralığı verilmemişse ve imleç üzerinde bir seçim varsa aralığı yakala
        if target_range is None and cur.hasSelection():
            raw_sel = cur.selectedText()
            lead_spaces = len(raw_sel) - len(raw_sel.lstrip())
            trail_spaces = len(raw_sel) - len(raw_sel.rstrip())
            s_start = cur.selectionStart() + lead_spaces
            s_end = cur.selectionEnd() - trail_spaces
            if s_start < s_end:
                target_range = (s_start, s_end)
                if not selected_text:
                    selected_text = raw_sel.strip()

        # Eğer hala hedef aralık yoksa ama bu öğede kayıtlı bir aralık varsa
        if target_range is None and getattr(self, "link_range", None):
            target_range = self.link_range
            if not selected_text:
                selected_text = getattr(self, "link_text", "")

        initial_word = selected_text or getattr(self, "link_text", "")
        initial_url = getattr(self, "link_url", "") or "https://"
        has_existing = bool(getattr(self, "link_url", "")) or getattr(self, "manual_link", False)

        parent_widget = self.scene().views()[0] if self.scene() and self.scene().views() else self.tab_doc.main_window
        dlg = ModernLinkInputDialog(
            parent_widget,
            initial_text=initial_word,
            initial_url=initial_url,
            has_existing_link=has_existing
        )
        if dlg.exec():
            data = dlg.get_data()
            if data['remove']:
                self.clear_link_formatting()
                self.tab_doc.commit_inline_text(self)
            else:
                target_url = data['url']
                target_word = data['word'] or selected_text
                if target_url:
                    if not target_url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                        target_url = 'https://' + target_url
                    self.format_link_substring(target_word, target_url, char_range=target_range)
                    self.tab_doc.commit_inline_text(self)

    def enable_editing(self):
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        self.tab_doc.active_text_item = self
        self.tab_doc.last_text_item = self
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def hoverEnterEvent(self, event):
        if self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        else:
            anc = self.document().documentLayout().anchorAt(event.pos())
            has_action = bool(anc) or (bool(getattr(self, "link_url", None)) and not getattr(self, "link_text", "")) or getattr(self, "link_type", None) == "tc"
            if has_action:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.IBeamCursor if self.tab_doc.main_window.current_tool == 'text' else Qt.CursorShape.ArrowCursor)
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        if self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction:
            self.setCursor(Qt.CursorShape.IBeamCursor)
            self.setToolTip("")
            super().hoverMoveEvent(event)
            return

        anc = self.document().documentLayout().anchorAt(event.pos())
        if anc:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"Bağlantı: {anc}\n(Tıklayarak siteye gidin)")
        elif getattr(self, "link_url", "") and not getattr(self, "link_text", ""):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"Bağlantı: {self.link_url}\n(Tıklayarak siteye gidin)")
        elif getattr(self, "link_type", None) == "tc":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            val = getattr(self, "link_raw", "") or self.toPlainText().strip()
            self.setToolTip(f"T.C. Kimlik No: {val}\n(Tıklayarak panoya kopyalayın)")
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor if self.tab_doc.main_window.current_tool == 'text' else Qt.CursorShape.ArrowCursor)
            self.setToolTip("")
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.enable_editing()
        layout = self.document().documentLayout()
        char_idx = layout.hitTest(event.pos(), Qt.HitTestAccuracy.ExactHit)
        if char_idx >= 0:
            cur = self.textCursor()
            cur.setPosition(char_idx)
            cur.select(QTextCursor.SelectionType.WordUnderCursor)
            self.setTextCursor(cur)
        event.accept()

    def mousePressEvent(self, event):
        is_editing = bool(self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction)

        # 1. Eğer düzenleme modundaysa: Normal tıklamalar imleç konumlandırma ve seçim içindir!
        if is_editing:
            if event.button() == Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                anc = self.document().documentLayout().anchorAt(event.pos())
                if anc:
                    QDesktopServices.openUrl(QUrl(anc))
                    event.accept()
                    return
            super().mousePressEvent(event)
            return

        # 2. Düzenleme modunda değilse (okuma / seçim modundaysa):
        if event.button() == Qt.MouseButton.LeftButton:
            anc = self.document().documentLayout().anchorAt(event.pos())
            if anc:
                QDesktopServices.openUrl(QUrl(anc))
                main_win = self.tab_doc.main_window
                status_bar = getattr(main_win, "statusBar", lambda: None)()
                if status_bar:
                    status_bar.showMessage(f"Web sitesi açılıyor: {anc}", 4000)
                event.accept()
                return

            link_url = getattr(self, "link_url", "")
            link_type = getattr(self, "link_type", "url")
            link_raw = getattr(self, "link_raw", "") or self.toPlainText().strip()
            link_text = getattr(self, "link_text", "")

            # T.C. Kimlik No: Kesinlikle siteye yönlendirme yapma, panoya kopyala
            if link_type == "tc":
                val = link_raw or self.toPlainText().strip()
                QApplication.clipboard().setText(val)
                main_win = self.tab_doc.main_window
                status_bar = getattr(main_win, "statusBar", lambda: None)()
                if status_bar:
                    status_bar.showMessage(f"T.C. Kimlik No panoya kopyalandı: {val}", 4000)
                return

            # Tüm metin bir bağlantı ise:
            if link_url and not link_text:
                main_win = self.tab_doc.main_window
                status_bar = getattr(main_win, "statusBar", lambda: None)()
                if link_type == "phone":
                    val = link_raw or self.toPlainText().strip()
                    QApplication.clipboard().setText(val)
                    if status_bar:
                        status_bar.showMessage(f"Telefon numarası panoya kopyalandı: {val}", 4000)
                    QDesktopServices.openUrl(QUrl(link_url))
                elif link_type == "email":
                    val = link_raw or self.toPlainText().strip()
                    QApplication.clipboard().setText(val)
                    if status_bar:
                        status_bar.showMessage(f"E-Posta adresi panoya kopyalandı: {val}", 4000)
                    QDesktopServices.openUrl(QUrl(link_url))
                else:
                    QDesktopServices.openUrl(QUrl(link_url))
                    if status_bar:
                        status_bar.showMessage(f"Web sitesi açılıyor: {link_url}", 4000)
                return

            # Tıklanan yer bağlantı değilse ve araç select veya text ise düzenleme moduna geç
            if self.tab_doc.main_window.current_tool in ('select', 'text'):
                self.enable_editing()
                layout = self.document().documentLayout()
                char_idx = layout.hitTest(event.pos(), Qt.HitTestAccuracy.ExactHit)
                if char_idx >= 0:
                    cur = self.textCursor()
                    cur.setPosition(char_idx)
                    self.setTextCursor(cur)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._check_selection_and_update_hud()

    def keyPressEvent(self, event):
        mods = event.modifiers()
        key = event.key()

        # Klavye kısayolları ile zengin metin biçimlendirme
        if mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_B:
                fmt = self.get_selection_format()
                self.apply_format_to_selection(bold=not fmt["bold"])
                event.accept()
                return
            elif key == Qt.Key.Key_I:
                fmt = self.get_selection_format()
                self.apply_format_to_selection(italic=not fmt["italic"])
                event.accept()
                return
            elif key == Qt.Key.Key_U:
                fmt = self.get_selection_format()
                self.apply_format_to_selection(underline=not fmt["underline"])
                event.accept()
                return
            elif key in (Qt.Key.Key_BracketRight, Qt.Key.Key_Greater):  # Ctrl+] veya Ctrl+>
                fmt = self.get_selection_format()
                new_size = min(120, int(round(fmt["font_size"])) + 2)
                self.apply_format_to_selection(font_size=new_size)
                event.accept()
                return
            elif key in (Qt.Key.Key_BracketLeft, Qt.Key.Key_Less):  # Ctrl+[ veya Ctrl+<
                fmt = self.get_selection_format()
                new_size = max(8, int(round(fmt["font_size"])) - 2)
                self.apply_format_to_selection(font_size=new_size)
                event.accept()
                return

        if key == Qt.Key.Key_Escape:
            self.clearFocus()
            self.hide_floating_hud()
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        self._check_selection_and_update_hud()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.tab_doc.active_text_item = self
        self.tab_doc.last_text_item = self

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        # Kayan hızlı biçimlendirme çubuğuna veya ayar popup'larına tıklanmışsa düzenleme modundan çıkma
        hud = getattr(self.tab_doc, 'text_floating_hud', None)
        focus_w = QApplication.focusWidget()
        mouse_pos = QCursor.pos()

        # 1. Fare kayan hızlı biçimlendirme çubuğunun üzerindeyse çıkma
        if hud and hud.isVisible():
            if hasattr(self.tab_doc, 'view') and self.tab_doc.view:
                vp = self.tab_doc.view.viewport()
                if hud.geometry().contains(vp.mapFromGlobal(mouse_pos)):
                    return

        # 2. Fare araç çubuğu metin ayar penceresi üzerindeyse çıkma
        text_popup = getattr(getattr(self.tab_doc, 'main_window', None), 'text_popup', None)
        if text_popup and text_popup.isVisible():
            if text_popup.rect().contains(text_popup.mapFromGlobal(mouse_pos)):
                return

        # 3. Aktif bir popup (ör. renk seçici QMenu) veya modal pencere (QColorDialog) açıksa çıkma
        active_popup = QApplication.activePopupWidget()
        if active_popup:
            return
        active_modal = QApplication.activeModalWidget()
        if isinstance(active_modal, (QColorDialog, QDialog)):
            return

        # 4. Odaklanan widget HUD, text_popup, QMenu veya QColorDialog hiyerarşisi içindeyse çıkma
        curr = focus_w
        while curr:
            if hud and (curr == hud or hud.isAncestorOf(curr)):
                return
            if text_popup and (curr == text_popup or text_popup.isAncestorOf(curr)):
                return
            if isinstance(curr, (QColorDialog, QMenu)):
                return
            curr = curr.parent()

        content = self.toPlainText().strip()
        if not content:
            if hud:
                hud.hide()
            self.tab_doc.scene.removeItem(self)
            self.tab_doc.drawings = [d for d in self.tab_doc.drawings if d.get("item_ref") != self]
            self.tab_doc.active_text_item = None
        else:
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            if hud:
                hud.hide()
            self.tab_doc.commit_inline_text(self)

    def contextMenuEvent(self, event):
        cur = self.textCursor()
        anc = self.document().documentLayout().anchorAt(event.pos())

        # Eğer halihazırda bir seçim yoksa ve tıklandığı yer bir kelime üzerindeyse o kelimeyi seç
        if not cur.hasSelection():
            layout = self.document().documentLayout()
            char_pos = layout.hitTest(event.pos(), Qt.HitTestAccuracy.ExactHit)
            if char_pos >= 0:
                cur.setPosition(char_pos)
                cur.select(QTextCursor.SelectionType.WordUnderCursor)
                if cur.selectedText().strip():
                    self.setTextCursor(cur)

        selected_text = cur.selectedText().strip()
        raw_sel = cur.selectedText()
        target_range = None
        if cur.hasSelection() and selected_text:
            lead_spaces = len(raw_sel) - len(raw_sel.lstrip())
            trail_spaces = len(raw_sel) - len(raw_sel.rstrip())
            s_start = cur.selectionStart() + lead_spaces
            s_end = cur.selectionEnd() - trail_spaces
            if s_start < s_end:
                target_range = (s_start, s_end)

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)

        # Yalnızca belirli bir kelime bağlantı ise, sadece o kelimeye tıklandığında link menüsü aktif olur
        if getattr(self, "link_text", ""):
            active_url = anc
            has_link = bool(anc)
        else:
            active_url = anc or getattr(self, "link_url", "")
            has_link = bool(active_url or getattr(self, "manual_link", False))

        link_type = getattr(self, "link_type", "url")
        link_raw = getattr(self, "link_raw", "") or self.toPlainText().strip()

        act_action = None
        act_copy = None

        if active_url and link_type != "tc":
            if link_type == "phone":
                act_action = menu.addAction(f"Numarayı Ara ({link_raw})")
                act_copy = menu.addAction("Telefon Numarasını Kopyala")
            elif link_type == "email":
                act_action = menu.addAction(f"E-Posta Gönder ({link_raw})")
                act_copy = menu.addAction("E-Posta Adresini Kopyala")
            else:
                act_action = menu.addAction(f"Siteye Git ({active_url})")
                act_copy = menu.addAction("Bağlantı Adresini Kopyala")
            menu.addSeparator()
        elif link_type == "tc":
            act_copy = menu.addAction(f"T.C. Kimlik No Kopyala ({link_raw})")
            menu.addSeparator()

        # Harf / Kelime Düzeyinde Hızlı Biçimlendirme Seçenekleri
        act_bold = None
        act_italic = None
        act_underline = None
        if cur.hasSelection() and selected_text:
            fmt = self.get_selection_format()
            is_bold = fmt.get("bold", False)
            is_italic = fmt.get("italic", False)
            is_underline = fmt.get("underline", False)

            act_bold = menu.addAction(f"Kalın (Bold){'  ✓' if is_bold else ''}")
            act_italic = menu.addAction(f"İtalik (Italic){'  ✓' if is_italic else ''}")
            act_underline = menu.addAction(f"Altı Çizili (Underline){'  ✓' if is_underline else ''}")

            size_menu = menu.addMenu("Yazı Tipi Boyutu")
            curr_sz = int(round(fmt.get("font_size", 14)))
            for sz in [9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]:
                act_sz = size_menu.addAction(f"{sz} pt{'  ✓' if sz == curr_sz else ''}")
                act_sz.triggered.connect(lambda _, s=sz: self.apply_format_to_selection(font_size=s))

            color_menu = menu.addMenu("Metin Rengi")
            colors = [
                ("Siyah", "#000000"),
                ("Beyaz", "#ffffff"),
                ("Kırmızı", "#e53935"),
                ("Mavi", "#1e88e5"),
                ("Yeşil", "#43a047"),
                ("Sarı", "#fdd835"),
                ("Turuncu", "#fb8c00"),
                ("Mor", "#8e24aa"),
            ]
            for col_name, col_hex in colors:
                act_c = color_menu.addAction(col_name)
                pix = QPixmap(12, 12)
                pix.fill(QColor(col_hex))
                act_c.setIcon(QIcon(pix))
                act_c.triggered.connect(lambda _, c=col_hex: self.apply_format_to_selection(color=QColor(c)))

            act_custom_c = color_menu.addAction("Özel Renk Seç...")
            def _choose_custom_color():
                c = QColorDialog.getColor(fmt.get("color", QColor("#000000")), None, "Metin Rengi Seç")
                if c.isValid():
                    self.apply_format_to_selection(color=c)
            act_custom_c.triggered.connect(_choose_custom_color)
            menu.addSeparator()

        if selected_text:
            act_link = menu.addAction(f"'{selected_text}' İfadesine Bağlantı Ekle / Düzenle...")
            target_word_hint = selected_text
        else:
            act_link = menu.addAction("Bağlantı (Hyperlink) Ekle / Düzenle...")
            target_word_hint = ""

        act_edit_txt = menu.addAction("Metni Düzenle")
        act_rm_link = menu.addAction("Bağlantıyı Kaldır")
        if not has_link:
            act_rm_link.setEnabled(False)

        chosen = menu.exec(event.screenPos())
        if act_action and chosen == act_action:
            QDesktopServices.openUrl(QUrl(active_url))
        elif act_copy and chosen == act_copy:
            val_to_copy = link_raw if link_type in ("tc", "phone", "email") else (active_url or self.toPlainText().strip())
            QApplication.clipboard().setText(val_to_copy)
            status_bar = getattr(self.tab_doc.main_window, "statusBar", lambda: None)()
            if status_bar:
                status_bar.showMessage(f"Panoya kopyalandı: {val_to_copy}", 3000)
        elif act_bold and chosen == act_bold:
            self.apply_format_to_selection(bold=not is_bold)
        elif act_italic and chosen == act_italic:
            self.apply_format_to_selection(italic=not is_italic)
        elif act_underline and chosen == act_underline:
            self.apply_format_to_selection(underline=not is_underline)
        elif chosen == act_edit_txt:
            self.enable_editing()
        elif chosen == act_link:
            self.open_link_dialog(prefill_word=target_word_hint, char_range=target_range)
        elif chosen == act_rm_link:
            self.clear_link_formatting()
            self.tab_doc.commit_inline_text(self)
        event.accept()


# --- 2.4. TAM EKRAN ARAÇ ÇUBUĞU TUTAMACI (FULLSCREEN TOOLBAR GRIP) ---
class FullscreenToolbarGrip(QWidget):
    """
    Sürükle-bırak tutamacı.
    Minimalist antialiased grip deseni ile panelin kolayca sürüklenmesini sağlar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setToolTip("Sürükleyip Bırak (Ekranın Kenarlarına Taşı)")
        self.is_horizontal = False
        self.setFixedSize(36, 14)

    def set_orientation(self, is_horizontal):
        self.is_horizontal = is_horizontal
        if is_horizontal:
            self.setFixedSize(14, 36)
        else:
            self.setFixedSize(36, 14)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 110))

        if self.is_horizontal:
            xs = [4, 9]
            ys = [12, 18, 24]
        else:
            xs = [12, 18, 24]
            ys = [4, 9]

        for x in xs:
            for y in ys:
                p.drawEllipse(QPointF(float(x), float(y)), 1.5, 1.5)
        p.end()


# --- 2.5. TAM EKRAN 4 KENARLI SÜRÜKLENEBİLİR ARAÇ ÇUBUĞU (FULLSCREEN SLIDE TOOLBAR) ---
class FullscreenSlideToolbar(QFrame):
    """
    Tam ekran modunda ekranın 4 kenarında (sol, sağ, üst, alt) durabilen,
    fare kenara yaklaştığında kayarak açılan, fare uzaklaştığında kendiliğinden gizlenen
    modern ve minimalist araç çubuğu.
    Kullanıcı paneli tutamaçtan veya herhangi bir yerinden sürükleyip bırakarak (drag-and-drop)
    istediği kenara (sol, sağ, üst, alt) taşıyabilir.
    İçerik: Tutamaç (Grip), Seçim Aracı (Select), El Aracı (Pan), Kare Seçim Aracı (Selection Tool),
    Çizim (Pen), Vurgulayıcı (Highlighter), Silgi (Eraser), Metin Kutusu (Text), İşaretçi (Laser Pointer) ve Tam Ekrandan Çıkış.
    """
    STYLE_NORMAL = """
        QFrame#FullscreenToolbarFrame {
            background-color: rgba(26, 26, 28, 0.94);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 14px;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 6px;
        }
        QToolButton:hover {
            background-color: rgba(255, 255, 255, 0.16);
        }
        QToolButton:checked {
            background-color: #0284c7;
        }
    """

    STYLE_DRAGGING = """
        QFrame#FullscreenToolbarFrame {
            background-color: rgba(26, 26, 28, 0.96);
            border: 1.5px solid #38bdf8;
            border-radius: 14px;
        }
        QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 8px;
            padding: 6px;
        }
        QToolButton:hover {
            background-color: rgba(255, 255, 255, 0.16);
        }
        QToolButton:checked {
            background-color: #0284c7;
        }
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setObjectName("FullscreenToolbarFrame")
        self.main_window = main_window
        self._active_popup = None

        settings = QSettings("AuraPDF", "PDFViewer")
        edge = settings.value("fullscreen_toolbar_edge", None, type=str)
        if not edge:
            edge = settings.value("fullscreen_toolbar_side", "left", type=str)
        if edge not in ("left", "right", "top", "bottom"):
            edge = "left"
        self.edge = edge

        self.box_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self.box_layout.setContentsMargins(6, 6, 6, 6)
        self.box_layout.setSpacing(6)

        # Sürükle-bırak tutamacı
        self.grip = FullscreenToolbarGrip(self)
        self.box_layout.addWidget(self.grip)

        self.buttons = {}
        tools = [
            ('select', ModernIconFactory.icon_cursor(), 'Seçim Aracı (İmleç / Ayarlar için tıkla)'),
            ('pan', ModernIconFactory.icon_select_pan(), 'El Aracı (Sayfayı Kaydır)'),
            ('selection_tool', ModernIconFactory.icon_select_rect(), 'Kare Seçim Aracı (Seçim / Cetvel Paneli için tıkla)'),
            ('pen', ModernIconFactory.icon_pen(), 'Çizim / Kalem (Renk & Boyut Paneli için tıkla)'),
            ('highlighter', ModernIconFactory.icon_highlighter(), 'Vurgulayıcı (Renk & Boyut Paneli için tıkla)'),
            ('eraser', ModernIconFactory.icon_eraser(), 'Silgi (Silgi Ayarları için tıkla)'),
            ('text', ModernIconFactory.icon_text_box(), 'Metin Kutusu (Yazı & Biçim Paneli için tıkla)'),
            ('insert', ModernIconFactory.icon_insert(), LanguageManager.tr("insert_btn_tip")),
            ('pointer', ModernIconFactory.icon_pointer(), 'Lazer İşaretçi (İşaretçi Ayarları için tıkla)')
        ]

        for name, icon, tip in tools:
            btn = QToolButton(self)
            btn.setIcon(icon)
            btn.setToolTip(tip)
            if name != 'insert':
                btn.setCheckable(True)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked=False, n=name: self._on_tool_clicked(n))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, n=name: self._on_tool_context_menu(n))
            self.box_layout.addWidget(btn)
            self.buttons[name] = btn

        self.sep = QFrame(self)
        self.sep.setFrameShape(QFrame.Shape.NoFrame)
        self.sep.setStyleSheet('border: none; background-color: rgba(255, 255, 255, 0.15);')
        self.box_layout.addWidget(self.sep)

        self.btn_exit = QToolButton(self)
        self.btn_exit.setIcon(ModernIconFactory.icon_fullscreen())
        self.btn_exit.setToolTip('Tam Ekrandan Çık (F11 / Esc)')
        self.btn_exit.setFixedSize(40, 40)
        self.btn_exit.clicked.connect(self._on_exit_fullscreen)
        self.box_layout.addWidget(self.btn_exit)

        # Sürükleme durumu takibi
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_panel_pos = None
        self._drag_target_button = None

        # Olay filtresi: panel, tutamaç ve butonlardan sürüklemeyi yakalar
        self.installEventFilter(self)
        self.grip.installEventFilter(self)
        for btn in self.buttons.values():
            btn.installEventFilter(self)
        self.btn_exit.installEventFilter(self)

        self.anim = QPropertyAnimation(self, b"pos", self)
        enable_anim = settings.value("enable_animations", True, type=bool)
        self.anim.setDuration(220 if enable_anim else 0)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(1600)
        self.hide_timer.timeout.connect(self.slide_out)

        self.is_slid_in = False
        self._apply_edge_layout(self.edge)

        current_th = settings.value("app_theme", "gray")
        if current_th == "navy":
            current_th = "gray"
        self.apply_theme(current_th)

        self.hide()

    def apply_theme(self, theme_name: str = "gray", spec: Optional[dict] = None):
        if theme_name == "navy":
            theme_name = "gray"
        if not spec:
            from src.ui.popups import POPUP_THEME_SPECS
            spec = POPUP_THEME_SPECS.get(theme_name, POPUP_THEME_SPECS.get("gray", {}))

        tb_bg = spec.get("tb_bg", "#1c1c1c")
        tb_border = spec.get("tb_border", "#404040")
        accent = spec.get("accent", "#388bfd")
        btn_hover = spec.get("btn_hover", "rgba(255, 255, 255, 0.16)")

        self.STYLE_NORMAL = f"""
            QFrame#FullscreenToolbarFrame {{
                background-color: {tb_bg};
                border: 1px solid {tb_border};
                border-radius: 14px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 6px;
            }}
            QToolButton:hover {{
                background-color: {btn_hover};
            }}
            QToolButton:checked {{
                background-color: {accent};
            }}
        """
        self.STYLE_DRAGGING = f"""
            QFrame#FullscreenToolbarFrame {{
                background-color: {tb_bg};
                border: 1.5px solid {accent};
                border-radius: 14px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 6px;
            }}
            QToolButton:hover {{
                background-color: {btn_hover};
            }}
            QToolButton:checked {{
                background-color: {accent};
            }}
        """
        self.setStyleSheet(self.STYLE_DRAGGING if getattr(self, '_is_dragging', False) else self.STYLE_NORMAL)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(2, 4)
        self.setGraphicsEffect(shadow)

    @property
    def side(self):
        return self.edge

    @side.setter
    def side(self, val):
        self.edge = val

    def _apply_edge_layout(self, edge):
        self.edge = edge
        is_horiz = edge in ('top', 'bottom')
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        if is_horiz:
            self.box_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self.grip.set_orientation(is_horizontal=True)
            self.sep.setFixedSize(1, 36)
            self.setFixedHeight(54)
        else:
            self.box_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self.grip.set_orientation(is_horizontal=False)
            self.sep.setFixedSize(36, 1)
            self.setFixedWidth(54)
        self.adjustSize()

    def set_edge(self, edge):
        if edge not in ("left", "right", "top", "bottom"):
            return
        self._apply_edge_layout(edge)
        settings = QSettings("AuraPDF", "PDFViewer")
        settings.setValue("fullscreen_toolbar_edge", self.edge)
        settings.setValue("fullscreen_toolbar_side", self.edge)
        self.slide_in()
        self.hide_timer.start(3000)

    def eventFilter(self, watched, event):
        if watched is getattr(self, '_active_popup', None):
            if event.type() in (QEvent.Type.Hide, QEvent.Type.Close):
                self._active_popup = None
                self.hide_timer.start(2500)

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                self._drag_start_panel_pos = self.pos()
                self._is_dragging = False
                self._drag_target_button = watched if isinstance(watched, QToolButton) else None
        elif event.type() == QEvent.Type.MouseMove:
            if self._drag_start_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                cur_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                diff = cur_pos - self._drag_start_pos
                if not self._is_dragging and diff.manhattanLength() > 6:
                    self._is_dragging = True
                    self.hide_timer.stop()
                    self.anim.stop()
                    if getattr(self, '_active_popup', None) and self._active_popup.isVisible():
                        self._active_popup.close()
                    self.setStyleSheet(self.STYLE_DRAGGING)
                    if self._drag_target_button:
                        self._drag_target_button.setDown(False)
                if self._is_dragging:
                    new_x = self._drag_start_panel_pos.x() + diff.x()
                    new_y = self._drag_start_panel_pos.y() + diff.y()
                    new_x = max(0, min(self.main_window.width() - self.width(), new_x))
                    new_y = max(0, min(self.main_window.height() - self.height(), new_y))
                    self.move(new_x, new_y)
                    return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._is_dragging:
                self._finish_drag()
                return True
            self._drag_start_pos = None
            self._drag_target_button = None
        return super().eventFilter(watched, event)

    def _finish_drag(self):
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_target_button = None
        self.setStyleSheet(self.STYLE_NORMAL)

        win_w = max(1, self.main_window.width())
        win_h = max(1, self.main_window.height())
        center_x = self.x() + self.width() / 2.0
        center_y = self.y() + self.height() / 2.0

        norm_left = center_x / win_w
        norm_right = 1.0 - norm_left
        norm_top = center_y / win_h
        norm_bottom = 1.0 - norm_top

        min_norm = min(norm_left, norm_right, norm_top, norm_bottom)
        if min_norm == norm_top:
            new_edge = 'top'
        elif min_norm == norm_bottom:
            new_edge = 'bottom'
        elif min_norm == norm_left:
            new_edge = 'left'
        else:
            new_edge = 'right'

        self.set_edge(new_edge)

    def update_active_tool(self, tool_name):
        for name, btn in self.buttons.items():
            if not btn.isCheckable():
                continue
            btn.blockSignals(True)
            if tool_name == 'ruler':
                btn.setChecked(name == 'selection_tool')
            else:
                btn.setChecked(name == tool_name)
            btn.blockSignals(False)

        if 'selection_tool' in self.buttons:
            btn_sel = self.buttons['selection_tool']
            if tool_name == 'ruler':
                btn_sel.setIcon(ModernIconFactory.icon_ruler())
            else:
                mode = getattr(self.main_window, 'selection_shape_mode', 'rect')
                if mode == 'rect':
                    btn_sel.setIcon(ModernIconFactory.icon_select_rect())
                elif mode == 'lasso':
                    btn_sel.setIcon(ModernIconFactory.icon_select_lasso())
                elif mode == 'move':
                    btn_sel.setIcon(ModernIconFactory.icon_select_move())

    def _get_popup_for_tool(self, name: str):
        mw = self.main_window
        if not mw:
            return None
        if name == 'pen':
            return getattr(mw, 'pen_popup', None)
        elif name == 'highlighter':
            return getattr(mw, 'hl_popup', None)
        elif name == 'text':
            return getattr(mw, 'text_popup', None)
        elif name == 'eraser':
            return getattr(mw, 'eraser_popup', None)
        elif name == 'selection_tool':
            return getattr(mw, 'selection_popup', None)
        elif name == 'pointer':
            return getattr(mw, 'pointer_popup', None)
        elif name in ('select', 'pan'):
            return getattr(mw, 'cursor_popup', None)
        return None

    def show_popup_for_tool(self, popup, btn):
        if not popup or not btn:
            return

        if getattr(self, '_active_popup', None) and self._active_popup != popup and self._active_popup.isVisible():
            self._active_popup.close()

        self._active_popup = popup
        self.hide_timer.stop()

        if hasattr(popup, 'show_below'):
            popup.show_below(btn)
        else:
            popup.show()

        popup.adjustSize()
        pw = max(popup.width(), popup.sizeHint().width())
        ph = max(popup.height(), popup.sizeHint().height())

        btn_pos = btn.mapToGlobal(QPoint(0, 0)) if hasattr(btn, 'mapToGlobal') else self.mapToGlobal(QPoint(0, 0))
        btn_w = btn.width() if hasattr(btn, 'width') else 40
        btn_h = btn.height() if hasattr(btn, 'height') else 40

        screen = QApplication.screenAt(btn_pos) or QApplication.primaryScreen()
        sgeo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        if self.edge == "left":
            x = btn_pos.x() + btn_w + 8
            y = max(sgeo.top() + 8, min(sgeo.bottom() - ph - 8, btn_pos.y() - 10))
        elif self.edge == "right":
            x = btn_pos.x() - pw - 8
            y = max(sgeo.top() + 8, min(sgeo.bottom() - ph - 8, btn_pos.y() - 10))
        elif self.edge == "top":
            x = max(sgeo.left() + 8, min(sgeo.right() - pw - 8, btn_pos.x() - pw // 2 + btn_w // 2))
            y = btn_pos.y() + btn_h + 8
        else:  # bottom
            x = max(sgeo.left() + 8, min(sgeo.right() - pw - 8, btn_pos.x() - pw // 2 + btn_w // 2))
            y = btn_pos.y() - ph - 8

        popup.move(int(x), int(y))
        popup.raise_()
        popup.activateWindow()

        popup.installEventFilter(self)

    def _on_tool_clicked(self, name):
        if name == 'insert':
            self._show_insert_menu(self.buttons.get('insert', self))
            return

        btn = self.buttons.get(name, self)
        popup = self._get_popup_for_tool(name)

        is_already_active = False
        cur_tool = getattr(self.main_window, 'current_tool', '')
        if name == 'select' and cur_tool == 'select':
            is_already_active = True
        elif name == 'pan' and cur_tool == 'pan':
            is_already_active = True
        elif name == 'selection_tool' and cur_tool in ('selection_tool', 'ruler'):
            is_already_active = True
        elif name == cur_tool:
            is_already_active = True

        if is_already_active and popup:
            if popup.isVisible():
                popup.close()
            else:
                self.show_popup_for_tool(popup, btn)
            return

        if popup and popup.isVisible():
            popup.close()

        if name == 'selection_tool':
            if hasattr(self.main_window, 'set_selection_mode'):
                self.main_window.set_selection_mode(getattr(self.main_window, 'selection_shape_mode', 'rect'))
            else:
                self.main_window.set_tool_state('selection_tool')
        elif name == 'pan':
            if hasattr(self.main_window, 'set_cursor_mode'):
                self.main_window.set_cursor_mode('pan')
            else:
                self.main_window.set_tool_state('pan')
        elif name == 'select':
            if hasattr(self.main_window, 'set_cursor_mode'):
                self.main_window.set_cursor_mode('select')
            else:
                self.main_window.set_tool_state('select')
        else:
            self.main_window.set_tool_state(name)

        self.update_active_tool(name)

    def _on_tool_context_menu(self, name):
        if name == 'insert':
            self._show_insert_menu(self.buttons.get('insert', self))
            return

        btn = self.buttons.get(name, self)
        popup = self._get_popup_for_tool(name)

        if name == 'selection_tool':
            if hasattr(self.main_window, 'set_selection_mode'):
                self.main_window.set_selection_mode(getattr(self.main_window, 'selection_shape_mode', 'rect'))
            else:
                self.main_window.set_tool_state('selection_tool')
        elif name == 'pan':
            if hasattr(self.main_window, 'set_cursor_mode'):
                self.main_window.set_cursor_mode('pan')
            else:
                self.main_window.set_tool_state('pan')
        elif name == 'select':
            if hasattr(self.main_window, 'set_cursor_mode'):
                self.main_window.set_cursor_mode('select')
            else:
                self.main_window.set_tool_state('select')
        else:
            self.main_window.set_tool_state(name)

        self.update_active_tool(name)

        if popup:
            self.show_popup_for_tool(popup, btn)

    def _show_insert_menu(self, btn):
        self.hide_timer.stop()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { 
                background-color: #1c1c1e; 
                color: #f1f5f9; 
                border: 1px solid rgba(255, 255, 255, 0.16); 
                border-radius: 10px; 
                padding: 6px; 
            }
            QMenu::item { 
                padding: 8px 22px 8px 12px; 
                border-radius: 6px; 
                font-size: 13px; 
            }
            QMenu::item:selected { 
                background-color: #0284c7; 
                color: #ffffff; 
            }
            QMenu::separator { 
                height: 1px; 
                background: rgba(255, 255, 255, 0.12); 
                margin: 4px 8px; 
            }
        """)

        # 1. Tablo Ekle
        act_table = menu.addAction(ModernIconFactory.icon_table(), "  " + LanguageManager.tr("insert_table"))
        act_table.triggered.connect(self.main_window.show_insert_table_dialog)

        # 3. Emoji, Çıkartma ve GIF Ekle
        act_emoji = menu.addAction(ModernIconFactory.icon_emoji(), "  " + LanguageManager.tr("insert_emoji"))
        act_emoji.triggered.connect(self.main_window.show_insert_emoji_dialog)

        menu.addSeparator()

        # 4. Görsel Ekle
        act_img = menu.addAction(ModernIconFactory.icon_image(), "  " + LanguageManager.tr("insert_image"))
        act_img.triggered.connect(lambda: self.main_window.show_insert_image_dialog(default_tab=0))

        menu.addSeparator()

        # 5. Ses Dosyası / Kayıt Ekle
        act_audio = menu.addAction(ModernIconFactory.icon_mic(), "  " + LanguageManager.tr("insert_audio"))
        act_audio.triggered.connect(self.main_window.show_insert_audio_dialog)

        # 6. Video / Animasyon Ekle
        act_video = menu.addAction(ModernIconFactory.icon_video(), "  " + LanguageManager.tr("insert_video"))
        act_video.triggered.connect(self.main_window.show_insert_video_dialog)

        # Menü konumunu kenar yönüne göre konumlandır
        menu.adjustSize()
        hint = menu.sizeHint()
        btn_pos = btn.mapToGlobal(QPoint(0, 0)) if hasattr(btn, 'mapToGlobal') else self.mapToGlobal(QPoint(0, 0))
        win_w = max(100, self.main_window.width())
        win_h = max(100, self.main_window.height())

        if self.edge == "left":
            x = btn_pos.x() + (btn.width() if hasattr(btn, 'width') else 40) + 6
            y = max(10, min(win_h - hint.height() - 10, btn_pos.y()))
        elif self.edge == "right":
            x = btn_pos.x() - hint.width() - 6
            y = max(10, min(win_h - hint.height() - 10, btn_pos.y()))
        elif self.edge == "top":
            x = max(10, min(win_w - hint.width() - 10, btn_pos.x()))
            y = btn_pos.y() + (btn.height() if hasattr(btn, 'height') else 40) + 6
        else:  # bottom
            x = max(10, min(win_w - hint.width() - 10, btn_pos.x()))
            y = btn_pos.y() - hint.height() - 6

        menu.aboutToHide.connect(lambda: self.hide_timer.start(2500))
        menu.exec(QPoint(int(x), int(y)))

    def _on_exit_fullscreen(self):
        if self.main_window.isFullScreen():
            self.main_window.toggle_fullscreen()

    def get_target_coords(self, visible=True):
        win_w = self.main_window.width()
        win_h = self.main_window.height()
        w = self.width()
        h = self.height()

        if self.edge == "left":
            x = 16 if visible else (-w - 10)
            y = max(20, (win_h - h) // 2)
        elif self.edge == "right":
            x = (win_w - w - 16) if visible else (win_w + 10)
            y = max(20, (win_h - h) // 2)
        elif self.edge == "top":
            x = max(20, (win_w - w) // 2)
            y = 16 if visible else (-h - 10)
        else: # bottom
            x = max(20, (win_w - w) // 2)
            y = (win_h - h - 16) if visible else (win_h + 10)

        return QPoint(int(x), int(y))

    def slide_in(self):
        if self._is_dragging:
            return
        self.hide_timer.stop()
        target_pos = self.get_target_coords(visible=True)
        self.show()
        self.raise_()
        self.anim.stop()
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if not self.isVisible() or not self.is_slid_in:
            win_w = self.main_window.width()
            win_h = self.main_window.height()
            w = self.width()
            h = self.height()
            if self.edge == "left":
                start_x = -w if self.x() > win_w // 2 else self.x()
                start_pos = QPoint(int(start_x), target_pos.y())
            elif self.edge == "right":
                start_x = win_w + 10 if self.x() < win_w // 2 else self.x()
                start_pos = QPoint(int(start_x), target_pos.y())
            elif self.edge == "top":
                start_y = -h if self.y() > win_h // 2 else self.y()
                start_pos = QPoint(target_pos.x(), int(start_y))
            else: # bottom
                start_y = win_h + 10 if self.y() < win_h // 2 else self.y()
                start_pos = QPoint(target_pos.x(), int(start_y))
            self.anim.setStartValue(start_pos)
        else:
            self.anim.setStartValue(self.pos())

        self.anim.setEndValue(target_pos)
        self.anim.start()
        self.is_slid_in = True

    def slide_out(self):
        if self._is_dragging:
            return
        self.hide_timer.stop()
        target_pos = self.get_target_coords(visible=False)
        self.anim.stop()
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(target_pos)
        self.anim.start()
        self.is_slid_in = False

    def reposition(self):
        if self._is_dragging:
            return
        target_pos = self.get_target_coords(visible=self.is_slid_in)
        self.move(target_pos)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not getattr(self, '_is_dragging', False):
            self.hide_timer.start()
        super().leaveEvent(event)

    def show_fullscreen_mode(self):
        self.update_active_tool(self.main_window.current_tool)
        self.slide_in()
        self.hide_timer.start(3500)

    def hide_fullscreen_mode(self):
        if getattr(self, '_active_popup', None) and self._active_popup.isVisible():
            self._active_popup.close()
            self._active_popup = None
        self.hide_timer.stop()
        self.anim.stop()
        self.hide()
        self.is_slid_in = False
        self.move(-self.width() - 80, -self.height() - 80)


# --- 10. SOL ÇOK SEKMELİ YAN PANEL (THUMBNAILS, BOOKMARKS & ATTACHMENTS DOCK) ---
class EmptyThumbsWidget(QWidget):
    def __init__(self, dock, parent=None):
        super().__init__(parent)
        self.dock = dock

    def contextMenuEvent(self, event):
        self.dock._show_thumbnails_context_menu(event.pos(), source_widget=self)
        event.accept()


class ThumbnailsDock(QDockWidget):
    def __init__(self, main_window):
        super().__init__(LanguageManager.tr("dock_title"), main_window)
        self.main_window = main_window
        self.is_loaded = False
        self._current_tab_doc = None
        self._rendered_pages = set()
        self._render_queue = []
        self._raw_thumb_images = {}
        self._loading_bookmarks = False

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._process_render_queue)

        self.setStyleSheet("""
            QDockWidget { color: #f0f0f0; background: #1c1c1e; font-size: 12px; }
            QDockWidget::title { background: #242426; padding: 6px 10px; text-align: left; font-weight: 600; }
            QWidget#SidebarHeader { background: #202022; border-bottom: 1px solid #2d2d30; }
            QToolButton.SidebarTab {
                background: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 5px;
                padding: 4px 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QToolButton.SidebarTab:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #f1f5f9;
            }
            QToolButton.SidebarTab:checked {
                background: #232d3d;
                color: #38bdf8;
                font-weight: 600;
            }
            QListWidget, QTreeWidget {
                background-color: #18181a;
                border: none;
                color: #e2e8f0;
            }
            QListWidget::item {
                background-color: #242428;
                border: 1px solid #323238;
                border-radius: 5px;
                padding: 5px;
                margin: 3px 5px;
                color: #cbd5e1;
            }
            QListWidget::item:hover {
                background-color: #2c2c32;
                border-color: #4b5563;
            }
            QListWidget::item:selected {
                background-color: #1e3a5f;
                border: 1.5px solid #38bdf8;
                color: #ffffff;
                font-weight: bold;
            }
            QTreeWidget::item {
                padding: 5px 6px;
                margin: 2px 4px;
                border-radius: 4px;
                color: #cbd5e1;
            }
            QTreeWidget::item:hover {
                background-color: #26262b;
                color: #ffffff;
            }
            QTreeWidget::item:selected {
                background-color: #1e3a5f;
                color: #38bdf8;
                font-weight: bold;
            }
            QTreeWidget QLineEdit {
                background-color: #27272a;
                color: #ffffff;
                border: 1.5px solid #0284c7;
                border-radius: 4px;
                padding: 2px 5px;
                selection-background-color: #0369a1;
                selection-color: #ffffff;
                font-size: 12px;
            }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Apple tarzı segmented kontrol çubuğu
        self.header_bar = QWidget()
        self.header_bar.setObjectName("SidebarHeader")
        self.header_bar.setFixedHeight(34)
        h_layout = QHBoxLayout(self.header_bar)
        h_layout.setContentsMargins(4, 3, 4, 3)
        h_layout.setSpacing(3)

        self.btn_tab_thumbs = QToolButton()
        self.btn_tab_thumbs.setProperty("class", "SidebarTab")
        self.btn_tab_thumbs.setIcon(ModernIconFactory.icon_thumbnails())
        self.btn_tab_thumbs.setText(" " + LanguageManager.tr("sidebar_thumbnails"))
        self.btn_tab_thumbs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_thumbs.setCheckable(True)
        self.btn_tab_thumbs.setChecked(True)
        self.btn_tab_thumbs.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_bookmarks = QToolButton()
        self.btn_tab_bookmarks.setProperty("class", "SidebarTab")
        self.btn_tab_bookmarks.setIcon(ModernIconFactory.icon_bookmark())
        self.btn_tab_bookmarks.setText(" " + LanguageManager.tr("sidebar_bookmarks"))
        self.btn_tab_bookmarks.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_bookmarks.setCheckable(True)
        self.btn_tab_bookmarks.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_attachments = QToolButton()
        self.btn_tab_attachments.setProperty("class", "SidebarTab")
        self.btn_tab_attachments.setIcon(ModernIconFactory.icon_attachment())
        self.btn_tab_attachments.setText(" " + LanguageManager.tr("sidebar_attachments"))
        self.btn_tab_attachments.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_attachments.setCheckable(True)
        self.btn_tab_attachments.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_comments = QToolButton()
        self.btn_tab_comments.setProperty("class", "SidebarTab")
        self.btn_tab_comments.setIcon(ModernIconFactory.icon_comments())
        self.btn_tab_comments.setText(" " + LanguageManager.tr("sidebar_comments"))
        self.btn_tab_comments.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_tab_comments.setCheckable(True)
        self.btn_tab_comments.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_tab_thumbs.clicked.connect(lambda: self.switch_view(0))
        self.btn_tab_bookmarks.clicked.connect(lambda: self.switch_view(1))
        self.btn_tab_attachments.clicked.connect(lambda: self.switch_view(2))
        self.btn_tab_comments.clicked.connect(lambda: self.switch_view(3))

        h_layout.addWidget(self.btn_tab_thumbs, 1)
        h_layout.addWidget(self.btn_tab_bookmarks, 1)
        h_layout.addWidget(self.btn_tab_attachments, 1)
        h_layout.addWidget(self.btn_tab_comments, 1)
        layout.addWidget(self.header_bar)

        # Görünüm katmanları (Stacked Widget)
        self.stacked = QStackedWidget()

        # 0: Küçük Resimler (Thumbnails) ve Boş Durum
        box_thumbs = QWidget()
        l_thumbs = QVBoxLayout(box_thumbs)
        l_thumbs.setContentsMargins(0, 0, 0, 0)
        l_thumbs.setSpacing(0)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(100, 140))
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.model().rowsMoved.connect(self._on_pages_reordered)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_thumbnails_context_menu)
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.installEventFilter(self)
        self.list_widget.viewport().installEventFilter(self)
        l_thumbs.addWidget(self.list_widget)

        # Boş Durum (Hiçbir PDF açık değilken)
        self.empty_thumbs_widget = EmptyThumbsWidget(self)
        self.empty_thumbs_widget.setAcceptDrops(True)
        self.empty_thumbs_widget.installEventFilter(self)
        l_empty = QVBoxLayout(self.empty_thumbs_widget)
        l_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_empty.setContentsMargins(18, 28, 18, 28)
        l_empty.setSpacing(10)

        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setPixmap(ModernIconFactory.icon_thumbnails().pixmap(44, 44))
        l_empty.addWidget(lbl_icon)

        self.lbl_empty_title = QLabel(LanguageManager.tr("sidebar_no_pages_title"))
        self.lbl_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_title.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 600; margin-top: 4px;")
        l_empty.addWidget(self.lbl_empty_title)

        self.lbl_empty_desc = QLabel(LanguageManager.tr("sidebar_no_pages_desc"))
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_desc.setStyleSheet("color: #94a3b8; font-size: 11px; margin-bottom: 6px; line-height: 1.4;")
        l_empty.addWidget(self.lbl_empty_desc)

        btn_style = """
            QPushButton {
                background-color: #27272a;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #0284c7;
                border-color: #38bdf8;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #0369a1;
            }
        """

        self.btn_empty_insert_pdf = QPushButton("  " + LanguageManager.tr("sidebar_btn_add_pdf"))
        self.btn_empty_insert_pdf.setIcon(ModernIconFactory.icon_new_document())
        self.btn_empty_insert_pdf.setIconSize(QSize(18, 18))
        self.btn_empty_insert_pdf.setStyleSheet(btn_style)
        self.btn_empty_insert_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_insert_pdf.clicked.connect(self._on_add_pdf_clicked)
        l_empty.addWidget(self.btn_empty_insert_pdf)

        self.btn_empty_add_blank = QPushButton("  " + LanguageManager.tr("sidebar_btn_add_blank"))
        self.btn_empty_add_blank.setIcon(ModernIconFactory.icon_add_page())
        self.btn_empty_add_blank.setIconSize(QSize(18, 18))
        self.btn_empty_add_blank.setStyleSheet(btn_style)
        self.btn_empty_add_blank.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_add_blank.clicked.connect(self._on_add_blank_page_clicked)
        l_empty.addWidget(self.btn_empty_add_blank)

        l_thumbs.addWidget(self.empty_thumbs_widget)
        self.stacked.addWidget(box_thumbs)

        self.list_widget.hide()
        self.empty_thumbs_widget.show()

        # 1: Yer İmleri / İçindekiler (Bookmarks Tree)
        box_bm = QWidget()
        l_bm = QVBoxLayout(box_bm)
        l_bm.setContentsMargins(0, 0, 0, 0)
        self.tree_bookmarks = QTreeWidget()
        self.tree_bookmarks.setHeaderHidden(True)
        self.tree_bookmarks.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree_bookmarks.setExpandsOnDoubleClick(False)
        self.tree_bookmarks.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.tree_bookmarks.itemClicked.connect(self._on_bookmark_clicked)
        self.tree_bookmarks.itemDoubleClicked.connect(self._on_bookmark_double_clicked)
        self.tree_bookmarks.itemChanged.connect(self._on_bookmark_item_changed)
        self.tree_bookmarks.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_bookmarks.customContextMenuRequested.connect(self._show_bookmark_context_menu)
        self.lbl_no_bookmarks = QLabel(LanguageManager.tr("sidebar_no_bookmarks"))
        self.lbl_no_bookmarks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_bookmarks.setStyleSheet("color: #71717a; font-size: 11px; padding: 24px;")
        self.lbl_no_bookmarks.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lbl_no_bookmarks.customContextMenuRequested.connect(self._show_bookmark_context_menu)
        l_bm.addWidget(self.tree_bookmarks)
        l_bm.addWidget(self.lbl_no_bookmarks)
        self.stacked.addWidget(box_bm)

        # 2: Ekler / İliştirilmiş Dosyalar (Attachments List)
        box_att = QWidget()
        l_att = QVBoxLayout(box_att)
        l_att.setContentsMargins(0, 0, 0, 0)
        self.list_attachments = QListWidget()
        self.list_attachments.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_attachments.customContextMenuRequested.connect(self._show_attachment_context_menu)
        self.list_attachments.itemDoubleClicked.connect(self._on_attachment_double_clicked)
        self.lbl_no_attachments = QLabel(LanguageManager.tr("sidebar_no_attachments"))
        self.lbl_no_attachments.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_attachments.setStyleSheet("color: #71717a; font-size: 11px; padding: 24px;")
        l_att.addWidget(self.list_attachments)
        l_att.addWidget(self.lbl_no_attachments)
        self.stacked.addWidget(box_att)

        # 3: Yorumlar & Ek Açıklamalar (Comments & Annotations)
        box_com = QWidget()
        l_com = QVBoxLayout(box_com)
        l_com.setContentsMargins(4, 4, 4, 4)
        l_com.setSpacing(4)

        self.txt_filter_comments = QLineEdit()
        self.txt_filter_comments.setPlaceholderText(LanguageManager.tr("search") + "...")
        self.txt_filter_comments.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; padding: 4px 6px; color: #f1f5f9; font-size: 11px;")
        self.txt_filter_comments.textChanged.connect(self._filter_comments)
        l_com.addWidget(self.txt_filter_comments)

        self.tree_comments = QTreeWidget()
        self.tree_comments.setHeaderHidden(True)
        self.tree_comments.itemClicked.connect(self._on_comment_clicked)
        self.lbl_no_comments = QLabel(LanguageManager.tr("comments_no_items"))
        self.lbl_no_comments.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_comments.setStyleSheet("color: #71717a; font-size: 11px; padding: 24px;")
        l_com.addWidget(self.tree_comments)
        l_com.addWidget(self.lbl_no_comments)
        self.stacked.addWidget(box_com)

        layout.addWidget(self.stacked)
        self.setWidget(container)

    def switch_view(self, index: int):
        self.btn_tab_thumbs.setChecked(index == 0)
        self.btn_tab_bookmarks.setChecked(index == 1)
        self.btn_tab_attachments.setChecked(index == 2)
        self.btn_tab_comments.setChecked(index == 3)
        self.stacked.setCurrentIndex(index)
        if index == 0:
            self.load_thumbnails_lazy()
        elif index == 1:
            self.load_bookmarks()
        elif index == 2:
            self.load_attachments()
        elif index == 3:
            self.load_comments()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_thumbnails_lazy()
        tab_doc = self.main_window.get_current_tab_doc()
        if tab_doc and tab_doc.doc is not None:
            self.select_page(tab_doc.current_page_idx)

    def apply_theme(self, theme_name: str = "dark", spec: Optional[dict] = None):
        if not spec:
            return
        bg = spec.get("tb_bg", "#1c1c1e")
        main_bg = spec.get("main_bg", "#121212")
        title_bg = spec.get("tab_bg", "#242426")
        border = spec.get("tb_border", "#2d2d30")
        accent = spec.get("accent", "#38bdf8")
        text = spec.get("main_text", "#f0f0f0")
        btn_hover = spec.get("btn_hover", "#2c2c32")
        tab_text = spec.get("tab_text", "#94a3b8")

        self.setStyleSheet(f"""
            QDockWidget {{ color: {text}; background: {bg}; font-size: 12px; }}
            QDockWidget::title {{ background: {title_bg}; padding: 6px 10px; text-align: left; font-weight: 600; color: {text}; }}
            QWidget#SidebarHeader {{ background: {title_bg}; border-bottom: 1px solid {border}; }}
            QToolButton.SidebarTab {{
                background: transparent;
                color: {tab_text};
                border: none;
                border-radius: 5px;
                padding: 4px 6px;
                font-size: 11px;
                font-weight: 500;
            }}
            QToolButton.SidebarTab:hover {{
                background: {btn_hover};
                color: #ffffff;
            }}
            QToolButton.SidebarTab:checked {{
                background: {btn_hover};
                color: {accent};
                border-bottom: 2.5px solid {accent};
                font-weight: 600;
            }}
            QListWidget, QTreeWidget {{
                background-color: {main_bg};
                border: none;
                color: {text};
            }}
            QListWidget::item {{
                background-color: {title_bg};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 5px;
                margin: 3px 5px;
                color: {text};
            }}
            QListWidget::item:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QListWidget::item:selected {{
                background-color: {btn_hover};
                border: 1.5px solid {accent};
                color: #ffffff;
                font-weight: bold;
            }}
            QTreeWidget::item {{
                padding: 5px 6px;
                margin: 2px 4px;
                border-radius: 4px;
                color: {text};
            }}
            QTreeWidget::item:hover {{
                background-color: {btn_hover};
                color: #ffffff;
            }}
            QTreeWidget::item:selected {{
                background-color: {btn_hover};
                color: {accent};
                font-weight: bold;
            }}
            QTreeWidget QLineEdit {{
                background-color: {main_bg};
                color: #ffffff;
                border: 1.5px solid {accent};
                border-radius: 4px;
                padding: 2px 5px;
                selection-background-color: {accent};
                selection-color: #ffffff;
                font-size: 12px;
            }}
        """)

    def _is_pos_on_bookmark_ribbon(self, pos: QPoint) -> tuple:
        item = self.list_widget.itemAt(pos)
        if not item:
            return False, None, -1
        page_idx = item.data(Qt.ItemDataRole.UserRole)
        if page_idx is None or page_idx < 0:
            return False, item, -1

        bookmarked_pages = self.get_bookmarked_pages()
        if page_idx not in bookmarked_pages:
            return False, item, page_idx

        item_rect = self.list_widget.visualItemRect(item)
        opt = QStyleOptionViewItem()
        self.list_widget.initViewItemOption(opt)
        opt.rect = item_rect
        opt.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration
        opt.decorationSize = self.list_widget.iconSize()

        style = self.list_widget.style()
        icon_rect = style.subElementRect(style.SubElement.SE_ItemViewItemDecoration, opt, self.list_widget)

        ribbon_hit_rect = QRect(icon_rect.right() - 28, icon_rect.top() - 2, 30, 34)
        if ribbon_hit_rect.contains(pos):
            return True, item, page_idx
        return False, item, page_idx

    def _find_bookmark_tree_item(self, page_idx: int) -> Optional[QTreeWidgetItem]:
        def search_node(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) == page_idx:
                    return child
                res = search_node(child)
                if res:
                    return res
            return None

        for i in range(self.tree_bookmarks.topLevelItemCount()):
            top_item = self.tree_bookmarks.topLevelItem(i)
            if top_item.data(0, Qt.ItemDataRole.UserRole) == page_idx:
                return top_item
            res = search_node(top_item)
            if res:
                return res
        return None

    def show_bookmark_for_page(self, page_idx: int):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        # 1. Sayfaya git
        tab_doc.go_to_page(page_idx)

        # 2. İçindekiler sekmesine geç
        self.switch_view(1)

        # 3. İlgili yer imi öğesini ağaçta bul ve seç
        target_item = self._find_bookmark_tree_item(page_idx)
        if target_item:
            curr = target_item.parent()
            while curr:
                curr.setExpanded(True)
                curr = curr.parent()

            self.tree_bookmarks.clearSelection()
            target_item.setSelected(True)
            self.tree_bookmarks.setCurrentItem(target_item)
            self.tree_bookmarks.scrollToItem(target_item, QAbstractItemView.ScrollHint.PositionAtCenter)
            self.tree_bookmarks.setFocus()

            title = target_item.text(0)
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(f"Yer İmi: {title} (Sayfa {page_idx + 1})", 3500)
        else:
            if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                self.main_window.statusBar().showMessage(f"Sayfa {page_idx + 1} yer imi gösterildi", 3000)

    def eventFilter(self, source, event):
        if source == self.list_widget.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                is_hit, item, page_idx = self._is_pos_on_bookmark_ribbon(event.pos())
                if is_hit and page_idx >= 0:
                    self.show_bookmark_for_page(page_idx)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                is_hit, item, page_idx = self._is_pos_on_bookmark_ribbon(event.pos())
                if is_hit:
                    self.list_widget.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.list_widget.viewport().unsetCursor()
            elif event.type() == QEvent.Type.Leave:
                self.list_widget.viewport().unsetCursor()

        if source in (self.list_widget, getattr(self, 'empty_thumbs_widget', None)):
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
                    if pdf_urls:
                        self.main_window.handle_dropped_urls(pdf_urls)
                        event.acceptProposedAction()
                        return True
        return super().eventFilter(source, event)

    def _show_thumbnails_context_menu(self, pos, source_widget=None):
        if source_widget is None:
            source_widget = self.sender()
        if source_widget == getattr(self, 'empty_thumbs_widget', None):
            global_pos = self.empty_thumbs_widget.mapToGlobal(pos)
            item = None
        else:
            global_pos = self.list_widget.mapToGlobal(pos)
            item = self.list_widget.itemAt(pos)

        idx = item.data(Qt.ItemDataRole.UserRole) if item else -1
        tab_doc = self.main_window.get_current_tab_doc()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)
        
        act_show_bm = None
        if item and idx >= 0 and idx in self.get_bookmarked_pages():
            act_show_bm = menu.addAction(ModernIconFactory.icon_bookmark(), "İçindekiler'de Göster")
            menu.addSeparator()

        act_add_blank = menu.addAction(ModernIconFactory.icon_add_page(), LanguageManager.tr("sidebar_btn_add_blank"))
        act_change_style = menu.addAction(ModernIconFactory.icon_brush(), LanguageManager.tr("change_page_style_action")) if item else None
        act_insert_pdf = menu.addAction(ModernIconFactory.icon_new_document(), LanguageManager.tr("sidebar_btn_add_pdf"))
        act_del = menu.addAction("Sayfayı Sil") if item else None
        
        chosen = menu.exec(global_pos)
        if not chosen:
            return

        if chosen == act_show_bm:
            self.show_bookmark_for_page(idx)
        elif chosen == act_add_blank:
            self._on_add_blank_page_clicked()
        elif chosen == act_change_style and item and hasattr(self.main_window, 'show_change_page_style_dialog'):
            self.main_window.show_change_page_style_dialog(idx)
        elif chosen == act_insert_pdf:
            if tab_doc and tab_doc.doc is not None:
                path, _ = QFileDialog.getOpenFileName(self, "Eklenecek PDF Dosyasını Seç", "", "PDF Dosyaları (*.pdf)")
                if path:
                    tab_doc.insert_pdf_at(path, idx if idx >= 0 else None)
            else:
                self._on_add_pdf_clicked()
        elif chosen == act_del and item:
            if tab_doc and tab_doc.doc is not None:
                tab_doc.delete_page(idx)

    def _on_add_blank_page_clicked(self):
        if hasattr(self.main_window, 'show_new_page_dialog'):
            self.main_window.show_new_page_dialog()
            return

        tab_doc = self.main_window.get_current_tab_doc()
        curr_item = self.list_widget.currentItem() if (tab_doc and tab_doc.doc is not None) else None
        idx = curr_item.data(Qt.ItemDataRole.UserRole) if curr_item else None

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 8px 24px; border-radius: 4px; font-size: 13px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)

        styles = [
            (LanguageManager.tr("template_blank"), "blank"),
            (LanguageManager.tr("template_grid"), "grid"),
            (LanguageManager.tr("template_lines"), "lined"),
            (LanguageManager.tr("template_dotted"), "dotted"),
            (LanguageManager.tr("template_cornell"), "cornell"),
            (LanguageManager.tr("template_cover"), "cover")
        ]

        for name, style_code in styles:
            action = menu.addAction(name)
            action.setData(style_code)

        if not tab_doc or tab_doc.doc is None:
            pos = self.btn_empty_add_blank.mapToGlobal(QPoint(0, self.btn_empty_add_blank.height())) if hasattr(self, 'btn_empty_add_blank') else QCursor.pos()
        else:
            pos = QCursor.pos()

        chosen = menu.exec(pos)
        if chosen:
            style = chosen.data()
            if tab_doc and tab_doc.doc is not None:
                tab_doc.insert_blank_page(idx, style=style)
            else:
                self.main_window.new_blank_document(style)

    def _on_add_pdf_clicked(self):
        tab_doc = self.main_window.get_current_tab_doc()
        if tab_doc and tab_doc.doc is not None:
            curr_item = self.list_widget.currentItem()
            idx = curr_item.data(Qt.ItemDataRole.UserRole) if curr_item else None
            path, _ = QFileDialog.getOpenFileName(self, "Eklenecek PDF Dosyasını Seç", "", "PDF Dosyaları (*.pdf)")
            if path:
                tab_doc.insert_pdf_at(path, idx)
        else:
            paths, _ = QFileDialog.getOpenFileNames(self, "PDF Dosyası Seç", "", "PDF Dosyaları (*.pdf)")
            if paths:
                for path in paths:
                    self.main_window.add_pdf_tab(path)

    def _on_pages_reordered(self, parent, start, end, destination, row):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            new_order.append(item.data(Qt.ItemDataRole.UserRole))
        tab_doc.reorder_pages(new_order)
        
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setData(Qt.ItemDataRole.UserRole, i)
        
        self.load_thumbnails_lazy()

    def _on_item_clicked(self, item):
        idx = item.data(Qt.ItemDataRole.UserRole)
        tab_doc = self.main_window.get_current_tab_doc()
        if idx is not None and tab_doc:
            tab_doc.go_to_page(idx)

    def _on_bookmark_clicked(self, item, column):
        page_idx = item.data(0, Qt.ItemDataRole.UserRole)
        tab_doc = self.main_window.get_current_tab_doc()
        if page_idx is not None and tab_doc:
            tab_doc.go_to_page(page_idx)

    def _on_bookmark_double_clicked(self, item, column):
        if not item:
            return
        self.tree_bookmarks.editItem(item, 0)

    def _on_bookmark_item_changed(self, item, column):
        if getattr(self, '_loading_bookmarks', False):
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return

        new_title = item.text(0).strip()
        old_title = item.data(0, Qt.ItemDataRole.UserRole + 2)
        toc_idx = item.data(0, Qt.ItemDataRole.UserRole + 1)
        page_idx = item.data(0, Qt.ItemDataRole.UserRole)

        if not new_title:
            # Boş başlığa izin verilmez, eski başlığa geri dön
            self._loading_bookmarks = True
            item.setText(0, old_title or "")
            self._loading_bookmarks = False
            return

        if new_title == old_title:
            return

        try:
            toc = tab_doc.doc.get_toc(simple=False)
            old_toc = [list(e) for e in toc]
            found = False

            # Önce kesin TOC indeksine göre kontrol et
            if toc_idx is not None and 0 <= toc_idx < len(toc):
                if toc[toc_idx][1] == old_title:
                    toc[toc_idx][1] = new_title
                    found = True

            # Bulunamazsa eski başlık ve sayfa numarasına göre ara
            if not found:
                target_page_1_based = (page_idx + 1) if page_idx is not None else None
                for i, entry in enumerate(toc):
                    if entry[1] == old_title and (target_page_1_based is None or (len(entry) > 2 and entry[2] == target_page_1_based)):
                        toc[i][1] = new_title
                        found = True
                        break

            # Sadece başlığa göre ara
            if not found:
                for i, entry in enumerate(toc):
                    if entry[1] == old_title:
                        toc[i][1] = new_title
                        found = True
                        break

            if found:
                tab_doc.doc.set_toc(toc)
                tab_doc.set_modified(True)
                tab_doc.push_undo_action({
                    "type": "bookmark",
                    "old_toc": old_toc,
                    "new_toc": [list(e) for e in toc]
                })
                item.setData(0, Qt.ItemDataRole.UserRole + 2, new_title)
                if hasattr(tab_doc, 'update_bookmark_ribbons'):
                    tab_doc.update_bookmark_ribbons()
                if hasattr(self, 'refresh_bookmark_indicators'):
                    self.refresh_bookmark_indicators()
                if hasattr(self.main_window, 'statusBar') and self.main_window.statusBar():
                    self.main_window.statusBar().showMessage(f"Yer imi güncellendi: {new_title}", 3000)
        except Exception as e:
            print(f"Yer imi yeniden adlandırma hatası: {e}")

    def load_bookmarks(self):
        self._loading_bookmarks = True
        self.tree_bookmarks.blockSignals(True)
        self.tree_bookmarks.clear()
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.tree_bookmarks.hide()
            self.lbl_no_bookmarks.show()
            self.tree_bookmarks.blockSignals(False)
            self._loading_bookmarks = False
            if hasattr(self, 'refresh_bookmark_indicators'):
                self.refresh_bookmark_indicators()
            return
        
        try:
            toc = tab_doc.doc.get_toc(simple=False)
        except Exception:
            toc = []

        if not toc:
            self.tree_bookmarks.hide()
            self.lbl_no_bookmarks.show()
            self.tree_bookmarks.blockSignals(False)
            self._loading_bookmarks = False
            if tab_doc and hasattr(tab_doc, 'update_bookmark_ribbons'):
                tab_doc.update_bookmark_ribbons()
            if hasattr(self, 'refresh_bookmark_indicators'):
                self.refresh_bookmark_indicators()
            return

        self.lbl_no_bookmarks.hide()
        self.tree_bookmarks.show()

        items_by_level = {0: self.tree_bookmarks.invisibleRootItem()}
        first_item_for_page = {}

        for toc_idx, entry in enumerate(toc):
            lvl = entry[0]
            title = str(entry[1] or "").strip()
            page_1_based = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 0

            is_sub = False
            # Eğer bu sayfaya ait daha önce eklenmiş bir ana yer imi varsa, bunu onun altına alt başlık yap
            if page_1_based > 0 and page_1_based in first_item_for_page:
                parent = first_item_for_page[page_1_based]
                is_sub = True
            else:
                parent = items_by_level.get(lvl - 1, self.tree_bookmarks.invisibleRootItem())

            tree_item = QTreeWidgetItem(parent)
            tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsEditable)
            tree_item.setText(0, f"{title}")
            tree_item.setIcon(0, ModernIconFactory.icon_bookmark())

            if page_1_based > 0:
                if is_sub:
                    tree_item.setToolTip(0, f"Sayfa {page_1_based} • Alt Yer İmi (Çift tıklayarak düzenleyin / F2)")
                    tree_item.setForeground(0, QBrush(QColor("#94a3b8")))
                else:
                    tree_item.setToolTip(0, f"Sayfa {page_1_based} • Çift tıklayarak yeniden adlandırın (F2)")
                    tree_item.setForeground(0, QBrush(QColor("#f1f5f9")))
                tree_item.setData(0, Qt.ItemDataRole.UserRole, page_1_based - 1)
            else:
                tree_item.setToolTip(0, "Çift tıklayarak yeniden adlandırın (F2)")
                tree_item.setData(0, Qt.ItemDataRole.UserRole, None)

            tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, toc_idx)
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 2, title)
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 3, lvl)
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 4, is_sub)

            if page_1_based > 0 and page_1_based not in first_item_for_page:
                first_item_for_page[page_1_based] = tree_item

            if not is_sub:
                items_by_level[lvl] = tree_item

        self.tree_bookmarks.expandAll()
        self.tree_bookmarks.blockSignals(False)
        self._loading_bookmarks = False

        if tab_doc and hasattr(tab_doc, 'update_bookmark_ribbons'):
            tab_doc.update_bookmark_ribbons()
        if hasattr(self, 'refresh_bookmark_indicators'):
            self.refresh_bookmark_indicators()

    def load_attachments(self):
        self.list_attachments.clear()
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.list_attachments.hide()
            self.lbl_no_attachments.show()
            return

        try:
            names = tab_doc.doc.embfile_names() if hasattr(tab_doc.doc, 'embfile_names') else []
        except Exception:
            names = []

        if not names:
            self.list_attachments.hide()
            self.lbl_no_attachments.show()
            return

        self.lbl_no_attachments.hide()
        self.list_attachments.show()

        for name in names:
            info = {}
            try:
                info = tab_doc.doc.embfile_info(name)
            except Exception:
                pass
            size_bytes = info.get("size", 0) if isinstance(info, dict) else 0
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"
            elif size_bytes > 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes > 0:
                size_str = f"{size_bytes} B"
            else:
                size_str = ""

            display_text = f"{name}"
            if size_str:
                display_text += f" ({size_str})"
            item = QListWidgetItem(ModernIconFactory.icon_attachment(), display_text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_attachments.addItem(item)

    def load_comments(self):
        self.tree_comments.clear()
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            self.tree_comments.hide()
            self.lbl_no_comments.show()
            return

        items_found = 0
        pages_dict = {}

        # 1. Dokümandaki PyMuPDF ek açıklamaları
        for p_idx in range(len(tab_doc.doc)):
            try:
                page = tab_doc.doc[p_idx]
                for annot in page.annots():
                    a_type_name = annot.type[1]
                    info = annot.info or {}
                    content = info.get("content", "") or annot.get_text() or a_type_name
                    pages_dict.setdefault(p_idx, []).append({
                        "type": a_type_name,
                        "title": content[:60],
                        "rect": annot.rect,
                        "page": p_idx
                    })
                    items_found += 1
            except Exception:
                pass

        # 2. Sahnede çizilmiş nesneler
        for d in getattr(tab_doc, 'drawings', []):
            p_idx = d.get("page", 0)
            d_type = d.get("type", "çizim")
            text_preview = d.get("text", "") or d_type
            pages_dict.setdefault(p_idx, []).append({
                "type": d_type,
                "title": str(text_preview)[:60],
                "rect": None,
                "y": d.get("y", 0),
                "page": p_idx
            })
            items_found += 1

        if items_found == 0:
            self.tree_comments.hide()
            self.lbl_no_comments.show()
            return

        self.lbl_no_comments.hide()
        self.tree_comments.show()

        for p_idx in sorted(pages_dict.keys()):
            annots = pages_dict[p_idx]
            page_item = QTreeWidgetItem(self.tree_comments)
            page_item.setText(0, f"Sayfa {p_idx + 1} ({len(annots)})")
            page_item.setExpanded(True)
            for a in annots:
                sub = QTreeWidgetItem(page_item)
                icon = ModernIconFactory.icon_highlighter() if "high" in a['type'].lower() else ModernIconFactory.icon_comments()
                sub.setIcon(0, icon)
                sub.setText(0, f"[{a['type']}] {a['title']}")
                sub.setData(0, Qt.ItemDataRole.UserRole, a)

    def _on_comment_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc:
            return
        p_idx = data.get("page", 0)
        tab_doc.go_to_page(p_idx)

    def _filter_comments(self, text: str):
        query = text.strip().lower()
        for i in range(self.tree_comments.topLevelItemCount()):
            top = self.tree_comments.topLevelItem(i)
            match_any = False
            for j in range(top.childCount()):
                child = top.child(j)
                txt = child.text(0).lower()
                visible = not query or query in txt
                child.setHidden(not visible)
                if visible:
                    match_any = True
            top.setHidden(not match_any)

    def _show_bookmark_context_menu(self, pos):
        item = self.tree_bookmarks.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)
        
        act_rename = menu.addAction(ModernIconFactory.icon_bookmark(), "Yeniden Adlandır (F2)") if item else None
        act_add_sub = menu.addAction(ModernIconFactory.icon_bookmark(), "Bu Sayfaya Alt Yer İmi Ekle...") if item else None
        act_edit = menu.addAction("Düzenle (Başlık & Sayfa)...") if item else None
        act_add = menu.addAction("Yeni Yer İmi Ekle...")
        act_del = menu.addAction("Sil") if item else None
        
        chosen = menu.exec(self.tree_bookmarks.mapToGlobal(pos))
        if chosen == act_rename and item:
            self.tree_bookmarks.editItem(item, 0)
        elif chosen == act_add_sub and item:
            self._add_sub_bookmark(item)
        elif chosen == act_add:
            self._add_bookmark(item)
        elif chosen == act_edit and item:
            self._edit_bookmark(item)
        elif chosen == act_del and item:
            self._delete_bookmark(item)

    def _add_sub_bookmark(self, parent_item):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc or not parent_item: return
        page_idx = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if page_idx is not None:
            tab_doc.add_custom_page_bookmark(page_idx)
        else:
            self._add_bookmark(parent_item)

    def _add_bookmark(self, parent_item=None):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        
        from PyQt6.QtWidgets import QInputDialog
        title, ok = QInputDialog.getText(self, "Yer İmi Ekle", "Başlık:")
        if not ok or not title.strip(): return
        
        page_str, ok2 = QInputDialog.getText(self, "Yer İmi Ekle", "Sayfa Numarası (1'den başlar):")
        if not ok2 or not page_str.isdigit(): return
        page_num = int(page_str)
        
        toc = tab_doc.doc.get_toc(simple=False)
        old_toc = [list(e) for e in toc]

        # Bu sayfaya ait mevcut yer imleri var mı kontrol et
        existing_indices = [
            i for i, entry in enumerate(toc)
            if len(entry) > 2 and isinstance(entry[2], int) and entry[2] == page_num
        ]
        
        if parent_item:
            insert_idx = len(toc)
            level = 1
            for i, entry in enumerate(toc):
                if entry[1] == parent_item.text(0):
                    insert_idx = i + 1
                    level = entry[0] + 1
                    break
        elif existing_indices:
            parent_level = toc[existing_indices[0]][0]
            level = parent_level + 1
            insert_idx = existing_indices[-1] + 1
        else:
            level = 1
            insert_idx = len(toc)
            for i, entry in enumerate(toc):
                p_num = entry[2] if len(entry) > 2 and isinstance(entry[2], int) else 0
                if p_num > page_num:
                    insert_idx = i
                    break
        
        toc.insert(insert_idx, [level, title.strip(), page_num])
        tab_doc.doc.set_toc(toc)
        tab_doc.set_modified(True)
        tab_doc.push_undo_action({
            "type": "bookmark",
            "old_toc": old_toc,
            "new_toc": [list(e) for e in toc]
        })
        self.load_bookmarks()

    def _edit_bookmark(self, item):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        
        from PyQt6.QtWidgets import QInputDialog
        old_title = item.text(0)
        title, ok = QInputDialog.getText(self, "Yer İmini Düzenle", "Yeni Başlık:", text=old_title)
        if not ok or not title.strip(): return
        
        old_page = item.data(0, Qt.ItemDataRole.UserRole)
        page_str = str(old_page + 1) if old_page is not None else ""
        new_page_str, ok2 = QInputDialog.getText(self, "Yer İmini Düzenle", "Yeni Sayfa Numarası:", text=page_str)
        if not ok2 or not new_page_str.isdigit(): return
        new_page = int(new_page_str)
        
        toc = tab_doc.doc.get_toc(simple=False)
        old_toc = [list(e) for e in toc]
        toc_idx = item.data(0, Qt.ItemDataRole.UserRole + 1)

        found_idx = -1
        if toc_idx is not None and 0 <= toc_idx < len(toc) and toc[toc_idx][1] == old_title:
            found_idx = toc_idx
        else:
            for i, entry in enumerate(toc):
                if entry[1] == old_title:
                    found_idx = i
                    break

        if found_idx >= 0:
            toc[found_idx][1] = title.strip()
            if len(toc[found_idx]) > 2:
                toc[found_idx][2] = new_page
            else:
                toc[found_idx].append(new_page)

        tab_doc.doc.set_toc(toc)
        tab_doc.set_modified(True)
        tab_doc.push_undo_action({
            "type": "bookmark",
            "old_toc": old_toc,
            "new_toc": [list(e) for e in toc]
        })
        self.load_bookmarks()

    def _delete_bookmark(self, item):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        
        toc = tab_doc.doc.get_toc(simple=False)
        old_toc = [list(e) for e in toc]
        old_title = item.text(0)
        toc_idx = item.data(0, Qt.ItemDataRole.UserRole + 1)
        
        remove_indices = []
        found_idx = -1

        if toc_idx is not None and 0 <= toc_idx < len(toc) and toc[toc_idx][1] == old_title:
            found_idx = toc_idx
        else:
            for i, entry in enumerate(toc):
                if entry[1] == old_title:
                    found_idx = i
                    break

        if found_idx >= 0:
            found_level = toc[found_idx][0]
            remove_indices.append(found_idx)
            for i in range(found_idx + 1, len(toc)):
                if toc[i][0] > found_level:
                    remove_indices.append(i)
                else:
                    break

            for i in reversed(remove_indices):
                del toc[i]
                
            tab_doc.doc.set_toc(toc)
            tab_doc.set_modified(True)
            tab_doc.push_undo_action({
                "type": "bookmark",
                "old_toc": old_toc,
                "new_toc": [list(e) for e in toc]
            })
            self.load_bookmarks()

    def _show_attachment_context_menu(self, pos):
        item = self.list_attachments.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #242426; color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; font-size: 12px; }
            QMenu::item:selected { background-color: #0284c7; color: #ffffff; }
        """)
        
        act_add = menu.addAction("Dosya Ekle")
        act_open = menu.addAction(LanguageManager.tr("sidebar_open_attachment")) if item else None
        act_save = menu.addAction(LanguageManager.tr("sidebar_save_attachment")) if item else None
        act_del = menu.addAction("Sil") if item else None
        
        chosen = menu.exec(self.list_attachments.mapToGlobal(pos))
        if chosen == act_add:
            self._add_attachment()
        elif item:
            name = item.data(Qt.ItemDataRole.UserRole)
            if chosen == act_open:
                self._open_attachment(name)
            elif chosen == act_save:
                self._save_attachment(name)
            elif chosen == act_del:
                self._delete_attachment(name)

    def _add_attachment(self):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        path, _ = QFileDialog.getOpenFileName(self, "Eklenecek Dosyayı Seç")
        if path:
            try:
                with open(path, "rb") as f:
                    content = f.read()
                basename = os.path.basename(path)
                tab_doc.doc.embfile_add(basename, content)
                tab_doc.set_modified(True)
                self.load_attachments()
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya eklenemedi:\n{e}")

    def _delete_attachment(self, name):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc: return
        try:
            tab_doc.doc.embfile_del(name)
            tab_doc.set_modified(True)
            self.load_attachments()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Dosya silinemedi:\n{e}")

    def _on_attachment_double_clicked(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        if name:
            self._open_attachment(name)

    def _open_attachment(self, name: str):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            content = tab_doc.doc.embfile_get(name)
            temp_dir = tempfile.gettempdir()
            safe_name = os.path.basename(name)
            out_path = os.path.join(temp_dir, safe_name)
            with open(out_path, "wb") as f:
                f.write(content)
            os.startfile(out_path)
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("app_title"), f"Ek açılamadı:\n{e}")

    def _save_attachment(self, name: str):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return
        try:
            content = tab_doc.doc.embfile_get(name)
            safe_name = os.path.basename(name)
            out_path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("sidebar_save_attachment"), safe_name)
            if out_path:
                with open(out_path, "wb") as f:
                    f.write(content)
                QMessageBox.information(self, LanguageManager.tr("app_title"), LanguageManager.tr("sidebar_attachment_saved", path=out_path))
        except Exception as e:
            QMessageBox.warning(self, LanguageManager.tr("app_title"), f"Ek kaydedilemedi:\n{e}")

    def retranslate_ui(self):
        self.setWindowTitle(LanguageManager.tr("dock_title"))
        self.btn_tab_thumbs.setText(" " + LanguageManager.tr("sidebar_thumbnails"))
        self.btn_tab_bookmarks.setText(" " + LanguageManager.tr("sidebar_bookmarks"))
        self.btn_tab_attachments.setText(" " + LanguageManager.tr("sidebar_attachments"))
        self.lbl_no_bookmarks.setText(LanguageManager.tr("sidebar_no_bookmarks"))
        self.lbl_no_attachments.setText(LanguageManager.tr("sidebar_no_attachments"))
        if hasattr(self, 'lbl_empty_title'):
            self.lbl_empty_title.setText(LanguageManager.tr("sidebar_no_pages_title"))
        if hasattr(self, 'lbl_empty_desc'):
            self.lbl_empty_desc.setText(LanguageManager.tr("sidebar_no_pages_desc"))
        if hasattr(self, 'btn_empty_insert_pdf'):
            self.btn_empty_insert_pdf.setText("  " + LanguageManager.tr("sidebar_btn_add_pdf"))
        if hasattr(self, 'btn_empty_add_blank'):
            self.btn_empty_add_blank.setText("  " + LanguageManager.tr("sidebar_btn_add_blank"))

    def get_bookmarked_pages(self) -> set:
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not tab_doc.doc:
            return set()
        try:
            toc = tab_doc.doc.get_toc(simple=False)
            return {
                entry[2] - 1 for entry in toc
                if len(entry) > 2 and isinstance(entry[2], int) and entry[2] >= 1
            }
        except Exception:
            return set()

    def _draw_bookmark_ribbon_badge(self, base_pixmap: QPixmap) -> QPixmap:
        pix = base_pixmap.copy()
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rw = 16.0
        rh = 24.0
        rnotch = 5.5
        rx = max(0.0, float(pix.width()) - rw - 5.0)
        ry = 0.0

        # 1. Gölge efekti
        shadow_path = QPainterPath()
        shadow_path.moveTo(rx + 1.0, ry + 1.0)
        shadow_path.lineTo(rx + rw + 1.0, ry + 1.0)
        shadow_path.lineTo(rx + rw + 1.0, ry + rh + 1.5)
        shadow_path.lineTo(rx + rw / 2.0 + 1.0, ry + rh - rnotch + 1.5)
        shadow_path.lineTo(rx + 1.0, ry + rh + 1.5)
        shadow_path.closeSubpath()
        painter.fillPath(shadow_path, QColor(0, 0, 0, 80))

        # 2. Kurdele gövdesi (Kırmızı-koral gradient)
        ribbon_path = QPainterPath()
        ribbon_path.moveTo(rx, ry)
        ribbon_path.lineTo(rx + rw, ry)
        ribbon_path.lineTo(rx + rw, ry + rh)
        ribbon_path.lineTo(rx + rw / 2.0, ry + rh - rnotch)
        ribbon_path.lineTo(rx, ry + rh)
        ribbon_path.closeSubpath()

        grad = QLinearGradient(rx, ry, rx + rw, ry + rh)
        grad.setColorAt(0.0, QColor("#fb7185"))
        grad.setColorAt(0.45, QColor("#ef4444"))
        grad.setColorAt(1.0, QColor("#be123c"))

        painter.setPen(QPen(QColor("#881337"), 1.0))
        painter.setBrush(QBrush(grad))
        painter.drawPath(ribbon_path)

        # 3. Üst kenar katlantı yansıması
        painter.setPen(QPen(QColor(255, 255, 255, 160), 1.0))
        painter.drawLine(QPointF(rx + 1, ry + 0.5), QPointF(rx + rw - 1, ry + 0.5))

        # 4. Minyatür iç beyaz yer imi ikonu
        iw = 6.6
        ih = 8.8
        inot = 2.2
        ix = rx + (rw - iw) / 2.0
        iy = ry + 4.0
        ipath = QPainterPath()
        ipath.moveTo(ix, iy)
        ipath.lineTo(ix + iw, iy)
        ipath.lineTo(ix + iw, iy + ih)
        ipath.lineTo(ix + iw / 2.0, iy + ih - inot)
        ipath.lineTo(ix, iy + ih)
        ipath.closeSubpath()

        painter.setPen(QPen(QColor(255, 255, 255, 235), 0.9))
        painter.setBrush(QBrush(QColor(255, 255, 255, 75)))
        painter.drawPath(ipath)

        painter.end()
        return pix

    def _create_placeholder_pixmap(self, is_bookmarked: bool = False) -> QPixmap:
        pix = QPixmap(100, 140)
        pix.fill(QColor(36, 36, 36))
        if is_bookmarked:
            return self._draw_bookmark_ribbon_badge(pix)
        return pix

    def refresh_bookmark_indicators(self):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not self.is_loaded:
            return
        bookmarked_pages = self.get_bookmarked_pages()
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            if not item:
                continue
            is_bm = idx in bookmarked_pages
            if idx in self._raw_thumb_images:
                base_img = self._raw_thumb_images[idx]
                pix = QPixmap.fromImage(base_img)
                if is_bm:
                    pix = self._draw_bookmark_ribbon_badge(pix)
                item.setIcon(QIcon(pix))
            else:
                pix = self._create_placeholder_pixmap(is_bm)
                item.setIcon(QIcon(pix))

            p_num = idx + 1
            if is_bm:
                item.setToolTip(f"Sayfa {p_num} • Yer İmi Ekli")
            else:
                item.setToolTip(f"Sayfa {p_num}")

    def load_thumbnails_lazy(self):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None or len(tab_doc.doc) == 0:
            self.list_widget.clear()
            self.list_widget.hide()
            if hasattr(self, 'empty_thumbs_widget'):
                self.empty_thumbs_widget.show()
            self.is_loaded = False
            self._current_tab_doc = None
            self._rendered_pages.clear()
            self._render_queue.clear()
            self._raw_thumb_images.clear()
            self.tree_bookmarks.clear()
            self.tree_bookmarks.hide()
            self.lbl_no_bookmarks.show()
            self.list_attachments.clear()
            self.list_attachments.hide()
            self.lbl_no_attachments.show()
            return

        if hasattr(self, 'empty_thumbs_widget'):
            self.empty_thumbs_widget.hide()
        self.list_widget.show()

        total_pages = len(tab_doc.doc)
        curr_idx = getattr(tab_doc, 'current_page_idx', 0)

        # Fast path: already loaded for this tab_doc with same page count
        if self.is_loaded and self._current_tab_doc == tab_doc and self.list_widget.count() == total_pages:
            self.update_thumbnail(curr_idx)
            self.select_page(curr_idx)
            return

        # New document or cache invalidation
        self._render_timer.stop()
        self.list_widget.clear()
        self._rendered_pages.clear()
        self._render_queue.clear()
        self._raw_thumb_images.clear()
        self._current_tab_doc = tab_doc
        self.load_bookmarks()
        self.load_attachments()

        # Create lightweight placeholder items instantly (<1ms)
        bookmarked_pages = self.get_bookmarked_pages()
        for idx in range(total_pages):
            is_bm = idx in bookmarked_pages
            placeholder_pix = self._create_placeholder_pixmap(is_bm)
            item = QListWidgetItem(QIcon(placeholder_pix), f"{idx + 1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            if is_bm:
                item.setToolTip(f"Sayfa {idx + 1} • Yer İmi Ekli")
            else:
                item.setToolTip(f"Sayfa {idx + 1}")
            self.list_widget.addItem(item)
        self.is_loaded = True

        # Render current viewed page and immediate neighbors first
        immediate_pages = [curr_idx]
        for offset in (1, -1, 2, -2):
            p = curr_idx + offset
            if 0 <= p < total_pages:
                immediate_pages.append(p)

        for p in immediate_pages:
            self.update_thumbnail(p)

        # Immediately select and center on current page!
        self.select_page(curr_idx)

        # Queue remaining pages ordered by distance from current page
        remaining = [p for p in range(total_pages) if p not in self._rendered_pages]
        remaining.sort(key=lambda p: abs(p - curr_idx))
        self._render_queue = remaining

        if self._render_queue:
            self._render_timer.start(10)

    def _process_render_queue(self):
        if not self.isVisible() or not self.is_loaded or not self._render_queue:
            return
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or tab_doc != self._current_tab_doc:
            return

        # Batch render 2 pages per tick to keep UI 60fps smooth
        for _ in range(2):
            if not self._render_queue:
                break
            page_idx = self._render_queue.pop(0)
            if page_idx not in self._rendered_pages:
                self.update_thumbnail(page_idx)

        if self._render_queue:
            self._render_timer.start(10)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.is_loaded:
            self.load_thumbnails_lazy()

    def update_thumbnail(self, page_idx: int):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or tab_doc.doc is None:
            return
        if not self.is_loaded or page_idx < 0 or page_idx >= self.list_widget.count():
            return
        if not hasattr(tab_doc, 'page_positions') or page_idx not in tab_doc.page_positions:
            return

        pinfo = tab_doc.page_positions[page_idx]
        thumb_w = 100
        thumb_h = max(10, int(100 * (pinfo['height'] / max(1.0, pinfo['width']))))

        laser = getattr(tab_doc, 'laser_pointer_item', None)
        was_laser_vis = laser.isVisible() if laser else False
        if laser and was_laser_vis:
            laser.setVisible(False)

        sel_item = getattr(tab_doc, 'selection_item', None)
        was_sel_vis = sel_item.isVisible() if sel_item else False
        if sel_item and was_sel_vis:
            sel_item.setVisible(False)

        ribbon = getattr(tab_doc, 'bookmark_ribbon_items', {}).get(page_idx, None)
        was_ribbon_vis = ribbon.isVisible() if ribbon else False
        if ribbon and was_ribbon_vis:
            ribbon.setVisible(False)

        # Seçili öğelerin mavi kesikli çizgilerinin ve tutamaçlarının küçük resme yansımasını engelle
        selected_items = tab_doc.scene.selectedItems()
        for sit in selected_items:
            sit.setSelected(False)

        src_rect = QRectF(pinfo.get('left', 0), pinfo['top'], pinfo['width'], pinfo['height'])

        try:
            if pinfo['item'] and not pinfo['item'].pixmap().isNull():
                # Sayfa sahnede aktif çizilmiş durumda, canlı çizimlerle birlikte sahneden render et
                img = QImage(thumb_w, thumb_h, QImage.Format.Format_ARGB32_Premultiplied)
                img.fill(QColor(255, 255, 255))
                painter = QPainter(img)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                tab_doc.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                painter.end()
            else:
                # Sayfa ekranda değil veya pixmap null:
                # 1. PyMuPDF ile taban sayfayı 100px ölçeğinde anında ve ultra hafif render et
                page = tab_doc.doc[page_idx]
                p_w = max(1.0, page.rect.width)
                scale = float(thumb_w) / p_w
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                base_img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                img = base_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)

                # 2. Sayfa üzerindeki çizim ve medya elemanlarını (tablo, görsel, emoji, ses, video, çizim) sahneden çiz
                bg_rect = pinfo.get('bg_rect')
                was_bg_vis = bg_rect.isVisible() if bg_rect else False
                if bg_rect and was_bg_vis:
                    bg_rect.setVisible(False)
                pix_item = pinfo.get('item')
                was_pix_vis = pix_item.isVisible() if pix_item else False
                if pix_item and was_pix_vis:
                    pix_item.setVisible(False)

                painter = QPainter(img)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                try:
                    tab_doc.scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), src_rect)
                finally:
                    painter.end()
                    if bg_rect and was_bg_vis:
                        bg_rect.setVisible(True)
                    if pix_item and was_pix_vis:
                        pix_item.setVisible(True)
        finally:
            if laser and was_laser_vis:
                laser.setVisible(True)
            if sel_item and was_sel_vis:
                sel_item.setVisible(True)
            if ribbon and was_ribbon_vis:
                ribbon.setVisible(True)
            for sit in selected_items:
                sit.setSelected(True)

        # Ham resmi önbelleğe al
        self._raw_thumb_images[page_idx] = img.copy()

        item = self.list_widget.item(page_idx)
        if item:
            pixmap = QPixmap.fromImage(img)
            bookmarked_pages = self.get_bookmarked_pages()
            is_bm = page_idx in bookmarked_pages
            if is_bm:
                pixmap = self._draw_bookmark_ribbon_badge(pixmap)
                item.setToolTip(f"Sayfa {page_idx + 1} • Yer İmi Ekli")
            else:
                item.setToolTip(f"Sayfa {page_idx + 1}")
            item.setIcon(QIcon(pixmap))
            self.list_widget.viewport().update()
        self._rendered_pages.add(page_idx)

    def update_all_thumbnails(self):
        tab_doc = self.main_window.get_current_tab_doc()
        if not tab_doc or not self.is_loaded:
            return
        for page_idx in range(self.list_widget.count()):
            self.update_thumbnail(page_idx)

    def select_page(self, page_idx):
        if not self.is_loaded or page_idx < 0 or page_idx >= self.list_widget.count():
            return
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentRow(page_idx)
        item = self.list_widget.item(page_idx)
        if item and self.isVisible():
            self.list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.list_widget.blockSignals(False)

        # Prioritize rendering this page's thumbnail if not yet rendered
        if page_idx not in self._rendered_pages:
            self.update_thumbnail(page_idx)



# --- 11. SÜRÜKLE-BIRAK DESTEKLİ TAB BİLEŞENİ ---
class ModernTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.tabBar().setAcceptDrops(True)
        self.tabBar().installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.tabBar():
            if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
                    if pdf_urls:
                        win = self.window()
                        if hasattr(win, 'handle_dropped_urls'):
                            win.handle_dropped_urls(pdf_urls)
                            event.acceptProposedAction()
                            return True
        return super().eventFilter(source, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            pdf_urls = [u for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
            if pdf_urls:
                win = self.window()
                if hasattr(win, 'handle_dropped_urls'):
                    win.handle_dropped_urls(pdf_urls)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            w = self.width()
            h = self.height()
            cx = w / 2.0
            cy = h / 2.0

            # Uygulama Logosu
            logo_size = 112
            logo_pix = ModernIconFactory.pixmap_app(logo_size)
            if not logo_pix.isNull():
                p.drawPixmap(int(cx - logo_size / 2.0), int(cy - logo_size / 2.0 - 45), logo_pix)

            # Başlık
            p.setPen(QColor("#f0f0f0"))
            p.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
            title_rect = QRectF(0, cy + 25, w, 28)
            p.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "AuraPDF")

            # Açıklama / İpucu
            p.setPen(QColor("#858585"))
            p.setFont(QFont("Segoe UI", 11))
            hint_rect = QRectF(0, cy + 55, w, 28)
            text = LanguageManager.tr("empty_tab_hint")
            p.drawText(hint_rect, Qt.AlignmentFlag.AlignCenter, text)
            p.end()


# --- 12. MODERN METİN ARAMA ÇUBUĞU (SEARCH BAR) ---
class ModernSearchBar(QFrame):
    def __init__(self, parent_viewer):
        super().__init__(parent_viewer)
        self.viewer = parent_viewer
        self.setObjectName("ModernSearchBar")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.setStyleSheet("""
            QFrame#ModernSearchBar {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 170px;
                selection-background-color: #1a73e8;
            }
            QLineEdit:focus {
                border: 1px solid #388bfd;
            }
            QLabel {
                color: #aaaaaa;
                font-size: 12px;
                font-weight: 500;
                padding: 0 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #cccccc;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px;
                min-width: 24px;
                min-height: 24px;
                font-size: 12px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #383838;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QToolButton:pressed {
                background-color: #1a73e8;
                color: #ffffff;
            }
            QToolButton:checked {
                background-color: #1a73e8;
                color: #ffffff;
                border: 1px solid #388bfd;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(5)

        # Search icon
        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_search().pixmap(14, 14))
        lbl_icon.setStyleSheet("border: none; background: transparent; padding-left: 2px;")
        layout.addWidget(lbl_icon)

        # Search line edit
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(LanguageManager.tr("search_placeholder"))
        self.txt_search.textChanged.connect(self._on_text_changed)
        self.txt_search.installEventFilter(self)
        layout.addWidget(self.txt_search)

        # Count label
        self.lbl_count = QLabel("0 / 0")
        layout.addWidget(self.lbl_count)

        # Prev button
        self.btn_prev = QToolButton()
        self.btn_prev.setText("▲")
        self.btn_prev.setToolTip(LanguageManager.tr("search_prev_tip"))
        self.btn_prev.clicked.connect(self.find_prev)
        layout.addWidget(self.btn_prev)

        # Next button
        self.btn_next = QToolButton()
        self.btn_next.setText("▼")
        self.btn_next.setToolTip(LanguageManager.tr("search_next_tip"))
        self.btn_next.clicked.connect(self.find_next)
        layout.addWidget(self.btn_next)

        # Case sensitivity toggle button
        self.btn_case = QToolButton()
        self.btn_case.setText("Aa")
        self.btn_case.setCheckable(True)
        self.btn_case.setToolTip(LanguageManager.tr("search_case_tip"))
        self.btn_case.toggled.connect(lambda: self.do_search(reset_index=True))
        layout.addWidget(self.btn_case)

        # Close button
        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setToolTip(LanguageManager.tr("search_close_tip"))
        self.btn_close.clicked.connect(self.hide_search)
        layout.addWidget(self.btn_close)

        # Debounce timer for smooth typing
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(lambda: self.do_search(reset_index=True))

        self.hide()

    def apply_theme(self, theme_name: str = "dark", spec: Optional[dict] = None):
        if not spec:
            return
        bg = spec.get("tb_bg", "#252526")
        border = spec.get("tb_border", "#3c3c3c")
        page_bg = spec.get("page_bg", "#1e1e1e")
        text = spec.get("main_text", "#f0f0f0")
        accent = spec.get("accent", "#388bfd")
        btn_hover = spec.get("btn_hover", "#383838")
        tab_text = spec.get("tab_text", "#aaaaaa")

        self.setStyleSheet(f"""
            QFrame#ModernSearchBar {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLineEdit {{
                background-color: {page_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 170px;
                selection-background-color: {accent};
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QLabel {{
                color: {tab_text};
                font-size: 12px;
                font-weight: 500;
                padding: 0 4px;
            }}
            QToolButton {{
                background-color: transparent;
                color: {tab_text};
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px;
                min-width: 24px;
                min-height: 24px;
                font-size: 12px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: {btn_hover};
                color: #ffffff;
                border: 1px solid {border};
            }}
            QToolButton:pressed {{
                background-color: {accent};
                color: #ffffff;
            }}
            QToolButton:checked {{
                background-color: {accent};
                color: #ffffff;
                border: 1px solid {accent};
            }}
        """)

    def show_search(self):
        self.reposition()
        self.show()
        self.raise_()
        self.txt_search.setFocus()
        self.txt_search.selectAll()
        if self.txt_search.text().strip():
            self.do_search(reset_index=False)

    def hide_search(self):
        self.hide()
        tab_doc = self.viewer.get_current_tab_doc()
        if tab_doc:
            tab_doc.clear_search_highlights()
            tab_doc.view.setFocus()

    def reposition(self):
        tb_height = self.viewer.toolbar.height() if hasattr(self.viewer, 'toolbar') and self.viewer.toolbar.isVisible() else 0
        w = max(360, self.sizeHint().width())
        h = max(38, self.sizeHint().height())
        x = max(10, self.viewer.width() - w - 24)
        y = tb_height + 8
        self.setGeometry(x, y, w, h)

    def _on_text_changed(self, text):
        self.search_timer.start()

    def do_search(self, reset_index=True):
        tab_doc = self.viewer.get_current_tab_doc()
        query = self.txt_search.text().strip()
        if not tab_doc or not tab_doc.doc or not query:
            if tab_doc:
                tab_doc.clear_search_highlights()
            self.lbl_count.setText("0 / 0")
            self.lbl_count.setStyleSheet("color: #aaaaaa;")
            return

        case_sens = self.btn_case.isChecked()
        count = tab_doc.perform_search(query, case_sensitive=case_sens)
        if count == 0:
            self.lbl_count.setText(LanguageManager.tr("search_no_results"))
            self.lbl_count.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        else:
            curr = tab_doc.search_current_idx + 1
            self.lbl_count.setText(f"{curr} / {count}")
            self.lbl_count.setStyleSheet("color: #4caf50; font-weight: bold;")

    def find_next(self):
        tab_doc = self.viewer.get_current_tab_doc()
        if not tab_doc or not tab_doc.search_results:
            self.do_search()
            return
        idx = tab_doc.next_search_match()
        if idx >= 0:
            count = len(tab_doc.search_results)
            self.lbl_count.setText(f"{idx + 1} / {count}")
            self.lbl_count.setStyleSheet("color: #4caf50; font-weight: bold;")

    def find_prev(self):
        tab_doc = self.viewer.get_current_tab_doc()
        if not tab_doc or not tab_doc.search_results:
            self.do_search()
            return
        idx = tab_doc.prev_search_match()
        if idx >= 0:
            count = len(tab_doc.search_results)
            self.lbl_count.setText(f"{idx + 1} / {count}")
            self.lbl_count.setStyleSheet("color: #4caf50; font-weight: bold;")

    def eventFilter(self, source, event):
        if source == self.txt_search and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.find_prev()
                else:
                    self.find_next()
                return True
            elif event.key() == Qt.Key.Key_Escape:
                self.hide_search()
                return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_search()
            event.accept()
            return
        super().keyPressEvent(event)



