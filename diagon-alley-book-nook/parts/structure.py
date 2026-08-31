"""Chassis structure: base pan, cobblestone floor, rear perspective assembly,
ceiling baffle, front arch header and the chassis rear wall.

Depth budget for the rear bay (y measured from the front opening):
    150.6 - 172.0   rear perspective block, four compressed storeys
    174.0           opaque silhouette screen, 1.6 thick
    178.0           printed sky diffuser, 0.8 thick        <- 4 mm air gap
    184.8 - 193.1   RGB/CCT puck, face forward             <- 6 mm air gap
    195.1 - 197.1   chassis rear wall
The two air gaps are what stop the puck's twelve discrete beads reading as twelve
dots through the sky.
"""
import math
import cadquery as cq
import params as P
import data.facade as F
from lib.cobble import cobble_field, camber_solid
from lib.brick import brick_field
from lib.mount import (peg_p1, peg_p2, socket_p1_solids, socket_p2_solids,
                       tongue_t3, groove_t3_solids, c4_clip, c4_catch)
from lib.light import puck_cradle, diffuser_plate
from lib.util import compound, batch_cut, batch_add, keep_largest, try_chamfer, rng
from lib.window import window_frame, glazing, door, aperture

W_CH, D_CH, H_CH = P.CHASSIS_W, P.CHASSIS_D, P.CHASSIS_H
WA = P.WALL_ASSEMBLY_D
CX = W_CH / 2.0

Y_BLOCK_0, Y_BLOCK_1 = P.ALLEY_D, 172.0
Y_SCREEN, Y_SKYDIFF = 174.0, 178.0
Y_PUCK, Y_REARWALL = 184.8, 195.1

FLOOR_T = 4.0
RAIL_W = 6.0


def _hw(y):
    """Half-width of the clear alley at depth y."""
    return P.alley_half_width(y)


# ------------------------------------------------------------- 00 base pan ---
def base_pan():
    t = P.BASE_PAN_T
    body = cq.Workplane("XY").box(W_CH, D_CH, t, centered=(False, False, False))
    cuts, adds = [], []

    # lighten: a coffered underside, leaving a 2 mm deck and 3 mm ribs
    for i in range(3):
        for j in range(7):
            w = (W_CH - 4 * 5.0) / 3
            d = (D_CH - 8 * 5.0) / 7
            cuts.append(cq.Workplane("XY").box(w, d, t - 2.0, centered=(False, False, False))
                        .translate((5.0 + i * (w + 5.0), 5.0 + j * (d + 5.0), 0)))

    # T3 grooves for the two wall assemblies, following the cant
    for sx, x0 in ((1, 0.0), (-1, W_CH)):
        for k in range(4):
            y = D_CH * (k + 0.5) / 4
            xw = x0 + sx * (WA / 2 + (min(y, P.ALLEY_D) * math.tan(math.radians(P.WALL_CANT_DEG)) * sx * 0))
            c, _ = groove_t3_solids((xw, y, t), 26.0, axis="-Z", rot=90)
            cuts.append(c)

    # floor rails
    for sx in (-1, 1):
        adds.append(cq.Workplane("XY")
                    .box(RAIL_W, P.ALLEY_D + 2.0, 2.0, centered=(True, False, False))
                    .translate((CX + sx * (_hw(0) - RAIL_W / 2 - 1.0), 0, t)))

    # wire bus along the rear edge, plus grommets up into both wall ribs
    cuts.append(cq.Workplane("XY").box(W_CH - 12.0, P.BUS_CHANNEL_WIDTH,
                                       P.WIRE_CHANNEL_DEPTH, centered=(True, True, False))
                .translate((CX, D_CH - 8.0, t - P.WIRE_CHANNEL_DEPTH)))
    for sx in (-1, 1):
        for y in (D_CH * 0.25, D_CH * 0.75):
            cuts.append(cq.Workplane("XY").cylinder(t * 3, 2.2)
                        .translate((CX + sx * (W_CH / 2 - WA / 2), y, 0)))
    # drop into the plinth drawer
    cuts.append(cq.Workplane("XY").cylinder(t * 3, 3.2).translate((CX, D_CH - 8.0, 0)))

    # dovetail rails underneath, for sliding the cartridge into the case
    for sx in (-1, 1):
        adds.append(_dovetail_rail(D_CH - 4.0)
                    .translate((CX + sx * (W_CH / 2 - 12.0), 2.0, -3.0)))

    body = batch_cut(body, cuts)
    body = batch_add(body, adds)
    return keep_largest(body, "00_Chassis_Base_Pan")


