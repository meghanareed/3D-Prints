"""Fairy-light plumbing: pass-through bead pockets, wire channels, coil bays,
baffle caps and the RGB/CCT puck cradle.

The defining difference from a discrete-LED design: a fairy-light bead is a point on a
continuous series circuit, so every emitter site needs the wire to ARRIVE and LEAVE.
Pockets are therefore pass-through, and the channel network is a path, not a tree.
"""
import math
import cadquery as cq
import params as P
from lib.util import try_chamfer


def bead_pocket(wp, x, y, angle=0.0, depth=None):
    """Cut a pass-through bead seat into the face the workplane sits on.
    Slots on BOTH sides so the string can continue to the next bead."""
    d = depth or P.BEAD_POCKET_D
    seat = cq.Workplane("XY").box(P.BEAD_POCKET_W, P.BEAD_POCKET_H, d,
                                  centered=(True, True, False)).translate((0, 0, -d))
    run = P.BEAD_POCKET_W + 2 * 8.0
    slot = cq.Workplane("XY").box(run, P.WIRE_SLOT_W, min(d, P.WIRE_DIA + 0.9),
                                  centered=(True, True, False))
    slot = slot.translate((0, 0, -min(d, P.WIRE_DIA + 0.9)))
    out = wp
    for s in (seat, slot):
        out = out.cut(s.rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0)))
    return out


def light_slot(wp, x, y, w, h, thickness, angle=0.0):
    """Pierce the wall face so a pocket behind it can shine through an opening."""
    cut = cq.Workplane("XY").box(w, h, thickness * 3,
                                 centered=(True, True, True))
    return wp.cut(cut.rotate((0, 0, 0), (0, 0, 1), angle).translate((x, y, 0)))


def wire_channel(wp, path, width=None, depth=None, nubs=True):
    """Cut a trough following a polyline of (x, y) points on the current top face.

    Retention nubs every ~25 mm pinch the mouth so the wire snaps in and stays; they
    are 0.5 mm proud, which FDM prints as a trivial overhang.
    """
    w = width or P.WIRE_CHANNEL_WIDTH
    d = depth or P.WIRE_CHANNEL_DEPTH
    out, nub_solids = wp, None
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 0.01:
            continue
        ang = math.degrees(math.atan2(dy, dx))
        seg = (cq.Workplane("XY").box(L + w, w, d, centered=(True, True, False))
               .translate((0, 0, -d))
               .rotate((0, 0, 0), (0, 0, 1), ang)
               .translate(((x0 + x1) / 2, (y0 + y1) / 2, 0)))
        out = out.cut(seg)
        if nubs:
            n = max(1, int(L // 25))
            for k in range(n):
                t = (k + 0.5) / n
                px, py = x0 + dx * t, y0 + dy * t
                for side in (-1, 1):
                    nb = (cq.Workplane("XY")
                          .box(2.0, 0.5, 1.0, centered=(True, True, False))
                          .translate((0, side * (w / 2 - 0.25), -1.0))
                          .rotate((0, 0, 0), (0, 0, 1), ang)
                          .translate((px, py, 0)))
                    nub_solids = nb if nub_solids is None else nub_solids.union(nb)
    if nub_solids is not None:
        out = out.union(nub_solids)
    return out


def coil_bay(wp, x, y, w=None, h=None, d=None):
    """Recess for stowing the surplus of a string that cannot be shortened."""
    w = w or P.COIL_BAY_W
    h = h or P.COIL_BAY_H
    d = d or P.COIL_BAY_D
    pocket = (cq.Workplane("XY").box(w, h, d, centered=(True, True, False))
              .translate((0, 0, -d)))
    out = wp.cut(pocket.translate((x, y, 0)))
    return try_chamfer(out, "|Z", 0.0)


def coil_bay_cover(w=None, h=None):
    """Part 45x -- traps stowed string so it cannot rattle or migrate."""
    from lib.mount import peg_p1
    w = (w or P.COIL_BAY_W) - 0.6
    h = (h or P.COIL_BAY_H) - 0.6
    body = cq.Workplane("XY").box(w, h, 1.2, centered=(True, True, False))
    for dy in (-h / 2 + 4, h / 2 - 4):
        body = body.union(peg_p1((0.0, dy, 0.0), axis="-Z"))
    return body


def baffle_cap(w=12.0, h=14.0, d=6.0, wall=None):
    """Part 40x -- an open-backed box that seals one bead pocket so its light cannot
    wash the neighbouring shop. Prints open-side-up, no supports."""
    wall = wall or P.DETAIL_MIN_T
    outer = cq.Workplane("XY").box(w, h, d, centered=(True, True, False))
    inner = (cq.Workplane("XY")
             .box(w - 2 * wall, h - 2 * wall, d - wall, centered=(True, True, False))
             .translate((0, 0, wall)))
    cap = outer.cut(inner)
    # wire entry and exit notches
    for side in (-1, 1):
        notch = (cq.Workplane("XY")
                 .box(wall * 3, P.WIRE_SLOT_W, P.WIRE_DIA + 0.8,
                      centered=(True, True, False))
                 .translate((side * (w / 2 - wall / 2), 0, d - (P.WIRE_DIA + 0.8))))
        cap = cap.cut(notch)
    return cap


def puck_cradle(dia=None, thick=None, ring=4.0, back=2.0, fingers=3):
    """Part 03E -- holds a 59.5 x 8.3 RGB/CCT puck facing forward, with a cable exit
    and three flexible fingers so the puck can be pulled out again."""
    dia = dia or P.SKY_PUCK_DIA
    thick = thick or P.SKY_PUCK_T
    bore = dia + 2 * P.SKY_PUCK_CLEAR
    body = cq.Workplane("XY").circle(bore / 2 + ring).extrude(thick + back)
    body = body.faces(">Z").workplane().circle(bore / 2).cutBlind(-thick)
    # cable exit
    body = body.cut(cq.Workplane("XY")
                    .box(P.PUCK_CABLE_DIA + 1.0, bore / 2 + ring + 2,
                         P.PUCK_CABLE_DIA + 1.0, centered=(True, False, False))
                    .translate((0, 0, back)))
    # retaining fingers over the rim
    tabs = None
    for i in range(fingers):
        a = math.radians(90 + i * 360 / fingers)
        t = (cq.Workplane("XY")
             .box(9.0, ring + 2.2, 1.4, centered=(True, True, False))
             .translate((0, -(bore / 2 - 1.1), thick + back))
             .rotate((0, 0, 0), (0, 0, 1), math.degrees(a)))
        tabs = t if tabs is None else tabs.union(t)
    return body.union(tabs)


def diffuser_plate(w, h, t=None, frame=False):
    """Parts 42x -- printed in natural or white PLA, 3 walls, 0 % infill."""
    t = t or P.DIFFUSER_PRINT_T
    plate = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    if frame:
        rim = (cq.Workplane("XY").box(w + 2.4, h + 2.4, 1.2, centered=(True, True, False))
               .cut(cq.Workplane("XY").box(w - 1.6, h - 1.6, 4,
                                           centered=(True, True, True))))
        plate = plate.union(rim)
    return plate
