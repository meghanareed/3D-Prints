"""Write a Bambu Studio PROJECT, with the settings baked in per object.

Adapted from the book nook's writer next door. Not an STL export: an STL carries geometry
and nothing else, so every setting has to be re-applied by hand at every slice, which is
how that project shipped a sprue with a brim it was already known not to need.

Three things this file exists to get right, each of which has already cost a print there:

  * **The Application tag.** Bambu only honours the settings in a 3MF when
    `<metadata name="Application">` starts with `BambuStudio-`. Get it wrong and the file
    still opens -- it silently discards every setting and says "load geometry data only",
    which does not sound like "your brim is gone".

  * **Per-object settings, written as OVERRIDES.** Bambu writes only the keys that DIFFER
    from the plate default, and serialises booleans and numbers as strings. An emitter
    that writes a full config onto every object pins every value and the plate profile
    stops meaning anything.

  * **Plate spacing of 2 x brim + 1.** At 6 mm the brims of neighbours merged and 22 of
    64 parts fused into one raft. A raft that peels takes every part on it.

    python plate.py            build the coupon plate, verify, report
    python plate.py --write    write out/plate_1_coupon.3mf
"""
import json
import os
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

import cadquery as cq

import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
APP_TAG = "BambuStudio-02.08.02.61"      # MUST start with "BambuStudio-"; see above
TESS_TOLERANCE = 0.05                    # mm; finer than the nozzle can resolve
PART_SUBTYPE_NORMAL = "normal_part"

# Applied on top of the vendored profile. Kept short and each one justified, because a
# long override list is a second profile pretending to be a patch.
PLATE_OVERRIDES = {
    # The profile ships auto_brim, and Auto looked at a 15 mm2 plaque and gave it no brim
    # at all; it came off the bed. outer_only at the PLATE level, with per-object
    # overrides as the belt to this pair of braces.
    "brim_type": "outer_only",
    "brim_width": "5",
}


# ------------------------------------------------------------------- geometry --
def _mesh(solid):
    """(vertices, triangles) for one CadQuery solid, normalised to sit on z=0.

    Normalised against the TESSELLATED VERTICES, not against BoundingBox(). Once a shape
    has been tessellated, OCCT computes its bounding box from the triangulation and adds
    the deflection, so `shape.BoundingBox()` called after `shape.tessellate()` comes back
    up to the tolerance larger than the shape. Subtracting that zmin lifted parts off the
    bed -- 0.001 mm for a filleted tile and 0.2 mm for one built by an intersect -- and a
    part with no first layer is not something the slicer warns about.

    Measure, do not derive: these are the vertices the file will actually contain.
    """
    shape = solid.val() if hasattr(solid, "val") else solid
    verts, tris = shape.tessellate(TESS_TOLERANCE)
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    dx, dy, dz = -(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(v.z for v in verts)
    return [(v.x + dx, v.y + dy, v.z + dz) for v in verts], tris


def _footprint(solid):
    bb = (solid.val() if hasattr(solid, "val") else solid).BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


# --------------------------------------------------------------------- layout --
def layout(items, bed=None, spacing=None):
    """Shelf-pack by footprint. Returns [(name, solid, brim, x, y)], and the depth used.

    Spacing is 2 x brim + 1 and is not negotiable -- see the module docstring.
    """
    bed = float(P.BED_X if bed is None else bed)
    gap = float(P.PLATE_SPACING if spacing is None else spacing)
    margin = float(P.BRIM_WIDTH) + 2.0

    placed, x, y, row_h = [], margin, margin, 0.0
    for name, solid, brim in items:
        w, d, _ = _footprint(solid)
        if x + w + margin > bed:                     # new shelf
            x, y, row_h = margin, y + row_h + gap, 0.0
        placed.append((name, solid, brim, x + w / 2, y + d / 2))
        x += w + gap
        row_h = max(row_h, d)
    return placed, y + row_h + margin


# ----------------------------------------------------------------- 3mf writing --
def _uuid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"inhaler-{seed}"))


def _object_model(mesh_id, verts, tris):
    v = "\n".join(f'     <vertex x="{a:.6f}" y="{b:.6f}" z="{c:.6f}"/>'
                  for a, b, c in verts)
    t = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p">\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        ' <resources>\n'
        f'  <object id="{mesh_id}" p:UUID="{_uuid(f"mesh{mesh_id}")}" type="model">\n'
        '   <mesh>\n'
        f'    <vertices>\n{v}\n    </vertices>\n'
        f'    <triangles>\n{t}\n    </triangles>\n'
        '   </mesh>\n'
        '  </object>\n'
        ' </resources>\n'
        ' <build/>\n'
        '</model>\n')


