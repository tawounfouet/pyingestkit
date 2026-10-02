from __future__ import annotations

from ._imports import PACKAGE_ROOT, imports_in


def test_pytransformkit_imports_are_integration_only() -> None:
    violations: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        modules = imports_in(path)
        if any(module == "pytransformkit" or module.startswith("pytransformkit.") for module in modules):
            relative = path.relative_to(PACKAGE_ROOT)
            if not str(relative).startswith("integrations/pytransformkit/"):
                violations.append(str(relative))
    assert not violations, "\n".join(violations)


def test_pyworkflowkit_is_absent_from_pyingestkit_core() -> None:
    violations: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        modules = imports_in(path)
        if any(module == "pyworkflowkit" or module.startswith("pyworkflowkit.") for module in modules):
            violations.append(str(path.relative_to(PACKAGE_ROOT)))
    assert not violations, "\n".join(violations)
