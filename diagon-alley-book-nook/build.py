#!/usr/bin/env python3
"""Build the whole kit.

    python3 build.py              every part, STLs + assembly + exploded + plates
    python3 build.py --list       list part IDs without building
    python3 build.py --only 01,04 build just those IDs
    python3 build.py --no-preview skip the assembly/exploded previews

Outputs land in out/stl, out/preview and out/plates.
"""
import argparse
import json
import math
import os
import sys
import time

import cadquery as cq

import params as P
import data.facade as F
from lib.util import fits_bed, keep_largest
from parts import walls as WL
from parts import structure as ST
from parts import case as CA
from parts import kit as KT
from parts.decor import to_wall

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
STL = os.path.join(OUT, "stl")
PREVIEW = os.path.join(OUT, "preview")
PLATES = os.path.join(OUT, "plates")


# =============================================================== the manifest ==
def manifest():
    """Every printable part: id, name, builder, group, print orientation, colour.

    `place` positions the part in the assembled preview. `print_rot` is applied only
    on export, so each STL lands on the bed in the orientation it should be printed.
    """
    M = []

    def add(pid, name, fn, group, place=None, print_rot=None, colour="tan", note=""):
        M.append(dict(id=pid, name=name, fn=fn, group=group, place=place,
                      print_rot=print_rot, colour=colour, note=note))

    WA, W, D = P.WALL_ASSEMBLY_D, P.CHASSIS_W, P.CHASSIS_D
    BP = P.BASE_PAN_T

    def wall_xf(side, solid):
        """Wall-local -> chassis. The right wall is the left wall mirrored, so both
        are built identically and no socket can end up on the wrong face."""
        s = solid
        if side == "R":
            s = s.mirror("YZ")
            s = s.translate((W, 0, 0))
        else:
            s = s.translate((0, 0, 0))
        s = s.translate((0, 0, BP))
        # the forced-perspective cant, applied at assembly only
        return s.rotate((0 if side == "L" else W, 0, 0), (0 if side == "L" else W, 0, 1),
                        -P.WALL_CANT_DEG if side == "L" else P.WALL_CANT_DEG)

    # ---- 00-09 structure ---------------------------------------------------
    add("00", "Chassis_Base_Pan", ST.base_pan, "structure",
        place=lambda s: s, colour="grey")
    for side, ids in (("L", ("01", "01R")), ("R", ("02", "02R"))):
        add(ids[0], f"{side}_Wall_Face", (lambda sd=side: WL.wall_face(sd)), "structure",
            place=(lambda s, sd=side: wall_xf(sd, s)),
            print_rot=("Y", -90), colour="brick",
            note="print brick-up, no supports")
        add(ids[1], f"{side}_Wall_Rib", (lambda sd=side: WL.wall_rib(sd)), "structure",
            place=(lambda s, sd=side: wall_xf(sd, s)),
            print_rot=("Y", 90), colour="grey", note="hidden; print flat")
    add("03A", "Rear_Perspective_Block", ST.rear_block, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, ST.Y_BLOCK_0, BP)), colour="brick",
        print_rot=("X", -90), note="lies on its back; 170 mm tall is too tippy upright")
    add("03B", "Rear_Archway", ST.rear_archway, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, ST.Y_BLOCK_1 - 9.0, BP)), colour="stone",
        print_rot=("X", -90))
    add("03C", "Rear_Silhouette", ST.rear_silhouette, "structure",
        place=lambda s: s.rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((P.CHASSIS_W / 2, ST.Y_SCREEN, BP + 30.0)), colour="black")
    add("03D", "Rear_Glow_Frame", ST.rear_glow_frame, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, ST.Y_SKYDIFF, BP + 26.0)), colour="black",
        print_rot=("X", -90))
    add("03E", "Sky_Puck_Cradle", ST.sky_puck_cradle, "lighting",
        place=lambda s: s.rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((P.CHASSIS_W / 2, ST.Y_PUCK, BP + 68.0)), colour="black",
        note="holds the 59.5 x 8.3 RGB/CCT puck")
    add("03F", "Sky_Diffuser", ST.sky_diffuser, "lighting",
        place=lambda s: s.rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((P.CHASSIS_W / 2, ST.Y_SKYDIFF + 1.0, BP + 28.0)), colour="white",
        note="natural/white PLA, 3 walls, 0 % infill")
    add("04", "Cobblestone_Floor", ST.cobblestone_floor, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, 0, BP)), colour="stone")
    for side in ("L", "R"):
        sx = -1 if side == "L" else 1
        add(f"04{'B' if side == 'L' else 'C'}", f"Gutter_{side}",
            (lambda sd=side: ST.gutter_strip(sd)), "structure",
            place=(lambda s, q=sx: s.translate((P.CHASSIS_W / 2 + q * (P.ALLEY_W_FRONT / 2 - 3.0),
                                                0, BP + 4.0))), colour="stone")
    add("05", "Ceiling_Baffle", ST.ceiling_baffle, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, 0, BP + P.SCENE_H - 6.0)), colour="black",
        note="its P1 pegs stand 5.1 mm proud -- that is what sets the top of the stack")
    for side, pid in (("L", "06"), ("R", "07")):
        add(pid, f"Front_Bezel_{side}", (lambda sd=side: WL.front_bezel(sd)), "structure",
            print_rot=("X", -90),
            place=(lambda s, sd=side: (s if sd == "L"
                                       else s.mirror("YZ").translate((P.CHASSIS_W, 0, 0)))
                   .translate((0, 0, BP))), colour="brick",
            note="torn brick edge, the signature part -- prints flat, relief up")
    add("08", "Front_Arch_Header", ST.front_arch_header, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, 0, BP + P.SCENE_H - 24.0)), colour="brick")
    add("09", "Chassis_Rear_Wall", ST.chassis_rear_wall, "structure",
        place=lambda s: s.translate((P.CHASSIS_W / 2, ST.Y_REARWALL, BP)), colour="black",
        print_rot=("X", -90))

    # ---- 10-29 facade decoration -------------------------------------------
    for side in ("L", "R"):
        parts, _, _, _ = WL.collect(side)
        for p in parts:
            add(p["id"], p["name"], (lambda pp=p: pp["solid"]), f"facade_{side}",
                place=(lambda s, pp=p, sd=side: wall_xf(sd, pp["placed"])),
                colour="wood", print_rot=("X", 180),
                note="face down, pegs up")

    # ---- 30-39 signs, brackets, lanterns, props -----------------------------
    for it in KT.signs() + KT.brackets() + KT.lanterns():
        sd, u, z = it.get("side"), it.get("u", 0), it.get("z", 0)
        if sd in ("L", "R"):
            add(it["id"], it["name"], (lambda i=it: i["solid"]), "signs",
                place=(lambda s, i=it, q=sd: wall_xf(q, to_wall(i["solid"], i["u"], i["z"]))),
                colour="iron", print_rot=("X", 180), note="face down, pegs up")
        else:
            add(it["id"], it["name"], (lambda i=it: i["solid"]), "signs",
                place=None, colour="iron", print_rot=("X", 180),
                note="blank spare -- face down, pegs up")
    PROP_ROT = {"37B": ("X", -90),        # broom rack lies flat
                "38A": ("X", 180), "38B": ("X", 180),   # wall-hung, pegs up
                "39C": ("X", 180)}
    for it in KT.props():
        sd = it.get("side")
        sx = -1 if sd == "L" else 1
        add(it["id"], it["name"], (lambda i=it: i["solid"]), "props",
            print_rot=PROP_ROT.get(it["id"]),
            place=(lambda s, i=it, q=sx: s.translate(
                (P.CHASSIS_W / 2 + q * (P.alley_half_width(i["u"]) - 7.0),
                 i["u"], BP + 4.0 + P.CAMBER))), colour="wood")

    # ---- 40-49 lighting hardware -------------------------------------------
    for it in KT.lighting_hardware():
        add(it["id"], it["name"], (lambda i=it: i["solid"]), "lighting",
            place=None, colour="black")

    # ---- 50-59 case ---------------------------------------------------------
    HO, WO, DO = P.BOOKNOOK_HEIGHT, P.BOOKNOOK_WIDTH, P.BOOKNOOK_DEPTH
    T, PH = P.SHELL_THICKNESS, P.PLINTH_HEIGHT
    add("50", "Outer_Left", lambda: CA.outer_side("L"), "case",
        place=lambda s: s.translate((-WO / 2, 0, PH)), colour="black",
        print_rot=("X", -90), note="lies flat, 200 x 214 -- never print this on edge")
    add("51", "Outer_Right", lambda: CA.outer_side("R"), "case",
        place=lambda s: s.mirror("XZ").translate((WO / 2, 0, PH)), colour="black",
        print_rot=("X", -90), note="lies flat")
    add("52", "Outer_Top", CA.outer_top, "case",
        place=lambda s: s.translate((0, 0, HO - T)), colour="black")
    add("53", "Outer_Back", CA.outer_back, "case",
        place=lambda s: s.translate((0, DO - T, PH)), colour="black",
        print_rot=("X", -90), note="service hatch -- pops off for LED access")
    add("54", "Plinth_Body", CA.plinth_body, "case", place=lambda s: s, colour="black")
    add("55", "Power_Drawer", CA.power_drawer, "case",
        place=lambda s: s.translate((0, DO - P.DRAWER_INNER_L - 6.0, 3.0)), colour="black")
    add("56", "Drawer_Face", CA.drawer_face, "case",
        place=lambda s: s.translate((0, DO - 3.0, 3.0)), colour="black",
        print_rot=("X", -90))
    add("57", "Batt_Cradle_x2", CA.batt_cradle, "case", place=None, colour="black")
    for side, pid in (("L", "58A"), ("R", "58B")):
        add(pid, f"Case_Spine_Trim_{side}", (lambda sd=side: CA.spine_trim(sd)), "case",
            place=None, colour="black", print_rot=("X", -90),
            note="214 mm long -- lies down")
    add("59", "Case_Clip_x6", CA.case_clip, "case", place=None, colour="black")
    add("59G", "Foot_Pad_x4", CA.foot_pad, "case", place=None, colour="black")

    # ---- 60-69 switch module ------------------------------------------------
    add("60", "Switch_Housing", CA.switch_housing, "switch", place=None, colour="black")
    add("61", "Switch_Cover", CA.switch_cover, "switch", place=None, colour="black",
        print_rot=("X", -90))
    for kind, pid in (("rocker", "62A"), ("slide", "62B"), ("button", "62C"),
                      ("blank", "62D")):
        add(pid, f"Switch_Bezel_{kind.title()}", (lambda k=kind: CA.switch_bezel(k)),
            "switch", place=None, colour="black", print_rot=("X", -90))
    add("63", "Jack_Plate_DC", CA.jack_plate, "switch", place=None, colour="black",
        print_rot=("X", -90))
    add("64", "Strain_Relief", CA.strain_relief, "switch", place=None, colour="black")
    add("65", "Remote_Clip", CA.remote_clip, "switch", place=None, colour="black")

    # ---- 70-79 jigs ---------------------------------------------------------
    for it in KT.jigs():
        add(it["id"], it["name"], (lambda i=it: i["solid"]), "jigs",
            place=None, colour="white")
    return M


