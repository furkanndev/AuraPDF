using System;
using System.IO;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading.Tasks;
using Windows.Data.Pdf;
using Windows.Graphics.Imaging;
using Windows.Storage;
using Windows.Storage.Streams;

namespace AuraPDF.ThumbnailRenderer
{
    /// <summary>
    /// AuraPDF Windows Explorer Shell Thumbnail Helper.
    /// High-performance, isolated rendering process that converts page 0 of a PDF
    /// into a crisp BMP thumbnail for the Windows Shell Thumbnail Provider.
    /// If the PDF is encrypted/password-protected, generates an elegant locked document
    /// thumbnail with blurred background, a centered padlock badge, and the AuraPDF Pro logo.
    /// </summary>
    internal static class Program
    {
        [STAThread]
        public static async Task Main(string[] args)
        {
            try
            {
                File.AppendAllText(Path.Combine(Path.GetTempPath(), "pdf_thumb_log.txt"), $"{DateTime.Now}: args={string.Join(" ", args ?? Array.Empty<string>())}\n");
            }
            catch { }

            if (args == null || args.Length < 1)
            {
                return;
            }

            string pdfPath = Path.GetFullPath(args[0]);
            if (!File.Exists(pdfPath))
            {
                return;
            }

            uint cx = 256;
            if (args.Length >= 2 && uint.TryParse(args[1], out uint requestedCx) && requestedCx > 0)
            {
                cx = Math.Min(requestedCx, 2048);
            }

            bool isFileEncrypted = false;
            try
            {
                using var fsCheck = new FileStream(pdfPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                byte[] sample = new byte[Math.Min(fsCheck.Length, 131072)];
                int read = fsCheck.Read(sample, 0, sample.Length);
                string text = System.Text.Encoding.Latin1.GetString(sample, 0, read);
                if (text.Contains("/Encrypt"))
                {
                    isFileEncrypted = true;
                }
            }
            catch { }

            if (isFileEncrypted)
            {
                await RenderLockedPdfThumbnailAsync(pdfPath, cx);
                return;
            }

            try
            {
                var file = await StorageFile.GetFileFromPathAsync(pdfPath);
                var pdf = await PdfDocument.LoadFromFileAsync(file);

                if (pdf.IsPasswordProtected || pdf.PageCount == 0)
                {
                    await RenderLockedPdfThumbnailAsync(pdfPath, cx);
                    return;
                }

                // Render standard branded AuraPDF document thumbnail (consistent, non-preview branded icon as requested)
                await RenderStandardPdfThumbnailAsync(pdfPath, cx);
            }
            catch (Exception ex)
            {
                try
                {
                    if (isFileEncrypted)
                    {
                        await RenderLockedPdfThumbnailAsync(pdfPath, cx);
                    }
                    else
                    {
                        await RenderStandardPdfThumbnailAsync(pdfPath, cx);
                    }
                }
                catch { }
            }
        }

        private static async Task RenderStandardPdfThumbnailAsync(string pdfPath, uint cx)
        {
            uint size = Math.Clamp(cx, 32, 2048);
            byte[]? pixels = await LoadEmbeddedImagePixelsAsync("standard_pdf_thumbnail.png", size, size);
            if (pixels == null)
            {
                pixels = await LoadEmbeddedImagePixelsAsync("app_icon_128.png", size, size);
                if (pixels == null) return;
            }

            string outBmpPath = Path.ChangeExtension(pdfPath, ".bmp");
            WriteBmpFile(outBmpPath, pixels, size, size);
        }

        private static async Task RenderLockedPdfThumbnailAsync(string pdfPath, uint cx)
        {
            uint size = Math.Clamp(cx, 32, 2048);
            byte[]? pixels = await LoadEmbeddedImagePixelsAsync("locked_pdf_thumbnail.png", size, size);
            if (pixels == null)
            {
                pixels = await LoadEmbeddedImagePixelsAsync("app_icon_128.png", size, size);
                if (pixels == null) return;
            }

            string outBmpPath = Path.ChangeExtension(pdfPath, ".bmp");
            WriteBmpFile(outBmpPath, pixels, size, size);
        }

        private static async Task<byte[]?> LoadEmbeddedImagePixelsAsync(string resourceSubstr, uint targetW, uint targetH)
        {
            try
            {
                var asm = typeof(Program).Assembly;
                string? resName = null;
                foreach (var name in asm.GetManifestResourceNames())
                {
                    if (name.EndsWith(resourceSubstr, StringComparison.OrdinalIgnoreCase))
                    {
                        resName = name;
                        break;
                    }
                }
                if (resName == null) return null;

                using var s = asm.GetManifestResourceStream(resName);
                if (s == null) return null;

                using var mem = new MemoryStream();
                await s.CopyToAsync(mem);
                byte[] rawBytes = mem.ToArray();

                using var ras = new InMemoryRandomAccessStream();
                using var writer = new DataWriter(ras);
                writer.WriteBytes(rawBytes);
                await writer.StoreAsync();
                ras.Seek(0);

                var decoder = await BitmapDecoder.CreateAsync(ras);
                var transform = new BitmapTransform
                {
                    ScaledWidth = targetW,
                    ScaledHeight = targetH,
                    InterpolationMode = BitmapInterpolationMode.Fant
                };
                var pixelData = await decoder.GetPixelDataAsync(
                    BitmapPixelFormat.Bgra8,
                    BitmapAlphaMode.Premultiplied,
                    transform,
                    ExifOrientationMode.IgnoreExifOrientation,
                    ColorManagementMode.DoNotColorManage
                );
                return pixelData.DetachPixelData();
            }
            catch
            {
                return null;
            }
        }

        private static void WriteBmpFile(string outBmpPath, byte[] pixels, uint w, uint h)
        {
            uint rowStride = w * 4;
            uint imageSize = rowStride * h;
            uint fileSize = 54 + imageSize;

            using var fs = File.Create(outBmpPath);
            using var bw = new BinaryWriter(fs);

            // BITMAPFILEHEADER (14 bytes)
            bw.Write((ushort)0x4D42); // "BM"
            bw.Write(fileSize);
            bw.Write((ushort)0);
            bw.Write((ushort)0);
            bw.Write((uint)54); // Offset to image bits

            // BITMAPINFOHEADER (40 bytes - Bottom-up DIB)
            bw.Write((uint)40); // biSize
            bw.Write((int)w);   // biWidth
            bw.Write((int)h);   // biHeight (positive = bottom-up)
            bw.Write((ushort)1); // biPlanes
            bw.Write((ushort)32); // biBitCount (BGRA)
            bw.Write((uint)0);    // biCompression = BI_RGB
            bw.Write(imageSize);
            bw.Write((int)2835); // 72 DPI
            bw.Write((int)2835);
            bw.Write((uint)0);
            bw.Write((uint)0);

            // Write scanlines bottom-up
            for (int y = (int)h - 1; y >= 0; y--)
            {
                int offset = y * (int)rowStride;
                bw.Write(pixels, offset, (int)rowStride);
            }

            bw.Flush();
        }
    }
}
