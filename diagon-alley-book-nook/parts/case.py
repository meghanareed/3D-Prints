"""Outer case, plinth, power drawer and switch module.

The case is a SLEEVE, not a box: left + right + top + plinth clip together once and
stay together, the finished chassis slides in from the rear on the plinth's dovetail
rails, and the rear panel is a removable service hatch. Battery changes never require
opening anything -- the drawer slides out below the hatch.
"""
import math
import cadquery as cq
import params as P
from lib.mount import c4_clip, c4_catch, peg_p1, socket_p1_solids, C4_L, C4_W, C4_T
from lib.util import compound, batch_cut, batch_add, keep_largest, try_chamfer

WO, HO, DO = P.BOOKNOOK_WIDTH, P.BOOKNOOK_HEIGHT, P.BOOKNOOK_DEPTH
T = P.SHELL_THICKNESS
PH = P.PLINTH_HEIGHT
PANEL_H = HO - PH - T          # side panels sit on the plinth, capped by the top
CLIP_Z = [PANEL_H * 0.22, PANEL_H * 0.55, PANEL_H * 0.86]


def _clip_slots(panel, ys, zs, axis="+Y"):
    cuts = []
    for y in ys:
        for z in zs:
            cuts.append(cq.Workplane("XY")
                        .box(C4_L + 2 * P.FIT_CLEARANCE, T * 3,
                             C4_W + 2 * P.FIT_CLEARANCE, centered=(True, True, True))
                        .translate((y, 0, z)))
    return batch_cut(panel, cuts)


# ----------------------------------------------------------- 50 / 51 sides ---
def outer_side(side):
    """One-piece on a 256 bed. If PANEL_SPLIT is True the exporter emits halves."""
    panel = cq.Workplane("XY").box(DO, T, PANEL_H, centered=(False, False, False))
    adds, cuts = [], []
    # stiffening ribs at the free (front) edge and along the top, where a 2.2 mm panel
    # would otherwise bow
    adds.append(cq.Workplane("XY").box(4.0, 3.0, PANEL_H, centered=(False, False, False))
                .translate((0, T, 0)))
    adds.append(cq.Workplane("XY").box(DO, 3.0, 4.0, centered=(False, False, False))
                .translate((0, T, PANEL_H - 4.0)))
    # clip pockets that engage the top panel and the plinth
    for y in (DO * 0.2, DO * 0.55, DO * 0.85):
        cuts.append(cq.Workplane("XY")
                    .box(C4_L + 2 * P.FIT_CLEARANCE, T * 4, C4_T + 1.6,
                         centered=(True, True, False)).translate((y, T / 2, PANEL_H - C4_T - 1.6)))
        cuts.append(cq.Workplane("XY")
                    .box(C4_L + 2 * P.FIT_CLEARANCE, T * 4, C4_T + 1.6,
                         centered=(True, True, False)).translate((y, T / 2, 0)))
    # rear hatch catches
    for z in CLIP_Z:
        cuts.append(cq.Workplane("XY").box(6.0, T * 4, C4_W + 2 * P.FIT_CLEARANCE,
                                           centered=(True, True, True))
                    .translate((DO - 4.0, T / 2, z)))
    panel = batch_add(panel, adds)
    panel = batch_cut(panel, cuts)
    return keep_largest(panel, f"5{0 if side == 'L' else 1}_Outer_{side}")


# ------------------------------------------------------------------ 52 top ---
def outer_top():
    top = cq.Workplane("XY").box(WO, DO, T, centered=(True, False, False))
    adds = []
    for sx in (-1, 1):
        adds.append(cq.Workplane("XY").box(3.0, DO, 4.0, centered=(True, False, False))
                    .translate((sx * (WO / 2 - T - 1.5), 0, -4.0)))
        for y in (DO * 0.2, DO * 0.55, DO * 0.85):
            adds.append(clip_oriented(sx)
                        .translate((sx * (WO / 2 - T - C4_T), y, -C4_W + 0.8)))
    return keep_largest(batch_add(top, adds), "52_Outer_Top")


# ---------------------------------------------------------- 53 rear hatch ----
def outer_back():
    w = WO - 2 * T - 2 * P.FIT_CLEARANCE
    hatch = cq.Workplane("XY").box(w, T, PANEL_H - 2 * P.FIT_CLEARANCE,
                                   centered=(True, False, False))
    adds, cuts = [], []
    for sx in (-1, 1):
        for z in CLIP_Z:
            adds.append(clip_oriented(sx)
                        .rotate((0, 0, 0), (1, 0, 0), -90)    # beam now runs along -Z
                        .translate((sx * (w / 2 - C4_T), T, z)))
    # switch-module keyhole and the cable grommet
    cuts.append(cq.Workplane("XY").box(28.0, T * 4, 18.0, centered=(True, True, True))
                .translate((0, T / 2, PANEL_H * 0.30)))
    cuts.append(cq.Workplane("XY").cylinder(T * 4, 3.4)
                .rotate((0, 0, 0), (1, 0, 0), 90).translate((22.0, T / 2, PANEL_H * 0.30)))
    # finger notch so the hatch can be popped without a tool
    cuts.append(cq.Workplane("XY").cylinder(T * 4, 7.0)
                .rotate((0, 0, 0), (1, 0, 0), 90)
                .translate((0, T / 2, PANEL_H - 2.0)))
    hatch = batch_add(hatch, adds)
    hatch = batch_cut(hatch, cuts)
    return keep_largest(hatch, "53_Outer_Back")


