"""Write a Bambu Studio PROJECT, with the settings baked in per object.

Not an STL export. An STL carries geometry and nothing else, so every setting has to be
re-applied by hand at every slice -- which is how the last attempt shipped a pin sprue
with a brim it was already known not to need.

Three things this file exists to get right, each of which has already cost a print:

  * **The Application tag.** Bambu only honours the settings in a 3MF when
    `<metadata name="Application">` starts with `BambuStudio-`. Get it wrong and the file
    still opens -- it just silently discards every setting and says "load geometry data
    only", which does not sound like "your brim is gone". Two rounds were spent guessing
    at this before someone read the source.

  * **Per-object settings, written as OVERRIDES.** Confirmed by reading a real project
    (see ingest.py): Bambu writes only the keys that DIFFER from the plate default, and
    serialises booleans and numbers as strings. An emitter that writes a full config onto
    every object would pin every value and the plate profile would stop meaning anything.

  * **Plate spacing of 2 x brim + 1.** At 6 mm the brims of neighbours merged and 22 of
    64 parts fused into one raft. A raft that peels takes every part on it.

The structure mirrors what Bambu itself writes, because this is not the place to be
clever: wrapper objects in 3dmodel.model whose components point at a mesh file each, and
it is the WRAPPER id that both the build items and model_settings reference.

    python plate.py            build the coupon plate, verify, report
    python plate.py --write    write out/plate_1_coupon.3mf
"""
import os
import sys
import uuid
import zipfile

import cadquery as cq

import ingest
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
APP_TAG = "BambuStudio-02.08.02.61"      # MUST start with "BambuStudio-"; see above
TESS_TOLERANCE = 0.05                    # mm; finer than the nozzle can resolve

# Applied on top of the vendored profile. Kept short and each one justified, because a
# long override list is a second profile pretending to be a patch.
PLATE_OVERRIDES = {
    # The profile ships auto_brim, and Auto looked at a 15 mm2 wall plaque and gave it no
    # brim at all; it came off the bed. outer_only at the PLATE level, with per-object
    # overrides as the belt to this pair of braces.
    "brim_type": "outer_only",
    "brim_width": "5",
    # Stringing across window openings. The one real print-quality change here.
    "reduce_crossing_wall": "1",
}


