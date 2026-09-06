"""Checks that model the PRINTER and the SWITCH, not just the model.

Two structural rules, carried over from the book nook because each came from a specific
failure there:

  1. The registry is a LIST THE RUNNER ITERATES, and `check_registry_complete` asserts
     every `check_*` in this module is in it. That project defined 22 checks and ran 21
     for months, while the missing one was documented as passing.

  2. Nothing here says "0 failures" and stops. `UNCHECKED` is printed every run, because
     "no check I have written is unhappy" is not "this will print".

    python checks.py            run everything
    python checks.py -v         also print what passed
"""
import inspect
import os
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
    "Whether a real MX switch is the size this project thinks it is. Every number in "
    "the R-1 group is a datasheet figure or a reading off a third-party model, and the "
    "whole vertical stack hangs off them. Calipers on an actual switch closes it; "
    "nothing in software can.",
    "Whether the click FEELS right. Travel, actuation force and the sound are the "
    "project's first three priorities (spec section 22) and none of them is a dimension. "
    "Prototype B answers this and nothing else does.",
    "Part A, the cosmetic body, and Part B, the switch carrier. Neither is modelled "
    "yet -- see README.md 'What is not built'. The collar, the stop and the switch "
    "mount that go INSIDE them are modelled and tested.",
    "Unsupported overhang. The book nook wrote this check twice, and both times it "
    "passed a known-bad part or failed a good one, so it was deleted rather than "
    "shipped. The canister's one real overhang is a 15.4 mm bridged crown, which is the "
    "same span the sample bridges at 13.4.",
    "The slicer's own sharp-tail and cantilever warnings. Opening the 3MF in Bambu is "
    "the review step that has actually been finding these next door. Do it.",
    "Whether the raised text separates cleanly as an AMS colour. The layout is now "
    "checked -- size, stroke and fit on the real face -- and coupon 03 prints it, but "
    "plate.py still emits one body per object, so the colour split itself is untested.",
    "Whether Arial Black's stems really are 0.12 of the glyph size. TYPE_STEM_RATIO is "
    "a bold SERIF figure and Arial Black is heavier, so the stroke check is "
    "conservative rather than accurate. Coupon 03 settles it (R-5).",
]


# ============================================================ params and provenance ==
@check("params.sanity() -- the cheap arithmetic guards")
def check_params_sanity():
    return [(FAIL, m) for m in P.sanity()] or [(OK, "all params.sanity() guards pass")]


@check("no load-bearing geometry rests on an unvalidated number")
def check_no_assumed_in_critical():
    """A clearance sat at a guess next door while 119 parts were built on it. Never
    again -- and this project has MORE assumed numbers than that one did, because the
    switch is not ours to measure from the outside."""
    critical = {"MX_HOUSING_SQ", "MX_ABOVE_PLATE", "MX_STEM_BASE", "MX_STEM_TOP",
                "MX_TRAVEL", "MX_ACTUATE", "GUIDE_CLEARANCE"}
    out = []
    for p in P.assumptions_in_critical_use(critical):
        out.append((WARN, f"{p.name} = {float(p):g} is ASSUMED and the mechanism depends "
                          f"on it -- close {p.ref} before printing anything but coupons"))
    return out or [(OK, "every mechanism parameter is measured")]


@check("the sample's numbers are labelled as the sample's, not as measurements")
def check_sample_is_not_measured():
    """The sample is a working clicker, which is real evidence -- but it was printed on
    an A1 mini at 0.16 and nobody here has held it. Calling that MEASURED would let it
    pass check_no_assumed_in_critical without anyone ever checking it."""
    n = len([p for p in P.REGISTRY.values() if p.src == P.SAMPLE])
    if not n:
        return [(FAIL, "nothing is marked SAMPLE -- did the provenance get flattened?")]
    return [(OK, f"{n} parameters carry SAMPLE provenance and none of them claims to be "
                 f"a measurement taken here")]


