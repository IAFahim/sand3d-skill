# The environment: which Python, what it prints, what it writes

Verified on sand3d 1.6.3 (source digest `fee4e403d8206135`), Blender 5.2.3 LTS as the `bpy` module, Python 3.13.15, Linux. System Blender on the same machine: 5.2.2 LTS, Python 3.14.8.

## What runs where

| | |
|---|---|
| Python 3.13 | `bpy` 5.2 LTS: what sand3d's CI runs, and what the arena was built with |
| Python 3.11 | `bpy` 4.5 LTS: supported, older Blender inside |
| Python 3.12, 3.14 | no `bpy` wheel: `pip install sand3d` fails; Blender 5.2's own Python is 3.14, so system Blender is a different interpreter |

From sand3d's `pyproject.toml`: `requires-python = ">=3.11,!=3.12.*,<3.14"`, with `bpy>=4.5,<4.6` on 3.11 and `bpy>=5.2,<5.3` on 3.13.

## A new machine

```bash
uv venv -p 3.13 .venv && uv pip install -p .venv sand3d     # or: python3.13 -m venv .venv && .venv/bin/pip install sand3d
.venv/bin/python -c "import sand3d, bpy, sys; print(sys.version.split()[0], sand3d.__version__, bpy.app.version_string)"
scripts/sand3d-env.sh --make                               # does the same when it finds no interpreter
```

`scripts/sand3d-env.sh` prints the first interpreter that imports sand3d, looking at `$SAND3D_PYTHON`, `./.venv`, the clone's own `.venv` (`~/GitHub/sand3d/.venv`), then `python3.13`, `python3.11`, `python`. Tested from the skill's folder, a project folder and `/tmp`; with none in reach it prints `no Python here imports sand3d; run with --make to create ./.venv` and exits 1. Use it as `PY=$(scripts/sand3d-env.sh) && "$PY" build.py`.

## Timings

- `import sand3d`: 1.0 s (it starts Blender).
- A box, a material and its GLB: 0.10 s, of which the glTF export 0.014 s.
- Cycles, see `render-cycles.md`.

## Lines that look like errors and are not

- `ERROR Draco is not available because library could not be found at <site-packages>/bpy/lib/libbf_intern_draco_bridge.so`, and the same for `MeshOptimizer`, on every glTF export from the module. The wheel ships without those two libraries: Draco (`export_draco_mesh_compression_enable`) and meshopt compression cannot be written from the module. Compress with another tool after export if a file must be smaller.
- `cycles | WARNING HIPEW initialization failed: Error opening HIP dynamic library`: Cycles looking for an AMD card that is not there.
- `DeprecationWarning: 'Material.use_nodes' is expected to be removed in Blender 6.0` (and the same for `World.use_nodes`): in 5.x a material and a world always have nodes. Write `if x.node_tree is None: x.use_nodes = True`, which is right on Blender 4 too.

## What `s3d.export` writes for one box

`s3d.at(s3d.box("box", 1000, 500, 250), x=1000)` with `s3d.material(b, "concrete", color="#d6d6d0")`, exported to `.glb`:

- one node: `{"mesh": 0, "name": "box", "scale": [0.001, 0.001, 0.001], "translation": [1, 0, 0]}`. The metres are the node's scale; the mesh data stays in millimetres. With `s3d.units("m")` before the first verb the node has `translation: [1, 0, 0]` and no scale.
- one mesh of 8 vertices and 6 quads in Blender; in the file 24 positions (one per face corner), 24 normals, 36 indices: 12 triangles.
- no `TEXCOORD_0`: sand3d's solids carry no UVs.
- one material, `"concrete #d6d6d0"`: `doubleSided: true`, `metallicFactor: 0`, `roughnessFactor: 0.85`, `baseColorFactor` linear.
- no extras on the node, though the object in Blender carries `s3d_name`, `s3d~place` and `s3d_material`. Blender's own exporter with `export_extras=True` writes those, so take them off first if you export through it.
- `asset.generator: "Khronos glTF Blender I/O v5.2.41"`.

With `on=s3d.grid(2, 2, 2.0)`, `at` returns a list of four objects named `tile.001` to `tile.004`. `s3d.export(four, out)` then raises `AttributeError: 'list' object has no attribute 'name'`; `s3d.export(s3d.group("four", four), out)` writes four nodes under one empty.

## What a pocket leaves

`s3d.shell(s3d.box("walls", 4.0, 3.0, 2.1), 0.06, open="top bottom")` in metres: 16 vertices, 12 faces. One `s3d.pocket(walls, s3d.rect(0.85, 2.07), depth=0.14, on=walls.face("+X").move(0, 0.975))` later: 24 vertices, 16 faces, five of them with more than four sides. The exporter triangulates those, so count triangles in the file, not faces in Blender: 32 before, 48 after.

## Axes

sand3d and Blender: x, y, z up, what the script writes. Every export is Y-up (glTF, FBX, OBJ with `forward_axis='NEGATIVE_Z', up_axis='Y'`): the file holds (x, z, -y). A camera placed for a picture in the script's axes goes into a three.js viewer as (x, z, -y), with y up.
