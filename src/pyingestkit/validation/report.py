from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    rule: str
    message: str
    severity: ValidationSeverity
    field: str | None = None
    row_index: int | None = None

    @property
    def code(self) -> str:
        return self.rule

    def as_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "row_index": self.row_index,
        }


@dataclass(slots=True)
class ValidationReport:
    """Mutable compatibility report retained for the V0.1 validation-rule API."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.WARNING for issue in self.issues)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.as_dict() for issue in self.issues],
        }
