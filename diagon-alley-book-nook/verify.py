#!/usr/bin/env python3
"""Checks that run against the built kit.

    python3 verify.py

Reads out/manifest.json (so run build.py first) and additionally re-derives the
peg/socket interference maths, which is the one thing a bounding box cannot tell you.
"""
import json
import os
import sys

import cadquery as cq

import params as P
from lib import mount as MT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
FAILS, WARNS = [], []


def fail(msg):
    FAILS.append(msg)
    print("  FAIL  " + msg)


def warn(msg):
    WARNS.append(msg)
    print("  warn  " + msg)


def ok(msg):
    print("  ok    " + msg)


# ------------------------------------------------------------- fit geometry --
def check_fits():
    """The meaningful test: take a REAL part, place it on a REAL wall built from the
    same tables, and measure the interference.

    An abstract peg-vs-socket pair is not enough. The first version of this kit passed
    an abstract check while every keyed pair on the actual wall landed wide-peg-in-
    narrow-hole, because peg and socket were being oriented by opposite conventions.
    """
    print("\n[fit] real parts against a real wall")
    import data.facade as FD
    from parts.decor import build_element, FACE
    from lib.util import batch_cut, batch_add

    cases = [("13A", "P2 keyed pair, sash window"),
             ("19C", "P1 micro peg, wall ornament"),
             ("11A", "T3 tongue, projecting bay")]
    for rid, what in cases:
        rows = [r for r in FD.LEFT if r["id"] == rid]
        if not rows:
            warn(f"{rid} not in the table any more -- skipping")
            continue
        parts, (cuts, adds), _ = build_element(rows[0], "L")
        plate = cq.Workplane("XY").box(FACE, P.CHASSIS_D, P.SCENE_H,
                                       centered=(False, False, False))
        bored = batch_cut(plate, cuts)
        ribbed = batch_add(bored, adds)
        placed = parts[0]["placed"]
        a = bored.intersect(placed)
        b = ribbed.intersect(placed)
        foul = a.val().Volume() if a.val().Solids() else 0.0
        grip = (b.val().Volume() if b.val().Solids() else 0.0) - foul
        if foul > 0.05:
            fail(f"{rid} {what}: part fouls the wall by {foul:.2f} mm^3 -- will not seat")
        elif grip < 0.05 and rid != "11A":
            fail(f"{rid} {what}: no crush-rib grip, the part will fall out")
        else:
            note = "detent retained" if rid == "11A" else f"grip {grip:.2f} mm^3"
            ok(f"{rid} {what}: clears the bore, {note}")


def check_all_mates():
    """Every facade part against the wall it mounts to.

    This is the check that matters. Sampling three parts is how the bay windows shipped
    with their groove on the wrong axis: the samples passed and 8 parts were wrong.
    """
    print("\n[fit] all 119 facade parts against their walls")
    import data.facade as FD
    from parts import walls as WL
    from parts.decor import FACE
    from lib.util import batch_cut

    worst = []
    for side, table in (("L", FD.LEFT), ("R", FD.RIGHT)):
        parts, cuts, adds, _ = WL.collect(side)
        plate = cq.Workplane("XY").box(FACE, P.CHASSIS_D, P.SCENE_H,
                                       centered=(False, False, False))
        bored = batch_cut(plate, cuts)
        for pt in parts:
            inter = bored.intersect(pt["placed"])
            v = inter.val().Volume() if inter.val().Solids() else 0.0
            if v > 0.05:
                worst.append((v, side, pt["id"], pt["name"]))
    if worst:
        for v, side, pid, name in sorted(worst, reverse=True)[:12]:
            fail(f"{pid} {name} fouls its wall by {v:.2f} mm^3")
        if len(worst) > 12:
            fail(f"...and {len(worst)-12} more")
    else:
        ok("all facade parts clear their walls (no interference anywhere)")


def check_keying():
    """A keyed mount must NOT accept its part rotated 180 degrees."""
    print("\n[keying] wrong-way-round rejection")
    plate = cq.Workplane("XY").box(40, 40, 6, centered=(True, True, False))
    for name, peg_fn, sock_fn in (("P1", MT.peg_p1, MT.socket_p1_solids),
                                  ("P2", MT.peg_p2, MT.socket_p2_solids)):
        cut, _ = sock_fn((0, 0, 6), axis="-Z")
        bored = plate.cut(cut)
        right = bored.intersect(peg_fn((0, 0, 6), axis="-Z"))
        vr = right.val().Volume() if right.val().Solids() else 0.0
        flipped = bored.intersect(peg_fn((0, 0, 6), axis="-Z", rot=180))
        vf = flipped.val().Volume() if flipped.val().Solids() else 0.0
        if vr > 0.05:
            fail(f"{name}: correct orientation does not seat ({vr:.2f} mm^3)")
        elif vf < 0.2:
            fail(f"{name}: accepts a 180 deg install -- the key does nothing")
        else:
            ok(f"{name}: seats one way only (wrong way fouls by {vf:.2f} mm^3)")


