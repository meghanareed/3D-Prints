# Crooked Lane Book Nook — Assembly Guide

Generated from the same tables that generate the geometry, so this guide and the STLs
cannot drift apart. Part IDs match the filenames in `out/stl/`.

---

## 0. Before you print anything

**Print `70A_Tolerance_Test_Coupon` and `70B_Tolerance_Test_Pegs` first.**

The coupon is four stations separated by a shallow groove you can find with a thumbnail.
Each station has one **P1 socket** (upper row) and one **keyed P2 pair** (lower row),
cut at a different clearance, with the value raised beside it:

```
   0.20        0.25        0.30        0.35
 [   o   ] │ [   o   ] │ [   o   ] │ [   o   ]     <- P1 socket
 [ o   o ] │ [ o   o ] │ [ o   o ] │ [ o   o ]     <- keyed P2 pair
```

`70B` is **four tabs**, numbered 1–4, on a thin runner. **Snap them apart first** — a
thumbnail does it. One tab per station: the crush ribs shear on first insertion, so
re-using a tab burnishes its pegs and biases every test after the first.

The tabs sit on the same 26 mm pitch as the stations, so the whole strip does line up if
you would rather drop it on in one go. (It did not in the first version — the tabs were
on a 25 mm pitch, which drifts 1 mm per station. Against a 0.2 mm clearance that is a
wall, so only the leftmost tab could ever enter its holes and the other three sat on the
surface with their pegs looking far too long.)

**The tab is a mirror of the station, not a copy.** You turn the tab over to use it, and
turning it over swaps the rows — so the tab carries its single P1 peg on the row where
the station has its *pair* of holes. Both parts have a **chamfered corner**: turn the
tab over so the two chamfers meet, and everything lines up. Press it home and both
mount types engage at once.

The coupon itself is **one piece** — the lines between stations are 1 mm grooves in a
6 mm plate, there so you can find a station by thumbnail. Do not try to split them.

Use a **fresh tab for each station**. The crush ribs shear on first insertion, and
re-using one tab burnishes its pegs and biases every test after the first.

You are looking for the station where the tab goes in with firm thumb pressure and does
not drop out when you turn the coupon over. Then:

```python
# params.py
FIT_CLEARANCE        = 0.25   # -> the value under the station that felt right
DECORATIVE_CLEARANCE = 0.25   # -> the SAME value
```

and re-run `python3 build.py`.

**Set both to the same number.** The coupon applies one value to both, so the station
that felt right is the only clearance you have actually tried by hand. Leaving the
decorative clearance tighter than that makes all 157 decorative mounts tighter than
anything you tested.

*Already set to 0.25 in this repo, from a printed coupon on a Bambu P2S in PLA.*

> **Seen from directly above — which is how the slicer shows a flat plate — a 2 mm peg
> and a 2.4 mm hole look identical.** If you want to confirm the coupon is right before
> printing, `python3 render_coupon.py` draws it raked over so the holes and pegs read.

### The lumps inside the holes are supposed to be there

Look into any socket and you will see small bits protruding from the side walls, part
way down, so the hole is not a clean square all the way through. Those are the **crush
ribs** — two per side. They are the entire retention mechanism.

Measured down a 0.20 P1 socket:

| Depth below the surface | Clear opening |
|---|---|
| 0 – 0.5 mm | 3.9 mm — the lead-in counterbore |
| 0.5 – 0.9 mm | 2.9 mm — the clean bore |
| **0.9 – 3.2 mm** | **2.1 mm — the ribs** |
| 3.2 – 4.1 mm | 2.9 mm — clean again, down to the floor |

The peg is 2.5 mm. It passes freely for the first millimetre, then meets 2.1 mm of
opening and shears its way through, and that shearing is what holds the part in.

**Do not clean them out.** A knife through those ribs leaves you with a socket that a
peg drops into and falls straight back out of. The correct feel is loose, then a
distinct bite, then firm.

`python3 render_socket.py` draws this section from the generated geometry if you want to
see it.

