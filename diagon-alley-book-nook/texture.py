"""Brick, as cut mortar rather than stacked bricks.

The obvious way to model a brick wall is to make bricks and union them. Do not: OCCT
booleans are the slow part of this whole pipeline, a wall face is hundreds of bricks, and
unioning hundreds of solids one at a time is how a build goes from seconds to an hour.

Cut the MORTAR instead. A running-bond wall is a handful of long horizontal grooves and a
scattering of short vertical ones, and every groove goes into a single cutting solid that
meets the plate in **one** boolean. A 60 x 40 tile is 42 grooves and 1 cut.

The variation matters as much as the pattern. A perfect grid reads as a texture map; real
brickwork is slightly irregular, and a wall of identical rectangles is the thing that makes
a print look printed. So brick ends jitter, a few bricks are knocked back, and a very few
are cut right out -- all from a fixed seed, because a texture that moves between builds
cannot be compared between prints.

    python texture.py           build a sample tile and report
    python texture.py --export  write out/texture_sample.stl
"""
import math
import os
import random
import sys

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))


def _rng(seed=None):
    return random.Random(int(P.RANDOM_SEED if seed is None else seed))


def courses(height, course_h=None):
    """Course baselines, bottom up."""
    ch = float(P.BRICK_HEIGHT if course_h is None else course_h)
    return [i * ch for i in range(int(math.ceil(height / ch)) + 1)]


def brick_ends(width, course_index, brick_l=None, jitter=None, rng=None):
    """Where the vertical joints fall on one course.

    Running bond: every other course is offset half a brick, so joints never stack. The
    jitter is what stops it reading as a grid.
    """
    bl = float(P.BRICK_LENGTH if brick_l is None else brick_l)
    jit = float(P.BRICK_JITTER if jitter is None else jitter)
    rng = rng or _rng()
    offset = (bl / 2.0) if course_index % 2 else 0.0
    xs, x = [], offset - bl
    while x < width + bl:
        if 0 < x < width:
            xs.append(x + rng.uniform(-jit, jit))
        x += bl

    # Drop any joint that would leave a stub. Clamping it to the edge instead -- which is
    # what this did first -- just moves the sliver rather than removing it, and plate 3
    # printed the result as a visible gap in the second course.
    floor = bl * float(P.MIN_BRICK_FRAC)
    kept = []
    for j in sorted(xs):
        if j < floor or (width - j) < floor:
            continue
        if kept and (j - kept[-1]) < floor:
            continue
        kept.append(j)
    return kept


def mortar(width, height, depth=None, seed=None):
    """The cutting solid: every mortar groove, unioned once.

    Returns (cutter, stats). Cut it from a face in a single boolean.
    """
    d = float(P.BRICK_RELIEF if depth is None else depth)
    gap = float(P.MORTAR_GAP)
    ch = float(P.BRICK_HEIGHT)
    rng = _rng(seed)

    parts, n_h, n_v, worn, missing = [], 0, 0, 0, 0

    # horizontal courses -- one long groove each, and cheap
    for y in courses(height)[1:]:
        if y >= height:
            break
        parts.append(cq.Workplane("XY")
                     .box(width + 2, gap, d + 1, centered=(True, True, False))
                     .translate((width / 2, y, -d)))
        n_h += 1

    # vertical joints, plus the worn and missing bricks
    for ci, y0 in enumerate(courses(height)[:-1]):
        y1 = min(y0 + ch, height)
        if y1 - y0 < gap:
            continue
        ends = brick_ends(width, ci, rng=rng)
        for x in ends:
            parts.append(cq.Workplane("XY")
                         .box(gap, (y1 - y0) - gap, d + 1, centered=(True, True, False))
                         .translate((x, (y0 + y1) / 2, -d)))
            n_v += 1

        # a few faces knocked back, a very few cut out entirely
        edges = [0.0] + ends + [width]
        for a, b in zip(edges, edges[1:]):
            if b - a < 2.0:
                continue
            r = rng.random()
            if r < float(P.BRICK_MISSING_FRAC):
                back, missing = d, missing + 1
            elif r < float(P.BRICK_MISSING_FRAC) + float(P.BRICK_WORN_FRAC):
                back, worn = d * rng.uniform(0.35, 0.7), worn + 1
            else:
                continue
            parts.append(cq.Workplane("XY")
                         .box(b - a - gap, (y1 - y0) - gap, back + 1,
                              centered=(True, True, False))
                         .translate(((a + b) / 2, (y0 + y1) / 2, -back)))

    # Union as a BALANCED TREE, not a running total. Folding 300 grooves into one
    # accumulator means every step boolean-ing against an ever-larger solid; pairing them
    # up keeps both operands small and turns O(n) big unions into O(log n) rounds. A wall
    # panel has ~300 grooves where the test tile had 26, and the difference is minutes.
    level = parts
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level) - 1, 2):
            nxt.append(level[i].union(level[i + 1]))
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    cutter = level[0]
    return cutter, dict(horizontals=n_h, verticals=n_v, worn=worn, missing=missing,
                        solids=len(parts))


