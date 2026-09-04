#!/usr/bin/env python3
"""Checks that run against the built kit.

    python3 verify.py

Reads out/manifest.json (so run build.py first) and additionally re-derives the
peg/socket interference maths, which is the one thing a bounding box cannot tell you.
"""
import json
import os
import sys

import math

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


def _vol(wp):
    return wp.val().Volume() if wp.val() and wp.val().Solids() else 0.0


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
        # Grip is now a T3 question only. P1 and P2 are glued locators with no ribs and
        # nothing to grip with, by decision and not by accident: docs/09_COUPON_RESULTS.
        # Demanding grip of them here would fail the kit for being built as designed --
        # which is what this check did the moment the clearance changed. What P1 and P2
        # owe is the opposite: enter with nothing fouling and leave a gap for glue.
        ribbed_joint = rid == "11A"
        if foul > 0.05:
            fail(f"{rid} {what}: part fouls the wall by {foul:.2f} mm^3 -- will not seat")
        elif ribbed_joint and grip < 0.05:
            fail(f"{rid} {what}: no crush-rib grip, the part will fall out")
        elif ribbed_joint:
            ok(f"{rid} {what}: clears the bore, grip {grip:.2f} mm^3")
        else:
            ok(f"{rid} {what}: enters clean, glued -- {grip:.2f} mm^3 of rib (expected 0)")


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
    """A keyed mount must NOT accept its part rotated 180 degrees -- at ANY clearance.

    The sweep is the point. P1's key is a flat chord, and turned the wrong way round the
    peg presents its arc at P1_D/2 where the bore presents its flat at P1_FLAT +
    clearance: the key works only while the second is smaller than the first. With the
    old 1.0 mm flat that stopped being true at 0.20, so the kit's 0.25 had a P1 that
    keyed nothing, and it took raising the clearance to 0.30 for anything to say so.
    A check that only ever looks at today's number cannot see a cliff one step away.
    """
    print("\n[keying] wrong-way-round rejection")
    real = (P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE)
    plate = cq.Workplane("XY").box(40, 40, 6, centered=(True, True, False))
    sweep = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
    try:
        for name, peg_fn, sock_fn in (("P1", MT.peg_p1, MT.socket_p1_solids),
                                      ("P2", MT.peg_p2, MT.socket_p2_solids)):
            here, cliff = None, None
            for v in sweep:
                P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
                cut, _ = sock_fn((0, 0, 6), axis="-Z")
                bored = plate.cut(cut)
                right = bored.intersect(peg_fn((0, 0, 6), axis="-Z"))
                vr = right.val().Volume() if right.val().Solids() else 0.0
                flipped = bored.intersect(peg_fn((0, 0, 6), axis="-Z", rot=180))
                vf = flipped.val().Volume() if flipped.val().Solids() else 0.0
                if vr > 0.05:
                    fail(f"{name} @ {v:.2f}: correct orientation does not seat "
                         f"({vr:.2f} mm^3)")
                    continue
                if vf < 0.2 and cliff is None:
                    cliff = v
                if abs(v - real[1]) < 1e-9:
                    here = vf
            if here is None:
                warn(f"{name}: FIT_CLEARANCE {real[1]} is not in the swept range")
            elif here < 0.2:
                fail(f"{name}: accepts a 180 deg install at the configured "
                     f"{real[1]:.2f} -- the key does nothing")
            else:
                last = max(v for v in sweep if cliff is None or v < cliff)
                ok(f"{name}: seats one way only at {real[1]:.2f} (wrong way fouls by "
                   f"{here:.2f} mm^3); the key stops working above {last:.2f}")
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real


MIN_TEXT_SIZE = 3.5    # a bold serif stem is ~0.12 of the glyph size; below this the
                       # stems are under one 0.42 mm extrusion and print as mush


