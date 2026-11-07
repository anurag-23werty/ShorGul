"""Local Whisper-small baseline via faster-whisper (CPU, int8, greedy-deterministic)."""
from __future__ import annotations

import time
from typing import Any

from shorgul.asr.base import ASRResult
from shorgul.audio import read_bytes


class WhisperASR:
    billed = False
    name = "whisper-small"

    def __init__(self, size: str = "small") -> None:
        self.size = size
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio: bytes, params: dict[str, Any]) -> ASRResult:
        wav = read_bytes(audio)
        model = self.model  # load outside the timed region
        t0 = time.perf_counter()
        segs, _ = model.transcribe(
            wav, language=params["language"], beam_size=params.get("beam_size", 5),
            temperature=0.0, condition_on_previous_text=False, vad_filter=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        return ASRResult(text, "ok", round(time.perf_counter() - t0, 3), {})
