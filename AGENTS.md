# AuraPDF Proje İlkeleri, Kuralları ve Geliştirme Rehberi

Bu belge, AuraPDF projesinde kod yazan, hata gideren veya yeni özellik geliştiren tüm geliştiriciler ve AI agent'lar için bağlayıcı temel kuralları tanımlar.

---

## 1. Tema ve Görsel Bütünlük Kuralları
* **Tüm Temalarla Kusursuz Uyum:**
  * AuraPDF bünyesinde 8 tema yer alır (`dark`, `gray`, `emerald`, `purple`, `crimson`, `nord`, `vice_city`, `apple`).
  * Geliştirilen her yeni diyalog, pencere, açılır menü (popup) ve araç kutusu mutlaka tüm bu temalarla uyumlu olmalıdır.
  * Diyalog pencerelerinde `apply_dialog_theme(self, parent)` fonksiyonu kullanılmalıdır.
  * Sabit (hardcoded) ve temayı bozan arka plan/yazı renkleri yerine tema paletine duyarlı veya nötr/şeffaf stiller tercih edilmelidir.
* **Görsel Kalite ve Tipografi:**
  * Kenarlıklar, arka plan geçişleri ve yarı-saydam katmanlar modern işletim sistemi estetiğine (Windows 11 / macOS) uygun olmalıdır.
  * Odaklanma (focus), üzerine gelme (hover) ve devre dışı (disabled) durumları için görsel geri bildirim tanımlanmalıdır.

---

## 2. İkon ve Simge Kullanımı
* **Gereksiz Emoji Yasağı:**
  * Buton etiketlerinde, sekmelerde, araç çubuğunda, durum çubuklarında, hata veya bilgilendirme diyaloglarında gereksiz ve tutarsız emoji kullanımından kesinlikle kaçınılmalıdır.
* **Vektörel Çizim İkonları:**
  * Tüm simgeler `AuraIconFactory` (`ModernIconFactory`, `src/ui/icons.py`) üzerinden `QPainterPath` / vektörel çizimle üretilmelidir.
  * İkonlar açık ve koyu tema renklerine duyarlı olmalı, yüksek DPI (retina/ölçekli ekranlar) ekranlarda pikselleşmemelidir.

---

## 3. Çoklu Dil ve Yerelleştirme (i18n)
* **Sabit Metin (Hardcoded String) Yasağı:**
  * Kullanıcıya görünen hiçbir metin (pencere başlıkları, butonlar, ipuçları, hata mesajları vb.) doğrudan kod içerisine yazılmamalıdır.
  * Tüm metinler `LanguageManager.tr("anahtar")` çağrısı ile yerelleştirilmelidir.
* **TR - EN Tam Eşitlik:**
  * Yeni bir anahtar eklendiğinde hem Türkçe (`tr`) hem İngilizce (`en`) sözlüklerine aynı anda eklenmelidir.
  * İki sözlük arasındaki anahtar farkı (diff) daima `0` olmalıdır.

---

## 4. Mimari, Kaynak ve Bellek Güvenliği
* **Qt C++ Nesne Yaşam Döngüsü:**
  * `QTimer`, `QThread`, `QGraphicsItem` ve `QGraphicsProxyWidget` nesneleri silinirken veya sekme kapatılırken (`close_document`) silinmiş C++ nesnelerinden kaynaklanan `RuntimeError` riskine karşı korunmalıdır.
  * Zamanlayıcılar (`QTimer`) durdurulurken `try/except Exception` blokları kullanılmalıdır.
* **Asenkron İşlemler (Non-blocking UI):**
  * PDF sıkıştırma, OCR, sayfa dönüştürme ve parola kurtarma gibi CPU/G-Ç yoğun işlemler kesinlikle ana iş parçacığında (UI thread) çalıştırılmamalıdır; `QThread` ile arka planda yürütülmeli ve durum sinyallerle arayüze iletilmelidir.
* **Güvenli Dosya Kaydı:**
  * Dosyalar doğrudan üzerine yazılmak yerine geçici dosya (`.tmp_save`) oluşturulup başarı teyidinden sonra atomik olarak asıl dosyayla değiştirilmelidir.

---

## 5. Sürüm ve Branch Ayrımı
* **`aurapdf-basic-windows`:**
  * Standart, hızlı, bağımsız ve temel araçları eksiksiz barındıran tüketici/ofis sürümü.
  * Temel PDF okuma, not alma, çizim, AcroForms doldurma, PDF birleştirme/bölme/sıkıştırma, OCR ve sayfa yönetimi bu sürümün omurgasıdır.
* **`pro-windows`:**
  * Gelişmiş profesyonel ve kurumsal yetenekler (yapay zeka destekli belge analizi, e-imza / zaman damgası, ileri düzey toplu işleme vb.) bu dalda geliştirilir.
  * Basic sürümdeki geliştirmeler Pro dalına aktarılabilir olmalı, kod tabanları uyumlu tutulmalıdır.

---

## 6. Commit Mesaj Standartları
Commit mesajları açık, anlaşılır ve Conventional Commits standardına uygun olmalıdır. Asla emoji içermemelidir.

* **Format:** `<tip>(<kapsam>): <kısa açıklama>`
* **Kullanılacak Tipler:**
  * `feat`: Yeni bir kullanıcı özelliği eklendiğinde.
    * *Örnek:* `feat(compress): add background pdf compression with presets`
  * `fix`: Bir hata veya çökme giderildiğinde.
    * *Örnek:* `fix(timer): prevent runtimeerror on document close`
  * `refactor`: İşlevselliği değiştirmeden kod kalitesini artıran düzenlemeler.
    * *Örnek:* `refactor(forms): improve widget synchronization on save`
  * `style`: Mantıksal değişiklik içermeyen stil, tema ve UI düzenlemeleri.
    * *Örnek:* `style(ribbon): unify toolbar spacing and dark mode borders`
  * `i18n`: Çeviri anahtarları ve yerelleştirme düzeltmeleri.
    * *Örnek:* `i18n: add english translations for shortcuts guide`
  * `docs`: Dokümantasyon, kılavuz veya kural güncellemeleri.
    * *Örnek:* `docs: update AGENTS.md with architecture principles`
  * `chore`: Paketleme, derleme betikleri veya bağımlılık güncellemeleri.
    * *Örnek:* `chore(build): update inno setup script dependencies`

---

## 7. Çalışma Ortamı ve Dağıtım
* **Python Yürütücüsü:** `C:\Users\MRF4 ROG\AppData\Local\Microsoft\WindowsApps\python3.13.exe` (`python3.13`)
* **Paketleme / Dağıtım:** `build_setup.py` çalıştırılarak `Kurulum\AuraPDF_Setup.exe` oluşturulur.
