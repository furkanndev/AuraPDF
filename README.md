# AuraPDF 📄✨

<p align="center">
  <img src="assets/app_icon_128.png" alt="AuraPDF Logo" width="128" height="128" />
</p>

<p align="center">
  <strong>Modern, Hızlı ve Güçlü PDF Görüntüleyici & Düzenleyici</strong><br>
  <em>Python, PyQt6 ve PyMuPDF ile geliştirilmiş zengin özellikli masaüstü PDF aracı.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-PyQt6-green?style=flat-square&logo=qt" alt="PyQt6" />
  <img src="https://img.shields.io/badge/Engine-PyMuPDF-orange?style=flat-square" alt="PyMuPDF" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-purple?style=flat-square" alt="License" />
</p>

---

## 🚀 Özellikler

### 📑 Belge Yönetimi ve Görüntüleme
- **Sekmeli Arayüz (Tabbed Interface):** Birden fazla PDF belgesini tek pencerede kolayca açın ve yönetin.
- **Akıcı Gezinme:** Sayfa küçük resimleri (Thumbnails dock), yakınlaştırma, döndürme ve tam ekran okuma modları.
- **Çoklu Dil Desteği:** Türkçe ve İngilizce dil desteği.
- **Modern Temalar:** Göz yormayan koyu ve açık tema seçenekleri.

### ✏️ Not Alma & Çizim Araçları
- **Serbest Çizim & Vurgulayıcı:** Ayarlanabilir fırça boyutu, opaklık ve zengin renk paleti.
- **Geometrik Şekiller:** Düz çizgi, dikdörtgen, elips, ok ve çokgen çizim araçları.
- **Metin Ekleme:** Belge üzerine serbest veya biçimlendirilmiş metin kutuları yerleştirme.
- **Damga, Çıkartma & Medya:** Özel damgalar, emojiler, çıkartmalar ve animasyonlu GIF desteği.

### 🛠️ Gelişmiş PDF Araç Kutusu (Toolbox)
- **Sayfa Düzenleme & Birleştirme:**
  - PDF Birleştirme (Merge) ve Sayfa Ayırma (Split)
  - Sayfa Silme, Döndürme, Yeniden Sıralama ve Boş Sayfa Ekleme
  - Sayfa Numaralandırma (Konum, format ve stil seçenekleriyle)
- **Format Dönüştürme:**
  - PDF ➔ Word (`.docx`)
  - PDF ➔ PowerPoint (`.pptx`)
  - PDF ➔ Excel (`.xlsx`)
  - PDF ➔ E-Kitap (`.epub`, `.mobi`)
- **Güvenlik & Gizlilik:**
  - PDF Şifreleme ve Parola Koruma
  - Hassas Bilgileri Kalıcı Sansürleme / Karartma (Redaction)
  - Dijital / Görsel İmza Ekleme
- **OCR & İçerik:**
  - Dahili Hızlı Metin Tanıma (RapidOCR / ONNX)
  - PDF Belgelerini Karşılaştırma (Diff / Compare)
  - Filigran (Watermark) ve Özel Arka Plan Ekleme

---

## 💻 Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.10 veya üzeri
- Windows 10 / 11

### Adım Adım Kurulum

1. **Depoyu klonlayın:**
   ```bash
   git clone https://github.com/furkanndev/AuraPDF.git
   cd AuraPDF
   ```

2. **Sanal ortam oluşturun ve aktif edin (Önerilen):**
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. **Gerekli paketleri yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı başlatın:**
   ```bash
   python main.py
   ```

---

## 📦 Dağıtım & Kurulum Paketi (Installer) Oluşturma

AuraPDF'i tek tıkla kurulabilir bir Windows kurulum dosyasına (`Setup.exe`) dönüştürmek için:

1. [Inno Setup 6](https://jrsoftware.org/isinfo.php)'nın sisteminizde kurulu olduğundan emin olun.
2. Proje kök dizinindeki derleme script'ini çalıştırın:
   ```bash
   python build_setup.py
   ```
3. Derleme tamamlandığında kurulum dosyası `Kurulum/AuraPDF_Setup.exe` altında hazır olacaktır.

---

## 📁 Proje Mimarisi

```
AuraPDF/
├── assets/                 # Logo, ikon ve medya bileşenleri
├── src/
│   ├── core/              # Çekirdek yardımcılar (i18n, kısayollar, köprü algılama)
│   ├── document/          # Sekme ve belge yönetimi (tab_document, media_items)
│   ├── ui/                # Kullanıcı arayüzü bileşenleri
│   │   ├── dialogs/       # Araç kutusu, ayarlar ve dönüşüm pencereleri
│   │   ├── widgets.py     # Özelleştirilmiş widget'lar ve araç çubukları
│   │   ├── popups.py      # Araç ayar açılır pencereleri
│   │   └── icons.py       # Vektörel ve dinamik ikon üretim fabrikası
│   └── viewer.py          # Ana uygulama penceresi ve görüntüleyici mantığı
├── build_setup.py         # PyInstaller ve Inno Setup derleme scripti
├── installer.iss          # Inno Setup kurulum betiği
├── main.py                # Giriş noktası (Application Entrypoint)
├── requirements.txt       # Python bağımlılıkları
└── README.md
```

---

## 📄 Lisans

Bu proje MIT lisansı ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına göz atabilirsiniz.
