# A packed export: hidden faces out, one mesh, one atlas, no z-fighting

What `tools/pack_arena.py` in `IAFahim/liminal-arena` does, with what it took to get right. Blender 5.2 as the `bpy` module, three.js r187, a GeForce RTX 3060. The source keeps its named parts, their pivots and its separate textures (rule 4); the packed file is written from it, never edited.

## What came out of the arena

| | source | packed, 2048 atlas |
|---|---|---|
| triangles | 5,900 | 2,461 (−58.3%) |
| draws in the file | 321 | 43 |
| mesh nodes | 188 | 20: the arena in one, 19 doors on their hinges |
| materials | 27, each on its own image | 6: two on one atlas, four flat |
| sides | all double-sided | single-sided, no two faces in one plane |
| GLB | 745 KB | 858 KB with the atlas embedded |

By the atlas's side (triangles left as merged; watertight, see T-junctions): 512, 11,043 (+87%; 15,809); 1024, 3,755 (−36%; 6,563); 2048, 2,461 (−58%; 4,664); 4096, 2,171 (−63%; 4,097); no atlas, 2,109 (−64%; 4,012; 315 KB, 27 materials, 60 draws). GLB sizes with the atlas embedded: 996 KB, 672 KB, 858 KB, 1,426 KB.

- "80% fewer" was not there without moving a texel: with no atlas at all the visible arena is 2,109 triangles. A 512 atlas holds every texture at full resolution but gives each one repeat of room, so every face is cut at every repeat: more triangles than the source and a larger file. Say which side you chose and why; 1024 was the lightest file, 2048 the fewest triangles.

## The order of work

1. **Measure where the triangles are.** The dressed arena: 2,188 in its ceilings (one quad to the metre), 1,612 in wall tops, bottoms and upper courses, of 6,083. So: out of sight first, merging second, texture cuts last.
2. **Faces into two kinds.** Faces on a plane that faces an axis go on that side's grid of (s, t) in metres; the rest (slopes, a triangle cut from a ramp's side) are convex polygons in a frame of their own.
3. **Out of sight.** A face with the matter of another solid 0.1 mm in front of it goes (931 faces, 3,072 m²). Of two faces in one plane the smaller gives way (30.7 m²), unless it is enclosed on all sides, where cutting it would only cut a bigger face.
4. **Merge** the kept cells of one texture in one plane into as few quads as possible: strips along s, strips along t, then greedy. Each quad is two triangles.
5. **Atlas.** Each texture gets a block of a by b repeats; a face is cut once per block it crosses.
6. **One mesh** for the arena, one primitive per material; each door keeps its name and a mesh of its own in its hinge's frame (`frame.inverted() @ point`).
7. **Prove**, in the tool and from the outside (below), then look at the pictures.

## One atlas without resampling a texel

- A glTF material samples the whole image: UVs outside 0 to 1 wrap, so a corner of an atlas cannot be tiled. The way that keeps every texel is a face per block of its texture.
- A block is its texture from a whole repeat. Round it lies an **apron** (half a repeat each way, where a face may start off a whole repeat) and outside that a **gutter** for the mip levels (4 texels round a block up to 128 px, then 8, 16 and 32 as it grows), both the texture's own continuation. A face no longer than a block is never cut.
- A texture's block is grown one step at a time (a repeat along u, along v, doubled either way, an apron) for as long as everything fits, each time where it saves the most quads per texel. Blocks are stacked along the lowest skyline, the best of three orders.
- Every texel of the atlas is the one in its file, top row first as PNG and glTF have it; the sheet elsewhere is the average colour. **Blender reads an image from its bottom row**, so a texture is flipped on the way in (`(ih − 1 − y)`), and the atlas's v is counted from the bottom: `1 − (y0 + margin + …) / size`. The first atlas came out upside down and the tool's own test passed, because the test read it the same wrong way.
- The apron has to be taken from the block on **both axes of the atlas UV**, and a block may start off a whole repeat only where it has one: the first layout left the v apron out, and faces at a block's edge sampled the block below.
- Sums over a face are done in **exact doubles** from its first corner (`turn`): a `mathutils` vector keeps 32 bits, and at thirty metres that is thicker than a strip of wall. A corner rebuilt from a face's own frame (`a·q0 + b·q1 + n·d`) lands a grid step or two off; a corner of the face itself is given back as it was, and any other is set on the grid (0.01 mm).

## Z-fighting, and how to measure it on a GPU

