import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


EPISODE_FILE = Path("output/episode_github_generated.json")
OUTPUT_DIR = Path("output/cartoon_scenes")

WIDTH = 1280
HEIGHT = 720


def font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


TITLE_FONT = font(38)
SMALL_FONT = font(24)


def draw_background(draw, scene_text):
    text = scene_text.lower()

    if any(w in text for w in ["school", "class", "teacher", "bus"]):
        sky = (170, 220, 255)
        ground = (105, 180, 95)
        draw.rectangle((0, 0, WIDTH, 470), fill=sky)
        draw.rectangle((0, 470, WIDTH, HEIGHT), fill=ground)

        draw.rectangle((300, 250, 980, 500), fill=(245, 190, 95))
        draw.polygon(
            [(270, 250), (640, 120), (1010, 250)],
            fill=(215, 90, 65),
        )

        draw.rectangle((520, 340, 760, 500), fill=(110, 75, 55))

        for x in (370, 820):
            draw.rectangle(
                (x, 300, x + 90, 390),
                fill=(110, 190, 230),
            )

    elif any(w in text for w in ["beach", "sea", "ocean", "plage"]):
        draw.rectangle((0, 0, WIDTH, 400), fill=(125, 205, 255))
        draw.rectangle((0, 400, WIDTH, 520), fill=(60, 175, 205))
        draw.rectangle((0, 520, WIDTH, HEIGHT), fill=(238, 205, 130))

        draw.ellipse(
            (1010, 60, 1120, 170),
            fill=(255, 215, 80),
        )

    elif any(w in text for w in ["market", "shop", "marché"]):
        draw.rectangle((0, 0, WIDTH, 430), fill=(175, 220, 255))
        draw.rectangle((0, 430, WIDTH, HEIGHT), fill=(195, 160, 100))

        for x, color in [
            (100, (235, 90, 90)),
            (430, (80, 170, 110)),
            (760, (240, 180, 70)),
            (1060, (120, 100, 190)),
        ]:
            draw.rectangle(
                (x, 270, x + 180, 530),
                fill=color,
            )
            draw.polygon(
                [(x - 15, 270), (x + 90, 190), (x + 195, 270)],
                fill=(220, 70, 70),
            )

    elif any(w in text for w in ["home", "house", "maison", "family"]):
        draw.rectangle((0, 0, WIDTH, 430), fill=(175, 225, 255))
        draw.rectangle((0, 430, WIDTH, HEIGHT), fill=(100, 180, 95))

        draw.rectangle(
            (330, 220, 950, 500),
            fill=(244, 195, 115),
        )
        draw.polygon(
            [(285, 220), (640, 75), (995, 220)],
            fill=(205, 85, 65),
        )

        draw.rectangle(
            (570, 355, 710, 500),
            fill=(120, 80, 55),
        )

    else:
        draw.rectangle((0, 0, WIDTH, 430), fill=(170, 220, 255))
        draw.rectangle((0, 430, WIDTH, HEIGHT), fill=(100, 180, 95))

        for x in range(80, WIDTH, 250):
            draw.rectangle(
                (x, 310, x + 80, 450),
                fill=(135, 90, 50),
            )
            draw.ellipse(
                (x - 65, 210, x + 145, 370),
                fill=(65, 155, 75),
            )

    # soleil
    draw.ellipse(
        (80, 60, 180, 160),
        fill=(255, 215, 70),
    )


