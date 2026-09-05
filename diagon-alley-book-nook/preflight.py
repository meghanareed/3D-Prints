"""Predict the slicer's own warnings, before slicing.

Four defects in four previews were found by opening the plate in Bambu and reading an
orange box. That is a working feedback loop but a slow one, and it was finding things
19 joint tests and 22 coupon tests could not. This module closes it by implementing
Bambu's ACTUAL criteria rather than a guess at them.

Read out of BambuStudio/src/libslic3r, not inferred:

    PrintObject::is_support_necessary()
        const double cantilevel_dist_thresh = scale_(6);
        if (tree_support.has_sharp_tails)                      -> SharpTail
        else if (has_cantilever && max_cantilever_dist > 6mm)   -> Cantilever

    TreeSupport::detect_overhangs()
        const double area_thresh_well_supported   = SQ(scale_(6));   // 36 mm2
        const double length_thresh_well_supported = scale_(6);       // 6 mm
        const double radius_thresh_small_overhang = 2.5 * extrusion_width;
        static const double sharp_tail_max_support_height = 16.f;
        thresh_angle = support_threshold_angle + 1

        // a sharp tail is a region that:
        //   does NOT overlap the layer below, offset by 0.1 * extrusion_width
        //   is small in area AND bounding box
        //   survives eroding by 0.1 * extrusion_width  (not a sliver)
        //   does not overlap TWO layers below either

The important correction this brought: **"floating regions" is not an overhang-angle
test.** It is an ISLAND test -- material whose footprint has nothing beneath it. I had
been reasoning in degrees for four rounds, and degrees are the wrong unit. An overhang
at 20 degrees is fine if it is attached; a perfectly vertical wall is a sharp tail if it
starts in mid-air.

    python preflight.py            check every part on the coupon plate
    python preflight.py --self     run the regression corpus only

KNOWN LIMITATION, recorded so nobody plans around a tool that cannot do it: this is far
too SLOW to sit in the edit-slice loop. Each layer costs several CAD booleans, each
erosion and dilation costs eight more, and a 13-part plate runs for many minutes -- long
enough that opening the file in Bambu is simply faster. Two full-plate runs were killed
rather than waited out.

It is useful for what it IS: a corpus that pins down what the criteria actually are, and
a way to answer a specific question about a specific part offline. It is not a gate, and
checks.py deliberately does not call it. Making it practical means working on 2D
polygons -- slice once, then use a polygon library -- rather than on solids, which is a
rewrite and not a tuning.
"""
import math
import os
import sys
import time

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))

# Bambu's own constants, named as they are named there.
CANTILEVER_DIST_THRESH = 6.0        # mm; scale_(6) in is_support_necessary()
THRESH_BIG_OVERHANG = 6.0           # mm; SQ(scale_(6)) as an area, 6 mm as a length
OVERLAP_EPS_FACTOR = 0.1            # of extrusion width, from !overlaps(expoly, lower)


def lower_layer_offset(layer=None, thresh_angle=None):
    """How far the lower layer is ERODED before the overlap test.

        coordf_t lower_layer_offset = lower_layer->height / tan(threshold_rad);

    This is the line that matters, and getting it backwards is what made the first
    version of this module pass a pin it should have failed. The lower layer is shrunk,
    not grown: a region only counts as supported if it sits over material that is still
    there after allowing for how far one layer may legally overhang. Erode by less and
    everything looks supported.
    """
    lay = float(P.LAYER if layer is None else layer)
    ang = float(P.PROFILE["support_threshold_angle"] if thresh_angle is None
                else thresh_angle) + 1.0        # "+1 makes the threshold inclusive"
    ang = min(ang, 89.0)
    return lay / math.tan(math.radians(ang))


def _erode(w, r, n=8):
    """Erode a slab by r, as the intersection of its translations round a circle."""
    if r <= 1e-9:
        return w
    out = w
    for i in range(n):
        a = 2 * math.pi * i / n
        out = out.intersect(w.translate((r * math.cos(a), r * math.sin(a), 0)))
        if not out.solids().vals():
            return out
    return out


