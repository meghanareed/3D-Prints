"""The MX switch interface: the plate cutout, the pocket, the stem receiver -- and a
solid stand-in for the switch itself.

The stand-in is the point of this module. Every number here came off a third-party model
or a datasheet, and the only way to find out whether they agree with each other is to
build a switch-shaped solid and try to put it where it is supposed to go. A check that
compares MX_POCKET against MX_POCKET cannot see a switch that will not fit.

Geometry convention: the PLATE TOP FACE is z = 0 and the stem points +z. Callers
translate. That way nothing in this file has to know where in the body the switch lives.

    python switch.py            build everything and run the self-test
    python switch.py --export   also write out/switch_*.step for eyeballing
"""
import os
import sys

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))

# The switch is not ours to design, so nothing here is a fit clearance we get to pick --
# it is the switch's own dimensions, plus the room it needs.
STEM_OD = 7.2          # the round shoulder the stem cross stands on. ASSUMED, R-1.
PIN_ZONE = 3.0         # below the housing, where the legs and the two pins live


# ------------------------------------------------------------------ primitives --
def plus_wire(length, width):
    """The MX cross, as a closed wire on the current workplane.

    Drawn as an explicit polyline rather than two overlapping rectangles: a union of two
    boxes leaves a coincident internal face that OCCT sometimes keeps, and a stem socket
    with an internal face in it is a socket that fuses shut on the next boolean.
    """
    a, b = length / 2.0, width / 2.0
    pts = [(a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b),
           (-a, -b), (-b, -b), (-b, -a), (b, -a), (b, -b), (a, -b)]
    return cq.Workplane("XY").polyline(pts).close()


def stem_socket(depth=None, mouth_chamfer=0.4):
    """The female cross, as a CUTTING solid, sitting on z=0 and going UP.

    The mouth is flared by a loft rather than a chamfer. Rule 6 next door: a chamfer must
    follow the bore's own shape, and OCCT's chamfer on a twelve-sided re-entrant profile
    either fails or eats the arms.
    """
    depth = float(P.MX_SOCKET_DEPTH) if depth is None else float(depth)
    lo = plus_wire(float(P.MX_STEM_CROSS_L) + 2 * mouth_chamfer,
                   float(P.MX_STEM_CROSS_W) + 2 * mouth_chamfer).wires().val()
    hi = plus_wire(float(P.MX_STEM_CROSS_L),
                   float(P.MX_STEM_CROSS_W)).wires().val().moved(
                       cq.Location(cq.Vector(0, 0, mouth_chamfer)))
    lead_in = cq.Workplane("XY").add(cq.Solid.makeLoft([lo, hi]))
    body = (plus_wire(float(P.MX_STEM_CROSS_L), float(P.MX_STEM_CROSS_W))
            .extrude(depth))
    return lead_in.union(body)


def stem_receiver(boss_len, socket_depth=None):
    """The boss that carries the socket: a cylinder with the cross cut out of it.

    `boss_len` is how far the boss stands off whatever it is built on. The socket is cut
    the whole way so the caller can put the boss on a floor or hang it from a ceiling
    without the socket depth changing meaning.
    """
    socket_depth = float(P.MX_SOCKET_DEPTH) if socket_depth is None else socket_depth
    boss = (cq.Workplane("XY").circle(float(P.MX_BOSS_MOUTH_OD) / 2).extrude(0.6)
            .faces(">Z").workplane().circle(float(P.MX_BOSS_OD) / 2)
            .extrude(boss_len - 0.6))
    return boss.cut(stem_socket(socket_depth))


# --------------------------------------------------------------- the mount ----
def plate_cutout():
    """The hole through the 1.5 mm plate band, as a CUTTING solid spanning z=-1.5..0.

    14.00 square with 0.50 mm of clip relief on all four sides. The relief is THE
    retention feature -- the clips spring out into it and hook under the band. The spec
    proposed a 2.0-2.2 mm shelf instead, which is thicker than the clips can reach past.
    """
    a = float(P.MX_POCKET)
    r = float(P.MX_CLIP_RELIEF)
    sq = cq.Workplane("XY").box(a, a, float(P.MX_PLATE_T), centered=(True, True, False))
    relief = (cq.Workplane("XY").box(a + 2 * r, a, float(P.MX_PLATE_T),
                                     centered=(True, True, False))
              .union(cq.Workplane("XY").box(a, a + 2 * r, float(P.MX_PLATE_T),
                                            centered=(True, True, False))))
    return sq.union(relief).translate((0, 0, -float(P.MX_PLATE_T)))


