# V8 Center ODB Diagnostic Report
## Date: 2026-07-23
## Status: DIAGNOSTIC_COMPLETE

---

## Key Finding: NO CONTACT ESTABLISHED

### contact_v8_rough_center.odb
- **Contact status**: CSTATUS = 0/1485 points (0%)
- **CPRESS**: All zero across all 3 steps
- **Workpiece**: 1845 nodes, 1280 C3D8R elements — **RECTANGULAR BLOCK**
- **Belt**: 459 nodes, 400 S4R elements — Flat plane, 200×30mm
- **Pretension RF**: ~32.4 N per belt corner (node pairs 452/458, 2/8) → ~129.6 N total tension
- **FrameEngage**: Belt end nodes displaced ~81 mm in Z (simulated frame rotation)
- **Equilibrium**: Stable but zero contact

### contact_v8_fine_center.odb
- **Contact status**: CSTATUS = 0/1485 points (0%)
- **CPRESS**: All zero across all 3 steps
- **Pretension RF**: ~21.4 N per belt corner → ~85.5 N total tension  
- **FrameEngage**: Same end-node Z displacement pattern
- **Equilibrium**: Stable but zero contact

### contact_v8_rough_center_frame.odb
- Failed to open fully — appears to be an empty or corrupt variant

## Root Cause Analysis

1. **Incorrect workpiece geometry**: Flat rectangular block cannot conform to belt surface
2. **Oversimplified belt geometry**: Flat belt plane doesn't wrap around pulleys — no two-pulley path
3. **End-node Z displacement**: Not true frame rigid body rotation — belt deformation is unrealistic
4. **Initial gap too large**: Belt and workpiece start too far apart; frame rotation angle insufficient

## V8 Reclassification

| Item | V8 Status | V9 Status |
|------|-----------|-----------|
| V8-0/V8-1 Gates | PASS | PASS_INHERITED |
| V8-2 Pretension | PASS | PASS_PRETENSION_TECHNICAL |
| V8-3 Center Contact | 0 CONTACT | FAILED_NO_CONTACT |
| Rectangular workpiece | In use | INVALID_WORKPIECE_GEOMETRY_FOR_PRODUCTION |
| End-node Z actuation | In use | APPROXIMATE_FRAME_ACTUATION |
| 16 offset INPs | Generated | DO_NOT_SUBMIT — need adaptive bracket search first |
| V8 ODBs | Extraction complete | DIAGNOSTIC_ONLY |

## V9 Action Items

1. Build true cylinder (D=26mm, L=160mm) with O-grid hex mesh — ZERO zero-volume elements
2. Build two-pulley open belt path with proper geometry
3. Build FRAME_RP rigid body chain — rotation about big pulley center
4. Calibrate two-pulley pretension (rough 90N, fine 60N at tensioner RP)
5. Run centerpoint zero-offset ODBs → extract → adaptive bracket to target force
