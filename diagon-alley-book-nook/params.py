"""Crooked Lane Book Nook - master parameters.  All dimensions in millimetres.

Edit this file and re-run build.py; every part re-derives.  The three numbers you are
most likely to touch are FIT_CLEARANCE, DECORATIVE_CLEARANCE and PERSP_STRENGTH.
"""

# ---------------------------------------------------------------- envelope --
BOOKNOOK_WIDTH  = 100.0     # X, across the alley
BOOKNOOK_HEIGHT = 240.0     # Z
BOOKNOOK_DEPTH  = 200.0     # Y, front (0) to back
SHELL_THICKNESS = 2.2
PLINTH_HEIGHT   = 24.0      # houses the battery / controller drawer

# ------------------------------------------------- printer: Bambu P2S 256^3 --
BED_X, BED_Y, BED_Z = 256.0, 256.0, 256.0
NOZZLE, LAYER       = 0.4, 0.20
MATERIAL            = "PLA"
PANEL_SPLIT = (BOOKNOOK_HEIGHT + 6.0) > min(BED_X, BED_Y)   # False at 256

# -------------------------------------------------------------- tolerances --
FIT_CLEARANCE        = 0.25   # structural mating faces, per side
DECORATIVE_CLEARANCE = 0.20   # decorative snap-ins, per side
SLIP_CLEARANCE       = 0.35   # chassis sliding into the case, per side
CRUSH_RIB            = 0.30   # sacrificial rib inside sockets
LEAD_IN_CHAMFER      = 0.50   # 45 deg at every socket mouth -- do not remove
PEG_TIP_CHAMFER      = 0.30

# ------------------------------------------------------------ wall build-up --
WALL_FACE_T     = 2.5       # brick plate the viewer sees
RIB_GAP         = 2.5       # clear gap behind the plate: decorative pegs pass through
                            # the 2.5 mm plate and need somewhere to go
WALL_SERVICE_D  = 5.0       # depth of the open service lattice behind the gap
WALL_ASSEMBLY_D = WALL_FACE_T + RIB_GAP + WALL_SERVICE_D   # 10.0
DETAIL_MIN_T      = 1.2
STRUCT_MIN_T      = 2.0
LIGHT_BLOCK_MIN_T = 1.5     # min solid left in front of any emitter

# ----------------------------------------------- lighting: fairy-light string --
LIGHT_SYSTEM       = "fairy"    # "fairy" | "discrete3mm"
BEAD_POCKET_W      = 3.2
BEAD_POCKET_H      = 5.0
BEAD_POCKET_D      = 3.2
WIRE_DIA           = 0.6
WIRE_SLOT_W        = 1.4        # pass-through slot BOTH sides of every pocket
WIRE_CHANNEL_WIDTH = 3.0
WIRE_CHANNEL_DEPTH = 3.0
WIRE_CAPTURE_MOUTH = 2.2        # pinched mouth: wire snaps in and stays
BUS_CHANNEL_WIDTH  = 4.5        # main run along the rear of the base pan
COIL_BAY_W, COIL_BAY_H, COIL_BAY_D = 34.0, 46.0, 4.0
LED_BORE = 3.0 + 2 * FIT_CLEARANCE   # retained for the "discrete3mm" option

# ------------------------------------------------- lighting: RGB/CCT pucks --
# Measured from the product listing: D 59.5 x H 8.3, 12 beads, PC light guide.
SKY_PUCK_DIA    = 59.5
SKY_PUCK_T      = 8.3
SKY_PUCK_CLEAR  = 0.6           # cradle bore = dia + 2*clear
SKY_PUCK_REAR   = True          # rear sky wash -- the standard build
SKY_PUCK_TOP    = False         # optional top plenum; costs 12 mm scene height
TOP_PLENUM_H    = 12.0
SKY_AIR_GAP_1   = 6.0           # puck -> diffuser
SKY_AIR_GAP_2   = 4.0           # diffuser -> silhouette screen
SKY_DIFFUSER_T  = 0.8
PUCK_CABLE_DIA  = 3.6

# ------------------------------------------------------------ power drawer --
DRAWER_INNER_L, DRAWER_INNER_W, DRAWER_INNER_H = 150.0, 86.0, 18.0
BATT_BOX_L, BATT_BOX_W, BATT_BOX_H = 64.0, 28.0, 17.0   # 3xAAA; shims for coin cells

