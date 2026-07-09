"""Tests for ODB extraction pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from abaqus_mcp_server.abaqus_cli import AbaqusCLIError, AbaqusResult
from abaqus_mcp_server.tools.extract_odb_summary import _make_summary_script


class TestOdbSummaryScript:
    """Tests for the generated ODB summary script."""

    def test_script_is_valid_python(self):
        code = _make_summary_script(Path("/tmp/test.odb"))
        import ast
        ast.parse(code)

    def test_script_contains_odb_path(self):
        code = _make_summary_script(Path("C:/workspace/model.odb"))
        assert "C:/workspace/model.odb" in code

    def test_script_has_json_markers(self):
        code = _make_summary_script(Path("test.odb"))
        assert "ODB_JSON_START" in code
        assert "ODB_JSON_END" in code

    def test_script_uses_read_only(self):
        code = _make_summary_script(Path("test.odb"))
        assert "readOnly=True" in code


class TestExtractOdbSummaryMocked:
    """Test the extract_odb_summary tool pipeline with mocked AbaqusCLI."""

    @pytest.mark.asyncio
    async def test_parses_valid_json_output(self, tmp_path):
        """Simulate successful ODB extraction with mock JSON output."""
        from abaqus_mcp_server.tools.extract_odb_summary import (
            extract_odb_summary,
        )

        # Create a mock ODB file
        odb = tmp_path / "test.odb"
        odb.write_text("mock odb content")

        # Valid JSON output from the mock
        mock_json = """===ODB_JSON_START===
{
  "steps": ["Step-1"],
  "frames": {"Step-1": 5},
  "instances": ["PART-1-1"],
  "field_outputs": ["U", "S", "E"],
  "history_regions": ["Assembly ASSEMBLY"]
}
===ODB_JSON_END==="""

        mock_result = AbaqusResult(0, mock_json, "", 1.0)

        # We need to patch at the right level. The tool creates its own
        # AbaqusCLI internally, so we patch _run on the class.
        with patch(
            "abaqus_mcp_server.abaqus_cli.AbaqusCLI._run",
            AsyncMock(return_value=mock_result),
        ):
            # Override workspace to tmp_path
            with patch(
                "abaqus_mcp_server.tools.extract_odb_summary.AbaqusServerConfig"
            ) as MockConfig:
                cfg_instance = MockConfig.return_value
                cfg_instance.resolve_workspace.return_value = tmp_path
                cfg_instance.max_output_chars = 20000
                cfg_instance.script_timeout = 300

                result = await extract_odb_summary(str(odb))

        assert "Step-1" in result
        assert "PART-1-1" in result
        assert "U" in result

    @pytest.mark.asyncio
    async def test_handles_odb_error_in_json(self, tmp_path):
        """Simulate ODB read error inside Abaqus Python."""
        from abaqus_mcp_server.tools.extract_odb_summary import (
            extract_odb_summary,
        )

        odb = tmp_path / "broken.odb"
        odb.write_text("mock")

        mock_json = """===ODB_JSON_START===
{"error": "ODB file is corrupted"}
===ODB_JSON_END==="""

        mock_result = AbaqusResult(1, mock_json, "", 0.5)

        with patch(
            "abaqus_mcp_server.abaqus_cli.AbaqusCLI._run",
            AsyncMock(return_value=mock_result),
        ):
            with patch(
                "abaqus_mcp_server.tools.extract_odb_summary.AbaqusServerConfig"
            ) as MockConfig:
                cfg_instance = MockConfig.return_value
                cfg_instance.resolve_workspace.return_value = tmp_path
                cfg_instance.max_output_chars = 20000

                result = await extract_odb_summary(str(odb))

        assert "error" in result.lower() or "corrupted" in result.lower()

    @pytest.mark.asyncio
    async def test_rejects_non_odb_file(self, tmp_path):
        """Should reject .txt files."""
        from abaqus_mcp_server.tools.extract_odb_summary import (
            extract_odb_summary,
        )

        txt = tmp_path / "notes.txt"
        txt.write_text("not an odb")

        with patch(
            "abaqus_mcp_server.tools.extract_odb_summary.AbaqusServerConfig"
        ) as MockConfig:
            cfg_instance = MockConfig.return_value
            cfg_instance.resolve_workspace.return_value = tmp_path

            result = await extract_odb_summary(str(txt))

        assert "must be a .odb" in result.lower()

    @pytest.mark.asyncio
    async def test_rejects_missing_file(self, tmp_path):
        """Should error on nonexistent file."""
        from abaqus_mcp_server.tools.extract_odb_summary import (
            extract_odb_summary,
        )

        with patch(
            "abaqus_mcp_server.tools.extract_odb_summary.AbaqusServerConfig"
        ) as MockConfig:
            cfg_instance = MockConfig.return_value
            cfg_instance.resolve_workspace.return_value = tmp_path

            with pytest.raises(FileNotFoundError):
                await extract_odb_summary(str(tmp_path / "missing.odb"))

    @pytest.mark.asyncio
    async def test_handles_cli_error(self, tmp_path):
        """Should surface AbaqusCLI errors gracefully."""
        from abaqus_mcp_server.tools.extract_odb_summary import (
            extract_odb_summary,
        )

        odb = tmp_path / "test.odb"
        odb.write_text("mock")

        with patch(
            "abaqus_mcp_server.abaqus_cli.AbaqusCLI._run",
            AsyncMock(side_effect=AbaqusCLIError("Simulated failure")),
        ):
            with patch(
                "abaqus_mcp_server.tools.extract_odb_summary.AbaqusServerConfig"
            ) as MockConfig:
                cfg_instance = MockConfig.return_value
                cfg_instance.resolve_workspace.return_value = tmp_path

                result = await extract_odb_summary(str(odb))

        assert "error" in result.lower()
