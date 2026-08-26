"""
Standard fixtures used to configure the suite of tests.
"""

from pathlib import Path

import pytest

from tesseract.core.paths import DATA_DIR_VARIABLE


# author: austin <colt.austin@coltco.net>
@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATA_DIR_VARIABLE, str(tmp_path/"data"))
