# 3D-Prints

Models designed for **one specific machine**, and the hard-won facts about that machine.

**One folder per project.** This file is not about any of them — it is the printer, the
measurements taken on it, and the rules that came out of getting things wrong. Read it
before starting a new model, so the next project does not re-buy lessons this one already
paid for in filament.

| | |
|---|---|
| Starting a **new** model | Read this file top to bottom first. Everything in it applies to anything printed here |
| Working on the **book nook** | [`diagon-alley-book-nook/`](diagon-alley-book-nook/) — its `PLAN.md` is the live document |

Every rule below exists because breaking it cost a print. Where a number came off a
printed part rather than a datasheet, it says so.

---

# Part 1 — The machine

| | |
|---|---|
| Printer | **Bambu Lab P2S** |
| Nozzle | **0.4 mm** |
| Material | **PLA** |
| Layer height | **0.20 mm**, first layer 0.20 |
| Build volume | **256 × 256 × 256 mm** |
| Line width | 0.42 nominal, 0.50 first layer |
| Walls / infill | 2 perimeters, 15 % sparse |
| Elephant foot | 0.15 mm, with `xy_hole_compensation` **0** |

## What has been measured on it

Off printed parts and calipers, not from a datasheet. Roughly 70 g of filament and
several wasted plates bought this table, and it carries across projects.

| | | |
|---|---|---|
| **Fit clearance** | **0.30 mm per side, and glue it** | Seven identical sockets cut to one number: three held a peg, four dropped it. The scatter between one socket and the next is wider than the whole 0.20–0.45 range, so **no nominal clearance gives a repeatable press fit** at small scale. Locating features locate; adhesive retains |
| **XY repeatability** | ±0.20 mm | Any fit depending on a dimension tighter than this is a coin toss, not a joint |
| **Hole shrinkage** | 0.1–0.3 mm per side, undersize | Normal, not the bad case. Outer dimensions run 0.05–0.15 mm large |
| **Internal corner radius** | **≈ 0.21 mm** | Half the line width. A round nozzle *cannot* cut a sharp internal corner, so a square peg binds on the diagonal of a square socket long before the flats meet. Proven on a coupon: a square bore cut 0.05 mm **looser** per side still would not seat while the round one did |
| **Minimum feature** | 1.2 mm thick × 2.0 mm long | Below this it will not survive handling |
| **Minimum wall** | 0.84 mm | Two perimeters. Use 1.2–1.6 mm if structural |
| **Crush ribs** | **Do not** | Printed twice. Permanent on one peg, impossible to assemble on two |
| **Raised text** | stroke ≥ 0.5 mm | Stroke is the limit, not glyph height. A bold serif stem is ≈0.12 of glyph size, which is where "3.5 mm minimum" comes from *for that face* — a fatter face goes smaller, a finer one cannot |

**A caution about compensating twice.** Elephant foot adds material at a socket mouth and
hole compensation is 0, so nothing corrects it — but the 0.30 clearance was measured on
*real printed sockets against real printed pegs*, so that effect is **already inside it**.
Adding a second correction opens every joint too far.

---

# Part 2 — Design rules

1. **Every mating feature is round, D-sectioned or chamfered.** Never mate a sharp
   external corner to an internal one.
2. **Put the male feature on whichever part lets both keep their good face up.**
   Standardise the dimensions; flip the gender per joint. A sign must print lettering-up,
   so its socket faces the plate and the *wall* carries the peg. A part that prints
   standing takes sockets on both halves and a loose pin.
3. **A loose pin frees both halves.** An integral peg forces its part face-down.
4. **Cone the blind end of every bore** (≈45° included), so a downward-facing socket is
   self-supporting and the male gets a positive depth stop.
5. **Size the part for bore + cone, not bore alone.** The cone adds real height; sized to
   the bore, it punches out of the far face and the blind end is a through hole.
6. **A chamfer must follow the bore's own shape.** A *round* lead-in around a
   *D-sectioned* bore undercuts the flat and leaves it cantilevered.
