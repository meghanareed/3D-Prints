# Crooked Lane Book Nook — Engineering Design Plan (v1, for approval)

A modular, fully-paintable, LED-lit miniature alley book nook.
**Status: v3 — all decisions resolved, geometry generated.**

### v3 change — the lamp kit is a 59.5 mm puck, not a bar
The product photo settles it: **D 59.5 × H 8.3 mm aluminium puck, 12 LED beads, PC light
guide, inline switch cycling 3000/4000/6000 K, IR remote, 1.5 m lead.** That is a very
different object from the 300 mm chamber bar I assumed, and it changes the verdict:

* It **fits** — 59.5 mm across a 94.8 mm chassis, 8.3 mm thick.
* It is **promoted from "optional if it fits" to a default fitted part**: one puck behind
  the rear silhouette screen is now the standard build (`SKY_PUCK_REAR = True`).
* It still cannot do the shop windows — a sealed puck with a light guide can't be
  distributed behind twenty separate frames. Fairy lights remain primary. Unchanged.
* **The IR remote will not work once the nook is closed** — the receiver looks out of the
  emitting face, which will be buried behind the sky diffuser. But the listing says the
  puck *saves its mode before shutdown*, so you set the colour with the remote during
  bench testing and it keeps it. The inline switch stays accessible on the case back and
  still cycles 3000/4000/6000 K — dusk / neutral / moonlight — which is the control that
  actually matters here.
* A hotspot fix is required: 12 discrete beads 4 mm behind a screen would read as twelve
  dots. The rear now uses a **diffuser sandwich** — puck → 6 mm air → 0.8 mm printed sky
  diffuser → 4 mm air → opaque silhouette screen. 22 mm total, absorbed inside the space
  the rear block already occupied, so no alley depth is lost.
* A second puck in a top plenum (down-lit sky fill) is offered but **off by default** —
  it costs 12 mm of scene height. Pucks 3 and 4 stay in the printer, which is what they
  were bought for.

### v2 changes
| # | Your answer | Effect |
|---|---|---|
| 1 | Printer LED lamp kit / battery fairy lights | **Lighting fully re-architected around fairy lights.** See §7. The lamp kit is kept as an *optional* rear sky wash only — reasoning in §7.0 |
| 2 | ok | `PERSP_STRENGTH 0.42`, `WALL_CANT 1.75°` locked |
| 3 | ok | Shop names locked, text embossed by default |
| 4 | **Bambu P2S, 256³ confirmed** | **No part needs splitting.** Walls and case panels print in one piece |
| 5 | PLA glazing | Printed PLA diffusers/glazing are now the **default**; slots still take sheet material |
| 6 | Torn brick both sides | Locked |
| — | *(my error, caught on re-check)* | v1 put a 3 mm wire channel into a 2.5 mm wall plate — impossible. Walls are now a 10 mm ribbed assembly with a real service cavity. See §2 |

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
PLINTH_HEIGHT    = 24.0    # v2: now houses the battery/controller drawer

# ---- printer: Bambu P2S ---------------------------------------------------
BED_X, BED_Y, BED_Z = 256.0, 256.0, 256.0   # <-- confirm on the machine
NOZZLE, LAYER       = 0.4, 0.20
MATERIAL            = "PLA"
PANEL_SPLIT = (BOOKNOOK_HEIGHT + 6) > min(BED_X, BED_Y)   # False at 256 -> one-piece panels

# ---- tolerances (the three that matter) -----------------------------------
FIT_CLEARANCE        = 0.25  # structural mating faces, per side
DECORATIVE_CLEARANCE = 0.20  # decorative snap-ins, per side
SLIP_CLEARANCE       = 0.35  # chassis sliding into case, per side
CRUSH_RIB            = 0.30  # sacrificial rib inside sockets
LEAD_IN_CHAMFER      = 0.50  # 45 deg at every socket mouth  <-- do not remove