def check_sign_text():
    """Sign lettering must be RAISED, land face UP on the bed, and be big enough to print.

    Three ways a sign can carry text nobody can read, and the kit had all three.

    RAISED: text sunk into a plate that will be painted fills with paint and disappears.
    lib.sign embosses, and this checks it still adds material rather than cutting it.

    FACE UP: signs used to print ("X", 180) -- "face down, pegs up" -- which laid every
    raised letter on the bed to be squashed flat and elephant-footed. The peg is a
    socket and a loose pin now, so the plate lies back-down and the letters stand up.

    BIG ENOUGH: the forced perspective scales a rear plate to 0.6, and the fitter then
    shrinks the type to keep it inside the plate. Eight of the kit's twelve signs were
    sized between 1.97 and 3.05 mm, which on a 0.4 mm nozzle is not lettering.
    """
    print("\n[signs] lettering is raised, faces up, and is big enough to print")
    import build as B
    import data.facade as F
    from parts import kit as KT
    from lib.sign import _fit_size

    EFF = {"swing": 0.86, "shield": 1.0, "lozenge": 0.8, "arrow": 0.72,
           "fasciaplate": 0.94}
    for r in F.SIGNS:
        txt = r.get("text", "")
        if not txt:
            continue
        sc = F.wpersp(r["u"]) if r.get("side") else 1.0
        w, h = r["w"] * sc, r["h"] * sc
        if r["kind"] == "banner":
            size = min(w * 0.62, h / (len(txt) + 0.4) * 0.82)
        else:
            size = _fit_size(txt, w * EFF[r["kind"]],
                             h * 0.7 if r["kind"] == "shield" else h)
        if size < MIN_TEXT_SIZE:
            fail(f"{r['id']} {r['name']}: {txt!r} comes out at {size:.2f} mm on a "
                 f"{w:.1f} x {h:.1f} plate -- under {MIN_TEXT_SIZE}, the stems are "
                 "thinner than one extrusion. Shorten it or widen the plate.")

    rows = {m["id"]: m for m in B.manifest()}
    for it in KT.signs():
        row = next(r for r in F.SIGNS if r["id"] == it["id"])
        if not row.get("text"):
            continue
        m = rows[it["id"]]
        # No rule about WHICH rotation -- a flat sign needs none, a sign fused into its
        # bracket's plane needs a quarter turn to lie down. The rule is about where the
        # letters end up, and that is measured below rather than asserted here.
        real = P.RENDER_TEXT
        try:
            P.RENDER_TEXT = False
            blank = KT._sign_part(row)
        finally:
            P.RENDER_TEXT = real
        lettered = it["solid"]
        dv = lettered.val().Volume() - blank.val().Volume()
        if dv <= 0.05:
            fail(f"{it['id']}: text removes {-dv:.2f} mm^3 -- it is engraved, not raised")
            continue
        # BOTH have to be carried into the print orientation. Measuring the letters in
        # the part frame and the part on the bed compares two different spaces, and it
        # passed every flat sign (whose print_rot is None, where the two spaces are the
        # same) while calling the rotated ones face-down whichever way they turned.
        rot = m["print_rot"]
        printed = B.print_orient(lettered, rot)
        dz = -printed.val().BoundingBox().zmin
        pb = printed.translate((0, 0, dz)).val().BoundingBox()
        ab = B.print_orient(lettered.cut(blank), rot).translate((0, 0, dz)) \
              .val().BoundingBox()
        # The letters need not be the highest thing on the plate -- the banner's side
        # rails stand 0.6 proud of its face on purpose, and lettering in that channel is
        # protected rather than wrong. What matters is that they are not on the bed.
        if pb.zmax - ab.zmax > 1.0:
            warn(f"{it['id']}: the lettering sits {pb.zmax - ab.zmax:.2f} mm below the "
                 "top of the plate -- check nothing is standing over it")
        if ab.zmin < 0.2:
            fail(f"{it['id']}: the lettering reaches the bed -- it prints face down")
        else:
            ok(f"{it['id']}: {dv:.1f} mm^3 raised, standing {ab.zmax - ab.zmin:.1f} mm "
               f"proud, text up")


def check_sign_hanging():
    """A hanging sign has to be assemblable after it is printed.

    This is the check that was missing when three of the kit's most visible parts --
    the Ollivanders, Eeylops and Scribbulus swing signs -- had no way to attach to
    anything. Their plates carry two closed eyes, the brackets carry a closed eye, and
    the chain between them is printed with closed end links. Three closed rings cannot
    be threaded together once they exist, and nothing in this file looked.

    So: the hook must be OPEN, its wire must pass both eyes with clearance, and the
    printed chain -- which is a decorative prop, not a working chain -- must not be
    mistaken for the thing that carries the sign.
    """
    print("\n[signs] a hanging sign can actually be hung")
    import lib.sign as SG

    hook = SG.s_hook()
    n = len(hook.val().Solids())
    ring = (cq.Workplane("XY").circle(2.7 + SG.HOOK_WIRE / 2).extrude(SG.HOOK_WIRE)
            .cut(cq.Workplane("XY").circle(2.7 - SG.HOOK_WIRE / 2)
                 .extrude(SG.HOOK_WIRE)))
    if n != 1:
        fail(f"the hook is {n} solids")
    elif hook.val().Volume() >= ring.val().Volume() - 0.05:
        fail("the hook is a CLOSED ring -- it cannot be sprung into an eye")
    else:
        ok(f"hook is open, {SG.HOOK_WIRE} mm wire, "
           f"{ring.val().Volume() - hook.val().Volume():.1f} mm^3 of mouth cut out")

    slack = SG.EYE_HOLE - SG.HOOK_WIRE
    if slack < 0.6:
        fail(f"eye {SG.EYE_HOLE} takes {SG.HOOK_WIRE} wire with only {slack:.2f} mm "
             "spare -- it will not pass")
    else:
        ok(f"eye {SG.EYE_HOLE} mm passes {SG.HOOK_WIRE} mm wire with {slack:.2f} to spare")

    # A swing sign is FUSED to its bracket now and hangs by neither eye nor hook, so
    # what has to be true of it is different: one solid, and two wall pegs, because a
    # sign on the end of an arm is a cantilever and one peg is a hinge.
    import data.facade as F
    from parts import kit as KT
    for it in KT.signs():
        row = next(r for r in F.SIGNS if r["id"] == it["id"])
        if row["kind"] != "swing" or not row.get("bracket"):
            continue
        n = len(it["solid"].val().Solids())
        if n != 1:
            fail(f"{it['id']} {it['name']}: {n} disconnected solids -- a peg or the "
                 "plate is not touching the arm")
        else:
            ok(f"{it['id']} {it['name']}: one solid, fused to its bracket")
    for it in KT.brackets():
        if not it["id"].startswith("31"):
            continue
        n = len(it["solid"].val().Solids())
        if n != 1:
            fail(f"{it['id']} {it['name']}: {n} disconnected solids")
        else:
            ok(f"{it['id']} {it['name']}: one solid")