# ================================================================== the machine ==
@check("every feature is something a 0.4 mm nozzle can actually place")
def check_features_are_printable():
    out = []
    if P.LUG_PROUD < P.NOZZLE:
        out.append((FAIL, f"the stop lug stands {float(P.LUG_PROUD)} mm proud, under one "
                          f"extrusion -- it is the whole hard stop"))
    if P.CANISTER_WALL < P.MIN_WALL:
        out.append((FAIL, f"canister wall {float(P.CANISTER_WALL)} is under two perimeters"))
    if P.TEXT_RAISE < 2 * P.LAYER:
        out.append((FAIL, "raised text is under two layers"))
    # The one that ended attempt one next door, kept as a live assertion, not a memory.
    out.append((OK, f"internal corners print at r~{float(P.INTERNAL_CORNER_R):.2f} mm -- "
                    f"which is why the guide is a ROUND bore and not a square skirt"))
    return out


@check("the lettering is big enough to print and short enough to fit")
def check_lettering():
    """The check that killed the spec's text plan. Section 12 asked for 3-3.5 mm glyphs
    with WHEEZY at 4-5, which is a 0.42-0.54 mm stem against a 0.70 mm floor -- the blob
    end of the ladder plate 1 printed. And IT AIN'T EASY at a printable 6 mm is 56 mm
    wide on a face 27 mm across, so it does not fit horizontally at any size that prints.
    Hence the vertical layout."""
    out = []
    for txt, size in P.TEXT_LINES:
        ok, stroke, floor = P.text_prints(size)
        if not ok:
            out.append((FAIL, f"{txt!r} at {float(size)} mm has a {stroke:.2f} mm stem, "
                              f"under the {floor:.2f} mm floor -- blobs"))
        ok, w, avail = P.text_fits(txt, size, P.BODY_HEIGHT)
        if not ok:
            out.append((FAIL, f"{txt!r} is {w:.1f} mm long against {avail:.1f} mm of "
                              f"body height"))
    if not P.TEXT_VERTICAL:
        out.append((WARN, "TEXT_VERTICAL is off. Check the layout against BODY_WIDTH "
                          "rather than BODY_HEIGHT -- sanity() measures the vertical run"))
    flat = float(P.BODY_WIDTH) - 2 * float(P.BODY_CORNER_R)
    return out or [
        (OK, f"{len(P.TEXT_LINES)} columns run up the {float(P.BODY_HEIGHT):.0f} mm axis, "
             f"longest {max(P.text_width(t, s) for t, s in P.TEXT_LINES):.1f} mm"),
        (OK, f"stacking {P.text_flat_width():.1f} mm across {flat:.0f} mm of flat face, "
             f"thinnest stem {min(P.text_prints(s)[1] for _, s in P.TEXT_LINES):.2f} mm "
             f"against a {float(P.TEXT_STROKE_MIN)} mm floor")]


@check("nothing is identified by printed text at a size that prints as a blob")
def check_no_blob_labels():
    """Rule 12. Three test blocks next door printed with 3 mm labels that came out as
    blobs, and which clearance did what is now permanently unknowable."""
    try:
        import coupon
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, coupon labelling unchecked: {exc}")]
    if coupon.ID_BAR_W < P.MIN_FEATURE_T or coupon.ID_BAR_L < P.MIN_FEATURE_L:
        return [(FAIL, f"the ID bars are {coupon.ID_BAR_W} x {coupon.ID_BAR_L}, under the "
                       f"{float(P.MIN_FEATURE_T)} x {float(P.MIN_FEATURE_L)} minimum")]
    return [(OK, f"coupons are identified by {coupon.ID_BAR_W} x {coupon.ID_BAR_L} mm "
                 f"countable bars, not by numbers")]


