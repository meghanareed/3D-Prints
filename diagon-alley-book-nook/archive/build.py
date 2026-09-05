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


# How thin a base, and how tippy a footprint, before a part wants a brim.
#
# ONE definition, because there were three. verify.py had all the rules, mf3.py had two
# of them and plates.py's checklist had one, so 13As_L_L_Window_A_Sill -- a part that
# had already come off the plate as spaghetti -- was warned about by verify.py, listed
# without a brim in the checklist, and shipped in the 3MF with no brim setting at all.
# Three copies of a rule is three chances to disagree, and they took all three.
SMALL_BASE = 25.0        # mm^2 of first layer, in absolute terms
TIPPY = 2.0              # height as a multiple of the narrower footprint dimension
BRIM_OVERHANG = 50.0     # mm^2, below which a big ratio does not matter
WIDE = 150.0             # mm LONG, at which a sheet is long enough to curl along it
THIN = 6.0               # mm tall, below which it has no height to resist curling
SPARSE = 0.25            # fraction of its own footprint a wide part puts on the bed
SLENDER = 8.0            # length as a multiple of width, at which a footprint is a strip
NARROW = 8.0             # mm, the width below which that strip has nothing to hold it
BRIM_WIDTH = 5.0         # mm. plates.py spaces parts so two of these cannot touch


def is_cut(row):
    """Is this part CUT from sheet rather than printed?

    The window panes drop into a DIFFUSER_SLOT_T rebate that is documented as taking
    vellum, acetate, PET or 1 mm acrylic as readily as a printed pane -- cut sheet is a
    designed-in option. Cutting them takes 25 parts off the facade plates, and acetate
    reads as glass where 0.8 mm of clear PLA reads as fog. 71A is the template: the
    outlines of all 25, taken from the panes themselves.

    They stay in the manifest and in the parts list -- they are still parts of the model
    and the template is generated from them -- but plates.py and mf3.py leave them off.
    """
    return row.get("group") in ("facade_L", "facade_R") and "Glazing" in row.get("name", "")


def needs_brim(row):
    """Does this manifest row want a brim? `row` is an entry from out/manifest.json."""
    bed = row.get("bed")
    if bed is None:
        return False
    if bed < SMALL_BASE:
        return True
    w, d, h = row.get("bbox", [99, 99, 0])
    if h > TIPPY * max(min(w, d), 0.01):
        return True
    # A big thin sheet. Adhesion AREA is not its problem -- the wall face has 31,000 mm^2
    # on the bed -- so none of the rules above sees it. Its problem is 2,480 mm of free
    # perimeter with 3.1 mm of height behind it: it shrinks as it cools, the corners and
    # the long torn front edge curl, and the nozzle drags the part around. The first wall
    # face printed here needed a brim and got one by hand; nothing in the file said so.
    # The wall ribs are the same problem in the other form: 10 mm tall, so not thin, but
    # a skeleton -- 5,864 mm^2 of first layer spread over a 203 x 197 mm footprint, in
    # strips two nozzles wide and 200 mm long. Strips like that curl exactly like a sheet.
    # Measured on the LONG side, not the short one. A sheet curls along its length, and
    # the width it curls across is beside the point: the glazing cut template is
    # 224 x 102 x 1.6 and will lift exactly like the 203 x 193 x 3.1 wall face, but a
    # min() test sees 102 and lets it through.
    if max(w, d) > WIDE and (h < THIN or bed < SPARSE * w * d):
        return True
    # A long thin strip. 15A_L_L_Drainpipe_Lower is 91.6 mm long and 4.3 mm wide with
    # 228 mm^2 on the bed -- too much base for the small-part rule, not wide enough for
    # the sheet rule, and it lifted at the ends far enough for the nozzle to strike it
    # and pile filament against it. Length over width is the thing that matters here:
    # a strip curls along its length and has no width to anchor the curl.
    if max(w, d) > SLENDER * max(min(w, d), 0.01) and min(w, d) < NARROW:
        return True
    over = row.get("overhang", 0.0)
    return over > BRIM_OVERHANG and over > 4.0 * max(bed, 0.1)


