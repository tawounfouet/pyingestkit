from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .report import ValidationIssue, ValidationReport, ValidationSeverity


class ValidationRule(ABC):
    @abstractmethod
    def evaluate(self, data: Any) -> ValidationIssue | None:
        raise NotImplementedError


class MinimumRows(ValidationRule):
    def __init__(
        self,
        minimum: int,
        *,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        self.minimum = minimum
        self.severity = severity

    def evaluate(self, data: Any) -> ValidationIssue | None:
        try:
            count = len(data)
        except TypeError:
            return ValidationIssue("minimum_rows", "Object has no row count", self.severity)
        if count < self.minimum:
            return ValidationIssue(
                "minimum_rows",
                f"Expected at least {self.minimum} rows, got {count}",
                self.severity,
            )
        return None


class RequiredField(ValidationRule):
    def __init__(
        self,
        field: str,
        *,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        self.field = field
        self.severity = severity

    def evaluate(self, data: Any) -> ValidationIssue | None:
        for index, row in enumerate(data):
            if not isinstance(row, dict) or self.field not in row or row[self.field] in (None, ""):
                return ValidationIssue(
                    "required_field",
                    f"Missing required field {self.field!r} at row {index}",
                    self.severity,
                )
        return None


class UniqueField(ValidationRule):
    def __init__(
        self,
        field: str,
        *,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        self.field = field
        self.severity = severity

    def evaluate(self, data: Any) -> ValidationIssue | None:
        seen: set[Any] = set()
        for index, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            value = row.get(self.field)
            if value in seen:
                return ValidationIssue(
                    "unique_field",
                    f"Duplicate {self.field!r} value {value!r} at row {index}",
                    self.severity,
                )
            seen.add(value)
        return None


def validate(data: Any, rules: list[ValidationRule]) -> ValidationReport:
    report = ValidationReport()
    for rule in rules:
        issue = rule.evaluate(data)
        if issue is not None:
            report.add(issue)
    return report