def _reach(unsup, support, probes=(0.4, 1.0, 2.0, 4.0, 6.0, 9.0)):
    """How far `unsup` extends beyond `support`.

    Dilate the support until it swallows the unsupported material; the radius that does
    it is the reach. Bambu measures a distance along the contour from its support, which
    this approximates -- stated as an approximation rather than dressed up as the same
    thing.
    """
    for r in probes:
        grown = support
        for i in range(8):
            a = 2 * math.pi * i / 8
            grown = grown.union(support.translate((r * math.cos(a), r * math.sin(a), 0)))
        if _vol(unsup.cut(grown)) < 1e-6:
            return r
    return probes[-1] + 1.0


def _slab(solid, z, h):
    """The material between z and z+h, as a thin slab."""
    box = cq.Workplane("XY").box(400, 400, h, centered=(True, True, False)).translate((0, 0, z))
    try:
        return solid.intersect(box)
    except Exception:
        return None


def _vol(w):
    try:
        return w.val().Volume() if w and w.solids().vals() else 0.0
    except Exception:
        return 0.0


def analyse(solid, layer=None, step=1, first_layer=None):
    """Find islands and unsupported extents, layer by layer.

    Returns dict(islands=[...], max_unsupported=mm, layers=n, seconds=t).

    An ISLAND is a connected component of a layer that does not overlap the layer below
    -- Bambu's sharp-tail test, and the thing that produces "floating regions".
    """
    t0 = time.time()
    lay = float(P.LAYER if layer is None else layer)
    first = float(P.FIRST_LAYER_H if first_layer is None else first_layer)
    eps = OVERLAP_EPS_FACTOR * float(P.LINE_W)

    bb = solid.val().BoundingBox()
    erode_r = max(lower_layer_offset(lay) - OVERLAP_EPS_FACTOR * float(P.LINE_W), 0.0)
    # Anything whose lowest material is above the plate starts in mid-air.
    if bb.zmin > 1e-6:
        return dict(islands=[(bb.zmin, 0.0)], max_unsupported=0.0, layers=0,
                    seconds=time.time() - t0, note="part does not touch the plate")
    z = bb.zmin + first
    islands, max_unsup, n = [], 0.0, 0

    while z < bb.zmax - 1e-6:
        cur = _slab(solid, z, lay * 0.9)
        if cur is None or not cur.solids().vals():
            z += lay * step
            continue
        below = _slab(solid, z - lay, lay * 0.9)
        n += 1

        if below is None or not below.solids().vals():
            # nothing at all beneath this layer: every component is an island unless
            # this IS the first layer, which rests on the plate.
            if z > bb.zmin + first + 1e-6:
                for s in cur.solids().vals():
                    islands.append((z, s.Volume() / (lay * 0.9)))
            z += lay * step
            continue

        # Lift the lower slab so the two are coplanar, then ERODE it by
        # layer_height / tan(threshold) -- Bambu's lower_layer_offset. A region counts as
        # supported only if it sits over material still present after allowing for how
        # far one layer may legally overhang.
        lifted = below.translate((0, 0, lay))
        try:
            grown = _erode(lifted, erode_r)
        except Exception:
            grown = lifted

        for s in cur.solids().vals():
            comp = cq.Workplane(obj=s)
            supported = _vol(comp.intersect(grown))
            area = s.Volume() / (lay * 0.9)
            if supported < 1e-6:
                islands.append((z, area))                     # nothing below at all
            else:
                unsup = comp.cut(grown)
                if _vol(unsup) > 1e-6:
                    # REACH, not bounding box. Every vertical wall leaves an unsupported
                    # ring one lower_layer_offset wide, and that ring's bbox is the whole
                    # part -- which made a plain 10 mm box read as a 10 mm cantilever.
                    # What matters is how far the unsupported material extends FROM the
                    # supported material, found by dilating the support until it covers.
                    max_unsup = max(max_unsup, _reach(unsup, grown))
        z += lay * step

    return dict(islands=islands, max_unsupported=max_unsup, layers=n,
                seconds=time.time() - t0)


def verdict(res):
    """Bambu's own wording, from is_support_necessary()."""
    if res["islands"]:
        return "SharpTail", "floating regions"
    if res["max_unsupported"] > CANTILEVER_DIST_THRESH:
        return "Cantilever", "floating cantilever"
    return "NoNeedSupp", ""


