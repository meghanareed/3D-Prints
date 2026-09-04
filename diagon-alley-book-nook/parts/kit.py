"""Signs, brackets, lanterns, props, lighting hardware and build jigs -- plus the
wall and floor sockets they need.

These come from the same tables as the facade, so a sign and its socket can never
disagree about where it lives.
"""
import math
import cadquery as cq
import params as P
import data.facade as F
from lib import sign as S
from lib import prop as PR
from lib.light import baffle_cap, coil_bay_cover, diffuser_plate, puck_cradle
from lib.mount import (peg_p1, socket_p1_solids, socket_p2_solids, tolerance_coupon,
                       joint_coupon, joint_coupon_pieces, c4_clip, P1_L, P2_L)
from lib.util import keep_largest, compound
from parts.decor import to_wall, FACE


# ------------------------------------------------------------------ signs ----
def _sign_part(row):
    k, w, h, txt = row["kind"], row["w"], row["h"], row.get("text", "")
    s = F.wpersp(row["u"]) if row.get("side") else 1.0
    w, h = w * s, h * s
    if k == "banner":
        return S.plate_vertical_banner(w, h, txt)
    if k == "swing":
        return S.plate_swing(w, h, txt)
    if k == "shield":
        return S.plate_shield(w, h, txt)
    if k == "lozenge":
        return S.plate_lozenge(w, h, txt)
    if k == "arrow":
        return S.plate_arrow(w, h, txt)
    if k == "fasciaplate":
        body = cq.Workplane("XY").box(w, h, S.PLATE_T, centered=(True, True, False))
        body = S._text_on(body, txt, w * 0.94, h, top_z=S.PLATE_T)
        for sx in (-1, 1):
            body = body.union(peg_p1((sx * (w / 2 - 6.0), 0.0, 0.0), axis="-Z"))
        return body
    raise KeyError(k)


def _bracket_solid(row):
    s = F.wpersp(row["u"])
    return S.bracket_scroll(row["reach"] * s, row["drop"] * s)


# Signs and their brackets are NOT fused, and the reason is measured rather than
# assumed. A hanging sign's plate lies parallel to the wall; its bracket is a fin
# standing perpendicular to it. Fused, the pair is a T in three dimensions with no flat
# lie anywhere: the best of the 24 axis-aligned orientations puts 30B on 40.4 mm^2 of
# bed under 88.4 mm^2 of overhang, and 30D on 6.7 mm^2. Separately, both parts lie flat.
#
# Fusing them would need the sign hung in the bracket's PLANE -- perpendicular to the
# wall, which is how a real hanging shop sign works and how they read down an alley --
# and that moves the sign 26 mm out into the alley, which is a design decision and an
# envelope question, not a print setting.


def signs():
    out = []
    for row in F.SIGNS:
        out.append(dict(id=row["id"], name=row["name"],
                        solid=keep_largest(_sign_part(row), row["id"]),
                        side=row.get("side"), u=row["u"], z=row["z"]))
    return out


def brackets():
    out = []
    for row in F.BRACKETS:
        out.append(dict(id=row["id"], name=row["name"],
                        solid=_bracket_solid(row),
                        side=row["side"], u=row["u"], z=row["z"]))
    out.append(dict(id="32A", name="Sign_Hanging_Chain_A", solid=S.chain(4),
                    side=None, u=0, z=0))
    out.append(dict(id="32B", name="Sign_Hanging_Chain_B", solid=S.chain(3),
                    side=None, u=0, z=0))
    out.append(dict(id="32C", name="Sign_Rail_Hook", solid=S.rail_hook(),
                    side=None, u=0, z=0))
    return out


def lanterns():
    out = []
    for row in F.LANTERNS:
        s = F.wpersp(row["u"])
        out.append(dict(id=row["id"], name=row["name"],
                        solid=PR.lantern(row["h"] * s, row["w"] * s),
                        side=row["side"], u=row["u"], z=row["z"]))
    return out


def props():
    made = []
    for row in F.PROPS:
        k = row["kind"]
        if k == "barrel":
            sol = PR.barrel(row["d"], row["h"])
        elif k == "crate":
            sol = PR.crate(row["w"], row["d"], row["h"])
        elif k == "crate_stack":
            sol = PR.crate_stack()
        elif k == "cauldrons":
            sol = PR.cauldron_stack()
        elif k == "brooms":
            sol = PR.broom_rack()
        elif k == "postbox":
            sol = PR.post_box()
        elif k == "notice":
            sol = PR.notice_board()
        elif k == "posters":
            sol = PR.poster_layer()
        elif k == "kerb":
            sol = PR.kerb_step()
        elif k == "hatch":
            sol = PR.cellar_hatch()
        elif k == "scraper":
            sol = PR.boot_scraper()
        else:
            raise KeyError(k)
        made.append(dict(id=row["id"], name=row["name"], solid=sol,
                         side=row.get("side"), u=row["u"], z=row.get("z", 0)))
    return made


