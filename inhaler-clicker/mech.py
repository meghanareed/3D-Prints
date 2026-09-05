"""The mechanism: Part C (the canister) and the collar it runs in.

The self-test here is the reason this file is separate from the parts it builds. Rule:
test the physical motion, not the numbers. So `travel_test()` builds the canister, the
collar and the switch, puts them where they will actually be, and then MOVES the canister
down in steps, measuring interference at each one. A check that compares BUTTON_TRAVEL
against BUTTON_TRAVEL cannot see a lug that misses its slot.

Two coordinate systems, and they are not the same one:

    BODY coords   z = 0 is the base of the inhaler. params.stack() speaks this.
    PART coords   z = 0 is the face the part prints on.

Everything below says which it is returning. The one bug this file has already had was a
receiver placed in the wrong one.

    python mech.py            build and run the travel test
    python mech.py --export   also write out/*.step
"""
import math
import os
import sys

import cadquery as cq

import params as P
import switch

HERE = os.path.dirname(os.path.abspath(__file__))

RIB_T = 1.2            # = MIN_FEATURE_T. Four of them, tying the boss to the skirt.
RIB_COUNT = 4
BOSS_CLOSED_TOP = 1.5  # material above the blind socket, so the stem cannot punch out


# ==================================================================== Part C ==
def canister(printing=True):
    """The faux canister / button. PART coords: z=0 is the open rim, which is the face
    it prints on. Pass printing=False for BODY coords at the rest position.

    Prints rim-down, like the sample does, so the boss and the ribs grow up off the plate
    instead of hanging in mid-air, and the only overhang in the part is the closed crown
    bridging the cavity -- which is exactly what the sample bridges, at 13.4 mm, and it
    is a known-good span.
    """
    h = P.stack()["canister_height"]
    od = float(P.CANISTER_OD)
    inner = od - 2 * float(P.CANISTER_WALL)

    shell = (cq.Workplane("XY").circle(od / 2).extrude(h)
             .faces(">Z").edges().chamfer(float(P.CANISTER_TOP_CHAMFER)))

    # The lugs: the entire hard stop, on +X and -X, where the body has the width to
    # take a slot. A full flange would have to be wider than the canister, and a bore
    # wide enough to swallow one does not fit across the body's depth.
    lug = (cq.Workplane("XY")
           .box(float(P.LUG_OD), float(P.LUG_W), float(P.LUG_H),
                centered=(True, True, False))
           .intersect(cq.Workplane("XY").circle(float(P.LUG_OD) / 2)
                      .extrude(float(P.LUG_H))))
    shell = shell.union(lug)

    # Cavity: a plain bore with a flat crown over it. NOT a cone -- a 45 deg cone roof
    # is 45 deg off vertical against a 30 deg support threshold, and the note next door
    # is that sitting near the threshold is the worst place to be. A bridged flat span
    # is what the sample does and it is not an overhang at all.
    cavity_h = h - float(P.CANISTER_TOP_T)
    shell = shell.cut(cq.Workplane("XY").circle(inner / 2).extrude(cavity_h))

    # The stem receiver, standing on the rim plane so the socket mouth is AT the rim.
    boss_len = float(P.MX_SOCKET_DEPTH) + BOSS_CLOSED_TOP
    shell = shell.union(switch.stem_receiver(boss_len))

    # Ribs tie the boss to the skirt. Overlapped into both at each end, because tangency
    # is not contact -- two solids that merely touch stay two solids.
    r_in, r_out = float(P.MX_BOSS_OD) / 2 - 0.8, inner / 2 + 0.3
    rib = (cq.Workplane("XY")
           .box(r_out - r_in, RIB_T, boss_len, centered=(False, True, False))
           .translate((r_in, 0, 0)))
    for i in range(RIB_COUNT):
        shell = shell.union(rib.rotate((0, 0, 0), (0, 0, 1), 45 + i * 360.0 / RIB_COUNT))

    if printing:
        return shell
    return shell.translate((0, 0, P.stack()["canister_rim_rest"]))


# ============================================================ the collar ======
def collar_cut():
    """What the body removes to make the canister collar. BODY coords.

    Bore, plus two lug slots that run OPEN TO THE TOP FACE. The slot floor is the hard
    stop; there is no ceiling, because a captured lug cannot be got in past one.
    """
    s = P.stack()
    top = s["body_top"]
    bore = (cq.Workplane("XY").circle(float(P.GUIDE_BORE) / 2)
            .extrude(top - s["stop_ledge"]).translate((0, 0, s["stop_ledge"])))

    slot_w = float(P.LUG_W) + 2 * float(P.GUIDE_CLEARANCE)
    slot = (cq.Workplane("XY")
            .box(float(P.SLOT_OD), slot_w, top - s["stop_ledge"],
                 centered=(True, True, False))
            .intersect(cq.Workplane("XY").circle(float(P.SLOT_OD) / 2)
                       .extrude(top - s["stop_ledge"]))
            .translate((0, 0, s["stop_ledge"])))
    return bore.union(slot)


