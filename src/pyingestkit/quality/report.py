from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from pyingestkit.profiling import DatasetProfile
from pyingestkit.validation import ValidationResult


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Portable in-memory aggregate of validation and profiling evidence."""

    run_id: str
    job_id: str
    source_artifact_id: str | None = None
    validation: ValidationResult | None = None
    profile: DatasetProfile | None = None
    report_version: str = "1"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "source_artifact_id": self.source_artifact_id,
            "generated_at": self.generated_at.isoformat(),
            "validation": self.validation.as_dict() if self.validation else None,
            "profile": self.profile.as_dict() if self.profile else None,
        }
