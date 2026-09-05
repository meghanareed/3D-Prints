#!/usr/bin/env python3
"""The one plate that decides whether this kit is worth continuing.

    python3 coupon.py     ->  out/coupon/FIT_TEST.stl  and  .3mf

Nothing over 10 g gets printed again until a plate off this file goes together in your
hand.

---------------------------------------------------------------------- plate 1 ------
Printed. It asked three questions and answered two of them, one of them by accident.

  SHAPE.  A square-cornered socket and a round one, the old peg and the new. Reported:
  the square "fits but comes out when turned over and you can see that the shape is not
  perfectly aligned"; the round "is almost a perfect shape match". That is the rounded
  internal corner, seen directly, and it settles the redesign: round is right.

  THE REAL PART.  The 13A frame went into the aperture of a tile cut from the real left
  wall and fitted well -- the first thing in this project to assemble.

  CLEARANCE.  Nothing, because of a bug in this file: the ladder passed its clearance to
  the SQUARE bore only, so all seven round sockets were cut at FIT_CLEARANCE and the six
  labels were decoration. Cross-sections measured 6.4064 mm^2 at every station.

That bug turned the ladder into something more useful than the test it replaced: seven
identical sockets, seven identical pegs, one plate. Three held the peg when turned over
and four dropped it. So the scatter between one socket and the next is wider than the
whole 0.20-0.45 mm range the ladder meant to span, and NO nominal clearance gives a
repeatable press fit on a 2.4 mm peg on this machine.

---------------------------------------------------------------------- plate 2 ------
Which is what a crush rib is for. A rib stands proud of the bore wall by the clearance
plus a fixed bite, so it reaches the peg whether that particular bore came out tight or
loose, and shears to suit. The kit's old ribs were rectangular, in a rectangular bore
whose corners the nozzle could not cut; that pairing failed, and the rib got the blame.

This plate puts ribs in a ROUND bore and asks one question -- does a ribbed socket hold
a peg that a plain socket at the same clearance drops? -- with three copies of every
station, because a single sample is what got us here:

    P30   plain bore, 0.30/side          the control: expected to drop the peg
    R30   ribbed bore, 0.30/side         same hole, three ribs
    R40   ribbed bore, 0.40/side         goes in easily; do the ribs still hold it?

and the same comparison once more on P2, the pair mount that every window and door in
the kit actually uses, since the ladder only ever tested P1.
"""
import os
import sys

import cadquery as cq

import build as B
import plates as PL
import mf3
from lib import mount as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "coupon")

# (label, clearance per side, ribbed)
P1_STATIONS = [("P30", 0.30, False), ("R30", 0.30, True), ("R40", 0.40, True)]
P2_STATIONS = [("P30", 0.30, False), ("R30", 0.30, True)]
COPIES = 3

BLOCK_W, BLOCK_D, BLOCK_H = 13.0, 13.5, 5.5
HANDLE_W, HANDLE_D, HANDLE_H = 10.0, 13.5, 3.0
BAR_W, BAR_D, BAR_H = 24.0, 13.5, 6.0   # P2 bores go 4.6 deep, so the bar is taller
SOCKET_Y, PEG_Y = 3.6, 3.6      # feature in the top half, label in the bottom
LABEL_Y = -4.6


def _engrave(solid, txt, size, top_z, y, flip=False):
    """Sink a label into the top face at an ABSOLUTE position.

    lib.util.emboss_text works in the selected face's own frame, which after a socket
    and its counterbore have been cut is not the frame you think it is -- an earlier
    version of this plate put "0.35" straight through the bore. Building the text on a
    global XY workplane at a known height and cutting it leaves nothing to guess at.

    `flip` is for the peg handles. They are built peg-down and printed peg-up, so the
    face that carries their label is turned over on the way to the bed; mirroring the
    text about XZ first means it reads the right way round in your hand.
    """
    try:
        cut = (cq.Workplane("XY").workplane(offset=top_z).center(0, y)
               .text(txt, size, -0.5, font="DejaVu Sans", kind="bold", combine=False))
        if flip:
            cut = cut.mirror("XZ")
        return solid.cut(cut)
    except Exception:
        return solid


def _socket_block(label, clearance, ribbed, pair=False):
    """A block with one mount in the top half of its face and its label in the bottom.

    The socket is driven DOWN from the top face, the same direction the peg travels.
    That is the library's convention -- a socket is the oversized swept volume of its
    peg, built in the same frame and with the same axis -- and it also puts the lead-in
    counterbore at the mouth. Plate 1 drove the bore upward from inside the block, which
    left the lead-in at the blind end and the mouth square.
    """
    w = BAR_W if pair else BLOCK_W
    d = BAR_D if pair else BLOCK_D
    top = BAR_H if pair else BLOCK_H
    blk = cq.Workplane("XY").box(w, d, top, centered=(True, True, False))
    fn = M.socket_p2_solids if pair else M.socket_p1_solids
    cut, add = fn((0, SOCKET_Y, top), axis="-Z", decorative=False,
                  clear=clearance, ribs=ribbed)
    blk = blk.cut(cut)
    if add is not None:
        blk = blk.union(add)
    return _engrave(blk, label, 3.0, top, LABEL_Y)


