"""Tests for AbaqusCLI — the subprocess abstraction layer.

All tests use mocks; no real Abaqus installation is required.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from abaqus_mcp_server.abaqus_cli import (
    AbaqusCLI,
    AbaqusCLIError,
    AbaqusCLITimeoutError,
    AbaqusResult,
    _build_windows_command,
    _classify_sta_content,
)
from abaqus_mcp_server.config import AbaqusServerConfig


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fake_proc(returncode=0, stdout=b"", stderr=b""):
    """Create an AsyncMock process with the given outputs."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


def _config(**overrides) -> AbaqusServerConfig:
    kwargs = {
        "abaqus_command": "abaqus_test",
        "workspace_dir": "./test_work",
    }
    kwargs.update(overrides)
    return AbaqusServerConfig(**kwargs)


# ── Unit: helpers ────────────────────────────────────────────────────────────


class TestBuildWindowsCommand:
    def test_wraps_with_cmd_exe_call(self):
        cmd = _build_windows_command(r"C:\abaqus.bat", ["information=release"])
        assert cmd[0] == "cmd.exe"
        assert cmd[1] == "/c"
        assert cmd[2] == "call"
        assert cmd[3] == r"C:\abaqus.bat"
        assert cmd[4] == "information=release"

    def test_multiple_args(self):
        cmd = _build_windows_command("abaqus", ["job=test", "input=test.inp", "cpus=4"])
        assert cmd[-3:] == ["job=test", "input=test.inp", "cpus=4"]


class TestClassifySta:
    def test_completed(self):
        content = "STEP 1 COMPLETED\nTHE ANALYSIS HAS COMPLETED SUCCESSFULLY"
        assert _classify_sta_content(content) == "completed"

    def test_aborted(self):
        content = "THE ANALYSIS HAS BEEN TERMINATED"
        assert _classify_sta_content(content) == "aborted"

    def test_failed(self):
        content = "THE ANALYSIS HAS NOT BEEN COMPLETED"
        assert _classify_sta_content(content) == "failed"

    def test_running(self):
        content = "STEP INC ATT SEVERE ...\n1 5 1 0 ..."
        assert _classify_sta_content(content) == "running"

    def test_empty_is_unknown(self):
        assert _classify_sta_content("") == "unknown"


# ── AbaqusCLI: mocked subprocess ─────────────────────────────────────────────


class TestAbaqusCLICheckEnvironment:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        cli = AbaqusCLI(_config())
        with patch.object(
            cli, "_run", AsyncMock(return_value=AbaqusResult(0, "Abaqus 2025", "", 0.5))
        ):
            result = await cli.check_environment()
            assert result.returncode == 0
            assert "Abaqus 2025" in result.stdout


class TestAbaqusCLIRunScript:
    @pytest.mark.asyncio
    async def test_runs_abaqus_python(self, tmp_path):
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        cli = AbaqusCLI(_config())
        with patch.object(
            cli, "_run", AsyncMock(return_value=AbaqusResult(0, "hello", "", 0.3))
        ) as mock_run:
            result = await cli.run_python_script(script)
            assert result.stdout == "hello"
            # Verify the call included "python" and the script path
            call_args = mock_run.call_args[0][0]
            assert "python" in call_args

    @pytest.mark.asyncio
    async def test_raises_when_script_missing(self):
        cli = AbaqusCLI(_config())
        with pytest.raises(AbaqusCLIError, match="Script not found"):
            await cli.run_python_script(Path("/nonexistent/script.py"))


