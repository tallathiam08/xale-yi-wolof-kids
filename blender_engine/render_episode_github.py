import subprocess
from pathlib import Path

import bpy


PROJECT = Path(__file__).resolve().parents[1]

SCENE_DIR = (
    PROJECT
    / "output"
    / "blender"
    / "scenes"
)

VIDEO_DIR = (
    PROJECT
    / "output"
    / "blender"
    / "videos"
)

FINAL = (
    PROJECT
    / "output"
    / "blender"
    / "episode_silent.mp4"
)


FPS = 30
WIDTH = 640
HEIGHT = 360
FRAMES = 150


def render_scene(blend_file, output_file):
    print(f"🎞️ Rendu : {blend_file.name}")

    bpy.ops.wm.open_mainfile(
        filepath=str(blend_file)
    )

    scene = bpy.context.scene

    scene.render.engine = (
        "BLENDER_WORKBENCH"
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
    scene.render.ffmpeg.constant_rate_factor = (
        "HIGH"
    )
    scene.render.ffmpeg.audio_codec = "NONE"

    scene.render.filepath = str(output_file)

    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True

    bpy.ops.render.render(
        animation=True
    )

    if not output_file.exists():
        raise RuntimeError(
            f"❌ MP4 manquant : {output_file}"
        )


def main():
    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    blend_files = sorted(
        SCENE_DIR.glob("scene_*.blend")
    )

    if len(blend_files) != 60:
        raise RuntimeError(
            f"❌ {len(blend_files)} blends trouvés "
            "au lieu de 60"
        )

    files = []

    for blend_file in blend_files:
        number = blend_file.stem.split("_")[-1]

        output_file = (
            VIDEO_DIR
            / f"scene_{number}.mp4"
        )

        render_scene(
            blend_file,
            output_file,
        )

        files.append(output_file)

    concat_file = (
        PROJECT
        / "output"
        / "blender"
        / "concat.txt"
    )

    lines = []

    for file in files:
        safe = str(file).replace(
            "'",
            "'\\''"
        )
        lines.append(
            f"file '{safe}'"
        )

    concat_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    FINAL.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(FINAL),
        ],
        check=True,
    )

    print("")
    print("==============================")
    print("✅ ÉPISODE BLENDER TERMINÉ")
    print("==============================")
    print(f"📁 {FINAL}")


if __name__ == "__main__":
    main()
