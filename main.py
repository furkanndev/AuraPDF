"""
AuraPDF
=======
Ana Uygulama Giriş Noktası (Application Entrypoint)

Bu dosya, AuraPDF uygulamasının ana çalıştırma dosyasıdır.
"""

import sys
import os

# src paketinin ve çalışma dizininin Python path'inde bulunmasını sağla
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt

# Gerekli ana bileşenleri doğrudan aktar
from src.core.i18n import LanguageManager
from src.ui.icons import ModernIconFactory
from src.viewer import ModernPDFViewer

# Diğer sınıfları geriye dönük uyumluluk (backward compatibility) için ihtiyaç anında tembel yükle (Lazy load)
_LAZY_EXPORTS = {
    "CursorFactory": ("src.ui.cursors", "CursorFactory"),
    "DraggableToolButton": ("src.ui.widgets", "DraggableToolButton"),
    "ReorderableToolBar": ("src.ui.widgets", "ReorderableToolBar"),
    "EditableInlineTextItem": ("src.ui.widgets", "EditableInlineTextItem"),
    "ThumbnailsDock": ("src.ui.widgets", "ThumbnailsDock"),
    "ModernTabWidget": ("src.ui.widgets", "ModernTabWidget"),
    "SelectionSettingsPopup": ("src.ui.popups", "SelectionSettingsPopup"),
    "TextSettingsPopup": ("src.ui.popups", "TextSettingsPopup"),
    "TextPreviewWidget": ("src.ui.popups", "TextPreviewWidget"),
    "StrokePreviewWidget": ("src.ui.popups", "StrokePreviewWidget"),
    "ToolSettingsPopup": ("src.ui.popups", "ToolSettingsPopup"),
    "FloatingHUDPreview": ("src.ui.popups", "FloatingHUDPreview"),
    "PointerSettingsPopup": ("src.ui.popups", "PointerSettingsPopup"),
    "ModernPrintDialog": ("src.ui.dialogs.print_dialog", "ModernPrintDialog"),
    "get_ebook_convert_path": ("src.ui.dialogs.toolbox_dialogs", "get_ebook_convert_path"),
    "EbookConversionThread": ("src.ui.dialogs.toolbox_dialogs", "EbookConversionThread"),
    "PDFMergeListWidget": ("src.ui.dialogs.toolbox_dialogs", "PDFMergeListWidget"),
    "PDFMergeDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFMergeDialog"),
    "PDFSplitDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFSplitDialog"),
    "PDFToEbookDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFToEbookDialog"),
    "PDFToWordDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFToWordDialog"),
    "PDFToPowerPointDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFToPowerPointDialog"),
    "PDFToExcelDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFToExcelDialog"),
    "PDFEncryptDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFEncryptDialog"),
    "PDFPasswordRecoveryDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFPasswordRecoveryDialog"),
    "PDFWatermarkDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFWatermarkDialog"),
    "PDFBackgroundDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFBackgroundDialog"),
    "PDFPasswordDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFPasswordDialog"),
    "PDFOrganizePagesDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFOrganizePagesDialog"),
    "PDFReorderPagesDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFReorderPagesDialog"),
    "PDFPageNumberDialog": ("src.ui.dialogs.toolbox_dialogs", "PDFPageNumberDialog"),
    "PDFContentEditorDialog": ("src.ui.dialogs.pdf_content_editor_dialog", "PDFContentEditorDialog"),
    "PDFSignatureDialog": ("src.ui.dialogs.pdf_signature_dialog", "PDFSignatureDialog"),
    "PDFCompareDialog": ("src.ui.dialogs.pdf_compare_dialog", "PDFCompareDialog"),
    "PDFRedactionDialog": ("src.ui.dialogs.pdf_redaction_dialog", "PDFRedactionDialog"),
    "PDFScanOCRDialog": ("src.ui.dialogs.pdf_ocr_dialog", "PDFScanOCRDialog"),
    "PDFTabDocument": ("src.document.tab_document", "PDFTabDocument"),
    "ModernLaserPointerItem": ("src.document.tab_document", "ModernLaserPointerItem"),
    "PDFTableItem": ("src.document.media_items", "PDFTableItem"),
    "PDFResizableImageItem": ("src.document.media_items", "PDFResizableImageItem"),
    "PDFAudioItem": ("src.document.media_items", "PDFAudioItem"),
    "PDFVideoItem": ("src.document.media_items", "PDFVideoItem"),
    "TableInsertDialog": ("src.ui.dialogs.media_dialogs", "TableInsertDialog"),
    "EmojiGifPickerDialog": ("src.ui.dialogs.media_dialogs", "EmojiGifPickerDialog"),
    "ImageInsertDialog": ("src.ui.dialogs.media_dialogs", "ImageInsertDialog"),
    "AudioRecordDialog": ("src.ui.dialogs.media_dialogs", "AudioRecordDialog"),
    "VideoInsertDialog": ("src.ui.dialogs.media_dialogs", "VideoInsertDialog"),
    "ModernCategoryBar": ("src.ui.ribbon_bar", "ModernCategoryBar"),
    "CATEGORY_ITEMS": ("src.ui.ribbon_bar", "CATEGORY_ITEMS"),
    "PDFCompressDialog": ("src.ui.dialogs.pdf_compress_dialog", "PDFCompressDialog"),
    "KeyboardShortcutsDialog": ("src.ui.dialogs.shortcuts_dialog", "KeyboardShortcutsDialog"),
    "PDFCompressor": ("src.core.pdf_compressor", "PDFCompressor"),
}