**Grip does not depend on which value you pick.** The crush ribs are sized *from* the
clearance, so each rib bites `CRUSH_INTERFERENCE` (0.15 mm) into the peg whether you run
0.15 or 0.40. An earlier version used a fixed rib height measured from the bore wall,
which meant anything at or above 0.30 had literally zero retention — the parts were a
slip fit and would have fallen out. `verify.py` now checks grip across the whole range
on every build.

**Paint eats clearance.** Two coats of primer plus colour on both halves of a joint is
worth 0.15–0.25 mm. Either mask the sockets, or scrape the pegs before final assembly.
The crush ribs give you some margin, but not that much.

---

## 0b. Second calibration print — the two joints that carry the model

**Print `74A_Joint_Test_Block` and `74B_Joint_Test_Pieces` (plate `01_CALIBRATE_JOINTS`)
before you print the outer case.**

The first coupon tests P1 and P2 — the decorative mounts, which hold windows, signs and
ornaments on. It does not touch the two joints that hold the *model* together:

* **T3**, the sliding tongue that fixes every wall face to its service rib, the floor to
  the base pan, and every projecting bay to its wall.
* **C4**, the cantilever snap that is the only thing holding the outer case together —
  about 750 g of parts.

Both of these were wrong, and both looked perfect in CAD:

| | What was there | What it measured |
|---|---|---|
| C4 | the clip lay in a rectangular pocket 0.5 mm larger than itself in every direction, and its barb's ramp was on the tip instead of behind it | seated, and pulled back 0.4, 1.0 and 2.0 mm, clip and catch intersected in **0.000 mm³** every time |
| T3 | the detent pocket was cut at ball radius **plus** the full clearance, so a 0.5 mm ball dropped in with 0.25 mm of slop | peak withdrawal interference **0.008 mm³**, against ~1.8 mm³ for a working P1 crush fit |

Neither is a fit problem — both *fitted*, beautifully. They simply did not hold. So the
check in `verify.py` no longer asks "does it go in"; it seats each piece against the real
block and measures **what touches what on the way back out**.

### The four stations

| Station | What it is | How to test it |
|---|---|---|
| `T3 0.25` / `T3 0.30` | a groove in the top face, with crush ribs down both flanks | drop the matching tab in. **Line the clipped corners up** — a tongue has no key, and turned the wrong way it still drops in, with its detent against a solid wall instead of its pocket |
| `C4 0.25` / `C4 0.30` | an upright fin, 2.2 mm thick — the case wall at full size — with a window through it | push the cap down over the fin. You should feel the barb ride up, then a distinct click as it springs into the window. Then pull: it should fight you |

The pieces on plate `01` are printed **turned over** — tongue up, clip up — because that
is the only way they print without supports. Turn them back over to use them. That is a
rotation, not a mirror, so the printed piece is exactly the one the checks measured.

### What "right" feels like

* **T3** — noticeably stiff for the first 2 mm as the ribs shear, then it seats with a
  faint click from the detent. If it slides in freely, the ribs printed short; go down
  one clearance step.
* **C4** — a click you can hear. Then, pulling straight back, the cap should not come off
  under finger pressure. If it lifts off cleanly, the barb never engaged.

The two joints are set independently, because they did not come out the same:

```python
FIT_CLEARANCE = 0.25   # P1, P2 and C4 -- the press and snap mounts
T3_CLEARANCE  = 0.30   # T3 -- the sliding tongues
```

*Both already set in this repo, from a printed coupon on a Bambu P2S in PLA: the C4
snap was right at 0.25 and the T3 tongue at 0.30.* A joint you **slide** wants more room
than one you **press** — that is the whole reason this coupon has four stations instead
of two. Grip is sized *from* the clearance for both joints, so moving either number does
not change how hard the joint holds; `verify.py` checks that across 0.15–0.40 on every
build.

---

## 0c. Do not print the outer case yet

`verify.py` fails three checks against the case, and they are not close calls:

```
[envelope] the assembled chassis against the case cavity
  FAIL  chassis height 216.7 exceeds the 213.8 cavity by  2.9 mm  (L_L_Chimney)
  FAIL  chassis width  116.6 exceeds the  95.6 cavity by 21.0 mm  (Bracket_Scroll_B)
  FAIL  chassis depth  200.7 exceeds the 197.8 cavity by  2.8 mm  (Chassis_Rear_Wall)
```

