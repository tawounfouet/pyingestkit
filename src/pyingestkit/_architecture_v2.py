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

# Existing V1 implementations remain temporarily present while the V2 branch is
# migrated lot by lot. LOT-12 establishes pyingestkit.runtime.v2 as the only
# runtime-facing surface for V2-owned code; the V1 runtime root remains solely
# for maintenance compatibility until the 2.0 package cut.
V2_TRANSITIONAL_LEGACY_PACKAGES: frozenset[str] = frozenset({"cli", "config", "plugins", "runtime"})
V2_QUALIFIED_RUNTIME_SURFACE = "pyingestkit.runtime.v2"
V2_FORBIDDEN_V2_EXECUTION_IMPORTS: frozenset[str] = frozenset(
    {"pyingestkit.runtime.runner", "pyingestkit.core"}
)

V2_SUPPORTED_PYTHON: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")

V2_DEPENDENCY_DISPOSITION: dict[str, str] = {
    "typer": "BASE_CANDIDATE",
    "rich": "BASE_CANDIDATE",
    "pydantic": "BASE_CANDIDATE",
    "PyYAML": "BASE_CANDIDATE",
    "SQLAlchemy": "TRANSITIONAL_BASE_REVIEW_LOT08_LOT14",
    "httpx": "HTTP_EXTRA_V2_BASE_RETAINED_FOR_V1_COMPAT_UNTIL_2_0",
    "tenacity": "BASE_CANDIDATE",
    "python-dotenv": "BASE_CANDIDATE",
    "psycopg": "OPTIONAL_POSTGRES",
    "boto3": "OPTIONAL_S3",
    "openpyxl": "OPTIONAL_EXCEL",
    "pyarrow": "OPTIONAL_PARQUET",
    "pytransformkit": "OPTIONAL_TRANSFORM_LOT17",
}