# ==================================================================== export ==
def print_orient(solid, rot):
    if rot is None:
        return solid
    axis, deg = rot
    v = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]
    return solid.rotate((0, 0, 0), v, deg)


def drop_to_bed(solid):
    bb = solid.val().BoundingBox()
    return solid.translate((0, 0, -bb.zmin))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    for d in (STL, PREVIEW, PLATES):
        os.makedirs(d, exist_ok=True)

    M = manifest()
    if args.list:
        for m in M:
            print(f"{m['id']:>5}  {m['group']:<10} {m['name']}")
        print(f"\n{len(M)} printable parts")
        return

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    report, assembly, t0 = [], [], time.time()
    total_g = 0.0

    for m in M:
        if only and m["id"] not in only:
            continue
        t = time.time()
        try:
            solid = m["fn"]()
        except Exception as e:
            print(f"  FAIL {m['id']:>5} {m['name']}: {type(e).__name__}: {e}")
            report.append(dict(id=m["id"], name=m["name"], status="FAIL", error=str(e)))
            continue

        pr = drop_to_bed(print_orient(solid, m["print_rot"]))
        bb = pr.val().BoundingBox()
        vol = pr.val().Volume()
        grams = vol * 1.24 / 1000.0
        total_g += grams
        ok_bed = fits_bed(pr)
        nsolids = len(pr.val().Solids())

        fn = os.path.join(STL, f"{m['id']}_{m['name']}.stl")
        cq.exporters.export(pr, fn, tolerance=0.03, angularTolerance=0.2)

        report.append(dict(id=m["id"], name=m["name"], group=m["group"],
                           status="ok", grams=round(grams, 1), solids=nsolids,
                           bbox=[round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)],
                           fits_bed=ok_bed, colour=m["colour"], note=m["note"],
                           file=os.path.basename(fn)))
        flag = "" if ok_bed else "  << TOO BIG FOR BED"
        warn = "" if nsolids == 1 else f"  << {nsolids} SOLIDS"
        print(f"  {m['id']:>5} {m['name']:<34} {time.time()-t:5.1f}s "
              f"{bb.xlen:6.1f}x{bb.ylen:6.1f}x{bb.zlen:6.1f} {grams:6.1f} g{flag}{warn}")

        if m["place"] is not None and not args.no_preview:
            try:
                placed = m["place"](solid)
                assembly.append((m["id"], m["colour"], placed))
                # Record where the part actually lands in the assembly. verify.py needs
                # this to answer "does the chassis fit inside the case", which cannot be
                # answered from part sizes alone and was never being asked: the old
                # envelope check compared CASE_CAVITY_H against its own definition.
                pb = placed.val().BoundingBox()
                report[-1]["place_bbox"] = [round(v, 2) for v in
                                            (pb.xmin, pb.ymin, pb.zmin,
                                             pb.xmax, pb.ymax, pb.zmax)]
            except Exception as e:
                print(f"        (preview placement skipped: {e})")

    # A partial build must NOT replace the manifest. `--only 74A` used to leave a
    # two-entry manifest.json behind, and verify.py would then read it, check those two
    # parts and report that everything was fine.
    if only:
        print(f"  partial build ({len(report)} parts) -- manifest.json left alone")
    else:
        with open(os.path.join(OUT, "manifest.json"), "w") as f:
            json.dump(report, f, indent=1)

    if assembly and not args.no_preview:
        _write_previews(assembly)

    built = [r for r in report if r["status"] == "ok"]
    bad = [r for r in report if r["status"] != "ok"]
    big = [r for r in built if not r["fits_bed"]]
    multi = [r for r in built if r["solids"] != 1]
    print(f"\n{len(built)} parts built, {len(bad)} failed, {total_g:.0f} g PLA total, "
          f"{time.time()-t0:.0f}s")
    if big:
        print("  TOO BIG:", ", ".join(r["id"] for r in big))
    if multi:
        print("  MULTI-SOLID:", ", ".join(f"{r['id']}({r['solids']})" for r in multi))
    print(f"  STLs -> {STL}")


