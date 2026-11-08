"""Real telephone speech: Gram Vaani ASR challenge eval set (OpenSLR 118, Interspeech 2022).

Spontaneous Hindi phone calls from rural India, human transcripts, annotator flags for real channel
defects ("audio_jump", "audio_break"). Licence: free for academic use; commercial use needs permission
from contact@gramvaani.org. Download GV_Eval_3h.tar.gz from https://www.openslr.org/118/ into
data/external/gramvaani/ and extract it there.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from shorgul.audio import SR, read_wav, write_wav
from shorgul.config import ROOT

GV = ROOT / "data" / "external" / "gramvaani" / "GV_Eval_3h"


def _labels() -> dict[str, dict]:
    with open(GV / "utt2labels", encoding="utf-8") as f:
        return {r["Uttids"]: r for r in csv.DictReader(f, delimiter="\t")}


def select(n_clean: int = 36, n_dropout: int = 24, max_s: float = 25.0, seed: int = 118) -> list[dict]:
    """Seeded, stratified: lines flagged clean vs lines with real dropouts. Never 'inaudible' (bad references)."""
    text = dict(l.rstrip("\n").split(" ", 1) for l in open(GV / "text", encoding="utf-8") if " " in l)
    lab = _labels()
    rng = np.random.default_rng(seed)
    pools: dict[str, list[str]] = {"clean_line": [], "dropout": []}
    for uid, t in text.items():
        other = lab.get(uid, {}).get("Other", "NA")
        if "inaudible" in other or "not_clear" in other or not t.strip():
            continue
        if other == "NA":
            pools["clean_line"].append(uid)
        elif "audio_jump" in other or "audio_break" in other:
            pools["dropout"].append(uid)
    out = []
    for kind, n in (("clean_line", n_clean), ("dropout", n_dropout)):
        ids = sorted(pools[kind])
        rng.shuffle(ids)
        for uid in ids:
            if sum(o["kind"] == kind for o in out) >= n:
                break
            p = GV / "Audio" / f"{uid}.mp3"
            if not p.exists():
                continue
            x = read_wav(p)
            if len(x) / SR > max_s or len(x) / SR < 2:
                continue
            out.append({"uid": uid, "kind": kind, "text": text[uid].strip(), "audio": x,
                        "background": lab.get(uid, {}).get("Background", "NA"),
                        "state": lab.get(uid, {}).get("State", "NA")})
    return out


def load_gramvaani(out_dir: Path, **kw) -> list[dict]:
    if not (GV / "text").exists():
        raise FileNotFoundError(f"{GV} not found: download GV_Eval_3h.tar.gz from https://www.openslr.org/118/")
    rows = []
    for c in select(**kw):
        clip_id = f"gv_{c['kind'].split('_')[0]}_{c['uid']}"
        wav = out_dir / f"{clip_id}.wav"
        write_wav(wav, c["audio"])
        rows.append({"clip_id": clip_id, "lang": "hi_gv", "source": f"gramvaani_{c['kind']}",
                     "audio_path": str(wav.relative_to(ROOT)), "duration_s": round(len(c["audio"]) / SR, 3),
                     "reference": c["text"], "has_entities": False, "entities": ""})
    return rows