7. **Make the socket deeper than the peg is long**, so a part seats on its face and never
   bottoms out on a peg tip.
8. **Lay a round part on a flat if it has one.** A cylinder on its round side touches the
   bed along a hairline; on a flat it sits on a band and prints without support.
9. **Fewer, larger parts.** A part earns separation only if it needs a different print
   orientation, a different filament, or a cavity that cannot be made in one piece.
   Assemblies as parts, yes; trim as parts, no.
10. **Supports are allowed** on large grouped parts. Banning them forces everything flat,
    which forces joints, and joints are where failures happen.
11. **Never let supports reach a mating bore.** Support in a socket does not scar a
    cosmetic surface, it destroys the fit.

## Brims

| | |
|---|---|
| Type / width | `outer_only`, 5 mm. The profile ships `auto_brim` — **override it.** Auto gave a 15 mm² plaque no brim and it came off the bed |
| Set it **per object** | Bambu keeps `brim_type` per object; so do support settings. They are all `PrintObjectConfig` |
| **Plate spacing** | **2 × brim + 1 = 11 mm.** At 6 mm, neighbouring brims merged and **22 of 64 parts fused into one raft**. A raft that peels takes every part with it |
| Never brim a sprue | Or a comb, or anything with internal gaps. A brim floods 4 mm channels and tears the parts off on removal. No area-and-slenderness heuristic can see that — use an explicit override |

---

# Part 3 — The slicer

## Two things that fail *silently*

**A 3MF is only a project if `<metadata name="Application">` starts with `BambuStudio-`.**
Get it wrong and the file still opens — it discards every setting and reports "load
geometry data only", which does not sound like *your brim is gone*.

**Per-object settings must be written as OVERRIDES ONLY.** Bambu writes only the keys
that *differ* from the plate default, serialising booleans and numbers as strings
(`"1"`, `"32"`). Write a full config onto every object and each one pins every value —
the plate profile stops meaning anything.

```xml
<object id="2">
  <metadata key="name"                    value="..."/>
  <metadata key="brim_type"               value="outer_only"/>
  <metadata key="enable_support"          value="1"/>
  <metadata key="support_threshold_angle" value="32"/>
  <part id="1" subtype="normal_part"> ... </part>
</object>
```

## What Bambu's warnings actually mean

Read out of `BambuStudio/src/libslic3r`, not inferred:

| Warning | Criterion |
|---|---|
| **"floating regions"** (`SharpTail`) | A region that does **not overlap the layer below**, once that layer is **eroded** by `layer_height / tan(threshold + 1)` — **0.333 mm** at 0.2 mm layers and a 30° threshold |
| **"floating cantilever"** (`Cantilever`) | An overhang contour that is totally floating and extends more than **6 mm** from its support |

**This is an island test, not an overhang-angle test.** A 20° overhang is fine if it is
*attached*; a perfectly vertical wall is a sharp tail if it *begins in mid-air*. Reasoning
in degrees will send you the wrong way — it sent this project the wrong way four times.

**Keep clear of the threshold, don't sit on it.** A cone at exactly 30° against a 30°
threshold was flagged on every part; 22.5° was not. Borderline is the worst place to be.

## Open the slicer. It is a review step, not a formality

On one plate, the preview found **five** defects that a suite of 19 joint tests and 22
coupon tests had passed: a blind cone punching through a top face, a lead-in chamfer
cutting nothing but air, pins lying on their round side, a round chamfer undercutting a D
flat, and a cone sitting exactly on the support threshold.

`diagon-alley-book-nook/preflight.py` implements the criteria above and has a regression
corpus, but it runs CAD booleans per layer and takes **minutes per plate** — too slow to
gate on. Opening the file in Bambu is faster and is what has actually been finding things.

---

# Part 4 — Writing the code

CadQuery, on the Python already installed — `cadquery-ocp` publishes a `cp314` wheel.

