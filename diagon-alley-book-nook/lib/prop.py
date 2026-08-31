"""Street props and lanterns -- the small parts that make the alley feel inhabited."""
import math
import cadquery as cq
import params as P
from lib.mount import peg_p1
from lib.util import try_fillet, try_chamfer


def barrel(d=13.0, h=17.0, staves=14, hoops=3):
    """Coopered barrel with a belly, staves and hoops. Prints upright, no supports."""
    body = (cq.Workplane("XZ")
            .moveTo(d * 0.40, 0).lineTo(d * 0.50, h * 0.30).lineTo(d * 0.50, h * 0.70)
            .lineTo(d * 0.40, h).lineTo(0, h).lineTo(0, 0).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))
    for i in range(staves):
        a = 2 * math.pi * i / staves
        groove = (cq.Workplane("XY").box(0.6, 0.6, h * 1.1, centered=(True, True, False))
                  .translate((math.cos(a) * d * 0.5, math.sin(a) * d * 0.5, 0)))
        body = body.cut(groove)
    # Hoops sit on the belly only, and their inner radius is well inside the staves.
    # A hoop sized to the widest point floats free where the barrel tapers back in.
    for k in range(hoops):
        z = h * (0.10 + 0.30 * k)
        ring = (cq.Workplane("XY").circle(d * 0.54).extrude(1.6)
                .cut(cq.Workplane("XY").circle(d * 0.38).extrude(1.6))
                .translate((0, 0, z)))
        body = body.union(ring)
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def crate(w=12.0, d=10.0, h=9.0, t=1.2):
    """Slatted crate."""
    body = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    body = body.cut(cq.Workplane("XY").box(w - 2 * t, d - 2 * t, h,
                                           centered=(True, True, False))
                    .translate((0, 0, t)))
    for s in (-1, 1):
        for k in range(2):
            body = body.cut(cq.Workplane("XY")
                            .box(w * 0.7, t * 3, 1.0, centered=(True, True, False))
                            .translate((0, s * d / 2, h * (0.28 + 0.34 * k))))
            body = body.cut(cq.Workplane("XY")
                            .box(t * 3, d * 0.7, 1.0, centered=(True, True, False))
                            .translate((s * w / 2, 0, h * (0.28 + 0.34 * k))))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def crate_stack():
    a = crate(12, 10, 9)
    b = crate(9.5, 8, 7).rotate((0, 0, 0), (0, 0, 1), 18).translate((1.2, 0.8, 9.0))
    return a.union(b)


def cauldron(d=11.0, h=8.0, legs=3, peg=True):
    body = (cq.Workplane("XZ")
            .moveTo(0, h).lineTo(d / 2, h).lineTo(d * 0.46, h * 0.35)
            .threePointArc((d * 0.30, h * 0.06), (0, 0)).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))
    body = body.cut(cq.Workplane("XZ")
                    .moveTo(0, h).lineTo(d / 2 - 1.1, h).lineTo(d * 0.46 - 1.1, h * 0.35)
                    .threePointArc((d * 0.30 - 1.0, h * 0.10 + 1.0), (0, 1.2)).close()
                    .revolve(360, (0, 0, 0), (0, 1, 0)))
    body = body.union(cq.Workplane("XY").circle(d * 0.52).extrude(1.0)
                      .cut(cq.Workplane("XY").circle(d * 0.47).extrude(1.0))
                      .translate((0, 0, h - 1.2)))
    for i in range(legs):
        a = 2 * math.pi * i / legs
        body = body.union(cq.Workplane("XY").cylinder(2.6, 0.9)
                          .translate((math.cos(a) * d * 0.28, math.sin(a) * d * 0.28, -1.0)))
    body = body.translate((0, 0, 1.3))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z")) if peg else body


