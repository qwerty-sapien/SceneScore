"""Portrait camera and render stage for the concrete kinetic_geometry_01 batch.

The existing directions driver owns computed-pose build/replay/verification.  This
small Blender-only companion only applies the packet's generated camera path and
renders portrait frames; it never changes actor motion or mechanics evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def packet(out: Path):
    return json.loads((out / "packet.json").read_text())


def look(camera, position, target):
    from mathutils import Vector
    camera.location = position
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = (Vector(target) - camera.location).to_track_quat("-Z", "Y")


def linear_keys(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(obj.animation_data.action_slot)
            if bag:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "BEZIER"


def apply_camera(out: Path):
    import bpy
    document = packet(out)
    bpy.ops.wm.open_mainfile(filepath=str(out / "scene.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    camera = scene.camera
    if camera is None:
        raise RuntimeError("camera missing")
    design = document.get("camera", {})
    path = design.get("path") or [[0, design.get("position", [10, -12, 9]), design.get("look_at", [0, 0, 2])],
                                   [document["duration_s"], design.get("position", [10, -12, 9]), design.get("look_at", [0, 0, 2])]]
    camera.data.type = "ORTHO"
    # Preserve the source driver's wide three-quarter coverage when changing its
    # landscape output to portrait; the subsequent camera track supplies diversity.
    camera.data.ortho_scale = float(design.get("ortho_scale", 8.0)) * 1.75
    for time_s, position, target in path:
        look(camera, position, target)
        frame = 1 + float(time_s) * 30
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    linear_keys(camera)
    scene["kinetic_geometry_camera"] = "packet-generated portrait composition"
    scene["approval"] = "pending human review"
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"), check_existing=False)
    (out / "camera.json").write_text(json.dumps({"status": "PASSED", "camera": camera.name,
        "path_keyframes": len(path), "portrait_ortho_scale": camera.data.ortho_scale,
        "scope": "generated camera only; actor mechanics transforms unchanged", "approval": None}, indent=2) + "\n")


def render(out: Path, profile: str):
    import bpy
    if profile not in ("proxy", "final"):
        raise ValueError("unknown profile")
    document = packet(out)
    bpy.ops.wm.open_mainfile(filepath=str(out / "scene.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    width, height = (360, 640) if profile == "proxy" else (1080, 1920)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.frame_start, scene.frame_end = 1, round(document["duration_s"] * 30)
    target = out / ("proxy_frames" if profile == "proxy" else "final_frames")
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("preserve earlier rendered frames: " + str(target))
    target.mkdir(exist_ok=True)
    scene.render.filepath = str(target / "frame_")
    bpy.ops.render.render(animation=True)
    (out / (profile + "_render.json")).write_text(json.dumps({"status": "PASSED", "profile": profile,
        "width": width, "height": height, "fps": 30, "frames": scene.frame_end,
        "directory": str(target), "approval": None}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("camera", "render"))
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--profile", choices=("proxy", "final"))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    out = args.out.resolve()
    if args.command == "camera":
        apply_camera(out)
    else:
        render(out, args.profile)
    print("KINETIC_GEOMETRY_RENDER_COMPLETE", args.command, flush=True)


if __name__ == "__main__":
    main()
