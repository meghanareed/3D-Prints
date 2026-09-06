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
        elif kind == "storefront":
            # One big opening behind the whole shop, and four pegs where the storefront's
            # sockets ACTUALLY land -- via the same transform that places the part, not a
            # hand-written copy of it. Writing the mapping out by hand put them on the
            # wrong side and one millimetre off, which is the whole 21-of-21 failure in
            # miniature: two expressions of one relationship, and only one of them right.
            body = body.cut(cq.Workplane("XY")
                            .box(ew - 8.0, eh - 14.0, 40.0, centered=(True, True, True))
                            .translate((cx, cy, t / 2)))
            for wx, wy in storefront_peg_xy(ew, eh, cx, cy, t):
                body = body.union(J.peg().translate((wx, wy, t)))
        else:
            body = body.cut(E.wall_opening(ew, eh).translate((cx, cy, t / 2)))
            for px, py in E.flange_points(ew, eh):
                body = body.union(J.peg().translate((cx + px, cy + py, t)))
    return body


def _store_transform(ew, eh, cx, cy, t):
    """The one place the standing->flat mapping is written down.

    Returns (rotate_fn, dx, dy, dz). Everything that needs to know where a storefront
    feature ends up on the wall goes through this: the part itself, and the pegs.
    """
    t = float(P.WALL_FACE_T if t is None else t)
    probe = E.storefront(ew, eh).rotate((0, 0, 0), (1, 0, 0), -90)
    bb = probe.val().BoundingBox()
    return (lambda s: s.rotate((0, 0, 0), (1, 0, 0), -90),
            cx, cy - eh / 2 - bb.ymin, t - bb.zmin)


def storefront_peg_xy(ew, eh, cx, cy, t=None):
    """Where a storefront's sockets land on the flat wall. Derived, never retyped."""
    _rot, dx, dy, _dz = _store_transform(ew, eh, cx, cy, t)
    # -90 about X sends a point (x, y, z) to (x, z, -y); the sockets sit at y=flange.
    return [(px + dx, pz + dy) for px, pz in E.store_points(ew, eh)]


def mate_storefront(store, ew, eh, cx, cy, t=None):
    """Lay a standing storefront against a flat wall.

    The storefront is built STANDING -- x across, y projecting out of the wall, z up it --
    and the wall is built FLAT with its face on +Z. So the two frames disagree and a
    rotation is genuinely required here, unlike the flat window in mate().

    -90 about X, and the storefront is BUILT to suit it -- bulging toward -Y so that one
    rotation gets the projection out of the wall AND leaves the part upright. Built the
    other way it needed +90, which does get the projection out but turns the shop upside
    down: sill at the top, open end at the bottom, light leaking out underneath. That is
    handedness, and no choice of rotation fixes a mirrored frame -- the fix was in how the
    footprint is drawn.
    """
    rot, dx, dy, dz = _store_transform(ew, eh, cx, cy, t)
    return rot(store).translate((dx, dy, dz))


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


# The first real wall module. Storeys, not a scatter of holes: a wall reads as a
# building because its openings line up in courses and shrink as they go up, and that is
# cheaper to get right in a table than by eye.
PANEL_WINDOWS = [
    # (w, h, cx, cy)  -- ground floor
    (36.0, 50.0, 38.0, 30.0),
    (36.0, 50.0, 103.0, 30.0),
    # first floor
    (36.0, 46.0, 38.0, 100.0),
    (36.0, 46.0, 103.0, 100.0),
    # attic, smaller and set in
    (28.0, 34.0, 70.5, 165.0),
]


