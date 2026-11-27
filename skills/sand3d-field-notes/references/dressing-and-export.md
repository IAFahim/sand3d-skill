# Dressing a model in textures, exporting it four ways, and proving it

What `examples/arena_liminal.py`, `tools/check_arena.py`, `tools/roundtrip.py`, `tools/glbinfo.py` and `tools/floor_cells.py` in `IAFahim/liminal-arena` do, and why each line is the way it is. Built with sand3d 1.6.3 and Blender 5.2.3.

## The shape of it

Build the grey solids with sand3d. Then, for each part, read its faces where it stands (`ob.matrix_world @ vertex / 1000`, in metres; the normal from `matrix_world.to_3x3() @ polygon.normal`) and write a new mesh of the faces you want, each with its own material and UVs. Put that mesh back on the same object in the object's own frame (`ob.data = me`, `ob.matrix_basis = frame`): the part keeps its name and its pivot, and in an editor a crate still turns about itself. No sand3d verb ran after that and complained.

A part's role comes from its name (`role()`): stairs, ramp, roof, crate, mark, pad, wall with its side, shell, gate. `finish()` turns (role, normal, height, floor) into (texture, tile width in metres, shine). Name parts for the role when you build them; this is the payoff.

## Textures from world position

`place(point, normal, width, course, key)`:

- an upright face: `u = (p.x * -n.y + p.y * n.x) / width`, which runs along the wall left to right as its front is seen, and `v = (p.z - course * BAND) / height`;
- a flat face: `u = p.x / width`, `v = p.y / height`.

Kenney's *Retro Textures (Liminal)* are 64 pixels to the metre: a wallpaper panel 64 by 128 is 1 m wide and 2 m tall. Because the address is the world position, one texture runs across a hundred parts with no seam, and a face cut anywhere still finds its place.

- `courses(ring)` cuts every upright face into bands `BAND` metres tall (2) at heights `k * BAND`, each its own face with its own `course`: a wainscot panel on the first, plain tile above.
- `floor(ring)` cuts the ground's top along every zone's edges (carpet where a room is, water in one corner, a lane line 1 m wide) and tiles each cell.
- `ceiling(ring, lamps)` replaces a roof's or a deck's underside with 1 m tiles: lit where `i % 4 == 2 and j % 4 == 2`, a vent where `i % 7 == 5 and j % 6 == 4`, and a lamp recorded under every second lit tile.
- `outline(ring, pad)` is a pad's top: its floor inside, a 0.15 m band round the edge that shines.
- Materials: one per texture, made once; `image.interpolation = 'Closest'` keeps pixels square; roughness 0.85; an emissive material links the same image to Emission Color with strength 3.
- A door leaf is 1.1 by 2.2 m (its texture is 64 by 128) and 0.06 m thick, hung open at a right angle on one jamb, its four edges a flat colour.

## Exporting

- `s3d.export(root, "x.glb")` for a plain GLB. For the rest, Blender's own exporters, in the same script:
  - `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', export_image_format='AUTO', export_yup=True, export_extras=True, export_lights=True, export_copyright=...)`
  - `bpy.ops.export_scene.fbx(filepath=..., object_types={'EMPTY', 'MESH', 'LIGHT'}, path_mode='COPY', embed_textures=True, bake_anim=False)`
  - `bpy.ops.wm.obj_export(filepath=..., forward_axis='NEGATIVE_Z', up_axis='Y', export_materials=True, path_mode='COPY', apply_modifiers=True)`: empty the OBJ's folder first, or textures from an earlier run outlive their use.
  - a `.blend`: `image.pack()` for every image, `preferences.filepaths.save_version = 0` (no `.blend1` beside it), `wm.save_as_mainfile(filepath=..., compress=True)`.
