#!/usr/bin/env python3
"""Write each plate as a Bambu Studio project (.3mf), sliced-ready for a P2S.

    python3 mf3.py            # after build.py and plates.py

Three things this buys over the STL plates:

  * Each part is a separate OBJECT. The STL plates are one fused mesh, so the slicer
    sees a single blob per plate: you cannot select a part, cannot arrange, and cannot
    set anything per part. In a 3MF the 64 parts of the left facade arrive as 64
    objects on the plate, already positioned.
  * The parts that need a brim CARRY one. Not a suffix in the name asking you to add it
    by hand -- `brim_type = outer_only` on the object, which is where Bambu keeps a
    per-object brim. The slicer's own Auto brim looked at a 15 mm^2 plaque and a 3 mm
    wide window sill and gave neither one; both came off the plate as spaghetti.
  * The print profile comes with it: 0.4 nozzle, 0.20 mm layers, PLA, textured plate,
    and the bed temperature the big flat parts want.

WHY THE FORMAT IS THIS SHAPE
----------------------------
The first version of this wrote plain 3MF core spec plus one Metadata/model_settings
block carrying brim_type. Bambu Studio answered "The 3mf file has invalid config, load
geometry data only" and dropped the settings on the floor -- brims silently not applied.
That dialog does not mean "your settings are wrong"; it means "this is not a Bambu
project, so there is nothing to load". A Bambu project is a specific package:

  [Content_Types].xml            png and gcode Defaults as well as rels and model
  _rels/.rels                    -> /3D/3dmodel.model
  3D/3dmodel.model               the production extension: no meshes, only WRAPPER
                                 objects, each a <component> pointing at a part file
  3D/_rels/3dmodel.model.rels    -> every part file
  3D/Objects/object_N.model      one mesh per file, ending <build/>
  Metadata/model_settings.config per-object name, brim, extruder, <part>, mesh_stat,
                                 then <plate> and <assemble>
  Metadata/project_settings.config   the 582-key print/filament/printer profile
  Metadata/slice_info.config     client version header

Object ids interleave: part N is mesh object 2N-1 inside object_N.model, wrapped by
object 2N in 3dmodel.model, and it is the WRAPPER id that model_settings and the build
items refer to. Getting that wrong is the difference between a project and a dialog.

The profile in profiles/P2S_project_settings.config is a real P2S profile exported from
Bambu Studio, vendored so the plates carry it. OVERRIDES below is the short list of
things this kit changes about it, applied at write time so the deviations stay greppable
instead of buried in 82 kB of JSON.

If you do not have a P2S, do not fight the profile -- load the STL plates from out/plates
instead and set your own. docs/05_PRINT_SETTINGS.md is the list of what these files bake
in, so you can reproduce it by hand on any printer.
"""
import datetime as _dt
import hashlib
import json
import os
import struct
import sys
import zipfile
from xml.sax.saxutils import escape, quoteattr

import build as B
import params as P
import plates as PL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MF3 = os.path.join(OUT, "3mf")
PROFILE = os.path.join(HERE, "profiles", "P2S_project_settings.config")

# The Bambu Studio these files claim to have been written by. It has to be a real
# version string: the importer parses the part after "BambuStudio-" as a semver and
# compares it against the running application. This is the version the vendored
# profile was exported from -- keep the two together.
BAMBU_VERSION = "02.08.02.61"
BED_X, BED_Y = P.BED_X, P.BED_Y
TODAY = _dt.date.today().isoformat()

# The filament slot every part is assigned to. Slot 6 in the vendored profile is
# "Bambu PLA Basic @BBL P2S - Large Flats", which differs from stock PLA in exactly one
# respect: the bed runs 65 C on the first layer and 60 C after, instead of 55/55. The
# big flat parts -- wall faces, base pan, case sides -- lift at 55. Using one slot for
# everything means no tool changes and no purge tower; the small parts do not mind the
# warmer bed. Remap it in the Filament panel if your AMS is loaded differently.
FILAMENT_SLOT = 6

