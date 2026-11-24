# Rendering a GLB with Cycles in the `bpy` module

What `render/render_liminal.py` and `render/views.py` in `IAFahim/liminal-arena` do, with the numbers that were measured. Blender 5.2.3 as a module, a GeForce RTX 3060. One picture of any GLB without any of this set up: `scripts/render_glb.py <in.glb> <out.png> [width height] [lens] [azimuth elevation] [samples]`.

## The rule the pictures follow

Nothing is in a picture that the file does not hold, beyond the plain under the model, the sun, the sky and a thin mist. The GLB is imported into an empty scene (`read_factory_settings(use_empty=True)`, then `import_scene.gltf`), so a picture is of the export, not of the script's memory of it. Two renderers share one file of cameras and labels, so a grey view and a dressed one are the same photograph.

## GPU

```python
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
for kind in ('OPTIX', 'CUDA'):            # the type must be chosen before devices are counted
    try:
        prefs.compute_device_type = kind
        break
    except TypeError:
        continue
prefs.get_devices()
for device in prefs.devices:
    device.use = device.type in ('OPTIX', 'CUDA')
scene.cycles.device, scene.cycles.samples, scene.cycles.use_denoising = 'GPU', samples, True
```

The loop is there because the type must be chosen before the devices are counted, as `views.py` notes beside it. 1800 × 1012 at 256 samples takes about half a minute on the RTX 3060; `50 32` on the command line gives a quick half-size look.

## Light, for each time of day

| | day | dusk |
|---|---|---|
| sun on level ground, W/m² | 3.2 | none |
| the sun's height | where the view puts it | 3 degrees below the horizon |
| sky strength, and how much of its blue it keeps | 0.07, all | 0.3, 60% |
| mist density, per metre | 0.003 | 0.006 |
| exposure, in stops | -0.2 | +3.0 |
| bloom: what starts to glow, how far it spreads | 1.0, 0.12 | 1.0, 0.5 |

- A lamp is the sun, not the sky's disc: `ShaderNodeTexSky` with `sky_type = 'MULTIPLE_SCATTERING'` and `sun_disc = False`, and a SUN lamp with `angle = radians(2.0)` for the softer shadow. A sun lamp's strength is irradiance flat-on, so `energy = ground / toward.z` keeps a view as bright whatever height its sun hangs at.
- `sun_rotation = atan2(toward.x, toward.y)`: no turn is north, a right angle east.
- Exposure in stops (`scene.view_settings.exposure`) and `view_transform = 'Standard'`, which is exposure times the colour, then clipped: the same as three.js's `LinearToneMapping`, so a viewer and a picture can be matched number for number.
- Bloom in Blender 5 is a compositor node group: `scene.compositing_node_group = tree`, with `CompositorNodeRLayers` into `CompositorNodeGlare` (`Type = 'Bloom'`) into the group's output.

## What was learned about dusk

- The sun sits 3 degrees below the horizon, not just above it. Measured: with the sun 1.5 degrees up, the physical sky is only about 2.6 stops darker than midday, far too bright for lit windows to carry a picture.
- A mist cannot be the whole world's. That far away it swallows the sun and the sky on their way in, and only the lit tiles are left. It is a bounded layer: a box 2000 × 2000 × 30 m over the ground with a Volume Scatter shader (anisotropy 0.3). The sky and the sun cross 30 m of it in a breath; a sightline along the ground loses itself in it.
- Rooms are lit by their own ceiling tiles: the emissive material (strength 3) is the light. The point lamps are hidden in every picture, `ob.hide_render = ob.hide_render or ob.type == 'LIGHT'`.

## Pixels up close, smooth far away

A texture node's `interpolation` is `Closest` for an eye-level view and `Linear` for the plan and the aerial: from above a pixel holds many texels, up close one texel holds many pixels. (In the exported GLB the sampler does the same: nearest magnification, trilinear minification.)

## Cameras

- A lens on Blender's 36 mm sensor is `fov = 2 * atan(18 / lens)`. In three.js the same lens is the field of view across the window's wider side; on the narrow side it is `2 * atan(tan(fov / 2) / aspect)`.
- An eye-level camera has a guard: cast 0.2 m from it along the six axis directions and stop with a message if anything is hit. A camera inside a wall renders a flat colour and no error.
- Labels drawn on the model are flat text and tiles of an unlit material (`ShaderNodeEmission`) with `visible_shadow`, `visible_diffuse` and `visible_glossy` turned off, so they cast no shadow and no ghost.

## Reading colours back

To match a viewer to a picture, sample the picture: `magick picture.jpg -format "%[pixel:p{120,340}]" info:` gives one pixel. The arena's measured values, in 8-bit sRGB: day, plain (97-100, 103-106, 114-118), sunlit deck (198, 207, 236), deck in shade (79, 97, 133); sky at eye level (100, 129, 169) at the top of the frame to (134-140, 164-176, 198-212) at the horizon; dusk, plain (46-53, 49-56, 64-73), deck (68, 70, 93), sky (121-128, 125-131, 154-162).
