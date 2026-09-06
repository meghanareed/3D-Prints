"""Master parameters for the inhaler fidget clicker. All dimensions in millimetres.

Same rule as the book nook next door: a parameter is not a float, it is a float that
knows where it came from. The most expensive mistake in this repo was a clearance that
sat at a guess while 119 parts were built on it, and nothing in the code said it was a
guess.

    MACHINE   read out of the slicer profile at import. NEVER retyped by hand.
    MEASURED  printed on THIS machine and measured. Calipers or the bench.
    SAMPLE    read off ref/blank_clicker_sample.3mf -- a third-party clicker that is
              known to work with a real MX switch. Stronger than a guess, weaker than
              a measurement: it was printed on an A1 mini at 0.16, not a P2S at 0.20,
              and nobody here has held the printed part.
    CHOSEN    a design decision. Free to change; changing it changes the model.
    ASSUMED   not validated yet. Carries the R-number that settles it, and
              `assumptions_in_critical_use()` fails the build if load-bearing geometry
              depends on one.

    python params.py            print every parameter with its provenance
    python params.py --assumed  print only what is still unvalidated
    python params.py --stack    print the vertical mechanism stack
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MACHINE = "machine"
MEASURED = "measured"
SAMPLE = "sample"
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
PROFILE_PATH = os.path.join(HERE, "profiles", "P2S_project_settings.config")
if not os.path.exists(PROFILE_PATH):
    raise SystemExit(
        "No slicer profile found.\n"
        f"  expected: {PROFILE_PATH}\n"
        "Save a project from Bambu Studio for the P2S, unzip it, and copy\n"
        "Metadata/project_settings.config to that path.")

with open(PROFILE_PATH, encoding="utf8") as fh:
    PROFILE = json.load(fh)


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
    return Param(float(v), MACHINE, why)


# ==================================================================== the machine ==
NOZZLE        = machine("nozzle_diameter", "what the hotend has in it")
LAYER         = machine("layer_height", "")
LINE_W        = machine("line_width", "nominal extrusion width")
WALL_LOOPS    = machine("wall_loops", "")
ELEPHANT_FOOT = machine("elefant_foot_compensation",
                        "squeeze-out at the first layer. CLOSES a socket mouth")
XY_HOLE_COMP  = machine("xy_hole_compensation",
                        "0 means nothing corrects hole shrinkage -- the model must")
BRIM_WIDTH    = machine("brim_width", "outer only, on the parts that need it")

_corners = [tuple(float(n) for n in p.split("x")) for p in PROFILE["printable_area"]]
BED_X = Param(max(c[0] for c in _corners), MACHINE, "from printable_area")
BED_Y = Param(max(c[1] for c in _corners), MACHINE, "from printable_area")

MIN_WALL = Param(WALL_LOOPS * LINE_W, MACHINE, "two perimeters, nothing between them")
INTERNAL_CORNER_R = Param(
    LINE_W / 2.0, MACHINE,
    "a round nozzle cannot cut a sharp internal corner. This is why the canister guide "
    "is ROUND: a square skirt in a square collar binds on the diagonal long before the "
    "flats meet, which is what ended attempt one on the book nook")

PLATE_SPACING = Param(
    2 * BRIM_WIDTH + 1.0, MEASURED,
    "at 6 mm the brims of neighbours merged and 22 of 64 parts fused into one raft")

# ========================================= what this machine has been measured to do ==
# Off printed parts and calipers next door. Carried across because it is the same
# printer, the same filament and the same nozzle -- see ../README.md Part 1.
XY_REPEATABILITY = Param(
    0.20, MEASURED,
    "+/- per side. Any fit depending on a dimension tighter than this is a coin toss",
    "../README.md")
HOLE_SHRINK_MIN = Param(0.10, MEASURED, "per side; holes print undersize", "../README.md")
HOLE_SHRINK_MAX = Param(0.30, MEASURED, "per side; the bad case, and it is common",
                        "../README.md")
MIN_FEATURE_T = Param(1.2, MEASURED, "thinnest standalone feature that survives handling",
                      "../README.md")
MIN_FEATURE_L = Param(2.0, MEASURED, "and it must be at least this long", "../README.md")
PRESS_FIT_CLEARANCE = Param(
    0.30, MEASURED,
    "per side, AND GLUE IT. Seven identical sockets cut to one number: three held a peg, "
    "four dropped it. No nominal clearance gives a repeatable press fit at small scale",
    "../README.md")

# ================================================================== the MX switch ==
# Everything in this block is read off ref/blank_clicker_sample.3mf, a working
# third-party clicker, by dumping its mesh and slicing it by Z. See README.md
# 'What the sample measured'. Where the SPEC proposed a different number it is noted,
# because the difference is the finding.
MX_POCKET = Param(
    14.00, SAMPLE,
    "square, below the plate. The spec proposed 14.10 nominal with a 13.95-14.25 fit "
    "coupon; the sample says the body pocket is not what retains the switch at all",
    "ref/blank_clicker_sample.3mf")
MX_POCKET_DEPTH = Param(
    6.50, SAMPLE, "plate underside to the bottom of the switch housing",
    "ref/blank_clicker_sample.3mf")
MX_PLATE_T = Param(
    1.50, SAMPLE,
    "THE retention feature. The switch clips snap UNDER a 1.5 mm plate. The spec asked "
    "for a 2.0-2.2 mm shelf, which the clips cannot reach past",
    "ref/blank_clicker_sample.3mf")
MX_CLIP_RELIEF = Param(
    0.50, SAMPLE, "per side, all four sides, over the full 1.5 mm plate band -- the "
    "room the clips need to spring into", "ref/blank_clicker_sample.3mf")
MX_STEM_CROSS_L = Param(
    4.17, SAMPLE, "socket arm length, over a 4.10 nominal stem",
    "ref/blank_clicker_sample.3mf")
MX_STEM_CROSS_W = Param(
    1.55, SAMPLE, "socket arm width, over a 1.17 nominal stem -- 0.19/side, generous, "
    "and this is the joint that has to survive every press the fidget ever gets",
    "ref/blank_clicker_sample.3mf")
MX_SOCKET_DEPTH = Param(
    4.92, SAMPLE, "blind. DEEPER than the stem is tall, so the cap seats on the stem "
    "shoulder and never bottoms out in its own socket", "ref/blank_clicker_sample.3mf")
MX_BOSS_OD = Param(5.59, SAMPLE, "the receiver boss around the cross socket",
                   "ref/blank_clicker_sample.3mf")
MX_BOSS_MOUTH_OD = Param(6.19, SAMPLE, "flared lead-in at the boss mouth",
                         "ref/blank_clicker_sample.3mf")

MX_HOUSING_SQ = Param(
    15.60, ASSUMED, "top housing, above the plate. Sets the smallest hole the switch can "
    "be passed through and therefore the whole insertion strategy", "R-1")
MX_ABOVE_PLATE = Param(
    5.00, ASSUMED, "plate top face to the top of the switch housing", "R-1")
MX_STEM_BASE = Param(
    3.50, ASSUMED, "housing top to the bottom of the cross. The sample's boss mouth sits "
    "exactly here, which is the reason to believe it", "R-1")
MX_STEM_TOP = Param(
    6.90, ASSUMED, "housing top to the tip of the stem (18.5 overall - 11.6 housing)",
    "R-1")
MX_TRAVEL = Param(4.00, ASSUMED, "the switch's own bottom-out. The printed stop must "
                  "arrive BEFORE this", "R-1")
MX_ACTUATE = Param(2.00, ASSUMED, "where the click happens", "R-1")

# The sample has a solid floor 1.0 mm under its switch pocket, which only works if the
# switch has no pins -- and the clicker the sample links to is a bare module. A real MX
# switch carries two metal pins and a centre post below the housing. switch.self_test()
# found this by standing the stand-in in the mount and measuring the overlap.
PIN_RELIEF_D = Param(9.0, ASSUMED, "clears both pins and the centre post", "R-1")
PIN_RELIEF_DEPTH = Param(3.5, ASSUMED, "below the pocket floor. Only needed where the "
                         "mount is monolithic -- Part B's pocket is open underneath and "
                         "the pins fall into the body's own cavity", "R-1")

# ============================================================== the canister button ==
CANISTER_OD = Param(19.0, CHOSEN, "spec section 3: 18-19. A real MDI canister is ~20.5")
CANISTER_EXPOSED = Param(20.0, CHOSEN, "spec section 3: 18-22, above the body top face")
CANISTER_WALL = Param(1.8, CHOSEN, "spec section 6: 1.6-2.0")
CANISTER_TOP_T = Param(2.2, CHOSEN, "spec section 6: 2.0-2.4")
CANISTER_TOP_CHAMFER = Param(1.0, CHOSEN, "the rounded canister crown")

# The hard stop is TWO LUGS, not a flange. A full flange has to be wider than the
# canister, and a bore wide enough to take it does not fit across a 22-24 mm body depth
# -- that arithmetic is what killed the first version of this block. Lugs put the stop on
# the body's WIDE axis, where there is room, and leave the depth alone. They run in two
# blind slots whose ceiling is the up-stop and whose floor is the down-stop.
LUG_PROUD = Param(1.0, CHOSEN, "radial, past the canister OD")
LUG_W = Param(5.0, CHOSEN, "circumferential. Two of them, on +X and -X")
LUG_H = Param(4.0, CHOSEN, "tall enough to spread the stop load over real material")

GUIDE_CLEARANCE = Param(
    0.30, ASSUMED,
    "per side, radial, on the collar bore AND in the lug slots. Spec section 7 starts "
    "here; the sample runs 1.00/side on a square skirt. 0.30 is only 1.5x this machine's "
    "own XY error bar", "R-2")
GUIDE_HEIGHT = Param(
    10.0, CHOSEN,
    "how deep the canister skirt sits in the collar AT REST -- the anti-wobble number. "
    "Spec section 7 says 8-12 for the collar; this is the engagement, which is the thing "
    "that actually resists an off-centre press")
# There is no UP stop and no slot ceiling. There was, until the assembly order was
# worked through: a lug that is captured under a ceiling cannot be got in past that
# ceiling, and a bayonet twist is not available because the stem is already holding the
# canister by the time it is down. So the slots run open to the top face and the MX stem
# retains the canister -- which is what an MX stem does for every keycap ever made.

BUTTON_TRAVEL = Param(
    3.4, CHOSEN,
    "spec section 8 asked for 3.5-3.8 against a switch that bottoms out at 4.0. That "
    "leaves 0.2-0.5 mm of margin on a machine whose XY error bar is 0.20. 3.4 keeps "
    "0.6 mm, so the PRINTED stop takes the abuse and not the switch")
REST_GAP = Param(
    0.4, CHOSEN,
    "canister rim above the switch housing at FULL PRESS. Below this the rim lands on "
    "the switch, which is the thing the hard stop exists to prevent")

# ======================================================================== the body ==
BODY_HEIGHT = Param(63.0, CHOSEN, "spec section 18")
BODY_WIDTH = Param(29.0, CHOSEN, "spec section 18")
BODY_DEPTH = Param(
    24.0, CHOSEN,
    "spec section 18 said 22, and 22 does not fit: a Ø19 canister plus 2 x 0.30 "
    "clearance leaves 1.2 mm of wall front and back against a 2.2 mm BODY_WALL. 24 is "
    "1 mm over the spec's stated range and is the smallest number that keeps the wall")
BODY_WALL = Param(2.2, CHOSEN, "spec section 18")
BODY_CORNER_R = Param(4.0, CHOSEN, "spec section 4: 3-5")

MOUTH_LENGTH = Param(24.0, CHOSEN, "spec section 18, projection from the body face")
MOUTH_CAVITY_DEPTH = Param(10.0, CHOSEN, "spec section 5: 8-12, and it TERMINATES")
MOUTH_OPEN_W = Param(21.5, CHOSEN, "spec section 3: 20-23")
MOUTH_OPEN_H = Param(11.5, CHOSEN, "spec section 3: 10-13")

PANEL_CLEARANCE = Param(0.25, ASSUMED, "service panel mating surfaces", "R-4")

# --- Part B, the switch carrier -------------------------------------------------
# An MX switch loads DOWNWARD through its plate: the 13.9 mm below-plate body passes the
# 14.0 cutout and the 15.6 mm top housing lands on the band. So the switch cannot be
# fitted through the canister collar -- 15.6 square is 22.06 across the diagonal and the
# collar bore is 19.6 -- and it cannot be pushed up from below either, because the top
# housing is wider than the cutout it would have to come through.
#
# So the body does not own the plate band. A CARRIER owns it: the switch clips into the
# carrier in free air, and the loaded carrier slides in through a window in the back of
# the body. The alternative -- splitting the band and sliding the switch in sideways --
# throws away the unbroken 1.5 mm ring that is the only thing retaining the switch.
CARRIER_WALL = Param(2.0, CHOSEN, "material around the pocket, in the carrier")
CARRIER_W = Param(MX_POCKET + 2 * CARRIER_WALL, CHOSEN, "derived")
CARRIER_H = Param(MX_PLATE_T + MX_POCKET_DEPTH, CHOSEN, "derived: band plus pocket")

# ============================================================================ text ==
TEXT_RAISE = Param(
    0.60, CHOSEN,
    "spec section 12. Three layers at 0.20 -- and NOT a whole number of layers at the "
    "0.16 the spec recommends in section 16, which is the contradiction sanity() fails on")
# Settled by the book nook's plate 1 and promoted into ../README.md. These are the
# numbers that made the spec's lettering plan impossible, so they sit above the sizes
# rather than below them.
TEXT_STROKE_MIN = Param(
    0.70, MEASURED,
    "stroke, not glyph height, is the limit. A four-size ladder located it: 0.30 and "
    "0.36 mm strokes printed as blobs, 0.48 held partially, 0.72 held. One extrusion "
    "(0.42) is the floor; 0.70 is where it is reliable", "../README.md, plate 1")
TYPE_STEM_RATIO = Param(
    0.12, MEASURED,
    "a bold serif stem is this fraction of its glyph size. Conservative for a face as "
    "heavy as Arial Black, which is the point -- R-5 has not measured the face in use",
    "../README.md")
TEXT_SIZE_MIN = Param(
    6.0, MEASURED,
    "glyph height that actually reads. Follows from TEXT_STROKE_MIN and TYPE_STEM_RATIO, "
    "not chosen separately", "../README.md, plate 1")
TEXT_ADVANCE_EM = Param(
    0.72, MEASURED,
    "advance width per character, all-caps bold. 0.62 was assumed twice next door and "
    "ran the lettering off the plate both times. Measure text against the thing it sits "
    "on", "../README.md, plate 1")

# The spec asked for 3-3.5 mm text with WHEEZY at 4-5, on a 29 mm wide face. At 3.5 the
# stem is 0.42 mm -- one extrusion, the blob end of the ladder -- and IT AIN'T EASY at a
# printable 6 mm is 56 mm wide against 27 mm of face. It does not fit horizontally at any
# size that prints.
#
# So the lettering runs VERTICALLY, up the 63 mm axis, the way a pharmacy label does.
# Two columns, both landing at 56.2 mm of the 61 available, which is why they are
# different sizes: it makes them the same length.
TEXT_VERTICAL = True
TEXT_H_SMALL = Param(6.0, CHOSEN, "= TEXT_SIZE_MIN. There is no room below it")
TEXT_H_WHEEZY = Param(
    6.5, CHOSEN,
    "spec section 12 wants WHEEZY as the focal point. Enlarging the whole second column "
    "is how that survives a vertical layout")
TEXT_LINE_GAP = Param(2.0, CHOSEN, "between the two columns, across the body's width")
TEXT_FONT = "Arial Black"       # not a Param: it is a string, and it is a guess. R-5.
TEXT_LINES = (("IT AIN'T EASY", TEXT_H_SMALL), ("BEING WHEEZY", TEXT_H_WHEEZY))


def text_width(text, size):
    """How wide raised lettering will actually be. Nobody guesses this again."""
    return len(text) * float(size) * float(TEXT_ADVANCE_EM)


def text_fits(text, size, along, margin=1.0):
    """Does it fit along `along` mm, with margin? Returns (ok, width, available)."""
    w = text_width(text, size)
    avail = float(along) - 2 * margin
    return w <= avail, w, avail


def text_prints(size):
    """Will the stems survive? Returns (ok, stroke, floor)."""
    stroke = float(size) * float(TYPE_STEM_RATIO)
    return stroke >= float(TEXT_STROKE_MIN), stroke, float(TEXT_STROKE_MIN)


def text_flat_width():
    """How much flat face the columns need, across the body's width."""
    return sum(float(s) for _, s in TEXT_LINES) + float(TEXT_LINE_GAP) * (len(TEXT_LINES) - 1)


