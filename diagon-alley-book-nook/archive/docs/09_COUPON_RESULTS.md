# Fit coupon — printed results

The kit is gated on this plate: nothing over 10 g gets printed until a coupon assembles
in the hand. This file records what each plate asked, what came back, and what it
changed. `coupon.py` builds the current plate; earlier plates are in git history.

---

## Plate 1 — six-station ladder, A/B shape pair, real wall tile

18 pieces, 36 g. Printed on a Bambu P2S, 0.4 mm nozzle, Generic PLA, from
`out/coupon/FIT_TEST.3mf`.

### What came back

| Station | Reported |
|---|---|
| 0.20 | goes in, falls out when turned over |
| 0.25 | holds a moment, then falls out |
| 0.30 | does not come out; wiggles a little |
| 0.35 | holds a moment, then falls out |
| 0.40 | does not come out; slightly looser than 0.30 |
| 0.45 | does not come out; slightly tighter than 0.40 |
| A/B round (`RND`) | goes in, falls out when turned over, "almost a perfect shape match" |
| A/B square (`SQR`) | goes in, falls out when turned over, "the shape is not perfectly aligned" |
| 13A frame in the wall tile | fits well |

### The ladder measured the wrong thing

`_socket_block()` passed its clearance to the **square** bore only. The round branch
called `socket_p1_solids()` with no clearance argument, so every round socket on the
plate was cut at `params.FIT_CLEARANCE`. Measured cross-sections confirm it: all seven
round bores came out at **6.4064 mm²**, and the six ladder labels were decoration.
(The square bore really was cut at 0.30: 8.06 mm².)

### What it says anyway

Seven identical sockets, seven identical pegs, one plate, one filament, one hour.
**Three held the peg and four dropped it.**

That is a cleaner experiment than the one intended, and its result is stronger. The
scatter between one socket and the next is wider than the entire 0.20–0.45 mm range the
ladder was built to explore, so **no nominal clearance gives a repeatable press fit on
a 2.4 mm peg on this machine.** Picking a number off a ladder — the thing this coupon
existed to do since the project began — could never have worked.

The `RND` / `SQR` pair still reads, because it was never about retention. The square
bore was cut 0.05 mm *looser* per side and still would not sit square on its peg, while
the round one was described as a near-perfect shape match. That is the radiused internal
corner, seen directly, and it settles the redesign: **round is right.**

And the 13A frame seating in a tile cut from the real left wall is the first thing in
this project to physically assemble.

---

## Plate 2 — crush ribs in a round bore

26 pieces, 29 g.

A crush rib is the standard answer to exactly the scatter plate 1 measured: it stands
proud of the bore wall by the clearance *plus* a fixed bite, so it reaches the peg
whether that particular bore printed tight or loose, and shears to suit. The kit used to
carry ribs and they were removed as the suspected cause of the failure. That was
half wrong — the ribs were **rectangular, in a rectangular bore whose corners the nozzle
could not cut**. It is that pairing that failed. On a round bore the rib has nothing to
fight.

| Station | Bore | Clearance/side | Asks |
|---|---|---|---|
| `P30` | plain | 0.30 | the control — expected to drop the peg |
| `R30` | 3 ribs | 0.30 | same hole, ribbed: does it hold? |
| `R40` | 3 ribs | 0.40 | goes in easily; do the ribs still hold it? |

Three copies of every P1 station, because one sample is what got us here, and the same
`P30`/`R30` comparison twice more on **P2** — the pair mount every window and door in
the kit actually uses, which the P1-only ladder never tested.

Every handle carries the same peg; only the bores differ, so any handle fits any block
and one peg can be tried in two sockets.

### How to read it

Press each peg in by thumb — no tool, no tapping — then turn the block over.

1. Does `P30` drop the peg? (If it holds, this plate is inside the noise again and the
   answer is more copies, not more stations.)
2. Do `R30` and `R40` hold where `P30` does not, on all three copies?
3. Does a ribbed socket still accept the peg by thumb, or does it need forcing?

If ribbed holds and plain does not, `FIT_CLEARANCE` goes to the looser of the two that
worked and ribs go back into `lib/mount.py` for the whole kit. If ribbed is a coin flip
too, then friction is not the mechanism and the pegs become alignment features with
adhesive doing the holding — which is how most book nooks are built, and no worse a kit
for it.

---

## Standing lesson

