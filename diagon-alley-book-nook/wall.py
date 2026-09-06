"""The wall: a dumb plate with brick on it, big holes, and pegs.

Deliberately stupid. It carries no fine geometry at all -- no mullions, no matched
apertures, nothing that has to line up with anything on the element in front of it. That
is the whole design: **21 of 21 wall mounts fouled the facade** in the last attempt
because element geometry and mount geometry came from two tables nothing compared, and a
wall with one big hole per element cannot have that bug.

What it does carry:

    brick        cut as mortar, one boolean (texture.py)
    an opening   per element, larger than its panes and smaller than its frame
    pegs         standing UP, because the wall prints face-up and a peg on a large plate
                 does not blob -- which plate 1 proved rather than assumed

Peg positions come from `elements.flange_points()`, the same call the element uses for its
sockets. Not a copy of it, not a table beside it. The one structural guarantee that a peg
and its socket cannot drift apart is that there is only one place they are computed.

    python wall.py           build a tile, mate a window to it, self-test
    python wall.py --export  write out/wall_tile.stl and out/wall_tile_window.stl
"""
import os
import sys

import cadquery as cq

import elements as E
import joints as J
import params as P
import texture as T

HERE = os.path.dirname(os.path.abspath(__file__))


def tile(w=62.0, h=52.0, t=None, elements=(), brick=True, seed=None):
    """A patch of wall face.

    `elements` is [(kind, ew, eh, cx, cy)] -- what sits on it and where. The wall asks the
    element module for the hole it needs and for where its sockets are; it does not decide
    either.
    """
    t = float(P.WALL_FACE_T if t is None else t)
    body = cq.Workplane("XY").box(w, h, t, centered=(False, False, False))

    if brick:
        body, _stats = T.brick_face(body, w, h, at=(0, 0, t), seed=seed)

    for kind, ew, eh, cx, cy in elements:
        if kind == "window_fused":
            # Rule 9 applied rather than asserted: same orientation, same filament, and
            # its cavity is a hole -- so it does not earn being a part. Frame and mullions
            # become relief on the wall face; the panes are cut straight through.
            add, cut = E.window_relief(ew, eh)
            body = body.cut(cut.translate((cx, cy, t / 2)))
            body = body.union(add.translate((cx, cy, t)))
        else:
            body = body.cut(E.wall_opening(ew, eh).translate((cx, cy, t / 2)))
            for px, py in E.flange_points(ew, eh):
                body = body.union(J.peg().translate((cx + px, cy + py, t)))
    return body


def mate(element_solid, ew, eh, cx, cy, t=None):
    """Put an element onto the wall the way it actually goes on.

    NO FLIP. I wrote one in first -- "its face was built +Z so it must turn over" -- and
    it fouled by 3.9 mm3, because the reasoning was wrong: the element is already built
    with its VISIBLE face up and its socket mouths opening at its z=0 underside. The wall
    face also points up and its pegs stand out of it. The two already agree; turning the
    element over puts its sockets on the sky.

    Third time in this project that a rotation was reasoned about instead of checked.
    The element just drops straight down.
    """
    t = float(P.WALL_FACE_T if t is None else t)
    bb = element_solid.val().BoundingBox()
    return element_solid.translate((cx, cy, t - bb.zmin))


# ==================================================================== self-test ==
def self_test():
    out = []

    def t_(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    ew, eh = 22.0, 30.0
    cx, cy = 31.0, 26.0
    t = float(P.WALL_FACE_T)
    plate = tile(elements=[("window", ew, eh, cx, cy)])

    t_("tile is one solid", len(plate.solids().vals()) == 1,
       f"{len(plate.solids().vals())} solids")

    # The opening must go right through, or there is no light and no point.
    probe = cq.Workplane("XY").box(ew - 2, eh - 2, 40).translate((cx, cy, t / 2))
    t_("the opening goes right through", not plate.intersect(probe).solids().vals(),
       "nothing left in the aperture")

    # Pegs and sockets from ONE source. This is the check that the last attempt's
    # 21-of-21 failure could not have had, because there were two sources.
    win = E.window(ew, eh)
    placed = mate(win, ew, eh, cx, cy)
    foul = plate.intersect(placed)
    vol = foul.val().Volume() if foul.solids().vals() else 0.0
    t_("the element drops onto the wall", vol < 1e-6, f"interference {vol:.4f} mm3")

    # And it must actually SEAT -- the flange has to reach the wall face, not hover on
    # peg tips. A part standing proud is what "the pieces are too big for the wall" meant.
    pb = placed.val().BoundingBox()
    t_("the element seats on the wall face", abs(pb.zmin - t) < 1e-6,
       f"flange at z={pb.zmin:.3f}, wall face at {t:.3f}")

    # Brick must not intrude where the element sits, or it rocks. Attempt two put brick
    # relief under every flange and every part rocked on it.
    flange_zone = (cq.Workplane("XY")
                   .box(pb.xlen, pb.ylen, 4.0, centered=(True, True, False))
                   .translate((cx, cy, t - 2.0)))
    proud = plate.intersect(flange_zone.translate((0, 0, 2.0)))
    proud_v = proud.val().Volume() if proud.solids().vals() else 0.0
    pegs_v = 4 * (float(P.PEG_L) * 3.14159 * (float(P.PEG_D) / 2) ** 2)
    t_("nothing but pegs stands proud under the element",
       proud_v < pegs_v * 1.35,
       f"{proud_v:.0f} mm3 above the face, pegs alone are ~{pegs_v:.0f}")

    # The flip that is NOT needed must still be wrong, or mate() is doing nothing and a
    # future edit could quietly put one back.
    upside_down = win.rotate((0, 0, 0), (1, 0, 0), 180)
    ub = upside_down.val().BoundingBox()
    bad_place = upside_down.translate((cx, cy, t - ub.zmin))
    bv = plate.intersect(bad_place)
    t_("turning the element over WOULD foul",
       (bv.val().Volume() if bv.solids().vals() else 0.0) > 0.5,
       "so the absence of a flip in mate() is load-bearing")
    return out, plate, placed


if __name__ == "__main__":
    print("wall -- a dumb plate with brick, holes and pegs\n")
    res, plate, placed = self_test()
    bad = 0
    for ok, name, detail in res:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    bb = plate.val().BoundingBox()
    print(f"\n  tile {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.1f} mm, "
          f"{plate.val().Volume() * 1.24e-3:.1f} g")

    if "--export" in sys.argv:
        d = os.path.join(HERE, "out")
        os.makedirs(d, exist_ok=True)
        cq.exporters.export(plate.val(), os.path.join(d, "wall_tile.stl"))
        cq.exporters.export(E.window().val(), os.path.join(d, "wall_tile_window.stl"))
        print(f"  wrote wall_tile.stl and wall_tile_window.stl to {d}")

    print(f"\n  {bad} failures")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
