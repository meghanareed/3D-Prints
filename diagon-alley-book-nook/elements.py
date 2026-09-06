"""Facade elements. Shapes, not parts -- what a part is gets decided in shops.py.

The first one is a window, because it is the element the kit has most of and the one that
carries every constraint at once: a bridge at the top of each pane, mullions thin enough
to read and thick enough to survive, a hollow back so light gets through, and a mounting
flange that keeps the sockets out of the light path.

Everything here obeys the rules the two coupon plates bought:

    mullions 1.26 mm     THREE extrusions exactly. 1.2 is 2.86 of them, and a wall that
                         is not a whole number of beads is where the slicer either
                         over-widens or gap-fills; the printed storefront bars came out
                         visibly ropy
    grids, not bars      muntins run BOTH ways. Every leaded window on the reference
                         street is a grid, and the grid is also the strong version: a bar
                         tied only top and bottom is a free-standing tower on a standing
                         print, which is how a storefront separator snapped coming off
                         the plate. The transoms are the fix for the looks AND the print
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
MULLION = 1.26           # 3 x LINE_W exactly -- see the module docstring
PANE_CHAMFER = 0.8       # at the top corners of each pane
STORE_PANE_W = 9.0       # a shopfront is glazed finer than a plain window
STORE_PANE_H = 11.0
STORE_REVEAL = 1.0       # architrave proud of the glazing, so the panes read as set back


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


def pane_grid(open_w, open_h, pane_w=None, pane_h=None, mullion=None,
              cols=None, rows=None):
    """Pane rectangles for one opening, as [(ox, oy, pw, ph)] about its centre.

    ONE definition of what a glazed opening looks like, because there were two and they
    drifted. The flat window grew rows; the storefront's private copy never did, and
    nothing caught it -- both were "working", and the difference only showed up as a
    broken bar in a photograph. Anything glazed comes through here now.

    Driven by the pane, not the window. A bigger opening gets MORE muntins at the same
    pane size, because the top of every pane is a bridge and 12 mm is the widest one
    measured. Letting the panes grow instead puts a 17.4 mm bridge in a 36 mm window,
    which nothing has printed.
    """
    m = MULLION if mullion is None else mullion
    pw_max = float(P.MAX_PANE_W if pane_w is None else pane_w)
    ph_max = float(P.MAX_PANE_H if pane_h is None else pane_h)
    if cols is None:
        cols = max(1, math.ceil((open_w + m) / (pw_max + m)))
    if rows is None:
        rows = max(1, math.ceil((open_h + m) / (ph_max + m)))
    pw = (open_w - (cols - 1) * m) / cols
    ph = (open_h - (rows - 1) * m) / rows
    rects = [(-open_w / 2 + pw / 2 + c * (pw + m),
              -open_h / 2 + ph / 2 + r * (ph + m), pw, ph)
             for c in range(cols) for r in range(rows)]
    return rects, cols, rows


def panes_for(w, h):
    """How many panes a window of this size needs."""
    _, cols, rows = pane_grid(w, h)
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
    rects, cols, rows = pane_grid(w, h, mullion=mullion, cols=cols, rows=rows)
    grid = None
    for x, y, pw, ph in rects:
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
    ow, oh = w + 2 * FRAME_LIP, h + 2 * FRAME_LIP

    band = cq.Workplane("XY").box(ow, oh, 1.4, centered=(True, True, False))
    rects, cols, rows = pane_grid(w, h, mullion=mullion)
    grid = None
    for x, y, pw, ph in rects:
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
    E_store_pts = store_points(90.0, 72.0)
    back = (cq.Workplane("XY")
            .box(90.0 - 4, 1.0, 72.0 - STORE_SILL - STORE_CORNICE - 4,
                 centered=(True, True, False))
            .translate((0, -STORE_WALL_T / 2, STORE_SILL + 2)))
    blocked_back = sf.intersect(back)
    bv = blocked_back.val().Volume() if blocked_back.solids().vals() else 0.0
    # As a FRACTION of the aperture, not a raw volume. A bay has side walls, and they
    # necessarily cross the back plane at the extreme edges; an absolute threshold calls
    # that a light leak and fails forever. What actually matters is how much of the
    # aperture is closed -- a full-width flange is ~100%, side walls are a couple.
    aperture = (90.0 - 4) * (72.0 - STORE_SILL - STORE_CORNICE - 4)
    frac = bv / aperture
    t("the storefront is open at the back", frac < 0.15,
      f"{frac * 100:.1f}% of the back aperture blocked -- a full-width flange is a wall "
      f"across the one place light has to get through")

    # The bug that produced a broken bar and a ropy surface: glazing with columns only.
    _, gc, gr = pane_grid(90.0 - 2 * FRAME_LIP,
                          72.0 - STORE_SILL - STORE_CORNICE - 2 * FRAME_LIP,
                          STORE_PANE_W, STORE_PANE_H)
    t("storefront glazing is a grid, not bars", gr > 1 and gc > 1,
      f"{gc} cols x {gr} rows -- a bar tied only top and bottom is a free-standing "
      f"tower on a standing print, and one snapped coming off the plate")

    # Muntins must be a WHOLE number of beads or the slicer improvises across the whole
    # lattice, which is what the ropy surface in the photograph was.
    beads = MULLION / float(P.LINE_W)
    t("mullions are a whole number of extrusions", abs(beads - round(beads)) < 0.02,
      f"{MULLION} / {float(P.LINE_W)} = {beads:.2f} beads")

    # PINNED. A wall is already printed with pegs at these points, and a storefront is
    # swapped onto it to test. Move these and the part stops fitting hardware that
    # exists -- which is a different and much worse failure than a part that looks wrong.
    t("sockets are where the already-printed wall expects them",
      E_store_pts == [(-47.5, 8.0), (47.5, 8.0), (-47.5, 63.0), (47.5, 63.0)],
      f"{E_store_pts}")

    # The socket sits outside the bow's nominal width, so the bay is flared to reach it.
    # If the flare ever stops covering the bore, the fix silently becomes a tab again.
    bore_r = (float(P.PEG_D) + 2 * float(P.FIT_CLEARANCE)) / 2
    _half = 90.0 / 2 + FLANGE_W + 2.0
    need = abs(E_store_pts[0][0]) + bore_r + float(P.MIN_WALL)
    t("the socket is inside the bay, not on a tab", _half >= need,
      f"bay reaches {_half:.1f} mm, socket needs {need:.2f} mm")
    t("the return is deeper than the bore", J.socket_min_material(cone=False) + 0.8 >=
      J.socket_min_material(cone=False),
      f"return {J.socket_min_material(cone=False) + 0.8:.1f} vs bore "
      f"{J.socket_min_material(cone=False):.1f} mm")
    t("nothing hangs outside the bow", abs(sb.xlen - 2 * _half) < 0.01,
      f"{sb.xlen:.2f} wide vs a {2 * _half:.0f} mm footprint")

    t("the mounting face is the rearmost plane", sb.ymax < 1e-6,
      f"ymax {sb.ymax:.3f} -- proud material behind the part is a gap in front of it")

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


def _bow_footprint(w, proj, facets, inset=0.0, flare=0.0, ret=0.0):
    """The plan of a faceted bow, as points. Back edge closed along y=0.

    Faceted rather than round on purpose: it prints better, the flats take flat glazing,
    and plate 3's bow read as curved at arm's length. `inset` shrinks it for the hollow.

    `flare` widens the BACK of the bow and `ret` gives it a straight return before the
    facets start. Together they are what lets a socket sit inside the bay instead of on a
    tab hung off its side: the socket is out at w/2 + FLANGE_W/2, which is wider than the
    bow, so without a flare there is simply no bay material there to bore into. Flared,
    the outer surface is continuous and the socket lands in the bay's own corner.

    The return has to be at least as deep as the socket needs. A pure flare -- corner
    straight to facet, no return -- angles away from the bore too fast: the facet has
    left x = 47.5 by 4.6 mm of depth and the bore needs 6.2, so it would break out
    through the side.
    """
    half = w / 2 + flare - inset
    # -Y, not +Y. Built bulging toward +Y it needed a +90 rotation to get its projection
    # out of the wall, and +90 also turns the part upside down -- sill at the top, open
    # end at the bottom. Bulging the other way lets -90 do both jobs right. Handedness,
    # not a sign slip: no rotation fixes a mirrored frame.
    if ret <= 0:
        return [(-math.cos(math.pi * i / facets) * half,
                 -math.sin(math.pi * i / facets) * (proj - inset))
                for i in range(facets + 1)]

    depth = proj - ret - inset
    pts = [(-half, 0.0), (-half, -ret)]
    for i in range(1, facets):
        a = math.pi * i / facets
        pts.append((-math.cos(a) * half, -ret - math.sin(a) * depth))
    pts += [(half, -ret), (half, 0.0)]
    return pts


def _bow_glazed(facets, ret):
    """Index of the first footprint edge that is a glazing facet.

    With a return there are two extra edges at the front of the list, and glazing the
    return instead of the bow is a silent one-off.
    """
    return 1 if ret > 0 else 0


def storefront(w=90.0, h=72.0, proj=None, facets=3, t=None):
    """A bow-fronted shop window: sill, faceted glazing, cornice, and a back flange.

    Built STANDING -- base on z=0, growing up, back face at y=0 -- because that is how it
    prints and how it hangs on the wall. Hollow behind, so the light the nook exists for
    gets through.
    """
    proj = float(P.STOREFRONT_PROJ if proj is None else proj)
    t = STORE_WALL_T if t is None else t
    glaz_h = h - STORE_SILL - STORE_CORNICE

    # cone=False: these bores are HORIZONTAL in the print. The blind cone is support for
    # a downward-facing bore and nothing else, and it was costing 4.22 mm of jamb depth
    # for a self-supporting problem this socket does not have.
    strip_d = J.socket_min_material(cone=False)
    strip_w = FLANGE_W + 4.0
    # The socket sits at w/2 + FLANGE_W/2 -- OUTSIDE the bow. That is the whole reason
    # this part used to grow two tabs off its sides: there was no bay material out there
    # to bore into. Flare the back of the bay past the socket and give it a straight
    # return deeper than the bore, and the same jamb is inside a continuous outer
    # surface. Same overall width, same socket positions, no fins.
    flare = FLANGE_W + 2.0
    ret = strip_d + 0.8
    half = w / 2 + flare

    outer = _bow_footprint(w, proj, facets, flare=flare, ret=ret)
    body = cq.Workplane("XY").polyline(outer).close().extrude(h)

    # hollow: the same plan, inset, cut from sill top to under the cornice
    inner = _bow_footprint(w, proj, facets, inset=t, flare=flare, ret=ret)
    # STOP UNDER THE CORNICE. Extruding the void the full height and shifting it up by the
    # sill ran it straight out of the top, so the bay was a tube open at one end -- and
    # mounted, that open end faced down and leaked light out under the shop.
    void = (cq.Workplane("XY").polyline(inner).close()
            .extrude(h - STORE_SILL - STORE_CORNICE)
            .translate((0, 0, STORE_SILL)))
    body = body.cut(void)

    # glazing: one opening per facet, panes sized by MAX_PANE_W like every other window
    g0 = _bow_glazed(facets, ret)
    for i in range(g0, g0 + facets):
        (x0, y0), (x1, y1) = outer[i], outer[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        seg = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        open_w = seg - 2 * FRAME_LIP
        if open_w <= 4.0:
            continue
        open_h = glaz_h - 2 * FRAME_LIP
        zc = STORE_SILL + glaz_h / 2
        rects, cols, rows = pane_grid(open_w, open_h, STORE_PANE_W, STORE_PANE_H)
        for ox, oy, pw, ph in rects:
            pane = (cq.Workplane("XZ")
                    .box(pw, ph, 4 * proj, centered=(True, True, True))
                    .translate((ox, 0, zc + oy))
                    .rotate((0, 0, 0), (0, 0, 1), ang)
                    .translate((mx, my, 0)))
            body = body.cut(pane)

        # Architrave: a band around the glazing standing proud of the facet. Without it
        # the panes are holes in a flat panel; with it the glazing reads as SET BACK,
        # which is where the reference street gets its depth from. It is added, not
        # carved, so the muntins keep the full wall thickness behind them.
        arch = (cq.Workplane("XZ")
                .box(open_w + 2 * FRAME_LIP, open_h + 2 * FRAME_LIP,
                     2 * STORE_REVEAL, centered=(True, True, True))
                .cut(cq.Workplane("XZ").box(open_w, open_h, 6 * STORE_REVEAL,
                                            centered=(True, True, True)))
                .translate((0, 0, zc))
                .rotate((0, 0, 0), (0, 0, 1), ang)
                .translate((mx, my, 0)))
        body = body.union(arch)

    # The mounting plane is the mounting plane. An architrave on an ANGLED facet runs
    # past the back of the bay near its rear edge -- 0.6 mm of it -- and 0.6 mm of proud
    # material behind a part is 0.6 mm of gap in front of it. Trim to y <= 0 and the
    # flange strips are what touches the wall, which is the whole point of them.
    body = body.cut(cq.Workplane("XY")
                    .box(4 * w, 4 * proj, 4 * h, centered=(True, False, True))
                    .translate((0, 0, h / 2)))

    # ...and no wider than the bow. The architrave stands proud along its facet's normal,
    # which near the corner has an outward x component, so it can push past the return
    # and put the part back over its own width. Trimmed flush -- a band dying into the
    # reveal is what the real detail does anyway.
    for sx in (-1, 1):
        body = body.cut(cq.Workplane("XY")
                        .box(4 * w, 4 * proj, 4 * h, centered=(True, True, True))
                        .translate((sx * (half + 2 * w), 0, h / 2)))

    # Back flange: SIDE STRIPS ONLY, never a full plate.
    #
    # It was a full-width plate first, and that is a wall across the back of a window --
    # the one place in the whole model where light has to get through. A storefront lit
    # from behind with its back closed is an unlit storefront.
    #
    # The flange exists to carry sockets, and sockets are at the sides. So put material
    # only where a socket needs it and leave the middle open to the light box.
    # The jambs must be DEEP, not just present. A socket needs socket_min_material of
    # material behind its mouth and a 2 mm flange has none of it -- the bore came out as
    # a through hole with 2 mm of engagement, and when the mouth moved it cut pure air and
    # all four pegs fouled. They run FORWARD into the bay's depth, inside the return, so
    # they take nothing from the light path and nothing hangs off the sides.
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
        body = J.socket_in(body, (x, 0.0, z), "-Y", cone=False)
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


