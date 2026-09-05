"""Hanging signs, brackets and chain.

Signs are the strongest depth cue in the alley, so they get their own mounting rail
and are all separate parts with replaceable text plates.
"""
import math
import cadquery as cq
import params as P
from lib.mount import peg_p1, socket_p1, socket_p1_solids, tenon_t5, T5_W
from lib.util import try_fillet, emboss_text

# 2.4, not 1.8. A sign is located by a loose pin into a socket in its back, and a
# 1.8 mm plate leaves only 1.2 mm of bore before the floor -- too little for one pin
# length to serve both the wall (2.5 mm bore) and a fascia board (1.6 mm). At 2.4 the
# plate takes a 1.6 mm bore, one 3.2 mm pin fits every joint, and the plate is stiffer.
PLATE_T = 2.4

# A hanging sign hangs on something. Both halves of that joint used to be CLOSED rings
# -- a 1.6 mm eye on the sign, a 1.7 mm eye on the bracket tip -- with a printed chain
# between them whose end links were closed too. Three closed loops cannot be threaded
# together after printing, so 30B, 30C and 30H had no way to attach to anything at all.
# The eyes are wider now and an open hook (s_hook, part 32E) springs into both.
EYE_HOLE = 2.4          # both eyes, so one hook size fits every hanging sign
EYE_WALL = 1.1          # ring material around the hole
HOOK_WIRE = 1.4         # section of the open hook: passes a 2.4 eye with 1.0 to spare


def _fit_size(txt, w, h):
    """Pick a size that actually fits the plate -- by MEASURING the text, not guessing.

    This used to assume 0.62 em of advance per character. All-caps bold serif is nearer
    0.72, so every name ran wide: POTIONS and APOTHECARY both came off the plate, which
    is how a letter ends up a detached solid.
    """
    if not txt:
        return 0.0
    try:
        probe = (cq.Workplane("XY")
                 .text(txt, 10.0, 1.0, font=P.TEXT_FONT, kind="bold", combine=False))
        b = probe.val().BoundingBox()
        by_w = 10.0 * (w * 0.92) / b.xlen if b.xlen else h * 0.62
        by_h = 10.0 * (h * 0.80) / b.ylen if b.ylen else h * 0.62
    except Exception:
        by_w = (w * 0.92) / (0.72 * len(txt))
        by_h = h * 0.62
    return max(1.6, min(by_w, by_h))


def _text_on(body, txt, w, h, vertical=False, size=None, top_z=None):
    """Emboss text on the plate's top face.

    top_z is passed explicitly rather than re-selecting faces(">Z") each time: once one
    glyph stands proud, ">Z" selects THAT glyph's top and the next line lands on it.
    """
    if not (P.RENDER_TEXT and txt):
        return body
    if top_z is None:
        top_z = body.val().BoundingBox().zmax
    try:
        if vertical:
            n = len(txt)
            cell = h / (n + 0.4)
            gsz = max(1.6, min(w * 0.62, cell * 0.82))
            for i, ch in enumerate(txt):
                if ch == " ":
                    continue
                zc = h / 2 - (i + 0.7) * cell
                body = (cq.Workplane("XY", origin=(0, zc, top_z - 0.5))
                        .text(ch, gsz, P.TEXT_DEPTH + 0.5, font=P.TEXT_FONT,
                              kind="bold")
                        .union(body))
            return body
        sz = size or _fit_size(txt, w, h)
        # sunk 0.5 into the plate: text sitting exactly on the surface is tangent,
        # and every letter comes out as its own solid
        return (cq.Workplane("XY", origin=(0, 0, top_z - 0.5))
                .text(txt, sz, P.TEXT_DEPTH + 0.5, font=P.TEXT_FONT, kind="bold")
                .union(body))
    except Exception:
        return body


BACK_BORE = 1.6      # bore into a 2.4 mm plate, leaving a 0.8 mm floor
NAMEPLATE_PITCH = 20.0   # pin spacing shared by a fascia board and its name plate


def _back_socket(body, x=0.0, y=0.0, depth=BACK_BORE):
    """Locating socket in the plate's BACK, for a loose pin.

    Signs used to carry a peg here, and a peg on the back is what forced the plate onto
    the bed face-down -- print_rot ("X", 180), "face down, pegs up" -- with every raised
    letter crushed into the plate and elephant-footed. A socket does the same locating
    job and lets the plate lie back-down with its lettering standing up in clean air.

    Built along +Z, the direction the pin travels as it enters from the back, so the
    lead-in lands on the back face where the pin meets it. rot=180 because the pin is
    the peg this plate used to carry: that peg was placed axis="-Z", which turns the
    D-flat to -Y, and a bore built the other way up puts its flat at +Y and jams on the
    key. verify.check_pin_joints() assembles the real pair and measures it.
    """
    cut, _ = socket_p1_solids((x, y, 0.0), axis="+Z", rot=180.0, depth=depth,
                              decorative=True)
    return body.cut(cut)


