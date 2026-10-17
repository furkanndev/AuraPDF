"""
AuraPDF - Otomatik Güncelleme Yöneticisi (Auto-Updater)
======================================================
GitHub Releases API üzerinden en güncel sürümü denetleyen,
sürüm notlarını getiren ve yeni kurulum paketini arka planda
indirebilen thread-tabanlı modül.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal, QSettings

CURRENT_VERSION = "Pro v2.2.3"
GITHUB_REPO = "furkanndev/AuraPDF"


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Sürüm metnini (örn: 'v2.1.0', 'Pro v2.2.2' -> (2, 2, 2)) sayı demetine çevirir."""
    if not v_str:
        return (0, 0, 0)
    digits = [int(x) for x in re.findall(r'\d+', str(v_str))]
    while len(digits) < 3:
        digits.append(0)
    return tuple(digits[:3])


class UpdateInfo:
    """Güncelleme denetimi sonucunu taşıyan veri yapısı."""
    def __init__(self,
                 has_update: bool = False,
                 current_version: str = CURRENT_VERSION,
                 latest_version: str = CURRENT_VERSION,
                 release_name: str = "",
                 release_notes: str = "",
                 html_url: str = "",
                 download_url: Optional[str] = None,
                 asset_name: Optional[str] = None,
                 asset_size: int = 0,
                 published_at: str = "",
                 error_message: Optional[str] = None):
        self.has_update = has_update
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_name = release_name
        self.release_notes = release_notes
        self.html_url = html_url
        self.download_url = download_url
        self.asset_name = asset_name
        self.asset_size = asset_size
        self.published_at = published_at
        self.error_message = error_message

    @property
    def formatted_size(self) -> str:
        if self.asset_size <= 0:
            return ""
        mb = self.asset_size / (1024 * 1024)
        return f"{mb:.1f} MB"