def _root_model(entries, title):
    """Wrapper objects + build items. The WRAPPER id is what everything else references."""
    res, build = [], []
    for e in entries:
        res.append(
            f'  <object id="{e["wrap_id"]}" p:UUID="{_uuid("w" + str(e["wrap_id"]))}" '
            f'type="model">\n'
            f'   <components>\n'
            f'    <component p:path="/3D/Objects/object_{e["mesh_id"]}.model" '
            f'objectid="{e["mesh_id"]}" p:UUID="{_uuid("c" + str(e["wrap_id"]))}" '
            f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
            f'   </components>\n'
            f'  </object>')
        build.append(
            f'  <item objectid="{e["wrap_id"]}" p:UUID="{_uuid("i" + str(e["wrap_id"]))}" '
            f'transform="1 0 0 0 1 0 0 0 1 {e["x"]:.6f} {e["y"]:.6f} 0" printable="1"/>')
    meta = "".join(f' <metadata name="{k}">{v}</metadata>\n' for k, v in (
        ("Application", APP_TAG), ("BambuStudio:3mfVersion", "1"),
        ("Title", title), ("Designer", ""), ("Description", "")))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'requiredextensions="p">\n'
        f'{meta}'
        ' <resources>\n' + "\n".join(res) + '\n </resources>\n'
        f' <build p:UUID="{_uuid("build")}">\n' + "\n".join(build) + '\n </build>\n'
        '</model>\n')


