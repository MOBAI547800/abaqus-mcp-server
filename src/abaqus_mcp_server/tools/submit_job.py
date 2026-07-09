"""Submit an Abaqus analysis job for execution."""

from __future__ import annotations

import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI, AbaqusCLIError
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="submit_job",
    description="Submit an Abaqus analysis job from an .inp file. "
    "IMPORTANT: This starts a potentially long-running computation and MUST "
    "be confirmed by the user. Set confirmed=True to proceed. "
    "Returns the job name and instructions for checking status.",
)
async def submit_job(
    input_file: str,
    cpus: int = 1,
    confirmed: bool = False,
) -> str:
    """Submit an Abaqus analysis job.

    Args:
        input_file: Path to the .inp file (relative to workspace).
        cpus: Number of CPUs to use (capped by server config).
        confirmed: Must be True to actually submit the job.
    """
    if not confirmed:
        return (
            "⚠️  Job submission requires confirmation. "
            "Please call this tool again with confirmed=True to proceed.\n\n"
            f"Input file: {input_file}\n"
            f"CPUs: {cpus}\n\n"
            "This will start a potentially long-running Abaqus analysis."
        )

    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    resolved = validate_path(input_file, workspace=ws, must_exist=True)

    if resolved.suffix.lower() not in (".inp",):
        return f"Error: Input file must be a .inp file, got: {resolved.suffix}"

    job_name = resolved.stem

    # Check for existing lock file (job already running)
    lck = resolved.parent / f"{job_name}.lck"
    if lck.exists():
        return f"Error: Job '{job_name}' appears to be already running (.lck file exists)."

    cli = AbaqusCLI(cfg)

    try:
        result = await cli.submit_job(
            resolved,
            job_name=job_name,
            cpus=min(cpus, cfg.max_cpus),
            cwd=resolved.parent,
        )
    except AbaqusCLIError as exc:
        return f"Error submitting job: {exc}"

    if result.returncode != 0:
        return (
            f"Job submission returned non-zero exit code: {result.returncode}\n\n"
            f"--- stderr ---\n{result.stderr[:cfg.max_output_chars]}"
        )

    # Check job status
    status = await cli.get_job_status(job_name, cwd=resolved.parent)

    return (
        f"=== Job Submitted ===\n"
        f"Job name: {job_name}\n"
        f"Input file: {resolved.name}\n"
        f"CPUs: {min(cpus, cfg.max_cpus)}\n"
        f"Elapsed: {result.elapsed:.1f}s\n"
        f"Status: {status}\n\n"
        f"Monitor with: check_job_status(job_name='{job_name}')\n"
        f"Read logs with: read_job_logs(job_name='{job_name}')"
    )
