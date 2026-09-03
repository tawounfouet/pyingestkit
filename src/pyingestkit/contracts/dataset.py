from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyingestkit.dataset import Dataset
from pyingestkit.validation import ValidationIssue, ValidationResult, ValidationSeverity

ExpectedType = type[Any] | tuple[type[Any], ...]


@dataclass(frozen=True, slots=True)
class FieldContract:
    name: str
    required: bool = True
    nullable: bool = True
    expected_type: ExpectedType | None = None
    unique: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("FieldContract.name must not be empty")
        if isinstance(self.expected_type, tuple) and not self.expected_type:
            raise ValueError("FieldContract.expected_type tuple must not be empty")


@dataclass(frozen=True, slots=True)
class DatasetContract:
    fields: tuple[FieldContract, ...] = ()
    allow_extra_fields: bool = True
    min_rows: int | None = None
    max_rows: int | None = None

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

    def validate(self, dataset: Dataset) -> ValidationResult:
        issues: list[ValidationIssue] = []
        self._validate_row_count(dataset, issues)
        contract_by_name = {field.name: field for field in self.fields}
        self._validate_schema(dataset, contract_by_name, issues)
        for contract in self.fields:
            if contract.name in dataset.fields:
                self._validate_field(dataset, contract, issues)
        return ValidationResult(tuple(issues))

    def _validate_row_count(self, dataset: Dataset, issues: list[ValidationIssue]) -> None:
        if self.min_rows is not None and dataset.row_count < self.min_rows:
            issues.append(
                ValidationIssue(
                    "dataset.min_rows",
                    f"Expected at least {self.min_rows} rows, got {dataset.row_count}",
                    ValidationSeverity.ERROR,
                )
            )
        if self.max_rows is not None and dataset.row_count > self.max_rows:
            issues.append(
                ValidationIssue(
                    "dataset.max_rows",
                    f"Expected at most {self.max_rows} rows, got {dataset.row_count}",
                    ValidationSeverity.ERROR,
                )
            )

    def _validate_schema(
        self,
        dataset: Dataset,
        contract_by_name: dict[str, FieldContract],
        issues: list[ValidationIssue],
    ) -> None:
        dataset_fields = set(dataset.fields)
        for contract in self.fields:
            if contract.required and contract.name not in dataset_fields:
                issues.append(
                    ValidationIssue(
                        "field.required",
                        f"Required field {contract.name!r} is missing from the dataset schema",
                        ValidationSeverity.ERROR,
                        field=contract.name,
                    )
                )
        if not self.allow_extra_fields:
            for field in dataset.fields:
                if field not in contract_by_name:
                    issues.append(
                        ValidationIssue(
                            "dataset.extra_field",
                            f"Unexpected field {field!r}",
                            ValidationSeverity.ERROR,
                            field=field,
                        )
                    )

    def _validate_field(
        self,
        dataset: Dataset,
        contract: FieldContract,
        issues: list[ValidationIssue],
    ) -> None:
        seen: dict[Any, int] = {}
        for row_index, row in enumerate(dataset):
            if contract.name not in row:
                if contract.required:
                    issues.append(
                        ValidationIssue(
                            "field.required",
                            f"Required field {contract.name!r} is missing from row {row_index}",
                            ValidationSeverity.ERROR,
                            field=contract.name,
                            row_index=row_index,
                        )
                    )
                continue

            value = row[contract.name]
            if value is None:
                if not contract.nullable:
                    issues.append(
                        ValidationIssue(
                            "field.null",
                            f"Field {contract.name!r} must not be null",
                            ValidationSeverity.ERROR,
                            field=contract.name,
                            row_index=row_index,
                        )
                    )
                continue

            if contract.expected_type is not None and not isinstance(value, contract.expected_type):
                issues.append(
                    ValidationIssue(
                        "field.type",
                        (
                            f"Field {contract.name!r} has type {type(value).__name__}; "
                            f"expected {self._type_label(contract.expected_type)}"
                        ),
                        ValidationSeverity.ERROR,
                        field=contract.name,
                        row_index=row_index,
                    )
                )

            if contract.unique:
                try:
                    previous = seen.get(value)
                    if previous is not None:
                        issues.append(
                            ValidationIssue(
                                "field.unique",
                                (
                                    f"Field {contract.name!r} duplicates a value first seen "
                                    f"at row {previous}"
                                ),
                                ValidationSeverity.ERROR,
                                field=contract.name,
                                row_index=row_index,
                            )
                        )
                    else:
                        seen[value] = row_index
                except TypeError:
                    issues.append(
                        ValidationIssue(
                            "field.unique_unhashable",
                            f"Field {contract.name!r} contains a value that cannot be compared for uniqueness",
                            ValidationSeverity.ERROR,
                            field=contract.name,
                            row_index=row_index,
                        )
                    )

    @staticmethod
    def _type_label(expected: ExpectedType) -> str:
        types = expected if isinstance(expected, tuple) else (expected,)
        return " | ".join(item.__name__ for item in types)