def switch_window_cut():
    """The hole under the collar that the switch top housing occupies. BODY coords."""
    s = P.stack()
    w = float(P.SWITCH_WINDOW)
    return (cq.Workplane("XY").box(w, w, s["stop_ledge"] - s["plate_top"],
                                   centered=(True, True, False))
            .translate((0, 0, s["plate_top"])))


def skeleton():
    """Prototype B: the mechanism and nothing else. BODY coords, trimmed to the bay.

    Spec section 25 asks for exactly this before the cosmetic body exists -- a block that
    carries the collar, the stop and the switch mount so the FEEL can be cycled and
    judged. It is a test fixture. It is not Part A, and it does not pretend to be: no
    mouthpiece, no silhouette, no text.
    """
    s = P.stack()
    bot = s["pin_relief_bot"] - float(P.BODY_WALL)
    blk = (cq.Workplane("XY")
           .box(float(P.BODY_WIDTH), float(P.BODY_DEPTH), s["body_top"] - bot,
                centered=(True, True, False))
           .edges("|Z").fillet(float(P.BODY_CORNER_R))
           .translate((0, 0, bot)))
    return (blk.cut(collar_cut())
               .cut(switch_window_cut())
               .cut(switch.mount_cut().translate((0, 0, s["plate_top"]))))


def switch_in_place(pressed=0.0):
    """The switch stand-in, at the height the body mounts it. BODY coords."""
    return switch.switch_solid(pressed).translate((0, 0, P.stack()["plate_top"]))


# ==================================================================== self-test ==
def _vol(shape):
    try:
        return shape.val().Volume()
    except Exception:
        return 0.0


def _overlap(a, b):
    try:
        return _vol(a.intersect(b))
    except Exception:
        return 0.0


def travel_test(steps=9):
    """Press the canister, for real, and report interference at each step."""
    body = skeleton()
    cap0 = canister(printing=False)
    rows = []
    for i in range(steps + 1):
        d = float(P.BUTTON_TRAVEL) * i / steps
        cap = cap0.translate((0, 0, -d))
        rows.append((d, _overlap(cap, body), _overlap(cap, switch_in_place(d))))
    return rows


def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    s = P.stack()
    cap = canister()
    bb = cap.val().BoundingBox()

    t("the canister is the height the stack budgeted for it",
      abs(bb.zlen - s["canister_height"]) < 1e-6,
      f"{bb.zlen:.2f} vs {s['canister_height']:.2f}")
    t("the lugs are the widest thing on it, and only on X",
      abs(bb.xlen - float(P.LUG_OD)) < 1e-6 and abs(bb.ylen - float(P.CANISTER_OD)) < 1e-6,
      f"x {bb.xlen:.2f} y {bb.ylen:.2f}")
    t("exposed height above the body top is what section 3 asked for",
      abs((s["canister_height"] - (s["body_top"] - s["canister_rim_rest"]))
          - float(P.CANISTER_EXPOSED)) < 1e-6)

    # -- the motion ------------------------------------------------------------
    rows = travel_test()
    free = [r for r in rows if r[1] > 1e-6]
    t("the canister travels the full stroke without touching the collar",
      not free,
      "first fouled at " + (f"{free[0][0]:.2f} mm, {free[0][1]:.3f} mm3" if free else "-"))

    t("it never touches the switch housing, at rest or at the stop",
      all(r[2] < 1e-6 for r in rows),
      f"worst {max(r[2] for r in rows):.4f} mm3")

    # Make sure the test can fail: push PAST the stop and the lug must hit the floor.
    over = canister(printing=False).translate((0, 0, -(float(P.BUTTON_TRAVEL) + 0.3)))
    t("pushed past the stop, the lug lands on the slot floor -- the check CAN fail",
      _overlap(over, skeleton()) > 1e-3,
      f"{_overlap(over, skeleton()):.3f} mm3 of interference 0.3 mm past the stop")

    # -- and the printed stop beats the switch's own bottom-out ----------------
    t("the printed stop arrives before the switch bottoms out",
      float(P.BUTTON_TRAVEL) < float(P.MX_TRAVEL),
      f"{float(P.MX_TRAVEL) - float(P.BUTTON_TRAVEL):.2f} mm of margin")

    # -- printability ----------------------------------------------------------
    first = cap.faces("<Z").vals()
    t("the canister prints rim-down on one connected first layer",
      len(first) == 1, f"{len(first)} separate faces on the plate")
    return out


if __name__ == "__main__":
    print("mech -- the canister, the collar, and the press\n")
    results = self_test()
    bad = 0
    for ok, name, detail in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    print("\n  travel, mm    collar overlap    switch overlap")
    for d, a, b in travel_test():
        print(f"  {d:9.2f}    {a:12.4f}    {b:12.4f}")
    print(f"\n  {len(results)} tests, {bad} failures")

    if "--export" in sys.argv:
        out_dir = os.path.join(HERE, "out")
        os.makedirs(out_dir, exist_ok=True)
        for name, shape in (("C_canister", canister()),
                            ("PROTO_B_skeleton", skeleton())):
            cq.exporters.export(shape, os.path.join(out_dir, f"{name}.step"))
            print(f"  wrote out/{name}.step")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
