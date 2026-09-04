from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class ValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One stable, machine-readable validation finding.

    V0.3 enriches the V0.2 coordinates with an optional safe value preview,
    constraint name, and compact JSON-oriented context. The original positional
    constructor remains compatible.
    """

    rule: str
    message: str
    severity: ValidationSeverity
    field: str | None = None
    row_index: int | None = None
    value_preview: str | None = None
    constraint: str | None = None
    context: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.context is not None:
            object.__setattr__(self, "context", MappingProxyType(dict(self.context)))

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
            "value_preview": self.value_preview,
            "constraint": self.constraint,
            "context": dict(self.context) if self.context is not None else None,
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
