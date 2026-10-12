"""
AuraPDF Belge Özellikleri ve Üstveri Diyaloğu (Document Properties)
===================================================================
Acrobat / Foxit standardında, PDF belgesinin üstverilerini (metadata),
sayfa boyutlarını, şifreleme/izin durumlarını görüntüleyen ve düzenleyen diyalog.
"""

import os
import datetime
from typing import Optional
import pymupdf as fitz
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTabWidget, QWidget, QFormLayout,
                             QLineEdit, QTextEdit, QMessageBox, QGroupBox,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import get_dialog_theme_stylesheet


class AuraDocumentPropertiesDialog(QDialog):
    def __init__(self, tab_doc, main_window=None, parent=None):
        if hasattr(tab_doc, 'doc'):
            self.tab_doc = tab_doc
            self.doc = tab_doc.doc
            self.file_path = getattr(tab_doc, 'file_path', None)
            self.main_window = main_window
            parent_widget = main_window
        else:
            self.doc = tab_doc
            self.tab_doc = None
            self.file_path = main_window if isinstance(main_window, str) else None
            self.main_window = parent
            parent_widget = parent
        super().__init__(parent_widget)

        self.setWindowTitle(LanguageManager.tr("doc_props_title"))
        self.resize(580, 520)
        self.setMinimumSize(500, 440)
        self.setSizeGripEnabled(True)
        self.setStyleSheet(get_dialog_theme_stylesheet(self, extra_css="""
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QTextEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 8px;
                color: #f1f5f9;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #38bdf8;
            }
            QLineEdit:read-only {
                background: rgba(0, 0, 0, 0.2);
                color: #94a3b8;
            }
            QLabel.KeyLabel {
                font-weight: 600;
                color: #94a3b8;
            }
            QLabel.ValueLabel {
                color: #e2e8f0;
            }
        """))

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, 1)

        # Tab 1: Belge Bilgileri & Metadata
        self.tab_meta = QWidget()
        self._build_meta_tab()
        self.tabs.addTab(self.tab_meta, LanguageManager.tr("doc_props_tab_info"))

        # Tab 2: Sayfa ve Biçim
        self.tab_format = QWidget()
        self._build_format_tab()
        self.tabs.addTab(self.tab_format, LanguageManager.tr("doc_props_tab_format"))

        # Tab 3: Güvenlik ve İzinler
        self.tab_security = QWidget()
        self._build_security_tab()
        self.tabs.addTab(self.tab_security, LanguageManager.tr("doc_props_tab_security"))

        # Alt Butonlar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("close"))
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(LanguageManager.tr("save"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self._save_metadata)
        bottom_bar.addWidget(self.btn_save)

        root_layout.addLayout(bottom_bar)

    def _build_meta_tab(self):
        layout = QVBoxLayout(self.tab_meta)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Dosya Konumu ve Boyutu
        grp_file = QGroupBox(LanguageManager.tr("doc_props_grp_file"))
        form_file = QFormLayout(grp_file)
        form_file.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_filename = QLabel("-")
        self.lbl_filepath = QLabel("-")
        self.lbl_filepath.setWordWrap(True)
        self.lbl_filesize = QLabel("-")

        form_file.addRow(LanguageManager.tr("doc_props_lbl_filename") + ":", self.lbl_filename)
        form_file.addRow(LanguageManager.tr("doc_props_lbl_filepath") + ":", self.lbl_filepath)
        form_file.addRow(LanguageManager.tr("doc_props_lbl_filesize") + ":", self.lbl_filesize)
        layout.addWidget(grp_file)

        # Düzenlenebilir Üstveri Alanları
        grp_meta = QGroupBox(LanguageManager.tr("doc_props_grp_meta"))
        form_meta = QFormLayout(grp_meta)
        form_meta.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_title = QLineEdit()
        self.txt_author = QLineEdit()
        self.txt_subject = QLineEdit()
        self.txt_keywords = QLineEdit()

        form_meta.addRow(LanguageManager.tr("doc_props_lbl_title") + ":", self.txt_title)
        form_meta.addRow(LanguageManager.tr("doc_props_lbl_author") + ":", self.txt_author)
        form_meta.addRow(LanguageManager.tr("doc_props_lbl_subject") + ":", self.txt_subject)
        form_meta.addRow(LanguageManager.tr("doc_props_lbl_keywords") + ":", self.txt_keywords)
        layout.addWidget(grp_meta)

        # Oluşturan & Tarih Bilgileri
        grp_creator = QGroupBox(LanguageManager.tr("doc_props_grp_creator"))
        form_creator = QFormLayout(grp_creator)
        form_creator.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_creator = QLabel("-")
        self.lbl_producer = QLabel("-")
        self.lbl_created = QLabel("-")
        self.lbl_modified = QLabel("-")

        form_creator.addRow(LanguageManager.tr("doc_props_lbl_creator") + ":", self.lbl_creator)
        form_creator.addRow(LanguageManager.tr("doc_props_lbl_producer") + ":", self.lbl_producer)
        form_creator.addRow(LanguageManager.tr("doc_props_lbl_created") + ":", self.lbl_created)
        form_creator.addRow(LanguageManager.tr("doc_props_lbl_modified") + ":", self.lbl_modified)
        layout.addWidget(grp_creator)

    def _build_format_tab(self):
        layout = QVBoxLayout(self.tab_format)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        grp_spec = QGroupBox(LanguageManager.tr("doc_props_grp_spec"))
        form_spec = QFormLayout(grp_spec)
        form_spec.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_page_count = QLabel("-")
        self.lbl_pdf_version = QLabel("-")
        self.lbl_page_size = QLabel("-")
        self.lbl_page_dims = QLabel("-")

        form_spec.addRow(LanguageManager.tr("doc_props_lbl_page_count") + ":", self.lbl_page_count)
        form_spec.addRow(LanguageManager.tr("doc_props_lbl_version") + ":", self.lbl_pdf_version)
        form_spec.addRow(LanguageManager.tr("doc_props_lbl_page_size") + ":", self.lbl_page_size)
        form_spec.addRow(LanguageManager.tr("doc_props_lbl_page_dims") + ":", self.lbl_page_dims)
        layout.addWidget(grp_spec)
        layout.addStretch()

    def _build_security_tab(self):
        layout = QVBoxLayout(self.tab_security)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        grp_sec = QGroupBox(LanguageManager.tr("doc_props_grp_sec_status"))
        form_sec = QFormLayout(grp_sec)
        form_sec.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_encrypted = QLabel("-")
        self.lbl_perm_print = QLabel("-")
        self.lbl_perm_copy = QLabel("-")
        self.lbl_perm_edit = QLabel("-")
        self.lbl_perm_annotate = QLabel("-")

        form_sec.addRow(LanguageManager.tr("doc_props_lbl_encrypted") + ":", self.lbl_encrypted)
        form_sec.addRow(LanguageManager.tr("doc_props_lbl_perm_print") + ":", self.lbl_perm_print)
        form_sec.addRow(LanguageManager.tr("doc_props_lbl_perm_copy") + ":", self.lbl_perm_copy)
        form_sec.addRow(LanguageManager.tr("doc_props_lbl_perm_edit") + ":", self.lbl_perm_edit)
        form_sec.addRow(LanguageManager.tr("doc_props_lbl_perm_annotate") + ":", self.lbl_perm_annotate)
        layout.addWidget(grp_sec)
        layout.addStretch()

    def _load_data(self):
        if not self.doc:
            return

        file_path = getattr(self, 'file_path', None) or getattr(self.tab_doc, 'file_path', None)
        if file_path and os.path.isfile(file_path):
            self.lbl_filename.setText(os.path.basename(file_path))
            self.lbl_filepath.setText(file_path)
            size_bytes = os.path.getsize(file_path)
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bayt)"
            else:
                size_str = f"{size_bytes / 1024:.1f} KB ({size_bytes:,} bayt)"
            self.lbl_filesize.setText(size_str)
        else:
            self.lbl_filename.setText(LanguageManager.tr("untitled_doc"))
            self.lbl_filepath.setText(LanguageManager.tr("not_saved_yet"))
            self.lbl_filesize.setText("-")

        # Metadata
        meta = self.doc.metadata or {}
        self.txt_title.setText(meta.get("title") or "")
        self.txt_author.setText(meta.get("author") or "")
        self.txt_subject.setText(meta.get("subject") or "")
        self.txt_keywords.setText(meta.get("keywords") or "")

        self.lbl_creator.setText(meta.get("creator") or "-")
        self.lbl_producer.setText(meta.get("producer") or "-")
        self.lbl_created.setText(self._format_date(meta.get("creationDate")))
        self.lbl_modified.setText(self._format_date(meta.get("modDate")))

        # Format & Sayfa
        total_p = len(self.doc)
        self.lbl_page_count.setText(str(total_p))
        
        pdf_fmt = meta.get("format") or "PDF 1.7"
        self.lbl_pdf_version.setText(pdf_fmt)

        if total_p > 0:
            cur_idx = getattr(self.tab_doc, 'current_page_idx', 0)
            cur_idx = max(0, min(cur_idx, total_p - 1))
            page = self.doc[cur_idx]
            pw_pt = page.rect.width
            ph_pt = page.rect.height
            pw_mm = pw_pt * 25.4 / 72.0
            ph_mm = ph_pt * 25.4 / 72.0
            pw_in = pw_pt / 72.0
            ph_in = ph_pt / 72.0

            paper_name = self._detect_paper_name(pw_mm, ph_mm)
            self.lbl_page_size.setText(f"{paper_name} ({pw_mm:.1f} x {ph_mm:.1f} mm)")
            self.lbl_page_dims.setText(f"{pw_pt:.0f} x {ph_pt:.0f} pt / {pw_in:.2f} x {ph_in:.2f} inç")

        # Güvenlik
        is_enc = self.doc.is_encrypted
        self.lbl_encrypted.setText(LanguageManager.tr("yes") if is_enc else LanguageManager.tr("no"))
        
        perm = getattr(self.doc, 'permissions', 0)
        # Standart izinler: bit 3 = print, bit 4 = modify, bit 5 = copy, bit 6 = annot
        def perm_str(allowed: bool) -> str:
            return LanguageManager.tr("perm_allowed") if allowed else LanguageManager.tr("perm_denied")

        self.lbl_perm_print.setText(perm_str(not is_enc or bool(perm & 4)))
        self.lbl_perm_edit.setText(perm_str(not is_enc or bool(perm & 8)))
        self.lbl_perm_copy.setText(perm_str(not is_enc or bool(perm & 16)))
        self.lbl_perm_annotate.setText(perm_str(not is_enc or bool(perm & 32)))

    def _format_date(self, raw_date: Optional[str]) -> str:
        if not raw_date:
            return "-"
        # PDF date format: D:YYYYMMDDHHmmSS...
        try:
            d_str = raw_date.replace("D:", "").replace("'", "")[:14]
            dt = datetime.datetime.strptime(d_str, "%Y%m%d%H%M%S")
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return raw_date

    def _detect_paper_name(self, w_mm: float, h_mm: float) -> str:
        w, h = min(w_mm, h_mm), max(w_mm, h_mm)
        if abs(w - 210) < 3 and abs(h - 297) < 3:
            return "A4"
        elif abs(w - 297) < 3 and abs(h - 420) < 3:
            return "A3"
        elif abs(w - 148) < 3 and abs(h - 210) < 3:
            return "A5"
        elif abs(w - 215.9) < 3 and abs(h - 279.4) < 3:
            return "Letter"
        elif abs(w - 215.9) < 3 and abs(h - 355.6) < 3:
            return "Legal"
        return LanguageManager.tr("custom_size")

    def _save_metadata(self):
        if not self.doc:
            self.reject()
            return
        try:
            new_meta = self.doc.metadata or {}
            new_meta["title"] = self.txt_title.text().strip()
            new_meta["author"] = self.txt_author.text().strip()
            new_meta["subject"] = self.txt_subject.text().strip()
            new_meta["keywords"] = self.txt_keywords.text().strip()
            self.doc.set_metadata(new_meta)
            if hasattr(self.tab_doc, 'set_modified'):
                self.tab_doc.set_modified(True)
            QMessageBox.information(self, LanguageManager.tr("success"), LanguageManager.tr("doc_props_saved_msg"))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, LanguageManager.tr("error"), f"{LanguageManager.tr('error')}: {e}")

ModernDocumentPropertiesDialog = AuraDocumentPropertiesDialog
DocumentPropertiesDialog = AuraDocumentPropertiesDialog