# What this kit pins in the vendored profile. Each entry is (key, value, why). Two of
# the three already match the profile as exported -- they are pinned so that re-exporting
# it from a later Bambu Studio cannot quietly change them under the plates.
OVERRIDES = [
    ("reduce_crossing_wall", "1",
     "CHANGED. Avoid crossing walls -- the window interiors came out webbed with "
     "strings, and every one of them was a travel move straight across the opening"),
    ("brim_type", "outer_only",
     "CHANGED. The PLATE default, belt to the per-object braces below. Auto is what "
     "gave 19C and 13As no brim and let them come off the plate. Set here as well as "
     "on the objects because the object setting is invisible until you select the "
     "object, and because a plate that reads Auto in the Global tab is indistinguishable "
     "from a plate whose settings did not load at all"),
    ("brim_width", "5",
     "pinned. 5 mm holds the 15 mm^2 plaques down and still peels off"),
    ("slow_down_layer_time", "8",
     "CHANGED. Every object on every plate is assigned to filament slot 6, and slot 6 "
     "inherits Bambu PLA Basic, whose minimum layer time is 4 s where Generic PLA's is "
     "8. That is the right number for the large flat parts the slot is named after and "
     "the wrong one for a plate of 5 mm parts, which then never cool between layers"),
    ("nozzle_temperature", "210",
     "CHANGED. 220 is Bambu's Generic PLA default and is hot for most PLA. Five of the "
     "eleven parts on the trial plate had to be abandoned mid-print for stringing; "
     "temperature is the biggest lever left after avoid-crossing-walls, and PLA's range "
     "here is 190-240"),
    ("nozzle_temperature_initial_layer", "220",
     "pinned at 220 while the rest drops to 210 -- the first layer wants the heat for "
     "adhesion, and there is nothing above it yet to string to"),
]

BRIM_SUFFIX = " [brim]"
BRIM_WIDTH = "5"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""

SLICE_INFO = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-BBL-Client-Type" value="slicer"/>
    <header_item key="X-BBL-Client-Version" value="%s"/>
  </header>
</config>
""" % BAMBU_VERSION

MODEL_NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
            'requiredextensions="p"')


def uid(*parts):
    """A stable UUID for these parts, so rebuilding a plate does not churn the file."""
    h = hashlib.md5("/".join(str(p) for p in parts).encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def mesh_of_stl(path):
    """Read a binary STL back into (vertices, triangles), welding coincident points.

    Reading the meshes that build.py already exported, rather than re-tessellating the
    CAD, is not just faster -- it guarantees the 3MF and the STL of a part are the same
    mesh. Re-deriving it invited them to drift. (It is also the difference between two
    seconds and the hour of CPU the first version of this was still burning when it was
    killed.)
    """
    with open(path, "rb") as f:
        n = struct.unpack("<I", f.read(84)[80:84])[0]
        data = f.read(n * 50)
    verts, index, tris = [], {}, []
    for i in range(n):
        off = i * 50 + 12
        tri = []
        for k in range(3):
            x, y, z = struct.unpack_from("<3f", data, off + k * 12)
            key = (round(x, 4), round(y, 4), round(z, 4))
            j = index.get(key)
            if j is None:
                j = len(verts)
                index[key] = j
                verts.append(key)
            tri.append(j)
        if len(set(tri)) == 3:
            tris.append(tuple(tri))
    return verts, tris


def object_model(idx, name, verts, tris):
    """3D/Objects/object_{idx}.model -- one mesh, id 2*idx-1."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<model unit="millimeter" xml:lang="en-US" {MODEL_NS}>',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
           ' <resources>',
           f'  <object id="{2 * idx - 1}" p:UUID="{uid("mesh", idx, name)}" type="model">',
           '   <mesh>',
           '    <vertices>']
    out += ['     <vertex x="%.6f" y="%.6f" z="%.6f"/>' % v for v in verts]
    out += ['    </vertices>', '    <triangles>']
    out += ['     <triangle v1="%d" v2="%d" v3="%d"/>' % t for t in tris]
    out += ['    </triangles>', '   </mesh>', '  </object>', ' </resources>',
            ' <build/>', '</model>']
    return "\n".join(out)


