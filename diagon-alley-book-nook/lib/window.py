"""Window, door and shopfront families.

Every opening is built as a set of separately printable, separately paintable pieces:
    recess  (in the wall)  ->  frame  ->  glazing/diffuser  ->  sill  ->  trim
so wall, joinery, glass and stonework can each be their own colour.
"""
import math
import cadquery as cq
import params as P
from lib.mount import (peg_p1, socket_p1, peg_p2, socket_p2, tongue_t3, groove_t3,
                       socket_p1_solids, P2_SPACING)
from lib.util import try_chamfer, try_fillet

# PART FRAME CONVENTION -- every wall-mounted part in this file uses it, and to_wall()
# in parts/decor.py assumes it:
#
#     +X   along the wall's depth (the alley receding away from you)
#     +Y   up the wall
#     +Z   out of the wall, into the alley  (relief / projection)
#     mounting pegs point -Z
#
# Projecting parts were originally drawn with Y as the projection, which to_wall() then
# rotated into the wall's HEIGHT -- bays came out lying on their sides.

BAY_TONGUE_Y = 0.90  # where a bay/bow's tongue sits, as a fraction of its height.
                     # Shared with parts/decor.py so the groove in the wall lands in
                     # exactly the same place.

FRAME_T   = 2.0      # frame plate thickness
FRAME_LIP = 3.0      # how far the frame overlaps the aperture on each side
BAR_W     = 1.2      # glazing bar width
BAR_PROUD = 0.8
BEAD_W    = 1.4      # outer moulding, proud by the same amount as the glazing bars.
                     # Not decoration: the frame prints front-face-DOWN, so whatever
                     # stands proudest is what touches the bed. With only the bars
                     # proud, they were the entire first layer -- 129.5 mm^2 -- and the
                     # frame band landed 0.8 mm up in mid-air, held on where the bar
                     # ends met it. 376.8 mm^2 of unsupported overhang on 129.5 mm^2 of
                     # bed, which is what Bambu Studio calls a floating cantilever. A
                     # proud bead round the outside puts a continuous ring on the bed
                     # and turns the rest into ordinary short-span bridging.


# --------------------------------------------------------------- mounting ----
# Convention for flat wall-mounted parts: built in XY with the visible front face
# growing in +Z from z=0, and mounting pegs pointing -Z out of the z=0 plane.  The
# exporter flips them 180 deg so they print front-face-down with the pegs up: no
# supports, and the textured plate gives the front a free matte finish.

def mount_offsets(w, h):
    """Where this part's mounts sit, in part-local (x, z). One list, used by both the
    part and the wall, so a peg and its socket can never drift apart."""
    a = -(h / 2 + FRAME_LIP / 2) + 0.6
    b = (h / 2 + FRAME_LIP / 2) - 0.6
    return [(0.0, a), (0.0, b)]


def _mount_pegs(body, w, h, z=0.0):
    big = w >= P2_SPACING + 6
    for i, (ox, oz) in enumerate(mount_offsets(w, h)):
        pt = (ox, oz, z)
        # The pair spreads along the part's own X (its width). Spreading it along Y
        # put the pegs 3 mm clear of the frame band and they came off as loose solids.
        body = body.union(peg_p2(pt, axis="-Z", rot=180 * i) if big
                          else peg_p1(pt, axis="-Z", rot=180 * i))
    return body


def frame_sockets(wp, x, z, w, h, decorative=True, axis="+X", face=0.0):
    """Cut the matching sockets into a wall face.

    axis is the wall's outward normal (+X for the left wall, -X for the right), and
    `face` is the coordinate of that face along the normal.
    """
    big = w >= P2_SPACING + 6
    for i, (ox, oz) in enumerate(mount_offsets(w, h)):
        if axis in ("+X", "-X"):
            pt = (face, x + ox, z + oz)
        else:
            pt = (x + ox, face, z + oz)
        wp = (socket_p2(wp, pt, axis=axis, rot=180 * i, decorative=decorative) if big
              else socket_p1(wp, pt, axis=axis, rot=180 * i, decorative=decorative))
    return wp


def aperture(w, h, thickness, arch=False):
    """Cutting solid for the opening itself."""
    if arch:
        body = (cq.Workplane("XY")
                .moveTo(-w / 2, -h / 2).lineTo(w / 2, -h / 2).lineTo(w / 2, h / 2 - w / 2)
                .threePointArc((0, h / 2), (-w / 2, h / 2 - w / 2)).close()
                .extrude(thickness * 4))
        return body.translate((0, 0, -thickness * 2))
    return cq.Workplane("XY").box(w, h, thickness * 4, centered=(True, True, True))


