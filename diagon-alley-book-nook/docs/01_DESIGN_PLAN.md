# Crooked Lane Book Nook — Engineering Design Plan (v1, for approval)

A modular, fully-paintable, LED-lit miniature alley book nook.
**Status: architecture only. No geometry is generated until this document is approved.**

Design language: Victorian/Dickensian magical shopping lane. Original shop names and
original geometry — the reference photos were used for *functional* analysis
(what separates, where light comes from, how deep it reads) only.

---

## 0. Reference analysis — what the photos actually tell us

| Observation in reference | Engineering consequence for this design |
|---|---|
| Alley reads ~3× deeper than the physical box | Perspective must be a *scale ladder* applied to every element family (bricks, cobbles, windows, doors, signs), not just a tapered floor |
| Warm light comes from behind windows, never from a visible emitter | Every LED sits in a blind pocket with ≥1.5 mm of solid material toward the viewer, behind a diffuser |
| Hanging signs crossing the alley are the strongest depth cue | Signs get their own overhead mounting rail so they can cross the void without touching the floor |
| The laser-cut original has ~8 flat layers; depth comes from stacking | We replace stacked flats with true 3D relief + projecting bay volumes, which reads better in raking light |
| Torn/broken brick edge at the front opening is the signature detail | Made a **separate part** (06/07) so it prints flat with crisp jagged edges and paints independently |
| Switch is an external add-on box in the build photo | Switch housing is a rear-panel module, never bonded to the diorama |
| Build photos show wiring done before the case closed | Confirms the **cartridge architecture**: interior finished and tested on the bench, then slid into the case |

---

## 1. Top-level architecture — the cartridge concept

Three independent assemblies:

```
        ┌──────────────────────────────────────────────┐
        │  C. OUTER CASE (sleeve, 4 sides + hatch)     │
        │   ┌────────────────────────────────────────┐ │
        │   │  B. INNER CHASSIS  (self-supporting)   │ │
        │   │     walls + floor + rear block         │ │
        │   │     ┌──────────────────────────────┐   │ │
        │   │     │ A. DECORATIVE PARTS (~80)    │   │ │
        │   │     │  snap in, painted separately │   │ │
        │   │     └──────────────────────────────┘   │ │
        │   └────────────────────────────────────────┘ │
        │  D. SWITCH MODULE (on rear hatch)            │
        └──────────────────────────────────────────────┘
```

**The case is a sleeve, not a box.** Left + Right + Top + Base plinth clip together once
and stay together. The finished, wired, tested chassis then **slides in from the rear on
two dovetail rails**. The **rear panel is a service hatch** (2 concealed clips) carrying
the switch module.

Maintenance path: pop hatch → slide cartridge out → full access to every LED. You never
work inside a closed box.

---

## 2. Parameters (`params.py`)

All millimetres. Changing any value re-derives the whole model.

