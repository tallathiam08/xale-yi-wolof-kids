import json
import subprocess
import tempfile
from pathlib import Path

from xale_2d_engine import render_video


PROJECT = Path(__file__).resolve().parent

EPISODE = (
    PROJECT
    / "output"
    / "episode_github_generated.json"
)

VIDEO_DIR = (
    PROJECT
    / "output"
    / "2d"
    / "scenes"
)

FINAL = (
    PROJECT
    / "output"
    / "2d"
    / "episode_silent.mp4"
)

FPS = 30


def run(cmd):
    print("▶", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def main():
    if not EPISODE.exists():
        raise RuntimeError(
            f"❌ JSON absent : {EPISODE}"
        )

    data = json.loads(
        EPISODE.read_text(
            encoding="utf-8"
        )
    )

    scenes = data.get("scenes", [])

    if len(scenes) != 60:
        raise RuntimeError(
            f"❌ {len(scenes)} scènes au lieu de 60"
        )

    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    scene_videos = []

    with tempfile.TemporaryDirectory(
        prefix="xale_render_"
    ) as tmp:

        tmp = Path(tmp)

        for index, scene in enumerate(
            scenes,
            start=1,
        ):
            scene_json = (
                tmp
                / f"scene_{index:02d}.json"
            )

            scene_json.write_text(
                json.dumps(
                    scene,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            output = (
                VIDEO_DIR
                / f"scene_{index:02d}.mp4"
            )

            print("")
            print(
                f"🎬 SCÈNE {index:02d}/60"
                f" | {scene.get('scene_type')}"
                f" | {scene.get('location')}"
                f" | {scene.get('camera')}"
            )

            render_video(
                scene_json,
                output,
            )

            if not output.exists():
                raise RuntimeError(
                    f"❌ Vidéo absente : {output}"
                )

            scene_videos.append(output)

        concat = (
            PROJECT
            / "output"
            / "2d"
            / "concat.txt"
        )

        with concat.open(
            "w",
            encoding="utf-8",
        ) as f:
            for video in scene_videos:
                f.write(
                    f"file '{video.resolve()}'\n"
                )

        FINAL.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        run([
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(FINAL),
        ])

    if not FINAL.exists():
        raise RuntimeError(
            "❌ Épisode 2D non créé"
        )

    print("")
    print("==============================")
    print("✅ ÉPISODE 2D SILENCIEUX")
    print("==============================")
    print(FINAL)
    print("==============================")


if __name__ == "__main__":
    main()
