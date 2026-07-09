"""Extract field output from an Abaqus ODB file and save as CSV."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI, AbaqusCLIError
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.odb_script_templates import make_field_output_script
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="extract_field_output",
    description="Extract field output (stress, displacement, strain, etc.) from an ODB file. "
    "Saves results as CSV and returns summary statistics. "
    "Specify step, frame (-1 = last), variable (e.g., S, U, E), and optional component (e.g., Mises, U1).",
)
async def extract_field_output(
    odb_path: str,
    step: str,
    frame: int = -1,
    variable: str = "S",
    component: str | None = None,
    instance: str | None = None,
    output_csv: str | None = None,
) -> str:
    """Extract field output from an ODB file.

    Args:
        odb_path: Path to the .odb file.
        step: Step name.
        frame: Frame index (-1 = last frame).
        variable: Field output variable (S, U, E, PEEQ, RF, etc.).
        component: Optional component (Mises, U1, S11, etc.).
        instance: Optional instance name to filter.
        output_csv: Optional path to save CSV results.
    """
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    resolved = validate_path(odb_path, workspace=ws, must_exist=True)

    if resolved.suffix.lower() not in (".odb",):
        return f"Error: File must be a .odb file"

    # Generate extraction script
    script_code = make_field_output_script(
        resolved, step=step, frame=frame, variable=variable,
        component=component, instance=instance,
    )

    script_path = resolved.parent / f"_extract_field_{resolved.stem}.py"
    script_path.write_text(script_code, encoding="utf-8")

    cli = AbaqusCLI(cfg)

    try:
        result = await cli.run_python_script(script_path, cwd=resolved.parent, timeout=120)
    except AbaqusCLIError as exc:
        _cleanup(script_path)
        return f"Error extracting field output: {exc}"
    finally:
        _cleanup(script_path)

    if result.returncode != 0:
        return f"Field output extraction failed (exit code {result.returncode}).\n\n{result.stderr[:cfg.max_output_chars]}"

    try:
        start = result.stdout.find("===ODB_JSON_START===")
        end = result.stdout.find("===ODB_JSON_END===")
        if start >= 0 and end > start:
            json_str = result.stdout[start + len("===ODB_JSON_START==="):end].strip()
        else:
            json_str = result.stdout.strip()
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return f"Failed to parse extraction output.\n\n{result.stdout[:cfg.max_output_chars]}"

    if "error" in data:
        return f"Extraction error: {data['error']}"

    rows = data.get("rows", [])
    if not rows:
        return "No data extracted. Check step, frame, and variable names."

    # Compute stats
    values = [r[1] if isinstance(r[1], (int, float)) else r[1][0] if hasattr(r[1], '__iter__') else 0 for r in rows if len(r) >= 2]
    # Handle nested tuples from Abaqus (e.g., stress tensor components)
    flat_vals = []
    for v in values:
        if hasattr(v, '__iter__') and not isinstance(v, str):
            flat_vals.append(v[0] if hasattr(v, '__getitem__') else v)
        else:
            flat_vals.append(v)

    stats = {
        "variable": variable,
        "component": component or "all",
        "num_points": len(rows),
    }
    if flat_vals:
        stats["min"] = min(flat_vals)
        stats["max"] = max(flat_vals)
        stats["avg"] = sum(flat_vals) / len(flat_vals)

    # Write CSV if requested
    csv_msg = ""
    if output_csv:
        csv_path = validate_path(output_csv, workspace=ws)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w") as f:
            f.write("label,value\n")
            for r in rows:
                f.write(f"{r[0]},{r[1]}\n")
        csv_msg = f"\nCSV saved to: {csv_path}"

    return (
        f"=== Field Output ===\n"
        f"ODB: {resolved.name}\n"
        f"Step: {step}  Frame: {frame}\n"
        f"Variable: {variable}  Component: {component or 'all'}\n"
        f"Data points: {stats['num_points']}\n"
        + (f"Min: {stats.get('min', 'N/A'):.6g}  "
           f"Max: {stats.get('max', 'N/A'):.6g}  "
           f"Avg: {stats.get('avg', 'N/A'):.6g}" if flat_vals else "")
        + csv_msg
    )


def _cleanup(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
