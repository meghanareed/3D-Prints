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
from lib.util import emboss_text

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "coupon")

LADDER = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45)
BLOCK_W, BLOCK_D, BLOCK_H = 16.0, 14.0, 6.0
HANDLE_W, HANDLE_D, HANDLE_H = 10.0, 8.0, 3.0


def _socket_block(clearance, label, square=False):
    """A block with one socket in its top face, labelled with its clearance."""
    blk = cq.Workplane("XY").box(BLOCK_W, BLOCK_D, BLOCK_H, centered=(True, True, False))
    if square:
        # the mount as it was: a rectangular bore, for the A/B comparison only
        w, h = 2.5 + 2 * clearance, 2.0 + 2 * clearance
        bore = (cq.Workplane("XY").box(w, h, M.P1_L + 0.6, centered=(True, True, False))
                .translate((0, 0, BLOCK_H - M.P1_L - 0.6)))
        blk = blk.cut(bore)
    else:
        cut, _ = M.socket_p1_solids((0, 0, BLOCK_H - M.P1_L - 0.6), axis="+Z",
                                    decorative=False)
        blk = blk.cut(cut)
    return emboss_text(blk, label, 3.4, -0.4, face=">Z", centre=(0, -4.4))


def _peg_handle(clearance, label, square=False):
    """A peg standing on a handle you can hold, labelled to match its block."""
    h = cq.Workplane("XY").box(HANDLE_W, HANDLE_D, HANDLE_H, centered=(True, True, False))
    if square:
        peg = (cq.Workplane("XY").box(2.5, 2.0, M.P1_L, centered=(True, True, False))
               .translate((0, 0, HANDLE_H)))
    else:
        peg = M.peg_p1((0, 0, HANDLE_H), axis="+Z")
    return emboss_text(h.union(peg), label, 2.6, -0.4, face=">Z", centre=(0, -2.8))


def _wall_tile():
    """A patch of the REAL left wall around the REAL 13A aperture."""
    from parts import walls as W
    import data.facade as F
    row = next(r for r in F.LEFT if r["id"] == "13A")
    parts, _, _ = W.build_element(row, "L")
    frame = next(p for p in parts if p["id"] == "13A")
    b = frame["placed"].val().BoundingBox()
    pad = 7.0
    box = (cq.Workplane("XY")
           .box(20.0, b.ylen + 2 * pad, b.zlen + 2 * pad, centered=(False, False, False))
           .translate((-5.0, b.ymin - pad, b.zmin - pad)))
    tile = W.wall_face("L").intersect(box)
    bb = tile.val().BoundingBox()
    return tile.translate((-bb.xmin, -bb.ymin, -bb.zmin)), frame["solid"]


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
