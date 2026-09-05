"""Pull real settings out of a Bambu Studio project, instead of guessing at them.

Two research items need a human in Bambu Studio for two minutes, and both end here:

    R-3   the vendored slicer profile IS a real 'Bambu Lab P2S' export at 0.4 -- that
          was checked rather than assumed -- but it predates the current Studio
          session and carries 7 filament slots where a later project carried 8.
          Re-export to be certain the elephant-foot and compensation values are the
          ones that will actually slice.

    R-13  per-object support settings have never been written by this project, and
          guessing at Bambu's format has already cost two rounds. Read the real thing.

    python ingest.py <project.3mf>            inspect: what is in it, what changed
    python ingest.py <project.3mf> --install  also replace profiles/ with its profile

Nothing is written without --install, so it is safe to point at any file and look.
"""
import difflib
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DEST = os.path.join(HERE, "profiles", "P2S_project_settings.config")

# The keys R-13 exists to confirm. Bambu declares all of these in PrintObjectConfig, so
# they are per-object overridable -- but the SPELLING of the values is what we cannot
# guess: is it "tree(auto)" or "tree"? Is a bool "1" or "true"?
SUPPORT_KEYS = [
    "enable_support", "support_type", "support_style", "support_threshold_angle",
    "support_on_build_plate_only", "support_critical_regions_only",
    "support_top_z_distance", "support_bottom_z_distance", "support_object_xy_distance",
    "tree_support_branch_angle", "tree_support_branch_diameter",
    "tree_support_branch_distance", "tree_support_wall_count",
]
BRIM_KEYS = ["brim_type", "brim_width", "brim_object_gap"]

# ============================================================================
# CONFIRMED by reading a real Bambu project, 2026-09-05. plate.py imports this
# rather than guessing, because guessing at this format has cost two rounds.
#
# Per-object settings are <metadata key="..." value="..."/> children of <object>
# in Metadata/model_settings.config:
#
#     <object id="2">
#       <metadata key="name"                    value="..."/>
#       <metadata key="brim_type"               value="outer_only"/>
#       <metadata key="enable_support"          value="1"/>
#       <metadata key="support_threshold_angle" value="32"/>
#       <part id="1" subtype="normal_part"> ... </part>
#     </object>
#
# Three things that were guesses and are now facts:
#   * booleans serialise as the STRING "1" / "0", not "true"/"false";
#   * numbers serialise as strings too ("32", not 32);
#   * Bambu writes ONLY THE KEYS THAT DIFFER from the plate default. An object
#     with three overrides carries three metadata lines, not the full set. So
#     the emitter must write overrides, not a complete config, or every object
#     will pin every value and the plate profile stops meaning anything.
#
# STILL UNKNOWN: the subtype spelling for support enforcer / blocker volumes.
# The sample project had only 'normal_part'. Add one in Studio and re-ingest.
VALUE_TRUE, VALUE_FALSE = "1", "0"
PART_SUBTYPE_NORMAL = "normal_part"



def _read(zf, name):
    try:
        return zf.read(name).decode("utf8", "ignore")
    except KeyError:
        return None


