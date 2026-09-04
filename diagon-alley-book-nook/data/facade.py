"""Facade layout tables.

Everything decorative on the two walls is a row here, so adding a window is a row and
not a new function.  Coordinates are wall-local:

    u  depth from the front opening, 0 .. ALLEY_D
    z  height above the alley floor, 0 .. SCENE_H

Sizes in the table are FRONT-PLANE sizes.  The builder multiplies them by wpersp(u),
so the same row placed further back automatically becomes a smaller, more distant
version of itself -- that is the forced-perspective scale ladder in §3.
"""
import params as P

VP_U, VP_Z = 300.0, 105.0        # vanishing point for storey lines


def wpersp(u):
    """Element scale at wall depth u."""
    return 1.0 - P.PERSP_STRENGTH * (min(max(u, 0.0), P.ALLEY_D) / P.ALLEY_D)


def storey_z(z_front, u):
    """Height of a horizontal architectural line at depth u, converging on the
    vanishing point.  This is what makes the rear read as four compressed storeys
    where the front reads as three."""
    return z_front + (VP_Z - z_front) * (min(u, P.ALLEY_D) / VP_U)


# The six shopfronts, by their Diagon Alley names. The full name is the shop's
# identity; what a given sign can physically SAY is a different question, answered by
# verify.check_sign_text() -- at 0.4 mm of nozzle a bold serif glyph needs about 3.5 mm
# of size before its stems are one extrusion wide, and the rear plates are scaled to
# 0.6 by the forced perspective. So the front shops carry their name and the rear ones
# carry their trade.
SHOPS = {
    "L1": "OLLIVANDERS",                    # wands -- the hero bow front
    "L2": "THE APOTHECARY",                 # potion ingredients, projecting bay
    "L3": "SCRIBBULUS WRITING IMPLEMENTS",  # quills and ink, rear
    "R1": "EEYLOPS OWL EMPORIUM",           # owls, arched door
    "R2": "QUALITY QUIDDITCH SUPPLIES",     # brooms, full storefront
    "R3": "FLOURISH AND BLOTTS",            # books, rear
}

# ---------------------------------------------------------------------------
# Element rows.  Required keys: id, kind, u, z (front-plane height), plus the
# geometry keys each kind needs.  `lit` marks a bead pocket behind the element.
# ---------------------------------------------------------------------------
LEFT = [
    # --- L1  Ollivanders : the hero bow-fronted wandmaker ---------------------
    dict(id="10B", kind="bow",       u=20,  z=8,  w=40, h=46, proj=15, lit=2,
         name="L1_Bow_Window"),
    dict(id="10E", kind="stallriser", u=20, z=2,  w=40, h=10, name="L1_Stallriser"),
    dict(id="10D", kind="lintel",    u=20,  z=56, w=40, name="L1_Cornice"),
    dict(id="10G", kind="door",      u=44,  z=6,  w=22, h=44, panels=4, lit=1,
         name="L1_Door", fanlight=True),
    dict(id="19A", kind="quoin",     u=3,   z=0,  h=70, name="L_Quoin_Front"),

    # --- L2  The Apothecary : projecting bay ----------------------------------
    dict(id="11A", kind="bay",       u=74,  z=10, w=30, h=40, proj=13, lit=2,
         name="L2_Bay_Window"),
    # z=68, above the bay's roof. At its original 52 the awning's single mount landed
    # entirely inside the bay window's upper aperture -- the one element in the kit
    # with nothing to peg into -- and at 60 it fouled the bay roof by 6.9 mm^3. 68
    # clears both and gets 20.8 mm^3 of wall to grip.
    dict(id="11J", kind="awning",    u=74,  z=68, w=30, proj=8, name="L2_Awning"),
    dict(id="11F", kind="door",      u=98,  z=6,  w=18, h=36, panels=2, lit=1,
         name="L2_Door", fanlight=True),
    dict(id="11K", kind="fascia",    u=86,  z=54, w=38, name="L2_Fascia"),

    # --- L3  Scribbulus Writing Implements : rear, compressed -----------------
    dict(id="12A", kind="shopwin",   u=124, z=8,  w=24, h=26, cols=3, rows=2, lit=1,
         name="L3_Shop_Window"),
    dict(id="12D", kind="stallriser", u=124, z=2, w=24, h=7,  name="L3_Stallriser"),
    dict(id="12G", kind="door",      u=142, z=5,  w=14, h=26, panels=2,
         name="L3_Door"),

    # --- upper storeys : sash windows, shrinking with depth -------------------
    dict(id="13A", kind="window",    u=16,  z=78,  w=22, h=30, cols=2, rows=3, lit=1,
         style="sash", name="L_Window_A"),
    dict(id="13B", kind="window",    u=46,  z=78,  w=20, h=28, cols=2, rows=3, lit=1,
         style="sash", name="L_Window_B"),
    dict(id="12B", kind="oriel",     u=76,  z=76,  w=24, h=30, proj=10, lit=1,
         name="L_Oriel", lean=3.0),
    dict(id="13C", kind="window",    u=108, z=76,  w=18, h=24, cols=2, rows=2, lit=1,
         style="sash", name="L_Window_C"),
    dict(id="13D", kind="window",    u=134, z=74,  w=15, h=20, cols=2, rows=2,
         style="plain", name="L_Window_D"),
    dict(id="13E", kind="window",    u=24,  z=128, w=20, h=26, cols=2, rows=3, lit=1,
         style="sash", name="L_Window_E"),
    dict(id="13F", kind="window",    u=62,  z=126, w=18, h=24, cols=2, rows=2,
         style="sash", name="L_Window_F"),
    dict(id="13G", kind="window",    u=100, z=124, w=15, h=20, cols=2, rows=2,
         style="plain", name="L_Window_G"),
    dict(id="14A", kind="window",    u=36,  z=170, w=16, h=20, cols=2, rows=2,
         style="plain", arch=True, name="L_Attic_Dormer", lit=1),
    dict(id="14B", kind="window",    u=88,  z=166, w=13, h=16, cols=1, rows=2,
         style="plain", arch=True, name="L_Attic_B"),

    # --- rainwater goods, cornices, ornament ---------------------------------
    dict(id="15A", kind="pipe",      u=60,  z=6,   h=110, dia=4.2, name="L_Drainpipe_Lower"),
    dict(id="15B", kind="pipe",      u=60,  z=118, h=76,  dia=3.6, name="L_Drainpipe_Upper"),
    dict(id="15C", kind="hopper",    u=60,  z=114, w=8,   name="L_Hopper"),
    dict(id="17A", kind="cornice",   u=0,   z=190, length=78, name="L_Cornice_Front"),
    dict(id="17B", kind="cornice",   u=80,  z=190, length=70, name="L_Cornice_Rear"),
    dict(id="18A", kind="chimney",   u=52,  z=196, w=14, h=22, pots=2, name="L_Chimney"),
    dict(id="19B", kind="ornament",  u=110, z=54,  w=10, h=8,  name="L_Keystone"),
    dict(id="19C", kind="ornament",  u=30,  z=64,  w=12, h=9,  name="L_Wall_Plaque"),
]

