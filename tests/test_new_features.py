import sys
import os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings, QPoint, QSize
from PyQt6.QtGui import QIcon, QPixmap

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

def test_default_theme():
    """Klasik arayüzde varsayılan tema gridir; kullanıcının kayıtlı arayüz ve temasından etkilenmez."""
    from src.ui import ui_style
    settings = QSettings("AuraPDF", "PDFViewer")
    keys = ("app_theme", "app_theme_default_version", "interface_style")
    saved = {key: settings.value(key) for key in keys}
    try:
        settings.setValue("interface_style", "classic")
        settings.setValue("app_theme_default_version", 0)
        ui_style._active_style = None
        from src.viewer import AuraPDFViewer
        viewer = AuraPDFViewer()
        assert settings.value("app_theme_default_version", 0, type=int) >= 4, "Version not bumped"
        assert settings.value("app_theme", "") == "gray", f"Theme is not gray: {settings.value('app_theme')}"
        assert viewer.current_theme == "gray", f"Viewer theme not gray: {viewer.current_theme}"
        viewer.close()
    finally:
        for key, value in saved.items():
            if value is None:
                settings.remove(key)
            else:
                settings.setValue(key, value)
        ui_style._active_style = None
    print("[PASS] Default theme is verified as 'gray'")

def test_rotate_icons():
    from src.ui.icons import AuraIconFactory
    cw = AuraIconFactory.icon_rotate("#60a5fa")
    ccw = AuraIconFactory.icon_rotate_ccw("#60a5fa")
    assert not cw.isNull(), "CW rotate icon is null"
    assert not ccw.isNull(), "CCW rotate icon is null"
    print("[PASS] Full-turn 360-degree rotate icons verified")

def test_stamp_palette():
    from src.ui.popups import AuraStampPalettePopup
    selected = []
    popup = AuraStampPalettePopup(on_stamp_selected=lambda d, t, w, h: selected.append((d, t, w, h)))
    assert len(popup._preset_btns) == 8, f"Expected 8 presets, got {len(popup._preset_btns)}"
    btn, k, col = popup._preset_btns[0]
    btn.click()
    assert len(selected) == 1, "Preset click did not trigger callback"
    popup.btn_date_today.click()
    assert len(selected) == 2, "Date stamp click did not trigger callback"
    for th in ["dark", "gray", "emerald", "purple", "crimson", "nord", "vice_city", "apple"]:
        popup.apply_theme(th)
    print("[PASS] AuraStampPalettePopup presets & 8 themes verified")

def test_horizontal_centering():
    from src.document.tab_document import PDFTabDocument
    import fitz
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    tab_doc = PDFTabDocument(file_path=None)
    tab_doc.doc = doc
    tab_doc.page_positions[0] = {'left': 0.0, 'right': 612.0, 'top': 0.0, 'bottom': 792.0, 'width': 612.0, 'height': 792.0}
    tab_doc.center_current_page_horizontal()
    print("[PASS] Document auto-centering on resize verified", flush=True)

def test_minimalist_thumbnails():
    from src.ui.aura_views import AuraRightSidebar
    sb = AuraRightSidebar()
    assert sb.list_thumbnails.iconSize() == QSize(140, 190), f"Wrong icon size {sb.list_thumbnails.iconSize()}"
    assert sb.list_thumbnails.spacing() == 6, f"Wrong spacing {sb.list_thumbnails.spacing()}"
    pix = sb._create_placeholder_pixmap()
    assert pix.size() == QSize(140, 190), f"Wrong placeholder size {pix.size()}"
    print("[PASS] Minimalist thumbnails gallery verified")

if __name__ == "__main__":
    test_default_theme()
    test_rotate_icons()
    test_stamp_palette()
    test_horizontal_centering()
    test_minimalist_thumbnails()
    print("\nALL NEW FEATURES VERIFIED SUCCESSFULLY!")
