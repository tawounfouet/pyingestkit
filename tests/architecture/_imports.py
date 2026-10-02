from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "pyingestkit"


def python_files(*relative_roots: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for relative in relative_roots:
        root = PACKAGE_ROOT / relative
        if root.is_file() and root.suffix == ".py":
            paths.append(root)
        elif root.is_dir():
            paths.extend(sorted(root.rglob("*.py")))
    return tuple(paths)


def imports_in(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return frozenset(modules)


def imported_roots(paths: Iterable[Path]) -> dict[Path, frozenset[str]]:
    return {path: imports_in(path) for path in paths}


def matches_prefix(module: str, prefixes: Iterable[str]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)
