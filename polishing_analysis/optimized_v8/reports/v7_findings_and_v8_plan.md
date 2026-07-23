# V7 Audit Findings & V8 Execution Plan
## Gate V8-0 — Generated 2026-07-23

---

## 1. V7 Asset Inventory

### 1.1 Configuration (config/)
| File | Status |
|---|---|
| model_parameters_v7.yaml | Valid — contains AISI304, belt params, DOE center, mesh sensitivity |
| material_aisi304_v7.yaml | Valid — AISI 304 material card |
| belt_model_v7.yaml | Valid — S4R specification, lineage enforcement rules |
| assembly_reference_v7.yaml | **CRITICAL ISSUE**: Workpiece axis = Global Z, belt nodes in Z-Y plane. Belt length direction = Z, workpiece axis = Z. Both parallel! |
| contact_search_v7.yaml | Valid — closure scan protocol, monotonicity checks |
| contact_force_targets_v7.yaml | Valid — 30N rough, 20N fine, UNCALIBRATED_ENGINEERING_BASELINE |
| contact_validation_limits_v7.yaml | Valid |
| thermal_parameters_v7.yaml | Valid |
| wear_parameters_v7.yaml | Valid |
| solver_budget_v7.yaml | Valid |
| optimization_constraints_v7.yaml | Valid |

### 1.2 Scripts (scripts/)
| File | Status |
|---|---|
| audit_v6_and_initialize_v7.py | Executed — V7-0 PASS |
| build_supported_s4r_belt.py | Executed — V7-1 pretension models |
| build_centerpoint_contact_v7.py | Executed — V7-2 contact models |
| scan_contact_onset.py | Executed — closure scan manifest |

### 1.3 Input Files (inps/)
| Pattern | Count | Status |
|---|---|---|
| belt_v7_pretension_{rough,fine}.inp | 2 | Built, submitted |
| contact_v7_{rough,fine}_center_s4r.inp | 2 | Built, submitted |
| contact_v7_{rough,fine}_scan_cl{0.1..3.5}.inp | 16 pairs = 32 | Built, partially submitted |

### 1.4 ODB Files (odb/)
**No ODB files found in V7 odb/ directory.** All ODBs are in the workspace or were not generated. The contact_centerpoint_v7.json shows zero CPRESS across all steps — contact was NOT established in the center model at 0.1mm closure.

### 1.5 Results (results/)
| File | Key Data |
|---|---|
| belt_pretension_v7.json | Rough: 90.23N, Fine: 60.18N — pretension SUCCESS |
| belt_lineage_manifest.json | S4R element type consistent between pretension and contact |
| contact_scan_manifest.json | 8 rough + 8 fine closure scans configured (0.1–3.5 mm) |
| contact_centerpoint_v7.json | **ALL CPRESS = 0, ALL CSTATUS = OPEN** — Contact NOT established at 0.1mm |
| belt_pretension_models_v7.json | Model metadata |
| v6_status_reclassification.json | V6→V7 migration record |

### 1.6 Sentinels
| File | Status |
|---|---|
| gate_v7_0.json | PASS — V7 initialized |
| gate_v7_1.json | PASS — Belt lineage verified, pretension calibrated, contact at cl=1.5mm |
| gate_v7_status.json | Shows V7-2 through V7-8 as NOT_STARTED |

---

## 2. V7 Reclassification (per Prompt §3.2)

```json
{
  "V7-0": {"v7_status": "PASS", "v8_status": "PASS_INHERITED"},
  "V7-1": {"v7_status": "PASS", "v8_status": "PASS_BELT_LINEAGE_AND_PRETENSION"},
  "rough_cl1.5": {"v7_status": "COMPLETED", "v8_status": "DIAGNOSTIC_DIRECT_BELTMID_CLOSURE"},
  "RawMax_CPRESS_448.6_MPa": {"v7_status": "EXTRACTED", "v8_status": "NOT_AREA_WEIGHTED_NOT_VALIDATED"},
  "349_closed_faces": {"v7_status": "EXTRACTED", "v8_status": "CONTACT_ESTABLISHED_DIAGNOSTIC"},
  "BELTMID_uniform_Z_displacement": {"v7_status": "CURRENT_ACTUATION", "v8_status": "DEPRECATED_CONTACT_ACTUATION"},
  "belt_length_parallel_workpiece_axis": {"v7_status": "CURRENT_COORDINATE", "v8_status": "REQUIRES_COORDINATE_AUDIT"},
  "dual_end_Encastre": {"v7_status": "CURRENT_BC", "v8_status": "ENGINEERING_BASELINE_REQUIRES_SENSITIVITY"},
  "V7-2": {"v7_status": "IN_PROGRESS", "v8_status": "REOPENED_ACTUATION_AND_COORDINATE_MODEL"},
  "V7-3_to_V7-8": {"v7_status": "NOT_STARTED", "v8_status": "NOT_STARTED"},
  "cl2.0_to_3.5_scans": {"v7_status": "NOT_SUBMITTED", "v8_status": "STOPPED_DEPRECATED_CLOSURE"}
}
```

