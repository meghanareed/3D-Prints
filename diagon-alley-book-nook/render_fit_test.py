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
from matplotlib.patches import Polygon

import build as B
import plates as PL
import coupon as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "img")

BED = (0.0, 0.6)        # first layers: the footprint
TOP = (0.8, 0.2)        # zmax minus this band: the top face


def _slab(tris, lo, hi):
    """Triangles whose whole span lies between lo and hi, as XY polygons."""
    z = tris[:, :, 2]
    keep = (z.min(axis=1) >= lo) & (z.max(axis=1) <= hi)
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
        v, t = it["solid"].val().tessellate(0.10)
        tris = np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]
        zmax = tris[:, :, 2].max()
        for band, colour, zo in ((( BED[0], BED[1]), "#c9ced3", 1),
                                 ((zmax - TOP[0], zmax - TOP[1]), "#5b6670", 2)):
            for poly in _slab(tris, *band):
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
    ax.set_title("FIT_TEST plate, true scale — light grey touches the bed, "
                 "dark grey is the top face", fontsize=11, color="#222")
    fig.tight_layout()
    out = os.path.join(OUT, "coupon_pieces.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print("  ->", out)


if __name__ == "__main__":
    main()