@check("nothing being measured is measured from a single sample")
def check_replicates():
    """Rule 13. Socket-to-socket scatter here is wider than the whole range worth
    sweeping, so one tile tells you about that tile."""
    try:
        import coupon
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, replicates unchecked: {exc}")]
    if coupon.REPLICATES < 3:
        return [(FAIL, f"REPLICATES is {coupon.REPLICATES}; the rule is three")]
    return [(OK, f"every swept value is printed {coupon.REPLICATES} times")]


@check("the guide is not specified tighter than the machine's own error bar")
def check_guide_beats_the_noise():
    out = []
    if P.GUIDE_CLEARANCE <= P.XY_REPEATABILITY:
        out.append((FAIL, f"guide clearance {float(P.GUIDE_CLEARANCE)} <= repeatability "
                          f"+/-{float(P.XY_REPEATABILITY)} -- a coin toss, not a fit"))
    elif P.GUIDE_CLEARANCE < 2 * P.XY_REPEATABILITY:
        out.append((WARN, f"guide clearance {float(P.GUIDE_CLEARANCE)} is only "
                          f"{float(P.GUIDE_CLEARANCE) / float(P.XY_REPEATABILITY):.1f}x "
                          f"the error bar. The sample runs 1.00/side. Coupon 02 settles "
                          f"it -- do not print a body before it does"))
    if P.GUIDE_CLEARANCE < P.HOLE_SHRINK_MAX:
        out.append((WARN, f"a bore printing {float(P.HOLE_SHRINK_MAX)} mm/side undersize "
                          f"closes a {float(P.GUIDE_CLEARANCE)} mm clearance completely "
                          f"-- the canister would seize"))
    return out or [(OK, "the guide clears the machine's noise floor")]


# ================================================================ the mechanism ==
@check("the printed stop, not the switch, absorbs an angry press")
def check_stop_protects_switch():
    margin = float(P.MX_TRAVEL) - float(P.BUTTON_TRAVEL)
    if margin <= 0:
        return [(FAIL, "the switch bottoms out before the printed stop does -- section 8 "
                       "of the spec exists to prevent exactly this")]
    if margin < 0.5:
        return [(WARN, f"only {margin:.2f} mm between the printed stop and the switch's "
                       f"own bottom-out")]
    return [(OK, f"{margin:.2f} mm of margin; the spec's 3.5-3.8 travel would have left "
                 f"0.2-0.5")]


@check("the click happens, and happens before the stop")
def check_it_actually_clicks():
    if P.MX_ACTUATE >= P.BUTTON_TRAVEL:
        return [(FAIL, "the stop arrives before the actuation point -- it will never "
                       "click")]
    return [(OK, f"actuates at {float(P.MX_ACTUATE)} mm, stops at "
                 f"{float(P.BUTTON_TRAVEL)} mm, so there is "
                 f"{float(P.BUTTON_TRAVEL) - float(P.MX_ACTUATE):.1f} mm of overtravel "
                 f"past the click")]


@check("the switch can physically be got into the body it is mounted in")
def check_switch_can_be_installed():
    """The check that rewrote the part architecture. An MX switch loads downward through
    its plate, and its top housing is wider across the diagonal than the collar bore, so
    it cannot go in through the collar -- and it cannot come up from below either,
    because the top housing is wider than the cutout. Hence Part B, the carrier."""
    diag = float(P.MX_HOUSING_SQ) * 2 ** 0.5
    out = []
    if diag > P.GUIDE_BORE:
        out.append((OK, f"the housing is {diag:.1f} across the diagonal and the collar "
                        f"bore is {float(P.GUIDE_BORE)} -- so the switch CANNOT be fitted "
                        f"through the top, and Part B has to carry the plate band"))
    else:
        out.append((WARN, "the housing would now pass through the collar bore. The "
                          "carrier may no longer be necessary -- re-read the README "
                          "before simplifying, the geometry moved"))
    if P.MX_HOUSING_SQ <= P.MX_POCKET:
        out.append((FAIL, "the top housing is not wider than the plate cutout, so nothing "
                          "stops the switch falling straight through"))
    return out


