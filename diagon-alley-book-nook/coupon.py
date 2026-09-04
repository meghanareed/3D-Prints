#!/usr/bin/env python3
"""The one plate that decides whether this kit is worth continuing.

    python3 coupon.py     ->  out/coupon/FIT_TEST.stl  and  .3mf

Nothing over 10 g gets printed again until this plate goes together in your hand. It
answers three questions, in the order they matter:

  1. WHAT CLEARANCE FITS.  Six stations, 0.20 to 0.45 mm per side in 0.05 steps, each a
     block with a P1 socket and a peg on a handle to try in it. Whichever one presses in
     with thumb pressure and stays is the number that goes into params.FIT_CLEARANCE.
     This is the coupon that existed all along as 70A/70B and whose answer never reached
     the model: T3 and C4 were measured from a printed coupon, P1 and P2 never were.

     READ IT AS A RETENTION TEST, NOT AN ENTRY TEST.  Printed once, all six went in --
     which is the expected result and not a pass. The crush ribs are gone, so the only
     thing holding a peg in its socket now is the interference, and every station that
     accepts the peg still differs in how hard it is to pull back out. For each station:
     press in by thumb (no tool), then turn the block over. The answer is the TIGHTEST
     station that still seats without a tool and does not drop out or rock. If 0.20 does
     that, 0.20 is not automatically the number -- the printer repeats to about
     +-0.20 mm, so a clearance at that figure will be a no-go on some parts of a real
     wall. 0.25 is the floor worth shipping.

  2. WHETHER THE SHAPE WAS THE PROBLEM.  Two sockets side by side at the same clearance
     -- the old square-cornered peg and the new D-section round one. A round nozzle
     leaves internal corners radiused to about half its line width while the peg's
     corners print sharp, so the old pair binds on the diagonal before the flats meet.
     If the round one goes in and the square one does not, that is the whole story.

  3. WHETHER IT WORKS ON THE REAL PART.  A tile cut straight out of the real left wall
     around the real 13A aperture, with the real 13A frame that mounts to it. Not a
     representative test piece -- the actual geometry, so nothing can be lost in
     translation between the coupon and the kit.
"""
import os
import sys

import cadquery as cq

import params as P
import build as B
import plates as PL
import mf3
from lib import mount as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "coupon")

LADDER = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
WALL_PRINT_ROT = ("Y", -90)   # the wall face prints brick-up and flat; so does a tile of it
BLOCK_W, BLOCK_D, BLOCK_H = 18.0, 20.0, 6.0
HANDLE_W, HANDLE_D, HANDLE_H = 12.0, 16.0, 3.0
SOCKET_Y, PEG_Y = 5.0, 4.0      # feature sits in the top half
LABEL_Y = -6.0                  # label in the bottom half, clear of it


def _engrave(solid, txt, size, top_z, y):
    """Sink a label into the top face at an ABSOLUTE position.

    lib.util.emboss_text works in the selected face's own frame, which after a socket
    and its counterbore have been cut is not the frame you think it is -- the first
    version of this plate put "0.35" straight through the bore. Building the text on a
    global XY workplane at a known height and cutting it leaves nothing to guess at.
    """
    try:
        cut = (cq.Workplane("XY").workplane(offset=top_z).center(0, y)
               .text(txt, size, -0.5, font="DejaVu Sans", kind="bold", combine=False))
        return solid.cut(cut)
    except Exception:
        return solid


def _socket_block(clearance, label, square=False):
    """A block with one socket in the top half of its face and its label in the bottom."""
    blk = cq.Workplane("XY").box(BLOCK_W, BLOCK_D, BLOCK_H, centered=(True, True, False))
    z0 = BLOCK_H - M.P1_L - 0.6
    if square:
        # the mount as it was: a rectangular bore, for the A/B comparison only
        w, h = 2.5 + 2 * clearance, 2.0 + 2 * clearance
        bore = (cq.Workplane("XY").box(w, h, M.P1_L + 0.6, centered=(True, True, False))
                .translate((0, SOCKET_Y, z0)))
        blk = blk.cut(bore)
    else:
        cut, _ = M.socket_p1_solids((0, SOCKET_Y, z0), axis="+Z", decorative=False)
        blk = blk.cut(cut)
    return _engrave(blk, label, 3.6, BLOCK_H, LABEL_Y)


def _peg_handle(clearance, label, square=False):
    """A peg standing on a handle you can hold, labelled to match its block."""
    h = cq.Workplane("XY").box(HANDLE_W, HANDLE_D, HANDLE_H, centered=(True, True, False))
    if square:
        peg = (cq.Workplane("XY").box(2.5, 2.0, M.P1_L, centered=(True, True, False))
               .translate((0, PEG_Y, HANDLE_H)))
    else:
        peg = M.peg_p1((0, PEG_Y, HANDLE_H), axis="+Z")
    return _engrave(h.union(peg), label, 3.0, HANDLE_H, -4.5)


