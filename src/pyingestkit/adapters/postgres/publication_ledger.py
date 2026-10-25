"""PostgreSQL durable lifecycle PublicationLedger for PyIngestKit 2.1."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import cast

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError, SQLAlchemyError

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    VersionHold,
)
from pyingestkit.domain.replay import ReplayLineage
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import validate_aware_datetime
from pyingestkit.governance._ledger_codec import (
    decode_event,
    decode_intent,
    encode_event,
    encode_intent,
    is_terminal_event,
)
from pyingestkit.ports.governance import PublicationLedger
from pyingestkit.ports.replay import ReplayLineageLedger

_METADATA = MetaData()

_PUBLICATION_OPERATION = Table(
    "pyingestkit_v2_publication_operation",
    _METADATA,
    Column("operation_id", String(36), primary_key=True),
    Column("dataset_id", String(512), nullable=False, index=True),
    Column("intent_fingerprint", String(71), nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("intent_payload", Text, nullable=False),
    Column("terminal_event_type", String(64), nullable=True),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
)

_PUBLICATION_EVENT = Table(
    "pyingestkit_v2_publication_event",
    _METADATA,
    Column("sequence_id", BigInteger, primary_key=True, autoincrement=True),
    Column("event_id", String(512), nullable=False, unique=True),
    Column(
        "operation_id",
        String(36),
        ForeignKey("pyingestkit_v2_publication_operation.operation_id"),
        nullable=True,
        index=True,
    ),
    Column("dataset_id", String(512), nullable=False, index=True),
    Column("event_type", String(64), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("event_payload", Text, nullable=False),
)

_VERSION_HOLD = Table(
    "pyingestkit_v2_version_hold",
    _METADATA,
    Column("hold_id", String(512), primary_key=True),
    Column("dataset_id", String(512), nullable=False, index=True),
    Column("version_id", String(512), nullable=False),
    Column("held_at", DateTime(timezone=True), nullable=False),
    Column("released_at", DateTime(timezone=True), nullable=True),
    Column("reason", Text, nullable=True),
)

_REPLAY_LINEAGE = Table(
    "pyingestkit_v2_replay_lineage",
    _METADATA,
    Column("lineage_id", String(64), primary_key=True),
    Column("source_run_id", String(64), nullable=False, index=True),
    Column("replay_run_id", String(64), nullable=False, index=True),
    Column("dataset_id", String(512), nullable=False, index=True),
    Column("version_id", String(512), nullable=False),
    Column("origin_raw_checksum", String(128), nullable=False),
    Column("replay_raw_checksum", String(128), nullable=False),
    Column("matched", Boolean, nullable=False),
    Column("replayed_at", DateTime(timezone=True), nullable=False),
    Column("published", Boolean, nullable=False, default=False),
)


class PostgresPublicationLedger(PublicationLedger, ReplayLineageLedger):
    """Durable PostgreSQL implementation of the frozen LOT-23 ledger port."""

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgresPublicationLedger requires a non-empty DSN.")
        self._raw_dsn = dsn
        self._normalized_dsn = _normalize_dsn(dsn)
        self._safe_dsn = _safe_dsn(dsn)
        self._closed = False
        try:
            self._engine = create_engine(
                self._normalized_dsn,
                future=True,
                pool_pre_ping=True,
            )
        except (ModuleNotFoundError, NoSuchModuleError) as exc:
            raise RuntimeError("PostgresPublicationLedger requires the 'postgres' extra.") from exc
        try:
            _METADATA.create_all(self._engine)
        except (ModuleNotFoundError, SQLAlchemyError) as exc:
            self._engine.dispose()
            raise RuntimeError(
                f"Unable to initialize lifecycle ledger at {self._safe_dsn}."
            ) from exc

    @property
    def safe_dsn(self) -> str:
        return self._safe_dsn

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def engine(self) -> Engine:
        """Expose the provider engine for explicit operational inspection only."""
        self._ensure_open()
        return self._engine

    def register(self, intent: PublicationIntent) -> PublicationIntent:
        self._ensure_open()
        with self._engine.begin() as connection:
            return _register(connection, intent)

    def append(self, event: PublicationLifecycleEvent) -> None:
        self._ensure_open()
        with self._engine.begin() as connection:
            _append(connection, event)

    def get_operation(self, operation_id: PublicationOperationId) -> PublicationIntent | None:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _get_operation(connection, operation_id)

    def list_operations(self, dataset_id: str) -> tuple[PublicationIntent, ...]:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _list_operations(connection, dataset_id=dataset_id, unresolved_only=False)

    def list_unresolved(
        self,
        dataset_id: str | None = None,
    ) -> tuple[PublicationIntent, ...]:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _list_operations(connection, dataset_id=dataset_id, unresolved_only=True)

    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _list_events(connection, operation_id=operation_id, dataset_id=dataset_id)

    def place_hold(self, hold: VersionHold) -> VersionHold:
        self._ensure_open()
        with self._engine.begin() as connection:
            return _place_hold(connection, hold)

    def release_hold(
        self,
        reference: DatasetVersionReference,
        *,
        released_at: datetime,
    ) -> bool:
        self._ensure_open()
        with self._engine.begin() as connection:
            return _release_hold(connection, reference, released_at=released_at)

    def list_active_holds(self, dataset_id: str) -> tuple[VersionHold, ...]:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _list_active_holds(connection, dataset_id)

    def record_replay_lineage(self, lineage: ReplayLineage) -> ReplayLineage:
        self._ensure_open()
        with self._engine.begin() as connection:
            return _record_replay_lineage(connection, lineage)

    def list_replays(
        self,
        dataset_id: str | None = None,
        source_run_id: IngestionRunId | None = None,
    ) -> tuple[ReplayLineage, ...]:
        self._ensure_open()
        with self._engine.connect() as connection:
            return _list_replays(connection, dataset_id=dataset_id, source_run_id=source_run_id)

    @contextmanager
    def transaction(self) -> Iterator[_PostgresPublicationLedgerTransaction]:
        """Yield a ledger bound to one caller-controlled SQL transaction."""
        self._ensure_open()
        with self._engine.begin() as connection:
            yield _PostgresPublicationLedgerTransaction(connection)

    def close(self) -> None:
        if not self._closed:
            self._engine.dispose()
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("PostgresPublicationLedger is closed.")


class _PostgresPublicationLedgerTransaction(PublicationLedger, ReplayLineageLedger):
    """Protocol-compatible view that never commits its bound Connection."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def register(self, intent: PublicationIntent) -> PublicationIntent:
        return _register(self._connection, intent)

    def append(self, event: PublicationLifecycleEvent) -> None:
        _append(self._connection, event)

    def get_operation(self, operation_id: PublicationOperationId) -> PublicationIntent | None:
        return _get_operation(self._connection, operation_id)

    def list_operations(self, dataset_id: str) -> tuple[PublicationIntent, ...]:
        return _list_operations(
            self._connection,
            dataset_id=dataset_id,
            unresolved_only=False,
        )

    def list_unresolved(
        self,
        dataset_id: str | None = None,
    ) -> tuple[PublicationIntent, ...]:
        return _list_operations(
            self._connection,
            dataset_id=dataset_id,
            unresolved_only=True,
        )

    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]:
        return _list_events(
            self._connection,
            operation_id=operation_id,
            dataset_id=dataset_id,
        )

    def place_hold(self, hold: VersionHold) -> VersionHold:
        return _place_hold(self._connection, hold)

    def release_hold(
        self,
        reference: DatasetVersionReference,
        *,
        released_at: datetime,
    ) -> bool:
        return _release_hold(self._connection, reference, released_at=released_at)

    def list_active_holds(self, dataset_id: str) -> tuple[VersionHold, ...]:
        return _list_active_holds(self._connection, dataset_id)

    def record_replay_lineage(self, lineage: ReplayLineage) -> ReplayLineage:
        return _record_replay_lineage(self._connection, lineage)

    def list_replays(
        self,
        dataset_id: str | None = None,
        source_run_id: IngestionRunId | None = None,
    ) -> tuple[ReplayLineage, ...]:
        return _list_replays(
            self._connection,
            dataset_id=dataset_id,
            source_run_id=source_run_id,
        )


