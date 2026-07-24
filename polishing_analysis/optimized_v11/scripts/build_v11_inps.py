    # === STEPS ===
    # TWO-STEP DISPLACEMENT-DRIVEN STRATEGY:
    # Step 1: Release pretension at fixed frame pose.
    #   Belt tensions under *Initial Conditions, TYPE=STRESS.
    #   No stabilization needed — belt finds equilibrium via tension.
    # Step 2: Move workpiece RIGHT_RP in Z+ direction toward belt by a small
    #   displacement to bring workpiece into contact with the tensioned belt.

    def output_field():
        return [
            "*Output, field",
            "*Node Output",
            "U, RF",
            "*Element Output",
            "S, PEEQ",
            "*Contact Output",
            "CSTRESS, CSTATUS, CFORCE, CDISP",
            "*Output, history"
        ]

    # STEP 1: Release pretension at fixed frame pose
    step1 = []
    step1.append(f"**")
    step1.append(f"** STEP 1: Pretension release ({pretension_N:.1f}N) at frame theta={theta_x2_deg:.3f}deg")
    step1.append(f"**")
    step1.append("*Step, name=Pretension, nlgeom=YES, inc=200")
    step1.append("*Static")
    step1.append("0.01, 1.0, 1e-08, 1.0")
    step1.append("*Boundary")
    step1.append("FRAME_RP, 1, 3, 0.0")
    step1.append("FRAME_RP, 5, 6, 0.0")
    step1.append(f"FRAME_RP, 4, 4, {theta_x2_rad:.8f}")
    step1.append("SP_RP, 1, 6, 0.0")
    step1.append("WP_LEFT_RP, 1, 3, 0.0")
    step1.append("WP_LEFT_RP, 4, 6, 0.0")
    step1.append("WP_RIGHT_RP, 1, 3, 0.0")
    step1.append("WP_RIGHT_RP, 4, 6, 0.0")
    step1.extend(output_field())
    step1.append("*Energy Output")
    step1.append("ALLSE, ALLSD, ALLWK")
    inp.add_step("Pretension", step1)

    # STEP 2: Move workpiece Z+ to engage belt (displacement-driven)
    step2 = []
    step2.append(f"**")
    step2.append(f"** STEP 2: Workpiece approach (Z+ displacement to engage belt)")
    step2.append(f"**")
    step2.append("*Step, name=ContactApproach, nlgeom=YES, inc=500")
    step2.append("*Static")
    step2.append("0.01, 1.0, 1e-08, 1.0")
    step2.append("*Boundary, op=NEW")
    step2.append("FRAME_RP, 1, 3, 0.0")
    step2.append("FRAME_RP, 5, 6, 0.0")
    step2.append(f"FRAME_RP, 4, 4, {theta_x2_rad:.8f}")
    step2.append("SP_RP, 1, 6, 0.0")
    step2.append("WP_LEFT_RP, 1, 3, 0.0")
    step2.append("WP_LEFT_RP, 4, 6, 0.0")
    step2.append("WP_RIGHT_RP, 1, 2, 0.0")
    step2.append("WP_RIGHT_RP, 4, 6, 0.0")
    step2.append(f"WP_RIGHT_RP, 3, 3, 2.0")
    step2.extend(output_field())
    step2.append("*Energy Output")
    step2.append("ALLSE, ALLSD, ALLWK")
    inp.add_step("ContactApproach", step2)