# ============================================================= the vertical stack ==
def stack():
    """Every Z level in the mechanism, derived once, from the body top face down.

    Returns absolute Z in BODY coordinates (z=0 is the body's base). This is the only
    place the mechanism's geometry is decided; switch.py and mech.py read it, so no
    literal here appears anywhere else as well.
    """
    top = float(BODY_HEIGHT)

    # The collar, top down. GUIDE_HEIGHT is engagement at rest, so the rim comes first
    # and the slot is placed around the lug that sits on it.
    rim_rest = top - float(GUIDE_HEIGHT)
    stop_ledge = rim_rest - float(BUTTON_TRAVEL)     # the lug slot floor: the DOWN stop

    # And the switch hangs off the down-stop, not the other way round.
    housing_top = stop_ledge - float(REST_GAP)
    plate_top = housing_top - float(MX_ABOVE_PLATE)
    plate_bot = plate_top - float(MX_PLATE_T)
    pocket_bot = plate_bot - float(MX_POCKET_DEPTH)

    return dict(
        body_top=top,
        canister_rim_rest=rim_rest,
        canister_rim_pressed=rim_rest - float(BUTTON_TRAVEL),
        stop_ledge=stop_ledge,
        housing_top=housing_top,
        stem_base=housing_top + float(MX_STEM_BASE),
        stem_tip=housing_top + float(MX_STEM_TOP),
        plate_top=plate_top,
        plate_bot=plate_bot,
        pocket_bot=pocket_bot,
        pin_relief_bot=pocket_bot - float(PIN_RELIEF_DEPTH),
        # derived, for the checks
        stem_engagement=(housing_top + float(MX_STEM_TOP)) - rim_rest,
        canister_height=float(CANISTER_EXPOSED) + (top - rim_rest),
        overall_height=top + float(CANISTER_EXPOSED),
    )


