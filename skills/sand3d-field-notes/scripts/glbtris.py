"""Where a GLB's triangles are: total, per material, per node, the biggest first; and what an optimised
file saved against another, when two are given.

    python -I glbtris.py <model.glb> [<optimised.glb>] [rows]

Reads the file as bytes; needs nothing but Python.
"""
import json
import struct
import sys
from collections import Counter


def load(path):
    data = open(path, "rb").read()
    length = struct.unpack_from("<I", data, 12)[0]                 # the JSON chunk's length
    doc = json.loads(data[20:20 + length])
    parent = {child: i for i, node in enumerate(doc["nodes"]) for child in node.get("children", [])}

    def root(index):
        below = index                                # what a node hangs under: its group, a level below the root
        while index in parent:
            below, index = index, parent[index]
        return doc["nodes"][below].get("name", "?")

    def count(mesh):
        return sum((doc["accessors"][p["indices"]]["count"] if "indices" in p
                    else doc["accessors"][p["attributes"]["POSITION"]]["count"]) // 3 for p in mesh["primitives"])

    nodes = {n.get("name", f"node{i}"): count(doc["meshes"][n["mesh"]]) for i, n in enumerate(doc["nodes"]) if "mesh" in n}
    groups = Counter()
    for i, n in enumerate(doc["nodes"]):
        if "mesh" in n:
            groups[root(i)] += count(doc["meshes"][n["mesh"]])
    materials = Counter()
    for mesh in doc["meshes"]:
        for p in mesh["primitives"]:
            triangles = (doc["accessors"][p["indices"]]["count"] if "indices" in p
                         else doc["accessors"][p["attributes"]["POSITION"]]["count"]) // 3
            materials[doc["materials"][p["material"]]["name"] if "material" in p else "(none)"] += triangles
    vertices = sum(doc["accessors"][p["attributes"]["POSITION"]]["count"] for m in doc["meshes"] for p in m["primitives"])
    return {"bytes": len(data), "triangles": sum(nodes.values()), "vertices": vertices, "nodes": nodes, "groups": groups,
            "materials": materials, "mesh nodes": len(nodes), "materials count": len(doc["materials"]),
            "images": len(doc.get("images", [])), "draws": sum(len(m["primitives"]) for m in doc["meshes"])}


def show(path, top):
    d = load(path)
    print(f"{path}: {d['bytes']:,} bytes, {d['triangles']:,} triangles, {d['vertices']:,} vertices, "
          f"{d['mesh nodes']} mesh nodes, {d['draws']} primitives (draws if nothing merges them), "
          f"{d['materials count']} materials, {d['images']} images")
    print("  by group:", ", ".join(f"{g} {n:,}" for g, n in d["groups"].most_common()))
    print("  by material, the most first:")
    for name, n in d["materials"].most_common(top):
        print(f"    {name[:48]:48} {n:6,}  {100 * n / max(1, d['triangles']):4.1f}%")
    print("  by node, the most first:")
    for name, n in sorted(d["nodes"].items(), key=lambda item: -item[1])[:top]:
        print(f"    {name[:48]:48} {n:6,}")
    return d


args = sys.argv[1:]
files = [a for a in args if a.lower().endswith(".glb")]
rows = [int(a) for a in args if a.isdigit()]
if not files:
    raise SystemExit(__doc__)
top = rows[0] if rows else 12
before = show(files[0], top)
if len(files) > 1:
    after = show(files[1], top)
    print(f"\nafter against before: triangles {after['triangles']:,} against {before['triangles']:,} "
          f"({100 * (1 - after['triangles'] / before['triangles']):.1f}% fewer), vertices {after['vertices']:,} against "
          f"{before['vertices']:,}, draws {after['draws']} against {before['draws']}, bytes {after['bytes']:,} against "
          f"{before['bytes']:,}, materials {after['materials count']} against {before['materials count']}, "
          f"images {after['images']} against {before['images']}")
