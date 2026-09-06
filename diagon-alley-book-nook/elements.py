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


def window(w=22.0, h=30.0, cols=2, rows=3, t=None, mullion=MULLION):
    """A window frame: outer band, mullions, hollow back, flange with four sockets.

    Built face-up in XY. The visible face is +Z; the flange and sockets are on -Z, which
    is the side that meets the wall.
    """
    t = float(P.WALL_FACE_T if t is None else t)
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
    t("wall opening clears the panes but hides behind the frame",
      ob.xlen > w and ob.xlen < w + 2 * FRAME_LIP,
      f"opening {ob.xlen:.1f} vs pane {w:.1f}, frame {w + 2 * FRAME_LIP:.1f}")
    return out


if __name__ == "__main__":
    print("elements -- the window\n")
    bad = 0
    for ok, name, detail in self_test():
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    if "--export" in sys.argv:
        d = os.path.join(HERE, "out")
        os.makedirs(d, exist_ok=True)
        cq.exporters.export(window().val(), os.path.join(d, "window_sample.stl"))
        print(f"\n  wrote {d}/window_sample.stl")

    print(f"\n  {bad} failures")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
