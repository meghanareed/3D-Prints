# 10 — Build spec

**Read this first, then `07_RETROSPECTIVE.md`, then `08_JOINT_DESIGN.md`.**

§8 records the decisions already taken. §9 is what two reference models were measured to do differently, and it changes the shape of Phase 2 onward.

This is the working spec for finishing the Diagon Alley book nook. It exists because two
attempts to build it as one 182-part kit both ended with a bench full of parts that would
not go together. The design is not the problem and the printer is not the problem. The
problem is that a kit this size cannot be validated at one print per round, so defects
accumulate faster than they are found.

So the kit is now **phased**. Each phase has an exit test that has to happen in plastic,
in a hand, before the next phase starts. Phase 1 is one wall. Nothing in Phase 2 gets
printed until Phase 1 is glued together and sitting on the desk.

---

## 1. Where this stands

| | |
|---|---|
| Repo | `meghanareed/3d-prints`, `diagon-alley-book-nook/` |
| Branch | `claude/diagon-alley-book-nook-svpb8h` |
| Printer | Bambu P2S, 0.4 mm nozzle, PLA, 0.2 mm layers |
| Model | 181 parts, ~1687 g if it were all printed — **too many; see §9** |
| Printed so far | ~6 trial parts, one wall face, two coupons, one first-fit plate |
| Assembled so far | **one** window frame in a tile of its own wall |

`verify.py` reports 0 failures. That has been true while the printed plate was unusable,
so it means "no check I have written is unhappy", not "this will work".

### What is measured and can be trusted

* **Joint clearance 0.30 mm per side, and the joint is GLUED.** Two printed coupons.
  Friction cannot hold at this scale on this machine — seven sockets cut to one number
  gave three that held and four that dropped. Crush ribs hold far too well: on one peg
  the joint became permanent, on a pair it would not go together at all.
* **A round nozzle cannot cut a sharp internal corner.** Radius ≈ half the line width,
  0.21 mm at 0.42. A square-cornered peg binds on the diagonal of a square socket long
  before the flats meet. This was diagnosed from a printed wall and confirmed on a
  coupon: a square bore cut 0.05 mm *looser* per side still would not sit square while
  the round one did. All mating features are round, D-sectioned or chamfered now.
* **Raised type under about 3.5 mm has stems thinner than one extrusion.** Bold serif
  stem ≈ 0.12 of the glyph size.
* **Printer XY repeatability ≈ ±0.20 mm**; holes print 0.1–0.3 mm undersize; the
  smallest dependable standalone feature is ≈1.2 mm thick and ≥2 mm long.

### What is stale or untrusted

* `out/` — every STL, plate, 3MF, `manifest.json`, `03_PARTS_LIST.md` and
  `04_PRINT_CHECKLIST.md` predates the clearance change, the mount redesign, the sign
  rework and the layout pass. **Regenerate before believing any of it.**
* There is no check for an unsupported overhang. One was written, its own regression
  test failed it, a rewrite failed a good part, and it was deleted rather than shipped.
* `check_manifest()` reads `out/manifest.json`. It warns when the model is newer;
  `check_every_part_builds()` is the one that actually rebuilds and counts.

---

## 2. Recap — what went wrong, from the square-peg era on

Full detail is in `07_RETROSPECTIVE.md`. The short version, because a new session needs
to know which mistakes are already paid for.

### Attempt one — the square peg

Every facade part mounted with a rectangular peg in a rectangular socket, gripped by
crush ribs, at a clearance of 0.25 mm that was **guessed and never printed**. A coupon
existed to measure it and its result was never fed back. 119 parts were built on the
guess.

Printed, the sockets came out with rounded corners and nothing would enter them. Six
trial parts and a wall face; nothing assembled. Stopped.

### Attempt two — the restart

Rebuilt the mount round, printed two coupons, got the clearance number. Then, in order,
these were all found **by the owner looking at a printed part**, not by any check:

1. The coupon's own clearance ladder measured nothing — the value never reached the bore.
2. Its lead-in counterbore was at the blind end.
3. Signs printed face down, crushing every raised letter into the bed.
4. Sign lettering ran off the plate — the fitter assumed 0.62 em per character, all-caps
   bold serif is nearer 0.72.