The interior does not fit inside the shell. The width is the serious one: the wall
*ribs* and the scroll brackets hang about 7.5 mm and 12 mm outboard of the base pan on
each side, so the finished scene is roughly 117 mm across where the case gives it 95.6.

Two separate things let this through:

1. **The old envelope check compared `CASE_CAVITY_H` with its own definition.**
   `CASE_CAVITY_H` is *defined* as `BOOKNOOK_HEIGHT - PLINTH_HEIGHT - SHELL_THICKNESS`,
   so the assertion could never fail no matter what the parts did. It now reads the
   placed bounding boxes `build.py` records and measures the real stack.
2. **The chassis and the case are authored in two different coordinate frames.** The
   chassis runs `x = 0 … 94.9`; the case is centred on `x = 0`, `±50`. Nothing ever
   put them in the same space, so the assembled preview has never shown the two
   sub-assemblies in their real relationship — and the left and right case panels'
   assembly transform lays them flat across the front of the model instead of standing
   them at the sides.

The case's own snap joints need rebuilding too: its clip pockets are hand-rolled boxes
that do not match the clip in size or orientation, and there is no room for a clip
anywhere inside the cavity (95.6 mm of case against a 94.9 mm chassis leaves 0.35 mm a
side). Everything from `50_Outer_Left` to `59G_Foot_Pad` is on hold until that is
resolved.

Everything inboard of the case — chassis, walls, floor, facade, lighting, signs — is
unaffected and is checked part by part.

---

## 0d. "Do I need to reprint this?"

The kit is printed piecemeal over days, so after every change the question is never
what changed but whether the thing already on your shelf is still good. A source diff
cannot answer that, and neither can the file size — the wall face changed by 82.7 mm³
out of 85,025, a tenth of a percent, and whether that was worth another four hours came
down entirely to *where* those 82.7 mm³ were.

```
python3 reprint.py <git-ref> [part-id ...]
python3 reprint.py 7726174 01 02
```

It builds the parts as they were at that commit, compares them against what the current
source produces, and for a wall face also measures every part that mounts to it against
**both** walls. Three answers:

| | |
|---|---|
| **identical** | keep what you printed |
| **cosmetic** | the part changed, but nothing that mates with it fits differently |
| **functional** | something that plugs into it now fits differently — reprint before final assembly; testing on the old one is still fine |

The comparison runs on real solids via BREP, not STL. CadQuery's STL import gives a
triangulation-only face that does not behave like a solid in a boolean — that is what
put every part on a plate at the origin once already.

---

## 1. Print plan

`python3 plates.py` writes these ready-arranged to `out/plates/`, every part already
lying in its print orientation. Drop one straight into the slicer.

| Plate | Parts | PLA | Notes |
|---|---|---|---|
| `00_CALIBRATE_FIRST` | 2 | 33 g | **print this one first and stop.** The coupon and its four tabs, nothing else |
| `01_CALIBRATE_JOINTS` | 2 | 67 g | **print this before the case.** T3 and C4 test block and its four pieces |
| `02_wall_face_LEFT` | 1 | 107 g | brick side UP |
| `02_wall_face_RIGHT` | 1 | 108 g | brick side UP |
| `03_wall_rib_LEFT` | 1 | 60 g | hidden; flat |
| `03_wall_rib_RIGHT` | 1 | 62 g | hidden; flat |
| `04_chassis` | 2 | 349 g | base pan and plinth |
| `05_floor` | 4 | 87 g | cobbles UP |
| `06_rear` ×2 | 5 + 2 | 150 / 23 g | rear perspective assembly |
| `07_front` | 3 | 47 g | bezels and header, broken edge UP |
| `08_case` ×4 | 6 / 1 / 2 / 3 | 136 / 121 / 115 / 273 g | panels lie flat, outer face DOWN |
| `09_facade_left` | 64 | 44 g | face DOWN, pegs UP |
| `10_facade_right` | 55 | 33 g | face DOWN, pegs UP |
| `11_signs_props` | 38 | 19 g | |
| `12_hardware` | 24 | 54 g | lighting and switch parts |
| `13_bench_tools` | 8 | 61 g | paint handles, ID card, glazing templates — **none of these go into the nook**, and you do not need them until you start painting |

