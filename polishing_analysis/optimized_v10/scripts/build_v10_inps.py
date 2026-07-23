"""
V10 INP Generator — Clean approach using *INCLUDE for V9 mesh.
"""
import math
import hashlib
import os
from datetime import datetime

V10_DIR = "D:/mcp/abaqus_mcp/polishing_analysis/optimized_v10"
ABAQUS_WORK = "D:/mcp/abaqus_mcp/abaqus_work"
INCLUDES = f"{ABAQUS_WORK}/includes"

BIG_PULLEY_R = 31.5
SMALL_PULLEY_R = 12.0
CENTER_DIST = 207.0
BELT_WIDTH = 30.0
BELT_THICKNESS = 1.0
BELT_N_AXIAL = 9
BELT_N_CIRCUM = 51
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
        "alpha_rad": alpha,
        "straight_mm": straight_len,
        "big_wrap_deg": math.degrees(big_wrap),
        "big_wrap_rad": big_wrap,
        "small_wrap_deg": math.degrees(small_wrap),
        "small_wrap_rad": small_wrap,
        "big_arc_mm": big_arc,
        "small_arc_mm": small_arc,
        "total_mm": total,
    }


def generate_belt_part():
    geo = belt_path_geometry()
    alpha = geo["alpha_rad"]
    big_start = -math.pi/2 - alpha
    big_end = math.pi/2 + alpha
    small_start = math.pi/2 - alpha
    small_end = -math.pi/2 + alpha

    lines = []
    lines.append("*Part, name=BI")
    lines.append("*Node")

    node_map = {}
    nid = 1
    n_seg = BELT_N_CIRCUM

    t_big = (BIG_PULLEY_R * (big_end - big_start)) / geo["total_mm"]
    t_straight = geo["straight_mm"] / geo["total_mm"]
    t_small = 1.0 - t_big - t_straight
    r_outer = BIG_PULLEY_R + BELT_THICKNESS / 2
    r_inner = SMALL_PULLEY_R + BELT_THICKNESS / 2

    for i_path in range(n_seg + 1):
        t = i_path / n_seg
        if t <= t_big:
            angle = big_start + t / t_big * (big_end - big_start)
            y_pos = r_outer * math.cos(angle)
            z_pos = r_outer * math.sin(angle)
        elif t <= t_big + t_straight:
            s = (t - t_big) / t_straight
            big_top_y = r_outer * math.cos(big_end)
            big_top_z = r_outer * math.sin(big_end)
            small_bot_y = r_inner * math.cos(small_start)
            small_bot_z = CENTER_DIST + r_inner * math.sin(small_start)
            y_pos = big_top_y + s * (small_bot_y - big_top_y)
            z_pos = big_top_z + s * (small_bot_z - big_top_z)
        else:
            s = (t - t_big - t_straight) / t_small
            angle = small_start + s * (small_end - small_start)
            y_pos = r_inner * math.cos(angle)
            z_pos = CENTER_DIST + r_inner * math.sin(angle)

        for j_width in range(BELT_N_AXIAL):
            x = -BELT_WIDTH/2 + j_width * BELT_WIDTH / (BELT_N_AXIAL - 1)
            lines.append(f"{nid},{x:.6f},{y_pos:.6f},{z_pos:.6f}")
            node_map[(i_path, j_width)] = nid
            nid += 1

    total_nodes = nid - 1

    lines.append("*Element, type=S4R")
    eid = 1
    for i_path in range(n_seg):
        for j_width in range(BELT_N_AXIAL - 1):
            n1 = node_map[(i_path, j_width)]
            n2 = node_map[(i_path, j_width + 1)]
            n3 = node_map[(i_path + 1, j_width + 1)]
            n4 = node_map[(i_path + 1, j_width)]
            lines.append(f"{eid},{n1},{n2},{n3},{n4}")
            eid += 1
    total_elems = eid - 1

    # Sets
    lines.append("*Elset, elset=BI_ALL, generate")
    lines.append(f"1,{total_elems},1")
    lines.append("*Nset, nset=BI_ALL, generate")
    lines.append(f"1,{total_nodes},1")

    # Belt outer surface (SPOS side = outer)
    lines.append("*Surface, name=BELT_OUTER, type=ELEMENT")
    for ep in range(1, total_elems + 1):
        lines.append(f"{ep},SPOS")

    # Belt inner surface (SNEG side = inner, contacts pulleys)
    lines.append("*Surface, name=BELT_INNER, type=ELEMENT")
    for ep in range(1, total_elems + 1):
        lines.append(f"{ep},SNEG")

    # Shell section
    lines.append("*Shell Section, elset=BI_ALL, material=BeltMat")
    lines.append(f"{BELT_THICKNESS},")

    lines.append("*End Part")
    return "\n".join(lines), total_nodes, total_elems, node_map


