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
# migrated lot by lot. New V2 code must not depend on their legacy execution model.
V2_TRANSITIONAL_LEGACY_PACKAGES: frozenset[str] = frozenset(
    {"cli", "config", "plugins", "runtime"}
)

V2_SUPPORTED_PYTHON: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")

V2_DEPENDENCY_DISPOSITION: dict[str, str] = {
    "typer": "BASE_CANDIDATE",
    "rich": "BASE_CANDIDATE",
    "pydantic": "BASE_CANDIDATE",
    "PyYAML": "BASE_CANDIDATE",
    "SQLAlchemy": "TRANSITIONAL_BASE_REVIEW_LOT08_LOT14",
    "httpx": "TRANSITIONAL_BASE_TARGET_HTTP_EXTRA_LOT13",
    "tenacity": "BASE_CANDIDATE",
    "python-dotenv": "BASE_CANDIDATE",
    "psycopg": "OPTIONAL_POSTGRES",
    "boto3": "OPTIONAL_S3",
    "openpyxl": "OPTIONAL_EXCEL",
    "pyarrow": "OPTIONAL_PARQUET",
    "pytransformkit": "OPTIONAL_TRANSFORM_LOT17",
}