**18 plates, 218 parts, 1590 g.** All 157 decorative parts together are under 100 g;
the mass is in the case and the plinth, and the plinth is deliberately heavy — it is
the ballast under a 240 mm tall narrow object.

### Filament — three, not eight

| What | Filament | Painted? |
|---|---|---|
| Everything that gets painted — structure, facade, signs, props | **light grey PLA** | yes, over primer |
| All `*_Glazing` parts, `42x` diffusers, `03F` sky diffuser | **natural / white / translucent PLA**, 3 walls, **0 % infill** | **never** |
| Outer case, plinth, drawer, switch module (`50`–`65`) | **matte black PLA** | no — leave as printed |

**Grey, not white, for the painted parts.** Brick relief is 0.6 mm and mortar lines are
1.2 mm. On white PLA under room light you genuinely cannot see that detail, so you
cannot tell whether the print came out until you have primed it. Grey reads. It is also
what grey primer exists for.

**Do not colour-match filament per part.** 218 parts across eight paint colours means a
lot of filament changes for no benefit — you are priming anyway, and primer hides the
substrate completely. The one place colour-matching genuinely pays is the case: matte
black PLA off a textured plate *is* the finish. That is 750 g of large flat panels you
never have to paint.

The one real argument for matching is chip resistance — a snap-fit kit gets handled, and
a chip on a painted part shows bare plastic. If that bothers you, the cheap version is
to prime everything mid-grey and keep your paints in a similar value range, so a chip
reads as wear rather than as a hole in the paint. On a Dickensian alley that is arguably
an improvement.

Avoid silk or high-gloss filament everywhere: paint adheres badly to it and the sheen
hides exactly the surface detail this model depends on.

### The jigs are tools — none of them go into the nook

| ID | What it is | Keep or bin |
|---|---|---|
| `70A` / `70B` | tolerance coupon and test pegs | **single use.** Bin them once you have set `FIT_CLEARANCE` |
| `74A` / `74B` | T3 and C4 joint test block and pieces | **single use.** Print before the case; bin them once both joints feel right |
| `72` | paint handles | reusable tool — a part's peg drops into the handle so you never hold a painted surface. Keep |
| `73` | ID card | records the clearance and random seed this kit was generated with. Keep it with the kit; if you ever reprint a lost part you need those numbers |
| `71A`–`71D` | glazing cut templates | **only needed for sheet glazing.** You are printing PLA glazing, so you can delete these four from plate 01 |

The calibration parts are on their own plate (`00_CALIBRATE_FIRST`, 33 g, about
ten minutes) precisely so that "print this first and stop" costs you ten minutes rather
than an hour of tools you will not touch until painting day. Everything else in this
table is on `13_bench_tools`.

The eight identical sticks on the tools plate are the **paint handles**. Each carries a
socket on top and the mount type embossed on the side of its pad — `P1` takes signs,
props, brackets, pipes and ornaments; `P2` takes window frames, doors, stallrisers and
fascias. They are not testing anything.

### Orientation policy

Nothing prints standing on end and nothing needs supports. Specifically:

- **Case panels lie flat** (200 × 214), never on edge. A 5 mm-thick panel standing
  214 mm tall would be a lost print.
- **Facade parts and signs print face DOWN with their pegs UP.** Pegs-down would make
  each frame bridge over its own 4 mm pegs.
- **Free-standing floor props have flat bottoms and no peg** — they locate in shallow
  recesses moulded into the cobbles. A peg underneath would force the whole body to
  start as an overhang off a 2.5 mm stub.
- The relief on facade parts and signs lands on the build plate. On a textured sheet
  that reads well for brick and timber; if you want a glossy sign face, run plate 11
  on a smooth sheet.

### The big flat parts need a brim

