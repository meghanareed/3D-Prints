"""Printable brick relief.

All brick faces for a wall are collected as profiles and extruded in ONE operation,
then fused to the plate in a single boolean. Doing it brick-by-brick would be a few
hundred sequential fuses; this way a full wall face takes about a second.
"""
import cadquery as cq
import params as P
from lib.util import rng


def brick_field(length, height, tag, scale_fn=None, y0=0.0,
                openings=(), broken_edge=None):
    """Return a Workplane of brick relief occupying (0..length) x (0..height).

    length     runs along +X and maps to scene depth, so scale_fn(x) drives perspective
    openings   list of (x0, z0, x1, z1) rectangles to keep clear (windows, doors)
    broken_edge callable(z) -> x  ; bricks whose centre is left of it are dropped,
               giving a torn wall that breaks along mortar lines
    """
    r = rng(tag)
    sf = scale_fn or (lambda x: 1.0)
    solids, worn, z = [], [], 0.0
    course = 0
    while z < height:
        s = sf(z * 0 + max(0.0, min(length, 0.0)))  # course height uses mid-length scale
        s = sf(length * 0.5)
        bh = P.BRICK_HEIGHT_FRONT * s
        if z + bh > height:
            bh = height - z
            if bh < 1.2:
                break
        x = -P.BRICK_LENGTH_FRONT * (0.5 if course % 2 else 0.0) * sf(0.0)
        x += r.uniform(-1.0, 1.0)
        while x < length:
            sx = sf(max(0.0, min(length, x)))
            bl = P.BRICK_LENGTH_FRONT * sx * r.uniform(0.86, 1.0)
            x0, x1 = max(0.0, x), min(length, x + bl)
            if x1 - x0 > 1.5:
                cx, cz = (x0 + x1) / 2, z + bh / 2
                keep = True
                if broken_edge is not None and cx < broken_edge(cz):
                    keep = False
                for (ax0, az0, ax1, az1) in openings:
                    if ax0 - 0.6 < cx < ax1 + 0.6 and az0 - 0.6 < cz < az1 + 0.6:
                        keep = False
                        break
                if keep and r.random() > P.BRICK_MISSING_FRAC:
                    rec = r.random() < P.BRICK_WORN_FRAC
                    jitter = r.uniform(-0.12, 0.12)
                    d = (P.BRICK_RELIEF * 0.35) if rec else (P.BRICK_RELIEF + jitter)
                    d = max(0.25, d * (0.75 + 0.25 * sx))
                    (worn if rec else solids).append(
                        (x0 + P.MORTAR_GAP * 0.5, z + P.MORTAR_GAP * 0.35,
                         x1 - P.MORTAR_GAP * 0.5, z + bh - P.MORTAR_GAP * 0.35, d))
            x += bl + P.MORTAR_GAP * sx
        z += bh + P.MORTAR_GAP * sf(length * 0.5)
        course += 1

    out = None
    for group in (solids, worn):
        if not group:
            continue
        # bucket by depth so each depth is one extrusion
        buckets = {}
        for (a, b, c, d, dep) in group:
            buckets.setdefault(round(dep, 2), []).append((a, b, c, d))
        for dep, rects in buckets.items():
            wp = cq.Workplane("XY")
            for (a, b, c, d) in rects:
                wp = wp.moveTo((a + c) / 2, (b + d) / 2).rect(c - a, d - b)
            try:
                sol = wp.extrude(dep)
            except Exception:
                continue
            out = sol if out is None else out.union(sol)
    return out


def quoin_stack(height, block_w=9.0, block_h=8.0, depth=1.0, tag="quoin", back=1.0):
    """Alternating corner stones. They sit on a thin backing plate: as free-standing
    blocks with a 0.7 mm gap between courses, the strip was eight separate solids."""
    r = rng(tag)
    wp, z, alt, n = cq.Workplane("XY"), 0.0, 0, 0
    while z + block_h <= height:
        w = block_w if alt % 2 == 0 else block_w * 0.62
        wp = wp.moveTo(w / 2, z + block_h / 2).rect(w - 0.8, block_h - 0.8)
        z += block_h + 0.7
        alt += 1
        n += 1
    if not n:
        return None
    plate = cq.Workplane("XY").box(block_w * 0.62, z, back,
                                   centered=(False, False, False))
    return plate.union(wp.extrude(depth + back))


def stone_band(length, thickness=3.0, depth=1.4):
    """A continuous string course / plinth band."""
    return cq.Workplane("XY").box(length, thickness, depth, centered=(False, False, False))
