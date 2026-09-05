"""Prototype A: the calibration coupons. Print these before anything else.

Spec section 17 is emphatic and it is right -- do not print the full inhaler first. What
is here is that list, with two changes the sample forced:

  * The MX fit sweep is recentred. The spec swept 13.95-14.25 around a 14.10 nominal
    that came from nowhere. The sample -- a clicker that works -- cuts 14.00, so the
    sweep runs 13.90-14.20 around that instead.
  * A BAND THICKNESS sweep was added, and it matters more than the cutout does. The
    switch is retained by its clips hooking under a 1.5 mm plate band, not by friction
    against the pocket. The spec's 2.0-2.2 mm shelf is thicker than the clips can reach
    past, so tiles at 1.5 and 2.0 settle whether that reading is right.

Every tile is stamped with its own number in raised text. A tray of anonymous tiles is
how the last project ended up with results it could not attribute.

    python coupon.py            build all four coupons and report
    python coupon.py --export   also write out/*.step
"""
import os
import sys

import cadquery as cq

import params as P
import switch

HERE = os.path.dirname(os.path.abspath(__file__))

TILE = 24.0            # square, big enough to hold a switch and be held in fingers
TILE_T = 3.0
STAMP_H = 3.0          # the tile's own label

MX_CUTOUT_SWEEP = (13.90, 14.00, 14.10, 14.20)
MX_BAND_SWEEP = (1.5, 2.0)
GUIDE_SWEEP = (0.20, 0.25, 0.30, 0.35)
STEM_W_SWEEP = (1.45, 1.50, 1.55, 1.60)


def _stamp(solid, label, z, y=None):
    """Raised text on a top face at height `z`. Overlapped 0.1 into the face, because a
    body extruded from EXACTLY a face stays a separate body."""
    y = -(TILE / 2 - 3.5) if y is None else y
    txt = (cq.Workplane("XY").workplane(offset=z - 0.1)
           .text(label, STAMP_H, float(P.TEXT_RAISE) + 0.1, font=P.TEXT_FONT,
                 halign="center", valign="center")
           .translate((0, y, 0)))
    return solid.union(txt)


# ------------------------------------------------- 01: does the switch clip in --
def mx_fit_tiles():
    """One tile per cutout size and per band thickness. Goal: secure but removable."""
    items = []
    for cut in MX_CUTOUT_SWEEP:
        items.append((f"01_mx_{cut:.2f}".replace(".", "p"), _mx_tile(cut, 1.5),
                      f"{cut:.2f}"))
    for band in MX_BAND_SWEEP:
        items.append((f"01_band_{band:.1f}".replace(".", "p"), _mx_tile(14.00, band),
                      f"B{band:.1f}"))
    return items


def _mx_tile(cutout, band):
    """A slab with a full MX mount in it, at the given cutout and band thickness.

    Built by overriding the params the mount reads, so the coupon and the real part come
    out of ONE piece of code. A coupon with its own copy of the geometry tests the copy.
    """
    old_pocket, old_band = P.MX_POCKET, P.MX_PLATE_T
    try:
        P.MX_POCKET = P.Param(cutout, P.CHOSEN, "coupon sweep")
        P.MX_PLATE_T = P.Param(band, P.CHOSEN, "coupon sweep")
        h = band + float(P.MX_POCKET_DEPTH) + float(P.PIN_RELIEF_DEPTH) + 1.0
        slab = (cq.Workplane("XY").box(TILE, TILE, h, centered=(True, True, False))
                .translate((0, 0, -h)))
        # mount_cut is written with the plate top at z=0; so is the slab.
        tile = slab.cut(switch.mount_cut())
        return _stamp(tile, f"{cutout:.2f}" if band == 1.5 else f"B{band:.1f}", 0.0)
    finally:
        P.MX_POCKET, P.MX_PLATE_T = old_pocket, old_band


# --------------------------------------------- 02: does the canister slide free --
def guide_tiles():
    """Four collars at four clearances, plus ONE stub to try in all of them.

    The stub is the real canister's rim, lugs and boss, cut short. Testing a collar
    against a turned dowel would test the dowel.
    """
    import mech
    items = []
    for c in GUIDE_SWEEP:
        items.append((f"02_guide_{c:.2f}".replace(".", "p"), _guide_tile(c),
                      f"{c:.2f}"))
    stub_h = float(P.LUG_H) + 8.0
    stub = mech.canister().intersect(
        cq.Workplane("XY").box(40, 40, stub_h, centered=(True, True, False)))
    items.append(("02_guide_stub", stub, "stub"))
    return items


def _guide_tile(clearance):
    old = P.GUIDE_CLEARANCE
    try:
        P.GUIDE_CLEARANCE = P.Param(clearance, P.CHOSEN, "coupon sweep")
        P.GUIDE_BORE = P.Param(P.CANISTER_OD + 2 * P.GUIDE_CLEARANCE, P.CHOSEN, "derived")
        P.SLOT_OD = P.Param(P.LUG_OD + 2 * P.GUIDE_CLEARANCE, P.CHOSEN, "derived")
        import mech
        s = P.stack()
        h = float(P.LUG_H) + 8.0
        blk = (cq.Workplane("XY")
               .box(float(P.BODY_WIDTH), float(P.BODY_DEPTH), h + TILE_T,
                    centered=(True, True, False))
               .edges("|Z").fillet(float(P.BODY_CORNER_R)))
        cut = mech.collar_cut().translate((0, 0, TILE_T - s["stop_ledge"]))
        return _stamp(blk.cut(cut), f"{clearance:.2f}", h + TILE_T,
                      y=-(float(P.BODY_DEPTH) / 2 - 2.6))
    finally:
        P.GUIDE_CLEARANCE = old
        P.GUIDE_BORE = P.Param(P.CANISTER_OD + 2 * old, P.CHOSEN, "derived")
        P.SLOT_OD = P.Param(P.LUG_OD + 2 * old, P.CHOSEN, "derived")