def _place_hold(connection: Connection, hold: VersionHold) -> VersionHold:
    if not isinstance(hold, VersionHold):
        raise TypeError("PostgresPublicationLedger.place_hold requires VersionHold.")

    active = (
        connection.execute(
            select(_VERSION_HOLD).where(
                _VERSION_HOLD.c.dataset_id == hold.dataset_version.dataset_id,
                _VERSION_HOLD.c.version_id == hold.dataset_version.version_id,
                _VERSION_HOLD.c.released_at.is_(None),
            )
        )
        .mappings()
        .one_or_none()
    )
    if active is not None:
        existing = _hold_from_row(active)
        if existing != hold:
            raise ValueError("Dataset version already has a different active hold.")
        return existing

    hold_id = _hold_id(hold.dataset_version, hold.held_at)
    connection.execute(
        postgres_insert(_VERSION_HOLD)
        .values(
            hold_id=hold_id,
            dataset_id=hold.dataset_version.dataset_id,
            version_id=hold.dataset_version.version_id,
            held_at=hold.held_at,
            released_at=None,
            reason=hold.reason,
        )
        .on_conflict_do_nothing(index_elements=[_VERSION_HOLD.c.hold_id])
    )
    _append(
        connection,
        _hold_event(hold, PublicationLifecycleEventType.HOLD_PLACED, hold.held_at),
    )
    return hold


