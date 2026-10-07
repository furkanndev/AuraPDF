"""
AuraPDF Speech Engine (Metin Seslendirme / Read Aloud)
=====================================================
EMA Lightning (canberk7/ema-lightning) tabanlı, 8.6M parametreli,
ultra hızlı ve doğal Türkçe yapay zeka ses motoru.
Tamamen yerel ve çevrimdışı (offline) çalışır, internet gerektirmez.

Optimizasyonlar:
- Otomatik model önbellekleme (Tekil model örneği, her seferinde diskten yükleme yapmaz)
- Markdown, yıldız (*, **), madde işaretleri ve görsel sembollerin temizlenmesi
- Cümle tabanlı akış (Pipelined streaming): İlk cümle ~0.3 saniyede çalmaya başlar,
  arka planda kalan cümleler önbelleğe alınır.
- Windows dosya kilitleme (WinError 32) ve QMediaPlayer çakışmalarının önlenmesi
"""

import os
import sys
import re
import time
import glob
import tempfile
import threading
from typing import Optional, List, Dict, Tuple
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Çevrimdışı modu ortam değişkeninde güvenceye al
os.environ["HF_HUB_OFFLINE"] = "1"

# Global Model Önbelleği (Singleton)
_EMA_MODEL = None
_EMA_LOCK = threading.Lock()


def is_ema_installed() -> bool:
    try:
        import ema_lightning  # noqa: F401
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def is_ema_model_cached() -> bool:
    if not is_ema_installed():
        return False
    try:
        from huggingface_hub import try_to_load_from_cache
        REPO = "canberkkkkkk/ema-lightning"
        p1 = try_to_load_from_cache(REPO, "ema.pt")
        p2 = try_to_load_from_cache(REPO, "decoder.pt")
        return bool(p1 and p2 and os.path.exists(str(p1)) and os.path.exists(str(p2)))
    except Exception:
        cache_dir = os.path.expanduser("~/.cache/huggingface/hub/models--canberkkkkkk--ema-lightning")
        return os.path.exists(cache_dir)


def get_cached_ema_model():
    """EMA Lightning modelini bir kez belleğe yükler ve tekrar tekrar kullanır (Hızlandırıcı)."""
    global _EMA_MODEL
    with _EMA_LOCK:
        if _EMA_MODEL is None:
            os.environ["HF_HUB_OFFLINE"] = "1"
            import torch
            try:
                # CPU iş parçacığı optimizasyonu
                cpu_cnt = os.cpu_count() or 4
                torch.set_num_threads(max(1, min(8, cpu_cnt)))
            except Exception:
                pass
            from ema_lightning import EMA
            _EMA_MODEL = EMA()
        return _EMA_MODEL


