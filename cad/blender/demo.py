"""Blender demo of the VacController: turntable, exploded view, then a running pulse cycle.

Build the scene and save vaccontroller_demo.blend next to this file:
    blender --background --python cad/blender/demo.py
Also render:
    blender --background --python cad/blender/demo.py -- --still     one PNG of the exploded view
    blender --background --python cad/blender/demo.py -- --render    the full animation (MP4)
Or open Blender, go to the Scripting tab, open this file and press Run Script.

Works with Blender 3.6 to 5.x. Needs the files made by cad/build_cad.py (manifest.json, parts/).

Timeline (24 fps, 336 frames, 14 s):
    1-60     closed box, camera starts orbiting
    60-110   explodes into its parts
    110-160  hold exploded
    160-210  reassembles
    210-310  running: status LED on, gauge needle pulses with each stroke, pump vibrates
    310-336  STOP pressed: needle drops to zero, LED off
"""
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(bpy.context.space_data.text.filepath if bpy.context.space_data and
                                       getattr(bpy.context.space_data, "text", None) and
                                       bpy.context.space_data.text.filepath else __file__))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MM = 0.001
FPS, END = 24, 336
F_EXPLODE, F_EXPLODED, F_REASSEMBLE, F_ASSEMBLED = 60, 110, 160, 210
F_RUN, F_STOP = 210, 310

with open(os.path.join(HERE, "manifest.json")) as f:
    MAN = json.load(f)


# ------------------------------------------------------------------ helpers

def set_input(node, names, value):
    """Principled BSDF socket names changed across Blender versions; try each."""
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return node.inputs[n]
    return None


def material(name, rgb, rough=0.55, metal=0.0, transmission=0.0, alpha=1.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    set_input(b, ["Base Color"], (*rgb, 1))
    set_input(b, ["Roughness"], rough)
    set_input(b, ["Metallic"], metal)
    if transmission:
        set_input(b, ["Transmission Weight", "Transmission"], transmission)
    if alpha < 1:
        set_input(b, ["Alpha"], alpha)
        if hasattr(m, "blend_method"):
            m.blend_method = "BLEND"
    if emission:
        set_input(b, ["Emission Color", "Emission"], (*emission, 1))
        set_input(b, ["Emission Strength"], 0.0)
    return m


def import_stl(path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):           # Blender 4.2+
        bpy.ops.wm.stl_import(filepath=path, global_scale=MM)
    else:                                           # older built-in add-on
        bpy.ops.import_mesh.stl(filepath=path, global_scale=MM)
    new = [o for o in bpy.data.objects if o not in before]
    return new[0]


def smooth(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))   # 4.1+
    except Exception:
        bpy.ops.object.shade_smooth()
        if hasattr(obj.data, "use_auto_smooth"):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(35)


def key_loc(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def set_engine(scene):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            return eng
        except TypeError:
            continue
    scene.render.engine = "CYCLES"
    return "CYCLES"


def vacuum_curve(t):
    """Demo vacuum (kPa) at time t seconds after start: soft-started 'Stroke' pattern."""
    period, duty, level = 1.5, 0.55, 12.0
    soft = min(1.0, 0.3 + 0.7 * t / 3.0)
    ph = (t % period) / period
    if ph < duty:
        return level * soft * (1 - math.exp(-ph / duty * 4))
    peak = level * soft * (1 - math.exp(-4))
    return peak * math.exp(-(ph - duty) * period * 9)


# ------------------------------------------------------------------ scene

def clear_scene():
    # Not read_factory_settings(): that would also delete this script when run from the Text editor.
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves):
        for item in list(coll):
            coll.remove(item)


