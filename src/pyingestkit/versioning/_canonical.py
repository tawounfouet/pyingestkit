from __future__ import annotations

import base64
import json
import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class _MissingValue:
    __slots__ = ()


MISSING = _MissingValue()


def canonical_value(value: Any) -> object:
    """Return a deterministic, type-aware JSON-safe representation."""

    if value is MISSING:
        return {"$type": "missing"}
    if value is None:
        return {"$type": "none"}
    if isinstance(value, bool):
        return {"$type": "bool", "value": value}
    if isinstance(value, int):
        return {"$type": "int", "value": str(value)}
    if isinstance(value, float):
        if math.isnan(value):
            encoded = "nan"
        elif math.isinf(value):
            encoded = "+inf" if value > 0 else "-inf"
        else:
            encoded = value.hex()
        return {"$type": "float", "value": encoded}
    if isinstance(value, str):
        return {"$type": "str", "value": value}
    if isinstance(value, bytes):
        encoded = base64.b64encode(value).decode("ascii")
        return {"$type": "bytes", "encoding": "base64", "value": encoded}
    if isinstance(value, Decimal):
        return {"$type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"$type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$type": "date", "value": value.isoformat()}
    if isinstance(value, list):
        return {"$type": "list", "items": [canonical_value(item) for item in value]}
    if isinstance(value, tuple):
        return {"$type": "tuple", "items": [canonical_value(item) for item in value]}
    if isinstance(value, Mapping):
        items = [
            [canonical_value(key), canonical_value(item)]
            for key, item in value.items()
        ]
        items.sort(key=lambda pair: canonical_json(pair[0]))
        return {"$type": "mapping", "items": items}
    raise TypeError(f"Unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    encoded = value if _is_canonical(value) else canonical_value(value)
    return json.dumps(encoded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_canonical(value: Any) -> bool:
    return isinstance(value, dict) and "$type" in value