```python
# ---- envelope -------------------------------------------------------------
BOOKNOOK_WIDTH   = 100.0   # X, across the alley
BOOKNOOK_HEIGHT  = 240.0   # Z
BOOKNOOK_DEPTH   = 200.0   # Y, front (0) to back
SHELL_THICKNESS  = 2.2
PLINTH_THICKNESS = 6.0

# ---- tolerances (the three that matter) -----------------------------------
FIT_CLEARANCE       = 0.25  # structural mating faces, per side
DECORATIVE_CLEARANCE= 0.20  # decorative snap-ins, per side
SLIP_CLEARANCE      = 0.35  # chassis sliding into case, per side
CRUSH_RIB           = 0.30  # sacrificial rib height inside sockets
LEAD_IN_CHAMFER     = 0.50  # 45 deg at every socket mouth  <-- do not remove

# ---- structure ------------------------------------------------------------
WALL_PLATE_T     = 2.5
DETAIL_MIN_T     = 1.2
STRUCT_MIN_T     = 2.0
LIGHT_BLOCK_MIN_T= 1.5     # min solid left in front of any LED pocket

# ---- lighting -------------------------------------------------------------
LED_DIAMETER       = 3.0
LED_BORE           = 3.0 + 2*FIT_CLEARANCE
LED_BORE_DEPTH     = 6.0
WIRE_CHANNEL_WIDTH = 3.0
WIRE_CHANNEL_DEPTH = 3.0
WIRE_CAPTURE_MOUTH = 2.4   # channel mouth narrowed so wire snaps in and stays
DIFFUSER_SLOT_T    = 1.2   # accepts vellum / acetate / 0.8-1.0 acrylic
BUS_CHANNEL_WIDTH  = 4.5

# ---- surface detail -------------------------------------------------------
BRICK_RELIEF       = 0.6
BRICK_LENGTH_FRONT = 18.0
BRICK_HEIGHT_FRONT = 6.0
MORTAR_GAP         = 1.2
COBBLESTONE_RELIEF = 0.8
COBBLE_SIZE_FRONT  = 10.0
RANDOM_SEED        = 20260830   # deterministic: same seed = same STLs

# ---- forced perspective ---------------------------------------------------
PERSP_STRENGTH  = 0.42   # element scale at rear = 1 - 0.42 = 0.58
WALL_CANT_DEG   = 1.75   # each wall leans inward toward the rear
FACADE_LEAN_MAX = 4.0    # per-block "crooked" lean, from the facade table

# ---- print constraints ----------------------------------------------------
BED_X, BED_Y, BED_Z = 220.0, 220.0, 250.0
NOZZLE, LAYER       = 0.4, 0.20
```

### Derived envelope

| Quantity | Value | Check |
|---|---|---|
| Case cavity (X × Z × Y) | 95.6 × 231.2 × 197.8 | — |
| Chassis envelope | 94.8 × 230.4 × 196.5 | slides on 0.35/side |
| Clear alley at front (wall face to wall face) | 88.6 | |
| Clear alley at rear (after 1.75° cant) | 76.6 | subtle, not cartoonish |
| Visible alley aperture at rear block | ≈ 30 | after facades step in |
| Perceived depth | ≈ 500–600 mm | 2.5–3× actual |

---

## 3. Forced perspective — the scale ladder

One function drives everything:

```python
def persp(y):                     # y = depth from front opening
    return 1.0 - PERSP_STRENGTH * (y / CHASSIS_DEPTH)
```

| Element | Front (y=0) | Rear (y=196) |
|---|---|---|
| Brick course height | 6.0 | 3.5 |
| Brick length | 18.0 | 10.4 |
| Cobblestone cell | 10.0 | 5.5 |
| Shop door height | 58 | 30 |
| Ground-floor window | 46 × 38 | 26 × 21 |
| Hanging sign plate | 34 tall | 19 tall |
| Lantern | 22 tall | 12 tall |
| Storey height | 78 | 46 |

Four reinforcing tricks on top of the scale ladder:

1. **Storey count grows with depth** — the front block shows 3 storeys over 230 mm; the
   rear block shows 4 compressed storeys in the same height. This is the strongest cue and
   costs nothing.
2. **Wall cant** — 1.75°/side in plan.
3. **Vertical convergence** — the eaves/cornice line drops 14 mm from front to rear, and
   the ceiling baffle follows it, so the sky slot narrows.
4. **Detail density falls off** — rear parts drop pipework, sill mouldings and glazing
   bars, matching how detail vanishes with distance. Rear parts are also deliberately
   flatter (lower relief) so they don't out-shout the front.

**Anti-cartoon rule:** no element shrinks faster than the ladder, and nothing on the
front plane is oversized to fake it.

---

## 4. The mount standard — "DA-Mount"

One socket family used everywhere. Four types only, so a single library function
generates both halves and the clearances are guaranteed to match.