def check_clearance_sanity():
    print("\n[params] tolerance sanity")
    if P.DECORATIVE_CLEARANCE > P.FIT_CLEARANCE:
        warn("DECORATIVE_CLEARANCE > FIT_CLEARANCE: decorative parts will be looser "
             "than structural ones, which is usually backwards")
    # CRUSH_INTERFERENCE reaches only T3 now: P1 and P2 are glued locators with no ribs.
    if P.CRUSH_INTERFERENCE > 0.30:
        warn(f"CRUSH_INTERFERENCE {P.CRUSH_INTERFERENCE} is a lot of material for a T3 "
             "tongue to shear -- it will need real force to slide")
    if P.CRUSH_INTERFERENCE < 0.06:
        warn(f"CRUSH_INTERFERENCE {P.CRUSH_INTERFERENCE} may not hold a T3 once painted")
    if P.LEAD_IN_CHAMFER <= 0:
        fail("LEAD_IN_CHAMFER is 0: sockets will be undersize after elephant's foot "
             "and the kit will not assemble")
    else:
        ok(f"lead-in {P.LEAD_IN_CHAMFER}, press/decorative/slide clearances "
           f"{P.FIT_CLEARANCE}/{P.DECORATIVE_CLEARANCE}/{P.T3_CLEARANCE}, "
           f"T3 rib bite {P.CRUSH_INTERFERENCE}")
    if P.T3_CLEARANCE < P.FIT_CLEARANCE:
        warn(f"T3_CLEARANCE {P.T3_CLEARANCE} is tighter than FIT_CLEARANCE "
             f"{P.FIT_CLEARANCE} -- a joint you slide should not be tighter than one "
             "you press")


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


def check_assembled_envelope():
    """Does the built chassis fit inside the built case?

    Not the same question as "do the numbers add up". CASE_CAVITY_H is DEFINED as
    BOOKNOOK_HEIGHT - PLINTH_HEIGHT - SHELL_THICKNESS, so comparing the two compared a
    value with its own definition and could never fail.

    Nor is it "how big is the bounding box", which is what this check asked next and
    got wrong twice. The chassis datum is the plane it SITS on, not the lowest point of
    any part: the base pan's dovetail feet drop 3 mm below it into the plinth's rails,
    and counting those made a chassis that fits by 0.12 mm look 2.9 mm too tall. The
    front is open -- it is the nook's opening -- so a cornice reaching forward of the
    front plane is not a collision either, and counting that made the depth look 2.8 mm
    over. Both were the measurement, not the model.

    So: measure height and depth from the datums, and ask about anything below the
    seating plane or proud of the front separately, where the answer is legible.
    """
    print("\n[envelope] the assembled chassis against the case cavity")
    try:
        rows = json.load(open(os.path.join(OUT, "manifest.json")))
    except Exception:
        warn("no out/manifest.json -- run build.py first")
        return
    boxes = [(r, r["place_bbox"]) for r in rows
             if r.get("group") != "case" and r.get("place_bbox")]
    if not boxes:
        warn("manifest has no placed bounding boxes -- rebuild with the current build.py")
        return

    # the pan's feet are the only thing meant to sit below the seating plane
    FEET = {"00"}
    top = max(b[5] for _, b in boxes)
    tallest = max(((r["name"], b[5]) for r, b in boxes), key=lambda t: t[1])[0]
    rear = max(b[4] for _, b in boxes)
    deepest = max(((r["name"], b[4]) for r, b in boxes), key=lambda t: t[1])[0]
    xlo = min(b[0] for _, b in boxes)
    xhi = max(b[3] for _, b in boxes)
    widest = max(((r["name"], max(b[3] - P.CHASSIS_W, -b[0])) for r, b in boxes),
                 key=lambda t: t[1])[0]

    for what, got, room, who in (("height", top, P.CASE_CAVITY_H, tallest),
                                 ("depth", rear, P.CASE_CAVITY_D, deepest),
                                 ("width", xhi - xlo, P.CASE_CAVITY_W, widest)):
        if got > room + 0.01:
            fail(f"chassis {what} {got:.1f} exceeds the {room:.1f} cavity by "
                 f"{got - room:.1f} mm -- the case will not close ({who})")
        else:
            ok(f"chassis {what} {got:.1f} fits the {room:.1f} cavity "
               f"({room - got:.1f} mm spare)")

    below = [(r["name"], b[2]) for r, b in boxes if b[2] < -0.01 and r["id"] not in FEET]
    if below:
        for name, z in sorted(below, key=lambda t: t[1]):
            fail(f"{name} drops {-z:.1f} mm below the plinth top and is not a foot "
                 "-- nothing is cut away for it")
    else:
        ok("nothing but the base pan's feet sits below the plinth top")

    proud = [(r["name"], b[1]) for r, b in boxes if b[1] < -0.01]
    if proud:
        for name, y in sorted(proud, key=lambda t: t[1])[:4]:
            warn(f"{name} stands {-y:.1f} mm proud of the front plane -- the opening is "
                 "open so it will not foul, but check it against the bezel")


GLUE_GAP_MIN, GLUE_GAP_MAX = 0.15, 0.45     # per side, for a gel CA joint


