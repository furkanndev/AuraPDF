# AuraPDF Pro

<p align="center">
  <img src="assets/app_icon_128.png" alt="AuraPDF Logo" width="128" height="128" />
</p>

<p align="center">
  <strong>Gelişmiş, Yüksek Performanslı ve Kurumsal Masaüstü PDF Platformu</strong><br>
  Python 3, PyQt6 ve PyMuPDF motoru üzerine inşa edilmiş profesyonel PDF okuma, düzenleme ve belge işleme paketi.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Sürüm-Pro%20v2.2-6366f1?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python Version" />
  <img src="https://img.shields.io/badge/Arayüz-PyQt6-green?style=flat-square" alt="PyQt6" />
  <img src="https://img.shields.io/badge/PDF_Motoru-PyMuPDF-orange?style=flat-square" alt="PyMuPDF" />
  <img src="https://img.shields.io/badge/Platform-Windows_10%20%2F%2011-0078D6?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/Lisans-MIT-purple?style=flat-square" alt="License" />
</p>

---

## Genel Bakış

AuraPDF Pro, hem bireysel ofis ihtiyaçlarını hem de ileri düzey kurumsal PDF iş akışlarını karşılamak üzere tasarlanmış kapsamlı masaüstü uygulamasıdır.

PyMuPDF'in C seviyesindeki yüksek hızlı render altyapısını PyQt6'nın modern grafik bileşenleriyle harmanlayan AuraPDF Pro; çok sekmeli belge inceleme, doğrudan metin düzenleme, dijital/görsel imzalama, sandviç OCR (aranabilir PDF katmanı oluşturma), etkileşimli AcroForms form yönetimi ve zengin dönüştürme araçları sunar.

---

## Sürümler ve Branch Mimarisi

AuraPDF iki temel dal üzerinde geliştirilmektedir:

* **Basic Sürümü (`aurapdf-basic-windows`):**
  * Temel ofis ve günlük kullanım için bağımsız, hafif ve hızlı sürüm.
* **Pro Sürümü (`aurapdf_pro_windows`):**
  * Gelişmiş profesyonel yetenekler, kurumsal PDF imzalama/kaşe, sandviç OCR ve ileri düzey araç kutusunu içeren profesyonel sürüm.

---

## Temel Yetenekler ve Özellikler

### 1. Görüntüleme ve Okuma Deneyimi
* **Çok Sekmeli Mimari:** Birden fazla PDF belgesini tek pencerede bağımsız sekmeler halinde yönetebilme.
* **Akıcı Sayfa Gezinimi:** Sayfa küçük resimleri (Thumbnails paneli), sürekli kaydırma ve hızlı sayfa atlama.
* **Akıllı Yakınlaştırma ve Sığdırma:** Sayfa genişliğine sığdırma (`Ctrl+2`), sayfa yüksekliğine sığdırma (`Ctrl+0`) ve serbest yakınlaştırma.
* **Renk ve Okuma Modları:**
  * Standart (Gündüz) modu.
  * Gece okumaları için donanım/C-seviyesi ters çevirmeli Karanlık (Dark) modu.
  * Sıcak kağıt tonuyla göz yorgunluğunu önleyen Kitap (Sepia) modu.
* **Görünüm Geçmişi:** Tarayıcı mantığında ileri/geri konum geçmişi (`Alt+Sol Ok`, `Alt+Sağ Ok`).
* **Etkileşimli Köprüler:** Belge içi referans bağlantılarına ve web adreslerine anında erişim.

### 2. Metin İşlemleri ve Düzenleme
* **Doğal Metin Seçimi ve Kopyalama:** Sayfadaki metinleri fare ile doğal şekilde seçebilme ve panoya aktarma (`Ctrl+C`).
* **Yüzen Hızlı İşlem Çubuğu (HUD):** Metin seçildiği anda beliren araçlarla hızlı kopyalama, Google'da arama veya Google Çeviri'ye yönlendirme.
* **PDF Standart İşaretlemeleri:** Seçili metne Vurgulama (Highlight), Altı Çizili (Underline) ve Üstü Çizili (Strikeout) işaretleri ekleme.
* **Doğrudan Metin Düzenleme:** Mevcut PDF içeriğindeki metinleri sayfa üzerinde doğrudan seçip içeriğini ve tipografisini düzenleme.

### 3. Çizim, Not Alma ve Açıklamalar
* **Serbest Çizim ve Vurgulayıcı:** Ayarlanabilir çizgi kalınlığı, opaklık ve zengin renk paleti.
* **Vektörel Şekiller:** Düz çizgi, ok, dikdörtgen, elips ve serbest çizim araçları.
* **Metin Kutuları:** Belge üzerine serbest metin kutuları ekleme ve biçimlendirme.
* **Açıklamalar ve Yorumlar Paneli:** Belgedeki tüm not ve vurgulamaları filtreleme ve anında ilgili konuma odaklanma.

### 4. Pro Özellikler: İmzalama ve Gelişmiş OCR
* **PDF İmzalama (İmza & Kaşe):**
  * Çizerek imza oluşturma (fareniz veya kaleminizle imza çizimi).
  * Yazarak imza (farklı el yazısı fontları ve renk seçenekleriyle).
  * Görsel veya resmi kaşe yükleyip belgeye ekleme.
* **Sandviç OCR (Aranabilir PDF Katmanı):**
  * Orijinal görsel kalitesini ve mizanpajı %100 koruyarak arkaya görünmez koordinatlı metin katmanı yerleştirme.
  * Taranmış veya görsel PDF belgelerini doğrudan aranabilir (`Ctrl+F`) ve kopyalanabilir hale getirme.