| Type | Geometry | Used for | Retention |
|---|---|---|---|
| **P1** micro | one 2.5 × 2.0 peg × 3.5 deep, one flat keying face | signs, brackets, small props | 2 crush ribs |
| **P2** standard | two pegs, 3.0×2.0 **and** 2.0×2.0, 4.0 deep, 10.0 apart | window frames, doors, lanterns, awnings | crush ribs + 0.4 detent |
| **T3** tongue | 4.0 wide × 2.5 deep sliding tongue, full part width, mid-span snap dimple | shopfronts, bay windows, walls, floor | detent bump |
| **C4** clip | cantilever beam 14 × 4 × 2.0, 0.9 barb, 30° lead / 45° return | outer case, hatch, switch housing | elastic |

**Key rules baked into the library:**

- Sockets are `peg + 2 × clearance`, **plus** a 0.5 × 45° lead-in chamfer at the mouth.
  Without the chamfer, first-layer squish and elephant's foot make every socket
  under-size and the kit becomes unassemblable. This is non-negotiable.
- Peg tips get a 0.3 chamfer.
- **Crush ribs, not tight fits.** Sockets are cut generously (0.20–0.25/side) and grip via
  three sacrificial 0.3 mm ribs. This makes the kit tolerant of printer variation, which
  matters far more than a nominal number. Changing `FIT_CLEARANCE` from 0.25 to 0.35 is a
  one-line edit and every mating feature follows.
- **Every P2 and T3 mount is keyed asymmetric** — unequal peg widths or an offset rib. A
  part physically cannot go in upside-down, backwards, or in the wrong socket.
- **Every part carries an engraved ID** (0.4 mm recess) on its hidden face, and **every
  socket carries the matching ID** on the wall. With ~80 painted parts on a tray this is
  the difference between an hour and an evening.
- No clip is thinner than 2.0 mm; no peg thinner than 2.0 mm. Nothing fragile.
- All C4 clips print with layer lines **along** the beam, never across it.

---

## 5. Component breakdown

`~104 unique printable parts.` IDs follow your scheme, extended where I needed room.

### 5.1 Structure — inner chassis (00–09)

| ID | Part | Size (mm) | Print | Notes |
|---|---|---|---|---|
| 00 | `Chassis_Base_Pan` | 196 × 95 × 10 | flat, no support | floor rails, rear junction bay, 2 case dovetails underneath |
| 01A | `Left_Wall_Lower` | 196 × 118 × 2.5+relief | flat on outer face | brick relief up, LED pockets & channels on back |
| 01B | `Left_Wall_Upper` | 196 × 116 | flat | dovetail + 2 pins to 01A |
| 02A | `Right_Wall_Lower` | 196 × 118 | flat | mirror |
| 02B | `Right_Wall_Upper` | 196 × 116 | flat | mirror |
| 03A | `Rear_Perspective_Block` | 76 × 92 × 46 | upright | miniature converging facades, 4 compressed storeys |
| 03B | `Rear_Archway` | 44 × 60 × 14 | flat | the "lane continues" arch |
| 03C | `Rear_Silhouette_Screen` | 70 × 80 × 1.6 | flat | distant rooftops/chimneys, backlit |
| 03D | `Rear_Glow_Diffuser_Frame` | 72 × 84 × 6 | flat | holds diffuser sheet + 2 LEDs |
| 04 | `Cobblestone_Floor` | 194 × 84 × 4 | flat, cobbles up | tapered, cambered, slides on 00 rails |
| 04B/04C | `Gutter_Left / _Right` | 190 × 6 × 3 | flat | drain channel + 3 grates |
| 05A/05B | `Ceiling_Baffle_Front / _Rear` | 90 × 98 × 1.6 | flat | sky occluder, overhead sign rail, top wire race |
| 06 | `Front_Bezel_Left` | 196*… 44 × 232 × 5 | flat | **torn broken-brick edge** |
| 07 | `Front_Bezel_Right` | 44 × 232 × 5 | flat | mirror, different break pattern |
| 08 | `Front_Arch_Header` | 90 × 26 × 8 | flat | ties the two bezels, hides the ceiling seam |
| 09 | `Chassis_Rear_Wall` | 94 × 90 × 2.5 | flat | closes the cartridge, wire grommet |

