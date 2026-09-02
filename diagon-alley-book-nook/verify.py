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
        # 11A used to be exempt from the grip test, because T3 had no grip to test --
        # it relied on a detent that measured 0.008 mm^3. Now that T3 carries the same
        # crush ribs as P1 and P2, it is held to the same standard. An exemption that
        # outlives its reason is how a regression hides.
        if foul > 0.05:
            fail(f"{rid} {what}: part fouls the wall by {foul:.2f} mm^3 -- will not seat")
        elif grip < 0.05:
            fail(f"{rid} {what}: no crush-rib grip, the part will fall out")
        else:
            ok(f"{rid} {what}: clears the bore, grip {grip:.2f} mm^3")


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
        ok(f"lead-in {P.LEAD_IN_CHAMFER}, press/decorative/slide clearances "
           f"{P.FIT_CLEARANCE}/{P.DECORATIVE_CLEARANCE}/{P.T3_CLEARANCE}, "
           f"rib bite {P.CRUSH_INTERFERENCE}")
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
    # Two more ways to lose a small part, both learned the hard way when 19C and 13As
    # came off the plate as spaghetti with the slicer's Auto brim enabled:
    #   * not much base in absolute terms, whatever the ratio says. 19C had 15.4 mm^2.
    #   * a footprint far narrower than the part is tall, so the nozzle levers it off
    #     sideways. 13As was 27 x 2.6 mm and 7.3 mm tall.
    SMALL_BASE = 25.0
    TIPPY = 2.0
    def narrow(r):
        w, d, h = r.get("bbox", [99, 99, 0])
        return h > TIPPY * max(min(w, d), 0.01)
    brim = [r for r in rows if r not in tiny and r not in risky
            and ((r["overhang"] > 50.0 and ratio(r) > 4.0)
                 or r["bed"] < SMALL_BASE or narrow(r))]
    for r in sorted(tiny, key=lambda r: r["bed"]):
        fail(f"{r['id']} {r['name']}: only {r['bed']:.2f} mm^2 on the bed "
             f"({r['overhang']:.0f} mm^2 hanging) -- it stands on a point")
    for r in sorted(risky, key=lambda r: -ratio(r)):
        fail(f"{r['id']} {r['name']}: {r['overhang']:.0f} mm^2 of overhang on only "
             f"{r['bed']:.1f} mm^2 of first layer (x{ratio(r):.0f}) -- it will come off "
             "the plate")
    for r in sorted(brim, key=lambda r: r["bed"]):
        why = ("only %.0f mm^2 of base" % r["bed"]) if r["bed"] < SMALL_BASE else \
              ("%.0fx%.0f mm footprint under a %.0f mm height"
               % (r["bbox"][0], r["bbox"][1], r["bbox"][2])) if narrow(r) else \
              ("%.0f mm^2 bridged over %.0f" % (r["overhang"], r["bed"]))
        warn(f"{r['id']} {r['name']}: {why} -- print it with a brim")
    if not tiny and not risky:
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
    check_envelope()
    check_assembled_envelope()
    check_light_block()
    check_keying()
    check_fits()
    check_all_mates()
    check_grip_across_clearances()
    check_coupon_tab_flips()
    check_joint_coupon()
    check_t3_grip()
    check_paint_handles()
    check_unsupported_relief()
    check_first_layer_islands()
    check_bed_contact()
    check_manifest()
    print(f"\n{len(FAILS)} failures, {len(WARNS)} warnings")
    sys.exit(1 if FAILS else 0)
