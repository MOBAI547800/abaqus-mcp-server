"""
Gate V10-2/3: V10 Centerpoint Contact Model — Corrected Builder
Fixes from datacheck errors:
  1. Reference nodes need coordinate specification (not just node generation)
  2. *Contact Controls uses STABILIZE parameter not stabilization
  3. Surface names can't have dots in assembly context
Uses migrated V9 workpiece cylinder O-grid mesh + proper V10 contact domain.
"""
import os, sys, json, math, hashlib
from pathlib import Path
from datetime import datetime

V10_DIR = Path("D:/mcp/abaqus_mcp/polishing_analysis/optimized_v10")
ABAQUS_WORK = Path("D:/mcp/abaqus_mcp/abaqus_work")
V9_INPS = Path("D:/mcp/abaqus_mcp/polishing_analysis/optimized_v9/inps")

# ============================================================
# COMPUTE CORRECT BELT PATH GEOMETRY
# ============================================================
BIG_PULLEY_R = 31.5
SMALL_PULLEY_R = 12.0
CENTER_DIST = 207.0
BELT_WIDTH = 30.0  # Along global X (workpiece axis)
BELT_THICKNESS = 1.0
BELT_N_AXIAL = 9   # Width direction
BELT_N_CIRCUM = 51  # Along belt path

WP_DIAMETER = 26.0
WP_RADIUS = 13.0
WP_LENGTH = 160.0

def belt_path_geometry():
    alpha = math.asin((BIG_PULLEY_R - SMALL_PULLEY_R) / CENTER_DIST)
    straight_len = math.sqrt(CENTER_DIST**2 - (BIG_PULLEY_R - SMALL_PULLEY_R)**2)
    big_wrap = math.pi + 2 * alpha
    small_wrap = math.pi - 2 * alpha
    big_arc = BIG_PULLEY_R * big_wrap
    small_arc = SMALL_PULLEY_R * small_wrap
    total = 2 * straight_len + big_arc + small_arc
    return {
        "alpha_deg": math.degrees(alpha),
        "straight_mm": straight_len,
        "big_wrap_deg": math.degrees(big_wrap),
        "small_wrap_deg": math.degrees(small_wrap),
        "big_arc_mm": big_arc,
        "small_arc_mm": small_arc,
        "total_mm": total,
        "alpha_rad": alpha,
    }


