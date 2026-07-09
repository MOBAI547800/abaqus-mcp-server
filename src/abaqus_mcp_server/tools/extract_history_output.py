"""Extract history output from an Abaqus ODB file and save as CSV."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from abaqus_mcp_server.abaqus_cli import AbaqusCLI, AbaqusCLIError
from abaqus_mcp_server.app import mcp
from abaqus_mcp_server.config import AbaqusServerConfig
from abaqus_mcp_server.odb_script_templates import make_history_output_script
from abaqus_mcp_server.security import validate_path

logger = logging.getLogger(__name__)


@mcp.tool(
    name="extract_history_output",
    description="Extract history output (time-series data) from an ODB file. "
    "Returns energy, reaction force, displacement history, or contact force "
    "as time-value pairs. Saves as CSV. Use for XY plotting.",
)
async def extract_history_output(
    odb_path: str,
    step: str,
    variable: str,
    region_keyword: str = "Assembly",
    output_csv: str | None = None,
) -> str:
    """Extract history output from an ODB file.

    Args:
        odb_path: Path to the .odb file.
        step: Step name.
        variable: History variable (ALLIE, ALLSE, ALLKE, ALLWK, RF1, U1, etc.).
        region_keyword: History region (usually "Assembly").
        output_csv: Optional path to save CSV results.
    """
    cfg = AbaqusServerConfig()
    ws = cfg.resolve_workspace()

    resolved = validate_path(odb_path, workspace=ws, must_exist=True)

    if resolved.suffix.lower() not in (".odb",):
        return f"Error: File must be a .odb file"

    script_code = make_history_output_script(
        resolved, step=step, variable=variable,
        region_keyword=region_keyword,
    )

    script_path = resolved.parent / f"_extract_history_{resolved.stem}.py"
    script_path.write_text(script_code, encoding="utf-8")

    cli = AbaqusCLI(cfg)

    try:
        result = await cli.run_python_script(script_path, cwd=resolved.parent, timeout=120)
    except AbaqusCLIError as exc:
        _cleanup(script_path)
        return f"Error extracting history output: {exc}"
    finally:
        _cleanup(script_path)

    if result.returncode != 0:
        return f"History output extraction failed (exit code {result.returncode}).\n\n{result.stderr[:cfg.max_output_chars]}"

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
    num_points = data.get("num_points", len(rows))

    if not rows:
        return "No data extracted."

    # Stats
    values = [r[1] for r in rows if len(r) >= 2]
    stats = ""
    if values:
        stats = (
            f"Min: {min(values):.6g}  "
            f"Max: {max(values):.6g}  "
            f"Final: {values[-1]:.6g}"
        )

    # Write CSV
    csv_msg = ""
    if output_csv:
        csv_path = validate_path(output_csv, workspace=ws)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w") as f:
            f.write("time,value\n")
            for r in rows:
                f.write(f"{r[0]},{r[1]}\n")
        csv_msg = f"\nCSV saved to: {csv_path}"

    return (
        f"=== History Output ===\n"
        f"ODB: {resolved.name}\n"
        f"Step: {step}\n"
        f"Variable: {variable}  Region: {region_keyword}\n"
        f"Data points: {num_points}\n"
        + (f"{stats}\n" if stats else "")
        + csv_msg
    )


def _cleanup(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
