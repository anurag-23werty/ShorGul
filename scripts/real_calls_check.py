"""Free reality check (no API calls): do simulated calls look like real ones, and does the health check catch
REAL dropouts? Compares Gram Vaani real telephone clips with the benchmark's simulated conditions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shorgul.config import load_config  # noqa: E402
from shorgul.health.check import check_file, condition_profiles, nearest_condition  # noqa: E402


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """P(score of a real-dropout clip > score of a clean-line clip), ties count half."""
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))


def main() -> None:
    m = pd.read_csv(ROOT / "data" / "manifest.csv", keep_default_na=False)
    gv = m[m["lang"] == "hi_gv"]
    rows = [{"clip_id": r.clip_id, "kind": r.source.replace("gramvaani_", ""), **check_file(ROOT / r.audio_path).as_dict()}
            for r in gv.itertuples()]
    real = pd.DataFrame(rows)
    conds = list(load_config()["conditions"])
    prof = condition_profiles(ROOT / "data" / "degraded", conds, max_clips=40)
    from shorgul.health.check import Health
    real["nearest"] = [nearest_condition(Health(**{k: r[k] for k in Health.__dataclass_fields__}), prof)
                       for r in real.to_dict("records")]
    sim = []
    for c in ["clean", "phone", "loss_5", "amrnb_mobile", "opus_voip", "market_10", "market_0"]:
        for f in sorted((ROOT / "data" / "degraded" / c).glob("hi_*.wav"))[:25]:
            sim.append({"condition": c, **check_file(f).as_dict()})
    sim = pd.DataFrame(sim)
    feats = ["snr_db", "hf_ratio", "dropout_pct", "clipping_pct"]
    table = pd.concat([real.groupby("kind")[feats].median().rename(index=lambda k: f"REAL {k}"),
                       sim.groupby("condition")[feats].median().rename(index=lambda k: f"sim {k}")])
    d, c = real[real.kind == "dropout"]["dropout_pct"].values, real[real.kind == "clean_line"]["dropout_pct"].values
    out = {
        "n_real": len(real), "n_real_dropout": int(len(d)), "n_real_clean_line": int(len(c)),
        "medians": table.round(5).to_dict(orient="index"),
        "dropout_detector_auc": round(auc(d, c), 3),
        "flagged_loss_rate": {"real_dropout": round(float(np.mean(d >= 1.5)), 3), "real_clean_line": round(float(np.mean(c >= 1.5)), 3)},
        "real_narrowband_share": round(float(np.mean(real["hf_ratio"] < 3e-4)), 3),
        "nearest_condition_counts": real["nearest"].value_counts().to_dict(),
    }
    (ROOT / "results" / "real_calls_health.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    with pd.option_context("display.width", 160):
        print(table.round(4).to_string())
    print(json.dumps({k: v for k, v in out.items() if k != "medians"}, indent=1))


if __name__ == "__main__":
    main()
