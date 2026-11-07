"""ShorGul Bench CLI: prepare | degrade | enhance | run | score."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from shorgul.config import load_config, path

app = typer.Typer(add_completion=False, no_args_is_help=True)

MANIFEST_COLS = ["clip_id", "lang", "source", "audio_path", "duration_s",
                 "reference", "has_entities", "entities"]


def _split(s: str | None) -> list[str] | None:
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def read_manifest() -> pd.DataFrame:
    return pd.read_csv(path("manifest"), keep_default_na=False)


def _merge_manifest(rows: list[dict], langs: set[str]) -> pd.DataFrame:
    new = pd.DataFrame(rows, columns=MANIFEST_COLS)
    mpath = path("manifest")
    if mpath.exists():
        old = read_manifest()
        new = pd.concat([old[~old["lang"].isin(langs)], new], ignore_index=True)
    new = new.sort_values("clip_id").reset_index(drop=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(mpath, index=False)
    return new


@app.command()
def prepare(
    langs: str = typer.Option("hi,bn,ta", help="FLEURS langs to fetch (hi,bn,ta)"),
    n: int = typer.Option(None, help="Clips per language (default from config)"),
    tts: bool = typer.Option(False, help="Also build Hinglish clips via Timbre TTS (billed)"),
    max_calls: int = typer.Option(0, help="Max NEW TTS API calls (cached lines are free)"),
    noise: bool = typer.Option(True, help="Download DEMAND noise if missing"),
) -> None:
    """Fetch FLEURS subset, (optionally) TTS Hinglish lines, noise; write manifest.csv."""
    from shorgul.data.fleurs_loader import fetch_fleurs

    cfg = load_config()["data"]
    n = n or cfg["n_clips"]
    clean = path("clean")
    rows: list[dict] = []
    done_langs: set[str] = set()
    for lang in _split(langs) or []:
        got = fetch_fleurs(lang, cfg["fleurs_configs"][lang], n, cfg["max_duration_s"], clean)
        print(f"[fleurs] {lang}: {len(got)} clips")
        rows += got
        done_langs.add(lang)
    if tts:
        from shorgul.data.tts_generator import generate_hinglish
        rows += generate_hinglish(clean, max_calls=max_calls, n=n)
        done_langs.add("hinglish")
    if noise:
        from shorgul.data.noise_fetch import fetch_noise
        fetch_noise(path("noise"))
    df = _merge_manifest(rows, done_langs)
    print(f"[manifest] {len(df)} rows -> {path('manifest')}")
    print(df.groupby("lang").agg(clips=("clip_id", "count"), mean_dur=("duration_s", "mean")).round(2))


@app.command()
def degrade() -> None:
    """(Phase 2)"""
    raise typer.Exit("not implemented yet")


@app.command()
def enhance() -> None:
    """(Phase 4)"""
    raise typer.Exit("not implemented yet")


@app.command()
def run() -> None:
    """(Phase 3)"""
    raise typer.Exit("not implemented yet")


@app.command()
def score() -> None:
    """(Phase 4)"""
    raise typer.Exit("not implemented yet")


if __name__ == "__main__":
    app()