def brick_face(plate, width, height, depth=None, seed=None, at=(0, 0, 0)):
    """Cut brick into the +Z face of `plate`, whose face sits at z = at[2].

    ONE boolean against the plate, however many grooves that took.
    """
    cutter, stats = mortar(width, height, depth, seed)
    return plate.cut(cutter.translate(at)), stats


# ==================================================================== self-test ==
def self_test():
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    w, h, thick = 60.0, 40.0, 2.5
    plate = cq.Workplane("XY").box(w, h, thick, centered=(False, False, False))
    faced, st = brick_face(plate, w, h, at=(0, 0, thick))

    t("the face is still one solid", len(faced.solids().vals()) == 1,
      f"{len(faced.solids().vals())} solids")
    t("mortar was actually cut", faced.val().Volume() < plate.val().Volume() - 10,
      f"{plate.val().Volume() - faced.val().Volume():.0f} mm3 removed")

    # The groove must be something a 0.4 nozzle can enter, or it prints as a flat face.
    t("mortar gap is at least two extrusions",
      float(P.MORTAR_GAP) >= 2 * float(P.LINE_W),
      f"{float(P.MORTAR_GAP)} vs {2 * float(P.LINE_W):.2f} mm")

    # Relief must survive its own layer height, or the courses vanish.
    t("relief is a whole number of layers",
      P._is_multiple(float(P.BRICK_RELIEF), float(P.LAYER)),
      f"{float(P.BRICK_RELIEF)} / {float(P.LAYER)}")

    # Running bond: joints must NOT stack between courses, or it reads as a grid.
    rng = _rng()
    c0 = brick_ends(w, 0, rng=_rng())
    c1 = brick_ends(w, 1, rng=_rng())
    closest = min(abs(a - b) for a in c0 for b in c1) if c0 and c1 else 99
    t("courses are offset, not stacked", closest > 1.0,
      f"nearest joint pair {closest:.2f} mm apart")

    # Determinism. A texture that moves between builds cannot be compared between prints.
    a, _ = mortar(30, 20)
    b, _ = mortar(30, 20)
    t("same seed gives the same wall", abs(a.val().Volume() - b.val().Volume()) < 1e-6)

    # No slivers. A stub brick beside full ones reads as a gap, not as brickwork.
    floor = float(P.BRICK_LENGTH) * float(P.MIN_BRICK_FRAC)
    rng2 = _rng()
    shortest = 99.0
    for ci in range(int(h / float(P.BRICK_HEIGHT))):
        e = [0.0] + brick_ends(w, ci, rng=rng2) + [w]
        shortest = min(shortest, min(b - a for a, b in zip(e, e[1:])))
    t("no brick is a sliver", shortest >= floor - 1e-6,
      f"shortest {shortest:.2f} mm, floor {floor:.2f} -- plate 3 printed a 3.8 mm stub "
      f"and it read as a gap")

    t("variation is present but sparse", 0 < st["worn"] + st["missing"] <= st["verticals"],
      f"{st['worn']} worn, {st['missing']} missing, of ~{st['verticals']} bricks")
    return out, st


if __name__ == "__main__":
    print("texture -- brick, cut as mortar\n")
    res, st = self_test()
    bad = 0
    for ok, name, detail in res:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok
    print(f"\n  a 60 x 40 tile: {st['horizontals']} course grooves + {st['verticals']} "
          f"verticals + {st['worn'] + st['missing']} knocked back")
    print(f"  {st['solids']} groove solids -> 1 cut on the plate")

    if "--export" in sys.argv:
        d = os.path.join(HERE, "out")
        os.makedirs(d, exist_ok=True)
        plate = cq.Workplane("XY").box(60, 40, 2.5, centered=(False, False, False))
        faced, _ = brick_face(plate, 60, 40, at=(0, 0, 2.5))
        cq.exporters.export(faced.val(), os.path.join(d, "texture_sample.stl"))
        print(f"\n  wrote {d}/texture_sample.stl")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
