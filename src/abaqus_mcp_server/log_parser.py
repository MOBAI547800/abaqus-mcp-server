"""Parsers for Abaqus output files: .sta, .msg, .dat, .log."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from abaqus_mcp_server.constants import (
    ERROR_KEYWORDS,
    SUCCESS_KEYWORDS,
    WARNING_KEYWORDS,
)


@dataclass
class StaInfo:
    """Parsed information from a ``.sta`` file."""

    status: str  # completed, running, failed, aborted, unknown
    current_increment: int | None = None
    current_step: int | None = None
    step_time: float | None = None
    total_time: float | None = None
    summary: str = ""


@dataclass
class MessageEntry:
    """A single message from a ``.msg`` file."""

    severity: str  # ERROR, WARNING, INFO
    message: str
    line_number: int | None = None


@dataclass
class DatFileContent:
    """Parsed content from a ``.dat`` file."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    full_text: str = ""


# ── .sta parser ──────────────────────────────────────────────────────────────


def parse_sta_file(content: str) -> StaInfo:
    """Parse an Abaqus ``.sta`` file and extract status information.

    Args:
        content: Full text content of the ``.sta`` file.

    Returns:
        ``StaInfo`` with status classification and progress details.
    """
    if not content.strip():
        return StaInfo(status="unknown", summary="(empty file)")

    # Determine status from key phrases
    status = _classify_status(content)

    # Try to extract the last increment line
    # Format: STEP INC ATT SEVERE EQUIL TOTAL TOTAL ...
    # Example:    1    5   1      0     1    0.100  0.100 ...
    inc_info = _parse_last_increment(content)

    return StaInfo(
        status=status,
        current_increment=inc_info.get("increment"),
        current_step=inc_info.get("step"),
        step_time=inc_info.get("step_time"),
        total_time=inc_info.get("total_time"),
        summary=_extract_summary_lines(content),
    )


def _classify_status(content: str) -> str:
    """Classify job status from .sta content."""
    if "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in content:
        return "completed"
    if "THE ANALYSIS HAS BEEN TERMINATED" in content:
        return "aborted"
    if "THE ANALYSIS HAS NOT BEEN COMPLETED" in content:
        return "failed"
    if content.strip().splitlines():
        return "running"
    return "unknown"


_STA_INCREMENT_RE = re.compile(
    r"^\s*(?P<step>\d+)\s+(?P<inc>\d+)\s+\d+\s+\d+\s+\d+\s+"
    r"(?P<step_time>[0-9.]+)\s+(?P<total_time>[0-9.]+)",
    re.MULTILINE,
)


def _parse_last_increment(content: str) -> dict:
    """Find the last increment line in .sta content."""
    matches = list(_STA_INCREMENT_RE.finditer(content))
    if not matches:
        return {}

    m = matches[-1]
    return {
        "step": int(m.group("step")),
        "increment": int(m.group("inc")),
        "step_time": float(m.group("step_time")),
        "total_time": float(m.group("total_time")),
    }


def _extract_summary_lines(content: str) -> str:
    """Extract the most relevant summary lines from .sta content."""
    lines = content.strip().splitlines()
    summary_lines = []
    for line in lines:
        stripped = line.strip()
        if any(
            kw.casefold() in stripped.casefold()
            for kw in SUCCESS_KEYWORDS + ["TERMINATED", "COMPLETED", "ABORTED"]
        ):
            summary_lines.append(stripped)
    if not summary_lines and lines:
        # Return the last few lines as summary
        summary_lines = [l.strip() for l in lines[-5:] if l.strip()]
    return "\n".join(summary_lines)


# ── .msg parser ──────────────────────────────────────────────────────────────


def parse_msg_file(content: str) -> list[MessageEntry]:
    """Parse an Abaqus ``.msg`` file into structured message entries.

    Args:
        content: Full text content of the ``.msg`` file.

    Returns:
        List of ``MessageEntry`` objects, one per message line.
    """
    entries: list[MessageEntry] = []
    lines = content.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        severity = "INFO"
        upper = stripped.upper()

        # Check error keywords first (more specific)
        if any(kw.casefold() in stripped.casefold() for kw in ERROR_KEYWORDS):
            severity = "ERROR"
        elif any(kw.casefold() in stripped.casefold() for kw in WARNING_KEYWORDS):
            severity = "WARNING"

        entries.append(
            MessageEntry(
                severity=severity,
                message=stripped[:500],
                line_number=i + 1,
            )
        )

    return entries


# ── .dat parser ──────────────────────────────────────────────────────────────

_ERROR_LINE_RE = re.compile(r"\*{3,}\s*ERROR", re.IGNORECASE)
_WARNING_LINE_RE = re.compile(r"\*{3,}\s*WARNING", re.IGNORECASE)


def parse_dat_file(content: str) -> DatFileContent:
    """Parse an Abaqus ``.dat`` file.

    Extracts errors, warnings, and a textual summary.

    Args:
        content: Full text content of the ``.dat`` file.

    Returns:
        ``DatFileContent`` with categorized errors and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if _ERROR_LINE_RE.search(stripped):
            errors.append(stripped[:300])
        elif _WARNING_LINE_RE.search(stripped):
            warnings.append(stripped[:300])

    # Build summary
    summary_parts = []
    if errors:
        summary_parts.append(f"{len(errors)} error(s) detected")
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s) detected")
    if not summary_parts:
        summary_parts.append("No errors or warnings detected")

    return DatFileContent(
        errors=errors,
        warnings=warnings,
        summary="; ".join(summary_parts),
        full_text=content,
    )