def build():
    clear_scene()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, END
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    engine = set_engine(scene)

    objs = {}
    for p in MAN["parts"]:
        o = import_stl(os.path.join(HERE, p["file"]))
        o.name = p["name"]
        smooth(o)
        n = p["name"]
        rgb = tuple(p["color"])
        if n in ("vent_valve", "relief_valve"):
            mat = material(n, rgb, 0.3, 1.0)
        elif n in ("gauge", "pump_motor"):
            mat = material(n, rgb, 0.25, 1.0)
        elif n == "tubing":
            mat = material(n, rgb, 0.15, 0.0, transmission=0.7, alpha=0.85)
        elif n == MAN["led_name"]:
            mat = material(n, rgb, 0.3, emission=(0.1, 1.0, 0.3))
        elif n == "gauge_face":
            mat = material(n, rgb, 0.4)
        else:
            mat = material(n, rgb, 0.6 if p["group"] == "printed" else 0.45)
        o.data.materials.append(mat)
        objs[n] = (o, p)

    # Gauge needle (pivot at the gauge centre, points along +Y at zero vacuum before the offset).
    gc = [c * MM for c in MAN["gauge_center"]]
    r = MAN["gauge_radius"] * MM * 0.85
    mesh = bpy.data.meshes.new("needle")
    mesh.from_pydata([(-0.0007, 0, 0), (0.0007, 0, 0), (0, r, 0), (0, -0.003, 0)], [], [(0, 1, 2), (1, 0, 3)])
    needle = bpy.data.objects.new("gauge_needle", mesh)
    scene.collection.objects.link(needle)
    needle.location = (gc[0], gc[1], gc[2] + 0.0006)
    needle.data.materials.append(material("needle", (0.85, 0.05, 0.05), 0.4))
    objs["gauge_needle"] = (needle, {"explode": objs["gauge_face"][1]["explode"]})

    # The bought cylinder on its stand (clear acrylic look) + a hose to the box.
    c = MAN["cylinder"]
    bpy.ops.mesh.primitive_cylinder_add(radius=c["radius"] * MM, depth=c["length"] * MM, vertices=64,
                                        location=((c["start"][0] + c["length"] / 2) * MM, c["start"][1] * MM, c["start"][2] * MM),
                                        rotation=(0, math.pi / 2, 0))
    cylinder = bpy.context.active_object
    cylinder.name = "cylinder_bought"
    bpy.ops.object.shade_smooth()
    cylinder.data.materials.append(material("acrylic", (0.9, 0.95, 1.0), 0.05, transmission=0.95, alpha=0.25))
    hp = [v * MM for v in MAN["hose_port"]]
    curve = bpy.data.curves.new("hose", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.003
    sp = curve.splines.new("BEZIER")
    sp.bezier_points.add(1)
    end = ((c["start"][0] + c["length"]) * MM, c["start"][1] * MM, c["start"][2] * MM)
    for bp, co, h in ((sp.bezier_points[0], hp, (0, -0.08, 0)), (sp.bezier_points[1], end, (0.08, 0, 0))):
        bp.co = co
        bp.handle_left = tuple(a - b for a, b in zip(co, h))
        bp.handle_right = tuple(a + b for a, b in zip(co, h))
    hose = bpy.data.objects.new("hose", curve)
    scene.collection.objects.link(hose)
    hose.data.materials.append(objs["tubing"][0].data.materials[0])

    # Floor, lights, world.
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, -0.0005))
    bpy.context.active_object.data.materials.append(material("floor", (0.18, 0.19, 0.21), 0.8))
    # Watts for a desk-sized scene; much more and the dark plastic renders white.
    for name, loc, energy, size in (("key", (0.45, -0.35, 0.55), 14, 0.4), ("fill", (-0.4, -0.25, 0.3), 4, 0.6),
                                    ("rim", (0.0, 0.5, 0.45), 9, 0.4)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        scene.collection.objects.link(lo)
        tc = lo.constraints.new("TRACK_TO")
        tc.target = None  # set below once the target exists
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.06, 1)
    scene.world = world

    # Camera on an orbiting rig, aimed at the box centre.
    bx, by, bz = (v * MM for v in MAN["box"])
    target = bpy.data.objects.new("cam_target", None)
    target.location = (bx / 2 - 0.05, by / 2, bz / 2 + 0.01)  # nudged towards the cylinder stand
    scene.collection.objects.link(target)
    rig = bpy.data.objects.new("cam_rig", None)
    rig.location = target.location
    scene.collection.objects.link(rig)
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.lens = 42
    cam.parent = rig
    cam.location = (0, -0.72, 0.42)  # far enough to keep the exploded lid in frame
    scene.collection.objects.link(cam)
    scene.camera = cam
    for o in [cam] + [o for o in scene.objects if o.type == "LIGHT"]:
        tc = o.constraints.get("Track To") or o.constraints.new("TRACK_TO")
        tc.target = target
        tc.track_axis = "TRACK_NEGATIVE_Z"
        tc.up_axis = "UP_Y"
    rig.rotation_euler = (0, 0, math.radians(-35))
    rig.keyframe_insert("rotation_euler", frame=1)
    rig.rotation_euler = (0, 0, math.radians(-35 + 300))
    rig.keyframe_insert("rotation_euler", frame=END)
    for fc in rig.animation_data.action.fcurves if hasattr(rig.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    # Explode and reassemble.
    for name, (o, p) in objs.items():
        home = tuple(o.location)
        off = tuple(home[i] + p["explode"][i] * MM * 1.4 for i in range(3))
        for f, loc in ((1, home), (F_EXPLODE, home), (F_EXPLODED, off), (F_REASSEMBLE, off), (F_ASSEMBLED, home)):
            key_loc(o, f, loc)

    # Running: needle follows the vacuum, pump shakes, LED glows. Then STOP.
    full_scale_kpa, sweep = 100.0, math.radians(270)  # 0 to -100 kPa gauge, 270 degree dial
    zero_angle = sweep / 2
    pump = [objs[n][0] for n in MAN["pump_parts"]]
    pump_home = [tuple(o.location) for o in pump]
    for f in range(1, END + 1):
        if F_RUN <= f < F_STOP:
            t = (f - F_RUN) / FPS
            kpa = vacuum_curve(t)
            pumping = ((t % 1.5) / 1.5) < 0.55
        elif f >= F_STOP:
            t = (F_STOP - F_RUN) / FPS
            kpa = vacuum_curve(t) * math.exp(-(f - F_STOP) / 3)
            pumping = False
        else:
            kpa, pumping = 0.0, False
        needle.rotation_euler = (0, 0, zero_angle - sweep * kpa / full_scale_kpa)
        needle.keyframe_insert("rotation_euler", frame=f)
        if f >= F_RUN - 1:
            for o, h in zip(pump, pump_home):
                jitter = 0.00025 * math.sin(f * 2.7) if pumping else 0.0
                o.location = (h[0], h[1], h[2] + jitter)
                o.keyframe_insert("location", frame=f)

    led_mat = objs[MAN["led_name"]][0].data.materials[0]
    strength = set_input(led_mat.node_tree.nodes["Principled BSDF"], ["Emission Strength"], 0.0)
    if strength is not None:
        for f, v in ((F_RUN - 1, 0.0), (F_RUN, 25.0), (F_STOP, 25.0), (F_STOP + 1, 0.0)):
            strength.default_value = v
            strength.keyframe_insert("default_value", frame=f)

    cap = objs[MAN["stop_cap"]][0]
    home = tuple(cap.location)
    for f, dz in ((F_STOP - 3, 0.0), (F_STOP, -0.002), (F_STOP + 6, -0.002), (F_STOP + 10, 0.0)):
        key_loc(cap, f, (home[0], home[1], home[2] + dz))

    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    out = os.path.join(HERE, "vaccontroller_demo.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"Saved {out} (engine {engine})")
    return scene


scene = build()

if "--still" in ARGS:
    scene.frame_set(135)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(HERE, "render", "exploded.png")
    bpy.ops.render.render(write_still=True)
    print("Rendered", scene.render.filepath)

if "--render" in ARGS:
    os.makedirs(os.path.join(HERE, "render"), exist_ok=True)
    try:
        if hasattr(scene.render.image_settings, "media_type"):  # Blender 5.x: pick video first
            scene.render.image_settings.media_type = "VIDEO"
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.filepath = os.path.join(HERE, "render", "vaccontroller_demo.mp4")
    except Exception:  # no video output in this build: write numbered PNGs instead
        if hasattr(scene.render.image_settings, "media_type"):
            scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = os.path.join(HERE, "render", "frame_")
    bpy.ops.render.render(animation=True)
    print("Rendered animation to", scene.render.filepath)