# -------------------------------------------------------- 54 plinth body -----
def plinth_body():
    body = cq.Workplane("XY").box(WO, DO, PH, centered=(True, False, False))
    cuts, adds = [], []
    dl, dw, dh = P.DRAWER_INNER_L, P.DRAWER_INNER_W, P.DRAWER_INNER_H
    # drawer cavity, open at the rear
    cuts.append(cq.Workplane("XY")
                .box(dw + 2 * P.FIT_CLEARANCE, dl + 40.0, dh + 2 * P.FIT_CLEARANCE,
                     centered=(True, False, False))
                .translate((0, DO - dl - 6.0, 3.0)))
    # drawer runners
    for sx in (-1, 1):
        adds.append(cq.Workplane("XY").box(2.0, dl + 2.0, 2.0, centered=(True, False, False))
                    .translate((sx * (dw / 2 - 1.0), DO - dl - 5.0, 3.0)))
    # chassis dovetail rails on top
    for sx in (-1, 1):
        adds.append(_dovetail_socket(DO - 4.0)
                    .translate((sx * (P.CHASSIS_W / 2 - 12.0), 2.0, PH)))
    # wire drop from the chassis bus into the drawer
    cuts.append(cq.Workplane("XY").cylinder(PH * 3, 3.4).translate((0, DO - 12.0, 0)))
    # clip ledges for the side panels
    for sx in (-1, 1):
        for y in (DO * 0.2, DO * 0.55, DO * 0.85):
            cuts.append(cq.Workplane("XY")
                        .box(C4_L + 2 * P.FIT_CLEARANCE, C4_W + 2 * P.FIT_CLEARANCE,
                             C4_T + 1.6, centered=(True, True, False))
                        .translate((sx * (WO / 2 - T / 2), y, PH - C4_T - 1.6)))
    # feet
    for sx in (-1, 1):
        for y in (14.0, DO - 14.0):
            cuts.append(cq.Workplane("XY").cylinder(4.0, 5.0)
                        .translate((sx * (WO / 2 - 12.0), y, -1.0)))
    # Hollow the solid block in front of the drawer, and coffer what is left. A solid
    # plinth is 300 g of PLA doing nothing -- this brings it under 100 g.
    front_d = DO - dl - 8.0
    for i in range(2):
        for j in range(3):
            pw = (WO - 4 * 4.0) / 2
            pd = (front_d - 4 * 4.0) / 3
            if pw > 4 and pd > 4:
                cuts.append(cq.Workplane("XY")
                            .box(pw, pd, PH - 5.0, centered=(False, False, False))
                            .translate((-WO / 2 + 4.0 + i * (pw + 4.0),
                                        4.0 + j * (pd + 4.0), 2.5)))
    # coffer the floor under the drawer
    for i in range(3):
        for j in range(4):
            pw = (WO - 5 * 4.0) / 3
            pd = (dl - 5 * 4.0) / 4
            if pw > 4 and pd > 4:
                cuts.append(cq.Workplane("XY")
                            .box(pw, pd, 2.0, centered=(False, False, False))
                            .translate((-WO / 2 + 4.0 + i * (pw + 4.0),
                                        DO - dl - 4.0 + 4.0 + j * (pd + 4.0), 0.5)))
    body = batch_add(body, adds)
    body = batch_cut(body, cuts)
    return keep_largest(body, "54_Plinth_Body")


def _dovetail_socket(length, w=9.0, h=3.0, c=None):
    c = P.SLIP_CLEARANCE if c is None else c
    outer = cq.Workplane("XZ").polyline([(-w * 0.5 - 3, 0), (-w * 0.5 - 3, h + 1.0),
                                         (w * 0.5 + 3, h + 1.0), (w * 0.5 + 3, 0)]) \
        .close().extrude(-length)
    slot = cq.Workplane("XZ").polyline([(-w * 0.25 - c, -1), (-w * 0.5 - c, h),
                                        (w * 0.5 + c, h), (w * 0.25 + c, -1)]) \
        .close().extrude(-length)
    return outer.cut(slot)


