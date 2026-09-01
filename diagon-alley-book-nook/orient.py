#!/usr/bin/env python3
"""Find a better print orientation for the parts that stand on a point.

    python3 orient.py              # every part check_bed_contact() fails
    python3 orient.py --all        # every part in the kit
    python3 orient.py 04B 45A      # just these

Builds each part once, tries it in every axis-aligned orientation, and measures the
first-layer area and the downward-facing area of each. Prints the current orientation
alongside the best candidates so the choice can be made on numbers.

It does NOT edit build.py. Orientation is not purely a printability question -- a
facade part wants its visible face against the plate whatever that costs in overhang --
so the manifest keeps the last word and this is the evidence for it.
"""
import json
import os
import sys

import build as B

HERE = os.path.dirname(os.path.abspath(__file__))

CANDIDATES = [None,
              ("X", 180), ("X", 90), ("X", -90),
              ("Y", 90), ("Y", -90),
              ("Z", 90)]

# Facade parts mount with their pegs along the part's -Z (the PART FRAME CONVENTION at
# the top of lib/window.py), so only a 180 degree flip leaves those pegs pointing UP.
#
# That constraint is not negotiable for a mount feature. Laid on its side a P1 peg is a
# 2.5 x 3.5 mm horizontal cantilever, and it is the one surface on the part that has to
# slide into a 0.25 mm clearance: it will droop, or it will need support, and support
# scarring on a peg is worse than the adhesion problem re-orienting was solving. An
# earlier pass of this sweep traded exactly that away on some forty sills, lintels,
# keystones and corbels, because it was scoring bed area and overhang and knew nothing
# about which face was fit-critical.
#
# Small facade parts that then have too little bed get a brim, which is mandatory for
# them anyway -- see check_bed_contact() and docs/02_ASSEMBLY.md section 0e.
PEGS_UP_GROUPS = {"facade_L", "facade_R"}
PEGS_UP_CANDIDATES = [("X", 180), ("Y", 180)]


def score(bed, overhang, bbox):
    """Lower is better.

    Three ways a part fails on the plate, and the first version of this function only
    knew about one of them:

      1. nothing holding it down. Dominates everything else.
      2. more hanging in the air than standing on the bed.
      3. tall and narrow, so the nozzle levers it off sideways -- which scoring on
         overhang alone actively caused: it stood the chassis base pan on edge, a
         15 mm wide footprint under 95 mm of height, and the ceiling baffle likewise.
         Both were fine lying flat.

    Small parts also need enough base in absolute terms; 19C came off the plate as
    spaghetti with 15.4 mm^2 and the slicer's Auto brim enabled.
    """
    if bed < 3.0:
        return 1e6 - bed
    w, d, h = bbox
    tippy = h / max(min(w, d), 0.01)
    return (overhang / bed
            + 2.0 * max(0.0, tippy - 1.5)
            + 2.0 * max(0.0, (25.0 - bed) / 25.0))


def candidates_for(group):
    return PEGS_UP_CANDIDATES if group in PEGS_UP_GROUPS else CANDIDATES


def measure_all(solid, current, group=None):
    """Every orientation, best first.

    Ties break toward the orientation the manifest already has, then toward no rotation
    at all. Without that the sweep "recommended" ("Z", 90) for a couple of parts -- a
    rotation about Z cannot change which face is down, so it scored identically to the
    current setting and won on list order alone. A recommendation that changes nothing
    is worse than none: it invites a pointless edit and hides the real ones.
    """
    out = []
    for rot in candidates_for(group):
        try:
            pr = B.drop_to_bed(B.print_orient(solid, rot))
            if not B.fits_bed(pr):
                continue
            bed, over = B.bed_and_overhang(pr)
            bb = pr.val().BoundingBox()
        except Exception:
            continue
        rank = 0 if rot == current else (1 if rot is None else 2)
        out.append((score(bed, over, (bb.xlen, bb.ylen, bb.zlen)), rank, rot, bed, over))
    out.sort(key=lambda r: (round(r[0], 6), r[1]))
    return [(a, c, d, e) for a, _, c, d, e in out]


def all_ids():
    return [m["id"] for m in B.manifest()]


def failing_ids():
    path = os.path.join(HERE, "out", "manifest.json")
    if not os.path.exists(path):
        raise SystemExit("run build.py first")
    rows = [r for r in json.load(open(path))
            if r.get("status") == "ok" and "bed" in r]
    return [r["id"] for r in rows
            if r["bed"] < 3.0
            or (r["overhang"] > 50.0 and r["overhang"] > 4.0 * max(r["bed"], 0.1))]


def main():
    want = sys.argv[1:]
    if want == ["--all"]:
        want = all_ids()
    elif not want:
        want = failing_ids()
    if not want:
        print("nothing to do -- no part is standing on a point")
        return 0
    manifest = {m["id"]: m for m in B.manifest()}
    print(f"{len(want)} part(s) to re-orient\n")
    print("%-6s %-28s %-12s %8s %9s   %-12s %8s %9s"
          % ("id", "name", "current", "bed", "overhang", "best", "bed", "overhang"))
    changes = []
    for pid in want:
        m = manifest.get(pid)
        if m is None:
            continue
        try:
            solid = m["fn"]()
        except Exception as e:
            print(f"{pid}: will not build -- {e}")
            continue
        results = measure_all(solid, m["print_rot"], m["group"])
        if not results:
            print(f"{pid}: no orientation fits the bed")
            continue
        cur = next((r for r in results if r[1] == m["print_rot"]), None)
        best = results[0]
        cb, co = (cur[2], cur[3]) if cur else (float("nan"), float("nan"))
        print("%-6s %-28s %-12s %8.1f %9.1f   %-12s %8.1f %9.1f%s"
              % (pid, m["name"], str(m["print_rot"]), cb, co,
                 str(best[1]), best[2], best[3],
                 "" if best[1] == m["print_rot"] else "   <-- change"))
        # only call it a change if it is worth making
        better = cur is None or best[0] < cur[0] * 0.95 or (cur[2] < 3.0 <= best[2])
        if best[1] != m["print_rot"] and better:
            changes.append((pid, m["name"], m["print_rot"], best[1]))
    if changes:
        print(f"\n{len(changes)} part(s) would improve. Suggested manifest edits:")
        for pid, name, old, new in changes:
            print(f"    {pid:<6} {name:<28} print_rot={old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