# ------------------------------------------------------------------- geometry --
def _mesh(solid):
    """(vertices, triangles) for one CadQuery solid, normalised to sit on z=0."""
    shape = solid.val() if hasattr(solid, "val") else solid
    verts, tris = shape.tessellate(TESS_TOLERANCE)
    bb = shape.BoundingBox()
    dx, dy, dz = -(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin
    return [(v.x + dx, v.y + dy, v.z + dz) for v in verts], tris


def _footprint(solid):
    bb = (solid.val() if hasattr(solid, "val") else solid).BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


# --------------------------------------------------------------------- layout --
def layout(items, bed=None, spacing=None):
    """Shelf-pack by footprint. Returns [(name, solid, brim, x, y)].

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
    height = y + row_h + margin
    return placed, height


# ----------------------------------------------------------------- 3mf writing --
def _uuid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"nook-{seed}"))


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


def _root_model(entries):
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
        ("Title", "Diagon Alley book nook"), ("Designer", ""), ("Description", "")))
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
    """Per-object settings. OVERRIDES ONLY -- see the module docstring and ingest.py."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for e in entries:
        out.append(f'  <object id="{e["wrap_id"]}">')
        out.append(f'    <metadata key="name" value="{e["name"]}"/>')
        for k, v in e["settings"].items():
            out.append(f'    <metadata key="{k}" value="{v}"/>')
        out.append(f'    <part id="{e["mesh_id"]}" subtype="{ingest.PART_SUBTYPE_NORMAL}">')
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
    for i, (name, solid, brim) in enumerate(
            [(n, s, b) for n, s, b in items], start=1):
        pl = placed[i - 1]
        settings = {}
        if brim is False:
            # B4: a brim floods the gaps inside a sprue and tears the pins off on
            # removal. brim_width 0 rather than a brim_type enum, because "outer_only"
            # is a spelling we have READ in a real file and "no_brim" is one we have not.
            settings["brim_width"] = "0"
        entries.append(dict(name=name, mesh_id=i, wrap_id=1000 + i,
                            x=pl[3], y=pl[4], settings=settings, solid=solid))
    return entries


def write(items, path):
    entries = build_entries(items)
    profile = dict(ingest.json.load(open(P.PROFILE_PATH, encoding="utf8")))
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
        z.writestr("3D/3dmodel.model", _root_model(entries))
        z.writestr("Metadata/project_settings.config",
                   ingest.json.dumps(profile, indent=4))
        z.writestr("Metadata/model_settings.config", _model_settings(entries))
        z.writestr("Metadata/slice_info.config", SLICE_INFO)
    return entries


# ==================================================================== self-test ==
def self_test(path):
    """Read our own output back with ingest.py. A writer that cannot be read is a guess."""
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

    prof = ingest.json.loads(z.read("Metadata/project_settings.config").decode("utf8"))
    t("plate brim overridden off Auto", prof.get("brim_type") == "outer_only",
      f"brim_type={prof.get('brim_type')}")

    ms = z.read("Metadata/model_settings.config").decode("utf8")
    import xml.etree.ElementTree as ET
    cfg = ET.fromstring(ms)
    wrap_ids = {o.get("id") for o in cfg.findall("object")}
    built = set()
    for line in root.splitlines():
        if "<item objectid=" in line:
            built.add(line.split('objectid="')[1].split('"')[0])
    t("every build item has settings, and vice versa", wrap_ids == built,
      f"settings {sorted(wrap_ids)} vs build {sorted(built)}")

    sprues = [o for o in cfg.findall("object")
              if any(m.get("key") == "name" and "sprue" in (m.get("value") or "")
                     for m in o.findall("metadata"))]
    t("both sprue orientations are on the plate", len(sprues) == 2,
      f"{len(sprues)} found -- horizontal and vertical settle R-14 against each other")
    # Only the HORIZONTAL sprue needs the brim suppressed: its pins lie in 7 mm channels
    # a brim would flood. The vertical one stands on a solid base and wants its brim.
    flat_sprue = [o for o in sprues
                  if any(m.get("key") == "name" and m.get("value") == "02_pin_sprue"
                         for m in o.findall("metadata"))]
    if flat_sprue:
        keys = {m.get("key"): m.get("value") for m in flat_sprue[0].findall("metadata")}
        t("the LYING sprue overrides its brim to zero", keys.get("brim_width") == "0",
          "B4: a brim floods a lying sprue's gaps and tears the pins off")

    # Overrides only -- an object carrying dozens of keys means we wrote a whole config.
    worst = max((len([m for m in o.findall("metadata")]) for o in cfg.findall("object")),
                default=0)
    t("settings are OVERRIDES, not full configs", worst <= 4, f"{worst} keys on one object")
    return out


def coupon_items():
    import coupon
    return coupon.parts()


if __name__ == "__main__":
    items = coupon_items()
    placed, height = layout(items)
    bed = float(P.BED_X)
    print("plate -- Bambu project writer\n")
    print(f"  {len(items)} objects, spacing {float(P.PLATE_SPACING):.0f} mm "
          f"(2 x brim + 1)")
    print(f"  layout {height:.0f} mm deep on a {bed:.0f} mm bed"
          f"{'  -- OVERFLOWS' if height > bed else ''}\n")

    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "plate_1_coupon.3mf")
    write(items, path)

    bad = 0
    for ok, name, detail in self_test(path):
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))
        bad += not ok

    if "--write" not in sys.argv:
        os.remove(path)
        print(f"\n  {bad} failures  (pass --write to keep the file)")
    else:
        print(f"\n  {bad} failures")
        print(f"  wrote {path}  ({os.path.getsize(path) / 1024:.0f} kB)")

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(1 if bad else 0)
