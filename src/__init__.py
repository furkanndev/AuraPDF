"""AuraPDF"""

import sys as _sys

# PyMuPDF, kuruluysa "pymupdf.layout" eklentisini içe aktarırken onnxruntime ve numpy'ı
# yükler; bu, açılışa yaklaşık 3-4 saniye ekler. AuraPDF bu eklentiyi kullanmaz
# (sayfa düzeni analizi yok), bu yüzden PyMuPDF'in isteğe bağlı içe aktarımı
# ImportError ile atlatılır. OCR (rapidocr) onnxruntime'ı kendi zamanında yükler.
_sys.modules.setdefault("pymupdf.layout", None)
