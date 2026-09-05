"""Master parameters for the Diagon Alley book nook. All dimensions in millimetres.

Every number in this file carries its PROVENANCE, because the single most expensive
mistake in this project was a number whose provenance nobody could see:
`FIT_CLEARANCE = 0.25` sat at "its initial guess for the entire project" while 119 parts
were built on it. Nothing in the code said it was a guess.

So a parameter is not a float here, it is a float that knows where it came from:

    MACHINE   read out of the slicer profile at import. NEVER retyped by hand, so it
              cannot drift from what actually slices.
    MEASURED  printed on this machine and measured. Calipers or the bench.
    CHOSEN    a design decision. Free to change; changing it changes the model, not
              the truth.
    ASSUMED   not validated yet. Carries the R-number that settles it, and
              `assumptions_in_critical_use()` will fail the build if load-bearing
              geometry depends on one.

Arithmetic works normally -- Param subclasses float -- so `PEG_D + 2 * FIT_CLEARANCE`
is just a float, and CadQuery never knows the difference.

    python params.py            print every parameter with its provenance
    python params.py --assumed  print only what is still unvalidated
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MACHINE = "machine"
MEASURED = "measured"
CHOSEN = "chosen"
ASSUMED = "assumed"

REGISTRY = {}


class Param(float):
    """A float that remembers where it came from."""

    def __new__(cls, value, src, why, ref=""):
        obj = super().__new__(cls, value)
        obj.src, obj.why, obj.ref, obj.name = src, why, ref, None
        return obj

    def __repr__(self):
        return f"{float(self):g}"


# ------------------------------------------------------------------ the profile --
# R-3: this is still the P1S-era export vendored during attempt two. Re-export it from
# Bambu Studio for the actual P2S before anything is printed. Until that happens every
# MACHINE value below carries the R-3 caveat, which is the provenance system earning
# its keep on day one.
PROFILE_PATH = os.path.join(HERE, "profiles", "P2S_project_settings.config")
_FALLBACK = os.path.join(HERE, "archive", "profiles", "P2S_project_settings.config")

PROFILE_IS_STALE = False
_path = PROFILE_PATH
if not os.path.exists(_path):
    if not os.path.exists(_FALLBACK):
        raise SystemExit(
            "No slicer profile found.\n"
            f"  expected: {PROFILE_PATH}\n"
            "Do R-3: save a project from Bambu Studio for the P2S, unzip it, and copy\n"
            "Metadata/project_settings.config to that path."
        )
    _path = _FALLBACK
    PROFILE_IS_STALE = True

with open(_path, encoding="utf8") as fh:
    PROFILE = json.load(fh)

_R3 = "R-3 (profile is the P1S-era export; re-export for the P2S)" if PROFILE_IS_STALE else ""


def machine(key, why, index=None):
    """Read a machine fact from the slicer profile. Do not retype these."""
    if key not in PROFILE:
        raise KeyError(f"{key!r} is not in the slicer profile -- the profile changed "
                       f"shape, or the key was renamed. Do not guess it.")
    v = PROFILE[key]
    if isinstance(v, list):
        v = v[0 if index is None else index]
    if isinstance(v, str) and v.endswith("%"):
        v = float(v[:-1]) / 100.0
    return Param(float(v), MACHINE, why, _R3)


# ================================================================ the machine ==
NOZZLE        = machine("nozzle_diameter", "what the hotend has in it")
LAYER         = machine("layer_height", "")
FIRST_LAYER_H = machine("initial_layer_print_height", "")
LINE_W        = machine("line_width", "nominal extrusion width")
OUTER_LINE_W  = machine("outer_wall_line_width", "the bead that forms a visible face")
FIRST_LINE_W  = machine("initial_layer_line_width", "wider, and it is why elephant foot exists")
WALL_LOOPS    = machine("wall_loops", "")
ELEPHANT_FOOT = machine("elefant_foot_compensation",
                        "squeeze-out at the first layer. CLOSES a socket mouth")
XY_HOLE_COMP  = machine("xy_hole_compensation",
                        "0 means nothing corrects hole shrinkage -- the model must")
XY_CONT_COMP  = machine("xy_contour_compensation", "")
INFILL        = machine("sparse_infill_density", "")
BED_Z         = machine("printable_height", "")

# printable_area is a polygon: ['0x0', '256x0', '256x256', '0x256']
_corners = [tuple(float(n) for n in p.split("x")) for p in PROFILE["printable_area"]]
BED_X = Param(max(c[0] for c in _corners), MACHINE, "from printable_area", _R3)
BED_Y = Param(max(c[1] for c in _corners), MACHINE, "from printable_area", _R3)

# ------------------------------------------- what the machine's geometry implies --
# This block is the answer to the retrospective's sharpest line: "Every check measured
# the model. None modelled the printer."
INTERNAL_CORNER_R = Param(
    LINE_W / 2.0, MACHINE,
    "a round nozzle cannot cut a sharp internal corner. THIS number ended attempt one: "
    "a square peg binds on the diagonal of a square socket long before the flats meet",
    _R3)
MIN_WALL = Param(WALL_LOOPS * LINE_W, MACHINE, "two perimeters, nothing between them", _R3)

# ================================================================== measured ==
# Printed on this machine, in PLA, and read with calipers or a thumb. ~70 g of filament
# paid for this block and it survives the rewrite; see archive/docs/09_COUPON_RESULTS.md.
FIT_CLEARANCE = Param(
    0.30, MEASURED,
    "per side, and the joint is GLUED not pressed. Coupon plate 1: seven sockets cut to "
    "one number, three held and four dropped -- the scatter between sockets is wider "
    "than the whole 0.20-0.45 range, so no clearance gives a repeatable press fit",
    "coupon plate 1 + 2")
CRUSH_RIBS = False   # measured, not a parameter: plate 2 made the joint permanent on one
                     # peg and impossible on two. Kept as a named constant so the reason
                     # travels with the decision.
XY_REPEATABILITY = Param(
    0.20, MEASURED, "+/- on a well-calibrated machine. Any fit tighter than this is a "
    "coin toss, not a joint", "attempt one bench")
HOLE_SHRINK_MIN = Param(0.10, MEASURED, "per side; holes print undersize", "bench")
HOLE_SHRINK_MAX = Param(0.30, MEASURED, "per side; the bad case, and it is common", "bench")
MIN_FEATURE_T = Param(1.2, MEASURED, "thinnest standalone feature that survives handling", "bench")
MIN_FEATURE_L = Param(2.0, MEASURED, "and it must be at least this long", "bench")
TYPE_STEM_RATIO = Param(
    0.12, MEASURED, "bold serif stem as a fraction of glyph size. This is what makes "
    "3.5 mm the floor FOR THAT FACE -- a fatter face goes smaller", "attempt two")

# ===================================================================== brim ==
# Four prints were damaged or wasted by brim behaviour and the cause was different every
# time. All of it lives here, because there were once THREE definitions of "needs a brim"
# in three files that disagreed, and a part that had already failed on the bed was warned
# about by one, listed without a brim by another, and shipped with no brim by the third.
# ONE definition, in ONE place. Do not write a second one.
BRIM_WIDTH = machine("brim_width", "outer only, on the parts that need it")
BRIM_TYPE_WANTED = "outer_only"     # the profile ships `auto_brim`; it must be overridden
BRIM_TYPE_IN_PROFILE = PROFILE.get("brim_type")

# B3. The one that cost a whole plate: at 6 mm spacing the brims of neighbouring parts
# merged and 22 of 64 left-facade parts fused into a single raft. A raft that peels takes
# every part on it with it.
PLATE_SPACING = Param(
    2 * BRIM_WIDTH + 1.0, MEASURED,
    "2 x brim + 1. At 6 mm the brims of neighbours merge -- 22 of 64 parts fused into one "
    "raft. Costs an extra plate and is worth it", "B3")

# B6. Thresholds that flagged 49 of 182 parts. Each was paid for by a part that came off
# the bed, so they are MEASURED, not tuned.
BRIM_MIN_BED_AREA   = Param(25.0, MEASURED, "first-layer area below this cannot hold on", "B6")
BRIM_TIPPY_RATIO    = Param(2.0, MEASURED, "height > this x the narrower footprint side", "B6")
BRIM_WIDE_LEN       = Param(150.0, MEASURED, "long parts lift at the corners", "B6")
BRIM_WIDE_MAX_H     = Param(6.0, MEASURED, "...if they are also flat", "B6")
BRIM_WIDE_BED_FRAC  = Param(0.25, MEASURED, "...or barely touch their own footprint", "B6")
BRIM_STRIP_RATIO    = Param(8.0, MEASURED, "length > this x width makes a strip", "B6")
BRIM_STRIP_MAX_W    = Param(8.0, MEASURED, "...and a narrow one", "B6")
BRIM_TOPHEAVY_AREA  = Param(50.0, MEASURED, "downward-facing area above this", "B6")
BRIM_TOPHEAVY_RATIO = Param(4.0, MEASURED, "...and more than this x the bed area", "B6")


def needs_brim(stats, force=None):
    """THE definition. `stats` needs bed_area, height, foot_w, foot_l, down_area.

    `force` is an explicit per-part override and it wins outright -- B4: a brim rule that
    scores bed area, height and slenderness cannot see the 4 mm channels inside a sprue's
    own outline. Sixteen pins on a runner were torn off by their own brim flooding between
    them, so no pin joint on that plate could be tried at all. Sprues, combs and anything
    with internal gaps pass force=False; their runner is the adhesion.
    """
    if force is not None:
        return bool(force), "explicit override"
    bed, h = stats["bed_area"], stats["height"]
    w, l = sorted((stats["foot_w"], stats["foot_l"]))
    if bed < BRIM_MIN_BED_AREA:
        return True, f"footprint {bed:.0f} mm2 under {float(BRIM_MIN_BED_AREA):.0f}"
    if h > BRIM_TIPPY_RATIO * w:
        return True, f"tippy: {h:.0f} tall on a {w:.0f} mm side"
    if l > BRIM_WIDE_LEN and (h < BRIM_WIDE_MAX_H or bed < BRIM_WIDE_BED_FRAC * (w * l)):
        return True, f"wide and thin: {l:.0f} mm long"
    if l > BRIM_STRIP_RATIO * w and w < BRIM_STRIP_MAX_W:
        return True, f"a strip: {l:.0f} x {w:.1f}"
    if stats["down_area"] > BRIM_TOPHEAVY_AREA and \
       stats["down_area"] > BRIM_TOPHEAVY_RATIO * bed:
        return True, f"top-heavy: {stats['down_area']:.0f} mm2 overhanging {bed:.0f}"
    return False, ""


# ==================================================================== chosen ==
# Design decisions. Changing these changes the model; they are not facts about anything.
# Q-4 answered: 6" W x 11" H x 12" D. Deliberately larger than a typical book nook
# (4-5" W x 8-10" H x 7-10" D) because projecting bays, readable signs, LEDs, cobbles and
# an entrance arch all need room. The 12" depth is the one that matters most -- a 7-8"
# nook has no room to establish the alley.
BOOKNOOK_WIDTH  = Param(203.2, CHOSEN, "8 in. X. Split the difference between the 6 in "
                                       "and 9.5-10 in briefs: 6 gave no room for deep "
                                       "shopfronts, 9.5+ made the plan nearly square and "
                                       "ate the shelf")
BOOKNOOK_HEIGHT = Param(266.7, CHOSEN, "10.5 in. Z")
BOOKNOOK_DEPTH  = Param(304.8, CHOSEN, "12 in. Y, front to back -- this is the one that "
                                       "buys the forced perspective")
SHELL_THICKNESS = Param(2.2, CHOSEN, "outer case wall")
PLINTH_HEIGHT   = Param(8.0, CHOSEN, "a foot, NOT a drawer. The electronics moved to the "                                     "rear service cavity behind the forced-perspective "                                     "end wall, which frees 16 mm straight into building "                                     "height -- and the brief is explicit that the "                                     "buildings stay tall while the alley narrows")
BASE_PAN_T      = Param(10.0, CHOSEN, "floor build-up under the cobbles")
REAR_BAY_D      = Param(20.0, CHOSEN, "rear service cavity: the visible end of the alley "                                      "sits this far in front of the exterior rear panel. "                                      "From the front it reads as a dark alley continuing "                                      "through an arch; behind it is the electrical "                                      "cabinet -- junctions, controller, USB")
SLIP_CLEARANCE  = Param(0.35, CHOSEN, "chassis sliding into the case, per side")
WALL_FACE_T     = Param(2.5, CHOSEN, "the brick plate the viewer sees")
RIB_GAP         = Param(2.5, CHOSEN, "clear gap behind the plate")
WALL_SERVICE_D  = Param(5.0, CHOSEN, "open service lattice behind the gap")
WALL_CANT_DEG   = Param(3.6, CHOSEN, "takes the alley from 6.9 in at the front to about "
                                     "5.5 in at the rear")
STOREFRONT_PROJ = Param(35.0, CHOSEN, "how far a storefront module stands into the alley. "
                                      "It is ALSO the light-diffusion path: the bay is "
                                      "hollow, so the LED sits at the wall plane and "
                                      "throws 35 mm forward to the glazing. The wall does "
                                      "not have to be thick to diffuse")
OUTER_SKIN_T    = Param(2.5, CHOSEN, "removable brick panel: the finished outside AND the "
                                     "access hatch for the wiring behind it")
WIRE_CAVITY_D   = Param(6.0, CHOSEN, "between inner wall and outer skin. WIRING ONLY -- "
                                     "diffusion is STOREFRONT_PROJ. Sizing this for "
                                     "diffusion instead would cost 18 mm of alley")
WIRE_CHANNEL_W  = Param(6.0, CHOSEN, "concealed vertical channel in each wall module, "
                                     "dropping into the floor channel. The floor is the "
                                     "wiring highway; nothing runs across visible brick")
ROOF_BAND_H     = Param(34.0, CHOSEN, "the top band of facade carried by the removable "
                                      "roof section instead of by the wall module. Not "
                                      "cosmetic: a full-height module is 245.8 mm and "
                                      "255.8 with its brim on a 256 bed. Splitting the "
                                      "wall lengthways does not help -- height is the "
                                      "binding dimension -- so the roof takes the top and "
                                      "the seam lands at the roofline, where a real "
                                      "building has one")
ROOF_LIP_D      = Param(10.0, CHOSEN, "concealed inner lip on the removable roof. Ambient "
                                      "LEDs sit behind it, so a viewer sees the glow on "
                                      "the buildings and cobbles, never the emitter")
LIT_WINDOWS_MAX = Param(7.0, CHOSEN, "light 5-7 KEY windows, not every one. Selective "
                                     "lighting reads as atmosphere; lighting everything "
                                     "reads as a lamp")
ARCH_OPENING_W  = Param(182.0, CHOSEN, "7.17 in. clear, out of 8 in. exterior -- thin brick "
                                       "piers. Deliberately WIDER than the alley so the "
                                       "reveal does not shadow the near shopfronts")
PERSP_STRENGTH  = Param(0.42, CHOSEN, "element scale at the rear = 1 - this. The thing "
                                      "that makes a 197 mm alley read as a street")
BRICK_RELIEF    = Param(0.6, CHOSEN, "mortar groove depth. 0.5-0.8 is the useful band")
COBBLE_RELIEF   = Param(0.8, CHOSEN, "stone height above the joint")
COBBLE_CHAMFER  = Param(0.4, CHOSEN, "top-edge bevel -- this is what catches dry-brushing")

# =================================================================== assumed ==
# NOT VALIDATED. Each carries the research item that settles it. Nothing load-bearing
# should depend on one of these without the R-number being closed first.
PEG_D = Param(3.0, ASSUMED,
              "up from 2.4: published tolerance tables start at 6 mm and small features "
              "round off below the nozzle width, so bigger is more forgiving", "R-5")
PEG_L = Param(4.0, ASSUMED,
              "INTEGRAL peg -- the whole length enters ONE socket, so with a 0.5 lead-in "
              "this grips over 3.5 mm. This is the wall-peg case (sign, flat trim)", "R-5")
PIN_L = Param(5.0, ASSUMED,
              "LOOSE pin -- the length is SPLIT between two sockets, so each side gets "
              "half minus a chamfer. 4.0 would give only 1.5 mm per side, under the 2 mm "
              "floor; 5.0 gives exactly 2.0. These are different numbers and conflating "
              "them is how the engagement problem hid in the first place", "R-5")
LEAD_IN_CHAMFER = Param(0.50, ASSUMED, "45 deg at every socket mouth. Do not remove -- but "
                        "note it eats engagement depth, which is R-5's whole point", "R-5")
BLIND_BORE_CONE = Param(60.0, ASSUMED,
                        "degrees of included angle at a blind bore's end, so a "
                        "downward-facing socket is self-supporting and the pin gets a "
                        "positive depth stop", "R-5")
TEXT_DEPTH = Param(0.6, ASSUMED,
                   "exactly 3 layers at 0.2, so an AMS colour change lands on a clean "
                   "boundary. 0.5 was 2.5 layers and could not", "R-15")
TEXT_STROKE_MIN = Param(0.5, ASSUMED,
                        "the REAL legibility limit is stroke, not glyph height: a stem "
                        "must be at least one extrusion and comfortably more", "R-10")
PAINT_PER_COAT = Param(0.0, ASSUMED,
                       "UNKNOWN. D3 turns on 'two coats close a 0.30 clearance', which is "
                       "a plausible number nobody has put calipers on. 0.0 here is a "
                       "placeholder that will fail its own check", "R-7")
LIGHT_CAVITY_MAX = Param(12.5, ASSUMED,
                         "the alley is only 74.9 wide; a 20-40 mm cavity would cut it to "
                         "29.9. Diffusion has to come from a diffuser, side-washing or a "
                         "frosted pane instead of from distance", "R-16")
ARCH_REVEAL_D = Param(12.0, ASSUMED,
                      "the first shopfront element sits at u=20, so a deeper reveal starts "
                      "competing with it for the grazing sightline", "R-18")
SUPPORT_THRESHOLD = Param(30.0, ASSUMED,
                          "degrees. The references split -- normal @30 and tree @15 -- and "
                          "neither has brick relief under its overhangs", "R-9")

# ================================================================== derived ==
SOCKET_D = Param(PEG_D + 2 * FIT_CLEARANCE, ASSUMED,
                 "3.0 + 0.30/side = 3.6. NOT 3.4 and NOT 3.5 -- those are 0.20 and 0.25 "
                 "per side, and 0.25 is the guessed number attempt one shipped on and "
                 "failed with. Generic guides quote 3.4-3.6 as a starting range; this "
                 "machine has measured its own answer and it is the top of it", "R-5")
SOCKET_DEPTH = Param(PEG_L + 1.0, ASSUMED,
                     "deeper than the peg is long, ON PURPOSE: the module must seat on its "
                     "flange against the wall, never bottom out on the peg tip. A peg that "
                     "bottoms holds the part proud and no amount of glue fixes it", "R-5")
PEG_ENGAGE = Param(PEG_L - LEAD_IN_CHAMFER, ASSUMED,
                   "integral peg: parallel bore actually gripping, once the mouth chamfer "
                   "is taken off", "R-5")
PIN_ENGAGE = Param(PIN_L / 2.0 - LEAD_IN_CHAMFER, ASSUMED,
                   "loose pin: gripping length PER SIDE. The one that nearly shipped short",
                   "R-5")

# The wall is a sandwich now, not a ribbed plate: storefront | glazing | inner wall |
# wiring cavity | removable outer brick skin. PLAN 6.14.
WALL_ASSEMBLY_D = WALL_FACE_T + WIRE_CAVITY_D + OUTER_SKIN_T

CASE_CAVITY_W = BOOKNOOK_WIDTH - 2 * SHELL_THICKNESS
CASE_CAVITY_H = BOOKNOOK_HEIGHT - PLINTH_HEIGHT - SHELL_THICKNESS
CASE_CAVITY_D = BOOKNOOK_DEPTH - SHELL_THICKNESS

CHASSIS_W = CASE_CAVITY_W - 2 * SLIP_CLEARANCE
CHASSIS_H = CASE_CAVITY_H - 2 * SLIP_CLEARANCE
CHASSIS_D = CASE_CAVITY_D - 2 * SLIP_CLEARANCE

SCENE_H = CHASSIS_H - BASE_PAN_T
ALLEY_D = CHASSIS_D - REAR_BAY_D
ALLEY_W_FRONT = CHASSIS_W - 2 * WALL_ASSEMBLY_D
CLEAR_WALK_FRONT = ALLEY_W_FRONT - 2 * STOREFRONT_PROJ

import math
CANT_OFFSET = ALLEY_D * math.tan(math.radians(WALL_CANT_DEG))
ALLEY_W_REAR = ALLEY_W_FRONT - 2 * CANT_OFFSET

# The wall face is the biggest single part in the kit, and whether it fits the bed in one
# piece decides whether the wall can be one object or must be panels (PLAN 6.6 / 6.9).
WALL_FACE_L = ALLEY_D
WALL_FACE_H = SCENE_H
WALL_MODULES_PER_WALL = 2      # each 12 in side wall splits into two ~6 in modules
WALL_MODULE_H = SCENE_H - ROOF_BAND_H
WALL_MODULE_L = ALLEY_D / WALL_MODULES_PER_WALL

MM_PER_IN = 25.4


def _register():
    for name, v in list(globals().items()):
        if isinstance(v, Param):
            v.name = name
            REGISTRY[name] = v


_register()


# =================================================================== guards ==
def assumptions():
    """Every parameter still resting on a guess, with the item that settles it."""
    return sorted((p for p in REGISTRY.values() if p.src == ASSUMED),
                  key=lambda p: (p.ref, p.name))


def assumptions_in_critical_use(used):
    """Fail the build if load-bearing geometry depends on an unvalidated number.

    `used` is the set of parameter names a mating feature actually consumed. This is the
    check that did not exist when FIT_CLEARANCE sat at a guess and 119 parts were built
    on it. Wire it into checks.py, not here.
    """
    return [REGISTRY[n] for n in sorted(used)
            if n in REGISTRY and REGISTRY[n].src == ASSUMED]


def _is_multiple(value, step, tol=1e-6):
    """Is `value` a whole number of `step`? Tolerant of binary floating point."""
    n = round(float(value) / float(step))
    return abs(n * float(step) - float(value)) < tol


def sanity():
    """Cheap self-checks that need no geometry."""
    bad = []
    if FIT_CLEARANCE <= XY_REPEATABILITY:
        bad.append("clearance is inside the machine's own error bar -- that is a coin "
                   "toss, not a joint (08_JOINT_DESIGN)")
    for nm, v in (("integral peg", PEG_ENGAGE), ("loose pin, per side", PIN_ENGAGE)):
        if v < 2.0:
            bad.append(f"{nm} engagement {float(v):.2f} is under the 2.0 mm floor -- R-5")
    # Binary floating point: 0.6 % 0.2 is 0.19999999999999998, not 0. A check that fails
    # a good value is worse than no check -- the retrospective has one of those in it.
    if not _is_multiple(TEXT_DEPTH, LAYER):
        bad.append(f"TEXT_DEPTH {float(TEXT_DEPTH)} is not a whole number of "
                   f"{float(LAYER)} layers, so an AMS colour change cannot land on a "
                   f"layer boundary")
    if MIN_WALL < 2 * NOZZLE:
        bad.append("MIN_WALL is under two nozzle widths")
    if PAINT_PER_COAT <= 0:
        bad.append("PAINT_PER_COAT is a placeholder -- R-7 has not been measured")
    if PLATE_SPACING < 2 * BRIM_WIDTH + 1.0:
        bad.append(f"plate spacing {float(PLATE_SPACING)} is under 2 x brim + 1 -- "
                   f"neighbouring brims will merge into a raft (B3)")
    if BRIM_TYPE_IN_PROFILE != BRIM_TYPE_WANTED:
        bad.append(f"profile ships brim_type={BRIM_TYPE_IN_PROFILE!r}; it must be "
                   f"overridden to {BRIM_TYPE_WANTED!r} at the plate AND set per object "
                   f"(B2) -- Auto gave a 15 mm2 plaque no brim and it came off the bed")
    # Not "does a one-piece wall fit" -- that decision is taken. Does the module we
    # actually build fit, at the split we actually chose?
    if WALL_MODULES_PER_WALL < 2:
        bad.append(f"a one-piece wall face is {WALL_FACE_L:.0f} x {WALL_FACE_H:.0f} on a "
                   f"{float(BED_X):.0f} bed and cannot print. WALL_MODULES_PER_WALL must "
                   f"be >= 2")
    # A tall part still has to fit WITH its brim, and the brim is 5 mm on every side.
    # Splitting a wall lengthways does not help: the binding dimension is scene height.
    brimmed = WALL_MODULE_H + 2 * BRIM_WIDTH
    if brimmed > min(BED_X, BED_Y) - 10.0:
        bad.append(
            f"a wall module is {WALL_MODULE_H:.0f} mm tall, {brimmed:.0f} mm with its "
            f"brim, on a {float(BED_X):.0f} bed. Height is the binding dimension -- "
            f"splitting the wall lengthways does NOT help. Give the removable roof "
            f"section a taller band (ROOF_BAND_H), or place the module diagonally")
    if ARCH_OPENING_W <= ALLEY_W_FRONT:
        bad.append(f"arch opening {float(ARCH_OPENING_W):.0f} is not wider than the "
                   f"{ALLEY_W_FRONT:.0f} alley -- the reveal will shadow the near "
                   f"shopfronts off-axis (PLAN 6.10)")
    # B8 is real -- elephant foot adds material at the socket mouth and hole compensation
    # is 0, so nothing corrects it. But FIT_CLEARANCE was MEASURED on printed sockets
    # against printed pegs, so all of that is ALREADY INSIDE the 0.30. Adding a second
    # compensation term would double-count it and open every joint too far. This only
    # becomes a fault if the clearance ever stops being a measured number.
    if ELEPHANT_FOOT > 0 and XY_HOLE_COMP == 0 and FIT_CLEARANCE.src != MEASURED:
        bad.append(f"elephant foot {float(ELEPHANT_FOOT)} with hole compensation 0, and "
                   f"FIT_CLEARANCE is {FIT_CLEARANCE.src}, not measured -- nothing "
                   f"corrects the material added at a socket mouth (B8)")
    return bad


if __name__ == "__main__":
    only_assumed = "--assumed" in sys.argv
    if PROFILE_IS_STALE:
        print(f"!! profile: {os.path.relpath(_path, HERE)} -- {_R3}\n")
    rows = assumptions() if only_assumed else sorted(
        REGISTRY.values(), key=lambda p: (p.src, p.name))
    src_now = None
    for p in rows:
        if p.src != src_now and not only_assumed:
            src_now = p.src
            print(f"\n--- {src_now.upper()} " + "-" * (58 - len(src_now)))
        tag = f"[{p.ref}]" if p.ref else ""
        print(f"  {p.name:<20} {float(p):>8.3f}  {tag}")
        if p.why:
            for i in range(0, len(p.why), 66):
                print(f"  {'':<20} {'':>8}  {p.why[i:i + 66]}")
    print()
    for msg in sanity():
        print(f"  FAIL  {msg}")
    print(f"\n  {len(REGISTRY)} parameters, {len(assumptions())} still assumed")
