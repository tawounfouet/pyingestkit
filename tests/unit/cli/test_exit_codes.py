"""Unit tests for the CLI ExitCode enumeration."""

from __future__ import annotations

from pyingestkit.cli.exit_codes import ExitCode


def test_exit_code_values_are_deterministic() -> None:
    """Ensure all exit codes maintain their contracted numeric values."""
    assert int(ExitCode.SUCCESS) == 0
    assert int(ExitCode.GENERAL_ERROR) == 1
    assert int(ExitCode.VALIDATION_ERROR) == 2
    assert int(ExitCode.EXECUTION_FAILURE) == 3
    assert int(ExitCode.SECURITY_ERROR) == 4
    assert int(ExitCode.MISSING_OPTIONAL_DEPENDENCY) == 11
    assert int(ExitCode.FILESYSTEM_ERROR) == 12
    assert int(ExitCode.INTERNAL_ERROR) == 70
    assert int(ExitCode.INTERRUPTED) == 130
    assert int(ExitCode.BROKEN_PIPE) == 141


def test_exit_codes_are_integers() -> None:
    """Verify that ExitCode instances can be used directly as integers."""
    assert isinstance(ExitCode.SUCCESS, int)
    assert isinstance(ExitCode.MISSING_OPTIONAL_DEPENDENCY, int)
    assert isinstance(ExitCode.BROKEN_PIPE, int)


def test_all_expected_exit_codes_exist() -> None:
    """Ensure the enum has the expected members."""
    expected = {
        "SUCCESS",
        "GENERAL_ERROR",
        "VALIDATION_ERROR",
        "EXECUTION_FAILURE",
        "SECURITY_ERROR",
        "MISSING_OPTIONAL_DEPENDENCY",
        "FILESYSTEM_ERROR",
        "INTERNAL_ERROR",
        "INTERRUPTED",
        "BROKEN_PIPE",
    }
    assert set(ExitCode.__members__.keys()) == expected