class TestAbaqusCLISubmitJob:
    @pytest.mark.asyncio
    async def test_submits_with_correct_args(self, tmp_path):
        inp = tmp_path / "beam.inp"
        inp.write_text("*HEADING\n...")

        cli = AbaqusCLI(_config())
        with patch.object(
            cli, "_run", AsyncMock(return_value=AbaqusResult(0, "Job completed", "", 10.0))
        ) as mock_run:
            result = await cli.submit_job(inp, cpus=2, cwd=tmp_path)
            assert result.returncode == 0
            call_args = mock_run.call_args[0][0]
            # Should contain job=beam
            job_arg = [a for a in call_args if a.startswith("job=")]
            assert len(job_arg) == 1

    @pytest.mark.asyncio
    async def test_caps_cpus_at_max(self, tmp_path):
        inp = tmp_path / "test.inp"
        inp.write_text("*HEADING")

        cfg = _config(max_cpus=4)
        cli = AbaqusCLI(cfg)
        with patch.object(
            cli, "_run", AsyncMock(return_value=AbaqusResult(0, "", "", 1.0))
        ) as mock_run:
            await cli.submit_job(inp, cpus=16, cwd=tmp_path)
            call_args = mock_run.call_args[0][0]
            cpus_arg = [a for a in call_args if a.startswith("cpus=")]
            assert cpus_arg == ["cpus=4"]

    @pytest.mark.asyncio
    async def test_raises_when_inp_missing(self):
        cli = AbaqusCLI(_config())
        with pytest.raises(AbaqusCLIError, match="Input file not found"):
            await cli.submit_job(Path("/nonexistent/test.inp"))


class TestAbaqusCLIJobStatus:
    @pytest.mark.asyncio
    async def test_running_when_lck_exists(self, tmp_path):
        (tmp_path / "test.lck").write_text("")
        cli = AbaqusCLI(_config())
        status = await cli.get_job_status("test", cwd=tmp_path)
        assert status == "running"

    @pytest.mark.asyncio
    async def test_completed_from_sta(self, tmp_path):
        (tmp_path / "test.sta").write_text(
            "THE ANALYSIS HAS COMPLETED SUCCESSFULLY\n"
        )
        cli = AbaqusCLI(_config())
        status = await cli.get_job_status("test", cwd=tmp_path)
        assert status == "completed"

    @pytest.mark.asyncio
    async def test_unknown_when_no_files(self, tmp_path):
        cli = AbaqusCLI(_config())
        status = await cli.get_job_status("test", cwd=tmp_path)
        assert status == "unknown"


class TestAbaqusCLIReadFile:
    @pytest.mark.asyncio
    async def test_reads_last_n_lines(self, tmp_path):
        f = tmp_path / "test.log"
        f.write_text("\n".join(str(i) for i in range(100)))
        cli = AbaqusCLI(_config())
        content = await cli.read_file(f, tail_lines=10)
        assert len(content.splitlines()) == 10

    @pytest.mark.asyncio
    async def test_returns_full_content_when_short(self, tmp_path):
        f = tmp_path / "test.log"
        f.write_text("line1\nline2\n")
        cli = AbaqusCLI(_config())
        content = await cli.read_file(f, tail_lines=100)
        assert "line1" in content


class TestAbaqusCLICleanJob:
    @pytest.mark.asyncio
    async def test_deletes_intermediate_files(self, tmp_path):
        # Create some cleanable files
        for ext in [".com", ".prt", ".sim", ".023"]:
            (tmp_path / f"test{ext}").write_text("garbage")
        # Create a file that should NOT be deleted
        (tmp_path / "test.odb").write_text("precious")

        cli = AbaqusCLI(_config())
        deleted = await cli.clean_job("test", cwd=tmp_path)

        assert len(deleted) >= 4
        for d in deleted:
            assert not d.exists()
        # odb should survive
        assert (tmp_path / "test.odb").exists()


class TestAbaqusCLITimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises(self, tmp_path):
        script = tmp_path / "slow.py"
        script.write_text("")

        cli = AbaqusCLI(_config())
        # Simulate a timeout by patching _run to raise
        with patch.object(cli, "_run", AsyncMock(side_effect=AbaqusCLITimeoutError("timed out"))):
            with pytest.raises(AbaqusCLITimeoutError):
                await cli.run_python_script(script, timeout=1)


class TestAbaqusCLIRealRun:
    """Smoke test with real subprocess (no Abaqus required).

    Uses ``cmd.exe /c echo`` to validate the subprocess plumbing.
    """

    @pytest.mark.asyncio
    async def test_run_simple_command(self, tmp_path):
        """Use actual subprocess to verify _run plumbing works."""
        cfg = _config(abaqus_command="cmd.exe")
        cli = AbaqusCLI(cfg)

        # Override _run internals for a simple test
        result = await cli._run(["/c", "echo", "hello_world"], cwd=tmp_path, timeout=10)
        assert result.returncode == 0
        assert "hello_world" in result.stdout
        assert result.elapsed >= 0