class UpdateChecker(QThread):
    """GitHub API üzerinden yeni sürümü arka planda sorgulayan iş parçacığı."""
    check_finished = pyqtSignal(object)  # UpdateInfo
    check_failed = pyqtSignal(str)

    def __init__(self, repo: str = GITHUB_REPO, custom_token: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.custom_token = custom_token

    def run(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        token = self.custom_token or settings.value("github_token", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()

        headers = {
            "User-Agent": "AuraPDF-Desktop-App",
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        release_data = None
        html_release_url = f"https://github.com/{self.repo}/releases"

        # 1. En son resmi sürümü (latest release) sorgula
        api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    release_data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # 'latest' bulunamadıysa (örneğin sadece draft veya prerelease varsa veya henüz releases/latest oluşturulmadıysa),
                # tüm releases listesini veya tags listesini dene
                try:
                    all_rel_url = f"https://api.github.com/repos/{self.repo}/releases"
                    req2 = urllib.request.Request(all_rel_url, headers=headers)
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        releases_list = json.loads(resp2.read().decode('utf-8'))
                        if releases_list and isinstance(releases_list, list):
                            release_data = releases_list[0]
                except Exception:
                    pass

                # Eğer releases boşsa etiketleri (tags) sorgula
                if not release_data:
                    try:
                        tags_url = f"https://api.github.com/repos/{self.repo}/tags"
                        req3 = urllib.request.Request(tags_url, headers=headers)
                        with urllib.request.urlopen(req3, timeout=10) as resp3:
                            tags_list = json.loads(resp3.read().decode('utf-8'))
                            if tags_list and isinstance(tags_list, list):
                                latest_tag = tags_list[0].get("name", "")
                                if latest_tag:
                                    tag_parsed = parse_version(latest_tag)
                                    curr_parsed = parse_version(CURRENT_VERSION)
                                    has_up = tag_parsed > curr_parsed
                                    info = UpdateInfo(
                                        has_update=has_up,
                                        current_version=CURRENT_VERSION,
                                        latest_version=latest_tag,
                                        release_name=f"AuraPDF {latest_tag}",
                                        release_notes="GitHub üzerinden yeni bir etiket yayınlandı.",
                                        html_url=f"https://github.com/{self.repo}/releases/tag/{latest_tag}"
                                    )
                                    self._save_last_check_timestamp()
                                    self.check_finished.emit(info)
                                    return
                    except Exception:
                        pass

                if not release_data:
                    err_msg = (
                        "Depo henüz herkese açık (Public) bir Release içermiyor veya "
                        "özel (Private) bir depoysa Ayarlar'dan GitHub Token girilmesi gerekiyor."
                    )
                    self._save_last_check_timestamp()
                    self.check_finished.emit(UpdateInfo(error_message=err_msg))
                    return
            else:
                self.check_failed.emit(f"GitHub API Hatası ({e.code}): {e.reason}")
                return
        except Exception as e:
            self.check_failed.emit(f"Bağlantı hatası: {str(e)}")
            return

        if not release_data:
            self.check_finished.emit(UpdateInfo(error_message="Sürüm bilgisi alınamadı."))
            return

        # Sürüm verilerini çözümle
        tag_name = release_data.get("tag_name", "")
        release_name = release_data.get("name") or tag_name or "Yeni Sürüm"
        body = release_data.get("body", "")
        html_url = release_data.get("html_url") or html_release_url
        published_at = release_data.get("published_at", "")

        if published_at:
            try:
                # 2026-09-29T18:00:00Z -> 29.09.2026 18:00
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                published_at = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                pass

        # İndirilebilir kurulum dosyası (.exe) var mı kontrol et
        download_url = None
        asset_name = None
        asset_size = 0
        assets = release_data.get("assets", [])
        for a in assets:
            name = a.get("name", "")
            if name.lower().endswith(".exe"):
                download_url = a.get("browser_download_url")
                asset_name = name
                asset_size = a.get("size", 0)
                break

        # Sürüm karşılaştırması
        latest_ver_clean = re.sub(r'^[vV]', '', tag_name.strip())
        latest_parsed = parse_version(latest_ver_clean)
        current_parsed = parse_version(CURRENT_VERSION)
        has_update = latest_parsed > current_parsed

        info = UpdateInfo(
            has_update=has_update,
            current_version=CURRENT_VERSION,
            latest_version=latest_ver_clean or CURRENT_VERSION,
            release_name=release_name,
            release_notes=body,
            html_url=html_url,
            download_url=download_url,
            asset_name=asset_name,
            asset_size=asset_size,
            published_at=published_at
        )

        self._save_last_check_timestamp()
        self.check_finished.emit(info)

    def _save_last_check_timestamp(self):
        settings = QSettings("AuraPDF", "PDFViewer")
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        settings.setValue("last_update_check_time", now_str)
        settings.setValue("last_update_check_epoch", int(datetime.now().timestamp()))


class UpdateDownloader(QThread):
    """Kurulum dosyasını indiren ve ilerlemeyi bildiren iş parçacığı."""
    progress = pyqtSignal(int, int)          # indirilen bayt, toplam bayt
    download_finished = pyqtSignal(str)     # indirilen dosyanın yerel yolu
    download_failed = pyqtSignal(str)       # hata mesajı

    def __init__(self, download_url: str, filename: str = "AuraPDF_Setup.exe", parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.filename = filename
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            import tempfile
            dest_dir = os.path.join(tempfile.gettempdir(), "AuraPDF_Update")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, self.filename)

            headers = {
                "User-Agent": "AuraPDF-Desktop-App",
                "Accept": "application/octet-stream"
            }
            req = urllib.request.Request(self.download_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024  # 64 KB

                while True:
                    if self._is_cancelled:
                        out_file.close()
                        try:
                            os.remove(dest_path)
                        except Exception:
                            pass
                        self.download_failed.emit("İndirme kullanıcı tarafından iptal edildi.")
                        return

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total_size)

            self.download_finished.emit(dest_path)
        except Exception as e:
            self.download_failed.emit(f"İndirme hatası: {str(e)}")


def launch_installer(installer_path: str):
    """İndirilen kurulum dosyasını başlatır ve mevcut uygulamayı sonlandırır."""
    import subprocess
    if not os.path.isfile(installer_path):
        return False
    try:
        subprocess.Popen([installer_path], shell=True)
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.quit()
        return True
    except Exception as e:
        print(f"[HATA] Kurulum başlatılamadı: {e}")
        return False