def generate_pulley_part(name, radius, z_center, y_center=0.0):
    lines = []
    lines.append(f"*Part, name={name}")
    lines.append("*Node")
    lines.append(f"1, 0.0, {y_center:.6f}, {z_center:.6f}")
    lines.append(f"*Nset, nset={name}_REF")
    lines.append("1,")
    # Analytical rigid surface: REVOLUTION about the X axis
    # For REVOLUTION type: local z is along revolution axis (X global),
    # local r is radial distance. START(r,z) LINE(r,z)
    half_w = BELT_WIDTH/2 + 2.0
    # Small positive r at one end, moving to same r at other end = cylinder
    lines.append(f"*Surface, type=REVOLUTION, name={name}_SURF")
    lines.append(f"START, {radius:.3f}, -{half_w:.3f}")
    lines.append(f"LINE,  {radius:.3f},  {half_w:.3f}")
    lines.append(f"*Rigid Body, ref node={name}_REF, analytical surface={name}_SURF")
    lines.append("*End Part")
    return "\n".join(lines)


def generate_inp(job_name, desc, mu, pretension_N, x2_mm):
    geo = belt_path_geometry()
    theta_x2_rad = math.asin(x2_mm / CENTER_DIST)
    theta_x2_deg = math.degrees(theta_x2_rad)
    belt_part, belt_nodes, belt_elems, belt_map = generate_belt_part()
    bp_part = generate_pulley_part("BP", BIG_PULLEY_R, 0.0)
    sp_part = generate_pulley_part("SP", SMALL_PULLEY_R, CENTER_DIST)
    model_hash = hashlib.sha256(
        f"v10:{WP_RADIUS*2}:{WP_LENGTH}:{BIG_PULLEY_R}:{SMALL_PULLEY_R}:{CENTER_DIST}:{BELT_WIDTH}:{BELT_THICKNESS}".encode()
    ).hexdigest()[:16]

    # Pretension stress
    belt_cs = BELT_WIDTH * BELT_THICKNESS
    pretension_stress = pretension_N / belt_cs

    lines = []
    lines.append("*Heading")
    lines.append(f"** V10 {job_name}: {desc}")
    lines.append(f"** Model hash: {model_hash}")
    lines.append(f"** V9 audit: 61-98 kN = EXTRACTION ARTIFACT confirmed")
    lines.append(f"** V10: Whole-frame rotation + double-center coupling support")
    lines.append(f"** Belt: {belt_nodes} nodes, {belt_elems} S4R")
    lines.append(f"** Date: {datetime.now().isoformat()}")
    lines.append("*Preprint, echo=NO, model=NO, history=NO, contact=NO")

    # Materials
    lines.append("** MATERIALS")
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

    # Workpiece — include V9 validated mesh
    lines.append("** WORKPIECE: V9 validated cylindrical O-grid (D=26mm L=160mm)")
    lines.append(f"*Include, input=includes/wp_cylinder_v9.inc")

    # Belt
    lines.append("** BELT: Two-pulley flexible S4R")
    lines.append(belt_part)

    # Pulleys
    lines.append("** BIG PULLEY: Rigid R=31.5mm")
    lines.append(bp_part)
    lines.append("** SMALL PULLEY: Rigid R=12.0mm")
    lines.append(sp_part)

    # Assembly
    lines.append("** ASSEMBLY")
    lines.append("*Assembly, name=Assembly")
    lines.append("*Instance, name=WI, part=WP")
    lines.append("*End Instance")
    lines.append("*Instance, name=BI, part=BI")
    lines.append("*End Instance")
    lines.append("*Instance, name=BPR, part=BP")
    lines.append("*End Instance")
    lines.append("*Instance, name=SPR, part=SP")
    lines.append("*End Instance")

    # Reference points
    lines.append("*Node")
    lines.append("9999991, 0.0, 0.0, {:.6f}".format(-WP_LENGTH/2))
    lines.append("9999992, 0.0, 0.0, {:.6f}".format(WP_LENGTH/2))
    lines.append("9999993, 0.0, 0.0, 0.0")
    lines.append("*Nset, nset=WP_LEFT_RP")
    lines.append("9999991,")
    lines.append("*Nset, nset=WP_RIGHT_RP")
    lines.append("9999992,")
    lines.append("*Nset, nset=FRAME_RP")
    lines.append("9999993,")

    # Surfaces for coupling (using V9 node set names)
    # V9 workpiece defines EndLeft, EndRight, OuterSurface, ContactSurface
    lines.append("*Surface, type=NODE, name=WP_LEFT_NODES")
    lines.append("WI.EndLeft")
    lines.append("*Surface, type=NODE, name=WP_RIGHT_NODES")
    lines.append("WI.EndRight")
    # Grinding surface — use OuterSurface for contact
    lines.append("*Surface, type=NODE, name=WP_GRIND_SURF_NODES")
    lines.append("WI.OuterSurface")
    lines.append("*Surface, type=ELEMENT, name=WP_ALL_SURF")
    lines.append("WI.AllElems, ")  # All element faces for General Contact

    # Coupling constraints
    lines.append("*Coupling, constraint name=WP_LEFT_CPLG, ref node=WP_LEFT_RP, surface=WP_LEFT_NODES")
    lines.append("*Distributing")
    lines.append("*Coupling, constraint name=WP_RIGHT_CPLG, ref node=WP_RIGHT_RP, surface=WP_RIGHT_NODES")
    lines.append("*Distributing")

    # Frame: tie big pulley to frame
    lines.append("*Kinematic Coupling, ref node=FRAME_RP")
    lines.append("BPR.BP_REF, 1, 6")
    # Tie small pulley: rigid link from frame
    lines.append("*Kinematic Coupling, ref node=SPR.SP_REF")
    lines.append("FRAME_RP, 1, 6")

    lines.append("*End Assembly")

    # Contact/surface definitions — at model level, between End Assembly and Steps
    # (matches V9: Surface Interaction → Contact → Contact Inclusions → Contact Property Assignment)
    lines.append("*Surface Interaction, name=INT_BW")
    lines.append("*Friction")
    lines.append(f"{mu},")
    lines.append("*Surface Behavior, pressure-overclosure=HARD")
    lines.append("*Surface Interaction, name=INT_PULLEY")
    lines.append("*Friction")
    lines.append("0.0,")
    lines.append("*Surface Behavior, pressure-overclosure=HARD")
    lines.append("*Contact")
    lines.append("*Contact Inclusions")
    lines.append("WI.WP_ALL_SURF, BI.BELT_OUTER")
    lines.append("BI.BELT_INNER, BPR.BP_SURF")
    lines.append("BI.BELT_INNER, SPR.SP_SURF")
    lines.append("*Contact Property Assignment")
    lines.append("WI.WP_ALL_SURF, BI.BELT_OUTER,  INT_BW")
    lines.append("BI.BELT_INNER, BPR.BP_SURF,   INT_PULLEY")
    lines.append("BI.BELT_INNER, SPR.SP_SURF,   INT_PULLEY")
    lines.append("*Initial Conditions, type=STRESS")
    lines.append(f"BI.BI_ALL, {pretension_stress:.4f}")

    lines.append("*Step, name=Pretension, nlgeom=YES, inc=200")
    lines.append("*Static")
    lines.append("0.01, 1.0, 1e-08, 1.0")
    lines.append("*Boundary")
    lines.append("FRAME_RP, 1, 6, 0.0")
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
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN")
    lines.append("*Output, history")

    # ================================================================
    # STEP 2: FramePose
    # ================================================================
    lines.append("**")
    lines.append(f"** STEP 2: FramePose (theta={theta_x2_deg:.3f}deg)")
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
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN")
    lines.append("*Output, history")

    # ================================================================
    # STEP 3: ContactApproach
    # ================================================================
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
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN")
    lines.append("*Output, history")
    lines.append("*Energy Output")
    lines.append("ALLSE, ALLSD, ALLWK")
    lines.append("*End Step")

    # ================================================================
    # STEP 4: FrictionRamp
    # ================================================================
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
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN")
    lines.append("*Output, history")

    # ================================================================
    # STEP 5: Equilibrium
    # ================================================================
    lines.append("**")
    lines.append("** STEP 5: Equilibrium (steady state)")
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
    lines.append("CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN")
    lines.append("*Output, history")

    return "\n".join(lines), model_hash


