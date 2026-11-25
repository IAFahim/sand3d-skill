"""T-junctions in a GLB: an edge one triangle holds whole while another holds part of it, a
corner of the latter lying on the edge. Each triangle works the line out for itself, and where
the two differ a pixel can be drawn by neither: a crack of less than a pixel.

    python -I tjunctions.py <model.glb> [another.glb ...] [--grid 1e-5]

Asked over every triangle of the file where its node puts it, which is what a GPU draws
together, so a door's corner is asked of the wall's edge as well as of its own mesh's; and
of each mesh apart, in its own numbers. A corner lies on an edge when it is within 0.02 mm
of the edge's line and more than 0.02 mm from either end: one rule for every edge. Corners
are first set on a grid of `--grid` metres (a hundredth of a millimetre): a corner carried
through its node's frame in 32 bits comes out a few microns from the same corner of the mesh
next to it, and must not count as another. The count is of edges, not of the corners on them.
Nothing but Python. The exit is 1 if a file has any.
"""
import argparse
import json
import math
import struct
import sys
from collections import defaultdict

SEAM = 2e-5          # metres: this far from an edge's line, and no nearer than this to its ends, a corner is on it
CODE = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}     # glTF's component types


def read(path):
    """The file's JSON and the bytes its accessors and images point into."""
    data = open(path, "rb").read()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + length]), data[28 + length:]


def held(doc, body, i):
    """An accessor's numbers: each corner of a POSITION, or the indices one by one."""
    a, v = doc["accessors"][i], doc["bufferViews"][doc["accessors"][i]["bufferView"]]
    start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    if a["type"] == "VEC3":
        return [struct.unpack_from("<3f", body, start + k * v.get("byteStride", 12)) for k in range(a["count"])]
    return struct.unpack_from("<" + CODE[a["componentType"]] * a["count"], body, start)


def frame(n):
    """A node's own place in its parent's: glTF's sixteen numbers, down each column."""
    if "matrix" in n:
        return list(n["matrix"])
    x, y, z, w = n.get("rotation", (0, 0, 0, 1))
    a, b, c = n.get("scale", (1, 1, 1))
    p = n.get("translation", (0, 0, 0))
    return [a * (1 - 2 * (y * y + z * z)), b * 2 * (x * y - z * w), c * 2 * (x * z + y * w), 0,
            a * 2 * (x * y + z * w), b * (1 - 2 * (x * x + z * z)), c * 2 * (y * z - x * w), 0,
            a * 2 * (x * z - y * w), b * 2 * (y * z + x * w), c * (1 - 2 * (x * x + y * y)), 0,
            p[0], p[1], p[2], 1]


def after(outer, inner):
    """`outer` then `inner`: where the one puts what the other has put."""
    return [sum(outer[4 * k + r] * inner[4 * c + k] for k in range(4)) for c in range(4) for r in range(4)]


def threes(seq):
    return [seq[k:k + 3] for k in range(0, len(seq) - len(seq) % 3, 3)]


def corners(doc, body, grid):
    """Every mesh's triangles as corners in its own numbers, each mesh apart, and over the scene,
    where each node's frame puts them. One POSITION is often written several times, once per
    corner's other attributes: corners are told apart by where they are, and set on the grid."""
    def set_down(q):
        return tuple(round(round(c / grid) * grid, 10) for c in q)

    meshes = []
    for mesh in doc.get("meshes", []):
        tris = []
        for pr in mesh["primitives"]:
            here = [set_down(q) for q in held(doc, body, pr["attributes"]["POSITION"])]
            tris += [[here[j] for j in t] for t in threes(held(doc, body, pr["indices"]) if "indices" in pr else here)]
        meshes.append(tris)
    world = []

    def walk(i, m):
        n = doc["nodes"][i]
        m = after(m, frame(n))
        if "mesh" in n:
            world.extend([[set_down([sum(m[4 * k + r] * q[k] for k in range(3)) + m[12 + r] for r in range(3)]) for q in t]
                          for t in meshes[n["mesh"]]])
        for c in n.get("children", []):
            walk(c, m)

    for i in doc.get("scenes", [{"nodes": []}])[doc.get("scene", 0)]["nodes"]:
        walk(i, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
    return meshes, world


def count(triangles, seam=SEAM):
    """(the edges that have the corner of another triangle on them, each with the corners on it,
    up to three; how many edges there are). A corner is looked for in the boxes over its edge,
    so that a long edge costs boxes, not corners."""
    places, edges, tris = {}, set(), []
    for t in triangles:
        here = []
        for q in t:
            if q not in places:
                places[q] = len(places)
            here.append(places[q])
        tris.append(here)
    for t in tris:
        for x, y in ((0, 1), (1, 2), (2, 0)):
            edges.add((min(t[x], t[y]), max(t[x], t[y])))
    by = [None] * len(places)
    for q, v in places.items():
        by[v] = q
    if not by:
        return [], 0
    size = max(seam, max(max(q[k] for q in by) - min(q[k] for q in by) for k in range(3)) / 64)
    boxes = defaultdict(list)
    for v, q in enumerate(by):
        boxes[tuple(math.floor(c / size) for c in q)].append(v)
    found = []
    for a, b in edges:
        A, B = by[a], by[b]
        d = [y - x for x, y in zip(A, B)]
        square, length = sum(c * c for c in d), math.dist(A, B)
        if not square:
            continue                                   # two corners within the grid step of each other
        low = [math.floor((min(x, y) - seam) / size) for x, y in zip(A, B)]
        high = [math.floor((max(x, y) + seam) / size) for x, y in zip(A, B)]
        hit = []
        for i in range(low[0], high[0] + 1):
            for j in range(low[1], high[1] + 1):
                for k in range(low[2], high[2] + 1):
                    for v in boxes.get((i, j, k), ()):
                        w = [c - x for c, x in zip(by[v], A)]
                        t = sum(x * y for x, y in zip(w, d)) / square
                        if (seam / length < t < 1 - seam / length and math.dist(w, [t * c for c in d]) < seam
                                and ((min(v, a), max(v, a)) in edges or (min(v, b), max(v, b)) in edges)):
                            hit.append(by[v])
        if hit:
            found.append((A, B, hit))
    return found, len(edges)


def report(path, grid):
    doc, body = read(path)
    meshes, world = corners(doc, body, grid)
    apart = sum(len(count(tris)[0]) for tris in meshes)
    found, edges = count(world)
    print(f"{path}: {len(found)} of {edges:,} edges have the corner of another triangle on them, asked over every "
          f"triangle where its node puts it; asked of each mesh apart: {apart}")
    for A, B, hit in found[:3]:
        print(f"   from {A} to {B}, a corner at {hit[0]}")
    return len(found)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T-junctions in a GLB, asked over every triangle where its node puts it.")
    parser.add_argument("glb", nargs="+")
    parser.add_argument("--grid", type=float, default=1e-5, help="metres: corners are set on a grid of this side before they are compared")
    args = parser.parse_args()
    sys.exit(1 if sum(report(path, args.grid) for path in args.glb) else 0)
