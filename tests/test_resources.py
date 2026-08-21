"""
The test of the resources of the package.

The stylesheets are data files inside `tesseract`, and not files beside the
checkout. This test therefore passes against an installed wheel as well.
"""

import pytest

from tesseract.utils.helpers import load_stylesheet


@pytest.mark.parametrize("filename", ["dark.qss", "light.qss"])
def test_a_stylesheet_loads_from_the_package(filename: str) -> None:
    assert load_stylesheet(filename).strip()


def test_an_absent_stylesheet_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_stylesheet("no-such-theme.qss")
