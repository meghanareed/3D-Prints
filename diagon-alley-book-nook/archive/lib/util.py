"""Shared helpers: deterministic RNG, safe chamfers, print-orientation records."""
import math, random
import cadquery as cq
import params as P


def rng(tag):
    """Deterministic per-feature RNG so the same seed always yields the same STLs."""
    return random.Random(f"{P.RANDOM_SEED}:{tag}")


def try_chamfer(wp, selector, amount):
    """Chamfer that degrades gracefully -- OCCT refuses some edge sets and a failed
    cosmetic chamfer must never abort a build."""
    try:
        return wp.edges(selector).chamfer(amount)
    except Exception:
        return wp


def try_fillet(wp, selector, amount):
    try:
        return wp.edges(selector).fillet(amount)
    except Exception:
        return wp


def slab(l, w, h):
    """Axis-aligned slab with its min corner at the origin."""
    return cq.Workplane("XY").box(l, w, h, centered=(False, False, False))


def bbox_of(shape):
    bb = shape.val().BoundingBox() if isinstance(shape, cq.Workplane) else shape.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def fits_bed(shape, margin=3.0):
    x, y, z = bbox_of(shape)
    fp = sorted([x, y])
    bed = sorted([P.BED_X - margin, P.BED_Y - margin])
    return fp[0] <= bed[0] and fp[1] <= bed[1] and z <= P.BED_Z - margin


def taper_prism(l, w_front, w_rear, h):
    """Flat trapezoidal prism: length along Y, width along X, tapering front to rear."""
    return (cq.Workplane("XY")
            .polyline([(-w_front / 2, 0), (w_front / 2, 0),
                       (w_rear / 2, l), (-w_rear / 2, l)])
            .close().extrude(h))


def emboss_text(wp, txt, size, depth, face=">Z", centre=(0, 0), bold=True):
    """Raised lettering. Returns wp unchanged if text is disabled or the font fails."""
    if not P.RENDER_TEXT or not txt:
        return wp
    try:
        return (wp.faces(face).workplane(centerOption="CenterOfBoundBox")
                  .center(*centre)
                  .text(txt, size, depth, font=P.TEXT_FONT,
                        kind="bold" if bold else "regular", combine=True))
    except Exception:
        return wp


def engrave_id(wp, ident, face="<Z", size=4.0):
    """Sink the part ID into a hidden face. Silent no-op if it will not cut."""
    try:
        return (wp.faces(face).workplane(centerOption="CenterOfBoundBox")
                  .text(ident, size, -0.4, font="DejaVu Sans", kind="bold", combine="cut"))
    except Exception:
        return wp


def compound(items):
    """Collect many disjoint solids into ONE compound.

    Accumulating with repeated .union() is O(n^2) in OCCT -- 60 sockets took 29 s that
    way and 0.4 s this way. Every batched cut/add in this project goes through here.
    """
    import cadquery as cq
    shapes = []
    for it in items:
        if it is None:
            continue
        if isinstance(it, cq.Workplane):
            shapes.extend(s for s in it.vals() if s is not None)
        else:
            shapes.append(it)
    if not shapes:
        return None
    if len(shapes) == 1:
        return cq.Workplane("XY").newObject([shapes[0]])
    # ONE multi-argument fuse. A plain Compound is invalid as a boolean argument when
    # any two members touch or overlap, and sequential .union() is O(n^2).
    fused = shapes[0].fuse(*shapes[1:])
    try:
        fused = fused.clean()
    except Exception:
        pass
    return cq.Workplane("XY").newObject([fused])


def batch_cut(base, items):
    c = compound(items)
    return base if c is None else base.cut(c)


def batch_add(base, items):
    c = compound(items)
    return base if c is None else base.union(c)


def keep_largest(wp, name="part", warn_frac=0.01, verbose=True):
    """Keep only the main body of a part and drop detached fragments.

    Fragments here are almost always crush ribs at a mount whose neighbouring material
    was removed by an adjacent aperture -- a rib with no wall to grip is simply not
    wanted. The guard matters though: if the discarded volume is more than warn_frac of
    the part, something real has been cut in half and you want to know.
    """
    import cadquery as cq
    solids = wp.val().Solids()
    if len(solids) <= 1:
        return wp
    solids = sorted(solids, key=lambda s: -s.Volume())
    dropped = sum(s.Volume() for s in solids[1:])
    total = dropped + solids[0].Volume()
    if verbose and dropped / total > warn_frac:
        print(f"  !! {name}: dropped {len(solids)-1} fragments = "
              f"{100*dropped/total:.2f}% of volume -- check this part")
    return cq.Workplane("XY").newObject([solids[0]])