# ------------------------------------------------------------------ frames ----
def _frame_outline(ow, oh, t, arch):
    """The frame's outer profile, extruded `t` from z=0. Used at full size for the
    body and inset by BEAD_W for the recessed glazing field."""
    if arch:
        return (cq.Workplane("XY")
                .moveTo(-ow / 2, -oh / 2).lineTo(ow / 2, -oh / 2)
                .lineTo(ow / 2, oh / 2 - ow / 2)
                .threePointArc((0, oh / 2), (-ow / 2, oh / 2 - ow / 2)).close()
                .extrude(t))
    return cq.Workplane("XY").box(ow, oh, t, centered=(True, True, False))


def window_frame(w, h, cols=2, rows=3, arch=False, style="sash"):
    """A snap-in frame. Prints front-face-down, pegs up: no supports.

    The front face is BAR_PROUD proud at the outer bead and at the glazing bars, and
    recessed between them -- which is how a real window reads, and is also the only
    arrangement that prints this part face-down without a floating cantilever.
    """
    ow, oh = w + 2 * FRAME_LIP, h + 2 * FRAME_LIP
    front = FRAME_T + BAR_PROUD
    outer = _frame_outline(ow, oh, front, arch)
    inner = aperture(w - 1.0, h - 1.0, front, arch=arch)
    body = outer.cut(inner)

    # recess the glazing field, leaving the outer bead standing proud with the bars
    bead = min(BEAD_W, (FRAME_LIP + 0.5) * 0.5)
    if ow - 2 * bead > 2 and oh - 2 * bead > 2:
        body = body.cut(_frame_outline(ow - 2 * bead, oh - 2 * bead,
                                       BAR_PROUD + 0.02, arch)
                        .translate((0, 0, FRAME_T - 0.01)))

    # glazing bars, standing proud on the front face
    bars = None
    for i in range(1, cols):
        b = cq.Workplane("XY").box(BAR_W, h, front,
                                   centered=(True, True, False))
        b = b.translate((-w / 2 + i * w / cols, 0, 0))
        bars = b if bars is None else bars.union(b)
    for j in range(1, rows):
        b = cq.Workplane("XY").box(w, BAR_W, front,
                                   centered=(True, True, False))
        b = b.translate((0, -h / 2 + j * h / rows, 0))
        bars = b if bars is None else bars.union(b)
    if bars is not None:
        body = body.union(bars)

    if style == "sash":                      # heavier meeting rail
        body = body.union(cq.Workplane("XY")
                          .box(w, BAR_W * 2.0, front,
                               centered=(True, True, False)))
    if style == "ornate":                    # moulded outer bead
        body = try_fillet(body, ">Z and (not %CIRCLE)", 0.4)

    # Glazing rebate, on the BACK -- cut last, so it also takes the back off the bars
    # and the glazing sits flush behind them. This used to be cut at FRAME_T - slot,
    # which is the FRONT face: the docstring said "on the back" and the code put the
    # rebate, and therefore the glazing, on the side you look at.
    body = body.cut(cq.Workplane("XY").box(w + 1.6, h + 1.6, P.DIFFUSER_SLOT_T,
                                           centered=(True, True, False))
                    .translate((0, 0, -0.01)))

    return _mount_pegs(body, w, h)


def glazing(w, h, arch=False, t=None, clear_frame=False):
    """Diffuser or clear insert that drops into the frame rebate."""
    t = t or P.DIFFUSER_PRINT_T
    if arch:
        g = (cq.Workplane("XY")
             .moveTo(-(w + 1.2) / 2, -(h + 1.2) / 2).lineTo((w + 1.2) / 2, -(h + 1.2) / 2)
             .lineTo((w + 1.2) / 2, (h + 1.2) / 2 - (w + 1.2) / 2)
             .threePointArc((0, (h + 1.2) / 2), (-(w + 1.2) / 2, (h + 1.2) / 2 - (w + 1.2) / 2))
             .close().extrude(t))
    else:
        g = cq.Workplane("XY").box(w + 1.2, h + 1.2, t, centered=(True, True, False))
    if clear_frame:      # thin rim to hold a scrap of clear PET instead of printed PLA
        g = g.cut(cq.Workplane("XY").box(w - 2.4, h - 2.4, t * 3, centered=(True, True, True)))
    return g