def _write_previews(assembly):
    asm = cq.Assembly()
    COL = dict(brick=(0.72, 0.44, 0.35), stone=(0.78, 0.75, 0.68), wood=(0.45, 0.32, 0.22),
               iron=(0.20, 0.20, 0.22), black=(0.12, 0.12, 0.13), grey=(0.55, 0.55, 0.57),
               white=(0.95, 0.94, 0.88), tan=(0.80, 0.70, 0.55))
    for pid, colour, solid in assembly:
        r, g, b = COL.get(colour, COL["tan"])
        asm.add(solid, name=pid, color=cq.Color(r, g, b, 1.0))
    asm.save(os.path.join(PREVIEW, "assembly.step"))
    try:
        cq.exporters.export(asm.toCompound(), os.path.join(PREVIEW, "assembly.stl"),
                            tolerance=0.06, angularTolerance=0.35)
    except Exception as e:
        print("  (assembly STL skipped:", e, ")")

    # exploded: push each part outward from the alley centreline
    exp = cq.Assembly()
    cx, cy = P.CHASSIS_W / 2, P.CHASSIS_D / 2
    for pid, colour, solid in assembly:
        bb = solid.val().BoundingBox()
        dx = bb.center.x - cx
        dy = bb.center.y - cy
        n = math.hypot(dx, dy) or 1.0
        k = 0.9
        r, g, b = COL.get(colour, COL["tan"])
        exp.add(solid.translate((dx / n * 60 * k, dy / n * 30 * k, 0)),
                name=pid, color=cq.Color(r, g, b, 1.0))
    exp.save(os.path.join(PREVIEW, "exploded.step"))
    print(f"  previews -> {PREVIEW}")


if __name__ == "__main__":
    main()
