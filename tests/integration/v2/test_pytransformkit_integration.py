from __future__ import annotations

from datetime import UTC, datetime

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, FailureCategory
from pyingestkit.domain.shared import CorrelationId, IngestionRunId
from pyingestkit.integrations.pytransformkit import (
    DatasetVersionInputAdapter,
    TransformationPublicationAdapter,
    from_transform_correlation,
    from_transform_failure,
    pytransformkit_version,
    to_transform_correlation,
)


def test_customer360_dataset_version_handoff_uses_portable_resource_binding() -> None:
    import pytransformkit

    reference = DatasetVersionReference(
        dataset_id="customer360.customers",
        version_id="sha256-" + "a" * 64,
        schema_fingerprint="sha256:" + "b" * 64,
        content_fingerprint="sha256-" + "a" * 64,
        locator=ResourceReference(
            namespace="pyingestkit.dataset_version.s3",
            resource_id="customers-v7",
            locator="s3://data/customer360/customers/v7/snapshot.parquet",
            media_type="application/vnd.apache.parquet",
            format="parquet",
        ),
    )

    binding = DatasetVersionInputAdapter().to_input_binding(
        reference,
        input_name="customers",
    )

    assert isinstance(binding, pytransformkit.InputBinding)
    assert binding.portable is True
    assert binding.native_value is None
    assert binding.resource is not None
    assert binding.resource.scheme == "s3"
    assert binding.resource.locator == reference.locator.locator
    assert dict(binding.resource.metadata) == {
        "pyingestkit.dataset_id": "customer360.customers",
        "pyingestkit.version_id": reference.version_id,
        "pyingestkit.schema_fingerprint": reference.schema_fingerprint,
    }


def test_correlation_round_trip_preserves_cross_framework_identity() -> None:
    from pytransformkit.runtime import CorrelationContext as TransformCorrelationContext

    ingestion_run_id = IngestionRunId.new()
    context = CorrelationContext(
        correlation_id=CorrelationId.new(),
        causation_id="source-acquisition",
        parent_execution_id="workflow-parent",
        workflow_run_id="workflow-42",
        task_run_id="task-7",
        task_attempt_id="attempt-2",
        ingestion_run_id=str(ingestion_run_id),
        trace_id="trace-123",
        span_id="span-456",
    )

    transform = to_transform_correlation(context)

    assert isinstance(transform, TransformCorrelationContext)
    assert str(transform.correlation_id) == str(context.correlation_id)
    assert transform.ingestion_run_id == str(ingestion_run_id)

    returned = from_transform_correlation(
        transform,
        transformation_execution_id="transform-execution-9",
    )

    assert returned.correlation_id == context.correlation_id
    assert returned.ingestion_run_id == context.ingestion_run_id
    assert returned.workflow_run_id == context.workflow_run_id
    assert returned.trace_id == context.trace_id
    assert returned.transformation_execution_id == "transform-execution-9"


def test_transform_failure_translation_preserves_retry_and_uncertainty() -> None:
    from pytransformkit.runtime import (
        CorrelationId as TransformCorrelationId,
        FailureCategory as TransformFailureCategory,
        FailureEvidence as TransformFailureEvidence,
        OutcomeUncertainty as TransformOutcomeUncertainty,
        Retryability as TransformRetryability,
        TransformationExecutionId,
    )

    transform_failure = TransformFailureEvidence(
        error_code="PTK-EXEC-777",
        category=TransformFailureCategory.UNKNOWN_OUTCOME,
        retryability=TransformRetryability.RETRYABLE_AFTER_RECONCILIATION,
        uncertainty=TransformOutcomeUncertainty.REQUIRES_RECONCILIATION,
        execution_id=TransformationExecutionId.new(),
        correlation_id=TransformCorrelationId.new(),
        source_component="runtime.writer",
        provider_code="provider-unknown",
        message_summary="External write outcome is unknown.",
        occurred_at=datetime(2026, 10, 3, 12, 30, tzinfo=UTC),
    )
    ingestion_run_id = IngestionRunId.new()

    failure = from_transform_failure(
        transform_failure,
        ingestion_run_id=ingestion_run_id,
    )

    assert failure.ingestion_run_id == ingestion_run_id
    assert failure.category is FailureCategory.UNKNOWN_OUTCOME
    assert failure.retryability.value == "retryable_after_reconciliation"
    assert failure.uncertainty.value == "requires_reconciliation"
    assert failure.provider_code == "provider-unknown"
    assert (
        "transformation_execution_id",
        str(transform_failure.execution_id),
    ) in failure.details


