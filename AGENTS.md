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
  * Tüm simgeler `AuraIconFactory` (`src/ui/icons.py`) üzerinden `QPainterPath` / vektörel çizimle üretilmelidir.
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
Commit mesajları açık, anlaşılır ve Conventional Commits standardına uygun olmalıdır. Asla emoji içermemelidir. Yapay zeka araçları için `Co-Authored-By` satırı veya "Generated with" imzası eklenmemelidir; bu satırlar GitHub'da aracı katkıda bulunan olarak gösterir.

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
* **Sürüm Numarası:** Her sürüm güncellemesinde sürüm tam olarak `v0.0.1` artırılır (örn. `v2.2.5` → `v2.2.6`). Kullanıcı açıkça istemedikçe sürüm atlanmaz, orta veya büyük numara artırılmaz. Sürüm `src/core/updater.py`, `installer.iss` ve `README.md` içinde birlikte güncellenir.
* **Paketleme / Dağıtım:** `build_setup.py` çalıştırılarak aktif branch'e göre (`aurapdf-basic-windows` dalında `Kurulum\Basic\AuraPDF_Basic v<sürüm>.exe`, `aurapdf_pro_windows` dalında `Kurulum\Pro\AuraPDF_Pro v<sürüm>.exe`) kurulum paketi oluşturulur.

---

## 8. Kalite, Detay ve Telif Hakkı Standartları (Altın Kural)
* **En Güncel, Sorunsuz ve Detaylı Çözümler:**
  * Kullanıcının verdiği her talimatta geçici veya yüzeysel yamalar yerine; mimariyi, kullanıcı deneyimini (UX), kenar durumlarını (edge cases) ve işletim sistemi standartlarını bütünüyle kapsayan en detaylı ve en kusursuz çözüm üretilmelidir.
* **Telif Hakkı Güvencesi ve Özgünlük:**
  * İhtiyaç duyulduğunda en güncel teknik dokümantasyon, Qt standartları ve açık kaynak desenleri incelenebilir; ancak projeye eklenen tüm kod, algoritma ve tasarımlar kesinlikle telif hakkı ihlali içermeyen, bağımsız ve AuraPDF mimarisine özgü temiz çözümler olmalıdır.
* **Bütüncül Deneyim ve Eksiksiz Tamamlama:**
  * Fare etkileşimleri (boş alana tıklama ile seçimi temizleme, kutu ile çoklu seçim, sürükle-bırak yerleşim göstergeleri, interaktif tutamaçlar ve imleç değişimleri), klavye kısayolları, asenkron iş parçacıkları ve tema uyumu tam bir bütünlük içinde eksiksiz çalışmalıdır.

---

## 9. Korunan Çözümler ve Değişiklik Disiplini
Bu bölüm, bu projede çalışan tüm yapay zeka araçları (Claude, Codex, Gemini / Antigravity, Cursor, Copilot vb.) için geçerlidir. Amaç, bir aracın yaptığı düzeltmenin başka bir araç tarafından sessizce geri alınmasını önlemektir.

* **Değiştirmeden Önce Oku:**
  * Bir dosyayı değiştirmeden önce ilgili kod için `git log` geçmişine bakılmalı ve kodun neden öyle yazıldığı anlaşılmalıdır.
  * Hata düzeltme veya özellik işine başlarken `aurapdf-safe-change` skill'i (`.claude/skills/aurapdf-safe-change/SKILL.md`) izlenmelidir.
* **Kapsamı Dar Tut:**
  * Yalnızca istenen iş için gereken satırlar değiştirilmelidir. İstenmeden toplu biçimlendirme, yeniden adlandırma, taşıma veya yeniden yazma yapılmamalıdır.
  * Çalışan bir çözüm, daha "temiz" görünüyor diye değiştirilmemelidir.
* **Koruma Testlerine Dokunma:**
  * Kırılan bir koruma testi, kodda sorun olduğunu gösterir. Test gevşetilmemeli, silinmemeli veya atlanmamalıdır.
  * Bir testin gerçekten değişmesi gerekiyorsa önce gerekçesi kullanıcıya açıklanıp onay alınmalıdır.