def clean_text_for_speech(text: str) -> str:
    """
    Ses motoru için metni temizler:
    - Yıldız şekillerini (*, **, ***) kaldırır (TTS'in 'yıldız' kelimesini okumasını önler).
    - Madde işaretleri (•, ·, ■, ➢, vb.) ve dekoratif sembolleri temizler.
    - Markdown etiketlerini (başlıklar, bağlantılar, kod blokları) temizler.
    - Dipnot köşeli parantezlerini ([1], [12]) kaldırır.
    - Noktalama ve boşlukları doğal akışa uyarlar.
    """
    if not text:
        return ""

    # 1. Markdown kalın/italik yıldızlarını kaldır: **metin** -> metin, *metin* -> metin
    text = re.sub(r'\*{1,4}(.*?)\*{1,4}', r'\1', text)
    # Kalan tekil yıldız ve benzeri şekilleri tamamen temizle
    text = re.sub(r'[\*\★\☆\✦\✧\✪\✫\✬\✭\✮\✯\✰]', ' ', text)

    # 2. Markdown başlıkları, bağlantıları ve kodları
    text = re.sub(r'#+\s*', '', text)                     # ### Başlık -> Başlık
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text) # [link](url) -> link
    text = re.sub(r'\[\s*\d+\s*\]', '', text)              # [1], [23] dipnotları
    text = re.sub(r'`+([^`]+)`+', r'\1', text)            # `kod` -> kod
    text = re.sub(r'~~([^~]+)~~', r'\1', text)            # ~~üstü çizili~~ -> üstü çizili

    # 3. Madde imi ve liste sembolleri
    text = re.sub(r'[•·⁃■□➢➤○●✓✔►◄◆◇▲▼△▽▸▹▪▫\-\–\—]{1,2}\s+', ' ', text)
    text = re.sub(r'[•·⁃■□➢➤○●✓✔►◄◆◇▲▼△▽▸▹▪▫]', ' ', text)

    # 4. Uzun ayırıcı çizgiler (----, ====, ____)
    text = re.sub(r'[-=_~]{2,}', ' ', text)

    # 5. Tekrarlayan noktalar (...) ve fazla noktalama
    text = re.sub(r'\.{3,}', '.', text)

    # 6. Fazla boşlukları ve kırık satırları birleştir
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned = ' '.join(lines)
    cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def split_into_speech_chunks(text: str, max_words_per_chunk: int = 25) -> List[str]:
    """
    Metni doğal cümle sınırlarından akıcı ses parçalarına böler.
    Bu sayede ilk parça ~0.3 saniyede çalmaya başlar (sıfır gecikme hissi).
    """
    clean = clean_text_for_speech(text)
    if not clean:
        return []

    # Cümle sonlarına göre ayır (. ! ?)
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    if not raw_sentences:
        raw_sentences = [clean]

    chunks = []
    current_chunk = []
    current_word_count = 0

    for sent in raw_sentences:
        words = sent.split()
        if not words:
            continue

        if current_word_count + len(words) <= max_words_per_chunk or not current_chunk:
            current_chunk.append(sent)
            current_word_count += len(words)
        else:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sent]
            current_word_count = len(words)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks if chunks else [clean]


