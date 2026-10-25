<p align="center">
  <img src="assets/app_icon_128.png" alt="AuraPDF Pro Logo" width="112" height="112" />
</p>

<h1 align="center">AuraPDF Pro</h1>

<p align="center">
  <strong>Gelişmiş, Yüksek Performanslı ve Çevrimdışı Yapay Zeka Destekli Masaüstü PDF Platformu</strong><br>
  Python 3, PyQt6 ve C++ tabanlı PyMuPDF render motoru üzerine inşa edilmiş kurumsal düzeyde PDF okuma, doğrudan düzenleme, sayfa organizasyonu ve belge zekası paketi.
</p>

<p align="center">
  <a href="https://github.com/furkanndev/AuraPDF/releases"><img src="https://img.shields.io/badge/Sürüm-Pro%20v2.2.3-6366f1?style=for-the-badge&logo=windows&logoColor=white" alt="Version" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://www.riverbankcomputing.com/software/pyqt/"><img src="https://img.shields.io/badge/Arayüz-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6" /></a>
  <a href="https://pymupdf.readthedocs.io/"><img src="https://img.shields.io/badge/PDF_Motoru-PyMuPDF_2.0-FF6F00?style=for-the-badge" alt="PyMuPDF" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Windows_10%20%2F%2011-0078D6?style=for-the-badge&logo=windows11&logoColor=white" alt="Platform" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/Lisans-MIT-a855f7?style=for-the-badge" alt="License" /></a>
</p>

---

<p align="center">
  <img src="docs/screenshots/01_hero_reader_dark.png" alt="AuraPDF Pro Belge Okuma Arayüzü" width="96%" style="border-radius: 10px; box-shadow: 0 8px 30px rgba(0,0,0,0.3);" />
</p>

---

