"""Run inside Blender; consumes a reviewed, triangulated scene JSON. No pip inside Blender."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--frames", type=int, default=192)
    parser.add_argument("--size", type=int, default=1280)
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.frames < 8 or args.size < 64: raise ValueError("Need >=8 frames and >=64px")
    data = json.loads(Path(args.scene).read_text())
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.fps = 24
    scene.frame_start = 1; scene.frame_end = args.frames
    scene.render.resolution_x = args.size
    scene.render.resolution_y = round(args.size * 9 / 16 / 2) * 2
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_stamp_filename = False
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_WORKBENCH" if args.draft else "BLENDER_EEVEE"
    scene.world = bpy.data.worlds.new("Studio world")
    scene.world.color = (.55, .55, .55)
    scene.view_settings.view_transform = "Standard"
    if args.draft:
        shading = scene.display.shading
        shading.light = "STUDIO"; shading.color_type = "TEXTURE"
        shading.background_type = "WORLD"; shading.show_shadows = True
        shading.show_cavity = True
    material = bpy.data.materials.new("Exact print artwork")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    image = bpy.data.images.load(data["texture"]); image.pack()
    image.filepath = "//artwork.png"
    for packed in image.packed_files: packed.filepath = "//artwork.png"
    # Startup file-browser state can otherwise retain the operator's home directory.
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "FILE_BROWSER" and space.params:
                    space.params.directory = b"//"
    tex = nodes.new("ShaderNodeTexImage"); tex.image = image; nodes.active = tex
    material.node_tree.links.new(tex.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"])
    nodes.get("Principled BSDF").inputs["Roughness"].default_value = .72
    panels = {p["id"]: p for p in data["panels"]}
    pivots, meshes, origins = {}, [], {}
    w, h = data["canvas_mm"]

    def build(pid):
        if pid in pivots: return pivots[pid]
        p = panels[pid]
        parent = build(p["parent"]) if p.get("parent") else None
        a = Vector((*p["hinge"][0], 0)) * .001 if parent else Vector((0, 0, 0))
        pivot = bpy.data.objects.new(pid + " / HINGE", None)
        scene.collection.objects.link(pivot)
        pivot.parent = parent
        pivot.location = a - (origins[p["parent"]] if parent else Vector((0, 0, 0)))
        origins[pid] = a; pivots[pid] = pivot
        verts, faces = [], []
        for tri in p["triangles"]:
            start = len(verts)
            verts.extend([(x*.001-a.x, y*.001-a.y, -a.z) for x, y in tri])
            faces.append((start, start+1, start+2))
        mesh = bpy.data.meshes.new(pid); mesh.from_pydata(verts, [], faces); mesh.update()
        uv = mesh.uv_layers.new(name="Print sheet UV")
        for face in mesh.polygons:
            for vi, li in zip(face.vertices, face.loop_indices):
                v = mesh.vertices[vi].co + a
                uv.data[li].uv = (v.x*1000/w, v.y*1000/h)
        ob = bpy.data.objects.new(pid, mesh); scene.collection.objects.link(ob)
        ob.parent = pivot; ob.data.materials.append(material); meshes.append(ob)
        if parent:
            axis = Vector((p["hinge"][1][0]-p["hinge"][0][0], p["hinge"][1][1]-p["hinge"][0][1], 0)).normalized()
            pivot.rotation_mode = "AXIS_ANGLE"
            start, end = p.get("stage", [.1, .6])
            for frame in range(1, args.frames+1):
                t = (frame-1)/(args.frames-1)
                u = max(0, min(1, (t-start)/(end-start))); u = u*u*(3-2*u)
                pivot.rotation_axis_angle = (math.radians(p["angle_deg"])*u, *axis)
                pivot.keyframe_insert("rotation_axis_angle", frame=frame)
        return pivot

    for pid in panels: build(pid)
    bpy.ops.object.camera_add()
    cam = bpy.context.object; cam.name = "Fold and full orbit camera"
    cam.data.type = "ORTHO"; cam.data.clip_start = .0001; cam.data.clip_end = 100
    scene.camera = cam
    witnesses = []
    for frame in range(1, args.frames+1):
        scene.frame_set(frame); bpy.context.view_layer.update()
        pts = [ob.matrix_world @ v.co for ob in meshes for v in ob.data.vertices]
        lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
        hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
        center = (lo+hi)/2; radius = max((hi-lo).length/2, .001)
        t = (frame-1)/(args.frames-1)
        theta = 2*math.pi*max(0, (t-.75)/.25)
        direction = Vector((math.sin(theta+.45), -math.cos(theta+.45), .75)).normalized()
        cam.location = center + direction * radius * 5
        cam.rotation_euler = (center-cam.location).to_track_quat("-Z", "Y").to_euler()
        aspect = scene.render.resolution_x/scene.render.resolution_y
        cam.data.ortho_scale = radius * 2 * max(1, aspect) * 1.18
        cam.keyframe_insert("location", frame=frame); cam.keyframe_insert("rotation_euler", frame=frame)
        cam.data.keyframe_insert("ortho_scale", frame=frame)
        from bpy_extras.object_utils import world_to_camera_view
        bpy.context.view_layer.update()
        projected = [world_to_camera_view(scene, cam, p) for p in pts]
        if any(not (.01 < p.x < .99 and .01 < p.y < .99 and p.z > 0) for p in projected):
            raise ValueError(f"Camera clips model at frame {frame}")
        if frame in {1, args.frames//2, args.frames}:
            witnesses.append({"frame": frame, "bounds_m": [list(lo), list(hi)]})
    # Large studio lights; texture and cut holes belong to the same manufacturing coordinates.
    for xyz in [(-.5,-.5,1),(.8,-.2,.8),(0,.8,.9)]:
        bpy.ops.object.light_add(type="AREA", location=xyz)
        ob = bpy.context.object; ob.data.energy = 20; ob.data.size = 1
        ob.rotation_euler = (center-ob.location).to_track_quat("-Z", "Y").to_euler()
    scene["geometry_sha256"] = data["geometry_report"]["geometry_sha256"]
    scene["limitations"] = "Kinematic visualization. Lock engagement, collision and paper-thickness fit require separate review."
    scene.render.filepath = "//frames/frame-"
    (out/"frames").mkdir(exist_ok=True)
    scene.frame_set(args.frames)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"folding.blend"))
    (out/"scene-check.json").write_text(json.dumps({"geometry_sha256": scene["geometry_sha256"],
        "camera_all_frames_inside": True, "frames": args.frames, "fps": 24,
        "resolution": [scene.render.resolution_x,scene.render.resolution_y],
        "milestones": witnesses, "physical_fit_verified": False}, indent=2))
    bpy.ops.render.render(animation=True)


if __name__ == "__main__": main()
