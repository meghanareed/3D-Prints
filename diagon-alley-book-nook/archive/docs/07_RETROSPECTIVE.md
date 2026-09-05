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

> **Corrected after the fact.** The first version of this named the crush ribs as the
> root cause. The bench observation that settles it is simpler and was made from the
> printed wall: **the sockets come out with rounded corners, not square ones.** A round
> nozzle cannot cut a sharp internal corner, so a sharp-cornered peg binds on the
> diagonal before its flats ever touch — and that is true of every rectangular socket in
> the kit, with or without ribs. `docs/08_JOINT_DESIGN.md` works it through with the
> numbers and the design rules that follow from it.

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

---

# Part two — the restart, and where it stopped the second time

The project restarted on a strict gate: fix the mount in one file, print one small
coupon, print nothing over 10 g until something assembles. Written at the point where
the second attempt stopped, with a printed FIRST_FIT plate on the bench that again did
not go together.

## What was actually achieved

* **The joint question was answered, by printing.** Two coupons, ~35 g total. P1 and P2
  locate; glue retains; 0.30 mm per side. That number is now measured rather than
  guessed, which is more than the first attempt ever had.
* **The 13A window frame seated in a tile cut from the real wall.** One physical fit,
  and the only one in the whole project.
* **The rounded-corner diagnosis was confirmed on the bench** — a square-cornered bore
  cut 0.05 mm *looser* per side still would not sit square on its peg while the round
  one did.

Everything else below is what went wrong.

## The pattern, again

Every defect in part two was found by a printed part or by the owner's eye. Not one was
found by a check before it reached the printer. The checks were then written *after*
each — which is better than not writing them, and is still the same failure mode the
first retrospective named. Fourteen checks now exist that did not; all fourteen were
paid for in filament.

Worse: **`verify.py` reported "0 failures" on a model whose printed plate was
unusable.** Passing the suite never meant printable, and saying "0 failures" as though
it did was misleading.

## Defects found by the owner, not by me

| | What was wrong |
|---|---|
| 1 | **The coupon ladder measured nothing.** Six stations labelled 0.20–0.45 were cut at one clearance — the value never reached the round bore. Cross-sections were identical to four decimal places. |
| 2 | The coupon's lead-in counterbore was at the **blind end** of the bore, not the mouth. |
| 3 | **Signs printed face down**, laying every raised letter on the bed to be crushed. |
| 4 | **Sign lettering ran off the plate.** The fitter assumed 0.62 em of advance per character; all-caps bold serif is nearer 0.72. |
| 5 | **Eight of twelve signs had type between 1.97 and 3.05 mm** — stems thinner than one extrusion. None of it would have read. |
| 6 | **Three swing signs could never be attached to anything.** Sign eye, bracket eye and chain end-link are three closed rings, printed separately; there is no order of operations that threads them. |
| 7 | The printed **"chain" is not a chain** — consecutive links overlap by 0.10 mm³ and fuse into a rigid strip. |
| 8 | **21 of 21 wall mounts fouled the facade.** Signs, brackets, lanterns and props take their coordinates from one table and the shopfronts from another; nothing had ever compared them. |
| 9 | The **notice board and its poster layer shared one socket** — two pegs, one hole. |
| 10 | **`31B` was two disconnected solids** — its wall peg placed 3.2 mm clear of the body. |
| 11 | A round peg lying in a sign's own plane **prints its first layers into air** over a 3.5 mm cantilever. |
| 12 | **The pin sprue was destroyed by its own brim.** The brim flooded between pins spaced 4 mm apart and tore them off on removal — so no pin joint on the plate could be tested at all. |
| 13 | **Facade parts still print round pegs standing up.** This is the *original* complaint from the very first print — blobbed vertical posts — and it was never fixed. Signs were converted to sockets and loose pins; the 119 facade parts were not. `11K`'s back printing badly is that same defect. |
| 14 | The FIRST_FIT plate carried **pieces that mate with nothing on it**. A plate about fits, with parts that fit nothing. |

## Defects I introduced while fixing other things

* Widening the bracket eye made the ring **tangent** to the arm — and a tangent solid is
  a separate solid. The bracket silently became three pieces. (Tangency has now caused
  this three times in the project.)
