#!/usr/bin/env python3
"""Write each plate as a 3MF project instead of a single fused STL.

    python3 mf3.py            # after plates.py

Two things this buys over the STL plates:

  * Each part is a separate OBJECT. The STL plates are one fused mesh, so the slicer
    sees a single blob per plate: you cannot select a part, cannot arrange, and cannot
    set anything per part. In a 3MF the 64 parts of the left facade arrive as 64
    objects on the plate, already positioned.
  * The parts that need a brim say so, per object, in the Bambu/Orca settings block.
    The slicer's Auto brim looked at a 15.4 mm^2 plaque and a 27 x 2.6 mm sill and gave
    neither one; both came off the plate as spaghetti.

The geometry half is plain 3MF core spec and will open anywhere. The per-object brim
setting is written into Metadata/model_settings.config, which is Bambu Studio's and
Orca's own extension -- if a slicer ignores that file you still get the objects laid
out correctly and can set the brim by hand, so nothing is lost either way.
"""
import json
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import struct

import build as B
import plates as PL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MF3 = os.path.join(OUT, "3mf")

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


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


def model_xml(objects):
    """objects: list of (name, verts, tris, (dx, dy, dz))."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           '<metadata name="Application">Crooked Lane Book Nook</metadata>',
           '<resources>']
    for i, (name, verts, tris, _) in enumerate(objects, start=1):
        out.append(f'<object id="{i}" type="model" name="{escape(name)}"><mesh><vertices>')
        out += ['<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in verts]
        out.append('</vertices><triangles>')
        out += ['<triangle v1="%d" v2="%d" v3="%d"/>' % t for t in tris]
        out.append('</triangles></mesh></object>')
    out.append('</resources><build>')
    for i, (_, _, _, (dx, dy, dz)) in enumerate(objects, start=1):
        out.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.4f %.4f %.4f"/>'
                   % (i, dx, dy, dz))
    out.append('</build></model>')
    return "\n".join(out)


def settings_xml(objects, brim):
    """Bambu Studio / Orca per-object settings."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
    for i, (name, _, _, _) in enumerate(objects, start=1):
        out.append(f'  <object id="{i}">')
        out.append(f'    <metadata key="name" value="{escape(name)}"/>')
        if name in brim:
            out.append('    <metadata key="brim_type" value="outer_only"/>')
            out.append('    <metadata key="brim_width" value="5"/>')
        out.append('  </object>')
    out.append('</config>')
    return "\n".join(out)


def main():
    os.makedirs(MF3, exist_ok=True)
    for f in os.listdir(MF3):
        if f.endswith(".3mf"):
            os.remove(os.path.join(MF3, f))

    grams, brim_ids = {}, set()
    mpath = os.path.join(OUT, "manifest.json")
    if os.path.exists(mpath):
        for r in json.load(open(mpath)):
            grams[r["id"]] = r.get("grams", 0.0)
            if r.get("bed", 99) < 25.0 or (
                    r.get("overhang", 0) > 50.0
                    and r["overhang"] > 4.0 * max(r.get("bed", 0.1), 0.1)):
                brim_ids.add(r["id"])

    rows = {r["id"]: r for r in json.load(open(mpath))} if os.path.exists(mpath) else {}
    if not rows:
        raise SystemExit("run build.py first -- this reads out/stl and out/manifest.json")
    group = {m["id"]: m["group"] for m in B.manifest()}
    print("reading meshes ...")
    built = {}
    for pid, r in rows.items():
        path = os.path.join(OUT, "stl", r["file"])
        if r.get("status") != "ok" or not os.path.exists(path):
            continue
        w, d, _ = r["bbox"]
        built[pid] = dict(id=pid, name=f"{pid}_{r['name']}", path=path,
                          group=group.get(pid, ""), w=w, d=d)

    n = 0
    already = set()
    for label, groups, ids in PL.PLATE_GROUPS:
        chosen = [b for b in built.values()
                  if b["id"] not in already
                  and ((ids is not None and b["id"] in ids)
                       or (groups is not None
                           and b["group"] in groups))]
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
            suffix = "" if part_no == 1 else f"_{part_no}"
            objs, brim = [], set()
            for it, x, y in placed:
                verts, tris = mesh_of_stl(it["path"])
                objs.append((it["name"], verts, tris, (x, y, 0.0)))
                if it["id"] in brim_ids:
                    brim.add(it["name"])
            path = os.path.join(MF3, f"{label}{suffix}.3mf")
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("[Content_Types].xml", CONTENT_TYPES)
                z.writestr("_rels/.rels", RELS)
                z.writestr("3D/3dmodel.model", model_xml(objs))
                z.writestr("Metadata/model_settings.config",
                           settings_xml(objs, brim))
            g = sum(grams.get(it["id"], 0.0) for it, _, _ in placed)
            print(f"  {label + suffix:<22} {len(objs):3d} objects  {g:6.0f} g   "
                  f"{len(brim)} with a brim   {os.path.getsize(path)/1024:6.0f} kB")
            n += 1
    print(f"\n{n} plates -> {MF3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
