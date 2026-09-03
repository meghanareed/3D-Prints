"""DA-Mount: the one connector family used across the whole kit.

Four types, each with a matched peg/socket pair so clearances can never drift apart:

    P1  micro   one keyed peg               signs, brackets, small props
    P2  standard two pegs, unequal widths   window frames, doors, lanterns, awnings
    T3  tongue  sliding tongue + detent     shopfronts, bays, walls, floor
    C4  clip    cantilever snap             outer case, hatch, switch housing

Two rules are load-bearing and must not be "cleaned up":
  * every socket mouth gets a 45 deg lead-in chamfer, or first-layer squish and
    elephant's foot make every socket undersize and the kit will not assemble;
  * grip comes from sacrificial crush ribs, not from a tight nominal fit, so the
    kit tolerates printer-to-printer variation.
"""
import cadquery as cq
import params as P
from lib.util import try_chamfer

PEG_ROOT = 1.0   # Every peg starts this far INSIDE its parent. Sized exactly to the
                 # surface it stands on, a peg is only tangent and OCCT leaves it a
                 # separate solid -- brackets, lanterns and barrels all came out in two
                 # pieces on the first build. 0.4 was still too thin an overlap for
                 # OCCT to fuse reliably against a narrow arm, hence 1.0.

# ------------------------------------------------------------------ P1 micro --
# ROUND, with one flat, and no crush ribs. The rectangular version did not work and
# could not have: a round nozzle cannot cut a sharp internal corner, so a printed
# socket has corners radiused to about half the line width -- 0.21 mm on a 0.4 mm
# nozzle -- while the peg's external corners print sharp. The two bind on the diagonal
# before their flats ever touch, and a hole that prints 0.2 mm undersize (which is
# normal) makes it certain. docs/08_JOINT_DESIGN.md has the arithmetic.
#
# The flat gives anti-rotation without a single 90 degree internal corner: where it
# meets the arc the bore turns through an obtuse angle, which a round nozzle traces
# accurately. The crush ribs are gone -- they asked for 0.15 mm of interference from a
# machine whose XY repeatability is +/-0.20, and each rib was a 0.40 mm protrusion
# where the minimum dependable feature on this nozzle is 1.2 mm.
P1_D, P1_FLAT, P1_L = 2.4, 1.0, 3.5     # dia, flat this far off axis, length
# ------------------------------------------------------------- P2 standard ---
# Two ROUND pegs of unequal diameter. The pair prevents rotation and the difference in
# diameter is the key: the part physically cannot go in backwards.
P2_DA, P2_DB, P2_L, P2_SPACING = 2.8, 2.0, 4.0, 10.0
# ----------------------------------------------------------------- T3 tongue --
T3_W, T3_D = 4.0, 2.5
T3_DETENT_R, T3_DETENT_L = 0.5, 6.0
# ------------------------------------------------------------------- C4 clip --
C4_L, C4_W, C4_T, C4_BARB = 14.0, 4.0, 2.0, 0.9


def _clear(decorative):
    return P.DECORATIVE_CLEARANCE if decorative else P.FIT_CLEARANCE


_AXIS_ROT = {
    "+Z": None,
    "-Z": ((1, 0, 0), 180),
    "+Y": ((1, 0, 0), -90),
    "-Y": ((1, 0, 0), 90),
    "+X": ((0, 1, 0), 90),
    "-X": ((0, 1, 0), -90),
}


def _place(solid, point, axis="+Z", rot=0.0):
    """Orient a +Z-built feature along `axis` and move its base to `point`.

    Everything in this library is built standing on +Z at the origin and then placed
    explicitly, rather than relying on face workplanes -- face workplane axes are not
    predictable enough to trust across a hundred parts.
    """
    if rot:
        solid = solid.rotate((0, 0, 0), (0, 0, 1), rot)
    r = _AXIS_ROT[axis]
    if r is not None:
        solid = solid.rotate((0, 0, 0), r[0], r[1])
    return solid.translate(point)


