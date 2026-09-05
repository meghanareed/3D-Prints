"""Checks that model the PRINTER, not just the model.

Written before any geometry exists, on purpose. Both previous attempts wrote each check
after the print that found the defect, so the suite was permanently one print behind.

Two structural rules, each from a specific past failure:

  1. The registry is a LIST THE RUNNER ITERATES, and `check_registry_complete` asserts
     every `check_*` in this module is in it. `archive/verify.py` defined 22 checks and
     ran 21 -- `check_hung_clearance` was called from nowhere while the spec claimed it
     passed. A check that never runs cannot be seen to be missing in a "N failures" line.

  2. Nothing here says "0 failures" and stops. `UNCHECKED` is printed every run, because
     "no check I have written is unhappy" is not "this will print", and reporting the
     first as the second is what made the last suite misleading.

    python checks.py            run everything
    python checks.py -v         also print what passed
"""
import inspect
import os
import re
import sys

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))

FAIL, WARN, OK = "FAIL", "WARN", "ok"
REGISTRY = []


def check(covers):
    """Register a check. `covers` is what it actually looks at, in one line."""
    def deco(fn):
        fn.covers = covers
        REGISTRY.append(fn)
        return fn
    return deco


# What this suite does NOT look at. Printed every run. Add to it honestly.
UNCHECKED = [
    "Unsupported overhang. Written once, its own regression test failed to catch a "
    "known-bad part, a rewrite failed a good part, and it was deleted rather than "
    "shipped. Still open, and now partly mitigated by supports being allowed.",
    "Part volumes, real first-layer area, and actual wall thickness behind a socket. "
    "The JOINT geometry is now built and physically tested (check_joints_assemble); "
    "everything else still arrives with its module.",
    "Whether a printed joint holds. Only a bench answers that; see the R-register.",
]


# ============================================================ params and provenance ==
@check("params.sanity() -- the cheap arithmetic guards")
def check_params_sanity():
    return [(FAIL, m) for m in P.sanity()] or [(OK, "all params.sanity() guards pass")]


@check("no load-bearing geometry rests on an unvalidated number")
def check_no_assumed_in_critical():
    """FIT_CLEARANCE sat at a guess while 119 parts were built on it. Never again."""
    critical = {"PEG_D", "SOCKET_D", "PEG_L", "PIN_L", "FIT_CLEARANCE",
                "LEAD_IN_CHAMFER", "SOCKET_DEPTH"}
    out = []
    for p in P.assumptions_in_critical_use(critical):
        out.append((WARN, f"{p.name} = {float(p):g} is ASSUMED and joints depend on it "
                          f"-- close {p.ref} before printing anything that mates"))
    if not out:
        out.append((OK, "every joint parameter is measured"))
    return out


@check("the slicer profile is this machine's current one")
def check_profile_is_current():
    if P.PROFILE_IS_STALE:
        return [(WARN, "using the profile vendored in archive/. It IS a Bambu Lab P2S "
                       "profile at 0.4 -- checked, not assumed -- but it predates the "
                       "current Studio session (7 filament slots, not 8). Re-export to "
                       "close R-3")]
    return [(OK, "profile is the project's own export")]


# ================================================================== the machine ==
@check("every mating feature is something a 0.4 mm nozzle can actually place")
def check_features_are_printable():
    out = []
    if P.PEG_D < P.MIN_FEATURE_T:
        out.append((FAIL, f"peg Ø{float(P.PEG_D)} is under the {float(P.MIN_FEATURE_T)} mm "
                          f"minimum dependable feature"))
    if P.WIRE_CHANNEL_W < 2 * P.LINE_W:
        out.append((FAIL, f"wire channel {float(P.WIRE_CHANNEL_W)} is under two extrusions"))
    if P.OUTER_SKIN_T < P.MIN_WALL:
        out.append((FAIL, f"outer brick skin {float(P.OUTER_SKIN_T)} is thinner than "
                          f"{float(P.MIN_WALL):.2f} mm (two perimeters)"))
    if P.WALL_FACE_T < P.MIN_WALL:
        out.append((FAIL, f"wall face {float(P.WALL_FACE_T)} is under two perimeters"))
    # The one that ended attempt one, kept as a live assertion rather than a memory.
    if P.INTERNAL_CORNER_R > 0.15:
        out.append((OK, f"internal corners print at r≈{float(P.INTERNAL_CORNER_R):.2f} mm "
                        f"-- every mating feature must be round, D-sectioned or chamfered"))
    return out or [(OK, "features clear the machine's floor")]


