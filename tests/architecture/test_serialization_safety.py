from __future__ import annotations

import ast

from ._imports import python_files

FORBIDDEN_MODULES = {"cloudpickle", "dill", "pickle"}
FORBIDDEN_CALLS = {"eval", "exec"}


def test_v2_serialization_has_no_executable_deserialization_primitives() -> None:
    violations: list[str] = []
    for path in python_files("serialization"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in FORBIDDEN_MODULES:
                        violations.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".", 1)[0] in FORBIDDEN_MODULES:
                    violations.append(f"{path}: from {node.module}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    violations.append(f"{path}: {node.func.id}()")
    assert not violations, "\n".join(violations)