# ============================================================== P1: micro peg ==
#
# THE RECURRING BUG IN THIS FILE: A MATING PART IS A MIRROR, NOT A COPY.
#
# Two parts that join are brought together by turning one of them over, and turning a
# part over mirrors it. Generating the second part in the same frame as the first looks
# correct in CAD, renders correctly, and does not fit. It has been shipped three times
# here: wall sockets built as the mirror of their pegs, paint handles given a peg where
# they needed a socket, and coupon tabs built as a copy of the station instead of its
# mirror. Every one of them was caught by a person looking at the printed part, not by
# the geometry checks.
#
# So: whenever you add a mating pair, add a check to verify.py that applies the REAL
# physical transform -- the flip, the rotation into place -- and measures the
# interference. Not a check that the two halves were built from the same numbers.
#
# CONVENTION -- read this before changing anything below.
#
# `axis` is the direction the PEG TRAVELS, for both the peg and its socket. A socket
# is therefore built as the oversized swept volume of the peg it receives, oriented
# identically, so the two are registered by construction.
#
# The earlier version took the wall's outward normal for the socket and the part's
# outward normal for the peg. Those are opposite directions, which mirrors the keyed
# cross-section: every P2 pair landed wide-peg-in-narrow-hole and fouled by 20 mm^3.

def _d_solid(dia, flat, length, root=0.0):
    """A D-section prism: a cylinder with one chord flattened `flat` off the axis."""
    body = cq.Workplane("XY").circle(dia / 2).extrude(length)
    if root:
        body = body.union(cq.Workplane("XY").circle(dia / 2)
                          .extrude(root).translate((0, 0, -root)))
    keep = cq.Workplane("XY").box(dia + 2, dia + 2, length + root + 2,
                                  centered=(True, False, False))
    return body.cut(keep.translate((0, flat, -root - 1)))


def _p1_solid():
    peg = _d_solid(P1_D, P1_FLAT, P1_L, root=PEG_ROOT)
    return try_chamfer(peg, ">Z", P.PEG_TIP_CHAMFER)


def peg_p1(point, axis="+Z", rot=0.0):
    """Keyed micro peg. The clipped corner means it cannot seat rotated 180 deg."""
    return _place(_p1_solid(), point, axis, rot)


def socket_p1_solids(point, axis="+Z", rot=0.0, depth=None, decorative=True):
    """Bore for a peg travelling along `axis` from `point`.

    Returns (cut_solid, add_solid) so a wall can batch hundreds of mounts into two
    booleans instead of hundreds.
    """
    c = _clear(decorative)
    d = depth or (P1_L + 0.6)
    bore = _d_solid(P1_D + 2 * c, P1_FLAT + c, d)
    bore = bore.union(_leadin_round(P1_D + 2 * c))
    return _place(bore, point, axis, rot), None


def socket_p1(wp, point, axis="+Z", rot=0.0, depth=None, decorative=True):
    cut, _ = socket_p1_solids(point, axis, rot, depth, decorative)
    return wp.cut(cut)


# =========================================================== P2: standard pair ==
def peg_p2(point, axis="+Z", rot=0.0):
    """Two round pegs of unequal diameter -- the part cannot go in backwards."""
    out = None
    for dx, dia in ((-P2_SPACING / 2, P2_DA), (P2_SPACING / 2, P2_DB)):
        peg = cq.Workplane("XY").circle(dia / 2).extrude(P2_L)
        peg = try_chamfer(peg, ">Z", P.PEG_TIP_CHAMFER)
        peg = peg.union(cq.Workplane("XY").circle(dia / 2).extrude(PEG_ROOT)
                        .translate((0, 0, -PEG_ROOT))).translate((dx, 0, 0))
        out = peg if out is None else out.union(peg)
    return _place(out, point, axis, rot)


def socket_p2_solids(point, axis="+Z", rot=0.0, depth=None, decorative=True):
    c = _clear(decorative)
    d = depth or (P2_L + 0.6)
    bores = None
    for dx, dia in ((-P2_SPACING / 2, P2_DA), (P2_SPACING / 2, P2_DB)):
        b = (cq.Workplane("XY").circle(dia / 2 + c).extrude(d)
             .union(_leadin_round(dia + 2 * c)).translate((dx, 0, 0)))
        bores = b if bores is None else bores.union(b)
    return _place(bores, point, axis, rot), None


def socket_p2(wp, point, axis="+Z", rot=0.0, depth=None, decorative=True):
    cut, _ = socket_p2_solids(point, axis, rot, depth, decorative)
    return wp.cut(cut)