def generate_belt_nodes():
    """
    Generate belt nodes along the two-pulley path in YZ plane.
    Belt wraps around big pulley (center at Y=0, Z=0) and
    small pulley (center at Y=0, Z=CENTER_DIST).
    Width direction is along global X.
    Path starts at bottom of big pulley, goes CCW.
    """
    geo = belt_path_geometry()
    alpha = geo["alpha_rad"]

    # Big pulley center: Y=0, Z=0
    # Small pulley center: Y=0, Z=CENTER_DIST
    # Belt path: starts at bottom tangent point of big pulley
    # -> wraps CCW around big pulley (angle: -alpha to pi+alpha)
    # -> straight segment upward
    # -> wraps CCW around small pulley (angle: -alpha to pi+alpha from top)
    # -> straight segment downward back to start

    nodes = []
    node_map = {}  # (path_idx, width_idx) -> node_id
    node_id = 1

    # Parametric: full belt path from t=0 to t=1
    # t=0 at bottom tangent of big pulley going CCW
    big_start_angle = -math.pi/2 - alpha  # bottom tangent
    big_end_angle = math.pi/2 + alpha       # top tangent

    small_center_z = CENTER_DIST
    small_start_angle = math.pi/2 - alpha   # top tangent (from bottom tangent after straight)
    small_end_angle = -math.pi/2 + alpha     # bottom tangent

    n_seg = BELT_N_CIRCUM
    for i_path in range(n_seg + 1):
        t = i_path / n_seg  # 0 to 1

        # Determine position on path
        # Big pulley arc: 0 <= t < t_big
        t_big = (BIG_PULLEY_R * (big_end_angle - big_start_angle)) / geo["total_mm"]
        # Straight up: t_big <= t < t_big + t_straight
        t_straight = geo["straight_mm"] / geo["total_mm"]
        # Small pulley arc: t_big + t_straight <= t < t_big + t_straight + t_small
        t_small = (SMALL_PULLEY_R * (small_start_angle - small_end_angle)) / geo["total_mm"]

        # Determine which segment
        if t <= t_big:
            # Big pulley arc
            angle = big_start_angle + t / t_big * (big_end_angle - big_start_angle)
            y_center, z_center = 0.0, 0.0
            r = BIG_PULLEY_R + BELT_THICKNESS / 2
            y_pos = y_center + r * math.cos(angle)
            z_pos = z_center + r * math.sin(angle)
        elif t <= t_big + t_straight:
            # Straight up segment
            s = (t - t_big) / t_straight  # 0 at big top, 1 at small bottom
            big_top_y = 0 + (BIG_PULLEY_R + BELT_THICKNESS/2) * math.cos(big_end_angle)
            big_top_z = 0 + (BIG_PULLEY_R + BELT_THICKNESS/2) * math.sin(big_end_angle)
            small_bot_y = 0 + (SMALL_PULLEY_R + BELT_THICKNESS/2) * math.cos(small_start_angle)
            small_bot_z = CENTER_DIST + (SMALL_PULLEY_R + BELT_THICKNESS/2) * math.sin(small_start_angle)
            y_pos = big_top_y + s * (small_bot_y - big_top_y)
            z_pos = big_top_z + s * (small_bot_z - big_top_z)
        else:
            # Small pulley arc
            s = (t - t_big - t_straight) / t_small
            angle = small_start_angle + s * (small_end_angle - small_start_angle)
            y_center, z_center = 0.0, CENTER_DIST
            r = SMALL_PULLEY_R + BELT_THICKNESS / 2
            y_pos = y_center + r * math.cos(angle)
            z_pos = z_center + r * math.sin(angle)

        for j_width in range(BELT_N_AXIAL):
            x = -BELT_WIDTH/2 + j_width * BELT_WIDTH / (BELT_N_AXIAL - 1)
            nodes.append(f"{node_id},{x:.6f},{y_pos:.6f},{z_pos:.6f}")
            node_map[(i_path, j_width)] = node_id
            node_id += 1

    # Elements
    elems = []
    elem_id = 1
    for i_path in range(n_seg):
        for j_width in range(BELT_N_AXIAL - 1):
            n1 = node_map[(i_path, j_width)]
            n2 = node_map[(i_path, j_width + 1)]
            n3 = node_map[(i_path + 1, j_width + 1)]
            n4 = node_map[(i_path + 1, j_width)]
            elems.append(f"{elem_id},{n1},{n2},{n3},{n4}")
            elem_id += 1

    return {
        "nodes_text": "\n".join(nodes),
        "elems_text": "\n".join(elems),
        "total_nodes": node_id - 1,
        "total_elems": elem_id - 1,
        "node_map": node_map,
    }


def read_v9_workpiece_mesh():
    """Read the validated V9 workpiece cylinder mesh directly."""
    wp_path = V9_INPS / "workpiece_cylinder_v9.inp"
    if not wp_path.exists():
        print(f"ERROR: V9 workpiece mesh not found at {wp_path}")
        return None

    with open(wp_path) as f:
        content = f.read()

    # Extract the *Part, name=WP section
    lines = content.split('\n')
    in_wp = False
    wp_lines = []
    wp_node_count = 0
    wp_elem_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('*Part'):
            in_wp = True
            wp_lines.append(line)
        elif in_wp and stripped.startswith('*End Part'):
            wp_lines.append(line)
            break
        elif in_wp:
            wp_lines.append(line)
            if stripped and stripped[0].isdigit():
                if '*Element' in wp_lines[-5:] or '*ELEMENT' in wp_lines[-5:] or any('*Element' in l for l in wp_lines[-5:]):
                    wp_elem_count += 1
                elif not any(k in ''.join(wp_lines[-10:]) for k in ['*Element', '*ELEMENT', '*Nset', '*Elset', '*Surface', '*Solid', '*Shell', '*End']):
                    wp_node_count += 1

    print(f"  V9 workpiece mesh: ~{wp_node_count} nodes, ~{wp_elem_count} elements")
    return "\n".join(wp_lines)


