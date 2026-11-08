from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from shorgul.config import path

APP = str(Path(__file__).resolve().parent.parent / "app" / "dashboard.py")
HAS = (path("results") / "summary.csv").exists() and (path("results") / "scored_full.parquet").exists()


@pytest.mark.skipif(not HAS, reason="needs scored results (results/scored_full.parquet is generated locally)")
def test_all_tabs_render_without_exceptions():
    at = AppTest.from_file(APP, default_timeout=180).run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 7
    for label, value in (("Audio", "denoised"), ("Metric", "cer")):
        for r in at.radio:
            if r.label == label:
                r.set_value(value).run()
                assert not at.exception, (label, at.exception)


@pytest.mark.skipif(not (path("results") / "mock" / "summary.csv").exists(), reason="run score --mock first")
def test_mock_source_renders():
    at = AppTest.from_file(APP, default_timeout=180).run()
    if "mock" in at.sidebar.radio[0].options:
        at.sidebar.radio[0].set_value("mock").run()
        assert not at.exception, at.exception
