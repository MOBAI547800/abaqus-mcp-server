"""
Gate V9-0: Extract V8 center ODB diagnostics.
Runs via: abaqus python extract_v8_center_odb_diagnostic.py
"""
from odbAccess import openOdb
import json
import sys
import os

def extract_odb_summary(odb_path):
    """Extract complete summary from an ODB file."""
    result = {"odb_path": odb_path, "status": "unknown", "steps": []}

    if not os.path.exists(odb_path):
        result["status"] = "ODB_MISSING"
        return result

    try:
        odb = openOdb(odb_path, readOnly=True)
        result["status"] = "OPENED"

        # Root assembly info
        root = odb.rootAssembly
        result["instances"] = []
        for name, inst in root.instances.items():
            try:
                inst_info = {
                    "name": name,
                    "num_nodes": len(inst.nodes) if inst.nodes else 0,
                    "num_elements": len(inst.elements) if inst.elements else 0,
                }
                result["instances"].append(inst_info)
            except:
                result["instances"].append({"name": name, "error": "Could not read"})

        # Steps
        for step_name, step in odb.steps.items():
            step_info = {
                "name": step_name,
                "procedure": step.procedure if hasattr(step, 'procedure') else "unknown",
                "num_frames": len(step.frames),
                "total_time": step.totalTime if hasattr(step, 'totalTime') else None,
                "frames": []
            }

            # Field outputs available
            if step.frames and len(step.frames) > 0:
                last_frame = step.frames[-1]
                fouts = last_frame.fieldOutputs
                step_info["field_outputs_available"] = list(fouts.keys()) if fouts else []

                # For each frame, extract key data
                for i, frame in enumerate(step.frames):
                    frame_data = {
                        "frame_index": i,
                        "frame_value": frame.frameValue,
                        "time": frame.incrementTime if hasattr(frame, 'incrementTime') else None,
                    }

                    fouts = frame.fieldOutputs
                    if fouts:
                        frame_fields = {}
                        for key in ['CPRESS', 'CSTATUS', 'COPEN', 'CSHEAR', 'CSLIP',
                                     'U', 'RF', 'S', 'PEEQ', 'CNORMF']:
                            if key in fouts:
                                fo = fouts[key]
                                field_info = {
                                    "description": fo.description if hasattr(fo, 'description') else "",
                                    "type": str(fo.type) if hasattr(fo, 'type') else "",
                                    "locations": [str(loc) for loc in fo.locations] if hasattr(fo, 'locations') else [],
                                }
                                # Try to extract basic stats
                                try:
                                    vals = [v.data for v in fo.values]
                                    if vals:
                                        if hasattr(vals[0], 'magnitude'):
                                            mags = [v.magnitude for v in fo.values]
                                            field_info["max"] = max(mags)
                                            field_info["min"] = min(mags)
                                            field_info["mean"] = sum(mags)/len(mags)
                                            nonzero = sum(1 for v in mags if v > 1e-10)
                                            field_info["nonzero_count"] = nonzero
                                        elif isinstance(vals[0], (int, float)):
                                            field_info["max"] = max(vals)
                                            field_info["min"] = min(vals)
                                            field_info["mean"] = sum(vals)/len(vals)
                                            nonzero = sum(1 for v in vals if abs(v) > 1e-10)
                                            field_info["nonzero_count"] = nonzero
                                except Exception as e:
                                    field_info["stats_error"] = str(e)

                                frame_fields[key] = field_info
                        frame_data["fields"] = frame_fields

                    step_info["frames"].append(frame_data)

            result["steps"].append(step_info)

        odb.close()
        result["status"] = "EXTRACTED"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result

def main():
    odb_paths = [
        "D:/mcp/abaqus_mcp/abaqus_work/jobs/contact_v8_rough_center.odb",
        "D:/mcp/abaqus_mcp/abaqus_work/jobs/contact_v8_fine_center.odb",
        "D:/mcp/abaqus_mcp/abaqus_work/jobs/contact_v8_rough_center_frame.odb",
    ]

    out_dir = "D:/mcp/abaqus_mcp/polishing_analysis/optimized_v9/results"
    os.makedirs(out_dir, exist_ok=True)

    all_results = {}
    for path in odb_paths:
        name = os.path.basename(path).replace(".odb", "")
        print(f"Extracting: {name} ...")
        data = extract_odb_summary(path)
        all_results[name] = data

        # Write individual JSON
        out_path = os.path.join(out_dir, f"v8_diagnostic_{name}.json")
        with open(out_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  -> {out_path}")
        print(f"  Status: {data['status']}")
        for step in data.get('steps', []):
            print(f"  Step '{step['name']}': {step['num_frames']} frames, fields: {step.get('field_outputs_available', [])}")

    # Write combined results
    combined_path = os.path.join(out_dir, "v8_center_odb_diagnostic_all.json")
    with open(combined_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nCombined diagnostic: {combined_path}")

if __name__ == "__main__":
    main()
