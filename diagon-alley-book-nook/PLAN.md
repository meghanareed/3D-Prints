# Implementation plan — Diagon Alley book nook

Companion to `SPEC.md`. The spec says *what* and *in what order*; this says *how*, and
what has to be measured before any of it is worth typing.

Target machine throughout: **Bambu P2S, 0.4 mm nozzle, PLA, 0.2 mm layers.**

## Decisions taken, this session

* **`archive/` is not the starting point and no code comes out of it.** Attempt three is
  **net new**. `archive/` is read as evidence — what was measured, what failed and why —
  and nothing is imported, copied or edited. §3 draws the line between the two.
* **R-1 is closed, and the answer overturns the first draft of this plan.** There is no
  interpreter problem. §2.

---

## 1. What changed from the first draft

The first version of this plan opened with a hard blocker: CadQuery could not run on this
machine, and a second Python interpreter would be needed. **That was wrong.** Measured
rather than assumed, this time:

* `cadquery-ocp 7.9.3.1.1` publishes a **`cp314/win_amd64` wheel**, and declares
  `requires_python <3.15,>=3.10`.
* `cadquery 2.8.0` is a pure-Python wheel (`py3-none-any`), `requires_python >=3.11`.
* `pip install --dry-run cadquery` on the installed **Python 3.14.3** resolves cleanly —
  cadquery 2.8.0, cadquery-ocp 7.9.3.1.1, matplotlib 3.11.1 and the rest.

The installed 3.14.3 is fine. Nothing needs a second interpreter.

**One caveat, and it is the reason to pin.** `cp314` wheels appear *only* in
`7.9.3.1.1`; the immediately preceding `7.9.3.1` has none. Python 3.14 support is one
patch release old. Pin the exact versions in `requirements.txt` — an unpinned resolve on
a machine that later gets Python 3.15 falls straight off the `<3.15` ceiling.

---

## 2. Environment — the commands

Run from `diagon-alley-book-nook/`. **These have already been run on this machine**;
they are recorded so the setup is reproducible.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install cadquery matplotlib numpy
```

Then freeze what resolved, so this cannot drift:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements.txt
```

Verify:

```powershell
.\.venv\Scripts\python.exe -c "import cadquery; print(cadquery.__version__)"
```

Nothing else is required. **Do not `winget install` another Python.** No conda, no `uv`.

Notes:

* The install is large — roughly half a gigabyte. `cadquery` pulls `vtk`, `scipy`,
  `numba`, `casadi`, `nlopt` and `trame` for its viewer, none of which a headless build
  script uses. If the size becomes annoying later, `cadquery-ocp-novtk` exists; it is not
  worth the deviation now.
* Use `.\.venv\Scripts\python.exe` explicitly, or activate the venv. The bare `python` on
  this machine is the user-scope 3.14.3 install and does not see these packages.
* `.venv/` must be in `.gitignore`, and `requirements.txt` must be committed.

---

## 3. What carries over from two failed attempts, and what does not

This is the most important section in the document, because "net new" is easy to say and
easy to over-apply. The distinction is **evidence versus implementation**:

> **What was learned in plastic carries over. What was written in Python does not.**

A caliper reading on a printed coupon is a fact about a Bambu P2S extruding PLA through a
0.4 mm nozzle. It does not become untrue because the code that produced the test part is
being discarded. Re-buying those measurements would cost prints, and the whole reason for
attempt three is that this project cannot afford prints it does not need.

### Carries over — physical results, ~70 g of filament already paid for

| | |
|---|---|
| **Clearance 0.30 mm per side, and the joint is GLUED** | Two printed coupons. Seven identical sockets cut to one number: three held, four dropped. The scatter between one socket and the next is wider than the whole 0.20–0.45 range, so no nominal clearance gives a repeatable press fit at this diameter |
| **Crush ribs are unusable at this scale** | Printed. On one peg the joint became permanent; on a pair it would not go together at all |
| **Round, not square** | A square bore cut 0.05 mm *looser* per side still would not sit square, while the round one did. A 0.4 mm nozzle leaves internal corners radiused ≈0.21 mm |
| **Raised type needs ≥ 3.5 mm** | Bold serif stem ≈ 0.12 of glyph size; below that the stem is thinner than one extrusion |
| **XY repeatability ≈ ±0.20 mm; holes print 0.1–0.3 mm undersize; smallest dependable standalone feature ≈1.2 mm thick × 2 mm long** | |
| **A vertical 2.4 mm peg prints blobbed** | 4.5 mm² per layer with no cooling time. Observed on the very first print |
| **Gel cyanoacrylate, bead in the socket** | Thin CA wicks onto the brick face before it sets |

Every one of these is independently corroborated by published guidance — §4.

### Does not carry over — all of it

`build.py`, `plates.py`, `parts/`, `lib/`, `data/facade.py`, `verify.py`, `mf3.py`,
`orient.py`, `coupon.py`, and all of `out/`. Not imported, not copied, not adapted.

Two of those are genuinely good and will be tempting. Resist both:

* **`mf3.py`** — 834 lines that write a Bambu project 3MF. Two *facts* from it carry over
  and are worth more than the code: Bambu only recognises a project if
  `<metadata name="Application">` starts with `BambuStudio-`, and **per-object print
  settings go in `Metadata/model_settings.config`, where its per-object brim is already
  proven to work**. §7 builds on both. The file itself does not carry over — and note
  what it does *not* contain: any support handling at all.
* **`verify.py`** — 22 checks, each paid for in filament. The *failures they encode*
  carry over as a checklist. The file does not, and §5 explains why importing it would be
  actively harmful.

`profiles/P2S_project_settings.config` is the one edge case: it is not code, it is a
vendored Bambu Studio export. It should be **re-exported fresh from the installed Bambu
Studio for the actual P2S** rather than copied — see R-3, which was already a live
research item because the vendored one dates from the P1S era.

---

## 4. Research: is the peg method right for PLA? — answered

You asked whether the peg/pin method should be confirmed against published guidance
before committing to it. It should, and I have. **It holds up, with three refinements and
one larger caveat.**

### The published numbers agree with the printed ones

| Measured here | Published guidance |
|---|---|
| Holes print 0.1–0.3 mm undersize | "Holes run 0.1–0.3 mm undersize; outer dimensions run 0.05–0.15 mm large" |
| XY repeatability ±0.20 mm | "A well-calibrated FDM printer holds about ±0.2 mm in XY" |
| Round beats square; corners radius ≈ half the line width | Same figure, from nozzle geometry |
| Gel CA, in the socket | "Gel viscosity prevents wicking away from the joint gap, allowing controlled application in tight-fit dowel assemblies" |

Two independent lines of evidence reaching the same numbers is the strongest position
this project has been in.

### Refinement 1 — the D-section pin is textbook, not a workaround

The reason for the D-flat here was anti-rotation without a sharp internal corner. The
published dowel guidance recommends **D-shaped dowels for a different reason**: *"flat
face on build plate — no bridging required."* The same feature solves the keying problem
and the print-orientation problem at once. Keep it.

### Refinement 2 — "locate, then glue" is the published answer too

The dowel tolerance tables distinguish three regimes. At Ø6 mm:

| Fit | Clearance |
|---|---|
| Press | +0.15 mm |
| Loose | +0.25 mm |
| **Glue-only** | **+0.40 mm** |

**Glue-only is deliberately about 2.5× the press-fit clearance.** The 0.30 mm/side landed
on here is squarely in that regime. It was arrived at by discovering that press fit does
not work at this scale — but it is not a consolation prize, it is the recommended fit for
a glued dowel. That reframing matters, because it means the joint is now *designed*
rather than *settled for*.