RIGHT = [
    # --- R1  Eeylops Owl Emporium : arched door, tall window ------------------
    # u=21 w=19, not u=16 w=22. The door's opening reached to within 1.5 mm of the
    # wall's front edge, so the front quoin's mounts -- which sit at depth 5.5-9.5 for
    # the quoin's whole height -- landed INSIDE the door opening. The quoin ended up
    # anchored by a single 2.5 mm strip of lintel above the door, and that strip is
    # what verify.py kept reporting as a 1.8 mm^2 crumb hanging by a sub-nozzle neck.
    # Moving the door back and narrowing it by 3 mm gives the quoin solid wall to grip
    # and still leaves 2 mm of clearance to R1_Tall_Window behind it.
    dict(id="20B", kind="door",      u=21,  z=6,  w=19, h=46, panels=2, arch=True,
         lit=1, name="R1_Arched_Door"),
    dict(id="20E", kind="window",    u=42,  z=12, w=20, h=40, cols=2, rows=4, lit=2,
         style="sash", name="R1_Tall_Window"),
    dict(id="20G", kind="ornament",  u=21,  z=56, w=12, h=8,  name="R1_Door_Keystone"),
    dict(id="29A", kind="quoin",     u=3,   z=0,  h=70, name="R_Quoin_Front"),

    # --- R2  Quality Quidditch Supplies : full storefront under the banner ----
    dict(id="21B", kind="shopwin",   u=72,  z=10, w=34, h=32, cols=3, rows=2, lit=2,
         name="R2_Shop_Window"),
    dict(id="21D", kind="pilaster",  u=54,  z=4,  h=44, name="R2_Pilaster_Left"),
    dict(id="21E", kind="pilaster",  u=90,  z=4,  h=44, name="R2_Pilaster_Right"),
    dict(id="21F", kind="fascia",    u=72,  z=46, w=40, name="R2_Fascia"),
    dict(id="21G", kind="stallriser", u=72, z=2,  w=34, h=8, name="R2_Stallriser"),

    # --- R3  Flourish and Blotts : rear, compressed ---------------------------
    dict(id="22A", kind="shopwin",   u=120, z=8,  w=22, h=24, cols=2, rows=2, lit=1,
         name="R3_Shop_Window"),
    dict(id="22D", kind="door",      u=138, z=5,  w=13, h=24, panels=2,
         name="R3_Door"),

    # --- upper storeys --------------------------------------------------------
    dict(id="24A", kind="bay",       u=30,  z=76, w=26, h=34, proj=12, lit=1,
         name="R_Bay_Window"),
    dict(id="23A", kind="window",    u=62,  z=78, w=20, h=28, cols=2, rows=3, lit=1,
         style="sash", name="R_Window_A"),
    dict(id="23B", kind="window",    u=94,  z=76, w=17, h=23, cols=2, rows=2, lit=1,
         style="sash", name="R_Window_B"),
    dict(id="23C", kind="window",    u=124, z=74, w=14, h=19, cols=2, rows=2,
         style="plain", name="R_Window_C"),
    dict(id="23D", kind="window",    u=20,  z=128, w=20, h=26, cols=2, rows=3, lit=1,
         style="sash", name="R_Window_D"),
    dict(id="23E", kind="window",    u=58,  z=126, w=17, h=23, cols=2, rows=2,
         style="sash", name="R_Window_E"),
    dict(id="23F", kind="window",    u=96,  z=124, w=14, h=19, cols=2, rows=2,
         style="plain", name="R_Window_F"),
    dict(id="23G", kind="window",    u=44,  z=170, w=15, h=19, cols=2, rows=2,
         style="plain", arch=True, lit=1, name="R_Attic_A"),
    dict(id="23H", kind="window",    u=96,  z=166, w=12, h=15, cols=1, rows=2,
         style="plain", arch=True, name="R_Attic_B"),

    # --- rainwater goods, cornices, ornament ---------------------------------
    dict(id="25A", kind="pipe",      u=110, z=6,  h=108, dia=4.0, name="R_Drainpipe_Lower"),
    dict(id="25B", kind="pipe",      u=110, z=116, h=76, dia=3.4, name="R_Drainpipe_Upper"),
    dict(id="25C", kind="hopper",    u=110, z=112, w=7,  name="R_Hopper"),
    dict(id="27A", kind="cornice",   u=0,   z=188, length=76, name="R_Cornice_Front"),
    dict(id="27B", kind="cornice",   u=78,  z=188, length=72, name="R_Cornice_Rear"),
    dict(id="28A", kind="chimney",   u=104, z=194, w=12, h=18, pots=2, name="R_Chimney"),
    dict(id="29B", kind="ornament",  u=118, z=50, w=9,  h=7,  name="R_Keystone"),
    dict(id="29C", kind="ornament",  u=76,  z=60, w=11, h=8,  name="R_Guild_Badge"),
]

