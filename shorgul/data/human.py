"""Human validation set: your own Hinglish recordings in data/human/ + refs.csv.

refs.csv columns: file,reference,entities[,channel,line_id]
  entities ";"-separated, written form (e.g. "₹4,500;5 मार्च")
  channel: "direct" (phone voice memo) or "call" (recorded over a real phone/WhatsApp call)
  line_id: the held-out line it reads (e.g. hh_000), so TTS and human can be compared on identical text
Clips are added to the manifest as lang="hinglish_human", source="human", and reported separately from TTS.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from shorgul.audio import SR, read_wav, write_wav
from shorgul.config import ROOT

MAX_S = 30.0


def load_human(human_dir: Path, out_dir: Path) -> list[dict]:
    refs = human_dir / "refs.csv"
    if not refs.exists():
        raise FileNotFoundError(f"{refs} not found (columns: file,reference,entities)")
    df = pd.read_csv(refs, keep_default_na=False)
    missing = {"file", "reference"} - set(df.columns)
    if missing:
        raise ValueError(f"refs.csv is missing columns: {sorted(missing)}")
    rows = []
    for i, r in enumerate(df.itertuples()):
        src = human_dir / r.file
        if not src.exists():
            raise FileNotFoundError(f"{src} listed in refs.csv but not found")
        audio = read_wav(src)
        if len(audio) / SR > MAX_S:
            raise ValueError(f"{r.file} is {len(audio) / SR:.1f} s; Gnani STT accepts at most {MAX_S:.0f} s")
        ents = getattr(r, "entities", "") or ""
        channel = (getattr(r, "channel", "") or "").strip()
        if channel and channel not in ("direct", "call"):
            raise ValueError(f"{r.file}: channel must be 'direct' or 'call', got {channel!r}")
        line = (getattr(r, "line_id", "") or "").strip()
        clip_id = f"hu_{channel or 'x'}_{line or f'{i:03d}'}"
        wav = out_dir / f"{clip_id}.wav"
        write_wav(wav, audio)
        rows.append({"clip_id": clip_id, "lang": "hinglish_human", "source": f"human_{channel}" if channel else "human",
                     "audio_path": str(wav.relative_to(ROOT)), "duration_s": round(len(audio) / SR, 3),
                     "reference": r.reference, "has_entities": bool(ents), "entities": ents})
    return rows
