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
P1_W, P1_H, P1_L = 2.5, 2.0, 3.5
# ------------------------------------------------------------- P2 standard ---
P2_WA, P2_WB, P2_H, P2_L, P2_SPACING = 3.0, 2.0, 2.0, 4.0, 10.0
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

P1_KEY = 1.1   # size of the clipped corner. At 0.8 a wrong-way install only fouled by
               # 0.22 mm^3, which a determined thumb would simply crush through.


def _p1_profile(w, h):
    return (cq.Workplane("XY")
            .polyline([(-w / 2, -h / 2), (w / 2, -h / 2),
                       (w / 2, h / 2 - P1_KEY), (w / 2 - P1_KEY, h / 2), (-w / 2, h / 2)])
            .close())


def _p1_solid():
    prof = _p1_profile(P1_W, P1_H).extrude(P1_L)
    prof = try_chamfer(prof, ">Z", P.PEG_TIP_CHAMFER)
    return prof.union(cq.Workplane("XY").box(P1_W, P1_H, PEG_ROOT,
                                             centered=(True, True, False))
                      .translate((0, 0, -PEG_ROOT)))


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
    w, h = P1_W + 2 * c, P1_H + 2 * c
    bore = _p1_profile(w, h).extrude(d)
    bore = bore.union(_leadin(w, h))
    ribs = _rib_solid(w, h, d, c, n=2)
    return _place(bore, point, axis, rot), _place(ribs, point, axis, rot)


def socket_p1(wp, point, axis="+Z", rot=0.0, depth=None, decorative=True):
    cut, add = socket_p1_solids(point, axis, rot, depth, decorative)
    return wp.cut(cut).union(add)


# =========================================================== P2: standard pair ==
def peg_p2(point, axis="+Z", rot=0.0):
    """Two pegs of unequal width -- the part physically cannot go in backwards."""
    out = None
    for dx, w in ((-P2_SPACING / 2, P2_WA), (P2_SPACING / 2, P2_WB)):
        peg = try_chamfer(cq.Workplane("XY").rect(w, P2_H).extrude(P2_L),
                          ">Z", P.PEG_TIP_CHAMFER)
        peg = peg.union(cq.Workplane("XY").box(w, P2_H, PEG_ROOT,
                                               centered=(True, True, False))
                        .translate((0, 0, -PEG_ROOT))).translate((dx, 0, 0))
        out = peg if out is None else out.union(peg)
    return _place(out, point, axis, rot)


def socket_p2_solids(point, axis="+Z", rot=0.0, depth=None, decorative=True):
    c = _clear(decorative)
    d = depth or (P2_L + 0.6)
    bores = ribs = None
    for dx, w in ((-P2_SPACING / 2, P2_WA), (P2_SPACING / 2, P2_WB)):
        ww, hh = w + 2 * c, P2_H + 2 * c
        b = (cq.Workplane("XY").rect(ww, hh).extrude(d)
             .union(_leadin(ww, hh)).translate((dx, 0, 0)))
        bores = b if bores is None else bores.union(b)
        r = _rib_solid(ww, hh, d, c, n=2).translate((dx, 0, 0))
        ribs = r if ribs is None else ribs.union(r)
    return _place(bores, point, axis, rot), _place(ribs, point, axis, rot)


def socket_p2(wp, point, axis="+Z", rot=0.0, depth=None, decorative=True):
    cut, add = socket_p2_solids(point, axis, rot, depth, decorative)
    return wp.cut(cut).union(add)


def _leadin(w, h):
    """Lead-in at the socket mouth, as a shallow counterbore step rather than a 45 deg
    flare. On FDM a flare on a horizontal face prints as a staircase anyway, while a
    0.5 mm oversize entry step prints cleanly, guides the peg in, and clears the
    elephant's foot that would otherwise make every socket undersize."""
    return cq.Workplane("XY").box(w + 2 * P.LEAD_IN_CHAMFER, h + 2 * P.LEAD_IN_CHAMFER,
                                  P.LEAD_IN_CHAMFER, centered=(True, True, False))


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
    c = _clear(decorative)
    g = cq.Workplane("XY").box(length + 2 * c, T3_W + 2 * c, T3_D + extra + c,
                               centered=(True, True, False))
    g = g.union(_leadin(length + 2 * c, T3_W + 2 * c))
    g = g.union(cq.Workplane("XY").sphere(T3_DETENT_R + c)
                .translate((0, T3_W / 2 - 0.1, extra + T3_D / 2)))
    return _place(g, point, axis, rot), None


