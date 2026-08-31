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
    ribs = _rib_solid(w, h, d, n=2)
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
        r = _rib_solid(ww, hh, d, n=2).translate((dx, 0, 0))
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


def _rib_solid(w, h, depth, n=2):
    """Sacrificial crush ribs: they shear on first insertion and give a firm grip
    regardless of the printer's real-world dimensional accuracy.

    Each rib spans from CRUSH_RIB inside the bore to RIB_EMBED inside the wall. The
    embed matters: a rib sized exactly to the bore wall is merely tangent to it, and
    OCCT then leaves it as a detached solid.
    """
    ribs = None
    width = P.CRUSH_RIB + RIB_EMBED
    for sx in (-1, 1):
        for k in range(n):
            zc = depth * (k + 1) / (n + 1)
            r = (cq.Workplane("XY")
                 .box(width, min(h * 0.6, 1.6), depth / (n + 2))
                 .translate((sx * (w / 2 - P.CRUSH_RIB + width / 2), 0, zc)))
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
def tolerance_coupon():
    """Part 70. Print this FIRST: P1 and P2 sockets at four clearances with the value
    engraved beside each, plus loose pegs to test them with. Pick the fit that feels
    right, set it in params.py, re-export everything."""
    base = cq.Workplane("XY").box(96, 34, 6, centered=(False, False, False))
    values = [0.20, 0.25, 0.30, 0.35]
    real_dec, real_fit = P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE
    try:
        for i, v in enumerate(values):
            P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
            cx = 12 + i * 23
            base = socket_p1(base, (cx, 25, 6), axis="-Z")
            base = socket_p2(base, (cx, 11, 6), axis="-Z")
            try:
                base = (base.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                        .center(cx - 48, 15.0)
                        .text(f"{v:.2f}", 3.2, -0.4, font="DejaVu Sans",
                              kind="bold", combine="cut"))
            except Exception:
                pass
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real_dec, real_fit
    pegs = cq.Workplane("XY").box(46, 16, 3, centered=(False, False, False))
    pegs = pegs.union(peg_p1((10, 8, 3), axis="+Z"))
    pegs = pegs.union(peg_p2((30, 8, 3), axis="+Z"))
    return base, pegs.translate((0, 40, 0))
