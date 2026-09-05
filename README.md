# 3D-Prints

Models designed for **one specific machine**, and the measured facts about that machine.

Everything below the first section applies to **any** model in this repo, not just the
current project. It exists because the single most expensive mistake made here was a
dimension that was guessed, never printed, and then built on 119 times. Start a new model
from these numbers rather than from a fresh guess.

---

## The machine

| | |
|---|---|
| Printer | **Bambu Lab P2S** |
| Nozzle | **0.4 mm** |
| Material | **PLA** |
| Layer height | **0.20 mm** |
| Build volume | **256 × 256 × 256 mm** |
| Walls / infill | 2 perimeters, 15 % sparse |
| Slicer | Bambu Studio (profile vendored per project) |

A Bambu project 3MF is only recognised as a *project* — rather than loose geometry — if
`<metadata name="Application">` starts with `BambuStudio-`. Get that wrong and the file
still opens, but **every setting in it is silently discarded** and the slicer uses its own
defaults. It reports this as "The 3mf file has invalid config, load geometry data only",
which does not sound like "your brim and support settings were thrown away".

---

## What has been measured on it

These came off printed parts and calipers, not from a datasheet. They cost roughly 70 g of
filament and several wasted plates. They are machine facts, so they carry across projects.

| | | |
|---|---|---|
| **Fit clearance** | **0.30 mm per side, and glue it** | Seven identical sockets cut to one number: three held a peg, four dropped it. The scatter between one socket and the next is wider than the whole 0.20–0.45 range, so **no nominal clearance gives a repeatable press fit** at small scale. Locating features locate; adhesive retains. |
| **XY repeatability** | ±0.20 mm | Any fit that depends on a dimension tighter than this is a coin toss, not a joint. |
| **Hole shrinkage** | 0.1–0.3 mm per side, undersize | Normal, not the bad case. Outer dimensions run 0.05–0.15 mm large. |
| **Internal corner radius** | **≈ 0.21 mm** | Half the 0.42 mm line width. A round nozzle *cannot* cut a sharp internal corner, so a square peg binds on the diagonal of a square socket long before the flats meet. Proven on a coupon: a square bore cut 0.05 mm **looser** per side still would not seat, while the round one did. |
| **Minimum dependable feature** | 1.2 mm thick × 2.0 mm long | Below this it will not survive handling. |
| **Minimum wall** | 0.84 mm | Two perimeters at 0.42. Use 1.2–1.6 mm if it is structural. |
| **Crush ribs** | **Do not** | Printed twice. On one peg the joint became permanent; on a pair it would not assemble at all. A joint you can only make once, or not at all, is not a joint. |
| **Raised text** | stroke ≥ 0.5 mm | Stroke is the real limit, not glyph height. A bold serif stem is ≈0.12 of glyph size, which is where "3.5 mm minimum" comes from **for that face** — a fatter face goes smaller, a finer one cannot. |
| **Elephant foot** | 0.15 mm, with hole compensation **0** | Every socket mouth gets *more* material and nothing corrects it. Note this is already baked into the 0.30 clearance above, because that was measured on real printed sockets — do not compensate for it a second time. |

### Design rules that follow

1. **Every mating feature is round, D-sectioned or chamfered.** Never mate a sharp
   external corner to an internal one.
2. **A loose pin beats an integral peg** wherever a part's good face must point up. Give
   both halves a socket and join them with a separate pin — a peg forces the part
   face-down onto the bed.
3. **Put the male feature on whichever part lets both keep their visible face up.**
   Standardise the dimensions; flip the gender per joint.
4. **Cone the blind end of every bore**, so a downward-facing socket is self-supporting and
   the pin gets a positive depth stop.
5. **Make the socket deeper than the peg is long**, so a part seats on its face and never
   bottoms out on a peg tip.
6. **Fewer, larger parts.** A part earns separation only if it needs a different print
   orientation, a different filament, or a cavity that cannot be made in one piece.
   Otherwise fuse it. Assemblies as parts, yes; trim as parts, no.
