"""Portable references to PyIngestKit ingestion executions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.runtime.status import IngestionStatus
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_contract_version,
    validate_optional_text,
    validate_owner,
)


@dataclass(frozen=True, slots=True)
class IngestionExecutionReference:
    """Minimal cross-boundary reference to one PyIngestKit IngestionRun."""

    CONTRACT_ID: ClassVar[str] = "pykit.ingestion_execution_reference"

    ingestion_run_id: IngestionRunId
    ingestion_definition_id: str | None = None
    output_dataset_version: DatasetVersionReference | None = None
    status: IngestionStatus | None = None
    owner: str = "pyingestkit"
    namespace: str = "pyingestkit.execution"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError(
                "IngestionExecutionReference ingestion_run_id must be an IngestionRunId."
            )
        validate_optional_text(
            self.ingestion_definition_id,
            "IngestionExecutionReference ingestion_definition_id",
        )
        if self.output_dataset_version is not None and not isinstance(
            self.output_dataset_version,
            DatasetVersionReference,
        ):
            raise TypeError(
                "IngestionExecutionReference output_dataset_version must be "
                "a DatasetVersionReference."
            )
        if self.status is not None:
            if not isinstance(self.status, IngestionStatus):
                raise TypeError("IngestionExecutionReference status must be an IngestionStatus.")
            if not self.status.terminal:
                raise ValueError(
                    "IngestionExecutionReference status must be terminal when provided."
                )
        validate_owner(self.owner)
        require_non_blank(self.namespace, "IngestionExecutionReference namespace")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
