#!/usr/bin/env python3
"""Arrange the parts onto print plates.

    python3 plates.py

Builds each part from the model (in its print orientation), shelf-packs them onto
BED_X x BED_Y plates with a gap, and writes one STL per plate to out/plates/.
Drop a plate file straight into the slicer -- everything is already laid out flat and
the right way up.

This works from the MODEL, not from the exported STLs. Round-tripping through STL
produced a face carrying only a triangulation and no surface; translating one of those
moves the shape's location but the mesh comes back out at its original coordinates, so
every plate exported with all its parts stacked on top of each other at the origin.
"""
import json
import os
import sys

import cadquery as cq

import params as P
import build as B
from lib.util import compound

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PLATES = os.path.join(OUT, "plates")
GAP = 6.0
MARGIN = 6.0

# Grouped so one plate is one painting session: brickwork together, joinery together,
# ironwork together.
PLATE_GROUPS = [
    ("01_jigs_first", ("jigs",), None),
    ("02_wall_faces", None, ["01", "02"]),
    ("03_wall_ribs", None, ["01R", "02R"]),
    ("04_chassis", None, ["00", "54"]),
    ("05_floor", None, ["04", "04B", "04C", "05"]),
    ("06_rear", None, ["03A", "03B", "03C", "03D", "03E", "03F", "09"]),
    ("07_front", None, ["06", "07", "08"]),
    ("08_case", ("case",), None),
    ("09_facade_left", ("facade_L",), None),
    ("10_facade_right", ("facade_R",), None),
    ("11_signs_props", ("signs", "props"), None),
    ("12_hardware", ("lighting", "switch"), None),
]


def shelf_pack(items):
    """Shelf packing, tallest row first. Returns (placed, leftover)."""
    placed, leftover = [], []
    x, y, row_d = MARGIN, MARGIN, 0.0
    for it in sorted(items, key=lambda t: -t["d"]):
        w, d = it["w"], it["d"]
        if w > P.BED_X - 2 * MARGIN or d > P.BED_Y - 2 * MARGIN:
            print(f"    {it['id']} is {w:.0f} x {d:.0f} -- larger than the bed, skipped")
            continue
        if x + w > P.BED_X - MARGIN:          # next shelf
            x = MARGIN
            y += row_d + GAP
            row_d = 0.0
        if y + d > P.BED_Y - MARGIN:          # plate full
            leftover.append(it)
            continue
        placed.append((it, x, y))
        x += w + GAP
        row_d = max(row_d, d)
    return placed, leftover


def _assert_no_overlap(placed, label):
    """Guard the thing that actually went wrong: parts silently stacked on top of each
    other. Cheap AABB check -- if two footprints overlap, the layout is broken."""
    boxes = [(x, y, x + it["w"], y + it["d"], it["id"]) for it, x, y in placed]
    for i in range(len(boxes)):
        ax0, ay0, ax1, ay1, aid = boxes[i]
        for j in range(i + 1, len(boxes)):
            bx0, by0, bx1, by1, bid = boxes[j]
            if ax0 < bx1 - 1e-6 and bx0 < ax1 - 1e-6 and \
               ay0 < by1 - 1e-6 and by0 < ay1 - 1e-6:
                raise AssertionError(
                    f"{label}: {aid} and {bid} overlap on the plate")


def main():
    os.makedirs(PLATES, exist_ok=True)
    grams = {}
    mpath = os.path.join(OUT, "manifest.json")
    if os.path.exists(mpath):
        grams = {r["id"]: r.get("grams", 0.0) for r in json.load(open(mpath))}

    print("building parts ...")
    built = {}
    for m in B.manifest():
        try:
            solid = B.drop_to_bed(B.print_orient(m["fn"](), m["print_rot"]))
        except Exception as e:
            print(f"  {m['id']}: {type(e).__name__}: {e}")
            continue
        bb = solid.val().BoundingBox()
        built[m["id"]] = dict(id=m["id"], group=m["group"],
                              solid=solid.translate((-bb.xmin, -bb.ymin, 0)),
                              w=bb.xlen, d=bb.ylen)

    n_plates = 0
    for label, groups, ids in PLATE_GROUPS:
        chosen = [b for b in built.values()
                  if (ids is not None and b["id"] in ids)
                  or (groups is not None and b["group"] in groups)]
        if not chosen:
            continue
        items = sorted(chosen, key=lambda b: b["id"])
        part_no = 0
        while items:
            placed, items = shelf_pack(items)
            if not placed:
                break
            _assert_no_overlap(placed, label)
            solids = [it["solid"].translate((x, y, 0)) for it, x, y in placed]
            out = compound(solids)
            part_no += 1
            suffix = "" if part_no == 1 else f"_{part_no}"
            fn = os.path.join(PLATES, f"{label}{suffix}.stl")
            cq.exporters.export(out, fn, tolerance=0.04, angularTolerance=0.25)
            bb = out.val().BoundingBox()
            g = sum(grams.get(it["id"], 0.0) for it, _, _ in placed)
            print(f"  {label + suffix:<22} {len(placed):3d} parts  {g:6.0f} g   "
                  f"footprint {bb.xlen:5.1f} x {bb.ylen:5.1f} mm")
            n_plates += 1
    print(f"\n{n_plates} plates -> {PLATES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