def bed_and_overhang(solid, layer=0.25, steep=0.707):
    """(area of the first layer, area facing down above it) in mm^2.

    Both measured on the part in its PRINT orientation, which is what the slicer sees.
    A part whose downward-facing area dwarfs its first layer is the one the slicer
    calls a floating cantilever: the window frame stood on its glazing bars alone,
    129.5 mm^2 of bed under 376.8 mm^2 of overhang, and the first anyone knew about it
    was a warning dialog.

    The first layer is measured as a real cross-section, not as "downward-facing faces
    near z=0". Those are not the same thing, and the difference is not academic: a
    plate sheared by 5 degrees has a bottom face that is still flat and still
    downward-facing, but its centroid sits well above the first layer, so counting
    faces said the ceiling baffle had 0.0 mm^2 on the bed and 11,189 mm^2 of overhang.
    It rests on one edge, which is a real problem, but not that one.
    """
    import numpy as np
    bb = solid.val().BoundingBox()
    slab = (cq.Workplane("XY")
            .box(bb.xlen + 8, bb.ylen + 8, layer, centered=(False, False, False))
            .translate((bb.xmin - 4, bb.ymin - 4, bb.zmin)))
    try:
        first = solid.intersect(slab)
        bed = (first.val().Volume() / layer) if first.val().Solids() else 0.0
    except Exception:
        bed = 0.0
    verts, tris = solid.val().tessellate(0.02)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    t = np.array(tris)
    if not len(t):
        return float(bed), 0.0
    tri = v[t]
    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(cr, axis=1) / 2.0
    good = area > 1e-9
    nz = np.zeros(len(area))
    nz[good] = cr[good, 2] / (2 * area[good])
    zc = tri[:, :, 2].mean(axis=1)
    over = good & (nz < -steep) & (zc > bb.zmin + layer)
    return float(bed), float(area[over].sum())


# Print orientations chosen by measurement rather than by eye. Each of these was
# standing on a point or hanging more than four times what it stood on, and the value
# here is whichever axis-aligned orientation measured best -- run `orient.py` to see the
# working. Twenty of them were resting on exactly two P1 pegs, 6.14 mm^2 of first layer,
# because their pegs point down and nothing turned them over; that is the same bug that
# was fixed once for the floor props and came back everywhere else.
#
# Note how many go from ("X", -90) to ("X", 90). That is a sign error, and it ran right
# through the case: 50_Outer_Left was resting on its stiffening ribs with the whole
# 200 x 214 panel in the air above them -- 40,883 mm^2 of overhang. The right way up it
# is 42,366 mm^2 flat on the bed and nothing overhanging at all.
#
# 30A_Sign_Vertical_Banner is deliberately NOT here. The sweep prefers it on edge, but
# it already has 76.7 mm^2 on the bed, which is enough, and a sign printed on edge has
# layer lines across the face you are going to paint.
PRINT_ROT_MEASURED = {
    "00": None,            "01R": ("Y", -90),     "02R": ("Y", -90),
    "03A": ("X", 180),     "03C": ("X", 180),     "04B": ("Y", -90),
    "04C": ("Y", -90),     "05": ("X", 90),       "06": ("Y", -90),
    "07": ("Y", -90),      "08": ("X", 90),       "10B": ("X", 180),
    "10Bc": ("X", 180),    "10D": ("X", 180),     "10Gl": ("X", 180),
    "11Ac": ("X", 180),    "11Fl": ("X", 180),    "12Al": ("X", 180),
    "13As": ("X", 180),    "13Bs": ("X", 180),    "13Cs": ("X", 180),
    "13Ds": ("X", 180),    "13Es": ("X", 180),    "13Fs": ("X", 180),
    "13Gs": ("X", 180),    "14As": ("X", 180),    "14Bs": ("X", 180),
    "15A": ("X", 180),     "15B": ("X", 180),     "15C": ("X", 180),
    "17A": ("X", 180),     "17B": ("X", 180),     "18A": ("X", 180),
    "19B": ("X", 180),     "19C": ("X", 180),     "20Es": ("X", 180),
    "20G": ("X", 180),     "21Bl": ("X", 180),    "21D": ("X", 180),
    "21E": ("X", 180),     "22Al": ("X", 180),    "23As": ("X", 180),
    "23Bs": ("X", 180),    "23Cs": ("X", 180),    "23Ds": ("X", 180),
    "23Es": ("X", 180),    "23Fs": ("X", 180),    "23Gs": ("X", 180),
    "23Hs": ("X", 180),    "24Ac": ("X", 180),    "25A": ("X", 180),
    "25B": ("X", 180),     "27A": ("X", 180),     "27B": ("X", 180),
    "28A": ("X", 180),     "29B": ("X", 180),     "29C": ("X", 180),
    # Signs are deliberately ABSENT from this table. It used to stand nine of them on
    # edge, ("X", -90), which was measured back when a sign carried a peg on its back
    # and the only question was where the peg pointed. A sign now lies back-down with
    # its lettering standing up, and manifest() sets that for every sign in one place.
    "31A": ("Y", -90),      "31B": ("Y", -90),      "31C": ("Y", -90),
    "31D": ("Y", -90),      "32B": None,           "32C": ("X", 90),
    "33A": None,           "34A": None,           "34C": ("X", -90),
    "36B": ("Y", 90),      "37C": ("X", 180),     "39C": ("X", 90),
    "43": ("X", 180),      "44": ("X", 180),      "45A": ("X", 180),
    "45B": ("X", 180),     "45C": ("X", 180),     "50": ("X", 90),
    "51": ("X", 90),       "52": ("X", 180),      "53": ("X", 90),
    "56": ("X", 90),       "58A": ("Y", 90),      "58B": ("Y", 90),
    "62A": ("X", 90),      "62B": ("X", 90),      "62C": ("X", 90),
    "62D": ("X", 90),      "63": ("X", 90),       "64": ("X", -90),
}