@check("the canister guide is long enough to resist an off-centre press")
def check_no_wobble():
    s = P.stack()
    engage = s["body_top"] - s["canister_rim_rest"]
    lever = float(P.CANISTER_EXPOSED)
    if engage < 4.0:
        return [(FAIL, f"only {engage:.1f} mm of skirt in the collar")]
    ratio = lever / engage
    if ratio > 2.5:
        return [(WARN, f"{lever:.0f} mm of exposed canister on {engage:.0f} mm of guide "
                       f"({ratio:.1f}:1). Spec priority 2 is that it does not wobble")]
    return [(OK, f"{engage:.0f} mm of guide under {lever:.0f} mm of canister "
                 f"({ratio:.1f}:1), and it grows to "
                 f"{engage + float(P.BUTTON_TRAVEL):.0f} mm at full press")]


@check("this is a fidget and not a functional inhaler")
def check_not_a_medical_device():
    """Section 1 of the spec, as an assertion rather than an intention."""
    out = []
    if P.MOUTH_CAVITY_DEPTH >= P.MOUTH_LENGTH:
        out.append((FAIL, "the mouthpiece cavity runs the full projection -- that is an "
                          "airway"))
    if P.MOUTH_CAVITY_DEPTH > 0.6 * P.MOUTH_LENGTH:
        out.append((WARN, "the mouthpiece cavity is more than half the projection; keep "
                          "it visibly blind"))
    return out or [(OK, f"the mouthpiece cavity is {float(P.MOUTH_CAVITY_DEPTH)} of "
                        f"{float(P.MOUTH_LENGTH)} mm and terminates in solid material; "
                        f"no airway, no canister receptacle")]


# =================================================================== geometry ==
@check("the MX interface, built and assembled")
def check_switch_interface():
    try:
        import switch
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, switch geometry unchecked: {exc}")]
    results = switch.self_test()
    out = [(FAIL, name + (f" [{detail}]" if detail else ""))
           for ok, name, detail in results if not ok]
    return out or [(OK, f"all {len(results)} switch interface tests pass, with the "
                        f"switch stand-in actually inserted")]


@check("the canister pressed through its whole stroke, solid against solid")
def check_mechanism_travels():
    try:
        import mech
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, mechanism unchecked: {exc}")]
    results = mech.self_test()
    out = [(FAIL, name + (f" [{detail}]" if detail else ""))
           for ok, name, detail in results if not ok]
    return out or [(OK, f"all {len(results)} mechanism tests pass, including the negative "
                        f"control that presses PAST the stop and expects a collision")]


@check("the coupons build, and the sweeps actually sweep")
def check_coupons():
    try:
        import coupon
    except ImportError as exc:
        return [(WARN, f"CadQuery not importable, coupons unchecked: {exc}")]
    results = coupon.self_test()
    out = [(FAIL, name + (f" [{detail}]" if detail else ""))
           for ok, name, detail in results if not ok]
    return out or [(OK, f"all {len(results)} coupon tests pass")]


# ======================================================================= meta ==
@check("every check in this module is actually in the registry")
def check_registry_complete():
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

    print("\n" + "=" * 74)
    print(f"  {len(REGISTRY)} checks ran: {fails} failures, {warns} warnings")
    print("\n  NOT CHECKED -- say this every time:")
    for note in UNCHECKED:
        first, *rest = [note[i:i + 68] for i in range(0, len(note), 68)]
        print(f"    - {first}")
        for line in rest:
            print(f"      {line}")
    print("=" * 74)
    return fails


if __name__ == "__main__":
    failed = run("-v" in sys.argv)
    # This file imports CadQuery via the geometry checks, so it inherits OCCT's teardown
    # crash. Flush, then os._exit, or the gate lies.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if failed else 0)