def test_successful_transformation_publication_retains_execution_reference() -> None:
    import pytransformkit
    from pytransformkit.engines import EngineDescriptor
    from pytransformkit.lineage import analyze
    from pytransformkit.planning import TransformationCompiler
    from pytransformkit.runtime import (
        CorrelationContext as TransformCorrelationContext,
        ExecutionManifest,
        ExecutionStatus,
        TransformationExecution,
        TransformationExecutionId,
        TransformationOutput,
    )

    schema = pytransformkit.Schema(fields=())
    builder = pytransformkit.TransformationPlan.builder("customer360-publication")
    customers = builder.input("customers", schema=schema)
    plan = builder.output("customers_out", customers).build()
    logical = TransformationCompiler().compile(plan)

    output_resource = pytransformkit.ResourceReference(
        scheme="s3",
        locator="s3://data/customer360/golden/customers.parquet",
        media_type="application/vnd.apache.parquet",
    )
    lineage = analyze(
        logical,
        output_resources={"customers_out": output_resource},
    )
    correlation = TransformCorrelationContext(
        ingestion_run_id=str(IngestionRunId.new()),
    )
    execution_id = TransformationExecutionId.new()
    engine = EngineDescriptor(
        id="contract-engine",
        name="Contract Engine",
        adapter_version="1",
        capabilities=frozenset(),
    )
    started_at = datetime(2026, 10, 3, 12, 35, tzinfo=UTC)
    ended_at = datetime(2026, 10, 3, 12, 35, 1, tzinfo=UTC)
    fingerprint = logical.fingerprint()
    execution = TransformationExecution(
        execution_id=execution_id,
        status=ExecutionStatus.SUCCEEDED,
        correlation=correlation,
        started_at=started_at,
        ended_at=ended_at,
        plan_id=logical.plan_id,
        plan_fingerprint=fingerprint,
        engine=engine,
    )
    manifest = ExecutionManifest(
        framework_version=pytransformkit.__version__,
        execution_id=execution_id,
        correlation=correlation,
        status=ExecutionStatus.SUCCEEDED,
        started_at=started_at,
        ended_at=ended_at,
        input_names=logical.input_names,
        output_names=logical.output_names,
        diagnostic_codes=(),
        plan_id=logical.plan_id,
        plan_fingerprint=fingerprint,
        engine_id=engine.id,
        adapter_version=engine.adapter_version,
    )
    result = pytransformkit.TransformationResult(
        execution=execution,
        engine=engine,
        logical_plan=logical,
        outputs=(
            TransformationOutput(
                name="customers_out",
                handle=object(),  # type: ignore[arg-type]
                schema=schema,
            ),
        ),
        lineage=lineage,
        manifest=manifest,
    )

    publication = TransformationPublicationAdapter().from_result(
        result,
        output_name="customers_out",
    )

    assert publication.transformation_execution_id == str(execution_id)
    assert publication.transformation_plan_fingerprint == (
        f"{fingerprint.algorithm}:{fingerprint.value}"
    )
    assert publication.engine_id == "contract-engine"
    assert publication.resource.locator == output_resource.locator
    assert publication.correlation.transformation_execution_id == str(execution_id)
    assert (
        "transformation_execution_id",
        str(execution_id),
    ) in publication.provenance


def test_lot17_qualifies_expected_pytransformkit_major_line() -> None:
    assert pytransformkit_version().startswith("1.")
