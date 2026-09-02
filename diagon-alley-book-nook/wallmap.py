#!/usr/bin/env python3
"""Draw both wall faces with every aperture labelled -- which wall is this, and what
goes in which hole.

    python3 wallmap.py        ->  docs/img/wall_apertures.png

The two walls are the same size and the same colour and both are a field of brick with
a dozen holes in it, and once a plate is off the bed there is nothing on it that says
LEFT or RIGHT. This is the picture that tells you: the aperture pattern is completely
different between the two, and every facade part is named for the wall it belongs to.

Drawn from the BRICK side -- the side the facade parts mount on, and the side that
faces up when the plate comes off the printer -- so it can be held against the print.
The front opening is on the right, where the torn edge is.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import os

import numpy as np
import cadquery as cq
import parts.walls as W

TRIAL = {"13A", "11A", "12G", "19C", "15A"}
FIG, AX = plt.subplots(1, 2, figsize=(16, 9))

for ax, side, title in zip(AX, ("L", "R"),
                           ("LEFT wall   01_L_Wall_Face   105 g",
                            "RIGHT wall   02_R_Wall_Face   108 g")):
    s = W.wall_face(side)
    bb = s.val().BoundingBox()
    slab = (cq.Workplane("XY")
            .box(1.0, bb.ylen + 8, bb.zlen + 8, centered=(False, False, False))
            .translate((1.0, bb.ymin - 4, bb.zmin - 4)))
    verts, tris = s.intersect(slab).val().tessellate(0.05)
    # seen from the brick side: the depth axis runs the other way
    v = np.array([[-p.y, p.z] for p in verts])
    ax.add_collection(PolyCollection(v[np.array(tris)],
                                     facecolors="#9aa3ab", edgecolors="none"))

    n = 0
    for row in W._rows(side):
        _p, (c, _a), _b = W.build_element(row, side)
        thru = [x.val().BoundingBox() for x in c]
        thru = [b for b in thru if b.xmin < 2.1 and b.ylen > 4 and b.zlen > 4]
        if not thru:
            continue
        n += 1
        b = max(thru, key=lambda b: b.ylen * b.zlen)
        hot = row["id"] in TRIAL
        ax.add_patch(plt.Rectangle((-b.ymax, b.zmin), b.ylen, b.zlen, fill=False,
                                   ec="#c1121f" if hot else "#33404d",
                                   lw=2.4 if hot else 1.0,
                                   zorder=3 if hot else 2))
        ax.text(-b.ymax + b.ylen / 2, b.zmin + b.zlen / 2,
                f"{row['id']}\n{b.ylen:.0f}x{b.zlen:.0f}" if hot else row["id"],
                ha="center", va="center", fontsize=8.5 if hot else 7.5,
                color="#c1121f" if hot else "#33404d",
                weight="bold" if hot else "normal", zorder=4)

    ax.set_xlim(-bb.ymax - 6, -bb.ymin + 6)
    ax.set_ylim(bb.zmin - 6, bb.zmax + 6)
    ax.set_aspect("equal")
    ax.set_title(f"{title}\n{n} apertures   -   torn front edge on the RIGHT", fontsize=11)
    ax.set_xlabel("<- back of the nook            front opening ->")
    ax.set_ylabel("height above the alley floor  (mm)")
    ax.grid(alpha=.15)

FIG.suptitle("Which wall did you print?   The trial-plate parts (red) are all LEFT-wall parts",
             fontsize=13)
plt.tight_layout()
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "docs", "img", "wall_apertures.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out, dpi=130)
print("wrote", out)