7. **Supports are allowed** on large grouped parts. Banning them is what forces everything
   flat, which forces joints, which is where failures happen.

### Brims

| | |
|---|---|
| Type / width | `outer_only`, 5 mm. The profile ships `auto_brim`; **override it** — Auto gave a 15 mm² plaque no brim and it came off the bed |
| Set it **per object** | Bambu keeps `brim_type` per object in `Metadata/model_settings.config`. So do support settings — they are all `PrintObjectConfig` |
| **Plate spacing** | **2 × brim + 1 = 11 mm.** At 6 mm, neighbouring brims merged and 22 of 64 parts fused into one raft. A raft that peels takes every part with it |
| Never brim a sprue | Or a comb, or anything with internal gaps. A brim floods 4 mm channels and tears the parts off on removal. No area-and-slenderness heuristic can see that — use an explicit override |

---

## Toolchain

CadQuery, on the Python already installed. No second interpreter needed — `cadquery-ocp`
publishes a `cp314` wheel.

```powershell
cd <project>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pin the versions. `cp314` support is recent, and `cadquery-ocp` declares
`requires_python <3.15`.

**Known quirk — any script that imports `cadquery` needs `os._exit`.** OCCT, the C++
kernel underneath, crashes during interpreter teardown on this build. It happens *after*
all work is done and all output is flushed, but before Python hands back its exit code, so
the script does its job correctly and then reports a meaningless status (`139`/`127`
rather than `0`). It fires on a bare `import cadquery` too, so it is nothing to do with
the geometry. Anything gating on `python foo.py && ...` will read success as failure.

```python
sys.stdout.flush()          # os._exit does not flush
sys.stderr.flush()
os._exit(1 if failures else 0)
```

Scripts that only import `params` are unaffected.

---

## Projects

### [`diagon-alley-book-nook/`](diagon-alley-book-nook/)

A parametric illuminated book nook — a narrow crooked wizarding shopping lane, **8 × 10.5
× 12 in** (203 × 267 × 305 mm), with forced perspective, hidden LED wiring and a removable
outer brick skin for access.

| | |
|---|---|
| [`PLAN.md`](diagon-alley-book-nook/PLAN.md) | the live implementation plan — architecture, decisions, and the research register |
| [`SPEC.md`](diagon-alley-book-nook/SPEC.md) | phases, rules and the exit test for each |
| [`params.py`](diagon-alley-book-nook/params.py) | **every dimension, with its provenance.** Machine values are read from the slicer profile rather than retyped |
| [`checks.py`](diagon-alley-book-nook/checks.py) | the check suite. Registry-driven, printer-aware, written before the geometry |
| [`archive/`](diagon-alley-book-nook/archive/) | two previous attempts — the record and the raw material, **not** the starting point |

Two attempts were made at building this as a 182-part kit. Both ended with a bench of
parts that would not go together. The reasons are written down rather than forgotten:

* [`07_RETROSPECTIVE.md`](diagon-alley-book-nook/archive/docs/07_RETROSPECTIVE.md) — what
  went wrong, both times
* [`08_JOINT_DESIGN.md`](diagon-alley-book-nook/archive/docs/08_JOINT_DESIGN.md) — why a
  round nozzle cannot cut a square socket
* [`09_COUPON_RESULTS.md`](diagon-alley-book-nook/archive/docs/09_COUPON_RESULTS.md) — the
  two printed coupons that settled the joint

**`params.py` is the authority, not this file.** The numbers above are a human summary;
the machine-readable versions carry their provenance — `MACHINE` (read from the slicer
profile at import), `MEASURED` (off a printed part), `CHOSEN` (a design decision) or
`ASSUMED` (not validated yet, with the research item that settles it). Run
`python params.py` for the annotated dump and `python checks.py` for the guards.

The suite never reports "0 failures" as though it meant "this will print". It prints what
it did **not** check, every run.
