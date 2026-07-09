"""Run an Abaqus Python script via ``abaqus python``."""

from __future__ import annotations

import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI, AbaqusCLIError
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="run_script",
    description="Run a Python script (.py) using Abaqus's bundled Python interpreter. "
    "The Abaqus Python has access to odbAccess and other Abaqus-specific modules. "
    "The script path must be within the workspace. "
    "This tool requires user confirmation before execution.",
)
async def run_script(
    script_path: str,
    timeout_sec: int | None = None,
) -> str:
    """Execute a Python script through the Abaqus Python interpreter."""
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    # Validate path is within workspace
    resolved = validate_path(script_path, workspace=ws, must_exist=True)

    if resolved.suffix.lower() not in (".py",):
        return f"Error: Script must be a .py file, got: {resolved.suffix}"

    cli = AbaqusCLI(cfg)

    try:
        result = await cli.run_python_script(
            resolved,
            cwd=resolved.parent,
            timeout=timeout_sec or cfg.script_timeout,
        )
    except AbaqusCLIError as exc:
        return f"Error running script: {exc}"

    lines = [
        f"=== Script Execution ===",
        f"Script: {resolved.name}",
        f"Exit code: {result.returncode}",
        f"Elapsed: {result.elapsed:.1f}s",
        "",
    ]

    if result.stdout.strip():
        stdout = result.stdout
        if len(stdout) > cfg.max_output_chars:
            stdout = stdout[:cfg.max_output_chars] + "\n... [output truncated]"
        lines.append("--- stdout ---")
        lines.append(stdout)

    if result.stderr.strip():
        stderr = result.stderr
        if len(stderr) > cfg.max_output_chars:
            stderr = stderr[:cfg.max_output_chars] + "\n... [output truncated]"
        lines.append("--- stderr ---")
        lines.append(stderr)

    return "\n".join(lines)