def _leadin(w, h):
    """Lead-in at the socket mouth, as a shallow counterbore step rather than a 45 deg
    flare. On FDM a flare on a horizontal face prints as a staircase anyway, while a
    0.5 mm oversize entry step prints cleanly, guides the peg in, and clears the
    elephant's foot that would otherwise make every socket undersize."""
    return cq.Workplane("XY").box(w + 2 * P.LEAD_IN_CHAMFER, h + 2 * P.LEAD_IN_CHAMFER,
                                  P.LEAD_IN_CHAMFER, centered=(True, True, False))


def _leadin_round(dia):
    """The same counterbore step for a round bore. T3 keeps the rectangular one: it is
    a sliding tongue, it was validated on a printed coupon, and it is not being
    redesigned on the strength of a problem that belongs to the peg mounts."""
    return (cq.Workplane("XY").circle(dia / 2 + P.LEAD_IN_CHAMFER)
            .extrude(P.LEAD_IN_CHAMFER))


RIB_EMBED = 0.6   # how far a crush rib buries itself in the parent material


def _rib_solid(w, h, depth, clearance, n=2):
    """Sacrificial crush ribs: they shear on first insertion and give a firm grip
    regardless of the printer's real-world dimensional accuracy.

    Each rib runs from CRUSH_INTERFERENCE inside the PEG's surface out to RIB_EMBED
    inside the parent material. Sizing it from the clearance is the whole point: a rib
    of fixed height measured from the BORE wall stops reaching the peg as soon as the
    clearance grows past that height, and then nothing grips. With the old fixed
    0.30 rib, setting FIT_CLEARANCE to 0.30 or 0.35 -- which the tolerance coupon
    invites you to do -- silently gave every part in the kit zero retention.

    The embed matters too: a rib sized exactly to the bore wall is merely tangent to
    it, and OCCT leaves it as a detached solid.
    """
    ribs = None
    peg_half = w / 2 - clearance
    inner = peg_half - P.CRUSH_INTERFERENCE
    outer = w / 2 + RIB_EMBED
    width = outer - inner
    for sx in (-1, 1):
        for k in range(n):
            zc = depth * (k + 1) / (n + 1)
            r = (cq.Workplane("XY")
                 .box(width, min(h * 0.6, 1.6), depth / (n + 2))
                 .translate((sx * (inner + width / 2), 0, zc)))
            ribs = r if ribs is None else ribs.union(r)
    return ribs


# ============================================================== T3: tongue ======
def tongue_t3(point, length, axis="+Z", rot=0.0, extra=0.0):
    """`extra` lengthens the root so a tongue can bridge a standoff gap before it
    engages its groove."""
    t = try_chamfer(cq.Workplane("XY").box(length, T3_W, T3_D + extra,
                                           centered=(True, True, False)), ">Z", 0.4)
    t = t.union(cq.Workplane("XY").box(length, T3_W, PEG_ROOT,
                                       centered=(True, True, False))
                .translate((0, 0, -PEG_ROOT)))
    t = t.union(cq.Workplane("XY").sphere(T3_DETENT_R)
                .translate((0, T3_W / 2 - 0.1, extra + T3_D / 2)))
    return _place(t, point, axis, rot)


def groove_t3_solids(point, length, axis="+Z", rot=0.0, decorative=False, extra=0.0):
    """Returns (cut_solid, rib_solid) -- the second one has to be UNIONED BACK IN.

    T3 used to return no ribs and rely on the detent alone, and the detent does
    essentially nothing: its pocket was cut at T3_DETENT_R + clearance, so a 0.5 mm
    ball dropped into it with a quarter-millimetre of slop all round. Withdrawing the
    tongue measured 0.008 mm^3 of interference at its worst, against the ~1.8 mm^3 a
    P1 crush rib gives -- and T3 is what holds every wall face to its rib and the floor
    to the base pan. The ribs below are the same ones P1 and P2 use; the detent is now
    just the click that tells you the tongue is home.
    """
    # T3 runs on its own clearance: it is a sliding joint, and the printed coupon put
    # it a step looser than the press and snap mounts. `decorative` still overrides,
    # for the few decorative parts that carry a tongue.
    c = P.DECORATIVE_CLEARANCE if decorative else P.T3_CLEARANCE
    depth = T3_D + extra + c
    g = cq.Workplane("XY").box(length + 2 * c, T3_W + 2 * c, depth,
                               centered=(True, True, False))
    g = g.union(_leadin(length + 2 * c, T3_W + 2 * c))
    g = g.union(cq.Workplane("XY").sphere(T3_DETENT_R + c - P.CRUSH_INTERFERENCE)
                .translate((0, T3_W / 2 - 0.1, extra + T3_D / 2)))
    # ribs live on the FLANKS (+/-Y), so the rib solid is turned a quarter turn before
    # it is placed; _place then applies `rot` and the axis on top of that
    ribs = _rib_solid(T3_W + 2 * c, T3_D + 2 * c, depth, c, n=2) \
        .rotate((0, 0, 0), (0, 0, 1), 90)
    return _place(g, point, axis, rot), _place(ribs, point, axis, rot)


