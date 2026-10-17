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
import wave
from typing import Optional, List, Dict, Tuple, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioDevice

# Çevrimdışı modu ortam değişkeninde güvenceye al
os.environ["HF_HUB_OFFLINE"] = "1"

# Global Model Önbelleği (Singleton)
_EMA_MODEL = None
_EMA_LOCK = threading.Lock()
_EMA_INFERENCE_LOCK = threading.Lock()


def is_ema_installed() -> bool:
    try:
        import importlib.util
        if importlib.util.find_spec("ema_lightning") is None:
            return False
        if importlib.util.find_spec("torch") is None:
            return False
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
    # Kalan tekil yıldız ve benzeri şekilleri tamamen temizle (ama madde işareti mantığına bırakılmayanları)
    text = re.sub(r'[\★\☆\✦\✧\✪\✫\✬\✭\✮\✯\✰]', ' ', text)

    # 2. Markdown başlıkları, bağlantıları ve kodları
    text = re.sub(r'#+\s*', '', text)                     # ### Başlık -> Başlık
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text) # [link](url) -> link
    text = re.sub(r'\[\s*\d+\s*\]', '', text)              # [1], [23] dipnotları
    text = re.sub(r'`+([^`]+)`+', r'\1', text)            # `kod` -> kod
    text = re.sub(r'~~([^~]+)~~', r'\1', text)            # ~~üstü çizili~~ -> üstü çizili

    # Uzun ayırıcı çizgiler (----, ====, ____)
    text = re.sub(r'[-=_~]{2,}', ' ', text)

    # Tekrarlayan noktalar (...) ve fazla noktalama
    text = re.sub(r'\.{3,}', '.', text)

    # Madde imlerini düzgünce işle ve boşlukları temizle
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    new_lines = []
    for line in lines:
        # Madde işareti var mı kontrol et
        is_bullet = bool(re.match(r'^[\-\*\•\·\⁃\■\□\➢\➤\○\●\✓\✔\►\◄\◆\◇\▲\▼\△\▽\▸\▹\▪\▫]', line))
        if is_bullet:
            line = re.sub(r'^[\-\*\•\·\⁃\■\□\➢\➤\○\●\✓\✔\►\◄\◆\◇\▲\▼\△\▽\▸\▹\▪\▫]{1,2}\s*', '', line)
            if line and not re.search(r'[.,;:!?]$', line):
                line += '.'
        new_lines.append(line)

    cleaned = ' '.join(new_lines)
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

            import numpy as np
            from ema_lightning.audio import write_wav

            for idx, chunk in enumerate(chunks):
                if self._is_cancelled:
                    return

                # Benzersiz dosya adı oluşturarak Windows dosya kilitleme hatasını engelle
                timestamp = time.time_ns()
                wav_path = os.path.join(self.temp_dir, f"aurapdf_speech_{pid}_{timestamp}_{idx}.wav")

                with _EMA_INFERENCE_LOCK:
                    if self._is_cancelled:
                        return
                    with torch.inference_mode():
                        speech = tts.say(chunk.strip(), path=None)

                if self._is_cancelled:
                    return

                audio_data = speech.audio
                # Windows WASAPI / FFmpeg ses çıktısının donanım uyanma ve başlatma gecikmesi nedeniyle
                # ilk kelimeleri kesmesini önlemek için ilk parçanın başına 300ms sessizlik ekle
                if idx == 0:
                    silence_samples = int(speech.sample_rate * 0.30)
                    silence = np.zeros(silence_samples, dtype=audio_data.dtype)
                    audio_data = np.concatenate([silence, audio_data])

                write_wav(wav_path, audio_data, speech.sample_rate)
                duration = float(len(audio_data)) / float(speech.sample_rate)

                if self._is_cancelled:
                    try:
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                    except Exception:
                        pass
                    return

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
    Gelişmiş akış kuyruğu, hız kontrolü, cümle takibi ve dışa aktarma yetenekleri.
    """
    state_changed = pyqtSignal(bool)                     # is_speaking
    reading_started = pyqtSignal(str)                    # snippet
    reading_finished = pyqtSignal()
    playback_progress = pyqtSignal(int, int)             # current_ms, total_ms
    error_occurred = pyqtSignal(str)
    model_status_changed = pyqtSignal(bool, str)
    current_chunk_changed = pyqtSignal(int, int, str)    # current_index, total_chunks, current_chunk_text
    audio_device_changed = pyqtSignal(str, bool)         # device_name, is_auto_switched
    available_devices_changed = pyqtSignal(list)         # list of devices

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
        self._playback_rate: float = 1.0

        # Ses Çıkış Cihazı Yönetimi (Bluetooth / Hoparlör Otomatik Algılama)
        self.media_devices = QMediaDevices(self)
        self.media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)
        self._current_device_id: Optional[bytes] = None
        def_d = QMediaDevices.defaultAudioOutput()
        self._last_active_device_desc: str = def_d.description() if not def_d.isNull() else ""

        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # Akış ve Kuyruk Yönetimi
        self._all_chunks: List[Dict] = []
        self._queue_indices: List[int] = []
        self._active_wav_path: Optional[str] = None
        self._played_wav_paths: List[str] = []
        self._total_chunks = 0
        self._current_chunk_idx = 0
        self._accumulated_played_ms = 0
        self._current_chunk_dur_ms = 0
        self._estimated_total_ms = 0
        self._is_paused = False
        self._is_synthesizing_done = False
        self._is_playing = False

    def is_model_ready(self) -> bool:
        return is_ema_installed() and is_ema_model_cached()

    def is_speaking(self) -> bool:
        has_active_playback = self._is_playing and self._active_wav_path is not None
        has_active_worker = (self._worker is not None and self._worker.isRunning())
        has_pending_queue = len(self._queue_indices) > 0
        return has_active_playback or has_active_worker or has_pending_queue

    def is_paused(self) -> bool:
        return self._is_paused and (self._active_wav_path is not None or self._is_playing)

    def is_active(self) -> bool:
        return self.is_speaking() or self.is_paused()

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

    def set_playback_rate(self, rate: float):
        """0.5x ile 2.5x arasında ses oynatma hızını ayarlar."""
        clamped = max(0.5, min(2.5, float(rate)))
        self._playback_rate = clamped
        try:
            self.player.setPlaybackRate(clamped)
        except Exception:
            pass

    def get_playback_rate(self) -> float:
        return self._playback_rate

    def get_available_audio_devices(self) -> List[Dict[str, Any]]:
        """Sistemdeki tüm aktif ses çıkış cihazlarını listeler."""
        res = []
        def_dev = QMediaDevices.defaultAudioOutput()
        def_id = def_dev.id()
        for d in QMediaDevices.audioOutputs():
            res.append({
                "id": d.id(),
                "name": d.description(),
                "is_default": (d.id() == def_id),
                "device": d
            })
        return res

    def get_current_audio_device_desc(self) -> str:
        """Şu an aktif olan ses çıkış cihazının adını döndürür."""
        curr = self.audio_output.device()
        if curr and not curr.isNull():
            return curr.description()
        def_d = QMediaDevices.defaultAudioOutput()
        return def_d.description() if not def_d.isNull() else "Sistem Varsayılanı"

    def set_audio_device(self, device_id: Optional[bytes] = None):
        """
        Ses çıkış cihazını ayarlar. device_id None ise sistem varsayılanı (otomatik) kullanılır.
        """
        self._current_device_id = device_id
        target_dev = None

        if device_id is not None:
            for d in QMediaDevices.audioOutputs():
                if d.id() == device_id:
                    target_dev = d
                    break

        if target_dev is None or target_dev.isNull():
            target_dev = QMediaDevices.defaultAudioOutput()

        self._last_active_device_desc = target_dev.description()
        self.audio_output.setDevice(target_dev)

    def _on_audio_outputs_changed(self):
        """
        Sistemdeki ses cihazları (Bluetooth kulaklık açılma/kapanma, hoparlör değişimi)
        değiştiğinde otomatik olarak devreye girer ve sesi yeni aktif cihaza yönlendirir.
        """
        available = self.get_available_audio_devices()
        self.available_devices_changed.emit(available)

        def_dev = QMediaDevices.defaultAudioOutput()
        new_desc = def_dev.description()
        curr_dev = self.audio_output.device()

        is_switched = False
        # Eğer otomatik varsayılan modundaysa:
        if self._current_device_id is None:
            if curr_dev.isNull() or curr_dev.id() != def_dev.id() or self._last_active_device_desc != new_desc:
                is_switched = True
        else:
            # Seçili cihaz listeden kaybolduysa varsayılana dön
            still_exists = any(d["id"] == self._current_device_id for d in available)
            if not still_exists:
                self._current_device_id = None
                is_switched = True

        if is_switched:
            self.set_audio_device(self._current_device_id)
            self.audio_device_changed.emit(new_desc, True)

            # Eğer o sırada ses çalıyorsa veya cihaz kopmasından durduysa, kesintisiz devam et
            if self.is_speaking() or self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                try:
                    pos = self.player.position()
                    src = self.player.source()
                    if src and not src.isEmpty():
                        self.player.setSource(src)
                        self.player.setPosition(pos)
                        self.player.play()
                except Exception:
                    pass

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
        self._all_chunks.clear()
        self._queue_indices.clear()
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

    def speak_text(self, text: str):
        """speak metoduna takma ad (alias)."""
        self.speak(text)

    def _on_chunk_ready(self, idx: int, total: int, wav_path: str, duration_sec: float, text: str):
        self._total_chunks = total
        dur_ms = int(duration_sec * 1000)
        chunk_info = {
            "idx": idx,
            "wav_path": wav_path,
            "duration_sec": duration_sec,
            "start_ms": self._estimated_total_ms,
            "dur_ms": dur_ms,
            "text": text
        }
        self._all_chunks.append(chunk_info)
        self._queue_indices.append(idx)
        self._estimated_total_ms += dur_ms

        # İlk parça hazır olduğunda bekletmeden anında çalmaya başla!
        if not self._is_playing and not self._is_paused:
            self._play_next_chunk()

    def _play_chunk_by_index(self, idx: int, seek_within_chunk_ms: int = 0):
        if idx < 0 or idx >= len(self._all_chunks):
            return

        chunk = self._all_chunks[idx]
        self._current_chunk_idx = idx
        self._active_wav_path = chunk["wav_path"]
        self._accumulated_played_ms = chunk["start_ms"]
        self._current_chunk_dur_ms = chunk["dur_ms"]
        self._is_playing = True
        if chunk["wav_path"] not in self._played_wav_paths:
            self._played_wav_paths.append(chunk["wav_path"])

        try:
            # Oynatma öncesinde ses cihazının aktifliğini güvenceye al
            curr_dev = self.audio_output.device()
            def_dev = QMediaDevices.defaultAudioOutput()
            if self._current_device_id is None:
                if curr_dev.isNull() or curr_dev.id() != def_dev.id():
                    self.audio_output.setDevice(def_dev)
                    self._last_active_device_desc = def_dev.description()
            elif curr_dev.isNull():
                self.set_audio_device(self._current_device_id)

            self.player.setSource(QUrl.fromLocalFile(chunk["wav_path"]))
            self.player.setPlaybackRate(self._playback_rate)
            if seek_within_chunk_ms > 0:
                self.player.setPosition(seek_within_chunk_ms)
            self.player.play()
            self.state_changed.emit(True)
            self.current_chunk_changed.emit(idx, max(self._total_chunks, len(self._all_chunks)), chunk["text"])
        except Exception as e:
            self.error_occurred.emit(f"Ses çalma hatası: {e}")
            self._play_next_chunk()

    def _play_next_chunk(self):
        if self._queue_indices:
            next_idx = self._queue_indices.pop(0)
            self._play_chunk_by_index(next_idx)
            return

        # Kuyrukta şu an çalınacak yeni parça yok
        self._is_playing = False

        # Eğer sentez de tamamen bittiyse okuma bitti
        if self._is_synthesizing_done:
            try:
                self.player.stop()
                self.player.setSource(QUrl())
            except Exception:
                pass
            self._active_wav_path = None
            self.state_changed.emit(False)
            self.reading_finished.emit()
            self._cleanup_temp_files()

    def _on_synthesis_finished(self, total: int):
        self._is_synthesizing_done = True
        self._total_chunks = total
        # Eğer hiç parça üretilemediyse (metin boş vb.)
        if total == 0 or not self._all_chunks:
            self.stop()
            self.reading_finished.emit()
        elif not self._queue_indices and not self._is_playing:
            self.stop()
            self.reading_finished.emit()

    def _on_synthesis_error(self, err_msg: str):
        self.error_occurred.emit(err_msg)
        if not self._queue_indices and not self._is_playing:
            self.state_changed.emit(False)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_paused = False
            self.state_changed.emit(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_paused = True
            self.state_changed.emit(False)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            if not self._queue_indices and self._is_synthesizing_done:
                self._is_playing = False
                self.state_changed.emit(False)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if not self._is_paused:
                QTimer.singleShot(15, self._play_next_chunk)

    def _on_position_changed(self, pos_ms: int):
        current_total = self._accumulated_played_ms + pos_ms
        total_dur = max(self._estimated_total_ms, current_total)
        self.playback_progress.emit(current_total, total_dur)

    def _on_duration_changed(self, dur_ms: int):
        pass

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str):
        if error != QMediaPlayer.Error.NoError:
            # Cihaz bağlantısı kesintisi kontrolü (Bluetooth kapanması vb.)
            def_dev = QMediaDevices.defaultAudioOutput()
            if not def_dev.isNull() and self.audio_output.device().id() != def_dev.id():
                pos = self.player.position()
                self.audio_output.setDevice(def_dev)
                self._last_active_device_desc = def_dev.description()
                self.audio_device_changed.emit(def_dev.description(), True)
                try:
                    src = self.player.source()
                    if src and not src.isEmpty():
                        self.player.setSource(src)
                        self.player.setPosition(pos)
                        self.player.play()
                        return
                except Exception:
                    pass
            self.error_occurred.emit(f"Ses sürücüsü uyarısı: {error_string}")

    def pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self._is_paused = True
            self.state_changed.emit(False)

    def resume(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            self.player.setPlaybackRate(self._playback_rate)
            self._is_paused = False
            self.state_changed.emit(True)
        elif self._queue_indices:
            self._play_next_chunk()

    def stop(self):
        if self._worker:
            worker = self._worker
            self._worker = None
            try:
                worker.chunk_ready.disconnect()
            except Exception:
                pass
            try:
                worker.synthesis_finished.disconnect()
            except Exception:
                pass
            try:
                worker.synthesis_error.disconnect()
            except Exception:
                pass
            worker.cancel()
            try:
                worker.quit()
                worker.wait(600)
            except Exception:
                pass

        self._is_playing = False
        try:
            self.player.stop()
            self.player.setSource(QUrl())
        except Exception:
            pass

        self._queue_indices.clear()
        self._active_wav_path = None
        self._is_paused = False
        self._is_synthesizing_done = False
        self._accumulated_played_ms = 0
        self._estimated_total_ms = 0
        self.state_changed.emit(False)
        self.playback_progress.emit(0, 0)

        # Tüm parçaların geçici wav dosyalarını temizliğe ekle
        for c in self._all_chunks:
            wpath = c.get("wav_path")
            if wpath and wpath not in self._played_wav_paths:
                self._played_wav_paths.append(wpath)
        self._all_chunks.clear()

        self._cleanup_temp_files()

    def seek_to_ms(self, target_ms: int):
        """Tüm konuşma akışı boyunca belirli bir milisaniyeye atlar."""
        if not self._all_chunks:
            return

        target_ms = max(0, min(self._estimated_total_ms, target_ms))
        found_idx = 0
        seek_in_chunk = 0

        for idx, chunk in enumerate(self._all_chunks):
            start = chunk["start_ms"]
            end = start + chunk["dur_ms"]
            if start <= target_ms <= end or idx == len(self._all_chunks) - 1:
                found_idx = idx
                seek_in_chunk = max(0, target_ms - start)
                break

        # Kalan kuyruk indekslerini güncelle
        self._queue_indices = [i for i in range(found_idx + 1, len(self._all_chunks))]
        self._play_chunk_by_index(found_idx, seek_within_chunk_ms=seek_in_chunk)

    def skip_seconds(self, delta_sec: float):
        """+5 sn ileri veya -5 sn geri atlar."""
        if not self._all_chunks:
            return
        curr = self._accumulated_played_ms + self.player.position()
        target = curr + int(delta_sec * 1000)
        self.seek_to_ms(target)

    def next_chunk(self):
        """Bir sonraki cümleye/parçaya atlar."""
        if not self._all_chunks:
            return
        next_idx = self._current_chunk_idx + 1
        if next_idx < len(self._all_chunks):
            self._queue_indices = [i for i in range(next_idx + 1, len(self._all_chunks))]
            self._play_chunk_by_index(next_idx)

    def prev_chunk(self):
        """Önceki cümleye/parçaya döner veya mevcut cümleyi başa sarar."""
        if not self._all_chunks:
            return
        if self.player.position() > 2000 or self._current_chunk_idx == 0:
            self._play_chunk_by_index(self._current_chunk_idx, seek_within_chunk_ms=0)
        else:
            prev_idx = max(0, self._current_chunk_idx - 1)
            self._queue_indices = [i for i in range(prev_idx + 1, len(self._all_chunks))]
            self._play_chunk_by_index(prev_idx)

    def export_audio_file(self, target_wav_path: str) -> bool:
        """
        Sentezlenen tüm ses parçalarını birleştirerek tek bir .wav dosyası olarak kaydeder.
        """
        if not self._all_chunks:
            return False

        valid_wavs = [c["wav_path"] for c in self._all_chunks if os.path.exists(c["wav_path"])]
        if not valid_wavs:
            return False

        try:
            with wave.open(valid_wavs[0], 'rb') as first_w:
                params = first_w.getparams()

            with wave.open(target_wav_path, 'wb') as out_w:
                out_w.setparams(params)
                for wpath in valid_wavs:
                    with wave.open(wpath, 'rb') as in_w:
                        out_w.writeframes(in_w.readframes(in_w.getnframes()))

            return True
        except Exception as e:
            self.error_occurred.emit(f"Ses dışa aktarma hatası: {e}")
            return False

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
        self.seek_to_ms(position_ms)
