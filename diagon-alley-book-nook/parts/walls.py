"""The two wall assemblies.

Each wall is TWO printable parts:
    <side>_Wall_Face    2.5 mm brick plate, prints brick-up, gets painted
    <side>_Wall_Rib     7.5 mm open service lattice, prints flat, never seen

Splitting them is what makes the fairy-light wiring possible: the rib carries every
bead pocket, channel and coil bay, and can be lifted off again to re-route a string.
A solid 197 x 203 x 7.5 backing would have been ~140 g of PLA per wall, so the rib is
an open lattice -- perimeter rails plus a vertical rib at each bead column.
"""
import math
import cadquery as cq
import params as P
import data.facade as F
from lib.brick import brick_field
from lib.light import bead_pocket, wire_channel, coil_bay
from lib.mount import (peg_p2, socket_p2, socket_p2_solids, tongue_t3, groove_t3,
                       groove_t3_solids, socket_p1)
from lib.util import compound, batch_cut, batch_add, keep_largest
from lib.util import try_chamfer
from parts.decor import build_element, FACE, to_wall

WALL_LEN = P.CHASSIS_D
WALL_H   = P.SCENE_H
BEZEL_W  = 16.0          # front torn-brick bezel width
RIB_W    = 5.0           # lattice rib width
JOIN_PITCH = 46.0        # face <-> rib T3 joints


def break_profile(z, tag="break", amp=9.0, base=4.0):
    """Jagged front edge: the break steps along whole brick courses, the way a real
    demolished wall fails, rather than following a smooth curve."""
    from lib.util import rng
    r = rng(tag)
    course = P.BRICK_HEIGHT_FRONT + P.MORTAR_GAP
    steps = int(WALL_H / course) + 2
    if not hasattr(break_profile, "_cache"):
        break_profile._cache = {}
    if tag not in break_profile._cache:
        vals, cur = [], base + amp * 0.5
        for _ in range(steps):
            cur += r.uniform(-amp * 0.55, amp * 0.55)
            cur = max(base, min(base + amp, cur))
            vals.append(cur)
        break_profile._cache[tag] = vals
    vals = break_profile._cache[tag]
    return vals[min(int(z / course), len(vals) - 1)]


def _dedupe(pts, eps=1e-6):
    """Drop repeated consecutive points -- a staircase profile produces them whenever
    two courses break at the same depth, and OCCT refuses a zero-length edge."""
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    return out


def _rows(side):
    return F.LEFT if side == "L" else F.RIGHT


_COLLECT_CACHE = {}


def collect(side):
    """Run every facade row for one side once, and cache it -- the face, the rib and
    the exporter all need the same result and each row costs real time to build."""
    if side not in _COLLECT_CACHE:
        parts, cuts, adds, beads = [], [], [], []
        for row in _rows(side):
            p, (c, a), b = build_element(row, side)
            parts += p
            cuts += c
            adds += a
            beads += b
        # signs, brackets, lanterns and the wall-hung props mount into the same wall
        from parts import kit as K
        kc, ka = K.wall_mount_cuts(side)
        cuts += kc
        adds += ka
        beads += K.sign_beads(side) + K.lantern_beads(side)
        _COLLECT_CACHE[side] = (parts, cuts, adds, beads)
    return _COLLECT_CACHE[side]


