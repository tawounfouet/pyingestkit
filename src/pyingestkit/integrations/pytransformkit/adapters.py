"""Optional anti-corruption layer between PyIngestKit V2 and PyTransformKit."""

from __future__ import annotations

import hashlib
import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import CorrelationId, IngestionRunId


class PyTransformKitIntegrationError(RuntimeError):
    """Base error for the optional PyTransformKit integration boundary."""


class PyTransformKitUnavailableError(PyTransformKitIntegrationError):
    """The optional sibling package is not installed."""


class PyTransformKitCompatibilityError(PyTransformKitIntegrationError):
    """The installed sibling package is outside the supported public API range."""


class PyTransformKitMappingError(PyTransformKitIntegrationError):
    """A portable contract cannot be translated without semantic loss."""


DatasetVersionResolver = Callable[[DatasetVersionReference], ResourceReference]


@dataclass(frozen=True, slots=True)
class TransformationPublicationInput:
    """Portable PyIngestKit-side handoff produced from a transformation result."""

    output_name: str
    resource: ResourceReference
    transformation_execution_id: str
    transformation_plan_fingerprint: str | None
    engine_id: str | None
    correlation: CorrelationContext
    provenance: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.output_name, str) or not self.output_name.strip():
            raise ValueError("TransformationPublicationInput output_name must be non-blank.")
        if not isinstance(self.resource, ResourceReference):
            raise TypeError("TransformationPublicationInput resource must be ResourceReference.")
        if (
            not isinstance(self.transformation_execution_id, str)
            or not self.transformation_execution_id.strip()
        ):
            raise ValueError(
                "TransformationPublicationInput transformation_execution_id must be non-blank."
            )
        if self.transformation_plan_fingerprint is not None and (
            not isinstance(self.transformation_plan_fingerprint, str)
            or not self.transformation_plan_fingerprint.strip()
        ):
            raise ValueError(
                "TransformationPublicationInput transformation_plan_fingerprint "
                "must be non-blank when provided."
            )
        if self.engine_id is not None and (
            not isinstance(self.engine_id, str) or not self.engine_id.strip()
        ):
            raise ValueError(
                "TransformationPublicationInput engine_id must be non-blank when provided."
            )
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError(
                "TransformationPublicationInput correlation must be CorrelationContext."
            )
        if not isinstance(self.provenance, tuple):
            raise TypeError("TransformationPublicationInput provenance must be a tuple.")
        for item in self.provenance:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not all(isinstance(value, str) for value in item)
            ):
                raise TypeError(
                    "TransformationPublicationInput provenance must contain string pairs."
                )


class DatasetVersionInputAdapter:
    """Translate a governed DatasetVersionReference into a resource InputBinding."""

    def __init__(self, resolver: DatasetVersionResolver | None = None) -> None:
        if resolver is not None and not callable(resolver):
            raise TypeError("DatasetVersionInputAdapter resolver must be callable.")
        self._resolver = resolver

    def to_input_binding(
        self,
        reference: DatasetVersionReference,
        *,
        input_name: str,
    ) -> object:
        if not isinstance(reference, DatasetVersionReference):
            raise TypeError("DatasetVersionInputAdapter requires DatasetVersionReference.")
        if not isinstance(input_name, str) or not input_name.strip():
            raise ValueError("input_name must be non-blank.")

        api = _pytransformkit_api()
        resource = self._resolve(reference)
        transform_resource = _to_transform_resource(
            api,
            resource,
            dataset_version=reference,
        )
        return api.input_binding.from_resource(input_name, transform_resource)

    def _resolve(self, reference: DatasetVersionReference) -> ResourceReference:
        if self._resolver is not None:
            resource = self._resolver(reference)
            if not isinstance(resource, ResourceReference):
                raise PyTransformKitMappingError(
                    "DatasetVersion resolver must return ResourceReference."
                )
            return resource
        if reference.locator is not None:
            return reference.locator
        if reference.artifact_reference is not None:
            return reference.artifact_reference.resource
        raise PyTransformKitMappingError(
            "DatasetVersionReference has no concrete ResourceReference; "
            "configure a DatasetVersion resolver."
        )


