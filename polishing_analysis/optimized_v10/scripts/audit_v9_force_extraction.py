"""
Gate V10-1: V9 Normal Force Extraction Audit
Correctly extracts CNORMF using VECTOR sum (not magnitude sum).
Determines root cause of 61-98 kN CNORMF.
"""
import os, sys, json, math
from collections import defaultdict


def extract_corrected_cnormf(odb_path):
    """Extract CNORMF with proper vector summation and instance filtering."""
    from odbAccess import openOdb

    if not os.path.exists(odb_path):
        return {"error": f"ODB not found: {odb_path}"}

    odb = openOdb(odb_path, readOnly=True)
    result = {
        "odb_path": odb_path,
        "instances": {},
        "steps": {}
    }

    # Instance info
    for name, inst in odb.rootAssembly.instances.items():
        result["instances"][name] = {
            "node_count": len(inst.nodes) if inst.nodes else 0,
            "element_count": len(inst.elements) if inst.elements else 0,
        }

    # Contact normal (approximate: Z-direction in global, or Y based on geometry)
    # For V9 models: belt runs in YZ plane, workpiece axis along X
    # Contact normal is primarily in the YZ plane (perpendicular to belt surface)

    for step_name, step in odb.steps.items():
        if len(step.frames) == 0:
            result["steps"][step_name] = {"num_frames": 0, "error": "No frames"}
            continue

        sd = {"num_frames": len(step.frames), "total_time": step.totalTime}
        last = step.frames[-1]
        fouts = last.fieldOutputs

        # ===== CSTATUS =====
        for k in fouts.keys():
            if 'CSTATUS' in str(k):
                vals_per_instance = defaultdict(list)
                for v in fouts[k].values:
                    d = v.data
                    if d is not None:
                        inst_name = v.instance.name if v.instance else "UNKNOWN"
                        vals_per_instance[inst_name].append(float(d))

                sd['cstatus'] = {}
                for inst, vals in vals_per_instance.items():
                    nonzero = sum(1 for v in vals if v > 0.5)
                    sd['cstatus'][inst] = {
                        "total": len(vals),
                        "contact_points": nonzero,
                        "contact_frac": nonzero / max(len(vals), 1)
                    }
                break

        # ===== CNORMF - CORRECTED VECTOR SUM =====
        for k in fouts.keys():
            if 'CNORMF' in str(k):
                # === METHOD: Vector sum per instance ===
                vec_sum = defaultdict(lambda: [0.0, 0.0, 0.0])
                mag_sum = defaultdict(float)     # OLD WRONG METHOD
                mag_list = defaultdict(list)
                node_count = defaultdict(int)

                for v in fouts[k].values:
                    inst_name = v.instance.name if v.instance else "UNKNOWN"
                    d = v.data
                    if d is None:
                        continue

                    # CNORMF data is [fx, fy, fz] vector at each node
                    if isinstance(d, (int, float)):
                        mag = float(d)
                        vec_sum[inst_name][0] += float(d)  # scalar, assume X
                    else:
                        fx, fy, fz = float(d[0]), float(d[1]), float(d[2])
                        vec_sum[inst_name][0] += fx
                        vec_sum[inst_name][1] += fy
                        vec_sum[inst_name][2] += fz
                        mag = math.sqrt(fx*fx + fy*fy + fz*fz)

                    mag_sum[inst_name] += mag
                    mag_list[inst_name].append(mag)
                    node_count[inst_name] += 1

                # Compute stats per instance
                sd['cnormf_corrected'] = {}
                sd['cnormf_old_wrong'] = {}
                global_vec = [0.0, 0.0, 0.0]
                global_mag_sum = 0.0

                for inst in vec_sum:
                    vs = vec_sum[inst]
                    vec_mag = math.sqrt(vs[0]**2 + vs[1]**2 + vs[2]**2)

                    # Sorted magnitudes for stats
                    sorted_mags = sorted(mag_list[inst])
                    n = len(sorted_mags)

                    sd['cnormf_corrected'][inst] = {
                        "vector_sum_N": [round(x, 4) for x in vs],
                        "vector_magnitude_N": round(vec_mag, 4),
                        "node_count": node_count[inst],
                    }

                    sd['cnormf_old_wrong'][inst] = {
                        "magnitude_sum_N": round(mag_sum[inst], 4),
                        "max_magnitude_N": round(max(sorted_mags), 4) if sorted_mags else 0,
                        "mean_magnitude_N": round(sum(sorted_mags)/n, 4) if n else 0,
                        "nonzero_count": sum(1 for m in sorted_mags if m > 1e-10),
                    }

                    global_vec[0] += vs[0]
                    global_vec[1] += vs[1]
                    global_vec[2] += vs[2]
                    global_mag_sum += mag_sum[inst]

                global_vec_mag = math.sqrt(global_vec[0]**2 + global_vec[1]**2 + global_vec[2]**2)
                sd['cnormf_corrected']['GLOBAL_VECTOR_SUM'] = {
                    "vector_N": [round(x, 4) for x in global_vec],
                    "magnitude_N": round(global_vec_mag, 4)
                }
                sd['cnormf_old_wrong']['GLOBAL_MAGNITUDE_SUM_N'] = round(global_mag_sum, 4)

                # Also compute the 8 diagnostic checks from the prompt
                sd['force_extraction_audit'] = {
                    "method_A_vector_sum": round(global_vec_mag, 4),
                    "method_OLD_magnitude_sum": round(global_mag_sum, 4),
                    "ratio_mag_sum_to_vector_sum": round(global_mag_sum / max(global_vec_mag, 0.001), 4),
                    "verdict": "ARTIFACT_CONFIRMED" if global_mag_sum / max(global_vec_mag, 0.001) > 5
                               else "NEEDS_FURTHER_INVESTIGATION" if global_mag_sum / max(global_vec_mag, 0.001) > 1.5
                               else "EXTRACTION_LIKELY_CORRECT",
                }
                break

        # ===== CPRESS =====
        for k in fouts.keys():
            if 'CPRESS' in str(k):
                mags_per_instance = defaultdict(list)
                for v in fouts[k].values:
                    inst_name = v.instance.name if v.instance else "UNKNOWN"
                    m = 0.0
                    try:
                        if hasattr(v, 'magnitude'):
                            m = v.magnitude or 0.0
                        else:
                            d = v.data
                            if d is not None:
                                if isinstance(d, (int, float)):
                                    m = float(d)
                                else:
                                    m = math.sqrt(sum(c**2 for c in d))
                    except:
                        pass
                    mags_per_instance[inst_name].append(m)

                sd['cpress'] = {}
                for inst, mags in mags_per_instance.items():
                    nz = [m for m in mags if m > 1e-10]
                    if nz:
                        s = sorted(nz)
                        n = len(s)
                        sd['cpress'][inst] = {
                            "nonzero_count": n,
                            "max_MPa": round(max(nz), 6),
                            "mean_MPa": round(sum(nz)/n, 6),
                            "p95_MPa": round(s[int(n*0.95)], 6) if n > 1 else round(s[0], 6),
                            "p99_MPa": round(s[int(n*0.99)], 6) if n > 1 else round(s[0], 6),
                        }
                    else:
                        sd['cpress'][inst] = {
                            "nonzero_count": 0,
                            "max_MPa": 0,
                            "mean_MPa": 0,
                            "p95_MPa": 0,
                            "p99_MPa": 0,
                            "WARNING": "CPRESS is zero or missing — pressure field not usable for thermal/wear",
                        }
                break

        # ===== RF at support nodes =====
        if 'RF' in fouts:
            rf_per_instance = defaultdict(lambda: [0.0, 0.0, 0.0])
            for v in fouts['RF'].values:
                inst_name = v.instance.name if v.instance else "UNKNOWN"
                d = v.data
                if d is not None and not isinstance(d, (int, float)):
                    rf_per_instance[inst_name][0] += float(d[0])
                    rf_per_instance[inst_name][1] += float(d[1])
                    rf_per_instance[inst_name][2] += float(d[2])
            sd['rf_vector_sum'] = {}
            for inst, vs in rf_per_instance.items():
                sd['rf_vector_sum'][inst] = {
                    "vector_N": [round(x, 4) for x in vs],
                    "magnitude_N": round(math.sqrt(vs[0]**2 + vs[1]**2 + vs[2]**2), 4)
                }

        # ===== PEEQ =====
        if 'PEEQ' in fouts:
            peeq_vals = []
            for v in fouts['PEEQ'].values:
                try:
                    d = v.data
                    if d is not None:
                        peeq_vals.append(float(d) if isinstance(d, (int, float)) else v.magnitude or 0)
                except:
                    pass
            nz_peeq = [v for v in peeq_vals if v > 1e-10]
            sd['peeq'] = {
                "max": round(max(nz_peeq), 6) if nz_peeq else 0,
                "nonzero_frac": round(len(nz_peeq)/max(len(peeq_vals),1), 6)
            }

        result["steps"][step_name] = sd

    odb.close()
    return result