def plate_rect(w, h, txt="", t=PLATE_T, bevel=True):
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    if bevel:
        body = try_fillet(body, "|Z", 1.0)
        body = body.union(cq.Workplane("XY").box(w, h, 0.6, centered=(True, True, False))
                          .translate((0, 0, t)).faces(">Z").shell(-0.0)
                          if False else cq.Workplane("XY").box(0.001, 0.001, 0.001))
    return _text_on(body, txt, w, h)


def plate_vertical_banner(w, h, txt="", t=PLATE_T):
    """The tall hanging banner -- backlit, so it also carries a bead pocket recess."""
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    body = body.union(cq.Workplane("XY").box(w + 3.0, 3.0, t + 1.2,
                                             centered=(True, True, False))
                      .translate((0, h / 2 - 1.5, 0)))
    body = body.union(cq.Workplane("XY").box(w + 3.0, 3.0, t + 1.2,
                                             centered=(True, True, False))
                      .translate((0, -h / 2 + 1.5, 0)))
    body = _text_on(body, txt, w, h, vertical=True, top_z=t)
    return _back_socket(body, 0.0, h / 2 - 1.5)


def plate_shield(w, h, txt="", t=PLATE_T):
    """Heraldic shield -- a shape the eye reads instantly as a shop badge."""
    body = (cq.Workplane("XY")
            .moveTo(-w / 2, h / 2).lineTo(w / 2, h / 2).lineTo(w / 2, -h * 0.12)
            .threePointArc((0, -h / 2), (-w / 2, -h * 0.12)).close().extrude(t))
    body = body.union(cq.Workplane("XY").box(w + 2.0, 2.4, t + 1.0,
                                             centered=(True, True, False))
                      .translate((0, h / 2 - 1.2, 0)))
    body = _text_on(body, txt, w, h * 0.7, top_z=t)
    return _back_socket(body)


def plate_lozenge(w, h, txt="", t=PLATE_T):
    """Stacked lozenge plates -- STYLE / VALUE / EASE / VARIETY style column."""
    k = h * 0.28
    body = (cq.Workplane("XY")
            .polyline([(-w / 2, 0), (-w / 2 + k, h / 2), (w / 2 - k, h / 2),
                       (w / 2, 0), (w / 2 - k, -h / 2), (-w / 2 + k, -h / 2)])
            .close().extrude(t))
    body = _text_on(body, txt, w * 0.8, h, top_z=t)
    return _back_socket(body)


def plate_arrow(w, h, txt="", t=PLATE_T):
    body = (cq.Workplane("XY")
            .polyline([(-w / 2, h / 2), (w / 2 - h * 0.5, h / 2), (w / 2, 0),
                       (w / 2 - h * 0.5, -h / 2), (-w / 2, -h / 2)])
            .close().extrude(t))
    body = _text_on(body, txt, w * 0.72, h, top_z=t)
    return _back_socket(body, -w * 0.3, 0.0)


def plate_swing(w, h, txt="", t=PLATE_T, eyes=True):
    """Projecting swing sign.

    `eyes` are for a plate that hangs on hooks. A plate fused into its bracket's plane
    is carried by the arm above it and hangs from nothing, so eyes on it are 4 mm of
    dead height on a part fighting for a 15 mm band of bare wall.
    """
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    body = try_fillet(body, "|Z", 1.2)
    r_in = EYE_HOLE / 2
    for s in (-1, 1) if eyes else ():
        eye = (cq.Workplane("XY").circle(r_in + EYE_WALL).extrude(t)
               .cut(cq.Workplane("XY").circle(r_in).extrude(t))
               .translate((s * (w / 2 - 3.4), h / 2 + r_in + EYE_WALL - 0.6, 0)))
        body = body.union(eye)
    return _text_on(body, txt, w * 0.86, h, top_z=t)


# THE PART FRAME, as lib/window.py documents it: +X across the wall's depth, +Y up the
# wall, +Z out of the wall into the alley, and pegs pointing -Z. to_wall() assumes it.
#
# The brackets below are DRAWN in a different frame, because drawing a scroll in XZ is
# how you get it to print flat with the layer lines running along the arm. That is a
# good reason to draw them that way and no reason at all to hand them to to_wall() like
# that: the arm came out running along the wall's depth instead of projecting from it,
# and the whole part landed 12 mm outboard of the base pan -- the rest of the 21 mm the
# chassis overhung its own case. So they are rotated into the convention on the way
# out. It is the same mistake the bay-window grooves made, and it looks right in CAD
# both times.
def _to_part_frame(body):
    """Drawing frame (arm +X, post +Z, width -Y) -> part frame (arm +Z, post +Y)."""
    return body.rotate((0, 0, 0), (1, 1, 1), -120)


