"""Hanging signs, brackets and chain.

Signs are the strongest depth cue in the alley, so they get their own mounting rail
and are all separate parts with replaceable text plates.
"""
import math
import cadquery as cq
import params as P
from lib.mount import peg_p1, socket_p1, socket_p1_solids
from lib.util import try_fillet, emboss_text

# 2.4, not 1.8. A sign is located by a loose pin into a socket in its back, and a
# 1.8 mm plate leaves only 1.2 mm of bore before the floor -- too little for one pin
# length to serve both the wall (2.5 mm bore) and a fascia board (1.6 mm). At 2.4 the
# plate takes a 1.6 mm bore, one 3.2 mm pin fits every joint, and the plate is stiffer.
PLATE_T = 2.4


def _fit_size(txt, w, h):
    """Pick a size that actually fits the plate. Letters that overhang the plate edge
    become detached solids, which is what happened to the long fascia names."""
    if not txt:
        return 0.0
    per_char = 0.62                     # rough advance width of DejaVu Serif Bold
    return max(1.6, min(h * 0.62, (w * 0.92) / (per_char * len(txt))))


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


def plate_swing(w, h, txt="", t=PLATE_T):
    """Projecting swing sign: plate plus two hanging eyes for the chain."""
    body = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    body = try_fillet(body, "|Z", 1.2)
    for s in (-1, 1):
        eye = (cq.Workplane("XY").circle(1.6).extrude(t)
               .cut(cq.Workplane("XY").circle(0.8).extrude(t))
               .translate((s * (w / 2 - 3.0), h / 2 + 1.4, 0)))
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


def bracket_scroll(reach=14.0, drop=16.0, t=2.4, w=2.6):
    """Wrought-iron scroll bracket. Drawn in XZ and extruded so it prints flat with
    the scroll lying on the bed -- no supports, and the layer lines run along the arm."""
    arm = (cq.Workplane("XZ")
           .moveTo(0, 0).lineTo(reach, 0).lineTo(reach, -t).lineTo(0, -t)
           .close().extrude(-w))
    post = (cq.Workplane("XZ")
            .moveTo(0, -drop).lineTo(t, -drop).lineTo(t, 2.0).lineTo(0, 2.0)
            .close().extrude(-w))
    body = arm.union(post)
    # diagonal stay plus a scroll curl
    stay = (cq.Workplane("XZ")
            .moveTo(t, -drop * 0.85).lineTo(reach * 0.86, -t)
            .lineTo(reach * 0.86, -t - 2.0).lineTo(t + 2.2, -drop * 0.85)
            .close().extrude(-w))
    body = body.union(stay)
    curl = (cq.Workplane("XZ").center(reach * 0.5, -drop * 0.42).circle(drop * 0.20)
            .extrude(-w).cut(cq.Workplane("XZ")
                            .center(reach * 0.5, -drop * 0.42)
                            .circle(drop * 0.20 - 1.1).extrude(-w)))
    body = body.union(curl)
    # tip eye for the sign to hang from
    body = body.union(cq.Workplane("XZ").center(reach - 1.5, -t - 1.6).circle(1.7)
                      .extrude(-w)
                      .cut(cq.Workplane("XZ").center(reach - 1.5, -t - 1.6).circle(0.85)
                           .extrude(-w)))
    body = body.union(peg_p1((0.0, w / 2, -drop * 0.5), axis="-X"))
    return _to_part_frame(body)


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


def rail_hook(h=6.0, t=2.0, w=4.0):
    """Overhead rail hook on the ceiling baffle: signs hang across the alley from it."""
    body = (cq.Workplane("XZ").moveTo(0, 0).lineTo(t, 0).lineTo(t, -h)
            .lineTo(t + 2.2, -h).lineTo(t + 2.2, -h - t).lineTo(0, -h - t)
            .close().extrude(-w))
    return body.union(peg_p1((0.0, w / 2, 0.0), axis="+Z"))
