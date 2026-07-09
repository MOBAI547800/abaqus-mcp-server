"""Check Abaqus environment — installation, version, and workspace status."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig

logger = logging.getLogger(__name__)


@mcp.tool(
    name="check_environment",
    description="Verify Abaqus installation and report MCP server configuration. "
    "Use this to check if Abaqus is available before running scripts or jobs.",
)
async def check_environment() -> str:
    """Check the Abaqus installation and server environment."""
    cfg = AbaqusServerConfig()
    cli = AbaqusCLI(cfg)

    lines = [
        "=== Abaqus MCP Server Environment ===",
        f"Python version: {sys.version}",
        f"Python executable: {sys.executable}",
        f"Abaqus command: {cli._abaqus_cmd}",
        f"Workspace directory: {cfg.resolve_workspace()}",
        f"Workspace exists: {cfg.resolve_workspace().exists()}",
        "",
    ]

    # Try to get Abaqus version
    try:
        result = await cli.check_environment()
        if result.returncode == 0:
            lines.append("Abaqus is available:")
            # Extract first few meaningful lines
            for line in result.stdout.splitlines()[:10]:
                if line.strip():
                    lines.append(f"  {line.strip()}")
        else:
            lines.append(f"Abaqus returned non-zero exit code: {result.returncode}")
            if result.stderr.strip():
                lines.append(f"stderr: {result.stderr[:500]}")
    except Exception as exc:
        lines.append(f"Abaqus check failed: {exc}")

    lines.extend([
        "",
        f"Default script timeout: {cfg.script_timeout}s",
        f"Default job timeout: {cfg.job_timeout}s",
        f"Max CPUs: {cfg.max_cpus}",
        f"Allow overwrite: {cfg.allow_overwrite}",
    ])

    return "\n".join(lines)
