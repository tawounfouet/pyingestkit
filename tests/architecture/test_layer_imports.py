from __future__ import annotations

from ._imports import imported_roots, matches_prefix, python_files

PROVIDER_MODULES = {
    "boto3",
    "botocore",
    "duckdb",
    "httpx",
    "openpyxl",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "requests",
    "sqlalchemy",
}


def _assert_no_imports(layer: str, forbidden: set[str]) -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files(layer)).items():
        for module in modules:
            if matches_prefix(module, forbidden):
                violations.append(f"{path.relative_to(path.parents[3])}: {module}")
    assert not violations, "\n".join(violations)


def test_domain_has_no_provider_imports() -> None:
    _assert_no_imports("domain", PROVIDER_MODULES)


def test_domain_does_not_depend_on_outer_layers() -> None:
    _assert_no_imports(
        "domain",
        {
            "pyingestkit.adapters",
            "pyingestkit.application",
            "pyingestkit.cli",
            "pyingestkit.integrations",
            "pyingestkit.plugins",
            "pyingestkit.runtime",
        },
    )


def test_application_depends_on_ports_not_adapters() -> None:
    _assert_no_imports("application", PROVIDER_MODULES | {"pyingestkit.adapters"})


def test_ports_do_not_depend_on_adapters_or_runtime() -> None:
    _assert_no_imports(
        "ports",
        {"pyingestkit.adapters", "pyingestkit.application", "pyingestkit.runtime"},
    )


def test_new_v2_runtime_provider_rule_is_reserved_during_transition() -> None:
    # The V1 runtime package still exists on the migration branch. This test
    # prevents new V2 layers from depending on providers until LOT-12 replaces
    # the legacy Runner surface.
    _assert_no_imports("application", PROVIDER_MODULES)
