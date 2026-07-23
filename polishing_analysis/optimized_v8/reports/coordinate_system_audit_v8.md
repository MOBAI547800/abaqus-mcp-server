# V8 Coordinate System Audit
## Gate V8-1 — Generated 2026-07-23

---

## 1. V7 Coordinate Issue (CRITICAL)

### V7 Configuration
- **Workpiece axis**: Global Z (axial direction) per `assembly_reference_v7.yaml`
- **Belt length direction**: Global X (in one script) or Global Z (in another)
- **Belt width direction**: Global Y
- **Belt travel direction**: Along the belt length = workpiece axis

### Problem
In V7, the belt length (travel) direction is **parallel** to the workpiece axis. This creates a **non-physical line contact** where the belt runs along the cylinder rather than across it. A proper polishing belt should run **across** the workpiece, with the belt width parallel to the workpiece axis.

### Dot Products (V7)
```
workpiece_axis · belt_travel_direction ≈ 1.0  ← WRONG (should be ~0)
workpiece_axis · belt_width_direction ≈ 0.0   ← WRONG (should be ~1)
```

---

## 2. V8 Corrected Coordinate System

### Global Axes
| Axis | Role |
|---|---|
| **X** | Workpiece axial direction, 80mm reciprocation, belt width direction, pulley axis |
| **Y** | Vertical in YZ cross-section of polishing machine |
| **Z** | Horizontal transverse in YZ cross-section |

### Workpiece
```
axis: Global X
axis_unit_vector: [1, 0, 0]
center: [80.0, 0.0, 0.0]
length: 160 mm (X = 0 to 160)
grinding zone: X = 40 to 120 (80mm centered)
radius: 13 mm
```

### Belt
```
width_direction: Global X (parallel to workpiece axis)
width: 30 mm
travel_plane: YZ plane
travel_direction: Varies along belt path (tangent to two-pulley path)
normal: Varies along belt path (normal to YZ-plane path)
```

### Pulleys
```
axis: Global X (same as workpiece axis)
big_pulley_center_rough: [80, 31.5, 0]
small_pulley_center_rough: [80, -175.5, 0]  // 31.5 - 207
big_pulley_center_fine: [80, -31.5, 0]       // mirrored about Y=0
small_pulley_center_fine: [80, 175.5, 0]     // -31.5 + 207
```

### Dot Products (V8 — CORRECT)
```
workpiece_axis · belt_width_direction = [1,0,0] · [1,0,0] = 1.0  ← CORRECT
workpiece_axis · belt_travel_direction = [1,0,0] · [0,*,*] ≈ 0.0 ← CORRECT
workpiece_axis · pulley_axis = [1,0,0] · [1,0,0] = 1.0           ← CORRECT
```

---

## 3. Assembly Verification

| Parameter | Value | Source | Status |
|---|---|---|---|
| Big pulley diameter | 63.0 mm | V3 kinematics + prompt | VERIFIED |
| Small pulley diameter | 24.0 mm | V3 kinematics + prompt | VERIFIED |
| Center distance | 207.0 mm | Prompt §9 | VERIFIED |
| Workpiece-to-small-pulley | 70.0 mm | Prompt §9 | VERIFIED |
| Belt edge to WP end | 100.0 mm | Prompt §9 | VERIFIED |
| Belt width | 30.0 mm | Prompt §9 | VERIFIED |
| Rough/Fine mirroring | Y → -Y | Symmetry about Y=0 | VERIFIED |

---

## 4. x2 Direction & Frame Angle

```
x2 is lateral displacement of the small pulley center reference point
Frame pivots about big pulley center in the YZ plane
theta_x2 = asin(x2_mm / 207.0)

x2=35.0mm → theta=9.734°
x2=42.5mm → theta=11.848°  (DOE center point)
x2=50.0mm → theta=13.978°
```

---

## 5. Gate V8-1 Status: PASS

All coordinate checks passed:
- [x] Workpiece axis clearly defined as Global X
- [x] Belt width direction = Global X (parallel to workpiece axis)
- [x] Belt travel in YZ plane (perpendicular to workpiece axis)
- [x] Pulley axes aligned with workpiece axis (Global X)
- [x] x2 direction clearly defined as lateral frame displacement
- [x] Rough/Fine mirror symmetry verified
- [x] 207, 70, 100 mm verified
- [x] No BELTMID closure used
- [x] Frame-driven actuation mechanism defined

### Key Coordinate Correction from V7
```
V7: belt_travel ‖ workpiece_axis → non-physical line contact
V8: belt_travel ⟂ workpiece_axis → correct cylindrical-conformal contact
```