The wall faces, ribs, case panels and base pan are all very wide and very thin — the wall
face is 203 × 193 mm and only 3.1 mm tall, an aspect ratio of about 66:1. There is
31,000 mm² of bed contact, so adhesion area is not the issue; the issue is that a large
thin PLA sheet shrinks as it cools and has almost no height to resist peeling, so the
corners and the long jagged torn edge lift first and the nozzle then drags the part
around.

For every part over about 150 mm across:

1. **Brim type: outer brim only. Width 5 mm.** Not mouse ears — see below.
2. **Bed at 60–65 °C**, not 55. The Bambu PLA default is fine for small parts and low
   for these.
3. **Wash the plate with dish soap and hot water.** IPA alone smears skin oils around on
   textured PEI rather than removing them.
4. **Door closed** for these parts — they are short prints and draughts cause the lift.
   (Crack it only for the tall multi-hour prints where heat creep matters.)

**Outer brim, not mouse ears.** Ears anchor a few discrete points, which is the right
tool for a part whose bed contact is a handful of small footprints. This part has
31,000 mm² of contact — area was never the problem. What lifts is the perimeter: 2,480 mm
of free edge, most of it the jagged torn front edge, curling along its length. Only a
continuous brim holds that down.

**Outer only, never "outer and inner".** An inner brim lays brim inside every window
aperture, and those apertures are exactly where the window frames seat. Brim residue
there would wreck the fit and is miserable to pick out.

Leave brim-object gap at the default — attached, but it still peels.

Which plates want a 5 mm brim: the four single-part plates that hold the big thin sheets,
plus the outer side panel.

| Plate | Footprint | Brim |
|---|---|---|
| `02_wall_face_LEFT`, `02_wall_face_RIGHT` | 203 × 193 | **5 mm** |
| `03_wall_rib_LEFT`, `03_wall_rib_RIGHT` | 203 × 197 | **5 mm** |
| `08_case_2` (outer side panel) | 200 × 214 | **5 mm** |
| `04_chassis`, `05_floor`, `06_rear`, `07_front`, `08_case*` | multi-part | 3 mm — parts sit 6 mm apart, so a 5 mm brim merges them into one sheet |
| `09`–`13` (small parts) | multi-part | none — they are small enough not to warp, and brims would fuse dozens of tiny parts together |

### Slicer warnings — do not turn supports on

Bambu Studio will flag the wall faces for **floating cantilevers**. What it is seeing is
the crush ribs inside the mounting sockets and the small counterbore ledges at the mouth
of each groove: little shelves 0.5–0.9 mm wide starting part way down a hole. PLA bridges
those without help.

**Never enable supports on any part in this kit.** Support material inside a 2.9 mm blind
socket cannot be got out again, and what is left behind destroys the fit the whole design
depends on. If a slicer offers to add supports, decline.

`verify.py` measures the genuinely unsupported area on every build. Brick relief hanging
over a hole currently measures 0.08 mm² and 0.84 mm² on the two walls — nothing.

Settings: 0.4 mm nozzle, 0.2 mm layer, PLA, 3 walls, 15 % infill (structure) / 0 %
(diffusers, printed in natural or white). No supports anywhere — every part has a flat
print face and no overhang steeper than 45°.

On a P2S: crack the door for the big flat panels. It is an enclosed chamber and PLA
heat-creeps on long single-layer-height prints.

---

## 2. The mount system

Four connector types, used everywhere. Each part's ID is engraved on its hidden face and
next to its socket in the wall.

| Type | Where | Fit |
|---|---|---|
| **P1** single keyed peg 2.5 × 2.0 × 3.5 | signs, brackets, lanterns, props, pipes, ornaments | thumb press |
| **P2** keyed pair, 3.0 and 2.0 wide | window frames, doors, stallrisers, fascias, bezels | thumb press |
| **T3** sliding tongue 4.0 × 2.5 + detent | bays, bows, wall-to-rib, floor, walls-to-base | slides then clicks |
| **C4** cantilever snap 14 × 4 × 2.0 | outer case, hatch, switch housing | audible click |