# ---- wall build-up (v2: walls are ribbed assemblies, not bare plates) ------
WALL_FACE_T      = 2.5   # the brick plate the viewer sees
WALL_SERVICE_D   = 7.5   # ribbed cavity behind it: channels, bead pockets, coil bays
WALL_ASSEMBLY_D  = 10.0  # = FACE + SERVICE
DETAIL_MIN_T     = 1.2
STRUCT_MIN_T     = 2.0
LIGHT_BLOCK_MIN_T= 1.5   # min solid left in front of any emitter

# ---- lighting: fairy-light string (primary) -------------------------------
LIGHT_SYSTEM       = "fairy"   # "fairy" | "discrete3mm" | "both"
BEAD_POCKET_W      = 3.2   # micro-LED bead seat  (bead approx 2.0 x 4.0)
BEAD_POCKET_H      = 5.0
BEAD_POCKET_D      = 3.2
WIRE_DIA           = 0.6   # enamelled copper pair
WIRE_SLOT_W        = 1.4   # PASS-THROUGH slot on BOTH sides of every pocket
WIRE_CHANNEL_WIDTH = 3.0   # carries up to 4 strands (out + return legs)
WIRE_CHANNEL_DEPTH = 3.0
WIRE_CAPTURE_MOUTH = 2.2   # pinched mouth: wire snaps in and stays, no tape
COIL_BAY = (34.0, 46.0, 5.0)   # stow unused string length (W, H, D) x4
LED_BORE = 3.0 + 2*FIT_CLEARANCE   # retained for the "discrete3mm" option

# ---- lighting: optional RGB/CCT bar as rear sky wash -----------------------
SKY_BAR_ENABLE = True
SKY_BAR_MAX    = (90.0, 16.0, 10.0)   # cradle accepts up to this (L, W, T)

# ---- power drawer ---------------------------------------------------------
DRAWER_INNER   = (150.0, 86.0, 18.0)  # L, W, H -- 2 battery boxes + controller
BATT_BOX       = (64.0, 28.0, 17.0)   # 3xAAA default; shims for 2xCR2032

# ---- glazing / diffusers (v2: printed PLA is the default) -----------------
DIFFUSER_PRINT_T = 0.8   # natural/white PLA, 3 walls, 0 % infill
DIFFUSER_SLOT_T  = 1.2   # also takes vellum / acetate / PET / 1.0 acrylic

# ---- surface detail -------------------------------------------------------
BRICK_RELIEF       = 0.6
BRICK_LENGTH_FRONT = 18.0
BRICK_HEIGHT_FRONT = 6.0
MORTAR_GAP         = 1.2
COBBLESTONE_RELIEF = 0.8
COBBLE_SIZE_FRONT  = 10.0
RANDOM_SEED        = 20260830   # deterministic: same seed = same STLs