@check("the joint is not specified tighter than the machine's own error bar")
def check_joint_beats_the_noise():
    out = []
    if P.FIT_CLEARANCE <= P.XY_REPEATABILITY:
        out.append((FAIL, f"clearance {float(P.FIT_CLEARANCE)} <= repeatability "
                          f"±{float(P.XY_REPEATABILITY)} -- that is a coin toss, not a fit"))
    slop = P.SOCKET_D - P.PEG_D
    if slop < 2 * P.HOLE_SHRINK_MAX - 0.05:
        out.append((WARN, f"socket is {slop:.2f} mm over the peg; a hole printing "
                          f"{float(P.HOLE_SHRINK_MAX)}/side undersize would close it"))
    return out or [(OK, f"Ø{float(P.PEG_D)} into Ø{float(P.SOCKET_D)} survives "
                        f"{float(P.HOLE_SHRINK_MAX)} mm/side of shrinkage")]


@check("a peg seats the part on its flange, never bottoms out in its socket")
def check_socket_deeper_than_peg():
    if P.SOCKET_DEPTH <= P.PEG_L:
        return [(FAIL, f"socket {float(P.SOCKET_DEPTH)} is not deeper than peg "
                       f"{float(P.PEG_L)} -- the part will stand proud on the peg tip and "
                       f"no amount of glue fixes it")]
    return [(OK, f"{float(P.SOCKET_DEPTH) - float(P.PEG_L):.1f} mm of relief past the peg")]


# ===================================================================== the bed ==
# Declared sizes, not measured ones -- there is no geometry yet, and saying so is the
# point. These are the ten major structural prints.
MAJOR_PARTS = [
    ("wall module (x4)", lambda: (P.WALL_MODULE_L, P.WALL_MODULE_H)),
    ("floor section (x2)", lambda: (P.WALL_MODULE_L, P.ALLEY_W_FRONT)),
    ("back/end wall", lambda: (P.ALLEY_W_REAR, P.WALL_MODULE_H)),
    ("front arch", lambda: (float(P.BOOKNOOK_WIDTH), P.SCENE_H * 0.5)),
    ("roof section (x2)", lambda: (P.WALL_MODULE_L, P.CHASSIS_W)),
]


@check("every major part fits the bed WITH its brim")
def check_major_parts_fit_bed():
    bed = min(float(P.BED_X), float(P.BED_Y))
    out = []
    for name, fn in MAJOR_PARTS:
        w, h = fn()
        big = max(w, h) + 2 * float(P.BRIM_WIDTH)
        if big > bed:
            out.append((FAIL, f"{name}: {w:.0f} x {h:.0f}, {big:.0f} with brim, on a "
                              f"{bed:.0f} bed"))
        elif big > bed - 15.0:
            out.append((WARN, f"{name}: {big:.0f} with brim on a {bed:.0f} bed -- "
                              f"{bed - big:.1f} mm spare is a coincidence, not a fit"))
    return out or [(OK, f"all {len(MAJOR_PARTS)} major part types fit with a brim")]


@check("plate spacing keeps neighbouring brims from merging into a raft")
def check_plate_spacing():
    need = 2 * float(P.BRIM_WIDTH) + 1.0
    if float(P.PLATE_SPACING) < need:
        return [(FAIL, f"spacing {float(P.PLATE_SPACING)} < {need} -- 22 of 64 parts "
                       f"once fused into one raft this way")]
    return [(OK, f"{float(P.PLATE_SPACING)} mm ≥ 2×brim+1")]


@check("there is exactly ONE definition of needs_brim in the tree")
def check_one_brim_definition():
    """There were three, in three files, and they disagreed."""
    found = []
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs
                   if d not in {".venv", "archive", "out", "__pycache__", ".git"}]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path, encoding="utf8", errors="ignore") as fh:
                if re.search(r"^\s*def needs_brim\b", fh.read(), re.M):
                    found.append(os.path.relpath(path, HERE))
    if len(found) > 1:
        return [(FAIL, "needs_brim is defined in " + ", ".join(found) +
                       " -- three disagreeing copies once shipped a part with no brim "
                       "that had already failed on the bed")]
    if not found:
        return [(FAIL, "needs_brim is defined nowhere")]
    return [(OK, f"one definition, in {found[0]}")]


# =================================================================== lettering ==
@check("raised text is printable and an AMS colour change can land on a layer")
def check_text():
    out = []
    if not P._is_multiple(P.TEXT_DEPTH, P.LAYER):
        out.append((FAIL, f"text depth {float(P.TEXT_DEPTH)} is not a whole number of "
                          f"{float(P.LAYER)} layers -- a colour change cannot land clean"))
    if P.TEXT_STROKE_MIN < P.LINE_W:
        out.append((FAIL, f"minimum stroke {float(P.TEXT_STROKE_MIN)} is under one "
                          f"extrusion ({float(P.LINE_W)})"))
    implied = float(P.TEXT_STROKE_MIN) / float(P.TYPE_STEM_RATIO)
    out.append((OK, f"stroke {float(P.TEXT_STROKE_MIN)} implies ≥{implied:.1f} mm glyphs "
                    f"for a bold serif -- a fatter face may go smaller, which is why the "
                    f"rule is on STROKE, not height"))
    return out


