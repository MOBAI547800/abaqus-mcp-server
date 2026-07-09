"""Query the status of a submitted Abaqus job."""

from __future__ import annotations

import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="job_status",
    description="Check the status of an Abaqus job. Reads the .sta and .lck files "
    "to determine if the job is running, completed, failed, or aborted. "
    "Returns the current status, step progress, and any warnings from .msg.",
)
async def job_status(job_name: str) -> str:
    """Query the status of an Abaqus job by name."""
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    # Validate job_name is a safe filename
    from abaqus_mcp_server.security import validate_filename

    try:
        validate_filename(job_name)
    except Exception as exc:
        return f"Error: Invalid job name: {exc}"

    cli = AbaqusCLI(cfg)

    # Look for job files in the jobs subdirectory, then workspace root
    search_dirs = [ws / "jobs", ws]
    job_dir = None
    for d in search_dirs:
        if (d / f"{job_name}.sta").exists() or (d / f"{job_name}.lck").exists():
            job_dir = d
            break

    if job_dir is None:
        return (
            f"Job '{job_name}' not found. No .sta or .lck files found in workspace.\n"
            f"Searched: {', '.join(str(d) for d in search_dirs)}"
        )

    status = await cli.get_job_status(job_name, cwd=job_dir)

    lines = [
        f"=== Job Status: {job_name} ===",
        f"Status: {status}",
    ]

    # Read .sta tail for progress info
    sta_path = job_dir / f"{job_name}.sta"
    if sta_path.exists():
        sta_content = sta_path.read_text(encoding="utf-8", errors="replace")
        sta_lines = sta_content.strip().splitlines()
        if sta_lines:
            lines.append(f"\n.sta tail (last 10 lines):")
            for line in sta_lines[-10:]:
                lines.append(f"  {line.strip()}")

    # Read .msg for warnings/errors
    msg_path = job_dir / f"{job_name}.msg"
    if msg_path.exists():
        msg_content = msg_path.read_text(encoding="utf-8", errors="replace")
        errors = [l for l in msg_content.splitlines() if "ERROR" in l.upper()]
        warnings = [l for l in msg_content.splitlines() if "WARNING" in l.upper()]
        if errors:
            lines.append(f"\nErrors ({len(errors)}):")
            for e in errors[-20:]:
                lines.append(f"  {e.strip()[:200]}")
        if warnings:
            lines.append(f"\nWarnings ({len(warnings)}):")
            for w in warnings[-20:]:
                lines.append(f"  {w.strip()[:200]}")

    return "\n".join(lines)
