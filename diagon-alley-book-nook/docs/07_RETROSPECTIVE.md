# 07 — Retrospective

Written when the project was stopped, at the point where none of the trial pieces would
go onto the printed wall. It is here for the next project rather than for this one.

## Where it ended

Six trial parts and a wall face, printed. Nothing assembled. Two observations from the
bench, both correct:

* **the pieces are too big for the wall** — they lap their apertures rather than drop
  into them, which is the design, but nothing about a part in your hand says so;
* **the sockets are misshapen and nothing snaps in** — this one is a real defect, and it
  is the root cause below.

## The root cause: a joint that was never printed

Every facade part mounts with **P1**, a 2.5 × 2.0 × 3.5 mm peg into a 3.0 × 2.5 mm
socket, gripped by four crush ribs. The rib geometry, worked out from `lib/mount.py`:

| | |
|---|---|
| socket bore | 3.00 × 2.50 mm |
| peg | 2.50 × 2.00 mm |
| rib protrusion into the bore | **0.40 mm** |
| rib footprint | 1.50 mm long × 0.625 mm tall |
| intended interference on the peg | **0.15 mm per side** |

A 0.40 mm protrusion is *one extrusion line* at a 0.42 mm line width. The slicer cannot
place it more finely than one bead, and every real-world error acts in the **closing**
direction:

* a small hole prints undersize by 0.1–0.2 mm per side;
* an extrusion overshoots its nominal width under pressure;
* `elefant_foot_compensation` is 0.15 mm — at the socket mouth, more material;
* `xy_hole_compensation` is 0 in the profile, so none of it is corrected.

Stack those and the effective interference is not 0.15 mm per side but something nearer
0.4 — a third of the peg's width. The peg does not press in; it does not go in. The
ribs, printed as single ragged beads inside a 3 mm hole, are exactly the "misshapen
indents" on the bench.

**None of this was ever tested in plastic.** `74A/74B` proved the T3 and C4 joints and
returned real numbers — T3 0.30, C4 0.25 — which went straight into `params.py`.
`70A/70B`, the coupon that measures P1 and P2, was printed and its result was never fed
back. `FIT_CLEARANCE` sat at its initial guess of 0.25 for the entire project, and 119
facade parts were built on it.

## What actually went wrong, in order of how much it cost

**1. The two joints that were easy to test got tested. The one everything depends on
did not.** T3 holds four wall parts. C4 holds the case. P1 holds all 119 facade parts,
and it is the one that shipped on a guess.

**2. Crush ribs were a CAD idea, not a manufacturing one.** The concept is sound — a
sacrificial rib shears on insertion and grips regardless of dimensional accuracy — but
it needs a rib the printer can resolve, and 0.15 mm of interference is below the noise
floor of a 0.4 mm nozzle. It was refined twice in CAD (sized from the clearance rather
than fixed; embedded 0.6 mm so OCCT would not leave it detached) and never once printed.

**3. Every check measured the model. None modelled the printer.** First-layer area,
overhang ratio, island necks, withdrawal interference, assembled envelope, brick under a
flange — all real checks that caught real things. Not one of them knew that a hole
prints small, that a 0.4 mm feature is one bead, or that elephant foot closes a socket
mouth. The gap between "valid geometry" and "manufacturable geometry" is where this
project died.

**4. Every defect was found by printing, and each check was written after the print that
found it.** The loose tab on the torn edge. The frames standing on their glazing bars.
The doors balanced on a 1.1 mm doorknob. Five parts abandoned to stringing. Brick relief
under every flange. Sills lifting fifteen frames back into the air. The checks improved
each time, and the checks were always exactly one print behind.

**5. Scope outran validation.** 220 parts, four mount families, forced perspective,
fairy-light integration and a puck-lit sky, all designed before a single joint had been
proven in plastic. One shop front — wall, one window, its sill and its glazing — built
and physically assembled would have found the P1 problem in the first week.

**6. Symptoms got fixed in the layer they appeared in.** Brim rules, print orientations,
nozzle temperature, minimum layer time, plate spacing, the 3MF format — each one a real
problem, correctly diagnosed and correctly fixed. None of them was the reason nothing
fits, and the effort spent there was effort not spent on the joint.

## Things asserted without evidence

Recorded because the pattern matters more than the instances.

* **"58 of 58 elements have mounts cutting no wall."** The probe used `c is q` to exclude
  an element's own cuts, but `collect()` rebuilds them internally so nothing matched. The
  true answer was 1 of 58. Reported as a crisis, withdrawn in the same session.
* **An `out/stl` cleanup that was never in the code.** The edit was written as
  `cd <dir> && python3 - <<PYEOF`; the `cd` failed, `&&` short-circuited, the heredoc
  never ran, and the next command on the line — an `ast.parse` of the untouched file —
  printed "parses", which read as success. It was committed with a message describing
  the fix, and "proved" by a test that could not fail.
* **Three definitions of "needs a brim"** in three files that disagreed, so a part that
  had already failed was warned about, listed without a brim, and shipped with no brim
  setting.
* **The 3MF Application tag.** Two rounds of guessing at why Bambu rejected the projects
  before reading `bbs_3mf.cpp` and finding the one line that decides it.

## For the next project

1. **Print the joint before the parts.** One coupon, one measured number, before
   anything depends on it. If a joint cannot be tested in the first week, the design is
   wrong for the schedule.
2. **Design mounts the printer can make.** Minimum feature ≥ one nozzle width.
   Interference ≥ 2× the machine's real dimensional error, or choose a joint that does
   not need tight tolerance at all: a through-hole and a drop of glue, a magnet, a slot
   with generous slop and a positive stop. At 1:24 a press fit is a lot to ask.
3. **Put the printer in the checks.** Hole shrinkage, extrusion width, elephant foot —
   as parameters, applied to every mating feature, failing the build when a feature is
   smaller than the machine can place.
4. **Build one vertical slice and assemble it before scaling.** One wall, one window,
   one sill, one pane. Glue nothing until it clicks.
5. **When the bench says it does not fit, measure before proposing.** Several rounds
   here went to plausible causes — brick relief, brim, orientation — while the actual
   interference was never measured on a real part.
6. **Attach evidence to claims, and make sure the test can fail.** "It parses" is not
   "it is in the file". "The other files survived" is not "the deletion works".
7. **Complexity is a tax on validation.** 220 parts means 220 chances to be wrong and
   one bench to find out on. Fewer, larger, more forgiving parts would have been a
   better model of this kit from the start — which is, in the end, what merging the
   sills and cutting the glazing was groping toward.

## What is worth keeping

The generated, self-checking pipeline is sound and would serve a simpler kit well:
`build.py` measuring every part in its print orientation, `verify.py` failing the build
on physical grounds, `orient.py` choosing orientations by measurement, `plates.py` and
`mf3.py` emitting slicer-ready projects with settings baked in, `reprint.py` answering
"is the one on my shelf still good", and the documents generated from the model so they
cannot drift. The problem was never the tooling. It was that the tooling was pointed at
the model instead of at the machine.