def draw_child(
    draw,
    x,
    y,
    shirt,
    pants,
    hair,
    skin=(105, 65, 48),
    glasses=False,
):
    head_r = 58

    # jambes
    draw.rectangle(
        (x - 32, y + 105, x - 2, y + 205),
        fill=pants,
    )
    draw.rectangle(
        (x + 2, y + 105, x + 32, y + 205),
        fill=pants,
    )

    # chaussures
    draw.ellipse(
        (x - 42, y + 188, x - 2, y + 215),
        fill=(55, 55, 60),
    )
    draw.ellipse(
        (x + 2, y + 188, x + 42, y + 215),
        fill=(55, 55, 60),
    )

    # corps
    draw.rounded_rectangle(
        (x - 70, y + 25, x + 70, y + 145),
        radius=30,
        fill=shirt,
    )

    # bras
    draw.ellipse(
        (x - 88, y + 48, x - 50, y + 135),
        fill=skin,
    )
    draw.ellipse(
        (x + 50, y + 48, x + 88, y + 135),
        fill=skin,
    )

    # oreilles
    draw.ellipse(
        (x - 72, y - 20, x - 45, y + 15),
        fill=skin,
    )
    draw.ellipse(
        (x + 45, y - 20, x + 72, y + 15),
        fill=skin,
    )

    # cheveux
    draw.ellipse(
        (x - 63, y - 82, x + 63, y + 42),
        fill=hair,
    )

    # visage
    draw.ellipse(
        (x - head_r, y - 65, x + head_r, y + 55),
        fill=skin,
    )

    # cheveux par-dessus
    draw.pieslice(
        (x - head_r, y - 82, x + head_r, y + 15),
        180,
        360,
        fill=hair,
    )

    # yeux
    draw.ellipse(
        (x - 30, y - 25, x - 10, y - 5),
        fill=(245, 245, 245),
    )
    draw.ellipse(
        (x + 10, y - 25, x + 30, y - 5),
        fill=(245, 245, 245),
    )

    draw.ellipse(
        (x - 24, y - 20, x - 14, y - 10),
        fill=(40, 25, 20),
    )
    draw.ellipse(
        (x + 14, y - 20, x + 24, y - 10),
        fill=(40, 25, 20),
    )

    # nez
    draw.ellipse(
        (x - 6, y - 2, x + 6, y + 10),
        fill=(85, 52, 40),
    )

    # sourire
    draw.arc(
        (x - 28, y + 2, x + 28, y + 38),
        15,
        165,
        fill=(80, 30, 30),
        width=5,
    )

    if glasses:
        draw.ellipse(
            (x - 42, y - 38, x - 2, y + 2),
            outline=(35, 35, 40),
            width=5,
        )
        draw.ellipse(
            (x + 2, y - 38, x + 42, y + 2),
            outline=(35, 35, 40),
            width=5,
        )
        draw.line(
            (x - 2, y - 18, x + 2, y - 18),
            fill=(35, 35, 40),
            width=5,
        )


def draw_dog(draw, x, y):
    fur = (145, 90, 55)
    dark = (80, 45, 30)

    # corps
    draw.ellipse(
        (x - 65, y + 30, x + 65, y + 150),
        fill=fur,
    )

    # tête
    draw.ellipse(
        (x - 80, y - 70, x + 80, y + 80),
        fill=fur,
    )

    # oreilles
    draw.ellipse(
        (x - 100, y - 55, x - 55, y + 30),
        fill=dark,
    )
    draw.ellipse(
        (x + 55, y - 55, x + 100, y + 30),
        fill=dark,
    )

    # museau
    draw.ellipse(
        (x - 48, y - 5, x + 48, y + 55),
        fill=(210, 165, 125),
    )

    # yeux
    draw.ellipse(
        (x - 35, y - 25, x - 10, y),
        fill=(30, 25, 20),
    )
    draw.ellipse(
        (x + 10, y - 25, x + 35, y),
        fill=(30, 25, 20),
    )

    # nez
    draw.ellipse(
        (x - 18, y + 8, x + 18, y + 28),
        fill=(35, 25, 25),
    )

    # sourire
    draw.arc(
        (x - 30, y + 5, x + 30, y + 45),
        10,
        170,
        fill=(50, 25, 20),
        width=4,
    )

    # pattes
    for dx in (-40, 40):
        draw.rounded_rectangle(
            (x + dx - 17, y + 125, x + dx + 17, y + 210),
            radius=12,
            fill=fur,
        )


def make_scene(scene):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (170, 220, 255),
    )

    draw = ImageDraw.Draw(image)

    prompt = scene.get("prompt", "")
    draw_background(draw, prompt)

    # personnages toujours au premier plan
    draw_child(
        draw,
        390,
        365,
        shirt=(245, 150, 90),
        pants=(55, 105, 190),
        hair=(55, 35, 28),
    )

    draw_child(
        draw,
        640,
        350,
        shirt=(245, 170, 45),
        pants=(65, 90, 150),
        hair=(45, 28, 23),
    )

    draw_child(
        draw,
        875,
        365,
        shirt=(70, 185, 175),
        pants=(70, 120, 105),
        hair=(55, 35, 28),
        glasses=True,
    )

    draw_dog(draw, 640, 505)

    # petit bandeau interne uniquement pour debug
    # retiré visuellement de la production finale

    return image


def main():
    if not EPISODE_FILE.exists():
        raise RuntimeError(
            f"Épisode introuvable : {EPISODE_FILE}"
        )

    data = json.loads(
        EPISODE_FILE.read_text(encoding="utf-8")
    )

    scenes = data.get("scenes", [])

    if len(scenes) != 60:
        raise RuntimeError(
            f"60 scènes attendues, obtenu : {len(scenes)}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for scene in scenes:
        number = int(scene["scene"])

        image = make_scene(scene)

        output_file = (
            OUTPUT_DIR
            / f"scene_{number:02d}.png"
        )

        image.save(
            output_file,
            format="PNG",
            optimize=True,
        )

        print(
            f"✅ Scène {number:02d}/60 → {output_file}"
        )

    print()
    print("🎉 60 IMAGES CARTOON GÉNÉRÉES")
    print(f"📁 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
