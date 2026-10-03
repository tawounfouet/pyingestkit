from __future__ import annotations

import ast
from pathlib import Path

from pyingestkit.integrations import pytransformkit as integration

from ._imports import imported_roots, python_files

PACKAGE_ROOT = Path("src/pyingestkit")


def test_lot17_only_integration_boundary_may_reference_pytransformkit() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files(".")).items():
        if any(
            module == "pytransformkit" or module.startswith("pytransformkit.") for module in modules
        ):
            relative = path.relative_to(PACKAGE_ROOT)
            if not str(relative).startswith("integrations/pytransformkit/"):
                violations.append(str(relative))
    assert not violations, "\n".join(violations)


def test_lot17_integration_has_no_static_sibling_import() -> None:
    source = Path("src/pyingestkit/integrations/pytransformkit/adapters.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    static_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not {
        name
        for name in static_imports
        if name == "pytransformkit" or name.startswith("pytransformkit.")
    }


def test_lot17_integration_surface_contains_no_transformation_engine() -> None:
    public = set(integration.__all__)

    assert public.isdisjoint(
        {
            "Dataset",
            "DataFrame",
            "LogicalPlan",
            "TransformationPlan",
            "TransformationRuntime",
            "join",
            "aggregate",
            "window",
            "pivot",
        }
    )
