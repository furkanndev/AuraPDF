import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PyQt6.QtWidgets import QApplication, QLabel, QDialog, QScrollArea, QWidget
from PyQt6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from src.ui.dialogs.toolbox_dialogs import (
    PDFPageNumberDialog, PDFWatermarkDialog, PDFBackgroundDialog,
    PDFPasswordRecoveryDialog, PDFMergeDialog, PDFSplitDialog,
    PDFToWordDialog, PDFToExcelDialog, PDFToPowerPointDialog,
    PDFToEbookDialog, PDFOrganizePagesDialog, PDFReorderPagesDialog,
    PDFEncryptDialog, PDFPasswordDialog
)
from src.ui.dialogs.pdf_compress_dialog import PDFCompressDialog
from src.ui.dialogs.pdf_ocr_dialog import PDFScanOCRDialog
from src.ui.dialogs.pdf_redaction_dialog import PDFRedactionDialog
from src.ui.dialogs.pdf_compare_dialog import PDFCompareDialog
from src.ui.dialogs.pdf_content_editor_dialog import PDFContentEditorDialog
from src.ui.dialogs.settings_dialog import AuraSettingsDialog
from src.ui.dialogs.shortcuts_dialog import ShortcutsDialog
from src.ui.dialogs.document_properties_dialog import AuraDocumentPropertiesDialog
from src.ui.dialogs.page_organize_dialogs import PageLabelDialog, CropPageDialog
from src.ui.dialogs.media_dialogs import TableInsertDialog, ImageInsertDialog, VideoInsertDialog, AudioRecordDialog

dialog_classes = [
    PDFCompressDialog, PDFScanOCRDialog, PDFRedactionDialog, PDFCompareDialog,
    PDFContentEditorDialog, AuraSettingsDialog, ShortcutsDialog,
    AuraDocumentPropertiesDialog, PageLabelDialog, CropPageDialog,
    PDFPageNumberDialog, PDFWatermarkDialog, PDFBackgroundDialog,
    PDFPasswordRecoveryDialog, PDFMergeDialog, PDFSplitDialog,
    PDFToWordDialog, PDFToExcelDialog, PDFToPowerPointDialog,
    PDFToEbookDialog, PDFOrganizePagesDialog, PDFReorderPagesDialog,
    PDFEncryptDialog, PDFPasswordDialog, TableInsertDialog,
    ImageInsertDialog, VideoInsertDialog, AudioRecordDialog
]

print("=== CHECKING DIALOG SIZES, OVERFLOWS & LABEL SIZES ===")

class MockTab:
    def __init__(self):
        import pymupdf
        self.doc = pymupdf.open()
        self.doc.new_page()
        self.file_path = "test.pdf"

class MockParent(QWidget):
    def __init__(self):
        super().__init__()
        self.mock_tab = MockTab()
    def get_current_tab_doc(self):
        return self.mock_tab

mock_parent = MockParent()

for cls in dialog_classes:
    try:
        try:
            dlg = cls(mock_parent)
        except Exception:
            try:
                dlg = cls()
            except Exception:
                dlg = cls(None)
        
        dlg.adjustSize()
        hint = dlg.sizeHint()
        min_size = dlg.minimumSize()
        cur_size = dlg.size()
        
        # Check all child QLabels
        overflowing_labels = []
        for lbl in dlg.findChildren(QLabel):
            txt = lbl.text()
            if not txt or len(txt) < 15:
                continue
            # If label has long text, is wordwrap enabled?
            if not lbl.wordWrap() and len(txt) > 35:
                overflowing_labels.append((lbl, txt[:40], lbl.width(), len(txt)))

        print(f"[{cls.__name__}] size: {cur_size.width()}x{cur_size.height()}, min: {min_size.width()}x{min_size.height()}, hint: {hint.width()}x{hint.height()}")
        if overflowing_labels:
            print(f"   -> Found {len(overflowing_labels)} unwrapped long labels:")
            for lbl, sample, w, length in overflowing_labels[:6]:
                ascii_sample = sample.encode('ascii', errors='replace').decode('ascii')
                print(f"      - '{ascii_sample}...' (length={length}, wordWrap=False)")
        
        dlg.deleteLater()
    except Exception as e:
        print(f"[{cls.__name__}] Error: {e}")
