"""Generate temporary Python scripts for ODB data extraction.

These templates produce valid Python that runs under Abaqus's bundled
Python (``abaqus python``), which has access to ``odbAccess``.
"""

from __future__ import annotations

from pathlib import Path


def make_odb_summary_script(odb_path: str | Path) -> str:
    """Generate a script that extracts ODB metadata as JSON.

    Args:
        odb_path: Path to the ``.odb`` file (absolute recommended).

    Returns:
        A Python script string ready to be written to a ``.py`` file
        and executed via ``abaqus python``.
    """
    # Use forward slashes in the generated script to avoid escape issues
    odb_str = Path(odb_path).as_posix()

    return f'''"""Auto-generated ODB summary extraction script."""
from odbAccess import openOdb
import json
import sys

odb = openOdb(r"{odb_str}", readOnly=True)
try:
    # Steps and frame counts
    steps = list(odb.steps.keys())
    frames = {{}}
    for step_name in steps:
        frames[step_name] = len(odb.steps[step_name].frames)

    # Instances
    instances = list(odb.rootAssembly.instances.keys())

    # Field outputs from last frame of last step
    field_outputs = []
    if steps:
        last_step = odb.steps[steps[-1]]
        if last_step.frames:
            field_outputs = list(last_step.frames[-1].fieldOutputs.keys())

    # History regions
    history_regions = []
    if steps:
        history_regions = list(odb.steps[steps[-1]].historyRegions.keys())

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

finally:
    odb.close()
'''


def make_field_output_script(
    odb_path: str | Path,
    step: str,
    frame: int,
    variable: str,
    component: str | None = None,
    instance: str | None = None,
) -> str:
    """Generate a script that extracts field output as CSV.

    Args:
        odb_path: Path to the ``.odb`` file.
        step: Step name.
        frame: Frame index (negative = from end, -1 = last).
        variable: Field output variable name (e.g. ``"S"``, ``"U"``, ``"E"``).
        component: Optional component (e.g. ``"Mises"``, ``"U1"``).
        instance: Optional instance name to filter by.

    Returns:
        A Python script string.
    """
    odb_str = Path(odb_path).as_posix()

    component_check = ""
    if component:
        component_check = f'''
    if "{component}" in fo.componentLabels:
        values = fo.getSubset(componentLabel="{component}")
    else:
        values = fo'''
    else:
        component_check = "\n    values = fo"

    instance_filter = ""
    if instance:
        instance_filter = f'''
    region = odb.rootAssembly.instances["{instance}"]'''

    return f'''"""Auto-generated field output extraction script."""
from odbAccess import openOdb
import json
import sys

odb = openOdb(r"{odb_str}", readOnly=True)
try:
    step_key = "{step}"
    frame_idx = {frame}
    var_name = "{variable}"

    if step_key not in odb.steps:
        print(json.dumps({{"error": f"Step '{{step_key}}' not found"}}))
        sys.exit(1)

    the_step = odb.steps[step_key]
    the_frame = the_step.frames[frame_idx]

    if var_name not in the_frame.fieldOutputs:
        avail = list(the_frame.fieldOutputs.keys())
        print(json.dumps({{"error": f"Variable '{{var_name}}' not found. Available: {{avail}}"}}))
        sys.exit(1)

    fo = the_frame.fieldOutputs[var_name]{instance_filter}
{component_check}

    # Build CSV: node/element label, value
    rows = []
    if hasattr(values, 'values'):
        for v in values.values:
            rows.append([v.elementLabel if hasattr(v, 'elementLabel') else v.nodeLabel, v.data])
    else:
        for v in values:
            rows.append([v.elementLabel if hasattr(v, 'elementLabel') else v.nodeLabel, v.data])

    print("===ODB_JSON_START===")
    print(json.dumps({{"variable": var_name, "component": "{component or ''}", "rows": rows}}))
    print("===ODB_JSON_END===")

finally:
    odb.close()
'''


def make_history_output_script(
    odb_path: str | Path,
    step: str,
    variable: str,
    region_keyword: str = "Assembly",
) -> str:
    """Generate a script that extracts history output as CSV.

    Args:
        odb_path: Path to the ``.odb`` file.
        step: Step name.
        variable: History variable name (e.g. ``"ALLIE"``, ``"ALLSE"``).
        region_keyword: History region name (usually ``"Assembly"``).

    Returns:
        A Python script string.
    """
    odb_str = Path(odb_path).as_posix()

    return f'''"""Auto-generated history output extraction script."""
from odbAccess import openOdb
import json
import sys

odb = openOdb(r"{odb_str}", readOnly=True)
try:
    step_key = "{step}"
    var_name = "{variable}"
    region_name = "{region_keyword}"

    if step_key not in odb.steps:
        print(json.dumps({{"error": f"Step '{{step_key}}' not found"}}))
        sys.exit(1)

    the_step = odb.steps[step_key]
    hist_regions = the_step.historyRegions

    if region_name not in hist_regions:
        avail = list(hist_regions.keys())
        print(json.dumps({{"error": f"Region '{{region_name}}' not found. Available: {{avail}}"}}))
        sys.exit(1)

    region = hist_regions[region_name]
    if var_name not in region.historyOutputs:
        avail = list(region.historyOutputs.keys())
        print(json.dumps({{"error": f"Variable '{{var_name}}' not found. Available: {{avail}}"}}))
        sys.exit(1)

    ho = region.historyOutputs[var_name]
    rows = [[t, v] for t, v in zip(ho.data[0], ho.data[1])]

    print("===ODB_JSON_START===")
    print(json.dumps({{"variable": var_name, "region": region_name, "num_points": len(rows), "rows": rows}}))
    print("===ODB_JSON_END===")

finally:
    odb.close()
'''
