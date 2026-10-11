import bpy
import json
import math
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT / "blender_engine"
SCENE_FILE = ENGINE / "scenes" / "test_scene.json"
OUTPUT_FILE = ENGINE / "renders" / "test_scene.blend"


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        pass


def material(name, color):
    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = (*color, 1.0)
    return mat


def create_plane(name, x, y, z, sx, sy, mat):
    bpy.ops.mesh.primitive_plane_add(
        size=2,
        location=(x, y, z)
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = (sx, sy, 1)

    if mat:
        obj.data.materials.append(mat)

    return obj


def create_circle(name, x, y, z, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=radius,
        location=(x, y, z)
    )

    obj = bpy.context.object
    obj.name = name

    if mat:
        obj.data.materials.append(mat)

    return obj


def create_character(name, x, y, z, body_color, skin_color, scale=1.0):
    skin = material(f"{name}_skin", skin_color)
    body = material(f"{name}_body", body_color)
    black = material(f"{name}_black", (0.03, 0.03, 0.03))

    parts = {}

    # Corps
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        radius=1.0,
        location=(x, y, z + 1.0)
    )
    torso = bpy.context.object
    torso.name = f"{name}_body"
    torso.scale = (0.65, 0.35, 0.95)
    torso.data.materials.append(body)

    # Tête
    head = create_circle(
        f"{name}_head",
        x,
        y,
        z + 2.15,
        0.52,
        skin,
    )

    # Yeux
    for eye_x in (-0.18, 0.18):
        eye = create_circle(
            f"{name}_eye",
            x + eye_x,
            y - 0.47,
            z + 2.27,
            0.06,
            black,
        )

    # Bouche
    mouth = create_plane(
        f"{name}_mouth",
        x,
        y - 0.49,
        z + 2.02,
        0.10,
        0.035,
        black,
    )

    # Bras
    for side, sign in (("L", -1), ("R", 1)):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=24,
            radius=0.14,
            depth=0.95,
            location=(
                x + sign * 0.78,
                y,
                z + 1.1
            )
        )

        arm = bpy.context.object
        arm.name = f"{name}_arm_{side}"
        arm.rotation_euler[1] = sign * math.radians(20)
        arm.data.materials.append(body)

    # Jambes
    for side, sign in (("L", -1), ("R", 1)):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=24,
            radius=0.16,
            depth=0.9,
            location=(
                x + sign * 0.24,
                y,
                z + 0.15
            )
        )

        leg = bpy.context.object
        leg.name = f"{name}_leg_{side}"
        leg.data.materials.append(black)

    parts["head"] = head
    parts["mouth"] = mouth

    # Petite animation de respiration / mouvement
    frame_start = 1
    frame_end = 150

    torso.location.z = z + 1.0
    torso.keyframe_insert(data_path="location", frame=frame_start)

    torso.location.z = z + 1.05
    torso.keyframe_insert(data_path="location", frame=frame_start + 15)

    torso.location.z = z + 1.0
    torso.keyframe_insert(data_path="location", frame=frame_start + 30)

    torso.location.z = z + 1.05
    torso.keyframe_insert(data_path="location", frame=frame_start + 45)

    torso.location.z = z + 1.0
    torso.keyframe_insert(data_path="location", frame=frame_end)

    # Animation de bouche
    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=1)

    mouth.scale.y = 1.5
    mouth.keyframe_insert(data_path="scale", frame=10)

    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=20)

    mouth.scale.y = 1.3
    mouth.keyframe_insert(data_path="scale", frame=30)

    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=40)

    mouth.scale.y = 1.4
    mouth.keyframe_insert(data_path="scale", frame=50)

    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=60)

    mouth.scale.y = 1.2
    mouth.keyframe_insert(data_path="scale", frame=75)

    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=90)

    mouth.scale.y = 1.4
    mouth.keyframe_insert(data_path="scale", frame=110)

    mouth.scale.y = 0.35
    mouth.keyframe_insert(data_path="scale", frame=frame_end)

    return parts


def create_environment(location):
    ground = material(
        "ground",
        (0.15, 0.55, 0.20)
    )

    sky = material(
        "sky",
        (0.40, 0.75, 1.0)
    )

    wall = material(
        "school_wall",
        (1.0, 0.75, 0.25)
    )

    create_plane(
        "Ground",
        0,
        0.8,
        -0.35,
        7,
        5,
        ground,
    )

    create_plane(
        "Sky",
        0,
        1.2,
        4,
        8,
        5,
        sky,
    )

    if location == "school":
        create_plane(
            "SchoolBuilding",
            0,
            0.2,
            1.8,
            3.8,
            1.5,
            wall,
        )


def create_camera():
    bpy.ops.object.camera_add(
        location=(0, -12, 4.5),
        rotation=(math.radians(78), 0, 0)
    )

    camera = bpy.context.object
    camera.name = "MainCamera"

    bpy.context.scene.camera = camera

    camera.data.lens = 48

    return camera


def create_light():
    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -4, 7)
    )

    light = bpy.context.object
    light.name = "KeyLight"
    light.data.energy = 1200
    light.data.shape = "DISK"
    light.data.size = 8


def build_scene(data):
    reset_scene()

    location = data.get("location", "school")
    characters = data.get("characters", [])

    create_environment(location)
    create_camera()
    create_light()

    palette = [
        ((0.20, 0.55, 0.95), (0.55, 0.32, 0.18)),
        ((0.95, 0.35, 0.45), (0.45, 0.23, 0.12)),
        ((0.30, 0.80, 0.45), (0.30, 0.17, 0.08)),
    ]

    positions = [-2.4, 0, 2.4]

    for i, character in enumerate(characters[:3]):
        body_color, skin_color = palette[i % len(palette)]

        create_character(
            character.get("name", f"Character_{i+1}"),
            positions[i],
            0,
            0,
            body_color,
            skin_color,
            1.0,
        )

    scene = bpy.context.scene

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 50

    scene.render.image_settings.file_format = "PNG"

    scene.frame_start = 1
    scene.frame_end = 150
    scene.render.fps = 30

    scene.render.filepath = str(
        ENGINE / "renders" / "test_scene_"
    )

    scene.world.color = (
        0.35,
        0.55,
        0.75,
    )

    scene["location"] = location
    scene["action"] = data.get("action", "")
    scene["emotion"] = data.get("emotion", "")
    scene["music"] = bool(data.get("music", False))

    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_FILE)
    )

    print("✅ Scène Blender créée")
    print(f"📍 Lieu : {location}")
    print(f"👧👦 Personnages : {len(characters)}")
    print(f"🎬 Action : {data.get('action', '')}")
    print(f"😊 Émotion : {data.get('emotion', '')}")
    print(f"🎵 Musique : {data.get('music', False)}")
    print(f"💾 Fichier : {OUTPUT_FILE}")


def main():
    if not SCENE_FILE.exists():
        raise FileNotFoundError(
            f"Scène JSON introuvable : {SCENE_FILE}"
        )

    with open(SCENE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    build_scene(data)


if __name__ == "__main__":
    main()
