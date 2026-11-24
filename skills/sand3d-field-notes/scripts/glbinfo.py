"""What a GLB holds, read as the bytes it is: counts, samplers, materials, lights, triangles.

    python -I glbinfo.py <model.glb> [another.glb ...]
"""
import json
import struct
import sys
from collections import Counter


def read(path):
    data = open(path, "rb").read()
    magic, version, total, length, kind = struct.unpack_from("<4sIII4s", data, 0)   # header, first chunk
    doc = json.loads(data[20:20 + length])
    bin_len = struct.unpack_from("<I", data, 20 + length)[0] if len(data) >= 28 + length else 0
    return data, magic, version, total, length, bin_len, doc


def triangles(doc, mesh):
    accessors = doc["accessors"]
    return sum((accessors[p["indices"]]["count"] if "indices" in p else accessors[p["attributes"]["POSITION"]]["count"]) // 3
               for p in mesh["primitives"])


def report(path):
    data, magic, version, total, length, bin_len, doc = read(path)
    scene = doc["scenes"][doc.get("scene", 0)]
    parents = {child: i for i, node in enumerate(doc["nodes"]) for child in node.get("children", [])}

    def group(index):
        below = index                                # what a node hangs under: its group, a level below the root
        while index in parents:
            below, index = index, parents[index]
        return doc["nodes"][below].get("name")

    used = [(n, triangles(doc, doc["meshes"][n["mesh"]])) for n in doc["nodes"] if "mesh" in n]
    by_material = Counter()
    for mesh in doc["meshes"]:
        for p in mesh["primitives"]:
            count = (doc["accessors"][p["indices"]]["count"] if "indices" in p else doc["accessors"][p["attributes"]["POSITION"]]["count"]) // 3
            by_material[doc["materials"][p["material"]]["name"] if "material" in p else "(none)"] += count
    print(f"{path}: {magic.decode()} v{version}, {total} bytes = json {length} + bin {bin_len}; "
          f"declared total matches the file: {total == len(data)}")
    print("  generator:", doc["asset"].get("generator"), "| extensions:", doc.get("extensionsUsed"), "required:", doc.get("extensionsRequired"))
    print("  nodes:", len(doc["nodes"]), " mesh nodes:", len(used), " meshes:", len(doc["meshes"]),
          " materials:", len(doc["materials"]), " images:", len(doc.get("images", [])), " textures:", len(doc.get("textures", [])))
    print("  triangles:", sum(t for _, t in used))
    groups = Counter()
    for i, node in enumerate(doc["nodes"]):
        if "mesh" in node:
            groups[group(i)] += triangles(doc, doc["meshes"][node["mesh"]])
    print("  triangles by group:", dict(groups.most_common()))
    print("  samplers (mag, min, wrapS, wrapT):", dict(Counter(
        (s.get("magFilter"), s.get("minFilter"), s.get("wrapS"), s.get("wrapT")) for s in doc.get("samplers", []))))
    print("  images:", dict(Counter((i.get("mimeType"), "embedded" if "bufferView" in i else i.get("uri")) for i in doc.get("images", []))))
    print("  double-sided materials:", sum(1 for m in doc["materials"] if m.get("doubleSided")), "of", len(doc["materials"]),
          "| with UVs on every primitive:", all("TEXCOORD_0" in p["attributes"] for m in doc["meshes"] for p in m["primitives"]))
    for name, count in by_material.most_common(12):
        print(f"    {name[:44]:44} {count:6} triangles")
    lights = doc.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])
    if lights:
        print("  lights:", len(lights), dict(Counter(l["type"] for l in lights)), "first:", lights[0])
    for i, (n, _) in enumerate(sorted(used, key=lambda u: -u[1])[:8]):
        print(f"    {n.get('name', '?')[:34]:34} {triangles(doc, doc['meshes'][n['mesh']]):6} triangles  under {group(i)}")
    print("  axes in the file are glTF's: x, y up, z south; Blender's and sand3d's are x, y, z up")


for path in sys.argv[1:]:
    report(path)
