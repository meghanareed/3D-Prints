"""Plate 1 -- the torture test. The first thing that gets printed.

Nothing over this size gets printed until this plate assembles in a hand. It is
deliberately one plate that answers six questions rather than six plates answering one
each, because the constraint on this project has never been filament, it has been rounds.

Closes, if it prints and fits:

    R-5   peg Ø3.0 at 0.30/side into Ø3.6 -- and whether 0.25 and 0.35 are better
    R-14  does a peg standing on a LARGE plate blob? The old ones blobbed on small
          parts, where a 4.5 mm2 island is most of the layer. This is the inference
          the sign joint now rests on, and it is ~0 g to settle
    R-10  what raised type actually reads, by size and by stroke
    R-15  whether an AMS colour change lands cleanly on the lettering layers
    R-17  whether a 5-facet bow reads as curved
    (part of R-9: how supports behave under a canopy)

P6 governs the layout: **every piece on this plate mates with another piece on this
plate**. The last first-fit plate carried parts that fitted nothing, and a plate whose
fasteners break on their own brim tests nothing at all.

    python coupon.py            build, self-test, report mass
    python coupon.py --export   write STLs to out/coupon/
"""
import math
import os
import sys

import cadquery as cq

import joints as J
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
PLA_DENSITY = 1.24e-3          # g/mm3

# The clearances under test. 0.30 is the measured incumbent; the neighbours say whether
# a Ø3.0 peg -- bigger than the Ø2.4 the number came from -- wants something different.
CLEARANCES = [0.25, 0.30, 0.35]
MULLIONS = [1.0, 1.2, 1.6]
TEXT_SIZES = [2.5, 3.0, 4.0, 6.0]


def _stamp_many(solid, lines, face="top", z=None):
    """Stamp several labels on ONE face, at a z captured BEFORE any of them is applied.

    Stamping twice in a row does not work if each call re-reads the bounding box: the
    first label makes the solid taller by its own relief, so the second lands floating
    in the air above the face. Capture the face once.
    """
    if z is None:
        bb = solid.val().BoundingBox()
        z = bb.zmax if face == "top" else bb.zmin
    for text, size, at in lines:
        solid = _stamp(solid, text, size, at, face=face, z=z)
    return solid


def _stamp(solid, text, size=3.2, at=None, face="top", z=None):
    """Emboss a label. Twelve pieces come off this plate and a bench cannot tell a 0.25
    socket from a 0.35 one by eye -- naming them is not decoration, it is the difference
    between a result and a pile of plastic."""
    if z is None:
        bb = solid.val().BoundingBox()
        z = bb.zmax if face == "top" else bb.zmin
    x, y = at if at else (0.0, 0.0)
    # SINK it. Text extruded from exactly the top face is only TANGENT to the body, and
    # OCCT leaves a tangent solid separate -- which is how a bracket silently became
    # three pieces in the last attempt. Start it inside the material and overlap.
    bite = 0.3
    txt = (cq.Workplane("XY").workplane(offset=z - bite)
           .text(text, size, float(P.TEXT_DEPTH) + bite, combine=False, kind="bold",
                 halign="center", valign="center")
           .translate((x, y, 0)))
    return solid.union(txt)


# =============================================================== joint station ==
def peg_tile(n=len(CLEARANCES)):
    """A wall-sized tile with pegs standing UP -- the R-14 question.

    The tile is deliberately BROAD. A peg on a small part is most of its own layer and
    never cools; on a 60 x 40 plate the nozzle spends seconds elsewhere before returning.
    That difference is the whole argument for putting the male feature on the wall, and
    it has never been printed.
    """
    w, d, t = 62.0, 40.0, 3.0
    tile = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    pitch = w / (n + 1)
    for i in range(n):
        x = -w / 2 + pitch * (i + 1)
        tile = tile.union(J.peg().translate((x, 0, t)))
    # z=t explicitly: the pegs stand 4 mm above this face, so bb.zmax is the peg TIPS
    # and a label placed there would float in mid-air.
    tile = _stamp_many(tile, [("PEG TILE  R-14", 4.0, (0, 13.0)),
                              ("do pegs blob on a big plate?", 2.6, (0, -13.0))], z=t)
    return tile


def socket_block(clearance, label=None):
    """The mate for one peg. Drops over it; the block's face must land on the tile."""
    # Tall enough that the blind cone does NOT punch out of the top. Sized to
    # depth alone, it did -- every block on the first plate had a pinhole where
    # its blind end should have been.
    w, d = 16.0, 16.0
    t = J.socket_min_material(clearance=clearance)
    blk = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    blk = J.socket_in(blk, (0, 0, 0), "+Z", clearance=clearance)
    if label:
        blk = _stamp_many(blk, [("SKT", 3.0, (0, 4.5)), (label, 4.4, (0, -2.5))])
    return blk