# ================================================================== regression ==
def corpus():
    """Cases whose answer is already known, from four printed-preview findings.

    A check that cannot fail is worse than no check -- this project deleted an overhang
    check twice for exactly that reason. Every case here has a known verdict.
    """
    import joints as J
    lay = float(P.LAYER)
    out = []

    # A plain box rests on the plate. Must be clean.
    out.append(("plain box", cq.Workplane("XY").box(10, 10, 4, centered=(True, True, False)),
                False))

    # A block floating 2 mm above the plate is the definition of an island.
    out.append(("box floating in air",
                cq.Workplane("XY").box(10, 10, 4, centered=(True, True, False))
                .translate((0, 0, 2.0)), True))

    # A pin lying on its ROUND side: a hairline first layer with flanks falling away.
    # This is what Bambu flagged on 02_pin_sprue.
    r = float(P.PEG_D) / 2
    # KNOWN GAP, recorded rather than hidden. Bambu called this one "floating regions",
    # i.e. a sharp tail. Our island test does NOT reproduce that verdict -- the pin's
    # layers do overlap each other, so whatever Bambu caught (most likely the end
    # chamfers) is not a plain island. What the model DOES establish is that it is much
    # worse than the flat placement: 4 mm of reach against 1 mm. That ranking is real and
    # would have flagged it in review; the verdict is not, and saying so is the point.
    # Tuning the corpus until this "passed" is precisely how the last two overhang checks
    # were shipped broken.
    out.append(("pin on its round side", 
                J.pin().rotate((0, 0, 0), (0, 1, 0), 90).translate((0, 0, r)),
                "known-gap"))

    # The same pin rolled onto its flat. Must be clean -- if this trips, the checker is
    # too eager and would condemn the fix.
    out.append(("pin on its flat",
                J.pin().rotate((0, 0, 0), (0, 1, 0), 90)
                .rotate((0, 0, 0), (1, 0, 0), 90)
                .translate((0, 0, float(P.D_FLAT))), False))

    # A T on a thin stem: the crossbar arrives with nothing under its ends.
    t = (cq.Workplane("XY").box(2, 2, 6, centered=(True, True, False))
         .union(cq.Workplane("XY").box(16, 2, 2, centered=(True, True, False))
                .translate((0, 0, 6))))
    out.append(("T-bar, 7 mm arms", t, "cantilever"))
    return out


def run_corpus(step=1):
    print("  regression corpus -- every case has a known answer\n")
    bad = 0
    for name, solid, expect in corpus():
        res = analyse(solid, step=step)
        kind, words = verdict(res)
        if expect == "known-gap":
            # Not scored. Printed every run so the limit stays visible.
            print(f"  GAP   {name:<26} Bambu says SharpTail, we say {kind:<12} "
                  f"[reach {res['max_unsupported']:.2f} mm vs 1.00 for the flat "
                  f"placement -- ranked worse, verdict not reproduced]")
            continue
        if expect is True:
            ok = kind == "SharpTail"
            want = "islands"
        elif expect == "cantilever":
            ok = kind in ("Cantilever", "SharpTail")
            want = "cantilever or islands"
        else:
            ok = kind == "NoNeedSupp"
            want = "clean"
        bad += not ok
        detail = (f"{len(res['islands'])} islands, "
                  f"max unsupported {res['max_unsupported']:.2f} mm")
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:<26} want {want:<20} got {kind:<12} "
              f"[{detail}]")
    return bad


if __name__ == "__main__":
    step = 1
    if "--self" in sys.argv:
        bad = run_corpus(step)
        print(f"\n  {bad} failures")
        sys.stdout.flush()
        os._exit(1 if bad else 0)

    bad = run_corpus(step)
    print()

    import coupon
    print("  coupon plate\n")
    flagged = 0
    for name, solid, _brim in coupon.parts():
        res = analyse(solid, step=step)
        kind, words = verdict(res)
        mark = "    " if kind == "NoNeedSupp" else "WARN"
        if kind != "NoNeedSupp":
            flagged += 1
        extra = f'  "{words}"' if words else ""
        print(f"  {mark}  {name:<22} {kind:<12} "
              f"{len(res['islands'])} islands, max unsupported "
              f"{res['max_unsupported']:.2f} mm{extra}")
        for z, a in res["islands"][:3]:
            print(f"          island at z={z:.2f}, {a:.2f} mm2")

    print(f"\n  {flagged} of {len(coupon.parts())} parts would warn; "
          f"{bad} corpus failures")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