def _dovetail_rail(length, w=9.0, h=3.0):
    """Runs along Y. Built on XZ (whose normal is -Y) and extruded negatively, so it
    grows in +Y; an YZ workplane would have extruded it across the pan instead."""
    return (cq.Workplane("XZ")
            .polyline([(-w * 0.25, 0), (-w * 0.5, h), (w * 0.5, h), (w * 0.25, 0)])
            .close().extrude(-length))


# ------------------------------------------------- 04 cobblestone floor ------
def cobblestone_floor():
    L = P.ALLEY_D
    deck = (cq.Workplane("XY")
            .polyline([(-_hw(0), 0), (_hw(0), 0), (_hw(L), L), (-_hw(L), L)])
            .close().extrude(FLOOR_T))
    deck = deck.union(camber_solid(L, _hw, crown=P.CAMBER).translate((0, 0, FLOOR_T)))
    def camber_at(x, y):
        hw0 = _hw(0.0)
        tt = max(-1.0, min(1.0, x / hw0))
        return FLOOR_T + P.CAMBER * (1 - tt * tt)

    stones = cobble_field(L, _hw, tag="floor", base_fn=camber_at)
    if stones is not None:
        deck = deck.union(stones)

    cuts, adds = [], []
    # gutter troughs at both kerbs
    for sx in (-1, 1):
        cuts.append(cq.Workplane("XY")
                    .polyline([(sx * (_hw(0) - 4.0), -1), (sx * _hw(0), -1),
                               (sx * _hw(L), L + 1), (sx * (_hw(L) - 3.0), L + 1)])
                    .close().extrude(3.0).translate((0, 0, FLOOR_T + P.CAMBER - 0.6)))
    # rail slots, so the floor drops onto the base pan and locates itself
    for sx in (-1, 1):
        cuts.append(cq.Workplane("XY")
                    .box(RAIL_W + 2 * P.FIT_CLEARANCE, L + 3.0, 2.0 + P.FIT_CLEARANCE,
                         centered=(True, False, False))
                    .translate((sx * (_hw(0) - RAIL_W / 2 - 1.0), -1.5, 0)))
    # prop sockets
    import data.facade as FD
    for row in FD.PROPS:
        if row["kind"] in ("notice", "posters"):
            continue
        sx = -1 if row["side"] == "L" else 1
        x = sx * (_hw(row["u"]) - 7.0)
        c, a = socket_p1_solids((x, row["u"], FLOOR_T + P.CAMBER), axis="-Z")
        cuts.append(c)
        adds.append(a)

    deck = batch_cut(deck, cuts)
    deck = batch_add(deck, adds)
    return keep_largest(deck, "04_Cobblestone_Floor")


def gutter_strip(side):
    """04B / 04C -- separate drain strip with grates, so it paints as wet stone."""
    L = P.ALLEY_D
    sx = -1 if side == "L" else 1
    strip = cq.Workplane("XY").box(4.0, L, 2.6, centered=(True, False, False))
    cuts = []
    for k in range(4):
        y = L * (k + 0.5) / 4
        for i in range(3):
            cuts.append(cq.Workplane("XY").box(2.6, 0.7, 1.2, centered=(True, True, False))
                        .translate((0, y + (i - 1) * 1.4, 1.4)))
    strip = batch_cut(strip, cuts)
    for y in (L * 0.2, L * 0.8):
        strip = strip.union(peg_p1((0.0, y, 0.0), axis="-Z"))
    return strip