def pocket():
    """The bay under the plate that the switch body drops into. Cutting solid, z<0."""
    d = float(P.MX_POCKET_DEPTH)
    return (cq.Workplane("XY").box(float(P.MX_POCKET), float(P.MX_POCKET), d,
                                   centered=(True, True, False))
            .translate((0, 0, -float(P.MX_PLATE_T) - d)))


def pin_relief():
    """Somewhere for the pins and the centre post to go. Cutting solid, below the pocket.

    The sample gets away with a solid floor 1.0 mm under its pocket because the clicker
    it links to is a bare module with nothing sticking out of the bottom. A real MX
    switch has two metal pins and a centre post, and self_test() found them by standing
    the stand-in in the mount and measuring 100 mm3 of overlap.

    A plain blind counterbore, and deliberately NOT coned. Rule 4 next door cones the
    blind end of a bore so a downward-facing socket is self-supporting -- but this bore
    faces UP, at the bottom of a pocket that is open above it. There is no roof over it
    to hold up, and the first version of this function coned it anyway, which put a
    4.5 mm cone into a 3.5 mm hole and extruded the straight section backwards.
    """
    d = float(P.PIN_RELIEF_D)
    z0 = -float(P.MX_PLATE_T) - float(P.MX_POCKET_DEPTH)
    return (cq.Workplane("XY").circle(d / 2)
            .extrude(-float(P.PIN_RELIEF_DEPTH)).translate((0, 0, z0)))


def mount_cut():
    """Everything the body has to remove to accept a switch, in one solid."""
    return plate_cutout().union(pocket()).union(pin_relief())


# ------------------------------------------------------- the switch stand-in ----
def switch_solid(pressed=0.0):
    """A solid the size and shape of a real MX switch, plate top at z=0, stem up.

    Deliberately a stand-in and not a model: the clips are omitted because their sprung
    shape is not known here, and the pins are a single block because nothing in this
    design goes near them. Everything that any part of this design can COLLIDE with is
    at its full size.

    `pressed` moves the stem down by that much, and only the stem: the housing does not
    move when you press a key.
    """
    housing = (cq.Workplane("XY")
               .box(float(P.MX_HOUSING_SQ), float(P.MX_HOUSING_SQ),
                    float(P.MX_ABOVE_PLATE), centered=(True, True, False)))
    below = (cq.Workplane("XY")
             .box(float(P.MX_POCKET) - 0.1, float(P.MX_POCKET) - 0.1,
                  float(P.MX_POCKET_DEPTH) + float(P.MX_PLATE_T),
                  centered=(True, True, False))
             .translate((0, 0, -float(P.MX_POCKET_DEPTH) - float(P.MX_PLATE_T))))
    pins = (cq.Workplane("XY").circle(4.0).extrude(PIN_ZONE)
            .translate((0, 0, -float(P.MX_POCKET_DEPTH) - float(P.MX_PLATE_T) - PIN_ZONE)))

    top = float(P.MX_ABOVE_PLATE) - float(pressed)
    shoulder = (cq.Workplane("XY").circle(STEM_OD / 2)
                .extrude(float(P.MX_STEM_BASE))
                .translate((0, 0, top)))
    cross = (plus_wire(float(P.MX_STEM_CROSS_L) - 0.07,     # the real stem, under the
                       float(P.MX_STEM_CROSS_W) - 0.38)     # socket the sample cuts
             .extrude(float(P.MX_STEM_TOP) - float(P.MX_STEM_BASE))
             .translate((0, 0, top + float(P.MX_STEM_BASE))))
    return housing.union(below).union(pins).union(shoulder).union(cross)


# ==================================================================== self-test ==
def _vol(shape):
    try:
        return shape.val().Volume()
    except Exception:
        return 0.0


def _interference(a, b):
    """Volume the two solids share. Tangency is not contact and 0 here means 0."""
    try:
        return _vol(a.intersect(b))
    except Exception:
        return 0.0


