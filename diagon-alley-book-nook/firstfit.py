#!/usr/bin/env python3
"""The first plate of the redesigned kit.

    python3 firstfit.py    ->  out/coupon/FIRST_FIT.stl  and  .3mf

The joint question is settled: P1 and P2 locate, glue retains, 0.30 per side. What has
never been printed is everything that changed on the way to settling it. This plate is
small enough to be cheap and carries one of each:

  THE PIN JOINT.  A sign no longer has a peg on its back -- it has a socket, and a loose
  pin joins it to the wall or to the board it sits on. Nothing about that has been in a
  printer. The pins come on a sprue, lying down, which is also the answer to the blobbed
  vertical pegs.

  LETTERING THAT PRINTS FACE UP.  Signs used to print face down with every raised letter
  crushed into the bed. They lie back-down now. Whether "APOTHECARY" at 3.6 mm actually
  reads on a 0.4 mm nozzle is a question only the printer can answer.

  REAL GEOMETRY, BOTH WAYS ROUND.  A 16 mm tile of the real left wall carrying 30D's
  own socket, so a pin can be tried in the wall itself; and the real fascia board with
  the real name plate that pins onto it, which is the other place a pin has to work.
  Every one of them is the part the kit will ship, at the clearance it will ship.

  THE HANGING SIGN, TURNED TO FACE THE OPENING.  30H is now its bracket: plate and arm
  fused, coplanar, projecting into the alley so the viewer sees its face instead of its
  edge. It carries the smallest lettering in the kit at 3.8 mm and mounts on two pins,
  because a sign on the end of an arm is a cantilever and one pin is a hinge.

EVERY PIECE HERE MATES WITH ANOTHER PIECE HERE. If one does not, it should not be on
the plate. Print it, dry-fit every joint, and glue nothing until they all go together.
"""
import os
import sys
import tempfile

import cadquery as cq

import build as B
import plates as PL
import mf3
from parts import walls as W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "coupon")

# 30D's own socket, beside the L2 door. Chosen for being CHEAP: the tile grows until
# every cut it touches is wholly inside it, and around the fascia at (86, 54) that
# swallows the door and the oriel and comes out 92 x 75 mm and 15 g. Here nothing else
# is within reach and it settles at 16 x 16.
TILE_AROUND = (98.0, 27.0)     # 30D's socket, in wall-local (u, z)
TILE2_AROUND = (143.0, 80.5)   # 30H's pair, over the L3 shopfront
TILE_PAD = 8.0
WALL_PRINT_ROT = ("Y", -90)    # the wall face prints brick-up and flat; so does a tile
# 30H carries the smallest lettering in the kit and is its own bracket, so the tile has
# to be the one with ITS sockets in it -- two of them, at the bracket's peg spacing.
PIECES = ["30D", "11K", "30J", "30H", "32D"]


def wall_tile(side="L", around=TILE_AROUND, pad=TILE_PAD):
    """A patch of the REAL wall, grown until every cut it touches is wholly inside.

    A fixed pad slices through the sockets of whatever is next door and leaves half
    bores opening onto the edge: nothing for a pin to grip and nothing holding those
    crescents on. Growing costs a bigger tile and gains a neighbour's mounts to look at.
    """
    u, z = around
    y0, y1 = u - pad, u + pad
    z0, z1 = z - pad, z + pad
    boxes = [c.val().BoundingBox() for c in W.collect(side)[1]]
    for _ in range(12):
        grew = False
        for c in boxes:
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
    tile = W.wall_face(side).intersect(box)
    n = len(tile.val().Solids())
    if n != 1:
        raise SystemExit(f"tile came out in {n} pieces -- widen it")
    print(f"  tile: depth {y0:.1f}..{y1:.1f}, height {z0:.1f}..{z1:.1f} "
          f"({y1 - y0:.0f} x {z1 - z0:.0f} mm)")
    return B.drop_to_bed(B.print_orient(tile, WALL_PRINT_ROT))


def build():
    rows = {m["id"]: m for m in B.manifest()}
    items = [("TILE_wall_30D", wall_tile()),
             ("TILE_wall_30H", wall_tile(around=TILE2_AROUND))]
    for pid in PIECES:
        m = rows[pid]
        items.append((f"{pid}_{m['name']}",
                      B.drop_to_bed(B.print_orient(m["fn"](), m["print_rot"]))))
    return items


def main():
    os.makedirs(OUT, exist_ok=True)
    placed = []
    for name, solid in build():
        s = B.drop_to_bed(solid)
        bb = s.val().BoundingBox()
        placed.append(dict(id=name, name=name, w=bb.xlen, d=bb.ylen,
                           solid=s.translate((-bb.xmin, -bb.ymin, 0))))
    laid, left = PL.shelf_pack(placed)
    if left:
        raise SystemExit(f"{len(left)} piece(s) did not fit the bed: "
                         + ", ".join(i["id"] for i in left))

    objs, stl_parts = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for it, x, y in laid:
            p = os.path.join(tmp, it["id"] + ".stl")
            cq.exporters.export(it["solid"], p)
            verts, tris = mf3.mesh_of_stl(p)
            objs.append(dict(name=it["id"], verts=verts, tris=tris, brim=True,
                             pos=(x - min(v[0] for v in verts),
                                  y - min(v[1] for v in verts), 0.0)))
            stl_parts.append(it["solid"].translate((x, y, 0)))
        from lib.util import compound
        cq.exporters.export(cq.Workplane(obj=compound(stl_parts)),
                            os.path.join(OUT, "FIRST_FIT.stl"))
        mf3.write_project(os.path.join(OUT, "FIRST_FIT.3mf"), "FIRST_FIT", objs,
                          mf3.project_settings())

    g = sum(it["solid"].val().Volume() for it, _, _ in laid) / 1000.0 * 1.24
    bb = [max(x + it["w"] for it, x, _ in laid), max(y + it["d"] for it, _, y in laid)]
    print(f"{len(laid)} pieces, {g:.0f} g, footprint {bb[0]:.0f} x {bb[1]:.0f} mm")
    print(f"  -> {OUT}/FIRST_FIT.stl and .3mf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
