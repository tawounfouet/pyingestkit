from pyingestkit.replay.service import _safe_historical_parameters


def test_secret_values_are_not_restored() -> None:
    value = {
        "api_token": "***REDACTED***",
        "page": 2,
        "nested": {"password": "[REDACTED]", "ok": True},
    }
    assert _safe_historical_parameters(value) == {"page": 2, "nested": {"ok": True}}
