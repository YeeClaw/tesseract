"""
The tests of the two rules that shape the code.

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

SOURCE_ROOT = Path(__file__).resolve().parent.parent/"src"/"tesseract"
CORE = SOURCE_ROOT/"core"
BACKEND = CORE/"backend"


def _modules(directory: Path) -> list[Path]:
    """Give every Python file under one directory, in a stable order."""
    return sorted(directory.rglob("*.py"))


def _imported_names(module: Path) -> set[str]:
    """
    Give the full dotted name of every import that one module makes.

    A relative import resolves against the package of the module, because
    `from ..gui import windows` reaches the same place as the absolute form.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    # ("tesseract", "core") for src/tesseract/core/instances.py.
    package = module.relative_to(SOURCE_ROOT.parent).parts[:-1]

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                # Level 1 is the package of the module, level 2 its parent.
                here = package[: len(package) - node.level + 1]
                base = ".".join((*here, node.module) if node.module else here)
            # Both halves are needed: the base alone misses "from tesseract
            # import gui", and the joins alone miss "from tesseract.gui.windows
            # import MainWindow".
            names.add(base)
            for alias in node.names:
                names.add(f"{base}.{alias.name}")
    return names


def _imported_packages(module: Path) -> set[str]:
    """Give the first name of every import that one module makes."""
    return {name.split(".")[0] for name in _imported_names(module)}


def _report(guilty: list[Path]) -> str:
    """Name each module that breaks a rule, relative to the source root."""
    return ", ".join(str(module.relative_to(SOURCE_ROOT)) for module in guilty)


def test_source_tree_holds_modules() -> None:
    """
    Guard the two tests below.

    A wrong path would make both tests pass and prove nothing.
    """
    assert SOURCE_ROOT.is_dir(), f"no source tree at {SOURCE_ROOT}"
    assert CORE.is_dir(), f"no core package at {CORE}"
    assert _modules(SOURCE_ROOT), "the source tree holds no module"


def test_no_module_in_core_imports_pyside6() -> None:
    """Rule 1."""
    guilty = [m for m in _modules(CORE) if "PySide6" in _imported_packages(m)]
    assert not guilty, (
        f"the core imports PySide6 in: {_report(guilty)}. "
        "Add a signal in the bridge module instead."
    )


def test_no_module_in_core_imports_gui() -> None:
    """Rule 1.1 A core module that imports the GUI needs Qt."""
    guilty = [
        module
        for module in _modules(CORE)
        # Exact or dotted: "tesseract.guitar" must not read as the GUI.
        if any(
            name == "tesseract.gui" or name.startswith("tesseract.gui.")
            for name in _imported_names(module)
        )
    ]
    assert not guilty, (
        f"the core imports the gui in: {_report(guilty)}. "
        "Take a callback in the core and connect it in gui/tasks.py instead."
    )


def test_only_backend_imports_mc_library() -> None:
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
