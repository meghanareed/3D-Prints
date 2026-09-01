"""Turn each facade row into (a) printable parts and (b) the cuts its wall needs.

Wall-local frame, used by both walls:
    x   0 .. WALL_FACE_T is the brick plate; +X points into the alley
    y   u, depth from the front opening
    z   height above the alley floor
The right wall is mirrored as a whole at assembly time, so both walls are built
identically here and a socket can never end up on the wrong face.
"""
import math
import cadquery as cq
import params as P
import data.facade as F
from lib import window as W
from lib import sign as S
from lib import prop as PR
from lib.mount import (peg_p1, socket_p1, peg_p2, socket_p2, tongue_t3, groove_t3,
                       socket_p1_solids, socket_p2_solids, groove_t3_solids,
                       P2_SPACING)
from lib.light import bead_pocket
from lib.util import try_chamfer, try_fillet
from lib.brick import quoin_stack

FACE = P.WALL_FACE_T


def to_wall(solid, u, z):
    """Place a part built in its own flat XY frame onto the wall face."""
    return solid.rotate((0, 0, 0), (1, 1, 1), 120).translate((FACE, u, z))


def _sc(row):
    return F.wpersp(row["u"])


# ---------------------------------------------------------------- registry --
def build_element(row, side):
    """Return (parts, (cut_solids, add_solids), beads).

    Cuts and adds are returned as SOLIDS rather than applied, so a wall can fuse all
    of them and do two booleans instead of two hundred.
    """
    k = row["kind"]
    fn = _KINDS.get(k)
    if fn is None:
        raise KeyError(f"unknown facade kind: {k}")
    return fn(row, side)


def _pack(row, side, items, spec, beads):
    out = []
    for suffix, name, solid, (u, z) in items:
        pid = row["id"] + suffix
        out.append(dict(id=pid, name=f"{side}_{name}" if side else name,
                        solid=solid, placed=to_wall(solid, u, z)))
    return out, spec, beads


def _frame_mounts(u, z, w, h):
    """Cut/add solids for a frame's mounts, using the SAME offsets the part uses."""
    cuts, adds = [], []
    big = w >= P2_SPACING + 6
    for i, (ox, oz) in enumerate(W.mount_offsets(w, h)):
        # built in the PART's own frame, at the same point and rotation as its peg,
        # then carried into wall coordinates by the same to_wall() the part uses
        pt = (ox, oz, 0.0)
        # depth is clamped to the plate: a socket deeper than the material it sits in
        # leaves its crush ribs floating in the service gap as loose fragments.
        c, a = (socket_p2_solids(pt, axis="-Z", rot=180 * i, depth=FACE) if big
                else socket_p1_solids(pt, axis="-Z", rot=180 * i, depth=FACE))
        cuts.append(to_wall(c, u, z))
        adds.append(to_wall(a, u, z))
    return cuts, adds


def _p1_mount_local(rot=0.0):
    """Socket solids in the PART's own frame, for callers that place with to_wall."""
    return socket_p1_solids((0.0, 0.0, 0.0), axis="-Z", rot=rot, depth=FACE)


def _p1_mount(u, z, rot=0.0):
    c, a = socket_p1_solids((0.0, 0.0, 0.0), axis="-Z", rot=rot, depth=FACE)
    return [to_wall(c, u, z)], [to_wall(a, u, z)]


def _ap(w, h, u, z, arch=False, t=None):
    """Aperture solid, already rotated into wall-local coordinates."""
    return (W.aperture(w, h, t or FACE, arch=arch)
            .rotate((0, 0, 0), (1, 1, 1), 120).translate(((t or FACE) / 2, u, z)))


# ------------------------------------------------------------------ windows --
def _window(row, side):
    s = _sc(row)
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"]) + h / 2
    arch = row.get("arch", False)
    cols, rows = row.get("cols", 2), row.get("rows", 3)
    style = row.get("style", "sash")

    frame = W.window_frame(w, h, cols, rows, arch=arch, style=style)
    glaz = W.glazing(w, h, arch=arch)
    sl = W.sill(w, proj=4.0 * s)

    cuts, adds = _frame_mounts(u, z, w, h)
    cuts.append(_ap(w, h, u, z, arch=arch))
    z_sill = z - h / 2 - 1.5
    c, a = _p1_mount(u, z_sill)
    cuts += c
    adds += a
    beads = [(u, z)] * int(row.get("lit", 0))
    return _pack(row, side,
                 [("", row["name"] + "_Frame", frame, (u, z)),
                  ("g", row["name"] + "_Glazing", glaz, (u, z)),
                  ("s", row["name"] + "_Sill", sl, (u, z - h / 2 - 1.5))],
                 (cuts, adds), beads)