class TransformationPublicationAdapter:
    """Translate a successful public TransformationResult into publication input."""

    def from_result(
        self,
        result: object,
        *,
        output_name: str,
    ) -> TransformationPublicationInput:
        api = _pytransformkit_api()
        if not isinstance(result, api.transformation_result):
            raise TypeError(
                "TransformationPublicationAdapter requires PyTransformKit TransformationResult."
            )
        provider_result = cast(Any, result)
        if not isinstance(output_name, str) or not output_name.strip():
            raise ValueError("output_name must be non-blank.")

        output_resource = _output_resource(provider_result, output_name)
        execution_reference = api.execution_reference.from_execution(
            provider_result.execution,
            output_reference=output_resource,
        )
        resource = _from_transform_resource(
            output_resource,
            execution_id=str(execution_reference.transformation_execution_id),
            output_name=output_name,
        )
        correlation = from_transform_correlation(
            provider_result.correlation,
            transformation_execution_id=str(execution_reference.transformation_execution_id),
        )
        fingerprint = execution_reference.transformation_plan_fingerprint
        fingerprint_text = (
            None if fingerprint is None else f"{fingerprint.algorithm}:{fingerprint.value}"
        )
        engine_id = execution_reference.engine_id
        provenance = [
            ("source_framework", "pytransformkit"),
            (
                "transformation_execution_id",
                str(execution_reference.transformation_execution_id),
            ),
            ("output_name", output_name),
        ]
        if fingerprint_text is not None:
            provenance.append(("transformation_plan_fingerprint", fingerprint_text))
        if engine_id is not None:
            provenance.append(("engine_id", engine_id))

        return TransformationPublicationInput(
            output_name=output_name,
            resource=resource,
            transformation_execution_id=str(execution_reference.transformation_execution_id),
            transformation_plan_fingerprint=fingerprint_text,
            engine_id=engine_id,
            correlation=correlation,
            provenance=tuple(provenance),
        )


def to_transform_correlation(context: CorrelationContext) -> object:
    """Project PyIngestKit correlation into the sibling public context contract."""
    if not isinstance(context, CorrelationContext):
        raise TypeError("context must be PyIngestKit CorrelationContext.")
    api = _pytransformkit_api()
    return api.correlation_context(
        correlation_id=api.correlation_id.parse(str(context.correlation_id)),
        causation_id=context.causation_id,
        parent_execution_id=context.parent_execution_id,
        workflow_run_id=context.workflow_run_id,
        task_run_id=context.task_run_id,
        task_attempt_id=context.task_attempt_id,
        ingestion_run_id=context.ingestion_run_id,
        trace_id=context.trace_id,
        span_id=context.span_id,
    )


def from_transform_correlation(
    context: object,
    *,
    transformation_execution_id: str | None = None,
) -> CorrelationContext:
    """Project the public sibling context back without changing CorrelationId."""
    api = _pytransformkit_api()
    if not isinstance(context, api.correlation_context):
        raise TypeError("context must be PyTransformKit CorrelationContext.")
    provider_context = cast(Any, context)
    return CorrelationContext(
        correlation_id=CorrelationId.parse(str(provider_context.correlation_id)),
        causation_id=provider_context.causation_id,
        parent_execution_id=provider_context.parent_execution_id,
        workflow_run_id=provider_context.workflow_run_id,
        task_run_id=provider_context.task_run_id,
        task_attempt_id=provider_context.task_attempt_id,
        ingestion_run_id=provider_context.ingestion_run_id,
        transformation_execution_id=transformation_execution_id,
        trace_id=provider_context.trace_id,
        span_id=provider_context.span_id,
    )


def from_transform_failure(
    failure: object,
    *,
    ingestion_run_id: IngestionRunId,
) -> FailureEvidence:
    """Translate public PyTransformKit failure semantics without flattening uncertainty."""
    if not isinstance(ingestion_run_id, IngestionRunId):
        raise TypeError("ingestion_run_id must be IngestionRunId.")
    api = _pytransformkit_api()
    if not isinstance(failure, api.failure_evidence):
        raise TypeError("failure must be PyTransformKit FailureEvidence.")
    provider_failure = cast(Any, failure)

    details = list(provider_failure.details)
    if "transformation_execution_id" not in {key for key, _ in details}:
        details.append(("transformation_execution_id", str(provider_failure.execution_id)))
    try:
        category = FailureCategory(provider_failure.category.value)
        retryability = Retryability(provider_failure.retryability.value)
        uncertainty = OutcomeUncertainty(provider_failure.uncertainty.value)
    except ValueError as exc:
        raise PyTransformKitMappingError(
            "PyTransformKit failure contains a semantic value unsupported by PyIngestKit."
        ) from exc

    return FailureEvidence(
        error_code=provider_failure.error_code,
        category=category,
        retryability=retryability,
        uncertainty=uncertainty,
        ingestion_run_id=ingestion_run_id,
        correlation_id=CorrelationId.parse(str(provider_failure.correlation_id)),
        source_framework=provider_failure.source_framework,
        source_component=provider_failure.source_component,
        provider_code=provider_failure.provider_code,
        message_summary=provider_failure.message_summary,
        occurred_at=provider_failure.occurred_at,
        details=tuple(details),
        contract_version=provider_failure.contract_version,
    )


def pytransformkit_version() -> str:
    """Return the qualified sibling version or raise an actionable integration error."""
    return _pytransformkit_api().version


@dataclass(frozen=True, slots=True)
class _PyTransformKitApi:
    version: str
    input_binding: Any
    resource_reference: Any
    correlation_context: Any
    correlation_id: Any
    failure_evidence: Any
    transformation_result: Any
    execution_reference: Any


