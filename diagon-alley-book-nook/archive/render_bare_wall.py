#!/usr/bin/env python3
"""Where is there any bare wall left to hang something on?

    python3 render_bare_wall.py   ->  docs/img/bare_wall_L.png, _R.png

Every sign, bracket, lantern and wall-hung prop needs a patch of wall that no shopfront,
window, pipe or cornice already covers -- for its socket AND for its own body. Guessing
at that from the element table is how eleven of the left wall's twelve hung mounts ended
up underneath the part next door.

White is free. Grey is taken, by the part named on it. The crosses are where the hung
parts sit now; a cross on grey is a mount with nothing to mount to.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from parts import walls as W
from parts import kit as K
from parts.decor import to_wall

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "img")
MARGIN = 1.0


def main():
    os.makedirs(OUT, exist_ok=True)
    for side in ("L", "R"):
        facade = [(p["id"], p["placed"].val().BoundingBox())
                  for p in W.collect(side)[0]]
        hung = []
        want = {r["id"] for _k, r, _ in K.wall_mount_rows(side)}
        for it in K.signs() + K.brackets() + K.lanterns() + K.props():
            if it.get("side") != side or it["id"] not in want:
                continue
            u, z = it["u"], it.get("z", 0) or 0
            b = to_wall(it["solid"], u, z).val().BoundingBox()
            hung.append((it["id"], u, z, b))

        fig, ax = plt.subplots(figsize=(15, 9), facecolor="white")
        ax.add_patch(Rectangle((0, 0), W.WALL_LEN, W.WALL_H, facecolor="white",
                               edgecolor="#333", lw=1.2, zorder=0))
        for pid, bb in sorted(facade, key=lambda t: -(t[1].ylen * t[1].zlen)):
            ax.add_patch(Rectangle((bb.ymin - MARGIN, bb.zmin - MARGIN),
                                   bb.ylen + 2 * MARGIN, bb.zlen + 2 * MARGIN,
                                   facecolor="#b9c0c6", edgecolor="#8a949c",
                                   lw=0.5, alpha=0.85, zorder=1))
            if bb.ylen * bb.zlen > 250:
                ax.text((bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2, pid,
                        ha="center", va="center", fontsize=7, color="#3d4750", zorder=2)
        for hid, u, z, b in hung:
            ax.add_patch(Rectangle((b.ymin, b.zmin), b.ylen, b.zlen, fill=False,
                                   edgecolor="#b23b3b", lw=1.4, zorder=3))
            ax.plot([u], [z], marker="+", ms=11, mew=2.0, color="#b23b3b", zorder=4)
            ax.text(u, b.zmax + 1.5, hid, ha="center", va="bottom", fontsize=8,
                    color="#b23b3b", fontweight="bold", zorder=4)

        ax.set_xlim(-6, W.WALL_LEN + 6)
        ax.set_ylim(-6, W.WALL_H + 10)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(f"{side} wall — white is bare wall (grey already carries a part, "
                     f"grown by the {MARGIN} mm a socket needs). "
                     "Red is what hangs on it.", fontsize=11, color="#1d2429")
        fig.tight_layout()
        out = os.path.join(OUT, f"bare_wall_{side}.png")
        fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print("  ->", out)


if __name__ == "__main__":
    main()
