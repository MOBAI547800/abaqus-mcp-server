"""Shared test helpers for abaqus_mcp_server tests."""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def temp_workspace() -> Path:
    """Create a temporary workspace directory for isolated testing."""
    with tempfile.TemporaryDirectory(prefix="abaqus_mcp_test_") as tmpdir:
        yield Path(tmpdir)


@asynccontextmanager
async def mcp_connection():
    """Context manager that spawns the MCP server and returns an initialized session.

    Use this in tests with ``async with mcp_connection() as session:``
    to avoid anyio cancel-scope issues with async generator fixtures.
    """
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "abaqus_mcp_server.cli", "serve"],
        env={
            **os.environ,
            "ABAQUS_MCP_WORKSPACE_DIR": tempfile.mkdtemp(prefix="abaqus_test_ws_"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