- Boxes that touch put pairs of faces in one plane. A path tracer picks one; a rasteriser with double-sided materials flickers between them. **glTF has no polygon offset**: the fix is in the asset.
- The stripes a user sees are often from a camera **inside a slab**: the backs of the ceiling tiles against the tops of the walls. Find where the camera is first.
- `scripts/zfight_tests.js`: every mesh in a colour of its own, then again with the order turned about (meshes last to first, triangles of each last to first); the pixels that changed are the ones whose surface depends on the order. The published arena from inside a roof slab: 20,047 of 1,371,200; packed: 0 in that camera and in five more inside slabs, 4 over the aerial (faces of two paints meeting on an edge). Take the count and its picture from the one pass over the pixels: a first script counted 57,101 where its own mask showed 97.
- Its second test, `crackTest`, draws the model alone and counts the pixels left empty with three or four neighbours drawn: a crack. One camera and one size each: ask of the views that matter.
- three.js casts a one-sided material's shadow from its **far** side unless `material.shadowSide = THREE.DoubleSide`. Without it, a hairline of light along every line indoors where a ceiling meets a wall (233 to 2,632 pixels per picture against the source; 0 to 91 with it).

## T-junctions, and corners that are one corner

- Merged faces leave T-junctions: a corner of one face on the edge of another, where each triangle works the line out for itself and a pixel can be drawn by neither. `scripts/tjunctions.py` counts them from the file alone.
- **One rule for every edge**: a corner is on an edge when it is within 0.02 mm of the edge's line and more than 0.02 mm from either end. Ask it **over every triangle where its node puts it** (doors with the walls), with corners first set on a 0.01 mm grid, which joins a corner from its node's 32-bit frame to the same corner of the mesh next to it. Asked per mesh, or with exact lines instead of a distance, the same files read 570, 608 and 611 for the export and 39, 392 and 44 for the source: write the rule down beside the number, and hold every quick counter against one slow plain one. Source 565 such edges, packed 613, 512 atlas 1,549.
- **All the meshes are mended together.** Mended apart, the structure had none left and each door still put corners on the wall's edges: 54.
- **Two corners within 0.1 mm are one corner**, the one most faces hold. The arena had 13 such twins (63 with the 512 atlas), all at the pointed tip of a ramp's side: each lay on the other's edge, and the mending loop cut them for ever (three corners within 0.03 mm at one tip).
- **A corner put on an edge is put on the edge's own line**, not where its neighbour has it: a step off the line gives the face a kink of 0.01 mm, and it can no longer be cut into triangles.
- **Fail aloud when an edge is cut twice**: that is the cycle, and ten minutes of silence is worse than a message with the two corners in it.
- Watertight (`--watertight`) costs 2,461 → 4,664 triangles at 2048. Left in, the T-junctions were 5 single pixels in one view of thirteen, on another rasteriser; on the GPU (a GeForce RTX 3060 through ANGLE's Vulkan) the default export's sixteen pictures differ from the watertight one's by 60 single pixels in all, at most 14 in one, and another rasteriser counts other pixels for the same edges. The arena's export leaves them; the reason is written in its README. On the GPU the watertight file showed 0, and the crack test finds no pixel left empty in those sixteen pictures, where it found 38 in the default's.

## Proofs, and the ones that are no proof

- In the tool: the area of each texture before and after; no two faces in one plane; every face points out of its solid; every kept face samples the texel it sampled before, asked once of the tool's mapping and once of the atlas file as a viewer decodes it; and the GLB as bytes: its images, its triangles, no double-sided material, the T-junctions.
- **A test that shares the tool's arithmetic is no proof** (the upside-down atlas). `tools/same_surfaces.py` shares nothing: rays from 4,799 points in the air and out of every face of each file, compared by the texture and colour met. On the packed arena 124,722 air rays and 6,381 + 2,698 face rays agree, on every atlas's side.
- Writing that proof: tolerances in metres, never in repeats; ray directions spread over the sphere, not along axes; a ray that lands within a hair of an edge is set aside and counted; and **a point "in the open" must also be at least 1 cm from every face** (`BVHTree.find_nearest(p)[3]`): a ray 2 m in front of a face can land on the far face of the same wall piece, where the odd-crossing test cannot tell matter from air. With that rule, three files that seemed to show doubly-drawn surfaces showed none.
- The checker's counts: 39 of 39 sightlines, 17,649 floor cells, the same before and after.
- Pictures: the page at 1600 × 857, sixteen cameras, packed against source, 0 to 91 pixels of 1.37 M differing by more than 32 of 255 (ramp feet 1 to 2 cm above the ground, seen from 177 m); Cycles on six views, one stray pixel.

## What one mesh costs

- A frame, shadows settled, RTX 3060 at 1600 × 857, the middle hundred of two hundred frames in a row, timed from its first draw to one pixel read back: draws 324 → 46 on the aerial and 75 → 13 on the deck; triangles drawn about 2,800 to 3,000 in every close view, where the source drew 1,766 to 6,142, because **one mesh cannot be culled a part at a time**. Frame time 4.0 to 6.1 ms either way, about 0.2 ms of it the copy to the canvas (a count taken another way, before the page had its own buffer, read 1.3 to 3.2 ms: write the method beside the number). The win is the smaller model and the fewer draws; do not promise a faster frame on a card that is not working.
- Keep apart what must move or be found again (doors by name and hinge, spawn points as empties).