def _release_hold(
    connection: Connection,
    reference: DatasetVersionReference,
    *,
    released_at: datetime,
) -> bool:
    if not isinstance(reference, DatasetVersionReference):
        raise TypeError("PostgresPublicationLedger.release_hold requires DatasetVersionReference.")
    validate_aware_datetime(released_at, "PostgresPublicationLedger released_at")
    row = (
        connection.execute(
            select(_VERSION_HOLD)
            .where(
                _VERSION_HOLD.c.dataset_id == reference.dataset_id,
                _VERSION_HOLD.c.version_id == reference.version_id,
                _VERSION_HOLD.c.released_at.is_(None),
            )
            .order_by(_VERSION_HOLD.c.held_at.desc(), _VERSION_HOLD.c.hold_id.desc())
            .with_for_update()
        )
        .mappings()
        .first()
    )
    if row is None:
        return False

    hold = _hold_from_row(row)
    if released_at < hold.held_at:
        raise ValueError("Version hold cannot be released before it was placed.")
    connection.execute(
        update(_VERSION_HOLD)
        .where(_VERSION_HOLD.c.hold_id == str(row["hold_id"]))
        .values(released_at=released_at)
    )
    _append(
        connection,
        _hold_event(hold, PublicationLifecycleEventType.HOLD_RELEASED, released_at),
    )
    return True


def _list_active_holds(
    connection: Connection,
    dataset_id: str,
) -> tuple[VersionHold, ...]:
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("PostgresPublicationLedger dataset_id must be non-blank.")
    rows = (
        connection.execute(
            select(_VERSION_HOLD)
            .where(
                _VERSION_HOLD.c.dataset_id == dataset_id,
                _VERSION_HOLD.c.released_at.is_(None),
            )
            .order_by(_VERSION_HOLD.c.held_at, _VERSION_HOLD.c.version_id)
        )
        .mappings()
        .all()
    )
    return tuple(_hold_from_row(row) for row in rows)


def _hold_from_row(row: object) -> VersionHold:
    mapping = cast(dict[str, object], row)
    return VersionHold(
        dataset_version=DatasetVersionReference(
            dataset_id=str(mapping["dataset_id"]),
            version_id=str(mapping["version_id"]),
        ),
        held_at=cast(datetime, mapping["held_at"]),
        reason=None if mapping["reason"] is None else str(mapping["reason"]),
    )


def _hold_id(reference: DatasetVersionReference, held_at: datetime) -> str:
    digest = hashlib.sha256(
        (f"{reference.dataset_id}\0{reference.version_id}\0{held_at.isoformat()}").encode()
    ).hexdigest()
    return f"hold:{digest}"