5. Eight of twelve signs had type too small to print at all.
6. Three swing signs could never be attached to anything: sign eye, bracket eye and
   chain end-link are three closed rings printed separately.
7. The printed "chain" is a fused rigid strip, not a chain.
8. **21 of 21 wall mounts fouled the facade** — signs and shopfronts took coordinates
   from different tables and nothing had ever compared them.
9. The notice board and its poster layer shared one socket.
10. A bracket was two disconnected solids.
11. A round peg lying in a sign's own plane prints its first layers into air.
12. **The pin sprue was destroyed by its own brim**, so no pin joint on the test plate
    could be tried at all.
13. **The facade parts still print round pegs standing up** — the original complaint from
    the very first print, never fixed.

And these were introduced while fixing others: a widened eye made tangent to its arm
(tangency has cost three parts in this project); an arch allowance applied to mounts
sitting on the arch crown, breaking three frames; a check comparing two different
coordinate spaces.

### The four process failures behind all of it

1. **Checks written from the same assumptions as the code.** They pass together and fail
   together.
2. **Sampling instead of sweeping.** A three-part check where a 182-part check was
   possible. The first full sweep found three broken parts immediately.
3. **Deriving what could be measured** — advance width, arch rise, which side of a body a
   peg lands on, which way a part rotates. All four derivations were wrong.
4. **Fixing instances, not classes.** Signs were converted to sockets and pins; the 119
   facade parts were not, and the same defect came back four prints later.

---

## 3. Design rules

Non-negotiable. Each one is here because breaking it cost a print.

**J1 — No vertical pegs, anywhere.** A part gets a **socket**; the wall gets a
**socket**; a loose **pin** joins them. Pins print lying down on a sprue. A 2.4 mm peg
standing up is 4.5 mm² per layer with no time to cool and comes out blobbed. *This is the
one rule that is written but not yet applied to the 119 facade parts — doing so is the
first task of Phase 1.*

**J2 — Every mating feature is round, D-sectioned or chamfered.** No sharp external
corner ever meets an internal corner cut by a round nozzle.

**J3 — Clearance 0.30 mm per side; the joint is glued.** Gel cyanoacrylate, bead in the
socket not on the peg. Locating features locate; adhesive retains.

**J4 — Anything on a cantilever gets two mounts.** One is a hinge.

**J5 — Anything meeting the wall edge-on uses a flat tenon in its own plane**, not a
round pin. A round pin in that plane cannot print.

**J6 — Raised text ≥ 3.5 mm, measured not estimated, and inside its plate by ≥ 0.2 mm.**

**J7 — Every part is one connected solid.** Tangency is not contact: anything placed to
touch must be made to overlap.

**J8 — A small part lies flat with its decorative face up or down by intent**, and
nothing on it starts in mid-air.

**J9 — Supports are allowed, and expected, on grouped parts.** This is a reversal. The
kit was built under a no-supports rule, and that rule is the reason it has 181 parts: no
supports means everything must lie flat, which means flat plates, which means joints, and
every failure in this project happened at a joint. Both reference models print with
supports on (§9). A shopfront printed standing up with supports has no joints to get
wrong. Use supports on anything grouped; keep J8 for the small flat parts that do not
need them.

---

## 4. Process rules

**P1 — Print before adding.** No new element type until the previous one has assembled in
a hand.

**P2 — Sweep, never sample.** If a check can run over all parts, it runs over all parts,
even if it is slow.

**P3 — Test the physical motion, not the numbers.** Build both halves, apply the real
transform — the flip, the rotation, the lowering — and measure the interference. Three
separate bugs in this project passed a check that compared the numbers both halves were
built from.

**P4 — Measure anything measurable.** Text extents, feature positions after a rotation,
which side of a body a point falls on.

**P5 — Never report "0 failures" as though it meant "will print".** Say what was checked
and what was not.

**P6 — A test plate must have every piece mate with another piece on the same plate**,
and the consumables it depends on must survive their own removal.

**P7 — Fix the class.** If a defect exists on one part, look for it on all of them before
declaring it fixed.

**P8 — One change at a time between prints.** Sign size, plate size and wall layout are
coupled; changing all three and re-running the checks moves the file under the owner.

**P9 — Kill switch.** If a phase needs more than four prints to pass its exit test, stop
and cut its scope rather than continuing.