# ---- forced perspective ---------------------------------------------------
PERSP_STRENGTH  = 0.42
WALL_CANT_DEG   = 1.75
FACADE_LEAN_MAX = 4.0
```

### Derived envelope

| Quantity | v1 | **v2** | Note |
|---|---|---|---|
| Case cavity (X × Z × Y) | 95.6 × 231.2 × 197.8 | **95.6 × 209.6 × 197.8** | plinth grew to hold the drawer |
| Chassis envelope | 94.8 × 230.4 × 196.5 | **94.8 × 208.9 × 196.5** | |
| Wall assembly depth | 2.5 | **10.0** | face plate + service cavity |
| Clear alley, front | 88.6 | **74.8** | narrower — better proportion, 1 : 2.8 |
| Clear alley, rear (after cant) | 76.6 | **62.8** | |
| Visible aperture at rear block | ≈ 30 | **≈ 28** | after facades step in |
| Perceived depth | — | **≈ 500–600** | 2.5–3× actual |

Losing 21 mm of scene height to the drawer is the right trade: a battery swap becomes a
five-second drawer pull instead of a disassembly, and the alley proportion actually
improves.

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

**P2S dividend:** at 256 × 256 nothing needs splitting. Walls and case panels that v1
had to cut in half now print in one piece — fewer seams, fewer parts, better alignment.

| ID | Part | Size (mm) | Print | Notes |
|---|---|---|---|---|
| 00 | `Chassis_Base_Pan` | 196 × 95 × 10 | flat, no support | floor rails, wire bus, drawer roof |
| 01 | `Left_Wall` | 196 × 209 × 2.5 | flat, brick up | **one piece** on a 256 bed |
| 01R | `Left_Wall_Service_Rib` | 196 × 209 × 7.5 | flat | channels, bead pockets, coil bays; bonds/clips to 01 |
| 02 | `Right_Wall` | 196 × 209 × 2.5 | flat | mirror |
| 02R | `Right_Wall_Service_Rib` | 196 × 209 × 7.5 | flat | mirror |
| 03A | `Rear_Perspective_Block` | 62 × 84 × 46 | upright | converging facades, 4 compressed storeys |
| 03B | `Rear_Archway` | 40 × 54 × 14 | flat | the "lane continues" arch |
| 03C | `Rear_Silhouette_Screen` | 66 × 72 × 1.6 | flat | distant rooftops/chimneys, backlit |
| 03D | `Rear_Glow_Diffuser_Frame` | 68 × 76 × 6 | flat | diffuser + fairy beads **or** sky bar |
| 03E | `Sky_Bar_Cradle` | 92 × 20 × 12 | flat | optional; parametric to `SKY_BAR_MAX` |
| 04 | `Cobblestone_Floor` | 194 × 72 × 4 | flat, cobbles up | tapered, cambered, slides on 00 rails |
| 04B/04C | `Gutter_Left / _Right` | 190 × 6 × 3 | flat | drain channel + 3 grates |
| 05 | `Ceiling_Baffle` | 76 × 196 × 1.6 | flat | sky occluder, overhead sign rail, top wire race |
| 06 | `Front_Bezel_Left` | 40 × 208 × 5 | flat | **torn broken-brick edge** |
| 07 | `Front_Bezel_Right` | 40 × 208 × 5 | flat | mirror, different break pattern |
| 08 | `Front_Arch_Header` | 90 × 24 × 8 | flat | ties the bezels, hides the ceiling seam |
| 09 | `Chassis_Rear_Wall` | 94 × 80 × 2.5 | flat | closes the cartridge, wire grommet |

Wall face (01/02) and service rib (01R/02R) are separate parts on purpose: the face
prints brick-up with no supports and gets painted; the rib prints flat and stays unseen.
They join with four T3 tongues + two locating pins, so the rib can come off if you need
to re-route a string.

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

| ID | Part | Purpose |
|---|---|---|
| 40A–40F | `Light_Baffle_A..F` | snap-on caps sealing each bead pocket, 1.2 mm walls — stops cross-talk between shops |
| 41A–41D | `Diffuser_Holder_A..D` | 1.2 mm slot |
| 42A–42H | `Diffuser_Plate_A..H` | **0.8 mm printed PLA, natural/white, 3 walls, 0 % infill** — the default glazing |
| 42J–42L | `Glazing_Clear_A..C` | thin printed frame for a scrap of clear PET, for the two shop windows you want to see *into* |
| 43 | `Bus_Cover` | snaps over the base-pan wire bus |
| 44 | `Wire_Clip` ×12 | printed channel retainers |
| 45A–45D | `Coil_Bay_Cover` | traps stowed surplus string so it can't rattle or migrate |
| 46 | `Bead_Shim` ×8 | 0.5 mm packers if your bead is smaller than the 3.2 pocket |
| 47 | `String_Entry_Grommet` ×4 | plinth-to-chassis wire pass-through |

### 5.6 Outer case (50–59)

| ID | Part | Size | Note |
|---|---|---|---|
| 50 | `Outer_Left` | 200 × 240 × 2.2 | **one piece** on the P2S |
| 51 | `Outer_Right` | 200 × 240 × 2.2 | one piece |
| 52 | `Outer_Top` | 200 × 100 × 2.2 | |
| 53 | `Outer_Back` | 100 × 216 × 2.2 | **service hatch**, 2 × C4 clips |
| 54 | `Plinth_Body` | 200 × 100 × 24 | drawer housing + chassis rails |
| 55 | `Power_Drawer` | 150 × 86 × 18 | **slides out the back**; battery boxes + controller |
| 56 | `Drawer_Face` | 96 × 22 × 3 | flush black face, finger notch, detent |
| 57 | `Batt_Box_Cradle` ×2 | parametric to `BATT_BOX` | shims for coin-cell packs |
| 58A/58B | `Case_Spine_Trim_L / _R` | | hides the front vertical seams |
| 59A–59F | `Case_Clip_Insert` ×6 | | separate C4 clips |
| 59G | `Foot_Pad` ×4 | | |

Largest part 200 × 240 — fits a 256 bed flat, no supports, no tall thin walls. If you
confirm a smaller bed, `PANEL_SPLIT` flips to `True` and the same source emits
dovetail-joined halves instead.

### 5.7 Power & switch module (60–69)

No soldering required in the default build.

| ID | Part | Note |
|---|---|---|
| 60 | `Switch_Housing` | 34 × 24 × 14, clips into a keyhole in 53 |
| 61 | `Switch_Cover` | snap-on, integral cable clamp |
| 62A–62C | `Switch_Bezel_Rocker / _Slide / _Button` | swappable — pick the switch after printing |
| 62D | `Bezel_Blank` | if you just use the fairy-light packs' own switches in the drawer |
| 63 | `Jack_Plate_DC` | 5.5 × 2.1 barrel jack, for a future mains conversion |
| 64 | `Strain_Relief_Insert` | serpentine, parametric Ø3.0–4.5 cable |
| 65 | `Remote_Clip` | holds the lamp kit's IR/RF remote to the case back, if you fit the sky bar |

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
      [50 Outer_Left] -------- CASE SLEEVE -------- [51 Outer_Right]
                                        |
                                 [54 Plinth_Body]
                                        |
                   ══ chassis slides in from rear on rails ══
                                        |
   ┌───────────────── INNER CHASSIS (finished + tested) ─────────────────┐
   │                                                                     │
   │  [05 Ceiling_Baffle] ── overhead sign rail ── [30A banner, 32 chain] │
   │        |                                                            │
   │  [01 Left_Wall] + [01R Service_Rib] <-P2/T3- 10*..19*               │
   │        |                                                            │
   │  [02 Right_Wall] + [02R Service_Rib] <-P2/T3- 20*..29*              │
   │        |                                                            │
   │  [03A Rear_Block] +[03B Arch] +[03C Silhouette] +[03D Glow]         │
   │                                   +[03E Sky_Bar_Cradle] (optional)  │
   │        |                                                            │
   │  [04 Cobblestone_Floor] <-P1- 35*,36*,37*,38*,39*                   │
   │        |                                                            │
   │  [00 Chassis_Base_Pan] --> [43 Bus_Cover]                           │
   └─────────────────────────────────────────────────────────────────────┘
                                        |
              STRING A loop ↺        STRING B loop ↺
                                        |
   [55 Power_Drawer] + [57 Batt_Cradles] + [56 Drawer_Face]  ← slides out the back
                                        |
                        [53 Rear hatch] + [60-65 Switch module]
```