### 5.2 Left facade (10–19) — shops, front → rear

**Shop L1 "MOONWRIGHT & DAUGHTERS · Wandmakers"** — curved bow front, the hero piece.

| ID | Part | Separates for paint as |
|---|---|---|
| 10A | `L1_Shopfront_Recess` | stone/plaster base, holds LEDs |
| 10B | `L1_Bow_Window_Frame` | dark green woodwork |
| 10C | `L1_Glazing_Template` | clear/frosted insert (print or cut) |
| 10D | `L1_Window_Trim_Cornice` | cream stone |
| 10E | `L1_Stallriser_Panel` | painted timber |
| 10F | `L1_Diffuser_Holder` | hidden |
| 10G | `L1_Door` | + 10H `L1_Door_Frame` |

**Shop L2 "THE BRASS CAULDRON · Apothecary"** — projecting bay + door.

| 11A | `L2_Bay_Window_Body` | projecting volume, 22 mm out |
| 11B | `L2_Bay_Window_Frame` | |
| 11C | `L2_Bay_Glazing` | |
| 11D | `L2_Bay_Roof_Lead` | |
| 11E | `L2_Bay_Corbel_Bracket` (×2) | |
| 11F | `L2_Door` / 11G `L2_Door_Frame` / 11H `L2_Fanlight` | |
| 11J | `L2_Awning` | |

**Shop L3 "PENNYQUILL'S · Quills, Ink & Ledgers"** — upper storey, smaller (perspective).

| 12A | `L3_Oriel_Window` | leans out 3° |
| 12B | `L3_Oriel_Frame` / 12C `L3_Oriel_Glazing` |
| 12D | `L3_Sill_Moulding` |
| 13A–13D | `L_Upper_Window_A/B/C/D` (sash, decreasing size rearward) + frames |
| 14A | `L_Attic_Dormer` + 14B frame + 14C glazing |
| 15A–15C | `L_Drainpipe_Upper / _Lower / _Hopper` |
| 16A–16C | `L_Pipe_Bracket` ×3 |
| 17A | `L_Cornice_Front` / 17B `L_Cornice_Rear` |
| 18A | `L_Chimney_Stack` (visible at the top-rear) |
| 19A–19C | `L_Wall_Ornament_A/B/C` (keystone, boot-scraper, wall plaque) |

### 5.3 Right facade (20–29)

**Shop R1 "GRIMSBY'S OWLERY & POST"** — arched door, tall narrow window.

| 20A | `R1_Arched_Door_Recess` |
| 20B | `R1_Arched_Door` / 20C `R1_Door_Arch_Trim` / 20D `R1_Door_Lamp_Hood` |
| 20E | `R1_Tall_Window_Frame` / 20F glazing / 20G sill |

**Shop R2 "HOLLOWAY BROOM CO."** — full storefront under the vertical banner.

| 21A | `R2_Shopfront_Recess` |
| 21B | `R2_Window_Frame` (6-light shop window) |
| 21C | `R2_Glazing_Template` |
| 21D | `R2_Pilaster_Left` / 21E `R2_Pilaster_Right` |
| 21F | `R2_Fascia_Board` (blank — takes sign 30E) |
| 21G | `R2_Stallriser` |
| 21H | `R2_Diffuser_Holder` |

**Shop R3 "THE INKWELL"** — rear, compressed scale.