class EmaSynthesisWorker(QThread):
    """
    Arka planda EMA Lightning ile ses sentezi üreten optimize edilmiş iş parçacığı.
    Cümle cümle sentezler ve her parça hazır olduğunda `chunk_ready` sinyali yayar.
    """
    synthesis_started = pyqtSignal()
    chunk_ready = pyqtSignal(int, int, str, float, str)  # index, total, wav_path, duration_sec, text
    synthesis_finished = pyqtSignal(int)                 # total_chunks
    synthesis_error = pyqtSignal(str)

    def __init__(self, text: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.text = text
        self._is_cancelled = False
        self.temp_dir = tempfile.gettempdir()

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        cleaned_text = clean_text_for_speech(self.text)
        if not cleaned_text:
            self.synthesis_error.emit("Seslendirilecek okunabilir metin bulunamadı.")
            return

        chunks = split_into_speech_chunks(cleaned_text)
        total_chunks = len(chunks)
        if total_chunks == 0:
            self.synthesis_error.emit("Seslendirilecek metin bulunamadı.")
            return

        self.synthesis_started.emit()

        try:
            import torch
            tts = get_cached_ema_model()
            pid = os.getpid()

            for idx, chunk in enumerate(chunks):
                if self._is_cancelled:
                    return

                # Benzersiz dosya adı oluşturarak Windows dosya kilitleme hatasını engelle
                timestamp = time.time_ns()
                wav_path = os.path.join(self.temp_dir, f"aurapdf_speech_{pid}_{timestamp}_{idx}.wav")

                with torch.inference_mode():
                    speech = tts.say(chunk.strip(), path=wav_path)

                if self._is_cancelled:
                    try:
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                    except Exception:
                        pass
                    return

                duration = float(getattr(speech, "duration", 0.0))
                self.chunk_ready.emit(idx, total_chunks, wav_path, duration, chunk)

            self.synthesis_finished.emit(total_chunks)

        except Exception as e:
            if not self._is_cancelled:
                self.synthesis_error.emit(str(e))


class EmaDownloadWorker(QThread):
    """EMA Lightning model ağırlıklarını (~34 MB) yerel önbelleğe indiren iş parçacığı."""
    download_started = pyqtSignal()
    download_finished = pyqtSignal(bool, str)

    def run(self):
        self.download_started.emit()
        try:
            if "HF_HUB_OFFLINE" in os.environ:
                del os.environ["HF_HUB_OFFLINE"]
            from ema_lightning import EMA
            _ = EMA()
            os.environ["HF_HUB_OFFLINE"] = "1"
            self.download_finished.emit(True, "Model başarıyla yerel olarak indirildi ve hazırlandı.")
        except Exception as e:
            os.environ["HF_HUB_OFFLINE"] = "1"
            self.download_finished.emit(False, str(e))


class AuraSpeechEngine(QObject):
    """
    AuraPDF ana konuşma ve seslendirme yöneticisi.
    Pipelined / streaming ses kuyruğu yönetimi ile anında ses başlatır ve kesintisiz çalar.
    """
    state_changed = pyqtSignal(bool)           # is_speaking
    reading_started = pyqtSignal(str)          # snippet
    reading_finished = pyqtSignal()
    playback_progress = pyqtSignal(int, int)   # current_ms, total_ms
    error_occurred = pyqtSignal(str)
    model_status_changed = pyqtSignal(bool, str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_text = ""
        self._worker: Optional[EmaSynthesisWorker] = None
        self._download_worker: Optional[EmaDownloadWorker] = None

        # Ses Oynatıcı (QMediaPlayer + QAudioOutput)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # Akış ve Kuyruk Yönetimi
        self._queue: List[Tuple[str, float, str]] = []  # (wav_path, duration_sec, text)
        self._active_wav_path: Optional[str] = None
        self._played_wav_paths: List[str] = []
        self._total_chunks = 0
        self._current_chunk_idx = 0
        self._accumulated_played_ms = 0
        self._current_chunk_dur_ms = 0
        self._estimated_total_ms = 0
        self._is_paused = False
        self._is_synthesizing_done = False

    def is_model_ready(self) -> bool:
        return is_ema_installed() and is_ema_model_cached()

    def is_speaking(self) -> bool:
        return (
            (self._worker is not None and self._worker.isRunning()) or
            (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState) or
            len(self._queue) > 0
        )

    def is_paused(self) -> bool:
        return self._is_paused or self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState

    def check_and_notify_status(self):
        ready = self.is_model_ready()
        msg = "Hazır (Yerel Model Yüklü)" if ready else "Model yerel olarak henüz indirilmedi"
        self.model_status_changed.emit(ready, msg)

    def download_model(self):
        if self._download_worker and self._download_worker.isRunning():
            return
        self._download_worker = EmaDownloadWorker(self)
        self._download_worker.download_started.connect(
            lambda: self.model_status_changed.emit(False, "EMA Lightning modeli indiriliyor (34 MB)...")
        )
        self._download_worker.download_finished.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_finished(self, success: bool, message: str):
        self.model_status_changed.emit(success, message)

    def speak(self, text: str):
        """Verilen metni optimize edilmiş akış kuyruğu ile anında seslendirir."""
        if not text or not text.strip():
            self.error_occurred.emit("Seslendirilecek metin boş.")
            return

        self.stop()
        self._cleanup_temp_files()

        self._current_text = text.strip()
        self._is_paused = False
        self._is_synthesizing_done = False
        self._queue.clear()
        self._played_wav_paths.clear()
        self._active_wav_path = None
        self._accumulated_played_ms = 0
        self._estimated_total_ms = 0
        self._current_chunk_idx = 0
        self._total_chunks = 0

        if not is_ema_installed():
            self.error_occurred.emit("ema-lightning kütüphanesi kurulu değil.")
            return

        cleaned_sample = clean_text_for_speech(self._current_text)
        snippet = cleaned_sample[:90].replace("\n", " ") if cleaned_sample else self._current_text[:90]
        self.reading_started.emit(snippet)
        self.state_changed.emit(True)

        self._worker = EmaSynthesisWorker(self._current_text, self)
        self._worker.chunk_ready.connect(self._on_chunk_ready)
        self._worker.synthesis_finished.connect(self._on_synthesis_finished)
        self._worker.synthesis_error.connect(self._on_synthesis_error)
        self._worker.start()

    def _on_chunk_ready(self, idx: int, total: int, wav_path: str, duration_sec: float, text: str):
        self._total_chunks = total
        self._queue.append((wav_path, duration_sec, text))
        self._estimated_total_ms += int(duration_sec * 1000)

        # İlk parça geldiğinde bekletmeden hemen çalmaya başla! (Hızlı ilk ses)
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState and not self._is_paused:
            self._play_next_chunk()

    def _play_next_chunk(self):
        if not self._queue:
            if self._is_synthesizing_done:
                self.stop()
                self.reading_finished.emit()
            return

        wav_path, dur_sec, text = self._queue.pop(0)
        self._active_wav_path = wav_path
        self._played_wav_paths.append(wav_path)
        self._current_chunk_dur_ms = int(dur_sec * 1000)

        try:
            self.player.setSource(QUrl.fromLocalFile(wav_path))
            self.player.play()
            self.state_changed.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"Ses çalma hatası: {e}")
            self._play_next_chunk()

    def _on_synthesis_finished(self, total: int):
        self._is_synthesizing_done = True
        self._total_chunks = total
        # Eğer kuyruk zaten boşalmışsa ve oynatıcı durmuşsa tamamlandı sinyali ver
        if not self._queue and self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.stop()
            self.reading_finished.emit()

    def _on_synthesis_error(self, err_msg: str):
        self.error_occurred.emit(err_msg)
        if not self._queue and self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.state_changed.emit(False)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_paused = False
            self.state_changed.emit(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_paused = True
            self.state_changed.emit(False)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            if not self._is_paused:
                self._accumulated_played_ms += self._current_chunk_dur_ms
                # Sıradaki parçaya otomatik geçiş
                self._play_next_chunk()

    def _on_position_changed(self, pos_ms: int):
        current_total = self._accumulated_played_ms + pos_ms
        total_dur = max(self._estimated_total_ms, current_total)
        self.playback_progress.emit(current_total, total_dur)

    def _on_duration_changed(self, dur_ms: int):
        pass

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str):
        # QMediaPlayer hatalarını temiz biçimde ele al
        if error != QMediaPlayer.Error.NoError:
            self.error_occurred.emit(f"Ses sürücüsü uyarısı: {error_string}")

    def pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self._is_paused = True
            self.state_changed.emit(False)

    def resume(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            self._is_paused = False
            self.state_changed.emit(True)
        elif self._queue:
            self._play_next_chunk()

    def stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            try:
                self._worker.quit()
                self._worker.wait(300)
            except Exception:
                pass
            self._worker = None

        if self.player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.player.stop()

        self._queue.clear()
        self._is_paused = False
        self._is_synthesizing_done = False
        self._accumulated_played_ms = 0
        self._estimated_total_ms = 0
        self.state_changed.emit(False)
        self.playback_progress.emit(0, 0)

        # Eski geçici ses dosyalarını temizle
        self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """Kullanımı biten geçici wav dosyalarını arka planda güvenle temizler."""
        paths_to_delete = list(self._played_wav_paths)
        self._played_wav_paths.clear()

        def _do_clean():
            for p in paths_to_delete:
                try:
                    if p and os.path.exists(p) and p != self._active_wav_path:
                        os.remove(p)
                except Exception:
                    pass

        threading.Thread(target=_do_clean, daemon=True).start()

    def set_volume(self, vol_percent: int):
        """0 ile 100 arası ses düzeyi."""
        clamped = max(0, min(100, vol_percent))
        self.audio_output.setVolume(clamped / 100.0)

    def seek(self, position_ms: int):
        self.player.setPosition(position_ms)
