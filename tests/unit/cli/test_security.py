"""Unit tests for the CLI security helpers and credentials redaction."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyingestkit.cli.exit_codes import ExitCode
from pyingestkit.cli.security import (
    REDACTED,
    SecurityError,
    assert_path_within_workspace,
    redact_mapping,
    redact_sensitive_text,
    sanitize_input_path,
)


def test_sanitize_input_path_accepts_clean_paths() -> None:
    path = sanitize_input_path("data/input.csv")
    assert isinstance(path, Path)
    assert str(path) == "data/input.csv"


def test_sanitize_input_path_rejects_null_bytes() -> None:
    with pytest.raises(SecurityError) as exc_info:
        sanitize_input_path("data/input\0.csv")
    assert exc_info.value.exit_code == ExitCode.SECURITY_ERROR
    assert "null-byte" in str(exc_info.value).lower()


def test_assert_path_within_workspace_accepts_valid_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target_file = workspace / "configs" / "job.yml"
    target_file.parent.mkdir()
    target_file.write_text("dummy", encoding="utf-8")

    # Relative path resolution
    resolved = assert_path_within_workspace("configs/job.yml", workspace_root=workspace)
    assert resolved == target_file.resolve()

    # Exact workspace root
    assert assert_path_within_workspace(workspace, workspace_root=workspace) == workspace.resolve()


def test_assert_path_within_workspace_rejects_path_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret", encoding="utf-8")

    # Relative traversal via ../
    with pytest.raises(SecurityError) as exc_info:
        assert_path_within_workspace("../outside.txt", workspace_root=workspace)
    assert exc_info.value.exit_code == ExitCode.SECURITY_ERROR
    assert "escapes the workspace root" in str(exc_info.value)

    # Absolute path outside workspace
    with pytest.raises(SecurityError) as exc_info:
        assert_path_within_workspace(outside_file, workspace_root=workspace)
    assert exc_info.value.exit_code == ExitCode.SECURITY_ERROR


def test_redact_sensitive_text_masks_uri_passwords() -> None:
    raw_uri = "postgresql://ingest_user:Sup3rS3cret!@db.internal:5432/analytics"
    redacted = redact_sensitive_text(raw_uri)
    assert "Sup3rS3cret!" not in redacted
    assert f"postgresql://ingest_user:{REDACTED}@db.internal:5432/analytics" == redacted


def test_redact_sensitive_text_masks_assignment_patterns() -> None:
    text = (
        'Connection failure with password="ultra_secret_pass" and '
        "api_key: ak_test_123456789. Also token=jwt_secret_token_value."
    )
    redacted = redact_sensitive_text(text)
    assert "ultra_secret_pass" not in redacted
    assert "ak_test_123456789" not in redacted
    assert "jwt_secret_token_value" not in redacted
    assert f'password="{REDACTED}"' in redacted or f"password={REDACTED}" in redacted
    assert f"api_key: {REDACTED}" in redacted
    assert f"token={REDACTED}" in redacted


def test_redact_sensitive_text_masks_bearer_token() -> None:
    text = "HTTP request header: Authorization: Bearer mock_sample_jwt_bearer_token_12345"
    redacted = redact_sensitive_text(text)
    assert "mock_sample_jwt_bearer_token_12345" not in redacted
    assert f"Authorization: Bearer {REDACTED}" in redacted


def test_redact_sensitive_text_preserves_innocuous_text() -> None:
    text = "https://data.gouv.fr/datasets/sirene.csv?limit=100&format=json"
    assert redact_sensitive_text(text) == text
    assert redact_sensitive_text("") == ""


def test_redact_mapping_recursive() -> None:
    data = {
        "job_id": "customer_sync",
        "api_key": "raw_secret_key",
        "nested": {
            "password": "db_password",
            "url": "postgresql://usr:pwd@host/db",
            "safe_list": ["item1", "item2"],
        },
    }
    redacted = redact_mapping(data)
    assert redacted["job_id"] == "customer_sync"
    assert redacted["api_key"] == REDACTED
    assert redacted["nested"]["password"] == REDACTED
    assert "pwd" not in redacted["nested"]["url"]
    assert redacted["nested"]["safe_list"] == ["item1", "item2"]