__all__ = [
    "LanguageManager", "ModernIconFactory", "CursorFactory",
    "DraggableToolButton", "ReorderableToolBar", "EditableInlineTextItem",
    "ThumbnailsDock", "ModernTabWidget", "SelectionSettingsPopup",
    "TextSettingsPopup", "TextPreviewWidget", "StrokePreviewWidget",
    "ToolSettingsPopup", "FloatingHUDPreview", "PointerSettingsPopup",
    "ModernPrintDialog", "get_ebook_convert_path", "EbookConversionThread",
    "PDFMergeListWidget", "PDFMergeDialog", "PDFSplitDialog", "PDFToEbookDialog",
    "PDFToWordDialog", "PDFToPowerPointDialog", "PDFToExcelDialog",
    "PDFEncryptDialog", "PDFPasswordRecoveryDialog", "PDFWatermarkDialog",
    "PDFBackgroundDialog", "PDFPasswordDialog",
    "PDFOrganizePagesDialog", "PDFReorderPagesDialog", "PDFPageNumberDialog",
    "PDFContentEditorDialog", "PDFSignatureDialog", "PDFCompareDialog",
    "PDFRedactionDialog", "PDFScanOCRDialog",
    "PDFTabDocument", "ModernLaserPointerItem", "ModernPDFViewer",
    "PDFTableItem", "PDFResizableImageItem", "PDFAudioItem", "PDFVideoItem",
    "TableInsertDialog", "EmojiGifPickerDialog", "ImageInsertDialog",
    "AudioRecordDialog", "VideoInsertDialog",
    "ModernCategoryBar", "CATEGORY_ITEMS",
    "PDFCompressDialog", "KeyboardShortcutsDialog", "PDFCompressor"
]


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        mod_name, attr_name = _LAZY_EXPORTS[name]
        import importlib
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


try:
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    HAS_LOCAL_IPC = True
except ImportError:
    HAS_LOCAL_IPC = False

SERVER_NAME = "AuraPDF_SingleInstance_App_Server"


def get_pdf_paths_from_args(args) -> list:
    """Komut satırından veya dosya ilişkilendirmesinden gelen geçerli PDF dosya yollarını ayıklar."""
    pdf_files = []
    unmatched = []
    for arg in args:
        if not arg:
            continue
        cleaned = arg.strip().strip('"').strip("'").strip()
        if not cleaned:
            continue
        norm = os.path.normpath(cleaned)
        if os.path.isfile(norm):
            abs_p = os.path.abspath(norm)
            if abs_p not in pdf_files:
                pdf_files.append(abs_p)
        else:
            unmatched.append(cleaned)

    # Eğer boşluklu dosya yolu tırnaksız olarak birden fazla argümana bölünmüşse birleştirmeyi dene
    if unmatched and not pdf_files:
        joined = os.path.normpath(" ".join(unmatched))
        if os.path.isfile(joined):
            abs_p = os.path.abspath(joined)
            pdf_files.append(abs_p)

    return pdf_files


def activate_window(window):
    """Pencereyi simge durumundan çıkarır ve tam ekran (maximized) olarak en öne getirir."""
    try:
        window.setWindowState(
            window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive | Qt.WindowState.WindowMaximized
        )
        window.showMaximized()
        window.raise_()
        window.activateWindow()
        import ctypes
        hwnd = int(window.winId())
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def main():
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("aurapdf.app")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app_icon = ModernIconFactory.icon_app()
    app.setWindowIcon(app_icon)

    # 1. Argümanlardan açılacak dosyaları tespit et (çift tıklanan PDF kitapları)
    files_to_open = get_pdf_paths_from_args(sys.argv[1:])

    # 2. Single-Instance Kontrolü: Uygulama zaten açıksa, dosyayı açık olan pencereye gönderip çık
    if HAS_LOCAL_IPC:
        client_socket = QLocalSocket()
        client_socket.connectToServer(SERVER_NAME)
        if client_socket.waitForConnected(600):
            payload = "\n".join(files_to_open) if files_to_open else "__ACTIVATE__"
            client_socket.write(payload.encode("utf-8"))
            client_socket.flush()
            client_socket.waitForBytesWritten(1000)
            client_socket.disconnectFromServer()
            sys.exit(0)

    # 3. Ana Uygulama Penceresini Başlat
    editor = ModernPDFViewer()

    # Dosya ilişkilendirmesiyle çift tıklanan PDF'leri doğrudan yeni sekme olarak aç
    for file_path in files_to_open:
        editor.add_pdf_tab(file_path)

    # Pencereyi tam ekran (maximized) olarak aç
    editor.showMaximized()

    # 4. Yerel Sunucuyu Başlat (Sonradan çift tıklanacak PDF'leri yakalamak için)
    server = None
    if HAS_LOCAL_IPC:
        server = QLocalServer()
        # Olası eski oturumlardan kalan soketi temizle
        QLocalServer.removeServer(SERVER_NAME)
        if server.listen(SERVER_NAME):
            def handle_client_connection():
                client = server.nextPendingConnection()
                if not client:
                    return
                if client.waitForReadyRead(1000):
                    raw_data = client.readAll().data().decode("utf-8", errors="ignore")
                    lines = [line.strip() for line in raw_data.splitlines() if line.strip()]
                    for item in lines:
                        if item != "__ACTIVATE__":
                            paths = get_pdf_paths_from_args([item])
                            for p in paths:
                                editor.add_pdf_tab(p)
                    activate_window(editor)
                client.disconnectFromServer()

            server.newConnection.connect(handle_client_connection)
            editor._local_server = server

    sys.exit(app.exec())


if __name__ == "__main__":
    main()