- Before exporting through Blender, delete sand3d's own properties (`s3d_name`, `s3d~place`, `s3d_material`) from every object, or `export_extras=True` writes them; and remove the materials sand3d made (`"s3d_material" in m`), or the file carries materials nothing uses.
- `polish()` then rewrites the GLB's JSON chunk in place (`struct` and `json`, the rest of the bytes kept):
  - every sampler's `minFilter` to 9729, `LINEAR_MIPMAP_LINEAR`. `Closest` had written nearest for both; nearest magnification is right for pixel art, nearest minification shimmers with distance.
  - `KHR_lights_punctual` out of `extensionsRequired`. The exporter declares the file cannot do without its lamps; a viewer that has no lights should still open it.
- What came out for the arena: GLB 748,600 bytes, 200 meshes, 333 primitives, 29 materials, 23 PNG images, 24 point lights, 6,083 triangles; `emissiveStrength` 3 through `KHR_materials_emissive_strength`; every material `doubleSided: true`.
- A point lamp of 5 W in Blender is 271.757 in the GLB (5 × 683 / 4π): photometric units, hundreds of times dimmer than a daylit scene scaled in watts. A viewer that wants lit rooms gives each lamp a light of its own or lights rooms another way.

## Proving the layout by ray casts

`tools/check_arena.py` imports the exported GLB into an empty scene and asks the file, not the code:

- standable floors: cast down on a 0.5 m grid; a cell stands if a face looks up and nothing is within a player's height above it;
- a walk from each spawn over those cells: a player steps up 0.4 m, jumps 1.05 m, runs at 5.5 m/s, so walk times are straight-line estimates;
- every way up behaves as meant (a loft is unreachable with its ramp hidden; a door shut fills its doorway with a box);
- 39 sightlines from each vantage to what it should see or not see.

Two things it took to make the casts honest:

- **No probe at exactly 45 degrees.** Samples sit at .25 and .75 m and corners on whole metres, so a true diagonal lands on corners, where it touches two faces at once and which one a cast reports is a tie that a rebuilt mesh can break either way. The nine probes are slightly off the diagonal: `(1, .13, .07)`, `(-1, .11, -.05)`, `(1, .93, .03)` and so on.
- **Count the floor cells.** `python -I tools/floor_cells.py tools/check_arena.py <glb> <out.json>` runs the checker's own code up to its survey and writes every 0.5 m cell with the heights it can stand on: 17,649 cells, the same for the grey and the dressed file. Any change that keeps that number has moved no floor, which is a receipt that costs one command. When a cell is not counted and should be, `python -I tools/probe_hit.py <glb> x y z` prints every probe's first hit above that spot, and what made it.

Run it after every export that claims to keep the layout: `python tools/check_arena.py models/liminal/arena_liminal.glb`. A camera check of the same kind is in `render/views.py`: cast 0.2 m from the camera in six directions and stop with a message if anything is hit.

## Reading exports back

- `tools/roundtrip.py`: import the FBX, the OBJ and the `.blend` into an empty scene each, measure the meshes' world box, count textured materials, lamps and empties, and check that every image in the `.blend` is packed. The arena is x -40..40, y -28..28, z -1..7 in Blender's axes; all three measured the same. It also looks for this machine's home path in every file under `models/` (32 of them) and stops with the names of those that hold it (below).
- `scripts/glbinfo.py` and `scripts/glbtris.py` here read a GLB as bytes with nothing but Python: `python -I glbtris.py before.glb after.glb` prints triangles, vertices, primitives, materials and images, by material and by node, and the difference.

## No file may say where it was written