* The arch allowance for P2 pairs was applied to **P1 mounts as well**, which sit on the
  arch crown where there is no dip. It pushed the peg off the top of the frame and broke
  `14B`, `23H` and `20B`.
* `check_sign_text` measured the lettering in the part's frame and the part on the bed —
  **two different coordinate spaces**. It passed every flat sign, whose rotation is
  identity and where the spaces coincide, and called every rotated one face-down
  whichever way it turned.
* Rotating a fused sign the wrong way, then the other wrong way, because I reasoned
  about the rotation instead of measuring where the letters landed.

## Process failures

**`check_manifest` reads the last BUILD, not the model.** It reported "182 parts, all
single-solid" for as long as `out/manifest.json` was older than whatever broke a part.
`31B` was broken underneath it the whole time. A check that reads a cached artefact and
reports it as current is worse than no check. It now warns when the model is newer, and
`check_every_part_builds()` rebuilds all 182 and counts — which found three broken parts
in its first run.

**Sampling instead of sweeping.** `check_fits` tests three parts. `check_all_mates`
tests 119. The difference between those two is exactly the class of bug that shipped.
When a check *can* be exhaustive it should be, even if it is slow.

**Guessing instead of measuring**, repeatedly: the per-character advance width, the arch
rise, which side of the body a peg lands on, which way a part rotates. Every one of them
was wrong, and every one was a one-line measurement away from being right.

**Fixing one dimension breaks another.** Sign text size, plate size and wall layout are
coupled: making the type legible widens the plate, which moves it on the wall, which
moves its socket. I solved these one at a time and re-ran the checks, so the file moved
under the owner between prints. There is no joint solve, and there should be.

**A check I could not trust.** I wrote a "nothing starts in mid-air" check, built a
regression test from the known-bad peg, and the test passed clean — the check did not
work. Rewritten to measure lateral growth, it then failed a part that is demonstrably
fine. I deleted it rather than ship it. **That gap is still open:** nothing in the suite
detects an unsupported overhang.

**A false choice offered to the owner.** I framed it as "keep tuning and the file keeps
moving, or print what's here" — when the honest position is that the tuning is necessary
and the drip-feed was my process problem, not a cost the owner should absorb. They said
so, correctly.

## Still open when it stopped

1. **Facade parts print round pegs vertically** — the original defect, unfixed. The
   remedy is known and proven on signs: socket in the part, socket in the wall, loose
   pin. It was never applied to the 119.
2. **No unsupported-overhang check.**
3. **Brim strategy is per-part and wrong for sprues.** `needs_brim` looks at bed area and
   tippiness; it cannot see that a brim will flood the 4 mm gaps between sixteen pins.
4. **The kit has never been regenerated.** `out/` is from before the clearance change,
   the flat change, the pin joints, the tenons, the sign redesign and the mount moves.
   There are no current plate files, no plate maps and no parts list.
5. **Nothing over 6 g of the redesigned kit has been printed.**
6. Never tested: the acetate glazing, whether 3.5 mm raised type actually reads, the
   T5 tenon, any pin joint at all.
7. **`11K` could probably just be part of the wall face** — a flat board with no
   undercuts, printed in the same orientation. That question was asked and never
   answered; it would remove a part, a joint and two vertical pegs.

## For the next project

Everything in the first retrospective still stands. Added:

1. **A check that reads a cached file must say so.** Better: rebuild and measure.
2. **Every mating pair needs a physical-motion test** — build both halves, apply the real
   transform, measure the interference. Not "both were built from the same numbers".
   This project has three separate bugs that a same-numbers check passed.
3. **Tangency is not contact.** Anything placed to touch must be made to overlap.
4. **Measure, do not derive**, whenever a measurement is available: text extents, where
   a feature lands after a rotation, which side of a body a point falls on.
5. **A test plate must have every piece mate with another piece on it**, and the
   consumables it depends on — pins, hooks — have to survive their own removal. A plate
   whose fasteners break on the brim tests nothing.
6. **Do not report "0 failures" as if it meant "will work".** Say what was checked and
   what was not.
7. **Fix a class, not an instance.** Signs got sockets and pins; the facade did not, and
   the same complaint came back four prints later on a different part.
