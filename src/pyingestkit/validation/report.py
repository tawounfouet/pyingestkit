from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    rule: str
    message: str
    severity: ValidationSeverity


@dataclass(slots=True)
class ValidationReport:
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
            "issues": [
                {"rule": i.rule, "message": i.message, "severity": i.severity.value}
                for i in self.issues
            ],
        }