def check_glue_gap_across_clearances():
    """P1 and P2 are glued locators, so what matters is that they always go together.

    This check used to demand crush-rib GRIP at every clearance, because the kit used
    to rely on an interference fit. Two printed coupons ended that: a fixed clearance
    cannot beat this printer's socket-to-socket scatter -- seven identical sockets, three
    held and four dropped -- and ribs beat it far too well, giving a P1 joint that could
    not be pulled apart and a P2 joint that would not go together.

    So the requirement is now the opposite of grip. At every clearance anyone might set,
    the peg must enter its bore with NOTHING fouling, and the annulus left around it must
    be a gap a gel cyanoacrylate can actually bridge: too tight and the glue is scraped
    off on the way in, too loose and the part floats while it sets.
    """
    print("\n[fit] the glued locator goes together across the usable clearance range")
    real = (P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE)
    try:
        for v in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
            P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
            plate = cq.Workplane("XY").box(30, 30, 6, centered=(True, True, False))
            c1, _r1 = MT.socket_p1_solids((0, 8, 6), axis="-Z")
            c2, _r2 = MT.socket_p2_solids((0, -6, 6), axis="-Z")
            bored = plate.cut(c1).cut(c2)
            pegs = MT.peg_p1((0, 8, 6), axis="-Z").union(MT.peg_p2((0, -6, 6), axis="-Z"))
            f = bored.intersect(pegs)
            fv = f.val().Volume() if f.val().Solids() else 0.0
            if fv > 0.05:
                fail(f"clearance {v:.2f}: peg fouls the bore by {fv:.2f} mm^3 -- "
                     "it will not go in")
            elif not GLUE_GAP_MIN <= v <= GLUE_GAP_MAX:
                warn(f"clearance {v:.2f} is outside the {GLUE_GAP_MIN}-{GLUE_GAP_MAX} mm "
                     "a gel CA joint wants per side")
            else:
                ok(f"clearance {v:.2f}: enters clean, {v:.2f} mm of glue gap per side")
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real


def check_coupon_tab_flips():
    """The REAL tab, turned over, seated in the REAL coupon.

    Two things have to hold: nothing proud of the coupon surface may hold the tab off,
    and the crush ribs must still bite. This check used to rebuild a bare plate from
    the same numbers instead of using the generated coupon, and so never saw the raised
    station labels -- which sat squarely under the middle of the tab and held it 0.5 mm
    off the surface. Reconstructing the part you are testing is not testing the part.
    """
    print("\n[jigs] real tab, turned over, seated in the real coupon")
    if abs(MT.TAB_PITCH - MT.COUPON_STATION_W) > 1e-6:
        fail(f"tab pitch {MT.TAB_PITCH} does not match station pitch "
             f"{MT.COUPON_STATION_W} -- the tabs will drift out of their holes")
    else:
        ok(f"tab pitch matches the station pitch ({MT.TAB_PITCH} mm)")

    coupon, _ = MT.tolerance_coupon()
    proud = (cq.Workplane("XY").box(400, 80, 10, centered=(False, False, False))
             .translate((0, -20, MT.COUPON_T)))
    above = coupon.intersect(proud)
    has_proud = bool(above.val().Solids())

    for i, v in enumerate(MT.COUPON_VALUES):
        seated = MT.seat_tab(i)
        blocked = above.intersect(seated) if has_proud else None
        bv = blocked.val().Volume() if blocked and blocked.val().Solids() else 0.0
        whole = coupon.intersect(seated)
        wv = whole.val().Volume() if whole.val().Solids() else 0.0
        grip = wv - bv
        if bv > 0.02:
            fail(f"station {v:.2f}: {bv:.2f} mm^3 of raised material holds the tab off "
                 "the surface -- it cannot seat flush")
        elif grip < 0.3:
            fail(f"station {v:.2f}: no crush-rib grip ({grip:.2f} mm^3)")
        else:
            ok(f"station {v:.2f}: seats flush, crush-rib grip {grip:.2f} mm^3")


def check_joint_coupon():
    """Parts 74A/74B: seat every loose piece against the REAL block and measure.

    This check exists because both joints it covers were broken and looked fine:

      * C4 was a clip lying in a rectangular pocket 0.5 mm bigger than itself in every
        direction. Seated, and pulled back 0.4, 1.0 and 2.0 mm, it intersected the
        catch in 0.000 mm^3 every time. Its barb's ramp was on the tip as well, so it
        could not have been pushed in even if there had been something to catch on.
      * T3 relied on a detent whose pocket was cut at ball radius PLUS the full
        clearance, so the ball dropped in with 0.25 mm of slop. Peak withdrawal
        interference: 0.008 mm^3, against the ~1.8 mm^3 a P1 crush rib gives.

    So the test is not "does it fit" -- both of them fitted beautifully. It is "does
    anything touch anything when you pull it back out".
    """
    print("\n[jigs] joint coupon: T3 and C4 seated in the real block")
    block = MT.joint_coupon()
    proud = (cq.Workplane("XY").box(400, 200, 60, centered=(False, False, False))
             .translate((-50, -20, MT.JC_T)))
    above = block.intersect(proud)

    for i, (kind, v) in enumerate(MT.JC_STATIONS):
        piece = MT.jc_piece(i)
        seated = _vol(block.intersect(piece))
        if kind == "T3":
            # everything proud of the block face, minus the groove ribs the tongue is
            # meant to bite: a label under the tab would hold it off, as one did before
            fins = _vol(above.intersect(piece))
            if fins > 0.02:
                fail(f"T3 {v:.2f}: {fins:.2f} mm^3 of raised material under the tab")
            elif seated < 0.30:
                fail(f"T3 {v:.2f}: no crush-rib grip ({seated:.3f} mm^3)")
            else:
                ok(f"T3 {v:.2f}: seats flush, crush-rib grip {seated:.2f} mm^3")
        else:
            back = _vol(block.intersect(piece.translate((0, 0, 1.0))))
            snap = _vol(block.intersect(piece.translate((0, 0, 3.0))))
            if seated > 0.05:
                fail(f"C4 {v:.2f}: will not seat (interference {seated:.2f} mm^3)")
            elif snap < 0.20:
                fail(f"C4 {v:.2f}: the barb never deflects on the way in "
                     f"({snap:.3f} mm^3) -- it is sliding into a hole, not snapping")
            elif back < 0.50:
                fail(f"C4 {v:.2f}: nothing holds it in -- pulling back 1 mm gives "
                     f"{back:.3f} mm^3 of interference")
            else:
                ok(f"C4 {v:.2f}: snaps in (deflection {snap:.2f} mm^3), holds "
                   f"{back:.2f} mm^3 against a 1 mm pull")


