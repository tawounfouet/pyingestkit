from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .report import ValidationIssue, ValidationReport, ValidationSeverity

Row = Mapping[str, Any]


class ValidationRule(ABC):
    severity: ValidationSeverity = ValidationSeverity.ERROR

    @abstractmethod
    def check(self, rows: Sequence[Row]) -> ValidationIssue | None:
        raise NotImplementedError


class MinimumRows(ValidationRule):
    def __init__(self, minimum: int, *, severity: ValidationSeverity = ValidationSeverity.ERROR) -> None:
        self.minimum = minimum
        self.severity = severity

    def check(self, rows: Sequence[Row]) -> ValidationIssue | None:
        if len(rows) < self.minimum:
            return ValidationIssue(
                rule=self.__class__.__name__,
                message=f"Expected at least {self.minimum} rows, got {len(rows)}",
                severity=self.severity,
            )
        return None


class RequiredField(ValidationRule):
    def __init__(self, field: str, *, severity: ValidationSeverity = ValidationSeverity.ERROR) -> None:
        self.field = field
        self.severity = severity

    def check(self, rows: Sequence[Row]) -> ValidationIssue | None:
        missing = sum(1 for row in rows if row.get(self.field) in (None, ""))
        if missing:
            return ValidationIssue(
                rule=self.__class__.__name__,
                message=f"Field '{self.field}' is missing/empty in {missing} row(s)",
                severity=self.severity,
            )
        return None


class UniqueField(ValidationRule):
    def __init__(self, field: str, *, severity: ValidationSeverity = ValidationSeverity.ERROR) -> None:
        self.field = field
        self.severity = severity

    def check(self, rows: Sequence[Row]) -> ValidationIssue | None:
        seen: set[Any] = set()
        duplicates = 0
        for row in rows:
            value = row.get(self.field)
            if value in seen:
                duplicates += 1
            else:
                seen.add(value)
        if duplicates:
            return ValidationIssue(
                rule=self.__class__.__name__,
                message=f"Field '{self.field}' contains {duplicates} duplicate value(s)",
                severity=self.severity,
            )
        return None


def validate(rows: Iterable[Row], rules: Iterable[ValidationRule]) -> ValidationReport:
    materialized = list(rows)
    report = ValidationReport()
    for rule in rules:
        issue = rule.check(materialized)
        if issue is not None:
            report.add(issue)
    return report
