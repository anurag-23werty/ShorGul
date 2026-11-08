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
def degrade(
    conditions: str = typer.Option(None, help="Comma list (default: all in bench.yaml)"),
    langs: str = typer.Option(None, help="Only these langs"),
    clips: str = typer.Option(None, help="Only these clip_ids"),
    force: bool = typer.Option(False, help="Rebuild existing files"),
) -> None:
    """Apply telephony conditions to clean clips -> data/degraded/{condition}/{clip_id}.wav."""
    from shorgul.degrade.pipeline import degrade_all

    df = read_manifest()
    if langs:
        df = df[df["lang"].isin(_split(langs))]
    if clips:
        df = df[df["clip_id"].isin(_split(clips))]
    conds = _split(conditions) or list(load_config()["conditions"])
    log = degrade_all(df, conds, force=force)
    print(f"[degrade] {len(df)} clips x {len(conds)} conditions -> {len(log)} new files")
    if len(log):
        print(log.to_string(index=False))


@app.command()
def enhance(
    conditions: str = typer.Option(None, help="Comma list (default: noisy_conditions)"),
    langs: str = typer.Option(None, help="Only these langs"),
    clips: str = typer.Option(None, help="Only these clip_ids"),
    force: bool = typer.Option(False, help="Rebuild existing files"),
) -> None:
    """Denoise degraded audio (spectral gating) -> data/enhanced/{condition}/{clip_id}.wav."""
    from shorgul.enhance.denoise import enhance_all

    df = read_manifest()
    if langs:
        df = df[df["lang"].isin(_split(langs))]
    if clips:
        df = df[df["clip_id"].isin(_split(clips))]
    conds = _split(conditions) or load_config()["noisy_conditions"]
    n = enhance_all(df, conds, force=force)
    print(f"[enhance] {len(df)} clips x {len(conds)} conditions -> {n} new files")


@app.command()
def run(
    models: str = typer.Option("prisma-v2.5,prisma-v3.0,whisper-small", help="Comma list of models"),
    conditions: str = typer.Option(None, help="Comma list (default: all)"),
    variants: str = typer.Option("raw", help="raw,denoised,context"),
    langs: str = typer.Option(None, help="Only these langs (hi,bn,ta,hinglish)"),
    clips: str = typer.Option(None, help="Only these clip_ids"),
    max_calls: int = typer.Option(0, help="Max NEW billed (Gnani) calls. 0 = cache only"),
    mock: bool = typer.Option(False, help="Fake transcripts; no API, separate results/mock/"),
    dry_run: bool = typer.Option(False, help="Only count cached vs needed calls"),
) -> None:
    """Transcribe degraded audio with each model (cache-first) -> results/hyps.parquet."""
    from shorgul.asr.runner import build_jobs, run_jobs, save_hyps

    df = read_manifest()
    if langs:
        df = df[df["lang"].isin(_split(langs))]
    if clips:
        df = df[df["clip_id"].isin(_split(clips))]
    conds = _split(conditions) or list(load_config()["conditions"])
    jobs = build_jobs(df, _split(models), conds, _split(variants))
    print(f"[run] {len(jobs)} jobs ({'MOCK' if mock else 'REAL'}), max billed calls = {max_calls}")
    hyps = run_jobs(jobs, mock=mock, max_calls=max_calls, dry_run=dry_run)
    if not dry_run:
        out = save_hyps(hyps, mock)
        print(f"[run] {len(hyps)} rows -> {out}")
        if len(hyps):
            print(hyps.groupby(["model", "status"]).size().to_string())


@app.command()
def score(
    mock: bool = typer.Option(False, help="Score results/mock/ instead of real results"),
    charts: bool = typer.Option(True, help="Also render README charts"),
) -> None:
    """Score hyps.parquet -> results.parquet (per row) + summary.csv (corpus-level per group)."""
    from shorgul.asr.runner import results_dir
    from shorgul.metrics.aggregate import RESULT_COLS, compare, score_rows, summarize

    rdir = results_dir(mock)
    hyps = pd.read_parquet(rdir / "hyps.parquet")
    scored = score_rows(hyps)
    scored.to_parquet(rdir / "scored_full.parquet", index=False)
    scored[RESULT_COLS].to_parquet(rdir / "results.parquet", index=False)
    summ = summarize(scored)
    summ.to_csv(rdir / "summary.csv", index=False)
    comp = compare(scored)
    comp.to_csv(rdir / "comparisons.csv", index=False)
    print(f"[score] {len(scored)} rows -> {rdir / 'results.parquet'}; "
          f"{len(summ)} groups with 95% CIs -> summary.csv; {len(comp)} paired tests -> comparisons.csv")
    if charts:
        from shorgul.metrics.charts import render_charts
        for p in render_charts(summ, rdir / "charts", comp):
            print(f"[chart] {p}")