**The pegs are keyed.** A P2 pair has one 3 mm and one 2 mm peg; a P1 peg has a clipped
corner. If a part will not go in, it is the wrong way round — turn it over rather than
pressing harder.

**Grip comes from crush ribs, not a tight hole.** Each socket has four 0.3 mm ribs that
shear on first insertion. The part will feel loose for the first millimetre and then
bite. That is correct.

---

## 3. What snaps into what

### Left wall (01 + 01R)

| Shop | Parts |
|---|---|
| **L1 Moonwright & Daughters**, wandmakers | 10B bow window · 10Bg glazing · 10Bd diffuser · 10Bc cornice · 10E stallriser · 10D cornice · 10G door + 10Gf frame + 10Gl fanlight |
| **L2 The Brass Cauldron**, apothecary | 11A bay body · 11Ag glazing · 11Ar roof · 11Ac corbel · 11J awning · 11F door + frame + fanlight · 11K fascia |
| **L3 Pennyquill's** | 12A shop window + glazing + lintel · 12D stallriser · 12G door + frame |
| Upper storeys | 13A–13G sash windows (frame + glazing + sill each) · 12B oriel · 14A/14B attic dormers |
| Rainwater & masonry | 15A/15B drainpipes · 15C hopper · 17A/17B cornices · 18A chimney · 19A quoin · 19B/19C ornaments |

### Right wall (02 + 02R)

| Shop | Parts |
|---|---|
| **R1 Grimsby's Owlery & Post** | 20B arched door + frame · 20E tall window + glazing + sill · 20G keystone |
| **R2 Holloway Broom Co.** | 21B shop window + glazing + lintel · 21D/21E pilasters · 21F fascia · 21G stallriser |
| **R3 The Inkwell** | 22A shop window + glazing + lintel · 22D door + frame |
| Upper storeys | 24A bay · 23A–23F sash windows · 23G/23H attic dormers |
| Rainwater & masonry | 25A/25B drainpipes · 25C hopper · 27A/27B cornices · 28A chimney · 29A quoin · 29B/29C ornaments |

### Signs and lanterns

| ID | Part | Mounts to |
|---|---|---|
| 30A | vertical banner "CROOKED LANE" | right wall, backlit |
| 30B/30C/30H | swing signs | brackets 31A/31B/31D |
| 30D | shield "BC" | bracket 31C |
| 30E | fascia "HOLLOWAY BROOM CO." | fascia board 21F |
| 30J | fascia "THE BRASS CAULDRON" | fascia board 11K |
| 30F | directional arrow | left wall |
| 30G1–4 | STYLE / VALUE / EASE / VARIETY lozenges | right wall |
| 30K–30N | **blank spares** | anywhere — add your own names |
| 31A–31D | scroll brackets | left/right walls |
| 32A/32B/32C | chain and rail hook | between signs and ceiling baffle 05 |
| 33A / 34A / 34C | lanterns, large / small / rear tiny | walls, each lit |

### Floor (04)

35A/35B barrels · 36A crate stack · 36B crate · 37A cauldron group · 37B broom rack ·
37C post box · 39A kerb step · 39B cellar hatch. 38A notice board and 39C boot scraper
go on the wall; 38B posters snap onto the notice board.

---

## 4. Lighting

Two fairy-light strings and one RGB/CCT puck.

### The important difference from discrete LEDs

A fairy-light bead is a point on a **continuous series circuit**. The wire arrives, the
bead sits, the wire leaves. So every pocket in the rib is a **pass-through** with a
1.4 mm slot on both sides, and the channel network is a **path**, not a tree. You thread
one string through its whole route and both ends come back to the drawer.

**A string cannot be shortened** without killing it. You will have 1–2 m spare per
string. That is what the three coil bays per wall (covers 45A–45C) are for. Do not cut,
do not hot-glue it to the back.

### Route

| String | Route | Beads |
|---|---|---|
| **A — left wall** | drawer → left grommet → up the rear column → attic → oriel → upper sashes → apothecary bay → shop fronts → lantern 33A → return down the same channel → drawer | 12 |
| **B — right wall + rear** | drawer → right grommet → R1 door and window → broom shop → banner 30A → lanterns 34A/34C → upper sashes → rear archway → drawer | 12 |