def _peg_handle(label, pair=False):
    """A peg on a handle you can hold.

    Built peg-DOWN, like every mounting part in the kit: the handle is the part, the
    block is the wall, and lowering one onto the other is a translation with no flip in
    it. A flip would mirror the D-flat and the unequal P2 pair, which is the mistake
    this library's header warns about and which has shipped three times.

    Every station takes the SAME peg -- only the bores differ -- so any handle fits any
    block and one peg can be tried in two sockets.
    """
    w = BAR_W if pair else HANDLE_W
    d = BAR_D if pair else HANDLE_D
    h = (cq.Workplane("XY").box(w, d, HANDLE_H, centered=(True, True, False))
         .translate((0, 0, 0)))
    peg = (M.peg_p2 if pair else M.peg_p1)((0, PEG_Y, 0.0), axis="-Z")
    # +4.4, not -4.4: the mirror puts the text on the far side of the peg, and the flip
    # onto the bed puts it back. Sign it the other way and the label lands on the peg.
    return _engrave(h.union(peg), label, 2.6, 0.5, 4.4, flip=True)


def _check_mates(pair=False):
    """Lower a handle onto a block and measure the interference, for real.

    Not "both were built from the same numbers" -- that check has passed three times on
    geometry that did not fit. Move the peg the way your hand moves it and subtract.
    """
    top = BAR_H if pair else BLOCK_H
    blk = _socket_block("X", 0.30, False, pair=pair)
    hnd = _peg_handle("X", pair=pair).translate((0, 0, top))
    peg = hnd.cut(cq.Workplane("XY").box(60, 60, HANDLE_H, centered=(True, True, False))
                  .translate((0, 0, top)))
    return blk, hnd, peg.val().Volume(), peg.intersect(blk).val().Volume()


def _print_peg(solid):
    """Handles are built peg-down and printed peg-up, exactly as the kit's parts are."""
    return B.drop_to_bed(B.print_orient(solid, ("X", 180)))


def build():
    items = []
    for label, clearance, ribbed in P1_STATIONS:
        for i in range(COPIES):
            tag = f"{label}{chr(ord('a') + i)}"
            items.append((f"P1_{tag}_socket", _socket_block(label, clearance, ribbed)))
            items.append((f"P1_{tag}_peg", _print_peg(_peg_handle(label))))
    for label, clearance, ribbed in P2_STATIONS:
        for i in range(2):
            tag = f"{label}{chr(ord('a') + i)}"
            items.append((f"P2_{tag}_socket",
                          _socket_block(label, clearance, ribbed, pair=True)))
            items.append((f"P2_{tag}_peg", _print_peg(_peg_handle(label, pair=True))))
    return items


def main():
    os.makedirs(OUT, exist_ok=True)

    for pair in (False, True):
        _, _, pegvol, fouled = _check_mates(pair=pair)
        kind = "P2" if pair else "P1"
        print(f"  {kind}: peg {pegvol:.2f} mm^3, fouling the block {fouled:.3f} mm^3")
        if fouled > 0.05:
            raise SystemExit(f"{kind} peg does not enter its own socket -- "
                             "the mating flip is wrong again")

    items = build()
    placed = []
    for name, solid in items:
        s = B.drop_to_bed(solid)
        bb = s.val().BoundingBox()
        placed.append(dict(id=name, name=name, w=bb.xlen, d=bb.ylen,
                           solid=s.translate((-bb.xmin, -bb.ymin, 0))))
    laid, left = PL.shelf_pack(placed)
    if left:
        raise SystemExit(f"{len(left)} piece(s) did not fit the bed: "
                         + ", ".join(i["id"] for i in left))

    import tempfile
    objs, stl_parts = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for it, x, y in laid:
            p = os.path.join(tmp, it["id"] + ".stl")
            cq.exporters.export(it["solid"], p)
            verts, tris = mf3.mesh_of_stl(p)
            lo_x = min(v[0] for v in verts)
            lo_y = min(v[1] for v in verts)
            objs.append(dict(name=it["id"], verts=verts, tris=tris, brim=True,
                             pos=(x - lo_x, y - lo_y, 0.0)))
            stl_parts.append(it["solid"].translate((x, y, 0)))
        from lib.util import compound
        cq.exporters.export(cq.Workplane(obj=compound(stl_parts)),
                            os.path.join(OUT, "FIT_TEST.stl"))
        mf3.write_project(os.path.join(OUT, "FIT_TEST.3mf"), "FIT_TEST", objs,
                          mf3.project_settings())

    g = sum(cq.Workplane(obj=it["solid"].val()).val().Volume() for it, _, _ in laid)
    g = g / 1000.0 * 1.24
    bb = [max(x + it["w"] for it, x, _ in laid), max(y + it["d"] for it, _, y in laid)]
    print(f"{len(laid)} pieces, {g:.0f} g, footprint {bb[0]:.0f} x {bb[1]:.0f} mm")
    print(f"  -> {OUT}/FIT_TEST.stl and .3mf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
