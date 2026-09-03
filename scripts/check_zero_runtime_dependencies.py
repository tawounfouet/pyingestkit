from __future__ import annotations

import ast
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source_root = root / "src" / "pyingestkit"
violations: list[str] = []

# Typer and Rich are deliberate CLI dependencies. Everything outside pyingestkit.cli
# must remain stdlib-only plus internal pyingestkit imports.
stdlib = set(sys.stdlib_module_names)
allowed_roots = stdlib | {"pyingestkit", "__future__"}

for path in sorted(source_root.rglob("*.py")):
    relative = path.relative_to(source_root)
    if relative.parts and relative.parts[0] == "cli":
        continue
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        module: str | None = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name not in allowed_roots:
                    violations.append(f"{relative}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            module = node.module
            root_name = module.split(".", 1)[0]
            if root_name not in allowed_roots:
                violations.append(f"{relative}: from {module} import ...")

if violations:
    raise SystemExit("Non-CLI runtime has third-party imports:\n" + "\n".join(violations))

print("OK: PyIngestKit non-CLI runtime remains stdlib-only; Typer/Rich are isolated to cli/")
