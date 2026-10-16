# AuraPDF

<p align="center">
  <img src="assets/app_icon_128.png" alt="AuraPDF Logo" width="128" height="128" />
</p>

<p align="center">
  <strong>Modern, Fast, and Extensible Windows Desktop PDF Suite</strong><br>
  Engineered with Python 3, PyQt6, and the high-speed PyMuPDF rendering engine. Features native OCR, direct page text editing, interactive forms, annotations, and standalone installer packaging.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-Basic%20v1.1-27272a?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white" alt="PyQt6" />
  <img src="https://img.shields.io/badge/Engine-PyMuPDF-D9381E?style=flat-square" alt="PyMuPDF" />
  <img src="https://img.shields.io/badge/OCR-RapidOCR%20%2F%20ONNX-blue?style=flat-square" alt="OCR" />
  <img src="https://img.shields.io/badge/Packaging-Inno%20Setup-0078D7?style=flat-square&logo=windows&logoColor=white" alt="Inno Setup" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=flat-square&logo=windows11&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square" alt="License" />
</p>

<p align="center">
  <a href="#english-overview">English Overview</a> •
  <a href="#genel-bakış">Türkçe Dokümantasyon</a> •
  <a href="#kurulum-ve-çalıştırma">Kurulum & İndirme</a>
</p>

---

## English Overview

AuraPDF is a high-performance Windows desktop PDF productivity suite engineered for power users, developers, and office professionals. By combining the low-latency C-based rendering of PyMuPDF with modern PyQt6 UI architecture, AuraPDF delivers fluid multi-tabbed viewing, in-place text modification, and complete document management without heavy runtime overhead.

### Key Capabilities
- **Direct Page Text Editing:** Select, mutate, re-font, and reflow text blocks directly on PDF pages in real time.
- **Embedded OCR Pipeline:** Extract text from scanned pages using local ONNX / RapidOCR inference.
- **Interactive Form Filling (AcroForms):** Populate, serialize, and validate text boxes, checkboxes, and select dropdowns.
- **Document Management Toolbox:** Split, merge, reorder, rotate, compress, redact sensitive areas, and password-encrypt documents.
- **Modern Fluent UI & Themes:** 8 curated color themes (Dark, Nord, Emerald, Vice City, etc.) with resolution-independent vector icons.
- **Production Installer:** Automated standalone build scripts generating single-click Windows installers (`.exe`) via PyInstaller and Inno Setup 6.

---

## Genel Bakış

AuraPDF, bireysel ve profesyonel kullanıcıların günlük PDF iş akışlarını modern bir arayüz, yüksek performans ve sistem kaynaklarını yormayan hafif mimariyle çözmek üzere tasarlanmış masaüstü uygulamasıdır.

PyMuPDF'in C tabanlı yüksek hızlı render kabiliyetini PyQt6'nın modern grafik bileşenleriyle birleştiren AuraPDF; çok sekmeli belge inceleme, doğrudan sayfa üzeri metin düzenleme, etkileşimli form doldurma, gelişmiş açıklama/çizim araçları ve kapsamlı bir PDF araç kutusu sunar.

---

## Sürümler ve Branch Mimarisi

AuraPDF iki temel sürüm kolu üzerinden geliştirilmektedir:

* **Basic Sürümü (`aurapdf-basic-windows`):**
  * Hızlı, bağımsız, günlük ve ofis kullanımına yönelik tüm temel işlevleri barındıran kararlı sürüm.
  * PDF okuma, doğrudan metin düzenleme, serbest not alma/çizim, etkileşimli form doldurma (AcroForms), sayfa yönetimi (birleştirme, bölme, döndürme), PDF sıkıştırma ve yerel OCR işlevlerini içerir.
* **Pro Sürümü (`pro-windows`):**
  * Kurumsal ve ileri düzey yeteneklere odaklanan genişletilmiş profesyonel sürüm.

---

## Temel Özellikler

### 1. Görüntüleme ve Okuma Deneyimi
* **Çok Sekmeli Çalışma:** Birden fazla PDF belgesini tek bir pencerede bağımsız sekmeler halinde açabilme ve yönetebilme.
* **Akıcı Sayfa Gezinimi:** Sürekli kaydırma, tek sayfa görünümü, sayfa küçük resimleri (Thumbnails paneli) ve hızlı atlama.
* **Akıllı Yakınlaştırma ve Sığdırma:** Sayfa genişliğine sığdırma (`Ctrl+2`), sayfa yüksekliğine sığdırma (`Ctrl+0`) ve serbest ölçekleme.
* **Renk ve Okuma Modları:**
  * Standart (Gündüz) modu.
  * Düşük ışık ve gece okumaları için yüksek performanslı karanlık (Dark) modu.
  * Göz yorgunluğunu azaltan sıcak kağıt tonu (Sepia) modu.
* **Görünüm Geçmişi:** Web tarayıcısı mantığıyla çalışan ileri/geri konum geçmişi (`Alt+Sol Ok`, `Alt+Sağ Ok`).
* **Etkileşimli Köprüler:** Belge içi sayfa referanslarına ve harici web bağlantılarına doğrudan tıklayarak erişim.

