"""Security module — workspace sandboxing and path validation.

Every tool that touches the filesystem must route through this module.
"""

from __future__ import annotations

import os
from pathlib import Path


class SecurityError(Exception):
    """Raised when a security policy is violated."""


def validate_path(
    user_path: str | Path,
    *,
    workspace: Path,
    must_exist: bool = False,
) -> Path:
    """Resolve *user_path* relative to *workspace* and verify it stays inside.

    Args:
        user_path: The user-supplied path (relative to workspace, or an
            absolute path already inside the workspace).
        workspace: The root workspace directory (already resolved).
        must_exist: If True, raise when the resolved path does not exist.

    Returns:
        The fully resolved ``Path``, guaranteed to be within *workspace*.

    Raises:
        SecurityError: If the resolved path escapes the workspace.
        FileNotFoundError: If *must_exist* is True and the path is missing.
    """
    workspace = workspace.resolve()
    raw = Path(user_path)

    # Reject dangerous characters before any resolution
    _reject_dangerous_chars(str(user_path))

    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (workspace / raw).resolve()

    # Case-insensitive containment check (Windows filesystem)
    if not _is_subpath(resolved, workspace):
        raise SecurityError(
            f"Path escapes workspace: '{user_path}' resolves to "
            f"'{resolved}' which is outside '{workspace}'."
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")

    return resolved


def validate_filename(name: str) -> str:
    """Check *name* for path traversal and dangerous shell characters.

    Returns the name unchanged if it passes validation.

    Raises:
        SecurityError: If *name* contains ``..``, absolute path components,
            or dangerous characters.
    """
    _reject_dangerous_chars(name)

    if ".." in name.replace("\\", "/").split("/"):
        raise SecurityError(f"Path traversal detected in filename: '{name}'")

    if os.path.isabs(name):
        raise SecurityError(f"Absolute paths are not allowed: '{name}'")

    return name


def truncate_output(text: str, max_chars: int) -> str:
    """Truncate *text* to *max_chars*, appending a notice if truncated."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    head = text[:half]
    tail = text[-half:]
    return (
        f"{head}\n\n... [truncated {len(text) - max_chars:,} chars] ...\n\n{tail}"
    )


# ── Private helpers ──────────────────────────────────────────────────────────

_DANGEROUS_CHARS: set[str] = {"\x00", ";", "|", "&", "$", "`", "(", ")", "{", "}", "<", ">", "\n", "\r"}


def _reject_dangerous_chars(text: str) -> None:
    for ch in _DANGEROUS_CHARS:
        if ch in text:
            raise SecurityError(
                f"Input contains forbidden character {repr(ch)}: '{text[:200]}'"
            )


def _is_subpath(child: Path, parent: Path) -> bool:
    """Check whether *child* is equal to or inside *parent*.

    Uses case-insensitive comparison on Windows.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        pass

    # Windows: try case-normalised comparison
    try:
        child_lower = Path(str(child).lower())
        parent_lower = Path(str(parent).lower())
        child_lower.relative_to(parent_lower)
        return True
    except ValueError:
        return False
