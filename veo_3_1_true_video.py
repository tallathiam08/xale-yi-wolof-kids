#!/usr/bin/env python3
"""
Xale Yi — TRUE VIDEO ENGINE with Google Veo 3.1 Gemini API.

Uses each generated scene image as the first frame and generates real motion.
The heavy AI generation runs remotely through Google's API; the Mac only
downloads/results and the final FFmpeg assembly can run in GitHub Actions.

Required environment variable:
  GEMINI_API_KEY

Recommended model for cost:
  veo-3.1-lite-generate-preview
"""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

MODEL = os.getenv("VEO_MODEL", "veo-3.1-lite-generate-preview")
SCENE_TARGET_SECONDS = 5
MODEL_GENERATION_SECONDS = 6
POLL_SECONDS = 10


def fail(message: str) -> None:
    print(f"\n❌ {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd)
    if p.returncode:
        fail(f"Command failed: {p.returncode}")


def find_episode(path_arg: str | None) -> Path:
    candidates = [Path(path_arg)] if path_arg else []
    candidates += [
        Path("output/episode_github_generated.json"),
        Path("output/episode_scenes.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    fail("Episode JSON introuvable.")


def load_scenes(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = data.get("scenes") if isinstance(data, dict) else data
    if not isinstance(scenes, list) or not scenes:
        fail(f"Aucune scène dans {path}")
    return scenes


def number_of(scene: dict[str, Any], fallback: int) -> int:
    for key in ("scene_number", "scene_no", "number", "id"):
        value = scene.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return fallback


def prompt_for(scene: dict[str, Any]) -> str:
    bits: list[str] = []
    for key in (
        "visual_prompt", "video_prompt", "prompt", "action", "camera",
        "location", "environment", "emotion", "movement"
    ):
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            bits.append(value.strip())

    motion = (
        "Animate the exact characters already visible in the input image. "
        "Preserve their faces, hair, clothing, colors, body proportions and "
        "the existing environment. This is a colorful 2D children's cartoon "
        "for Senegalese children. Show clear full-body action and natural "
        "expressions: walking, running, turning, waving, jumping, reacting, "
        "dancing or interacting exactly as described. Use lively but smooth "
        "motion and a gentle cinematic camera move. Keep the composition "
        "readable. Do not redesign or replace the characters. No text, "
        "captions, logos, watermark, subtitles or photorealism."
    )
    return motion + (" " + " ".join(bits) if bits else "")


def scene_images(root: Path) -> dict[int, Path]:
    found: dict[int, Path] = {}
    for p in root.rglob("*"):
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        m = re.search(r"scene[_ -]?0*(\d+)", p.stem.lower())
        if not m:
            continue
        n = int(m.group(1))
        name = p.stem.lower()
        # Avoid sprite sheets / thumbnails when possible.
        penalty = any(x in name for x in ("sheet", "sprite", "thumb", "composite"))
        if n not in found or (not penalty and any(x in found[n].stem.lower() for x in ("sheet", "sprite", "thumb", "composite"))):
            found[n] = p
    return found


def wait_and_download(client: genai.Client, operation, out_path: Path) -> None:
    while not operation.done:
        print("    ⏳ Veo en cours…")
        time.sleep(POLL_SECONDS)
        operation = client.operations.get(operation)

    response = operation.response
    if not response or not getattr(response, "generated_videos", None):
        raise RuntimeError(f"Veo n'a renvoyé aucune vidéo: {response}")

    video = response.generated_videos[0].video
    client.files.download(file=video)
    video.save(str(out_path))


def make_one(
    scene_no: int,
    scene: dict[str, Any],
    image_path: Path,
    work: Path,
    api_key: str,
    force: bool = False,
) -> Path:
    scene_dir = work / f"scene_{scene_no:02d}"
    scene_dir.mkdir(parents=True, exist_ok=True)
    out = scene_dir / "veo_raw.mp4"
    meta = scene_dir / "job.json"

    if out.exists() and not force:
        print(f"✅ Scene {scene_no}: cache hit")
        return out

    client = genai.Client(api_key=api_key)

    image_bytes = image_path.read_bytes()
    image = types.Image(
        image_bytes=image_bytes,
        mime_type="image/png" if image_path.suffix.lower() == ".png" else "image/jpeg",
    )

    prompt = prompt_for(scene)

    operation = client.models.generate_videos(
        model=MODEL,
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=MODEL_GENERATION_SECONDS,
            resolution="720p",
            number_of_videos=1,
        ),
    )

    meta.write_text(
        json.dumps({
            "scene": scene_no,
            "model": MODEL,
            "image": str(image_path),
            "prompt": prompt,
            "submitted": True,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    wait_and_download(client, operation, out)
    meta.write_text(
        json.dumps({
            "scene": scene_no,
            "model": MODEL,
            "image": str(image_path),
            "prompt": prompt,
            "completed": True,
            "output": str(out),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return out


def trim_concat(clips: list[Path], output: Path) -> None:
    norm = output.parent / "normalized"
    norm.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []

    for i, clip in enumerate(clips, 1):
        dst = norm / f"scene_{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(clip),
            "-t", str(SCENE_TARGET_SECONDS),
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=increase,"
            "crop=1280:720,fps=24",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(dst),
        ])
        normalized.append(dst)

    concat_file = output.parent / "concat.txt"
    concat_file.write_text(
        "\n".join("file '" + p.resolve().as_posix().replace("'", "'\\''") + "'" for p in normalized) + "\n",
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output),
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode")
    ap.add_argument("--images-root", default="output")
    ap.add_argument("--out", default="output/true_video/episode_silent.mp4")
    ap.add_argument("--work", default="output/true_video/cache")
    ap.add_argument("--max-scenes", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        fail("GEMINI_API_KEY manquant.")
    if not os.path.exists("/usr/bin/ffmpeg") and subprocess.run(["bash", "-lc", "command -v ffmpeg >/dev/null"]).returncode:
        fail("ffmpeg manquant.")

    episode = find_episode(args.episode)
    scenes = load_scenes(episode)
    if args.max_scenes:
        scenes = scenes[:args.max_scenes]

    imgs = scene_images(Path(args.images_root))
    missing = [number_of(s, i + 1) for i, s in enumerate(scenes) if number_of(s, i + 1) not in imgs]
    if missing:
        fail("Images de scènes manquantes: " + ", ".join(map(str, missing)))

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    results: dict[int, Path] = {}
    print(f"\n🎬 XALE YI TRUE VIDEO — {len(scenes)} scènes")
    print(f"Modèle: {MODEL}")
    print("Entrée: image de scène → vidéo réelle Veo 3.1\n")

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                make_one,
                number_of(scene, i + 1),
                scene,
                imgs[number_of(scene, i + 1)],
                work,
                api_key,
                args.force,
            ): number_of(scene, i + 1)
            for i, scene in enumerate(scenes)
        }

        for future in as_completed(futures):
            n = futures[future]
            results[n] = future.result()
            print(f"✅ Scene {n} prête")

    ordered = [results[number_of(scene, i + 1)] for i, scene in enumerate(scenes)]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    trim_concat(ordered, out)

    manifest = out.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps({
            "model": MODEL,
            "scenes": len(ordered),
            "seconds_per_scene": SCENE_TARGET_SECONDS,
            "target_duration_seconds": len(ordered) * SCENE_TARGET_SECONDS,
            "episode": str(episode),
            "output": str(out),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n🔥 VRAIE VIDÉO TERMINÉE: {out}")
    print(f"Durée cible: {len(ordered) * SCENE_TARGET_SECONDS} secondes")


if __name__ == "__main__":
    main()