def sill(w, proj=4.0, t=2.6, wash=0.8):
    """Stone sill with a weathering slope, plus a P1 peg into the wall."""
    body = cq.Workplane("XY").box(w + 6.0, t, proj, centered=(True, True, False))
    # weather the top face so rain would run off toward the alley
    body = body.cut(cq.Workplane("XY")
                    .polyline([(0, 0), (proj + 1, 0), (proj + 1, -wash)])
                    .close().extrude(w + 8.0)
                    .rotate((0, 0, 0), (0, 1, 0), -90)
                    .rotate((0, 0, 0), (0, 0, 1), 90)
                    .translate((-(w + 8.0) / 2, t / 2, 0)) if False else
                    cq.Workplane("XY").box(w + 8.0, wash, proj * 0.55,
                                           centered=(True, False, False))
                    .translate((0, t / 2 - wash, proj * 0.55)))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def lintel(w, t=3.2, proj=2.0):
    """Stone head over an opening. x = width, y = depth of the stone, z = projection."""
    body = cq.Workplane("XY").box(w + 8.0, t, proj, centered=(True, True, False))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


# ------------------------------------------------------------- projecting ----
def bay_body(w, h, proj, taper=0.72, arch_top=False):
    """A projecting bay/oriel: a three-sided box that prints with its open back on the
    bed -- no supports, no bridging. Width along X, height along Y, projection along Z.
    """
    wf = w * taper
    shell = (cq.Workplane("XZ")
             .polyline([(-w / 2, 0), (w / 2, 0), (wf / 2, proj), (-wf / 2, proj)])
             .close().extrude(-h))
    # The void stops 1.2 short of the back, leaving a flange for the tongue to root
    # into; the light gets through via an explicit aperture cut in that flange. With
    # the void running right through, the tongue only clipped two thin slivers of the
    # side walls and came away as a separate solid.
    inner = (cq.Workplane("XZ")
             .polyline([(-w / 2 + 2.0, 1.2), (w / 2 - 2.0, 1.2),
                        (wf / 2 - 2.0, proj - 2.0), (-wf / 2 + 2.0, proj - 2.0)])
             .close().extrude(-(h - 2.0)).translate((0, 1.0, 0)))
    body = shell.cut(inner)
    body = body.cut(cq.Workplane("XY").box(w - 9.0, h * 0.60, 6.0,
                                           centered=(True, True, True))
                    .translate((0, h * 0.42, 0)))
    # front light and two cheek lights
    body = body.cut(cq.Workplane("XY").box(wf - 5.0, h - 12.0, 8.0,
                                           centered=(True, False, False))
                    .translate((0, 6.0, proj - 4.0)))
    for sx in (-1, 1):
        body = body.cut(cq.Workplane("XY").box(6.0, h - 16.0, proj - 6.0,
                                               centered=(True, False, False))
                        .translate((sx * (w / 2 - 1.0), 8.0, 2.0)))
    if arch_top:
        body = try_fillet(body, ">Y", 1.2)
    return body.union(tongue_t3((0.0, h * BAY_TONGUE_Y, 0.0), min(w - 6.0, 24.0),
                                axis="-Z"))


def bay_roof(w, proj, taper=0.72, t=2.0):
    """Separate lead roof for a bay -- prints flat, snaps on, paints as lead."""
    wf = w * taper
    # the back edge starts at z = 0, flush with the wall face. Starting it at -1.5
    # buried the roof 1.5 mm into the brickwork.
    roof = (cq.Workplane("XZ")
            .polyline([(-w / 2 - 1.5, 0), (w / 2 + 1.5, 0),
                       (wf / 2 + 1.5, proj + 1.5), (-wf / 2 - 1.5, proj + 1.5)])
            .close().extrude(-t))
    for i in range(4):
        x = -w / 2 + (i + 0.5) * w / 4
        roof = roof.union(cq.Workplane("XZ")
                          .polyline([(x - 0.5, 0), (x + 0.5, 0),
                                     (x + 0.5, proj + 1.5), (x - 0.5, proj + 1.5)])
                          .close().extrude(-(t + 0.6)))
    return roof.union(peg_p1((0.0, -t / 2, 0.0), axis="-Z"))