# =============================================================== the manifest ==
def manifest():
    """Every printable part: id, name, builder, group, print orientation, colour.

    `place` positions the part in the assembled preview. `print_rot` is applied only
    on export, so each STL lands on the bed in the orientation it should be printed.
    """
    M = []

    def add(pid, name, fn, group, place=None, print_rot=None, colour="tan", note=""):
        if pid in PRINT_ROT_MEASURED:
            print_rot = PRINT_ROT_MEASURED[pid]
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
        s = s.rotate((0 if side == "L" else W, 0, 0), (0 if side == "L" else W, 0, 1),
                     -P.WALL_CANT_DEG if side == "L" else P.WALL_CANT_DEG)
        # Then sit the assembly on the pan.
        #
        # A wall is FACE + RIB_GAP + WALL_SERVICE_D deep and is built about the face
        # plate: the face runs 0..FACE and the rib hangs behind it at -(GAP + D)..-GAP,
        # exactly as wall_rib's docstring says. So wall-local x=0 is the BACK of the
        # face, not the back of the assembly, and placing the assembly at x=0 hung the
        # ribs 7.5 mm off the side of the base pan -- most of the 21 mm by which the
        # chassis would not fit its own case. Offsetting by the depth behind the face
        # puts the rib's outer face flush with the pan edge and the face's brick
        # surface on the alley line.
        off = P.RIB_GAP + P.WALL_SERVICE_D
        return s.translate((off if side == "L" else -off, 0, 0))

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
        .translate((P.CHASSIS_W / 2, ST.Y_SKYDIFF + 1.0, BP + 68.0)), colour="white",
        note="natural/white PLA, 3 walls, 0 % infill")
    # 68.0, not 28.0: the diffuser hangs 40 mm below the point it is placed at, so at
    # 28 it ran from z -2 to 78 and drove 193 mm^3 straight through the base pan, while
    # the puck it diffuses sits centred on z 78. The old envelope check folded this
    # into a bounding-box height and reported it as the chassis being 2.9 mm too tall.
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
    # Signs print TEXT UP. They used to print ("X", 180) -- "face down, pegs up" --
    # which laid every raised letter on the bed to be squashed and elephant-footed. The
    # peg is gone from the back of a sign plate (it is a socket and a loose pin now), so
    # the plate lies back-down and flat with its lettering standing in clear air.
    # Brackets and lanterns still carry pegs and still print pegs-up.
    import data.facade as FD
    for it in KT.signs():
        sd = it.get("side")
        row = next((r for r in FD.SIGNS if r["id"] == it["id"]), {})
        br = KT._bracket_row(row) if row.get("kind") == "swing" else None
        u, z = it["u"], it["z"]        # kit.signs() already anchors a fused sign
        # A flat sign already lies plate-down. A fused hanging sign is built in the
        # bracket's plane, which puts its 2.9 mm thickness along the part's X, so it
        # would stand on edge 32 mm tall; a quarter turn lays it down with the
        # lettering up, which is the whole reason the plate turned in the first place.
        add(it["id"], it["name"], (lambda i=it: i["solid"]), "signs",
            place=((lambda s, i=it, q=sd, uu=u, zz=z:
                    wall_xf(q, to_wall(i["solid"], uu, zz)))
                   if sd in ("L", "R") else None),
            colour="iron", print_rot=(("Y", -90) if br else None),
            note="text up" if sd in ("L", "R") else "blank spare -- text up")
    for it in KT.brackets() + KT.lanterns():
        sd = it.get("side")
        add(it["id"], it["name"], (lambda i=it: i["solid"]), "signs",
            place=((lambda s, i=it, q=sd: wall_xf(q, to_wall(i["solid"], i["u"], i["z"])))
                   if sd in ("L", "R") else None),
            colour="iron", print_rot=("X", 180),
            note="face down, pegs up" if sd in ("L", "R") else "blank spare")
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
        bed_a, over_a = bed_and_overhang(pr)
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
                           bed=round(bed_a, 1), overhang=round(over_a, 1),
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
        # ... and a full build owns out/stl. Merging the sills into their frames removed
        # 35 parts and collapsing the glazing templates removed 3 more, and every one of
        # their STLs stayed on disk and went into the repo: a 13As_L_L_Window_A_Sill.stl
        # that is now part of 13A, ready to be printed by anyone browsing the folder.
        # plates.py already clears its own directory for exactly this reason. A partial
        # build owns nothing and deletes nothing.
        want = {r["file"] for r in report}
        gone = sorted(f for f in os.listdir(STL) if f.endswith(".stl") and f not in want)
        for f in gone:
            os.remove(os.path.join(STL, f))
        if gone:
            print(f"  removed {len(gone)} STL(s) for parts that no longer exist: "
                  + ", ".join(g[:-4] for g in gone[:3])
                  + (" ..." if len(gone) > 3 else ""))

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