```powershell
cd <project>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pin the versions; `cadquery-ocp` declares `requires_python <3.15`.

**Any script that imports `cadquery` needs `os._exit`.** OCCT crashes during interpreter
teardown — after all work is done and output flushed, but before Python hands back its
exit code, so the script does its job and then reports `139`/`127` instead of `0`.
Anything gating on `python foo.py && ...` reads success as failure.

```python
sys.stdout.flush()          # os._exit does not flush
sys.stderr.flush()
os._exit(1 if failures else 0)
```

## Rules for the model code itself

Each of these came from a defect that shipped.

* **Every parameter carries its provenance** — `MACHINE` (read from the slicer profile at
  import, never retyped), `MEASURED`, `CHOSEN`, or `ASSUMED` with the item that settles
  it. The most expensive mistake in this repo was a clearance that sat at a guess while
  119 parts were built on it, and nothing in the code said it was a guess.
* **Tangency is not contact.** Two solids that merely touch stay two solids. It has split
  parts here at least six times: pegs sized exactly to the surface they stand on, text
  extruded from exactly a top face, pins butted against a sprue spine. Always overlap.
* **Test the physical motion, not the numbers.** Build both halves, apply the real
  transform, measure the interference. A check comparing the numbers both halves were
  built from cannot see a mirrored flat, and that bug is invisible any other way.
* **Measure, do not derive** — where a feature lands after a rotation, which side of a
  body a point falls on, text extents. Every derivation attempted here was wrong.
* **Make sure the test can fail.** Prove a check on a known-bad input *and* a known-good
  one. Two overhang checks were deleted from this repo for passing a bad part and failing
  a good one; both had been tuned until they went green.
* **The registry is a list the runner iterates**, with a meta-check that every `check_*`
  is in it. A suite here defined 22 checks and ran 21 for months, while the missing one
  was documented as passing.
* **Never report "0 failures" as "it will print."** Say what was checked and what was
  not. Print the not-checked list every run.
* **Recompute derived geometry, don't cache the bounding box.** Stamping a second label
  read `zmax` again — after the first label had made the part taller — and placed it in
  mid-air.

---

# Projects

### [`diagon-alley-book-nook/`](diagon-alley-book-nook/)

A parametric illuminated book nook — a narrow crooked wizarding shopping lane,
**8 × 10.5 × 12 in**, with forced perspective, hidden LED wiring and a removable outer
brick skin for access.

| | |
|---|---|
| [`PLAN.md`](diagon-alley-book-nook/PLAN.md) | the live document — architecture, decisions, research register |
| [`SPEC.md`](diagon-alley-book-nook/SPEC.md) | phases and the exit test for each |
| [`params.py`](diagon-alley-book-nook/params.py) | every dimension, with its provenance |
| [`checks.py`](diagon-alley-book-nook/checks.py) | the check suite — registry-driven, printer-aware |
| [`joints.py`](diagon-alley-book-nook/joints.py) | the D-pin and its socket, tested by real insertion |
| [`coupon.py`](diagon-alley-book-nook/coupon.py) · [`plate.py`](diagon-alley-book-nook/plate.py) | the test plate, and the Bambu project writer |
| [`ingest.py`](diagon-alley-book-nook/ingest.py) | read settings back out of a saved Bambu project |
| [`archive/`](diagon-alley-book-nook/archive/) | two previous attempts — the record, **not** the starting point |

Two attempts were made at building it as a 182-part kit; both ended with a bench of parts
that would not go together. The reasons are written down rather than forgotten, in
[`07_RETROSPECTIVE.md`](diagon-alley-book-nook/archive/docs/07_RETROSPECTIVE.md),
[`08_JOINT_DESIGN.md`](diagon-alley-book-nook/archive/docs/08_JOINT_DESIGN.md) and
[`09_COUPON_RESULTS.md`](diagon-alley-book-nook/archive/docs/09_COUPON_RESULTS.md).

---

**`params.py` is the authority; this file is the human summary.** Where they disagree, the
code wins — it is the one that can fail a build.