def main():
    os.makedirs(V10_DIR + "/inps", exist_ok=True)

    for grit, mu, pret, x2, suff in [
        ("ROUGH", 0.45, 90.0, 42.5, "rough_center"),
        ("ROUGH", 0.45, 90.0, 35.0, "rough_x2_35"),
        ("ROUGH", 0.45, 90.0, 50.0, "rough_x2_50"),
        ("FINE",  0.35, 60.0, 42.5, "fine_center"),
        ("FINE",  0.35, 60.0, 35.0, "fine_x2_35"),
        ("FINE",  0.35, 60.0, 50.0, "fine_x2_50"),
    ]:
        desc = f"{grit} x2={x2}mm mu={mu}"
        inp, mhash = generate_inp(f"v10_{suff}", desc, mu, pret, x2)
        fname = f"contact_v10_{suff}.inp"
        path_v10 = f"{V10_DIR}/inps/{fname}"
        path_work = f"{ABAQUS_WORK}/{fname}"
        with open(path_v10, 'w') as f: f.write(inp)
        with open(path_work, 'w') as f: f.write(inp)
        nlines = inp.count('\n')
        print(f"  {fname:35s} {nlines:>6d} lines  hash={mhash}")

    print(f"\nAll 6 contact scenario INPs generated.")
    print(f"Next: abaqus job=v10_rough_center_dc input=contact_v10_rough_center.inp datacheck")


if __name__ == "__main__":
    main()
