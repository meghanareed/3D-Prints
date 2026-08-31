#!/usr/bin/env python3
"""Section diagram of a tolerance-coupon socket, showing the crush ribs.

    python3 render_socket.py   ->  out/preview/socket_section.png

The ribs read as a printing fault -- small lumps part way down an otherwise square
hole -- so it is worth having a picture that says otherwise. The profile is MEASURED
off the generated solid rather than drawn from the nominal numbers, so if the ribs ever
stop being generated this picture stops showing them.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cadquery as cq
import params as P
from lib import mount as MT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "preview")
STEPS = 90


def measure(v):
    """Clear opening across the ribbed axis, at every depth down the P1 bore."""
    real = (P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE)
    P.DECORATIVE_CLEARANCE = P.FIT_CLEARANCE = v
    try:
        plate = cq.Workplane("XY").box(26, 34, 6, centered=(False, False, False))
        cut, ribs = MT.socket_p1_solids((13, MT.COUPON_P1_Y, 6), axis="-Z")
        st = plate.cut(cut).union(ribs)
    finally:
        P.DECORATIVE_CLEARANCE, P.FIT_CLEARANCE = real

    depths, lefts, rights = [], [], []
    for k in range(1, 45):
        d = k * 0.1
        z = 6.0 - d
        xs = []
        for i in range(121):
            x = 13 - 3.0 + 6.0 * i / 120
            probe = cq.Workplane("XY").box(0.02, 0.02, 0.04).translate((x, MT.COUPON_P1_Y, z))
            if not st.intersect(probe).val().Solids():
                xs.append(x - 13)
        if not xs:
            break
        depths.append(d)
        lefts.append(min(xs))
        rights.append(max(xs))
    return np.array(depths), np.array(lefts), np.array(rights)


def main():
    os.makedirs(OUT, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), facecolor="white")

    for ax, v in zip(axes, (0.20, 0.35)):
        d, lo, hi = measure(v)
        ax.fill_betweenx(d, -2.6, lo, color="#b9b4a6", zorder=1)
        ax.fill_betweenx(d, hi, 2.6, color="#b9b4a6", zorder=1)
        peg = MT.P1_W / 2
        ax.fill_betweenx([0, MT.P1_L], -peg, peg, color="#c2503c", alpha=0.32,
                         zorder=2, label=f"peg, {MT.P1_W:.1f} mm wide")
        ax.plot(lo, d, color="#3a362e", lw=1.4, zorder=3)
        ax.plot(hi, d, color="#3a362e", lw=1.4, zorder=3)
        pinch = float(np.min(hi - lo))
        ax.axhline(d[np.argmin(hi - lo)], color="#c2503c", lw=0.8, ls=":", zorder=4)
        ax.annotate(f"crush ribs pinch to {pinch:.2f} mm\n"
                    f"peg is {MT.P1_W:.1f} — it shears past them",
                    xy=(0, d[np.argmin(hi - lo)]), xytext=(0, -1.15),
                    ha="center", fontsize=9, color="#c2503c")
        ax.annotate("lead-in counterbore", xy=(hi[1], 0.1), xytext=(0, -0.5),
                    ha="center", fontsize=9, color="#555")
        ax.set_title(f"{v:.2f} station — bore {MT.P1_W + 2*v:.2f} mm", fontsize=11)
        ax.set_xlim(-2.6, 2.6)
        ax.set_ylim(max(d) + 0.4, -1.6)
        ax.set_xlabel("mm across the socket")
        ax.set_ylabel("mm below the surface")
        ax.grid(alpha=0.25)
        ax.legend(loc="lower right", fontsize=8)

    fig.suptitle("The lumps inside the hole are crush ribs — they are meant to be there",
                 fontsize=14, color="#222")
    fig.tight_layout()
    out = os.path.join(OUT, "socket_section.png")
    fig.savefig(out, dpi=135, bbox_inches="tight", facecolor="white")
    print("  ->", out)


if __name__ == "__main__":
    main()