| 22A | `R3_Shopfront` / 22B frame / 22C glazing / 22D `R3_Door` |
| 23A–23C | `R_Upper_Window_A/B/C` + frames |
| 24A | `R_Bay_Window_Body` + 24B frame + 24C glazing + 24D roof |
| 25A–25B | `R_Drainpipe_Upper/_Lower` |
| 26A–26C | `R_Pipe_Bracket` ×3 |
| 27A/27B | `R_Cornice_Front / _Rear` |
| 28A | `R_Chimney_Stack` |
| 29A–29C | `R_Wall_Ornament_A/B/C` |

### 5.4 Signs, lanterns, props (30–39)

| ID | Part | Mount | Text |
|---|---|---|---|
| 30A | `Sign_Vertical_Banner` (the tall hanging banner) | P1 + overhead rail | backlit, blank plate 30A-T |
| 30B | `Sign_Projecting_Swing_A` | P1 on bracket 31A | swaps |
| 30C | `Sign_Projecting_Swing_B` | P1 | swaps |
| 30D | `Sign_Shield_A` (heraldic shield) | P1 | blank |
| 30E | `Sign_Fascia_Long` (fits 21F) | T3 | blank |
| 30F | `Sign_Directional_Arrow` | P1 | "CROOKED LANE" |
| 30G | `Sign_Stack_Lozenges` (4 stacked lozenge plates) | P1 each | 4 blanks |
| 30H | `Sign_Small_Rear_A` / 30J `_B` | P1 | scaled 0.6 |
| 30K–30N | `Sign_Blank_Plate_1..4` | universal P1 | **blank spares** |
| 31A–31D | `Sign_Bracket_Scroll_A/B/C/D` | P1 into wall | wrought-iron scrollwork |
| 32A/32B | `Sign_Hanging_Chain_A/B` | interlocks | printed link pair |
| 33A | `Lantern_Wall_Large` (+33B hood, +33C glazing) | P2 | LED |
| 34A | `Lantern_Wall_Small` (+34B glazing) | P2 | LED |
| 34C | `Lantern_Rear_Tiny` | P1 | LED, 0.6 scale |
| 35A/35B | `Barrel_Large / Barrel_Small` | P1 into floor | |
| 36A/36B | `Crate_Stack / Crate_Single` | P1 | |
| 37A | `Cauldron_Stack` (3 nested cauldrons) | P1 | apothecary prop |
| 37B | `Broom_Rack` (3 brooms, printed flat) | P1 | |
| 37C | `Post_Box` | P1 | |
| 38A | `Notice_Board` + 38B `Poster_Layer` | P1 | layered posters |
| 39A | `Cobble_Kerb_Step` / 39B `Cellar_Hatch` / 39C `Boot_Scraper` | P1 | |

### 5.5 Lighting parts (40–49)

| 40A–40F | `Light_Baffle_A..F` — snap-on caps sealing each LED pocket, 1.2 mm walls |
| 41A–41D | `Diffuser_Holder_A..D` — 1.2 mm slot, takes vellum/acetate/acrylic |
| 42A–42E | `Diffuser_Plate_Printed_A..E` — 0.8 mm printed fallback, natural PLA, 0 % infill |
| 43 | `Junction_Bay_Cover` — snaps over the rear-bottom electronics bay |
| 44 | `Wire_Clip` ×10 — printed channel retainers |
| 45 | `LED_Collar` ×6 — 3 mm→2 mm bore reducer for smaller LEDs |

### 5.6 Outer case (50–59)

| 50A/50B | `Outer_Left_Lower / _Upper` — 200 × 118 each, dovetail-joined |
| 51A/51B | `Outer_Right_Lower / _Upper` |
| 52 | `Outer_Top` — 200 × 100 × 2.2 |
| 53A/53B | `Outer_Back_Lower / _Upper` — **service hatch**, 2 × C4 clips |
| 54 | `Outer_Base_Plinth` — 200 × 100 × 6, carries the chassis rails |
| 55A/55B | `Case_Spine_Trim_L / _R` — hides the front vertical seams |
| 56A–56F | `Case_Clip_Insert` ×6 — separate C4 clips (printable in a tougher filament) |
| 57 | `Foot_Pad` ×4 |

