"""Draw a plate at true scale with every part named.

A plate comes off the printer as thirty loose pieces and nothing on them says what they
are. The STL and 3MF carry each part's id as an object name, which is fine while it is
still in the slicer and useless the moment it is in your hand.

So every plate gets a map: the same shelf-pack positions, drawn to scale, each outline
labelled. Lay the plate on the bench in the orientation it printed and read it off.

The outline is the silhouette -- every triangle of the mesh projected onto XY. That is
one tessellation per part and no boolean, which matters when there are 182 of them; a
horizontal section would be truer but costs two booleans each.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


def silhouette(solid, tol=0.15):
    v, t = solid.val().tessellate(tol)
    return np.array([[p.x, p.y, p.z] for p in v])[np.array(t)][:, :, :2]


def draw(items, path, title, dpi=150, label_name=True):
    """items: [(id, name, solid_at_origin, x, y, w, d)] -- solids as shelf_pack placed them."""
    w = max(x + iw for _i, _n, _s, x, _y, iw, _d in items)
    d = max(y + idd for _i, _n, _s, _x, y, _w, idd in items)
    fig, ax = plt.subplots(figsize=(max(9.0, w / 22.0), max(6.0, d / 22.0 + 1.6)),
                           facecolor="white")
    for pid, name, solid, x, y, iw, idd in items:
        for poly in silhouette(solid):
            ax.add_patch(Polygon(poly + (x, y), closed=True, facecolor="#c3c9ce",
                                 edgecolor="none", zorder=1))
        txt = f"{pid}\n{name}" if label_name and name else pid
        ax.text(x + iw / 2, y + idd + 1.2, txt, ha="center", va="bottom",
                fontsize=6.5, color="#1d2429", zorder=3, linespacing=1.15)

    ax.plot([0, 50], [-7, -7], color="#222", lw=2)
    ax.text(25, -9.0, "50 mm", ha="center", va="top", fontsize=8, color="#222")
    ax.set_xlim(-6, w + 6)
    ax.set_ylim(-15, d + 14)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(title, fontsize=11, color="#1d2429")
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
