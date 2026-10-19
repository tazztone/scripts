"""
Static AST import verification suite for media_toolbox headless layer.

Enforces the core architectural invariant:
Zero GUI imports (gi, Gtk, Adw, Nautilus, tkinter, PyQt, PySide, wx) across:
- All core modules (python/media_toolbox/core/*.py)
- Standalone CLI entrypoint (python/media_toolbox/cli.py)
- Package router top-level (python/media_toolbox/__main__.py)
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import pytest

FORBIDDEN_ROOTS = {
    "gi",
    "gtk",
    "adw",
    "nautilus",
    "tkinter",
    "pyqt4",
    "pyqt5",
    "pyqt6",
    "pyside",
    "pyside2",
    "pyside6",
    "wx",
    "kivy",
}

FORBIDDEN_KEYWORDS = (
    "gi",
    "Gtk",
    "Adw",
    "Nautilus",
    "tkinter",
    "PyQt",
    "PySide",
    "wx",
)


def get_toolbox_root() -> Path:
    """Return Path to python/media_toolbox root."""
    return Path(__file__).resolve().parent.parent


def discover_headless_source_files() -> list[Path]:
    """
    Dynamically discover all Python source files in core/ and cli.py.
    Guarantees that new files added to core/ are automatically verified.
    """
    toolbox_root = get_toolbox_root()
    core_dir = toolbox_root / "core"
    cli_file = toolbox_root / "cli.py"

    files: list[Path] = []
    if core_dir.is_dir():
        files.extend(sorted(core_dir.glob("*.py")))

    if cli_file.is_file():
        files.append(cli_file)

    return files


def scan_ast_for_gui_violations(source_code: str, file_label: str) -> list[str]:
    """
    Parse Python source code into AST and detect forbidden GUI imports.

    Inspects:
    1. ast.Import: `import gi`, `import tkinter`, `import PyQt5.QtCore`
    2. ast.ImportFrom: `from gi.repository import Gtk`, `from tkinter import ttk`
    3. ast.Call: `__import__('gi')`, `importlib.import_module('Gtk')`

    Returns list of formatted violation strings.
    """
    violations: list[str] = []
    try:
        tree = ast.parse(source_code, filename=file_label)
    except SyntaxError as e:
        return [f"{file_label}:{e.lineno}: Syntax error parsing file: {e.msg}"]

    for node in ast.walk(tree):
        # 1. Direct imports: `import foo, bar`
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0].lower()
                if (
                    root_pkg in FORBIDDEN_ROOTS
                    or any(k.lower() == root_pkg for k in FORBIDDEN_KEYWORDS)
                    or any(k.lower() in alias.name.lower() for k in ("pyqt", "pyside", "tkinter", "nautilus", "wx"))
                ):
                    violations.append(
                        f"{file_label}:{node.lineno}: Forbidden import 'import {alias.name}'"
                    )

        # 2. From imports: `from foo import bar`
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            parts = [p.lower() for p in mod.split(".") if p]

            # Check module path: `from gi.repository import ...`
            if (
                any(p in FORBIDDEN_ROOTS for p in parts)
                or any(k.lower() in mod.lower() for k in ("pyqt", "pyside", "tkinter", "nautilus", "wx"))
                or (parts and parts[0] in ("gi", "gtk", "adw"))
            ):
                names_str = ", ".join(a.name for a in node.names)
                violations.append(
                    f"{file_label}:{node.lineno}: Forbidden import 'from {mod} import {names_str}'"
                )
            else:
                # Check imported symbol names: `from something import Gtk, Adw`
                for alias in node.names:
                    sym_lower = alias.name.lower()
                    if (
                        sym_lower in FORBIDDEN_ROOTS
                        or any(k.lower() == sym_lower for k in FORBIDDEN_KEYWORDS)
                        or any(k.lower() in sym_lower for k in ("gtk", "adw", "pyqt", "pyside"))
                    ):
                        violations.append(
                            f"{file_label}:{node.lineno}: Forbidden symbol import 'from {mod} import {alias.name}'"
                        )

        # 3. Dynamic import calls: `__import__("gi")` or `import_module("gi")`
        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in ("__import__", "import_module"):
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    target = node.args[0].value
                    target_lower = target.lower()
                    parts = [p for p in target_lower.split(".") if p]
                    if (
                        any(p in FORBIDDEN_ROOTS for p in parts)
                        or any(k.lower() in target_lower for k in ("gi", "gtk", "adw", "nautilus", "tkinter", "pyqt", "pyside", "wx"))
                    ):
                        violations.append(
                            f"{file_label}:{node.lineno}: Forbidden dynamic import call to '{target}'"
                        )

    return violations


class TestHeadlessASTInvariant:
    """Verifies that all headless core and CLI modules contain zero GUI imports."""

    def test_file_discovery_guard(self) -> None:
        """Ensure discovery found at least 8 core/cli files (prevent false positive passes)."""
        files = discover_headless_source_files()
        assert len(files) >= 8, f"Expected at least 8 headless files, found {len(files)}: {files}"

    @pytest.mark.parametrize(
        "source_file",
        discover_headless_source_files(),
        ids=lambda p: p.name,
    )
    def test_source_file_zero_gui_imports(self, source_file: Path) -> None:
        """Verify individual source file has zero GUI imports."""
        source_code = source_file.read_text(encoding="utf-8")
        violations = scan_ast_for_gui_violations(source_code, str(source_file))

        assert not violations, (
            f"GUI import invariant violated in {source_file.name}:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestMainRouterAST:
    """Verifies __main__.py has zero top-level GUI or UI imports."""

    def test_main_router_zero_top_level_gui_imports(self) -> None:
        """Assert __main__.py has zero top-level GUI or UI imports."""
        main_file = get_toolbox_root() / "__main__.py"
        if not main_file.exists():
            pytest.skip("__main__.py does not exist yet")

        source = main_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(main_file))

        top_level_violations: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0].lower()
                    if root in FORBIDDEN_ROOTS or root.startswith("ui"):
                        top_level_violations.append(f"Line {node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0].lower()
                    if root in FORBIDDEN_ROOTS or "ui" in node.module:
                        top_level_violations.append(f"Line {node.lineno}: from {node.module} import ...")

        assert not top_level_violations, (
            "Forbidden top-level GUI/UI imports found in __main__.py:\n"
            + "\n".join(top_level_violations)
        )

    def test_runtime_headless_execution_does_not_load_gi(self) -> None:
        """Assert running CLI in headless environment never loads 'gi' into sys.modules."""
        from media_toolbox import cli

        try:
            exit_code = cli.main(["--version"])
        except SystemExit as exc:
            exit_code = exc.code
        assert exit_code == 0
        assert "gi" not in sys.modules


class TestASTScannerIntegrity:
    """Self-verification suite proving the AST scanner correctly flags violations."""

    def test_detects_import_gi(self) -> None:
        snippet = "import gi\nfrom pathlib import Path"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "import gi" in v[0]

    def test_detects_from_gi_repository_gtk(self) -> None:
        snippet = "from gi.repository import Gtk, GLib\nprint('hello')"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "from gi.repository import Gtk, GLib" in v[0]

    def test_detects_from_gi_repository_adw(self) -> None:
        snippet = "from gi.repository import Adw"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "from gi.repository import Adw" in v[0]

    def test_detects_tkinter_import(self) -> None:
        snippet = "import tkinter as tk\nimport os"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "tkinter" in v[0]

    def test_detects_pyqt_import(self) -> None:
        snippet = "from PyQt5.QtWidgets import QWidget"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "PyQt5" in v[0]

    def test_detects_pyside_import(self) -> None:
        snippet = "import PySide6.QtCore as QtCore"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 1
        assert "PySide6" in v[0]

    def test_detects_dynamic_import_call(self) -> None:
        snippet = "mod = __import__('gi')\nmod2 = importlib.import_module('PyQt6')"
        v = scan_ast_for_gui_violations(snippet, "snippet.py")
        assert len(v) == 2
        assert any("Forbidden dynamic import call" in msg for msg in v)

    def test_permits_clean_stdlib_and_core_imports(self) -> None:
        snippet = (
            "import os\n"
            "import sys\n"
            "import json\n"
            "from pathlib import Path\n"
            "from media_toolbox.core.models import MediaInfo\n"
            "from media_toolbox.core.probe import probe_media\n"
        )
        v = scan_ast_for_gui_violations(snippet, "clean.py")
        assert v == []
