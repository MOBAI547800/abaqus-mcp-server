"""Read the output logs from an Abaqus job."""

from __future__ import annotations

import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.constants import ERROR_KEYWORDS, WARNING_KEYWORDS
from abaqus_mcp_server.security import truncate_output, validate_filename

logger = logging.getLogger(__name__)

LOG_TYPES = ["sta", "msg", "dat", "log"]


@mcp.tool(
    name="read_job_logs",
    description="Read the output logs from an Abaqus job (.sta, .msg, .dat, .log). "
    "Automatically extracts errors, warnings, and key diagnostic information. "
    "Use this to diagnose job failures or monitor progress.",
)
async def read_job_logs(
    job_name: str,
    log_types: str = "all",
    tail_lines: int = 200,
) -> str:
    """Read and parse Abaqus job log files.

    Args:
        job_name: Name of the job (without extension).
        log_types: Comma-separated list: sta, msg, dat, log. Default: all.
        tail_lines: Number of lines to return from each log file.
    """
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    try:
        validate_filename(job_name)
    except Exception as exc:
        return f"Error: Invalid job name: {exc}"

    cli = AbaqusCLI(cfg)

    # Determine which log types to read
    if log_types.lower() == "all":
        types_to_read = LOG_TYPES
    else:
        types_to_read = [t.strip().lower() for t in log_types.split(",")]
        for t in types_to_read:
            if t not in LOG_TYPES:
                return f"Error: Unknown log type '{t}'. Valid types: {', '.join(LOG_TYPES)}"

    # Search for job files
    search_dirs = [ws / "jobs", ws]
    results: list[str] = [f"=== Logs for Job: {job_name} ==="]

    for log_type in types_to_read:
        results.append(f"\n--- .{log_type} ---")
        file_found = False

        for d in search_dirs:
            fpath = d / f"{job_name}.{log_type}"
            if fpath.exists():
                try:
                    content = await cli.read_file(fpath, tail_lines=tail_lines)
                except Exception as exc:
                    results.append(f"Error reading {fpath.name}: {exc}")
                    file_found = True
                    break

                truncated = truncate_output(content, cfg.max_output_chars)
                results.append(truncated)

                # Scan for key patterns
                keywords_found = set()
                for kw in ERROR_KEYWORDS + WARNING_KEYWORDS:
                    if kw.lower() in content.lower():
                        keywords_found.add(kw)
                if keywords_found:
                    results.append(f"\n[Keywords found: {', '.join(sorted(keywords_found))}]")

                file_found = True
                break

        if not file_found:
            results.append("(file not found)")

    return "\n".join(results)