Both coupon bugs — the clearance never reaching the bore, and the lead-in counterbore
built at the blind end instead of the mouth — were invisible in CAD and invisible in the
slicer. Only a printed part and a person's thumb found them. `coupon.py` now measures
the peg into its own socket with the real physical motion before it will write a file,
which is the check `lib/mount.py`'s own header has been asking for since the beginning.

---

## What the tile found that the ladder was not looking for

Laid in the tile, the 13A frame covers a round socket at its lower right edge. It is not
19C's, which is 6.4 mm clear, and it is not 13A's own three mounts, which the frame is
*supposed* to cover. It belongs to **31A, Bracket_Scroll_A**, and the frame overlaps it
by 1.5 × 1.5 mm. Nothing can ever mount there.

That is not one bad coordinate. The facade elements get their apertures and sockets from
`data.facade.LEFT` / `RIGHT`; the signs, brackets, lanterns and wall-hung props get
theirs from `SIGNS`, `BRACKETS`, `LANTERNS` and `PROPS`. Both cut holes in the same wall
face and **nothing had ever compared the two tables**:

| Wall | Hung mounts | Fouled |
|---|---|---|
| Left | 12 | 11 |
| Right | 9 | 3 |

Every sign, bracket, lantern and prop on the left wall except the boot scraper has its
socket under a window, a door, a fascia or an awning. 38A and 38B — the notice board and
the poster layer that overlays it — are at the same (u, z) and share a single socket:
two pegs, one hole.

`verify.check_mount_crowding()` now compares them, and `kit.wall_mount_rows()` exists so
each socket has an owner to name — the loop that built them returned bare solids, which
is the mechanical reason this family was invisible to every check in the file.

Fixing the placement is a design pass, not a nudge: a swing sign and the bracket that
carries it have to move together, a fascia nameplate belongs on the fascia board rather
than on the wall behind it, and the poster layer belongs on the notice board. That
happens when the kit is regenerated after the coupon settles, and the check will say
when it is done.

---

## Plate 2 — printed. The answer is glue.

| Station | Reported |
|---|---|
| P1 `P30` ×3 | all three drop the peg |
| P1 `R30` ×3 | all three hold — but very tight, and **cannot be removed once inserted** |
| P1 `R40` ×3 | all three hold — same, cannot be removed |
| P2 `P30` ×2 | both drop the peg |
| P2 `R30` ×2 | **will not insert at all** |

The ribs work. They work far too well. On one peg they turn the joint permanent; on two
pegs and six ribs they turn it impossible. A joint that can only be assembled once, or
not at all, is not a joint on a kit with 182 parts and a first-time builder.

And plain 0.30 does exactly what it should: it enters every time on both mounts and
falls out every time. That is a perfect **locating** feature and a hopeless retaining
one — which is fine, because there is no reason a book-nook facade has to come apart.

### The decision

**P1 and P2 locate. Glue retains.** `FIT_CLEARANCE` and `DECORATIVE_CLEARANCE` are
0.30. `ribs=` stays in `lib/mount.py`, off, with this result recorded next to it. T3
keeps its ribs and its detent: it is a sliding joint, it was validated on a printed
coupon, and nothing here touches it.

### What the change moved

Raising the clearance to 0.30 broke P1's key, and `check_keying` caught it. The flat
only keys while `P1_FLAT + clearance < P1_D/2`; at the old flat of 1.0 that meant
clearance under 0.20, so the key had **already** been doing nothing at the kit's 0.25
and nobody knew. The flat is 0.6 now, which leaves 0.30 mm of interference the wrong way
round and keeps 3.6 of the peg's 4.5 mm² of section. `check_keying` sweeps the clearance
range instead of testing today's number, and reports where each key gives out: P1 above
0.45, P2 above 0.35.

`check_grip_across_clearances` is gone. In its place `check_glue_gap_across_clearances`
asks the opposite question — that the peg enters with nothing fouling, and that the
annulus left round it is a gap gel cyanoacrylate can bridge.

### Gluing

- **Gel cyanoacrylate**, not thin. Thin CA wicks along the joint and out onto the brick
  face before it sets; gel stays in the 0.30 mm annulus where it is put.
- One small bead **in the socket**, not on the peg — a bead on the peg is scraped off
  by the bore on the way in and ends up as a ring of glue on the wall face.
- Dry-fit the whole wall first. Every part goes in and comes out freely, which is the
  point of 0.30, so there is no cost to laying the entire facade out unglued, looking at
  it, and only then gluing.
- The part is squared by its **back face against the plate**, not by the peg. That is
  why `check_facade_seating` matters more under a glued design than it did under a
  pressed one.