* **Korunan Davranışı Değiştirme:**
  * Aşağıdaki tablodaki bir davranış, kullanıcı açıkça istemedikçe değiştirilmemelidir. Geri alma veya değiştirme gerekiyorsa önce kullanıcıya sorulmalıdır.
  * Her yeni kritik düzeltmede bu hatayı yakalayan test yazılmalı ve tabloya bir satır eklenmelidir.
* **Çalışma Ağaçlarına Saygı:**
  * Commit edilmemiş iş `git checkout`, `git restore`, `git reset --hard` veya `git clean` ile silinmemelidir.
  * Başka bir worktree'nin dosyaları düzenlenmemelidir. Aranan özellik bu dalda yoksa önce `git worktree list` ile diğer çalışma ağaçlarına bakılmalıdır.
* **Dürüst Raporlama:**
  * Test edilmeyen bir değişiklik "çalışıyor" diye raporlanmamalıdır. Çalıştırılamayan kontroller kullanıcıya açıkça bildirilmelidir.

### Korunan Çözümler Tablosu
| Davranış | Konum | Koruma |
| --- | --- | --- |
| İkon seti kartında ad üst satırda, ikonlar alt satırdadır; her genişlikte çakışmazlar. | `AuraIconSetGallery` (`src/ui/dialogs/settings_dialog.py`) | `tests/test_icon_sets.py` |
| Her ikon seti ayrı siluet üretir; galeri örnekleri birbirine benzemez ve kendi rengini korur. | `_ICON_SET_SHAPES`, `SAMPLES` | `tests/test_icon_sets.py` |
| İkon seti kodları (`modern`, `duotone`, `solid`, `badge`, `bold`, `sharp`, `classic`) saklı ayardır; görünen adlar yalnızca `i18n.py` içinden değişir. | `src/ui/icon_glyphs.py`, `src/core/i18n.py` | `tests/test_icon_sets.py` |
| Yeni sekmenin başlığı ilk açılıştan itibaren aktif temanın rengiyle çizilir. | `AuraTabItem` (`src/ui/aura_views.py`) | Görsel kontrol (offscreen test bu hatayı yakalamaz) |
| Sayfa stili penceresinde radyo düğmesi seçilince metni kırpılmaz; seçili ve seçili olmayan gösterge aynı boyuttadır. | `src/ui/dialogs/new_page_dialog.py` | `tests/test_ui_regressions.py` |
| PDF simgesi, Gezgin'in gerçekte kullandığı ProgID'ye (`AssocQueryString`, Windows 11'de `UserChoiceLatest`) göre belirlenir; AuraPDF varsayılan değilken ve kurulum kaydı yokken HKCU'ya ProgID yazılmaz; kaldırmada AuraPDF'i gösteren varsayılan uygulama seçimi silinir ve simge önbelleği yenilenir. | `src/core/shell_integration.py`, `installer.iss` | `tests/test_shell_integration.py` |
| Testler kullanıcının gerçek ayarlarını (kayıt defteri) okumaz veya değiştirmez; pytest, `QSettings`'i geçici INI'ye yönlendirir. | `tests/conftest.py` | `python -m pytest tests` sonrası ayarların aynı kalması |
| TR ve EN sözlükleri eştir; koddaki anahtarlar sözlükte vardır; arayüzde gömülü Türkçe metin yoktur. | `src/core/i18n.py` | `tests/test_static_guards.py` |
| Silinmiş modüllere import ve sınıf içinde tekrar eden metot bulunmaz. | `src/`, `main.py` | `tests/test_static_guards.py` |

### Proje Skill'leri
| Skill | Ne zaman |
| --- | --- |
| `aurapdf-safe-change` | Kod değiştiren her görevden önce |
| `aurapdf-icons` | İkon, ikon seti veya galeri çalışmalarında |
| `aurapdf-ui-verify` | Arayüz değişikliğini bitirmeden önce |

Skill dosyaları `.claude/skills/<ad>/SKILL.md` altındadır. Skill mekanizması olmayan araçlar bu dosyaları doğrudan okuyup adımlarını izlemelidir.
