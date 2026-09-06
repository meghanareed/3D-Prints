# Inhaler fidget clicker

A life-size faux metered-dose inhaler whose canister is the button. Pressing it actuates a
hidden MX-compatible keyboard switch. Raised two-colour lettering reads **IT AIN'T EASY /
BEING WHEEZY**.

Not a medical device, and deliberately not capable of being one: the mouthpiece cavity is
blind, there is no airway and nothing accepts a real canister. `checks.py` asserts that
rather than trusting it.

| | |
|---|---|
| Spec | [`../Inhaler_Fidget_Clicker_3D_Print_Spec.md`](../Inhaler_Fidget_Clicker_3D_Print_Spec.md) |
| Printer rules | [`../README.md`](../README.md) — **read it first**, everything in it applies here |
| Reference model | [`ref/blank_clicker_sample.3mf`](ref/) — a third-party clicker that works |
| Status | Prototypes A and B build and slice. Parts A and B are not modelled yet — see [What is not built](#what-is-not-built) |

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe checks.py -v      # 17 checks
.\.venv\Scripts\python.exe plate.py --write  # out/plate_A1, plate_A2, plate_B
```

**Blocked on one thing: a real MX switch.** Seven parameters carry the whole vertical
stack and every one of them is a datasheet figure or a reading off someone else's model.
Coupons and the mechanism skeleton can be printed now; nothing beyond them should be.

---

## What the sample measured

`ref/blank_clicker_sample.3mf` is *Blank Clicker Set* by Tinker Link — a two-part MX
clicker that is known to work. Its meshes were dumped and sliced by Z, and this is what
came out. It is the single most valuable thing in this folder, because it is a working
answer to the question the spec could only guess at.

| Feature | Sample | Spec proposed |
|---|---|---|
| Plate cutout | **14.00 mm** square | 14.10 nominal, sweep 13.95–14.25 |
| Plate band thickness | **1.50 mm** | 2.0–2.2 mm "switch shelf" |
| Clip relief | **+0.50 mm per side, all four sides**, over the full band | not mentioned |
| Pocket below plate | 14.00 square × **6.50 deep** | not specified |
| Stem socket | **4.17 × 1.55 mm**, 4.92 deep, blind, flared mouth | "test empirically" |
| Receiver boss | Ø5.59, Ø6.19 at the mouth | not specified |
| Cap wall | 2.28 mm | 1.6–2.0 |
| Cap guide | square skirt, **1.00 mm per side** | round, 0.30 mm per side |
| Cap crown | flat, bridging 13.4 mm | not specified |

**The finding that matters: the plate band is the retention.** The switch's clips spring
out into the relief and hook under a 1.5 mm band. Nothing is press-fitting against the
pocket walls. The spec's 2.0–2.2 mm shelf is thicker than the clips can reach past, so
building to it would give a switch that drops out — and the fit coupon it prescribes
would be sweeping the wrong dimension. `coupon.py` sweeps both.

Caveats, because this is evidence and not a measurement: the sample was printed on an
A1 mini at 0.16 mm, not a P2S at 0.20, and nobody here has held the printed part. Its
numbers carry a distinct `SAMPLE` provenance in `params.py` for exactly that reason, and
`check_sample_is_not_measured` stops them quietly becoming `MEASURED`.

---

## Where the spec and the machine disagree

Six deviations. Each one is a number the spec gives that this printer or this switch
will not accept, with what was done instead.

**1. Body depth 22 → 24 mm.** A Ø19 canister plus 2 × 0.30 clearance is a Ø19.6 bore. In
a 22 mm deep body that leaves 1.2 mm of wall front and back against the spec's own 2.2 mm
`BODY_WALL`. 24 is the smallest number that keeps the wall. This is arithmetic, not
preference — `params.sanity()` fails the build if it is put back.

**2. Travel 3.5–3.8 → 3.4 mm.** An MX switch bottoms out at 4.0. Stopping at 3.5–3.8
leaves 0.2–0.5 mm of margin on a machine whose XY error bar is ±0.20, which means some
prints would hard-stop on the switch instead of on the plastic — the exact failure the
spec's section 8 exists to prevent. 3.4 keeps 0.6 mm.

**3. The hard stop is two lugs, not a ring.** There is nowhere to put a stop ring around
the switch: the top housing is 15.6 mm square, 22.1 mm across its diagonal, and the
canister is only 19 mm wide. Nor can it be a full flange, because a bore wide enough to
swallow one does not fit across the body's depth. So the canister carries two lugs on
±X — the body's wide axis, where there is room — running in two blind slots. The slot
floor is the down stop.

**4. There is no up stop, and the slots run open to the top face.** A lug captured under
a ceiling cannot be got in past that ceiling, and a bayonet twist is not available because
the stem is already holding the canister by the time it is down. The MX stem retains the
canister, which is what an MX stem does for every keycap ever made. Cosmetically this
leaves two 5.6 mm notches in the collar rim; on a real inhaler there is a visible gap
around the canister anyway, but it is an open cosmetic question.

**5. The service panel becomes a switch carrier — and this rewrote the part split.**
An MX switch loads *downward* through its plate: the 13.9 mm below-plate body passes the
14.0 cutout and the 15.6 mm top housing lands on the band. So it cannot be dropped in
through the canister collar (22.1 diagonal against a 19.6 bore) and it cannot be pushed up
from below either (the top housing is wider than the cutout it would have to come
through). The body therefore does not own the plate band. **Part B owns it**: the switch
clips into the carrier in free air, and the loaded carrier goes into the body through a
window in the back. The alternative — splitting the band and sliding the switch in
sideways — throws away the unbroken ring that is the only thing retaining it.

**6. The lettering runs vertically, and is nearly twice the size the spec asked for.**
The book nook's plate 1 settled the text floor: **stroke ≥ 0.70 mm**, which for a bold
face means **glyphs ≥ 6 mm**, at **0.72 em per character**. Against that, the spec's
section 12 does not survive — 3.5 mm text has a 0.42 mm stem, one extrusion, the blob
end of the ladder; and `IT AIN'T EASY` at a printable 6 mm is **56.2 mm** wide against
27 mm of face. It does not fit horizontally at any size that prints.

So it runs **up** the 63 mm axis, the way a pharmacy label does, in two columns:

| | | |
|---|---|---|
| `IT AIN'T EASY` | 6.0 mm glyph | 56.2 mm of the 61 available |
| `BEING WHEEZY` | 6.5 mm glyph | 56.2 mm of the 61 available |

The sizes differ so the columns come out the same length, and enlarging the second column
is how section 12's "WHEEZY as the focal point" survives the layout. Together they stack
14.5 mm across the face, inside the 21 mm of flat between the corner radii. Coupon 03
prints them on a plaque with the real face's corner radii, so the question it answers is
the one that matters. `params.sanity()` and `check_lettering` hold all of it, and both
have been proven to fail on the spec's original numbers.

There is also a contradiction inside the spec itself. Section 12 sets `TEXT_RAISE` to
0.6 mm and computes it as three layers *at 0.20*; section 16 then recommends a 0.16 mm
layer height, at which 0.6 is 3.75 layers and an AMS colour change cannot land on a layer
boundary. This project prints at the machine's 0.20. `params.sanity()` fails if the two
ever stop agreeing.

---

## The mechanism

```
                  ╭───────╮
                  │ FAUX  │   canister, Ø19, 30 mm tall, prints rim-down
   z 63.0 ────────┤ CANI- ├──────── body top
                  │ STER  │
   z 53.0  rim ···└╌╌┬╌╌╌╌┘         10 mm of skirt engaged in the collar at rest
                 ┌──┴──┐            lug in slot, +X and -X
   z 49.6  stop ─┤ ▲   ├─           slot floor: the printed hard stop, 3.4 mm down
   z 49.2 ───────┤ │   ├──          switch housing top  (0.4 mm of daylight)
                 │[MX] │
   z 44.2 ───────┤═════├──          plate band top, 1.5 mm, clips hook under it
   z 36.2 ───────┤     ├──          pocket floor, 6.5 mm deep
                 └─────┘
```

`python params.py --stack` prints every level. Nothing above is a literal that also lives
somewhere else — `params.stack()` derives all of it, top down, and the geometry reads it.

| | |
|---|---|
| Travel | 3.40 mm, stop at 0.60 mm before the switch bottoms out |
| Click | at 2.00 mm, so 1.40 mm of overtravel past it |
| Stem engagement | 3.10 mm of cross in a 4.92 mm socket — seats on the shoulder, never bottoms out in its own socket |
| Guide | 10 mm of skirt at rest under 20 mm of exposed canister (2:1), growing to 13.4 mm at full press |
| Overall | 83 mm tall, 29 × 24 mm body |

`mech.travel_test()` presses the canister down in ten steps and measures the interference
volume against the collar and against the switch at each one. It has a negative control:
pressed 0.3 mm *past* the stop, the lug must collide, and the test fails if it does not.
A check that compares `BUTTON_TRAVEL` against `BUTTON_TRAVEL` cannot see a lug that misses
its slot.

---

## Files

| | |
|---|---|
| [`params.py`](params.py) | every dimension, with its provenance, plus `stack()` and `sanity()` |
| [`switch.py`](switch.py) | the MX interface — plate cutout, pocket, stem receiver, and a solid stand-in for the switch itself |
| [`mech.py`](mech.py) | Part C (the canister), the collar it runs in, and the travel test |
| [`coupon.py`](coupon.py) | Prototype A — the four calibration coupons, 16 tiles |
| [`checks.py`](checks.py) | the check suite: registry-driven, printer-aware, and it prints what it did **not** check every run |
| [`plate.py`](plate.py) | the Bambu project writer |
| [`ref/`](ref/) | the sample clicker, kept because it is the evidence for half of `params.py` |

Provenance is the point of `params.py`: `MACHINE` (read from the slicer profile at import,
never retyped), `MEASURED` (calipers, on this printer), `SAMPLE` (read off the reference
model), `CHOSEN` (a design decision) and `ASSUMED` (not validated — carries the R-number
that settles it). `check_no_assumed_in_critical` warns on every `ASSUMED` number the
mechanism leans on, and there are seven of them.

---

## Open questions

| | | |
|---|---|---|
| **R-1** | **Every MX switch dimension.** Housing 15.6 square, 5.0 above plate, stem cross from 3.5 to 6.9 above the housing, 4.0 travel, 2.0 actuation. All datasheet or inferred from the sample; the entire vertical stack hangs off them | calipers on an actual switch |
| **R-2** | Guide clearance 0.30/side. Only 1.5× the machine's own ±0.20 error bar, and a bore printing 0.30/side undersize would close it completely. The sample runs 1.00/side | coupon 02 |
| **R-3** | Which switch. Clicky blue is the obvious pick for a fidget, but travel and actuation force differ by type, and R-1 changes with it | buy one, then R-1 |
| **R-4** | Panel clearance 0.25 and snap-tab geometry | coupon, once Part B exists |
| **R-5** | `TEXT_FONT = "Arial Black"` is a guess, and CadQuery falls back silently when a font does not resolve. `TYPE_STEM_RATIO = 0.12` is a bold *serif* figure applied to a heavier sans, so the stroke check is conservative rather than accurate | coupon 03 |

The slicer profile in `profiles/` is vendored from the book nook next door. It is a
genuine P2S export at 0.4 mm, but re-export it from the current Bambu Studio session
before committing to a full print.

---

## Print order

Spec section 25, and it is right — do not print the full inhaler first.

1. **Prototype A — coupons.** `plate.py --write` writes `plate_A1` and `plate_A2`.
   16 swept values × **three copies** = 48 tiles, which is more than one bed holds.

   | | |
   |---|---|
   | 01, bars 1–4 | MX cutout 13.90 / 14.00 / 14.10 / 14.20 at a 1.5 mm band |
   | 01, bars 5–6 | band thickness 1.5 / 2.0 at a 14.00 cutout — the retention test |
   | 02, bars 1–4 | guide clearance 0.20 / 0.25 / 0.30 / 0.35, plus canister stubs |
   | 03 | the lettering, on a plaque with the real face's corner radii |
   | 04, bars 1–4 | stem socket width 1.45 / 1.50 / 1.55 / 1.60 |

   **Tiles are identified by countable bars, not printed numbers**, and there are three
   of everything. Both are rules 12 and 13 next door, and both were bought: three blocks
   printed with 3 mm labels came out as blobs and which clearance did what is now
   unknowable, and socket-to-socket scatter here is wider than the whole range worth
   sweeping, so one tile tells you about that tile.
2. **Prototype B — mechanism skeleton.** `plate_B.3mf`. A block carrying the collar, the
   stop and the switch mount, with no cosmetics at all. Cycle it and judge the feel.
   Spec priorities 1–3 are all things no dimension can answer.
3. **Prototype C — full single-colour body.** Needs Part A, which is not modelled yet.
4. **Prototype D — final AMS version.** Needs the lettering emitted as a separate body.

Open the 3MF in Bambu Studio before every print. Next door, one plate's preview found
five defects that a suite of 41 automated tests had passed. It is a review step, not a
formality.

---

## What is not built

Said plainly, because "no check I have written is unhappy" is not "this will print".

- **Part A, the cosmetic body** — silhouette, mouthpiece, fillets, raised text. The
  collar, the stop and the switch mount that go *inside* it are modelled and tested;
  the shell around them is not. It waits on Prototype B, because a body built around a
  mechanism that has not been cycled is a body built twice.
- **Part B, the switch carrier** — the design is decided (see deviation 5) but the
  geometry is not cut, and its snap features wait on R-4.
- **The AMS colour split.** `plate.py` writes one body per object. `coupon.lettering()`
  already returns the glyphs as their own solid, which is the half of the work that was
  in the way; the emitter still needs to write it as a second body with its own extruder
  assignment before Prototype D.
- **Overhang checking.** Deliberately absent. The book nook wrote that check twice and
  deleted it both times, once for passing a known-bad part and once for failing a good
  one. The canister's only real overhang is its bridged crown, at 15.4 mm — a span the
  sample already proves at 13.4.

**`params.py` is the authority; this file is the human summary.** Where they disagree, the
code wins — it is the one that can fail a build.