def _hold_event(
    hold: VersionHold,
    event_type: PublicationLifecycleEventType,
    occurred_at: datetime,
) -> PublicationLifecycleEvent:
    digest = hashlib.sha256(
        (
            f"{hold.dataset_version.dataset_id}\0"
            f"{hold.dataset_version.version_id}\0"
            f"{event_type.value}\0"
            f"{occurred_at.isoformat()}"
        ).encode()
    ).hexdigest()
    metadata: tuple[tuple[str, str], ...] = ()
    if hold.reason is not None:
        metadata = (("reason", hold.reason),)
    return PublicationLifecycleEvent(
        event_id=f"hold:{digest}",
        event_type=event_type,
        dataset_id=hold.dataset_version.dataset_id,
        occurred_at=occurred_at,
        dataset_version=hold.dataset_version,
        metadata=metadata,
    )


def _register(connection: Connection, intent: PublicationIntent) -> PublicationIntent:
    if not isinstance(intent, PublicationIntent):
        raise TypeError("PostgresPublicationLedger.register requires PublicationIntent.")

    payload = encode_intent(intent)
    statement = (
        postgres_insert(_PUBLICATION_OPERATION)
        .values(
            operation_id=str(intent.operation_id),
            dataset_id=intent.dataset_id,
            intent_fingerprint=intent.intent_fingerprint,
            requested_at=intent.requested_at,
            intent_payload=payload,
            terminal_event_type=None,
            resolved_at=None,
        )
        .on_conflict_do_nothing(index_elements=[_PUBLICATION_OPERATION.c.operation_id])
        .returning(_PUBLICATION_OPERATION.c.operation_id)
    )
    inserted_operation_id = connection.execute(statement).scalar_one_or_none()
    if inserted_operation_id is not None:
        return intent

    existing = _get_operation(connection, intent.operation_id)
    if existing is None:
        raise RuntimeError("Publication operation conflict could not be reloaded.")
    existing.assert_same_intent_as(intent)
    return existing