Nothing larger than 200 × 118 — every case panel prints flat, no supports, no tall
thin walls.

### 5.7 Switch module (60–69)

| 60 | `Switch_Housing` — 34 × 24 × 14, clips into a keyhole in 53A |
| 61 | `Switch_Cover` — snap-on, integral cable clamp |
| 62A | `Switch_Bezel_Rocker` (KCD11 ~ 20 × 13) |
| 62B | `Switch_Bezel_Slide` (SS12D00) |
| 62C | `Switch_Bezel_Button` (12 mm) |
| 63 | `Jack_Plate_DC` (5.5 × 2.1 barrel jack) |
| 64 | `Strain_Relief_Insert` — serpentine, parametric for Ø3.0–4.5 cable |

One housing, four swappable bezels — you pick the switch after the print, not before.

### 5.8 Jigs & aids (70–79)

| 70 | `Tolerance_Test_Coupon` — **print this first**: P1/P2/T3/C4 at 0.20/0.25/0.30/0.35 |
| 71 | `Glazing_Cut_Template` ×4 — trace onto vellum/acetate |
| 72 | `Paint_Handle_Sprue` — press-fit handles for painting small parts |
| 73 | `Assembly_ID_Card` — printed part-number reference tile |

---

## 6. Exploded assembly & build order

```
                                 [52 Outer_Top]
                                        |
   [50A/50B Outer_Left] ---- CASE SLEEVE ---- [51A/51B Outer_Right]
                                        |
                              [54 Outer_Base_Plinth]
                                        |
                   ══ chassis slides in from rear on rails ══
                                        |
   ┌───────────────── INNER CHASSIS (finished + tested) ─────────────────┐
   │                                                                     │
   │  [05 Ceiling_Baffle] ── overhead sign rail ── [30A banner, 32 chain] │
   │        |                                                            │
   │  [01A/01B Left Wall] <-P2/T3- 10*,11*,12*,13*,14*,15*,16*,17*,19*   │
   │        |                                                            │
   │  [02A/02B Right Wall] <-P2/T3- 20*,21*,22*,23*,24*,25*,26*,27*,29*  │
   │        |                                                            │
   │  [03A Rear_Block] + [03B Arch] + [03C Silhouette] + [03D Glow]      │
   │        |                                                            │
   │  [04 Cobblestone_Floor] <-P1- 35*,36*,37*,38*,39*                   │
   │        |                                                            │
   │  [00 Chassis_Base_Pan] --> [43 Junction_Bay_Cover]                  │
   └─────────────────────────────────────────────────────────────────────┘
                                        |
                        [53A/53B Rear hatch] + [60-64 Switch]
```

### Build sequence (the order the kit is designed around)

1. Print **70 Tolerance_Test_Coupon**. Pick the clearance that feels right, set it in
   `params.py`, re-export. *Everything downstream depends on this one step.*
2. Print structure (00–09), case (50–57), then decorative parts in batches.
3. Prime + paint structure: brick, stone, cobbles, weathering.
4. Paint decorative parts **on the sprue handles (72)**, off the model.
5. Dry-fit every decorative part before paint is fully cured — mark any tight socket.
6. Snap decorative parts into walls and floor.
7. Fit diffusers (41/42), then glazing (10C, 11C, …).
8. Seat LEDs in their bores, cap with baffles (40A–40F).
9. Route wire into the 3 × 3 channels, clip with 44, down to the junction bay.
10. Land the four branches in the bay, cover with 43.
11. **Power up and test on the bench** — everything is still open and reachable.
12. Assemble chassis: base pan + walls + rear block + floor + ceiling baffle.
13. Fit front bezels (06/07) and arch header (08).
14. Clip the case sleeve together (50/51/52/54/56).
15. Slide the chassis in from the rear.
16. Fit switch module to the hatch (60–64), connect, clip hatch on.