def groove_t3(wp, point, length, axis="+Z", rot=0.0, decorative=False, extra=0.0):
    cut, add = groove_t3_solids(point, length, axis, rot, decorative, extra)
    return wp.cut(cut).union(add)


# ================================================================ C4: snap clip ==
#
# A cantilever snap holds only if three things are true. The first version of this
# joint had none of them, and nothing caught it because a clip lying loose in an
# oversized hole is perfectly valid geometry.
#
#   1. The hook's shallow ramp must face the TIP, so the clip can be pushed in, and its
#      steep retention face must look back toward the root, so it cannot be pulled out.
#      The original profile was exactly reversed: a blunt full-height wall at the tip,
#      which cannot enter anything, and the ramp behind it, which nothing catches on.
#   2. The catch must be a WINDOW the barb springs into, not a pocket the whole clip
#      drops into. The original catch cut box(C4_L + 2c, C4_W + 2c, C4_T + barb + 2c) --
#      a rectangular hole 0.5 mm larger than the clip in every direction.
#   3. Withdrawal must be measurable. Seated, and then pulled back by 0.4, 1.0 and
#      2.0 mm, the original clip and catch intersected in 0.000 mm^3 every time. This
#      was the only thing holding 750 g of outer case together.
#
# STANDARD C4 FRAME, the same convention the rest of this file uses: the clip travels
# along `axis`, its barb springs toward local +Y, its width runs along local X, and the
# window is cut in the plate that lies on the +Y side. Build a clip and a window with
# the SAME (point, axis, rot) and they mate.
#
C4_L, C4_W, C4_T, C4_BARB = 14.0, 4.0, 2.0, 0.9
C4_RAMP, C4_RETAIN = 2.6, 0.6        # insertion-ramp run / retention-face run
C4_ENGAGE = C4_RAMP + C4_RETAIN      # tip -> retention face


def _c4_profile(length, thick, barb):
    """The clip seen edge-on, drawn in XZ: beam along +X, thickness along +Z.

    Going around: the underside from the buried root to the tip, up the (thin) tip
    face, back along the shallow insertion ramp to the crest, down the steep retention
    face, and home along the top.
    """
    crest = length - C4_RAMP
    heel = crest - C4_RETAIN
    return (cq.Workplane("XZ")
            .polyline([(-PEG_ROOT, 0), (length, 0), (length, thick),
                       (crest, thick + barb), (heel, thick), (-PEG_ROOT, thick)])
            .close())


def c4_clip(length=C4_L, width=C4_W, thick=C4_T, barb=C4_BARB):
    """The clip in its own build frame: beam along +X, barb toward +Z, width along +Y.

    Extruded along Y so that when it is printed lying on its side the layer lines run
    ALONG the beam and not across it -- a cantilever with the layers across it snaps
    off at the root the first time it is flexed.
    """
    c = _c4_profile(length, thick, barb).extrude(width)
    return c.translate((0, width, 0))          # XZ extrudes toward -Y; bring it back


def _c4_standard(length, width, thick, barb):
    """The clip re-cut into the standard frame: travels +Z, barb springs +Y, width X."""
    c = c4_clip(length, width, thick, barb)          # beam +X, barb +Z, width +Y
    c = c.translate((0, -width / 2.0, -thick / 2.0))  # centre width and thickness
    return c.rotate((0, 0, 0), (1, 1, 1), -120)       # x->z, z->y, y->x


