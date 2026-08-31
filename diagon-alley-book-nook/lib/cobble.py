"""Irregular cobblestone paving with real geometry, camber and perspective scaling."""
import math
import cadquery as cq
import params as P
from lib.util import rng


def cobble_field(depth, half_width_fn, tag="cobble", relief_fn=None, size_fn=None,
                 base_fn=None):
    """Stones fill y in (0..depth), x in (-hw(y)..hw(y)).

    Each stone is an irregular convex polygon inscribed in a jittered grid cell, so
    joints wander like real setts instead of forming a visible grid.
    """
    r = rng(tag)
    sz = size_fn or (lambda y: P.COBBLE_SIZE_FRONT * P.persp(y))
    rel = relief_fn or (lambda y: P.COBBLESTONE_RELIEF * (0.55 + 0.45 * P.persp(y)))
    # Each stone's base follows the road camber. Without this the stones sit on one
    # flat plane while the deck beneath them is crowned, so every stone near the
    # kerbs floats clear of the deck -- 161 loose fragments in the first floor build.
    bas = base_fn or (lambda x, y: 0.0)

    buckets = {}
    y = 1.0
    row = 0
    while y < depth:
        cell = sz(y)
        hw = half_width_fn(y) - 1.0
        stagger = (cell * 0.5) if row % 2 else 0.0
        x = -hw + stagger + r.uniform(-0.6, 0.6)
        while x < hw:
            w = cell * r.uniform(0.78, 1.0)
            h = cell * r.uniform(0.62, 0.88)
            cx, cy = x + w / 2, y + h / 2
            if abs(cx) + w / 2 < hw:
                pts = _stone_polygon(r, w - P.COBBLE_JOINT, h - P.COBBLE_JOINT)
                key = (round(rel(cy), 2), round(bas(cx, cy), 2))
                buckets.setdefault(key, []).append([(cx + px, cy + py) for px, py in pts])
            x += w + P.COBBLE_JOINT
        y += h + P.COBBLE_JOINT
        row += 1

    out = None
    for (d, base), polys in buckets.items():
        wp = cq.Workplane("XY")
        made = 0
        for poly in polys:
            try:
                wp = wp.polyline(poly).close()
                made += 1
            except Exception:
                pass
        if not made:
            continue
        try:
            sol = wp.extrude(d + 0.6).translate((0, 0, base - 0.6))
        except Exception:
            continue
        out = sol if out is None else out.union(sol)
    return out


def _stone_polygon(r, w, h, n=None):
    """A convex-ish 5-7 sided stone."""
    n = n or r.choice([5, 5, 6, 6, 7])
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-0.16, 0.16)
        pts.append((math.cos(a) * w / 2 * r.uniform(0.86, 1.0),
                    math.sin(a) * h / 2 * r.uniform(0.86, 1.0)))
    return pts


def camber_solid(depth, half_width_fn, crown=None, steps=14):
    """A gently crowned road surface: high at the centreline, falling to the gutters."""
    crown = P.CAMBER if crown is None else crown
    hw0 = half_width_fn(0.0)
    prof = []
    for i in range(steps + 1):
        t = -1.0 + 2.0 * i / steps
        prof.append((t * hw0, crown * (1 - t * t)))
    # An XZ workplane has normal -Y, so a positive extrude would push the camber to
    # NEGATIVE y, clear of the deck it is supposed to crown.
    # the whole profile, not prof[1:] -- polyline() ignores the current point
    wp = cq.Workplane("XZ").polyline(prof).close()
    return wp.extrude(-depth)