### Refinement 3 — this kit is below the scale the tables cover

The tables run **6 mm to 12 mm**. The pin here is **Ø2.4 mm**. The relevant guidance for
that end is thinner and more cautionary:

* under 6 mm, add 0.1–0.3 mm clearance;
* **"for anything under 2 mm of engagement, size up: tiny features round off below the
  nozzle width."**

That second clause lands directly on the open question in §6.3 — engagement depth per
side is currently **1.1 mm**, which is under the 2 mm the guidance names. It is now a
research-backed concern, not just my arithmetic. It does not mean the design is wrong; it
means the engagement depth is the thing to fix, and it is fixable for free.

Being below the tabulated range also *explains* the coupon result rather than
contradicting it: the socket-to-socket scatter that made press fit impossible is exactly
what "tiny features round off" predicts.

### The caveat that matters more than the refinements

**The best joint is no joint, and the published guidance says so as loudly as §9 of the
spec does.** Every source frames part-splitting as a cost to be minimised. Both reference
models do the whole job in 12 parts and 1 part. This kit's 181 parts are 181 chances for
a 0.30 mm clearance to be the wrong 0.30 mm.

So the answer to "is the peg method best" has two halves:

1. **Where a joint is genuinely needed, a loose D-section pin into two sockets, located
   not pressed, retained with gel CA, is correct** and matches published practice at this
   scale. No further literature research is warranted.
2. **The bigger win is not joint design at all — it is having fewer joints.** Attempt
   three should not begin by perfecting the mount. It should begin by designing so that
   most of the mounts never exist.

### Alternatives considered and rejected

| Option | Why not |
|---|---|
| **Press fit** | Measured impossible at Ø2.4 on this machine, and the tables put press fit at 6 mm+ |
| **Snap fit** | Needs ≥0.5 mm barb engagement and an arm printed lying in XY at 8:1 length/thickness. Nothing on a facade is big enough |
| **Crush ribs** | Printed. Permanent on one peg, impossible on two |
| **Bowtie / hourglass interlock** | Genuinely the strongest adhesive-free joint, and worth remembering for the **structure** — but it assembles by sliding, which a facade part applied to a wall face cannot do |
| **Heat-set inserts / magnets** | Both dwarf a 2.4 mm mount. Magnets stay interesting for the removable access wall (R4) only |
| **Integral peg (what attempt one did)** | Prints as a vertical 4.5 mm² island; blobs. This is the defect the pin exists to remove |

### Sources

