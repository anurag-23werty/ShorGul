import pandas as pd
from typer.testing import CliRunner

from shorgul.cli import app
from shorgul.compare import gate


def _side(err_words: int, n=30, entity_ok=True):
    rows = []
    for i in range(n):
        ref = "aapki emi ₹4,500 ki 5 मार्च ko due hai " + " ".join(f"w{j}" for j in range(10))
        words = ref.split()
        hyp = " ".join(words[:-err_words] if err_words else words)
        if not entity_ok:
            hyp = hyp.replace("₹4,500", "chaar hazaar")
        rows.append({"clip_id": f"c{i}", "lang": "hinglish", "condition": "clean", "reference": ref,
                     "hypothesis": hyp, "entities": "₹4,500;5 मार्च", "status": "ok"})
    return pd.DataFrame(rows)


def test_gate_passes_identical():
    g = gate(_side(1), _side(1), "wer", 2.0)
    assert not g.regressed and "PASS" in g.message


def test_gate_fails_significant_regression():
    g = gate(_side(0), _side(4), "wer", 2.0)  # candidate drops 4 words per clip
    assert g.regressed and (g.table["verdict"] == "REGRESSION").any()


def test_gate_threshold_blocks_small_but_significant():
    g = gate(_side(0), _side(1), "wer", 50.0)  # significant but far below a 50-pt threshold
    assert not g.regressed and (g.table["verdict"] == "worse (below threshold)").any()


def test_gate_entity_metric():
    assert gate(_side(0), _side(0, entity_ok=False), "entity", 2.0).regressed


def test_cli_mock_exit_codes():
    r = CliRunner()
    ok = r.invoke(app, ["compare", "--mock", "--metric", "wer", "--fail-on", "2"])
    bad = r.invoke(app, ["compare", "--mock", "--mock-regress", "--metric", "wer", "--fail-on", "2"])
    assert ok.exit_code == 0 and "PASS" in ok.output
    assert bad.exit_code == 1 and "FAIL" in bad.output
