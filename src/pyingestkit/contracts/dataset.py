from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from pyingestkit.dataset import Dataset
from pyingestkit.validation import ValidationIssue, ValidationResult, ValidationSeverity

ExpectedType = type[Any] | tuple[type[Any], ...]

_SECRET_FIELD = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|cookie|credential)",
    re.IGNORECASE,
)
_PREVIEW_LIMIT = 96


def _safe_preview(field: str | None, value: Any) -> str:
    if field is not None and _SECRET_FIELD.search(field):
        return "[REDACTED]"
    preview = repr(value)
    if len(preview) > _PREVIEW_LIMIT:
        return preview[: _PREVIEW_LIMIT - 1] + "…"
    return preview


def _stable_identity(value: Any) -> object:
    """Create a hashable identity for common Python/JSON values.

    Dataset remains engine-neutral and may contain nested JSON values. This
    helper is intentionally structural rather than semantic: it never coerces
    strings, numbers, dates, or business identifiers.
    """

    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return (type(value).__name__, value)
    if isinstance(value, tuple):
        return ("tuple", tuple(_stable_identity(item) for item in value))
    if isinstance(value, list):
        return ("list", tuple(_stable_identity(item) for item in value))
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple(
                sorted(
                    ((str(key), _stable_identity(item)) for key, item in value.items()),
                    key=lambda pair: pair[0],
                )
            ),
        )
    if isinstance(value, (set, frozenset)):
        frozen = [_stable_identity(item) for item in value]
        return ("set", tuple(sorted(frozen, key=repr)))
    try:
        hash(value)
    except TypeError:
        return (type(value).__name__, repr(value))
    return (type(value).__name__, value)


@dataclass(slots=True)
class _IssueCollector:
    max_issues: int | None
    issues: list[ValidationIssue]
    truncated: bool = False

    @classmethod
    def create(cls, max_issues: int | None) -> _IssueCollector:
        return cls(max_issues=max_issues, issues=[])

    def add(self, issue: ValidationIssue) -> bool:
        if self.max_issues is None or len(self.issues) < self.max_issues:
            self.issues.append(issue)
            return True
        self.truncated = True
        return False


@dataclass(frozen=True, slots=True)
class FieldContract:
    name: str
    required: bool = True
    nullable: bool = True
    expected_type: ExpectedType | None = None
    unique: bool = False
    allowed_values: Collection[Any] | None = None
    pattern: str | None = None
    min_value: Any | None = None
    max_value: Any | None = None
    min_length: int | None = None
    max_length: int | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("FieldContract.name must not be empty")
        if isinstance(self.expected_type, tuple) and not self.expected_type:
            raise ValueError("FieldContract.expected_type tuple must not be empty")
        if self.allowed_values is not None and not isinstance(self.allowed_values, tuple):
            values = tuple(self.allowed_values)
            if isinstance(self.allowed_values, (set, frozenset)):
                values = tuple(sorted(values, key=repr))
            object.__setattr__(self, "allowed_values", values)
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"FieldContract.pattern is invalid: {exc}") from exc
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("FieldContract.min_length must be >= 0")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("FieldContract.max_length must be >= 0")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError("FieldContract.min_length must be <= max_length")
        if self.min_value is not None and self.max_value is not None:
            try:
                if self.min_value > self.max_value:
                    raise ValueError("FieldContract.min_value must be <= max_value")
            except TypeError:
                # Runtime values may still be comparable with one side. The
                # validation engine reports incompatible observations safely.
                pass


