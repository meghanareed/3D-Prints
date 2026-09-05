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

# ==================================================================== chosen ==
# Design decisions. Changing these changes the model; they are not facts about anything.
BOOKNOOK_WIDTH  = Param(100.0, CHOSEN, "X, across the alley -- sized to sit between books")
BOOKNOOK_HEIGHT = Param(240.0, CHOSEN, "Z")
BOOKNOOK_DEPTH  = Param(200.0, CHOSEN, "Y, front to back")
SHELL_THICKNESS = Param(2.2, CHOSEN, "outer case wall")
WALL_FACE_T     = Param(2.5, CHOSEN, "the brick plate the viewer sees")
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
                 "3.0 + 0.30/side = 3.6. NOT 3.5: that is 0.25/side, which is the guessed "
                 "number attempt one shipped on and failed with", "R-5")
PEG_ENGAGE = Param(PEG_L - LEAD_IN_CHAMFER, ASSUMED,
                   "integral peg: parallel bore actually gripping, once the mouth chamfer "
                   "is taken off", "R-5")
PIN_ENGAGE = Param(PIN_L / 2.0 - LEAD_IN_CHAMFER, ASSUMED,
                   "loose pin: gripping length PER SIDE. The one that nearly shipped short",
                   "R-5")

CASE_CAVITY_W = BOOKNOOK_WIDTH - 2 * SHELL_THICKNESS


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
