"""Facade elements. Shapes, not parts -- what a part is gets decided in shops.py.

The first one is a window, because it is the element the kit has most of and the one that
carries every constraint at once: a bridge at the top of each pane, mullions thin enough
to read and thick enough to survive, a hollow back so light gets through, and a mounting
flange that keeps the sockets out of the light path.

Everything here obeys the rules the two coupon plates bought:

    mullions 1.2 mm      1.0 printed cleanest but is under the handling minimum; 1.2 with
                         a chamfer droops slightly and survives being picked up
    chamfered pane tops  the top of an opening is a bridge, and a small chamfer lets the
                         nozzle walk inward before it has to span
    hollow behind        a solid frame blocks the light the whole nook exists for
    flange sockets       four points at the corners, outside the illuminated area
    sockets face DOWN    the frame prints face-up, so its sockets open onto the plate;
                         cone-ended, so they are self-supporting

    python elements.py           build a window and self-test
    python elements.py --export  write out/window_sample.stl
"""
import math
import os
import sys

import cadquery as cq

import joints as J
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))

FRAME_LIP = 3.2          # frame band around the opening
FLANGE_W = 5.0           # hidden flange behind the frame, carries the sockets
MULLION = 1.2            # see the module docstring
PANE_CHAMFER = 0.8       # at the top corners of each pane


def flange_points(w, h):
    """The four socket positions, in the element's own frame.

    Four rather than two: a long part on two points rocks, and rocking is what puts a
    facade piece proud of its wall. They sit on the flange, outside the opening, so
    nothing intrudes on the light path.
    """
    x = w / 2 + FRAME_LIP + FLANGE_W / 2
    y = h / 2 + FRAME_LIP + FLANGE_W / 2
    return [(-x, -y), (x, -y), (-x, y), (x, y)]


def _pane_cut(pw, ph, t, chamfer=PANE_CHAMFER):
    """One pane opening, with its top corners chamfered so the bridge is shorter.

    A square-topped opening asks the nozzle to span the full pane width in one go. Taking
    a chamfer off each top corner lets it walk inward first, and it is invisible once the
    frame is painted.
    """
    c = min(chamfer, pw / 3, ph / 3)
    pts = [(-pw / 2, -ph / 2), (pw / 2, -ph / 2), (pw / 2, ph / 2 - c),
           (pw / 2 - c, ph / 2), (-pw / 2 + c, ph / 2), (-pw / 2, ph / 2 - c)]
    return cq.Workplane("XY").polyline(pts).close().extrude(t + 2).translate((0, 0, -1))


def panes_for(w, h):
    """How many panes a window of this size needs.

    Driven by the pane, not the window. A bigger window gets MORE mullions at the same
    pane size, because the pane top is a bridge and 12 mm is the widest one measured. The
    naive alternative -- keep 2x3 and let the panes grow -- puts a 17.4 mm bridge in a
    36 mm window, which nothing has printed.
    """
    cols = max(1, math.ceil((w + MULLION) / (float(P.MAX_PANE_W) + MULLION)))
    rows = max(1, math.ceil((h + MULLION) / (float(P.MAX_PANE_H) + MULLION)))
    return cols, rows


def window(w=22.0, h=30.0, cols=None, rows=None, t=None, mullion=MULLION):
    """A window frame: outer band, mullions, hollow back, flange with four sockets.

    Built face-up in XY. The visible face is +Z; the flange and sockets are on -Z, which
    is the side that meets the wall.
    """
    t = float(P.WALL_FACE_T if t is None else t)
    if cols is None or rows is None:
        auto_c, auto_r = panes_for(w, h)
        cols = auto_c if cols is None else cols
        rows = auto_r if rows is None else rows
    ow, oh = w + 2 * FRAME_LIP, h + 2 * FRAME_LIP
    fw, fh = ow + 2 * FLANGE_W, oh + 2 * FLANGE_W

    # flange first, then the frame standing on it -- one solid, overlapping, never tangent
    body = cq.Workplane("XY").box(fw, fh, t, centered=(True, True, False))
    body = body.union(cq.Workplane("XY").box(ow, oh, t + 1.4, centered=(True, True, False)))

    # panes: cut the whole opening, then put the mullions back
    body = body.cut(_pane_cut(w, h, t + 1.4))
    pw = (w - (cols - 1) * mullion) / cols
    ph = (h - (rows - 1) * mullion) / rows
    grid = None
    for c in range(cols):
        for r in range(rows):
            x = -w / 2 + pw / 2 + c * (pw + mullion)
            y = -h / 2 + ph / 2 + r * (ph + mullion)
            pane = _pane_cut(pw, ph, t + 1.4).translate((x, y, 0))
            grid = pane if grid is None else grid.union(pane)
    # the mullion lattice is what is LEFT of the opening once the panes are removed
    full = cq.Workplane("XY").box(w, h, t + 1.4, centered=(True, True, False))
    body = body.union(full.cut(grid))

    for x, y in flange_points(w, h):
        body = J.socket_in(body, (x, y, 0), "+Z")
    return body


