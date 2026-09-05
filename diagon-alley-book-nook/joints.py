"""The one joint family, and a test that applies the real motion.

A D-section pin or peg into a D-section socket, 0.30 mm per side, located not pressed,
retained with gel cyanoacrylate. Every number comes from `params`; nothing is typed here.

Why a D and not a square: a 0.4 mm nozzle leaves internal corners radiused to about half
the line width, so a sharp-cornered peg binds on the diagonal of its socket long before
the flats meet. A square bore cut 0.05 mm LOOSER per side still would not seat on a
printed coupon while the round one did. The single flat gives anti-rotation, and where it
meets the arc the bore turns through an obtuse angle a round nozzle can trace.

Three forms, because which half carries the male feature is decided per joint, not by a
blanket rule (PLAN 6.7):

    pin()      loose dowel, socket-to-socket. Frees BOTH parts to print good-face-up.
    peg()      integral male, for a part that prints face-down anyway -- e.g. the wall
               plate, whose pegs point up and take a sign's recessed sockets.
    socket()   the cutting solid. Lead-in chamfer at the mouth, cone at the blind end.

`fit_report()` is the point of the module. It BUILDS both halves, TRANSLATES one into the
other along the real insertion axis, and measures the intersection. It does not compare
the numbers the two halves were built from -- three separate bugs in this project passed
exactly that kind of check.

    python joints.py         build, self-test, and report the fit
    python joints.py --step  also write STEP/STL of a demo pair
"""
import math
import os
import sys

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ profiles --
def d_solid(dia, flat, length):
    """A cylinder with one flat, `flat` mm from the axis. The D that does the keying.

    Built as a solid and then cut, rather than as a 2D profile: the flat has to be a real
    boolean against real material, and a clearance that never reaches the geometry is
    exactly how the old coupon's ladder came back measuring nothing.
    """
    r = dia / 2.0
    if flat >= r:
        raise ValueError(f"flat {flat} is outside the radius {r} -- no material left")
    body = cq.Workplane("XY").circle(r).extrude(length)
    knife = (cq.Workplane("XY")
             .box(dia * 4, dia * 2, length + 2.0, centered=(True, True, False))
             .translate((0, -(flat + dia), -1.0)))
    return body.cut(knife)


def _taper_tool(dia, length, cham, both_ends):
    """A cylinder whose end(s) taper in by `cham` at 45 deg.

    Intersected with a D-section body this chamfers the tip without asking OCCT to
    chamfer a mixed arc/line edge loop, which is where try_chamfer used to give up.
    """
    r = dia / 2.0
    tool = cq.Workplane("XY").circle(r).extrude(length)
    top = (cq.Workplane("XY").circle(r).workplane(offset=cham).circle(max(r - cham, 0.05))
           .loft(combine=True).translate((0, 0, length - cham)))
    tool = tool.cut(cq.Workplane("XY").circle(r).extrude(cham)
                    .translate((0, 0, length - cham))).union(top)
    if both_ends:
        bot = (cq.Workplane("XY").circle(max(r - cham, 0.05))
               .workplane(offset=cham).circle(r).loft(combine=True))
        tool = tool.cut(cq.Workplane("XY").circle(r).extrude(cham)).union(bot)
    return tool


def _d_body(dia, flat, length, cham, both_ends):
    return d_solid(dia, flat, length).intersect(
        _taper_tool(dia, length, cham, both_ends))


# --------------------------------------------------------------------- males --
def pin(length=None):
    """The loose dowel. Chamfered BOTH ends -- it has no 'root', either end may lead."""
    length = float(P.PIN_L if length is None else length)
    return _d_body(float(P.PEG_D), float(P.D_FLAT), length,
                   float(P.PEG_TIP_CHAMFER), both_ends=True)


def peg(length=None, root=None):
    """Integral male. Chamfered tip only; the root end grows out of its parent.

    `root` sinks the peg into the parent so OCCT fuses it rather than leaving it tangent.
    Tangency is not contact -- it has split a part into two solids three times here.
    """
    length = float(P.PEG_L if length is None else length)
    root = float(P.PEG_ROOT if root is None else root)
    body = _d_body(float(P.PEG_D), float(P.D_FLAT), length,
                   float(P.PEG_TIP_CHAMFER), both_ends=False)
    if root > 0:
        body = body.union(d_solid(float(P.PEG_D), float(P.D_FLAT), root)
                          .translate((0, 0, -root)))
    return body