# ------------------------------------------------------- 03: can you read it --
def text_plaque():
    """The lettering at its real size, on a flat plaque, in one colour.

    What this settles is stroke width and legibility. It does NOT settle the AMS colour
    split -- that needs the text as a separate body in a real project file, which is what
    plate.py will have to grow next.
    """
    w, h = 30.0, 22.0
    plaque = cq.Workplane("XY").box(w, h, TILE_T, centered=(True, True, False))
    lines = ((P.TEXT_LINES[0], float(P.TEXT_H_SMALL), 6.5),
             (P.TEXT_LINES[1], float(P.TEXT_H_SMALL), 0.5),
             (P.TEXT_LINES[2], float(P.TEXT_H_WHEEZY), -6.0))
    for txt, size, y in lines:
        plaque = plaque.union(
            cq.Workplane("XY").workplane(offset=TILE_T - 0.1)
            .text(txt, size, float(P.TEXT_RAISE) + 0.1, font=P.TEXT_FONT,
                  halign="center", valign="center")
            .translate((0, y, 0)))
    return plaque


# ------------------------------------------------ 04: does the cap stay on --
def stem_tiles():
    """Four stem receivers at four socket widths. The width is the tight direction:
    the sample cuts 1.55 over a 1.17 stem, which is 0.19 a side and looks generous until
    you remember this joint takes every press the fidget will ever get."""
    items = []
    for w in STEM_W_SWEEP:
        items.append((f"04_stem_{w:.2f}".replace(".", "p"), _stem_tile(w), f"{w:.2f}"))
    return items


def _stem_tile(cross_w):
    old = P.MX_STEM_CROSS_W
    try:
        P.MX_STEM_CROSS_W = P.Param(cross_w, P.CHOSEN, "coupon sweep")
        boss_len = float(P.MX_SOCKET_DEPTH) + 1.5
        pad = (cq.Workplane("XY").box(14.0, 14.0, TILE_T, centered=(True, True, False))
               .edges("|Z").fillet(2.0))
        tile = pad.union(switch.stem_receiver(boss_len).translate((0, 0, TILE_T - 0.1)))
        return _stamp(tile, f"{cross_w:.2f}", TILE_T, y=-5.0)
    finally:
        P.MX_STEM_CROSS_W = old


# ==================================================================== the set ==
def parts():
    """[(name, solid, brim)] for plate.py. brim=None means let the plate default win."""
    items = []
    items += [(n, s, None) for n, s, _ in mx_fit_tiles()]
    items += [(n, s, None) for n, s, _ in guide_tiles()]
    items += [("03_text", text_plaque(), None)]
    items += [(n, s, None) for n, s, _ in stem_tiles()]
    return items


def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    built = parts()
    t("every coupon in spec section 17 is on the plate", len(built) == 16,
      f"{len(built)} tiles: 6 mx, 4 guide + 1 stub, 1 text, 4 stem")

    for name, solid, _ in built:
        # A stamp that did not fuse leaves two solids and slices as a loose chip.
        n = len(solid.solids().vals())
        t(f"{name} is one solid", n == 1, "" if n == 1 else f"{n} solids")

    # The sweeps must actually differ. Four identical tiles is a sweep that tests nothing,
    # and it is exactly what an override that silently failed would produce.
    vols = [round(s.val().Volume(), 3) for n, s, _ in built if n.startswith("01_mx")]
    t("the MX cutout sweep produces four DIFFERENT tiles",
      len(set(vols)) == len(vols), f"{vols}")
    gv = [round(s.val().Volume(), 3) for n, s, _ in built if n.startswith("02_guide_0")]
    t("the guide clearance sweep produces four DIFFERENT collars",
      len(set(gv)) == len(gv), f"{gv}")
    sv = [round(s.val().Volume(), 3) for n, s, _ in built if n.startswith("04_stem")]
    t("the stem socket sweep produces four DIFFERENT receivers",
      len(set(sv)) == len(sv), f"{sv}")

    # Text is the one thing here that is not ours: the font may not resolve, and cq
    # falls back silently. Measure it, do not derive it.
    plain = cq.Workplane("XY").box(30.0, 22.0, TILE_T, centered=(True, True, False))
    t(f"the {P.TEXT_FONT!r} lettering actually rendered",
      text_plaque().val().Volume() > plain.val().Volume() + 1.0,
      f"{text_plaque().val().Volume() - plain.val().Volume():.1f} mm3 of raised glyph")
    return out


if __name__ == "__main__":
    print("coupon -- Prototype A, the four calibration prints\n")
    results = self_test()
    bad = 0
    for ok, name, detail in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok
    print(f"\n  {len(results)} tests, {bad} failures")

    if "--export" in sys.argv:
        out_dir = os.path.join(HERE, "out")
        os.makedirs(out_dir, exist_ok=True)
        for name, solid, _ in parts():
            cq.exporters.export(solid, os.path.join(out_dir, f"{name}.step"))
        print(f"  wrote {len(parts())} step files to out/")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