def _wall_tile():
    """A patch of the REAL left wall around the REAL 13A aperture.

    Two things the first version got wrong, both visible the moment it was sliced.

    It kept the wall's own frame, so the tile stood on its 3.1 mm edge, 48 mm tall --
    "floating regions" and an empty layer at 29.8-34.6 mm. The wall prints FLAT, brick
    up, and so must a piece of it.

    And a fixed pad cut straight through the sockets of neighbouring elements, leaving
    half-bores opening onto the edge: nothing for a peg to grip and nothing holding
    those crescents on. The box now GROWS until every cut it touches is wholly inside
    it, so the tile carries whole sockets or none.
    """
    from parts import walls as W
    import data.facade as F
    row = next(r for r in F.LEFT if r["id"] == "13A")
    parts, (cuts, _adds), _ = W.build_element(row, "L")
    frame = next(p for p in parts if p["id"] == "13A")

    b = frame["placed"].val().BoundingBox()
    y0, y1 = b.ymin - 7.0, b.ymax + 7.0
    z0, z1 = b.zmin - 7.0, b.zmax + 7.0

    # Grow the box until every cut it touches is WHOLLY inside it. Pulling the boundary
    # back instead leaves the tile in two pieces: 13A's aperture very nearly reaches the
    # wall's torn front edge, so almost nothing joins the material above it to the
    # material below except the rail on the far side, and that rail is where the
    # neighbouring sockets are. Growing costs a bigger tile and gains a second element's
    # mounts to test.
    allc = [c.val().BoundingBox() for c in W.collect("L")[1]]
    for _ in range(12):
        grew = False
        for c in allc:
            inside = (c.ymin >= y0 and c.ymax <= y1 and c.zmin >= z0 and c.zmax <= z1)
            clear = (c.ymax <= y0 or c.ymin >= y1 or c.zmax <= z0 or c.zmin >= z1)
            if inside or clear:
                continue
            y0, y1 = min(y0, c.ymin - 3.0), max(y1, c.ymax + 3.0)
            z0, z1 = min(z0, c.zmin - 3.0), max(z1, c.zmax + 3.0)
            grew = True
        if not grew:
            break
    else:
        raise SystemExit("tile box will not settle -- the sockets overlap each other")

    box = (cq.Workplane("XY").box(20.0, y1 - y0, z1 - z0, centered=(False, False, False))
           .translate((-5.0, y0, z0)))
    tile = W.wall_face("L").intersect(box)
    n = len(tile.val().Solids())
    if n != 1:
        raise SystemExit(f"tile came out in {n} pieces -- widen it")
    print(f"  tile: depth {y0:.1f}..{y1:.1f}, height {z0:.1f}..{z1:.1f} "
          f"({y1-y0:.0f} x {z1-z0:.0f} mm)")
    # ("Y", -90) is the wall face's own print orientation from build.manifest -- brick
    # up, lying flat. PRINT_ROT_MEASURED has no entry for 01, so looking it up there
    # returned None and the tile stood on its 3.1 mm edge, 112 mm tall.
    return B.drop_to_bed(B.print_orient(tile, WALL_PRINT_ROT)), frame["solid"]


def build():
    items = []
    for c in LADDER:
        items.append((f"L{int(c*100):02d}_socket", _socket_block(c, f"{c:.2f}")))
        items.append((f"L{int(c*100):02d}_peg", _peg_handle(c, f"{c:.2f}")))
    items.append(("AB_round_socket", _socket_block(0.30, "RND")))
    items.append(("AB_round_peg", _peg_handle(0.30, "RND")))
    items.append(("AB_square_socket", _socket_block(0.30, "SQR", square=True)))
    items.append(("AB_square_peg", _peg_handle(0.30, "SQR", square=True)))
    tile, frame = _wall_tile()
    items.append(("TILE_wall_13A", tile))
    items.append(("TILE_frame_13A", B.drop_to_bed(B.print_orient(frame, ("X", 180)))))
    return items


def main():
    os.makedirs(OUT, exist_ok=True)
    items = build()
    placed = []
    for name, solid in items:
        s = B.drop_to_bed(solid)
        bb = s.val().BoundingBox()
        placed.append(dict(id=name, name=name, w=bb.xlen, d=bb.ylen,
                           solid=s.translate((-bb.xmin, -bb.ymin, 0))))
    laid, left = PL.shelf_pack(placed)
    if left:
        raise SystemExit(f"{len(left)} piece(s) did not fit the bed: "
                         + ", ".join(i["id"] for i in left))

    import tempfile
    objs, stl_parts = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for it, x, y in laid:
            p = os.path.join(tmp, it["id"] + ".stl")
            cq.exporters.export(it["solid"], p)
            verts, tris = mf3.mesh_of_stl(p)
            lo_x = min(v[0] for v in verts)
            lo_y = min(v[1] for v in verts)
            objs.append(dict(name=it["id"], verts=verts, tris=tris, brim=True,
                             pos=(x - lo_x, y - lo_y, 0.0)))
            stl_parts.append(it["solid"].translate((x, y, 0)))
        from lib.util import compound
        cq.exporters.export(cq.Workplane(obj=compound(stl_parts)),
                            os.path.join(OUT, "FIT_TEST.stl"))
        mf3.write_project(os.path.join(OUT, "FIT_TEST.3mf"), "FIT_TEST", objs,
                          mf3.project_settings())

    g = sum(cq.Workplane(obj=it["solid"].val()).val().Volume() for it, _, _ in laid)
    g = g / 1000.0 * 1.24
    bb = [max(x + it["w"] for it, x, _ in laid), max(y + it["d"] for it, _, y in laid)]
    print(f"{len(laid)} pieces, {g:.0f} g, footprint {bb[0]:.0f} x {bb[1]:.0f} mm")
    print(f"  -> {OUT}/FIT_TEST.stl and .3mf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
