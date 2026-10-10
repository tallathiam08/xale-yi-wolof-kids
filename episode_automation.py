#!/usr/bin/env python3
"""
Automatisation d'un épisode YouTube avec Comfy Cloud + Wan 2.2 + ElevenLabs.

Important :
- Le script NE lance rien tant que tu ne l'exécutes pas.
- Une scène = une exécution Comfy Cloud.
- Il réutilise le workflow Wan 2.2 exporté.
- Il peut générer l'audio Wolof avec ElevenLabs si --with-audio est utilisé.
- Il assemble ensuite toutes les scènes en un épisode MP4.

Pré-requis sur le Mac :
  comfy-cli connecté à Comfy Cloud
  python-dotenv
  google-genai (déjà installé dans le projet)
  elevenlabs
  imageio-ffmpeg

Fichier workflow attendu par défaut :
  /Users/macbook2020/Downloads/Wan 2.2 14B Image to Video.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None


VOICE_IDS = {
    "samba": "X865dA5LI1E5Gjl4Dm7g",
    "ibrahima": "hDAktVoHpCg7hnHohRjC",
    "awa": "9hOVxSsZXpvpKz5POzU1",
}


def run(cmd: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(str(x) for x in cmd))
    return subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture,
    )


def ffmpeg_path() -> str:
    if imageio_ffmpeg is None:
        raise RuntimeError(
            "imageio-ffmpeg n'est pas installé. Lance : pip install imageio-ffmpeg"
        )
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_scenes(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "scenes" in data:
        scenes = data["scenes"]
    elif isinstance(data, list):
        scenes = data
    else:
        raise ValueError("episode_scenes.json doit contenir une liste ou un objet avec 'scenes'.")

    if not scenes:
        raise ValueError("Aucune scène dans episode_scenes.json.")

    normalized = []
    for i, scene in enumerate(scenes, 1):
        prompt = str(scene.get("prompt", "")).strip()
        if not prompt:
            raise ValueError(f"Scène {i}: champ 'prompt' vide.")

        normalized.append(
            {
                "scene": int(scene.get("scene", i)),
                "prompt": prompt,
                "image": scene.get("image"),
                "dialogue": scene.get("dialogue", []),
            }
        )
    return normalized


def prepare_workflow(
    template_path: Path,
    output_path: Path,
    prompt: str,
    output_prefix: str,
    image_name: str | None,
    seed: int,
) -> None:
    workflow = json.loads(template_path.read_text(encoding="utf-8"))

    # Node 129:93 = prompt positif
    workflow["129:93"]["inputs"]["text"] = prompt

    # Node 108 = fichier vidéo de sortie
    workflow["108"]["inputs"]["filename_prefix"] = output_prefix

    # Node 129:86 = seed du premier sampler avancé
    workflow["129:86"]["inputs"]["noise_seed"] = seed

    # On ne remplace l'image que si une valeur est fournie.
    # Le template exporté actuel contient déjà une image valide dans Comfy Cloud.
    if image_name:
        workflow["97"]["inputs"]["image"] = image_name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_cloud_job_for_workflow(workflow_path: Path) -> str:
    result = run(
        ["comfy", "--json", "jobs", "ls", "--where", "cloud"],
        capture=True,
    )
    payload = json.loads(result.stdout)
    jobs = payload["data"]["jobs"]

    wanted = str(workflow_path.resolve())
    matching = [
        j for j in jobs
        if j.get("status") == "completed"
        and j.get("workflow_path") == wanted
        and j.get("outputs", 0) > 0
    ]
    if not matching:
        raise RuntimeError(
            f"Job Cloud terminé introuvable pour {workflow_path}."
        )

    matching.sort(key=lambda j: j.get("updated_at") or "", reverse=True)
    return matching[0]["prompt_id"]


def generate_scene(
    comfy_workflow: Path,
    scene_dir: Path,
    scene: dict,
    seed: int,
) -> Path:
    tmp_workflow = scene_dir / f"scene_{scene['scene']:02d}_workflow.json"
    output_prefix = f"video/episode_scene_{scene['scene']:02d}"

    prepare_workflow(
        comfy_workflow,
        tmp_workflow,
        scene["prompt"],
        output_prefix,
        scene.get("image"),
        seed,
    )

    run(
        [
            "comfy",
            "run",
            "--workflow",
            str(tmp_workflow),
            "--where",
            "cloud",
            "--wait",
        ]
    )

    prompt_id = find_cloud_job_for_workflow(tmp_workflow)

    download_dir = scene_dir / "raw"
    download_dir.mkdir(parents=True, exist_ok=True)

    run(
        [
            "comfy",
            "download",
            prompt_id,
            "--where",
            "cloud",
            "-o",
            str(download_dir),
        ]
    )

    videos = sorted(download_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not videos:
        raise RuntimeError(f"Aucune vidéo téléchargée pour la scène {scene['scene']}.")

    final_video = scene_dir / f"scene_{scene['scene']:02d}_video.mp4"
    shutil.copy2(videos[0], final_video)
    return final_video


def make_voice_clip(
    client: "ElevenLabs",
    voice_name: str,
    text: str,
    output_file: Path,
) -> None:
    voice_id = VOICE_IDS.get(voice_name.lower())
    if not voice_id:
        raise ValueError(
            f"Voix inconnue '{voice_name}'. Utilise : {', '.join(VOICE_IDS)}"
        )

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    with output_file.open("wb") as f:
        for chunk in audio:
            f.write(chunk)


def build_scene_audio(
    client: "ElevenLabs",
    scene: dict,
    scene_dir: Path,
) -> Path | None:
    dialogue = scene.get("dialogue") or []
    if not dialogue:
        return None

    parts = []
    for idx, line in enumerate(dialogue, 1):
        voice = str(line.get("voice", "")).strip().lower()
        text = str(line.get("text", "")).strip()
        if not voice or not text:
            continue

        part = scene_dir / f"voice_{idx:02d}_{voice}.mp3"
        print(f"🎙️ Scène {scene['scene']} — {voice}: {text}")
        make_voice_clip(client, voice, text, part)
        parts.append(part)

    if not parts:
        return None

    ff = ffmpeg_path()
    concat_file = scene_dir / "audio_concat.txt"

    # Petit silence entre les répliques.
    silence = scene_dir / "silence_025.wav"
    run(
        [
            ff,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "0.25",
            str(silence),
        ],
        capture=True,
    )

    lines = []
    for idx, part in enumerate(parts):
        lines.append(f"file '{part.as_posix()}'")
        if idx < len(parts) - 1:
            lines.append(f"file '{silence.as_posix()}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    audio_out = scene_dir / f"scene_{scene['scene']:02d}_audio.wav"
    run(
        [
            ff,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:a",
            "pcm_s16le",
            str(audio_out),
        ],
        capture=True,
    )
    return audio_out


def mux_scene(video: Path, audio: Path | None, output: Path) -> None:
    ff = ffmpeg_path()

    if audio is None:
        shutil.copy2(video, output)
        return

    # On garde toute la vidéo et on ajoute du silence après les dialogues si nécessaire.
    run(
        [
            ff,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-filter_complex",
            "[1:a]apad[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ],
        capture=True,
    )


def assemble_episode(scene_videos: list[Path], output: Path) -> None:
    if not scene_videos:
        raise RuntimeError("Aucune scène à assembler.")

    ff = ffmpeg_path()
    concat_file = output.parent / "episode_concat.txt"

    concat_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in scene_videos),
        encoding="utf-8",
    )

    run(
        [
            ff,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatise un épisode Wan 2.2.")
    parser.add_argument(
        "--workflow",
        default="/Users/macbook2020/Downloads/Wan 2.2 14B Image to Video.json",
    )
    parser.add_argument(
        "--scenes",
        default="/Users/macbook2020/youtube_automation/episode_scenes.json",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/macbook2020/youtube_automation/output/episode",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261009,
    )
    parser.add_argument(
        "--with-audio",
        action="store_true",
        help="Génère aussi les voix Wolof avec ElevenLabs.",
    )
    args = parser.parse_args()

    load_dotenv()

    workflow = Path(args.workflow)
    scenes_file = Path(args.scenes)
    output_dir = Path(args.output_dir)

    if not workflow.exists():
        raise FileNotFoundError(f"Workflow introuvable : {workflow}")
    if not scenes_file.exists():
        raise FileNotFoundError(f"Scènes introuvables : {scenes_file}")

    scenes = load_scenes(scenes_file)

    episode_dir = output_dir
    episode_dir.mkdir(parents=True, exist_ok=True)

    eleven_client = None
    if args.with_audio:
        if ElevenLabs is None:
            raise RuntimeError("Package ElevenLabs absent. Lance : pip install elevenlabs")
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY absent dans .env")
        eleven_client = ElevenLabs(api_key=api_key)

    completed_scene_files: list[Path] = []

    print(f"🎬 {len(scenes)} scène(s) à traiter.")
    print("⚠️ Une scène = une génération Comfy Cloud.")

    for index, scene in enumerate(scenes):
        scene_dir = episode_dir / f"scene_{scene['scene']:02d}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        print()
        print("=" * 70)
        print(f"🎬 SCÈNE {scene['scene']} ({index + 1}/{len(scenes)})")
        print("=" * 70)

        video = generate_scene(
            workflow,
            scene_dir,
            scene,
            seed=args.seed + index,
        )

        audio = None
        if eleven_client:
            audio = build_scene_audio(eleven_client, scene, scene_dir)

        final_scene = scene_dir / f"scene_{scene['scene']:02d}_final.mp4"
        mux_scene(video, audio, final_scene)
        completed_scene_files.append(final_scene)

    episode_file = episode_dir / "episode_final.mp4"
    assemble_episode(completed_scene_files, episode_file)

    print()
    print("✅ ÉPISODE TERMINÉ")
    print(f"📁 {episode_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Arrêt demandé.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n❌ ERREUR : {exc}")
        sys.exit(1)