def bracket_pegs(drop, arm_t=2.4):
    """Where a bracket's wall pegs sit, in the DRAWING frame (z along the post).

    Two, not one. A bracket carrying a sign that projects into the alley is a
    cantilever, and one peg is a hinge -- the sign would swing down and stay there.
    Spaced as widely as the post allows, and never closer than a socket is wide.
    """
    post_h = drop + POST_RISE
    sp = max(5.0, min(9.0, post_h - 4.4))
    zc = (POST_RISE - drop) / 2.0
    return [zc - sp / 2, zc + sp / 2]


POST_RISE = 1.0     # how far the post stands above the arm
BRACKET_W = 2.6     # ironwork thickness, the same at every depth


def _scroll_body(reach, drop, t, w):
    """The ironwork, in the drawing frame: arm +X, post +Z, width -Y."""
    arm = (cq.Workplane("XZ")
           .moveTo(0, 0).lineTo(reach, 0).lineTo(reach, -t).lineTo(0, -t)
           .close().extrude(-w))
    post = (cq.Workplane("XZ")
            .moveTo(0, -drop).lineTo(t, -drop).lineTo(t, POST_RISE)
            .lineTo(0, POST_RISE).close().extrude(-w))
    body = arm.union(post)
    stay = (cq.Workplane("XZ")
            .moveTo(t, -drop * 0.85).lineTo(reach * 0.86, -t)
            .lineTo(reach * 0.86, -t - 2.0).lineTo(t + 2.2, -drop * 0.85)
            .close().extrude(-w))
    body = body.union(stay)
    # The curl is a ring of wall 1.1 mm thick, and a shallow bracket at the back of the
    # alley has no room for one: at drop 6 scaled to 0.6 the inner radius goes negative
    # and OCCT refuses the circle. Below that it is simply left off.
    r_out = drop * 0.20
    if r_out - 1.1 > 0.4:
        curl = (cq.Workplane("XZ").center(reach * 0.5, -drop * 0.42).circle(r_out)
                .extrude(-w).cut(cq.Workplane("XZ")
                                 .center(reach * 0.5, -drop * 0.42)
                                 .circle(r_out - 1.1).extrude(-w)))
        body = body.union(curl)
    return body


def _wall_pegs(body, drop, w, t=2.4):
    """Flat tenons in the bracket's own plane, in the drawing frame.

    These used to be round pegs, and a round peg here cannot print. The bracket lies in
    a plane containing the wall's normal, so anything reaching the wall runs along that
    plane: printed flat, the peg was a 2.4 mm cylinder floating at mid-thickness with
    air under it, cantilevered off the edge of the part. The post is 2.6 mm thick, so
    there is no room to bore a socket there either.

    A tenon is the same material at the same height -- a flat extension of the post,
    no overhang anywhere -- and the wall takes a mortise. lib.mount.tenon_t5.

    +w/2, not -w/2: the body extrudes to y = -w, but _to_part_frame's rotation lands
    drawing +y on the same side of the part as the body. At -w/2 they come out 3.2 mm
    clear of it as loose solids, which is how 31B shipped as two pieces.
    """
    for zp in bracket_pegs(drop, t):
        body = body.union(tenon_t5((0.0, w / 2, zp), axis="-X", h=w))
    return body


def bracket_scroll(reach=14.0, drop=16.0, t=2.4, w=BRACKET_W):
    """Wrought-iron scroll bracket, no sign on it. Drawn in XZ and extruded so it
    prints flat with the scroll lying on the bed -- no supports, and the layer lines
    run along the arm."""
    body = _scroll_body(reach, drop, t, w)
    # tip eye, kept for a bracket that carries nothing but looks like it once did
    # 0.6 up into the arm. Sized to sit exactly under it the ring is TANGENT, and a
    # tangent solid is a separate solid: widening the eye to 2.4 mm quietly turned the
    # bracket into three pieces.
    r_in = EYE_HOLE / 2
    ez = -t - r_in - EYE_WALL + 0.6
    body = body.union(cq.Workplane("XZ").center(reach - 1.5, ez)
                      .circle(r_in + EYE_WALL).extrude(-w)
                      .cut(cq.Workplane("XZ").center(reach - 1.5, ez)
                           .circle(r_in).extrude(-w)))
    return _to_part_frame(_wall_pegs(body, drop, w, t))


