"""Customer 360 PyIngestKit V2 local reference profile."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pyingestkit.adapters.filesystem import (
    FileAccessPolicy,
    FileArtifactStore,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
    FileSourceConnector,
)
from pyingestkit.datasets import (
    DatasetVersionReference,
    ResourceDatasetVersionRequestV2,
)
from pyingestkit.decoders import CsvDecoder, DecoderRegistry
from pyingestkit.ingestion.v2 import IngestionDefinition
from pyingestkit.integrations.pytransformkit import (
    DatasetVersionInputAdapter,
    TransformationPublicationAdapter,
    to_transform_correlation,
)
from pyingestkit.publication.v2 import (
    PublicationRequestV2,
    PublicationServiceV2,
)
from pyingestkit.replay.v2 import ReplayRequest, ReplayResult, ReplayServiceV2
from pyingestkit.resources import ResourceReference
from pyingestkit.runtime.v2 import (
    CorrelationContext,
    CorrelationId,
    IngestionResult,
    IngestionRunId,
    IngestionRuntime,
)
from pyingestkit.sources.v2 import Source, SourceRegistry
from pyingestkit.validation.v2 import RequiredFieldV2

_NOW = datetime(2026, 10, 3, 15, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Customer360Evidence:
    """Inspectable evidence from one local Customer 360 run."""

    engine_id: str
    correlation_id: CorrelationId
    customers: IngestionResult
    orders: IngestionResult
    transformation_execution_id: str
    transformation_plan_fingerprint: str
    transformation_resource: ResourceReference
    customer_mart_version: DatasetVersionReference
    replay: ReplayResult
    state_root: Path

    @property
    def provenance(self) -> dict[str, str]:
        return dict(self.customer_mart_version.metadata)


def run_customer_360(
    *,
    workspace: str | Path,
    engine_id: str = "pandas",
) -> Customer360Evidence:
    """Run the PyIngestKit-owned Customer 360 beta profile end to end."""

    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    input_root = Path(__file__).resolve().parent / "data" / "input"
    state_root = root / "state"
    interop_root = root / "interop"
    transform_root = root / "transform"
    interop_root.mkdir(parents=True, exist_ok=True)
    transform_root.mkdir(parents=True, exist_ok=True)

    shared_correlation_id = CorrelationId.new()
    runtime, versions = _ingestion_runtime(input_root, state_root)

    customers_definition = IngestionDefinition(
        name="customer360.customers",
        source=Source.file(path=str(input_root / "customers.csv")),
        decoder="csv",
        dataset="customer360.customers",
    )
    orders_definition = IngestionDefinition(
        name="customer360.orders",
        source=Source.file(path=str(input_root / "orders.csv")),
        decoder="csv",
        dataset="customer360.orders",
    )

    customers = runtime.execute(
        customers_definition,
        validation_rules=(RequiredFieldV2("customer_id"),),
        publish=True,
        correlation=CorrelationContext(correlation_id=shared_correlation_id),
    )
    orders = runtime.execute(
        orders_definition,
        validation_rules=(RequiredFieldV2("order_id"), RequiredFieldV2("customer_id")),
        publish=True,
        correlation=CorrelationContext(correlation_id=shared_correlation_id),
    )
    if not customers.succeeded or customers.dataset_version is None:
        raise RuntimeError("Customer 360 customers ingestion did not succeed.")
    if not orders.succeeded or orders.dataset_version is None:
        raise RuntimeError("Customer 360 orders ingestion did not succeed.")
    if customers.raw_artifact is None or orders.raw_artifact is None:
        raise RuntimeError("Customer 360 ingestion did not retain RAW evidence.")

    portable_resources = {
        customers.dataset_version.identity: _export_version_csv(
            versions,
            customers.dataset_version,
            interop_root / "customers.csv",
        ),
        orders.dataset_version.identity: _export_version_csv(
            versions,
            orders.dataset_version,
            interop_root / "orders.csv",
        ),
    }
    input_adapter = DatasetVersionInputAdapter(
        resolver=lambda reference: portable_resources[reference.identity]
    )
    transform_result = _execute_transform(
        engine_id=engine_id,
        root=root,
        customers=input_adapter.to_input_binding(
            customers.dataset_version,
            input_name="customers",
        ),
        orders=input_adapter.to_input_binding(
            orders.dataset_version,
            input_name="orders",
        ),
        correlation=to_transform_correlation(
            CorrelationContext(correlation_id=shared_correlation_id)
        ),
        output_path=transform_root / f"customer_mart-{engine_id}.csv",
    )

    publication_input = TransformationPublicationAdapter().from_result(
        transform_result,
        output_name="customer_mart",
    )
    publication_run_id = IngestionRunId.new()
    provenance = (
        ("source.customers.artifact_id", customers.raw_artifact.artifact_id),
        ("source.customers.version_id", customers.dataset_version.version_id),
        ("source.orders.artifact_id", orders.raw_artifact.artifact_id),
        ("source.orders.version_id", orders.dataset_version.version_id),
        (
            "transformation.execution_id",
            publication_input.transformation_execution_id,
        ),
        (
            "transformation.plan_fingerprint",
            publication_input.transformation_plan_fingerprint or "unknown",
        ),
        ("transformation.engine_id", publication_input.engine_id or engine_id),
        ("transformation.output_resource_id", publication_input.resource.resource_id),
    )
    materializer = FileCsvDatasetVersionMaterializerV2(
        allowed_roots=(transform_root,),
    )
    customer_mart = materializer.materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id="customer360.customer_mart",
            resource=publication_input.resource,
            ingestion_run_id=publication_run_id,
            created_at=_NOW,
            provenance=provenance,
        )
    )
    stored_mart = versions.put(customer_mart)

    publication_context = CorrelationContext(
        correlation_id=shared_correlation_id,
        ingestion_run_id=str(publication_run_id),
        transformation_execution_id=publication_input.transformation_execution_id,
    )
    published = PublicationServiceV2(
        publisher=versions,
        clock=lambda: _NOW,
    ).publish(
        PublicationRequestV2(
            dataset_version=stored_mart,
            ingestion_run_id=publication_run_id,
            correlation=publication_context,
            requested_at=_NOW,
        )
    )
    if not published.succeeded or published.published_dataset is None:
        raise RuntimeError("Customer 360 publication did not succeed.")

    replay = ReplayServiceV2(
        runtime=runtime,
        clock=lambda: _NOW,
    ).replay(
        ReplayRequest(
            source_run_id=customers.ingestion_run_id,
            definition=customers_definition,
            origin_raw_artifact=customers.raw_artifact,
            expected_dataset_version=customers.dataset_version,
        ),
        validation_rules=(RequiredFieldV2("customer_id"),),
        correlation=CorrelationContext(correlation_id=shared_correlation_id),
    )
    if not replay.succeeded or replay.matched is not True:
        raise RuntimeError("Customer 360 strict replay did not reproduce source version.")

    return Customer360Evidence(
        engine_id=engine_id,
        correlation_id=shared_correlation_id,
        customers=customers,
        orders=orders,
        transformation_execution_id=publication_input.transformation_execution_id,
        transformation_plan_fingerprint=(
            publication_input.transformation_plan_fingerprint or "unknown"
        ),
        transformation_resource=publication_input.resource,
        customer_mart_version=published.published_dataset.version,
        replay=replay,
        state_root=state_root,
    )


def read_customer_mart(evidence: Customer360Evidence):
    """Read the final governed representation from the local reference store."""

    store = FileDatasetVersionStore(root=evidence.state_root / "versions")
    return store.read(evidence.customer_mart_version)


def _ingestion_runtime(
    input_root: Path,
    state_root: Path,
) -> tuple[IngestionRuntime, FileDatasetVersionStore]:
    sources = SourceRegistry()
    sources.register(
        FileSourceConnector(
            policy=FileAccessPolicy(
                allowed_roots=(input_root,),
                allowed_extensions=(".csv",),
            )
        )
    )
    decoders = DecoderRegistry()
    decoders.register(CsvDecoder())
    versions = FileDatasetVersionStore(root=state_root / "versions")
    return (
        IngestionRuntime(
            sources=sources,
            decoders=decoders,
            artifacts=FileArtifactStore(root=state_root / "artifacts"),
            versions=versions,
            publisher=versions,
            clock=lambda: _NOW,
        ),
        versions,
    )


def _export_version_csv(
    store: FileDatasetVersionStore,
    reference: DatasetVersionReference,
    path: Path,
) -> ResourceReference:
    representation = store.read(reference)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [dict(record.fields) for record in representation.records]
    fieldnames = list(records[0]) if records else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(records)
    return ResourceReference(
        namespace="customer360.dataset_export",
        resource_id=f"{reference.dataset_id}:{reference.version_id}",
        locator=path.resolve().as_uri(),
        media_type="text/csv",
        format="csv",
        schema_fingerprint=reference.schema_fingerprint,
    )


def _execute_transform(
    *,
    engine_id: str,
    root: Path,
    customers: object,
    orders: object,
    correlation: object,
    output_path: Path,
):
    import pytransformkit
    from pytransformkit import (
        DataType,
        EngineRegistry,
        Field,
        OutputBinding,
        ResourceReference as TransformResourceReference,
        RetrySafety,
        Schema,
        TransformationPlan,
        TransformationRuntime,
        WriteMode,
        quality,
    )
    from pytransformkit import functions as fn
    from pytransformkit.adapters.pandas import PandasEngineAdapter
    from pytransformkit.adapters.polars import PolarsEngineAdapter
    from pytransformkit.functions import col, lower, trim
    from pytransformkit.readers import LocalFileReader, ResourceIORegistry
    from pytransformkit.writers import LocalFileWriter

    if engine_id not in {"pandas", "polars"}:
        raise ValueError("Customer 360 engine_id must be 'pandas' or 'polars'.")

    customer_schema = Schema(
        fields=(
            Field("customer_id", DataType.int64(), nullable=False),
            Field("customer_name", DataType.string(), nullable=False),
            Field("country", DataType.string(), nullable=False),
            Field("email", DataType.string(), nullable=True),
        )
    )
    order_schema = Schema(
        fields=(
            Field("order_id", DataType.int64(), nullable=False),
            Field("customer_id", DataType.int64(), nullable=False),
            Field("amount", DataType.float64(), nullable=False),
            Field("status", DataType.string(), nullable=False),
        )
    )
    builder = TransformationPlan.builder("customer_360")
    customer_data = builder.input("customers", schema=customer_schema)
    order_data = builder.input("orders", schema=order_schema)
    paid = builder.filter(
        "paid_orders",
        source=order_data,
        where=col("status") == "PAID",
    )
    stats = builder.aggregate(
        "paid_order_stats",
        source=paid,
        group_by=(col("customer_id"),),
        metrics={
            "paid_order_count": fn.count(col("order_id")),
            "paid_revenue": fn.sum(col("amount")),
        },
    )
    joined = builder.join(
        "customer_stats",
        left=customer_data,
        right=stats,
        how="left",
        on=(("customer_id", "customer_id"),),
    )
    normalized = builder.derive(
        "normalized_email",
        source=joined,
        field_name="normalized_email",
        expression=lower(trim(col("email"))),
    )
    validated = builder.validate(
        "customer360_quality",
        source=normalized,
        spec=quality.ValidationSpec(
            name="customer360_quality",
            rules=(
                quality.not_null("customer_id"),
                quality.unique("customer_id"),
            ),
            policy=quality.ValidationPolicy.FAIL_FAST,
        ),
    )
    projected = builder.select(
        "customer360_projection",
        source=validated,
        columns=(
            "customer_id",
            "customer_name",
            "country",
            "normalized_email",
            "paid_order_count",
            "paid_revenue",
        ),
    )
    ordered = builder.sort(
        "customer360_ordered",
        source=projected,
        by=("customer_id",),
    )
    plan = builder.output("customer_mart", ordered).build()

    engines = EngineRegistry()
    engines.register(
        PandasEngineAdapter() if engine_id == "pandas" else PolarsEngineAdapter()
    )
    resources = ResourceIORegistry()
    resources.register_reader(LocalFileReader(root))
    resources.register_writer(LocalFileWriter(root))
    runtime = TransformationRuntime(engines=engines, resources=resources)
    output = TransformResourceReference(
        scheme="file",
        locator=str(output_path.resolve()),
        media_type="text/csv",
    )
    result = runtime.execute(
        plan,
        engine=engine_id,
        inputs={
            "customers": customers,
            "orders": orders,
        },
        outputs={
            "customer_mart": OutputBinding.to_resource(
                "customer_mart",
                output,
                mode=WriteMode.CREATE_NEW,
                retry_safety=RetrySafety.SAFE,
            )
        },
        correlation=correlation,
    )
    if result.engine.id != engine_id:
        raise RuntimeError("Customer 360 transformation engine identity mismatch.")
    if not output_path.is_file():
        raise RuntimeError("Customer 360 transformation output was not materialized.")
    return result