GUIDE_BORE = Param(CANISTER_OD + 2 * GUIDE_CLEARANCE, CHOSEN, "derived: the collar bore")
LUG_OD = Param(CANISTER_OD + 2 * LUG_PROUD, CHOSEN, "derived: over the lugs")
SLOT_OD = Param(LUG_OD + 2 * GUIDE_CLEARANCE, CHOSEN, "derived: the slot floor diameter")
SWITCH_WINDOW = Param(
    MX_HOUSING_SQ + 0.20, CHOSEN,
    "square. The hole under the collar that the switch top housing lives in, and the "
    "width of the rear slot the switch slides in through")


# ======================================================================== plumbing ==
def _register():
    for name, obj in list(globals().items()):
        if isinstance(obj, Param):
            obj.name = name
            REGISTRY[name] = obj


_register()


def assumptions():
    return [p for p in REGISTRY.values() if p.src == ASSUMED]


def assumptions_in_critical_use(used):
    """Fail the build if load-bearing geometry depends on an unvalidated number."""
    return [REGISTRY[n] for n in sorted(used)
            if n in REGISTRY and REGISTRY[n].src == ASSUMED]


def _is_multiple(value, step, tol=1e-6):
    """Is `value` a whole number of `step`? Tolerant of binary floating point:
    0.6 % 0.2 is 0.19999999999999998, not 0, and a check that fails a good value is
    worse than no check at all."""
    n = round(float(value) / float(step))
    return abs(n * float(step) - float(value)) < tol