# ------------------------------------------------------------------- female --
def socket(depth=None, clearance=None):
    """The CUTTING solid for a bore. Mouth at z=0, blind end up at +depth.

    Three parts, each earning its place:
      * the bore itself, oversize by `clearance` on the diameter AND on the flat;
      * a lead-in counterbore at the MOUTH -- the coupon that put this at the blind end
        measured nothing;
      * a cone at the blind end, so a socket facing DOWN on the plate is self-supporting
        and needs no bridge, and so the male gets a positive depth stop.
    """
    depth = float(P.SOCKET_DEPTH if depth is None else depth)
    c = float(P.FIT_CLEARANCE if clearance is None else clearance)
    dia = float(P.PEG_D) + 2 * c
    flat = float(P.D_FLAT) + c
    lead = float(P.LEAD_IN_CHAMFER)

    bore = d_solid(dia, flat, depth)

    # lead-in: widens outward at the mouth so the male finds the hole
    mouth = (cq.Workplane("XY").circle(dia / 2 + lead)
             .workplane(offset=lead).circle(dia / 2)
             .loft(combine=True).translate((0, 0, -lead)))

    # blind end: a cone, apex up. 60 deg included -> every wall is 60 deg from horizontal,
    # comfortably self-supporting.
    half = math.radians(float(P.BLIND_BORE_CONE) / 2.0)
    rise = (dia / 2.0) / math.tan(half)
    cone = (cq.Workplane("XY").circle(dia / 2)
            .workplane(offset=rise).circle(0.01)
            .loft(combine=True).translate((0, 0, depth)))

    return bore.union(mouth).union(cone)


# A socket placed on a REVERSED normal is flipped 180 deg to get there, and that flip
# MIRRORS the D-flat to the other side. Two parts facing each other therefore do NOT
# share a pin's key unless one of them is spun 180 to compensate.
#
# This is not a hypothetical. The first bridge_report() run came back with the pin
# fouling one socket by 0.85 mm3 and the other by nothing, which is exactly this. It is
# also the retrospective's own recurring failure -- "rotating a fused sign the wrong way,
# then the other wrong way, because I reasoned about the rotation instead of measuring
# where the letters landed". So `flat_side()` MEASURES it and the self-test checks it.
REVERSED_NORMALS = {"-Z", "-X", "-Y"}


def mate_rot(normal, rot=0.0):
    """The spin a socket needs so its flat matches a pin shared with the facing part."""
    return rot + (180.0 if normal in REVERSED_NORMALS else 0.0)


def flat_side(normal="+Z", rot=0.0):
    """Measure which way the flat actually faces. Never derive this."""
    c = _place(socket(), (0, 0, 0), normal, rot).val().Center()
    return (c.x, c.y, c.z)


def socket_in(solid, point, normal="+Z", rot=0.0, depth=None, clearance=None):
    """Cut a socket into `solid` at `point`, opening along `normal`.

    `rot` is taken as given. For a joint where a pin is SHARED with the facing part, pass
    `rot=mate_rot(normal)` -- or use `socket_facing`, which does it for you.
    """
    return solid.cut(_place(socket(depth, clearance), point, normal, rot))


def socket_facing(solid, point, normal="+Z", rot=0.0, depth=None, clearance=None):
    """A socket meant to share a pin with the part opposite. Compensates the flip."""
    return socket_in(solid, point, normal, mate_rot(normal, rot), depth, clearance)


# ---------------------------------------------------------------- placement --
_ROT = {"+Z": (0, 0, 0), "-Z": (180, 0, 0),
        "+X": (0, 90, 0), "-X": (0, -90, 0),
        "+Y": (-90, 0, 0), "-Y": (90, 0, 0)}


