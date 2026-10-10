import subprocess
from pathlib import Path
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

IMAGE = Path("images/characters.png")
AUDIO_DIR = Path("audio/episode")
OUTPUT_DIR = Path("videos")
TEMP_DIR = Path("videos/temp")

OUTPUT_FILE = OUTPUT_DIR / "episode_animatic.mp4"

if not IMAGE.exists():
    raise RuntimeError("❌ Image introuvable : images/characters.png")

audio_files = sorted(AUDIO_DIR.glob("scene_*.mp3"))

if not audio_files:
    raise RuntimeError("❌ Aucun fichier audio trouvé dans audio/episode/")

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

print(f"🎬 {len(audio_files)} scènes trouvées.")
print("🖼️ Création des scènes vidéo...")

scene_videos = []

for number, audio_file in enumerate(audio_files, start=1):

    output_scene = TEMP_DIR / f"scene_{number:02d}.mp4"

    print(f"\n🎞️ Scène {number}")
    print(f"   🎧 {audio_file}")

    command = [
        FFMPEG,
        "-y",
        "-loop", "1",
        "-i", str(IMAGE),
        "-i", str(audio_file),

        "-vf",
        (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "zoompan="
            "z='min(zoom+0.0005,1.08)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "d=1:"
            "s=1280x720:"
            "fps=30"
        ),

        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "192k",

        "-shortest",

        str(output_scene),
    ]

    subprocess.run(command, check=True)

    scene_videos.append(output_scene)

    print(f"   ✅ {output_scene}")

concat_file = TEMP_DIR / "concat.txt"

with open(concat_file, "w", encoding="utf-8") as f:
    for video in scene_videos:
        f.write(f"file '{video.resolve()}'\n")

print("\n🔗 Assemblage des scènes...")

concat_command = [
    FFMPEG,
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(concat_file),
    "-c", "copy",
    str(OUTPUT_FILE),
]

subprocess.run(concat_command, check=True)

print("\n========================================")
print("🎉 VIDÉO TERMINÉE")
print("========================================")
print(f"📹 {OUTPUT_FILE}")
