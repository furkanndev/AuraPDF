using System;
using System.IO;
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
    /// </summary>
    internal static class Program
    {
        [STAThread]
        public static async Task Main(string[] args)
        {
            if (args == null || args.Length < 1)
            {
                return;
            }

            try
            {
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

                var file = await StorageFile.GetFileFromPathAsync(pdfPath);
                var pdf = await PdfDocument.LoadFromFileAsync(file);

                if (pdf.PageCount == 0)
                {
                    return;
                }

                using var page = pdf.GetPage(0);

                double pageWidth = page.Size.Width;
                double pageHeight = page.Size.Height;
                if (pageWidth <= 0 || pageHeight <= 0)
                {
                    pageWidth = 612;
                    pageHeight = 792;
                }

                uint targetWidth;
                uint targetHeight;

                if (pageWidth >= pageHeight)
                {
                    targetWidth = cx;
                    targetHeight = (uint)Math.Max(1, Math.Round(pageHeight * cx / pageWidth));
                }
                else
                {
                    targetHeight = cx;
                    targetWidth = (uint)Math.Max(1, Math.Round(pageWidth * cx / pageHeight));
                }

                using var pngStream = new InMemoryRandomAccessStream();
                var renderOptions = new PdfPageRenderOptions
                {
                    DestinationWidth = targetWidth,
                    DestinationHeight = targetHeight
                };

                await page.RenderToStreamAsync(pngStream, renderOptions);
                pngStream.Seek(0);

                var decoder = await BitmapDecoder.CreateAsync(pngStream);
                var pixelData = await decoder.GetPixelDataAsync(
                    BitmapPixelFormat.Bgra8,
                    BitmapAlphaMode.Premultiplied,
                    new BitmapTransform(),
                    ExifOrientationMode.IgnoreExifOrientation,
                    ColorManagementMode.DoNotColorManage
                );
                byte[] pixels = pixelData.DetachPixelData();

                uint w = decoder.PixelWidth;
                uint h = decoder.PixelHeight;

                // Composite transparent pixels over a white paper background
                for (int i = 0; i < pixels.Length; i += 4)
                {
                    byte a = pixels[i + 3];
                    if (a < 255)
                    {
                        byte b = pixels[i];
                        byte g = pixels[i + 1];
                        byte r = pixels[i + 2];
                        pixels[i] = (byte)((b * a + 255 * (255 - a)) / 255);
                        pixels[i + 1] = (byte)((g * a + 255 * (255 - a)) / 255);
                        pixels[i + 2] = (byte)((r * a + 255 * (255 - a)) / 255);
                        pixels[i + 3] = 255;
                    }
                }

                uint rowStride = w * 4;
                uint imageSize = rowStride * h;
                uint fileSize = 54 + imageSize;

                string outBmpPath = Path.ChangeExtension(pdfPath, ".bmp");
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
            catch
            {
                // Silent fail for shell extension
            }
        }
    }
}