def _under(value, floor, tol=1e-6):
    """Is `value` MEANINGFULLY under `floor`? (24 - 19.6) / 2 is 2.1999999999999997, and
    a wall check that fails a wall of exactly BODY_WALL is a check that cries wolf."""
    return float(value) < float(floor) - tol


def sanity():
    """Cheap self-checks that need no geometry."""
    bad = []
    s = stack()

    # -- the mechanism ---------------------------------------------------------
    if BUTTON_TRAVEL >= MX_TRAVEL:
        bad.append(f"BUTTON_TRAVEL {float(BUTTON_TRAVEL)} >= the switch's own bottom-out "
                   f"{float(MX_TRAVEL)} -- the printed stop never arrives and every press "
                   f"lands on the switch")
    if _under(MX_TRAVEL - BUTTON_TRAVEL, 3 * XY_REPEATABILITY):
        bad.append(f"only {float(MX_TRAVEL) - float(BUTTON_TRAVEL):.2f} mm between the "
                   f"printed stop and the switch's own bottom-out, against a "
                   f"+/-{float(XY_REPEATABILITY)} error bar")
    if BUTTON_TRAVEL <= MX_ACTUATE:
        bad.append(f"travel {float(BUTTON_TRAVEL)} does not reach the actuation point "
                   f"{float(MX_ACTUATE)} -- it will never click")
    if _under(s["stem_engagement"], 2.5):
        bad.append(f"only {s['stem_engagement']:.2f} mm of stem in the socket; the cap "
                   f"will rock off the stem")
    if s["stem_engagement"] > MX_SOCKET_DEPTH:
        bad.append(f"stem engagement {s['stem_engagement']:.2f} exceeds the socket depth "
                   f"{float(MX_SOCKET_DEPTH)} -- the cap bottoms out in its own socket "
                   f"instead of seating on the stem shoulder")
    if s["canister_rim_pressed"] <= s["housing_top"]:
        bad.append("at full press the canister rim is at or below the switch housing -- "
                   "the rim (round, Ø19) cannot pass the housing (15.6 square, 22.1 "
                   "across the diagonal)")
    if _under(s["pin_relief_bot"], 3.0):
        bad.append(f"the pin relief floor lands at z={s['pin_relief_bot']:.1f}, too close "
                   f"to the body's own base")

    # -- the collar ------------------------------------------------------------
    # Depth is set by the plain bore; width by the bore plus the lug slots. Checking
    # only one of the two is how the flange version of this design got as far as it did.
    wall_depth = (float(BODY_DEPTH) - float(GUIDE_BORE)) / 2.0
    if _under(wall_depth, BODY_WALL):
        bad.append(f"only {wall_depth:.2f} mm of wall front and back of the collar bore, "
                   f"against BODY_WALL {float(BODY_WALL)} -- widen BODY_DEPTH or narrow "
                   f"the canister")
    wall_width = (float(BODY_WIDTH) - float(SLOT_OD)) / 2.0
    if _under(wall_width, BODY_WALL):
        bad.append(f"only {wall_width:.2f} mm of wall left and right of the lug slots, "
                   f"against BODY_WALL {float(BODY_WALL)} -- the slots break out of the "
                   f"side of the body")
    if GUIDE_CLEARANCE <= XY_REPEATABILITY:
        bad.append(f"guide clearance {float(GUIDE_CLEARANCE)} is inside the machine's own "
                   f"+/-{float(XY_REPEATABILITY)} error bar -- it will bind on some "
                   f"prints and rattle on others")
    if _under(LUG_PROUD, MIN_FEATURE_T / 2):
        bad.append(f"a {float(LUG_PROUD)} mm lug is the whole hard stop and is thinner "
                   f"than half the {float(MIN_FEATURE_T)} mm minimum dependable feature")
    if _under(s["body_top"] - s["stop_ledge"], LUG_H + 1.0):
        bad.append("the lug slot is barely longer than the lug -- there is no room to "
                   "get the canister in, let alone travel once it is")
    if SWITCH_WINDOW >= BODY_DEPTH - 2 * BODY_WALL:
        bad.append("the switch window is wider than the body's own cavity")

    # -- Part B, the carrier ---------------------------------------------------
    if CARRIER_W >= BODY_WIDTH - 2 * BODY_WALL:
        bad.append(f"the carrier is {float(CARRIER_W)} wide and the body's cavity is "
                   f"{float(BODY_WIDTH) - 2 * float(BODY_WALL):.1f} -- it will not go in")
    if CARRIER_W >= BODY_DEPTH - 2 * BODY_WALL:
        bad.append(f"the carrier is {float(CARRIER_W)} across and the body is only "
                   f"{float(BODY_DEPTH) - 2 * float(BODY_WALL):.1f} deep inside")
    if _under(CARRIER_WALL, MIN_WALL):
        bad.append("the carrier wall is under two perimeters, and it is the part the "
                   "switch clips pull against every time the switch is changed")
    if abs((s["plate_top"] - s["pocket_bot"]) - float(CARRIER_H)) > 1e-6:
        bad.append("CARRIER_H does not match the band-plus-pocket the stack lays out")

    # -- print rules -----------------------------------------------------------
    if not _is_multiple(TEXT_RAISE, LAYER):
        bad.append(f"TEXT_RAISE {float(TEXT_RAISE)} is not a whole number of "
                   f"{float(LAYER)} mm layers, so the AMS colour change cannot land on a "
                   f"layer boundary. Spec section 12 computed it for 0.20 and section 16 "
                   f"then recommended 0.16")
    if _under(CANISTER_WALL, MIN_WALL):
        bad.append(f"canister wall {float(CANISTER_WALL)} is under two perimeters "
                   f"({float(MIN_WALL):.2f})")
    if _under(BODY_WALL, MIN_WALL):
        bad.append(f"body wall {float(BODY_WALL)} is under two perimeters")
    if MOUTH_CAVITY_DEPTH >= MOUTH_LENGTH:
        bad.append("the mouthpiece cavity runs the full projection -- that is an airway, "
                   "and section 1 of the spec says do not build one")
    if _under(TEXT_RAISE, LAYER * 2):
        bad.append("raised text under two layers will not survive a colour change")

    # -- lettering. Measured against the face it sits on, not eyeballed --------
    # The vertical layout runs each column up BODY_HEIGHT; the columns stack across the
    # FLAT of the front face, which is the width minus both corner radii.
    for txt, size in TEXT_LINES:
        ok, stroke, floor = text_prints(size)
        if not ok:
            bad.append(f"{txt!r} at {float(size)} mm has a {stroke:.2f} mm stem, under "
                       f"the {floor:.2f} mm stroke floor -- it prints as blobs")
        ok, w, avail = text_fits(txt, size, BODY_HEIGHT)
        if not ok:
            bad.append(f"{txt!r} at {float(size)} mm is {w:.1f} mm long and only "
                       f"{avail:.1f} mm of body height is available to run it up")
    flat = float(BODY_WIDTH) - 2 * float(BODY_CORNER_R)
    if _under(flat, text_flat_width()):
        bad.append(f"the lettering columns need {text_flat_width():.1f} mm across the "
                   f"face and only {flat:.1f} mm of it is flat between the corner radii")
    if _under(PLATE_SPACING, 2 * BRIM_WIDTH + 1.0):
        bad.append(f"plate spacing {float(PLATE_SPACING)} is under 2 x brim + 1")

    return bad


# ============================================================================= cli ==
_SRC_ORDER = [MACHINE, MEASURED, SAMPLE, CHOSEN, ASSUMED]


def _dump(only=None):
    for src in _SRC_ORDER:
        if only and src != only:
            continue
        rows = [p for p in REGISTRY.values() if p.src == src]
        if not rows:
            continue
        print(f"\n{src.upper()}")
        for p in rows:
            ref = f"  [{p.ref}]" if p.ref else ""
            print(f"  {p.name:<22} {float(p):>8.3f}   {p.why}{ref}")


if __name__ == "__main__":
    if "--stack" in sys.argv:
        print("\nvertical stack, z=0 at the body's base, mm\n")
        for k, v in sorted(stack().items(), key=lambda kv: -kv[1]):
            print(f"  {v:8.2f}   {k}")
    else:
        _dump(ASSUMED if "--assumed" in sys.argv else None)

    print("\n" + "=" * 72)
    problems = sanity()
    for m in problems:
        print(f"  SANITY  {m}")
    print(f"  {len(REGISTRY)} parameters, {len(assumptions())} still ASSUMED, "
          f"{len(problems)} sanity failures")
    sys.exit(1 if problems else 0)
