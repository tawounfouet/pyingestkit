"""Qualified PyIngestKit V2 runtime API during the V1 transition."""

from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.domain.runtime.execution import IngestionResult, IngestionRun

__all__ = ["IngestionResult", "IngestionRun", "IngestionRuntime"]