# ------------------------------------- sockets these parts need in the wall --
def wall_mount_rows(side):
    """Everything that hangs off this wall, as (kind, row, rotation).

    One list, so the wall builder and verify.py cannot disagree about which sockets
    exist or which part owns each one. Rebuilding the same loop in two places is how
    a whole family of mounts went unchecked: verify had no way to name them.
    """
    out = []
    for row in F.SIGNS:
        if row.get("side") == side and row["kind"] != "banner":
            out.append(("sign", row, 0.0))
    for row in F.BRACKETS:
        if row["side"] == side:
            out.append(("bracket", row, 90.0))
    for row in F.LANTERNS:
        if row["side"] == side:
            out.append(("lantern", row, 90.0))
    for row in F.PROPS:
        if row.get("side") == side and row["kind"] in ("notice", "posters", "scraper"):
            out.append(("prop", row, 0.0))
    return out


def wall_mount_cuts(side):
    """Sockets for signs, brackets, lanterns and the wall-hung notice board.

    Returned as (cuts, adds) so the wall builder can fold them into its two booleans.
    Depth is clamped to the plate thickness: a socket deeper than the material would
    leave its crush ribs floating in the service gap.
    """
    cuts, adds = [], []
    for _kind, row, rot in wall_mount_rows(side):
        c, a = socket_p1_solids((0.0, 0.0, 0.0), axis="-Z", rot=rot, depth=FACE)
        cuts.append(to_wall(c, row["u"], row.get("z", 20.0)))
        adds.append(to_wall(a, row["u"], row.get("z", 20.0)))
    return cuts, adds


def sign_beads(side):
    """Backlit signs put a bead in the wall behind them."""
    return [(r["u"], r["z"]) for r in F.SIGNS
            if r.get("side") == side and r.get("lit")]


def lantern_beads(side):
    return [(r["u"], r["z"]) for r in F.LANTERNS
            if r["side"] == side and r.get("lit")]


# ------------------------------------------------------ lighting hardware ----
BAFFLE_SIZES = [("40A", 12.0, 14.0, 6.0), ("40B", 14.0, 16.0, 6.0),
                ("40C", 10.0, 12.0, 5.0), ("40D", 16.0, 18.0, 7.0),
                ("40E", 9.0, 10.0, 5.0), ("40F", 18.0, 20.0, 7.0)]


def lighting_hardware():
    out = []
    for pid, w, h, d in BAFFLE_SIZES:
        out.append(dict(id=pid, name=f"Light_Baffle_{pid[-1]}",
                        solid=baffle_cap(w, h, d)))
    for i in range(3):
        out.append(dict(id=f"45{chr(65+i)}", name=f"Coil_Bay_Cover_{chr(65+i)}",
                        solid=coil_bay_cover()))
    out.append(dict(id="43", name="Bus_Cover", solid=_bus_cover()))
    out.append(dict(id="44", name="Wire_Clip_x12", solid=_wire_clip_sprue(12)))
    out.append(dict(id="46", name="Bead_Shim_x8", solid=_bead_shim_sprue(8)))
    out.append(dict(id="47", name="String_Entry_Grommet_x4", solid=_grommet_sprue(4)))
    return out


def _bus_cover():
    body = cq.Workplane("XY").box(P.CHASSIS_W - 14.0, P.BUS_CHANNEL_WIDTH + 5.0, 1.4,
                                  centered=(True, True, False))
    for sx in (-1, 1):
        body = body.union(peg_p1((sx * (P.CHASSIS_W / 2 - 14.0), 0.0, 0.0), axis="-Z"))
    return body


def _wire_clip_sprue(n):
    """One clip: a C-section that snaps over a 3 mm channel and traps the wire."""
    clip = (cq.Workplane("XY")
            .box(P.WIRE_CHANNEL_WIDTH + 2.4, 4.0, 1.2, centered=(True, True, False)))
    for sx in (-1, 1):
        clip = clip.union(cq.Workplane("XY")
                          .box(1.2, 4.0, P.WIRE_CHANNEL_DEPTH - 0.4,
                               centered=(True, True, False))
                          .translate((sx * (P.WIRE_CHANNEL_WIDTH / 2 + 0.6), 0, -
                                      (P.WIRE_CHANNEL_DEPTH - 0.4))))
    return _sprue([clip] * n, pitch=8.0)