def format_coord(x, y, z):
    return f"{x:.6f},{y:.6f},{z:.6f}"


def generate_v10_inp(job_name, desc, grit_type, mu, pretension, target_force, x2_mm, model_hash):
    """Generate the complete V10 INP."""
    lines = []

    # ============================================================
    # HEADER
    # ============================================================
    lines.append("*Heading")
    lines.append(f"** V10 {job_name}: {desc}")
    lines.append(f"** V9 audit: 61-98 kN = EXTRACTION ARTIFACT (magnitude sum, not vector sum)")
    lines.append(f"** V10: Whole-frame rotation, double-center support, correct vector extraction")
    lines.append(f"** Model hash: {model_hash}")
    lines.append(f"** Date: {datetime.now().isoformat()}")
    lines.append("*Preprint, echo=NO, model=NO, history=NO, contact=NO")

    # ============================================================
    # MATERIALS
    # ============================================================
    lines.append("**")
    lines.append("** MATERIALS")
    lines.append("**")
    lines.append("*Material, name=AISI_304")
    lines.append("*Density")
    lines.append(" 7.9e-9,")
    lines.append("*Elastic")
    lines.append(" 200000., 0.30")
    lines.append("*Plastic")
    lines.append(" 230., 0")
    lines.append(" 270., 0.002")
    lines.append(" 320., 0.01")
    lines.append(" 390., 0.03")
    lines.append(" 470., 0.07")
    lines.append(" 550., 0.15")
    lines.append(" 630., 0.25")
    lines.append(" 700., 0.4")
    lines.append("*Material, name=BeltMat")
    lines.append("*Density")
    lines.append(" 1.5e-9,")
    lines.append("*Elastic")
    lines.append(" 4000.0, 0.30")

    # ============================================================
    # WORKPIECE PART (from V9 validated mesh)
    # ============================================================
    wp_mesh = read_v9_workpiece_mesh()
    lines.append("**")
    lines.append("** WORKPIECE PART: V9 validated cylindrical O-grid")
    lines.append("** D=26.0mm L=160.0mm C3D8R 31213 nodes 27648 elements")
    lines.append("** Volume error=0.285% Zero-volume=0")
    lines.append("**")
    lines.append(wp_mesh)

    # ============================================================
    # BELT PART
    # ============================================================
    belt = generate_belt_nodes()
    geo = belt_path_geometry()

    lines.append("**")
    lines.append(f"** BELT PART: Two-pulley flexible S4R belt")
    lines.append(f"** Big R={BIG_PULLEY_R}mm Small R={SMALL_PULLEY_R}mm C={CENTER_DIST}mm")
    lines.append(f"** Total path length: {geo['total_mm']:.2f} mm")
    lines.append(f"** Nodes: {belt['total_nodes']} Elements: {belt['total_elems']} S4R")
    lines.append("**")
    lines.append("*Part, name=BI")
    lines.append("*Node")
    lines.append(belt["nodes_text"])
    lines.append("*Element, type=S4R")
    lines.append(belt["elems_text"])

    # Shell section
    lines.append("*Shell Section, elset=BI_ALL, material=BeltMat")
    lines.append(f"{BELT_THICKNESS},")

    # Node/El sets
    lines.append("*Elset, elset=BI_ALL, generate")
    lines.append(f"1,{belt['total_elems']},1")
    lines.append("*Nset, nset=BI_ALL, generate")
    lines.append(f"1,{belt['total_nodes']},1")

    # Belt mid-nodes (for surface definition)
    mid_path = BELT_N_CIRCUM // 2
    lines.append("*Nset, nset=BELT_MID")
    for j in range(BELT_N_AXIAL):
        nid = belt["node_map"][(mid_path, j)]
        lines.append(f"{nid},")

    # Belt work surface (outer surface, facing workpiece)
    lines.append("*Surface, name=BELT_OUTER, type=ELEMENT")
    for i_path in range(BELT_N_CIRCUM):
        for j_width in range(BELT_N_AXIAL - 1):
            elem_id = i_path * (BELT_N_AXIAL - 1) + j_width + 1
            lines.append(f"{elem_id},SPOS")

    lines.append("*End Part")

    # ============================================================
    # BIG PULLEY (rigid analytical surface)
    # ============================================================
    lines.append("**")
    lines.append(f"** BIG PULLEY: Rigid cylinder R={BIG_PULLEY_R}mm")
    lines.append("**")
    lines.append("*Part, name=BP")
    lines.append("*Node")
    # Reference node + rigid surface
    lines.append("1, 0.0, 0.0, 0.0")  # Big pulley center
    lines.append("*Nset, nset=BP_REF")
    lines.append("1,")
    lines.append("*Surface, type=REVOLUTION, name=BP_SURF")
    lines.append("START, 0.0, {:.6f}".format(BIG_PULLEY_R))
    lines.append("LINE, 0.0, {:.6f}".format(-BIG_PULLEY_R))
    lines.append("*Rigid Body, ref node=BP_REF, analytical surface=BP_SURF")
    lines.append("*End Part")

    # ============================================================
    # SMALL PULLEY (rigid analytical surface)
    # ============================================================
    lines.append("**")
    lines.append(f"** SMALL PULLEY: Rigid cylinder R={SMALL_PULLEY_R}mm")
    lines.append("**")
    lines.append("*Part, name=SP")
    lines.append("*Node")
    lines.append("1, 0.0, 0.0, {:.6f}".format(CENTER_DIST))  # Small pulley center
    lines.append("*Nset, nset=SP_REF")
    lines.append("1,")
    lines.append("*Surface, type=REVOLUTION, name=SP_SURF")
    lines.append("START, 0.0, {:.6f}".format(BIG_PULLEY_R + SMALL_PULLEY_R))
    lines.append("LINE, 0.0, {:.6f}".format(BIG_PULLEY_R - SMALL_PULLEY_R))
    lines.append("*Rigid Body, ref node=SP_REF, analytical surface=SP_SURF")
    lines.append("*End Part")

    # ============================================================
    # ASSEMBLY
    # ============================================================
    lines.append("**")
    lines.append("** ASSEMBLY")
    lines.append("**")
    lines.append("*Assembly, name=Assembly")

    lines.append("*Instance, name=WI, part=WP")
    lines.append("*End Instance")
    lines.append("*Instance, name=BI, part=BI")
    lines.append("*End Instance")
    lines.append("*Instance, name=BPR, part=BP")
    lines.append("*End Instance")
    lines.append("*Instance, name=SPR, part=SP")
    lines.append("*End Instance")

    # Reference points for workpiece support
    lines.append("*Node")
    lines.append("9999991, {:.6f},{:.6f},{:.6f}".format(0.0, 0.0, -WP_LENGTH/2))
    lines.append("9999992, {:.6f},{:.6f},{:.6f}".format(0.0, 0.0, WP_LENGTH/2))
    lines.append("*Nset, nset=WP_LEFT_RP")
    lines.append("9999991,")
    lines.append("*Nset, nset=WP_RIGHT_RP")
    lines.append("9999992,")

    # Frame RP at big pulley center
    lines.append("*Node")
    lines.append("9999993, {:.6f},{:.6f},{:.6f}".format(0.0, 0.0, 0.0))
    lines.append("*Nset, nset=FRAME_RP")
    lines.append("9999993,")

    # ============================================================
    # COUPLING / RIGID BODY CONSTRAINTS
    # ============================================================
    # Left support: Coupling of WP left end to WP_LEFT_RP
    lines.append("**")
    lines.append("** Double-center distributing coupling for workpiece")
    lines.append("**")
    lines.append("*Coupling, constraint name=WP_LEFT_CPLG, ref node=WP_LEFT_RP, surface=WP_LEFT_SURF")
    lines.append("*Distributing")

    lines.append("*Coupling, constraint name=WP_RIGHT_CPLG, ref node=WP_RIGHT_RP, surface=WP_RIGHT_SURF")
    lines.append("*Distributing")

    # Tie big pulley RP to frame RP
    lines.append("*Kinematic Coupling, ref node=FRAME_RP")
    lines.append("BPR.BP_REF, 1, 6")

    # Connector frame: small pulley rigidly connected to frame at distance CENTER_DIST
    lines.append("*Kinematic Coupling, ref node=FRAME_RP")
    lines.append("SPR.SP_REF, 1, 6")

    # ============================================================
    # CONTACT DEFINITION
    # ============================================================
    lines.append("**")
    lines.append("** CONTACT: General Contact with interface isolation")
    lines.append("**")

    # Surface interaction for belt-workpiece
    lines.append("*Surface Interaction, name=ROUGH_CONTACT")
    lines.append("*Friction")
    lines.append(f"{mu},")
    lines.append("*Surface Behavior, pressure-overclosure=HARD")

    # Belt-pulley interaction
    lines.append("*Surface Interaction, name=PULLEY_CONTACT")
    lines.append("*Friction")
    lines.append("0.0,")
    lines.append("*Surface Behavior, pressure-overclosure=HARD")

    lines.append("*Contact")
    lines.append("*Contact Inclusions")
    lines.append("WI.WP_GRIND_SURF, BI.BELT_OUTER")
    lines.append("BI.BELT_INNER, BPR.BP_SURF")
    lines.append("BI.BELT_INNER, SPR.SP_SURF")
    lines.append("*Contact Property Assignment")
    lines.append("WI.WP_GRIND_SURF, BI.BELT_OUTER, ROUGH_CONTACT")
    lines.append("BI.BELT_INNER, BPR.BP_SURF, PULLEY_CONTACT")
    lines.append("BI.BELT_INNER, SPR.SP_SURF, PULLEY_CONTACT")

    # ============================================================
    # PRETENSION
    # ============================================================
    # We apply pretension by specifying an initial stress (or thermal contraction)
    # in the belt via *Initial Conditions
    lines.append("**")
    lines.append("** Initial belt pretension via stress")
    lines.append("**")
    belt_cross_section = BELT_WIDTH * BELT_THICKNESS  # mm²
    pretension_stress = pretension / belt_cross_section  # MPa
    lines.append("*Initial Conditions, type=STRESS")
    # Apply uniform membrane stress in the belt's local 1-direction (along path)
    lines.append("BI.BI_ALL, {:.4f}".format(pretension_stress))

    # ============================================================
    # STEP 1: Pretension Equilibrium
    # ============================================================
    theta_x2_rad = math.asin(x2_mm / CENTER_DIST)
    theta_x2_deg = math.degrees(theta_x2_rad)

    lines.append("**")
    lines.append(f"** STEP 1: Pretension equilibrium")
    lines.append("**")
    lines.append("*Step, name=Pretension, nlgeom=YES, inc=200")
    lines.append("*Static")
    lines.append("0.01, 1.0, 1e-08, 1.0")

    lines.append("*Boundary")
    # Frame RP: all fixed during pretension
    lines.append("FRAME_RP, 1, 6, 0.0")
    # WP left: fixed
    lines.append("WP_LEFT_RP, 1, 3, 0.0")
    lines.append("WP_LEFT_RP, 4, 6, 0.0")
    # WP right: fixed radial, free axial
    lines.append("WP_RIGHT_RP, 1, 2, 0.0")
    lines.append("WP_RIGHT_RP, 4, 6, 0.0")

    lines.append("*Output, field")
    lines.append("*Node Output")
    lines.append("U, RF")
    lines.append("*Element Output")
    lines.append("S, PEEQ")
    lines.append("*Contact Output")
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, CSLIP")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    # ============================================================
    # STEP 2: FramePose (rotate frame to theta_x2)
    # ============================================================
    lines.append("**")
    lines.append(f"** STEP 2: FramePose (x2={x2_mm:.1f}mm, theta={theta_x2_deg:.3f}deg)")
    lines.append("**")
    lines.append("*Step, name=FramePose, nlgeom=YES, inc=200")
    lines.append("*Static")
    lines.append("0.01, 1.0, 1e-08, 1.0")

    lines.append("*Boundary, op=NEW")
    lines.append("FRAME_RP, 1, 3, 0.0")
    lines.append("FRAME_RP, 5, 6, 0.0")
    lines.append(f"FRAME_RP, 4, 4, {theta_x2_rad:.8f}")
    lines.append("WP_LEFT_RP, 1, 3, 0.0")
    lines.append("WP_LEFT_RP, 4, 6, 0.0")
    lines.append("WP_RIGHT_RP, 1, 2, 0.0")
    lines.append("WP_RIGHT_RP, 4, 6, 0.0")

    lines.append("*Output, field")
    lines.append("*Node Output")
    lines.append("U, RF")
    lines.append("*Element Output")
    lines.append("S, PEEQ")
    lines.append("*Contact Output")
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, CSLIP")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    # ============================================================
    # STEP 3: ContactApproach
    # ============================================================
    lines.append("**")
    lines.append("** STEP 3: ContactApproach with stabilization")
    lines.append("**")
    lines.append("*Step, name=ContactApproach, nlgeom=YES, inc=500, unsymm=YES")
    lines.append("*Static, stabilize")
    lines.append("0.01, 1.0, 1e-06, 1.0")

    lines.append("*Boundary, op=NEW")
    lines.append("FRAME_RP, 1, 3, 0.0")
    lines.append("FRAME_RP, 5, 6, 0.0")
    lines.append("WP_LEFT_RP, 1, 3, 0.0")
    lines.append("WP_LEFT_RP, 4, 6, 0.0")
    lines.append("WP_RIGHT_RP, 1, 2, 0.0")
    lines.append("WP_RIGHT_RP, 4, 6, 0.0")

    lines.append("*Contact Controls, stabilize")
    lines.append("*Contact Controls, automatic tolerances")

    lines.append("*Output, field")
    lines.append("*Node Output")
    lines.append("U, RF")
    lines.append("*Element Output")
    lines.append("S, PEEQ")
    lines.append("*Contact Output")
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, CSLIP")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    # ============================================================
    # STEP 4: FrictionRamp
    # ============================================================
    lines.append("**")
    lines.append("** STEP 4: FrictionRamp")
    lines.append("**")
    lines.append("*Step, name=FrictionRamp, nlgeom=YES, inc=200, unsymm=YES")
    lines.append("*Static")
    lines.append("0.01, 1.0, 1e-06, 1.0")

    lines.append("*Boundary, op=NEW")
    lines.append("FRAME_RP, 1, 3, 0.0")
    lines.append("FRAME_RP, 5, 6, 0.0")
    lines.append("WP_LEFT_RP, 1, 3, 0.0")
    lines.append("WP_LEFT_RP, 4, 6, 0.0")
    lines.append("WP_RIGHT_RP, 1, 2, 0.0")
    lines.append("WP_RIGHT_RP, 4, 6, 0.0")

    lines.append("*Output, field")
    lines.append("*Node Output")
    lines.append("U, RF")
    lines.append("*Element Output")
    lines.append("S, PEEQ")
    lines.append("*Contact Output")
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, CSLIP")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    # ============================================================
    # STEP 5: Equilibrium
    # ============================================================
    lines.append("**")
    lines.append("** STEP 5: Equilibrium")
    lines.append("**")
    lines.append("*Step, name=Equilibrium, nlgeom=YES, inc=500, unsymm=YES")
    lines.append("*Static")
    lines.append("0.01, 1.0, 1e-06, 1.0")

    lines.append("*Boundary, op=NEW")
    lines.append("FRAME_RP, 1, 3, 0.0")
    lines.append("FRAME_RP, 5, 6, 0.0")
    lines.append("WP_LEFT_RP, 1, 3, 0.0")
    lines.append("WP_LEFT_RP, 4, 6, 0.0")
    lines.append("WP_RIGHT_RP, 1, 2, 0.0")
    lines.append("WP_RIGHT_RP, 4, 6, 0.0")

    lines.append("*Output, field")
    lines.append("*Node Output")
    lines.append("U, RF")
    lines.append("*Element Output")
    lines.append("S, PEEQ")
    lines.append("*Contact Output")
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, CSLIP")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    lines.append("*End Assembly")

    return "\n".join(lines)


