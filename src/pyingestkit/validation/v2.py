"""V2 validation foundation over dependency-neutral decoded representations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.decoding import DecodedRepresentation, DecodedValue
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import require_non_blank

from .report import ValidationIssue, ValidationSeverity
from .result import ValidationResult


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Resource bounds for deterministic issue collection."""

    max_issues: int = 1000

    def __post_init__(self) -> None:
        if not isinstance(self.max_issues, int):
            raise TypeError("ValidationLimits max_issues must be int.")
        if self.max_issues < 1:
            raise ValueError("ValidationLimits max_issues must be positive.")


@dataclass(frozen=True, slots=True)
class ValidationRequest:
    """One explicit validation request over LOT-05 decoded evidence."""

    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    artifact: ArtifactReference
    decoder_id: str
    representation: DecodedRepresentation
    limits: ValidationLimits = ValidationLimits()

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("ValidationRequest ingestion_run_id must be an IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("ValidationRequest correlation must be a CorrelationContext.")
        if not isinstance(self.artifact, ArtifactReference):
            raise TypeError("ValidationRequest artifact must be an ArtifactReference.")
        require_non_blank(self.decoder_id, "ValidationRequest decoder_id")
        if not isinstance(self.representation, DecodedRepresentation):
            raise TypeError("ValidationRequest representation must be DecodedRepresentation.")
        if not isinstance(self.limits, ValidationLimits):
            raise TypeError("ValidationRequest limits must be ValidationLimits.")
        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "ValidationRequest correlation ingestion_run_id must match the native IngestionRunId."
            )


@runtime_checkable
class ValidationRuleV2(Protocol):
    """Pure validation rule over a decoded representation."""

    @property
    def id(self) -> str: ...

    def evaluate(self, representation: DecodedRepresentation) -> tuple[ValidationIssue, ...]: ...


@dataclass(frozen=True, slots=True)
class MinimumRowsV2:
    minimum: int
    severity: ValidationSeverity = ValidationSeverity.ERROR
    id: str = "minimum_rows"

    def __post_init__(self) -> None:
        if not isinstance(self.minimum, int):
            raise TypeError("MinimumRowsV2 minimum must be int.")
        if self.minimum < 0:
            raise ValueError("MinimumRowsV2 minimum must be non-negative.")

    def evaluate(self, representation: DecodedRepresentation) -> tuple[ValidationIssue, ...]:
        count = len(representation)
        if count >= self.minimum:
            return ()
        return (
            ValidationIssue(
                self.id,
                f"Expected at least {self.minimum} rows, got {count}",
                self.severity,
                constraint="minimum_rows",
                context={"minimum": self.minimum, "actual": count},
            ),
        )


@dataclass(frozen=True, slots=True)
class RequiredFieldV2:
    field: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    id: str = "required_field"

    def __post_init__(self) -> None:
        require_non_blank(self.field, "RequiredFieldV2 field")

    def evaluate(self, representation: DecodedRepresentation) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        for index, record in enumerate(representation.records):
            try:
                value = record.get(self.field)
            except KeyError:
                value = None
            if value is None or value == "":
                issues.append(
                    ValidationIssue(
                        self.id,
                        f"Missing required field {self.field!r} at row {index}",
                        self.severity,
                        field=self.field,
                        row_index=index,
                        constraint="required",
                    )
                )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class UniqueFieldV2:
    field: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    id: str = "unique_field"

    def __post_init__(self) -> None:
        require_non_blank(self.field, "UniqueFieldV2 field")

    def evaluate(self, representation: DecodedRepresentation) -> tuple[ValidationIssue, ...]:
        seen: list[DecodedValue] = []
        issues: list[ValidationIssue] = []
        for index, record in enumerate(representation.records):
            try:
                value = record.get(self.field)
            except KeyError:
                continue
            if any(value == previous for previous in seen):
                issues.append(
                    ValidationIssue(
                        self.id,
                        f"Duplicate {self.field!r} value at row {index}",
                        self.severity,
                        field=self.field,
                        row_index=index,
                        constraint="unique",
                    )
                )
            else:
                seen.append(value)
        return tuple(issues)


def validate_v2(
    request: ValidationRequest,
    rules: tuple[ValidationRuleV2, ...],
) -> ValidationResult:
    """Evaluate rules deterministically and bound retained issue evidence."""

    if not isinstance(rules, tuple):
        raise TypeError("validate_v2 rules must be a tuple.")

    issues: list[ValidationIssue] = []
    truncated = False
    for rule in rules:
        if not isinstance(rule, ValidationRuleV2):
            raise TypeError("validate_v2 rules must implement ValidationRuleV2.")
        for issue in rule.evaluate(request.representation):
            if len(issues) >= request.limits.max_issues:
                truncated = True
                break
            issues.append(issue)
        if truncated:
            break
    return ValidationResult(tuple(issues), issues_truncated=truncated)
