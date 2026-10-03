"""Internal, machine-readable PyIngestKit V2 architecture baseline."""

from __future__ import annotations

V2_ARCHITECTURE_LAYERS: tuple[str, ...] = (
    "domain",
    "application",
    "runtime",
    "ports",
    "adapters",
    "serialization",
    "observability",
    "plugins",
    "integrations",
)

# The 2.0 RC promotes the V2 runtime to the canonical package surface. Legacy
# implementation modules may remain in-tree for migration history but no longer
# define the stable root contract.
V2_TRANSITIONAL_LEGACY_PACKAGES: frozenset[str] = frozenset({"cli", "config", "plugins"})
V2_QUALIFIED_RUNTIME_SURFACE = "pyingestkit.runtime"
V2_FORBIDDEN_V2_EXECUTION_IMPORTS: frozenset[str] = frozenset(
    {"pyingestkit.runtime.runner", "pyingestkit.core"}
)

V2_SUPPORTED_PYTHON: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")

V2_DEPENDENCY_DISPOSITION: dict[str, str] = {
    "typer": "LEGACY_CLI_NOT_INSTALLED_BY_2_0_RC",
    "rich": "LEGACY_CLI_NOT_INSTALLED_BY_2_0_RC",
    "pydantic": "BASE_CANDIDATE",
    "PyYAML": "BASE_CANDIDATE",
    "SQLAlchemy": "OPTIONAL_POSTGRES",
    "httpx": "OPTIONAL_HTTP",
    "tenacity": "LEGACY_RETRY_NOT_REQUIRED_BY_V2_CORE",
    "python-dotenv": "BASE_CANDIDATE",
    "psycopg": "OPTIONAL_POSTGRES",
    "boto3": "OPTIONAL_S3_LOT15",
    "openpyxl": "OPTIONAL_EXCEL",
    "pyarrow": "OPTIONAL_PARQUET",
    "pytransformkit": "OPTIONAL_TRANSFORM_LOT17_QUALIFIED",
}
