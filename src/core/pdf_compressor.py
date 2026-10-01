"""
AuraPDF - PDF Sıkıştırma ve Dosya Boyutu Küçültme Motoru
=======================================================
Görselleri akıllıca yeniden örnekleyerek (DPI downsampling), JPEG sıkıştırması
uygulayarak, kullanılmayan nesneleri temizleyerek (garbage collection) ve
akışları deflate ile sıkıştırarak PDF boyutunu küçülten çekirdek modül.
"""

import os
import io
from typing import Dict, Any, Optional, Callable
import pymupdf as fitz
from PIL import Image


class PDFCompressor:
    """PDF dosya boyutu optimizasyonu ve sıkıştırma sınıfı."""

    PRESETS = {
        "low": {
            "name": "Düşük Sıkıştırma (Yüksek Kalite)",
            "image_quality": 85,
            "max_dpi": 150,
            "desc": "Belge netliğini maksimum korur, hafif dosya küçültmesi sağlar."
        },
        "medium": {
            "name": "Orta Sıkıştırma (Dengeli / Önerilen)",
            "image_quality": 70,
            "max_dpi": 120,
            "desc": "Görsel netliğini korurken dosya boyutunu %40-%70 oranında küçültür."
        },
        "high": {
            "name": "Yüksek Sıkıştırma (Maksimum Küçültme)",
            "image_quality": 50,
            "max_dpi": 96,
            "desc": "E-posta ve internet yüklemeleri için maksimum dosya boyutu tasarrufu."
        }
    }

    @classmethod
    def compress_pdf(
        cls,
        input_path: str,
        output_path: str,
        preset: str = "medium",
        image_quality: Optional[int] = None,
        max_dpi: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        PDF belgesini optimize eder ve sıkıştırılmış halini hedefe kaydeder.
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Girdi dosyası bulunamadı: {input_path}")

        orig_size = os.path.getsize(input_path)
        preset_info = cls.PRESETS.get(preset, cls.PRESETS["medium"])

        quality = image_quality if image_quality is not None else preset_info["image_quality"]
        target_dpi = max_dpi if max_dpi is not None else preset_info["max_dpi"]

        doc = fitz.open(input_path)
        total_pages = len(doc)
        processed_xrefs = set()

        for page_idx in range(total_pages):
            if progress_callback:
                progress_callback(page_idx + 1, total_pages, f"Sayfa {page_idx + 1}/{total_pages} işleniyor...")

            page = doc[page_idx]
            image_list = page.get_images(full=True)

            for img_info in image_list:
                xref = img_info[0]
                if xref in processed_xrefs:
                    continue
                processed_xrefs.add(xref)

                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue

                    raw_bytes = base_image["image"]
                    ext = base_image["ext"].lower()
                    width = base_image["width"]
                    height = base_image["height"]

                    # Çok küçük ikon/vektör görsellerini atla
                    if width < 32 or height < 32:
                        continue

                    pil_img = Image.open(io.BytesIO(raw_bytes))

                    # DPI bazlı boyut küçültme hesabı
                    # Standart PDF sayfası 72 DPI varsayıldığında hedeflenen DPI ölçeği
                    scale = 1.0
                    # Eğer görsel 200+ DPI ise küçült
                    estimated_dpi = max(width, height) / 11.0  # Ortalama A4 ölçeği
                    if target_dpi and estimated_dpi > target_dpi * 1.25:
                        scale = target_dpi / estimated_dpi

                    new_w = max(32, int(width * scale))
                    new_h = max(32, int(height * scale))

                    if (new_w, new_h) != (width, height):
                        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    # RGB moduna dönüştür (şeffaflık maskesi yoksa)
                    if pil_img.mode in ("RGBA", "LA") and not base_image.get("smask"):
                        background = Image.new("RGB", pil_img.size, (255, 255, 255))
                        background.paste(pil_img, mask=pil_img.split()[-1])
                        pil_img = background
                    elif pil_img.mode not in ("RGB", "L"):
                        pil_img = pil_img.convert("RGB")

                    out_io = io.BytesIO()
                    pil_img.save(out_io, format="JPEG", quality=quality, optimize=True)
                    compressed_bytes = out_io.getvalue()

                    # Yalnızca orijinalinden daha küçükse değiştir
                    if len(compressed_bytes) < len(raw_bytes) * 0.95:
                        page.replace_image(xref, stream=compressed_bytes)

                except Exception:
                    # Hata alan görseli orijinal haliyle bırak
                    pass

        if progress_callback:
            progress_callback(total_pages, total_pages, "Belge akışları ve nesneler sıkıştırılıyor...")

        # Garbage collection ve deflate ile kaydet
        doc.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True
        )
        doc.close()

        comp_size = os.path.getsize(output_path)

        # Eğer herhangi bir nedenle sıkıştırılmış boyut orijinalden büyük çıktıysa
        # (örn. zaten aşırı sıkıştırılmış bir dosya) orijinali doğrudan kopyala
        if comp_size >= orig_size:
            doc_raw = fitz.open(input_path)
            doc_raw.save(output_path, garbage=4, deflate=True)
            doc_raw.close()
            comp_size = os.path.getsize(output_path)

        saved_bytes = max(0, orig_size - comp_size)
        savings_percent = (saved_bytes / orig_size * 100) if orig_size > 0 else 0.0

        return {
            "original_size": orig_size,
            "compressed_size": comp_size,
            "saved_bytes": saved_bytes,
            "savings_percent": round(savings_percent, 1)
        }
