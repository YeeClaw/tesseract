"""The tests of the two rules that shape the code.

Rule 1: no module in the core imports PySide6. The core must run and test
without a display.

Rule 2: only `core/backend/` imports `minecraft_launcher_lib`. Nothing above
that package knows that the library exists.

Each test reads the source of every module with `ast`. It therefore finds an
import in a branch that no test runs, and it needs neither Qt nor the library
to be installed.
"""

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent / "src" / "tesseract"
CORE = SOURCE_ROOT / "core"
BACKEND = CORE / "backend"


def _modules(directory: Path) -> list[Path]:
    """Give every Python file under one directory, in a stable order."""
    return sorted(directory.rglob("*.py"))


def _imported_packages(module: Path) -> set[str]:
    """Give the first name of every absolute import that one module makes.

    A relative import gives no name, because it can only reach Tesseract.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    packages: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                packages.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            packages.add(node.module.split(".")[0])
    return packages


def _report(guilty: list[Path]) -> str:
    """Name each module that breaks a rule, relative to the source root."""
    return ", ".join(str(module.relative_to(SOURCE_ROOT)) for module in guilty)


def test_the_source_tree_holds_modules() -> None:
    """Guard the two tests below.

    A wrong path would make both tests pass and prove nothing.
    """
    assert SOURCE_ROOT.is_dir(), f"no source tree at {SOURCE_ROOT}"
    assert CORE.is_dir(), f"no core package at {CORE}"
    assert _modules(SOURCE_ROOT), "the source tree holds no module"


def test_no_module_in_the_core_imports_pyside6() -> None:
    """Rule 1."""
    guilty = [m for m in _modules(CORE) if "PySide6" in _imported_packages(m)]
    assert not guilty, (
        f"the core imports PySide6 in: {_report(guilty)}. "
        "Add a signal in the bridge module instead."
    )


def test_only_the_backend_imports_the_library() -> None:
    """Rule 2."""
    guilty = [
        module
        for module in _modules(SOURCE_ROOT)
        if "minecraft_launcher_lib" in _imported_packages(module)
        and BACKEND not in module.parents
    ]
    assert not guilty, (
        f"minecraft_launcher_lib is imported outside core/backend/ in: {_report(guilty)}. "
        "Add a method to the Backend interface instead."
    )