def check_t3_grip():
    """T3 is what holds every wall face to its rib. It must grip like P1 and P2 do."""
    print("\n[fit] T3 crush-rib grip across the usable clearance range")
    real = P.T3_CLEARANCE
    try:
        for v in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
            P.T3_CLEARANCE = v
            plate = cq.Workplane("XY").box(40, 20, 8, centered=(True, True, False))
            cut, ribs = MT.groove_t3_solids((0, 0, 8), 24.0, axis="-Z")
            plate = plate.cut(cut).union(ribs)
            tongue = MT.tongue_t3((0, 0, 0), 24.0, axis="-Z")
            child = (cq.Workplane("XY").box(30, 14, 3, centered=(True, True, False))
                     .union(tongue).translate((0, 0, 8)))
            g = _vol(plate.intersect(child))
            if g < 0.30:
                fail(f"T3 at clearance {v:.2f}: grip {g:.3f} mm^3 -- nothing holds it")
            else:
                ok(f"T3 at clearance {v:.2f}: grip {g:.2f} mm^3")
    finally:
        P.T3_CLEARANCE = real


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


def check_unsupported_relief():
    """Surface relief must not hang over a hole.

    Bricks are up to 18 mm long and the torn front edge and the window apertures both
    remove the plate underneath them. Judged by their centres, bricks half over the
    void were kept and printed as floating cantilevers -- 147 mm^2 of them, which the
    slicer flagged and the geometry checks did not, because a cantilever is perfectly
    valid geometry.
    """
    print("\n[print] relief is not left hanging over a hole")
    import numpy as np
    import build as B
    from parts import walls as WL

    for side in ("L", "R"):
        w = B.drop_to_bed(B.print_orient(WL.wall_face(side), ("Y", -90)))
        v, t = w.val().tessellate(0.08)
        V = np.array([[p.x, p.y, p.z] for p in v])
        tri = V[np.array(t)]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        ln = np.linalg.norm(nrm, axis=1)
        ln[ln == 0] = 1.0
        area = 0.5 * ln
        zc = tri[:, :, 2].mean(axis=1)
        # relief sits above the plate; anything there facing down is over a void
        floating = ((nrm / ln[:, None])[:, 2] < -0.5) & (zc > P.WALL_FACE_T - 0.1)
        a = area[floating].sum()
        if a > 10.0:
            fail(f"{side} wall: {a:.1f} mm^2 of brick relief hangs over a void")
        elif a > 3.0:
            warn(f"{side} wall: {a:.1f} mm^2 of relief overhangs -- check the torn edge")
        else:
            ok(f"{side} wall: {a:.2f} mm^2 of relief over a void (nothing to support)")


def check_facade_seating():
    """Nothing that mounts on a wall may land on the brick relief.

    A facade part seats on the 2.5 mm plate; the brick is 0.6 mm of relief on top of
    that. A part whose footprint oversails its aperture -- which is all of them, on
    purpose, because a window frame has to lap the hole it covers -- comes down on that
    relief unless the relief is cut away underneath it, and then it rocks on a brick
    instead of sitting on the plate. Nothing in the geometry is invalid, and the part
    simply will not go on.

    That was 20 of the 49 parts touching the left wall, from 0.4 mm^3 under a window
    frame to 48.8 under the rear cornice, and it was found by hand after 13A would not
    seat. Seating matters more now than it did: with the mounts glued rather than
    pressed, the back face against the plate is what holds a part square, not the peg.
    """
    print("\n[fit] facade parts seat on the plate, not on the brick")
    import cadquery as cq
    from parts import walls as WL
    from parts.decor import FACE

    relief = (cq.Workplane("XY").box(2.0, 400.0, 400.0, centered=(False, True, True))
              .translate((FACE, 100.0, 100.0)))
    for side in ("L", "R"):
        wall = WL.wall_face(side)
        parts, _, _, _ = WL.collect(side)
        bad, n = [], 0
        for pt in parts:
            hit = wall.intersect(pt["placed"])
            if not hit.val().Solids():
                continue
            n += 1
            v = _vol(hit.intersect(relief))
            if v > 0.05:
                bad.append((v, pt["id"], pt["name"]))
        for v, pid, nm in sorted(bad, reverse=True):
            fail(f"{pid} {nm}: {v:.2f} mm^3 of it lands on brick relief -- it will rock "
                 "on the brick instead of seating on the plate")
        if not bad:
            ok(f"{side} wall: all {n} parts that touch it seat on the plate")


