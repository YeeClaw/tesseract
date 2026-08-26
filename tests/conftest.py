"""
Standard fixtures used to configure the suite of tests.
"""

import pytest

from tesseract.core.paths import DATA_DIR_VARIABLE


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(DATA_DIR_VARIABLE, str(tmp_path/"data"))
