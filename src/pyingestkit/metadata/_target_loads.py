from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from pyingestkit.logging.filters import redact_text

from ._schema import target_loads
from .capabilities import TargetLoadMetadataCapability
from .models import TargetLoadRecord


def _mapping(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


class SQLAlchemyTargetLoadMetadataMixin(TargetLoadMetadataCapability):
    """Additive SQLAlchemy implementation for V0.5 target-load audit metadata."""

    engine: Engine

    def record_target_load(self, record: TargetLoadRecord) -> None:
        values = {
            "run_id": record.run_id,
            "target_id": record.target_id,
            "dataset_id": record.dataset_id,
            "dataset_version_id": record.dataset_version_id,
            "mode": record.mode,
            "status": record.status,
            "destination": record.destination,
            "rows_input": record.rows_input,
            "rows_loaded": record.rows_loaded,
            "rows_verified": record.rows_verified,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_seconds": record.duration_seconds,
            "idempotency_action": record.idempotency_action,
            "metrics_json": dict(record.metrics),
            "error": None if record.error is None else redact_text(record.error),
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(target_loads.c.load_id).where(target_loads.c.load_id == record.load_id)
            ).scalar_one_or_none()
            if existing is None:
                connection.execute(
                    insert(target_loads).values(
                        load_id=record.load_id,
                        created_at=record.created_at,
                        **values,
                    )
                )
                return
            connection.execute(
                update(target_loads)
                .where(target_loads.c.load_id == record.load_id)
                .values(**values)
            )

    def get_target_load(self, load_id: str) -> TargetLoadRecord | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(target_loads).where(target_loads.c.load_id == load_id))
                .mappings()
                .one_or_none()
            )
        return None if row is None else self._target_load_record(row)

    def list_target_loads(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        target_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> tuple[TargetLoadRecord, ...]:
        statement = select(target_loads)
        if run_id is not None:
            statement = statement.where(target_loads.c.run_id == run_id)
        if dataset_id is not None:
            statement = statement.where(target_loads.c.dataset_id == dataset_id)
        if target_id is not None:
            statement = statement.where(target_loads.c.target_id == target_id)
        if status is not None:
            statement = statement.where(target_loads.c.status == status.upper())
        statement = statement.order_by(
            target_loads.c.started_at.desc(), target_loads.c.load_id.desc()
        ).limit(max(1, limit))
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(self._target_load_record(row) for row in rows)

    @staticmethod
    def _target_load_record(row: RowMapping) -> TargetLoadRecord:
        return TargetLoadRecord(
            load_id=cast(str, row["load_id"]),
            run_id=cast(str, row["run_id"]),
            target_id=cast(str, row["target_id"]),
            dataset_id=cast(str, row["dataset_id"]),
            dataset_version_id=cast(str | None, row["dataset_version_id"]),
            mode=cast(str, row["mode"]),
            status=cast(str, row["status"]),
            destination=cast(str, row["destination"]),
            rows_input=cast(int, row["rows_input"]),
            rows_loaded=cast(int, row["rows_loaded"]),
            rows_verified=cast(int | None, row["rows_verified"]),
            started_at=cast(Any, row["started_at"]),
            completed_at=cast(Any, row["completed_at"]),
            duration_seconds=cast(float | None, row["duration_seconds"]),
            idempotency_action=cast(str | None, row["idempotency_action"]),
            metrics=_mapping(row["metrics_json"]),
            error=cast(str | None, row["error"]),
            created_at=cast(Any, row["created_at"]),
        )


class MemoryTargetLoadMetadataMixin(TargetLoadMetadataCapability):
    """In-memory implementation kept separate from the legacy MemoryMetadataStore body."""

    def _target_load_state(self) -> dict[str, TargetLoadRecord]:
        state = self.__dict__.get("_target_load_records")
        if state is None:
            state = {}
            self.__dict__["_target_load_records"] = state
        return cast(dict[str, TargetLoadRecord], state)

    def record_target_load(self, record: TargetLoadRecord) -> None:
        state = self._target_load_state()
        existing = state.get(record.load_id)
        created_at = existing.created_at if existing is not None else record.created_at
        error = None if record.error is None else redact_text(record.error)
        state[record.load_id] = replace(record, created_at=created_at, error=error)

    def get_target_load(self, load_id: str) -> TargetLoadRecord | None:
        return self._target_load_state().get(load_id)

    def list_target_loads(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        target_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> tuple[TargetLoadRecord, ...]:
        rows = list(self._target_load_state().values())
        if run_id is not None:
            rows = [row for row in rows if row.run_id == run_id]
        if dataset_id is not None:
            rows = [row for row in rows if row.dataset_id == dataset_id]
        if target_id is not None:
            rows = [row for row in rows if row.target_id == target_id]
        if status is not None:
            rows = [row for row in rows if row.status == status.upper()]
        rows.sort(key=lambda row: (row.started_at, row.load_id), reverse=True)
        return tuple(rows[: max(1, limit)])
