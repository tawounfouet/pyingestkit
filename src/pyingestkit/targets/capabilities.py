from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetCapabilities:
    """Explicit backend capabilities; callers must not infer them from backend names."""

    transactional: bool = False
    bulk_load: bool = False
    append: bool = False
    truncate_load: bool = False
    replace: bool = False
    upsert: bool = False
    staging: bool = False
    row_count_verification: bool = False
    schema_creation: bool = False
