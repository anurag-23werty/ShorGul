import numpy as np
import pandas as pd

from shorgul.metrics.wer_cer import error_counts
from shorgul.stats.bootstrap import ci, paired


def _group(n=40, err_rate=0.2, seed=0, cond="clean"):
    rng = np.random.default_rng(seed)
    ref = rng.integers(8, 20, n)
    return pd.DataFrame({"clip_id": [f"c{i}" for i in range(n)], "condition": cond,
                         "word_err": rng.binomial(ref, err_rate).astype(float), "ref_words": ref,
                         "entity_hit_rate": rng.random(n)})


def test_ci_contains_point_and_is_corpus_level():
    g = _group()
    point, lo, hi = ci(g, "wer")
    assert lo < point < hi
    assert point == g["word_err"].sum() / g["ref_words"].sum()
    assert 0.1 < point < 0.3 and hi - lo < 0.15


def test_ci_deterministic():
    g = _group()
    assert ci(g, "wer") == ci(g, "wer")


def test_paired_identical_is_tie():
    g = _group()
    r = paired(g, g.copy(), "wer")
    assert r.point == 0 and not r.significant


def test_paired_detects_real_difference():
    a, b = _group(err_rate=0.10, seed=1), _group(err_rate=0.30, seed=2)
    b["clip_id"] = a["clip_id"]
    r = paired(a, b, "wer")
    assert r.point < 0 and r.significant and r.p < 0.05


def test_paired_small_noise_not_significant():
    a = _group(err_rate=0.2, seed=3)
    b = a.copy()
    b.loc[0, "word_err"] += 1  # one extra error in one clip
    assert not paired(a, b, "wer").significant


def test_paired_cluster_pools_conditions_by_clip():
    a = pd.concat([_group(seed=4, cond=c) for c in ("clean", "phone")])
    b = a.copy()
    b["word_err"] += 2
    r = paired(a, b, "wer")
    assert r.n_clips == 40 and r.significant


def test_paired_entity_mean_ignores_nan():
    a, b = _group(seed=5), _group(seed=5)
    a.loc[0, "entity_hit_rate"] = np.nan
    r = paired(a, b, "entity_hit_rate")
    assert r.n_clips == 39 and r.point == 0


def test_error_counts_and_currency_neutral():
    assert error_counts("a b c d", "a x c", "hi") == (2, 4, 3, 7)  # chars: b->x, delete " d"
    assert error_counts("a b", "", "hi")[:2] == (2, 2)
    ref, hyp = "₹4,500 की 5 मार्च", "4,500 रुपये की 5 March"
    assert error_counts(ref, hyp, "hinglish")[0] == 1          # "रुपये" counted as an insertion
    assert error_counts(ref, hyp, "hinglish", currency_neutral=True)[0] == 0


def test_update_readme_markers_idempotent(tmp_path):
    from shorgul.report.tables import update_readme
    p = tmp_path / "R.md"
    p.write_text("x\n<!-- table:wer -->\n<!-- /table:wer -->\ny\n")
    assert update_readme(p, {"wer": "| a |"}) == ["wer"]
    once = p.read_text()
    update_readme(p, {"wer": "| a |"})
    assert p.read_text() == once == "x\n<!-- table:wer -->\n| a |\n<!-- /table:wer -->\ny\n"
