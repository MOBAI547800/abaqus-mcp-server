"""Abaqus command-line interface abstraction.

All subprocess interaction with Abaqus goes through this module.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.constants import JOB_UNKNOWN

logger = logging.getLogger(__name__)


@dataclass
class AbaqusResult:
    """Result from an Abaqus subprocess call."""

    returncode: int
    stdout: str
    stderr: str
    elapsed: float  # seconds


class AbaqusCLIError(Exception):
    """Raised when an Abaqus CLI operation fails."""


class AbaqusCLITimeoutError(AbaqusCLIError):
    """Raised when an Abaqus command exceeds its timeout."""


class AbaqusCLI:
    """Encapsulates all subprocess calls to Abaqus.

    Args:
        config: Server configuration (abaqus command path, timeouts, etc.).
    """

    def __init__(self, config: AbaqusServerConfig) -> None:
        self._config = config
        self._abaqus_cmd = config.resolve_abaqus_command()

    # ── Public API ───────────────────────────────────────────────────────────

    async def check_environment(self) -> AbaqusResult:
        """Run ``abaqus information=release`` to verify the installation."""
        return await self._run(["information=release"], timeout=30)

    async def run_python_script(
        self,
        script_path: Path,
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> AbaqusResult:
        """Run a Python script with Abaqus's bundled Python.

        Equivalent to: ``abaqus python script.py``

        The Abaqus Python has ``odbAccess`` and other Abaqus-specific
        modules available.

        Args:
            script_path: Path to the Python script (must exist).
            cwd: Working directory for the subprocess.
            timeout: Seconds before the process is killed.
        """
        if not script_path.exists():
            raise AbaqusCLIError(f"Script not found: {script_path}")

        timeout = timeout or self._config.script_timeout
        return await self._run(
            ["python", str(script_path)],
            cwd=cwd,
            timeout=timeout,
        )

    async def submit_job(
        self,
        input_file: Path,
        *,
        job_name: str | None = None,
        cpus: int = 1,
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> AbaqusResult:
        """Submit an Abaqus analysis job.

        Equivalent to: ``abaqus job=<name> input=<file> cpus=<n> interactive``

        Args:
            input_file: Path to the ``.inp`` file.
            job_name: Job name (defaults to stem of *input_file*).
            cpus: Number of CPUs (clamped to config.max_cpus).
            cwd: Working directory.
            timeout: Seconds before the process is killed.
        """
        if not input_file.exists():
            raise AbaqusCLIError(f"Input file not found: {input_file}")

        name = job_name or input_file.stem
        cpus = min(cpus, self._config.max_cpus)
        timeout = timeout or self._config.job_timeout

        return await self._run(
            [
                f"job={name}",
                f"input={input_file.name}",
                f"cpus={cpus}",
                "interactive",
            ],
            cwd=cwd or input_file.parent,
            timeout=timeout,
        )

    async def get_job_status(self, job_name: str, *, cwd: Path) -> str:
        """Check the status of a job by reading its ``.sta`` and ``.lck`` files.

        Returns one of: ``completed``, ``running``, ``failed``, ``aborted``,
        ``submitted``, or ``unknown``.
        """
        sta_path = cwd / f"{job_name}.sta"
        lck_path = cwd / f"{job_name}.lck"

        if lck_path.exists():
            return "running"

        if not sta_path.exists():
            return JOB_UNKNOWN

        content = sta_path.read_text(encoding="utf-8", errors="replace")
        return _classify_sta_content(content)

    async def read_file(
        self, file_path: Path, tail_lines: int = 200
    ) -> str:
        """Read a text file, returning the last *tail_lines* lines."""
        if not file_path.exists():
            raise AbaqusCLIError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if len(lines) <= tail_lines:
            return content
        return "\n".join(lines[-tail_lines:])

    async def clean_job(self, job_name: str, *, cwd: Path) -> list[Path]:
        """Delete intermediate files for a job.

        Returns a list of files that were deleted.
        """
        from abaqus_mcp_server.constants import CLEANABLE_EXTENSIONS

        deleted: list[Path] = []
        for ext in CLEANABLE_EXTENSIONS:
            f = cwd / f"{job_name}{ext}"
            if f.exists():
                f.unlink()
                deleted.append(f)
        return deleted

    # ── Private implementation ────────────────────────────────────────────────

    async def _run(
        self,
        abaqus_args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int,
    ) -> AbaqusResult:
        """Execute an Abaqus command via subprocess.

        On Windows, wraps the call with ``cmd.exe /c "call abaqus.bat ..."``
        because Abaqus uses batch files.
        """
        if cwd is None:
            cwd = Path.cwd()

        cmd = _build_windows_command(self._abaqus_cmd, abaqus_args)
        logger.info("Running: %s (cwd=%s, timeout=%ds)", " ".join(cmd), cwd, timeout)

        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            # Kill on timeout
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            raise AbaqusCLITimeoutError(
                f"Abaqus command timed out after {timeout}s: {' '.join(cmd)}"
            )

        elapsed = time.perf_counter() - t0
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        result = AbaqusResult(
            returncode=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            elapsed=elapsed,
        )

        logger.info(
            "Abaqus command finished: returncode=%d elapsed=%.1fs",
            result.returncode,
            result.elapsed,
        )
        if result.returncode != 0:
            logger.warning("Abaqus stderr: %s", result.stderr[:500])

        return result


# ── Private helpers ──────────────────────────────────────────────────────────

def _build_windows_command(abaqus_path: str, args: list[str]) -> list[str]:
    """Build a subprocess arg list that invokes abaqus.bat correctly on Windows.

    Batch files require ``cmd.exe /c "call ..."`` so that the batch file's
    ``endlocal`` doesn't destroy the environment mid-execution.
    """
    return ["cmd.exe", "/c", "call", abaqus_path, *args]


def _classify_sta_content(content: str) -> str:
    """Inspect ``.sta`` content and classify job status."""
    if "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in content:
        return "completed"
    if "THE ANALYSIS HAS BEEN TERMINATED" in content:
        return "aborted"
    if "THE ANALYSIS HAS NOT BEEN COMPLETED" in content:
        return "failed"
    if content.strip():
        return "running"
    return JOB_UNKNOWN