def _bead_shim_sprue(n):
    shim = cq.Workplane("XY").box(P.BEAD_POCKET_W - 0.4, P.BEAD_POCKET_H - 0.4, 0.5,
                                  centered=(True, True, False))
    return _sprue([shim] * n, pitch=7.0)


def _grommet_sprue(n):
    g = (cq.Workplane("XY").cylinder(3.0, 3.0, centered=(True, True, False))
         .cut(cq.Workplane("XY").cylinder(9.0, 1.9))
         .union(cq.Workplane("XY").cylinder(1.0, 4.2, centered=(True, True, False))))
    return _sprue([g] * n, pitch=10.0)


def _sprue(items, pitch=8.0, bar=1.6):
    """Small parts on a runner, so a dozen 2 mm clips are one object on the plate."""
    n = len(items)
    body = cq.Workplane("XY").box(pitch * n, bar, 1.0, centered=(True, True, False)) \
        .translate((0, -6.0, 0))
    for i, it in enumerate(items):
        x = -pitch * n / 2 + pitch * (i + 0.5)
        body = body.union(it.translate((x, 0, 0)))
        body = body.union(cq.Workplane("XY").box(1.2, 6.0, 1.0, centered=(True, False, False))
                          .translate((x, -6.0, 0)))
    return body


# ------------------------------------------------------------------- jigs ----
def jigs():
    coupon, pegs = tolerance_coupon()
    out = [dict(id="70A", name="Tolerance_Test_Coupon", solid=coupon),
           dict(id="70B", name="Tolerance_Test_Pegs", solid=pegs),
           dict(id="74A", name="Joint_Test_Block", solid=joint_coupon()),
           dict(id="74B", name="Joint_Test_Pieces", solid=joint_coupon_pieces()),
           dict(id="72", name="Paint_Handle_Sprue", solid=_paint_handles(8)),
           dict(id="73", name="Assembly_ID_Card", solid=_id_card())]
    for i, sheet in enumerate(_glazing_templates()):
        out.append(dict(id=f"71{chr(65+i)}", name=f"Glazing_Cut_Template_{chr(65+i)}",
                        solid=sheet))
    return out