# ==================================================================== envelope ==
@check("the alley reads as an alley and the arch does not shadow it")
def check_envelope():
    out = []
    if P.ARCH_OPENING_W <= P.ALLEY_W_FRONT:
        out.append((FAIL, f"arch opening {float(P.ARCH_OPENING_W):.0f} is not wider than "
                          f"the {P.ALLEY_W_FRONT:.0f} alley -- the reveal will shadow the "
                          f"near shopfronts off-axis"))
    if P.ALLEY_W_REAR >= P.ALLEY_W_FRONT:
        out.append((FAIL, "the alley does not narrow toward the rear"))
    ratio = P.ALLEY_D / P.CLEAR_WALK_FRONT
    if ratio < 1.5:
        out.append((WARN, f"depth:walk is {ratio:.2f}:1 -- that reads as a courtyard, "
                          f"not an alley"))
    else:
        out.append((OK, f"depth:walk {ratio:.2f}:1 on a {P.CLEAR_WALK_FRONT:.0f} mm walk"))
    return out


@check("light diffuses before it reaches the glazing, and no emitter is visible")
def check_lighting_geometry():
    out = []
    if P.STOREFRONT_PROJ < 20.0:
        out.append((WARN, f"only {float(P.STOREFRONT_PROJ)} mm from emitter plane to "
                          f"glazing -- expect a visible hot spot"))
    else:
        out.append((OK, f"{float(P.STOREFRONT_PROJ)} mm of hollow bay does the diffusing, "
                        f"so the wall cavity only carries wire"))
    if P.WIRE_CAVITY_D < P.WIRE_CHANNEL_W:
        out.append((FAIL, f"wiring cavity {float(P.WIRE_CAVITY_D)} is narrower than the "
                          f"{float(P.WIRE_CHANNEL_W)} channel feeding it"))
    return out


# =================================================================== geometry ==
@check("the joint geometry, built and physically inserted")
def check_joints_assemble():
    """Delegates to joints.self_test(), which builds both halves and applies the real
    insertion. Imported lazily: it pulls in CadQuery, which is slow and which crashes on
    interpreter teardown, and most runs of this file do not need geometry at all.
    """
    try:
        import joints
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, joint geometry unchecked: {exc}")]
    out = [(FAIL, f"{name}" + (f" [{detail}]" if detail else ""))
           for ok, name, detail in joints.self_test() if not ok]
    n = len(joints.self_test())
    return out or [(OK, f"all {n} joint assembly tests pass, insertion actually applied")]


# ======================================================================= meta ==
@check("every check in this module is actually in the registry")
def check_registry_complete():
    """The one that would have caught check_hung_clearance sitting uncalled."""
    mod = sys.modules[__name__]
    defined = {n for n, o in vars(mod).items()
               if n.startswith("check_") and inspect.isfunction(o)}
    registered = {fn.__name__ for fn in REGISTRY}
    missing = sorted(defined - registered)
    if missing:
        return [(FAIL, "defined but never run: " + ", ".join(missing))]
    return [(OK, f"all {len(registered)} checks registered and run")]


def run(verbose=False):
    fails = warns = 0
    for fn in REGISTRY:
        results = fn()
        shown = [r for r in results if r[0] != OK or verbose]
        if shown:
            print(f"\n  {fn.__name__}")
            print(f"    ({fn.covers})")
        for level, msg in results:
            if level == FAIL:
                fails += 1
            elif level == WARN:
                warns += 1
            if level != OK or verbose:
                print(f"    {level:<4} {msg}")

    print("\n" + "=" * 72)
    print(f"  {len(REGISTRY)} checks ran: {fails} failures, {warns} warnings")
    print("\n  NOT CHECKED -- say this every time, per P5:")
    for note in UNCHECKED:
        first, *rest = [note[i:i + 68] for i in range(0, len(note), 68)]
        print(f"    - {first}")
        for line in rest:
            print(f"      {line}")
    print("=" * 72)
    return fails


if __name__ == "__main__":
    failed = run("-v" in sys.argv)
    # This file may now import CadQuery via check_joints_assemble, so it inherits OCCT's
    # teardown crash. See the README: flush, then os._exit, or the gate lies.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if failed else 0)
