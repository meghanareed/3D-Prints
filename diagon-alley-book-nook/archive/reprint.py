#!/usr/bin/env python3
"""Do I need to reprint this part?

    python3 reprint.py <git-ref> [part-id ...]
    python3 reprint.py 7726174 01 02

Builds the named parts as they were at `git-ref`, compares them against the parts the
current source produces, and says whether the difference matters.

This exists because the kit is printed piecemeal over days, so the real question after
every change is never "what did you change" but "is the thing already on my shelf still
good". A diff of the source cannot answer that and neither can the file size: the wall
face changed by 82.7 mm^3 out of 85,025 -- a tenth of a percent -- and the question of
whether to spend another four hours on it came down to *where* those 82.7 mm^3 were.

Three kinds of answer:

  identical    the geometry is the same. Keep what you printed.
  cosmetic     the part changed, but nothing that mates with it fits differently.
  functional   something that plugs into it now fits differently. Reprint before final
               assembly (testing on the old one is still fine).

The comparison is done on real solids via BREP, not STL. CadQuery's STL import produces
a triangulation-only face that does not behave like a solid in a boolean -- that is what
made every part on a plate stack at the origin once already.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROJ = os.path.basename(HERE)

# parts whose mates are worth re-checking one by one, and how to find those mates
MATED = {"01": ("L", "wall face"), "02": ("R", "wall face")}


def _vol(w):
    return w.val().Volume() if w.val() and w.val().Solids() else 0.0


def build_at(ref, ids, out_dir):
    """Check `ref` out into a scratch tree and build `ids` there, as BREP.

    In a subprocess: two versions of `parts.walls` cannot both be imported into one
    interpreter, and quietly getting the wrong one would defeat the whole exercise.
    """
    src = os.path.join(out_dir, "src")
    os.makedirs(src, exist_ok=True)
    tar = subprocess.run(["git", "archive", ref, PROJ], cwd=REPO,
                         capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", src], input=tar, check=True)
    proj = os.path.join(src, PROJ)

    script = (
        "import sys; sys.path.insert(0, '.')\n"
        "import cadquery as cq, build as B\n"
        f"ids = {ids!r}\n"
        f"out = {out_dir!r}\n"
        "for m in B.manifest():\n"
        "    if m['id'] not in ids:\n"
        "        continue\n"
        "    try:\n"
        "        s = m['fn']()\n"
        "    except Exception as e:\n"
        "        print('SKIP %s %s' % (m['id'], e)); continue\n"
        "    cq.exporters.export(s, out + '/old_' + m['id'] + '.brep')\n"
        "    print('built %s' % m['id'])\n"
    )
    r = subprocess.run([sys.executable, "-c", script], cwd=proj,
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit(f"could not build at {ref}")
    return {i: os.path.join(out_dir, f"old_{i}.brep") for i in ids
            if os.path.exists(os.path.join(out_dir, f"old_{i}.brep"))}


def load(path):
    return cq.Workplane("XY").newObject([cq.importers.importBrep(path).val()])


def compare_mates(pid, old, new):
    """For a wall, every facade part that mounts to it, measured against both walls.

    A part whose interference is unchanged fits the wall on your shelf exactly as it
    fits the current one -- including its crush-rib grip, which is interference and not
    a defect.
    """
    side, _ = MATED[pid]
    from parts import walls as WL
    parts, _, _, _ = WL.collect(side)
    moved = []
    for pt in parts:
        a = _vol(old.intersect(pt["placed"]))
        b = _vol(new.intersect(pt["placed"]))
        if abs(a - b) > 0.05:
            moved.append((a - b, a, b, pt["id"], pt["name"]))
    return len(parts), moved


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ref = sys.argv[1]
    ids = sys.argv[2:] or ["01", "02"]

    import build as B
    current = {m["id"]: m for m in B.manifest()}
    unknown = [i for i in ids if i not in current]
    if unknown:
        print("no such part: " + ", ".join(unknown))
        return 2

    tmp = tempfile.mkdtemp(prefix="reprint-")
    try:
        print(f"building {len(ids)} part(s) as of {ref} ...")
        old_files = build_at(ref, ids, tmp)
        for pid in ids:
            m = current[pid]
            if pid not in old_files:
                print(f"\n{pid} {m['name']}: did not exist at {ref} -- new part")
                continue
            old, new = load(old_files[pid]), m["fn"]()
            vo, vn = _vol(old), _vol(new)
            gone = _vol(old.cut(new))
            added = _vol(new.cut(old))
            print(f"\n{pid} {m['name']}")
            print(f"   volume {vo:.1f} -> {vn:.1f} mm^3 "
                  f"({added:.1f} added, {gone:.1f} removed)")
            if gone < 0.01 and added < 0.01:
                print("   IDENTICAL -- keep what you printed")
                continue
            if pid not in MATED:
                print("   changed; no mate list for this part, inspect it yourself")
                continue
            n, moved = compare_mates(pid, old, new)
            if not moved:
                print(f"   COSMETIC -- all {n} parts that mount to it fit identically")
                continue
            print(f"   FUNCTIONAL -- {len(moved)} of {n} mating parts fit differently:")
            for d, a, b, mid, nm in sorted(moved, key=lambda r: -abs(r[0])):
                how = "less grip" if d < 0 else "more grip"
                print(f"      {mid:<6} {nm:<30} printed {a:6.2f}  current {b:6.2f}"
                      f"   {how}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
