"""PyIngestKit 2.0 validation API."""

from .report import ValidationIssue, ValidationSeverity
from .result import ValidationResult
from .v2 import (
    MinimumRowsV2,
    RequiredFieldV2,
    UniqueFieldV2,
    ValidationLimits,
    ValidationRequest,
    ValidationRuleV2,
    validate_v2,
)

__all__ = [
    "MinimumRowsV2",
    "RequiredFieldV2",
    "UniqueFieldV2",
    "ValidationIssue",
    "ValidationLimits",
    "ValidationRequest",
    "ValidationResult",
    "ValidationRuleV2",
    "ValidationSeverity",
    "validate_v2",
]