### 5. Etkileşimli Form Doldurma (AcroForms)
* PDF formlarındaki metin kutularını (Text Fields), onay kutularını (Checkboxes) ve açılır seçim listelerini (Dropdowns) doğrudan doldurabilme ve kaydedebilme.

### 6. PDF Araç Kutusu (Toolbox)
* **Sayfa Yönetimi:**
  * PDF Birleştirme (Merge) ve Sayfa Ayırma (Split).
  * Sayfa silme, döndürme, yeniden sıralama ve boş sayfa ekleme.
  * Sayfa numaralandırma (konum, font, başlangıç numarası ayarlarıyla).
* **Format Dönüştürme:**
  * PDF ➔ Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`) ve E-Kitap (`.epub`).
* **Güvenlik ve Gizlilik:**
  * Parola koruması ve şifreleme.
  * Hassas alanları kalıcı olarak sansürleme / karartma (Redaction).
* **Filigran ve Arka Plan:**
  * Metin/görsel filigran ekleme, arka plan değiştirme veya temizleme.

### 7. Görsel Bütünlük ve Tema Sistemi
* Modern Windows 11 ve macOS estetiğine tam uyumlu arayüz.
* 8 dahili renk teması: `Dark`, `Gray`, `Nord`, `Emerald`, `Purple`, `Crimson`, `Vice City`, `Apple`.
* Yüksek DPI uyumlu vektörel simgeler (`AuraIconFactory`).

### 8. Çoklu Dil Desteği (i18n)
* Türkçe ve İngilizce dillerinde eksiksiz yerelleştirme.

---

## Kurulum ve Çalıştırma

### Sistem Gereksinimleri
* **İşletim Sistemi:** Windows 10 veya Windows 11 (64-bit)
* **Python Sürümü:** Python 3.10 veya üzeri

### Geliştirici Ortamı Kurulumu

1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/furkanndev/AuraPDF.git
   cd AuraPDF
   git checkout aurapdf_pro_windows
   ```

2. Sanal ortam (venv) oluşturun ve etkinleştirin:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Gerekli bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

---

## Kurulum Paketi (Installer) Üretimi

AuraPDF Pro, Inno Setup 6 ve PyInstaller aracılığıyla tek tıkla kurulabilir profesyonel Windows kurulum dosyası (`.exe`) haline getirilebilir.

1. Sisteminizde [Inno Setup 6](https://jrsoftware.org/isinfo.php) kurulu olmalıdır.
2. Derleme betiğini çalıştırın:
   ```bash
   python build_setup.py
   ```
3. Derleme tamamlandığında kurulum paketi aşağıdaki dizinde ve masaüstünde hazır olacaktır:
   * **Pro Sürümü:** `Kurulum/Pro/AuraPDF_Pro v<sürüm>.exe` (Örn: `Kurulum/Pro/AuraPDF_Pro v2.2.exe`)
   * **Basic Sürümü:** `Kurulum/Basic/AuraPDF_Basic v<sürüm>.exe`

*(Not: Sadece kurulum senaryosunu test etmek için `python build_setup.py --iss-only` parametresi kullanılabilir.)*

---

## Klavye Kısayolları

| Kısayol | İşlev |
| :--- | :--- |
| `Ctrl + O` | PDF Belgesi Aç |
| `Ctrl + S` | Belgeyi Kaydet |
| `Ctrl + Shift + S` | Farklı Kaydet |
| `Ctrl + W` | Aktif Sekmeyi Kapat |
| `Ctrl + Shift + T` | Son Kapatılan Sekmeyi Aç |
| `Ctrl + F` | Belge İçinde Metin Ara |
| `Ctrl + D` | Belge Özellikleri ve Güvenlik |
| `Ctrl + +` / `Ctrl + -` | Yakınlaştır / Uzaklaştır |
| `Ctrl + 0` | Sayfayı Yüksekliğe Sığdır |
| `Ctrl + 2` | Sayfayı Genişliğe Sığdır |
| `Alt + Sol Ok` | Önceki Görünüm Konumuna Git |
| `Alt + Sağ Ok` | Sonraki Görünüm Konumuna Git |
| `F11` | Tam Ekran Modu |
| `F1` | Kısayollar ve Yardım Rehberi |

---

## Proje Dizin Yapısı

```
AuraPDF/
├── assets/                 # Logo, vektörel varlıklar ve medya bileşenleri
├── src/
│   ├── core/              # Çekirdek yardımcılar (i18n, güncelleyici, kısayol yöneticisi)
│   ├── document/          # Belge, sayfa render ve sekme mimarisi (tab_document)
│   └── ui/                # Grafik arayüz bileşenleri
│       ├── dialogs/       # Araç kutusu, ayarlar, imza ve güncelleme pencereleri
│       ├── popups/        # Araç ayarları ve yüzen menüler
│       ├── icons.py       # Vektörel QPainterPath ikon fabrikası
│       ├── widgets.py     # Özelleştirilmiş araç çubukları ve kontroller
│       └── direct_text_editor.py # Doğrudan sayfa içi metin düzenleyici
├── Kurulum/               # Derlenen kurulum paketleri (Basic/ ve Pro/)
├── build_setup.py         # PyInstaller ve Inno Setup derleme otomasyonu
├── installer.iss          # Inno Setup kurulum senaryosu
├── main.py                # Uygulama ana giriş noktası
├── requirements.txt       # Python paket bağımlılıkları
├── AGENTS.md              # Geliştirme ilkeleri ve mimari kurallar rehberi
└── README.md              # Proje dokümantasyonu
```

---

## Lisans

Bu proje MIT Lisansı altında sunulmaktadır. Ayrıntılar için `LICENSE` dosyasına başvurabilirsiniz.
