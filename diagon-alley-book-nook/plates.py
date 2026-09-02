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
CHECKLIST = os.path.join(HERE, "docs", "04_PRINT_CHECKLIST.md")
# Wide enough that the brims of two neighbours cannot touch. It was 6 mm, which was
# fine while the brim was somebody else's problem; now that the 3MF projects put a
# 5 mm brim on 65 of the parts, 6 mm of gap would fuse 22 of the 64 left-facade parts
# into one raft, and a raft that peels takes all of them with it. The price is one
# extra plate.
GAP = 2 * B.BRIM_WIDTH + 1.0
MARGIN = 6.0

# Grouped so one plate is one painting session: brickwork together, joinery together,
# ironwork together.
PLATE_GROUPS = [
    # Split deliberately. Plate 00 is the calibration print and nothing else, so
    # "print this first and stop" costs ten minutes rather than an hour of tools you
    # do not need until much later.
    ("00_CALIBRATE_FIRST", None, ["70A", "70B"]),
    # T3 and C4 -- the two joints that carry the model. Print this before the case.
    ("01_CALIBRATE_JOINTS", None, ["74A", "74B"]),
    # One plate per side, named for the side. These used to be one group each, which
    # the packer spilled onto "..._2" -- so which file was the left wall and which the
    # right depended on the packing order rather than on anything you could read.
    ("02_wall_face_LEFT", None, ["01"]),
    ("02_wall_face_RIGHT", None, ["02"]),
    ("03_wall_rib_LEFT", None, ["01R"]),
    ("03_wall_rib_RIGHT", None, ["02R"]),
    ("04_chassis", None, ["00", "54"]),
    ("05_floor", None, ["04", "04B", "04C", "05"]),
    ("06_rear", None, ["03A", "03B", "03C", "03D", "03E", "03F", "09"]),
    ("07_front", None, ["06", "07", "08"]),
    ("08_case", ("case",), None),
    ("09_facade_left", ("facade_L",), None),
    ("10_facade_right", ("facade_R",), None),
    ("11_signs_props", ("signs", "props"), None),
    ("12_hardware", ("lighting", "switch"), None),
    ("13_bench_tools", ("jigs",), None),      # paint handles, ID card, cut templates
]