def check_clearance_sanity():
    print("\n[params] tolerance sanity")
    if P.DECORATIVE_CLEARANCE > P.FIT_CLEARANCE:
        warn("DECORATIVE_CLEARANCE > FIT_CLEARANCE: decorative parts will be looser "
             "than structural ones, which is usually backwards")
    if P.CRUSH_INTERFERENCE > 0.30:
        warn(f"CRUSH_INTERFERENCE {P.CRUSH_INTERFERENCE} is a lot of material to shear "
             "-- parts will need real force")
    if P.CRUSH_INTERFERENCE < 0.06:
        warn(f"CRUSH_INTERFERENCE {P.CRUSH_INTERFERENCE} may not grip once painted")
    if P.LEAD_IN_CHAMFER <= 0:
        fail("LEAD_IN_CHAMFER is 0: sockets will be undersize after elephant's foot "
             "and the kit will not assemble")
    else:
        ok(f"lead-in {P.LEAD_IN_CHAMFER}, clearances "
           f"{P.FIT_CLEARANCE}/{P.DECORATIVE_CLEARANCE}, "
           f"rib bite {P.CRUSH_INTERFERENCE}")


def check_light_block():
    print("\n[light] emitter concealment")
    solid_left = P.WALL_FACE_T - 0.0
    if P.BEAD_POCKET_D > P.WALL_SERVICE_D:
        fail(f"bead pocket {P.BEAD_POCKET_D} deeper than the rib {P.WALL_SERVICE_D}")
    else:
        ok(f"bead pocket {P.BEAD_POCKET_D} fits the {P.WALL_SERVICE_D} rib")
    if P.WIRE_CHANNEL_DEPTH > P.WALL_SERVICE_D - 1.0:
        fail("wire channel is too deep for the service rib")
    else:
        ok(f"wire channel {P.WIRE_CHANNEL_WIDTH}x{P.WIRE_CHANNEL_DEPTH} fits the rib")
    if P.RIB_GAP < MT.P2_L - P.WALL_FACE_T:
        fail(f"RIB_GAP {P.RIB_GAP} is smaller than the {MT.P2_L - P.WALL_FACE_T:.1f} mm "
             "a peg protrudes behind the wall plate -- pegs will foul the rib")
    else:
        ok(f"RIB_GAP {P.RIB_GAP} clears the {MT.P2_L - P.WALL_FACE_T:.1f} mm peg overhang")


def check_envelope():
    print("\n[envelope] the numbers hang together")
    tot = P.PLINTH_HEIGHT + P.CASE_CAVITY_H + P.SHELL_THICKNESS
    if abs(tot - P.BOOKNOOK_HEIGHT) > 0.01 + (P.TOP_PLENUM_H if P.SKY_PUCK_TOP else 0):
        fail(f"heights do not add up: {tot:.1f} vs {P.BOOKNOOK_HEIGHT}")
    else:
        ok(f"height {P.BOOKNOOK_HEIGHT} = plinth {P.PLINTH_HEIGHT} + cavity "
           f"{P.CASE_CAVITY_H:.1f} + top {P.SHELL_THICKNESS}")
    if P.ALLEY_W_REAR >= P.ALLEY_W_FRONT:
        fail("the alley does not narrow toward the rear -- no perspective cant")
    else:
        ok(f"alley narrows {P.ALLEY_W_FRONT:.1f} -> {P.ALLEY_W_REAR:.1f}")
    if P.CHASSIS_W + 2 * P.SLIP_CLEARANCE > P.CASE_CAVITY_W + 0.01:
        fail("chassis will not slide into the case")
    else:
        ok(f"chassis {P.CHASSIS_W:.1f} slides into cavity {P.CASE_CAVITY_W:.1f}")


