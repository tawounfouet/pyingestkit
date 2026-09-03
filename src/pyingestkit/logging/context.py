from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_RUN_ID: ContextVar[str | None] = ContextVar("pyingestkit_run_id", default=None)
_JOB_ID: ContextVar[str | None] = ContextVar("pyingestkit_job_id", default=None)
_STEP: ContextVar[str | None] = ContextVar("pyingestkit_step", default=None)


def current_log_context() -> dict[str, str | None]:
    return {
        "run_id": _RUN_ID.get(),
        "job_id": _JOB_ID.get(),
        "step": _STEP.get(),
    }


@contextmanager
def log_context(
    *,
    run_id: str | None = None,
    job_id: str | None = None,
    step: str | None = None,
) -> Iterator[None]:
    tokens: list[tuple[ContextVar[str | None], Token[str | None]]] = []
    if run_id is not None:
        tokens.append((_RUN_ID, _RUN_ID.set(run_id)))
    if job_id is not None:
        tokens.append((_JOB_ID, _JOB_ID.set(job_id)))
    if step is not None:
        tokens.append((_STEP, _STEP.set(step)))
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)
