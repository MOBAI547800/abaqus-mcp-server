"""Tests for security module — path validation and workspace sandboxing."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from abaqus_mcp_server.security import (
    SecurityError,
    truncate_output,
    validate_filename,
    validate_path,
)


class TestValidatePath:
    """Tests for validate_path — the core workspace sandbox function."""

    @pytest.fixture
    def ws(self) -> Path:
        with tempfile.TemporaryDirectory(prefix="abaqus_ws_") as tmp:
            yield Path(tmp).resolve()

    def test_accepts_valid_subpath(self, ws: Path):
        (ws / "sub").mkdir()
        result = validate_path("sub", workspace=ws)
        assert result == (ws / "sub")

    def test_accepts_file_in_subdirectory(self, ws: Path):
        (ws / "jobs").mkdir()
        f = ws / "jobs" / "test.inp"
        f.write_text("dummy")
        result = validate_path("jobs/test.inp", workspace=ws, must_exist=True)
        assert result == f

    def test_rejects_path_traversal_dotdot(self, ws: Path):
        with pytest.raises(SecurityError, match="escapes workspace"):
            validate_path("../../../etc/passwd", workspace=ws)

    def test_rejects_path_traversal_mixed(self, ws: Path):
        with pytest.raises(SecurityError):
            validate_path("sub/../../../outside", workspace=ws)

    def test_rejects_absolute_path_outside_workspace(self, ws: Path):
        with pytest.raises(SecurityError, match="escapes workspace"):
            validate_path("D:/outside/file.txt", workspace=ws)

    def test_accepts_absolute_path_inside_workspace(self, ws: Path):
        (ws / "data").mkdir()
        abs_path = str(ws / "data" / "model.inp")
        result = validate_path(abs_path, workspace=ws)
        assert result.resolve() == (ws / "data" / "model.inp")

    def test_raises_file_not_found_when_must_exist(self, ws: Path):
        with pytest.raises(FileNotFoundError):
            validate_path("nonexistent.inp", workspace=ws, must_exist=True)

    def test_rejects_pipe_character(self, ws: Path):
        with pytest.raises(SecurityError, match="forbidden character"):
            validate_path("script|rm", workspace=ws)

    def test_rejects_semicolon(self, ws: Path):
        with pytest.raises(SecurityError, match="forbidden character"):
            validate_path("safe;dangerous", workspace=ws)

    def test_rejects_newline_injection(self, ws: Path):
        with pytest.raises(SecurityError, match="forbidden character"):
            validate_path("script\nrm -rf /", workspace=ws)

    def test_case_insensitive_on_windows(self, ws: Path):
        """Windows path comparison must be case-insensitive."""
        (ws / "Jobs").mkdir()
        # Access using different case
        result = validate_path("jobs", workspace=ws)
        assert result.resolve() == (ws / "Jobs").resolve()


class TestValidateFilename:
    """Tests for validate_filename — single-segment name checks."""

    def test_accepts_plain_name(self):
        assert validate_filename("beam.inp") == "beam.inp"

    def test_accepts_unix_style_relative_path(self):
        assert validate_filename("jobs/beam.inp") == "jobs/beam.inp"

    def test_accepts_windows_style_relative_path(self):
        assert validate_filename(r"jobs\beam.inp") == r"jobs\beam.inp"

    def test_rejects_dotdot(self):
        with pytest.raises(SecurityError, match="Path traversal"):
            validate_filename("../../etc/passwd")

    def test_rejects_dotdot_windows(self):
        with pytest.raises(SecurityError, match="Path traversal"):
            validate_filename(r"..\..\outside.txt")

    def test_rejects_absolute_path(self):
        with pytest.raises(SecurityError, match="Absolute paths"):
            validate_filename("D:/absolute/path.txt")

    def test_rejects_shell_chars(self):
        for ch in [";", "|", "&", "$", "`"]:
            with pytest.raises(SecurityError):
                validate_filename(f"file{ch}.inp")


class TestTruncateOutput:
    """Tests for truncate_output."""

    def test_no_truncation_when_under_limit(self):
        text = "short output"
        assert truncate_output(text, 100) == text

    def test_truncates_long_text(self):
        text = "x" * 1000
        result = truncate_output(text, 100)
        assert len(result) < 200  # head + tail + notice
        assert "[truncated" in result

    def test_includes_notice(self):
        text = "x" * 5000
        result = truncate_output(text, 200)
        assert "truncated" in result.lower()