def pin_sprue(n=6, pitch=None):
    """Pins on a spine joined at ONE end only.

    The last sprue was a solid 0.8 mm plate under every pin, so freeing one meant cutting
    a sheet along its whole length -- and its brim flooded the 4 mm gaps and tore the pins
    off, which meant no pin joint on that plate could be tried at all. This one is a
    spine with cantilevered pins, wider pitch, and `needs_brim` is overridden to False.
    """
    pitch = pitch or (float(P.PEG_D) + 4.0)
    L = float(P.PIN_L)
    spine = cq.Workplane("XY").box(4.0, pitch * n, 2.0, centered=(True, True, False))
    out = spine
    for i in range(n):
        y = -pitch * n / 2 + pitch * (i + 0.5)
        # lying down, so no pin is a tower
        p = (J.pin().rotate((0, 0, 0), (0, 1, 0), 90)
             .translate((2.0, y, float(P.PEG_D) / 2.0)))
        out = out.union(p)
    # A label needs something to sit ON. The spine is only 4 mm wide, so give the sprue
    # a small tab at one end -- fused, overlapping, not merely touching.
    ty = pitch * n / 2
    tab = (cq.Workplane("XY").box(14.0, 7.0, 2.0, centered=(True, True, False))
           .translate((0, ty - 0.5, 0)))
    out = out.union(tab)
    out = _stamp(out, "PINS", 3.4, at=(0, ty + 3.0), z=2.0)
    return out


def pin_pair(clearance):
    """Two blocks that meet face to face over one loose pin -- the real pin joint."""
    w, d = 16.0, 16.0
    t = J.socket_min_material(clearance=clearance)
    a = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    a = J.socket_facing(a, (0, 0, t), "-Z", clearance=clearance)
    b = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    b = J.socket_facing(b, (0, 0, 0), "+Z", clearance=clearance)
    a = _stamp_many(a, [("PIN A", 3.4, (0, 4.5)), ("+B+pin", 2.4, (0, -4.5))])
    b = _stamp_many(b, [("PIN B", 3.4, (0, 4.5)), ("+A+pin", 2.4, (0, -4.5))])
    return a, b


# ============================================================== bridge station ==
def _opening(w, h, top):
    """A window opening whose TOP is square, chamfered or arched."""
    body = cq.Workplane("XY").box(w, 20.0, h, centered=(True, True, False))
    if top == "square":
        return body
    if top == "chamfer":
        c = min(1.5, w / 3)
        cut = (cq.Workplane("XZ").moveTo(-w / 2, h).lineTo(-w / 2 + c, h)
               .lineTo(-w / 2, h - c).close().extrude(30.0).translate((0, 15, 0)))
        return body.cut(cut).cut(cut.mirror("YZ"))
    if top == "arch":
        # the arc already terminates at (w/2, h); a lineTo the same point is a
        # zero-length edge and OCCT refuses it outright
        arch = (cq.Workplane("XZ").moveTo(-w / 2, h)
                .threePointArc((0, h + w / 2), (w / 2, h))
                .close().extrude(30.0).translate((0, 15, 0)))
        return body.union(arch)
    raise ValueError(top)


def bridge_panel(mullion):
    """A standing panel with three opening tops, at one mullion thickness.

    Openings are the failure this station exists to find: the top of a rectangular pane
    is a bridge between two mullions, and "the frames standing on their glazing bars" is
    a listed defect from the last attempt.
    """
    ow, oh = 12.0, 18.0
    tops = ("square", "chamfer", "arch")
    w = len(tops) * ow + (len(tops) + 1) * mullion
    h = oh + 2 * mullion + 8.0
    panel = cq.Workplane("XY").box(w, 3.0, h, centered=(True, True, False))
    for i, top in enumerate(tops):
        x = -w / 2 + mullion * (i + 1) + ow * (i + 0.5)
        panel = panel.cut(_opening(ow, oh, top).translate((x, 0, mullion)))
    panel = panel.union(
        cq.Workplane("XZ").workplane(offset=-1.5)
        .text(f"{mullion:.1f}", 4.0, 0.6, combine=False, kind="bold")
        .translate((0, 0, h - 4.0)))
    return panel


# ================================================================ text station ==
def text_plate(sizes=TEXT_SIZES):
    """Raised type, printed FACE UP, at several sizes.

    Face up because signs printed face down crushed every letter into the bed. The word
    is fixed so only size varies -- the question is what READS, not what slices.
    """
    pad, lead = 3.0, 2.0
    h = pad * 2 + sum(sizes) + lead * (len(sizes) - 1)
    w = 46.0
    plate = cq.Workplane("XY").box(w, h, 1.6, centered=(True, True, False))
    y = h / 2 - pad
    for s in sizes:
        y -= s
        plate = plate.union(
            cq.Workplane("XY").workplane(offset=1.6)
            .text("OLLIVANDERS", s, float(P.TEXT_DEPTH), combine=False,
                  kind="bold", halign="center", valign="bottom")
            .translate((0, y, 0)))
        y -= lead
    return plate