---

## 7. LED routing plan

**Topology:** 4 branches → one rear-bottom junction bay → one switch → one supply.

| Branch | Positions | Count | Route |
|---|---|---|---|
| **A** left facade | L1 bow ×2, L1 fanlight, L2 bay ×2, L2 door, L3 oriel, L attic | 8 | back of left wall → vertical trunk at y=170 → base pan |
| **B** right facade | R1 window ×2, R1 door lamp, R2 shop ×2, R3 shop, R upper | 7 | mirror |
| **C** lanterns + signs | 33A, 34A, 34C, banner backlight 30A | 4 | ceiling baffle race → down the rear corner |
| **D** rear glow | archway ×2, distant window | 3 | direct into the bay |
| | | **22** | |

**Channels.** 3 × 3 mm troughs on the *outer* face of both walls, mouth pinched to
2.4 mm so wire snaps in and stays without tape. Lateral spurs run from each LED bore to
the nearest vertical trunk. The ceiling baffle carries a top race for the overhead
lanterns and the banner. A 4.5 mm bus channel runs along the rear edge of the base pan.

**Pass-throughs.** Ø4 grommeted holes between wall halves (01A↔01B, 02A↔02B) and at the
wall/base junctions, so no wire is ever visible from the alley.

**Junction bay.** 30 × 22 × 12 cavity at rear-centre of the base pan: two tie-off posts,
space for a small resistor board or JST header, and cover 43. One Ø6 grommet through
09 and 53A to the switch.

**No-see rules, enforced in geometry:**
- Every LED bore leaves ≥ `LIGHT_BLOCK_MIN_T` (1.5 mm) of solid toward the viewer.
- Every bore is capped by a baffle (40x) so light cannot bleed to the neighbouring bay —
  each window is an optically closed box.
- Diffuser sits between the LED and the glazing in every case; no bare emitter is ever on
  a sight line from the front opening.
- Brick relief never thins the wall below 1.9 mm in front of a lit cavity.

---

## 8. Brick and cobblestone generation

**Bricks.** Running bond, per-course random offset, `BRICK_RELIEF = 0.6`, mortar 1.2.
Course height and brick length both follow `persp(y)`. Seeded randomness gives: ±0.35 mm
depth jitter, 4 % recessed/worn bricks, 2 % missing bricks, occasional soldier courses
over openings, and stone quoins at the shop corners. Generated as one extrusion of all
brick profiles per wall face, fused in a single boolean — this keeps the model tractable.

**Cobbles.** Jittered grid → irregular 4–6 sided stone per cell, 0.6 mm joints, relief
0.8 front → 0.45 rear, cell 10.0 → 5.5. The alley is **cambered** (1.2 mm crown at the
centreline) with gutters at both kerbs — real geometry, not a texture. Rear stones are
both smaller and shallower, which is what actually sells the distance.

**Torn front edge.** The broken-brick edge lives on separate parts (06/07) generated by
walking a jagged path through the brick grid and keeping whole bricks — so the break
follows mortar lines like a real demolished wall, and the two sides break differently.

---

## 9. Printability audit

| Rule | How it's enforced |
|---|---|
| Fits 220 × 220 × 250 | Largest part 200 × 118. Automated bounding-box assertion on every export. |
| No supports | Every part has a flat print face; overhangs held ≤ 45°; bay-window undersides corbelled, not cantilevered |
| Min thickness | 1.2 detail / 2.0 structural, asserted where checkable |
| No bridges over voids | Bay roofs and awnings print as separate flat parts and snap on |
| Nothing fragile | No clip < 2.0 thick, no peg < 2.0, no free-standing railing thinner than 1.2 |
| Layer direction | Clips oriented so layers run along the beam |
| Seam hiding | All part splits fall on mortar lines, cornices, or behind trim |