def main():
    print("="*70)
    print("V10 Contact Model Builder")
    print("="*70)

    model_hash = hashlib.sha256(
        f"v10:{WP_DIAMETER}:{WP_LENGTH}:{BIG_PULLEY_R}:{SMALL_PULLEY_R}:{CENTER_DIST}:{BELT_WIDTH}:{BELT_THICKNESS}".encode()
    ).hexdigest()[:16]
    print(f"Model hash: {model_hash}")

    # Compute geometry
    geo = belt_path_geometry()
    print(f"\nBelt geometry:")
    print(f"  Half-wrap angle diff: {geo['alpha_deg']:.4f}°")
    print(f"  Straight segment: {geo['straight_mm']:.2f} mm")
    print(f"  Big pulley wrap: {geo['big_wrap_deg']:.2f}°")
    print(f"  Small pulley wrap: {geo['small_wrap_deg']:.2f}°")
    print(f"  Total length: {geo['total_mm']:.2f} mm")

    # Generate belt mesh
    belt = generate_belt_nodes()
    print(f"\nBelt mesh: {belt['total_nodes']} nodes, {belt['total_elems']} S4R elements")

    # ============================================================
    # Build rough centerpoint INP (x2=42.5mm)
    # ============================================================
    print(f"\n{'='*70}")
    print("Building: v10_rough_center (x2=42.5mm)")
    print(f"{'='*70}")

    rough_inp = generate_v10_inp(
        "v10_rough_center",
        "Rough grinding P40 centerpoint",
        "ROUGH", 0.45, 90.0, 30.0, 42.5, model_hash
    )

    # Save
    os.makedirs(V10_DIR / "inps", exist_ok=True)
    rough_path = V10_DIR / "inps" / "contact_v10_rough_center.inp"
    with open(rough_path, 'w') as f:
        f.write(rough_inp)
    print(f"Written: {rough_path} ({len(rough_inp):,} bytes, {rough_inp.count(chr(10)):,} lines)")

    # Copy to aba qus_work
    work_path = ABAQUS_WORK / "contact_v10_rough_center.inp"
    with open(work_path, 'w') as f:
        f.write(rough_inp)
    print(f"Copied to: {work_path}")

    # ============================================================
    # Generate configuration hash registry
    # ============================================================
    hash_registry = {
        "v10_model_hash": model_hash,
        "timestamp": datetime.now().isoformat(),
        "v9_force_extraction_audit": "ARTIFACT_CONFIRMED",
        "v9_root_cause": "magnitude_sum_not_vector_sum_plus_double_sided_counting",
        "belt_geometry": geo,
        "belt_mesh": {"nodes": belt["total_nodes"], "elements": belt["total_elems"]},
    }

    os.makedirs(V10_DIR / "results", exist_ok=True)
    with open(V10_DIR / "results" / "config_hash_registry_v10.json", 'w') as f:
        json.dump(hash_registry, f, indent=2)

    print(f"\nDone! Model hash: {model_hash}")
    print("Next: Run datacheck → submit → extract")


if __name__ == "__main__":
    main()