def c4_clip_at(point, axis="+Z", rot=0.0, length=C4_L, width=C4_W):
    """A clip placed like any other mount in this library."""
    return _place(_c4_standard(length, width, C4_T, C4_BARB), point, axis, rot)


def c4_window_solids(point, axis="+Z", rot=0.0, width=C4_W, length=C4_L, plate_t=None):
    """The window the barb springs into, in the same frame as `c4_clip_at`.

    Cut through the plate lying on the +Y side of the clip. The window's near edge sits
    at the clip's retention face, so pulling the joint back drives that face straight
    into the plate: retention is interference, and `verify.py` measures it.
    """
    c = P.FIT_CLEARANCE
    plate_t = P.SHELL_THICKNESS if plate_t is None else plate_t
    heel = length - C4_RAMP - C4_RETAIN
    win = (cq.Workplane("XY")
           .box(width + 2 * c, plate_t + 4.0, C4_ENGAGE + 2 * c,
                centered=(True, False, False))
           .translate((0, C4_T / 2.0, heel)))
    return _place(win, point, axis, rot), None


def c4_window(wp, point, axis="+Z", rot=0.0, width=C4_W, length=C4_L, plate_t=None):
    cut, _ = c4_window_solids(point, axis, rot, width, length, plate_t)
    return wp.cut(cut)


def c4_catch(wp, point, axis="+Z", rot=0.0, width=C4_W, barb=C4_BARB, plate_t=None):
    """Kept for callers that still say `catch`. It is a window now, not a pocket."""
    return c4_window(wp, point, axis, rot, width=width, plate_t=plate_t)


# =========================================================== self-test coupon ===
COUPON_VALUES = [0.20, 0.25, 0.30, 0.35]
COUPON_STATION_W = 26.0
COUPON_H = 34.0
COUPON_T = 6.0
COUPON_P1_Y = 25.0        # the two mount rows, shared by the coupon and the tabs
COUPON_P2_Y = 11.0
TAB_W, TAB_H, TAB_T = 20.0, 24.0, 4.0
# the tab is centred between the two socket rows, so it covers this band of the station
TAB_Y0 = COUPON_P2_Y + (COUPON_P1_Y - COUPON_P2_Y) / 2 - TAB_H / 2
TAB_Y1 = TAB_Y0 + TAB_H
LABEL_Y = TAB_Y0 / 2 - 1.0      # clear of the tab, near the bottom edge
TAB_PITCH = COUPON_STATION_W    # the tabs MUST sit on the station pitch. At 25 mm on a
                                # 26 mm station pitch they drifted 1 mm per station, so
                                # only the first tab could ever enter its holes -- the
                                # rest sat on the surface with their pegs looking far
                                # too long. Off by 1 mm against a 0.2 mm clearance is
                                # simply a wall.


def _label(solid, txt, x, y, top_z, size=4.2):
    """Raised lettering, built as its own solid and fused.

    Not `faces(">Z").text(..., combine="cut")`: the first cut splits the top face, the
    next call then selects several faces and throws, and the surrounding try/except
    silently swallowed it. Three of the coupon's four labels were missing because of
    exactly that.
    """
    try:
        t = (cq.Workplane("XY", origin=(x, y, top_z - 0.4))
             .text(txt, size, 0.9, font="DejaVu Sans", kind="bold"))
        return solid.union(t)
    except Exception as e:
        print(f"  !! coupon label {txt!r} failed to render: {e}")
        return solid


def _corner_mark(x, y, sx, sy, t, leg=4.0):
    """A 45-degree corner cut, used as an orientation mark on both the coupon stations
    and the tabs."""
    return (cq.Workplane("XY")
            .polyline([(x, y), (x + sx * leg, y), (x, y + sy * leg)])
            .close().extrude(t * 2).translate((0, 0, -t * 0.5)))


