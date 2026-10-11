import bpy
import json
import math
import sys
from pathlib import Path


# ============================================================
# XALE YI — BLENDER CARTOON ENGINE V1
# ============================================================

PROJECT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT / "blender_engine"
SCENE_FILE = ENGINE / "scenes" / "test_scene.json"
OUTPUT_DIR = ENGINE / "renders"

FPS = 30
DURATION = 5
FRAME_END = FPS * DURATION

WIDTH = 1280
HEIGHT = 720


# ============================================================
# COLORS
# ============================================================

COLORS = {
    "sky": (0.42, 0.72, 1.00, 1.0),
    "grass": (0.20, 0.62, 0.24, 1.0),
    "road": (0.18, 0.18, 0.20, 1.0),
    "school": (0.95, 0.72, 0.25, 1.0),
    "wall": (0.96, 0.86, 0.65, 1.0),
    "tree": (0.12, 0.58, 0.18, 1.0),
    "tree_dark": (0.08, 0.37, 0.10, 1.0),
    "brown": (0.34, 0.17, 0.07, 1.0),
    "black": (0.025, 0.025, 0.025, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "red": (0.92, 0.15, 0.18, 1.0),
    "yellow": (1.0, 0.82, 0.10, 1.0),
    "blue": (0.10, 0.38, 0.90, 1.0),
    "pink": (1.0, 0.34, 0.56, 1.0),
    "green": (0.10, 0.72, 0.36, 1.0),
    "orange": (1.0, 0.44, 0.08, 1.0),
}


CHARACTER_COLORS = {
    "Samba": {
        "shirt": (0.10, 0.40, 0.95, 1.0),
        "shorts": (0.07, 0.08, 0.15, 1.0),
        "skin": (0.42, 0.22, 0.11, 1.0),
        "hair": (0.035, 0.018, 0.012, 1.0),
    },
    "Awa": {
        "shirt": (0.95, 0.25, 0.55, 1.0),
        "shorts": (0.95, 0.72, 0.15, 1.0),
        "skin": (0.46, 0.25, 0.13, 1.0),
        "hair": (0.035, 0.018, 0.012, 1.0),
    },
    "Ibrahima": {
        "shirt": (0.12, 0.70, 0.34, 1.0),
        "shorts": (0.15, 0.20, 0.30, 1.0),
        "skin": (0.40, 0.20, 0.10, 1.0),
        "hair": (0.025, 0.015, 0.010, 1.0),
    },
    "Toto": {
        "fur": (0.52, 0.30, 0.13, 1.0),
        "dark": (0.20, 0.10, 0.04, 1.0),
        "white": (0.95, 0.90, 0.80, 1.0),
    },
}


# ============================================================
# HELPERS
# ============================================================

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablock in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        pass


def mat(name, color):
    material = bpy.data.materials.get(name)

    if material is None:
        material = bpy.data.materials.new(name)

    material.diffuse_color = color
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.85

    return material


def cube(
    name,
    location,
    scale,
    material=None,
    parent=None,
):
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    if material:
        obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def sphere(
    name,
    location,
    scale,
    material=None,
    parent=None,
):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    if material:
        obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def cylinder(
    name,
    location,
    radius,
    depth,
    material=None,
    parent=None,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24,
        radius=radius,
        depth=depth,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name

    if material:
        obj.data.materials.append(material)

    if parent:
        obj.parent = parent

    return obj


def keyframe(obj, data_path, frame):
    obj.keyframe_insert(
        data_path=data_path,
        frame=frame,
    )


def linear_animation(obj):
    if not obj.animation_data:
        return

    if not obj.animation_data.action:
        return

    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"


def look_at(camera, target=(0, 0, 2.5)):
    direction = (
        target[0] - camera.location.x,
        target[1] - camera.location.y,
        target[2] - camera.location.z,
    )

    import mathutils

    camera.rotation_euler = direction_to_rotation(direction)


def direction_to_rotation(direction):
    import mathutils

    direction = mathutils.Vector(direction)
    return direction.to_track_quat("-Z", "Y").to_euler()


# ============================================================
# CHARACTER BASE
# ============================================================

def create_humanoid(name, x, y=0, z=0):
    colors = CHARACTER_COLORS.get(
        name,
        CHARACTER_COLORS["Samba"],
    )

    root = bpy.data.objects.new(
        f"{name}_ROOT",
        None,
    )

    bpy.context.collection.objects.link(root)
    root.location = (x, y, z)

    shirt = mat(
        f"{name}_shirt",
        colors["shirt"],
    )

    shorts = mat(
        f"{name}_shorts",
        colors["shorts"],
    )

    skin = mat(
        f"{name}_skin",
        colors["skin"],
    )

    hair = mat(
        f"{name}_hair",
        colors["hair"],
    )

    black = mat(
        f"{name}_black",
        COLORS["black"],
    )

    white = mat(
        f"{name}_white",
        COLORS["white"],
    )

    # torso
    torso = sphere(
        f"{name}_torso",
        (x, y, z + 1.65),
        (0.62, 0.34, 0.85),
        shirt,
    )
    torso.parent = root

    # shorts
    pants = cube(
        f"{name}_shorts",
        (x, y, z + 0.90),
        (0.55, 0.28, 0.32),
        shorts,
    )
    pants.parent = root

    # head
    head = sphere(
        f"{name}_head",
        (x, y, z + 2.55),
        (0.58, 0.42, 0.62),
        skin,
    )
    head.parent = root

    # hair
    hair_obj = sphere(
        f"{name}_hair",
        (x, y - 0.03, z + 2.92),
        (0.61, 0.44, 0.32),
        hair,
    )
    hair_obj.parent = root

    # eyes
    for side in (-1, 1):
        eye = sphere(
            f"{name}_eye_{side}",
            (x + side * 0.18, y - 0.40, z + 2.66),
            (0.055, 0.025, 0.075),
            white,
        )
        eye.parent = root

        pupil = sphere(
            f"{name}_pupil_{side}",
            (x + side * 0.18, y - 0.425, z + 2.66),
            (0.025, 0.012, 0.035),
            black,
        )
        pupil.parent = root

    # mouth
    mouth = sphere(
        f"{name}_mouth",
        (x, y - 0.43, z + 2.37),
        (0.11, 0.025, 0.045),
        black,
    )
    mouth.parent = root

    # neck
    neck = cylinder(
        f"{name}_neck",
        (x, y, z + 2.05),
        0.14,
        0.20,
        skin,
    )
    neck.parent = root

    # arm controllers
    left_shoulder = bpy.data.objects.new(
        f"{name}_left_shoulder",
        None,
    )
    right_shoulder = bpy.data.objects.new(
        f"{name}_right_shoulder",
        None,
    )

    bpy.context.collection.objects.link(left_shoulder)
    bpy.context.collection.objects.link(right_shoulder)

    left_shoulder.parent = root
    right_shoulder.parent = root

    left_shoulder.location = (-0.52, 0, 2.10)
    right_shoulder.location = (0.52, 0, 2.10)

    # arms are parented to shoulder controllers
    left_arm = cube(
        f"{name}_left_arm",
        (-0.52, 0, 1.66),
        (0.14, 0.16, 0.55),
        shirt,
    )

    right_arm = cube(
        f"{name}_right_arm",
        (0.52, 0, 1.66),
        (0.14, 0.16, 0.55),
        shirt,
    )

    left_arm.parent = left_shoulder
    right_arm.parent = right_shoulder

    left_arm.location = (0, 0, -0.44)
    right_arm.location = (0, 0, -0.44)

    # hands
    left_hand = sphere(
        f"{name}_left_hand",
        (-0.52, 0, 1.05),
        (0.16, 0.16, 0.16),
        skin,
    )
    right_hand = sphere(
        f"{name}_right_hand",
        (0.52, 0, 1.05),
        (0.16, 0.16, 0.16),
        skin,
    )

    left_hand.parent = left_shoulder
    right_hand.parent = right_shoulder

    left_hand.location = (0, 0, -0.85)
    right_hand.location = (0, 0, -0.85)

    # leg controllers
    left_leg = bpy.data.objects.new(
        f"{name}_left_leg",
        None,
    )

    right_leg = bpy.data.objects.new(
        f"{name}_right_leg",
        None,
    )

    bpy.context.collection.objects.link(left_leg)
    bpy.context.collection.objects.link(right_leg)

    left_leg.parent = root
    right_leg.parent = root

    left_leg.location = (-0.25, 0, 0.82)
    right_leg.location = (0.25, 0, 0.82)

    left_leg_mesh = cube(
        f"{name}_left_leg_mesh",
        (-0.25, 0, 0.38),
        (0.16, 0.17, 0.48),
        shorts,
    )

    right_leg_mesh = cube(
        f"{name}_right_leg_mesh",
        (0.25, 0, 0.38),
        (0.16, 0.17, 0.48),
        shorts,
    )

    left_leg_mesh.parent = left_leg
    right_leg_mesh.parent = right_leg

    left_leg_mesh.location = (0, 0, -0.45)
    right_leg_mesh.location = (0, 0, -0.45)

    # shoes
    shoe_mat = black

    left_shoe = sphere(
        f"{name}_left_shoe",
        (-0.25, -0.05, -0.02),
        (0.28, 0.42, 0.13),
        shoe_mat,
    )

    right_shoe = sphere(
        f"{name}_right_shoe",
        (0.25, -0.05, -0.02),
        (0.28, 0.42, 0.13),
        shoe_mat,
    )

    left_shoe.parent = root
    right_shoe.parent = root

    return {
        "root": root,
        "mouth": mouth,
        "head": head,
        "left_shoulder": left_shoulder,
        "right_shoulder": right_shoulder,
        "left_leg": left_leg,
        "right_leg": right_leg,
    }


# ============================================================
# TOTO
# ============================================================

def create_toto(x, y=0, z=0):
    colors = CHARACTER_COLORS["Toto"]

    fur = mat("Toto_fur", colors["fur"])
    dark = mat("Toto_dark", colors["dark"])
    white = mat("Toto_white", colors["white"])
    black = mat("Toto_black", COLORS["black"])

    root = bpy.data.objects.new(
        "Toto_ROOT",
        None,
    )

    bpy.context.collection.objects.link(root)
    root.location = (x, y, z)

    body = sphere(
        "Toto_body",
        (x, y, z + 0.65),
        (0.72, 0.40, 0.45),
        fur,
    )
    body.parent = root

    head = sphere(
        "Toto_head",
        (x + 0.55, y - 0.02, z + 0.95),
        (0.45, 0.38, 0.42),
        fur,
    )
    head.parent = root

    # muzzle
    muzzle = sphere(
        "Toto_muzzle",
        (x + 0.84, y - 0.04, z + 0.88),
        (0.22, 0.22, 0.18),
        white,
    )
    muzzle.parent = root

    # nose
    nose = sphere(
        "Toto_nose",
        (x + 0.98, y - 0.25, z + 0.92),
        (0.08, 0.06, 0.06),
        black,
    )
    nose.parent = root

    # eyes
    for offset in (0.42, 0.67):
        eye = sphere(
            "Toto_eye",
            (x + offset, y - 0.34, z + 1.08),
            (0.055, 0.025, 0.055),
            black,
        )
        eye.parent = root

    # ears
    for side in (-1, 1):
        ear = sphere(
            f"Toto_ear_{side}",
            (x + 0.48, y + side * 0.24, z + 1.30),
            (0.16, 0.13, 0.28),
            dark,
        )
        ear.parent = root

    # legs
    for side in (-1, 1):
        for front in (-1, 1):
            leg = cylinder(
                f"Toto_leg_{side}_{front}",
                (
                    x + 0.35 + front * 0.30,
                    y + side * 0.22,
                    z + 0.28,
                ),
                0.09,
                0.45,
                dark,
            )
            leg.parent = root

    return {
        "root": root,
        "head": head,
    }


# ============================================================
# ACTIONS
# ============================================================

def reset_pose(character):
    root = character["root"]

    root.rotation_euler = (0, 0, 0)
    root.scale = (1, 1, 1)

    for name in (
        "left_shoulder",
        "right_shoulder",
        "left_leg",
        "right_leg",
    ):
        if name in character:
            character[name].rotation_euler = (0, 0, 0)


def action_idle(character):
    root = character["root"]

    root.location.z += 0
    keyframe(root, "location", 1)

    root.location.z += 0.04
    keyframe(root, "location", 20)

    root.location.z -= 0.04
    keyframe(root, "location", 40)

    root.location.z += 0.04
    keyframe(root, "location", 60)

    root.location.z = root.location.z
    keyframe(root, "location", FRAME_END)


def action_talk(character):
    root = character["root"]
    mouth = character["mouth"]

    action_idle(character)

    for frame, scale_z in [
        (1, 0.5),
        (8, 1.4),
        (16, 0.45),
        (24, 1.5),
        (32, 0.45),
        (40, 1.3),
        (48, 0.45),
        (56, 1.5),
        (64, 0.45),
        (72, 1.35),
        (80, 0.45),
        (88, 1.4),
        (96, 0.45),
        (104, 1.25),
        (112, 0.45),
        (120, 1.35),
        (128, 0.45),
        (FRAME_END, 0.45),
    ]:
        mouth.scale.z = scale_z
        keyframe(mouth, "scale", frame)


def action_wave(character):
    action_idle(character)

    arm = character["right_shoulder"]

    for frame, angle in [
        (1, 0),
        (15, math.radians(-35)),
        (30, math.radians(35)),
        (45, math.radians(-35)),
        (60, math.radians(35)),
        (75, math.radians(-35)),
        (90, 0),
        (FRAME_END, 0),
    ]:
        arm.rotation_euler.y = angle
        keyframe(arm, "rotation_euler", frame)


def action_clap(character):
    left = character["left_shoulder"]
    right = character["right_shoulder"]

    for frame, left_angle, right_angle in [
        (1, 0.0, 0.0),
        (15, -0.55, 0.55),
        (30, -0.05, 0.05),
        (45, -0.55, 0.55),
        (60, -0.05, 0.05),
        (75, -0.55, 0.55),
        (90, -0.05, 0.05),
        (105, -0.55, 0.55),
        (120, 0.0, 0.0),
        (FRAME_END, 0.0, 0.0),
    ]:
        left.rotation_euler.y = left_angle
        right.rotation_euler.y = right_angle

        keyframe(left, "rotation_euler", frame)
        keyframe(right, "rotation_euler", frame)


def action_dance(character):
    root = character["root"]
    left_arm = character["left_shoulder"]
    right_arm = character["right_shoulder"]
    left_leg = character["left_leg"]
    right_leg = character["right_leg"]

    for frame, z, rot, la, ra, ll, rl in [
        (1, 0.0, 0.0, -0.5, 0.5, 0.15, -0.15),
        (15, 0.12, -0.12, 0.7, -0.7, -0.25, 0.25),
        (30, 0.0, 0.12, -0.7, 0.7, 0.25, -0.25),
        (45, 0.12, -0.12, 0.7, -0.7, -0.25, 0.25),
        (60, 0.0, 0.12, -0.7, 0.7, 0.25, -0.25),
        (75, 0.12, -0.12, 0.7, -0.7, -0.25, 0.25),
        (90, 0.0, 0.12, -0.7, 0.7, 0.25, -0.25),
        (105, 0.12, -0.12, 0.7, -0.7, -0.25, 0.25),
        (120, 0.0, 0.12, -0.7, 0.7, 0.25, -0.25),
        (135, 0.12, -0.12, 0.7, -0.7, -0.25, 0.25),
        (FRAME_END, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ]:
        root.location.z = z
        root.rotation_euler.y = rot

        left_arm.rotation_euler.y = la
        right_arm.rotation_euler.y = ra

        left_leg.rotation_euler.y = ll
        right_leg.rotation_euler.y = rl

        keyframe(root, "location", frame)
        keyframe(root, "rotation_euler", frame)

        keyframe(left_arm, "rotation_euler", frame)
        keyframe(right_arm, "rotation_euler", frame)

        keyframe(left_leg, "rotation_euler", frame)
        keyframe(right_leg, "rotation_euler", frame)


def action_jump(character):
    root = character["root"]

    ground = root.location.z

    for frame, offset in [
        (1, 0.0),
        (20, 0.0),
        (40, 1.0),
        (55, 1.25),
        (70, 0.6),
        (85, 0.0),
        (FRAME_END, 0.0),
    ]:
        root.location.z = ground + offset
        keyframe(root, "location", frame)


def action_run(character):
    root = character["root"]

    start_x = root.location.x

    for frame, x in [
        (1, start_x),
        (45, start_x + 1.5),
        (90, start_x + 3.0),
        (135, start_x + 4.5),
        (FRAME_END, start_x + 5.0),
    ]:
        root.location.x = x
        keyframe(root, "location", frame)


def action_sad(character):
    root = character["root"]
    head = character["head"]

    root.rotation_euler.y = math.radians(-8)
    head.rotation_euler.x = math.radians(10)

    keyframe(root, "rotation_euler", 1)
    keyframe(head, "rotation_euler", 1)

    root.rotation_euler.y = math.radians(8)
    keyframe(root, "rotation_euler", FRAME_END)


def action_surprised(character):
    root = character["root"]
    head = character["head"]
    mouth = character["mouth"]

    root.scale = (1, 1, 1)
    head.scale = (1.12, 1.12, 1.12)
    mouth.scale.z = 2.0

    keyframe(head, "scale", 1)
    keyframe(mouth, "scale", 1)

    head.scale = (1, 1, 1)
    mouth.scale.z = 0.8

    keyframe(head, "scale", 35)
    keyframe(mouth, "scale", 35)

    keyframe(head, "scale", FRAME_END)
    keyframe(mouth, "scale", FRAME_END)


ACTION_MAP = {
    "idle": action_idle,
    "talk": action_talk,
    "speak": action_talk,
    "wave": action_wave,
    "clap": action_clap,
    "dance": action_dance,
    "jump": action_jump,
    "run": action_run,
    "sad": action_sad,
    "surprised": action_surprised,
}


# ============================================================
# BACKGROUNDS
# ============================================================

def make_tree(x, y, z):
    brown = mat("tree_trunk", COLORS["brown"])
    green = mat("tree_green", COLORS["tree"])
    green_dark = mat("tree_dark", COLORS["tree_dark"])

    cylinder(
        "tree_trunk",
        (x, y, z + 1.3),
        0.25,
        2.6,
        brown,
    )

    sphere(
        "tree_top_1",
        (x, y, z + 2.9),
        (1.0, 0.8, 1.1),
        green,
    )

    sphere(
        "tree_top_2",
        (x + 0.55, y, z + 2.7),
        (0.7, 0.7, 0.8),
        green_dark,
    )


def make_background(location):
    sky = mat("BG_sky", COLORS["sky"])
    ground_mat = mat(
        "BG_ground",
        COLORS["grass"],
    )

    wall_mat = mat(
        "BG_wall",
        COLORS["wall"],
    )

    road_mat = mat(
        "BG_road",
        COLORS["road"],
    )

    # Sky wall
    cube(
        "Background",
        (0, 2.5, 4.5),
        (12, 0.15, 5.0),
        sky,
    )

    if location == "school":
        cube(
            "SchoolBuilding",
            (0, 1.4, 3.3),
            (5.0, 0.45, 2.4),
            wall_mat,
        )

        cube(
            "SchoolDoor",
            (0, 0.85, 1.8),
            (0.7, 0.12, 1.1),
            road_mat,
        )

        for x in (-2.5, 2.5):
            cube(
                "SchoolWindow",
                (x, 0.82, 3.3),
                (0.8, 0.10, 0.65),
                mat(
                    "window_blue",
                    (0.15, 0.55, 0.95, 1),
                ),
            )

        ground = cube(
            "SchoolGround",
            (0, 1.0, 0),
            (10, 3, 0.12),
            ground_mat,
        )

        make_tree(-6, 0.5, 0)
        make_tree(6, 0.5, 0)

    elif location == "park":
        cube(
            "ParkGround",
            (0, 1.0, 0),
            (10, 3, 0.12),
            ground_mat,
        )

        make_tree(-5.5, 0.5, 0)
        make_tree(5.5, 0.5, 0)
        make_tree(3.8, 1.0, 0)

    elif location == "market":
        ground = cube(
            "MarketGround",
            (0, 1.0, 0),
            (10, 3, 0.12),
            ground_mat,
        )

        for x, c in [
            (-5, COLORS["red"]),
            (-2.5, COLORS["yellow"]),
            (0, COLORS["blue"]),
            (2.5, COLORS["green"]),
            (5, COLORS["pink"]),
        ]:
            cube(
                "MarketStand",
                (x, 0.8, 1.8),
                (1.0, 0.35, 1.4),
                mat(f"market_{x}", c),
            )

    elif location == "bus":
        ground = cube(
            "BusGround",
            (0, 1.0, 0),
            (10, 3, 0.12),
            road_mat,
        )

        bus_mat = mat(
            "BusYellow",
            COLORS["yellow"],
        )

        cube(
            "BusBody",
            (0, 1.0, 2.1),
            (4.4, 1.0, 1.5),
            bus_mat,
        )

        window_mat = mat(
            "BusWindow",
            (0.15, 0.55, 0.90, 1),
        )

        for x in (-2.7, -1.0, 0.8, 2.5):
            cube(
                "BusWindow",
                (x, -0.02, 2.4),
                (0.65, 0.08, 0.55),
                window_mat,
            )

    elif location == "beach":
        sand = mat(
            "Sand",
            (0.90, 0.74, 0.43, 1),
        )

        cube(
            "Beach",
            (0, 1.0, 0),
            (10, 3, 0.12),
            sand,
        )

        ocean = mat(
            "Ocean",
            (0.05, 0.55, 0.85, 1),
        )

        cube(
            "Ocean",
            (5.5, 2.0, 1.0),
            (4.5, 0.4, 0.8),
            ocean,
        )

    elif location == "home":
        cube(
            "HomeFloor",
            (0, 1.0, 0),
            (10, 3, 0.12),
            ground_mat,
        )

        cube(
            "HomeWall",
            (0, 1.4, 3.6),
            (5.5, 0.35, 2.3),
            wall_mat,
        )

        cube(
            "Table",
            (0, 0.5, 1.0),
            (2.5, 1.0, 0.15),
            mat("table", COLORS["brown"]),
        )

    else:
        cube(
            "DefaultGround",
            (0, 1.0, 0),
            (10, 3, 0.12),
            ground_mat,
        )


# ============================================================
# CAMERA
# ============================================================

def create_camera(camera_type):
    bpy.ops.object.camera_add(
        location=(0, -18, 4.2)
    )

    camera = bpy.context.object
    camera.name = "MainCamera"

    camera.data.type = "ORTHO"

    if camera_type == "close":
        camera.data.ortho_scale = 5.0
    elif camera_type == "medium":
        camera.data.ortho_scale = 6.5
    else:
        camera.data.ortho_scale = 8.0

    camera.rotation_euler = direction_to_rotation(
        (0, 0, 2.8)
    )

    bpy.context.scene.camera = camera

    # simple camera motion
    if camera_type == "follow":
        camera.location.x = -3
        keyframe(camera, "location", 1)

        camera.location.x = 3
        keyframe(camera, "location", FRAME_END)

    elif camera_type == "dance":
        camera.location.x = -1.0
        camera.rotation_euler.z = math.radians(-2)

        keyframe(camera, "location", 1)
        keyframe(camera, "rotation_euler", 1)

        camera.location.x = 1.0
        camera.rotation_euler.z = math.radians(2)

        keyframe(camera, "location", FRAME_END)
        keyframe(camera, "rotation_euler", FRAME_END)

    return camera


# ============================================================
# LIGHT
# ============================================================

def create_lighting():
    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -6, 8),
    )

    light = bpy.context.object
    light.name = "KeyLight"
    light.data.energy = 1100
    light.data.shape = "DISK"
    light.data.size = 8

    light.rotation_euler = direction_to_rotation(
        (0, 0, 2)
    )


# ============================================================
# SCENE BUILD
# ============================================================

def normalize_characters(raw_characters):
    result = []

    for item in raw_characters:
        if isinstance(item, str):
            result.append({
                "name": item,
                "action": "idle",
                "emotion": "happy",
            })
        else:
            result.append({
                "name": item.get("name", "Samba"),
                "action": item.get("action", "idle"),
                "emotion": item.get("emotion", "happy"),
            })

    return result


def build_scene(data):
    clear_scene()

    location = data.get(
        "location",
        "school",
    )

    camera_type = data.get(
        "camera",
        "wide",
    )

    raw_characters = data.get(
        "characters",
        [],
    )

    characters = normalize_characters(
        raw_characters
    )

    make_background(location)
    create_lighting()
    camera = create_camera(camera_type)

    positions = [-3.0, 0.0, 3.0]

    created = []

    for index, info in enumerate(
        characters[:4]
    ):
        name = info["name"]
        action = str(
            info.get(
                "action",
                "idle",
            )
        ).lower()

        x = positions[
            index
            if index < len(positions)
            else -1
        ]

        if name.lower() == "toto":
            obj = create_toto(x)
        else:
            obj = create_humanoid(
                name,
                x,
            )

        reset_pose(obj)

        action_fn = ACTION_MAP.get(
            action,
            action_idle,
        )

        action_fn(obj)

        created.append(
            (
                name,
                action,
            )
        )

    # Scene metadata
    scene = bpy.context.scene

    scene["xale_location"] = location
    scene["xale_camera"] = camera_type
    scene["xale_music"] = bool(
        data.get("music", False)
    )
    scene["xale_emotion"] = data.get(
        "emotion",
        "happy",
    )
    scene["xale_scene_type"] = data.get(
        "scene_type",
        "story",
    )

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 50

    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END

    # Eevee for better visuals while remaining practical
    scene.render.engine = "BLENDER_EEVEE_NEXT"

    scene.render.image_settings.file_format = "PNG"

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    scene.render.filepath = str(
        OUTPUT_DIR / "frame_"
    )

    # World
    scene.world.color = (
        0.35,
        0.55,
        0.75,
    )

    blend_path = (
        OUTPUT_DIR /
        "xale_scene_v1.blend"
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=str(blend_path)
    )

    print("")
    print("======================================")
    print("✅ XALE YI BLENDER ENGINE V1")
    print("======================================")
    print(f"📍 Lieu       : {location}")
    print(f"🎥 Caméra     : {camera_type}")
    print(f"🎞️ Durée      : {DURATION}s")
    print(f"👥 Personnages: {len(created)}")
    print(f"🎵 Musique    : {data.get('music', False)}")
    print("")

    for name, action in created:
        print(
            f"   {name:<12} → {action}"
        )

    print("")
    print(f"💾 Blend      : {blend_path}")
    print("======================================")
    print("")

    return blend_path


# ============================================================
# MAIN
# ============================================================

def main():
    if not SCENE_FILE.exists():
        raise FileNotFoundError(
            f"JSON introuvable : {SCENE_FILE}"
        )

    with open(
        SCENE_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    build_scene(data)


if __name__ == "__main__":
    main()