# --------------------------------------------------------- 55/56 drawer ------
def power_drawer():
    dl, dw, dh = P.DRAWER_INNER_L, P.DRAWER_INNER_W, P.DRAWER_INNER_H
    wall = 1.6
    tray = cq.Workplane("XY").box(dw, dl, dh, centered=(True, False, False))
    tray = tray.cut(cq.Workplane("XY").box(dw - 2 * wall, dl - 2 * wall, dh,
                                           centered=(True, False, False))
                    .translate((0, wall, wall)))
    adds, cuts = [], []
    # two battery-box cradles plus a bay for the puck controller
    for sx in (-1, 1):
        adds.append(cq.Workplane("XY").box(1.6, P.BATT_BOX_L + 2, 6.0,
                                           centered=(True, False, False))
                    .translate((sx * (P.BATT_BOX_W / 2 + 0.8), 8.0, wall)))
    adds.append(cq.Workplane("XY").box(dw - 2 * wall, 1.6, 6.0, centered=(True, True, False))
                .translate((0, 8.0 + P.BATT_BOX_L + 4.0, wall)))
    # runners
    for sx in (-1, 1):
        cuts.append(cq.Workplane("XY").box(2.0 + 2 * P.FIT_CLEARANCE, dl + 2,
                                           2.0 + 2 * P.FIT_CLEARANCE,
                                           centered=(True, False, True))
                    .translate((sx * (dw / 2 - 1.0), -1, wall + 1.0)))
    # cable entry from the chassis above
    cuts.append(cq.Workplane("XY").cylinder(dh * 3, 3.4).translate((0, dl - 14.0, 0)))
    tray = batch_add(tray, adds)
    tray = batch_cut(tray, cuts)
    return keep_largest(tray, "55_Power_Drawer")


def drawer_face():
    dw, dh = P.DRAWER_INNER_W, P.DRAWER_INNER_H
    face = cq.Workplane("XY").box(dw + 6.0, 3.0, dh + 5.0, centered=(True, False, False))
    face = face.cut(cq.Workplane("XY").cylinder(6.0, 8.0)
                    .rotate((0, 0, 0), (1, 0, 0), 90)
                    .translate((0, 1.6, dh + 5.0)))
    for sx in (-1, 1):
        face = face.union(peg_p1((sx * (dw / 2 - 6.0), 3.0, (dh + 5.0) / 2), axis="+Y"))
    return keep_largest(face, "56_Drawer_Face")


def batt_cradle():
    l, w, h = P.BATT_BOX_L, P.BATT_BOX_W, P.BATT_BOX_H
    c = 0.4
    body = cq.Workplane("XY").box(w + 3.2, l + 3.2, h * 0.55, centered=(True, False, False))
    body = body.cut(cq.Workplane("XY").box(w + 2 * c, l + 2 * c, h,
                                           centered=(True, False, False))
                    .translate((0, 1.6, 1.6)))
    # shims for a smaller pack (coin-cell holders are much shorter than a 3xAAA box)
    for sy in (0.0, l * 0.5):
        body = body.union(cq.Workplane("XY").box(w + 3.2, 1.6, h * 0.55,
                                                 centered=(True, False, False))
                          .translate((0, 1.6 + sy, 0)) if False else body)
    return keep_largest(body, "57_Batt_Cradle")


# ------------------------------------------------------ 58 / 59 case trim ----
def spine_trim(side):
    t = cq.Workplane("XY").box(4.0, 4.0, PANEL_H, centered=(False, False, False))
    t = try_chamfer(t, "|Z", 1.2)
    for z in (PANEL_H * 0.25, PANEL_H * 0.75):
        t = t.union(peg_p1((2.0, 4.0, z), axis="+Y", rot=90))
    return t


def case_clip():
    """59x -- separate clips, so they can be printed in a tougher filament than the
    panels if you have one, and replaced if one ever fatigues."""
    body = c4_clip()
    # the root pad must OVERLAP the beam, not merely touch it, or it stays a second
    # disconnected solid
    body = body.union(cq.Workplane("XY").box(7.0, C4_W, C4_T,
                                             centered=(False, False, False))
                      .translate((-6.0, 0, 0)))
    return keep_largest(body, "59_Case_Clip")


def clip_oriented(sx):
    """A C4 clip with its beam along +Y and its barb pointing along sx*X, which is how
    both the top panel and the rear hatch need it."""
    c = c4_clip().rotate((0, 0, 0), (1, 1, 1), 120)      # beam +Y, barb +X, width +Z
    if sx < 0:
        c = c.rotate((0, 0, 0), (0, 0, 1), 180)
    return c


def foot_pad():
    return try_chamfer(cq.Workplane("XY").cylinder(3.6, 4.8 - P.FIT_CLEARANCE), ">Z", 0.8)