* [Connecting 3D Printed Parts: Dowel and Interlocking Joint Design Guide](https://industrialmonitordirect.com/blogs/knowledgebase/designing-interlocking-joints-for-multi-part-3d-prints-dowel-and-slot-connections)
* [Protolabs Network — How to design snap-fit joints for 3D printing](https://www.hubs.com/knowledge-base/how-design-snap-fit-joints-3d-printing/)
* [3DPut — Complete guide to 3D printing tolerances and fit](https://3dput.com/complete-guide-to-3d-printing-tolerances-and-fit-getting-perfect-clearance-for-moving-parts/)
* [X3D Studios — 3D printing tolerances, a practical guide](https://x3dstudios.com/blog/3d-printing-tolerances-guide)
* [Formfutura — The ultimate 3D prints bonding guide](https://www.formfutura.com/blog/blogs-1/the-ultimate-3d-prints-bonding-guide-50)
* [3D Filament Insider — How to stick PLA together](https://3dfilamentinsider.com/how-to-stick-pla-together/)
* [Kingroon — Best methods to bond 3D prints together](https://kingroon.com/blogs/3d-print-101/best-methods-to-bond-3d-prints-together)
* [CadQuery installation documentation](https://cadquery.readthedocs.io/en/latest/installation.html)
* [cadquery-ocp on PyPI](https://pypi.org/project/cadquery-ocp/)

---

## 5. Three lessons the new code must be built around

These come from reading `archive/`, and they are about *how the code is shaped*, not what
it contains. Each cost this project a print or a session.

### 5.1 A check that never runs reports nothing — and one has been hiding

`archive/verify.py` defines **22** checks. Its `__main__` runs **21**.
`check_hung_clearance`, defined at `verify.py:766`, is called from nowhere. `SPEC.md` §5
states it "passes now"; it has never executed.

The summary line — "N failures, M warnings" — structurally cannot show the absence. This
is the retrospective's own finding with the cache removed.

**For the new code:** the check registry is a **list the runner iterates**, not a
hand-written sequence of calls, and a meta-check asserts every `check_*` symbol is in it.
Ten lines, no geometry, and this class of defect becomes impossible rather than unlikely.

### 5.2 Point the checks at the machine, not at the model

The single sharpest line in the retrospective: *"Every check measured the model. None
modelled the printer... The gap between valid geometry and manufacturable geometry is
where this project died."*

**For the new code:** printer constants — hole shrinkage 0.1–0.3 mm, extrusion width
0.42, elephant foot 0.15, XY repeatability 0.20, minimum feature 1.2 × 2.0 mm — are
**first-class parameters applied to every mating feature**, and a feature smaller than the
machine can place fails the build. Write these before the first part.

### 5.3 Fix the class, and make the class unrepresentable

Attempt two converted signs to sockets-and-pins and left 119 facade parts on integral
pegs; the same defect returned four prints later. Swept just now, `archive/` has **32**
`peg_p1`/`peg_p2` call sites across eight files — the conversion the spec describes as one
function touches two of them.

**For the new code:** there is no public "integral peg" constructor for facade parts at
all. A facade part gets a socket; the wall gets a socket; a loose pin joins them. If the
peg cannot be written, it cannot come back.

---

## 6. Attempt three — the build

### 6.1 Shape of it

Structure the new tree so that the §9/R2 grouping is the default and the 181-part
decomposition is not expressible:

```
params.py      envelope, tolerances, AND the printer model (§5.2)
joints.py      D-pin, socket, and the T3/C4 families when Phase 4 needs them
texture.py     brick, cobble
elements.py    windows, doors, fascias -- shapes, not parts
shops.py       a shop is one object: its elements fused into its patch of wall
wall.py        a wall is its shops plus its own face
checks.py      registry-driven (§5.1), printer-aware (§5.2)
plate.py       plates and the Bambu project 3MF, incl. PER-OBJECT brim + supports (§7)
```

The load-bearing difference from `archive/`: **`shops.py` sits between elements and
walls.** In `archive/` a table row was a part, which is why there were 181 of them. Here a
table row is a *feature of a shop*, and the shop is the part. The regrouping the spec
defers to Phase 2 is the data model from line one, so Phase 2 stops being a rewrite.

### 6.2 Order of work

1. **`params.py` including the printer model.** No geometry. §5.2.
2. **`joints.py` — the D-pin and its socket only.** Carry the measured 0.30 forward.
3. **`checks.py` — the registry, the meta-check, and the printer-feasibility check.**
   Before there is anything to check. This is the one ordering the last two attempts got
   backwards, and it is the whole reason every check arrived exactly one print late.
4. **One wall tile + two sockets + a pin sprue.** Print it. §6.4.
5. Only then: `texture.py`, `elements.py`, `shops.py`.

### 6.3 The pin, settled before geometry

`PIN_L` is nominally 1.6 mm into each half. But a 0.5 mm lead-in chamfer at each socket
mouth means the parallel bore starts 0.5 mm in, so real engagement is:

    1.6 mm travel  −  0.5 mm counterbore  =  1.1 mm of parallel bore per side

Against Ø2.4 that is **0.46 diameters**, and it is under the 2 mm that the published
guidance names as the point where features stop being dependable (§4, refinement 3).

The fix is free. The wall face is 2.5 mm thick, so **2.0 mm of parallel bore already
exists in the wall and the pin only reaches 1.1 mm of it**, and there is a clear gap
behind the face if a deeper bore is ever wanted.

**Action:** carry a longer pin — 2.0 mm engagement per side — as the default, and settle
it on the first plate by printing both lengths. The constraint is the material each part
can offer behind its face, which is a build-time sweep, not a judgement call.

### 6.4 First plate

`SPEC.md` sequences "pin sprue alone" first. **P6** says every piece on a test plate must
mate with another piece on the same plate, and it exists because the last first-fit plate
carried pieces that mated with nothing.

Both intents fit on one plate, for about 2 g: **pin sprue + a wall-thickness socket block
+ a part-back socket block, with both candidate pin lengths.** It answers "do the pins
come off cleanly" *and* "does a snapped pin fit both bores at both lengths" in one print.

On the sprue itself: the last one was destroyed by its own brim flooding a 4 mm pitch —
but the deeper fault was that it was not a sprue. It was a solid 0.8 mm plate spanning
every pin, so freeing one meant cutting a sheet along its length. **A spine at one end,
pins cantilevered off it, wider pitch, and brim forced off.** Brim suppression must be
per-part and must reach every consumer that writes plate settings; in `archive/` there
were three, and the one that was missed is how a brim shipped on a part already known to
need none.

### 6.5 D3 — masking, and the reason the alternative is unavailable

`SPEC.md` §8 D3 offers two ways to stop paint closing a 0.30 mm clearance: mask the
mating faces, or open the features to 0.45 mm.

**The second is not available.** `archive`'s own keying sweep found the unequal-pair mount
stops keying above **0.35 mm**. At 0.45 that key is gone entirely — and it is the mount
every window and door wide enough to take it uses. Opening the clearance to save masking
would mean every window and door in the kit can be glued in backwards, by a first-time
builder.

**Mask the mating faces.** Record the 0.35 figure alongside the decision, or 0.45 gets
proposed again in six months. And measure real paint thickness (R-7) rather than trusting
"two coats close 0.30 mm", which is a plausible number nobody has put calipers on.

### 6.6 What groups with what — the grouping made explicit

§6.1 stated the principle ("a shop is one object, its elements fused into its patch of
wall") and never said which elements. That abstraction is exactly what let 181 parts
happen, so here it is concretely, read off the element tables.

**Some of it already groups.** `FUSE_INTO_BASE` in the old code fuses:

| Element | Already fused with it |
|---|---|
| `window` | its sill |
| `door` | its frame and fanlight |
| `shopwin` | its lintel |
| `bow` | its cornice |
| `bay` | its **corbel and roof** |
| `oriel` | its **corbel and roof** |

So **window-plus-roof is already grouped for the projecting types** — bay, oriel and bow
carry their own roof and corbel. That much is done and should be carried forward as a
requirement.

**What does not group, and should.** Reading the L1/L2 rows, these sit at the same depth
and width as the element they belong to and are still separate parts:

| Loose part | Belongs to | Evidence |
|---|---|---|
| `10E` L1 stallriser | the bow window | same `u=20`, same `w=40` |
| `10D` L1 "cornice" (a `lintel`) | the bow window | same `u=20`, same `w=40`, directly above it |
| `11J` L2 awning | the bay window | same `u=74`, same `w=30` — it *is* the bay's canopy |
| `11K` L2 fascia | the wall | flat board, no undercuts — this is D1's example case |
| `fasciaplate` ×3 | the fascia they name | a nameplate on a board is not a separate assembly |
| `stallriser`, `quoin`, `pilaster`, `lintel`, `ornament` | whatever they sit on | flat boards, D1 |

### The fascia question, and what it forces

Fusing the fascia "into the wall" (D1) and making a shopfront one object including its
fascia (D2) are only consistent if **the wall is not one continuous plate with parts
pinned to it — the wall is made of the shop objects.**

The reference models settle this by their own part names:
`Olivanders_Storefront_Wall_Remastered` · `Flourish_Blotts_Storefront_and_Wall_with_sign`
· `Quality_Quidditch_Storefront_and_Wall`. **"Storefront *and wall*"** — three shops, three
objects, each carrying its own piece of wall, sitting inside a separate modular enclosure.
That is the same shape as this kit's chassis-plus-wall-face, and it answers the question:
the fascia is fused into the shop object, and the shop object *is* the wall there.

**Proposal: a panel is a building, full height.** Not a shopfront band with plain wall
above it — a vertical slice from the alley floor to the eaves, carrying its shopfront at
the bottom and its own upper-storey windows above. Taken off the left table, the buildings
already separate cleanly:

| Panel | Spans | Carries |
|---|---|---|
| **L1 Ollivanders** | u ≈ 0–57 | bow + stallriser + cornice + door + front quoin; windows `13A`, `13B`, `13E`; dormer `14A` |
| **L2 The Apothecary** | u ≈ 59–109 | bay + awning + door + fascia; oriel `12B`, windows `13C`, `13F`, `13G`, attic `14B` |
| **L3 Scribbulus** | u ≈ 112–150 | shop window + stallriser + door; window `13D` |

Three things fall out of this, and all three are arguments for it:

1. **The seam is a building line.** Diagon Alley is a row of buildings, so a vertical joint
   at u ≈ 57 reads as the gap between two shops rather than as a defect. A horizontal seam
   would not.
2. **The drainpipe already sits on the seam.** `15A`/`15B` run the full height at
   **u = 60** — within 3 mm of the L1/L2 boundary. A drainpipe down a building junction is
   where a real one goes, and it hides the joint for free.
3. **It is the grouping that fights the forced perspective least, which partly answers
   R-8.** A full-height vertical panel spans a *narrow* range of depth — L1 covers u 0–57
   of a 150 mm alley — so the perspective scale barely varies across one panel. Grouping
   horizontally would have spanned the whole depth and forced the choice in R-8; grouping
   vertically shrinks that problem to a step at each building line, which is where a step
   is invisible anyway.

**The one element that breaks:** the cornices. `17A` runs u 0–78 and `17B` runs u 80–150,
so both cross a panel boundary. A cornice is continuous across a real facade, so it either
splits at the building line (correct architecturally — buildings have their own eaves) or
stays a separate capping part. Decide it when the panels are drawn, not now.

**Still a decision, and it is yours:** one object per *building* (three per wall, above) or
one object per *wall* (the whole left wall, shops integral, standing up). The wall face is
150.6 × 203.1 mm, so a whole wall does fit the 256 bed. One object per wall removes every
seam but concentrates 5–6 hours of printing into a single part that fails whole; the
reference chose per-building, and P9's kill-switch logic favours the smaller unit. **My
recommendation is per-building**, and Phase 1 does not depend on the answer.

### 6.7 Joint gender is chosen per part, not fixed by rule

**This supersedes J1's blanket form.** J1 says *"No vertical pegs, anywhere. A part gets a
socket; the wall gets a socket; a loose pin joins them."* That is the right answer for the
case it was written from and the wrong answer for signs. The better rule:

> **Put the male feature on whichever component lets both parts keep their important
> visible surface facing up. Standardise the connection dimensions; flip the gender per
> joint family.**

#### Why the sign case inverts

A sign must print **flat back down, lettering up** — defect 3 is signs printed face-down
with every raised letter crushed into the bed. Given that, pegs on the sign's back are
impossible: they hold the sign off the plate and force supports under the whole thing,
which is worse than the problem being solved. So the sign gets **recessed sockets in a
flat back**, which cost nothing because they open onto the plate and are simply absences
in the first layers.

That puts the male feature on the wall. And if the wall prints flat with its brick face
up, its pegs point **up** — the ideal orientation for both halves, no supports on either,
**and no loose pin at all**.

#### The objection, and why it does not apply

This project has a printed result that looks like it forbids exactly that: vertical pegs
came out blobbed, which is the whole reason J1 exists. The stated mechanism is
*"a 2.4 mm peg standing up is 4.5 mm² per layer with no time to cool."*

**That mechanism is about layer time, and layer time depends on what else is on the
layer.** The pegs that blobbed were on *small facade parts* — a 22 × 30 mm window frame,
where the peg is a large fraction of the layer and the nozzle returns to it almost
immediately. A peg standing on a **150 × 203 mm wall face** is a rounding error on that
layer; the nozzle spends seconds elsewhere before coming back, which is exactly the
cooling the small parts never got. The profile's minimum layer time is doing this job
already.

So the blobbing result does not transfer to a peg on a large plate, and the inversion is
sound. **But note what that last paragraph is: an inference, not a measurement,** and this
project's whole history is inferences that were one measurement away from being checked.
It costs ~0 g to settle — **put two pegs on the plate-1 wall tile** and look at them. That
is **R-14**.

#### Where I would not follow it: rectangular tabs

The proposal to use 2 × 4 mm rectangular tabs for anti-rotation is the one part to reject,
and it is rejected on printed evidence rather than preference. The *tab* prints fine —
external corners come out sharp. Its **socket** is the problem: a 0.4 mm nozzle cannot cut
a sharp internal corner, leaving a radius of ≈0.21 mm, so a sharp-cornered tab binds on
the diagonal before its flats ever touch. On the printed coupon a square bore cut
**0.05 mm looser per side still would not sit square**, while the round one did. That is
the defect that ended attempt one, on 119 parts.

The anti-rotation need is real and there are two shapes that meet it without a sharp
internal corner, both already dimensioned:

* **Two round pegs of unequal diameter (P2).** A pair cannot rotate, and the unequal
  diameters mean the part cannot go on backwards — the same keying a rectangle gives, from
  the shape FDM makes best. Spacing scales down for a small sign.
* **T5, the flat tenon — 4.0 × 2.6 × 2.2 with its corners chamfered 0.6.** This is the
  rectangular tab, with the corner relief that makes it printable. It is on the
  never-tested list, so it needs a coupon before anything depends on it.

Either is fine. A sharp-cornered tab is not.

#### AMS lettering — the part I had missed

Printing the text upward means the letters can be a **filament change**, not paintwork.
Above the sign body's top face there is nothing on those layers *except* the letters, so a
colour change at that Z colours the lettering and nothing else. That removes hand-painting
every tiny glyph, which was the single most tedious thing in the paint plan, and it
partially defuses **D3** — masking matters less when the lettering is not painted at all.

Two concrete consequences fall straight out:

1. **Give every sign the same body thickness.** If all the signs on a plate start their
   lettering at the same Z, the whole plate needs **one** colour change. Different
   thicknesses mean one change per distinct height, each with its own purge. This is a
   real constraint on the sign geometry and it should be set before the signs are drawn —
   and it pairs naturally with R3's "all the signs on one object".
2. **Set text depth to an exact multiple of the layer height.** `TEXT_DEPTH` was 0.5 mm at
   a 0.2 mm layer — 2.5 layers, so the last layer lands halfway and the change cannot fall
   on a clean boundary. **0.6 mm = exactly 3 layers.** (Unrelated to the ≥3.5 mm minimum,
   which is glyph *size*, not depth.)

**R-15** covers what a document cannot answer: whether the change purges cleanly, whether
the colour boundary is crisp at 3 layers, and whether the letters still read.

#### Where this leaves each family

| Family | Prints | Male feature on | Loose pin? |
|---|---|---|---|
| Sign, nameplate, flat plaque | flat, lettering up | **the wall**, if the wall prints flat | **No** |
| Small flat trim — sill, lintel, quoin | flat, face up | the wall, same reasoning | No |
| Grouped shopfront / window unit | standing, supports on | **neither** — sockets both sides | **Yes** |

The last row is not an inconsistency, it is the same rule applied: a standing panel's face
is vertical, so a peg on it is a horizontal cantilever that droops and needs support on the
one surface that must not have it. Sockets both sides plus a pin is what "keep the
important surface printable" gives for that family.

#### One interaction to be aware of

This couples to the still-open panel question in §6.6. **The sign half is settled either
way** — flat back, recessed sockets, lettering up. Only the wall half is contingent:

* if panels print **flat**, they carry integral pegs and signs need no pin at all;
* if panels print **standing**, the sign mounts on a loose pin into a socket instead.

From the sign's side those are identical, so nothing is blocked. But "signs need no pin"
is a genuine point in favour of flat panels, and it belongs in that decision.

### 6.8 Assemblies, not monoliths — and the rule for where to stop

A kit-of-parts direction: treat each facade as a miniature model kit rather than one
printable object. Windows become little assemblies — hollow frame, separate roof/canopy,
separate ledge — glazing is a captured pane rather than printed geometry, signs become a
reusable library, and the floor becomes removable tiles over a wiring base.

**Most of this is right and it is adopted below.** But it needs one guard rail bolted on
first, because in its general form it is also a description of how this project failed
twice.

#### The tension, stated plainly

The proposal includes *"every façade could have standardized mounting points for windows,
doors, signs, awnings, balconies, lamps, drainpipes, window ledges, roof trim, decorative
molding… every decorative component becomes something you can print separately."*

That is, almost item for item, `archive/data/facade.py`. It is the 181-part kit — the
thing `SPEC.md` §9 identifies as *"the whole difference"* between this project and two
reference models that work, and the thing the retrospective calls *"a tax on validation:
220 parts means 220 chances to be wrong and one bench to find out on."*

The justification offered is real and I do not dismiss it: *"a failed tiny detail costs 10
minutes of printing instead of ruining a 14-hour façade print."* True. But note which risk
that manages. **Two attempts died of assembly failure, not print failure.** Nothing failed
to print in a way that mattered; 21 of 21 wall mounts fouled the facade, and the bench
filled with parts that would not go together. Splitting parts trades print risk *down* and
assembly risk *up*, and assembly risk is the one that has actually bitten, twice.

So the direction is right and the axis matters. Which gives the rule:

> **A part earns separation if it needs a different print orientation, a different
> filament, or a cavity that cannot be made in one piece. Otherwise it fuses.**

| | Earns separation? | Why |
|---|---|---|
| Bay/bow **roof or canopy** | **Yes** | Different orientation — lies on its largest face instead of becoming an unsupported ceiling |
| **Glazing** | **Yes** | Different material |
| **Signs** | **Yes** | Different orientation (text up) *and* different filament (AMS) |
| **Window frame** vs its wall | **Yes** | Needs a hollow cavity behind the panes |
| **Drainpipes, lamps** | **Yes** | Different colour; and the pipe sits on a building seam anyway |
| **Balconies** | **Yes** | Undercut |
| Sills, ledges, lintels, quoins, **roof trim, moulding** | **No — fuse** | Same colour, same orientation, no undercut. This is D1, and it is where the 181 came from |

That last row is the whole guard rail. Assemblies as parts: yes. **Trim as parts: no.**
Applied across a wall this lands near 20–25 objects — three building panels, their window
assemblies, glazing, signs, pipes and lamps — which is roughly the Phase 2 target, reached
by a rule rather than by a target.

#### The window assembly, adopted

* **Hollow behind the panes.** The plan never stated this and it is a functional
  requirement, not a refinement: a solid frame blocks the light the whole nook exists for.
* **A perimeter mounting flange with four points, outside the illuminated area**, hidden
  by the window trim. Better than the current arrangement, which puts mounts on the frame
  band itself. Four points give redundant anti-rotation and keep the light path clear.
* **Roof/canopy separate**, so the frame has no unsupported ceiling and the roof prints on
  its largest face.
* **Frame printed standing on its sill**, with arches and chamfers used to keep overhangs
  printable — which suits the architecture rather than fighting it.

**Faceting the "curve" is already done, and independently.** `lib/window.py`'s
`bow_window` takes `facets=5`, with the comment: *"built faceted: it prints better than a
true cylinder and, at this scale, reads identically once painted."* Two people reaching
that conclusion separately is good evidence. The added benefit worth capturing is the one
the old code did not act on: **flat facets mean flat panes**, so glazing becomes several
small rectangles instead of a curved sheet.

#### Glazing in a channel — adopt, and it solves a masking problem

A channel on the back of the frame, panes inserted from behind after the frame is painted,
is strictly better than the current arrangement. It removes the need to mask glazing while
painting, which was one of the two things D3's masking decision had to cover. Both glazing
options — cut acetate/PET and a single 0.2 mm printed layer (R-11) — slide into the same
channel, so this does not force that choice.

#### Lighting: the advice is sound and **does not fit this envelope**

A 20–40 mm light cavity behind each window is the right way to avoid a visible hotspot.
It is also geometrically impossible here, and this is worth catching now rather than in
CAD. The nook is 100 mm wide overall:

| Wall build-up | Cavity behind the face | Resulting alley width |
|---|---|---|
| **10.0 (current)** | 7.5 | **74.9** |
| 15.0 | 12.5 | 64.9 |
| 20.0 | 17.5 | 54.9 |
| 32.5 | **30.0** | **29.9 — a corridor, not a street** |

The alley is the product. Spending it on cavity depth destroys the thing being built, so
**the cavity is capped near 7.5–12.5 mm** and diffusion has to come from somewhere other
than distance. Three ways, none of which need depth:

1. **A diffuser sheet close to the pane** — the kit already does exactly this for the sky
   puck (`SKY_DIFFUSER_T` 0.8 at a 6 mm gap).
2. **Side-wash the aperture** rather than aiming at it — run the emitter vertically in the
   wall cavity beside the opening. This also satisfies Phase 6's existing exit criterion
   that no emitter is visible from the front.
3. **Frost the pane itself**, which the printed-glazing option gives for free.

This is **R-16**. Everything else in the lighting proposal — a light cavity per storefront
rather than an LED per window, translucent backing, optional interior silhouettes — is
adopted as written.

#### Signage: adopted nearly wholesale

This section is the strongest part of the proposal, because it dissolves a measured
failure rather than working around it. Eight of twelve signs had type too small to print;
the answer is not smaller nozzles, it is **not every sign needs to be readable**.

* **Three tiers** — hero shop sign (full name), projecting sign (1–3 words), stacked
  signs (abbreviated, symbols, implied text).
* **Fake lettering below the legibility floor.** Raised lines that read as Victorian text
  once painted gold against dark. This is the honest answer to the 3.5 mm limit: below it,
  do not attempt letters, attempt *texture*.
* **Symbols aggressively** — cauldron, quill, key, broom, owl. Also the answer for the
  rear shops, whose plates are perspective-scaled to 0.6 and can never carry text.
* **Vary the silhouette** — rectangle, oval, shield, pointed, scroll, round. Cheap, and it
  makes the street read as dense even where nothing is legible.
* **70 % architecture / 30 % signage**, with *one* deliberately cluttered storefront so
  clutter is a feature rather than the baseline.
* **A sign library** — 10–15 blank shapes, 4–5 brackets, a couple of stacked frames. This
  is the *good* kind of modularity: a parameterised library reused many times, which is
  what this kit is already good at.
* **Stacked signs as backbone + separate plates**, each printed flat, text up, socket in
  the back. Consistent with §6.7, and it means one bad sign is reprinted alone.

**One numeric reconciliation.** The proposed floor is 2.5–3 mm letters with stroke
≥0.5–0.6 mm; this project measured ≥3.5 mm. Both are right, and they disagree only because
they constrain different things. **Stroke width is the real limit** — a stem must be at
least one extrusion, ~0.42 mm, and comfortably more. The 3.5 mm figure came from a *bold
serif* whose stem is ≈0.12 of glyph size. So the rule should be written as **stroke
≥ 0.5 mm, and glyph height derived from the chosen face's stem ratio** — which lets a
fatter-stemmed face go smaller than 3.5 mm and correctly forbids a fine serif at 3.5 mm.
That is a better rule than the one in the plan and it replaces it. **R-10** becomes: print
a strip of candidate faces at a range of sizes and read it at arm's length.

#### The floor: adopt, and it is mostly already specified

Running-bond cobbles with varied size and rotation, 0.6–1.0 mm relief, chamfered top
edges for dry-brushing. The existing parameters already sit in that range
(`COBBLESTONE_RELIEF` 0.8, `COBBLE_JOINT` 0.6, plus worn and missing-stone fractions), and
the forced-perspective scale ladder already shrinks cobbles toward the rear far more
aggressively than the suggested 5–15 %. The **top-edge chamfer is a genuine addition** —
0.3–0.5 mm, and it is what makes dry-brushing catch.

Three things here are new and adopted:

1. **Tile the floor, and hide the seam in the mortar.** Let individual stones cross the
   nominal tile boundary so the joint follows mortar lines instead of cutting across them,
   with alignment features underneath so the top surface stays uninterrupted. This is the
   same seam-hiding principle as the building lines in §6.6.
2. **A curb/gutter transition** at the storefronts, with the interruptions that stop a
   repeated pattern reading as texture: drains, cracks, chipped stones, puddle
   depressions, steps.
3. **Wire channels under the tiles, so the floor is the wiring infrastructure** — one bus
   down the alley with branches to each storefront, and the tiles become removable service
   panels rather than a lid glued over the electronics. The parameters for this partly
   exist already (`WIRE_CHANNEL_*`, `BUS_CHANNEL_WIDTH` along the base pan); what is new
   is making the tiles *lift out*.

That gives the three-layer build the proposal describes — removable cobble tiles over a
wiring base, with the buildings locating into the sides of that base.

#### Access: confirms a standing requirement

Removable back panel and roof, magnets or screws, and **nothing glued down until the
electronics are tested**. This is already binding — `SPEC.md` R4 makes access a removable
wall rather than removable parts, and Phase 6's exit test requires the walls still come
apart. The proposal sharpens it into a sequencing rule worth writing down: **the facade is
not glued to a building until that building has been lit and tested.**

### 6.9 The storefront module and the dumb wall — this resolves the open orientation question

Keep the entire storefront as **one upright print** — both bays, mullions, door, steps,
canopy, sills and trim — attached to a **much simpler wall** by hidden pegs, where the wall
carries *one large opening per bay* rather than reproducing the storefront's geometry.

Adopted, and it does more work than it looks like it does.

#### It settles §6.6's open decision

§6.6 left a real choice open: print the wall panels **flat** (good for signs and wall pegs,
bad for projecting bays) or **standing** (good for bays, bad for everything mounted on the
face). The tension existed only because one part was being asked to do both jobs.

**Splitting the storefront from the wall dissolves it.** The two halves want opposite
orientations, so give them opposite orientations:

| | Prints | Why | Consequence |
|---|---|---|---|
| **Structural wall** | **flat**, brick face up | Nothing projects from it any more — it is a plate with big holes | Its pegs point **up**: the ideal case from §6.7. Signs and flat trim need **no loose pin at all** |
| **Storefront module** | **standing** on its own base | Bays must project; the base gives a real footprint | Supports where they are wanted, sockets facing sideways |

That is both parts in their best orientation with no compromise, and it retires the
flat-vs-standing question rather than deciding it. It also makes the wall plate cheap and
low-risk enough that one plate per wall becomes viable again — a simple 150.6 × 203.1 plate
with rectangular holes is not the print that fails at hour five.

#### It kills the defect class that fouled 21 of 21 mounts

*"Don't make yourself precisely align 40 little window openings in the structural wall."*
This is the important half. The retrospective's worst single finding was **21 of 21 wall
mounts fouling the facade**, because element geometry and mount geometry came from two
tables that nothing compared.

A wall with **one big opening per bay** cannot have that bug. There is no fine geometry to
align, tolerance stack-ups disappear behind the storefront's own trim, and light floods
the whole assembly instead of squeezing through matched apertures. **The wall stops
carrying decorative geometry entirely** — it is structure, openings and four pegs per
module. That is a whole category of failure designed out rather than checked for.

#### The numbers, with one correction

Proposed: Ø3 mm pegs, 3–4 mm long, into ~3.5 mm sockets, tolerance-tested before
standardising.

* **Ø3.0 instead of Ø2.4 — agreed, and it is an improvement.** Published tolerance tables
  only start at Ø6, and the small-diameter guidance is that features round off below the
  nozzle width; every 0.6 mm of diameter moves away from that edge. Bigger is more
  forgiving here.
* **The socket should be Ø3.6, not Ø3.5.** 3.5 on a 3.0 peg is 0.25 mm per side — and
  **0.25 is the guessed number attempt one shipped on and that failed.** Two printed
  coupons put it at **0.30 per side**, glued. Ø3.0 + 0.30 = Ø3.6. Small correction, but it
  is the one number in this project that cost ~70 g of filament to establish.
* **3–4 mm long: take 4**, and see §6.3 — with a 0.5 mm lead-in chamfer at the mouth, 4 mm
  of travel is 3.5 mm of parallel bore, which finally clears the 2 mm engagement floor the
  guidance names.
* **"Tolerance-test before standardising the whole alley" is exactly right** and is already
  R-5 on plate 1. Test Ø3.0 there, not Ø2.4.

**Four points instead of two: agreed** for a wide module — it stops rocking and keeps a
long piece flush. One cheap piece of insurance: make two of the four sockets round and
relieve the other two slightly (or slot them), so four rigid pegs at ±0.20 mm machine error
cannot over-constrain the part. With 0.30 clearance there is 0.60 mm of play per peg and it
would probably be fine either way, but relieving two costs nothing.

#### Printing it upright — the three problem areas

1. **Tops of the rectangular window openings** — each horizontal bar bridges between
   verticals. Mullions at 1.2–1.6 mm, plus a **0.5–1 mm chamfer under every horizontal
   member**, so the nozzle gains material progressively before the final short bridge.
   Adopted, and note this project has prior form here: *"the frames standing on their
   glazing bars"* is a listed defect, and the panes being narrow is what makes it
   recoverable.
2. **Underside of the canopy/cornice** — the one place supports genuinely belong.
3. **Small decorative ledges** — design out with the same chamfer trick.

**All base surfaces at exactly Z = 0** — left bay base, right bay base, bottom step. This
is a checkable assertion, not a modelling intention: `checks.py` gets a test that every
surface nominated as a base actually touches the plate. Plus a brim, which touches nothing
visible.

#### "Support the canopy, leave the windows alone" — without hand-painting

Manual support painting is the right instinct and the wrong mechanism for a generated kit:
it is a hand operation that has to be redone every time the model changes, which is how a
pipeline drifts from its source.

The programmatic equivalent already exists in the 3MF. Bambu stores modifier geometry as
**parts with a `subtype`** — the real project inspected in §7 shows
`<part id="1" subtype="normal_part">`, and support **enforcer** and **blocker** volumes are
sibling subtypes of that same element. So the emitter can write:

* a **support enforcer** box under the canopy, derived from the canopy's own bounding
  geometry;
* a **support blocker** filling each window opening, derived from the aperture that made it.

Both fall out of geometry the model already has, they regenerate correctly every build, and
they say precisely *"support this roof, leave my windows alone"* without a mouse. This
folds into **R-13** — confirm the exact subtype spelling the same way: set one by hand in
Studio, save, unzip, read `model_settings.config`.

Tree supports from the plate to the canopy underside, as proposed.

#### Glazing

PET/acetate against the rear of the mullions after painting, with the wall's large opening
behind it and the light box beyond. This is §6.8's channel idea applied, and it confirms
the layer stack: **mullions → pane → mounting flange → structural wall → cavity → emitter.**

### 6.10 The entrance arch

A **segmental** arch, not semicircular — broad and low, framing the view without turning
the alley into a tunnel. Adopted, and worth noting the existing `arch=True` geometry builds
a *semicircle* of radius w/2, so the entrance arch is new geometry rather than a reuse.

* **Brick as real geometry, 0.5–0.8 mm relief**, with the arch ring slightly more pronounced
  than the field. `BRICK_RELIEF` is already 0.6, inside that range.
* **Brick returns into the reveal**, so an off-centre viewer sees masonry continuing into
  the opening rather than a plain plastic edge. Cheap, because the reveal is only 10–20 mm
  deep, and it is the difference between an entrance and a picture frame.
* **Restrained treatment** — dark weathered brick, a lantern each side, almost no signage.
  It frames the chaos rather than competing with it, which is also the 70/30 rule from §6.8
  applied at the front.

**On depth, the table gives a concrete limit.** The first shopfront element — L1's bow
window — sits at **u = 20**. A reveal of 10–20 mm therefore occupies the entire run-up to
the first shop, and anything deeper starts competing with it for the grazing sightline
along the near wall. So **10–20 mm is right, and 10–15 mm is safer.** A second lever worth
using: make the arch opening slightly **wider than the alley** rather than flush with the
wall line, so the reveal does not shadow the near shopfronts for an off-axis viewer.

**Print as three pieces — top arch, left pier, right pier — all brick-face-up and flat.**
Correct, and it forces one detail: with the brick face up, the back is **on the plate**, so
the joints between pieces cannot be tabs protruding from the back — those would lift the
piece off the bed, which is the same mistake §6.7 rejected for signs. Use either **in-plane
edge tenons** (T5, which is what J5 already prescribes for anything meeting edge-on) or a
**recess in the back face plus a loose biscuit**. Both keep every piece flat on the plate.

**Cobbles continuing out through the opening: adopt, with a caveat.** Fanning them near the
entrance and running them 30–50 mm proud does make it read as entering rather than viewing.
But `SPEC.md` Phase 8's exit test is *"it sits on a shelf between books"*, and a 50 mm apron
protrudes well past a book spine. Either the apron is a **removable display piece** that
comes off for shelving, or it is kept to ~10–15 mm. Worth deciding rather than discovering.
That is **R-18**.

### 6.11 The rule this settles on

*"Each building has 2–5 substantial decorative modules, not a wall plus 47 things to glue."*

That is the same rule as §6.8's fuse test, stated as a target, and the two agree: three
buildings × 2–5 modules ≈ 6–15 modules per wall, plus one wall plate, glazing and signs.
Comfortably inside the under-20 goal, and arrived at by decomposition rather than by
counting down to it.

---

## 7. Per-object print settings — where brim and supports actually live

This was missing from the first two drafts of this plan, which treated brim and supports
as a slicer-profile question. They are not. **They are written per object into the 3MF**,
and the emitter has to carry them from the first line — retrofitting them later is how the
sprue shipped with a brim it was known not to need.

### The mechanism, confirmed

A Bambu project 3MF keeps per-object settings in `Metadata/model_settings.config`, as
`<metadata key=… value=…/>` children of each `<object>`:

```xml
<object id="2">
  <metadata key="name" value="L1_Ollivanders_Shopfront"/>
  <metadata key="extruder" value="6"/>
  <metadata key="brim_type" value="outer_only"/>
  <metadata key="brim_width" value="5"/>
  <part id="1" subtype="normal_part" uuid="…">…</part>
</object>
```

Two facts, both checked rather than assumed:

1. **Per-object brim already works.** `archive/mf3.py`'s `model_settings()` writes
   `brim_type` and `brim_width` onto individual objects, and those plates printed. The
   mechanism is proven on this machine.
2. **Support settings live in the same config struct.** In BambuStudio's
   `PrintConfig.hpp`, `enable_support`, `support_type`, `support_style`,
   `support_threshold_angle`, `support_on_build_plate_only`,
   `support_critical_regions_only`, `tree_support_branch_angle` and
   `tree_support_branch_diameter` are all declared in **`PrintObjectConfig`** — the same
   struct as `brim_type`, `brim_width`, `brim_object_gap` and `raft_layers`.

`PrintObjectConfig` is per-object by definition. **So supports can be set per object by
exactly the code path that already sets brim per object.** No new mechanism is needed;
what is needed is the settings actually being written, which brings us to the gap.

### The gap

`archive/mf3.py` has **no support handling at all.** Swept: the only `enable_support`
in the file is in its documentation generator, reporting *"Off. `enable_support = 0`."*
The vendored profile agrees — `enable_support: 0` globally, with `support_type` sitting at
`tree(auto)` and `support_threshold_angle` at 30 doing nothing, because supports are off.

That was correct under the old no-supports rule. Under **J9/R1** it is a hole exactly
where the new design needs a capability: a window or door unit printed as one larger
object, standing up, secured by pins, **is the case that requires per-object supports**,
and nothing in the pipeline has ever written one.

### Consequences for the new emitter

**`supports` becomes a first-class part attribute, beside `brim`.** Both are per-object
facts about how a part prints, both are written into `model_settings.config`, and both are
consulted by the checks (§5.2). Not a flag bolted on when Phase 2 arrives.

**Keep the plate/object belt-and-braces pattern.** `mf3.py` deliberately set brim in two
places — as the plate default *and* per object — so that if one is dropped on load the
other still holds. Do the same for supports, and note the asymmetry: the plate default
should stay **off**, because most parts do not want supports and a plate-wide default
would put them on the small flat J8 parts that must not have them. The per-object setting
is the one that turns them on.

### The hazard this creates, and the rule that closes it

Grouping window and door units and pinning them into place puts a support generator and a
precision bore in the same part for the first time. A Ø2.7 mm blind socket that faces
downward will be **filled with support material that cannot be cleanly removed**, and the
bore is the one feature on the part whose dimension the fit depends on. Support inside a
mating bore does not scar a cosmetic surface; it destroys the joint.

**First draft of this rule was wrong, and a sign breaks it.** I wrote "no mating bore may
face downward in a part's print orientation". But a sign must print **text up** — that is
defect 3 from the retrospective, where signs printed face down and every raised letter was
crushed into the bed. A sign lying text-up rests on its back, so its socket necessarily
opens *downward*. The rule as written would have banned the one orientation a sign must
have.

The corrected rule has two clauses, and they apply to **disjoint classes of part**, which
is why they never actually collide:

> **(a) A mating bore may not face downward on a part that prints with supports enabled.**
> **(b) Every blind bore ends in a cone**, so a downward-facing bore is self-supporting on
> a part that prints without them.

Worked through the two cases:

| | Orientation | Supports | Socket faces | Result |
|---|---|---|---|---|
| **Sign, nameplate, small flat part** | flat, **text up** | **off** (J8) | down, onto the bed | Safe. No support is generated for this object at all, so nothing can enter the bore. Clause (b) handles the blind end |
| **Grouped shopfront / window unit** | standing up | **on** (J9) | sideways | Safe. No support can enter a horizontal bore, and no bridging is needed |

Clause (b) is worth having regardless of supports: the blind end of a downward-opening
bore is a small flat ceiling, and at Ø2.7 the slicer will bridge it — passably. A 45–60°
cone at the blind end is **fully self-supporting**, needs no bridge, cannot droop into the
clearance, and gives the pin a positive depth stop for free. Cone every blind bore.

Both clauses are checkable in `checks.py` from the start: take each socket's axis, apply
the part's print orientation, and fail only when the part is support-enabled *and* the
axis points below horizontal by more than `support_threshold_angle`. It models the machine
rather than the model, which is §5.2.

**And note what makes the sign case work at all: the loose pin.** Under the old integral
peg, a sign's peg forced it face-down onto the bed — that is exactly how defect 3
happened. Sockets on both halves plus a separate pin is what frees the print orientation,
so this concern is the one the pin design already exists to solve.

Two things follow, and both are arguments *for* the grouping rather than against it:

* A unit standing up presents its back face vertically, so its sockets point **sideways**
  — no support can enter them, and no bridging is needed. Standing the units up is what
  makes supports and pins safe to combine.
* A horizontal bore still prints its crown as a short unsupported arch. At Ø2.7 the bridge
  is trivial, but it means **the D-flat's rotation is now a print-orientation decision as
  well as a keying one**: orient the flat to the top of the bore and the crown becomes a
  1.2 mm flat bridge instead of an arch. Cheap, and the check can verify it.

### What to set, and what still has to be tested

The profile already carries every key needed; none of it has been exercised.
`support_type` is at `tree(auto)`, `support_threshold_angle` 30, `support_style` default,
`support_on_build_plate_only` 0, `support_object_xy_distance` 0.35,
`support_top_z_distance` 0.2.

Three of those are real decisions rather than defaults to inherit, and none can be settled
from a document — see **R-9**:

* **tree vs normal.** The reference models split on this (normal @30° and tree @15°). A
  shopfront's overhangs are architectural flats — sill undersides, bay roofs, lintels —
  and normal supports usually leave a cleaner flat underside, while tree is better under
  sparse points. This kit has both.
* **`support_on_build_plate_only`.** At 0, supports may land on the wall face itself and
  scar visible brick relief. At 1, anything projecting higher up gets nothing. Neither
  reference model has brick relief under its overhangs, so neither answers it.
* **`support_top_z_distance` / `support_object_xy_distance`.** The trade is release versus
  surface finish, on faces that will be seen and painted.

**R-13** is new and cheap: before writing a single support key, set per-object supports by
hand in Bambu Studio on a two-object project, save, unzip, and read
`model_settings.config` to see the exact serialisation — the spelling of `tree(auto)`,
whether booleans write as `1`/`0`. That is the same method that finally settled the
`Application` tag question after two rounds of guessing, and it costs two minutes.

---

## 8. Phases 2–8 — notes

| Phase | Note |
|---|---|
| 2 — regroup | Not a rewrite under §6.1 — it is what the data model already does. §8 R-8 is the open question |
| 3 — right wall | Mirror. If 2 was hard, the problem is systematic; do not start 3 |
| 4 — structure | T3 sliding tongue and C4 snap were validated on printed coupons. Those *results* carry over (§3); the code does not. A bowtie/hourglass interlock (§4) is worth evaluating here, where sliding assembly is available |
| 5 — signs | One sprue, not 25 parts. Nothing hung has ever been printed |
| 6 — lighting | Puck dimensions in `archive/params.py` are *"measured from the product listing"* — i.e. not measured. R-12 |
| 7 — glazing | Try a single 0.2 mm printed layer before acetate. R-11 |
| 8 — case | Cheapest phase |

**D4 is still open** — how much of the kit is wanted. Phases 5–8 are roughly half the
work, and stopping after Phase 4 gives a complete unlit alley. It changes the Phase 2
target, so it is worth answering before Phase 2 rather than during it.

---

## 9. Research and validation register

**R-1 and R-2 are closed** (§1, §2). No literature research remains outstanding on the
joint question either — §4 answers it. Everything left is **validation in plastic**,
which is the only kind of evidence this project has ever actually learned from.

| # | Item | Why | Blocks |
|---|---|---|---|
| ~~R-1~~ | ~~Which Python has a CadQuery wheel~~ | **Closed.** `cp314` wheel exists; 3.14.3 works | — |
| ~~R-2~~ | ~~Pin the versions~~ | **Closed.** `pip freeze > requirements.txt` | — |
| **R-3** | Re-export the **P2S** profile from the installed Bambu Studio; confirm build volume, and the elephant-foot and hole-compensation defaults | The vendored profile is a P1S-era export. A wrong elephant foot closes a socket mouth, which is precisely how attempt one died | First print |
| **R-4** | Confirm a generated 3MF opens, slices and prints | Bambu only accepts a project whose `Application` metadata starts with `BambuStudio-`; that took two rounds of guessing to find last time. Format-correct ≠ prints | First print |
| **R-5** | **Peg diameter, engagement and clearance** — test **Ø3.0 at 0.30/side into Ø3.6**, 4 mm long, on plate 1 | §6.3 and §6.9. Ø3.0 moves away from the small-feature edge; 4 mm finally clears the 2 mm engagement floor guidance names. Note 0.25/side is the *guessed* number attempt one failed on — do not standardise on Ø3.5 | Geometry, and the alley's standard |
| **R-6** | Does 0.30 + gel CA hold on a **vertical** wall | Both coupons were tested flat in the hand. The wall stands up and the parts hang off it | Phase 1 exit |
| **R-7** | **Measure paint thickness**, two coats, with calipers | D3 turns on it, and §6.5 shows the fallback is unavailable | Phase 2 |
| **R-8** | **Forced perspective vs grouping** — render before modelling | A grouped shopfront spans a range of depth, so it cannot take one perspective scale without either flattening the perspective inside the shop or stepping it at every shop boundary — a seam where the eye follows the street. Neither reference model has perspective, so neither answers this. Decide from a render, not from reasoning | **Phase 2 geometry** |
| **R-9** | **Support settings for a grouped unit**: tree vs normal, `support_on_build_plate_only`, and the z/xy release distances | The reference models split (normal @30° vs tree @15°) and both work. Unknown here is **support scarring on visible brick relief**, which neither reference has under its overhangs. §7 | Phase 2 print |
| **R-13** | **Read Bambu's per-object support serialisation** before writing any support key | Set them by hand in Bambu Studio on a two-object project, save, unzip, read `model_settings.config` — the exact spelling of `tree(auto)`, booleans as `1`/`0`. Two minutes, and it is the method that settled the `Application` tag after two rounds of guessing. §7 | The 3MF emitter |
| **R-14** | **Does a peg on a large plate blob?** Two pegs on the plate-1 wall tile | §6.7 inverts the sign joint on the reasoning that the blobbing was a layer-time effect on *small* parts. Sound, but an inference — and ~0 g to settle | The sign joint family |
| **R-15** | **AMS colour change for lettering** — purge, boundary crispness at 3 layers, legibility | §6.7. Removes hand-painting every glyph and partly defuses D3. Needs one printed sign to confirm | Phase 5, and the paint plan |
| **R-10** | **Type legibility strip** — candidate faces at a range of sizes, read at arm's length | §6.8 reformulates the rule: **stroke ≥ 0.5 mm** is the real limit, with glyph height derived from the face's stem ratio, replacing the flat "≥3.5 mm". Fold into R-15's plate | Phase 5 |
| **R-16** | **Diffusion without depth** — the light cavity is capped near 7.5–12.5 mm | §6.8. A 20–40 mm cavity would cut the alley from 74.9 mm to 29.9 mm. Test diffuser-close-to-pane, side-washing, and a frosted pane instead | Phase 6 |
| **R-17** | Does a 5-facet bow read as curved once mullioned and painted | Free to check — `render.py`, no print. The old code asserts it does; nobody has looked | Phase 2 geometry |
| **R-18** | **Cobble apron vs "sits on a shelf between books"** | §6.10. A 30–50 mm apron protrudes past a book spine and breaks Phase 8's exit test. Removable display piece, or keep it to ~10–15 mm | Phase 8 |
| **R-11** | Printed glazing: does one 0.2 mm layer diffuse and release | Reference does it; this kit never has. Needs transparent or white filament | Phase 7 |
| **R-12** | Measure the real puck and fairy string | Recorded from a product listing, not calipers | Phase 6 |

### Consumables before the first real print
PLA in the wall colour, and enough of it (~105 g for the wall face alone) · **gel**
cyanoacrylate, not thin · a fresh 0.4 nozzle · **calipers**, which R-3, R-5 and R-7 all
depend on · masking material for R-7.

---

## 10. Open questions

* **Q-2 — D4: how much of the kit is wanted?** Phases 5–8 are about half the work.
* **Q-3 — `out/diagon_alley.3mf` is untracked and unexplained.** A BambuStudio 2.8.02.61
  project, 3 plates, dated 2026-09-01, in a folder `SPEC.md` §0 says holds only `SPEC.md`
  and `archive/`. If it is one of the reference models from §9, name it as such or remove
  it — §9 is explicit that no geometry from them enters this kit, and an unlabelled
  reference 3MF in the output directory is how that promise gets broken by accident.

*(Q-1 — where the work happens — is answered: net new, nothing from `archive/`.)*

---

## 11. Critical path

    [DONE] R-1  CadQuery on Python 3.14.3
    [DONE] venv + install
      └─ requirements.txt pinned
      └─ R-3   re-export the P2S profile
      └─ R-13  read Bambu's per-object support serialisation   (§7)
           └─ params.py, incl. the printer model      (§5.2)
                └─ joints.py -- D-pin + socket only
                     └─ checks.py -- registry-driven, printer-aware, FIRST
                        incl. "no mating bore faces downward"     (§7)
                          └─ plate.py -- per-object brim AND supports from line one
                               └─ plate 1: sprue + 2 socket blocks + both pin lengths
                                  [R-4, R-5]
                                    └─ wall tile -> wall face -> 6 parts
                                       = Phase 1 exit                 [R-6]
                                         └─ D3 masking into params.py [R-7]
                                         └─ perspective vs grouping   [R-8]
                                         └─ support style on a real unit  [R-9]
                                              └─ Phase 2

The environment is no longer on this path. The first real gate is a 2 g print.
