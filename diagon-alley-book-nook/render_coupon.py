#!/usr/bin/env python3
"""Render the tolerance coupon and its test tabs.

    python3 render_coupon.py   ->  out/preview/coupon_check.png

Worth having as its own script: from directly above -- which is how a slicer shows a
flat plate -- a 2 mm peg and a 2.4 mm hole look identical, so it is easy to believe
the coupon is wrong (or, worse, to believe it is right when it is not).
"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq
from lib.mount import tolerance_coupon

def tess(shape, tol=0.12):
    v, t = shape.val().tessellate(tol)
    return np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]

def shade(tris, base):
    n = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln==0]=1
    n = n/ln
    L = np.array([-0.4,-0.5,0.77]); L/=np.linalg.norm(L)
    k = 0.30+0.70*np.clip(n@L,0,1)
    return np.clip(np.array(base)[None,:]*k[:,None],0,1)

def order(tris, elev, azim):
    import math
    e,a = math.radians(elev), math.radians(azim)
    view = np.array([math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)])
    return np.argsort(tris.mean(axis=1)@view)

def main():
        coupon, pegs = tolerance_coupon()
    fig = plt.figure(figsize=(15,6.5), facecolor="white")
    for i,(obj,elev,azim,title,lim) in enumerate([
            (coupon, 88, -90, "70A coupon — from directly above (what the slicer shows)", (96,34)),
            (coupon, 26, -78, "70A coupon — raked, so the holes read", (96,34)),
            (pegs,   26, -78, "70B pegs — raked, pegs stand 4 mm proud", (46,16))]):
        tris = tess(obj)
        ax = fig.add_subplot(1,3,i+1, projection="3d", facecolor="white")
        o = order(tris, elev, azim)
        pc = Poly3DCollection(tris[o], linewidths=0, zsort="average")
        pc.set_facecolor(shade(tris[o], (0.86,0.82,0.66)))
        ax.add_collection3d(pc)
        b = tris.reshape(-1,3)
        ax.set_xlim(b[:,0].min()-2, b[:,0].max()+2)
        ax.set_ylim(b[:,1].min()-2, b[:,1].max()+2)
        ax.set_zlim(0, max(12, b[:,2].max()))
        ax.set_box_aspect((lim[0], lim[1], 14))
        ax.view_init(elev=elev, azim=azim); ax.set_axis_off()
        ax.set_title(title, fontsize=10, color="#333")
    fig.tight_layout()
    fig.savefig("out/preview/coupon_check.png", dpi=130, bbox_inches="tight", facecolor="white")
    print("written")


if __name__ == "__main__":
    main()