---

## 3. Critical Findings

### 3.1 Coordinate System Issue (BLOCKING for V7 contact workflow)
**Finding**: In V7, the belt length direction AND the workpiece axis are BOTH along the Z/global-X direction:
- Belt: flat sheet in X-Y plane, length along X (or in the other model: Z-Y plane, length along Z)
- Workpiece: cylinder axis along X (or Z)

The prompt §8 requires: `workpiece_axis · belt_width_direction ≈ 1` and `workpiece_axis · belt_travel_direction ≈ 0`. In V7, the belt width is Y and workpiece axis is X — these are perpendicular, meaning the belt runs parallel to the workpiece axis. This creates a non-physical line contact instead of a proper cylindrical-conformal contact.

**Resolution**: V8 must rebuild with workpiece axis along X, belt width along X (parallel to workpiece), belt travel in YZ plane.

### 3.2 BELTMID Closure Actuation (BLOCKING for V7 as formal model)
**Finding**: V7 contact is driven by uniform Z-displacement of the entire workpiece toward the belt. The Engage step pushes ALL workpiece nodes in -Z. This is equivalent to BELTMID uniform closure — a DEPRECATED actuation method.

**Resolution**: V8 must use frame rotation about the big pulley center to establish contact, with small pulley, belt support, and belt path following the frame motion.

### 3.3 No Contact at 0.1mm Closure
**Finding**: The centerpoint contact model (`contact_v7_*_center_s4r`) shows ZERO CPRESS and ALL CSTATUS=OPEN across all steps. The 0.1mm engage displacement was insufficient to close the gap.

### 3.4 V7 Contact at cl=1.5mm is Diagnostic Only
**Finding**: Gate V7-1 reports CPRESS Max=448.6 MPa with 349 closed faces at closure=1.5mm. This is raw node-based CPRESS, not area-weighted. The closure mechanism is deprecated. This result is DIAGNOSTIC only.

---

## 4. Assets Migrated from V7 to V8

1. ✅ **AISI 304 material card** — elastic, plastic curve, density, thermal properties
2. ✅ **DOE design** — 17-run Box-Behnken, 13 unique combinations
3. ✅ **General Contact protocol** — All Exterior, Hard Contact, no Contact Pairs
4. ✅ **Solver budget framework** — stabilization, increment counts, NLGEOM
5. ✅ **S4R belt element type** — validated for shell-based belt modeling
6. ✅ **Pretension calibration method** — displacement-controlled stretch with reaction force measurement
7. ✅ **Force target engineering baselines** — 30N rough, 20N fine
8. ✅ **Contact physics validation limits** — monotonicity, force balance, PEEQ limits
9. ✅ **Belt lineage enforcement rules** — same mesh for pretension and contact
10. ✅ **Experimental run sheet** — 17 DOE runs from CSV

---

## 5. V8 Execution Status

| Gate | Status | Description |
|---|---|---|
| V8-0 | IN_PROGRESS | V7 audit & V8 initialization |
| V8-1 | NOT_STARTED | Coordinate and assembly validation |
| V8-2 | NOT_STARTED | Two-pulley pretension & frame drive test |
| V8-3 | NOT_STARTED | Center-point contact & mesh sensitivity |
| V8-4 | NOT_STARTED | Six contact scenarios |
| V8-5 | NOT_STARTED | Moving heat source |
| V8-6 | NOT_STARTED | Sequential thermal-mechanical residual stress |
| V8-7 | NOT_STARTED | Archard wear integration |
| V8-8 | NOT_STARTED | DOE regression & optimization |

---

## 6. V7 Jobs Stopped

The following V7 closure scan jobs will NOT be submitted:
- `contact_v7_rough_scan_cl1p0`, `cl2p0`, `cl2p5`, `cl3p0`, `cl3p5` (if not yet run)
- `contact_v7_fine_scan_cl1p0`, `cl2p0`, `cl2p5`, `cl3p0`, `cl3p5` (if not yet run)
- All closure >1.5mm scans are DECOMMISSIONED

Reason: DEPRECATED_CONTACT_ACTUATION — BELTMID uniform closure is not a valid physical actuation mechanism.