def _pytransformkit_api() -> _PyTransformKitApi:
    try:
        package = importlib.import_module("pytransformkit")
        runtime = importlib.import_module("pytransformkit.runtime")
    except ModuleNotFoundError as exc:
        if exc.name == "pytransformkit" or (
            exc.name is not None and exc.name.startswith("pytransformkit.")
        ):
            raise PyTransformKitUnavailableError(
                "PyTransformKit integration requires pytransformkit>=1.1,<2. "
                "The pyingestkit[transform] convenience extra is activated at the 2.0 package cut."
            ) from exc
        raise

    version = getattr(package, "__version__", None)
    if not isinstance(version, str):
        raise PyTransformKitCompatibilityError(
            "Installed PyTransformKit does not expose a public __version__."
        )
    major, minor = _version_prefix(version)
    if major != 1 or minor < 1:
        raise PyTransformKitCompatibilityError(
            f"Unsupported PyTransformKit {version!r}; expected >=1.1,<2."
        )
    return _PyTransformKitApi(
        version=version,
        input_binding=package.InputBinding,
        resource_reference=package.ResourceReference,
        correlation_context=runtime.CorrelationContext,
        correlation_id=runtime.CorrelationId,
        failure_evidence=runtime.FailureEvidence,
        transformation_result=package.TransformationResult,
        execution_reference=runtime.TransformationExecutionReference,
    )


def _to_transform_resource(
    api: _PyTransformKitApi,
    resource: ResourceReference,
    *,
    dataset_version: DatasetVersionReference,
) -> object:
    if resource.locator is None:
        raise PyTransformKitMappingError(
            "PyTransformKit InputBinding requires a concrete resource locator."
        )
    parsed = urlsplit(resource.locator)
    if not parsed.scheme:
        raise PyTransformKitMappingError(
            "ResourceReference locator must use an explicit URI scheme."
        )
    metadata: list[tuple[str, str]] = [
        ("pyingestkit.dataset_id", dataset_version.dataset_id),
        ("pyingestkit.version_id", dataset_version.version_id),
    ]
    if dataset_version.schema_fingerprint is not None:
        metadata.append(("pyingestkit.schema_fingerprint", dataset_version.schema_fingerprint))
    locator = resource.locator
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            raise PyTransformKitMappingError(
                "File ResourceReference must not target a remote host."
            )
        locator = str(Path(url2pathname(unquote(parsed.path))).resolve(strict=False))
    return api.resource_reference(
        scheme=parsed.scheme,
        locator=locator,
        media_type=resource.media_type,
        metadata=tuple(metadata),
    )


def _from_transform_resource(
    resource: object,
    *,
    execution_id: str,
    output_name: str,
) -> ResourceReference:
    api = _pytransformkit_api()
    if not isinstance(resource, api.resource_reference):
        raise TypeError("resource must be PyTransformKit ResourceReference.")
    provider_resource = cast(Any, resource)
    provider_locator = provider_resource.locator
    parsed = urlsplit(provider_locator)
    if parsed.scheme:
        if parsed.scheme != provider_resource.scheme:
            raise PyTransformKitMappingError(
                "PyTransformKit output ResourceReference scheme disagrees with its locator."
            )
        locator = provider_locator
        canonical = parsed
    elif provider_resource.scheme == "file":
        path = Path(provider_locator).expanduser()
        if not path.is_absolute():
            raise PyTransformKitMappingError(
                "PyTransformKit local output must expose an absolute path for publication."
            )
        locator = path.resolve(strict=False).as_uri()
        canonical = urlsplit(locator)
    else:
        raise PyTransformKitMappingError(
            "PyTransformKit output ResourceReference requires an explicit URI scheme."
        )
    resource_id = hashlib.sha256(
        f"{execution_id}\x00{output_name}\x00{locator}".encode()
    ).hexdigest()
    suffix = canonical.path.rsplit("/", 1)[-1]
    inferred_format = (
        suffix.rsplit(".", 1)[-1].lower() if "." in suffix and not suffix.endswith(".") else None
    )
    return ResourceReference(
        namespace="pyingestkit.integration.pytransformkit.resource",
        resource_id=f"transform_{resource_id}",
        locator=locator,
        media_type=provider_resource.media_type,
        format=inferred_format,
        metadata=(
            ("source_framework", "pytransformkit"),
            ("transformation_execution_id", execution_id),
            ("output_name", output_name),
        ),
    )


def _output_resource(result: Any, output_name: str) -> object:
    links = getattr(result.lineage, "resources", ())
    for link in links:
        role = getattr(getattr(link, "role", None), "value", None)
        if link.name == output_name and role == "output":
            return link.resource
    raise PyTransformKitMappingError(
        f"TransformationResult has no materialized ResourceReference for output {output_name!r}."
    )


def _version_prefix(value: str) -> tuple[int, int]:
    parts = value.split(".", 2)
    if len(parts) < 2:
        raise PyTransformKitCompatibilityError(
            f"Unable to interpret PyTransformKit version {value!r}."
        )
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError as exc:
        raise PyTransformKitCompatibilityError(
            f"Unable to interpret PyTransformKit version {value!r}."
        ) from exc