### 2. Metin İşlemleri ve Düzenleme
* **Doğal Metin Seçimi:** Belgedeki metinleri fare ile hassas şekilde seçebilme ve panoya kopyalama (`Ctrl+C`).
* **Yüzen Hızlı İşlem Çubuğu (HUD):** Metin seçildiği anda beliren araç çubuğu ile tek tıkla kopyalama, Google'da arama veya Google Çeviri'ye yönlendirme.
* **PDF Standart İşaretlemeleri:** Seçili metne doğrudan PDF standardına uygun Vurgulama (Highlight), Altı Çizili (Underline) ve Üstü Çizili (Strikeout) açıklamaları ekleme.
* **Doğrudan Sayfa Üzeri Metin Düzenleme:** Mevcut PDF içeriğindeki metin bloklarını doğrudan sayfa üzerinde seçip anında içeriğini, fontunu ve biçimini düzenleyebilme.

### 3. Çizim, Not Alma ve Açıklamalar
* **Serbest Çizim ve Vurgulayıcı:** Fırça kalınlığı, opaklık ve zengin renk paleti ile not alma.
* **Vektörel Şekiller:** Düz çizgi, ok, dikdörtgen, elips ve serbest çizim bileşenleri.
* **Metin Kutuları:** Sayfanın istenen bölgesine yerleştirilebilir, boyutlandırılabilir ve biçimlendirilebilir metin kutuları.
* **Açıklama ve Yorumlar Paneli:** Belgedeki tüm not ve vurgulamaları tek bir panelde sayfa/tür bazında filtreleyip doğrudan ilgili konuma odaklanma.

### 4. Etkileşimli Form Doldurma (AcroForms)
* PDF formlarında yer alan metin alanlarını (Text Fields), onay kutularını (Checkboxes) ve açılır seçim listelerini (Dropdowns) doğrudan doldurabilme, verileri kaydedebilme ve temizleyebilme.

### 5. PDF Araç Kutusu (Toolbox)
* **Sayfa Yönetimi:**
  * PDF Birleştirme (Merge) ve Sayfa Ayırma (Split).
  * Sayfa silme, döndürme, yeniden sıralama ve boş sayfa ekleme.
  * Özelleştirilebilir sayfa numaralandırma (konum, font, başlangıç numarası).
* **PDF Sıkıştırma (Compressor):**
  * Arka planda çalışan, görsel ve font optimizasyonu sağlayan sıkıştırma motoru.
  * Hazır profiller: Yüksek Sıkıştırma (Extreme), Dengeli (Recommended), Düşük Kayıplı (High Quality).
* **Format Dönüştürme:**
  * PDF belgesini Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`) ve E-Kitap (`.epub`) formatlarına dönüştürme.
* **Güvenlik ve Gizlilik:**
  * Parola koruması ve şifreleme.
  * Hassas alanları kalıcı olarak karartma (Redaction).
* **Optik Karakter Tanıma (OCR):**
  * Dahili RapidOCR / ONNX motoru ile taranmış belgelerden metin ayıklama.
* **Filigran ve Arka Plan:**
  * Belgelere metin/görsel filigran ekleme, arka plan değiştirme veya temizleme.

### 6. Görsel Bütünlük ve Tema Sistemi
* Modern Windows 11 ve macOS estetiğine uygun, yüksek DPI duyarlı arayüz tasarımı.
* 8 dahili renk teması: `Dark`, `Gray`, `Nord`, `Emerald`, `Purple`, `Crimson`, `Vice City`, `Apple`.
* Tutarlı vektörel simgeler (`QPainterPath` tabanlı `AuraIconFactory`).

### 7. Çoklu Dil Desteği (i18n)
* Türkçe ve İngilizce tam yerelleştirme.
* Çalışma anında anlık dil değişimi desteği.

### 8. Oturum ve Güncelleme Yönetimi
* **Oturum Kurtarma:** Uygulama yeniden başlatıldığında açık sekmelerin ve aktif sayfa konumlarının korunması.
* **Kapatılan Sekmeyi Geri Açma:** `Ctrl+Shift+T` desteği.
* **Dış Dosya İzleme:** Belge açıkken dosya üzerinde dışarıdan yapılan değişiklikleri algılama ve kullanıcıya yenileme teklif etme.
* **Yazılım Güncellemeleri:** GitHub Releases entegrasyonu üzerinden otomatik/manuel sürüm kontrolü ve doğrudan indirme diyalogu.

---

## Kurulum ve Çalıştırma

### Sistem Gereksinimleri
* **İşletim Sistemi:** Windows 10 veya Windows 11 (64-bit)
* **Python Sürümü:** Python 3.10 veya üzeri

### Geliştirici Ortamı Kurulumu

1. Depoyu yerel ortamınıza klonlayın:
   ```bash
   git clone https://github.com/furkanndev/AuraPDF.git
   cd AuraPDF
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

AuraPDF, Inno Setup 6 ve PyInstaller aracılığıyla tek tıkla kurulabilir profesyonel Windows kurulum dosyası (`.exe`) haline getirilebilir.

1. Sisteminizde [Inno Setup 6](https://jrsoftware.org/isinfo.php) kurulu olmalıdır.
2. Proje kök dizinindeki derleme betiğini çalıştırın:
   ```bash
   python build_setup.py
   ```
3. Derleme tamamlandığında paket aktif dala göre aşağıdaki konuma ve masaüstüne kaydedilir:
   * **Basic Sürümü:** `Kurulum/Basic/AuraPDF_Basic v<sürüm>.exe` (Örn: `Kurulum/Basic/AuraPDF_Basic v1.1.exe`)
   * **Pro Sürümü:** `Kurulum/Pro/AuraPDF_Pro v<sürüm>.exe`

*(Not: PyInstaller derlemesini atlayıp sadece Inno Setup senaryosunu test etmek için `python build_setup.py --iss-only` parametresi kullanılabilir.)*

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
│       ├── dialogs/       # Araç kutusu, ayarlar, sıkıştırma ve güncelleme pencereleri
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