# ------------------------------------------------------------------- face ----
def wall_face(side):
    tag = f"brick_{side}"
    plate = cq.Workplane("XY").box(FACE, WALL_LEN, WALL_H, centered=(False, False, False))

    # torn front edge, as one staircase profile rather than 30 unioned boxes
    course = P.BRICK_HEIGHT_FRONT + P.MORTAR_GAP
    pts, z = [(0.0, 0.0)], 0.0
    while z < WALL_H:
        u = break_profile(z, tag)
        zt = min(z + course, WALL_H)
        pts += [(u, z), (u, zt)]
        z = zt
    pts += [(0.0, WALL_H)]
    pts = _dedupe(pts)
    step = (cq.Workplane("XY").polyline(pts).close().extrude(FACE * 3)
            .rotate((0, 0, 0), (1, 1, 1), 120).translate((-FACE, 0, 0)))
    plate = plate.cut(step)

    # every element's apertures, recesses and mount sockets -- two booleans total
    _, cuts, adds, _ = collect(side)
    cuts = list(cuts)
    adds = list(adds)

    # T3 joints to the service rib, and P2 sockets for the front bezel
    for u in _join_positions():
        c, _ = groove_t3_solids((0.0, u, WALL_H * 0.5), 30.0, axis="+X", rot=90,
                                extra=P.RIB_GAP)
        cuts.append(c)
    for z in (WALL_H * 0.18, WALL_H * 0.5, WALL_H * 0.82):
        c, a = socket_p2_solids((FACE * 0.5, 0.0, z), axis="+Y", rot=90, depth=4.6)
        cuts.append(c)
        adds.append(a)

    # Brick relief must skip anything that will later be cut through the plate, or the
    # relief is left floating over a hole. Derive the keep-out list from the actual cut
    # solids rather than from the table, so it can never fall out of step.
    openings = []
    for c in cuts:
        bb = c.val().BoundingBox()
        if bb.xmin < FACE - 0.4:            # this cut reaches through the plate
            openings.append((bb.ymin - 1.5, bb.zmin - 1.5, bb.ymax + 1.5, bb.zmax + 1.5))

    bricks = brick_field(WALL_LEN, WALL_H, tag,
                         scale_fn=lambda u: F.wpersp(u),
                         openings=openings,
                         broken_edge=lambda zz: break_profile(zz, tag))
    if bricks is not None:
        bricks = bricks.rotate((0, 0, 0), (1, 1, 1), 120).translate((FACE, 0, 0))
        # Keep only relief that has plate directly beneath it. The plate is a constant
        # 2.5 mm slab, so a copy of it shifted up by the relief height covers exactly
        # the volume the relief may occupy; anything outside that is printing over air.
        #
        # This is exact, and it replaces reasoning about whether the brick grid and the
        # torn edge's staircase agree. They did not -- the measured plate edge and
        # break_profile() disagreed by 3-4 mm at some heights -- and every attempt to
        # reconcile them analytically left slivers behind.
        bricks = bricks.intersect(plate.translate((P.BRICK_RELIEF, 0, 0)))
        plate = plate.union(bricks)

    plate = batch_cut(plate, cuts)
    plate = batch_add(plate, adds)
    return keep_largest(plate, f"{side}_Wall_Face")


def _join_positions():
    n = max(3, int(WALL_LEN / JOIN_PITCH))
    return [WALL_LEN * (i + 0.5) / n for i in range(n)]


# -------------------------------------------------------------------- rib ----
def wall_rib(side):
    """Open lattice: perimeter rails plus a vertical rib at each bead column.

    Sits at x = -(GAP + D) .. -GAP, so there is a clear RIB_GAP behind the face plate.
    Decorative pegs are 4 mm long and the plate is only 2.5 mm, so they protrude out
    the back; the gap is where they go, and it means no peg can ever foul the lattice.
    """
    _, _, _, beads = collect(side)
    D, GAP = P.WALL_SERVICE_D, P.RIB_GAP
    X0 = -(GAP + D)          # outer face, against the case panel
    X1 = -GAP                # inner face

    cols = sorted({round(u, 1) for (u, z) in beads})
    merged = []
    for u in cols:
        if not merged or u - merged[-1] > 14.0:
            merged.append(u)
    for u in _join_positions():
        if all(abs(u - m) > 10.0 for m in merged):
            merged.append(u)
    merged = sorted(m for m in merged if 6.0 < m < WALL_LEN - 6.0)

    pieces = []
    add = pieces.append

    def bar(dy, dz, y, z):
        return cq.Workplane("XY").box(D, dy, dz, centered=(False, False, False)) \
                 .translate((X0, y, z))

    # perimeter and mid rails
    add(bar(WALL_LEN, RIB_W, 0, 0))
    add(bar(WALL_LEN, RIB_W, 0, WALL_H - RIB_W))
    add(bar(RIB_W, WALL_H, WALL_LEN - RIB_W, 0))
    add(bar(WALL_LEN, RIB_W, 0, WALL_H * 0.52))
    for u in merged:
        add(bar(RIB_W, WALL_H, u - RIB_W / 2, 0))

    # bead bosses -- each big enough for a pass-through pocket and a baffle cap
    for (u, z) in beads:
        add(cq.Workplane("XY").box(D, 15.0, 17.0, centered=(False, True, True))
            .translate((X0, u, z)))
        col = min(merged, key=lambda m: abs(m - u)) if merged else u
        if abs(col - u) > 0.5:
            add(cq.Workplane("XY").box(D, abs(col - u) + 2.0, RIB_W,
                                       centered=(False, True, True))
                .translate((X0, (col + u) / 2, z)))

    # three coil bays for the surplus of a string that cannot be shortened
    for (u, z) in COIL_BAYS:
        add(cq.Workplane("XY").box(P.COIL_BAY_D + 1.4, P.COIL_BAY_W + 4,
                                   P.COIL_BAY_H + 4, centered=(False, True, True))
            .translate((X0, u, z)))

    # T3 tongues bridge the gap into the face plate
    for u in _join_positions():
        add(tongue_t3((X1, u, WALL_H * 0.5), 30.0, axis="+X", rot=90,
                      extra=GAP))

    body = _cut_plumbing(compound(pieces), beads, merged, X0)
    return keep_largest(body, f"{side}_Wall_Rib")


