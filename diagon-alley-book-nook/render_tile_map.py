#!/usr/bin/env python3
"""Name every hole in the coupon tile.

    python3 render_tile_map.py   ->  docs/img/coupon_tile_map.png

The tile is a patch cut out of the real left wall, so it carries the mounts of
everything that lives near 13A, not just 13A's own. Without labels there is no way to
tell which hole belongs to the part in your hand, which belongs to a neighbour that
was never printed, and which is fouled by the frame lying on top of it.

The first version of this drawing left the sign and bracket sockets out entirely, and
the one hole it could not name turned out to be the bug: bracket 31A's socket, sitting
under the 13A frame.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import cadquery as cq

import build as B
from parts import walls as W
from parts import kit as K
from parts.decor import to_wall, FACE
from lib.mount import socket_p1_solids
import data.facade as F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "img")
ROT = ("Y", -90)


def tile_box():
    """The same box coupon.py grows around 13A."""
    row = next(r for r in F.LEFT if r["id"] == "13A")
    parts, _cuts, _ = W.build_element(row, "L")
    frame = next(p for p in parts if p["id"] == "13A")
    b = frame["placed"].val().BoundingBox()
    y0, y1 = b.ymin - 7.0, b.ymax + 7.0
    z0, z1 = b.zmin - 7.0, b.zmax + 7.0
    bbs = [c.val().BoundingBox() for c in W.collect("L")[1]]
    for _ in range(12):
        grew = False
        for c in bbs:
            if (c.ymin >= y0 and c.ymax <= y1 and c.zmin >= z0 and c.zmax <= z1):
                continue
            if (c.ymax <= y0 or c.ymin >= y1 or c.zmax <= z0 or c.zmin >= z1):
                continue
            y0, y1 = min(y0, c.ymin - 3.0), max(y1, c.ymax + 3.0)
            z0, z1 = min(z0, c.zmin - 3.0), max(z1, c.zmax + 3.0)
            grew = True
        if not grew:
            break
    return frame, (y0, y1, z0, z1)


def section(solid, z):
    slab = (cq.Workplane("XY").box(400, 400, 0.2, centered=(True, True, False))
            .translate((0, 0, z)))
    cut = slab.intersect(solid)
    if not cut.val().Solids():
        return []
    v, t = cut.val().tessellate(0.06)
    tris = np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]
    return tris[tris[:, :, 2].max(axis=1) <= z + 0.05][:, :, :2]


def main():
    os.makedirs(OUT, exist_ok=True)
    frame, (y0, y1, z0, z1) = tile_box()
    box = (cq.Workplane("XY").box(20.0, y1 - y0, z1 - z0, centered=(False, False, False))
           .translate((-5.0, y0, z0)))
    tile_wall = W.wall_face("L").intersect(box)

    tile = B.print_orient(tile_wall, ROT)
    dz = -tile.val().BoundingBox().zmin
    tile = tile.translate((0, 0, dz))

    def to_bed(s):
        return B.print_orient(s, ROT).translate((0, 0, dz))

    def inside(bb):
        return not (bb.ymax <= y0 or bb.ymin >= y1 or bb.zmax <= z0 or bb.zmin >= z1)

    holes = []
    for r in F.LEFT:
        try:
            _p, (cs, _a), _b = W.build_element(r, "L")
        except Exception:
            continue
        for c in cs:
            bb = c.val().BoundingBox()
            if bb.xlen > 5.0 or not inside(bb):     # skip the apertures themselves
                continue
            holes.append((r["id"], to_bed(c).val().BoundingBox()))
    for kind, row, rot in K.wall_mount_rows("L"):
        c, _a = socket_p1_solids((0.0, 0.0, 0.0), axis="-Z", rot=rot, depth=FACE)
        c = to_wall(c, row["u"], row.get("z", 20.0))
        if inside(c.val().BoundingBox()):
            holes.append((row["id"], to_bed(c).val().BoundingBox()))

    fbb = to_bed(frame["placed"]).val().BoundingBox()
    tb = tile.val().BoundingBox()
    fig, ax = plt.subplots(figsize=(16, 8.5), facecolor="white")
    for poly in section(tile, 0.3):
        ax.add_patch(Polygon(poly, closed=True, facecolor="#c9ced3",
                             edgecolor="none", zorder=1))
    for poly in section(tile, tb.zmax - 0.4):
        ax.add_patch(Polygon(poly, closed=True, facecolor="#8d979f",
                             edgecolor="none", zorder=2))

    for pid, bb in holes:
        under = not (bb.xmax <= fbb.xmin or bb.xmin >= fbb.xmax
                     or bb.ymax <= fbb.ymin or bb.ymin >= fbb.ymax)
        col = "#b23b3b" if pid == "13A" else ("#c8791b" if under else "#2f5d8a")
        ax.add_patch(Rectangle((bb.xmin, bb.ymin), bb.xlen, bb.ylen, fill=False,
                               edgecolor=col, lw=1.6, zorder=4))
        ax.text((bb.xmin + bb.xmax) / 2, bb.ymax + 0.7, pid, ha="center", va="bottom",
                fontsize=8, color=col, fontweight="bold", zorder=5)

    ax.add_patch(Rectangle((fbb.xmin, fbb.ymin), fbb.xlen, fbb.ylen, fill=False,
                           edgecolor="#b23b3b", lw=2.0, ls="--", zorder=6))
    ax.text(fbb.xmin + fbb.xlen / 2, fbb.ymin - 1.4, "13A frame covers this",
            ha="center", va="top", fontsize=9, color="#b23b3b",
            fontweight="bold", zorder=6)

    ax.plot([tb.xmin, tb.xmin + 20], [tb.ymin - 6, tb.ymin - 6], color="#222", lw=2)
    ax.text(tb.xmin + 10, tb.ymin - 7.4, "20 mm", ha="center", va="top", fontsize=8)
    ax.set_xlim(tb.xmin - 4, tb.xmax + 4)
    ax.set_ylim(tb.ymin - 12, tb.ymax + 6)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("Coupon tile as it lies on the bed — red: 13A's own mounts, "
                 "orange: a mount the frame covers, blue: another part's",
                 fontsize=12, color="#222")
    fig.tight_layout()
    out = os.path.join(OUT, "coupon_tile_map.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print("  ->", out)


if __name__ == "__main__":
    main()
