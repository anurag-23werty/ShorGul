"""Hinglish call-centre clips via Gnani Timbre v2.5 TTS (REST, synchronous wav).

Every TTS response is cached in the same sqlite cache as ASR, so re-running
`prepare` never re-bills a line. Real calls are capped by `max_calls`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

from shorgul.audio import SR, read_bytes, read_wav, write_wav
from shorgul.asr.cache import Cache
from shorgul.config import ROOT, api_key, load_config

TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
TTS_MODEL = "timbre-v2.5"


def read_script(path: Path) -> list[dict]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        clip_id, text, ents = raw.split("|")
        lines.append({"clip_id": clip_id, "text": text.strip(), "entities": ents.strip()})
    return lines


def tts_payload(text: str, voice: str) -> dict:
    return {
        "text": text, "voice": voice, "model": TTS_MODEL, "language": "hi-IN", "speed": 1.0,
        "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }


def tts_key(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def synthesize(payload: dict) -> bytes:
    r = requests.post(TTS_URL, json=payload, timeout=60,
                      headers={"X-API-Key-ID": api_key(), "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"TTS HTTP {r.status_code}: {r.text[:300]}")
    return r.content


def generate_hinglish(out_dir: Path, max_calls: int, n: int | None = None) -> list[dict]:
    """Return manifest rows for lines whose audio exists (cached or newly synthesized)."""
    cfg = load_config()["data"]
    voices = cfg["tts_voices"]
    cache = Cache.default()
    lines = read_script(ROOT / cfg["hinglish_script"])[: n or None]
    rows, calls = [], 0
    for i, line in enumerate(lines):
        wav = out_dir / f"{line['clip_id']}.wav"
        if not wav.exists():
            payload = tts_payload(line["text"], voices[i % len(voices)])
            key = tts_key(payload)
            blob = cache.get_blob(key)
            if blob is None:
                if calls >= max_calls:
                    print(f"[tts] max-calls {max_calls} reached; skipping {line['clip_id']}")
                    continue
                calls += 1
                blob = synthesize(payload)
                cache.put_blob(key, blob)
            write_wav(wav, read_bytes(blob))
        dur = len(read_wav(wav)) / SR
        rows.append({
            "clip_id": line["clip_id"], "lang": "hinglish", "source": "tts",
            "audio_path": str(wav.relative_to(ROOT)), "duration_s": round(dur, 3), "reference": line["text"],
            "has_entities": True, "entities": line["entities"],
        })
    print(f"[tts] {len(rows)} clips ready, {calls} new API calls")
    return rows
