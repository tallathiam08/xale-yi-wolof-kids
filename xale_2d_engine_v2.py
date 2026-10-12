import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageFilter


PROJECT = Path(__file__).resolve().parent
ASSETS = PROJECT / "blender_engine" / "assets"
CHARACTERS = ASSETS / "characters"
BACKGROUNDS = ASSETS / "backgrounds"

W = int(os.getenv("XALE_WIDTH", "1280"))
H = int(os.getenv("XALE_HEIGHT", "720"))
RENDER_FPS = int(os.getenv("XALE_RENDER_FPS", "20"))
OUTPUT_FPS = int(os.getenv("XALE_OUTPUT_FPS", "30"))
DURATION = 5
FRAMES = RENDER_FPS * DURATION

CHAR_HEIGHT = {
    "Samba": 360,
    "Ibrahima": 360,
    "Awa": 360,
    "Toto": 220,
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

ACTION_ALIASES = {
    "speak": "talk",
    "clap": "gesture",
    "laugh": "gesture",
    "surprised": "gesture",
    "sad": "idle",
    "wave": "gesture",
}

ACTION_FILES = {
    "idle": "idle.png",
    "talk": "talk.png",
    "walk": "walk.png",
    "run": "run.png",
    "jump": "jump.png",
    "dance": "dance.png",
    "gesture": "gesture.png",
}


def load_rgba(path):
    path = Path(path)
    img = Image.open(path).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img


def fit_background(path):
    img = load_rgba(path)
    return ImageOps.fit(
        img,
        (W, H),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def background_path(location):
    filename = BACKGROUND_MAP.get(location, "school.jpg")
    path = BACKGROUNDS / filename
    if not path.exists():
        raise FileNotFoundError(f"Décor absent : {path}")
    return path


def asset_path(name, action):
    folder = CHARACTERS / name
    if not folder.exists():
        raise FileNotFoundError(f"Personnage absent : {folder}")

    action = ACTION_ALIASES.get(
        str(action).lower(),
        str(action).lower(),
    )

    candidate = folder / ACTION_FILES.get(
        action,
        "front.png",
    )

    if not candidate.exists():
        candidate = folder / "front.png"

    if not candidate.exists():
        raise FileNotFoundError(f"Asset absent : {candidate}")

    return candidate


def sprite_dimensions(img, name):
    target_h = CHAR_HEIGHT.get(name, 330)
    ratio = img.width / max(1, img.height)
    return max(1, int(target_h * ratio)), target_h


def character_positions(names):
    count = len(names)

    # Composition centered, with smaller Toto.
    left = int(W * 0.12)
    right = int(W * 0.88)

    if count == 1:
        return [W // 2]

    step = (right - left) / (count - 1)
    return [int(left + i * step) for i in range(count)]


def speaker_for_frame(scene, frame):
    dialogues = scene.get("dialogue", [])
    if len(dialogues) < 2:
        return None
    return (
        dialogues[0].get("speaker")
        if frame < FRAMES / 2
        else dialogues[1].get("speaker")
    )


def motion(name, action, frame, index, count, speaker):
    t = frame / max(1, FRAMES - 1)
    phase = t * math.tau

    xs = character_positions(
        ["x"] * count
    )
    base_x = xs[index]

    action = str(action).lower()
    x = float(base_x)
    y = float(H - 24)
    angle = 0.0
    scale = 1.0

    # Natural idle movement.
    y += math.sin(phase * 2 + index * 0.7) * 3.0

    if name == speaker:
        scale *= 1.035

    if action == "talk":
        y += math.sin(phase * 8) * 2.0
        scale += math.sin(phase * 8) * 0.015

    elif action == "dance":
        x += math.sin(phase * 2.0 + index) * 18
        y -= abs(math.sin(phase * 4.0)) * 18
        angle = math.sin(phase * 2.0) * 5.0
        scale *= 1.02 + abs(math.sin(phase * 4.0)) * 0.02

    elif action == "jump":
        y -= (math.sin(math.pi * t * 3) ** 2) * 75
        angle = math.sin(phase * 3) * 2.5

    elif action == "run":
        direction = 1 if index % 2 == 0 else -1
        x += direction * math.sin(phase * 1.5) * 60
        y -= abs(math.sin(phase * 3)) * 8
        angle = math.sin(phase * 6) * 4

    elif action == "walk":
        direction = 1 if index % 2 == 0 else -1
        x += direction * math.sin(phase * 1.0) * 35
        y -= abs(math.sin(phase * 2)) * 5

    elif action == "gesture":
        angle = math.sin(phase * 4) * 4

    # Keep sprites inside the frame.
    if name == "Toto":
        x = max(70, min(W - 70, x))
    else:
        x = max(105, min(W - 105, x))

    return x, y, angle, scale


def add_shadow(canvas, x, foot_y, width, opacity=85):
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)

    sw = max(30, int(width * 0.42))
    sh = max(8, int(sw * 0.12))

    box = (
        int(x - sw / 2),
        int(foot_y - sh / 2),
        int(x + sw / 2),
        int(foot_y + sh / 2),
    )

    draw.ellipse(
        box,
        fill=(0, 0, 0, opacity),
    )

    shadow = shadow.filter(
        ImageFilter.GaussianBlur(5)
    )
    canvas.alpha_composite(shadow)


def place_character(
    canvas,
    sprite,
    name,
    action,
    frame,
    index,
    count,
    speaker,
):
    target_w, target_h = sprite_dimensions(
        sprite,
        name,
    )

    sprite = sprite.resize(
        (target_w, target_h),
        Image.Resampling.LANCZOS,
    )

    x, foot_y, angle, scale = motion(
        name,
        action,
        frame,
        index,
        count,
        speaker,
    )

    sw = max(1, int(sprite.width * scale))
    sh = max(1, int(sprite.height * scale))

    sprite = sprite.resize(
        (sw, sh),
        Image.Resampling.LANCZOS,
    )

    if abs(angle) > 0.01:
        sprite = sprite.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )

    add_shadow(
        canvas,
        x,
        foot_y,
        sprite.width,
    )

    px = int(x - sprite.width / 2)
    py = int(foot_y - sprite.height)

    canvas.alpha_composite(
        sprite,
        (px, py),
    )


def camera_transform(image, camera, frame, scene):
    t = frame / max(1, FRAMES - 1)

    zoom_map = {
        "wide": 1.00,
        "medium": 1.035,
        "close": 1.08,
        "follow": 1.06,
        "dance": 1.045,
    }

    zoom = zoom_map.get(
        camera,
        1.00,
    )

    if camera == "dance":
        zoom += math.sin(
            t * math.tau * 2
        ) * 0.012

    scale_w = int(W * zoom)
    scale_h = int(H * zoom)

    if scale_w == W and scale_h == H:
        return image

    enlarged = image.resize(
        (scale_w, scale_h),
        Image.Resampling.LANCZOS,
    )

    pan = 0

    if camera == "follow":
        pan = int(
            math.sin(t * math.pi) * W * 0.025
        )

    left = (scale_w - W) // 2 + pan
    top = (scale_h - H) // 2

    left = max(
        0,
        min(left, scale_w - W),
    )
    top = max(
        0,
        min(top, scale_h - H),
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
        background_path(
            scene.get("location", "school")
        )
    )

    canvas = bg.copy()

    characters = scene.get(
        "characters",
        [],
    )

    count = len(characters)
    speaker = speaker_for_frame(
        scene,
        frame,
    )

    for index, char in enumerate(
        characters
    ):
        name = char.get(
            "name",
            "Samba",
        )
        action = char.get(
            "action",
            "idle",
        )

        # The active speaker visibly talks.
        if name == speaker:
            action = "talk"

        sprite = load_rgba(
            asset_path(
                name,
                action,
            )
        )

        place_character(
            canvas,
            sprite,
            name,
            action,
            frame,
            index,
            count,
            speaker,
        )

    return camera_transform(
        canvas,
        scene.get("camera", "wide"),
        frame,
        scene,
    ).convert("RGB")


def render_preview(scene_file, output):
    with open(scene_file, encoding="utf-8") as f:
        scene = json.load(f)

    image = render_frame(
        scene,
        FRAMES // 2,
    )

    output = Path(output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        output,
        quality=95,
    )

    print(f"✅ Preview : {output}")


def render_scene(scene, output):
    output = Path(output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="xale2dv2_"
    ) as tmp:
        tmp = Path(tmp)

        for frame in range(FRAMES):
            image = render_frame(
                scene,
                frame,
            )

            image.save(
                tmp / f"frame_{frame:04d}.jpg",
                quality=92,
                subsampling=0,
            )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(RENDER_FPS),
                "-i",
                str(tmp / "frame_%04d.jpg"),
                "-vf",
                f"fps={OUTPUT_FPS}",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
        )

    print(f"✅ Vidéo : {output}")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", action="store_true")

    args = parser.parse_args()

    if args.preview:
        render_preview(
            Path(args.scene),
            Path(args.output),
        )
    else:
        with open(
            args.scene,
            encoding="utf-8",
        ) as f:
            scene = json.load(f)

        render_scene(
            scene,
            Path(args.output),
        )


if __name__ == "__main__":
    main()