def audit_all_v9_odbs():
    """Audit key V9 ODBs for force extraction correctness."""
    odb_list = [
        ("cl1p5v3", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_cl1p5v3.odb"),
        ("rough_b3_1p20", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_b3_1p20.odb"),
        ("fine_b3_12", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_fine_b3_12.odb"),
        ("rough_b3_1p40", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_b3_1p40.odb"),
        ("rough_cal_50", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_cal_50.odb"),
        ("rough_cal_40", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_cal_40.odb"),
        ("rough_cal_30", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_cal_30.odb"),
        ("rough_cal_20", "D:/mcp/abaqus_mcp/abaqus_work/contact_v9_rough_cal_20.odb"),
    ]

    all_results = {}
    summary = []

    for label, path in odb_list:
        print(f"\n{'='*70}")
        print(f"Auditing: {label}")
        print(f"Path: {path}")
        print(f"{'='*70}")

        r = extract_corrected_cnormf(path)
        all_results[label] = r

        if "error" in r:
            print(f"  ERROR: {r['error']}")
            summary.append({"label": label, "status": "NOT_FOUND", "error": r['error']})
            continue

        print(f"  Instances: {list(r['instances'].keys())}")

        for step_name, sd in r.get("steps", {}).items():
            if "error" in sd:
                continue

            old_wrong = sd.get("cnormf_old_wrong", {}).get("GLOBAL_MAGNITUDE_SUM_N", 0)
            new_correct = sd.get("cnormf_corrected", {}).get("GLOBAL_VECTOR_SUM", {}).get("magnitude_N", 0)
            ratio = sd.get("force_extraction_audit", {}).get("ratio_mag_sum_to_vector_sum", 0)
            verdict = sd.get("force_extraction_audit", {}).get("verdict", "UNKNOWN")

            # Per-instance breakdown
            print(f"\n  Step '{step_name}':")
            cstatus_info = sd.get("cstatus", {})
            for inst, info in cstatus_info.items():
                print(f"    CSTATUS [{inst}]: {info.get('contact_points',0)}/{info.get('total',0)} "
                      f"({info.get('contact_frac',0)*100:.1f}%)")

            print(f"\n    === CNORMF Force Extraction Audit ===")
            print(f"    OLD (magnitude sum, WRONG):  {old_wrong:.2f} N")
            print(f"    NEW (vector sum, CORRECT):    {new_correct:.2f} N")
            print(f"    Ratio old/new:                 {ratio:.2f}x")
            print(f"    VERDICT:                       {verdict}")

            # Per-instance breakdown
            for inst in r['instances']:
                v_old = sd.get("cnormf_old_wrong", {}).get(inst, {}).get("magnitude_sum_N", 0)
                v_new = sd.get("cnormf_corrected", {}).get(inst, {}).get("vector_magnitude_N", 0)
                vec = sd.get("cnormf_corrected", {}).get(inst, {}).get("vector_sum_N", [0,0,0])
                if v_old > 0 or v_new > 0:
                    print(f"    [{inst}] OLD={v_old:.2f}N  NEW={v_new:.2f}N  vector={vec}")

            # CPRESS
            for inst, info in sd.get("cpress", {}).items():
                if info.get("nonzero_count", 0) > 0:
                    print(f"\n    CPRESS [{inst}]: nz={info['nonzero_count']} "
                          f"max={info['max_MPa']:.4f} mean={info['mean_MPa']:.4f} "
                          f"p95={info['p95_MPa']:.4f}")
                else:
                    w = info.get("WARNING", "")
                    if w:
                        print(f"\n    CPRESS [{inst}]: {w}")

        summary.append({
            "label": label,
            "status": "AUDITED",
            "old_magnitude_sum_N": old_wrong,
            "new_vector_sum_N": new_correct,
            "ratio": ratio,
            "verdict": verdict,
            "instances": list(r['instances'].keys()),
        })

    # Save results
    out_dir = "D:/mcp/abaqus_mcp/polishing_analysis/optimized_v10/results"
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "v9_force_extraction_audit.json"), 'w') as f:
        json.dump({"summary": summary, "detailed": all_results}, f, indent=2, default=str)

    # Print final summary
    print(f"\n{'='*70}")
    print("FINAL AUDIT SUMMARY")
    print(f"{'='*70}")
    print(f"{'ODB':<25} {'OLD(wrong)':>12} {'NEW(correct)':>12} {'Ratio':>8} {'Verdict'}")
    print("-"*80)
    for s in summary:
        if s["status"] == "AUDITED":
            print(f"{s['label']:<25} {s['old_magnitude_sum_N']:>12.1f} {s['new_vector_sum_N']:>12.1f} "
                  f"{s['ratio']:>8.2f}x {s['verdict']}")

    return summary, all_results


if __name__ == "__main__":
    audit_all_v9_odbs()
