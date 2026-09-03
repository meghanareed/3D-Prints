# 08 — Designing 3D-printed joints for a 0.4 mm nozzle

Written after the P1 mounts on this kit would not go together, and the sockets on the
printed wall came out with rounded corners rather than square ones. That observation is
the correct diagnosis and it was not in the model anywhere.

## Why a square socket is not square

A round nozzle laying a constant-width bead cannot produce a sharp internal corner. The
corner it leaves has a radius of roughly **half the extrusion width** — about **0.21 mm**
at a 0.42 mm line width on a 0.4 mm nozzle. External corners come out sharp; internal
ones do not. So a sharp-cornered peg meets a round-cornered hole and binds on the
diagonal long before the flats touch.

For P1 as drawn — a 2.5 × 2.0 mm peg into a 3.0 × 2.5 mm socket:

| bore, after the hole prints undersize | sharp peg fits? |
|---|---|
| 3.00 × 2.50 (nominal) | fits |
| 2.80 × 2.30 (0.10 mm/side under) | fits |
| 2.60 × 2.10 (0.20 mm/side under) | **binds by 0.016 mm** |
| 2.40 × 1.90 (0.30 mm/side under) | **binds by 0.158 mm** |

FDM holes print 0.1–0.3 mm undersize as a matter of course, so the middle two rows are
the normal case, not the bad case. And that is *before* the crush ribs, which by design
bring the bore in to 2.20 mm across a 2.50 mm peg.

## The number that should have stopped this

```
intended P1 interference          0.15 mm per side
printer XY repeatability          ±0.20 mm, well calibrated
```

**The fit was specified tighter than the machine's own error bar.** No amount of care in
CAD recovers that. Any joint whose function depends on a dimension smaller than the
printer's repeatability is not a joint, it is a coin toss.

The crush ribs were meant to absorb exactly this, and they cannot: each rib protrudes
0.40 mm into the bore, which is *one extrusion line*. The published minimum for a
dependable standalone feature on a 0.4 mm nozzle is **≥ 1.2 mm thick and ≥ 2.0 mm long**.
The rib is a third of that in the direction that matters.

## Rules for the next one

**Geometry**

1. **Never mate sharp external corners to internal ones.** Either round the peg's corners
   to ≥ the nozzle radius, or put **corner relief** in the socket — the CNC dogbone: a
   circle of radius ≥ nozzle/2 at each internal corner, so the corner is over-cut instead
   of filled. Cheapest fix, applies to every rectangular socket.
2. **Better: use round pegs.** A cylinder in a circular hole has no corners to bind on,
   and both features are the shapes FDM makes best. Key it with a D-flat, an offset pair,
   or two pegs of different diameters, rather than with a rectangular profile.
3. **Chamfer the lead-in on both halves**, not just the socket mouth. A 0.5 mm × 45°
   chamfer on the peg tip does more for assembly than any clearance tweak.
4. **Minimum feature size, 0.4 mm nozzle:** ≥ 1.2 mm thick, ≥ 2.0 mm long for anything
   that has to survive handling. Walls ≥ 0.8 mm (2 perimeters), ≥ 1.2–1.6 mm if
   structural.

**Fits**

5. **Slip fit:** about one extrusion width of clearance per side — **0.4 mm** on a 0.4 mm
   nozzle. Free-running: two.
6. **Press fit:** 0.1–0.3 mm of *interference*, on features large enough that 0.2 mm of
   machine error does not swamp it. At 2 mm across it does swamp it; at 8 mm across it
   does not.
7. **Snap fits:** 0.20–0.40 mm clearance between the non-locking faces. Get retention
   from a **barb with real engagement** (≥ 0.5 mm), never from friction on a small
   feature.
8. **Cantilever arms:** length/thickness ≥ 8:1, root fillet ≥ 0.5 × thickness, ≥ 1 mm
   thick at the base, and **print the beam lying in XY** — a snap arm printed up the Z
   axis breaks along its layer lines.

**Process**

9. **Print the tolerance coupon before anything depends on it**, sweeping 0.05 mm steps
   from 0.05 to 0.5, and feed the measured number back into the model. A coupon that is
   printed but whose result never reaches `params.py` has done nothing.
10. **Measure a printed peg and a printed hole with calipers** and put the difference in
    the model as a compensation term. Do not assume the nominal dimension.
11. **Scale the joint to the part.** At 1:24, with pegs 2 mm across, a drop of glue in a
    generously clearanced hole is the *engineering* answer, not the lazy one. Reserve
    press and snap fits for features big enough to hold tolerance.

## What this kit should have used

For a 2.5 mm mount at this scale: a **Ø2.0 mm round peg into a Ø2.6 mm hole** (0.3 mm
clearance per side), chamfered lead-in, keyed by using two pegs at unequal spacing, and
glued. No corners to bind, no feature below the machine's resolution, no dependence on
an interference smaller than the printer's error bar. It would have gone together on the
first print.

## Sources

* [3DVerkstan — Designing for 3D printing](https://support.3dverkstan.se/article/38-designing-for-3d-printing)
* [Hackaday — nozzle diameter and internal corner radius](https://hackaday.com/2022/07/29/go-big-or-go-home-0-6-mm-nozzles-are-the-future/)
* [Protolabs Network — How to design snap-fit joints for 3D printing](https://www.hubs.com/knowledge-base/how-design-snap-fit-joints-3d-printing/)
* [Formlabs — Designing 3D printed snap-fit enclosures](https://formlabs.com/blog/designing-3d-printed-snap-fit-enclosures/)
* [3DPut — Tolerances and fit clearance for moving parts](https://3dput.com/complete-guide-to-3d-printing-tolerances-and-fit-clearance-for-moving-parts-2/)
* [Creative3DP — Press-fit tolerances for 3D printing](https://tools.creative3dp.com/blog/press-fit-tolerances-3d-printing/)
* [Voxel Magic — Minimum requirements for 3D printable designs in PLA/PETG/ABS](https://voxel-magic.com/minimum-requirements-for-making-your-design-3d-printable-in-pla-petg-and-abs)