## 📑 İçindekiler
- [Genel Bakış](#-genel-bakış)
- [Öne Çıkan Temel Yetenekler](#-öne-çıkan-temel-yetenekler)
  - [1. Akıllı Belge Okuma ve Çok Sekmeli Çalışma Alanı](#1-akıllı-belge-okuma-ve-çok-sekmeli-çalışma-alanı)
  - [2. Başlangıç Paneli ve Şablon Merkezi](#2-başlangıç-paneli-ve-şablon-merkezi)
  - [3. Görsel Sayfa Organizasyonu](#3-görsel-sayfa-organizasyonu)
  - [4. Kapsamlı PDF Araç Kutusu ve Format Dönüştürme](#4-kapsamlı-pdf-araç-kutusu-ve-format-dönüştürme)
  - [5. Doğrudan Sayfa İçi Metin Düzenleme ve İşaretlemeler](#5-doğrudan-sayfa-içi-metin-düzenleme-ve-işaretlemeler)
  - [6. Aura AI - Yerel Yapay Zeka Belge Zekası](#6-aura-ai---yerel-yapay-zeka-belge-zekası)
  - [7. Dijital İmza, Kaşe ve Etkileşimli Formlar (AcroForms)](#7-dijital-imza-kaşe-ve-etkileşimli-formlar-acroforms)
  - [8. 8 Farklı Renk Teması ve Yüksek DPI Estetiği](#8-8-farklı-renk-teması-ve-yüksek-dpi-estetiği)
- [Sistem Gereksinimleri](#-sistem-gereksinimleri)
- [Kurulum ve Çalıştırma](#-kurulum-ve-çalıştırma)
- [Kurulum Paketi (Installer .exe) Derleme](#-kurulum-paketi-installer-exe-derleme)
- [Klavye Kısayolları](#-klavye-kısayolları)
- [Proje Mimarisi ve Dizin Düzeni](#-proje-mimarisi-ve-dizin-düzeni)
- [Geliştirme İlkeleri ve Dal (Branch) Mimarisi](#-geliştirme-ilkeleri-ve-dal-branch-mimarisi)
- [Lisans](#-lisans)

---

## 🌟 Genel Bakış

**AuraPDF Pro**, hem bireysel günlük ofis ihtiyaçlarını hem de yüksek güvenlik gerektiren kurumsal belge işleme iş akışlarını tek bir çatı altında karşılamak üzere geliştirilmiş profesyonel masaüstü PDF platformudur.

PyMuPDF'in C/C++ seviyesindeki ultra hızlı rasterizasyon altyapısını PyQt6'nın modern grafik bileşenleriyle harmanlayan AuraPDF Pro; binlerce sayfalık büyük belgelerde bile akıcı 60+ FPS gezinme, sıfıra yakın bellek gecikmesi, %100 yerel ve gizlilik odaklı yapay zeka analizleri, doğrudan sayfa içi metin manipülasyonu, aranabilir Sandviç OCR katmanı ve Adobe Acrobat standartlarında zengin bir araç seti sunar.

---

## 🚀 Öne Çıkan Temel Yetenekler

### 1. Akıllı Belge Okuma ve Çok Sekmeli Çalışma Alanı

<p align="center">
  <img src="docs/screenshots/01_hero_reader_dark.png" alt="AuraPDF Pro Okuma Deneyimi" width="94%" style="border-radius: 8px;" />
</p>

* **Çok Sekmeli Sekme Çubuğu:** Birden fazla PDF belgesini tek ana pencerede modern, sürüklenebilir ve kapatılabilir sekmeler halinde yönetebilme (`Ctrl+W`, `Ctrl+Shift+T`).
* **Hiyerarşik Yer İmleri (TOC):** Belge içindeki içindekiler tablosunu derinlikli ağaç yapısıyla görüntüleme ve tek tıkla ilgili başlığa ışınlanma.
* **Yüzen Hızlı Araç Kapsülü (Floating Capsule):** Sayfa üzerinde farenizin hemen yanında beliren serbestçe taşınabilir, sabitleştirilebilir kompakt araç paleti.
* **Okuma ve Renk Modları:**
  * **Standart Gündüz Modu:** Orijinal PDF renk doğruluğu.
  * **Donanım Hızlandırmalı Karanlık Mod:** Gözü yormayan C-seviyesi ters çevirme ve koyu zemin uyumu.
  * **Kitap (Sepia) Modu:** Uzun soluklu okumalar için sıcak kağıt tonlaması.
* **Gelişmiş Navigasyon:** Sayfa genişliğine sığdırma (`Ctrl+2`), yüksekliğe sığdırma (`Ctrl+0`), dinamik yakınlaştırma (`Ctrl++` / `Ctrl+-`), tarayıcı mantığında ileri/geri görünüm geçmişi (`Alt+Sol Ok`, `Alt+Sağ Ok`).

---

### 2. Başlangıç Paneli ve Şablon Merkezi

<p align="center">
  <img src="docs/screenshots/02_home_dashboard.png" alt="AuraPDF Pro Başlangıç Paneli" width="94%" style="border-radius: 8px;" />
</p>

* **Hızlı Şablonlarla Yeni Belge Başlatma:** Tek tıkla *Boş Belge*, *Çizgili Not*, *Kareli Kağıt*, *Cornell Notlandırma Şablonu* veya *Noktalı Defter* sayfası oluşturup hemen çizim/yazmaya başlama.
* **Akıllı Son Açılanlar Listesi:** Dosya yolu, sayfa sayısı, dosya boyutu ve son değiştirilme zamanı metaverileriyle zenginleştirilmiş hızlı erişim listesi.
* **Favoriler Bölümü:** Sık çalıştığınız kritik kurumsal belgeleri favorilere ekleyerek tek tıkla erişme.
* **Önerilen Eylemler Kartları:** Sayfa organizasyonu, yorum ekleme, form doldurma, güvenlik ve dönüştürme araçlarına anında yönlendirme.

---

### 3. Görsel Sayfa Organizasyonu

<p align="center">
  <img src="docs/screenshots/03_organize_pages.png" alt="AuraPDF Pro Sayfa Organizasyonu" width="94%" style="border-radius: 8px;" />
</p>

* **Tam Ekran Sayfa Izgarası (Grid View):** Belgedeki tüm sayfaları yüksek çözünürlüklü küçük resim kartları halinde tek bir ekranda inceleme.
* **Sürükle-Bırak Sayfa Sıralama:** Sayfaları fare ile serbestçe sürükleyerek saniyeler içinde sırasını değiştirme.
* **Sayfa Manipülasyon Araçları:**
  * Saat yönünde veya tersinde sayfa döndürme (Rotate 90° CW / CCW).
  * İstenmeyen sayfaları toplu seçerek tek tıkla silme.
  * Belirli sayfaları yeni bağımsız bir PDF olarak dışa aktarma (Extract Pages).
  * Yeni boş sayfa veya harici PDF sayfaları ekleme (Insert Pages).
  * Seçili sayfaları çoğaltma (Duplicate).

---

### 4. Kapsamlı PDF Araç Kutusu ve Format Dönüştürme

<p align="center">
  <img src="docs/screenshots/04_convert_and_export.png" alt="AuraPDF Pro Format Dönüştürme" width="94%" style="border-radius: 8px;" />
</p>

* **Office ve Belge Formatlarına Dönüştürme:**
  * **Microsoft Word (`.docx`):** Mizanpajı, paragrafları ve tabloları koruyarak kusursuz Word dönüşümü.
  * **Hesap Tablosu (`.xlsx`):** Belge içi veri tablolarını otomatik algılayıp düzenlenebilir Excel sayfasına çevirme.
  * **Sunum (`.pptx`):** Sayfaları yüksek çözünürlüklü PowerPoint slaytlarına dönüştürme.
  * **E-Kitap (`.epub`):** E-okuyucular için akıcı metin formatına çevrim.
  * **Görsel Formatları (`.png`, `.jpg`):** Sayfaları veya belgedeki tüm gömülü resimleri topluca dışa aktarma.
  * **Web ve Metin:** HTML web sayfası, Zengin Metin Biçimi (`.rtf`), Düz Metin (`.txt`) ve PostScript (`.eps`).
* **PDF Birleştirme (Merge) ve Sayfa Ayırma (Split):** Onlarca PDF dosyasını sıralayıp tek dosyada birleştirme veya sayfa aralıklarına göre bölme.
* **Sandviç OCR (Aranabilir PDF Katmanı):** Taranmış dokümanların orijinal görsel kalitesini bozmadan arka plana koordinatlı, görünmez ve aranabilir (`Ctrl+F`) metin katmanı yerleştirme.
* **PDF Sıkıştırma (Compress):** Görsel DPI optimizasyonu ve akıllı veri akışı temizliği ile dosya boyutunu %80'e varan oranda küçültme.

---

### 5. Doğrudan Sayfa İçi Metin Düzenleme ve İşaretlemeler

<p align="center">
  <img src="docs/screenshots/05_direct_edit_mode.png" alt="AuraPDF Pro Doğrudan Metin Düzenleme" width="94%" style="border-radius: 8px;" />
</p>

* **Doğrudan Sayfa İçi Metin Düzenleyici (Direct Text Editor):** PDF üzerindeki mevcut metin bloklarına tıklayıp harf, kelime veya cümleleri doğrudan sayfa üzerinde düzenleme, font ve boyut uyarlaması yapabilme.
* **Standart PDF İşaretlemeleri:** Vurgulama (Highlight), Altı Çizili (Underline), Üstü Çizili (Strikeout) ve Dalgalı Çizgi işaretleri.
* **Serbest Çizim ve Vurgulayıcı:** Basınca ve opaklığa duyarlı serbest el kalemi, çizgi, ok, dikdörtgen, elips çizimleri.
* **Açıklama ve Yorum Notları:** Yapışkan notlar (Sticky Notes), serbest metin kutuları ve yorum paneli üzerinden filtreleme.
* **Kalıcı Sansürleme (Redaction):** Hassas TC kimlik, kredi kartı, adres veya kurumsal gizli bilgileri PDF kodlamasından kalıcı olarak yok eden siyah bantlama.

---

### 6. Aura AI - Yerel Yapay Zeka Belge Zekası

<p align="center">
  <img src="docs/screenshots/06_ai_assistant.png" alt="Aura AI Belge Asistanı" width="88%" style="border-radius: 8px;" />
</p>

* **%100 Çevrimdışı ve Gizlilik Öncelikli:** Belgeleriniz asla izniniz olmadan uzak sunuculara gönderilmez; yerel analiz altyapısı sayesinde gizli kurumsal ve hukuki dokümanlarınızı güvenle işler.
* **Yönetici Özeti (Executive Summary):** Yüzlerce sayfalık karmaşık belgeleri saniyeler içinde okuyup özetleyen, kritik bulguları ve bölüm dağılımını çıkaran analiz motoru.
* **Kritik Maddeler & Risk Tespiti:** Sözleşmelerdeki cezai şartları, bağlayıcı maddeleri, teslim tarihlerini ve parasal yükümlülükleri otomatik saptama.
* **Etkileşimli Soru-Cevap & Sohbet:** Belgenize istediğiniz dilde sorular sorup sayfa referanslı, doğrudan kaynak metinden beslenen yanıtlar alma.
* **İsteğe Bağlı Bulut API Desteği:** İhtiyaç duyulduğunda Google Gemini veya OpenAI API anahtarlarıyla ileri düzey akıl yürütme motorlarına bağlanabilme.

---

### 7. Dijital İmza, Kaşe ve Etkileşimli Formlar (AcroForms)

* **PDF İmzalama Paketi:**
  * Fare veya dijital kalem ile serbest el imzası çizimi.
  * Ad/soyad yazarak stilize edilmiş el yazısı fontlarıyla imza oluşturma.
  * Saydam arka planlı PNG mühür veya ıslak imza görseli yükleyip belgeye yerleştirme.
* **AcroForms Desteği:** Resmi PDF formlarındaki metin kutuları (Text Fields), onay kutuları (Checkboxes) ve açılır seçim listelerini (Dropdowns) çift yönlü doldurma, temizleme ve kaydetme.
* **Bates Numaralandırması & Sayfa Numaraları:** Hukuki ve resmi evraklar için özelleştirilebilir konum, önek ve sayaç ayarlarıyla sayfa numaralandırma.

---

### 8. 8 Farklı Renk Teması ve Yüksek DPI Estetiği

AuraPDF Pro, göz konforunuz ve çalışma tarzınıza göre seçebileceğiniz 8 profesyonel renk teması sunar:

| Tema | Açıklama |
| :--- | :--- |
| **Dark** | Modern derin siyah ve neon mavisi vurgularıyla gece okuma modu |
| **Gray** | IntelliJ / JetBrains tarzı dengeli, göz yormayan kurumsal gri |
| **Nord** | İskandinav esintili soğuk kutup mavisi ve yumuşak koyu tonlar |
| **Apple** | macOS Sonoma / Sequoia tasarım diline sadık zarif yarı-saydam estetik |
| **Emerald** | Zümrüt yeşili vurgular ve derin yeşilimsi siyah gece tonu |
| **Purple** | Canlı mor ve lila aksanlarıyla modern stüdyo teması |
| **Crimson** | Enerjik kırmızı aksanlara sahip güçlü koyu palet |
| **Vice City** | Siberpunk mor ve camgöbeği/pembe retro neon dokunuşları |

*Tüm simgeler `AuraIconFactory` üzerinden vektörel `QPainterPath` ile çizilir; 4K ve yüksek DPI ölçekli ekranlarda sıfır pikselleşme ile kusursuz görünür.*

---

## 💻 Sistem Gereksinimleri

* **İşletim Sistemi:** Windows 10 veya Windows 11 (64-bit)
* **İşlemci:** Çift çekirdekli 1.8 GHz veya daha üstü
* **Bellek (RAM):** Minimum 2 GB (4 GB önerilir)
* **Depolama:** Kurulum için 250 MB boş alan
* **Python (Geliştiriciler için):** Python 3.10 veya üzeri

---

## 🔧 Kurulum ve Çalıştırma

### Son Kullanıcılar İçin (Windows Kurulum Paketi)
En güncel `.exe` kurulum dosyasını doğrudan [Releases](https://github.com/furkanndev/AuraPDF/releases) sayfasından indirip tek tıkla kurabilirsiniz. Kurulum paketi masaüstü kısayollarını, başlat menüsü entegrasyonunu ve `.pdf` dosya ilişkilendirmesini otomatik olarak yapılandırır.

---

### Geliştiriciler İçin (Kaynak Koddan Çalıştırma)

1. **Depoyu Klonlayın:**
   ```bash
   git clone https://github.com/furkanndev/AuraPDF.git
   cd AuraPDF
   git checkout aurapdf_pro_windows
   ```

2. **Python Sanal Ortamını (venv) Oluşturun ve Etkinleştirin:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Bağımlılıkları Yükleyin:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Uygulamayı Başlatın:**
   ```powershell
   python main.py
   ```

---

## 📦 Kurulum Paketi (Installer .exe) Derleme

AuraPDF Pro, **PyInstaller** ve **Inno Setup 6** aracılığıyla profesyonel, imzalı ve taşınabilir kurulum dosyası (`.exe`) haline getirilebilir.

1. Bilgisayarınızda [Inno Setup 6](https://jrsoftware.org/isinfo.php)'nın kurulu olduğundan emin olun.
2. Proje kök dizininde derleme betiğini çalıştırın:
   ```powershell
   python build_setup.py
   ```
3. Derleme tamamlandığında kurulum paketi aşağıdaki konumlarda hazır olacaktır:
   * `Kurulum/Pro/AuraPDF_Pro v<sürüm>.exe` (Örn: `AuraPDF_Pro v2.2.3.exe`)
   * Masaüstü: `AuraPDF_Pro v2.2.3.exe`

*(Yalnızca Inno Setup betiğini test etmek isterseniz `python build_setup.py --iss-only` parametresini kullanabilirsiniz.)*

---

## ⌨️ Klavye Kısayolları

| Kısayol | Eylem / İşlev |
| :--- | :--- |
| `Ctrl + O` | PDF Belgesi Aç |
| `Ctrl + S` | Mevcut Belgeyi Güvenli Kaydet |
| `Ctrl + Shift + S` | Farklı Kaydet |
| `Ctrl + W` | Aktif Sekmeyi Kapat |
| `Ctrl + Shift + T` | Son Kapatılan Sekmeyi Geri Aç |
| `Ctrl + F` | Belge İçinde Metin Ara |
| `Ctrl + K` | Hızlı Komut ve Araç Paletini Aç (Command Palette) |
| `Ctrl + D` | Belge Özellikleri, Metaveri ve Güvenlik |
| `Ctrl + +` / `Ctrl + -` | Yakınlaştır / Uzaklaştır |
| `Ctrl + 0` | Sayfayı Pencere Yüksekliğine Sığdır |
| `Ctrl + 2` | Sayfayı Pencere Genişliğine Sığdır |
| `Alt + Sol Ok` | Önceki Görünüm Konumuna Geri Dön |
| `Alt + Sağ Ok` | Sonraki Görünüm Konumuna İlerle |
| `F11` | Tam Ekran Okuma Modu |
| `F1` | Kısayol Rehberi ve Yardım |

---

## 📂 Proje Mimarisi ve Dizin Düzeni

```text
AuraPDF/
├── assets/                     # İkonlar, logolar, Windows kabuk entegrasyonu bileşenleri
├── docs/
│   └── screenshots/            # Yüksek çözünürlüklü dokümantasyon ekran görüntüleri
├── src/
│   ├── core/                  # Çekirdek motorlar (i18n, AI iş parçacıkları, güncelleme yöneticisi)
│   ├── document/              # Çok sekmeli belge mimarisi (tab_document, render kuyruğu)
│   └── ui/                    # Kullanıcı arayüzü bileşenleri
│       ├── dialogs/           # Araç kutusu, AI asistanı, imza, OCR ve ayarlar pencereleri
│       ├── popups/            # Yüzen HUD, renk seçici ve araç ayar baloncukları
│       ├── modern_views.py    # Acrobat tarzı modern sekme, başlık, çekmece ve çalışma alanları
│       ├── icons.py           # Vektörel QPainterPath AuraIconFactory fabrikası
│       ├── widgets.py         # Özelleştirilmiş araç çubukları ve kaydırma denetleyicileri
│       └── direct_text_editor.py # Doğrudan sayfa içi metin düzenleme motoru
├── Kurulum/                   # Derlenen resmi kurulum paketleri (Basic/ ve Pro/)
├── build_setup.py             # PyInstaller ve Inno Setup derleme otomasyonu
├── installer.iss              # Inno Setup Windows kurulum senaryosu
├── main.py                    # Uygulama ana giriş noktası ve IPC sunucusu
├── requirements.txt           # Python kütüphane bağımlılıkları
├── AGENTS.md                  # Proje kuralları, kalite standartları ve commit rehberi
└── README.md                  # Proje ana dokümantasyonu
```

---

## 🌿 Geliştirme İlkeleri ve Dal (Branch) Mimarisi

AuraPDF iki ana dal üzerinde sürdürülmektedir:
* **`aurapdf-basic-windows`:** Hafif, temel PDF okuma, not alma, sayfa düzenleme ve AcroForms doldurma odaklı tüketici sürümü.
* **`aurapdf_pro_windows` (Aktif Dal):** Gelişmiş yapay zeka analizi, kurumsal imza/kaşe, sandviç OCR ve tam araç kutusu paketini içeren profesyonel sürüm.

Tüm geliştirmeler [AGENTS.md](AGENTS.md) içerisinde tanımlanan mimari ilkeler, çoklu dil (i18n) eşitliği ve Conventional Commits standartlarına uygun olarak yürütülür.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak sunulmaktadır. Ticari ve kişisel ortamlarda özgürce kullanılabilir, geliştirilebilir ve dağıtılabilir.

<p align="center">
  <sub>AuraPDF Pro — Gelişmiş Masaüstü Belge Mühendisliği.</sub>
</p>
