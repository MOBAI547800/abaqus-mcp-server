"""Validate that a workspace directory is properly set up for Abaqus jobs."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.security import SecurityError, validate_path

logger = logging.getLogger(__name__)

WORKSPACE_SUBDIRS = ["jobs", "scripts", "results", "logs"]


@mcp.tool(
    name="validate_workspace",
    description="Validate that the workspace directory is properly set up. "
    "Creates required subdirectories (jobs/, scripts/, results/, logs/) if "
    "create_if_missing is True. Use this before running jobs.",
)
async def validate_workspace(
    create_if_missing: bool = True,
) -> str:
    """Validate or initialise the workspace directory."""
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    lines = [f"=== Workspace Validation ===", f"Path: {ws}"]

    if not ws.exists():
        if create_if_missing and cfg.create_workspace:
            ws.mkdir(parents=True, exist_ok=True)
            lines.append("Status: CREATED (did not exist)")
        else:
            lines.append("Status: MISSING (set create_if_missing=True to create)")
            return "\n".join(lines)
    else:
        lines.append("Status: EXISTS")

    # Check writability
    try:
        test_file = ws / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        lines.append("Writable: YES")
    except Exception:
        lines.append("Writable: NO (permission issue)")

    # Disk space
    usage = shutil.disk_usage(ws)
    free_gb = usage.free / (1024**3)
    lines.append(f"Free disk space: {free_gb:.1f} GB")

    # Create subdirectories
    if create_if_missing:
        for sub in WORKSPACE_SUBDIRS:
            subdir = ws / sub
            if not subdir.exists():
                subdir.mkdir(parents=True, exist_ok=True)
                lines.append(f"  Created: {sub}/")
            else:
                lines.append(f"  Exists:  {sub}/")

    # Existing Abaqus files
    abq_files = list(ws.glob("*.inp")) + list(ws.glob("*.odb")) + list(ws.glob("*.cae"))
    if abq_files:
        lines.append(f"\nExisting Abaqus files ({len(abq_files)}):")
        for f in abq_files[:20]:
            lines.append(f"  {f.name}")

    return "\n".join(lines)