def tolerance_coupon():
    """Part 70. Print this FIRST.

    Four stations, each with a P1 socket and a keyed P2 pair cut at a different
    clearance, with the value raised beside it. Four loose tabs carry nominal pegs at
    the matching spacing, so one tab presses into one station and tests both mount
    types at once.

    A fresh tab per station matters: crush ribs shear on first insertion, and reusing
    one peg burnishes it and biases every test after the first.

    THE TAB IS THE MIRROR OF THE STATION, NOT A COPY. You turn the tab over to use it,
    and turning it over about its long axis mirrors the rows -- so the tab carries its
    P1 peg on the row where the station carries its P2 pair. Built as a straight copy
    (which is how it shipped first) the tab cannot seat in any orientation: tip it
    toward you and the single peg meets the pair of holes; turn it sideways instead and
    the keyed pair swaps wide-for-narrow. A chamfered corner on both parts shows which
    way round it goes.
    """
    n = len(COUPON_VALUES)
    plate = cq.Workplane("XY").box(COUPON_STATION_W * n, COUPON_H, COUPON_T,
                                   centered=(False, False, False))
    real_dec, real_fit = P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE
    try:
        for i, v in enumerate(COUPON_VALUES):
            P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
            cx = COUPON_STATION_W * (i + 0.5)
            plate = socket_p1(plate, (cx, COUPON_P1_Y, COUPON_T), axis="-Z")
            plate = socket_p2(plate, (cx, COUPON_P2_Y, COUPON_T), axis="-Z")
            # The label goes BELOW the tab's footprint. Raised text at the centre of
            # the station is 0.5 mm proud and the tab lands squarely on it, holding
            # the part 0.5 mm off the surface -- which reads exactly like a fit that
            # will not seat.
            plate = _label(plate, f"{v:.2f}", cx, LABEL_Y, COUPON_T)
            # alignment mark: the station's TOP-LEFT corner is chamfered, and so is the
            # tab's BOTTOM-LEFT. Turning the tab over brings the two marks together.
            plate = plate.cut(_corner_mark(cx - COUPON_STATION_W / 2, COUPON_H,
                                           +1, -1, COUPON_T))
            if i:                       # a groove between stations, findable by feel
                plate = plate.cut(cq.Workplane("XY")
                                  .box(1.2, COUPON_H, 1.0, centered=(True, False, False))
                                  .translate((COUPON_STATION_W * i, 0, COUPON_T - 1.0)))
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real_dec, real_fit

    # four loose tabs, pegs at the same row spacing as the stations
    tabs, sprue = None, None
    for i in range(n):
        t = coupon_tab(i)
        tabs = t if tabs is None else tabs.union(t)
        if i:
            # Runner: thin and narrow so it snaps cleanly with a thumbnail. The tabs
            # are meant to come apart -- one tab per station, fresh crush ribs each
            # time -- but the strip also seats as a whole if you would rather.
            gap = TAB_PITCH - TAB_W
            x0 = TAB_PITCH * (i + 0.5) - TAB_W / 2
            r = cq.Workplane("XY").box(gap + 0.4, 3.0, 0.8, centered=(False, False, False)) \
                .translate((x0 - gap - 0.2, TAB_H / 2 - 1.5, 0))
            sprue = r if sprue is None else sprue.union(r)
    if sprue is not None:
        tabs = tabs.union(sprue)
    return plate, tabs


def coupon_tab(i):
    """One test tab, positioned over station `i`. Single definition, so the strip and
    the verification both use exactly this."""
    dy = COUPON_P1_Y - COUPON_P2_Y
    lo = (TAB_H - dy) / 2
    # MIRRORED rows: P1 low, P2 high, so that turning the tab over lands P1 on the
    # station's upper socket and the pair on its lower one.
    tab_p1_y, tab_p2_y = lo, lo + dy
    x0 = TAB_PITCH * (i + 0.5) - TAB_W / 2
    t = cq.Workplane("XY").box(TAB_W, TAB_H, TAB_T, centered=(False, False, False)) \
        .translate((x0, 0, 0))
    t = t.cut(_corner_mark(x0, 0.0, +1, +1, TAB_T))
    t = t.union(peg_p1((x0 + TAB_W / 2, tab_p1_y, TAB_T), axis="+Z"))
    t = t.union(peg_p2((x0 + TAB_W / 2, tab_p2_y, TAB_T), axis="+Z"))
    # the number goes on the peg face, clear of the pegs, so it is not trapped
    # between the tab and the coupon when seated
    return _label(t, str(i + 1), x0 + TAB_W - 5.0, 3.0, TAB_T, size=3.0)