def bow_window(w, h, proj, facets=5):
    """Curved shop bow, built faceted: it prints better than a true cylinder and, at
    this scale, reads identically once painted."""
    def arc(rw, rp):
        return [(-math.cos(math.pi * i / facets) * rw,
                 math.sin(math.pi * i / facets) * rp) for i in range(facets + 1)]

    o = arc(w / 2, proj)
    inn = arc(w / 2 - 2.0, proj - 2.0)
    # polyline() takes the whole list: moveTo(p0).polyline(pts[1:]) drops p0,
    # which clipped the near end off every bow window.
    outer = cq.Workplane("XZ").polyline(o).close().extrude(-h)
    inner = (cq.Workplane("XZ").polyline(inn).close()
             .extrude(-(h - 2.0)).translate((0, 1.0, 1.2)))
    body = outer.cut(inner)
    body = body.cut(cq.Workplane("XY").box(w - 11.0, h * 0.58, 6.0,
                                           centered=(True, True, True))
                    .translate((0, h * 0.42, 0)))
    for i in range(facets):
        a = math.pi * ((i + 0.5) / facets)
        cx, cz = -math.cos(a) * (w / 2 - 1.0), math.sin(a) * (proj - 1.0)
        body = body.cut(cq.Workplane("XY")
                        .box(w / facets * 0.72, h - 14.0, 8.0,
                             centered=(True, False, False))
                        .rotate((0, 0, 0), (0, 1, 0), 90 - math.degrees(a))
                        .translate((cx, 7.0, cz)))
    return body.union(tongue_t3((0.0, h * BAY_TONGUE_Y, 0.0), min(w - 8.0, 28.0),
                                axis="-Z"))