# ------------------------------------------------------- 60-65 switch --------
def switch_housing():
    w, h, d = 34.0, 24.0, 14.0
    body = cq.Workplane("XY").box(w, d, h, centered=(True, False, False))
    body = body.cut(cq.Workplane("XY").box(w - 3.2, d - 1.6, h - 3.2,
                                           centered=(True, False, False))
                    .translate((0, 1.6, 1.6)))
    # bezel aperture
    body = body.cut(cq.Workplane("XY").box(24.0, 4.0, 16.0, centered=(True, False, False))
                    .translate((0, -1, h / 2 - 8.0)))
    # keyhole tongues that lock it into the rear hatch
    for sx in (-1, 1):
        body = body.union(cq.Workplane("XY").box(3.0, 3.0, 8.0, centered=(True, False, False))
                          .translate((sx * (13.0), -3.0, h / 2 - 4.0)))
    # strain-relief posts
    for sx in (-1, 1):
        body = body.union(cq.Workplane("XY").cylinder(6.0, 1.8, centered=(True, True, False))
                          .translate((sx * 5.0, d - 5.0, 1.6)))
    return keep_largest(body, "60_Switch_Housing")


def switch_cover():
    w, h = 34.0, 24.0
    cov = cq.Workplane("XY").box(w - 0.6, 2.0, h - 0.6, centered=(True, False, False))
    cov = cov.union(cq.Workplane("XY").box(w - 4.0, 3.0, 3.0, centered=(True, False, False))
                    .translate((0, -3.0, 2.0)))
    # cable clamp ridge
    cov = cov.union(cq.Workplane("XY").box(12.0, 3.0, 2.4, centered=(True, False, False))
                    .translate((0, -3.0, h - 6.0)))
    return cov


def switch_bezel(kind="rocker"):
    """62A/B/C -- one housing, three swappable bezels. Pick the switch after printing,
    not before."""
    plate = cq.Workplane("XY").box(26.0, 2.0, 18.0, centered=(True, False, False))
    if kind == "rocker":
        cut = cq.Workplane("XY").box(20.0 + 2 * P.FIT_CLEARANCE, 8.0,
                                     13.0 + 2 * P.FIT_CLEARANCE, centered=(True, True, True))
    elif kind == "slide":
        cut = cq.Workplane("XY").box(11.0 + 2 * P.FIT_CLEARANCE, 8.0,
                                     7.0 + 2 * P.FIT_CLEARANCE, centered=(True, True, True))
    elif kind == "button":
        cut = cq.Workplane("XY").cylinder(8.0, 6.0 + P.FIT_CLEARANCE) \
            .rotate((0, 0, 0), (1, 0, 0), 90)
    else:                                   # blank
        cut = cq.Workplane("XY").box(0.001, 0.001, 0.001)
    plate = plate.cut(cut.translate((0, 1.0, 9.0)))
    for sx in (-1, 1):
        plate = plate.union(peg_p1((sx * 11.0, 2.0, 9.0), axis="+Y", rot=90))
    return plate


def jack_plate():
    plate = cq.Workplane("XY").box(26.0, 2.0, 18.0, centered=(True, False, False))
    plate = plate.cut(cq.Workplane("XY").cylinder(8.0, 4.0 + P.FIT_CLEARANCE)
                      .rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 1.0, 9.0)))
    for sx in (-1, 1):
        plate = plate.union(peg_p1((sx * 11.0, 2.0, 9.0), axis="+Y", rot=90))
    return plate


def strain_relief(cable=None):
    """64 -- serpentine: the cable weaves between three posts, so a tug on the lead
    never reaches the joint inside."""
    cable = cable or (P.PUCK_CABLE_DIA + 0.8)
    body = cq.Workplane("XY").box(26.0, 14.0, 2.4, centered=(True, False, False))
    for i, sx in enumerate((-1, 1, -1)):
        body = body.union(cq.Workplane("XY")
                          .cylinder(7.0, cable * 0.55, centered=(True, True, False))
                          .translate((sx * cable * 0.9, 3.0 + i * 4.0, 2.4)))
    for sx in (-1, 1):
        body = body.union(peg_p1((sx * 10.0, 12.0, 0.0), axis="-Z"))
    return body


def remote_clip():
    """65 -- parks the puck's IR remote on the back of the case, where it is useful
    only while the nook is open. See the note in the assembly guide."""
    body = cq.Workplane("XY").box(44.0, 4.0, 14.0, centered=(True, False, False))
    for sx in (-1, 1):
        body = body.union(cq.Workplane("XY").box(3.0, 12.0, 14.0,
                                                 centered=(True, False, False))
                          .translate((sx * 20.5, 0, 0)))
        body = body.union(peg_p1((sx * 14.0, 0.0, 7.0), axis="-Y"))
    return body
