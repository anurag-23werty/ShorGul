from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from shorgul.config import path

APP = str(Path(__file__).resolve().parent.parent / "app" / "dashboard.py")


@pytest.mark.skipif(not (path("results") / "mock" / "summary.csv").exists(), reason="run score --mock first")
@pytest.mark.parametrize("source_index", [0, 1])
def test_dashboard_renders_without_exceptions(source_index):
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    if len(at.radio) and len(at.radio[0].options) > source_index:
        at.radio[0].set_value(at.radio[0].options[source_index]).run()
        assert not at.exception, at.exception
        at.radio[1].set_value("denoised").run()
        assert not at.exception, at.exception