# ---------------------------------------------------------------------------
# Signs.  side: "L" | "R" | "X" (crossing the alley from the overhead rail).
# ---------------------------------------------------------------------------
SIGNS = [
    # Sizes here are set by legibility, not by taste. verify.check_sign_text() computes
    # the size the letters actually come out at after the forced-perspective scale and
    # fails anything under MIN_TEXT_SIZE, because a bold serif stem is about 0.12 of the
    # glyph size and anything under one 0.42 mm extrusion prints as mush. Several of
    # these plates grew to carry their name; the ones that could not grow carry the
    # shop's trade instead, which is what a real alley sign does anyway.
    dict(id="30A", kind="banner",  side="R", u=66,  z=96, w=14, h=64, lit=1,
         text="DIAGON", name="Sign_Vertical_Banner"),
    dict(id="30B", kind="swing",   side="L", u=30,  z=64, w=34, h=15,
         text="OLLIVANDERS", name="Sign_Swing_Ollivanders", bracket="31A"),
    dict(id="30C", kind="swing",   side="R", u=52,  z=62, w=26, h=13,
         text="EEYLOPS", name="Sign_Swing_Eeylops", bracket="31B"),
    dict(id="30D", kind="shield",  side="L", u=90,  z=77, w=23, h=21,
         text="POTIONS", name="Sign_Shield_Apothecary", bracket="31C"),
    # fasciaplate: pinned to the fascia BOARD it sits on (21F), so its u and z match
    # that row's and its width stays inside the board's.
    dict(id="30E", kind="fasciaplate", side="R", u=72, z=46, w=38, h=8,
         text="QUIDDITCH", name="Sign_Fascia_Quidditch"),
    dict(id="30F", kind="arrow",   side="L", u=120, z=72, w=46, h=11,
         text="GRINGOTTS", name="Sign_Directional"),
    # the lozenge column is a shop directory: four more of the alley's trades
    dict(id="30G1", kind="lozenge", side="R", u=104, z=64, w=21, h=9,
         text="PETS", name="Sign_Lozenge_Menagerie"),
    dict(id="30G2", kind="lozenge", side="R", u=104, z=52, w=21, h=9,
         text="JOKE", name="Sign_Lozenge_Wheezes"),
    dict(id="30G3", kind="lozenge", side="R", u=104, z=40, w=21, h=9,
         text="ICES", name="Sign_Lozenge_Fortescue"),
    dict(id="30G4", kind="lozenge", side="R", u=104, z=28, w=21, h=9,
         text="ROBES", name="Sign_Lozenge_Malkin"),
    dict(id="30H", kind="swing",   side="L", u=138, z=52, w=20, h=10,
         text="INK", name="Sign_Swing_Scribbulus", bracket="31D"),
    dict(id="30J", kind="fasciaplate", side="L", u=86, z=54, w=34, h=8,
         text="APOTHECARY", name="Sign_Fascia_Apothecary"),
    # blank spares -- deliberately textless so custom names can be added later
    dict(id="30K", kind="swing",   side=None, u=0, z=0, w=34, h=15, text="",
         name="Sign_Blank_Swing"),
    dict(id="30L", kind="shield",  side=None, u=0, z=0, w=23, h=21, text="",
         name="Sign_Blank_Shield"),
    dict(id="30M", kind="lozenge", side=None, u=0, z=0, w=21, h=9, text="",
         name="Sign_Blank_Lozenge"),
    dict(id="30N", kind="fasciaplate", side=None, u=0, z=0, w=38, h=8, text="",
         name="Sign_Blank_Fascia"),
]

