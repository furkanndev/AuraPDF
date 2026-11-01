---
name: aurapdf-icons
description: AuraPDF'te ikon eklerken, çizerken, yeniden adlandırırken, ikon seti veya ikon galerisi üzerinde çalışırken kullan. src/ui/icon_glyphs.py, AuraIconFactory ve AuraIconSetGallery için kuralları ve kontrolleri içerir.
---

# AuraPDF İkonları

## Dosyalar

- `src/ui/icon_glyphs.py`: 24x24 ızgaralı glyph'ler, `ICON_SETS`, `AuraGlyphEngine`.
- `src/ui/icons.py`: `AuraIconFactory`. `icon_<ad>` metotları glyph varsa onunla değiştirilir.
- `src/ui/dialogs/settings_dialog.py`: `AuraIconSetGallery` ve İkon Seti ayarı.
- `tests/test_icon_sets.py`: Koruma testleri.

## Yeni glyph

1. `GLYPHS` içine `icon_glyphs.py` başlığındaki söz dizimiyle, özgün çizimle ekle.
2. Rengi çağıran yerden korunacaksa adı `COLORFUL_GLYPHS` içine ekle. Yoksa doygun renk temaya çevrilir.
3. Aynı anlam için aynı şekli kullan. Farklı anlam için belirgin farklı siluet kullan.
4. Kapalı şekilleri gerçekten kapat. `Katman` ve `Dolu Form` setleri dolguyu kapalı yollardan üretir.

## İkon setleri

- Setler `_ICON_SET_SHAPES` içinde tanımlıdır. Her setin `_mono` çifti otomatik oluşur.
- Yeni set ayrı bir siluet üretmelidir. Yalnızca çizgi kalınlığını birkaç onda bir değiştiren set ekleme.
- Set kodu saklı ayardır (`icon_style`), görünen ad değildir. Görünen adı değiştirmek için yalnızca `i18n.py` metnini değiştir.
- Her set için TR ve EN `settings_icon_style_<kod>` anahtarı gerekir.

## Galeri

- Ad üst satırda, ikonlar alt satırdadır. İkonları ad satırına geri taşıma. Eski çakışma buradan doğdu.
- Boyutları `_title_rect` ve `_icon_rects` üzerinden hesapla.
- Dar kartta ikon sayısı azalır, uzun ad kısaltılır. Çakışma kabul edilmez.
- `SAMPLES` içindeki ikonlar `COLORFUL_GLYPHS` sınıfında olmalı ve siluetleri birbirinden ayrılmalıdır. Kalem, fosforlu kalem ve silgi gibi çapraz şekilleri bir arada kullanma.

## Doğrulama

```bash
python -m unittest tests.test_icon_sets tests.test_static_guards
```

Sonra `aurapdf-ui-verify` skill'ini uygula.