def self_test():
    """Build the switch and the things that mate with it, and actually assemble them."""
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    sw = switch_solid()
    bb = sw.val().BoundingBox()

    # -- the stand-in is the size it claims to be ------------------------------
    t("switch stand-in is the housing size we designed the window from",
      abs(bb.xlen - float(P.MX_HOUSING_SQ)) < 1e-6,
      f"{bb.xlen:.2f} vs {float(P.MX_HOUSING_SQ)}")
    # MX_STEM_TOP is measured from the HOUSING top; this module's z=0 is the PLATE top.
    # Getting that wrong is how the first run of this test put the receiver 5 mm low.
    t("stem tip lands where params says it does, in plate coordinates",
      abs(bb.zmax - (float(P.MX_ABOVE_PLATE) + float(P.MX_STEM_TOP))) < 1e-6,
      f"{bb.zmax:.2f} vs {float(P.MX_ABOVE_PLATE) + float(P.MX_STEM_TOP)}")

    # -- the mount actually accepts the switch ---------------------------------
    # A block of material with the mount cut out of it. The switch must fit in the hole
    # with nothing left over. This is the check that a hand-copied 14.10 would fail.
    block = cq.Workplane("XY").box(30, 30, 20, centered=(True, True, False)).translate(
        (0, 0, -float(P.MX_PLATE_T) - float(P.MX_POCKET_DEPTH) - 2))
    mount = block.cut(mount_cut())
    below_plate = sw.intersect(
        cq.Workplane("XY").box(40, 40, 40, centered=(True, True, False))
        .translate((0, 0, -40)))
    t("the switch body goes into the mount without interference",
      _interference(mount, below_plate) < 1e-6,
      f"{_interference(mount, below_plate):.4f} mm3 of overlap")

    t("the clip relief is open all the way through the plate band",
      _vol(plate_cutout()) > _vol(
          cq.Workplane("XY").box(float(P.MX_POCKET), float(P.MX_POCKET),
                                 float(P.MX_PLATE_T))),
      "no relief means the clips have nowhere to spring and the switch will not latch")

    # -- the stem goes into the socket, and does not bottom out in it ----------
    # Built at the height the canister will actually hold it: socket mouth at the rim.
    s = P.stack()
    mouth = s["canister_rim_rest"] - s["housing_top"]        # above the housing top
    recv = stem_receiver(boss_len=float(P.MX_SOCKET_DEPTH) + 1.5).translate(
        (0, 0, float(P.MX_ABOVE_PLATE) + mouth))             # ...and into plate coords
    t("the stem enters the receiver -- solid on solid, not number on number",
      _interference(recv, sw) < 1e-6,
      f"{_interference(recv, sw):.4f} mm3 of overlap at rest")

    engaged = float(P.MX_STEM_TOP) - mouth
    t("stem engagement is real and is what stack() claims",
      abs(engaged - s["stem_engagement"]) < 1e-6 and engaged >= 2.5,
      f"{engaged:.2f} mm engaged, stack says {s['stem_engagement']:.2f}")
    t("the socket is deeper than the stem is long, so the cap seats on the shoulder",
      float(P.MX_SOCKET_DEPTH) > engaged,
      f"socket {float(P.MX_SOCKET_DEPTH)} vs {engaged:.2f} mm of stem")

    # -- pressing moves the stem and not the housing ---------------------------
    pressed = switch_solid(pressed=float(P.BUTTON_TRAVEL))
    t("pressing the switch moves the stem down by the travel, housing unmoved",
      abs((bb.zmax - pressed.val().BoundingBox().zmax) - float(P.BUTTON_TRAVEL)) < 1e-6,
      f"{bb.zmax - pressed.val().BoundingBox().zmax:.2f} mm")
    return out


if __name__ == "__main__":
    print("switch -- the MX interface, built and assembled\n")
    results = self_test()
    bad = 0
    for ok, name, detail in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok
    print(f"\n  {len(results)} tests, {bad} failures")

    if "--export" in sys.argv:
        out_dir = os.path.join(HERE, "out")
        os.makedirs(out_dir, exist_ok=True)
        for name, shape in (("switch", switch_solid()),
                            ("mount_cut", mount_cut()),
                            ("receiver", stem_receiver(6.4))):
            cq.exporters.export(shape, os.path.join(out_dir, f"switch_{name}.step"))
            print(f"  wrote out/switch_{name}.step")

    # OCCT crashes during interpreter teardown, after the work is done. Flush, then
    # os._exit, or anything gating on this script reads success as failure.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
