#!/usr/bin/env python3
"""Where does each part go on the wall?

    python3 wallmap.py        ->  docs/img/wall_placement_L.png
                                  docs/img/wall_placement_R.png
                                  docs/06_WHERE_IT_GOES.md

Every facade part drawn in its place on the wall it belongs to, over the wall's own
silhouette, plus a table of the same thing in numbers. This exists because a printed
part in your hand has nothing on it that says where it goes: half of them mount over an
aperture, half peg onto flat brick with nothing to line them up against, and the two
walls are the same size and colour with completely different aperture patterns.

Drawn from the BRICK side -- the side the parts mount on, and the side facing up as the
plate comes off the printer -- so the picture can be held against the print. The front
opening is on the right, where the torn edge is.

Coordinates in the table are the ones the drawing uses: depth back from the front
opening, and height above the alley floor.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
import cadquery as cq

import parts.walls as W

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "docs", "img")
DOC = os.path.join(HERE, "docs", "06_WHERE_IT_GOES.md")

# The parts on the trial plate, drawn hot so they can be found at a glance.
TRIAL = {"13A", "13Ag", "13As", "19C", "11A", "11Ag", "11Ar", "11Ac", "12G", "15A", "30H"}


def silhouette(ax, side):
    """Fill the wall's own cross-section, so apertures read as holes."""
    s = W.wall_face(side)
    bb = s.val().BoundingBox()
    slab = (cq.Workplane("XY")
            .box(1.0, bb.ylen + 8, bb.zlen + 8, centered=(False, False, False))
            .translate((1.0, bb.ymin - 4, bb.zmin - 4)))
    verts, tris = s.intersect(slab).val().tessellate(0.05)
    v = np.array([[-p.y, p.z] for p in verts])          # brick side: depth runs the other way
    ax.add_collection(PolyCollection(v[np.array(tris)],
                                     facecolors="#aab2ba", edgecolors="none", zorder=1))
    return bb


def placements(side):
    """(id, name, depth range, height range, proud height) for every part on this wall.

    Two populations. The facade elements come back from collect() already placed, so
    their footprint is measured. Signs, brackets, lanterns and the wall-hung props are
    mounted by parts.kit through wall_mount_cuts(), which folds their sockets into the
    wall and keeps no part list -- for those the (u, z) of the socket IS the answer, and
    they are drawn as a marker rather than a footprint. Leaving them off was worse: 30H
    is on the trial plate and had no home anywhere in the first version of this drawing.
    """
    import data.facade as F
    parts, _, _, _ = W.collect(side)
    out = []
    for pt in parts:
        b = pt["placed"].val().BoundingBox()
        out.append(dict(id=pt["id"], name=pt["name"], mark=False,
                        u0=b.ymin, u1=b.ymax, z0=b.zmin, z1=b.zmax, proud=b.xmax))
    for table, kinds in ((F.SIGNS, None), (F.BRACKETS, None), (F.LANTERNS, None),
                         (F.PROPS, ("notice", "posters", "scraper"))):
        for row in table:
            if row.get("side") != side:
                continue
            if kinds is not None and row.get("kind") not in kinds:
                continue
            if table is F.SIGNS and row.get("kind") == "banner":
                continue
            u, z = row["u"], row.get("z", 20.0)
            w, h = row.get("w", 8.0), row.get("h", 8.0)
            out.append(dict(id=row["id"], name=row.get("name", row.get("kind", "")), mark=True,
                            u0=u - w / 2, u1=u + w / 2, z0=z - h / 2, z1=z + h / 2,
                            proud=2.5))
    return sorted(out, key=lambda r: (-r["z0"], -r["u0"]))


def draw(side, title, path):
    fig, ax = plt.subplots(figsize=(13, 13))
    bb = silhouette(ax, side)
    for r in placements(side):
        hot = r["id"] in TRIAL
        ax.add_patch(plt.Rectangle((-r["u1"], r["z0"]), r["u1"] - r["u0"], r["z1"] - r["z0"],
                                   fill=False, lw=2.0 if hot else 0.8,
                                   ec="#c1121f" if hot else "#2f3b47",
                                   ls="--" if r["mark"] else "-",
                                   zorder=4 if hot else 3))
        ax.text(-(r["u0"] + r["u1"]) / 2, (r["z0"] + r["z1"]) / 2, r["id"],
                ha="center", va="center", zorder=5,
                fontsize=7.5 if hot else 6,
                color="#c1121f" if hot else "#2f3b47",
                weight="bold" if hot else "normal")
    ax.set_xlim(-bb.ymax - 6, -bb.ymin + 6)
    ax.set_ylim(bb.zmin - 6, bb.zmax + 6)
    ax.set_aspect("equal")
    ax.set_title(f"{title}\nbrick side up, front opening on the right."
                 "  Red = on the trial plate.  Dashed = pegs onto flat brick.", fontsize=12)
    ax.set_xlabel("<- back of the nook              front opening ->")
    ax.set_ylabel("height above the alley floor  (mm)")
    ax.grid(alpha=.15)
    plt.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path, dpi=140)
    plt.close(fig)
    print("wrote", path)


def main():
    draw("L", "LEFT wall  -  01_L_Wall_Face", os.path.join(IMG, "wall_placement_L.png"))
    draw("R", "RIGHT wall  -  02_R_Wall_Face", os.path.join(IMG, "wall_placement_R.png"))

    L = ["# 06 -- Where each part goes", "",
         "Generated by `wallmap.py`. Depth is measured back from the front opening and",
         "height above the alley floor, both to the part's outer edges -- the same two",
         "numbers the drawings are laid out on.",
         "",
         "![left wall](img/wall_placement_L.png)",
         "",
         "![right wall](img/wall_placement_R.png)",
         ""]
    for side, nm in (("L", "Left wall -- `01_L_Wall_Face`"),
                     ("R", "Right wall -- `02_R_Wall_Face`")):
        rows = placements(side)
        L += [f"## {nm}", "", f"{len(rows)} parts.", "",
              "| part | name | depth (mm) | height (mm) | stands proud |",
              "|---|---|---|---|---|"]
        for r in rows:
            proud = "pegs into a socket here" if r["mark"] else f"{r['proud'] - 2.5:.1f} mm"
            L.append(f"| `{r['id']}` | {r['name']} | {r['u0']:.1f} – {r['u1']:.1f} | "
                     f"{r['z0']:.1f} – {r['z1']:.1f} | {proud} |")
        L.append("")
    with open(DOC, "w") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