MOUNT_CLEAR = 1.0     # wall material a socket needs on every side of it


def check_mount_crowding():
    """A wall socket must be on bare wall, not under the part next door.

    Signs, brackets, lanterns and the wall-hung props get their sockets from one table
    of (u, z) coordinates, and the facade elements get their apertures and sockets from
    another. Nothing ever compared the two. Every one of them is a hole in the same
    wall face, so a sign bracket placed a couple of millimetres from a window ends up
    with its socket UNDER the window frame: the frame covers it, the bracket has
    nothing to reach, and neither part is wrong on its own.

    Found from a photograph -- a printed tile with the 13A frame laid in it and one
    round hole disappearing under the frame's edge, which is bracket 31A's. It was 21
    mounts out of 21, on both walls, and nothing in this file could see it because the
    sockets had no owner: kit.py built them in a loop that returned bare solids. They
    come from kit.wall_mount_rows now, which names each one.

    The margin is what a socket needs to be a socket: MOUNT_CLEAR of wall on every side
    of the 3.9 mm bore, so its wall is not the last 0.3 mm before an aperture.
    """
    print("\n[fit] wall sockets sit on bare wall")
    from parts import walls as WL
    from parts import kit as K

    for side in ("L", "R"):
        placed, _c, _a, _b = WL.collect(side)
        parts = [(p["id"], p["name"], p["placed"].val().BoundingBox()) for p in placed]
        mounts = []
        for kind, row, _rot, offsets in K.wall_mount_rows(side):
            for i, (du, dz) in enumerate(offsets):
                tag = row["id"] if len(offsets) == 1 else f"{row['id']}.{i + 1}"
                mounts.append((kind, tag, row.get("name", ""),
                               row["u"] + du, row.get("z", 20.0) + dz))

        def gap(u, z, bb):
            dy = max(u - 1.95 - bb.ymax, bb.ymin - u - 1.95, 0.0)
            dz = max(z - 1.95 - bb.zmax, bb.zmin - z - 1.95, 0.0)
            return (dy * dy + dz * dz) ** 0.5

        bad = 0
        for kind, mid, mname, u, z in mounts:
            for pid, pname, bb in parts:
                g = gap(u, z, bb)
                if g >= MOUNT_CLEAR:
                    continue
                bad += 1
                where = "sits under" if g == 0.0 else f"is {g:.2f} mm from"
                fail(f"{side}: {kind} {mid} {mname}'s socket at u={u:.0f} z={z:.0f} "
                     f"{where} {pid} {pname} -- nothing can mount there")
        for i in range(len(mounts)):
            for j in range(i + 1, len(mounts)):
                _, ai, an, au, az = mounts[i]
                _, bi, bn, bu, bz = mounts[j]
                if abs(au - bu) < 3.9 + MOUNT_CLEAR and abs(az - bz) < 3.9 + MOUNT_CLEAR:
                    bad += 1
                    fail(f"{side}: {ai} {an} and {bi} {bn} share one socket at "
                         f"u={au:.0f} z={az:.0f} -- two pegs, one hole")
        if not bad:
            ok(f"{side} wall: all {len(mounts)} hung mounts have bare wall around them")


def check_hung_clearance():
    """A sign moved to clear its SOCKET must still clear the parts around its BODY.

    check_mount_crowding()
    check_hung_clearance() compares 3.9 mm holes. A sign is a 30 mm plate on a bracket
    that reaches 15 mm into the alley, and the wall it hangs on carries a bay window
    that projects 13 and an oriel that projects 10. Move a socket up to find bare wall
    and the plate it carries can arrive inside the oriel, with the geometry still
    perfectly valid and the check still green.

    So this is the second half of the mount pass: every hung part, placed where its row
    puts it, against every facade part on that wall.
    """
    print("\n[fit] hung parts clear the facade they hang on")
    from parts import walls as WL
    from parts import kit as KT
    from parts.decor import to_wall

    for side in ("L", "R"):
        placed, _c, _a, _b = WL.collect(side)
        facade = [(p["id"], p["name"], p["placed"]) for p in placed]
        # Only the parts that actually lie against the wall. A swing sign hangs on chain
        # at the end of a bracket that reaches 15 mm into the alley, and the banner
        # hangs off the overhead rail: placing either flat on the wall and measuring
        # what it runs into measures nothing. A fascia name plate sits on its board,
        # which is a joint of its own and is checked by the pin geometry.
        want = {r["id"] for _k, r, _rot, _o in KT.wall_mount_rows(side)}
        hung = []
        for it in KT.signs() + KT.brackets() + KT.lanterns() + KT.props():
            if it.get("side") != side or it["id"] not in want:
                continue
            hung.append((it["id"], it["name"],
                         to_wall(it["solid"], it["u"], it.get("z", 0) or 0)))
        bad = 0
        for hid, hname, hsolid in hung:
            hb = hsolid.val().BoundingBox()
            for pid, pname, psolid in facade:
                pb = psolid.val().BoundingBox()
                if (hb.xmax <= pb.xmin or hb.xmin >= pb.xmax
                        or hb.ymax <= pb.ymin or hb.ymin >= pb.ymax
                        or hb.zmax <= pb.zmin or hb.zmin >= pb.zmax):
                    continue
                hit = hsolid.intersect(psolid)
                v = hit.val().Volume() if hit.val().Solids() else 0.0
                if v > 0.05:
                    bad += 1
                    fail(f"{side}: {hid} {hname} is inside {pid} {pname} by "
                         f"{v:.2f} mm^3")
        if not bad:
            ok(f"{side} wall: all {len(hung)} hung parts clear the facade")