COIL_BAYS = [(WALL_LEN * 0.30, WALL_H * 0.32),
             (WALL_LEN * 0.55, WALL_H * 0.74),
             (WALL_LEN * 0.78, WALL_H * 0.32)]


def _cut_plumbing(body, beads, cols, X0):
    """Bead pockets, wire channels and coil bays, all cut from the rib's outer face
    (x = X0) so they are hidden by the case panel. Collected, then cut in one go."""
    cuts = []
    for (u, z) in beads:
        # pass-through bead seat: the wire arrives and leaves
        cuts.append(cq.Workplane("XY")
                    .box(P.BEAD_POCKET_D, P.BEAD_POCKET_W, P.BEAD_POCKET_H,
                         centered=(False, True, True)).translate((X0, u, z)))
        cuts.append(cq.Workplane("XY")
                    .box(P.WIRE_DIA + 1.0, P.WIRE_SLOT_W, 26.0,
                         centered=(False, True, True)).translate((X0, u, z)))
        # light port right through, so the bead can shine at the window
        cuts.append(cq.Workplane("XY").box(40.0, 9.0, 11.0, centered=(True, True, True))
                    .translate((X0, u, z)))

    ch_w, ch_d = P.WIRE_CHANNEL_WIDTH, P.WIRE_CHANNEL_DEPTH
    for u in cols:
        cuts.append(cq.Workplane("XY").box(ch_d, ch_w, WALL_H,
                                           centered=(False, True, False))
                    .translate((X0, u, 0)))
    for z in (RIB_W / 2, WALL_H * 0.52 + RIB_W / 2, WALL_H - RIB_W / 2):
        cuts.append(cq.Workplane("XY").box(ch_d, WALL_LEN, ch_w,
                                           centered=(False, False, True))
                    .translate((X0, 0, z)))
    for (u, z) in COIL_BAYS:
        cuts.append(cq.Workplane("XY")
                    .box(P.COIL_BAY_D, P.COIL_BAY_W, P.COIL_BAY_H,
                         centered=(False, True, True)).translate((X0, u, z)))
    return batch_cut(body, cuts)


# ------------------------------------------------------------------ bezel ----
def front_bezel(side):
    """Parts 06 / 07 -- the torn brick edge at the front opening, printed separately
    so the break has real thickness and can be painted as broken masonry."""
    tag = f"bezel_{side}"
    body = cq.Workplane("XY").box(BEZEL_W, 5.0, P.SCENE_H, centered=(False, False, False))

    course = P.BRICK_HEIGHT_FRONT + P.MORTAR_GAP
    cutter_pieces, z = [], 0.0
    from lib.util import rng
    r = rng(tag)
    while z < P.SCENE_H:
        bite = max(0.6, r.uniform(0.0, 8.5))
        cutter_pieces.append(
            cq.Workplane("XY").box(bite, 12.0, min(course, P.SCENE_H - z),
                                   centered=(False, False, False))
            .translate((BEZEL_W - bite, -1.0, z)))
        z += course
    body = body.cut(compound(cutter_pieces))

    bricks = brick_field(BEZEL_W, P.SCENE_H, tag + "_b", scale_fn=lambda u: 1.0)
    if bricks is not None:
        body = body.union(bricks.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, 0)))
    for z in (P.SCENE_H * 0.18, P.SCENE_H * 0.5, P.SCENE_H * 0.82):
        body = body.union(peg_p2((BEZEL_W * 0.45, 5.0, z), axis="+Y", rot=90))
    return keep_largest(body, f"{side}_Front_Bezel")


def bezel_sockets(wall_face_solid, side):
    for z in (P.SCENE_H * 0.18, P.SCENE_H * 0.5, P.SCENE_H * 0.82):
        wall_face_solid = socket_p2(wall_face_solid, (FACE * 0.5, 0.0, z), axis="-Y")
    return wall_face_solid