### Build sequence (the order the kit is designed around)

1. Print **70 Tolerance_Test_Coupon**. Pick the clearance that feels right, set it in
   `params.py`, re-export. *Everything downstream depends on this one step.*
2. Print structure (00–09), case (50–59), then decorative parts in batches.
3. Prime + paint structure: brick, stone, cobbles, weathering. **Mask every socket** —
   paint film eats 0.15–0.25 mm of fit.
4. Paint decorative parts **on the sprue handles (72)**, off the model.
5. Dry-fit every decorative part before paint fully cures — mark any tight socket.
6. Snap decorative parts into walls and floor.
7. Fit diffusers (42) and glazing (42J–42L) into their holders.
8. **Thread string A**, bead by bead, front to back: seat each bead in its pass-through
   pocket, press the wire into the 3 × 3 channel, cap with a baffle (40x) as you go.
   Then string B. Clip with 44.
9. Coil the surplus into bays 45A–45D and cover.
10. Both string tails down the bus, through grommets 47, into the drawer.
11. **Power up and test on the bench** — everything is still open and reachable.
    *Do not skip this.* Rethreading a string after the chassis closes is miserable.
12. Fit the service ribs (01R/02R) to the wall faces.
13. Assemble chassis: base pan + walls + rear block + floor + ceiling baffle.
14. Fit front bezels (06/07) and arch header (08).
15. Clip the case sleeve together (50/51/52/54/59).
16. Slide the chassis in from the rear.
17. Battery boxes into cradles (57), into drawer (55), face on (56).
18. Switch module to the hatch (60–65), clip hatch on.

