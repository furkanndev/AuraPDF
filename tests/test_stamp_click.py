import sys
import os
import tempfile
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint
import fitz

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

def test_open_stamp_dialog_flow():
    print("STEP 1: Starting AuraPDFViewer", flush=True)
    from src.viewer import AuraPDFViewer
    viewer = AuraPDFViewer()

    print("STEP 2: Creating temp PDF", flush=True)
    tmp_pdf = os.path.join(tempfile.gettempdir(), "test_stamp_dummy.pdf")
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(tmp_pdf)
    doc.close()

    try:
        print("STEP 3: Adding tab", flush=True)
        viewer.add_pdf_tab(tmp_pdf)
        tab_doc = viewer.get_current_tab_doc()
        assert tab_doc is not None, "Tab document was not created"
        assert tab_doc.doc is not None, "Tab document has no doc"

        print("STEP 4: Opening stamp dialog", flush=True)
        viewer.open_stamp_dialog()
        assert hasattr(viewer, 'stamp_popup'), "Viewer has no stamp_popup"
        assert viewer.stamp_popup is not None, "stamp_popup is None"

        print("STEP 5: Clicking preset stamp", flush=True)
        btn, key, col = viewer.stamp_popup._preset_btns[0]
        btn.click()

        print("STEP 6: Checking drawings", flush=True)
        assert len(tab_doc.drawings) > 0 or len(tab_doc.scene.items()) > 0, "No stamp item added"

        print("STEP 7: Opening date stamp", flush=True)
        viewer.open_stamp_dialog()
        viewer.stamp_popup.btn_date_today.click()

        print("[PASS] Full stamp dialog open and preset click flow verified successfully!", flush=True)
    finally:
        if os.path.exists(tmp_pdf):
            try:
                os.remove(tmp_pdf)
            except Exception:
                pass
    sys.exit(0)

if __name__ == "__main__":
    test_open_stamp_dialog_flow()