Both channels are 3.0 × 3.0 and take the out and return legs together. The mouth is
pinched to 2.2 mm: press the wire in with a fingernail and it stays. No tape.

### Order of work — do not skip step 5

1. Fit diffusers (`*_Glazing` parts) into their frames.
2. Seat each bead in its pass-through pocket in the rib.
3. Press the wire into the channel; clip with 44 every 25 mm or so.
4. Cap each pocket with a baffle (40A–40F) — this is what stops one bead washing the
   neighbouring shop.
5. **Power up and test on the bench, with both walls still open.** Rethreading a string
   after the chassis is closed is genuinely unpleasant.
6. Coil the surplus into bays and fit covers 45A–45C.
7. Both tails down the bus channel in the base pan, cover 43, through grommet 47 into
   the drawer.

### The RGB/CCT puck (59.5 × 8.3 mm)

Goes in cradle 03E at the very back, facing forward, behind this sandwich:

```
   viewer  <--  03C silhouette screen (opaque)
                  4 mm air
                03F printed sky diffuser (0.8 mm)
                  6 mm air
                the puck
```

Both gaps matter. The puck has twelve discrete beads; sitting them straight behind a
screen would read as twelve dots rather than a sky.

**Set the colour before you close the case.** The remote is line-of-sight to the puck's
own face, which ends up buried — so the IR remote will not work once the nook is
assembled. The listing says the puck saves its mode before shutdown, so choose the
colour during bench testing and it will come back to it. The inline switch stays
accessible on the case back and still cycles 3000 K / 4000 K / 6000 K, which is the
control that actually matters: dusk, neutral, moonlight.

Clip 65 parks the remote on the back of the case for when the nook is next open.

---

## 5. Assembly order

1. Paint the structure: 01/02 wall faces, 04 floor, 03A rear block, 06/07 bezels, 08.
   **Mask the sockets.**
2. Paint decorative parts on the handles from sprue 72, off the model.
3. Dry-fit every decorative part before the paint fully cures. Mark anything tight.
4. Snap decorative parts into the wall faces and the floor.
5. Fit glazing and diffusers.
6. Do all the lighting work of §4, ending with a bench test.
7. Fit the service ribs 01R/02R to the wall faces (four T3 tongues each).
8. Chassis: base pan 00 → walls → rear block 03A/03B/03C/03D/03E → floor 04 →
   gutters → ceiling baffle 05 → rear wall 09.
9. Front: bezels 06/07, then arch header 08.
10. Case sleeve: plinth 54 + sides 50/51 + top 52, locked with clips 59. Feet 59G.
11. **Slide the finished chassis in from the rear**, onto the plinth's dovetail rails.
12. Battery boxes into cradles 57, into drawer 55, face 56 on.
13. Switch module 60–64 into the hatch, connect, clip hatch 53 on.

Steps 1–6 all happen with the interior completely open on the bench. That is the whole
point of the cartridge architecture.

---

## 6. Maintenance

Pop hatch 53 (two clips and the finger notch) → slide the chassis out → every bead is
reachable. Battery changes do not even need that: pull drawer 56/55 from the back.

---

## 7. Painting notes

| Element | Suggested |
|---|---|
| Wall faces 01/02 | warm brick, dark wash into the mortar, dry-brushed highlight |
| Bezels 06/07 | same brick, but paint the torn cross-section as pale broken stone — this is what sells the break |
| Joinery (frames, doors, bays, bows) | dark green, oxblood, black — one colour per shop |
| Stone (sills, lintels, quoins, cornices) | cream/grey, heavily washed |
| Ironwork (brackets, lanterns, pipes, chains) | near-black with a graphite dry-brush |
| Signs | cream ground, dark lettering, gold edge |
| Cobbles 04 | grey-brown base, wash, dry-brush; keep the rear stones DARKER and cooler than the front — that is half of the depth effect |
| Case | matte black; the textured plate does most of the work |

Keep the rear of the alley lower in contrast and cooler in hue than the front. The
geometry does the perspective; the paint has to agree with it.