def _shopwin(row, side):
    """Shop window: same family but wider lights and a recessed reveal."""
    s = _sc(row)
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"]) + h / 2
    frame = W.window_frame(w, h, row.get("cols", 3), row.get("rows", 2), style="ornate")
    glaz = W.glazing(w, h, clear_frame=row.get("clear", False))
    lint = W.lintel(w, t=3.0 * s)

    cuts, adds = _frame_mounts(u, z, w, h)
    cuts.append(W.shopfront_recess(w + 5.0, h + 5.0, 0.9)
                .rotate((0, 0, 0), (1, 1, 1), 120).translate((FACE, u, z)))
    cuts.append(_ap(w, h, u, z))
    c, a = _p1_mount(u, z + h / 2 + 2.0)          # lintel
    cuts += c
    adds += a

    return _pack(row, side,
                 [("", row["name"] + "_Frame", frame, (u, z)),
                  ("g", row["name"] + "_Glazing", glaz, (u, z)),
                  ("l", row["name"] + "_Lintel", lint, (u, z + h / 2 + 2.0))],
                 (cuts, adds), [(u, z)] * int(row.get("lit", 0)))


def _bay(row, side):
    s = _sc(row)
    w, h, proj = row["w"] * s, row["h"] * s, row["proj"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    body = W.bay_body(w, h, proj)
    glaz = W.glazing(w * 0.62, h * 0.55)
    roof = W.bay_roof(w, proj)
    cor = [W.pilaster(h * 0.22, w=3.4 * s, proj=2.6 * s, fluted=False) for _ in (0,)]

    # the groove sits at the same part-frame point as the tongue: (x, y, z) with the
    # offset in Y, the part's height -- not in Z, which is the projection axis
    gc, ga = groove_t3_solids((0.0, h * W.BAY_TONGUE_Y, 0.0), min(w - 6.0, 24.0),
                              axis="-Z")
    cuts = [_ap(w - 6.0, h - 10.0, u, z + h / 2), to_wall(gc, u, z)]
    adds = [to_wall(ga, u, z)]
    ph = h * 0.22
    for zz in (z + h - 2.0 / 2, z - h * 0.20 + ph * 0.25, z - h * 0.20 + ph * 0.75):
        c, a = _p1_mount(u, zz)                    # roof, then the two corbel pegs
        cuts += c
        adds += a

    return _pack(row, side,
                 [("", row["name"] + "_Body", body, (u, z)),
                  ("g", row["name"] + "_Glazing", glaz, (u, z + h * 0.45)),
                  ("r", row["name"] + "_Roof", roof, (u, z + h)),
                  ("c", row["name"] + "_Corbel", cor[0], (u, z - h * 0.20))],
                 (cuts, adds), [(u, z + h * 0.5)] * int(row.get("lit", 0)))


def _oriel(row, side):
    """An oriel is a bay carried on corbels at an upper storey."""
    return _bay(dict(row), side)


def _bow(row, side):
    s = _sc(row)
    w, h, proj = row["w"] * s, row["h"] * s, row["proj"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    body = W.bow_window(w, h, proj)
    glaz = W.glazing(w * 0.70, h * 0.52)
    diff = W.glazing(w * 0.74, h * 0.56, t=P.DIFFUSER_PRINT_T)
    cornice = W.lintel(w, t=3.4 * s, proj=3.0)

    gc, ga = groove_t3_solids((0.0, h * W.BAY_TONGUE_Y, 0.0), min(w - 8.0, 28.0),
                              axis="-Z")
    cuts = [_ap(w - 8.0, h - 12.0, u, z + h / 2), to_wall(gc, u, z)]
    adds = [to_wall(ga, u, z)]
    c, a = _p1_mount(u, z + h + 2.0)               # cornice
    cuts += c
    adds += a

    return _pack(row, side,
                 [("", row["name"], body, (u, z)),
                  ("g", row["name"] + "_Glazing", glaz, (u, z + h * 0.42)),
                  ("d", row["name"] + "_Diffuser", diff, (u, z + h * 0.42)),
                  ("c", row["name"] + "_Cornice", cornice, (u, z + h + 2.0))],
                 (cuts, adds), [(u, z + h * 0.4), (u, z + h * 0.7)][:int(row.get("lit", 0))])


# -------------------------------------------------------------------- doors --
def _door(row, side):
    s = _sc(row)
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"]) + h / 2
    arch = row.get("arch", False)
    d = W.door(w, h, row.get("panels", 4), arch=arch)
    fr = W.door_frame(w, h, arch=arch)
    items = [("", row["name"], d, (u, z)),
             ("f", row["name"] + "_Frame", fr, (u, z))]
    fan_h = 6.0 * s
    if row.get("fanlight"):
        items.append(("l", row["name"] + "_Fanlight",
                      W.fanlight(w * 0.94, h=fan_h), (u, z + h / 2 + 1.0)))

    cuts, adds = _frame_mounts(u, z, w, h)
    cuts.append(_ap(w, h, u, z, arch=arch))
    if row.get("fanlight"):
        c, a = _p1_mount(u, z + h / 2 + 1.0 + fan_h * 0.45)
        cuts += c
        adds += a
    return _pack(row, side, items, (cuts, adds),
                 [(u, z + h * 0.42)] * int(row.get("lit", 0)))


# --------------------------------------------------------- shopfront pieces --
def _stallriser(row, side):
    s = _sc(row)
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"]) + h / 2
    part = W.stallriser(w, h)

    spec = _frame_mounts(u, z, w - 2 * W.FRAME_LIP, h - 2 * W.FRAME_LIP)
    return _pack(row, side, [("", row["name"], part, (u, z))], spec, [])


def _fascia(row, side):
    s = _sc(row)
    w = row["w"] * s
    h = 9.0 * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    part = W.fascia(w, h)

    spec = _frame_mounts(u, z, w - 12, h - 2)
    return _pack(row, side, [("", row["name"], part, (u, z))], spec, [])


def _pilaster(row, side):
    s = _sc(row)
    h = row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    part = W.pilaster(h, w=6.0 * s, proj=3.4 * s)

    cuts, adds = [], []
    for zc in (h * 0.25, h * 0.75):
        c, a = _p1_mount(u, z + zc)
        cuts += c
        adds += a
    return _pack(row, side, [("", row["name"], part, (u, z))], (cuts, adds), [])


def _awning(row, side):
    s = _sc(row)
    w, proj = row["w"] * s, row["proj"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    part = W.awning(w, proj=proj, h=proj * 0.78)

    spec = _p1_mount(u, z - proj * 0.39)
    return _pack(row, side, [("", row["name"], part, (u, z))], spec, [])


def _lintel(row, side):
    s = _sc(row)
    part = W.lintel(row["w"] * s, t=3.2 * s)
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    return _pack(row, side, [("", row["name"], part, (u, z))], _p1_mount(u, z), [])


# ------------------------------------------------ rainwater goods & masonry --
# These four are built in the same part-local frame as everything else -- px along the
# wall's depth, py up the wall, pz out of the wall -- and placed by to_wall(). They used
# to be translated straight into wall coordinates, which stopped matching once their
# sockets moved into the part frame.

def _pipe(row, side):
    s = _sc(row)
    h, dia = row["h"] * s, row["dia"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    # half-round section, flat back on the bed: no supports, and the layer lines run
    # along the pipe
    body = (cq.Workplane("XZ")
            .moveTo(-dia / 2, 0).threePointArc((0, dia * 0.62), (dia / 2, 0))
            .close().extrude(-h))
    for k in range(1, 4):
        band = (cq.Workplane("XZ")
                .moveTo(-dia * 0.60, 0).threePointArc((0, dia * 0.74), (dia * 0.60, 0))
                .close().extrude(-2.2).translate((0, h * k / 4, 0)))
        body = body.union(band)
    cuts, adds = [], []
    for zc in (h * 0.2, h * 0.8):
        body = body.union(peg_p1((0.0, zc, 0.0), axis="-Z"))
        c, a = _p1_mount_local()
        cuts.append(to_wall(c, u, z + zc))
        adds.append(to_wall(a, u, z + zc))
    return _pack(row, side, [("", row["name"], body, (u, z))], (cuts, adds), [])


def _hopper(row, side):
    s = _sc(row)
    w = row["w"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    # Rainwater hopper: a wide mouth over a narrow throat. Built as two boxes rather
    # than a loft -- a loft has to be rotated into the part frame afterwards, and it
    # kept landing half inside the wall.
    mouth_h, throat_h = w * 0.55, w * 0.40
    body = cq.Workplane("XY").box(w, mouth_h, w * 0.62, centered=(True, False, False)) \
        .translate((0, throat_h, 0))
    body = body.cut(cq.Workplane("XY").box(w - 2.2, mouth_h, w * 0.62 - 1.6,
                                           centered=(True, False, False))
                    .translate((0, throat_h + 1.2, 1.6)))
    body = body.union(cq.Workplane("XY")
                      .box(w * 0.42, throat_h + 1.0, w * 0.40,
                           centered=(True, False, False)))
    body = body.union(peg_p1((0.0, throat_h * 0.5, 0.0), axis="-Z"))
    c, a = _p1_mount_local()
    zc = z + w * 0.40 * 0.5
    return _pack(row, side, [("", row["name"], body, (u, z))],
                 ([to_wall(c, u, zc)], [to_wall(a, u, zc)]), [])


def _cornice(row, side):
    s = F.wpersp(row["u"])
    L = row["length"]
    z = F.storey_z(row["z"], row["u"])
    # profile in (py, pz): drops from the eaves line and projects out of the wall
    prof = [(0, 0), (0, 5.0 * s), (-2.0 * s, 5.0 * s), (-3.6 * s, 2.4 * s),
            (-6.0 * s, 2.4 * s), (-6.0 * s, 0)]
    body = cq.Workplane("YZ").polyline(prof).close().extrude(L)
    dents = []
    n = max(4, int(L / (7.0 * s)))
    for i in range(n):
        dents.append(cq.Workplane("XY")
                     .box(3.0 * s, 2.0 * s, 2.2 * s, centered=(True, False, False))
                     .translate(((i + 0.5) * L / n, -5.6 * s, 1.2 * s)))
    for d in dents:
        body = body.union(d)
    cuts, adds = [], []
    for uu in (L * 0.2, L * 0.8):
        body = body.union(peg_p1((uu, -3.0 * s, 0.0), axis="-Z"))
        c, a = _p1_mount_local()
        cuts.append(to_wall(c, row["u"] + uu, z - 3.0 * s))
        adds.append(to_wall(a, row["u"] + uu, z - 3.0 * s))
    return _pack(row, side, [("", row["name"], body, (row["u"], z))], (cuts, adds), [])


def _chimney(row, side):
    s = F.wpersp(row["u"])
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    proj = w * 0.75
    body = cq.Workplane("XY").box(w, h, proj, centered=(True, False, False))
    body = body.union(cq.Workplane("XY").box(w + 1.8, 2.4, proj + 1.8,
                                             centered=(True, False, False))
                      .translate((0, h - 2.4, 0)))
    pots = row.get("pots", 2)
    for i in range(pots):
        x = -w / 2 + (i + 0.5) * w / pots
        pot = (cq.Workplane("XZ").circle(w * 0.16).extrude(-h * 0.30)
               .cut(cq.Workplane("XZ").circle(w * 0.10).extrude(-h * 0.30))
               .translate((x, h - 1.0, proj * 0.5)))
        body = body.union(pot)
    body = body.union(peg_p1((0.0, h * 0.4, 0.0), axis="-Z"))
    c, a = _p1_mount_local()
    return _pack(row, side, [("", row["name"], body, (u, z))],
                 ([to_wall(c, u, z + h * 0.4)], [to_wall(a, u, z + h * 0.4)]), [])


def _quoin(row, side):
    h = row["h"]
    q = quoin_stack(h, block_w=9.0, block_h=8.0, depth=1.6, tag=row["id"])
    body = q.union(peg_p1((4.5, h * 0.2, 0.0), axis="-Z")) \
             .union(peg_p1((4.5, h * 0.8, 0.0), axis="-Z"))

    cuts, adds = [], []
    for f in (0.2, 0.8):
        c, a = _p1_mount(row["u"] + 4.5, h * f)
        cuts += c
        adds += a
    return _pack(row, side, [("", row["name"], body, (row["u"], 0.0))], (cuts, adds), [])


def _ornament(row, side):
    s = F.wpersp(row["u"])
    w, h = row["w"] * s, row["h"] * s
    u, z = row["u"], F.storey_z(row["z"], row["u"])
    body = (cq.Workplane("XY")
            .polyline([(-w / 2, -h / 2), (w / 2, -h / 2), (w * 0.36, h / 2),
                       (-w * 0.36, h / 2)]).close().extrude(2.4 * s))
    body = try_fillet(body, ">Z", 0.6)
    body = body.union(cq.Workplane("XY").box(w * 0.5, h * 0.34, 3.2 * s,
                                             centered=(True, True, False)))
    body = body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))

    return _pack(row, side, [("", row["name"], body, (u, z))], _p1_mount(u, z), [])


_KINDS = dict(window=_window, shopwin=_shopwin, bay=_bay, oriel=_oriel, bow=_bow,
              door=_door, stallriser=_stallriser, fascia=_fascia, pilaster=_pilaster,
              awning=_awning, lintel=_lintel, pipe=_pipe, hopper=_hopper,
              cornice=_cornice, chimney=_chimney, quoin=_quoin, ornament=_ornament)
