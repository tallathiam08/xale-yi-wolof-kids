import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


PROJECT = Path(__file__).resolve().parent
ASSETS = PROJECT / "blender_engine" / "assets"
CHARACTERS = ASSETS / "characters"
BACKGROUNDS = ASSETS / "backgrounds"


W, H = 640, 360
FPS = 30
DURATION = 5
FRAMES = FPS * DURATION


CHAR_HEIGHT = {
    "Samba": 235,
    "Ibrahima": 235,
    "Awa": 235,
    "Toto": 145,
}


BASE_X = {
    "Samba": 125,
    "Ibrahima": 270,
    "Awa": 415,
    "Toto": 535,
}


BACKGROUND_MAP = {
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


def load_rgba(path):
    img = Image.open(path).convert("RGBA")

    alpha = img.getchannel("A")
    bbox = alpha.getbbox()

    if bbox:
        img = img.crop(bbox)

    return img


def background_for(location):
    filename = BACKGROUND_MAP.get(
        location,
        "school.jpg",
    )

    path = BACKGROUNDS / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Décor absent : {path}"
        )

    return load_rgba(path)


def character_asset(name, action):
    folder = CHARACTERS / name

    if not folder.exists():
        raise FileNotFoundError(
            f"Personnage absent : {folder}"
        )

    # Priorité aux vraies poses si elles existent.
    candidates = []

    action = str(action).lower()

    aliases = {
        "speak": "talk",
        "clap": "gesture",
        "wave": "gesture",
        "laugh": "gesture",
        "surprised": "gesture",
        "sad": "idle",
    }

    action = aliases.get(action, action)

    candidates.append(
        folder / f"{action}.png"
    )

    candidates.append(
        folder / "front.png"
    )

    for path in candidates:
        if path.exists():
            return load_rgba(path)

    raise FileNotFoundError(
        f"Aucun asset pour {name}"
    )


def fit_background(img):
    return ImageOps.fit(
        img,
        (W, H),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def sprite_size(img, name):
    target_h = CHAR_HEIGHT.get(
        name,
        220,
    )

    ratio = (
        img.width / img.height
    )

    return (
        max(1, int(target_h * ratio)),
        target_h,
    )


def motion(name, action, frame):
    t = frame / (FRAMES - 1)

    base_x = BASE_X.get(
        name,
        W // 2,
    )

    action = str(action).lower()

    bob = math.sin(
        t * math.pi * 4
    ) * 2.5

    x = base_x
    y = 300 + bob
    angle = 0.0
    scale = 1.0

    if action == "dance":
        x += math.sin(t * math.pi * 4) * 12
        y += abs(
            math.sin(t * math.pi * 4)
        ) * -10
        angle = (
            math.sin(t * math.pi * 4)
            * 5
        )

    elif action == "jump":
        y += -(
            math.sin(t * math.pi * 3)
            ** 2
        ) * 55

    elif action == "run":
        direction = 1 if name != "Toto" else -1
        x += (
            direction
            * math.sin(t * math.pi * 2)
            * 55
        )
        angle = (
            math.sin(t * math.pi * 6)
            * 3
        )

    elif action == "walk":
        x += (
            math.sin(t * math.pi * 2)
            * 30
        )
        y += abs(
            math.sin(t * math.pi * 4)
        ) * -4

    elif action == "talk":
        scale += (
            math.sin(t * math.pi * 12)
            * 0.018
        )
        y += (
            math.sin(t * math.pi * 12)
            * 1.5
        )

    elif action == "wave":
        angle = (
            math.sin(t * math.pi * 8)
            * 6
        )

    elif action == "gesture":
        angle = (
            math.sin(t * math.pi * 4)
            * 4
        )

    return x, y, angle, scale


def place_sprite(canvas, img, name, action, frame):
    target_w, target_h = sprite_size(
        img,
        name,
    )

    img = img.resize(
        (target_w, target_h),
        Image.Resampling.LANCZOS,
    )

    x, y, angle, scale = motion(
        name,
        action,
        frame,
    )

    if abs(scale - 1.0) > 0.001:
        sw = int(img.width * scale)
        sh = int(img.height * scale)

        img = img.resize(
            (max(1, sw), max(1, sh)),
            Image.Resampling.LANCZOS,
        )

    if abs(angle) > 0.01:
        img = img.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

    # y = position des pieds
    px = int(
        x - img.width / 2
    )

    py = int(
        y - img.height
    )

    canvas.alpha_composite(
        img,
        (px, py),
    )


def camera_transform(img, camera, frame):
    t = frame / max(1, FRAMES - 1)

    zooms = {
        "wide": 1.00,
        "medium": 1.06,
        "close": 1.12,
        "follow": 1.08,
        "dance": 1.05,
    }

    zoom = zooms.get(
        camera,
        1.00,
    )

    # Petit mouvement cinématique.
    if camera == "dance":
        zoom += (
            math.sin(t * math.pi * 2)
            * 0.015
        )

    if camera == "follow":
        pan = int(
            math.sin(t * math.pi)
            * 20
        )
    else:
        pan = 0

    nw = int(W * zoom)
    nh = int(H * zoom)

    if nw == W and nh == H:
        return img

    enlarged = img.resize(
        (nw, nh),
        Image.Resampling.LANCZOS,
    )

    left = (
        (nw - W) // 2
        + pan
    )

    top = (
        (nh - H) // 2
    )

    left = max(
        0,
        min(left, nw - W),
    )

    top = max(
        0,
        min(top, nh - H),
    )

    return enlarged.crop(
        (
            left,
            top,
            left + W,
            top + H,
        )
    )


def render_frame(scene, frame):
    bg = fit_background(
        background_for(
            scene.get(
                "location",
                "school",
            )
        )
    )

    canvas = bg.copy()

    characters = scene.get(
        "characters",
        [],
    )

    # Personnages arrière → avant.
    for char in characters:
        name = char.get(
            "name",
            "Samba",
        )

        action = char.get(
            "action",
            "idle",
        )

        sprite = character_asset(
            name,
            action,
        )

        place_sprite(
            canvas,
            sprite,
            name,
            action,
            frame,
        )

    camera = scene.get(
        "camera",
        "wide",
    )

    return camera_transform(
        canvas,
        camera,
        frame,
    ).convert("RGB")


def render_preview(scene_file, output):
    with open(
        scene_file,
        encoding="utf-8",
    ) as f:
        scene = json.load(f)

    frame = 75

    image = render_frame(
        scene,
        frame,
    )

    image.save(
        output,
        quality=95,
    )

    print(
        f"✅ Preview : {output}"
    )


def render_video(scene_file, output):
    with open(
        scene_file,
        encoding="utf-8",
    ) as f:
        scene = json.load(f)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="xale2d_"
    ) as tmp:
        tmp = Path(tmp)

        for frame in range(FRAMES):
            img = render_frame(
                scene,
                frame,
            )

            img.save(
                tmp / f"frame_{frame:04d}.jpg",
                quality=92,
            )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(
                    tmp / "frame_%04d.jpg"
                ),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
        )

    print(
        f"✅ Vidéo : {output}"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scene",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--preview",
        action="store_true",
    )

    args = parser.parse_args()

    scene = Path(args.scene)
    output = Path(args.output)

    if args.preview:
        render_preview(
            scene,
            output,
        )
    else:
        render_video(
            scene,
            output,
        )


if __name__ == "__main__":
    main()
