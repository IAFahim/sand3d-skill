---
name: sand3d-field-notes
description: Field-tested rules for AI agents building 3D with sand3d (Python over Blender's bpy) - find the Python that has sand3d, write programs, cut openings, dress parts in pixel textures, export GLB/FBX/OBJ/.blend, render with Cycles on the GPU, prove a layout by ray casts, pack an export (hidden faces out, one atlas, no z-fighting) and show it in a browser on GitHub Pages, plus the facts agents get wrong (units, exporter noise and extras, tiling, emissive tiles, WebGL limits). Use whenever the work touches sand3d, s3d, bpy as a Python module, a GLB built from code, a Blender headless render or a web viewer for a model - even if the user only says "model this", "make a room, level or building", "reduce the polys" or "fix the z-fighting".
---

# sand3d field notes for agents

Read once, top to bottom. Every line here was run. Versions are named only where they matter: sand3d 1.6.3, Blender 5.2 as the `bpy` module, three.js r187.

## Owner rules (every agent, every brief starts with rule 1)

1. **Before any work** pull this repo (`git -C <clone of IAFahim/sand3d-skill> pull --ff-only`, clone it if missing) and read this file. **Before you finish**, push what you learned back to `main` here: one verified line in the right section (`CONTRIBUTING.md`).
2. **Know the thing before you touch it.** Say in your own words what the model is for and what must not change (a layout, its routes and sightlines, each part's pivot, a look), from the project's AGENTS.md and README. Then read sand3d's `docs/api.md`, which is the whole vocabulary, before writing a verb.
3. **Decide, do not ask.** A decision that is reversible and in scope is yours: take the safer side, write one line, go on. Ask only for a repository's visibility, tags and releases, deleting what you did not make, force pushes, a public format or a licence.
4. **Source and export stay apart.** The source keeps its named parts, their pivots and its separate textures, so it can be dressed again. Packing (hidden faces out, meshes merged, one atlas) happens only in the export step, by a script in the repository, and never edits the source.
5. **Nothing visible may get worse.** An optimisation proves itself with the same pictures before and after, from the same cameras, and with the layout checker's counts unchanged. A smaller file that changed a picture is not done.
6. **Short reports**: commands, counts, shas, what is unverified. A goal that was not reached is never ticked.
7. **You own issues.** Talk before filing one; close it yourself with a receipt when a second run agrees; list what you closed and opened.
8. **Stuck after two honest attempts**: search the web (official documents first; quote the line and keep its URL), then `scripts/ask.sh`.
9. **No guessed APIs.** sand3d is deterministic, so a five-line probe that you ran beats a guess, and a count or a digest is a receipt.
10. Scratch stays outside repositories and is deleted at the end.

## 1. First minute: which Python

```bash
scripts/sand3d-env.sh                      # prints the interpreter that imports sand3d
```

- sand3d needs **Python 3.13** (Blender 5.2 LTS as the `bpy` module) or **3.11** (Blender 4.5 LTS). pip has no `bpy` for 3.12 or 3.14, so `pip install sand3d` cannot work there. (`pyproject.toml`: `requires-python = ">=3.11,!=3.12.*,<3.14"`.)
- The `python` on the PATH may be another one. Here `python` and `python3` were 3.11 with `ModuleNotFoundError: No module named 'sand3d'`; the one that worked was the clone's own `.venv` (3.13.15). Find it before concluding sand3d is missing; never install a second copy over a doubt.
- System Blender is not the module. Blender 5.2.2 runs its own Python (3.14.8); the module runs in yours. A script written for one needs care in the other.
- A program is a plain script, `python build.py`. `import sand3d` starts Blender headless: 1.0 s; a box and its GLB, 0.10 s. No editor, no `blender -b`.
- The glTF exporter prints two ERROR lines in the module, `Draco is not available because library could not be found at .../bpy/lib/libbf_intern_draco_bridge.so` and the same for `MeshOptimizer`. Noise, unless you asked for Draco or meshopt compression: the wheel cannot do it.
- `bpy.ops.wm.read_factory_settings(use_empty=True)` starts over inside one process, which is how render scripts run several files in a row.
- Detail, a new machine, what a box writes into a GLB: `references/environment.md`.

## 2. Writing a program

- Read sand3d's `docs/api.md` first (about 3,600 tokens, every signature) and `docs/guidelines.md` (eight rules for a program of several parts). Programs say `import sand3d as s3d`.
- Millimetres, unless `s3d.units("m")` runs before the first verb. `s3d.export` writes metres by putting `scale: 0.001` on the node and leaving the mesh in millimetres; in metres mode the node carries no scale.
- Every solid starts at z = 0, centred in x and y. So `s3d.at(s3d.box(...), x=cx, y=cy, z=bottom)` is a slab standing on `bottom`: one short helper, `slab(name, x0, y0, x1, y1, z0, z1)`, wrote a 181-part arena.
- A wall with a door or a window is cheapest as the boxes it is cut into (a span beside it, a sill below, a lintel above), each named so its role can be read back from the name. Booleans are for the shapes that cannot be said that way.
- An opening through a shell: `s3d.shell(s3d.box(...), T, open="top bottom")`, then `s3d.pocket(walls, s3d.rect(w, h + 60), depth=T + 80, on=front.move(...))`. The tool dips 60 mm under the floor and 80 past the wall, so no two faces end up coincident. A list of frames cuts several in one call.
- A slope is a triangle extruded and stood up: `s3d.extrude(name, s3d.poly([(0, 0), (run, 0), (run, rise)]), width)` with `at(..., rx=90, rz=...)`. A gable or a pitched roof plane is built on a `s3d.Frame(origin, normal=(...))`.
- `s3d.at(ob, on=s3d.grid(...))` returns a list. `s3d.export` of that list fails with `AttributeError: 'list' object has no attribute 'name'`: pass it through `s3d.group` first.
- sand3d leaves `s3d_name`, `s3d~place` and `s3d_material` on every object. `s3d.export` writes no extras; Blender's own glTF exporter with `export_extras=True` would, so delete those properties first.
- A `box` is 8 vertices and 6 quads: 12 triangles in the file and no UVs. Any texture needs UVs you write yourself (section 3).
- The guidelines forbid `bpy` in a program. That is for sand3d's own examples. For what sand3d does not say (a texture per face, lamps, an FBX, a `.blend`), build with sand3d, then read each part's `matrix_world` and mesh and write new meshes with `bpy`: done on the whole arena without a verb complaining.

## 3. Textures, export, and proving it

Detail and the code to copy: `references/dressing-and-export.md`.

- UVs from world position, 64 pixels to the metre, give the same texture across a hundred parts with no seam: `u = (p.x * -n.y + p.y * n.x) / width`, `v = (p.z - course * 2) / height` on an upright face, `p.x / width, p.y / height` on a flat one. A wall becomes one face per 2 m course.
- `Closest` interpolation on the image node keeps pixels square in the file. After export set every sampler's `minFilter` to 9729 (trilinear), or the distance shimmers.
- Every material comes out `doubleSided: true`. With two faces lying in one plane (a wall's top under a roof slab) that is z-fighting in any rasteriser; read section 6.
- `export_lights=True` puts `KHR_lights_punctual` into `extensionsRequired`: take it out, so a viewer with no lights still opens the file.
- Blender's own exporters give what sand3d's `export` does not: FBX, OBJ with its textures beside it, a `.blend` with images packed. Export Y-up, and remember the file's axes are (x, z, -y) of the script's.
- Prove a layout by ray casts on the exported file, never by reading the code: standable floors on a 0.5 m grid, a walk from each spawn, every sightline open or blocked as designed. Count the floor cells (17,649 for the arena): a number that stays the same after a change is proof that no floor moved.
- Read every export back before trusting it: import the FBX, the OBJ and the `.blend`, measure the world box, count textured materials and lamps (`tools/roundtrip.py` in liminal-arena).
- `scripts/glbinfo.py` and `scripts/glbtris.py` read a GLB as bytes with nothing but Python: counts, samplers, triangles by material and by node, and before against after.

## 4. Rendering with Cycles

Detail, and the numbers for day and dusk: `references/render-cycles.md`. One picture of any GLB: `scripts/render_glb.py <in.glb> <out.png>`.

- The GPU needs its type chosen before its devices are counted: `prefs.compute_device_type = 'OPTIX'` (else `'CUDA'`), then `get_devices()`. An RTX 3060 takes about half a minute for 1800 × 1012 at 256 samples.
- A room can be lit by its own emissive ceiling tiles, as a real one is; then hide the lamps in the picture.
- A mist over the ground must be a bounded layer (a 30 m deep box of volume scatter). A world-sized mist swallows the sun and the sky on their way in.
- At dusk the sun sits below the horizon. With it 1.5 degrees above, the sky is only 2.6 stops darker than midday, far too bright for lit windows to carry a picture.
- Before rendering an eye-level view, cast 0.2 m from the camera in six directions and stop if anything is hit: a camera inside a wall renders nothing and says nothing.
- The same camera in three.js: `fov = 2 * atan(18 / lens)`, across the window's wider side.

## 5. Showing it in a browser

Detail: `references/web-viewer.md`.

- Keep the viewer's library in the repository (`vendor/`) with an import map; the site then has one origin and works under a GitHub Pages sub-path with relative addresses. GitHub Pages is switched on with one API call and builds in about 30 s.
- WebGL 2 promises every machine 15 varying vectors, 16 texture units and 224 fragment uniform vectors. Each shadow-casting light takes one texture unit and one varying; 28 of them failed to link. Count what a program really uses before believing it fits: the software renderer in headless Chromium reports 31, 32 and 4096, which is not the minimum.
- A spot light without shadows shines through walls. Narrow each cone by casting rays to the nearest wall, or give it a shadow.
- Test a viewer with real input. `chromedriver` takes a true pointer, wheel and window resize; headless Chromium with `--ignore-gpu-blocklist --enable-gpu --use-angle=gl` uses the real card. Firefox's headless `--screenshot` does not capture a WebGL canvas: have the page post its own.

## 6. Packed exports: hidden faces, z-fighting, one atlas

Detail, tables and the traps: `references/packed-export.md`. Worked through on liminal-arena: 5,900 triangles and 321 draws became 2,461 and 43, with one 2048 atlas, and no picture moved.

- A model built from boxes that touch has pairs of faces in one plane: a wall's top and the roof's underside, a stair's risers, a pillar's top under a deck. A path tracer picks one and shows nothing wrong; a rasteriser with double-sided materials flickers between them: z-fighting. glTF has no polygon offset, so the fix is in the asset: leave out every face that cannot be seen, never leave two faces in one plane, ship the materials single-sided.
- Measure before promising. The dressed arena is 6,083 triangles: 2,188 are its ceilings, one quad to the metre; 1,612 are wall tops, bottoms and upper courses. What is left is cut by texture: 931 faces out of sight, then each atlas block a face crosses cuts it once. "80% fewer" was not there without moving a texel: 58% was.
- A glTF material cannot tile a corner of one image: UVs outside 0 to 1 wrap the whole atlas. One atlas with no texel resampled needs a face per repeat of its texture, so the atlas's side trades triangles for texture: for the arena 512 is +87% triangles, 1024 −36%, 2048 −58%, and no atlas −64%. Say which you chose and why.
- One mesh cannot be culled part by part. Draw calls fell from 323 to 45 on the aerial and from 74 to 12 on the deck, and triangles drawn per frame stayed near 2,800 in every close view, where the source culled down to 1,764 in one. Fewer calls at the same triangles is the win; say so, and keep doors apart where they must move.
- Z-fighting to a GPU is a draw-order question. `scripts/zfight_tests.js` draws every mesh in its own colour, then again with the order turned about, and counts the pixels that changed: the published arena, 20,047 of 1.37 M from inside a roof slab; packed, 0. One camera and one size each: ask it of the views that matter, and take the count and its picture from one pass over the pixels.
- A striped ceiling in an orbit viewer is often the camera inside a slab, its back faces against the tops of walls. Find where the camera is before hunting coplanar faces.
- three.js casts a one-sided material's shadow from its far side unless `material.shadowSide = THREE.DoubleSide`; without it a hairline of light shows along every ceiling-wall junction indoors.
- Merged faces leave T-junctions, a corner of one face on the edge of another, where a crack of a pixel can open. `scripts/tjunctions.py` counts them from the file alone, one rule for every edge, over every triangle where its node puts it. The arena's source has 565 such edges and its packed export 613; with the packer's `--watertight` none, at 4,664 triangles. Left in, they cost 5 single pixels in one view of thirteen; the choice is written down, not hidden.
- Two corners within a tenth of a millimetre are one corner worked out two ways (32-bit sums, a frame per face). Left apart, each lies on the other's edge and a mending loop cuts them for ever: make them one first, put a corner on the edge's own line, never on its neighbour's, and fail aloud when an edge is cut twice.
- A test that shares the tool's arithmetic is no proof: the packer's own texel test passed while the atlas was upside down. Ask the files from the outside, with a program that shares nothing (`tools/same_surfaces.py`: rays from 4,799 points in the air and from every face, in each file, compared).

## 7. Traps of the tool shell (each one cost time)

- `pkill -f` and `pgrep -f` match the shell that runs them, because the pattern is in its own command line: the call kills itself and prints nothing. Kill by PID found from `/proc`, with the command line compared whole, or by port.
- A helper that ignores an argument lies quietly: screenshots asked for at phone size came out at desktop width. Check the picture's real size (`magick identify`) before trusting a test that depends on it.
- A file read in the same breath as the command that writes it does not exist yet: write, then read.
- Patching a script by replacing text inside a quoted string breaks it when the text holds newlines: write the whole file.
- A number needs its question written beside it. "T-junctions in the export" read 39, 44, 392, 555, 565, 570, 608, 611, 613 and 768 from counters that each asked it another way (per mesh or over the whole file, exact lines or a distance, corners or edges). Write the rule down, and hold every quick counter against one slow plain one.
- A loop that will not end is found by printing its rounds, not by waiting. `PYTHONFAULTHANDLER=1` and `kill -ABRT <pid>` print where a hung Python stands.

## Done means

You ran it and looked at the pictures, the same cameras show the same model, the checker's counts are what they were or you said why, every export was read back, nothing of yours is left in a repository or on disk, you said plainly what you did not verify, and what you learned is pushed back here.