# Positions here are constrained, not chosen: every one of these sockets is a hole in
# the same wall face as the shopfronts, and verify.check_mount_crowding() will not let
# one sit under the part next door. The lower storey is solid shopfront, so a mount with
# nowhere to go goes UP -- which is where a bracket carrying a hanging sign belongs.
BRACKETS = [
    # 30B's bracket. 2.5 mm along the wall, because at u=30 the socket was 1.5 mm
    # inside the 13A window frame above it -- the hole that showed up on the coupon tile.
    dict(id="31A", side="L", u=33,  z=76, reach=15, drop=17, name="Bracket_Scroll_A"),
    dict(id="31B", side="R", u=52,  z=74, reach=14, drop=16, name="Bracket_Scroll_B"),
    # 30D's bracket, lifted with it to clear the L2 awning and the oriel above
    dict(id="31C", side="L", u=90,  z=87, reach=12, drop=14, name="Bracket_Scroll_C"),
    dict(id="31D", side="L", u=138, z=73, reach=8,  drop=10, name="Bracket_Scroll_D"),
]

LANTERNS = [
    # Both of the big lanterns hung on shopfront: 33A's socket was under the bow window
    # AND the door, 34A's under the R2 shop window. They hang above the fascia now,
    # which is where a street lantern goes anyway.
    dict(id="33A", side="L", u=40,  z=76, h=26, w=10, lit=1, name="Lantern_Large"),
    dict(id="34A", side="R", u=84,  z=71, h=21, w=8.5, lit=1, name="Lantern_Small"),
    dict(id="34C", side="R", u=132, z=40, h=15, w=6.5, lit=1, name="Lantern_Rear_Tiny"),
]

# `foot` is the footprint (w, d) of a free-standing prop, used to cut its locating
# recess in the cobbles. Wall-hung props have no foot.
PROPS = [
    dict(id="35A", kind="barrel", side="L", u=52,  d=13, h=17, name="Barrel_Large",
         foot=(14.0, 14.0)),
    dict(id="35B", kind="barrel", side="R", u=100, d=10, h=13, name="Barrel_Small",
         foot=(11.0, 11.0)),
    dict(id="36A", kind="crate_stack", side="R", u=36, name="Crate_Stack",
         foot=(13.0, 11.0)),
    dict(id="36B", kind="crate", side="L", u=112, w=9, d=8, h=7, name="Crate_Single",
         foot=(9.0, 8.0)),
    dict(id="37A", kind="cauldrons", side="L", u=92,  name="Cauldron_Stack",
         foot=(21.0, 13.0)),
    dict(id="37B", kind="brooms", side="R", u=64,  name="Broom_Rack"),
    dict(id="37C", kind="postbox", side="R", u=26, name="Post_Box", foot=(10.0, 9.0)),
    # down 6 mm: the board's socket was under the L2 bay. The poster layer glues
    # ONTO the board and has no wall socket of its own -- it used to share the
    # board's, which is two pegs in one hole.
    dict(id="38A", kind="notice", side="L", u=68,  z=24, name="Notice_Board"),
    dict(id="38B", kind="posters", side="L", u=68, z=24, name="Poster_Layer"),
    dict(id="39A", kind="kerb", side="L", u=80,  name="Kerb_Step", foot=(18.0, 6.0)),
    dict(id="39B", kind="hatch", side="R", u=48,  name="Cellar_Hatch", foot=(14.0, 11.0)),
    dict(id="39C", kind="scraper", side="L", u=46, z=2, name="Boot_Scraper"),
]