def cauldron_stack():
    """Three pots grouped on a common base rather than nested.

    Nesting them looked right but was never a single solid: a cauldron is narrowest at
    its foot, so an upper pot's base always hangs inside the hollow of the one below
    without ever touching it.
    """
    # overlap each pot into the one below; spacing them to just touch left five
    # separate solids
    # only the bottom pot carries the mounting peg; a peg on each one left three
    # loose plugs floating inside the stack
    base = cq.Workplane("XY").box(21.0, 13.0, 1.2, centered=(True, True, False))
    base = try_fillet(base, "|Z", 2.5)
    grp = (base
           .union(cauldron(11.0, 8.0, peg=False).translate((-4.0, 0.0, 0.8)))
           .union(cauldron(8.0, 6.0, peg=False).translate((5.0, -1.5, 0.8)))
           .union(cauldron(6.0, 4.6, peg=False).translate((7.5, 3.5, 0.8))))
    return grp.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def broom_rack(brooms=3, h=26.0, w=14.0):
    """A rack of brooms, printed lying flat so the handles are never thin verticals."""
    rack = cq.Workplane("XY").box(w, 2.2, 2.6, centered=(True, True, False))
    body = rack
    for i in range(brooms):
        x = -w / 2 + (i + 0.5) * w / brooms
        handle = cq.Workplane("XY").cylinder(h, 0.95, centered=(True, True, False)) \
            .translate((x, 0, 0))
        head = (cq.Workplane("XZ")
                .moveTo(0, 0).lineTo(2.6, -6.0).lineTo(-2.6, -6.0).close()
                .extrude(2.4).translate((x, -1.2, h * 0.30)))
        body = body.union(handle).union(head)
    body = body.union(cq.Workplane("XY").box(w, 2.2, 2.6, centered=(True, True, False))
                      .translate((0, 0, h * 0.72)))
    return body.union(peg_p1((0.0, 0.0, h * 0.10), axis="-Y"))


def post_box(w=9.0, d=8.0, h=16.0):
    body = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    body = try_fillet(body, "|Z", 1.6)
    body = body.union(cq.Workplane("XY").box(w + 1.4, d + 1.4, 1.4,
                                             centered=(True, True, False))
                      .translate((0, 0, h)))
    body = body.cut(cq.Workplane("XY").box(w * 0.62, d, 1.2, centered=(True, True, False))
                    .translate((0, d / 2 - 0.4, h * 0.72)))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def notice_board(w=22.0, h=17.0, t=2.0):
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    body = body.cut(cq.Workplane("XY").box(w - 3.2, h - 3.2, 0.8,
                                           centered=(True, True, False))
                    .translate((0, 0, t - 0.8)))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def poster_layer(w=20.0, h=15.0, t=0.8, n=4, seed_tag="poster"):
    """Loose overlapping posters that snap onto the notice board -- paint them
    separately and the board reads as years of accumulated fly-posting."""
    from lib.util import rng
    r = rng(seed_tag)
    body = None
    for i in range(n):
        pw, ph = w * r.uniform(0.30, 0.46), h * r.uniform(0.34, 0.52)
        px = r.uniform(-w / 2 + pw / 2 + 1, w / 2 - pw / 2 - 1)
        pz = r.uniform(-h / 2 + ph / 2 + 1, h / 2 - ph / 2 - 1)
        p = (cq.Workplane("XY").box(pw, ph, t, centered=(True, True, False))
             .rotate((0, 0, 0), (0, 0, 1), r.uniform(-7, 7))
             .translate((px, pz, 0)))
        body = p if body is None else body.union(p)
    return body


