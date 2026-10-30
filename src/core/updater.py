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
import urllib.parse
from datetime import datetime
from typing import Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal, QSettings

from src.core.i18n import LanguageManager

CURRENT_VERSION = "Pro v2.2.4"
GITHUB_REPO = "furkanndev/AuraPDF"


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Sürüm metnini (örn: 'v2.1.0', 'Pro v2.2.2' -> (2, 2, 2)) sayı demetine çevirir."""
    if not v_str:
        return (0, 0, 0)
    digits = [int(x) for x in re.findall(r'\d+', str(v_str))]
    while len(digits) < 3:
        digits.append(0)
    return tuple(digits[:3])



_TRANSLATION_CACHE = {}


def translate_changelog(text: str, target_lang: str = "en", source_lang: str = "tr") -> str:
    """Markdown sürüm notunu Google Translate uç noktası üzerinden çevirir."""
    if not text or not text.strip():
        return ""
    if target_lang == source_lang:
        return text

    cache_key = f"{source_lang}_{target_lang}_{hash(text)}"
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    try:
        url = (
            f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q="
            + urllib.parse.quote(text)
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([item[0] for item in data[0] if item and item[0]])
            if translated and translated.strip():
                _TRANSLATION_CACHE[cache_key] = translated
                return translated
    except Exception:
        pass
    return text


def parse_release_notes_by_language(raw_body: str) -> Tuple[str, str]:
    """
    GitHub Release açıklamasını (raw_body) inceler ve (notes_tr, notes_en) demeti döndürür.
    Desteklenen yapı:
      1) <!-- lang:tr --> / <!-- lang:en --> etiket blokları
      2) ## [TR], ## [EN], ## Türkçe, ## English başlıkları
      3) '---' ayırıcı ile iki dilli yapı
      4) Yalnızca tek dil varsa eksik olanı otomatik çevirme desteği
    """
    if not raw_body or not raw_body.strip():
        return "", ""

    body = raw_body.strip()

    # 1. HTML Comment etiketleri <!-- lang:tr --> ... <!-- /lang:tr -->
    tr_match = re.search(r'<!--\s*(?:lang:)?tr\s*-->(.*?)<!--\s*/(?:lang:)?tr\s*-->', body, re.DOTALL | re.IGNORECASE)
    en_match = re.search(r'<!--\s*(?:lang:)?en\s*-->(.*?)<!--\s*/(?:lang:)?en\s*-->', body, re.DOTALL | re.IGNORECASE)

    notes_tr = tr_match.group(1).strip() if tr_match else ""
    notes_en = en_match.group(1).strip() if en_match else ""

    # 2. Markdown başlıkları [TR] / [EN] veya Türkçe / English
    if not notes_tr or not notes_en:
        tr_head = re.search(r'(?:^|\n)(#{1,3}\s*(?:\[TR\]|\(TR\)|TR\b|Türkçe)[^\n]*)', body, re.IGNORECASE)
        en_head = re.search(r'(?:^|\n)(#{1,3}\s*(?:\[EN\]|\(EN\)|EN\b|English)[^\n]*)', body, re.IGNORECASE)

        if tr_head and en_head:
            if tr_head.start() < en_head.start():
                cand_tr = body[tr_head.start():en_head.start()].strip()
                cand_en = body[en_head.start():].strip()
            else:
                cand_en = body[en_head.start():tr_head.start()].strip()
                cand_tr = body[tr_head.start():].strip()
            cand_tr = re.sub(r'\n---+\s*$', '', cand_tr).strip()
            cand_en = re.sub(r'\n---+\s*$', '', cand_en).strip()
            if not notes_tr:
                notes_tr = cand_tr
            if not notes_en:
                notes_en = cand_en

    # 3. İki bölümlü '---' ayrımı
    if (not notes_tr or not notes_en) and "---" in body:
        parts = [p.strip() for p in body.split("---") if p.strip()]
        if len(parts) >= 2:
            p0, p1 = parts[0], parts[1]
            p0_has_tr = any(w in p0.lower() for w in ["güncelleme", "düzeltme", "iyileştir", "yeni", "özellik", "hata"])
            p1_has_en = any(w in p1.lower() for w in ["update", "fix", "improve", "feature", "change", "download"])
            if p0_has_tr and p1_has_en:
                if not notes_tr: notes_tr = p0
                if not notes_en: notes_en = p1

    # 4. Yalnızca tek dil varsa otomatik çeviri tamamlama
    if not notes_tr and not notes_en:
        has_tr_chars = any(c in body for c in "şŞğĞıİçÇöÖüÜ")
        has_tr_words = any(w in body.lower() for w in ["güncelleme", "yenilikler", "iyileştirme", "düzeltildi", "indir"])
        if has_tr_chars or has_tr_words:
            notes_tr = body
            notes_en = translate_changelog(body, target_lang="en", source_lang="tr")
        else:
            notes_en = body
            notes_tr = translate_changelog(body, target_lang="tr", source_lang="en")
    elif notes_tr and not notes_en:
        notes_en = translate_changelog(notes_tr, target_lang="en", source_lang="tr")
    elif notes_en and not notes_tr:
        notes_tr = translate_changelog(notes_en, target_lang="tr", source_lang="en")

    return notes_tr, notes_en
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
                 error_message: Optional[str] = None,
                 notes_tr: str = "",
                 notes_en: str = "",
                 raw_body: str = ""):
        self.has_update = has_update
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_name = release_name
        self.release_notes = release_notes
        self.notes_tr = notes_tr
        self.notes_en = notes_en
        self.raw_body = raw_body
        self.html_url = html_url
        self.download_url = download_url
        self.asset_name = asset_name
        self.asset_size = asset_size
        self.published_at = published_at
        self.error_message = error_message

    def get_release_notes(self, lang: Optional[str] = None) -> str:
        """Dile duyarlı sürüm notunu döndürür ('en' veya 'tr')."""
        if not lang:
            try:
                lang = LanguageManager.get_language()
            except Exception:
                lang = "tr"
        if lang == "en":
            return self.notes_en or self.release_notes or self.notes_tr or ""
        return self.notes_tr or self.release_notes or self.notes_en or ""

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

        # 1. Releases listesini sorgula (Pro / Basic ayrımı ve doğru sürüm eşleşmesi için)
        is_basic = "basic" in str(CURRENT_VERSION).lower()
        api_url = f"https://api.github.com/repos/{self.repo}/releases"
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    releases_list = json.loads(resp.read().decode('utf-8'))
                    if releases_list and isinstance(releases_list, list):
                        for r in releases_list:
                            t_name = str(r.get("tag_name", "")).lower()
                            r_name = str(r.get("name", "")).lower()
                            if is_basic:
                                if "basic" in t_name or "basit" in t_name or "basic" in r_name:
                                    release_data = r
                                    break
                            else:
                                if "pro" in t_name or "pro" in r_name or ("basic" not in t_name and "basit" not in t_name and "basic" not in r_name):
                                    release_data = r
                                    break
                        if not release_data and releases_list:
                            release_data = releases_list[0]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                err_api = LanguageManager.tr("updates_err_api", code=e.code, reason=e.reason)
                self.check_failed.emit(err_api)
                return
        except Exception:
            pass

        # 2. Releases listesinden bulunamadıysa doğrudan 'latest' sorgula
        if not release_data:
            try:
                latest_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
                req_lat = urllib.request.Request(latest_url, headers=headers)
                with urllib.request.urlopen(req_lat, timeout=10) as resp_lat:
                    if resp_lat.status == 200:
                        release_data = json.loads(resp_lat.read().decode('utf-8'))
            except Exception:
                pass

        # 3. Eğer releases boşsa etiketleri (tags) sorgula
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
                            tag_msg = LanguageManager.tr("updates_tag_released")
                            info = UpdateInfo(
                                has_update=has_up,
                                current_version=CURRENT_VERSION,
                                latest_version=latest_tag,
                                release_name=f"AuraPDF {latest_tag}",
                                release_notes=tag_msg,
                                notes_tr=LanguageManager.TRANSLATIONS.get("tr", {}).get("updates_tag_released", tag_msg),
                                notes_en=LanguageManager.TRANSLATIONS.get("en", {}).get("updates_tag_released", tag_msg),
                                raw_body=tag_msg,
                                html_url=f"https://github.com/{self.repo}/releases/tag/{latest_tag}"
                            )
                            self._save_last_check_timestamp()
                            self.check_finished.emit(info)
                            return
            except Exception:
                pass

        if not release_data:
            err_no_ver = LanguageManager.tr("updates_err_no_version_info")
            self.check_finished.emit(UpdateInfo(error_message=err_no_ver))
            return

        # Sürüm verilerini çözümle
        tag_name = release_data.get("tag_name", "")
        default_rel_name = LanguageManager.tr("updates_new_version_title")
        release_name = release_data.get("name") or tag_name or default_rel_name
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
        clean_digits = re.findall(r'\d+(?:\.\d+)*', tag_name)
        ver_num = clean_digits[0] if clean_digits else tag_name
        latest_ver_clean = f"v{ver_num}" if not ver_num.startswith("v") else ver_num
        latest_parsed = parse_version(ver_num)
        current_parsed = parse_version(CURRENT_VERSION)
        has_update = latest_parsed > current_parsed

        # Sürüm notlarını çok dilli (TR / EN) ayrıştır
        notes_tr, notes_en = parse_release_notes_by_language(body)
        cur_lang = LanguageManager.get_language()
        active_notes = notes_en if cur_lang == "en" else notes_tr
        if not active_notes:
            active_notes = body

        info = UpdateInfo(
            has_update=has_update,
            current_version=CURRENT_VERSION,
            latest_version=latest_ver_clean or CURRENT_VERSION,
            release_name=release_name,
            release_notes=active_notes,
            notes_tr=notes_tr,
            notes_en=notes_en,
            raw_body=body,
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