Optional sky bar: fit into cradle 03E at step 13, controller into the drawer at step 17.

---

## 7. Lighting plan (v2 — fairy-light architecture)

### 7.0 Which of your two options, and why

**Use the Minetom battery fairy lights as the primary system. Do not use the printer
lamp kit for the main lighting.** Three reasons, in order of weight:

1. **It cannot get light behind individual windows.** That is the entire book-nook
   effect — twenty small pools of warm light, each trapped behind its own shopfront.
   A bar lights the *volume*, which is the one thing you must avoid.
2. **Flood light kills the depth.** Forced perspective depends on the rear being dimmer
   and cooler than the front. Even illumination flattens the alley and throws away most
   of §3.
3. **It almost certainly won't fit.** Printer chamber bars are typically 250–300 mm rigid
   aluminium channels. The chassis cavity is 94.8 mm wide and each wall service cavity is
   7.5 mm deep. Unless yours are short flexible strips with cut marks, they physically
   can't go in.

The fairy lights are, by contrast, exactly the right tool: 2 mm beads on 0.6 mm enamelled
wire, warm white, no soldering, and six strings gives you generous spares.

**But the lamp kit is not wasted.** One bar — or one cut segment, if the strip is
cuttable — mounted behind the rear silhouette screen (03C) in cradle 03E makes an
excellent **adjustable sky**. The 3000 K–6000 K range dials dusk → moonlight, and the RGB
mode gives you a green or violet "something magical is happening down the lane" setting,
against the warm shop windows in front of it. That contrast is the single best-looking
thing you can do with this build. It is `SKY_BAR_ENABLE = True`, fully optional, and the
nook works completely without it.

### 7.1 The architectural consequence: strings pass *through*, they don't terminate

This is the change that rewrites v1's plan. A discrete 3 mm LED is a dead end — one
blind bore, one wire exit. A fairy-light bead is a **point on a continuous series
circuit**: the wire arrives, the bead sits, the wire leaves. So:

- Every emitter site is a **pass-through pocket**: 3.2 × 5.0 × 3.2 seat with a 1.4 mm
  wire slot on **both** sides.
- The channel network is a **path, not a tree**. Two strings, each a loop that leaves the
  drawer, threads every pocket on its route, and returns to the drawer.
- **A fairy-light string cannot be shortened** without killing it — it's one series
  circuit. You will have 1–2 m of surplus per string. So the design includes four
  **coil bays** (34 × 46 × 5) behind the walls with snap covers (45A–45D). This is the
  detail most book-nook builds get wrong and end up hot-gluing surplus wire to the back.

### 7.2 The two routes

| String | Route (drawer → … → drawer) | Beads used |
|---|---|---|
| **A — left + front** | drawer → left grommet → up rear trunk → L attic 14A → L oriel 12A → upper sash 13A-D → L2 apothecary bay ×2 → L2 door fanlight → L1 bow window ×2 → L1 fanlight → lantern 33A → *return leg shares the channel* → drawer | 13 |
| **B — right + rear** | drawer → right grommet → R1 tall window ×2 → R1 door lamp → R2 broom shop ×2 → banner backlight 30A → lantern 34A → R upper 23A-C → R3 shop → lantern 34C → rear archway ×2 → rear distant window → drawer | 16 |

