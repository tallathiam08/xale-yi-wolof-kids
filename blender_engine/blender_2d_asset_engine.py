import bpy
import json
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT / "blender_engine"
ASSETS = ENGINE / "assets"

OUTPUT_DIR = ENGINE / "renders"

WIDTH = 640
HEIGHT = 360
FPS = 30
FRAMES = 150


ACTION_FILE = {
    "idle": "idle.png",
    "talk": "talk.png",
    "walk": "walk.png",
    "run": "run.png",
    "jump": "jump.png",
    "dance": "dance.png",
    "clap": "gesture.png",
    "wave": "gesture.png",
    "gesture": "gesture.png",
    "laugh": "gesture.png",
    "surprised": "gesture.png",
    "sad": "idle.png",
}


CHARACTER_HEIGHT = {
    "Samba": 3.75,
    "Ibrahima": 3.75,
    "Awa": 3.75,
    "Toto": 3.05,
}


CAMERA_SCALE = {
    "wide": 7.0,
    "medium": 7.0,
    "close": 5.5,
    "follow": 7.4,
    "dance": 7.4,
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)


def load_image(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"❌ Image absente : {path}"
        )

    return bpy.data.images.load(
        str(path),
        check_existing=True
    )


def make_image_material(name, image):
    material = bpy.data.materials.get(name)

    if material is None:
        material = bpy.data.materials.new(name)

    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()

    output = nodes.new(
        "ShaderNodeOutputMaterial"
    )

    shader = nodes.new(
        "ShaderNodeBsdfPrincipled"
    )

    texture = nodes.new(
        "ShaderNodeTexImage"
    )

    texture.image = image

    shader.inputs["Roughness"].default_value = 1.0

    if "Specular IOR Level" in shader.inputs:
        shader.inputs[
            "Specular IOR Level"
        ].default_value = 0.0

    links.new(
        texture.outputs["Color"],
        shader.inputs["Base Color"]
    )

    if (
        "Alpha" in texture.outputs
        and "Alpha" in shader.inputs
    ):
        links.new(
            texture.outputs["Alpha"],
            shader.inputs["Alpha"]
        )

    links.new(
        shader.outputs["BSDF"],
        output.inputs["Surface"]
    )

    # Blender 4.5+
    if hasattr(
        material,
        "surface_render_method"
    ):
        material.surface_render_method = (
            "DITHERED"
        )

    return material


def create_plane(
    name,
    image_path,
    width,
    height,
    x,
    y,
    z,
    material_prefix,
):
    image = load_image(image_path)

    material = make_image_material(
        f"{material_prefix}_{name}",
        image,
    )

    bpy.ops.mesh.primitive_plane_add(
        size=2,
        location=(x, y, z),
        rotation=(math.radians(90), 0, 0),
    )

    obj = bpy.context.object
    obj.name = name

    obj.scale = (
        width / 2,
        height / 2,
        1,
    )

    obj.data.materials.append(material)

    return obj



def background_path(location):
    mapping = {
        "school": "school.jpg",
        "bus": "bus.jpg",
        "neighborhood": "neighborhood.jpg",
        "park": "park.jpg",
        "classroom": "classroom.jpg",
        "home": "neighborhood.jpg",
        "market": "neighborhood.jpg",
        "street": "neighborhood.jpg",
        "beach": "neighborhood.jpg",
        "kitchen": "classroom.jpg",
        "bedroom": "classroom.jpg",
        "celebration": "school.jpg",
    }

    filename = mapping.get(
        location,
        "school.jpg",
    )

    return (
        ASSETS
        / "backgrounds"
        / filename
    )


def create_background(location):
    path = background_path(location)

    return create_plane(
        name="XALE_BACKGROUND",
        image_path=path,
        width=12.8,
        height=7.2,
        x=0,
        y=2.0,
        z=3.6,
        material_prefix="BG",
    )


