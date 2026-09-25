# AuraPDF Geliştirme Kuralları & Geriye Dönük Uyumluluk (Backward Compatibility)

## Temel İlke
AuraPDF üzerinde geliştirilecek her yeni sürüm (v2, v3, vb.), bir önceki sürümün (v1, v2...) tüm özelliklerini, veri yapılarını ve kullanıcı alışkanlıklarını eksiksiz olarak kapsamak ve korumak zorundadır.

---

## Uyumluluk Kuralları

### 1. Eklemeli Tasarım (Additive Design)
* Yeni özellikler eklenirken mevcut özellikler, araçlar ve butonlar kaldırılmamalı veya kullanılamaz hale getirilmemelidir.
* Sınıf veya fonksiyonlara yeni parametreler eklenirken mutlaka varsayılan değerler (`default values` / `Optional[...]`) atanmalı, önceki çağrı biçimleri kırılmamalıdır.

### 2. Yapılandırma ve Kullanıcı Ayarları (QSettings)
* Kullanıcının kayıtlı tercihleri (`Language`, `Theme`, araç çubuğu yerleşimi, son açılan dosyalar vb.) yeni sürümde korunmalıdır.
* Yeni bir ayar eklendiğinde `settings.value(..., defaultValue)` şeklinde varsayılan değer atanmalı, eski kayıtlar bozulmadan okunabilmelidir.

### 3. Modül ve İçe Aktarma Sözleşmesi (API & Exports)
* `main.py` içerisindeki `_LAZY_EXPORTS` veya `src/` altındaki ana modül bağlantıları önceki sürümlerin beklediği sembolleri sağlamaya devam etmelidir.
* Gerekli refaktörlerde eski fonksiyon ve sınıflar takma ad (alias) veya uyumluluk katmanı (shim/facade) ile desteklenmelidir.

### 4. Dosya ve Belge Birlikte Çalışabilirliği
* PDF ek açıklamaları, kaydedilen projeler, form verileri ve çıktı formatları (PDF, Word, Excel, PPTX, EPUB) hem yeni hem eski sürümlerle tam uyumlu olmalıdır.

### 5. Kurulum ve Paketleme Uyumluluğu
* `installer.iss` (Inno Setup) ve `build_setup.py`, kullanıcı yeni sürümü mevcut sürümün üzerine kurduğunda (`over-install` / `upgrade`) ayarları ve kullanıcı verilerini silmeden sorunsuz güncelleme yapmalıdır.
