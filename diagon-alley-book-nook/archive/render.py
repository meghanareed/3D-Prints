#!/usr/bin/env python3
"""Render preview images of the assembled and exploded kit.

    python3 render.py

Rebuilds the placed assembly, tessellates it, and writes shaded PNGs to out/preview/.
Colour follows the part's paint group, so the images show the modularity rather than
just the silhouette.
"""
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import params as P
import build as B

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "preview")

COL = dict(brick=(0.70, 0.42, 0.34), stone=(0.80, 0.77, 0.70), wood=(0.42, 0.29, 0.20),
           iron=(0.17, 0.17, 0.19), black=(0.13, 0.13, 0.14), grey=(0.52, 0.52, 0.55),
           white=(0.95, 0.94, 0.88), tan=(0.78, 0.68, 0.53))


def tessellate(shape, tol=0.35):
    verts, tris = shape.val().tessellate(tol)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    t = np.array(tris)
    return v, t


def collect(explode=0.0, skip_groups=()):
    """Build every placed part once and return (triangles, colour) batches."""
    batches = []
    for m in B.manifest():
        if m["place"] is None or m["group"] in skip_groups:
            continue
        try:
            solid = m["fn"]()
            placed = m["place"](solid)
        except Exception:
            continue
        if explode:
            bb = placed.val().BoundingBox()
            dx = bb.center.x - P.CHASSIS_W / 2
            dy = bb.center.y - P.CHASSIS_D / 2
            n = math.hypot(dx, dy) or 1.0
            placed = placed.translate((dx / n * explode, dy / n * explode * 0.5, 0))
        try:
            v, t = tessellate(placed, tol=0.18)
        except Exception:
            continue
        if len(t) == 0:
            continue
        batches.append((v[t], COL.get(m["colour"], COL["tan"])))
    return batches


def shade(tris, base):
    """Flat lighting from the front-left-above, so relief actually reads."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1.0
    n = n / ln
    light = np.array([-0.45, -0.75, 0.49])
    light = light / np.linalg.norm(light)
    lam = np.clip(n @ light, 0.0, 1.0)
    k = 0.34 + 0.66 * lam
    return np.clip(np.array(base)[None, :] * k[:, None], 0, 1)


def _depth_order(tris, elev, azim):
    """Painter's order: farthest first, along the actual view direction."""
    e, a = math.radians(elev), math.radians(azim)
    view = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a),
                     math.sin(e)])
    d = tris.mean(axis=1) @ view
    return np.argsort(d)


def draw(ax, batches, elev, azim, title):
    # ONE collection holding every triangle. Poly3DCollection depth-sorts within an
    # artist but not between artists, so one collection per part gives arbitrary
    # occlusion -- which is what made the first render an unreadable black slab.
    tris = np.concatenate([b[0] for b in batches])
    cols = np.concatenate([shade(b[0], b[1]) for b in batches])
    order = _depth_order(tris, elev, azim)
    pc = Poly3DCollection(tris[order], linewidths=0, zsort="average")
    pc.set_facecolor(cols[order])
    ax.add_collection3d(pc)
    W, D, H = P.BOOKNOOK_WIDTH, P.BOOKNOOK_DEPTH, P.BOOKNOOK_HEIGHT
    ax.set_xlim(-W * 0.9, W * 0.9)
    ax.set_ylim(-10, D + 10)
    ax.set_zlim(0, H)
    ax.set_box_aspect((W * 1.8, D + 20, H))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, color="#333", fontsize=11, pad=2)


def main():
    os.makedirs(OUT, exist_ok=True)

    print("  tessellating chassis ...")
    # the case is deliberately left out: it is a plain black box and it hides the
    # entire scene, which is the whole point of it being removable
    asm = collect(skip_groups=("case", "switch"))
    fig = plt.figure(figsize=(15, 7.2), facecolor="white")
    for i, (elev, azim, name) in enumerate([
            (4, -90, "Down the alley (viewer's eye)"),
            (18, -62, "Three-quarter"),
            (14, -118, "Opposite three-quarter")]):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", facecolor="white")
        draw(ax, asm, elev, azim, name)
    fig.suptitle("Crooked Lane Book Nook — assembled chassis (case removed)",
                 fontsize=14, color="#222")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "assembly.png"), dpi=125,
                bbox_inches="tight", facecolor="white")
    print("  ->", os.path.join(OUT, "assembly.png"))

    print("  tessellating exploded ...")
    exp = collect(explode=95.0, skip_groups=("case", "switch"))
    fig2 = plt.figure(figsize=(11, 8), facecolor="white")
    ax = fig2.add_subplot(111, projection="3d", facecolor="white")
    draw(ax, exp, 18, -72, "")
    ax.set_xlim(-P.BOOKNOOK_WIDTH * 2.4, P.BOOKNOOK_WIDTH * 2.4)
    fig2.suptitle("Crooked Lane Book Nook — exploded", fontsize=14, color="#222")
    fig2.savefig(os.path.join(OUT, "exploded.png"), dpi=125,
                 bbox_inches="tight", facecolor="white")
    print("  ->", os.path.join(OUT, "exploded.png"))


if __name__ == "__main__":
    main()