---

## 5. Phases

Each phase states what gets built, what gets printed, and the **exit test** — which
happens in plastic. A phase is not done because the checks pass.

### Phase 1 — One wall

**Goal:** the left wall face, printed, with six facade parts glued into it and sitting on
the desk looking like a wall.

**Build**
1. **Apply J1 to the facade.** Convert `lib/window.py`'s `_mount_pegs` from pegs to
   sockets so every facade part takes a loose pin. The wall already has the matching
   sockets. Verify the pin reaches both and check the part's back is thick enough for a
   1.6 mm bore; thicken locally where it is not.
2. Fix the pin sprue: **no brim on it**, wider pitch, and the runner joined at one end
   only so a pin snaps off without taking its neighbours.
3. Regenerate everything: `build.py`, `plates.py`, the plate maps, the parts list.
4. Run `verify.py` in full, including `check_every_part_builds()`.

**Print** — in this order, stopping at each:
| | | |
|---|---|---|
| a | pin sprue alone | ~1 g. Do the pins come off cleanly? |
| b | one wall tile + two facade parts + pins | ~10 g. Do they seat flush and stay glued? |
| c | the full left wall face | ~105 g, 5–6 h |
| d | six facade parts for it | ~15 g |

**Exit test:** all six parts seat flush on the printed wall, locate on their pins, and
glue solid. No part rocks on brick relief. No part stands proud.

**Cut if it stalls:** drop to three parts, or to a half-height wall.

### Phase 2 — The rest of the left facade, REGROUPED

Not the remaining 38 parts as 38 parts. Regroup them per **D2** and **R1**: each shop
becomes one object — windows, door, riser, pilasters, fascia, cornice and its patch of
wall together — printed standing up with supports. Flat boards fuse into the wall face
per **D1**. Target: **under 20 parts on this wall**, from 44.

This is a real piece of modelling work, not a repack. Budget for it, and do it only after
Phase 1 has proved the wall, the socket, the pin and the glue at small scale.

**Exit test:** the whole left wall dressed, every part glued, nothing missing, and the
part count for the wall under 20.

### Phase 3 — The right wall

Same again, mirrored. Cheap if Phase 2 went well; if it did not, the problem is
systematic and Phase 3 must wait.

**Exit test:** both walls dressed and standing.

### Phase 4 — Structure

Base pan, alley floor and cobbles, wall ribs, chassis, rear bay, back panel. The T3
sliding tongue holds these and is the one joint family already validated on a printed
coupon — leave it alone.

**Exit test:** both walls slide into the chassis, stay square, and the assembly stands on
its own with the alley the right width front and back.

### Phase 5 — Signs, brackets, lanterns, props

Everything that hangs on a wall. Per **D2** and **R3** this is **one or two sprues, not
25 parts**: all the signs for a wall on a common frame, snipped off, painted, glued.
Hanging signs stay fused to their brackets and turned to face the opening; flat plates
pin on. This phase has the most unfinished business: `check_mount_crowding` and
`check_hung_clearance` pass now, but no hung part has ever been printed and fitted.

**Exit test:** every sign and lantern mounted, and the lettering readable at arm's length
from the front of the alley.

### Phase 6 — Lighting

LED beads behind the lit apertures, diffusers, wire channels, the bus, the puck cradle,
the switch housing. Walls stay separable from outer walls for access — that requirement
predates this spec and still stands.

**Exit test:** the alley lights, no emitter visible from the front, and the walls still
come apart to reach it.

### Phase 7 — Glazing and paint

Try **printed glazing first** (**R5**): a single 0.2 mm layer in transparent or white
filament, as the reference model does, rather than cutting acetate. Template `71A` is the
fallback if it does not diffuse well.

Paint happens **before assembly** (**D3**), so this phase largely moves earlier in
practice — the parts of each phase get painted as they come off the plate. What stays
here is the scheme, the masking rule and the final touch-in.

**Exit test:** glazed and painted, and nothing bound up by paint thickness — two coats
close a 0.30 mm clearance, so either the mating faces were masked or the clearance was
opened to 0.45 first.

### Phase 8 — The case

Outer shell, bezel, front arch, hatch, feet. The C4 cantilever snap holds these and is
validated.

**Exit test:** the chassis slides into the case, the bezel frames the alley, it sits on a
shelf between books.