def check_first_layer_islands():
    """Is the first layer one piece, and is it joined by more than a hair?

    The wall face came off the plate with a 1.0 x 6.7 mm tab beside a window lying
    loose. The part is a single solid and its first layer is a single connected region,
    so every check passed -- but the tab was attached by a neck under 0.4 mm wide, and
    a neck thinner than one extrusion is not a join. The slicer prints it as an island.

    So this rasterizes the first layer and erodes it by half a nozzle. Anything that
    falls off under that erosion is held on by less than one bead.
    """
    print("\n[print] first layer is one piece, joined by more than one extrusion")
    import numpy as np
    from scipy import ndimage
    import build as B
    from parts import walls as WL

    PIX, NOZZLE, LAYER = 0.1, 0.4, 0.2

    def raster(solid):
        bb = solid.val().BoundingBox()
        slab = (cq.Workplane("XY")
                .box(bb.xlen + 10, bb.ylen + 10, LAYER, centered=(False, False, False))
                .translate((bb.xmin - 5, bb.ymin - 5, 0.0)))
        verts, tris = solid.intersect(slab).val().tessellate(0.02)
        v = np.array([[p.x, p.y, p.z] for p in verts])
        t = np.array(tris)
        tri = v[t[np.all(np.abs(v[t][:, :, 2]) < 1e-6, axis=1)]][:, :, :2]
        w = int(np.ceil(bb.xlen / PIX)) + 2
        h = int(np.ceil(bb.ylen / PIX)) + 2
        img = np.zeros((h, w), bool)
        yy, xx = np.mgrid[0:h, 0:w]
        px = bb.xmin + (xx + 0.5) * PIX
        py = bb.ymin + (yy + 0.5) * PIX
        for a, b, c in tri:
            lo_x = max(int((min(a[0], b[0], c[0]) - bb.xmin) / PIX) - 1, 0)
            hi_x = min(int((max(a[0], b[0], c[0]) - bb.xmin) / PIX) + 2, w)
            lo_y = max(int((min(a[1], b[1], c[1]) - bb.ymin) / PIX) - 1, 0)
            hi_y = min(int((max(a[1], b[1], c[1]) - bb.ymin) / PIX) + 2, h)
            if lo_x >= hi_x or lo_y >= hi_y:
                continue
            X, Y = px[lo_y:hi_y, lo_x:hi_x], py[lo_y:hi_y, lo_x:hi_x]
            d = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[1]-c[1])*(X-c[0]) + (c[0]-b[0])*(Y-c[1])) / d
            l2 = ((c[1]-a[1])*(X-c[0]) + (a[0]-c[0])*(Y-c[1])) / d
            img[lo_y:hi_y, lo_x:hi_x] |= (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
        return img, bb

    r = int(round((NOZZLE / 2) / PIX))
    k = np.ones((2 * r + 1, 2 * r + 1), bool)
    for side in ("L", "R"):
        solid = B.drop_to_bed(B.print_orient(WL.wall_face(side), ("Y", -90)))
        img, bb = raster(solid)
        _, n = ndimage.label(img)
        er = ndimage.binary_erosion(img, k)
        lab, n2 = ndimage.label(er)
        if n > 1:
            fail(f"{side} wall face: first layer is {n} separate islands")
            continue
        if n2 <= 1:
            ok(f"{side} wall face: one island, {img.sum()*PIX*PIX:.0f} mm^2, "
               "nothing hanging by a thread")
            continue
        sizes = ndimage.sum(er, lab, range(1, n2 + 1)) * PIX * PIX
        for i in np.argsort(-sizes)[1:]:
            ys, xs = np.where(lab == i + 1)
            fail(f"{side} wall face: {sizes[i]:.1f} mm^2 held on by a neck under "
                 f"{NOZZLE} mm, at wall height "
                 f"{-(bb.xmin + xs.max()*PIX):.0f}-{-(bb.xmin + xs.min()*PIX):.0f} mm, "
                 f"depth {bb.ymin + ys.min()*PIX:.0f}-{bb.ymin + ys.max()*PIX:.0f} mm "
                 "-- it will print loose")


def check_bed_contact():
    """Every part must stand on more than it hangs off.

    Read from the manifest, which build.py fills in by measuring each part in its PRINT
    orientation. Two ways to fail:

      * almost nothing on the bed -- the part balances on a point and the nozzle knocks
        it off. Five doors stood on their 1.1 mm doorknob: 0.80 mm^2 of first layer.
      * far more downward-facing area than first layer -- the slicer calls this a
        floating cantilever and it is right. The window frame stood on its glazing bars,
        129.5 mm^2 under 376.8 mm^2 of overhang, and the first anyone knew was a dialog
        box in Bambu Studio.

    Neither is visible in CAD. Both are perfectly valid geometry.
    """
    print("\n[print] parts stand on more than they hang off")
    path = os.path.join(OUT, "manifest.json")
    if not os.path.exists(path):
        warn("no manifest.json -- run build.py first")
        return
    rows = [r for r in json.load(open(path))
            if r.get("status") == "ok" and "bed" in r]
    if not rows:
        warn("manifest has no bed/overhang figures -- rebuild with the current build.py")
        return
    def ratio(r):
        return r["overhang"] / max(r["bed"], 0.1)

    # A high overhang-to-bed ratio is only damning when the base is small. A recessed
    # panel -- a sign with a raised border, or the window frame now that its outer bead
    # stands proud -- legitimately has several times its border in bridged area, and
    # that bridging is anchored on all sides. The failing case is the part that has
    # nothing much holding it down in the first place.
    STAND_ON_POINT = 3.0
    TOO_LITTLE_BASE = 12.0
    tiny = [r for r in rows if r["bed"] < STAND_ON_POINT]
    risky = [r for r in rows if r not in tiny and r["overhang"] > 50.0
             and ratio(r) > 4.0 and r["bed"] < TOO_LITTLE_BASE]

    # A third way, and the one that got through. A part can have a perfectly respectable
    # 48.6 mm^2 on the bed and still be resting on a LINE: fusing the sills onto the
    # window frames put a proud sill under a 27 x 35 mm frame, so the frame floated
    # 1 mm up and stood on the sill's nose. Bambu called it a floating cantilever; the
    # absolute-area rules above did not, because 48.6 is not a small number until you
    # notice it is 5% of the 945 mm^2 the part covers. Fifteen parts regressed that way
    # in one commit. What matters is the FRACTION of its own footprint a part stands on.
    ON_A_LINE = 0.08
    def footprint(r):
        w, d, _ = r.get("bbox", [1, 1, 0])
        return max(w * d, 0.01)
    online = [r for r in rows if r not in tiny and r not in risky
              and r["overhang"] > 50.0 and ratio(r) > 4.0
              and r["bed"] < ON_A_LINE * footprint(r)]
    # Two more ways to lose a small part, both learned the hard way when 19C and 13As
    # came off the plate as spaghetti with the slicer's Auto brim enabled:
    #   * not much base in absolute terms, whatever the ratio says. 19C had 15.4 mm^2.
    #   * a footprint far narrower than the part is tall, so the nozzle levers it off
    #     sideways. 13As was 27 x 2.6 mm and 7.3 mm tall.
    import build as _B
    SMALL_BASE = _B.SMALL_BASE
    def narrow(r):
        w, d, h = r.get("bbox", [99, 99, 0])
        return h > _B.TIPPY * max(min(w, d), 0.01)
    brim = [r for r in rows if r not in tiny and r not in risky and _B.needs_brim(r)]
    for r in sorted(tiny, key=lambda r: r["bed"]):
        fail(f"{r['id']} {r['name']}: only {r['bed']:.2f} mm^2 on the bed "
             f"({r['overhang']:.0f} mm^2 hanging) -- it stands on a point")
    for r in sorted(risky, key=lambda r: -ratio(r)):
        fail(f"{r['id']} {r['name']}: {r['overhang']:.0f} mm^2 of overhang on only "
             f"{r['bed']:.1f} mm^2 of first layer (x{ratio(r):.0f}) -- it will come off "
             "the plate")
    for r in sorted(online, key=lambda r: r["bed"] / footprint(r)):
        fail(f"{r['id']} {r['name']}: stands on {r['bed']:.0f} mm^2, which is "
             f"{100 * r['bed'] / footprint(r):.0f}% of the {footprint(r):.0f} mm^2 it "
             f"covers, with {r['overhang']:.0f} mm^2 hanging -- it is resting on a line, "
             "not an area")
    def why_brim(r):
        """The clause of build.needs_brim that caught this part, in words."""
        w, d, h = r["bbox"]
        if r["bed"] < SMALL_BASE:
            return "only %.0f mm^2 of base" % r["bed"]
        if narrow(r):
            return "%.0fx%.0f mm footprint under a %.0f mm height" % (w, d, h)
        if min(w, d) > _B.WIDE:
            if h < _B.THIN:
                return "%.0f mm across and only %.1f mm tall -- it will curl" % (min(w, d), h)
            return ("%.0f mm across with %.0f mm^2 of first layer under it -- thin strips "
                    "200 mm long curl like a sheet" % (min(w, d), r["bed"]))
        if max(w, d) > _B.SLENDER * max(min(w, d), 0.01) and min(w, d) < _B.NARROW:
            return ("a %.0f x %.1f mm strip -- it curls along its length and has no width "
                    "to anchor the curl" % (max(w, d), min(w, d)))
        return "%.0f mm^2 bridged over %.0f" % (r["overhang"], r["bed"])
    for r in sorted(brim, key=lambda r: r["bed"]):
        why = why_brim(r)
        warn(f"{r['id']} {r['name']}: {why} -- print it with a brim")
    if not tiny and not risky and not online:
        ok(f"all {len(rows)} parts have a first layer that carries what is above it"
           + (f" ({len(brim)} want a brim)" if brim else ""))


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
    check_sign_text()
    check_sign_hanging()
    check_envelope()
    check_assembled_envelope()
    check_light_block()
    check_keying()
    check_fits()
    check_all_mates()
    check_glue_gap_across_clearances()
    check_coupon_tab_flips()
    check_joint_coupon()
    check_t3_grip()
    check_paint_handles()
    check_unsupported_relief()
    check_facade_seating()
    check_mount_crowding()
    check_first_layer_islands()
    check_bed_contact()
    check_manifest()
    print(f"\n{len(FAILS)} failures, {len(WARNS)} warnings")
    sys.exit(1 if FAILS else 0)
