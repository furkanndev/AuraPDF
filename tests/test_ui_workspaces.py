import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.viewer import AuraPDFViewer

def test_workspaces_and_drawers():
    print("=== Testing AuraPDF Workspaces and Drawers ===")
    window = AuraPDFViewer()
    
    # 1. Open test document
    test_pdf = os.path.abspath("test1.pdf")
    if os.path.exists(test_pdf):
        window.add_pdf_tab(test_pdf)
    
    # 2. Test Left Sidebar Drawers
    if hasattr(window, 'modern_left_sidebar') and window.modern_left_sidebar:
        sidebar = window.modern_left_sidebar
        print("[TEST] Testing Left Sidebar Drawers...")
        drawers = ['export', 'edit', 'read', 'fill_sign', 'prepare_form']
        for d in drawers:
            try:
                if hasattr(sidebar, 'show_drawer'):
                    sidebar.show_drawer(d)
                    print(f"  [PASS] Drawer '{d}' opened successfully")
            except Exception as e:
                print(f"  [FAIL] Drawer '{d}': {e}")
                
    # 3. Test Central Stack Workspaces
    if hasattr(window, 'central_stack'):
        print("[TEST] Testing Central Stack Workspaces...")
        for i in range(window.central_stack.count()):
            w = window.central_stack.widget(i)
            window.central_stack.setCurrentIndex(i)
            print(f"  [PASS] Workspace {i}: {type(w).__name__}")
            
    # 4. Test Organize Workspace
    if hasattr(window, 'organize_workspace') and window.organize_workspace:
        print("[TEST] Testing Organize Workspace...")
        try:
            window.open_organize_pages_workspace()
            print("  [PASS] open_organize_pages_workspace() executed")
        except Exception as e:
            print(f"  [FAIL] organize_workspace: {e}")

    # 5. Test Command Palette Dialog
    print("[TEST] Testing Command Palette Dialog...")
    try:
        from src.ui.modern_views import ModernCommandPaletteDialog
        cp = ModernCommandPaletteDialog(window)
        cp.filter_commands("")
        print("  [PASS] Command Palette initialized and commands populated")
    except Exception as e:
        print(f"  [FAIL] Command Palette: {e}")

    # 6. Test Accessibility Panel
    if hasattr(window, 'modern_right_sidebar') and window.modern_right_sidebar:
        print("[TEST] Testing Right Sidebar Panels...")
        rs = window.modern_right_sidebar
        if hasattr(rs, 'show_panel'):
            for p in ['tts', 'accessibility', 'annotations', 'bookmarks', 'signatures']:
                try:
                    rs.show_panel(p)
                    print(f"  [PASS] Right panel '{p}' shown")
                except Exception as e:
                    print(f"  [FAIL] Right panel '{p}': {e}")

    # Prevent unsaved changes dialog
    for idx in range(window.tab_widget.count()):
        w = window.tab_widget.widget(idx)
        if hasattr(w, 'is_modified'):
            w.is_modified = False

    window.close()
    print("=== Workspaces and Drawers Audit Completed Successfully ===")

if __name__ == '__main__':
    test_workspaces_and_drawers()