def check_grip_across_clearances():
    """Retention must survive the user actually changing the clearance.

    The tolerance coupon invites setting FIT_CLEARANCE anywhere from 0.20 to 0.35. With
    a fixed-height crush rib measured from the bore wall, everything at or above 0.30
    had ZERO grip and every part in the kit would have fallen out -- silently, because
    the geometry is still perfectly valid.
    """
    print("\n[fit] crush-rib grip across the usable clearance range")
    real = (P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE)
    try:
        for v in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
            P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
            plate = cq.Workplane("XY").box(30, 30, 6, centered=(True, True, False))
            c1, r1 = MT.socket_p1_solids((0, 8, 6), axis="-Z")
            c2, r2 = MT.socket_p2_solids((0, -6, 6), axis="-Z")
            bored = plate.cut(c1).cut(c2)
            ribbed = bored.union(r1).union(r2)
            pegs = MT.peg_p1((0, 8, 6), axis="-Z").union(MT.peg_p2((0, -6, 6), axis="-Z"))
            f = bored.intersect(pegs)
            g = ribbed.intersect(pegs)
            fv = f.val().Volume() if f.val().Solids() else 0.0
            gv = (g.val().Volume() if g.val().Solids() else 0.0) - fv
            if fv > 0.05:
                fail(f"clearance {v:.2f}: peg fouls the bore by {fv:.2f} mm^3")
            elif gv < 0.30:
                fail(f"clearance {v:.2f}: grip is only {gv:.2f} mm^3 -- parts fall out")
            else:
                ok(f"clearance {v:.2f}: clears the bore, grip {gv:.2f} mm^3")
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real


def check_paint_handles():
    """The paint handles must RECEIVE a part's peg. The first version had a peg on top,
    which cannot mate with a part that also has a peg -- an easy thing to ship without
    noticing, because it looks right."""
    print("\n[jigs] paint handles accept a real part's peg")
    real = P.DECORATIVE_CLEARANCE
    P.DECORATIVE_CLEARANCE = real + 0.12
    try:
        for name, sock, peg, L in (("P1", MT.socket_p1_solids, MT.peg_p1, MT.P1_L),
                                   ("P2", MT.socket_p2_solids, MT.peg_p2, MT.P2_L)):
            blk = cq.Workplane("XY").box(20, 20, 8, centered=(True, True, False))
            bored = blk.cut(sock((0, 0, 8), axis="-Z", depth=L + 0.4)[0])
            i = bored.intersect(peg((0, 0, 8), axis="-Z"))
            v = i.val().Volume() if i.val().Solids() else 0.0
            if v > 0.05:
                fail(f"paint handle rejects a {name} part (interference {v:.2f} mm^3)")
            else:
                ok(f"{name} parts drop into the paint handle and lift back out")
    finally:
        P.DECORATIVE_CLEARANCE = real


def check_manifest():
    print("\n[build] manifest")
    path = os.path.join(OUT, "manifest.json")
    if not os.path.exists(path):
        warn("no manifest.json -- run build.py first")
        return
    rep = json.load(open(path))
    bad = [r for r in rep if r.get("status") != "ok"]
    big = [r for r in rep if r.get("status") == "ok" and not r.get("fits_bed")]
    multi = [r for r in rep if r.get("status") == "ok" and r.get("solids", 1) != 1]
    thin = [r for r in rep if r.get("status") == "ok"
            and min(r.get("bbox", [9, 9, 9])) < 0.8]
    for r in bad:
        fail(f"{r['id']} {r['name']} failed to build")
    for r in big:
        fail(f"{r['id']} {r['name']} {r['bbox']} does not fit the "
             f"{P.BED_X:.0f}x{P.BED_Y:.0f}x{P.BED_Z:.0f} bed")
    for r in multi:
        fail(f"{r['id']} {r['name']} exported {r['solids']} disconnected solids")
    for r in thin:
        warn(f"{r['id']} {r['name']} has a {min(r['bbox'])} mm dimension -- check it "
             f"is not below one nozzle width")
    if not (bad or big or multi):
        ok(f"{len(rep)} parts, all single-solid and all inside the build volume")
    total = sum(r.get("grams", 0) for r in rep if r.get("status") == "ok")
    print(f"        {total:.0f} g PLA total across {len(rep)} parts")


if __name__ == "__main__":
    print("Crooked Lane Book Nook -- verification")
    check_clearance_sanity()
    check_envelope()
    check_light_block()
    check_keying()
    check_fits()
    check_all_mates()
    check_grip_across_clearances()
    check_paint_handles()
    check_manifest()
    print(f"\n{len(FAILS)} failures, {len(WARNS)} warnings")
    sys.exit(1 if FAILS else 0)