def root_model(label, objs):
    """3D/3dmodel.model -- wrapper objects only, plus the build items that place them."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<model unit="millimeter" xml:lang="en-US" {MODEL_NS}>',
           # THE Application TAG IS LOAD-BEARING. Bambu's importer sets its
           # m_is_bbl_3mf flag in exactly one place -- _handle_end_metadata in
           # src/libslic3r/Format/bbs_3mf.cpp -- and the test is
           # boost::starts_with(value, "BambuStudio-"). Nothing else sets it. With that
           # flag false the file is an "other vendor" 3MF: the model config is not
           # required to parse, objects get split by instance, and a single object is
           # renamed after the file. This said "Crooked Lane Book Nook" and the settings
           # did not take. The name of this kit lives in Title and Designer, below,
           # which is where Bambu puts a project's own name.
           f' <metadata name="Application">BambuStudio-{BAMBU_VERSION}</metadata>',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
           ' <metadata name="Title">Crooked Lane Book Nook</metadata>',
           ' <metadata name="Designer">Crooked Lane Book Nook</metadata>',
           f' <metadata name="Description">{escape(label)}</metadata>',
           ' <metadata name="Copyright"></metadata>',
           ' <metadata name="License"></metadata>',
           ' <metadata name="Origin"></metadata>',
           f' <metadata name="CreationDate">{TODAY}</metadata>',
           f' <metadata name="ModificationDate">{TODAY}</metadata>',
           ' <resources>']
    for i, o in enumerate(objs, start=1):
        out += [f'  <object id="{2 * i}" p:UUID="{uid("wrap", i, o["name"])}" type="model">',
                '   <components>',
                f'    <component p:path="/3D/Objects/object_{i}.model" objectid="{2 * i - 1}"'
                f' p:UUID="{uid("comp", i, o["name"])}"'
                ' transform="1 0 0 0 1 0 0 0 1 0 0 0"/>',
                '   </components>', '  </object>']
    out.append(' </resources>')
    out.append(f' <build p:UUID="{uid("build", *(o["name"] for o in objs))}">')
    for i, o in enumerate(objs, start=1):
        x, y, z = o["pos"]
        out.append(f'  <item objectid="{2 * i}" p:UUID="{uid("item", i, o["name"])}"'
                   ' transform="1 0 0 0 1 0 0 0 1 %.6f %.6f %.6f" printable="1"/>' % (x, y, z))
    out += [' </build>', '</model>']
    return "\n".join(out)


def model_settings(label, objs):
    """Metadata/model_settings.config -- per-object brim and extruder, plate, assemble."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
    for i, o in enumerate(objs, start=1):
        nm = quoteattr(o["name"])
        n = len(o["tris"])
        out.append(f'  <object id="{2 * i}">')
        out.append(f'    <metadata key="name" value={nm}/>')
        if o["brim"]:
            out.append('    <metadata key="brim_type" value="outer_only"/>')
            out.append(f'    <metadata key="brim_width" value="{BRIM_WIDTH}"/>')
        out.append(f'    <metadata key="extruder" value="{FILAMENT_SLOT}"/>')
        out.append(f'    <metadata face_count="{n}"/>')
        out.append(f'    <part id="{2 * i - 1}" subtype="normal_part"'
                   f' uuid="{uid("part", i, o["name"])}">')
        out.append(f'      <metadata key="name" value={nm}/>')
        out.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>')
        out.append(f'      <metadata key="source_file" value={quoteattr(label + ".3mf")}/>')
        out.append(f'      <metadata key="source_object_id" value="{i - 1}"/>')
        out.append('      <metadata key="source_volume_id" value="0"/>')
        for ax in "xyz":
            out.append(f'      <metadata key="source_offset_{ax}" value="0"/>')
        out.append(f'      <mesh_stat face_count="{n}" edges_fixed="0" degenerate_facets="0"'
                   ' facets_removed="0" facets_reversed="0" backwards_edges="0"/>')
        out.append('    </part>')
        out.append('  </object>')
    out += ['  <plate>',
            '    <metadata key="plater_id" value="1"/>',
            '    <metadata key="plater_name" value=""/>',
            '    <metadata key="locked" value="false"/>',
            '    <metadata key="filament_map_mode" value="Auto For Flush"/>']
    for i, o in enumerate(objs, start=1):
        out += ['    <model_instance>',
                f'      <metadata key="object_id" value="{2 * i}"/>',
                '      <metadata key="instance_id" value="0"/>',
                f'      <metadata key="identify_id" value="{201 + 22 * (i - 1)}"/>',
                '    </model_instance>']
    out.append('  </plate>')
    out.append('  <assemble>')
    for i, o in enumerate(objs, start=1):
        x, y, z = o["pos"]
        out.append(f'   <assemble_item object_id="{2 * i}" instance_id="0"'
                   ' transform="1 0 0 0 1 0 0 0 1 %.6f %.6f %.6f" offset="0 0 0" />' % (x, y, z))
    out += ['  </assemble>', '</config>']
    return "\n".join(out)


def _apply_overrides(cfg):
    """Apply OVERRIDES in place.

    Bambu keeps the per-filament and per-extruder settings as arrays, one entry per
    slot, and the arrays are not all the same length -- nozzle_temperature has 21
    entries where slow_down_layer_time has 7. An override on one of those means every
    slot, so fill the array that is already there rather than replacing it with a
    scalar and changing its shape.
    """
    for key, value, _why in OVERRIDES:
        cur = cfg.get(key)
        cfg[key] = [value] * len(cur) if isinstance(cur, list) else value


def project_settings():
    """The vendored P2S profile with this kit's OVERRIDES applied."""
    with open(PROFILE) as f:
        cfg = json.load(f)
    _apply_overrides(cfg)
    return json.dumps(cfg, indent=4, sort_keys=True)