def _model_settings(entries):
    """Per-object settings. OVERRIDES ONLY -- see the module docstring."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for e in entries:
        out.append(f'  <object id="{e["wrap_id"]}">')
        out.append(f'    <metadata key="name" value="{e["name"]}"/>')
        for k, v in e["settings"].items():
            out.append(f'    <metadata key="{k}" value="{v}"/>')
        out.append(f'    <part id="{e["mesh_id"]}" subtype="{PART_SUBTYPE_NORMAL}">')
        out.append(f'      <metadata key="name" value="{e["name"]}"/>')
        out.append('      <metadata key="matrix" value="1 0 0 0 1 0 0 0 1 0 0 0"/>')
        out.append("    </part>")
        out.append("  </object>")
    out.append("  <plate>")
    out.append('    <metadata key="plater_id" value="1"/>')
    out.append('    <metadata key="plater_name" value=""/>')
    out.append('    <metadata key="locked" value="false"/>')
    for e in entries:
        out.append("    <model_instance>")
        out.append(f'      <metadata key="object_id" value="{e["wrap_id"]}"/>')
        out.append('      <metadata key="instance_id" value="0"/>')
        out.append("    </model_instance>")
    out.append("  </plate>")
    out.append("</config>\n")
    return "\n".join(out)


CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                 ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-'
                 'package.relationships+xml"/>\n'
                 ' <Default Extension="model" ContentType="application/vnd.ms-package.'
                 '3dmanufacturing-3dmodel+xml"/>\n'
                 ' <Default Extension="png" ContentType="image/png"/>\n'
                 ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n'
                 '</Types>\n')

ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
             'relationships">\n'
             ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.'
             'microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
             '</Relationships>\n')

SLICE_INFO = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
              '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
              f'    <header_item key="X-BBL-Client-Version" value="{APP_TAG.split("-")[1]}"/>\n'
              '  </header>\n</config>\n')


def build_entries(items):
    placed, _ = layout(items)
    entries = []
    for i, (name, solid, brim) in enumerate(items, start=1):
        pl = placed[i - 1]
        settings = {}
        if brim is False:
            # brim_width 0 rather than a brim_type enum, because "outer_only" is a
            # spelling we have READ in a real file and "no_brim" is one we have not.
            settings["brim_width"] = "0"
        entries.append(dict(name=name, mesh_id=i, wrap_id=1000 + i,
                            x=pl[3], y=pl[4], settings=settings, solid=solid))
    return entries


def split_to_plates(items, bed=None, spacing=None):
    """Break a set of parts into bed-sized groups. Returns [[items], [items], ...].

    Three copies of every swept value is rule 13, and it takes Prototype A past what one
    bed holds. Packing them into one plate anyway would silently drop parts off the far
    edge -- shelf-packing does not fail, it just keeps going.
    """
    # One spacing gap of headroom. Packing to 252 of 256 mm leaves 4 mm for a brim that
    # is 5 mm wide, and the shelf-packer does not know that -- it reports a depth, it
    # does not check one.
    bed = float(P.BED_X if bed is None else bed)
    limit = bed - float(P.PLATE_SPACING)
    groups, current = [], []
    for item in items:
        trial = current + [item]
        _, depth = layout(trial, bed=bed, spacing=spacing)
        if depth > limit and current:
            groups.append(current)
            current = [item]
        else:
            current = trial
    if current:
        groups.append(current)
    return groups


def write(items, path, title="Inhaler clicker"):
    entries = build_entries(items)
    with open(P.PROFILE_PATH, encoding="utf8") as fh:
        profile = json.load(fh)
    profile.update(PLATE_OVERRIDES)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        rels = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                'relationships">']
        for e in entries:
            v, t = _mesh(e["solid"])
            z.writestr(f"3D/Objects/object_{e['mesh_id']}.model",
                       _object_model(e["mesh_id"], v, t))
            rels.append(f' <Relationship Target="/3D/Objects/object_{e["mesh_id"]}.model" '
                        f'Id="rel-{e["mesh_id"]}" Type="http://schemas.microsoft.com/'
                        f'3dmanufacturing/2013/01/3dmodel"/>')
        rels.append("</Relationships>\n")
        z.writestr("3D/_rels/3dmodel.model.rels", "\n".join(rels))
        z.writestr("3D/3dmodel.model", _root_model(entries, title))
        z.writestr("Metadata/project_settings.config", json.dumps(profile, indent=4))
        z.writestr("Metadata/model_settings.config", _model_settings(entries))
        z.writestr("Metadata/slice_info.config", SLICE_INFO)
    return entries


# ==================================================================== self-test ==
def self_test(path):
    """Read our own output back. A writer that cannot be read is a guess."""
    out = []

    def t(name, cond, detail=""):
        out.append((bool(cond), name, detail))

    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    for need in ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model",
                 "3D/_rels/3dmodel.model.rels", "Metadata/project_settings.config",
                 "Metadata/model_settings.config"):
        t(f"contains {need}", need in names)

    root = z.read("3D/3dmodel.model").decode("utf8")
    t("Application tag makes Bambu honour settings",
      f'<metadata name="Application">{APP_TAG}' in root,
      "otherwise every setting is silently discarded")

    prof = json.loads(z.read("Metadata/project_settings.config").decode("utf8"))
    t("plate brim overridden off Auto", prof.get("brim_type") == "outer_only",
      f"brim_type={prof.get('brim_type')}")

    cfg = ET.fromstring(z.read("Metadata/model_settings.config").decode("utf8"))
    wrap_ids = {o.get("id") for o in cfg.findall("object")}
    built = {line.split('objectid="')[1].split('"')[0]
             for line in root.splitlines() if "<item objectid=" in line}
    t("every build item has settings, and vice versa", wrap_ids == built,
      f"settings {len(wrap_ids)} vs build {len(built)}")

    # Overrides only -- an object carrying dozens of keys means we wrote a whole config.
    worst = max((len(o.findall("metadata")) for o in cfg.findall("object")), default=0)
    t("settings are OVERRIDES, not full configs", worst <= 4, f"{worst} keys on one object")

    # Every mesh must be watertight-ish and land on the bed. A part hovering at z>0
    # slices as a part with no first layer, and Bambu will not say so.
    for name in sorted(n for n in names if n.startswith("3D/Objects/")):
        body = z.read(name).decode("utf8")
        zs = [float(line.split('z="')[1].split('"')[0])
              for line in body.splitlines() if "<vertex " in line]
        t(f"{name.rsplit('/', 1)[1]} sits on the bed", abs(min(zs)) < 1e-6,
          f"zmin {min(zs):.4f}")
    return out


if __name__ == "__main__":
    import coupon
    import mech

    bed = float(P.BED_X)
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)

    jobs = [(f"A{i + 1}", g, f"Inhaler clicker -- Prototype A coupons {i + 1}")
            for i, g in enumerate(split_to_plates(coupon.parts()))]
    jobs.append(("B", [("PROTO_B_skeleton", mech.skeleton(), None)],
                 "Inhaler clicker -- Prototype B mechanism skeleton"))

    print("plate -- Bambu project writer\n")
    print(f"  spacing {float(P.PLATE_SPACING):.0f} mm (2 x brim + 1) on a {bed:.0f} mm bed\n")

    bad, written = 0, []
    for tag, group, title in jobs:
        _, depth = layout(group)
        path = os.path.join(out_dir, f"plate_{tag}.3mf")
        write(group, path, title=title)
        fails = [r for r in self_test(path) if not r[0]]
        bad += len(fails)
        print(f"  plate_{tag}  {len(group):3d} objects  {depth:5.0f} mm deep"
              f"{'  -- OVERFLOWS' if depth > bed else ''}"
              f"   {len(fails)} failures")
        for _, name, detail in fails:
            print(f"      FAIL  {name}" + (f"   [{detail}]" if detail else ""))
        written.append(path)

    if "--write" not in sys.argv:
        for p in written:
            os.remove(p)
        print(f"\n  {bad} failures  (pass --write to keep the files)")
    else:
        print(f"\n  {bad} failures")
        for p in written:
            print(f"  wrote {os.path.basename(p)}  ({os.path.getsize(p) / 1024:.0f} kB)")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
