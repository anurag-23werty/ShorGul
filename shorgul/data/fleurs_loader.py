"""Fetch a small FLEURS test subset without the deprecated `datasets` loading script.

Reads data/{cfg}/test.tsv, then streams audio/test.tar.gz and stops as soon as
n clips are collected (one per sentence id, duration <= max_dur), so we never
download the whole 250 MB archive.
"""
from __future__ import annotations

import csv
import tarfile
from pathlib import Path

import requests
from huggingface_hub import get_token, hf_hub_download, hf_hub_url

from shorgul.audio import SR, read_bytes, write_wav
from shorgul.config import ROOT

REPO = "google/fleurs"


def _read_tsv(cfg: str) -> dict[str, dict]:
    tsv = hf_hub_download(REPO, f"data/{cfg}/test.tsv", repo_type="dataset")
    rows: dict[str, dict] = {}
    with open(tsv, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rows[r[1]] = {"sent_id": r[0], "raw": r[2], "norm": r[3], "n": int(r[5])}
    return rows


def fetch_fleurs(lang: str, cfg: str, n: int, max_dur: float, out_dir: Path) -> list[dict]:
    rows = _read_tsv(cfg)
    url = hf_hub_url(REPO, f"data/{cfg}/audio/test.tar.gz", repo_type="dataset")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    clips: list[dict] = []
    seen_sent: set[str] = set()
    with requests.get(url, headers=headers, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        resp.raw.decode_content = True
        with tarfile.open(fileobj=resp.raw, mode="r|gz") as tar:
            for member in tar:
                name = Path(member.name).name
                row = rows.get(name)
                if not member.isfile() or row is None:
                    continue
                if row["n"] / SR > max_dur or row["sent_id"] in seen_sent:
                    continue
                audio = read_bytes(tar.extractfile(member).read())
                clip_id = f"{lang}_{len(clips):03d}"
                wav = out_dir / f"{clip_id}.wav"
                write_wav(wav, audio)
                seen_sent.add(row["sent_id"])
                clips.append({
                    "clip_id": clip_id, "lang": lang, "source": "fleurs",
                    "audio_path": str(wav.relative_to(ROOT)), "duration_s": round(len(audio) / SR, 3),
                    "reference": row["norm"], "has_entities": False, "entities": "",
                })
                if len(clips) >= n:
                    break
    return clips