Estimate: **~104 parts, ~14 plates, 55–70 h print time, 450–600 g PLA.**

---

## 10. Deliverables once approved

```
diagon-alley-book-nook/
  params.py                  # every number in §2
  lib/  mount.py  brick.py  cobble.py  window.py  sign.py  prop.py  util.py
  data/ facade_left.py  facade_right.py  led_map.py  sign_text.py
  parts/ p00_chassis.py  p01_left_wall.py  ...  p6x_switch.py
  build.py                   # exports every STL + assembled 3MF + exploded 3MF
  plates.py                  # arranges parts onto print plates
  verify.py                  # bbox / watertight / peg-socket interference checks
  docs/ 01_DESIGN_PLAN.md  02_ASSEMBLY.md  03_LED_WIRING.md  04_PAINT_GUIDE.md
  out/  stl/*.stl   preview/assembly.3mf   preview/exploded.3mf   plates/*.3mf
```

Data-driven: shops, windows, signs and LEDs come from tables, so adding a window is a row,
not a new function.

---

## 11. Risks — measured, not guessed

CadQuery 2.8.0 is installed here and I benchmarked the four things I was worried about
before writing this section. Results:

| Spike | Concern | Measured | Verdict |
|---|---|---|---|
| 173-brick wall face: extrude + fuse + STL | boolean explosion | **1.1 s** total, 0.1 MB STL | non-issue; full build will be well under 5 min |
| Keyed P2 socket + 0.5 lead-in chamfer | chamfering into cut pockets often fails in OCCT | **0.08 s**, clean | non-issue |
| Embossed serif sign text | slow, font-dependent | **0.15 s** with DejaVu Serif bold | works; text is on by default |
| C4 cantilever clip profile | — | **0.01 s** | non-issue |

Remaining real risks:

1. **Curved bow window (10B).** The one genuinely awkward shape. If lofting the curved
   glazing fights OCCT, the fallback is a 5-facet segmented bow — which prints better
   anyway, so this is a cosmetic risk, not a schedule risk.
2. **Clearance is printer-specific.** I cannot know your printer's real-world fit from
   here. Part **70 Tolerance_Test_Coupon** exists for exactly this: print it first, pick
   the number, re-export. This is the only step that can make or break the whole kit.
3. **Paint thickness eats clearance.** Two coats of primer + colour on both a peg and its
   socket costs roughly 0.15–0.25 mm of fit. The design assumes sockets are masked or the
   pegs are scraped; I'll call this out at every mount in the assembly guide.

## 12. Decisions I need before cutting geometry

1. **Power.** 5 V USB (recommended: cheap, safe, no batteries, resistors in the junction
   bay), 3 V pre-wired LEDs on 2×AA, or 12 V? Changes junction bay size and rear plate.
2. **Perspective strength.** `PERSP_STRENGTH = 0.42` and `WALL_CANT_DEG = 1.75` — stronger,
   weaker, or as proposed?
3. **Sign text.** Blank plates only, embossed with my fictional names, or your own names?
   Proposed: Moonwright & Daughters, The Brass Cauldron, Pennyquill's, Grimsby's Owlery &
   Post, Holloway Broom Co., The Inkwell, Crooked Lane.
4. **Printer confirm.** 220 × 220 × 250, 0.4 nozzle — and is a two-piece split of the case
   side panels acceptable? (A 240 mm panel cannot print flat on a 220 bed; the alternative
   is printing it on edge, which I do not recommend.)
5. **Glazing material** you plan to use — vellum, acetate, or 0.8 mm frosted acrylic?
   Fixes the diffuser slot at 1.2 mm or adjusts it.
6. **Front opening.** Full-height torn brick break on both sides (as proposed), or a
   framed rectangular opening with the break only at the top?

Reply with changes, or "approved" and I'll generate the full CadQuery source.
