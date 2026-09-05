#!/usr/bin/env python3
"""Draw the FIT_TEST plate at true scale, with every piece named.

    python3 render_fit_test.py   ->  docs/img/coupon_pieces.png

The plate comes off the printer as eighteen loose pieces and nothing on them says what
they are for except a 3 mm engraved label. This draws the plate exactly as it is packed
-- same shelf_pack, same positions -- so a piece in your hand can be found by its
outline and its neighbours, and gives every piece its size in millimetres.

Light grey is what touches the bed. Dark grey is the top face, so a socket bore reads as
a light hole in a dark block and a peg reads as a dark island on a light handle.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cadquery as cq
from matplotlib.patches import Polygon

import build as B
import plates as PL
import coupon as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "img")

BED = 0.3        # section height for the footprint
FEATURE = 1.0    # section this far below the top: pegs on a handle, bore in a block


def _section(solid, z):
    """Triangles of a real horizontal slice, as XY polygons.

    Filtering the mesh for triangles that happen to lie in a band does not work: the
    side wall of a 2.4 mm peg is two triangles spanning its whole height, so a peg
    drawn that way is invisible. Cutting an actual slab and tessellating that shows
    what is really there at that height.
    """
    slab = (cq.Workplane("XY").box(400, 400, 0.2, centered=(True, True, False))
            .translate((0, 0, z)))
    cut = slab.intersect(solid)
    if not cut.val().Solids():
        return []
    v, t = cut.val().tessellate(0.08)
    tris = np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]
    keep = tris[:, :, 2].max(axis=1) <= z + 0.05
    return tris[keep][:, :, :2]


def main():
    os.makedirs(OUT, exist_ok=True)
    items = C.build()
    placed = []
    for name, solid in items:
        s = B.drop_to_bed(solid)
        bb = s.val().BoundingBox()
        placed.append(dict(id=name, name=name, w=bb.xlen, d=bb.ylen,
                           solid=s.translate((-bb.xmin, -bb.ymin, 0))))
    laid, left = PL.shelf_pack(placed)
    if left:
        raise SystemExit("packing changed -- rerun coupon.py")

    fig, ax = plt.subplots(figsize=(15, 8.5), facecolor="white")
    for it, x, y in laid:
        zmax = it["solid"].val().BoundingBox().zmax
        for z, colour, zo in ((BED, "#c9ced3", 1), (zmax - FEATURE, "#5b6670", 2)):
            for poly in _section(it["solid"], z):
                ax.add_patch(Polygon(poly + (x, y), closed=True, facecolor=colour,
                                     edgecolor="none", zorder=zo))
        ax.text(x + it["w"] / 2, y + it["d"] + 2.5,
                f"{it['id']}\n{it['w']:.0f} x {it['d']:.0f} mm", ha="center",
                va="bottom", fontsize=7.5, color="#222", zorder=3)

    w = max(x + it["w"] for it, x, _ in laid)
    d = max(y + it["d"] for it, _, y in laid)
    ax.plot([0, 50], [-6, -6], color="#222", lw=2)
    ax.text(25, -8.5, "50 mm", ha="center", va="top", fontsize=8, color="#222")
    ax.set_xlim(-8, w + 8)
    ax.set_ylim(-14, d + 16)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("FIT_TEST plate, true scale — light grey is the footprint on the bed, "
                 "dark grey is a slice 1 mm below the top", fontsize=11, color="#222")
    fig.tight_layout()
    out = os.path.join(OUT, "coupon_pieces.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print("  ->", out)


if __name__ == "__main__":
    main()