def groove_t3(wp, point, length, axis="+Z", rot=0.0, decorative=False, extra=0.0):
    cut, _ = groove_t3_solids(point, length, axis, rot, decorative, extra)
    return wp.cut(cut)


# ================================================================ C4: snap clip ==
def c4_clip(length=C4_L, width=C4_W, thick=C4_T, barb=C4_BARB):
    """Cantilever snap, drawn in the XZ plane and extruded along Y so that when it is
    printed lying on its side the layer lines run ALONG the beam, not across it."""
    return (cq.Workplane("XZ")
            .polyline([(0, 0), (length, 0), (length, thick + barb),
                       (length - barb * 1.6, thick), (0, thick)])
            .close().extrude(width))


def c4_catch(wp, point, axis="+Z", rot=0.0, width=C4_W, barb=C4_BARB):
    """The matching ledge the clip snaps behind."""
    c = P.FIT_CLEARANCE
    pocket = cq.Workplane("XY").box(C4_L + 2 * c, width + 2 * c, C4_T + barb + 2 * c,
                                    centered=(True, True, False))
    return wp.cut(_place(pocket, point, axis, rot))


# =========================================================== self-test coupon ===
COUPON_VALUES = [0.20, 0.25, 0.30, 0.35]
COUPON_STATION_W = 26.0
COUPON_H = 34.0
COUPON_T = 6.0
COUPON_P1_Y = 25.0        # the two mount rows, shared by the coupon and the tabs
COUPON_P2_Y = 11.0
TAB_W, TAB_H, TAB_T = 20.0, 24.0, 4.0
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
            plate = _label(plate, f"{v:.2f}", cx, 18.0, COUPON_T)
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
    dy = COUPON_P1_Y - COUPON_P2_Y
    lo = (TAB_H - dy) / 2
    # MIRRORED rows: P1 low, P2 high, so that turning the tab over lands P1 on the
    # station's upper socket and the pair on its lower one.
    tab_p1_y, tab_p2_y = lo, lo + dy
    tabs, sprue = None, None
    for i in range(n):
        # centred in its station, so laying the whole strip on the coupon lines every
        # tab up with its own holes
        x0 = TAB_PITCH * (i + 0.5) - TAB_W / 2
        t = cq.Workplane("XY").box(TAB_W, TAB_H, TAB_T, centered=(False, False, False)) \
            .translate((x0, 0, 0))
        t = t.cut(_corner_mark(x0, 0.0, +1, +1, TAB_T))
        t = t.union(peg_p1((x0 + TAB_W / 2, tab_p1_y, TAB_T), axis="+Z"))
        t = t.union(peg_p2((x0 + TAB_W / 2, tab_p2_y, TAB_T), axis="+Z"))
        t = _label(t, str(i + 1), x0 + TAB_W - 7.0, TAB_H - 6.0, TAB_T, size=3.4)
        tabs = t if tabs is None else tabs.union(t)
        if i:
            # Runner: thin and narrow so it snaps cleanly with a thumbnail. The tabs
            # are meant to come apart -- one tab per station, fresh crush ribs each
            # time -- but the strip also seats as a whole if you would rather.
            gap = TAB_PITCH - TAB_W
            r = cq.Workplane("XY").box(gap + 0.4, 3.0, 0.8, centered=(False, False, False)) \
                .translate((x0 - gap - 0.2, TAB_H / 2 - 1.5, 0))
            sprue = r if sprue is None else sprue.union(r)
    if sprue is not None:
        tabs = tabs.union(sprue)
    return plate, tabs