def _paint_handles(n=8):
    """Handles that RECEIVE a decorative part's peg, so small parts can be primed and
    painted without being held by the surface you are painting.

    The socket is deliberately loose -- DECORATIVE_CLEARANCE + 0.12, and no crush ribs
    -- so a painted part lifts off without stressing the finish. Half the sprue takes
    P1 parts (signs, props, brackets, pipes, ornaments) and half takes the keyed P2
    pairs used by window frames, doors, stallrisers and fascias.

    The first version had a PEG on top, which is useless: the parts have pegs too, and
    two pegs do not mate.
    """
    real = P.DECORATIVE_CLEARANCE
    items = []
    try:
        P.DECORATIVE_CLEARANCE = real + 0.12
        for kind in ("p1", "p2"):
            body = (cq.Workplane("XY").box(13.0, 11.0, 3.0, centered=(True, True, False))
                    .union(cq.Workplane("XY")
                           .cylinder(15.0, 3.4, centered=(True, True, False))
                           .translate((0, 0, 3.0))))
            body = body.union(cq.Workplane("XY")
                              .box(13.0, 11.0, 3.5, centered=(True, True, False))
                              .translate((0, 0, 18.0)))
            top = 21.5
            # the mount type it takes, on the side of the pad -- with eight identical
            # sticks on a runner there is otherwise no way to tell P1 from P2
            try:
                body = body.union(
                    cq.Workplane("XZ", origin=(0, -5.5, 19.7))
                    .text(kind.upper(), 2.6, 1.0, font="DejaVu Sans", kind="bold"))
            except Exception:
                pass
            if kind == "p1":
                cut, _ = socket_p1_solids((0.0, 0.0, top), axis="-Z", depth=P1_L + 0.4)
            else:
                cut, _ = socket_p2_solids((0.0, 0.0, top), axis="-Z", depth=P2_L + 0.4)
            body = body.cut(cut)
            items += [body] * (n // 2)
    finally:
        P.DECORATIVE_CLEARANCE = real
    return _sprue(items, pitch=15.0)


def _label(plate, txt, size, centre):
    """Sink a label into the top face at a given offset from its centre.

    lib.util.engrave_id only writes at the middle of a face, which is no use on a sheet
    carrying twenty-five of them.
    """
    try:
        return (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                .center(*centre)
                .text(txt, size, -0.4, font="DejaVu Sans", kind="bold", combine="cut"))
    except Exception:
        return plate


GLAZING_SHEET_T = 1.6           # template thickness -- stiff enough to hold a knife
GLAZING_LABEL_H = 5.0           # strip under each opening for its part id
GLAZING_GAP = 4.0               # between openings
GLAZING_MARGIN = 5.0            # round the outside of the sheet


def glazing_panes():
    """Every window pane in the kit, as (id, outline prism), largest first.

    The outline is taken from the pane SOLID rather than from its w and h, so an arched
    window gives an arched opening and the template can never disagree with the part it
    is a template for. The four templates this replaces were 26x34, 34x32, 24x26 and
    20x40 -- four guesses for 25 panes, none of which is any of those sizes.
    """
    from parts import walls as WL
    out = []
    for side in ("L", "R"):
        for p in WL.collect(side)[0]:
            if "Glazing" not in p["name"]:
                continue
            prism = (cq.Workplane(obj=p["solid"].val())
                     .faces("<Z").wires().toPending()
                     .extrude(GLAZING_SHEET_T + 4.0))
            out.append((p["id"], prism))
    return sorted(out, key=lambda t: -_area(t[1]))


def _area(prism):
    b = prism.val().BoundingBox()
    return b.xlen * b.ylen


def _glazing_templates(bed=None):
    """Sheets of pane outlines to lay on acetate and cut round.

    The rebate behind every frame is DIFFUSER_SLOT_T deep and takes vellum, acetate, PET
    or 1 mm acrylic as readily as it takes a printed pane -- cut sheet is a designed-in
    option, not a substitute. Cutting them takes 25 parts off the facade plates, and a
    pane cut from acetate reads as glass where 0.8 mm of clear PLA reads as fog.
    """
    # Leave room for the brim it will need: a 1.6 mm sheet this size curls.
    bed = bed or (P.BED_X - 2 * GLAZING_MARGIN - 26.0)
    panes = glazing_panes()
    sheets, row, rows, x, row_h = [], [], [], 0.0, 0.0

    def flush_row():
        nonlocal row, x, row_h
        if row:
            rows.append((row, row_h))
        row, x, row_h = [], 0.0, 0.0

    for pid, prism in panes:
        b = prism.val().BoundingBox()
        w, h = b.xlen + GLAZING_GAP, b.ylen + GLAZING_LABEL_H + GLAZING_GAP
        if x + w > bed:
            flush_row()
        row.append((pid, prism, x, w, h))
        x += w
        row_h = max(row_h, h)
    flush_row()

    y, total_w, placed = 0.0, 0.0, []
    for r, h in rows:
        for pid, prism, x, w, _h in r:
            placed.append((pid, prism, x, y))
            total_w = max(total_w, x + w)
        y += h
    sheet_w = total_w + 2 * GLAZING_MARGIN - GLAZING_GAP
    sheet_h = y + 2 * GLAZING_MARGIN - GLAZING_GAP

    plate = cq.Workplane("XY").box(sheet_w, sheet_h, GLAZING_SHEET_T,
                                   centered=(False, False, False))
    for pid, prism, px, py in placed:
        b = prism.val().BoundingBox()
        dx = GLAZING_MARGIN + px - b.xmin
        dy = GLAZING_MARGIN + py + GLAZING_LABEL_H - b.ymin
        plate = plate.cut(prism.translate((dx, dy, -2.0)))
        plate = _label(plate, pid, 3.2,
                       (dx + (b.xmin + b.xmax) / 2 - sheet_w / 2,
                        GLAZING_MARGIN + py + GLAZING_LABEL_H / 2 - sheet_h / 2))
    return [plate]


def _id_card():
    card = cq.Workplane("XY").box(90.0, 55.0, 1.6, centered=(True, True, False))
    lines = [("CROOKED LANE", 7.0, 18.0), ("BOOK NOOK", 6.0, 6.0),
             (f"fit {P.FIT_CLEARANCE:.2f} / dec {P.DECORATIVE_CLEARANCE:.2f}", 4.0, -8.0),
             (f"seed {P.RANDOM_SEED}", 3.4, -18.0)]
    for txt, sz, y in lines:
        try:
            card = (cq.Workplane("XY", origin=(0, y, 1.4))
                    .text(txt, sz, 0.7, font=P.TEXT_FONT, kind="bold").union(card))
        except Exception:
            pass
    return card