# A trial plate: one of every joint in the kit, plus the two parts whose geometry was
# most recently reworked, in about 8 g and half an hour. Print this, try it against a
# wall face, and you have exercised every mount type before committing to 64 parts.
#
# It is emitted IN ADDITION to the twenty plates and deliberately sits outside their
# bookkeeping -- these parts still belong to the facade plates for the real build, so
# this is the one place the "a part belongs to exactly one plate" rule is suspended.
TRIAL_PLATE = [
    "13A", "13Ag", "13As",     # P2 keyed pair: frame, glazing, sill
    "19C",                     # P1 micro peg on its own
    "11A", "11Ag", "11Ar", "11Ac",   # T3 tongue: bay body, glazing, roof, corbel
    "12G",                     # door -- the knob is incised now, not proud
    "15A",                     # drainpipe -- the crown is planed flat now
    "30H",                     # a sign, printed face up
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
    # Clear the directory first. Renaming a plate used to leave the old file sitting
    # there -- "01_jigs_first.stl" survived three renames and would have been opened
    # as plate 01 by anyone reading the folder rather than the docs.
    for f in os.listdir(PLATES):
        if f.endswith(".stl"):
            os.remove(os.path.join(PLATES, f))
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
    sheet = []               # (plate file, grams, [part ids]) -- feeds the checklist
    already = set()          # a part belongs to exactly one plate
    for label, groups, ids in PLATE_GROUPS:
        chosen = [b for b in built.values()
                  if b["id"] not in already
                  and ((ids is not None and b["id"] in ids)
                       or (groups is not None and b["group"] in groups))]
        already.update(b["id"] for b in chosen)
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
            sheet.append((label + suffix, g, [it["id"] for it, _, _ in placed]))
            print(f"  {label + suffix:<22} {len(placed):3d} parts  {g:6.0f} g   "
                  f"footprint {bb.xlen:5.1f} x {bb.ylen:5.1f} mm")
            n_plates += 1
    missed = [b["id"] for b in built.values() if b["id"] not in already]
    if missed:
        print(f"\n  !! {len(missed)} parts are on no plate: {', '.join(sorted(missed))}")
    trial = [built[i] for i in TRIAL_PLATE if i in built]
    if trial:
        placed, left = shelf_pack(sorted(trial, key=lambda b: b["id"]))
        if placed and not left:
            _assert_no_overlap(placed, "TRIAL_first_fit")
            out = compound([it["solid"].translate((x, y, 0)) for it, x, y in placed])
            fn = os.path.join(PLATES, "TRIAL_first_fit.stl")
            cq.exporters.export(out, fn, tolerance=0.04, angularTolerance=0.25)
            g = sum(grams.get(it["id"], 0.0) for it, _, _ in placed)
            bb = out.val().BoundingBox()
            print(f"  {'TRIAL_first_fit':<22} {len(placed):3d} parts  {g:6.0f} g   "
                  f"footprint {bb.xlen:5.1f} x {bb.ylen:5.1f} mm   (extra, not counted)")
        else:
            print("  !! the trial plate does not fit on one bed")

    names = {m["id"]: m["name"] for m in B.manifest()}
    notes = {m["id"]: m["note"] for m in B.manifest()}
    write_checklist(sheet, names, notes, grams)
    print(f"\n{n_plates} plates, {len(already)} of {len(built)} parts -> {PLATES}")
    print(f"checklist -> {CHECKLIST}")
    return 1 if missed else 0


def _existing_ticks():
    """Read back whatever is already ticked, so regenerating never loses progress.

    The whole point of this file is that it is printed off piecemeal over days. A
    generator that wiped the ticks every time build.py ran would be worse than no
    generator at all.
    """
    done = set()
    if not os.path.exists(CHECKLIST):
        return done
    for line in open(CHECKLIST):
        st = line.strip()
        if st.startswith("- [x]") or st.startswith("- [X]"):
            bits = st.split("`")
            if len(bits) > 1:
                done.add(bits[1])
    return done


def write_checklist(sheet, names, notes, grams):
    done = _existing_ticks()
    # parts whose bridged area dwarfs their base want a brim -- see check_bed_contact()
    brim = set()
    mpath = os.path.join(OUT, "manifest.json")
    if os.path.exists(mpath):
        for r in json.load(open(mpath)):
            if B.needs_brim(r):
                brim.add(r["id"])
    os.makedirs(os.path.dirname(CHECKLIST), exist_ok=True)
    total = sum(g for _, g, _ in sheet)
    n_parts = sum(len(ids) for _, _, ids in sheet)
    n_done = sum(1 for _, _, ids in sheet for i in ids if i in done)
    with open(CHECKLIST, "w") as f:
        w = f.write
        w("# Print checklist\n\n")
        w("*Generated by `plates.py`. Ticks are preserved when it regenerates -- edit\n"
          "the boxes, not the part lists.*\n\n")
        w(f"**{n_done} of {n_parts} parts printed**, {total:.0f} g of PLA in the whole "
          f"kit across {len(sheet)} plates.\n\n")
        w("Tick a part when it is printed AND you have looked at it. A part that came\n"
          "off the plate warped or with a bit missing is not printed.\n\n")
        w("## Order\n\n")
        w("| # | Plate | Why in this position |\n|---|---|---|\n")
        for n, (lbl, why) in enumerate(ORDER_NOTES, 1):
            w(f"| {n} | `{lbl}` | {why} |\n")
        w("\n---\n\n")
        for label, g, ids in sheet:
            got = sum(1 for i in ids if i in done)
            w(f"## `{label}.stl`  ---  {len(ids)} parts, {g:.0f} g  "
              f"({got}/{len(ids)} done)\n\n")
            for i in sorted(ids):
                box = "x" if i in done else " "
                note = notes.get(i, "")
                if i in brim:
                    note = (note + "; " if note else "") + "**print with a brim**"
                tail = f" -- {note}" if note else ""
                w(f"- [{box}] `{i}` {names.get(i, '?')} "
                  f"({grams.get(i, 0.0):.1f} g){tail}\n")
            w("\n")


ORDER_NOTES = [
    ("00_CALIBRATE_FIRST", "sets FIT_CLEARANCE. Print this and stop."),
    ("01_CALIBRATE_JOINTS", "T3 and C4. Print before anything structural."),
    ("02_wall_face_LEFT", "the signature part; proves brim, bed temp and brick relief"),
    ("02_wall_face_RIGHT", "same again"),
    ("09_facade_left", "a handful first, tried on the printed wall, before all 64"),
    ("10_facade_right", ""),
    ("03_wall_rib_LEFT", "T3 mate for the face"),
    ("03_wall_rib_RIGHT", ""),
    ("04_chassis", "big and slow; only once the walls are proven"),
    ("05_floor", ""),
    ("06_rear", ""),
    ("07_front", ""),
    ("11_signs_props", ""),
    ("12_hardware", ""),
    ("13_bench_tools", "paint handles -- print before you start painting"),
    ("08_case", "ON HOLD -- see 02_ASSEMBLY.md section 0c"),
]


if __name__ == "__main__":
    sys.exit(main())
