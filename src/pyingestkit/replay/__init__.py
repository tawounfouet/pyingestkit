from typing import TYPE_CHECKING

from pyingestkit.application.replay import ReplayServiceV2
from pyingestkit.domain.replay import ReplayRequest, ReplayResult

if TYPE_CHECKING:
    from .models import ReplayContext as ReplayContext
    from .models import ReplayRawArtifact as ReplayRawArtifact
    from .resolver import materialize_replayed_raw as materialize_replayed_raw
    from .service import ReplayService as ReplayService

__all__ = ["ReplayRequest", "ReplayResult", "ReplayServiceV2"]


def __getattr__(name: str) -> object:
    if name == "ReplayService":
        from .service import ReplayService

        return ReplayService
    if name == "ReplayContext":
        from .models import ReplayContext

        return ReplayContext
    if name == "ReplayRawArtifact":
        from .models import ReplayRawArtifact

        return ReplayRawArtifact
    if name == "materialize_replayed_raw":
        from .resolver import materialize_replayed_raw

        return materialize_replayed_raw
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