@app.command()
def audit(
    folder: Path = typer.Argument(..., help="Folder of your audio files (wav/flac/ogg/mp3, <= 30 s each)"),
    lang: str = typer.Option(..., help="hi | bn | ta | hinglish"),
    model: str = typer.Option("prisma-v3.0", help="prisma-v2.5 | prisma-v3.0 | whisper-small"),
    max_calls: int = typer.Option(0, help="Max NEW billed calls. Needed = clips x (1 + conditions)"),
    mock: bool = typer.Option(False, help="Fake transcripts, no API: try the report for free"),
    refs: Path = typer.Option(None, help="Optional refs.csv (file,reference,entities) for WER/entity accuracy"),
    conditions: str = typer.Option(None, help="Comma list (default: phone,loss_5,traffic_5,market_0)"),
    out: Path = typer.Option(None, help="Output dir (default results/audits/<folder name>)"),
) -> None:
    """Audit your own audio: health check, stability grade A-F, breaking point, fixes -> report.html."""
    from shorgul.audit.report import render
    from shorgul.audit.run import DEFAULT_CONDITIONS, collect, plan_calls, run_audit

    conds = _split(conditions) or DEFAULT_CONDITIONS
    n = len(collect(folder))
    need = plan_calls(n, len(conds))
    out = out or path("results") / "audits" / folder.name
    print(f"[audit] {n} clips x (1 original + {len(conds)} conditions) = {need} transcriptions "
          f"({'MOCK, 0 billed' if mock or model == 'whisper-small' else f'up to {need} billed, cap {max_calls}'})")
    res = run_audit(folder, lang, model, max_calls, mock, out, conds, refs)
    report = render(res, out)
    res.rows.to_csv(out / "audit_rows.csv", index=False)
    res.clips.to_csv(out / "audit_clips.csv", index=False)
    s = res.summary
    print(f"[audit] grade {s['grade']} | mean stability {s['mean_stability']:.1%} | breaking point "
          f"{s['breaking_point'] or 'none'} | nearest: {s['nearest']}")
    print(s["per_condition"].round(3).to_string(index=False))
    print(f"[audit] report -> {report}")


@app.command()
def compare(
    baseline: Path = typer.Option(None, help="Baseline results (parquet/csv with clip_id,condition,reference,hypothesis)"),
    candidate: Path = typer.Option(None, help="Candidate results (same format; may be the same file)"),
    baseline_model: str = typer.Option(None), candidate_model: str = typer.Option(None),
    baseline_variant: str = typer.Option("raw"), candidate_variant: str = typer.Option("raw"),
    metric: str = typer.Option("wer", help="wer (currency-neutral) | entity"),
    fail_on: float = typer.Option(2.0, help="Fail if candidate is significantly worse by >= this many points"),
    langs: str = typer.Option(None, help="Only these langs"),
    mock: bool = typer.Option(False, help="Synthesize both sides with the mock ASR (CI smoke test, no audio/API)"),
    mock_regress: bool = typer.Option(False, help="With --mock: make the candidate worse, to prove the gate fails"),
) -> None:
    """Regression gate: paired bootstrap, exit 1 on a significant regression >= --fail-on points."""
    from shorgul.compare import gate, load_side, mock_side

    if mock:
        base = mock_side("prisma-v2.5", _split(langs))
        cand = mock_side("whisper-small" if mock_regress else "prisma-v3.0", _split(langs))
    else:
        if not (baseline and candidate):
            raise typer.BadParameter("--baseline and --candidate are required (or use --mock)")
        base = load_side(baseline, baseline_model, baseline_variant)
        cand = load_side(candidate, candidate_model, candidate_variant)
    if langs:
        base, cand = base[base["lang"].isin(_split(langs))], cand[cand["lang"].isin(_split(langs))]
    g = gate(base, cand, metric, fail_on)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(g.table[g.table["condition"] == "ALL"].to_string(index=False))
        worst = g.table[g.table["verdict"] != "no significant change"]
        if len(worst):
            print("\nper-condition changes:")
            print(worst[worst["condition"] != "ALL"].to_string(index=False))
    print(g.message)
    raise typer.Exit(1 if g.regressed else 0)


@app.command("stability")
def stability_cmd() -> None:
    """Validate the label-free stability score against true WER increase on FLEURS."""
    from shorgul.audit.stability import folder_level, plot_validation, stability_table, validate

    rdir = path("results")
    scored = pd.read_parquet(rdir / "scored_full.parquet")
    table = stability_table(scored[scored["lang"] != "hinglish"])
    folder = folder_level(table, pd.read_csv(rdir / "summary.csv"))
    v = validate(table)
    v.to_csv(rdir / "stability_validation.csv", index=False)
    folder.to_csv(rdir / "stability_folder_level.csv", index=False)
    plot_validation(table, folder, rdir / "charts" / "stability_validation.png")
    print("[stability] per clip (stability vs true WER increase):")
    print(v.to_string(index=False))
    from scipy.stats import spearmanr
    for name, g in [("prisma", folder[folder["model"].str.startswith("prisma")]), ("all", folder)]:
        r, p = spearmanr(g["mean_stability"], g["wer_increase"])
        print(f"[stability] folder level, {name}: rho={r:.3f} p={p:.2g} (n={len(g)})")
    print(f"[chart] {rdir / 'charts' / 'stability_validation.png'}")


@app.command("readme-gif")
def readme_gif() -> None:
    """Render docs/finding.gif from cached transcripts and results (needs libraqm for Devanagari)."""
    from shorgul.config import ROOT
    from shorgul.report.gif import build
    out = build(ROOT / "docs" / "finding.gif")
    print(f"[gif] {out} ({out.stat().st_size / 1024:.0f} KB)")


@app.command("readme-tables")
def readme_tables(mock: bool = typer.Option(False, help="Use results/mock/")) -> None:
    """Regenerate the README tables (with 95% CIs) from summary.csv and comparisons.csv."""
    from shorgul.asr.runner import results_dir
    from shorgul.config import ROOT
    from shorgul.report.tables import render, update_readme

    tables = render(results_dir(mock))
    (results_dir(mock) / "key_numbers.md").write_text(
        "\n\n".join(f"## {k}\n\n{v}" for k, v in tables.items()) + "\n", encoding="utf-8")
    done = update_readme(ROOT / "README.md", tables) if not mock else []
    if not mock:
        update_readme(results_dir(mock) / "repair_report.md", tables)
    print(f"[tables] key_numbers.md written; README tables updated: {done or 'none (no markers)'}")


if __name__ == "__main__":
    app()
