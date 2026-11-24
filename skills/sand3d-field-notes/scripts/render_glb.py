"""One picture of a GLB with Cycles, on the GPU where there is one: the camera frames the whole model
from a corner, a sun lights it from over the camera's shoulder, and a plain lies under it.

    python render_glb.py <model.glb> <out.png> [width height] [lens mm] [azimuth elevation] [samples]

Azimuth is the compass the camera stands on, degrees anticlockwise from +X and around the model's
middle; elevation, degrees above the horizon. The picture is what the file holds, plus the plain,
the sun and the sky. A JPEG is written when the name ends in .jpg.
"""
import math
import sys

import bpy
import mathutils

args = sys.argv[1:]
if len(args) < 2:
    raise SystemExit(__doc__)
glb, out = args[0], args[1]
width, height = (int(args[2]), int(args[3])) if len(args) > 3 else (1200, 800)
lens = float(args[4]) if len(args) > 4 else 40.0
azimuth, elevation = (float(args[5]), float(args[6])) if len(args) > 6 else (-35.0, 28.0)
samples = int(args[7]) if len(args) > 7 else 128

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
corners = [o.matrix_world @ mathutils.Vector(c) for o in meshes for c in o.bound_box]
if not corners:
    raise SystemExit("render_glb: the file holds no mesh")
lo = mathutils.Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners)))
hi = mathutils.Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))
middle, radius = (lo + hi) / 2, max((hi - lo).length / 2, 0.5)

scene = bpy.context.scene
data = bpy.data.cameras.new("cam")
data.lens, data.clip_end = lens, radius * 40
cam = bpy.data.objects.new("cam", data)
scene.collection.objects.link(cam)
field = 2 * math.atan(18 / lens)                                  # across the picture's wider side
reach = radius / math.sin(field / 2) * 1.08
turn, rise = math.radians(azimuth), math.radians(elevation)
cam.location = middle + reach * mathutils.Vector((math.cos(turn) * math.cos(rise), math.sin(turn) * math.cos(rise), math.sin(rise)))
cam.rotation_euler = (middle - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

bpy.ops.mesh.primitive_plane_add(size=radius * 12, location=(middle.x, middle.y, lo.z - 0.01))
plain = bpy.context.object
paint = bpy.data.materials.new("plain")
if paint.node_tree is None:                         # Blender 4; from 5 on a material is always nodes
    paint.use_nodes = True
bsdf = paint.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.10, 0.11, 0.13, 1.0)
bsdf.inputs["Roughness"].default_value = 1.0
plain.data.materials.append(paint)

lamp = bpy.data.lights.new("sun", 'SUN')
lamp.energy, lamp.angle, lamp.color = 3.2, math.radians(2.0), (1.0, 0.93, 0.80)
sun = bpy.data.objects.new("sun", lamp)
scene.collection.objects.link(sun)
over = mathutils.Vector((math.cos(turn), math.sin(turn), 0))
sun.rotation_euler = (-(over * math.cos(math.radians(50)) + mathutils.Vector((0, 0, math.sin(math.radians(50)))))).to_track_quat('-Z', 'Y').to_euler()

scene.world = bpy.data.worlds.new("sky")
if scene.world.node_tree is None:
    scene.world.use_nodes = True
background = scene.world.node_tree.nodes["Background"]
background.inputs[0].default_value = (0.45, 0.62, 1.0, 1.0)
background.inputs[1].default_value = 0.42 / math.pi          # a level white surface gets 0.42 from it, as the arena's sky did

scene.render.engine = 'CYCLES'
try:
    scene.cycles.device = 'GPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):                 # the type must be chosen before devices count
        try:
            prefs.compute_device_type = kind
            break
        except TypeError:
            continue
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type in ('OPTIX', 'CUDA')
except Exception as error:
    scene.cycles.device = 'CPU'
    print("GPU setup failed, CPU:", error)
scene.cycles.samples, scene.cycles.use_denoising = samples, True
scene.view_settings.view_transform = 'Standard'             # what the arena's pictures used: exposure times the colour, clipped
scene.view_settings.exposure = -0.2
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.image_settings.file_format = 'JPEG' if out.lower().endswith((".jpg", ".jpeg")) else 'PNG'
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"rendered {out}  {width}x{height}  lens {lens:g}  from {azimuth:g}/{elevation:g}  {samples} samples  "
      f"model box x {lo.x:.1f}..{hi.x:.1f} y {lo.y:.1f}..{hi.y:.1f} z {lo.z:.1f}..{hi.z:.1f}")
