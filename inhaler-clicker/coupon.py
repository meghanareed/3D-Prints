"""Prototype A: the calibration coupons. Print these before anything else.

Spec section 17 is emphatic and it is right -- do not print the full inhaler first. What
is here is that list, with four changes the sample and the machine forced:

  * The MX fit sweep is recentred. The spec swept 13.95-14.25 around a 14.10 nominal
    that came from nowhere. The sample -- a clicker that works -- cuts 14.00, so the
    sweep runs 13.90-14.20 around that instead.
  * A BAND THICKNESS sweep was added, and it matters more than the cutout does. The
    switch is retained by its clips hooking under a 1.5 mm plate band, not by friction
    against the pocket. The spec's 2.0-2.2 mm shelf is thicker than the clips can reach
    past, so tiles at 1.5 and 2.0 settle whether that reading is right.
  * Tiles are identified by COUNTABLE BARS, not by printed numbers. Rule 12 next door,
    and it was bought: three test blocks printed with 3 mm labels that came out as blobs,
    and which clearance did what is now permanently unknowable. This file used to stamp
    3 mm text on every tile.
  * THREE COPIES of every value. Rule 13. Socket-to-socket scatter on this machine is
    wider than the whole range worth sweeping, so one tile tells you about that tile.

Reading the bars: count them. 1 bar is the first value in the sweep listed below, 2 the
second, and so on. The sweep tables are the legend.

    python coupon.py            build every coupon and report
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
REPLICATES = 3         # rule 13. Never one.

# Countable raised bars, well over the 1.2 x 2.0 mm minimum dependable feature.
ID_BAR_W, ID_BAR_L, ID_BAR_H = 1.6, 4.0, 1.2
ID_PITCH = 3.2

MX_CUTOUT_SWEEP = (13.90, 14.00, 14.10, 14.20)
MX_BAND_SWEEP = (1.5, 2.0)
GUIDE_SWEEP = (0.20, 0.25, 0.30, 0.35)
STEM_W_SWEEP = (1.45, 1.50, 1.55, 1.60)


def _id_bars(solid, n, z, y):
    """`n` countable bars on a top face at height `z`. Geometry, not text -- see rule 12.

    Overlapped 0.1 into the face, because a body extruded from EXACTLY a face stays a
    separate body and slices off as a loose chip.
    """
    span = (n - 1) * ID_PITCH
    for i in range(n):
        bar = (cq.Workplane("XY")
               .box(ID_BAR_W, ID_BAR_L, ID_BAR_H + 0.1, centered=(True, True, False))
               .translate((-span / 2 + i * ID_PITCH, y, z - 0.1)))
        solid = solid.union(bar)
    return solid


def _replicated(name, solid):
    """Rule 13: three copies, or the result is about one tile and not about the value."""
    return [(f"{name}_r{i + 1}", solid, None) for i in range(REPLICATES)]


# ------------------------------------------------- 01: does the switch clip in --
def mx_fit_tiles():
    """One tile per cutout size and per band thickness. Goal: secure but removable.

    Bars 1-4 = cutout 13.90 / 14.00 / 14.10 / 14.20 at a 1.5 band.
    Bars 5-6 = band 1.5 / 2.0 at a 14.00 cutout.
    """
    items = []
    for i, cut in enumerate(MX_CUTOUT_SWEEP, start=1):
        items += _replicated(f"01_mx_{cut:.2f}".replace(".", "p"), _mx_tile(cut, 1.5, i))
    for j, band in enumerate(MX_BAND_SWEEP, start=len(MX_CUTOUT_SWEEP) + 1):
        items += _replicated(f"01_band_{band:.1f}".replace(".", "p"),
                             _mx_tile(14.00, band, j))
    return items


def _mx_tile(cutout, band, bars):
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
        return _id_bars(slab.cut(switch.mount_cut()), bars, 0.0, -(TILE / 2 - 3.5))
    finally:
        P.MX_POCKET, P.MX_PLATE_T = old_pocket, old_band


# --------------------------------------------- 02: does the canister slide free --
def guide_tiles():
    """Four collars at four clearances, plus stubs to try in them.

    Bars 1-4 = clearance 0.20 / 0.25 / 0.30 / 0.35.

    The stub is the real canister's rim, lugs and boss, cut short -- testing a collar
    against a turned dowel would test the dowel. Three of those too: the stub is the
    gauge, and a gauge that printed oversize shifts every reading the same way.
    """
    import mech
    items = []
    for i, c in enumerate(GUIDE_SWEEP, start=1):
        items += _replicated(f"02_guide_{c:.2f}".replace(".", "p"), _guide_tile(c, i))
    stub_h = float(P.LUG_H) + 8.0
    stub = mech.canister().intersect(
        cq.Workplane("XY").box(40, 40, stub_h, centered=(True, True, False)))
    items += _replicated("02_guide_stub", stub)
    return items


def _guide_tile(clearance, bars):
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
        return _id_bars(blk.cut(cut), bars, h + TILE_T,
                        -(float(P.BODY_DEPTH) / 2 - 2.6))
    finally:
        P.GUIDE_CLEARANCE = old
        P.GUIDE_BORE = P.Param(P.CANISTER_OD + 2 * old, P.CHOSEN, "derived")
        P.SLOT_OD = P.Param(P.LUG_OD + 2 * old, P.CHOSEN, "derived")


# ------------------------------------------------------- 03: can you read it --
def text_plaque():
    """The lettering at its real size, on a plaque the size and shape of the real face.

    Not a rectangle: the plaque carries BODY_CORNER_R, because the question that nearly
    sank this layout is whether the columns stay on the FLAT between the fillets. A
    rectangular coupon would answer a question nobody asked.

    Vertical, because horizontal does not fit: IT AIN'T EASY at the 6 mm printable floor
    is 56.2 mm wide against 27 mm of face. Running it up the 63 mm axis, it is 56.2 mm of
    61. params.sanity() holds both of those.
    """
    w, h = float(P.BODY_WIDTH), float(P.BODY_HEIGHT)
    plaque = (cq.Workplane("XY").box(w, h, TILE_T, centered=(True, True, False))
              .edges("|Z").fillet(float(P.BODY_CORNER_R)))
    return plaque.union(lettering(TILE_T))


def lettering(on_face_z):
    """Just the raised glyphs, as their own solid, sitting on a face at `on_face_z`.

    Separate from the plaque for two reasons: the AMS colour split will need the
    lettering as a second body, and a check that measures the plaque's bounding box
    instead of the glyphs' is a check that always passes.
    """
    out = None
    x = -P.text_flat_width() / 2
    for txt, size in P.TEXT_LINES:
        x += float(size) / 2
        col = (cq.Workplane("XY").workplane(offset=on_face_z - 0.1)
               .text(txt, float(size), float(P.TEXT_RAISE) + 0.1, font=P.TEXT_FONT,
                     halign="center", valign="center")
               .rotate((0, 0, 0), (0, 0, 1), 90)
               .translate((x, 0, 0)))
        out = col if out is None else out.union(col)
        x += float(size) / 2 + float(P.TEXT_LINE_GAP)
    return out


# ------------------------------------------------ 04: does the cap stay on --
def stem_tiles():
    """Four stem receivers at four socket widths. Bars 1-4 = 1.45 / 1.50 / 1.55 / 1.60.

    The width is the tight direction: the sample cuts 1.55 over a 1.17 stem, which is
    0.19 a side and looks generous until you remember this joint takes every press the
    fidget will ever get.
    """
    items = []
    for i, w in enumerate(STEM_W_SWEEP, start=1):
        items += _replicated(f"04_stem_{w:.2f}".replace(".", "p"), _stem_tile(w, i))
    return items


def _stem_tile(cross_w, bars):
    old = P.MX_STEM_CROSS_W
    try:
        P.MX_STEM_CROSS_W = P.Param(cross_w, P.CHOSEN, "coupon sweep")
        boss_len = float(P.MX_SOCKET_DEPTH) + 1.5
        pad = (cq.Workplane("XY").box(20.0, 14.0, TILE_T, centered=(True, True, False))
               .edges("|Z").fillet(2.0))
        tile = pad.union(switch.stem_receiver(boss_len).translate((0, 0, TILE_T - 0.1)))
        return _id_bars(tile, bars, TILE_T, -5.0)
    finally:
        P.MX_STEM_CROSS_W = old


# ==================================================================== the set ==
def parts():
    """[(name, solid, brim)] for plate.py. brim=None means let the plate default win."""
    return (mx_fit_tiles() + guide_tiles()
            + _replicated("03_text", text_plaque()) + stem_tiles())


def _by_value(items, prefix):
    """One representative solid per swept VALUE, replicates collapsed."""
    seen = {}
    for name, solid, _ in items:
        if name.startswith(prefix):
            seen.setdefault(name.rsplit("_r", 1)[0], solid)
    return seen


def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    built = parts()
    values = (len(MX_CUTOUT_SWEEP) + len(MX_BAND_SWEEP) + len(GUIDE_SWEEP)
              + 1 + 1 + len(STEM_W_SWEEP))       # + stub + text
    t("every coupon in spec section 17 is on the plate",
      len(built) == values * REPLICATES,
      f"{len(built)} tiles = {values} values x {REPLICATES} copies")

    t(f"every value has {REPLICATES} copies -- rule 13, never one",
      all(sum(1 for n, _, _ in built if n.rsplit("_r", 1)[0] == v) == REPLICATES
          for v in {n.rsplit("_r", 1)[0] for n, _, _ in built}))

    bad = [n for n, s, _ in built if len(s.solids().vals()) != 1]
    t("every tile is one solid -- a bar that did not fuse slices off as a chip",
      not bad, ", ".join(bad))

    # The sweeps must actually differ. Identical tiles are a sweep that tests nothing,
    # and it is exactly what an override that silently failed would produce.
    for prefix, label in (("01_mx", "MX cutout"), ("02_guide_0", "guide clearance"),
                          ("04_stem", "stem socket")):
        vols = [round(s.val().Volume(), 3) for s in _by_value(built, prefix).values()]
        t(f"the {label} sweep produces {len(vols)} DIFFERENT tiles",
          len(set(vols)) == len(vols), f"{vols}")

    # Rule 12. This file used to print a 3 mm number on every tile, which is the size
    # that came out as blobs next door and lost a whole plate's answer. The first version
    # of THIS check searched the source for the old helper's name -- and the check's own
    # line contained that name, so it could never pass. Count the calls instead: exactly
    # one place in this module is allowed to render glyphs, and it is the text coupon.
    src = open(__file__, encoding="utf8").read()
    pat = "." + "text("          # assembled, so this line is not itself a call site
    t("only the text coupon renders glyphs; tiles are identified by geometry",
      src.count(pat) == 1,
      f"{src.count(pat)} call sites -- countable bars everywhere else")
    t("the ID bars clear the minimum dependable feature",
      ID_BAR_W >= P.MIN_FEATURE_T and ID_BAR_L >= P.MIN_FEATURE_L,
      f"{ID_BAR_W} x {ID_BAR_L} against {float(P.MIN_FEATURE_T)} x {float(P.MIN_FEATURE_L)}")

    # Text is the one thing here that is not ours: the font may not resolve, and cq falls
    # back silently. Measure it, do not derive it.
    plain = (cq.Workplane("XY")
             .box(float(P.BODY_WIDTH), float(P.BODY_HEIGHT), TILE_T,
                  centered=(True, True, False))
             .edges("|Z").fillet(float(P.BODY_CORNER_R)))
    raised = text_plaque().val().Volume() - plain.val().Volume()
    t(f"the {P.TEXT_FONT!r} lettering actually rendered", raised > 1.0,
      f"{raised:.1f} mm3 of raised glyph")

    # And it landed where params.sanity() promised, which is the claim the whole vertical
    # layout rests on. Measure the GLYPHS -- the plaque's own bounding box is the plaque,
    # and checking it would pass however far the text overran.
    bb = lettering(TILE_T).val().BoundingBox()
    flat = float(P.BODY_WIDTH) - 2 * float(P.BODY_CORNER_R)
    t("the lettering columns stay on the flat, off the corner radii",
      bb.xlen <= flat + 1e-6, f"columns span {bb.xlen:.1f} mm of {flat:.1f} mm flat")
    t("the lettering stays on the face it runs up",
      bb.ylen <= float(P.BODY_HEIGHT) - 2.0,
      f"{bb.ylen:.1f} mm long, predicted {P.text_width(*P.TEXT_LINES[0]):.1f}, on a "
      f"{float(P.BODY_HEIGHT)} mm face")
    return out


if __name__ == "__main__":
    print("coupon -- Prototype A, the calibration prints\n")
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
