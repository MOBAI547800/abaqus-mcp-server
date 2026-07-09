"""Tests for CLI entry point and basic server connectivity."""

from __future__ import annotations

import pytest

from tests.conftest import mcp_connection

# Expected MVP tool names
EXPECTED_TOOLS = {
    "check_environment",
    "validate_workspace",
    "generate_script",
    "run_script",
    "submit_job",
    "job_status",
    "read_job_logs",
    "extract_odb_summary",
    "extract_field_output",
    "extract_history_output",
    "clean_job",
}


class TestServerStartup:
    """Verify the server starts and responds to MCP protocol messages."""

    @pytest.mark.asyncio
    async def test_server_initializes(self):
        """Server should accept initialize and respond without error."""
        async with mcp_connection() as session:
            assert session is not None

    @pytest.mark.asyncio
    async def test_list_tools_returns_expected_tools(self):
        """After tool registration, list_tools should include all MVP tools."""
        async with mcp_connection() as session:
            result = await session.list_tools()
            tool_names = {t.name for t in result.tools}
            missing = EXPECTED_TOOLS - tool_names
            assert not missing, f"Missing tools: {missing}"
            assert EXPECTED_TOOLS.issubset(tool_names), (
                f"Expected at least {EXPECTED_TOOLS}, got {tool_names}"
            )

    @pytest.mark.asyncio
    async def test_server_responds_to_ping(self):
        """Server should respond to ping without error."""
        async with mcp_connection() as session:
            result = await session.send_ping()
            # send_ping returns EmptyResult on success
            assert result is not None
