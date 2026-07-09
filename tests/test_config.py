"""Tests for configuration module."""

from __future__ import annotations

import os
from pathlib import Path

from abaqus_mcp_server.config import AbaqusServerConfig


class TestConfigDefaults:
    """Verify default configuration values."""

    def test_default_workspace(self):
        cfg = AbaqusServerConfig()
        assert cfg.workspace_dir == "./abaqus_work"

    def test_default_timeouts(self):
        cfg = AbaqusServerConfig()
        assert cfg.script_timeout == 300
        assert cfg.job_timeout == 3600

    def test_default_max_cpus(self):
        cfg = AbaqusServerConfig()
        assert cfg.max_cpus == 4

    def test_default_max_output_chars(self):
        cfg = AbaqusServerConfig()
        assert cfg.max_output_chars == 20000

    def test_allow_overwrite_defaults_false(self):
        cfg = AbaqusServerConfig()
        assert cfg.allow_overwrite is False


class TestConfigFromEnv:
    """Verify environment variable overrides."""

    def test_workspace_dir_from_env(self, monkeypatch):
        monkeypatch.setenv("ABAQUS_MCP_WORKSPACE_DIR", "/custom/workspace")
        cfg = AbaqusServerConfig()
        assert cfg.workspace_dir == "/custom/workspace"

    def test_job_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("ABAQUS_MCP_JOB_TIMEOUT", "7200")
        cfg = AbaqusServerConfig()
        assert cfg.job_timeout == 7200

    def test_max_cpus_from_env(self, monkeypatch):
        monkeypatch.setenv("ABAQUS_MCP_MAX_CPUS", "8")
        cfg = AbaqusServerConfig()
        assert cfg.max_cpus == 8

    def test_allow_overwrite_from_env(self, monkeypatch):
        monkeypatch.setenv("ABAQUS_MCP_ALLOW_OVERWRITE", "true")
        cfg = AbaqusServerConfig()
        assert cfg.allow_overwrite is True

    def test_abaqus_command_from_env(self, monkeypatch):
        monkeypatch.setenv("ABAQUS_MCP_ABAQUS_COMMAND", r"C:\custom\abaqus.bat")
        cfg = AbaqusServerConfig()
        assert cfg.abaqus_command == r"C:\custom\abaqus.bat"


class TestConfigHelpers:
    """Verify derived configuration helpers."""

    def test_resolve_workspace_absolute(self):
        cfg = AbaqusServerConfig(workspace_dir=r"D:\abaqus_workspace")
        resolved = cfg.resolve_workspace()
        assert resolved == Path(r"D:\abaqus_workspace")

    def test_resolve_abaqus_command_returns_set_value(self):
        cfg = AbaqusServerConfig(abaqus_command="my_abaqus")
        assert cfg.resolve_abaqus_command() == "my_abaqus"

    def test_resolve_abaqus_command_autodetect(self):
        cfg = AbaqusServerConfig(abaqus_command="")
        cmd = cfg.resolve_abaqus_command()
        # Should return something truthy on this system (abaqus is installed)
        assert cmd