# ------------------------------------- 03 rear forced-perspective assembly ---
def rear_block():
    """03A -- the far end of the lane: converging facades at roughly 0.55 scale with
    four compressed storeys, so the eye reads distance rather than a wall."""
    d = Y_BLOCK_1 - Y_BLOCK_0
    hwf, hwr = _hw(Y_BLOCK_0), 15.0
    h = P.SCENE_H * 0.82

    shell = (cq.Workplane("XY")
             .polyline([(-hwf, 0), (hwf, 0), (hwr, d), (-hwr, d)])
             .close().extrude(h))
    void = (cq.Workplane("XY")
            .polyline([(-hwf + 9.0, -1), (hwf - 9.0, -1), (hwr - 5.0, d + 1),
                       (-hwr + 5.0, d + 1)])
            .close().extrude(h - 8.0))
    body = shell.cut(void)

    cuts, adds = [], []
    # four compressed storeys of small windows on each cheek
    r = rng("rearblock")
    for sx in (-1, 1):
        for k in range(4):
            zc = 14.0 + k * (h - 26.0) / 4
            for j in range(2):
                yy = d * (0.28 + 0.42 * j)
                w = 8.5 - k * 0.7
                hh = 10.0 - k * 0.9
                cuts.append(cq.Workplane("XY").box(20.0, w, hh, centered=(True, True, True))
                            .translate((sx * (hwf - (hwf - hwr) * yy / d), yy, zc)))
    # Horizontal string courses instead of brick relief. The cheeks taper from hwf to
    # hwr, so a flat brick field does not lie on them -- it floated. At 0.55 scale and
    # this far back, banded stonework reads better than brick anyway.
    for sx in (-1, 1):
        p0 = (sx * hwf, 0.0)
        p1 = (sx * hwr, d)
        blen = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        theta = math.degrees(math.atan2(-(p1[0] - p0[0]), p1[1] - p0[1]))
        mid = ((p0[0] + p1[0]) / 2 - sx * 0.5, (p0[1] + p1[1]) / 2)
        for k in range(9):
            zc = 8.0 + k * (h - 16.0) / 8
            adds.append(cq.Workplane("XY")
                        .box(1.2, blen, 2.0, centered=(True, True, True))
                        .rotate((0, 0, 0), (0, 0, 1), theta)
                        .translate((mid[0], mid[1], zc)))
    body = batch_cut(body, cuts)
    body = batch_add(body, adds)
    for sx in (-1, 1):
        body = body.union(peg_p1((sx * (hwf - 5.0), 3.0, 0.0), axis="-Z"))
    return keep_largest(body, "03A_Rear_Perspective_Block")


def rear_archway():
    """03B -- the arch the lane disappears through. Reads as 'it keeps going'."""
    w, h, t = 26.0, 34.0, 5.0
    body = (cq.Workplane("XY").box(w + 12.0, t, h + 8.0, centered=(True, False, False)))
    body = body.cut(aperture(w, h, t, arch=True)
                    .rotate((0, 0, 0), (1, 0, 0), -90).translate((0, t / 2, h / 2 + 1.0)))
    vou = None
    for i in range(9):
        a = math.pi * i / 8
        v = (cq.Workplane("XY").box(4.2, t + 1.0, 5.0, centered=(True, False, True))
             .rotate((0, 0, 0), (0, 1, 0), -math.degrees(a) + 90)
             .translate((math.cos(a) * (w / 2 + 2.4), -0.5,
                         h / 2 + 1.0 + math.sin(a) * (w / 2 + 2.4))))
        vou = v if vou is None else vou.union(v)
    body = body.union(vou)
    return body.union(peg_p1((0.0, 0.0, 2.0), axis="-Y"))


def rear_silhouette():
    """03C -- opaque cut-out of distant roofs and chimneys, lit from behind."""
    w, h, t = 70.0, 78.0, 1.6
    r = rng("skyline")
    pts = [(-w / 2, 0)]
    x = -w / 2
    while x < w / 2:
        step = r.uniform(4.0, 10.0)
        top = r.uniform(h * 0.30, h * 0.62)
        pts += [(x, top), (min(x + step, w / 2), top)]
        x += step
    pts += [(w / 2, 0)]
    body = cq.Workplane("XY").polyline(pts).close().extrude(t)
    # a few chimney stacks poking above the roofline. The base height is READ OFF the
    # profile rather than guessed, or the stack floats above the roof it sits on.
    def roof_at(x):
        best = 0.0
        for (px, pz) in pts:
            if px <= x:
                best = pz
        return best

    for _ in range(5):
        cx = r.uniform(-w / 2 + 6, w / 2 - 6)
        body = body.union(cq.Workplane("XY")
                          .box(r.uniform(3.0, 5.0), r.uniform(4.0, 9.0), t,
                               centered=(True, False, False))
                          .translate((cx, roof_at(cx) - 1.0, 0)))
    # one distant lit window, the deepest point in the scene
    body = body.cut(cq.Workplane("XY").box(3.0, 4.0, t * 3, centered=(True, True, True))
                    .translate((w * 0.18, h * 0.20, t / 2)))
    for sx in (-1, 1):
        body = body.union(peg_p1((sx * (w / 2 - 4.0), 2.0, 0.0), axis="-Z"))
    return keep_largest(body, "03C_Rear_Silhouette")


