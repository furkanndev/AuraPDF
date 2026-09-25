from typing import List, Dict, Optional, Any
import os
import pymupdf as fitz
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QRadioButton, QLineEdit, QComboBox, 
                             QGroupBox, QMessageBox, QFileDialog)
from PyQt6.QtGui import QPainter, QImage, QColor
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet

# --- 8. MODERN YAZDIRMA & PRINT TO PDF DİYALOĞU ---
class ModernPrintDialog(QDialog):
    def __init__(self, tab_doc, main_window):
        super().__init__(main_window)
        self.tab_doc = tab_doc
        self.main_window = main_window
        self.total_pages = len(tab_doc.doc)

        self.setWindowTitle(LanguageManager.tr("print_dialog_title"))
        self.resize(500, 440)
        self.setMinimumSize(420, 360)
        self.setSizeGripEnabled(True)
        self.setStyleSheet(get_dialog_theme_stylesheet(self, extra_css="""
            QGroupBox { 
                border: 1px solid; 
                border-radius: 8px; 
                margin-top: 10px; 
                padding-top: 12px; 
                font-weight: bold; 
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """))

        layout = QVBoxLayout(self)
        
        # Hedef Seçimi
        grp_dest = QGroupBox(LanguageManager.tr("print_grp_dest"))
        v_dest = QVBoxLayout(grp_dest)
        self.rb_pdf = QRadioButton(LanguageManager.tr("print_dest_pdf"))
        self.rb_pdf.setChecked(True)
        self.rb_printer = QRadioButton(LanguageManager.tr("print_dest_printer"))
        v_dest.addWidget(self.rb_pdf)
        v_dest.addWidget(self.rb_printer)
        layout.addWidget(grp_dest)

        # Sayfa Aralığı
        grp_pages = QGroupBox(LanguageManager.tr("print_grp_pages"))
        v_pages = QVBoxLayout(grp_pages)
        self.rb_all = QRadioButton(LanguageManager.tr("print_all_pages", total=self.total_pages))
        self.rb_all.setChecked(True)
        h_range = QHBoxLayout()
        self.rb_custom = QRadioButton(LanguageManager.tr("print_range"))
        self.txt_range = QLineEdit()
        self.txt_range.setEnabled(False)
        self.rb_custom.toggled.connect(self.txt_range.setEnabled)
        h_range.addWidget(self.rb_custom)
        h_range.addWidget(self.txt_range)
        v_pages.addWidget(self.rb_all)
        v_pages.addLayout(h_range)
        layout.addWidget(grp_pages)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(LanguageManager.tr("print_btn_cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_run = QPushButton(LanguageManager.tr("print_btn_run"))
        btn_run.setObjectName("PrimaryBtn")
        btn_run.clicked.connect(self.execute_print)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_run)
        layout.addLayout(btn_layout)

    def _get_target_page_indices(self) -> List[int]:
        if self.rb_all.isChecked():
            return list(range(self.total_pages))
        
        # Basit sayfa parse işlemi
        raw = self.txt_range.text().strip()
        indices = set()
        for part in raw.split(','):
            part = part.strip()
            if not part: continue
            if '-' in part:
                try:
                    s, e = map(int, part.split('-'))
                    for p in range(s, e + 1):
                        if 1 <= p <= self.total_pages: indices.add(p - 1)
                except ValueError: pass
            else:
                try:
                    p = int(part)
                    if 1 <= p <= self.total_pages: indices.add(p - 1)
                except ValueError: pass
        return sorted(list(indices))

    def execute_print(self):
        page_indices = self._get_target_page_indices()
        if not page_indices:
            QMessageBox.warning(self, LanguageManager.tr("warning"), LanguageManager.tr("print_no_valid_pages"))
            return

        if self.rb_pdf.isChecked():
            orig_name = os.path.splitext(os.path.basename(self.tab_doc.file_path))[0] if getattr(self.tab_doc, 'file_path', None) else "belge"
            save_path, _ = QFileDialog.getSaveFileName(self, LanguageManager.tr("print_dialog_title"), f"yazdir_{orig_name}.pdf", "PDF (*.pdf)")
            if not save_path: return

            out_doc = fitz.open()
            for p_idx in page_indices:
                out_doc.insert_pdf(self.tab_doc.doc, from_page=p_idx, to_page=p_idx)

            self.tab_doc.export_drawings_to_pdf(out_doc, page_indices)
            out_doc.save(save_path, garbage=4, deflate=True, clean=True)
            out_doc.close()
            
            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("save_success"))
            self.accept()

        else:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self.main_window)
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                temp_pdf = fitz.open()
                for p_idx in page_indices:
                    temp_pdf.insert_pdf(self.tab_doc.doc, from_page=p_idx, to_page=p_idx)
                self.tab_doc.export_drawings_to_pdf(temp_pdf, page_indices)

                painter = QPainter(printer)
                page_rect = printer.pageLayout().paintRectPixels(printer.resolution())

                for idx in range(len(temp_pdf)):
                    if idx > 0: printer.newPage()
                    page = temp_pdf[idx]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    scaled_size = qimg.size().scaled(int(page_rect.width()), int(page_rect.height()), Qt.AspectRatioMode.KeepAspectRatio)
                    target_x = int(page_rect.left() + (page_rect.width() - scaled_size.width()) / 2)
                    target_y = int(page_rect.top() + (page_rect.height() - scaled_size.height()) / 2)
                    painter.drawImage(QRectF(target_x, target_y, scaled_size.width(), scaled_size.height()), qimg)

                painter.end()
                temp_pdf.close()
                self.accept()