def inspect(path):
    if not os.path.exists(path):
        sys.exit(f"no such file: {path}")
    zf = zipfile.ZipFile(path)
    names = zf.namelist()

    print(f"\n{'=' * 74}\n  {os.path.basename(path)}\n{'=' * 74}")

    # --- is it actually a Bambu PROJECT? ------------------------------------------
    model = _read(zf, "3D/3dmodel.model") or ""
    app = ""
    for line in model.splitlines()[:40]:
        if 'name="Application"' in line:
            app = line.split(">")[1].split("<")[0]
            break
    ok_app = app.startswith("BambuStudio-")
    print(f"\n  Application tag: {app or '(none)'}")
    print(f"  {'OK' if ok_app else 'PROBLEM'}: Bambu only honours settings when this "
          f"starts with 'BambuStudio-'.")
    if not ok_app:
        print("  Without it the file still opens, but every setting is discarded and "
              "you get\n  'load geometry data only'. That is not an error message about "
              "your brim.")

    # --- R-3: the print profile ----------------------------------------------------
    cfg = _read(zf, "Metadata/project_settings.config")
    print(f"\n{'-' * 74}\n  R-3  print profile\n{'-' * 74}")
    if not cfg:
        print("  NOT PRESENT. Save with File > Save Project As, not Export Plate.")
    else:
        new = json.loads(cfg)
        print(f"  found, {len(new)} keys.  printer_model = {new.get('printer_model')!r}")
        for k in ("nozzle_diameter", "layer_height", "elefant_foot_compensation",
                  "xy_hole_compensation", "brim_type", "brim_width", "enable_support",
                  "support_type", "support_threshold_angle", "printable_height"):
            print(f"    {k:32} {new.get(k)}")
        if os.path.exists(PROFILE_DEST):
            old = json.load(open(PROFILE_DEST, encoding="utf8"))
            diff = {k: (old.get(k), new.get(k))
                    for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)}
            print(f"\n  {len(diff)} keys differ from the vendored profile"
                  f"{':' if diff else ' -- it was already current.'}")
            for k, (o, n) in list(diff.items())[:25]:
                print(f"    {k:32} {o!r}  ->  {n!r}")
            if len(diff) > 25:
                print(f"    ... and {len(diff) - 25} more")

    # --- R-13: per-object settings -------------------------------------------------
    ms = _read(zf, "Metadata/model_settings.config")
    print(f"\n{'-' * 74}\n  R-13  per-object settings\n{'-' * 74}")
    if not ms:
        print("  NOT PRESENT.")
        return
    import xml.etree.ElementTree as ET
    root = ET.fromstring(ms)
    objs = root.findall("object")
    print(f"  {len(objs)} object(s) in the project")

    found_support, found_brim, subtypes = {}, {}, set()
    for obj in objs:
        oid = obj.get("id")
        keys = {m.get("key"): m.get("value") for m in obj.findall("metadata")
                if m.get("key")}
        interesting = {k: v for k, v in keys.items()
                       if k in SUPPORT_KEYS or k in BRIM_KEYS}
        name = keys.get("name", "?")
        print(f"\n    object {oid}  {name}")
        if interesting:
            for k, v in sorted(interesting.items()):
                print(f"      {k:32} = {v!r}")
                (found_support if k in SUPPORT_KEYS else found_brim)[k] = v
        else:
            print("      (no per-object print settings -- it is using plate defaults)")
        for part in obj.findall("part"):
            st = part.get("subtype")
            if st:
                subtypes.add(st)
            pk = {m.get("key"): m.get("value") for m in part.findall("metadata")}
            pi = {k: v for k, v in pk.items() if k in SUPPORT_KEYS or k in BRIM_KEYS}
            for k, v in sorted(pi.items()):
                print(f"      part {part.get('id')}: {k:24} = {v!r}")
                (found_support if k in SUPPORT_KEYS else found_brim)[k] = v

    print(f"\n  part subtypes seen: {sorted(subtypes) or '(none)'}")
    print("  Support enforcer/blocker volumes appear here as subtypes. Anything other")
    print("  than 'normal_part' is what plate.py must emit to steer supports.")

    print(f"\n{'=' * 74}\n  WHAT THIS ANSWERS\n{'=' * 74}")
    print(f"  R-3   profile present ............... {'YES' if cfg else 'NO'}")
    print(f"  R-13  per-object SUPPORT keys ....... "
          f"{'YES -- ' + ', '.join(sorted(found_support)) if found_support else 'NO'}")
    print(f"  R-13  per-object BRIM keys .......... "
          f"{'YES -- ' + ', '.join(sorted(found_brim)) if found_brim else 'NO'}")
    print(f"  R-13  modifier subtypes ............. "
          f"{sorted(subtypes - {'normal_part'}) or 'none found'}")
    if not found_support:
        print("\n  No per-object support settings found. Set them on an object and save"
              "\n  again -- see the steps in PLAN 9. Plate-wide settings live in the"
              "\n  profile above and are NOT what R-13 is asking for.")
    return cfg


def install(cfg):
    os.makedirs(os.path.dirname(PROFILE_DEST), exist_ok=True)
    if os.path.exists(PROFILE_DEST):
        shutil.copy2(PROFILE_DEST, PROFILE_DEST + ".bak")
        print(f"\n  backed up existing profile to {PROFILE_DEST}.bak")
    with open(PROFILE_DEST, "w", encoding="utf8") as fh:
        fh.write(cfg)
    print(f"  wrote {PROFILE_DEST}")
    print("  params.py will now read it, and its R-3 caveat drops off every MACHINE "
          "value.\n  Re-run: python checks.py")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    cfg = inspect(args[0])
    if "--install" in sys.argv:
        if cfg:
            install(cfg)
        else:
            print("\n  nothing to install -- no project_settings.config in that file")
    print()
