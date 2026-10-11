from pathlib import Path
import subprocess

from PIL import Image


REFERENCE = Path("reference/characters_reference.png")
OUTPUT_DIR = Path("output/animated_test")
OUTPUT = OUTPUT_DIR / "scene_01.mp4"

WIDTH = 1280
HEIGHT = 720
FPS = 30
DURATION = 5


def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def main():
    if not REFERENCE.exists():
        raise RuntimeError(
            f"Référence introuvable : {REFERENCE}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("🖼️ Vérification de la référence...")

    image = Image.open(REFERENCE).convert("RGB")

    # Le fichier généré est déjà en format paysage.
    # On le prépare en 1280x720 pour le pipeline.
    image = image.resize(
        (WIDTH, HEIGHT),
        Image.Resampling.LANCZOS,
    )

    prepared = OUTPUT_DIR / "reference_1280x720.png"
    image.save(
        prepared,
        "PNG",
        optimize=True,
    )

    print(f"✅ Image préparée : {prepared}")

    ffmpeg = get_ffmpeg()

    print("🎬 Création d'une animation test de 5 secondes...")

    filter_complex = (
        "zoompan="
        "z='min(zoom+0.0008,1.06)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={FPS*DURATION}:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        "format=yuv420p"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(prepared),
        "-vf",
        filter_complex,
        "-t",
        str(DURATION),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(OUTPUT),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("❌ FFmpeg a échoué")

    if not OUTPUT.exists() or OUTPUT.stat().st_size == 0:
        raise RuntimeError("❌ Vidéo non créée")

    print("✅ SCÈNE 01 ANIMÉE")
    print(f"🎬 Fichier : {OUTPUT}")
    print(f"⏱️ Durée : {DURATION}s")
    print(f"📐 Résolution : {WIDTH}x{HEIGHT}")


if __name__ == "__main__":
    main()