def get_action_image(character, action):
    action = str(action).lower()

    filename = ACTION_FILE.get(
        action,
        "idle.png",
    )

    path = (
        ASSETS
        / "characters"
        / character
        / filename
    )

    if not path.exists():
        fallback = (
            ASSETS
            / "characters"
            / character
            / "front.png"
        )

        if not fallback.exists():
            raise FileNotFoundError(
                f"❌ Asset absent pour "
                f"{character}: {path}"
            )

        return fallback

    return path


def animate_character(
    obj,
    action,
    base_x,
    index,
):
    action = str(action).lower()

    obj.location.z = (
        obj.dimensions.z / 2
    )

    # --------------------------------------------------------
    # IDLE / TALK : petit mouvement naturel
    # --------------------------------------------------------

    if action in {
        "idle",
        "talk",
        "laugh",
        "gesture",
        "wave",
        "clap",
        "surprised",
        "sad",
    }:
        for frame, offset in [
            (1, 0.00),
            (20, 0.06),
            (40, 0.00),
            (60, 0.05),
            (80, 0.00),
            (100, 0.06),
            (120, 0.00),
            (140, 0.05),
            (150, 0.00),
        ]:
            obj.location.z = (
                obj.dimensions.z / 2
                + offset
            )

            obj.keyframe_insert(
                data_path="location",
                frame=frame,
            )

    # --------------------------------------------------------
    # TALK : petite pulsation
    # --------------------------------------------------------

    if action == "talk":
        for frame, scale in [
            (1, 1.00),
            (10, 1.025),
            (20, 1.00),
            (30, 1.02),
            (40, 1.00),
            (50, 1.025),
            (60, 1.00),
            (70, 1.02),
            (80, 1.00),
            (90, 1.025),
            (100, 1.00),
            (110, 1.02),
            (120, 1.00),
            (130, 1.025),
            (150, 1.00),
        ]:
            obj.scale = (
                obj.scale.x
                / max(obj.scale.x, 0.0001)
                * scale,
                obj.scale.y
                / max(obj.scale.y, 0.0001)
                * scale,
                1,
            )

            obj.keyframe_insert(
                data_path="scale",
                frame=frame,
            )

    # --------------------------------------------------------
    # JUMP
    # --------------------------------------------------------

    elif action == "jump":
        ground = obj.location.z

        for frame, jump in [
            (1, 0.0),
            (25, 0.0),
            (45, 0.65),
            (60, 0.0),
            (80, 0.65),
            (95, 0.0),
            (115, 0.65),
            (130, 0.0),
            (150, 0.0),
        ]:
            obj.location.z = ground + jump

            obj.keyframe_insert(
                data_path="location",
                frame=frame,
            )

    # --------------------------------------------------------
    # RUN / WALK
    # --------------------------------------------------------

    elif action in {
        "run",
        "walk",
    }:
        direction = 1 if index % 2 == 0 else -1

        start_x = base_x
        end_x = (
            base_x
            + direction * 1.6
        )

        for frame, x in [
            (1, start_x),
            (50, start_x + direction * 0.5),
            (100, start_x + direction * 1.1),
            (150, end_x),
        ]:
            obj.location.x = x

            obj.keyframe_insert(
                data_path="location",
                frame=frame,
            )

    # --------------------------------------------------------
    # DANCE
    # --------------------------------------------------------

    elif action == "dance":
        ground = obj.location.z

        for frame, z, rot in [
            (1, ground, -0.05),
            (15, ground + 0.12, 0.10),
            (30, ground, -0.10),
            (45, ground + 0.12, 0.10),
            (60, ground, -0.10),
            (75, ground + 0.12, 0.10),
            (90, ground, -0.10),
            (105, ground + 0.12, 0.10),
            (120, ground, -0.10),
            (135, ground + 0.12, 0.10),
            (150, ground, 0.0),
        ]:
            obj.location.z = z
            obj.rotation_euler.z = rot

            obj.keyframe_insert(
                data_path="location",
                frame=frame,
            )

            obj.keyframe_insert(
                data_path="rotation_euler",
                frame=frame,
            )

    # --------------------------------------------------------
    # Linear interpolation sensible
    # --------------------------------------------------------

    if obj.animation_data:
        action_data = obj.animation_data.action

        if action_data:
            for curve in action_data.fcurves:
                for point in curve.keyframe_points:
                    point.interpolation = "BEZIER"