def rear_glow_frame():
    """03D -- carries the printed sky diffuser and the puck cradle, and sets the two
    air gaps that keep the puck's twelve beads from reading as twelve dots."""
    w, h = 78.0, 86.0
    depth = Y_REARWALL - Y_SKYDIFF + 2.0
    frame = cq.Workplane("XY").box(w, depth, h, centered=(True, False, False))
    frame = frame.cut(cq.Workplane("XY").box(w - 10.0, depth + 2, h - 10.0,
                                             centered=(True, False, False))
                      .translate((0, -1, 5.0)))
    # slot for the diffuser sheet at the front face
    frame = frame.cut(cq.Workplane("XY").box(w - 6.0, P.DIFFUSER_SLOT_T, h - 6.0,
                                             centered=(True, False, False))
                      .translate((0, 0.0, 3.0)))
    # standoffs that set the 6 mm puck gap
    for sx in (-1, 1):
        for sz in (-1, 1):
            frame = frame.union(cq.Workplane("XY")
                                .box(6.0, P.SKY_AIR_GAP_1, 6.0, centered=(True, False, False))
                                .translate((sx * (w / 2 - 8.0), P.DIFFUSER_SLOT_T,
                                            h / 2 + sz * (h / 2 - 8.0))))
    for sx in (-1, 1):
        frame = frame.union(peg_p1((sx * (w / 2 - 5.0), 0.0, 2.0), axis="-Z"))
    return keep_largest(frame, "03D_Rear_Glow_Frame")


def sky_diffuser():
    return diffuser_plate(72.0, 80.0, t=P.SKY_DIFFUSER_T)


def sky_puck_cradle():
    return puck_cradle()


# --------------------------------------------------- 05 ceiling baffle -------
def ceiling_baffle():
    """Occludes the sky, carries the overhead sign rail and a top wire race.
    Slopes down toward the rear so the sky slot narrows with distance."""
    L = P.ALLEY_D
    t = 1.6
    drop = P.CORNICE_DROP
    body = (cq.Workplane("XY")
            .polyline([(-_hw(0) - 2, 0), (_hw(0) + 2, 0), (_hw(L) + 2, L), (-_hw(L) - 2, L)])
            .close().extrude(t))
    # slope: shear the plate downward toward the rear
    body = body.rotate((0, 0, 0), (1, 0, 0), math.degrees(math.atan2(drop, L)))
    cuts, adds = [], []
    # top wire race
    cuts.append(cq.Workplane("XY").box(P.WIRE_CHANNEL_WIDTH, L, P.WIRE_CHANNEL_DEPTH,
                                       centered=(True, False, False))
                .translate((0, 0, t)))
    # sign rail hook sockets across the alley
    import data.facade as FD
    for row in FD.SIGNS:
        if row["kind"] == "banner" and row.get("side"):
            c, a = socket_p1_solids((0.0, row["u"], 0.0), axis="+Z")
            cuts.append(c)
            adds.append(a)
    body = batch_cut(body, cuts)
    body = batch_add(body, adds)
    for sx in (-1, 1):
        for y in (L * 0.15, L * 0.85):
            body = body.union(peg_p1((sx * (_hw(y) - 3.0), y, t), axis="+Z"))
    return keep_largest(body, "05_Ceiling_Baffle")


# ----------------------------------------------- 08 front arch header --------
def front_arch_header():
    w = W_CH - 2 * 6.0
    body = cq.Workplane("XY").box(w, 6.0, 22.0, centered=(True, False, False))
    br = brick_field(w, 22.0, "header", scale_fn=lambda u: 1.0)
    if br is not None:
        # +90 about X sends the brick field's height to +Z and its relief depth to -Y,
        # which is out of the front face. -90 sends the height to -Z, i.e. underneath.
        body = body.union(br.rotate((0, 0, 0), (1, 0, 0), 90).translate((-w / 2, 0, 0)))
    for sx in (-1, 1):
        body = body.union(peg_p2((sx * (w / 2 - 8.0), 6.0, 11.0), axis="+Y", rot=90))
    return keep_largest(body, "08_Front_Arch_Header")


# ------------------------------------------------ 09 chassis rear wall -------
def chassis_rear_wall():
    t = 2.5
    body = cq.Workplane("XY").box(W_CH - 2 * WA, t, P.SCENE_H * 0.9,
                                  centered=(True, False, False))
    # main grommet through to the switch module and the drawer
    body = body.cut(cq.Workplane("XY").cylinder(t * 4, 3.2)
                    .rotate((0, 0, 0), (1, 0, 0), 90).translate((0, t / 2, 12.0)))
    for sx in (-1, 1):
        body = body.union(peg_p1((sx * ((W_CH - 2 * WA) / 2 - 5.0), 0.0, 6.0), axis="-Y"))
    return keep_largest(body, "09_Chassis_Rear_Wall")