def window_relief(w=22.0, h=30.0, t=None, mullion=MULLION):
    """The same window, FUSED into a wall instead of pinned to it.

    Returns (add, cut): raised frame and mullions to union onto the wall face, and the
    pane grid to cut through it. No flange, no sockets, no joint -- because a flat window
    on a flat-printing wall needs none of the three things rule 9 says earn a part its
    separation. It is the same orientation, the same filament, and its cavity is a hole.

    Whether it LOOKS as good is the one thing arithmetic cannot answer, which is why one
    of each goes on plate 3.
    """
    t = float(P.WALL_FACE_T if t is None else t)
    cols, rows = panes_for(w, h)
    ow, oh = w + 2 * FRAME_LIP, h + 2 * FRAME_LIP

    band = cq.Workplane("XY").box(ow, oh, 1.4, centered=(True, True, False))
    pw = (w - (cols - 1) * mullion) / cols
    ph = (h - (rows - 1) * mullion) / rows
    grid = None
    for c in range(cols):
        for r in range(rows):
            x = -w / 2 + pw / 2 + c * (pw + mullion)
            y = -h / 2 + ph / 2 + r * (ph + mullion)
            pane = _pane_cut(pw, ph, 40.0).translate((x, y, -20.0))
            grid = pane if grid is None else grid.union(pane)
    full = cq.Workplane("XY").box(w, h, 1.4, centered=(True, True, False))
    add = band.cut(cq.Workplane("XY").box(w, h, 4.0, centered=(True, True, True)))               .union(full.cut(grid))
    return add, grid


def wall_opening(w=22.0, h=30.0):
    """The hole this element needs in the wall behind it.

    ONE opening, larger than the element's panes and smaller than its frame. The wall does
    not reproduce the mullions: matching fine geometry on both halves is what put 21 of 21
    mounts in the wrong place last time, and a big hole cannot be misaligned.
    """
    return cq.Workplane("XY").box(w + 1.0, h + 1.0, 20.0, centered=(True, True, True))


