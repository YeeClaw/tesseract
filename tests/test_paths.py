"""
The tests of the directories that Tesseract writes into.

No test reads the real data directory of the person. Each test that needs a
path sets the environment variable.
"""

from pathlib import Path

import pytest

from tesseract.core import paths


def test_variable_moves_data_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path))

    assert paths.data_dir() == tmp_path


def test_variable_accepts_tilde(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, "~/somewhere/tesseract")

    assert paths.data_dir() == Path.home()/"somewhere"/"tesseract"


def test_empty_variable_gives_directory_of_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty value must not give the working directory."""
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, "")

    assert paths.data_dir().is_absolute()
    assert paths.data_dir() != Path()


def test_directory_of_system_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """no variable, so platformdirs answers."""
    monkeypatch.delenv(paths.DATA_DIR_VARIABLE, raising=False)

    assert paths.data_dir().is_absolute()


def test_log_directory_sits_under_data_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path))

    assert paths.log_dir() == tmp_path/"logs"


def test_path_is_read_when_asked_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A change of the variable must reach the next call."""
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path/"one"))
    first = paths.data_dir()
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path/"two"))

    assert first != paths.data_dir()


def test_no_function_makes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path is an answer, and not an action. The writer makes the directory."""
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path/"absent"))

    paths.data_dir()
    paths.log_dir()

    assert not (tmp_path/"absent").exists()