def seat_tab(i):
    """The tab of station `i`, turned over and dropped into its station -- the real
    physical motion, for checking against the real coupon."""
    dy = COUPON_P1_Y - COUPON_P2_Y
    x0 = TAB_PITCH * (i + 0.5) - TAB_W / 2
    cx = x0 + TAB_W / 2
    t = coupon_tab(i).rotate((cx, TAB_H / 2, TAB_T / 2), (cx + 1, TAB_H / 2, TAB_T / 2), 180)
    bb = t.val().BoundingBox()
    return t.translate((0, COUPON_P2_Y + dy / 2 - TAB_H / 2, COUPON_T - bb.zmin - TAB_T))


# ================================================ joint coupon: T3 and C4 =====
# The first coupon tests P1 and P2 -- the decorative mounts. It never touched the two
# joints that carry the model: T3, which holds every wall face to its rib and the floor
# to the base pan, and C4, which is all that holds the outer case together. Both were
# taken on trust, and both were broken (see the notes on `groove_t3_solids` and on the
# C4 section above).
#
# Every station here is built from the SAME (point, axis, rot) as the piece that mates
# with it, which is the library's one rule for a pair that fits. `verify.py` then seats
# each loose piece against the real block and measures the interference on the way in
# and the grip on the way out.

JC_T = 6.0                      # block thickness -- a calibration print should be cheap
JC_STATION_W = 30.0             # one station
JC_H = 62.0
JC_T3_LEN = 24.0
JC_FIN_T = 2.2                  # = SHELL_THICKNESS: the case wall a case clip snaps in
JC_FIN_H = 18.0
JC_FIN_W = 24.0
JC_VALUES = (0.25, 0.30)        # a sliding joint wants a looser fit than a press joint
JC_STATIONS = [("T3", v) for v in JC_VALUES] + [("C4", v) for v in JC_VALUES]
JC_W = JC_STATION_W * len(JC_STATIONS)

JC_T3_Y = 40.0                  # where the tongue lands, in block coordinates
JC_FIN_Y = 34.0                 # the fin's near face
JC_TAB_W, JC_TAB_H, JC_TAB_T = 26.0, 15.0, 3.5
JC_CAP_W, JC_CAP_H, JC_CAP_T = 26.0, 16.0, 3.5


def _jc_x(i):
    return JC_STATION_W * (i + 0.5)


def _jc_save():
    return (P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE, P.T3_CLEARANCE)


def _jc_restore(saved):
    P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE, P.T3_CLEARANCE = saved


def _jc_set(kind, v):
    """Each station drives the parameter its own joint actually reads.

    These used to be set together, which was fine while every joint shared one
    clearance and wrong the moment the printed coupon said C4 wanted 0.25 and T3
    wanted 0.30. A station that does not move the number its joint reads is testing
    nothing.
    """
    if kind == "T3":
        P.T3_CLEARANCE = v
    else:
        P.FIT_CLEARANCE = v


def _jc_clip_geometry(i):
    """Where station `i`'s clip lives: (x, y of the beam centre, z of its root).

    The cap lands on the fin's top edge, so the clip's root is at that height and it
    travels straight down the fin's near face.
    """
    y = JC_FIN_Y - P.FIT_CLEARANCE - C4_T / 2.0
    return _jc_x(i), y, JC_T + JC_FIN_H