# ==================================================================== self-test ==
def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    w, h = 22.0, 30.0
    win = window(w, h)
    t("window is one solid", len(win.solids().vals()) == 1,
      f"{len(win.solids().vals())} solids")

    bb = win.val().BoundingBox()
    t("flange is outside the frame",
      bb.xlen > w + 2 * FRAME_LIP and bb.ylen > h + 2 * FRAME_LIP,
      f"{bb.xlen:.1f} x {bb.ylen:.1f}")

    # Hollow: light has to get THROUGH THE PANES. Bulk solidity is the wrong measure --
    # the flange and frame band are meant to be solid, and a part can be 80% solid and
    # still let every photon through where it counts. Measure the aperture instead.
    probe = cq.Workplane("XY").box(w, h, 40.0, centered=(True, True, True))
    blocked = win.intersect(probe)
    blocked_area = (blocked.val().Volume() / (float(P.WALL_FACE_T) + 1.4)
                    if blocked.solids().vals() else 0.0)
    open_frac = 1.0 - blocked_area / (w * h)
    t("light gets through the panes", open_frac > 0.75,
      f"{open_frac * 100:.0f}% of the {w:.0f}x{h:.0f} aperture is open "
      f"(the rest is mullion)")

    # Mullions must clear the handling minimum, not just print.
    t("mullions clear the minimum feature", MULLION >= float(P.MIN_FEATURE_T),
      f"{MULLION} vs {float(P.MIN_FEATURE_T)} mm")

    # Four sockets, all present, none inside the opening.
    pts = flange_points(w, h)
    t("four mounting points", len(pts) == 4)
    inside = [p for p in pts if abs(p[0]) < w / 2 and abs(p[1]) < h / 2]
    t("no socket sits in the light path", not inside, f"{len(inside)} intrude")

    # The sockets must be real holes, not intentions.
    plain = cq.Workplane("XY").box(bb.xlen, bb.ylen, float(P.WALL_FACE_T),
                                   centered=(True, True, False))
    t("sockets actually cut material",
      win.val().Volume() < plain.val().Volume(),
      "compared against a plain slab of the same footprint")

    # The wall's opening must clear the panes and stay inside the frame -- see the
    # docstring: matching fine geometry on both halves is the 21-of-21 failure.
    ob = wall_opening(w, h).val().BoundingBox()
    # A storefront must be OPEN AT THE BACK. It is lit from behind, and a flange that
    # spans the width is a wall across the one place light has to pass.
    sf = storefront()
    sb = sf.val().BoundingBox()
    back = (cq.Workplane("XY")
            .box(90.0 - 4, 1.0, 72.0 - STORE_SILL - STORE_CORNICE - 4,
                 centered=(True, True, False))
            .translate((0, -STORE_WALL_T / 2, STORE_SILL + 2)))
    blocked_back = sf.intersect(back)
    bv = blocked_back.val().Volume() if blocked_back.solids().vals() else 0.0
    t("the storefront is open at the back", bv < 1.0,
      f"{bv:.1f} mm3 of material across the back opening -- a full-width flange puts "
      f"{'a wall' if bv > 1 else 'nothing'} where the light comes in")

    t("wall opening clears the panes but hides behind the frame",
      ob.xlen > w and ob.xlen < w + 2 * FRAME_LIP,
      f"opening {ob.xlen:.1f} vs pane {w:.1f}, frame {w + 2 * FRAME_LIP:.1f}")
    return out


# ================================================================== storefront ==
# The element that DOES earn being a part. A wall prints flat and face-up; a bay window
# projects 35 mm and must print standing, so the two want opposite orientations and no
# amount of fusing reconciles them. That difference is exactly what rule 9 asks for.
STORE_WALL_T = 2.0       # skin of the bay -- it is hollow behind for light
STORE_SILL = 4.0         # base course the whole thing stands on
STORE_CORNICE = 5.0      # cap over the glazing


def _bow_footprint(w, proj, facets, inset=0.0):
    """The plan of a faceted bow, as points. Back edge closed along y=0.

    Faceted rather than round on purpose: it prints better, the flats take flat glazing,
    and plate 3's bow read as curved at arm's length. `inset` shrinks it for the hollow.
    """
    pts = []
    for i in range(facets + 1):
        a = math.pi * i / facets
        # -Y, not +Y. Built bulging toward +Y it needed a +90 rotation to get its
        # projection out of the wall, and +90 also turns the part upside down -- sill at
        # the top, open end at the bottom. Bulging the other way lets -90 do both jobs
        # right. Handedness, not a sign slip: no rotation fixes a mirrored frame.
        pts.append((-math.cos(a) * (w / 2 - inset), -math.sin(a) * (proj - inset)))
    return pts