@dataclass(frozen=True, slots=True)
class DatasetContract:
    fields: tuple[FieldContract, ...] = ()
    allow_extra_fields: bool = True
    min_rows: int | None = None
    max_rows: int | None = None
    unique_together: tuple[tuple[str, ...], ...] = ()
    primary_key: tuple[str, ...] = ()
    max_issues: int | None = 1000

    def __post_init__(self) -> None:
        names = tuple(field.name for field in self.fields)
        if len(names) != len(set(names)):
            raise ValueError("DatasetContract field names must be unique")
        if self.min_rows is not None and self.min_rows < 0:
            raise ValueError("DatasetContract.min_rows must be >= 0")
        if self.max_rows is not None and self.max_rows < 0:
            raise ValueError("DatasetContract.max_rows must be >= 0")
        if (
            self.min_rows is not None
            and self.max_rows is not None
            and self.min_rows > self.max_rows
        ):
            raise ValueError("DatasetContract.min_rows must be <= max_rows")
        if self.max_issues is not None and self.max_issues <= 0:
            raise ValueError("DatasetContract.max_issues must be > 0 or None")

        unique_together = tuple(tuple(group) for group in self.unique_together)
        for group in unique_together:
            if len(group) < 2:
                raise ValueError("DatasetContract.unique_together groups need at least two fields")
            if any(not name for name in group):
                raise ValueError("DatasetContract.unique_together field names must not be empty")
            if len(group) != len(set(group)):
                raise ValueError("DatasetContract.unique_together groups must not repeat fields")
        if len(unique_together) != len(set(unique_together)):
            raise ValueError("DatasetContract.unique_together groups must be unique")
        object.__setattr__(self, "unique_together", unique_together)

        primary_key = tuple(self.primary_key)
        if any(not name for name in primary_key):
            raise ValueError("DatasetContract.primary_key field names must not be empty")
        if len(primary_key) != len(set(primary_key)):
            raise ValueError("DatasetContract.primary_key fields must be unique")
        object.__setattr__(self, "primary_key", primary_key)

    def validate(self, dataset: Dataset) -> ValidationResult:
        collector = _IssueCollector.create(self.max_issues)
        self._validate_row_count(dataset, collector)
        if collector.truncated:
            return self._result(collector)

        contract_by_name = {field.name: field for field in self.fields}
        self._validate_schema(dataset, contract_by_name, collector)
        if collector.truncated:
            return self._result(collector)

        for contract in self.fields:
            if contract.name in dataset.fields:
                self._validate_field(dataset, contract, collector)
                if collector.truncated:
                    return self._result(collector)

        self._validate_unique_together(dataset, collector)
        if collector.truncated:
            return self._result(collector)
        self._validate_primary_key(dataset, collector)
        return self._result(collector)

    @staticmethod
    def _result(collector: _IssueCollector) -> ValidationResult:
        return ValidationResult(tuple(collector.issues), issues_truncated=collector.truncated)

    def _validate_row_count(self, dataset: Dataset, collector: _IssueCollector) -> None:
        # Existing V0.2 codes are intentionally retained for compatibility.
        if self.min_rows is not None and dataset.row_count < self.min_rows:
            collector.add(
                ValidationIssue(
                    "dataset.min_rows",
                    f"Expected at least {self.min_rows} rows, got {dataset.row_count}",
                    ValidationSeverity.ERROR,
                    constraint="min_rows",
                    context={"minimum": self.min_rows, "actual": dataset.row_count},
                )
            )
        if self.max_rows is not None and dataset.row_count > self.max_rows:
            collector.add(
                ValidationIssue(
                    "dataset.max_rows",
                    f"Expected at most {self.max_rows} rows, got {dataset.row_count}",
                    ValidationSeverity.ERROR,
                    constraint="max_rows",
                    context={"maximum": self.max_rows, "actual": dataset.row_count},
                )
            )

    def _validate_schema(
        self,
        dataset: Dataset,
        contract_by_name: dict[str, FieldContract],
        collector: _IssueCollector,
    ) -> None:
        dataset_fields = set(dataset.fields)
        for contract in self.fields:
            if contract.required and contract.name not in dataset_fields:
                if not collector.add(
                    ValidationIssue(
                        "field.required",
                        f"Required field {contract.name!r} is missing from the dataset schema",
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        constraint="required",
                    )
                ):
                    return
        if not self.allow_extra_fields:
            for field in dataset.fields:
                if field not in contract_by_name:
                    if not collector.add(
                        ValidationIssue(
                            "dataset.extra_field",
                            f"Unexpected field {field!r}",
                            ValidationSeverity.ERROR,
                            field=field,
                            constraint="allow_extra_fields",
                        )
                    ):
                        return

    def _validate_field(
        self,
        dataset: Dataset,
        contract: FieldContract,
        collector: _IssueCollector,
    ) -> None:
        seen: dict[object, int] = {}
        for row_index, row in enumerate(dataset):
            if contract.name not in row:
                if contract.required and not collector.add(
                    ValidationIssue(
                        "field.required",
                        f"Required field {contract.name!r} is missing from row {row_index}",
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        row_index=row_index,
                        constraint="required",
                    )
                ):
                    return
                continue

            value = row[contract.name]
            if value is None:
                if not contract.nullable and not collector.add(
                    ValidationIssue(
                        "field.null",
                        f"Field {contract.name!r} must not be null",
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        row_index=row_index,
                        constraint="nullable",
                    )
                ):
                    return
                continue

            type_matches = True
            expected = contract.expected_type
            if expected is not None:
                type_matches = isinstance(value, expected)
                if not type_matches:
                    if not collector.add(
                        ValidationIssue(
                            "field.type",
                            (
                                f"Field {contract.name!r} has type {type(value).__name__}; "
                                f"expected {self._type_label(expected)}"
                            ),
                            ValidationSeverity.ERROR,
                            field=contract.name,
                            row_index=row_index,
                            value_preview=_safe_preview(contract.name, value),
                            constraint="expected_type",
                        )
                    ):
                        return

            if contract.allowed_values is not None and not any(
                value == allowed for allowed in contract.allowed_values
            ):
                if not collector.add(
                    ValidationIssue(
                        "field.allowed_values",
                        f"Field {contract.name!r} contains a value outside the allowed set",
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        row_index=row_index,
                        value_preview=_safe_preview(contract.name, value),
                        constraint="allowed_values",
                        context={"allowed_count": len(contract.allowed_values)},
                    )
                ):
                    return

            if contract.pattern is not None:
                pattern_matches = (
                    isinstance(value, str) and re.fullmatch(contract.pattern, value) is not None
                )
                if not pattern_matches and not collector.add(
                    ValidationIssue(
                        "field.pattern",
                        (
                            f"Field {contract.name!r} does not satisfy the configured "
                            "full-match pattern"
                        ),
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        row_index=row_index,
                        value_preview=_safe_preview(contract.name, value),
                        constraint="pattern",
                        context={"requires_string": not isinstance(value, str)},
                    )
                ):
                    return

            if type_matches and contract.min_value is not None:
                if not self._validate_min_value(contract, value, row_index, collector):
                    return
            if type_matches and contract.max_value is not None:
                if not self._validate_max_value(contract, value, row_index, collector):
                    return
            if type_matches and contract.min_length is not None:
                if not self._validate_min_length(contract, value, row_index, collector):
                    return
            if type_matches and contract.max_length is not None:
                if not self._validate_max_length(contract, value, row_index, collector):
                    return

            if contract.unique:
                identity = _stable_identity(value)
                previous = seen.get(identity)
                if previous is not None:
                    if not collector.add(
                        ValidationIssue(
                            "field.unique",
                            (
                                f"Field {contract.name!r} duplicates a value first seen "
                                f"at row {previous}"
                            ),
                            ValidationSeverity.ERROR,
                            field=contract.name,
                            row_index=row_index,
                            value_preview=_safe_preview(contract.name, value),
                            constraint="unique",
                            context={"first_row_index": previous},
                        )
                    ):
                        return
                else:
                    seen[identity] = row_index

    @staticmethod
    def _validate_min_value(
        contract: FieldContract,
        value: Any,
        row_index: int,
        collector: _IssueCollector,
    ) -> bool:
        try:
            violated = value < contract.min_value
        except TypeError:
            violated = True
            reason = "not_comparable"
        else:
            reason = "below_minimum" if violated else ""
        if not violated:
            return True
        return collector.add(
            ValidationIssue(
                "field.min_value",
                f"Field {contract.name!r} does not satisfy its minimum value constraint",
                ValidationSeverity.ERROR,
                field=contract.name,
                row_index=row_index,
                value_preview=_safe_preview(contract.name, value),
                constraint="min_value",
                context={"minimum": contract.min_value, "reason": reason},
            )
        )

    @staticmethod
    def _validate_max_value(
        contract: FieldContract,
        value: Any,
        row_index: int,
        collector: _IssueCollector,
    ) -> bool:
        try:
            violated = value > contract.max_value
        except TypeError:
            violated = True
            reason = "not_comparable"
        else:
            reason = "above_maximum" if violated else ""
        if not violated:
            return True
        return collector.add(
            ValidationIssue(
                "field.max_value",
                f"Field {contract.name!r} does not satisfy its maximum value constraint",
                ValidationSeverity.ERROR,
                field=contract.name,
                row_index=row_index,
                value_preview=_safe_preview(contract.name, value),
                constraint="max_value",
                context={"maximum": contract.max_value, "reason": reason},
            )
        )

    @staticmethod
    def _validate_min_length(
        contract: FieldContract,
        value: Any,
        row_index: int,
        collector: _IssueCollector,
    ) -> bool:
        minimum = contract.min_length
        if minimum is None:
            return True
        if not isinstance(value, str):
            violated = True
            actual_length: int | None = None
            reason = "requires_string"
        else:
            actual_length = len(value)
            violated = actual_length < minimum
            reason = "below_minimum" if violated else ""
        if not violated:
            return True
        return collector.add(
            ValidationIssue(
                "field.min_length",
                f"Field {contract.name!r} does not satisfy its minimum string length",
                ValidationSeverity.ERROR,
                field=contract.name,
                row_index=row_index,
                value_preview=_safe_preview(contract.name, value),
                constraint="min_length",
                context={
                    "minimum": minimum,
                    "actual": actual_length,
                    "reason": reason,
                },
            )
        )

    @staticmethod
    def _validate_max_length(
        contract: FieldContract,
        value: Any,
        row_index: int,
        collector: _IssueCollector,
    ) -> bool:
        maximum = contract.max_length
        if maximum is None:
            return True
        if not isinstance(value, str):
            violated = True
            actual_length: int | None = None
            reason = "requires_string"
        else:
            actual_length = len(value)
            violated = actual_length > maximum
            reason = "above_maximum" if violated else ""
        if not violated:
            return True
        return collector.add(
            ValidationIssue(
                "field.max_length",
                f"Field {contract.name!r} does not satisfy its maximum string length",
                ValidationSeverity.ERROR,
                field=contract.name,
                row_index=row_index,
                value_preview=_safe_preview(contract.name, value),
                constraint="max_length",
                context={
                    "maximum": maximum,
                    "actual": actual_length,
                    "reason": reason,
                },
            )
        )

    def _validate_unique_together(self, dataset: Dataset, collector: _IssueCollector) -> None:
        for fields in self.unique_together:
            seen: dict[tuple[object, ...], int] = {}
            for row_index, row in enumerate(dataset):
                if any(field not in row for field in fields):
                    continue
                identity = tuple(_stable_identity(row[field]) for field in fields)
                previous = seen.get(identity)
                if previous is not None:
                    if not collector.add(
                        ValidationIssue(
                            "dataset.unique_together",
                            (
                                f"Fields {fields!r} duplicate a combination first seen "
                                f"at row {previous}"
                            ),
                            ValidationSeverity.ERROR,
                            row_index=row_index,
                            constraint="unique_together",
                            context={"fields": list(fields), "first_row_index": previous},
                        )
                    ):
                        return
                else:
                    seen[identity] = row_index

    def _validate_primary_key(self, dataset: Dataset, collector: _IssueCollector) -> None:
        if not self.primary_key:
            return

        dataset_fields = set(dataset.fields)
        missing_schema = [field for field in self.primary_key if field not in dataset_fields]
        for field in missing_schema:
            if not collector.add(
                ValidationIssue(
                    "dataset.required_field",
                    f"Primary-key field {field!r} is missing from the dataset schema",
                    ValidationSeverity.ERROR,
                    field=field,
                    constraint="primary_key",
                )
            ):
                return
        if missing_schema:
            return

        seen: dict[tuple[object, ...], int] = {}
        for row_index, row in enumerate(dataset):
            missing_row = [field for field in self.primary_key if field not in row]
            null_fields = [
                field for field in self.primary_key if field in row and row[field] is None
            ]
            if missing_row or null_fields:
                fields = missing_row + null_fields
                if not collector.add(
                    ValidationIssue(
                        "key.null",
                        f"Primary key contains missing or null field(s): {', '.join(fields)}",
                        ValidationSeverity.ERROR,
                        row_index=row_index,
                        constraint="primary_key",
                        context={"fields": fields},
                    )
                ):
                    return
                continue

            identity = tuple(_stable_identity(row[field]) for field in self.primary_key)
            previous = seen.get(identity)
            if previous is not None:
                if not collector.add(
                    ValidationIssue(
                        "key.duplicate",
                        f"Primary key duplicates a combination first seen at row {previous}",
                        ValidationSeverity.ERROR,
                        row_index=row_index,
                        constraint="primary_key",
                        context={
                            "fields": list(self.primary_key),
                            "first_row_index": previous,
                        },
                    )
                ):
                    return
            else:
                seen[identity] = row_index

    @staticmethod
    def _type_label(expected: ExpectedType) -> str:
        types = expected if isinstance(expected, tuple) else (expected,)
        return " | ".join(item.__name__ for item in types)
