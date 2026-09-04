from __future__ import annotations

from dataclasses import dataclass

from .report import ValidationIssue, ValidationSeverity


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()
    issues_truncated: bool = False

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.WARNING for issue in self.issues)

    @property
    def review_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.REVIEW for issue in self.issues)

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.is_valid,
            "issue_count": self.issue_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "review_count": self.review_count,
            "issues_truncated": self.issues_truncated,
            "issues": [issue.as_dict() for issue in self.issues],
        }
