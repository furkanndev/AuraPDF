---
name: aurapdf-ui-verify
description: AuraPDF'te diyalog, pencere, popup, panel, ikon veya tema değişikliğinden sonra, işi bitti demeden önce kullan. Tema, i18n, DPI ve yerleşim kontrollerini içerir.
---

# AuraPDF Arayüz Doğrulama

## Otomatik kontroller

```bash
python -m unittest tests.test_static_guards tests.test_icon_sets
```

## Görsel kontrol

Widget'ı `.render()` ile PNG'ye çiz ve görüntüyü aç. Yalnızca testin geçmesine güvenme.

- `QT_QPA_PLATFORM=offscreen` yazı tiplerini kutu olarak çizebilir. Bu bir yerleşim kontrolü için yeterlidir ama metni doğrulamak için `QT_QPA_PLATFORM=windows` kullan.
- En az bir dar ve bir geniş boyutta çiz. Çakışmalar çoğunlukla dar genişlikte görülür.

## Kontrol listesi

- Sekiz temanın hepsinde okunuyor: `dark`, `gray`, `emerald`, `purple`, `crimson`, `nord`, `vice_city`, `apple`.
- Diyaloglar `apply_dialog_theme(self, parent)` kullanıyor, renkler tema paletinden geliyor.
- Yeni metinlerin tamamı `LanguageManager.tr()` ile geliyor ve TR ile EN anahtarları eş.
- Uzun Türkçe metin yerleşimi bozmuyor.
- Hover, odak ve devre dışı durumları görünüyor. Klavye ile de kullanılabiliyor.
- Ölçeklenen ekranda ikonlar pikselleşmiyor. Metin ile ikon üst üste binmiyor.
- Dar pencerede içerik taşmıyor veya kesilmiyor.

Çalıştıramadığın kontrolü geçti sayma. Kullanıcıya hangisini doğrulamadığını söyle.