def lantern(h=22.0, w=9.0, hood=True, bracket_reach=9.0):
    """Wall lantern: tapered glass box, hood, and a bead pocket inside.
    Prints upright with the open bottom on the bed."""
    glass = (cq.Workplane("XY")
             .polyline([(-w / 2, -w / 2), (w / 2, -w / 2), (w / 2, w / 2), (-w / 2, w / 2)])
             .close().workplane(offset=h * 0.55)
             .polyline([(-w * 0.34, -w * 0.34), (w * 0.34, -w * 0.34),
                        (w * 0.34, w * 0.34), (-w * 0.34, w * 0.34)])
             .close().loft(combine=True))
    inner = (cq.Workplane("XY")
             .polyline([(-w / 2 + 1.1, -w / 2 + 1.1), (w / 2 - 1.1, -w / 2 + 1.1),
                        (w / 2 - 1.1, w / 2 - 1.1), (-w / 2 + 1.1, w / 2 - 1.1)])
             .close().workplane(offset=h * 0.55 - 1.0)
             .polyline([(-w * 0.24, -w * 0.24), (w * 0.24, -w * 0.24),
                        (w * 0.24, w * 0.24), (-w * 0.24, w * 0.24)])
             .close().loft(combine=True))
    body = glass.cut(inner)
    # glazing openings on the three visible sides
    for ang in (0, 90, 270):
        cut = (cq.Workplane("XY").box(w * 0.56, 4.0, h * 0.36,
                                      centered=(True, True, False))
               .translate((0, w / 2 - 1.0, h * 0.12))
               .rotate((0, 0, 0), (0, 0, 1), ang))
        body = body.cut(cut)
    if hood:
        body = body.union(cq.Workplane("XY")
                          .polyline([(-w * 0.62, -w * 0.62), (w * 0.62, -w * 0.62),
                                     (w * 0.62, w * 0.62), (-w * 0.62, w * 0.62)])
                          .close().workplane(offset=w * 0.42)
                          .polyline([(-0.9, -0.9), (0.9, -0.9), (0.9, 0.9), (-0.9, 0.9)])
                          .close().loft(combine=True).translate((0, 0, h * 0.55)))
        body = body.union(cq.Workplane("XY").cylinder(1.6, 0.9, centered=(True, True, False))
                          .translate((0, 0, h * 0.55 + w * 0.42)))
    # wire route up through the arm
    body = body.cut(cq.Workplane("XY").box(P.WIRE_SLOT_W, w, 1.4,
                                           centered=(True, True, False))
                    .translate((0, 0, 0.0)))
    arm = (cq.Workplane("XZ")
           .moveTo(0, 0).lineTo(bracket_reach, 0).lineTo(bracket_reach, -2.2).lineTo(0, -2.2)
           .close().extrude(-2.6).translate((0, 1.3, h * 0.62)))
    stay = (cq.Workplane("XZ")
            .moveTo(0, -6.0).lineTo(bracket_reach * 0.8, -2.2)
            .lineTo(bracket_reach * 0.8, -4.0).lineTo(2.0, -6.0)
            .close().extrude(-2.6).translate((0, 1.3, h * 0.62)))
    body = body.translate((bracket_reach, 0, 0)).union(arm).union(stay)
    # Wall rose: a real backplate at the fixing face. The arm and stay both taper to a
    # knife edge at x = 0, so a peg rooted straight into them never fused reliably --
    # and a lantern wants a rose anyway.
    rose = cq.Workplane("XY").box(2.2, 7.0, h * 0.34, centered=(False, True, True)) \
        .translate((0, 0, h * 0.55))
    rose = try_fillet(rose, "|X", 1.6)
    body = body.union(rose)
    return body.union(peg_p1((1.4, 0.0, h * 0.55), axis="-X"))


def cellar_hatch(w=14.0, d=11.0, t=2.0):
    body = cq.Workplane("XY").box(w, d, t, centered=(True, True, False))
    for i in range(1, 3):
        body = body.cut(cq.Workplane("XY").box(0.8, d, 0.6, centered=(True, True, False))
                        .translate((-w / 2 + i * w / 3, 0, t - 0.6)))
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))


def boot_scraper(w=7.0, h=6.0):
    body = cq.Workplane("XZ").moveTo(0, 0).lineTo(w, 0).lineTo(w, -1.6).lineTo(0, -1.6) \
        .close().extrude(-1.8)
    for s in (0, 1):
        body = body.union(cq.Workplane("XZ").moveTo(s * (w - 1.6), 0)
                          .lineTo(s * (w - 1.6) + 1.6, 0).lineTo(s * (w - 1.6) + 1.6, -h)
                          .lineTo(s * (w - 1.6), -h).close().extrude(-1.8))
    return body.union(peg_p1((0.0, 0.9, -h * 0.6), axis="-X"))


def kerb_step(w=18.0, d=6.0, h=3.0):
    body = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    body = try_chamfer(body, ">Z", 0.6)
    return body.union(peg_p1((0.0, 0.0, 0.0), axis="-Z"))
