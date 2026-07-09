"""Extract summary information from an Abaqus ODB file."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI, AbaqusCLIError
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="extract_odb_summary",
    description="Extract summary metadata from an Abaqus ODB file. "
    "Returns steps, frames, instances, field outputs, and history regions. "
    "This works by generating a temporary Python script that runs under "
    "Abaqus Python with odbAccess.",
)
async def extract_odb_summary(odb_path: str) -> str:
    """Extract metadata from an ODB file via Abaqus Python."""
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    resolved = validate_path(odb_path, workspace=ws, must_exist=True)

    if resolved.suffix.lower() not in (".odb",):
        return f"Error: File must be a .odb file, got: {resolved.suffix}"

    if not resolved.exists():
        return f"Error: ODB file not found: {resolved}"

    # Generate the extraction script
    script_code = _make_summary_script(resolved)

    # Write temp script in the same directory as the ODB
    script_path = resolved.parent / f"_odb_summary_{resolved.stem}.py"
    script_path.write_text(script_code, encoding="utf-8")

    cli = AbaqusCLI(cfg)

    try:
        result = await cli.run_python_script(
            script_path,
            cwd=resolved.parent,
            timeout=120,  # ODB operations should be fast
        )
    except AbaqusCLIError as exc:
        _cleanup(script_path)
        return f"Error extracting ODB summary: {exc}"
    finally:
        _cleanup(script_path)

    if result.returncode != 0:
        return (
            f"ODB extraction failed (exit code {result.returncode}).\n\n"
            f"--- stderr ---\n{result.stderr[:cfg.max_output_chars]}\n\n"
            f"--- stdout ---\n{result.stdout[:cfg.max_output_chars]}"
        )

    # Parse JSON from stdout (find the JSON block between markers)
    stdout = result.stdout
    try:
        # Find JSON between the markers we emit
        start = stdout.find("===ODB_JSON_START===")
        end = stdout.find("===ODB_JSON_END===")
        if start >= 0 and end > start:
            json_str = stdout[start + len("===ODB_JSON_START==="):end].strip()
        else:
            # Fallback: try parsing the whole stdout as JSON
            json_str = stdout.strip()

        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return (
            f"Failed to parse ODB summary JSON: {exc}\n\n"
            f"Raw stdout:\n{stdout[:cfg.max_output_chars]}"
        )

    if "error" in data:
        return f"ODB extraction error: {data['error']}"

    # Format the output
    lines = [
        f"=== ODB Summary: {resolved.name} ===",
        f"Path: {resolved}",
        "",
        f"Steps ({len(data.get('steps', []))}):",
    ]
    for step in data.get("steps", []):
        lines.append(f"  - {step}")
    lines.append("")

    if "instances" in data:
        lines.append(f"Instances ({len(data['instances'])}):")
        for inst in data["instances"]:
            lines.append(f"  - {inst}")
        lines.append("")

    if "field_outputs" in data:
        lines.append(f"Field outputs ({len(data['field_outputs'])}):")
        for fo in data["field_outputs"]:
            lines.append(f"  - {fo}")
        lines.append("")

    if "history_regions" in data:
        lines.append(f"History regions ({len(data['history_regions'])}):")
        for hr in data["history_regions"]:
            lines.append(f"  - {hr}")
        lines.append("")

    frames_info = data.get("frames", {})
    if frames_info:
        lines.append("Frames per step:")
        for step_name, count in frames_info.items():
            lines.append(f"  {step_name}: {count} frame(s)")

    return "\n".join(lines)


def _make_summary_script(odb_path: Path) -> str:
    """Generate an Abaqus Python script that extracts ODB metadata as JSON."""
    # Use forward slashes to avoid backslash escape issues
    odb_path_str = odb_path.as_posix()

    return f'''"""Auto-generated ODB summary extraction script."""
from odbAccess import openOdb
from abaqusConstants import *
import json
import sys

odb_path = r"{odb_path_str}"

try:
    odb = openOdb(odb_path, readOnly=True)

    # Steps
    steps = list(odb.steps.keys())

    # Frames per step
    frames = {{}}
    for step_name, step in odb.steps.items():
        frames[step_name] = len(step.frames)

    # Instances
    instances = list(odb.rootAssembly.instances.keys())

    # Field outputs (from last frame of first step)
    field_outputs = []
    if steps:
        last_frame = odb.steps[steps[-1]].frames[-1]
        field_outputs = list(last_frame.fieldOutputs.keys())

    # History regions
    history_regions = []
    if steps:
        hist_region = odb.steps[steps[-1]].historyRegions
        history_regions = list(hist_region.keys())

    data = {{
        "steps": steps,
        "frames": frames,
        "instances": instances,
        "field_outputs": field_outputs,
        "history_regions": history_regions,
    }}

    print("===ODB_JSON_START===")
    print(json.dumps(data, indent=2, default=str))
    print("===ODB_JSON_END===")

    odb.close()

except Exception as exc:
    print("===ODB_JSON_START===")
    print(json.dumps({{"error": str(exc)}}))
    print("===ODB_JSON_END===")
    sys.exit(1)
'''


def _cleanup(path: Path) -> None:
    """Remove a temporary script file, ignoring errors."""
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