def swing_assembly(reach, drop, plate_w, plate_h, txt, t=PLATE_T, arm_t=2.4,
                   w=BRACKET_W):
    """A hanging shop sign and its bracket as ONE part, in the bracket's PLANE.

    This is the shape a book nook needs. A sign built parallel to the wall shows the
    viewer its edge: you look down the alley from the front, so a plate flat on a side
    wall is raked away to nothing and no lettering on it can be read. Turned into the
    bracket's plane it faces the opening squarely, which is also how a real hanging
    shop sign works and why they read down a street.

    It is also the only orientation in which the pair prints flat. kit.py used to carry
    a note that fusing them made "a T in three dimensions with no flat lie anywhere" --
    true while the plate stayed parallel to the wall, and untrue the moment it turns:
    coplanar with the arm, the whole assembly lies on the bed in one piece with its
    lettering up, no chain, no hook and no eye doing any work.
    """
    body = _scroll_body(reach, drop, arm_t, w)
    plate = plate_swing(plate_w, plate_h, txt, t, eyes=False)   # lettering on +Z
    # into the bracket's plane: the plate's face turns to -Y, which is the face the
    # alley sees, and its width runs out along the arm
    plate = plate.rotate((0, 0, 0), (1, 0, 0), -90)
    plate = plate.translate((reach / 2.0, -w / 2 + t / 2, -arm_t - plate_h / 2 - 0.4))
    # a short hanger each side, so the plate is carried by the arm and not floating
    for sx in (-1, 1):
        x = reach / 2.0 + sx * (plate_w / 2 - 3.4)
        body = body.union(cq.Workplane("XZ").center(x, -arm_t - 0.3).rect(1.8, 1.8)
                          .extrude(-w))
    body = body.union(plate)
    return _to_part_frame(_wall_pegs(body, drop, w, arm_t))


def bracket_straight(reach=10.0, t=2.2, w=2.4):
    body = (cq.Workplane("XZ").moveTo(0, 0).lineTo(reach, 0)
            .lineTo(reach, -t).lineTo(0, -t).close().extrude(-w))
    body = body.union(cq.Workplane("XZ").moveTo(0, -reach * 0.8).lineTo(t, -reach * 0.8)
                      .lineTo(reach * 0.8, -t).lineTo(reach * 0.8 - t, -t)
                      .close().extrude(-w))
    body = body.union(peg_p1((0.0, w / 2, -reach * 0.4), axis="-X"))
    return _to_part_frame(body)


def chain(links=4, link_l=5.0, link_w=3.0, wire=0.9):
    """Printed chain: alternating links laid flat, printed as one piece in place.
    Kept deliberately chunky -- a scale-accurate chain would be unprintable."""
    body = None
    for i in range(links):
        outer = (cq.Workplane("XY").ellipse(link_l / 2, link_w / 2).extrude(wire)
                 .cut(cq.Workplane("XY")
                      .ellipse(link_l / 2 - wire, link_w / 2 - wire).extrude(wire)))
        lk = outer.translate((0, i * (link_l - link_w * 0.6), (i % 2) * wire * 0.9))
        if i % 2:
            lk = lk.rotate((0, i * (link_l - link_w * 0.6), 0),
                           (0, i * (link_l - link_w * 0.6), 1), 90)
        body = lk if body is None else body.union(lk)
    return body


def s_hook(gap=2.0, wire=HOOK_WIRE, mean_r=2.7):
    """An OPEN ring, so it can be sprung into two closed eyes after printing.

    This is the part that was missing. It prints lying flat -- a split washer, one
    extrusion tall at the thinnest -- and it is the only piece in the kit meant to be
    elastic, so it wants to come off the plate with the layer lines running round it.
    """
    ring = (cq.Workplane("XY").circle(mean_r + wire / 2).extrude(wire)
            .cut(cq.Workplane("XY").circle(mean_r - wire / 2).extrude(wire)))
    mouth = (cq.Workplane("XY").box(mean_r * 2 + wire * 2, gap, wire,
                                    centered=(False, True, False))
             .translate((0, 0, 0)))
    return ring.cut(mouth)


def hook_sprue(n=8, pitch=8.0):
    """n hooks on a runner. They are 6 mm across and would otherwise be lost."""
    out = None
    for i in range(n):
        h = s_hook().translate((0, pitch * i, 0))
        out = h if out is None else out.union(h)
    bar = (cq.Workplane("XY").box(1.2, pitch * (n - 1) + 6.0, 0.9,
                                  centered=(True, True, False))
           .translate((-2.7 - HOOK_WIRE / 2 + 0.4, pitch * (n - 1) / 2, 0)))
    return out.union(bar)


def rail_hook(h=6.0, t=2.0, w=4.0):
    """Overhead rail hook on the ceiling baffle: signs hang across the alley from it."""
    body = (cq.Workplane("XZ").moveTo(0, 0).lineTo(t, 0).lineTo(t, -h)
            .lineTo(t + 2.2, -h).lineTo(t + 2.2, -h - t).lineTo(0, -h - t)
            .close().extrude(-w))
    return body.union(peg_p1((0.0, w / 2, 0.0), axis="+Z"))