def create_camera(camera_type):
    bpy.ops.object.camera_add(
        location=(0, -20, 2.4),
        rotation=(math.radians(90), 0, 0),
    )

    camera = bpy.context.object
    camera.name = "XaleCamera"

    camera.data.type = "ORTHO"

    camera.data.ortho_scale = CAMERA_SCALE.get(
        camera_type,
        7.0,
    )

    camera.data.clip_start = 0.1
    camera.data.clip_end = 1000

    bpy.context.scene.camera = camera

    return camera



def configure_scene(data):
    scene = bpy.context.scene

    scene.render.engine = (
        "BLENDER_EEVEE_NEXT"
    )

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100

    scene.render.fps = FPS

    scene.frame_start = 1
    scene.frame_end = FRAMES

    scene.render.image_settings.file_format = (
        "FFMPEG"
    )

    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.audio_codec = "NONE"

    scene.render.ffmpeg.constant_rate_factor = (
        "HIGH"
    )

    scene.render.film_transparent = False

    scene.world.color = (
        0.35,
        0.55,
        0.75,
    )

    try:
        scene.view_settings.view_transform = "Standard"
    except Exception:
        pass

    scene.view_settings.look = (
        "None"
    )

    scene["xale_location"] = data.get(
        "location",
        "school",
    )

    scene["xale_scene_type"] = data.get(
        "scene_type",
        "story",
    )

    scene["xale_music"] = bool(
        data.get("music", False)
    )


def build_scene(
    data,
    output_file,
):
    clear_scene()

    location = data.get(
        "location",
        "school",
    )

    camera_type = data.get(
        "camera",
        "wide",
    )

    characters = data.get(
        "characters",
        [],
    )

    create_background(location)

    create_camera(camera_type)

    positions = [
        -4.35,
        -1.45,
        1.45,
        4.35,
    ]

    for index, info in enumerate(
        characters[:4]
    ):
        name = info.get(
            "name",
            "Samba",
        )

        action = info.get(
            "action",
            "idle",
        )

        if name == "Toto":
            height = 2.15
        else:
            height = 3.35

        image_path = get_action_image(
            name,
            action,
        )

        image = load_image(image_path)

        ratio = (
            image.size[0]
            / image.size[1]
        )

        width = height * ratio

        x = positions[index]

        plane = create_plane(
            name=f"{name}_Sprite",
            image_path=image_path,
            width=width,
            height=height,
            x=x,
            y=0,
            z=height / 2,
            material_prefix=name,
        )

        # Les enfants sont posés sur le sol.
        # Toto est légèrement plus bas.
        plane.location.z = height / 2

        # Profondeur contrôlée : tous devant le décor.
        plane.location.y = -0.5 - (index * 0.03)

        animate_character(
            plane,
            action,
            x,
            index,
        )

    configure_scene(data)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=str(output_file)
    )

    print("")
    print("==============================")
    print("✅ XALE YI 2D ASSET ENGINE")
    print("==============================")
    print(
        f"📍 Lieu       : {location}"
    )
    print(
        f"🎥 Caméra     : {camera_type}"
    )
    print(
        f"👥 Personnages: "
        f"{len(characters[:4])}"
    )

    for info in characters[:4]:
        print(
            f"   {info.get('name')} "
            f"→ {info.get('action', 'idle')}"
        )

    print(
        f"💾 {output_file}"
    )
    print("==============================")


def main():
    scene_file = (
        ENGINE
        / "scenes"
        / "test_scene.json"
    )

    if not scene_file.exists():
        raise FileNotFoundError(
            f"❌ Scène absente : {scene_file}"
        )

    with open(
        scene_file,
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    build_scene(
        data,
        ENGINE
        / "renders"
        / "xale_asset_scene.blend",
    )


if __name__ == "__main__":
    main()
