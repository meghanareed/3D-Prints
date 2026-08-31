# Crooked Lane Book Nook — Assembly Guide

Generated from the same tables that generate the geometry, so this guide and the STLs
cannot drift apart. Part IDs match the filenames in `out/stl/`.

---

## 0. Before you print anything

**Print `70A_Tolerance_Test_Coupon` and `70B_Tolerance_Test_Pegs` first.**

The coupon carries P1 and P2 sockets at 0.20 / 0.25 / 0.30 / 0.35 mm, with the value
engraved beside each. Try the loose pegs in each. Pick the one that goes in with firm
thumb pressure and does not fall out when inverted. Then:

```bash
# edit params.py
FIT_CLEARANCE        = 0.25   # -> whatever the coupon told you
DECORATIVE_CLEARANCE = 0.20
python3 build.py              # re-export everything
```

Everything else in this kit depends on that one number. Twenty minutes here saves a
weekend of filing.

**Paint eats clearance.** Two coats of primer plus colour on both halves of a joint is
worth 0.15–0.25 mm. Either mask the sockets, or scrape the pegs before final assembly.
The crush ribs give you some margin, but not that much.

---

## 1. Print plan

`python3 plates.py` writes these ready-arranged, already in print orientation, to
`out/plates/`. Drop one straight into the slicer.

| Plate | Parts | PLA | Notes |
|---|---|---|---|
| `01_jigs_first` | 8 | 48 g | **print this one first and stop** |
| `02_wall_faces` (×2) | 1 each | 107 / 110 g | brick side UP, no supports |
| `03_wall_ribs` (×2) | 1 each | 60 / 62 g | hidden; flat |
| `04_chassis` | 2 | 349 g | base pan and plinth |
| `05_floor` | 4 | 88 g | cobbles UP |
| `06_rear` | 7 | 173 g | rear perspective assembly |
| `07_front` | 3 | 47 g | bezels and arch header, broken edge UP |
| `08_case` | 6 | 407 g | face DOWN on the textured plate — free matte finish |
| `09_facade_left` | 64 | 44 g | front face DOWN, pegs up |
| `10_facade_right` | 55 | 33 g | |
| `11_signs_props` | 38 | 19 g | |
| `12_hardware` | 24 | 54 g | lighting and switch parts |

**14 plates, 218 parts, 1591 g.** Note how little filament the decoration costs: all 157
decorative parts together are under 100 g. The mass is in the case and the plinth, and
the plinth is deliberately heavy — it is the ballast under a 240 mm tall narrow object.

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