# ------------------------------------------------------------------- doors ----
def door(w, h, panels=4, arch=False, t=2.2):
    """Panelled door. Prints face-DOWN with the rest of the facade; the panel recesses
    become shallow bridged pockets and nothing needs support."""
    if arch:
        body = (cq.Workplane("XY")
                .moveTo(-w / 2, -h / 2).lineTo(w / 2, -h / 2).lineTo(w / 2, h / 2 - w / 2)
                .threePointArc((0, h / 2), (-w / 2, h / 2 - w / 2)).close().extrude(t))
    else:
        body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    rows = max(1, panels // 2)
    pw, ph = w * 0.34, (h * 0.82) / rows * 0.72
    for j in range(rows):
        zc = -h / 2 + h * 0.12 + (j + 0.5) * (h * 0.82) / rows
        for s in (-1, 1):
            rec = (cq.Workplane("XY").box(pw, ph, 0.7, centered=(True, True, False))
                   .translate((s * w * 0.21, zc, t - 0.7)))
            body = body.cut(rec)
    # Door knob, INCISED rather than proud. It used to be a 1.1 mm sphere standing off
    # the face, and the door prints face-down: the knob was the only thing touching the
    # bed. 0.80 mm^2 of first layer under 874 mm^2 of overhang -- the whole door landed
    # in mid-air 1.1 mm up, balanced on one dot. An engraved ring leaves the face dead
    # flat, prints with no support at all, and takes a wash of paint better than a
    # sphere does.
    kx, ky = w / 2 - 3.0, -h * 0.06
    ring = (cq.Workplane("XY").cylinder(0.5, 2.2, centered=(True, True, False))
            .cut(cq.Workplane("XY").cylinder(0.5, 1.3, centered=(True, True, False)))
            .translate((kx, ky, t - 0.5)))
    body = body.cut(ring)
    return _mount_pegs(body, w - 2 * FRAME_LIP, h - 2 * FRAME_LIP)


def door_frame(w, h, arch=False, t=2.4, lip=3.2):
    ow, oh = w + 2 * lip, h + lip
    if arch:
        outer = (cq.Workplane("XY")
                 .moveTo(-ow / 2, -oh / 2).lineTo(ow / 2, -oh / 2)
                 .lineTo(ow / 2, oh / 2 - ow / 2)
                 .threePointArc((0, oh / 2), (-ow / 2, oh / 2 - ow / 2)).close().extrude(t))
        inner = aperture(w, h, t, arch=True)
    else:
        outer = cq.Workplane("XY").box(ow, oh, t, centered=(True, True, False))
        inner = aperture(w, h, t)
    body = outer.cut(inner)
    return _mount_pegs(body, w, h)


def fanlight(w, h=8.0, spokes=5, t=1.8):
    """Semicircular light over a door -- a classic and a good place for a bead."""
    body = (cq.Workplane("XY").moveTo(-w / 2, 0).threePointArc((0, h), (w / 2, 0))
            .close().extrude(t))
    for i in range(1, spokes):
        a = math.pi * i / spokes
        bar = (cq.Workplane("XY").box(BAR_W, w, t + 0.6, centered=(True, False, False))
               .rotate((0, 0, 0), (0, 0, 1), math.degrees(a) - 90))
        body = body.union(bar.intersect(
            cq.Workplane("XY").moveTo(-w / 2, 0).threePointArc((0, h), (w / 2, 0))
            .close().extrude(t + 0.6)))
    return body.union(peg_p1((0.0, h * 0.45, 0.0), axis="-Z"))


# -------------------------------------------------------------- shopfronts ----
def shopfront_recess(w, h, depth=5.0):
    """Cutting solid for a shopfront: a shallow structural recess in the wall."""
    return cq.Workplane("XY").box(w, h, depth * 2, centered=(True, True, True))


def pilaster(h, w=6.0, proj=3.4, fluted=True):
    """Shop pilaster with cap and base -- gives the storefront its Victorian frame."""
    body = cq.Workplane("XY").box(w, h, proj, centered=(True, False, False))
    body = body.union(cq.Workplane("XY").box(w + 2.4, 4.0, proj + 1.2,
                                             centered=(True, False, False)))
    body = body.union(cq.Workplane("XY").box(w + 2.8, 3.2, proj + 1.6,
                                             centered=(True, False, False))
                      .translate((0, h - 3.2, 0)))
    if fluted:
        for i in (-1, 0, 1):
            body = body.cut(cq.Workplane("XY")
                            .box(0.9, h - 10.0, 1.0, centered=(True, False, False))
                            .translate((i * 1.7, 5.0, proj - 0.5)))
    for yc in (h * 0.25, h * 0.75):
        body = body.union(peg_p1((0.0, yc, 0.0), axis="-Z"))
    return body


def stallriser(w, h=12.0, t=2.0, boards=4):
    """The panelled board below a shop window."""
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    for i in range(1, boards):
        body = body.cut(cq.Workplane("XY")
                        .box(0.8, h, 0.6, centered=(True, True, False))
                        .translate((-w / 2 + i * w / boards, 0, t - 0.6)))
    return _mount_pegs(body, w - 2 * FRAME_LIP, h - 2 * FRAME_LIP)


def fascia(w, h=9.0, t=2.4, pitch=None):
    """Shop fascia board. Blank: the name lives on a separate plate pinned to it.

    Two sockets on the FRONT take that plate. They are here rather than in the wall
    because a name plate mounted to the wall has to find bare brick beside the board it
    is meant to sit on, and on this facade there is none -- every fascia name plate in
    the kit had its wall socket underneath the shopfront it belonged to.
    """
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    body = body.union(cq.Workplane("XY").box(w + 2.0, 2.0, t + 1.4,
                                             centered=(True, True, False))
                      .translate((0, h / 2 - 1.0, 0)))
    body = _mount_pegs(body, w - 12, h - 2)
    if pitch:
        for sx in (-1, 1):
            c, _a = socket_p1_solids((sx * pitch / 2, 0.0, t), axis="-Z", depth=t - 0.8,
                                     decorative=True)
            body = body.cut(c)
    return body


def awning(w, proj=9.0, h=7.0, scallops=6, t=1.6):
    """Canvas awning -- prints as a sloped shell, no supports needed at this angle."""
    # sloping canvas: y falls as z projects, so it prints as a 40-ish degree roof
    body = (cq.Workplane("YZ")
            .polyline([(0, 0), (-h, proj), (-h - t, proj), (-t, 0)])
            .close().extrude(w).translate((-w / 2, 0, 0)))
    body = body.union(cq.Workplane("XY").box(w, 4.0, t, centered=(True, False, False))
                      .translate((0, -h - 4.0, proj - t)))
    for i in range(scallops):
        x = -w / 2 + (i + 0.5) * w / scallops
        body = body.cut(cq.Workplane("XY")
                        .cylinder(t * 3, w / scallops * 0.42, centered=(True, True, False))
                        .translate((x, -h - 4.0, proj - t - t)))
    return body.union(peg_p1((0.0, -1.0, 0.0), axis="-Z"))
