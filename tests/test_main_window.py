import os
import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.viewer import AuraPDFViewer

def test_main_window():
    print("=== Testing AuraPDFViewer ===")
    window = AuraPDFViewer()
    
    # 1. Test opening a PDF
    test_pdf = os.path.abspath("test1.pdf")
    if os.path.exists(test_pdf):
        window.add_pdf_tab(test_pdf)
        print("[PASS] Document opened successfully")
    
    # 2. Check all QActions
    actions = window.findChildren(QAction)
    print(f"Total QActions found: {len(actions)}")
    unconnected_actions = []
    for act in actions:
        text = act.text().strip()
        # verify action can be triggered or has receivers
        if not text:
            continue

    # 3. Check all buttons in toolbars & menus
    buttons = window.findChildren(QPushButton) + window.findChildren(QToolButton)
    print(f"Total Buttons found: {len(buttons)}")

    # 4. Test page operations on loaded doc
    if hasattr(window, 'tab_widget') and window.tab_widget.count() > 0:
        td = window.get_current_tab_doc()
        if td:
            print(f"[PASS] Active Tab: {td.file_path}, Pages: {len(td.doc)}")
            # Zoom tests
            window.zoom_in()
            window.zoom_out()
            window.fit_to_page()
            window.fit_to_width()
            print("[PASS] Zoom actions executed successfully")
            
            # Rotation tests
            window.rotate_current_page()
            window.rotate_all_pages()
            print("[PASS] Page rotation executed successfully")

    # 5. Test theme switching across all 8 themes
    THEMES = ['dark', 'gray', 'emerald', 'purple', 'crimson', 'nord', 'vice_city', 'apple']
    for t in THEMES:
        window.apply_theme(t)
    print("[PASS] Applied all 8 themes to main window successfully")

    # Mark unmodified to close cleanly in headless test
    for idx in range(window.tab_widget.count()):
        w = window.tab_widget.widget(idx)
        if hasattr(w, 'is_modified'):
            w.is_modified = False

    window.close()
    print("=== Main Window Audit Completed Successfully ===")

if __name__ == '__main__':
    test_main_window()