def joint_coupon():
    """Parts 74A/74B. Print after the P1/P2 coupon and BEFORE committing to the case.

    Four stations: T3 at 0.25 and 0.30, then C4 at 0.25 and 0.30. The T3 stations are
    grooves in the top face; the C4 stations are upright fins with a window through
    them, which is the outer case's joint at full size.
    """
    block = cq.Workplane("XY").box(JC_W, JC_H, JC_T, centered=(False, False, False))
    adds, cuts = [], []
    real = _jc_save()
    try:
        for i, (kind, v) in enumerate(JC_STATIONS):
            _jc_set(kind, v)
            cx = _jc_x(i)
            if kind == "T3":
                cut, ribs = groove_t3_solids((cx, JC_T3_Y, JC_T), JC_T3_LEN, axis="-Z")
                cuts.append(cut)
                adds.append(ribs)
                # a clipped corner in the block matching the one on the tab. A T3
                # tongue has no key, so turning the tab over the wrong way still drops
                # it in -- with the detent against a solid wall instead of its pocket.
                # Line the two marks up and it cannot be wrong.
                cuts.append(_corner_mark(cx - JC_TAB_W / 2, JC_T3_Y - JC_TAB_H / 2,
                                         +1, +1, 1.2).translate((0, 0, JC_T - 0.6)))
            else:
                fin = cq.Workplane("XY").box(JC_FIN_W, JC_FIN_T, JC_FIN_H,
                                             centered=(True, False, False)) \
                    .translate((cx, JC_FIN_Y, JC_T - PEG_ROOT))
                x, y, z = _jc_clip_geometry(i)
                win, _ = c4_window_solids((x, y, z), axis="-Z", rot=180,
                                          plate_t=JC_FIN_T)
                adds.append(fin.cut(win))
            # the label goes clear of everything the mating piece touches -- a raised
            # label under a seated part holds it half a millimetre off the surface, and
            # that is exactly what went wrong on the first coupon
            block = _label(block, f"{kind} {v:.2f}", cx, 6.0, JC_T, size=4.2)
    finally:
        _jc_restore(real)
    for c in cuts:
        block = block.cut(c)
    for a in adds:
        block = block.union(a)
    return block


def jc_piece(i):
    """The loose piece for station `i`, IN ITS SEATED POSITION on the block.

    Built from the same (point, axis, rot) as the station it mates with, which is the
    only thing that guarantees a pair fits. `build.py` turns it over for printing.
    """
    kind, v = JC_STATIONS[i]
    cx = _jc_x(i)
    real = _jc_save()
    try:
        _jc_set(kind, v)
        if kind == "T3":
            tab = cq.Workplane("XY").box(JC_TAB_W, JC_TAB_H, JC_TAB_T,
                                         centered=(True, True, False)) \
                .translate((cx, JC_T3_Y, JC_T))
            tab = tab.union(tongue_t3((cx, JC_T3_Y, JC_T), JC_T3_LEN, axis="-Z"))
            tab = tab.cut(_corner_mark(cx - JC_TAB_W / 2, JC_T3_Y - JC_TAB_H / 2,
                                       +1, +1, JC_TAB_T * 4).translate((0, 0, JC_T)))
            return tab
        x, y, z = _jc_clip_geometry(i)
        cap = cq.Workplane("XY").box(JC_CAP_W, JC_CAP_H, JC_CAP_T,
                                     centered=(True, True, False)) \
            .translate((cx, JC_FIN_Y + JC_FIN_T / 2.0, z))
        cap = cap.union(c4_clip_at((x, y, z), axis="-Z", rot=180))
        # a plain guide skirt down the fin's far face, so the cap cannot skew off
        far = JC_FIN_Y + JC_FIN_T + P.FIT_CLEARANCE
        cap = cap.union(cq.Workplane("XY").box(JC_CAP_W, 2.0, C4_L,
                                               centered=(True, False, False))
                        .translate((cx, far, z - C4_L)))
        return cap
    finally:
        _jc_restore(real)


def joint_coupon_pieces():
    """Part 74B: the four loose pieces, turned over and laid out for printing.

    Each piece is authored in the position it occupies when it is seated -- tongue
    down, clip down -- so the flip here is what makes it printable. It is a rotation,
    not a mirror: turn the printed piece back over about the same axis and it is
    exactly the part that was checked against the block.
    """
    out = None
    for i in range(len(JC_STATIONS)):
        p = jc_piece(i).rotate((0, JC_T3_Y, 0), (1, JC_T3_Y, 0), 180)
        b = p.val().BoundingBox()
        p = p.translate((0, -b.ymin + 4.0, -b.zmin))
        out = p if out is None else out.union(p)
    # A runner along the front edge, so this exports as one solid rather than four
    # loose pieces the slicer will happily arrange somewhere else. Overlaps each piece
    # by 1.5 mm -- a sprue merely tangent to a part does not fuse. Snap them off.
    b = out.val().BoundingBox()
    runner = cq.Workplane("XY").box(b.xlen, 3.0, 1.2, centered=(False, False, False)) \
        .translate((b.xmin, 2.5, 0))
    return out.union(runner)