def storefront(w=90.0, h=72.0, proj=None, facets=3, t=None):
    """A bow-fronted shop window: sill, faceted glazing, cornice, and a back flange.

    Built STANDING -- base on z=0, growing up, back face at y=0 -- because that is how it
    prints and how it hangs on the wall. Hollow behind, so the light the nook exists for
    gets through.
    """
    proj = float(P.STOREFRONT_PROJ if proj is None else proj)
    t = STORE_WALL_T if t is None else t
    glaz_h = h - STORE_SILL - STORE_CORNICE

    outer = _bow_footprint(w, proj, facets)
    body = cq.Workplane("XY").polyline(outer).close().extrude(h)

    # hollow: the same plan, inset, cut from sill top to under the cornice
    inner = _bow_footprint(w, proj, facets, inset=t)
    # STOP UNDER THE CORNICE. Extruding the void the full height and shifting it up by the
    # sill ran it straight out of the top, so the bay was a tube open at one end -- and
    # mounted, that open end faced down and leaked light out under the shop.
    void = (cq.Workplane("XY").polyline(inner).close()
            .extrude(h - STORE_SILL - STORE_CORNICE)
            .translate((0, 0, STORE_SILL)))
    body = body.cut(void)

    # glazing: one opening per facet, panes sized by MAX_PANE_W like every other window
    for i in range(facets):
        (x0, y0), (x1, y1) = outer[i], outer[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        seg = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        open_w = seg - 2 * FRAME_LIP
        if open_w <= 4.0:
            continue
        cols = max(1, math.ceil((open_w + MULLION) / (float(P.MAX_PANE_W) + MULLION)))
        pw = (open_w - (cols - 1) * MULLION) / cols
        for c in range(cols):
            ox = -open_w / 2 + pw / 2 + c * (pw + MULLION)
            pane = (cq.Workplane("XZ")
                    .box(pw, glaz_h - 2 * FRAME_LIP, 4 * proj,
                         centered=(True, True, True))
                    .translate((ox, 0, STORE_SILL + glaz_h / 2))
                    .rotate((0, 0, 0), (0, 0, 1), ang)
                    .translate((mx, my, 0)))
            body = body.cut(pane)

    # Back flange: SIDE STRIPS ONLY, never a full plate.
    #
    # It was a full-width plate first, and that is a wall across the back of a window --
    # the one place in the whole model where light has to get through. A storefront lit
    # from behind with its back closed is an unlit storefront.
    #
    # The flange exists to carry sockets, and sockets are at the sides. So put material
    # only where a socket needs it and leave the middle open to the light box.
    # The strips must be DEEP, not just present. A socket needs socket_min_material of
    # material behind its mouth and a 2 mm flange has none of it -- the bore came out as
    # a through hole with 2 mm of engagement, and when the mouth moved it cut pure air and
    # all four pegs fouled. The strips run FORWARD into the bay's depth, alongside the
    # bow rather than in front of it, so they take nothing from the light path.
    strip_w = FLANGE_W + 4.0
    strip_d = J.socket_min_material()
    for sx in (-1, 1):
        body = body.union(cq.Workplane("XY")
                          .box(strip_w, strip_d, h, centered=(True, False, False))
                          .translate((sx * (w / 2 + FLANGE_W / 2), -strip_d, 0)))
    for x, z in store_points(w, h):
        # socket_in here, NOT socket_facing -- and that is the opposite of what the flat
        # window needs. Whether the D-flat wants compensating depends on the total
        # rotation a socket ends up under, which is the build handedness AND the assembly
        # rotation together. Changing the footprint to bulge -Y changed the assembly
        # rotation from +90 to -90, and that flipped the answer.
        #
        # Both were tried and MEASURED against the real wall: compensated fouls by
        # 6.41 mm3, uncompensated by 0.0000. There is no rule to remember here, only a
        # test -- which is why wall.py mates a storefront to a panel on every run.
        body = J.socket_in(body, (x, 0.0, z), "-Y")
    return body


def store_points(w, h):
    """The four peg positions for a storefront, in ITS frame (x across, z up).

    Same job as flange_points and the same reason for four: a 90 mm part on two points
    rocks. Out at the flange edges, clear of the glazing.
    """
    x = w / 2 + FLANGE_W / 2
    return [(-x, STORE_SILL + 4.0), (x, STORE_SILL + 4.0),
            (-x, h - STORE_CORNICE - 4.0), (x, h - STORE_CORNICE - 4.0)]


if __name__ == "__main__":
    print("elements -- the window\n")
    bad = 0
    for ok, name, detail in self_test():
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    if "--export" in sys.argv:
        d = P.out_dir("stl")
        cq.exporters.export(window().val(), os.path.join(d, "window_sample.stl"))
        print(f"\n  wrote {d}/window_sample.stl")

    print(f"\n  {bad} failures")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)