# ------------------------------------------------------ glazing / diffusers --
DIFFUSER_PRINT_T = 0.8      # natural/white PLA, 3 walls, 0 % infill
DIFFUSER_SLOT_T  = 1.2      # also takes vellum / acetate / PET / 1.0 acrylic

# --------------------------------------------------------- surface detail --
BRICK_RELIEF       = 0.6
BRICK_LENGTH_FRONT = 18.0
BRICK_HEIGHT_FRONT = 6.0
MORTAR_GAP         = 1.2
BRICK_WORN_FRAC    = 0.04
BRICK_MISSING_FRAC = 0.02
COBBLESTONE_RELIEF = 0.8
COBBLE_SIZE_FRONT  = 10.0
COBBLE_JOINT       = 0.6
CAMBER             = 1.2    # alley crown height at the centreline
RANDOM_SEED        = 20260830

# ------------------------------------------------------ forced perspective --
PERSP_STRENGTH  = 0.42      # element scale at the rear = 1 - PERSP_STRENGTH
WALL_CANT_DEG   = 1.75
FACADE_LEAN_MAX = 4.0
CORNICE_DROP    = 14.0      # eaves line drops this much front -> rear

# --------------------------------------------------------------- lettering --
RENDER_TEXT = True
TEXT_DEPTH  = 0.5
TEXT_FONT   = "DejaVu Serif"
TEXT_MIN_STROKE = 1.0

# ================================================================= derived ==
CASE_CAVITY_W = BOOKNOOK_WIDTH - 2 * SHELL_THICKNESS
CASE_CAVITY_H = BOOKNOOK_HEIGHT - PLINTH_HEIGHT - SHELL_THICKNESS \
                - (TOP_PLENUM_H if SKY_PUCK_TOP else 0.0)
CASE_CAVITY_D = BOOKNOOK_DEPTH - SHELL_THICKNESS

CHASSIS_W = CASE_CAVITY_W - 2 * SLIP_CLEARANCE
CHASSIS_H = CASE_CAVITY_H - 2 * SLIP_CLEARANCE
CHASSIS_D = CASE_CAVITY_D - 2 * SLIP_CLEARANCE

BASE_PAN_T   = 10.0
SCENE_H      = CHASSIS_H - BASE_PAN_T
ALLEY_W_FRONT = CHASSIS_W - 2 * WALL_ASSEMBLY_D

# rear assembly occupies the last REAR_BAY_D of the chassis
REAR_BAY_D = 46.5
ALLEY_D    = CHASSIS_D - REAR_BAY_D

import math
CANT_OFFSET = ALLEY_D * math.tan(math.radians(WALL_CANT_DEG))
ALLEY_W_REAR = ALLEY_W_FRONT - 2 * CANT_OFFSET


def persp(y):
    """Forced-perspective scale factor at depth y (0 = front opening)."""
    return 1.0 - PERSP_STRENGTH * (min(max(y, 0.0), CHASSIS_D) / CHASSIS_D)


def alley_half_width(y):
    """Half-width of the clear alley at depth y, following the wall cant."""
    return (ALLEY_W_FRONT / 2.0) - min(y, ALLEY_D) * math.tan(math.radians(WALL_CANT_DEG))


if __name__ == "__main__":
    print(f"case cavity   {CASE_CAVITY_W:.1f} W x {CASE_CAVITY_H:.1f} H x {CASE_CAVITY_D:.1f} D")
    print(f"chassis       {CHASSIS_W:.1f} x {CHASSIS_H:.1f} x {CHASSIS_D:.1f}")
    print(f"scene height  {SCENE_H:.1f}")
    print(f"alley width   {ALLEY_W_FRONT:.1f} front -> {ALLEY_W_REAR:.1f} rear")
    print(f"alley depth   {ALLEY_D:.1f}  (rear bay {REAR_BAY_D})")
    print(f"panel split   {PANEL_SPLIT}")
    print(f"persp         y=0 {persp(0):.2f}  y=mid {persp(CHASSIS_D/2):.2f}  y=rear {persp(CHASSIS_D):.2f}")