def panel(w=None, h=None, windows=None, seed=None):
    """A real wall module: brick over the whole face, windows FUSED into it.

    No mounted parts on a flat wall any more -- plate 3 printed a fused window beside a
    mounted one and they look the same at arm's length, so the fused one wins and takes a
    part, a joint, a flange and four sockets with it. What arrives here as `window_fused`
    used to be four separate objects.
    """
    w = float(P.WALL_MODULE_L if w is None else w)
    h = float(P.WALL_MODULE_H if h is None else h)
    wins = PANEL_WINDOWS if windows is None else windows
    return tile(w, h, elements=[("window_fused", ew, eh, cx, cy)
                                for ew, eh, cx, cy in wins], seed=seed)


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

    # The real module, at the size that ships.
    pan = panel()
    pb = pan.val().BoundingBox()
    t_("panel is one solid", len(pan.solids().vals()) == 1,
       f"{len(pan.solids().vals())} solids")
    bed = min(float(P.BED_X), float(P.BED_Y))
    t_("panel fits the bed with its brim",
       max(pb.xlen, pb.ylen) + 2 * float(P.BRIM_WIDTH) <= bed,
       f"{max(pb.xlen, pb.ylen) + 2 * float(P.BRIM_WIDTH):.0f} on {bed:.0f}")
    # Probe inside ONE PANE, not the window centre -- the centre of a fused window is a
    # mullion, so a probe the width of the opening correctly finds material and tells you
    # nothing. And distinct loop names: reusing ew/eh/cx/cy here shadowed the outer ones
    # and sent the flip test's window to the attic window's coordinates, off the tile.
    holes = 0
    for pwid, phgt, pcx, pcy in PANEL_WINDOWS:
        pc, pr_ = E.panes_for(pwid, phgt)
        pane_w = (pwid - (pc - 1) * E.MULLION) / pc
        pane_h = (phgt - (pr_ - 1) * E.MULLION) / pr_
        probe = (cq.Workplane("XY")
                 .box(pane_w * 0.6, pane_h * 0.6, 40).translate((pcx, pcy, t / 2)))
        if not pan.intersect(probe).solids().vals():
            holes += 1
    t_("light gets through every window", holes == len(PANEL_WINDOWS),
       f"{holes} of {len(PANEL_WINDOWS)} panes clear")

    # A STOREFRONT must mate too, and this is the check that catches a mirrored D-flat --
    # which has now gone both ways in this file depending on build handedness. No rule is
    # remembered; the assembly is performed and measured.
    sew, seh, scx, scy = 90.0, 72.0, 70.5, 45.0
    spanel = tile(float(P.WALL_MODULE_L), float(P.WALL_MODULE_H),
                  elements=[("storefront", sew, seh, scx, scy)], brick=False)
    shop = E.storefront(sew, seh)
    splaced = mate_storefront(shop, sew, seh, scx, scy)
    sf_foul = spanel.intersect(splaced)
    sv = sf_foul.val().Volume() if sf_foul.solids().vals() else 0.0
    t_("the storefront mounts on its pegs", sv < 1e-6, f"interference {sv:.4f} mm3")

    sb = splaced.val().BoundingBox()
    t_("the storefront projects OUT of the wall, not into it", sb.zmax > t + 20,
       f"reaches {sb.zmax - t:.1f} mm proud")

    # Upright, not upside down. Built bulging +Y it came out inverted -- sill at the top,
    # open end at the bottom, light leaking out under the shop.
    #
    # Comparing the volume of each end cap does NOT test this: a 4 mm sill and a 5 mm
    # cornice weigh almost the same and the check read 6685 against 6685. Transform a
    # point KNOWN to be in the sill and ask where it lands instead. Same discipline as
    # flat_side() -- measure where a feature goes, do not infer it from the rotation.
    rot, dx, dy, dz = _store_transform(sew, seh, scx, scy, t)
    sill_pt = cq.Workplane("XY").box(1, 1, 1).translate((0, -1.0, E.STORE_SILL / 2))
    landed = rot(sill_pt).translate((dx, dy, dz)).val().Center()
    t_("the shop is the right way up",
       landed.y < (sb.ymin + sb.ymax) / 2,
       f"a point inside the sill lands at y={landed.y:.1f}, "
       f"below the mid-height {(sb.ymin + sb.ymax) / 2:.1f}")

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
        d = P.out_dir("stl")
        cq.exporters.export(plate.val(), os.path.join(d, "wall_tile.stl"))
        cq.exporters.export(E.window().val(), os.path.join(d, "wall_tile_window.stl"))
        print(f"  wrote wall_tile.stl and wall_tile_window.stl to {d}")

    print(f"\n  {bad} failures")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
