"""Gnani Prisma STT client (v2.5 default, v3.0 via model=prisma-v3.0). Sequential, with backoff."""
from __future__ import annotations

import time
from typing import Any

import requests

from shorgul.asr.base import ASRResult
from shorgul.config import api_key

STT_URL = "https://api.vachana.ai/stt/v3"
BACKOFF_S = (1, 2, 4, 8, 16)


class PrismaASR:
    billed = True

    def __init__(self, name: str, session: requests.Session | None = None,
                 sleep=time.sleep) -> None:
        assert name in ("prisma-v2.5", "prisma-v3.0")
        self.name = name
        self.session = session or requests.Session()
        self.sleep = sleep

    def form_fields(self, params: dict[str, Any]) -> dict[str, str]:
        data = {k: v for k, v in params.items() if not k.startswith("_")}
        if self.name == "prisma-v3.0":
            data["model"] = "prisma-v3.0"  # v2.5 = omit model
        return data

    def transcribe(self, audio: bytes, params: dict[str, Any]) -> ASRResult:
        data = self.form_fields(params)
        headers = {"X-API-Key-ID": api_key()}
        last = "failed"
        for attempt, wait in enumerate((0, *BACKOFF_S)):
            if wait:
                self.sleep(wait)
            t0 = time.perf_counter()
            try:
                r = self.session.post(STT_URL, headers=headers, data=data, timeout=90,
                                      files={"audio_file": ("audio.wav", audio, "audio/wav")})
            except requests.RequestException as e:
                last = f"failed: {type(e).__name__}"
                continue
            latency = round(time.perf_counter() - t0, 3)
            if r.status_code == 429:
                last = "rate_limited"
                continue
            if r.status_code >= 500:
                last = f"error_{r.status_code}"
                continue
            if r.status_code != 200:  # 400/401/422...: log, never retry
                body = r.text[:300]
                print(f"[prisma] {self.name} HTTP {r.status_code}: {body}")
                return ASRResult("", f"error_{r.status_code}", latency, {"body": body})
            js = r.json()
            status = "ok_truncated" if js.get("truncated") else "ok"
            return ASRResult(js.get("transcript", "") or "", status, latency, js)
        print(f"[prisma] {self.name} gave up: {last}")
        return ASRResult("", last if last == "rate_limited" else "failed", 0.0, {"last": last})