- The FBX exporter, with `path_mode='COPY', embed_textures=True`, puts every texture's bytes into the file. Its name is written five times: `Video.RelativeFilename` and `Texture.RelativeFilename` as they should be, `arena_liminal.fbm/<name>.png`, a file beside the FBX; and `Video.Filename`, the `Path` property in the `Video`'s `Properties70`, and `Texture.FileName` as the path stood on the machine that ran. For 23 textures that is 70 absolute strings, and no option of the exporter leaves them out. A `.blend` can keep a path too.
- A search of the text diff finds none of it: the files are binary, and the diff says `Bin`. Search the files themselves, before every push, for the home path and for `/tmp/`: `grep -a -c "$HOME" <file>` over every file about to be published. `tools/roundtrip.py` does it over all of `models/` and stops.
- `unpath()` in `examples/arena_liminal.py` is the cure, run on the FBX right after the export. The file is read as the bytes it is; every string that begins with the output folder is cut to what follows it; and as the file counts its bytes, every count is made right again. It needs the binary layout of FBX 7400, which Blender writes:
  - 23 bytes of header, then the version as a 32-bit little-endian number; the nodes begin at byte 27.
  - A node: `EndOffset`, `NumProperties`, `PropertyListLen` (three 32-bit numbers), a one-byte name length, the name, the properties, the child nodes, and, if it has any, thirteen zeros, which are inside its `EndOffset`. Top-level nodes stand one after another without them, and thirteen zeros follow the last.
  - A property: a type letter, then its value. `Y` 2 bytes, `C` 1, `I` and `F` 4, `D` and `L` 8. `S` and `R`: a 32-bit length, then exactly that many bytes, **and no zero after** (a reader written for a zero terminator finds nothing to cut). An array (`b`, `c`, `i`, `l`, `d`, `f`): three 32-bit numbers, the count, the encoding and the compressed length, then the values.
  - The end: the thirteen zeros, a 16-byte ID, 4 zero bytes, zeros up to a multiple of 16 (sixteen bytes when it is one already), the version again, 120 zeros, a 16-byte mark. The last 140 bytes are put back as they are.
  - From version 7500 on the numbers are eight bytes wide: the function refuses those, by name.
- What proved it: a file with nothing to cut comes back the same bytes; the 70 strings cut and the 117 names beginning `arena_liminal.fbm/` left; a second run changes nothing; all 11,941 nodes written again in their order, each property list as long as it says; and Blender imports the file from before and the one from after to the same 233 objects, 200 meshes, 29 materials and 23 images, with the same rows and the same pixels in every image. Only the image's `filepath` differs, and the new one is found from the embedded bytes by a relative name.

## Two builds against each other

- The GLB, the OBJ and the JSON come out of two builds in two folders as the same bytes. An FBX does not: `CreationTimeStamp` holds the second it was written, and its object IDs are made from Python's `hash()`, which changes with the process's seed. A `.blend` differs between two saves in about 330 small counters of its node trees.
- `PYTHONHASHSEED=0` takes the IDs out: two builds of one code, in two folders, gave the same 20,114 records with the second and the millisecond of the time stamp apart, and nothing else. Without it 2,236 ID longs differ (`Model`, `Geometry`, `NodeAttribute`, `Material`, `Texture`, `Video`, `Document` and the `Connections` to them).
- So `cmp` says only that two FBX files are not the same. Read them record by record, with a walker over the layout above, and look at what differs by type: integers of the time stamp, longs of IDs, and strings. A string that differs is the one to read.

## The triangles of the dressed arena, by material

| what | triangles |
|---|---|
| ceilings (`ceiling_medium` 2,016, `_light_on` 124, `_vent` 48): one quad to the metre | 2,188 |
| wall tops, bottoms and courses above the first (`wall_yellow_small` 815, `wall_blue_stripes_small` 795, `wall_blue_small` 2) | 1,612 |
| yard and paving (`pool_tiles`) | 598 |
| concrete (`wall_concrete` 306), wallpaper panels (264 and 240), crates (`metal_structure_bolts` 244, `metal_structure` 48) | 1,102 |
| doors: 152 of edge, 76 of face | 228 |
| markers, the design plates | 144 |
| pads' shining outlines, carpets (66), a lane line (28), water, roofing, a flat panel | 211 |

The grey blockout under it is 2,156 triangles: every box with all six faces, most of them inside another box.