---

## 6. What to do first, in a new session

1. Read `07_RETROSPECTIVE.md` and `08_JOINT_DESIGN.md`.
2. Run `python3 verify.py`. Expect 0 failures and ~54 warnings, all brim advisories.
3. Run `python3 build.py` — **this has not been run since the redesign.** Expect it to
   surface things. `out/` is stale and every downstream file with it.
4. Do Phase 1 step 1: pegs to sockets across the facade. That is the single change that
   addresses the oldest unfixed complaint in the project.
5. Print the pin sprue on its own before anything else.
6. Read §9 before touching Phase 2. The regrouping there is the largest single
   improvement available to this project and it invalidates a lot of the current
   `data/facade.py` structure — do not start it until Phase 1 has passed.

---

## 7. Reference — the numbers

**Envelope**

| | mm |
|---|---|
| Chassis | 94.9 W × 213.1 H × 197.1 D |
| Alley width | 74.9 front → 65.7 rear |
| Alley depth | 150.6 |
| Scene height | 203.1 |
| Wall face plate | 2.5 thick; rib gap 2.5; service depth 5.0 |
| Perspective | element scale = 1 − 0.42 × (u / alley depth) |
| Bed | 256 × 256 × 256 |

**Joints**

| | |
|---|---|
| `FIT_CLEARANCE` / `DECORATIVE_CLEARANCE` / `T3_CLEARANCE` | 0.30 per side |
| `SLIP_CLEARANCE` (chassis into case) | 0.35 |
| `LEAD_IN_CHAMFER` | 0.5 |
| `CRUSH_INTERFERENCE` | 0.15 — **T3 only**, P1/P2 have no ribs |
| P1 | D-section, 2.4 dia, flat 0.6 off axis, 3.5 long |
| P2 | pair, 2.8 and 2.0 dia, 10.0 apart, 4.0 long |
| T3 | sliding tongue 4.0 × 2.5, detent + crush ribs |
| T5 | flat tenon 4.0 × 2.6 × 2.2, corners chamfered 0.6 |
| C4 | cantilever snap 14 × 4 × 2, barb 0.9 |
| Pin | 3.2 long, D-section, on a sprue |

**Print settings** — full list in `05_PRINT_SETTINGS.md`

| | |
|---|---|
| Nozzle | 210 °C (220 first layer) |
| Min layer time | 8 s |
| Max volumetric speed | 12 mm³/s |
| Brim | outer only, 5 mm, on the parts `needs_brim()` marks — **never on a sprue** |
| Avoid crossing walls | on |

A Bambu project 3MF is only recognised as one if `<metadata name="Application">` starts
with `BambuStudio-`. `mf3.check_project()` asserts it.

**The shops**

| | |
|---|---|
| L1 | Ollivanders — wands, hero bow front |
| L2 | The Apothecary — projecting bay |
| L3 | Scribbulus Writing Implements — rear |
| R1 | Eeylops Owl Emporium — arched door |
| R2 | Quality Quidditch Supplies — full storefront |
| R3 | Flourish and Blotts — rear |

Signs also name Magical Menagerie, Weasleys' Wizard Wheezes, Florean Fortescue's and
Madam Malkin's on the lozenge directory, and Gringotts on the directional arrow.

---

## 8. Decisions taken

These were open; they are now answered and are binding on the phases above.

**D1 — Flat boards become part of the wall face.** The L2 fascia, stall risers,
cornices, quoins, lintels and keystones are flat boards with no undercuts, printed in the
same orientation as the wall. They fuse into `wall_face()`. Roughly a dozen parts, a
dozen joints and two dozen mounts disappear.

**D2 — Group aggressively. Fewer, larger parts.** See §9: the reference models do the
whole job in 12 parts and 1 part respectively. The rule is now **a part is a group of
things you would paint the same colour and glue together anyway.** Specifically:

* a **shopfront** is one part — its windows, door, stall riser, pilasters, fascia and
  cornice together, and its patch of wall with it;
* **all the small signs on one wall are one part**, on a common sprue or frame, not
  fifteen separate plates;
* window boxes, brackets and ironwork group with whatever they sit on.

The target for Phase 2 is **under 20 parts per wall**, not 44.

