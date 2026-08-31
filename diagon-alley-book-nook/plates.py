#!/usr/bin/env python3
"""Arrange the exported STLs onto print plates.

    python3 plates.py

Reads out/manifest.json and out/stl/*.stl, shelf-packs each group onto
BED_X x BED_Y plates with a 6 mm gap, and writes one STL per plate to out/plates/.
Drop a plate file straight into the slicer: everything is already laid out and every
part is already in its print orientation.
"""
import json
import os
import sys

import cadquery as cq
from cadquery.occ_impl.shapes import Shape

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
STL = os.path.join(OUT, "stl")
PLATES = os.path.join(OUT, "plates")
GAP = 6.0
MARGIN = 5.0

# Parts are grouped so that one plate is one painting session: all the brickwork
# together, all the joinery together, all the ironwork together.
PLATE_GROUPS = [
    ("01_jigs_first", ["jigs"]),
    ("02_wall_faces", None, ["01", "02"]),
    ("03_wall_ribs", None, ["01R", "02R"]),
    ("04_chassis", None, ["00", "54"]),
    ("05_floor", None, ["04", "04B", "04C", "05"]),
    ("06_rear", None, ["03A", "03B", "03C", "03D", "03E", "03F", "09"]),
    ("07_front", None, ["06", "07", "08"]),
    ("08_case", None, ["50", "51", "52", "53", "55", "56"]),
    ("09_facade_left", ["facade_L"]),
    ("10_facade_right", ["facade_R"]),
    ("11_signs_props", ["signs", "props"]),
    ("12_hardware", ["lighting", "switch"]),
]


def load(rec):
    path = os.path.join(STL, rec["file"])
    if not os.path.exists(path):
        return None
    return cq.Workplane("XY").newObject([Shape.importBrep(path)]) \
        if path.endswith(".brep") else cq.importers.importStep(path) \
        if path.endswith(".step") else _import_stl(path)


def _import_stl(path):
    from OCP.RWStl import RWStl
    from OCP.TopoDS import TopoDS_Face
    from OCP.BRep import BRep_Builder
    poly = RWStl.ReadFile_s(path)
    face = TopoDS_Face()
    BRep_Builder().MakeFace(face, poly)
    return cq.Workplane("XY").newObject([cq.Shape.cast(face)])


def shelf_pack(items):
    """Simple shelf packing: sort tall-first, fill rows left to right."""
    placed, x, y, row_h = [], MARGIN, MARGIN, 0.0
    for name, shp, w, d in sorted(items, key=lambda t: -t[3]):
        if x + w > P.BED_X - MARGIN:
            x = MARGIN
            y += row_h + GAP
            row_h = 0.0
        if y + d > P.BED_Y - MARGIN:
            return placed, (name, shp, w, d)      # overflow: caller starts a new plate
        placed.append((name, shp, x, y))
        x += w + GAP
        row_h = max(row_h, d)
    return placed, None


def main():
    os.makedirs(PLATES, exist_ok=True)
    mpath = os.path.join(OUT, "manifest.json")
    if not os.path.exists(mpath):
        print("run build.py first")
        return 1
    rep = {r["id"]: r for r in json.load(open(mpath)) if r.get("status") == "ok"}

    n_plates = 0
    for spec in PLATE_GROUPS:
        label = spec[0]
        groups = spec[1]
        ids = spec[2] if len(spec) > 2 else None
        chosen = [r for r in rep.values()
                  if (ids is not None and r["id"] in ids)
                  or (groups is not None and r.get("group") in groups)]
        if not chosen:
            continue

        items = []
        for r in sorted(chosen, key=lambda r: r["id"]):
            shp = _import_stl(os.path.join(STL, r["file"]))
            bb = shp.val().BoundingBox()
            items.append((r["id"], shp.translate((-bb.xmin, -bb.ymin, -bb.zmin)),
                          bb.xlen, bb.ylen))

        part_no = 0
        while items:
            placed, overflow = shelf_pack(items)
            if not placed:
                print(f"  {label}: {items[0][0]} does not fit a plate on its own")
                items = items[1:]
                continue
            comp = None
            for name, shp, x, y in placed:
                moved = shp.translate((x, y, 0))
                comp = moved if comp is None else comp.union(moved) \
                    if False else (comp + [moved.val()] if isinstance(comp, list)
                                   else [comp.val(), moved.val()] if comp is not None
                                   else [moved.val()])
            shapes = comp if isinstance(comp, list) else [comp.val()]
            out = cq.Workplane("XY").newObject([cq.Compound.makeCompound(shapes)])
            part_no += 1
            suffix = "" if part_no == 1 else f"_{part_no}"
            fn = os.path.join(PLATES, f"{label}{suffix}.stl")
            cq.exporters.export(out, fn, tolerance=0.05, angularTolerance=0.3)
            g = sum(rep[n]["grams"] for n, _, _, _ in placed if n in rep)
            print(f"  {os.path.basename(fn):<28} {len(placed):3d} parts  {g:6.0f} g")
            n_plates += 1
            done = {n for n, _, _, _ in placed}
            items = [it for it in items if it[0] not in done]
    print(f"\n{n_plates} plates -> {PLATES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
