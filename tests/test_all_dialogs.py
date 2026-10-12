import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget
import pymupdf as fitz

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

THEMES = ['dark', 'gray', 'emerald', 'purple', 'crimson', 'nord', 'vice_city', 'apple']

class MockParent(QWidget):
    def __init__(self, doc_path="test1.pdf"):
        super().__init__()
        self.current_theme = "dark"
        self.app_font_size = 10
        self.doc = fitz.open(doc_path) if os.path.exists(doc_path) else fitz.open()
        if len(self.doc) == 0:
            self.doc.new_page()
        self.file_path = doc_path
        self.current_page_idx = 0

    def get_current_tab_doc(self):
        class TabDoc:
            pass
        td = TabDoc()
        td.doc = self.doc
        td.file_path = self.file_path
        td.current_page_idx = self.current_page_idx
        return td

def test_dialogs():
    parent = MockParent()
    tab_doc = parent.get_current_tab_doc()
    
    dialog_specs = [
        # (module_name, class_name, constructor_args)
        ("src.ui.dialogs.shortcuts_dialog", "KeyboardShortcutsDialog", lambda: (parent,)),
        ("src.ui.dialogs.shortcuts_dialog", "ShortcutsDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_compress_dialog", "PDFCompressDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_ocr_dialog", "PDFScanOCRDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_ocr_dialog", "PDFOCRDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_redaction_dialog", "PDFRedactionDialog", lambda: (parent,)),
        ("src.ui.dialogs.print_dialog", "AuraPrintDialog", lambda: (tab_doc, parent)),
        ("src.ui.dialogs.print_dialog", "ModernPrintDialog", lambda: (tab_doc, parent)),
        ("src.ui.dialogs.settings_dialog", "AuraSettingsDialog", lambda: (parent,)),
        ("src.ui.dialogs.settings_dialog", "SettingsDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_compare_dialog", "PDFCompareDialog", lambda: (parent,)),
        ("src.ui.dialogs.pdf_content_editor_dialog", "PDFContentEditorDialog", lambda: (parent,)),
        ("src.ui.dialogs.comment_dialog", "AuraCommentInputDialog", lambda: (parent,)),
        ("src.ui.dialogs.document_properties_dialog", "AuraDocumentPropertiesDialog", lambda: (tab_doc, parent)),
        ("src.ui.dialogs.new_page_dialog", "NewPageDialog", lambda: (parent,)),
        ("src.ui.dialogs.new_page_dialog", "ChangePageStyleDialog", lambda: (parent,)),
        ("src.ui.dialogs.page_organize_dialogs", "PageLabelDialog", lambda: (parent, 1)),
        ("src.ui.dialogs.page_organize_dialogs", "CropPageDialog", lambda: (parent, parent.doc[0])),
        ("src.ui.dialogs.pdf_signature_dialog", "PDFSignatureDialog", lambda: (parent,)),
        ("src.ui.dialogs.stamp_dialog", "ModernStampDialog", lambda: (parent,)),
        ("src.ui.dialogs.stamp_dialog", "DateStampDialog", lambda: (parent,)),
        ("src.ui.popups", "ModernStampPalettePopup", lambda: (parent,)),
        ("src.ui.dialogs.update_dialog", "UpdateDialog", lambda: (None, parent)),
        
        # media_dialogs
        ("src.ui.dialogs.media_dialogs", "TableInsertDialog", lambda: (parent,)),
        ("src.ui.dialogs.media_dialogs", "EmojiGifPickerDialog", lambda: (parent,)),
        ("src.ui.dialogs.media_dialogs", "ImageInsertDialog", lambda: (parent,)),
        ("src.ui.dialogs.media_dialogs", "AudioRecordDialog", lambda: (parent,)),
        ("src.ui.dialogs.media_dialogs", "VideoInsertDialog", lambda: (parent,)),

        # toolbox_dialogs
        ("src.ui.dialogs.toolbox_dialogs", "PDFMergeDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFSplitDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFToEbookDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFToWordDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFOrganizePagesDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFReorderPagesDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFPageNumberDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFToPowerPointDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFToExcelDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFEncryptDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFPasswordRecoveryDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFWatermarkDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFBackgroundDialog", lambda: (parent,)),
        ("src.ui.dialogs.toolbox_dialogs", "PDFPasswordDialog", lambda: (parent,)),
    ]

    from src.ui.dialog_theme import apply_dialog_theme

    total = len(dialog_specs)
    passed = 0
    failed = 0

    for mod_name, cls_name, get_args in dialog_specs:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            args = get_args()
            dlg = cls(*args)
            
            # Test all 8 themes
            for theme in THEMES:
                parent.current_theme = theme
                apply_dialog_theme(dlg, parent)
                
            passed += 1
            print(f"[PASS] {cls_name} (All 8 themes tested successfully)")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {cls_name}: {e}")

    print(f"\n==========================================")
    print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
    print(f"==========================================")
    return failed == 0

if __name__ == '__main__':
    success = test_dialogs()
    sys.exit(0 if success else 1)