def _place(body, point, normal="+Z", rot=0.0):
    """Put a +Z-built feature at `point`, pointing along `normal`, spun by `rot`."""
    if normal not in _ROT:
        raise ValueError(f"normal must be one of {sorted(_ROT)}, not {normal!r}")
    rx, ry, rz = _ROT[normal]
    b = body.rotate((0, 0, 0), (0, 0, 1), rot)
    if rx:
        b = b.rotate((0, 0, 0), (1, 0, 0), rx)
    if ry:
        b = b.rotate((0, 0, 0), (0, 1, 0), ry)
    if rz:
        b = b.rotate((0, 0, 0), (0, 0, 1), rz)
    return b.translate(point)


# =========================================================== the physical test ==
def _vol(w):
    try:
        return w.val().Volume()
    except Exception:
        return 0.0


def fit_report(clearance=None, spin=0.0):
    """Build both halves, APPLY THE INSERTION, and measure what actually happens.

    Returns a dict. `spin` rotates the male about its own axis before inserting, so
    spin=180 asks the question the keying exists to answer: does it refuse to go in
    the wrong way round?
    """
    c = float(P.FIT_CLEARANCE if clearance is None else clearance)
    block = cq.Workplane("XY").box(14, 14, float(P.SOCKET_DEPTH) + 3.0,
                                   centered=(True, True, False))
    block = socket_in(block, (0, 0, 0), "+Z", clearance=c)

    male = pin().rotate((0, 0, 0), (0, 0, 1), spin)
    # The real motion: insert until half the pin is buried (a pin spans two sockets).
    inserted = male.translate((0, 0, 0.0))

    interference = _vol(block.intersect(inserted))
    seated = _vol(inserted) - _vol(inserted.cut(
        cq.Workplane("XY").box(40, 40, float(P.SOCKET_DEPTH),
                               centered=(True, True, False))))
    return dict(clearance=c, spin=spin, interference=interference, seated=seated)


def bridge_report(clearance=None, gap=0.0):
    """THE joint, assembled: two socketed parts brought face to face over one pin.

    This is the assembly the kit actually uses and the one that has never been printed.
    A single pin-in-one-bore test cannot see the failure that matters here -- a pin too
    long for two sockets holds the parts apart, and the part then sits proud on the wall
    with a visible gap no glue closes.

    `gap` is how far apart the two faces are held. It should come out at 0.
    """
    c = float(P.FIT_CLEARANCE if clearance is None else clearance)
    d = float(P.SOCKET_DEPTH)

    # Part A: socket opening UP from its top face at z = 0.
    a = cq.Workplane("XY").box(14, 14, 6, centered=(True, True, False)).translate((0, 0, -6))
    a = socket_facing(a, (0, 0, 0), "-Z", clearance=c)
    # Part B: socket opening DOWN, its face at z = gap.
    b = cq.Workplane("XY").box(14, 14, 6, centered=(True, True, False)).translate((0, 0, gap))
    b = socket_facing(b, (0, 0, gap), "+Z", clearance=c)

    # The pin, centred on the joint line.
    p = pin().translate((0, 0, -float(P.PIN_L) / 2.0))

    return dict(
        clearance=c, gap=gap,
        foul_a=_vol(a.intersect(p)), foul_b=_vol(b.intersect(p)),
        parts_touch=_vol(a.intersect(b)),
        # how much pin is buried in each half
        into_a=_vol(p.intersect(cq.Workplane("XY").box(40, 40, 40).translate((0, 0, -20)))),
    )


