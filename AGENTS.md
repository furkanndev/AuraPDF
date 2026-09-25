# AuraPDF Agent Rehberi & Geliştirme İlkeleri

## 1. Geriye Dönük Tam Uyumluluk (Strict Backward Compatibility)
* **Kural:** Her yeni sürüm (v2, v3...), önceki sürümlerin (v1, v2...) sunduğu tüm özellikleri, araçları ve kullanıcı alışkanlıklarını eksiksiz kapsar.
* **Mevcut Özelliklerin Korunması:** Var olan hiçbir araç (çizim, metin, OCR, sayfa işlemleri, dönüşümler, yazdırma vb.) kaldırılmaz ya da bozulmaz.
* **API ve İçe Aktarmalar:** `main.py` ve `src/` mimarisindeki fonksiyon/sınıf imzaları geriye dönük uyumlu kalır (isteğe bağlı/varsayılan parametreler kullanılır).
* **Kullanıcı Verisi & Ayarlar:** `QSettings` anahtarları ve kullanıcı tercihleri silinmez, her zaman varsayılan değer fallback'leri ile okunur.
* Detaylı kural dosyası: [`.agents/rules/backward_compatibility.md`](file:///.agents/rules/backward_compatibility.md)

## 2. Çalışma Ortamı
* **Python Yürütücüsü:** `C:\Users\MRF4 ROG\AppData\Local\Microsoft\WindowsApps\python3.13.exe` (`python3.13`)
* **Paketleme / Dağıtım:** `build_setup.py` çalıştırılarak `Kurulum\AuraPDF_Setup.exe` oluşturulur.
