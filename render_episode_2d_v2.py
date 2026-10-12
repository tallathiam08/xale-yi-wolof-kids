import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from xale_2d_engine_v2 import render_scene


PROJECT = Path(__file__).resolve().parent
EPISODE = PROJECT / "output" / "episode_github_generated.json"
VIDEO_DIR = PROJECT / "output" / "2d" / "scenes"
FINAL = PROJECT / "output" / "2d" / "episode_silent.mp4"

WORKERS = int(os.getenv("XALE_WORKERS", "4"))


def render_one(item):
    scene, output = item
    render_scene(scene, output)
    return output


def main():
    if not EPISODE.exists():
        raise RuntimeError(f"JSON absent : {EPISODE}")

    data = json.loads(
        EPISODE.read_text(encoding="utf-8")
    )

    scenes = data.get("scenes", [])

    if len(scenes) != 60:
        raise RuntimeError(
            f"{len(scenes)} scènes trouvées, 60 attendues"
        )

    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    jobs = []

    for scene in scenes:
        number = int(scene["scene"])
        output = VIDEO_DIR / f"scene_{number:02d}.mp4"
        jobs.append((scene, output))

    print(
        f"🎬 Rendu 2D V2 : 60 scènes"
        f" | workers={WORKERS}"
    )

    done = 0

    with ProcessPoolExecutor(
        max_workers=WORKERS
    ) as pool:
        futures = [
            pool.submit(render_one, job)
            for job in jobs
        ]

        for future in as_completed(futures):
            output = future.result()
            done += 1
            print(
                f"✅ {done}/60 : {output.name}"
            )

    concat = PROJECT / "output" / "2d" / "concat.txt"

    with concat.open(
        "w",
        encoding="utf-8",
    ) as f:
        for scene in scenes:
            number = int(scene["scene"])
            output = VIDEO_DIR / f"scene_{number:02d}.mp4"
            f.write(
                f"file '{output.resolve()}'\n"
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
            str(concat),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(FINAL),
        ],
        check=True,
    )

    if not FINAL.exists() or FINAL.stat().st_size == 0:
        raise RuntimeError(
            "Épisode 2D absent"
        )

    print("")
    print("==============================")
    print("✅ ÉPISODE 2D V2 TERMINÉ")
    print("==============================")
    print(FINAL)
    print("==============================")


if __name__ == "__main__":
    main()
