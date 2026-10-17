# AuraPDF Thumbnail Renderer Helper

Bu yardımcı araç, Windows Dosya Gezgini'nde (Explorer) PDF dosyalarının ilk sayfasının küçük resim (thumbnail) önizlemesini yüksek çözünürlüklü ve kayıpsız olarak üretir.

Windows Shell Thumbnail Provider (`assets/PdfThumbnailProvider.dll`) tarafından izole bir alt işlem olarak çağrılır ve `filePath.replace(".pdf", ".bmp")` dosyasını oluşturur.

## Derleme Talimatı

```bash
dotnet publish PdfThumbnailRenderer.csproj -c Release -r win-x64 -o ../../assets
```

Çıktı dosyası `assets/PowerToys.PdfThumbnailProvider.exe` olarak kaydedilir ve Inno Setup / PyInstaller paketleme adımlarında otomatik olarak kurulum paketine dahil edilir.
