import json
import shutil
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
EPISODE = PROJECT / "output" / "episode_github_generated.json"

SCENE_DIR = (
    PROJECT
    / "output"
    / "blender"
    / "scenes"
)

sys.path.insert(
    0,
    str(PROJECT / "blender_engine")
)

import blender_episode_engine as engine


def main():
    if not EPISODE.exists():
        raise FileNotFoundError(
            f"❌ Épisode introuvable : {EPISODE}"
        )

    with open(
        EPISODE,
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    scenes = data["scenes"]

    if len(scenes) != 60:
        raise RuntimeError(
            f"❌ {len(scenes)} scènes au lieu de 60"
        )

    SCENE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    engine.OUTPUT_DIR = SCENE_DIR

    manifest = []

    for scene in scenes:
        number = int(scene["scene"])

        print("")
        print(
            f"🎬 SCÈNE {number:02d}/60 "
            f"| {scene['scene_type']} "
            f"| {scene['location']}"
        )

        engine.build_scene(scene)

        source = (
            SCENE_DIR
            / "xale_scene_v1.blend"
        )

        destination = (
            SCENE_DIR
            / f"scene_{number:02d}.blend"
        )

        if not source.exists():
            raise RuntimeError(
                f"Blend manquant : {source}"
            )

        if destination.exists():
            destination.unlink()

        shutil.move(
            str(source),
            str(destination),
        )

        manifest.append({
            "scene": number,
            "scene_type": scene["scene_type"],
            "location": scene["location"],
            "camera": scene["camera"],
            "music": scene["music"],
            "blend": str(destination),
        })

    manifest_file = (
        PROJECT
        / "output"
        / "blender"
        / "manifest.json"
    )

    manifest_file.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print("==============================")
    print("✅ 60 SCÈNES BLENDER CRÉÉES")
    print("==============================")
    print(f"📁 {SCENE_DIR}")
    print(f"📄 {manifest_file}")


if __name__ == "__main__":
    main()