def write_project(path, label, objs, settings):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", root_model(label, objs))
        rels = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(1, len(objs) + 1):
            rels.append(f' <Relationship Target="/3D/Objects/object_{i}.model" Id="rel-{i}"'
                        ' Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
        rels.append('</Relationships>')
        z.writestr("3D/_rels/3dmodel.model.rels", "\n".join(rels))
        for i, o in enumerate(objs, start=1):
            z.writestr(f"3D/Objects/object_{i}.model",
                       object_model(i, o["name"], o["verts"], o["tris"]))
        z.writestr("Metadata/model_settings.config", model_settings(label, objs))
        z.writestr("Metadata/project_settings.config", settings)
        z.writestr("Metadata/slice_info.config", SLICE_INFO)
    faults = check_project(path)
    if faults:
        raise SystemExit(f"{os.path.basename(path)} is not a valid project:\n  "
                         + "\n  ".join(faults))


NS = {"c": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
      "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}


def check_project(path):
    """Re-open a written project and prove it hangs together. Returns a list of faults.

    Bambu Studio's answer to a project it does not like is one dialog -- "invalid config,
    load geometry data only" -- with no indication of which part it choked on, and it
    then prints the plate with the settings silently missing. Nothing here can drive
    Bambu, so this checks the invariants that dialog is about instead: every wrapper is
    built, referred to by model_settings and instanced on the plate; every component
    resolves to a part file holding exactly the mesh id it names; every mesh_stat matches
    the triangles actually written; the profile is still a P2S profile.
    """
    import xml.etree.ElementTree as ET
    faults = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for req in ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model",
                    "3D/_rels/3dmodel.model.rels", "Metadata/model_settings.config",
                    "Metadata/project_settings.config", "Metadata/slice_info.config"):
            if req not in names:
                faults.append(f"missing {req}")
        if faults:
            return faults
        root = ET.fromstring(z.read("3D/3dmodel.model"))
        app = root.find('c:metadata[@name="Application"]', NS)
        if app is None or not (app.text or "").startswith("BambuStudio-"):
            # The single flag that decides whether Bambu treats this as a project at all.
            faults.append("the Application metadata does not start with BambuStudio- , "
                          "so the settings will not load")
        wrappers = [o.get("id") for o in root.findall("c:resources/c:object", NS)]
        items = [i.get("objectid") for i in root.findall("c:build/c:item", NS)]
        cfg = ET.fromstring(z.read("Metadata/model_settings.config"))
        settings = [o.get("id") for o in cfg.findall("object")]
        plated = [m.find("metadata").get("value")
                  for m in cfg.findall("plate/model_instance")]
        if sorted(items) != sorted(wrappers):
            faults.append("build items do not match the wrapper objects")
        if sorted(settings) != sorted(wrappers):
            faults.append("model_settings objects do not match the wrapper objects")
        if sorted(plated) != sorted(wrappers):
            faults.append("plate instances do not match the wrapper objects")
        comps = {}
        for o in root.findall("c:resources/c:object", NS):
            for c in o.findall("c:components/c:component", NS):
                sub = c.get("{%s}path" % NS["p"]).lstrip("/")
                comps[o.get("id")] = sub
                if sub not in names:
                    faults.append(f"component points at {sub}, which is not in the package")
                    continue
                m = ET.fromstring(z.read(sub))
                ids = [x.get("id") for x in m.findall("c:resources/c:object", NS)]
                if ids != [c.get("objectid")]:
                    faults.append(f"{sub} holds {ids}, not {c.get('objectid')}")
                    continue
                tris = len(m.findall(".//c:triangle", NS))
                mine = [x for x in cfg.findall("object") if x.get("id") == o.get("id")]
                stat = mine[0].find("part/mesh_stat") if mine else None
                if stat is None or int(stat.get("face_count")) != tris:
                    faults.append(f"{sub}: mesh_stat disagrees with {tris} triangles")
        # Every part must land on the bed. The transform is applied to mesh coordinates,
        # so a part whose mesh is centred on the origin -- which all of these are --
        # lands half a width away from where the packer meant unless its own minimum is
        # subtracted first. That shipped once: parts over the edge of the plate.
        for item in root.findall("c:build/c:item", NS):
            t = [float(v) for v in item.get("transform").split()]
            sub = comps.get(item.get("objectid"))
            if sub is None:
                continue
            m = ET.fromstring(z.read(sub))
            xs = [float(v.get("x")) + t[9] for v in m.findall(".//c:vertex", NS)]
            ys = [float(v.get("y")) + t[10] for v in m.findall(".//c:vertex", NS)]
            zs = [float(v.get("z")) + t[11] for v in m.findall(".//c:vertex", NS)]
            if not xs:
                continue
            if min(xs) < 0 or min(ys) < 0 or max(xs) > BED_X or max(ys) > BED_Y:
                faults.append("an object sits at x %.1f..%.1f y %.1f..%.1f, off a "
                              "%.0f x %.0f bed" % (min(xs), max(xs), min(ys), max(ys),
                                                   BED_X, BED_Y))
                break
            if min(zs) < -0.001:
                faults.append("an object sits %.2f mm below the plate" % min(zs))
                break
        prof = json.loads(z.read("Metadata/project_settings.config"))
        for key, value, _why in OVERRIDES:
            got = prof.get(key)
            ok = all(v == value for v in got) if isinstance(got, list) else got == value
            if not ok:
                faults.append(f"{key} is {got!r}, not {value!r}")
        if prof.get("printer_model") != "Bambu Lab P2S":
            faults.append("the profile is not a P2S profile")
    return faults


def make_objs(placed, brim_ids):
    """Turn shelf_pack's (item, x, y) into placed objects.

    x and y are where the part's bounding box should START, which is what plates.py
    means by them: it normalises each solid with translate((-bb.xmin, -bb.ymin, 0))
    before moving it to (x, y). The exported STLs are centred on X and Y, so using
    x and y directly as the item transform put each part's CENTRE at its corner --
    every part half a width down and left of where it belonged, and the ones at the
    end of a shelf hanging over the edge of the plate. Subtract the mesh's own
    minimum, exactly as plates.py does.
    """
    objs = []
    for it, x, y in placed:
        verts, tris = mesh_of_stl(it["path"])
        lo_x = min(v[0] for v in verts)
        lo_y = min(v[1] for v in verts)
        lo_z = min(v[2] for v in verts)
        brim = it["id"] in brim_ids
        objs.append(dict(name=it["name"] + (BRIM_SUFFIX if brim else ""),
                         verts=verts, tris=tris, brim=brim,
                         pos=(x - lo_x, y - lo_y, -lo_z)))
    return objs


DOCS = os.path.join(HERE, "docs")
SETTINGS_DOC = os.path.join(DOCS, "05_PRINT_SETTINGS.md")


def write_settings_doc(plated, brim_ids, rows):
    """docs/05_PRINT_SETTINGS.md -- what the projects bake in, for people without a P2S.

    Generated rather than written by hand for the same reason the checklist is: the brim
    list runs to dozens of entries and moves whenever a part is re-oriented, and a
    settings page that disagrees with the files it documents is worse than none.
    """
    with open(PROFILE) as f:
        p = json.load(f)
    _apply_overrides(p)

    def first(key):
        v = p.get(key)
        return v[0] if isinstance(v, list) and v else v

    slot = FILAMENT_SLOT - 1
    def s(key, i=slot):
        v = p.get(key)
        return v[i] if isinstance(v, list) and len(v) > i else v

    L = []
    w = L.append
    w("# 05 -- Print settings")
    w("")
    w("The projects in `out/3mf` are Bambu Studio projects for a **Bambu Lab P2S with a")
    w("0.4 mm nozzle**. Open one and everything on this page is already set, including a")
    w("brim on each of the parts that needs one. Nothing below needs doing by hand.")
    w("")
    w("This page is for everybody else. The STL plates in `out/plates` are geometry and")
    w("nothing else; these are the settings that go with them. None of it is exotic --")
    w("the only unusual entries are the brim list and *avoid crossing walls*, and both")
    w("are here because a plate came off the bed wrong without them.")
    w("")
    w("It is generated by `mf3.py` from the same profile the projects carry, so it")
    w("cannot drift from them. Do not edit it by hand.")
    w("")
    w("The brim is set in two places on purpose: `brim_type = outer_only` as the plate")
    w("default, and again on each of the parts below. Either one alone would do it if")
    w("everything loads; both, and the plate still has brims if the per-object settings")
    w("are ever dropped.")
    w("")
    w("## The five that matter")
    w("")
    w("| | Setting | Why |")
    w("|---|---|---|")
    w("| 1 | **An outer brim, 5 mm, on the %d parts listed below** | Auto brim looks at "
      "a 6 mm^2 keystone, decides it is fine, and it comes off as spaghetti |"
      % len(brim_ids))
    w("| 2 | **Avoid crossing walls** | The window interiors came out webbed with "
      "strings; every one was a travel move across the opening |")
    w("| 3 | **Bed %s C first layer, %s C after** | The wall faces and the base pan are "
      "big flat parts and they lift at 55 |" % (s("hot_plate_temp_initial_layer"),
                                                s("hot_plate_temp")))
    w("| 4 | **Do not re-orient anything** | Every part is exported already lying the way "
      "it should print. `orient.py` chose these; see the note at the bottom |")
    w("| 5 | **No supports** | Nothing in the kit needs them in its print orientation. If "
      "your slicer wants to add some, the part is the wrong way up |")
    w(f"| 6 | **Nozzle {s('nozzle_temperature')} C, minimum layer time {s('slow_down_layer_time')} s** | "
      "Five of eleven parts on the first trial plate were abandoned mid-print for "
      "stringing. 220 C and a 4 s minimum layer time is a profile tuned for large flat "
      "parts, applied to 5 mm ones |")
    w("")
    w("## Process")
    w("")
    w("| Setting | Value |")
    w("|---|---|")
    for label, key in (("Nozzle", "nozzle_diameter"),
                       ("Layer height", "layer_height"),
                       ("First layer height", "initial_layer_print_height"),
                       ("Wall loops", "wall_loops"),
                       ("Top / bottom shells", None),
                       ("Sparse infill", None),
                       ("Wall generator", "wall_generator"),
                       ("Seam position", "seam_position"),
                       ("Elephant foot compensation", "elefant_foot_compensation"),
                       ("Print sequence", "print_sequence")):
        if label == "Top / bottom shells":
            v = f"{p['top_shell_layers']} / {p['bottom_shell_layers']}"
        elif label == "Sparse infill":
            v = f"{p['sparse_infill_density']} {p['sparse_infill_pattern']}"
        else:
            v = first(key)
        w(f"| {label} | {v} |")
    w("")
    w("The profile is Bambu's own `%s` with the changes below. Anything not listed here"
      % p.get("print_settings_id"))
    w("is stock and does not matter to this model -- match your own slicer's PLA")
    w("defaults and you will be fine.")
    w("")
    w("## Filament")
    w("")
    w("| Setting | Value |")
    w("|---|---|")
    w(f"| Material | {s('filament_type')} |")
    w(f"| Nozzle | {s('nozzle_temperature_initial_layer')} C first layer, "
      f"{s('nozzle_temperature')} C after |")
    w(f"| Bed (textured PEI) | {s('textured_plate_temp_initial_layer')} C first layer, "
      f"{s('textured_plate_temp')} C after |")
    w(f"| Plate type | {p.get('curr_bed_type')} |")
    w(f"| Flow ratio | {s('filament_flow_ratio')} |")
    w(f"| Minimum layer time | {s('slow_down_layer_time')} s "
      f"(floor speed {s('slow_down_min_speed')} mm/s) |")
    w(f"| Part cooling fan | {s('fan_min_speed')}-{s('fan_max_speed')}%, "
      f"off for the first {s('close_fan_the_first_x_layers')} layer(s) |")
    w("")
    w("**The bed temperature is the one deliberate departure from stock PLA.** Bambu's")
    w("`Generic PLA @BBL P2S` runs the bed at 55 C throughout. The parts here that fail")
    w("are the big flat ones -- the wall faces are 240 x 100 mm and 2.5 mm thick, the")
    w("base pan is nearly the whole bed -- and at 55 C the corners lift. The projects")
    w(f"carry a `{s('filament_settings_id')}` profile which is stock PLA with the bed at")
    w(f"{s('textured_plate_temp_initial_layer')}/{s('textured_plate_temp')} C, and every")
    w(f"object on every plate is assigned to **filament slot {FILAMENT_SLOT}**, which is")
    w("that profile. One slot for everything means no tool changes and no purge tower;")
    w("the small parts do not mind the warmer bed.")
    w("")
    w("If your AMS is loaded differently, remap the slot in the Filament panel -- the")
    w("assignment is a slot number, not a colour. If you are on a printer without an AMS,")
    w("ignore the slot entirely and just raise the bed.")
    w("")
    w("## Adhesion")
    w("")
    w("| Setting | Value |")
    w("|---|---|")
    w(f"| Plate default brim | {p.get('brim_type')} |")
    w(f"| Brim width | {p.get('brim_width')} mm |")
    w(f"| Brim-object gap | {p.get('brim_object_gap')} mm |")
    w(f"| Skirt loops | {p.get('skirt_loops')} |")
    w("| Per-object brim | `outer_only`, on the parts listed below |")
    w("")
    small = min((rows[i] for i in brim_ids if i in rows), key=lambda r: r.get("bed", 0.0))
    failed = [rows[i] for i in ("19C", "13As") if i in rows]
    w("Outer brim, not Auto, and not outer-and-inner. Auto is what failed. It gave no")
    w("brim to " + " or ".join("`%s_%s` (%.0f mm^2 on the bed)" % (r["id"], r["name"],
                                                                  r.get("bed", 0.0))
                               for r in failed) + ",")
    w("and both of those came off the plate mid-print. The smallest part on the list,")
    w("`%s_%s`, has %.0f mm^2 -- about a grain of rice."
      % (small["id"], small["name"], small.get("bed", 0.0)))
    w("")
    w("Inner brims are worse than useless here: they land inside the window openings,")
    w("where they are unreachable to pick out.")
    w("")
    w("A part is on the list if any of four things is true of it in its print")
    w("orientation, measured off the mesh by `build.needs_brim`:")
    w("")
    w(f"* its first layer is under **{B.SMALL_BASE:.0f} mm^2** -- too little grip, full stop;")
    w(f"* it is over **{B.TIPPY:.0f}x** as tall as its footprint is narrow -- it will be knocked over;")
    w(f"* it has over **{B.BRIM_OVERHANG:.0f} mm^2** hanging down and more than 4x as much")
    w("  overhang as bed -- the slicer calls this a floating cantilever, and the peeling")
    w("  force of the unsupported material exceeds what the footprint can hold;")
    w(f"* or it is over **{B.WIDE:.0f} mm** across and either under **{B.THIN:.0f} mm**")
    w(f"  tall or putting less than **{B.SPARSE * 100:.0f}%** of its own footprint on the")
    w("  bed. Adhesion area is not the problem for these -- the wall face has 31,000 mm^2")
    w("  on the bed. What lifts is the perimeter: a wide sheet shrinks as it cools and")
    w("  has no height behind its edge to resist curling, and a wide skeleton is the same")
    w("  thing in strips.")
    w("")
    w("### Parts that need a brim")
    w("")
    w(f"{len(brim_ids)} of {len(rows)} parts. If picking them out one by one is more "
      "trouble than")
    w("it is worth, set an outer brim on the whole plate instead: a 5 mm brim does the")
    w("other parts no harm beyond a little cleanup.")
    w("")
    w(f"Parts on a plate sit {PL.GAP:.0f} mm apart, which is two brims plus a millimetre,")
    w("so no two brims can touch. Do not close that up when you rearrange a plate --")
    w("brims that merge into one raft peel as one raft, and take every part on it.")
    w("")
    for name, objs in plated:
        mine = [o for o in objs if o["brim"]]
        if not mine:
            continue
        w(f"**{name}** -- {len(mine)} of {len(objs)}")
        w("")
        for o in sorted(mine, key=lambda o: o["name"]):
            pid = o["name"].split("_")[0]
            r = rows.get(pid, {})
            bb = r.get("bbox", [0, 0, 0])
            w(f"* `{o['name'].replace(BRIM_SUFFIX, '')}` -- "
              f"{r.get('bed', 0):.0f} mm^2 on the bed, "
              f"{bb[0]:.0f} x {bb[1]:.0f} x {bb[2]:.0f} mm")
        w("")
    w("## Stringing")
    w("")
    w("A window frame is a border and a grid of bars, so the nozzle crosses open air on")
    w("nearly every layer, and a plate of small parts adds a hop per part on top of that.")
    w("Three settings here are about that, and all three are departures from the stock")
    w("profile rather than defaults you would land on by accident:")
    w("")
    w("| Setting | Value | Stock |")
    w("|---|---|---|")
    w("| Avoid crossing walls | on | off |")
    w(f"| Nozzle temperature | {s('nozzle_temperature')} C "
      f"({s('nozzle_temperature_initial_layer')} C first layer) | 220 C throughout |")
    w(f"| Minimum layer time | {s('slow_down_layer_time')} s | 4 s on the Large Flats "
      "slot every part is assigned to |")
    w("")
    w("The minimum layer time is the one that is easy to get wrong. Assigning every part")
    w("to the warm-bed filament slot also gives every part that slot's cooling settings,")
    w("and a profile named for large flat parts lets layers come round again after 4")
    w("seconds. A wall face takes far longer than that anyway; a 5 mm corbel does not,")
    w("and goes back under the nozzle still soft.")
    w("")
    w("If strings persist: dry the filament first -- nothing in a settings file can fix")
    w("damp PLA -- then drop the nozzle another 5 C, then try 1.0 mm of retraction, then")
    w("split the plate. In that order.")
    w("")
    w("## Supports")
    w("")
    w(f"Off. `enable_support = {p.get('enable_support')}`.")
    w("")
    w("Every part is exported lying the way `orient.py` chose for it, and that choice")
    w("already accounts for overhangs -- it is what the choice is for. The one thing that")
    w("looks like it needs support and does not is the facade: parts such as")
    w("`11Ac_L_L2_Bay_Window_Corbel` and `19C_L_L_Wall_Plaque` sit pegs-up, so the")
    w("slicer sees small towers sticking into the air. Those are the P1 mounting pegs.")
    w("They are 2.5 x 2.0 x 3.5 mm, they print fine unsupported, and support material")
    w("around them would have to be picked out of the one feature on the part whose")
    w("dimensions have to be right.")
    w("")
    w("## Orientation")
    w("")
    w("**Do not let the slicer re-orient anything, and do not lay a part flat because it")
    w("looks unstable.** The orientation in the file is the answer to a search over the")
    w("24 axis-aligned placements of each part, scored on overhang area, footprint and")
    w("tippiness, with the facade parts pinned pegs-up so the peg faces are not printed")
    w("into a support interface. Re-orienting a part loses that and, on the facade, loses")
    w("the fit of the mount as well.")
    w("")
    w("Arranging is fine -- move parts around the bed as you like. Rotating about Z is")
    w("fine. Rotating about X or Y is not.")
    w("")
    w("## Not on a P2S")
    w("")
    w("Nothing in the geometry is P2S-specific. The bed is 256 x 256 mm and every plate")
    w("is packed to fit it; a smaller bed means splitting the bigger plates, which the")
    w("STL plates in `out/plates` do not do for you -- load the individual STLs from")
    w("`out/stl` instead and pack them yourself.")
    w("")
    w("On another Bambu machine, or in Orca: open the project and change the printer.")
    w("The per-object brims survive, because they are stored on the object rather than in")
    w("the printer profile.")
    w("")
    w("In PrusaSlicer or SuperSlicer: the project will not open with its settings. Load")
    w("the STL plates, set the table above, and use a per-object modifier for the brim")
    w("list (right-click an object -> Add settings -> Skirt and brim).")
    w("")
    w("In Cura: same, and note that Cura's *Combing mode: Not in Skin* is the nearest")
    w("thing to *avoid crossing walls*. Set brim per-object with a Per Model Setting.")
    w("")
    w("## What this kit changes about the stock profile")
    w("")
    w("| Setting | Value | Why |")
    w("|---|---|---|")
    for key, value, why in OVERRIDES:
        tag = "**changed**" if why.startswith("CHANGED") else "pinned"
        w(f"| `{key}` | `{value}` | {tag}. "
          f"{why.replace('CHANGED. ', '').replace('pinned. ', '')} |")
    w("")
    os.makedirs(DOCS, exist_ok=True)
    with open(SETTINGS_DOC, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"  settings -> docs/{os.path.basename(SETTINGS_DOC)}")


def main():
    if not os.path.exists(PROFILE):
        raise SystemExit(f"missing {PROFILE} -- the P2S profile the plates carry")
    os.makedirs(MF3, exist_ok=True)
    for f in os.listdir(MF3):
        if f.endswith(".3mf"):
            os.remove(os.path.join(MF3, f))

    mpath = os.path.join(OUT, "manifest.json")
    if not os.path.exists(mpath):
        raise SystemExit("run build.py first -- this reads out/stl and out/manifest.json")
    rows = {r["id"]: r for r in json.load(open(mpath))}
    grams = {r["id"]: r.get("grams", 0.0) for r in rows.values()}
    brim_ids = {r["id"] for r in rows.values() if B.needs_brim(r)}

    settings = project_settings()
    print("P2S profile: " + ", ".join(f"{k}={v}" for k, v, _ in OVERRIDES))
    print(f"filament slot {FILAMENT_SLOT}, {len(brim_ids)} of {len(rows)} parts with a brim\n")

    group = {m["id"]: m["group"] for m in B.manifest()}
    built = {}
    for pid, r in rows.items():
        path = os.path.join(OUT, "stl", r["file"])
        if r.get("status") != "ok" or not os.path.exists(path):
            continue
        w, d, _ = r["bbox"]
        built[pid] = dict(id=pid, name=f"{pid}_{r['name']}", path=path,
                          group=group.get(pid, ""), w=w, d=d)

    n = 0
    plated = []
    already = set()
    for label, groups, ids in PL.PLATE_GROUPS:
        chosen = [b for b in built.values()
                  if b["id"] not in already
                  and ((ids is not None and b["id"] in ids)
                       or (groups is not None and b["group"] in groups))]
        already.update(b["id"] for b in chosen)
        if not chosen:
            continue
        items = sorted(chosen, key=lambda b: b["id"])
        part_no = 0
        while items:
            placed, items = PL.shelf_pack(items)
            if not placed:
                break
            part_no += 1
            name = label + ("" if part_no == 1 else f"_{part_no}")
            objs = make_objs(placed, brim_ids)
            path = os.path.join(MF3, f"{name}.3mf")
            write_project(path, name, objs, settings)
            plated.append((name, objs))
            g = sum(grams.get(it["id"], 0.0) for it, _, _ in placed)
            nb = sum(1 for o in objs if o["brim"])
            print(f"  {name:<22} {len(objs):3d} objects  {g:6.0f} g   "
                  f"{nb} with a brim   {os.path.getsize(path)/1024:6.0f} kB")
            n += 1

    trial = [built[i] for i in PL.TRIAL_PLATE if i in built]
    if trial:
        placed, left = PL.shelf_pack(sorted(trial, key=lambda b: b["id"]))
        if placed and not left:
            objs = make_objs(placed, brim_ids)
            path = os.path.join(MF3, "TRIAL_first_fit.3mf")
            write_project(path, "TRIAL_first_fit", objs, settings)
            plated.append(("TRIAL_first_fit", objs))
            g = sum(grams.get(it["id"], 0.0) for it, _, _ in placed)
            nb = sum(1 for o in objs if o["brim"])
            print(f"  {'TRIAL_first_fit':<22} {len(objs):3d} objects  {g:6.0f} g   "
                  f"{nb} with a brim   {os.path.getsize(path)/1024:6.0f} kB")
            n += 1
        else:
            print("  !! the trial plate does not fit on one bed")

    print()
    write_settings_doc(plated, brim_ids, rows)
    print(f"\n{n} Bambu projects -> {MF3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