29 lit points from two of your six strings. The remaining four are spares — which is why
I'm not worried about a bead failing mid-build.

Both walls' channels are 3.0 × 3.0, so the out and return legs share one channel
comfortably (4 strands of 0.6 mm). The mouth pinches to 2.2 mm: press the wire in with a
fingernail and it stays. No tape, no glue.

### 7.3 Pass-throughs, bus, drawer

- Ø4 grommeted holes at every wall/base junction (47) — no wire is ever visible from the
  alley.
- The ceiling baffle (05) carries a top race for the overhead lanterns and the banner.
- A 4.5 mm bus channel runs the rear edge of the base pan, covered by 43, down through
  the plinth roof into the drawer.
- **Drawer (55/56):** 150 × 86 × 18 internal, slides out the back below the hatch. Holds
  two battery boxes in cradles (57) plus the sky-bar controller. Battery change = pull the
  drawer. You never open the nook again after final assembly.
- Cradle 57 is parametric to `BATT_BOX` and ships with shims, so it takes a 3×AAA box, a
  2×AA box, or a flat coin-cell pack.

### 7.4 No-see rules, enforced in the geometry

- Every pocket leaves ≥ `LIGHT_BLOCK_MIN_T` (1.5 mm) of solid toward the viewer.
- Every pocket is capped by a baffle (40x) — each shop window is an optically closed box,
  so one bead cannot wash its neighbour.
- A diffuser always sits between bead and glazing. No bare bead is on a sight line from
  the front opening.
- Brick relief never thins the wall face below 1.9 mm in front of a lit cavity.

### 7.5 One honest caveat about coin cells

If your Minetom packs turn out to use 2×CR2032 rather than AAA cells, they will be dim
and will need replacing often. The drawer makes that survivable, but the better fix is a
$3 3×AA holder wired to one string's leads — a two-wire splice, no electronics. I've
sized the drawer so an AA box fits, so this stays an option you can take later without
reprinting anything.

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
| Fits 256 × 256 × 256 (P2S) | Largest part 200 × 240. Automated bbox assertion on every export; `PANEL_SPLIT` auto-splits if you confirm a smaller bed. |
| No supports | Every part has a flat print face; overhangs held ≤ 45°; bay-window undersides corbelled, not cantilevered |
| Min thickness | 1.2 detail / 2.0 structural, asserted where checkable |
| No bridges over voids | Bay roofs and awnings print as separate flat parts and snap on |
| Nothing fragile | No clip < 2.0 thick, no peg < 2.0, no free-standing railing thinner than 1.2 |
| Layer direction | Clips oriented so layers run along the beam |
| Seam hiding | All part splits fall on mortar lines, cornices, or behind trim |

| Enclosed-chamber PLA | P2S is enclosed — run the big flat panels with the door cracked to avoid heat creep on long prints |
| Textured plate | Case panels print face-down: the textured PEI finish gives a free matte-black book-cover look |

Estimate: **~101 parts, ~11 plates, 50–65 h print time, 430–580 g PLA.** Fewer parts and
plates than v1 because the P2S bed removed every split.

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

## 12. Status — decisions resolved

All six questions are answered and locked into §2. Nothing is blocking geometry
generation.

Two measurements I'd like **when convenient** — neither blocks the build, both are
one-line parameter edits afterwards:

1. **Bed size on the P2S.** I've assumed 256 × 256 × 256. If it's smaller, `PANEL_SPLIT`
   flips itself and re-emits split panels; nothing else changes.
2. **The lamp kit's bar dimensions and voltage** (length × width × thickness; USB 5 V,
   12 V or 24 V), and whether the strip has cut marks. Only affects the optional sky-bar
   cradle 03E. If the bars turn out to be long rigid aluminium, we simply leave
   `SKY_BAR_ENABLE = False` and the nook is complete without it.

One thing worth checking before you print: whether the fairy-light bead really is about
2 × 4 mm. Pocket 46 shims cover a smaller bead; a much larger one is a one-line change to
`BEAD_POCKET_*`.