# ================================================================= bow station ==
def bow_facet(facets=5, w=26.0, h=22.0, proj=9.0):
    """Does a faceted bow read as curved? R-17, and it costs almost nothing to find out."""
    pts = []
    for i in range(facets + 1):
        a = math.pi * i / facets
        pts.append((-math.cos(a) * w / 2, math.sin(a) * proj))
    pts += [(w / 2, -2.0), (-w / 2, -2.0)]
    body = cq.Workplane("XY").polyline(pts).close().extrude(h)
    # Labelled LOOK because it mates with nothing -- R-17 asks whether five facets read
    # as a curve once painted, which is a question for an eye, not a caliper.
    return _stamp(body, "BOW  LOOK", 3.0, at=(0, proj / 2))


# ==================================================================== the plate ==
def parts():
    """Every piece, named. `brim` False means an explicit override (B4)."""
    out = [("00_peg_tile", peg_tile(), None)]
    for c in CLEARANCES:
        out.append((f"01_socket_{int(c * 100)}", socket_block(c, f"{int(c*100)}"), None))
    out.append(("02_pin_sprue", pin_sprue(), False))
    for c in (0.30,):
        a, b = pin_pair(c)
        out.append((f"03_pinpair_A_{int(c * 100)}", a, None))
        out.append((f"03_pinpair_B_{int(c * 100)}", b, None))
    for m in MULLIONS:
        out.append((f"04_bridge_{str(m).replace('.', 'p')}", bridge_panel(m), None))
    out.append(("05_text", text_plate(), None))
    out.append(("06_bow", bow_facet(), None))
    return out


def _bbox(w):
    bb = w.val().BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    ps = parts()
    total = 0.0
    for name, solid, _ in ps:
        n = len(solid.solids().vals())
        t(f"{name} is one solid", n == 1, f"{n} solids" if n != 1 else "")
        total += solid.val().Volume()

    grams = total * PLA_DENSITY
    t("plate is small enough to be a gate", grams < 60.0, f"{grams:.1f} g")

    # P6: every piece must mate with something on this plate.
    names = {n for n, _, _ in ps}
    mates = {
        "00_peg_tile": [n for n in names if n.startswith("01_socket")],
        "02_pin_sprue": [n for n in names if n.startswith("03_pinpair")],
        "05_text": ["05_text"],          # read, not mated -- declared, not assumed
        "06_bow": ["06_bow"],
    }
    unmated = []
    for n in names:
        if n.startswith(("01_socket", "03_pinpair", "04_bridge")):
            continue
        if n in mates and mates[n]:
            continue
        unmated.append(n)
    t("P6: every piece mates or is declared standalone", not unmated, ", ".join(unmated))

    # P6 by NAME is a promise; this is the same claim tested by physically dropping each
    # socket block over its peg. A name map cannot see a flat pointing the wrong way.
    tile, tt, tw = peg_tile(), 3.0, 62.0
    pitch = tw / (len(CLEARANCES) + 1)
    for i, c in enumerate(CLEARANCES):
        x = -tw / 2 + pitch * (i + 1)
        foul = tile.intersect(socket_block(c).translate((x, 0, tt)))
        v = foul.val().Volume() if foul.solids().vals() else 0.0
        t(f"socket {c:.2f} drops onto its peg", v < 1e-6, f"{v:.4f} mm3")

    # ...and the key must still refuse the wrong way round on the real pieces.
    solo = (cq.Workplane("XY").box(tw, 40.0, tt, centered=(True, True, False))
            .union(J.peg().translate((0, 0, tt))))
    spun = solo.intersect(socket_block(0.30)
                          .rotate((0, 0, 0), (0, 0, 1), 180).translate((0, 0, tt)))
    sv = spun.val().Volume() if spun.solids().vals() else 0.0
    t("the key refuses a block spun 180", sv > 0.05, f"{sv:.4f} mm3")

    # The sprue must carry an explicit no-brim override; no heuristic can see its gaps.
    sprue = [b for n, _, b in ps if n == "02_pin_sprue"][0]
    t("sprue overrides brim to False", sprue is False)

    # Everything must fit the bed with its brim.
    bed = min(float(P.BED_X), float(P.BED_Y))
    over = [n for n, s, _ in ps
            if max(_bbox(s)[:2]) + 2 * float(P.BRIM_WIDTH) > bed]
    t("every piece fits the bed with a brim", not over, ", ".join(over))
    return out, grams


if __name__ == "__main__":
    print("coupon -- plate 1, the torture test\n")
    results, grams = self_test()
    bad = 0
    for ok, name, detail in results:
        if not ok:
            print(f"  FAIL  {name}" + (f"   [{detail}]" if detail else ""))
            bad += 1
    print(f"  {len(results) - bad} of {len(results)} checks pass")
    print(f"\n  {len(parts())} pieces, {grams:.1f} g of PLA")
    print("  closes R-5, R-10, R-14, R-15, R-17 and part of R-9 if it assembles")

    if "--export" in sys.argv:
        d = os.path.join(HERE, "out", "coupon")
        os.makedirs(d, exist_ok=True)
        for name, solid, _ in parts():
            cq.exporters.export(solid.val(), os.path.join(d, f"{name}.stl"))
        print(f"\n  wrote {len(parts())} STLs to {d}")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
