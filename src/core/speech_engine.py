"""
AuraPDF Speech Engine (Metin Seslendirme / Read Aloud)
=====================================================
PyQt6.QtTextToSpeech tabanlı, doküman metinlerini veya seçili metinleri
doğal ses tonlarıyla seslendiren konuşma motoru.
"""

from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtTextToSpeech import QTextToSpeech, QVoice


class AuraSpeechEngine(QObject):
    state_changed = pyqtSignal(bool)  # is_speaking
    reading_started = pyqtSignal(str)
    reading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.tts: Optional[QTextToSpeech] = None
        self._is_available = False
        self._current_text = ""
        self._init_tts()

    def _init_tts(self):
        try:
            self.tts = QTextToSpeech(self)
            self._is_available = True
            self.tts.stateChanged.connect(self._on_state_changed)
        except Exception as e:
            self._is_available = False
            self.tts = None
            print(f"[AuraSpeechEngine] TTS Başlatılamadı: {e}")

    def is_available(self) -> bool:
        return self._is_available and self.tts is not None

    def is_speaking(self) -> bool:
        if self.is_available():
            return self.tts.state() == QTextToSpeech.State.Speaking
        return False

    def _on_state_changed(self, state: QTextToSpeech.State):
        is_speaking = (state == QTextToSpeech.State.Speaking)
        self.state_changed.emit(is_speaking)
        if state == QTextToSpeech.State.Ready:
            self.reading_finished.emit()

    def speak(self, text: str):
        if not self.is_available() or not text or not text.strip():
            return
        self._current_text = text.strip()
        try:
            self.stop()
            self.reading_started.emit(self._current_text[:80])
            self.tts.say(self._current_text)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def pause(self):
        if self.is_available():
            try:
                self.tts.pause()
            except Exception:
                pass

    def resume(self):
        if self.is_available():
            try:
                self.tts.resume()
            except Exception:
                pass

    def stop(self):
        if self.is_available():
            try:
                self.tts.stop()
            except Exception:
                pass

    def get_state(self) -> QTextToSpeech.State:
        if self.is_available():
            return self.tts.state()
        return QTextToSpeech.State.Ready

    def set_rate(self, rate_val: float):
        """0.0 normal, -1.0 çok yavaş, 1.0 çok hızlı (PyQt6 QTextToSpeech standardı -1.0 ile 1.0 arası)."""
        if self.is_available():
            try:
                clamped = max(-1.0, min(1.0, rate_val))
                self.tts.setRate(clamped)
            except Exception:
                pass

    def set_volume(self, vol: float):
        """0.0 ile 1.0 arası ses düzeyi."""
        if self.is_available():
            try:
                clamped = max(0.0, min(1.0, vol))
                self.tts.setVolume(clamped)
            except Exception:
                pass

    def get_available_voices(self) -> List[QVoice]:
        if self.is_available():
            try:
                return self.tts.availableVoices()
            except Exception:
                return []
        return []

    def set_voice(self, voice: QVoice):
        if self.is_available() and voice:
            try:
                self.tts.setVoice(voice)
            except Exception:
                pass