def _append(connection: Connection, event: PublicationLifecycleEvent) -> None:
    if not isinstance(event, PublicationLifecycleEvent):
        raise TypeError("PostgresPublicationLedger.append requires PublicationLifecycleEvent.")

    payload = encode_event(event)

    duplicate = connection.execute(
        select(_PUBLICATION_EVENT.c.event_payload).where(
            _PUBLICATION_EVENT.c.event_id == event.event_id
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        existing = decode_event(cast(str, duplicate))
        if existing != event:
            raise ValueError("Lifecycle event ID cannot be reused for different event evidence.")
        return

    if event.operation_id is not None:
        operation_row = (
            connection.execute(
                select(_PUBLICATION_OPERATION)
                .where(_PUBLICATION_OPERATION.c.operation_id == str(event.operation_id))
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if operation_row is None:
            raise KeyError(str(event.operation_id))
        intent = decode_intent(cast(str, operation_row["intent_payload"]))
        if intent.dataset_id != event.dataset_id:
            raise ValueError("Lifecycle event dataset does not match registered intent.")

        duplicate_after_lock = connection.execute(
            select(_PUBLICATION_EVENT.c.event_payload).where(
                _PUBLICATION_EVENT.c.event_id == event.event_id
            )
        ).scalar_one_or_none()
        if duplicate_after_lock is not None:
            existing = decode_event(cast(str, duplicate_after_lock))
            if existing != event:
                raise ValueError(
                    "Lifecycle event ID cannot be reused for different event evidence."
                )
            return

        if operation_row["resolved_at"] is not None:
            raise ValueError("Resolved publication operation cannot accept new events.")

    statement = (
        postgres_insert(_PUBLICATION_EVENT)
        .values(
            event_id=event.event_id,
            operation_id=None if event.operation_id is None else str(event.operation_id),
            dataset_id=event.dataset_id,
            event_type=event.event_type.value,
            occurred_at=event.occurred_at,
            event_payload=payload,
        )
        .on_conflict_do_nothing(index_elements=[_PUBLICATION_EVENT.c.event_id])
        .returning(_PUBLICATION_EVENT.c.event_id)
    )
    inserted_event_id = connection.execute(statement).scalar_one_or_none()
    if inserted_event_id is None:
        duplicate_payload: object = connection.execute(
            select(_PUBLICATION_EVENT.c.event_payload).where(
                _PUBLICATION_EVENT.c.event_id == event.event_id
            )
        ).scalar_one()
        existing = decode_event(cast(str, duplicate_payload))
        if existing != event:
            raise ValueError("Lifecycle event ID cannot be reused for different event evidence.")
        return

    if event.operation_id is not None and is_terminal_event(event.event_type):
        connection.execute(
            update(_PUBLICATION_OPERATION)
            .where(_PUBLICATION_OPERATION.c.operation_id == str(event.operation_id))
            .values(
                terminal_event_type=event.event_type.value,
                resolved_at=event.occurred_at,
            )
        )


def _get_operation(
    connection: Connection,
    operation_id: PublicationOperationId,
) -> PublicationIntent | None:
    if not isinstance(operation_id, PublicationOperationId):
        raise TypeError("PostgresPublicationLedger.get_operation requires PublicationOperationId.")
    payload = connection.execute(
        select(_PUBLICATION_OPERATION.c.intent_payload).where(
            _PUBLICATION_OPERATION.c.operation_id == str(operation_id)
        )
    ).scalar_one_or_none()
    if payload is None:
        return None
    return decode_intent(cast(str, payload))


def _list_operations(
    connection: Connection,
    *,
    dataset_id: str | None,
    unresolved_only: bool,
) -> tuple[PublicationIntent, ...]:
    if dataset_id is not None and (not isinstance(dataset_id, str) or not dataset_id.strip()):
        raise ValueError("PostgresPublicationLedger dataset_id must be non-blank or None.")

    statement = select(_PUBLICATION_OPERATION.c.intent_payload)
    if dataset_id is not None:
        statement = statement.where(_PUBLICATION_OPERATION.c.dataset_id == dataset_id)
    if unresolved_only:
        statement = statement.where(_PUBLICATION_OPERATION.c.resolved_at.is_(None))
    statement = statement.order_by(
        _PUBLICATION_OPERATION.c.requested_at,
        _PUBLICATION_OPERATION.c.operation_id,
    )
    rows: Sequence[object] = connection.execute(statement).scalars().all()
    return tuple(decode_intent(cast(str, payload)) for payload in rows)


def _list_events(
    connection: Connection,
    *,
    operation_id: PublicationOperationId | None,
    dataset_id: str | None,
) -> tuple[PublicationLifecycleEvent, ...]:
    if operation_id is not None and not isinstance(operation_id, PublicationOperationId):
        raise TypeError(
            "PostgresPublicationLedger.list_events operation_id must be "
            "PublicationOperationId or None."
        )
    if dataset_id is not None and (not isinstance(dataset_id, str) or not dataset_id.strip()):
        raise ValueError("PostgresPublicationLedger dataset_id must be non-blank or None.")

    statement = select(_PUBLICATION_EVENT.c.event_payload)
    if operation_id is not None:
        statement = statement.where(_PUBLICATION_EVENT.c.operation_id == str(operation_id))
    if dataset_id is not None:
        statement = statement.where(_PUBLICATION_EVENT.c.dataset_id == dataset_id)
    statement = statement.order_by(_PUBLICATION_EVENT.c.sequence_id)
    rows: Sequence[object] = connection.execute(statement).scalars().all()
    return tuple(decode_event(cast(str, payload)) for payload in rows)


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


def _safe_dsn(dsn: str) -> str:
    try:
        return make_url(_normalize_dsn(dsn)).render_as_string(hide_password=True)
    except ArgumentError:
        return "<invalid-postgresql-dsn>"


def _record_replay_lineage(
    connection: Connection,
    lineage: ReplayLineage,
) -> ReplayLineage:
    if not isinstance(lineage, ReplayLineage):
        raise TypeError("PostgresPublicationLedger.record_replay_lineage requires ReplayLineage.")
    lineage_id = lineage.lineage_id or ""
    statement = (
        postgres_insert(_REPLAY_LINEAGE)
        .values(
            lineage_id=lineage_id,
            source_run_id=str(lineage.source_run_id),
            replay_run_id=str(lineage.replay_run_id),
            dataset_id=lineage.dataset_id,
            version_id=lineage.version_id,
            origin_raw_checksum=lineage.origin_raw_checksum,
            replay_raw_checksum=lineage.replay_raw_checksum,
            matched=lineage.matched,
            replayed_at=lineage.replayed_at,
            published=lineage.published,
        )
        .on_conflict_do_nothing(index_elements=[_REPLAY_LINEAGE.c.lineage_id])
        .returning(_REPLAY_LINEAGE.c.lineage_id)
    )
    inserted_id = connection.execute(statement).scalar_one_or_none()
    if inserted_id is None:
        row = connection.execute(
            select(
                _REPLAY_LINEAGE.c.source_run_id,
                _REPLAY_LINEAGE.c.replay_run_id,
                _REPLAY_LINEAGE.c.dataset_id,
                _REPLAY_LINEAGE.c.version_id,
                _REPLAY_LINEAGE.c.origin_raw_checksum,
                _REPLAY_LINEAGE.c.replay_raw_checksum,
                _REPLAY_LINEAGE.c.matched,
            ).where(_REPLAY_LINEAGE.c.lineage_id == lineage_id)
        ).one()
        if (
            row[0] != str(lineage.source_run_id)
            or row[1] != str(lineage.replay_run_id)
            or row[2] != lineage.dataset_id
            or row[3] != lineage.version_id
            or row[4] != lineage.origin_raw_checksum
            or row[5] != lineage.replay_raw_checksum
            or row[6] != lineage.matched
        ):
            raise ValueError("Replay lineage ID cannot be reused for different lineage evidence.")
        if lineage.published:
            connection.execute(
                update(_REPLAY_LINEAGE)
                .where(_REPLAY_LINEAGE.c.lineage_id == lineage_id)
                .values(published=True)
            )
    return lineage


def _list_replays(
    connection: Connection,
    *,
    dataset_id: str | None,
    source_run_id: IngestionRunId | None,
) -> tuple[ReplayLineage, ...]:
    if dataset_id is not None and (not isinstance(dataset_id, str) or not dataset_id.strip()):
        raise ValueError("PostgresPublicationLedger dataset_id must be non-blank or None.")
    if source_run_id is not None and not isinstance(source_run_id, IngestionRunId):
        raise TypeError("PostgresPublicationLedger source_run_id must be IngestionRunId or None.")

    statement = select(
        _REPLAY_LINEAGE.c.lineage_id,
        _REPLAY_LINEAGE.c.source_run_id,
        _REPLAY_LINEAGE.c.replay_run_id,
        _REPLAY_LINEAGE.c.dataset_id,
        _REPLAY_LINEAGE.c.version_id,
        _REPLAY_LINEAGE.c.origin_raw_checksum,
        _REPLAY_LINEAGE.c.replay_raw_checksum,
        _REPLAY_LINEAGE.c.matched,
        _REPLAY_LINEAGE.c.replayed_at,
        _REPLAY_LINEAGE.c.published,
    )
    if dataset_id is not None:
        statement = statement.where(_REPLAY_LINEAGE.c.dataset_id == dataset_id)
    if source_run_id is not None:
        statement = statement.where(_REPLAY_LINEAGE.c.source_run_id == str(source_run_id))
    statement = statement.order_by(_REPLAY_LINEAGE.c.replayed_at, _REPLAY_LINEAGE.c.lineage_id)
    rows = connection.execute(statement).all()
    return tuple(
        ReplayLineage(
            lineage_id=row[0],
            source_run_id=IngestionRunId.parse(row[1]),
            replay_run_id=IngestionRunId.parse(row[2]),
            dataset_id=row[3],
            version_id=row[4],
            origin_raw_checksum=row[5],
            replay_raw_checksum=row[6],
            matched=bool(row[7]),
            replayed_at=row[8],
            published=bool(row[9]),
        )
        for row in rows
    )