**D3 — Paint before assembly.** Parts are painted while separate, then glued. This has a
consequence that must be designed in, not discovered: **two coats close a 0.30 mm
clearance.** Either mask every mating surface, or open locating features to 0.45 mm and
let the glue take up the slack. Decide which before Phase 2, and record it in
`params.py`.

**D4 — Still open: how much of the kit is wanted.** Phases 5–8 are roughly half of it.
Stopping after Phase 4 gives an unlit, unglazed but complete alley.

---

## 9. What the reference models do

Two third-party Diagon Alley nooks were measured — not copied, and no geometry from them
goes into this kit. What they show is a completely different construction philosophy, and
it is the better one.

| | `Harry_Potter_Diagon_Alley` | `diagon3` |
|---|---|---|
| Objects | **12** | **1** |
| Largest | 186 × 140 × 177 mm | 164 × 102 × 169 mm |
| Layer height | 0.2 | 0.28 |
| Infill | 15 % | 5 % |
| Walls | 2 | 2 |
| **Supports** | **on**, normal auto, 30° | **on**, tree auto, 15° |
| Brim | none | outer only |
| Printer | P1S | A1 mini |

This kit has **181 parts**. That is the whole difference.

### What their part list is called

`Flourish_Blotts_Storefront_and_Wall_with_sign` · `Olivanders_Storefront_Wall_Remastered`
· `Quality_Quidditch_Storefront_and_Wall` · `Store_Signs` (all of them, one part) ·
`Ollivanders_Window_Boxes` · `Modular_Enclosure_3Walls` ·
`Modular_Enclosure_Removable_Wall` · `Top_And_Front` · `Bottom` · `windows`

A whole shop — its windows, its door, its wall and its sign — is **one printed object**.
Three enclosure walls are one object. Every store sign is one object.

### The five things worth taking

**R1 — Supports are allowed.** Both reference models print with supports on. This kit
banned them from the start, and that ban is the root of its shape: no supports means
everything must lie flat, which means a hundred flat plates, which means two hundred
joints, which is where every failure in this project came from. **Allowing supports on
the big grouped parts collapses the part count and removes most of the joints.** The cost
is support removal on interior faces, which the reference models evidently accept.

**R2 — A shopfront is one part, not thirty.** Windows, door, riser, pilasters, fascia,
cornice and sign in one object, printed standing up with its bay windows projecting.
Nothing to align, nothing to glue, no clearance to get wrong.

**R3 — All the signs on one object.** `Store_Signs v14` is 52.6 × 18 × 4 mm and carries
the lot. Snip them off a sprue, paint, glue. This is what the owner asked for and the
reference confirms it works.

**R4 — Access is a removable wall, not removable parts.** `Modular_Enclosure_3Walls`
plus `Modular_Enclosure_Removable_Wall` — a 5.5 mm panel that lifts out. That is how you
reach the lighting, and it is much simpler than making every facade element demountable.
It also satisfies the standing requirement that the walls come apart for the puck light.

**R5 — Printed glazing.** `windows.stl` is 62 × 82 × **0.2 mm** — a single layer,
printed in transparent or white filament, not cut acetate. One layer of PLA diffuses an
LED nicely and needs no knife, no template and no cutting jig. Worth trying before the
acetate route; template `71A` becomes a fallback.

### What this kit does better, and should keep

* **Forced perspective.** Neither reference has it. The scale ladder is the thing that
  makes a 197 mm alley read as a street, and it is already built and working.
* **Parametric everything.** A shop is a table row. Adding one is a row, not a mesh.
* **The verification suite.** Fourteen checks that came out of real failures. The
  reference models are static meshes with none of that.
* **Measured joints.** 0.30 glued, round features, no vertical pegs.

### What this means for the phases

Phase 1 stands as written — one wall, six parts — because it proves the wall and the
joint. **Phase 2 changes**: instead of dressing the left wall with 38 individual parts,
regroup it into shopfront-sized objects per D2, allow supports on them per R1, and aim
for under 20 parts on the wall. Phase 5 (signs) becomes one or two sprues rather than 25
parts.

Do not regroup before Phase 1 passes. The point of Phase 1 is to prove the wall, the
socket, the pin and the glue with something small; regrouping first would put a 100 mm
shopfront on the bed before any joint has been shown to work.