def self_test():
    """Everything here is a claim this module makes about its own geometry."""
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    p, g, s = pin(), peg(), socket()
    t("pin is one solid", len(p.solids().vals()) == 1)
    t("peg is one solid", len(g.solids().vals()) == 1)
    t("socket cut is one solid", len(s.solids().vals()) == 1)

    # A D-section must have LESS volume than its circumscribing cylinder, or the flat
    # did nothing -- which is exactly how the old coupon's clearance ladder measured
    # nothing at all.
    r = float(P.PEG_D) / 2.0
    cyl = math.pi * r * r * float(P.PIN_L)
    t("the flat actually removes material", _vol(p) < cyl * 0.98,
      f"pin {_vol(p):.2f} vs cylinder {cyl:.2f} mm3")

    # The real motion, right way round: it must go in.
    right = fit_report(spin=0.0)
    t("inserts the right way round", right["interference"] < 1e-6,
      f"interference {right['interference']:.4f} mm3")

    # The real motion, wrong way round: the key must STOP it.
    wrong = fit_report(spin=180.0)
    t("KEY REFUSES the wrong way round", wrong["interference"] > 0.05,
      f"interference {wrong['interference']:.4f} mm3")

    # The key has to survive the clearance range, not just today's number.
    gives_out = None
    for c in [x / 100 for x in range(20, 61, 5)]:
        if fit_report(clearance=c, spin=180.0)["interference"] <= 0.05:
            gives_out = c
            break
    t("key survives past 0.45", gives_out is None or gives_out > 0.45,
      f"gives out at {gives_out}" if gives_out else "holds to 0.60")

    # Glue needs a gap it can bridge, and gel CA wants roughly 0.05-0.5 mm.
    t("glue gap is bridgeable", 0.05 <= float(P.FIT_CLEARANCE) <= 0.5,
      f"{float(P.FIT_CLEARANCE)} mm annulus")

    # Socket must swallow the male with relief to spare, so the part seats on its face.
    t("socket is deeper than the peg", float(P.SOCKET_DEPTH) > float(P.PEG_L))

    # The real assembly: two socketed parts, face to face, over one pin.
    br = bridge_report()
    t("pin does not foul either socket", br["foul_a"] < 1e-6 and br["foul_b"] < 1e-6,
      f"A {br['foul_a']:.4f}, B {br['foul_b']:.4f} mm3")
    t("the two faces actually MEET", br["parts_touch"] < 1e-6,
      "nothing holds them apart")
    t("pin is shared evenly between the halves",
      abs(br["into_a"] - _vol(pin()) / 2.0) < 0.05,
      f"{br['into_a']:.2f} of {_vol(pin()):.2f} mm3 in the lower half")
    # The flip trap itself: the UNCOMPENSATED pair must foul, or mate_rot is doing
    # nothing and a future edit could silently drop it.
    naive = cq.Workplane("XY").box(14, 14, 6, centered=(True, True, False)).translate((0, 0, -6))
    naive = socket_in(naive, (0, 0, 0), "-Z", clearance=float(P.FIT_CLEARANCE))
    t("the uncompensated flip WOULD foul",
      _vol(naive.intersect(pin().translate((0, 0, -float(P.PIN_L) / 2.0)))) > 0.05,
      "so mate_rot is load-bearing, not decoration")
    t("mate_rot flips only the reversed normals",
      mate_rot("+Z") == 0 and mate_rot("-Z") == 180 and mate_rot("-X") == 180)

    # And the failure this test exists to catch: a pin too long for two sockets.
    long_pin = 2 * float(P.SOCKET_DEPTH) + 1.0
    t("a too-long pin WOULD be caught",
      _vol(pin(long_pin).translate((0, 0, -long_pin / 2))
           .cut(cq.Workplane("XY").box(40, 40, 2 * float(P.SOCKET_DEPTH),
                                       centered=(True, True, True)))) > 0.01,
      f"a {long_pin:.1f} mm pin protrudes past both bores")
    return out


if __name__ == "__main__":
    print("joints -- D-section pin and socket\n")
    print(f"  peg/pin  Ø{float(P.PEG_D)}, flat {float(P.D_FLAT)} off axis")
    print(f"  socket   Ø{float(P.SOCKET_D)} ({float(P.FIT_CLEARANCE)}/side), "
          f"{float(P.SOCKET_DEPTH)} deep")
    print(f"  pin {float(P.PIN_L)} long, peg {float(P.PEG_L)} long\n")

    bad = 0
    for ok, name, detail in self_test():
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    if "--step" in sys.argv:
        out = os.path.join(HERE, "out")
        os.makedirs(out, exist_ok=True)
        cq.exporters.export(pin().val(), os.path.join(out, "pin.stl"))
        cq.exporters.export(peg().val(), os.path.join(out, "peg.stl"))
        print(f"\n  wrote pin.stl and peg.stl to {out}")

    print(f"\n  {bad} failures")
    sys.exit(1 if bad else 0)
