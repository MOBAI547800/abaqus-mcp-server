"""Configuration management via environment variables.

All settings are read from environment variables prefixed with ``ABAQUS_MCP_``.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AbaqusServerConfig(BaseSettings):
    """Server configuration, loaded from environment variables.

    Environment variables are prefixed with ``ABAQUS_MCP_``.
    """

    model_config = SettingsConfigDict(
        env_prefix="ABAQUS_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Abaqus command ──────────────────────────────────────────────
    abaqus_command: str = Field(
        default="",
        description="Path to the Abaqus launcher (abaqus.bat). Auto-detected if empty.",
    )

    # ── Workspace ───────────────────────────────────────────────────
    workspace_dir: str = Field(
        default="./abaqus_work",
        description="Root directory for all Abaqus file operations. All paths are sandboxed under here.",
    )

    create_workspace: bool = Field(
        default=True,
        description="Auto-create the workspace directory if it does not exist.",
    )

    # ── Timeouts (seconds) ──────────────────────────────────────────
    script_timeout: int = Field(
        default=300,
        ge=1,
        le=7200,
        description="Maximum runtime for a Python script executed via abaqus python (seconds).",
    )

    job_timeout: int = Field(
        default=3600,
        ge=1,
        le=86400,
        description="Maximum wall-clock time for an Abaqus analysis job (seconds).",
    )

    # ── Resource limits ─────────────────────────────────────────────
    max_cpus: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum number of CPUs allowed per job.",
    )

    max_output_chars: int = Field(
        default=20000,
        ge=100,
        le=1_000_000,
        description="Maximum number of characters returned in a single tool output.",
    )

    allow_overwrite: bool = Field(
        default=False,
        description="Allow tools to overwrite existing files. If False, an error is returned instead.",
    )

    # ── Logging ─────────────────────────────────────────────────────
    log_level: str = Field(
        default="WARNING",
        description="Python logging level for the server (DEBUG, INFO, WARNING, ERROR).",
    )

    # ── Derived helpers ─────────────────────────────────────────────

    def resolve_workspace(self) -> Path:
        """Return the absolute, resolved workspace path."""
        return Path(self.workspace_dir).resolve()

    def resolve_abaqus_command(self) -> str:
        """Return the abaqus command, auto-detecting if not explicitly set."""
        if self.abaqus_command:
            return self.abaqus_command
        return _autodetect_abaqus()


def _autodetect_abaqus() -> str:
    """Try to locate abaqus.bat on the system."""
    # Known install locations on Windows
    candidates = [
        r"D:\SIMULIA\Commands\abaqus.bat",
        r"C:\SIMULIA\Commands\abaqus.bat",
        r"E:\SIMULIA\Commands\abaqus.bat",
        r"C:\Program Files\Dassault Systemes\SIMULIA\Commands\abaqus.bat",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    # Fall back to PATH lookup
    found = shutil.which("abaqus")
    if found:
        return found

    # Last resort: assume it's on PATH
    return "abaqus"
