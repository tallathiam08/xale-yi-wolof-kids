#!/usr/bin/env python3
"""
Wan 2.2 + ElevenLabs episode automation v2.

Designed for the exported ComfyUI API workflow:
- node 97  = LoadImage
- node 108 = SaveVideo
- node 129:98 = WanImageToVideo
- node 129:93 = positive prompt

Usage examples:
  python episode_automation_v2.py --scenes episode_01_scenes_wolof.json
  python episode_automation_v2.py --scenes episode_01_scenes_wolof.json --with-audio
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

VOICE_IDS = {
    "samba": "X865dA5LI1E5Gjl4Dm7g",
    "ibrahima": "hDAktVoHpCg7hnHohRjC",
    "awa": "9hOVxSsZXpvpKz5POzU1",
}

VOICE_ALIASES = {
    "samba": "samba",
    "Samba": "samba",
    "ibrahima": "ibrahima",
    "Ibrahima": "ibrahima",
    "awa": "awa",
    "Awa": "awa",
}

DEFAULT_WORKFLOW = "/Users/macbook2020/Downloads/Wan 2.2 14B Image to Video.json"
DEFAULT_OUTPUT = "/Users/macbook2020/youtube_automation/output/episode"

def run(cmd: list[str], cwd: str | None = None) -> str:
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise RuntimeError(p.stdout)
    return p.stdout

def ffmpeg_path() -> str:
    out = run(["python", "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"])
    return out.strip().splitlines()[-1]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_workflow(template: dict, prompt: str, prefix: str, seed: int | None, out_path: Path):
    wf = json.loads(json.dumps(template))
    wf["129:93"]["inputs"]["text"] = prompt
    wf["108"]["inputs"]["filename_prefix"] = prefix
    if seed is not None and "129:86" in wf:
        wf["129:86"]["inputs"]["noise_seed"] = seed
    out_path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")

def find_latest_job(workflow_path: str, timeout_s: int = 180):
    deadline = time.time() + timeout_s
    target = str(Path(workflow_path).resolve())
    while time.time() < deadline:
        raw = run(["comfy", "--json", "jobs", "ls", "--where", "cloud"])
        data = json.loads(raw)
        jobs = data.get("jobs", data if isinstance(data, list) else [])
        candidates = []
        for j in jobs:
            status = str(j.get("status", "")).lower()
            if status not in {"completed", "success", "succeeded"}:
                continue
            wp = str(j.get("workflow_path") or j.get("workflow") or "")
            if wp and wp == target:
                candidates.append(j)
        if candidates:
            candidates.sort(key=lambda j: str(j.get("completed_at") or j.get("updated_at") or j.get("created_at") or ""))
            return candidates[-1]
        time.sleep(3)
    raise TimeoutError(f"Aucun job terminé trouvé pour {target}")

def generate_scene(template: dict, scene: dict, work_dir: Path, raw_dir: Path, seed: int | None, force: bool = False):
    n = int(scene["scene"])

    # Fichier normalisé pour permettre la reprise automatique.
    reusable_raw = raw_dir / f"scene_{n:02d}_raw.mp4"

    if reusable_raw.exists() and reusable_raw.stat().st_size > 0 and not force:
        print(f"♻️  SCÈNE {n}: vidéo brute déjà présente, reprise automatique.")
        return reusable_raw

    wf_path = work_dir / f"scene_{n:02d}.json"
    prefix = f"episode_scene_{n:02d}"

    save_workflow(template, scene["prompt"], prefix, seed, wf_path)

    print(f"🎬 SCÈNE {n}: génération Comfy Cloud…")
    run([
        "comfy",
        "run",
        "--workflow",
        str(wf_path),
        "--where",
        "cloud",
        "--wait",
    ])

    job = find_latest_job(str(wf_path))
    prompt_id = job.get("prompt_id") or job.get("id") or job.get("job_id")

    if not prompt_id:
        raise RuntimeError(f"prompt_id introuvable dans le job: {job}")

    before = {
        p.resolve()
        for p in raw_dir.glob("*.mp4")
        if p.is_file()
    }

    out = run([
        "comfy",
        "download",
        str(prompt_id),
        "--where",
        "cloud",
        "-o",
        str(raw_dir),
    ])

    files = sorted(
        raw_dir.glob("*.mp4"),
        key=lambda p: p.stat().st_mtime
    )

    # Priorité au fichier nouvellement téléchargé.
    new_files = [
        p for p in files
        if p.resolve() not in before
    ]

    candidates = new_files if new_files else files

    if not candidates:
        raise FileNotFoundError(
            f"Aucune vidéo MP4 téléchargée. Sortie CLI:\n{out}"
        )

    latest = candidates[-1]

    # Copie vers un nom stable pour la reprise.
    if latest.resolve() != reusable_raw.resolve():
        import shutil
        shutil.copy2(latest, reusable_raw)

    print(f"✅ SCÈNE {n}: vidéo brute enregistrée → {reusable_raw}")
    return reusable_raw


class ElevenLabsQuotaExceeded(RuntimeError):
    """Quota ElevenLabs insuffisant pour poursuivre la génération audio."""
    pass


def tts_line(text: str, voice_key: str, out_mp3: Path):
    # Lazy import so --with-audio is the only mode that needs the SDK.
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as e:
        raise RuntimeError("Installe elevenlabs dans le venv avant --with-audio") from e

    if load_dotenv:
        load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY manque dans .env")

    voice = VOICE_IDS[VOICE_ALIASES[voice_key]]
    client = ElevenLabs(api_key=api_key)

    try:
        audio = client.text_to_speech.convert(
            voice_id=voice,
            model_id=os.getenv(
                "ELEVENLABS_MODEL",
                "eleven_multilingual_v2"
            ),
            text=text,
            output_format="mp3_44100_128",
        )
    except Exception as e:
        status = getattr(e, "status_code", None)
        body = getattr(e, "body", None)
        body_text = str(body).lower()

        if (
            status in {401, 402, 429}
            and "quota_exceeded" in body_text
        ):
            raise ElevenLabsQuotaExceeded(
                "Quota ElevenLabs insuffisant pour cette génération."
            ) from e

        raise

    out_mp3.write_bytes(b"".join(audio))

def make_dialogue_audio(dialogue: list[dict], scene_dir: Path, scene_no: int, force: bool = False) -> Path | None:
    if not dialogue:
        return None

    ffmpeg = ffmpeg_path()

    valid_lines = []
    for line in dialogue:
        speaker = line.get("voice") or line.get("speaker")
        text = (line.get("text") or "").strip()
        if speaker and text:
            valid_lines.append((speaker, text))

    if not valid_lines:
        return None

    scene_dir.mkdir(parents=True, exist_ok=True)
    out = scene_dir / f"scene_{scene_no:02d}_audio.mp3"

    expected = len(valid_lines)
    existing = [
        scene_dir / f"line_{i:02d}.mp3"
        for i in range(1, expected + 1)
    ]

    # Si tout l'audio est déjà terminé, on le réutilise.
    if (
        not force
        and out.exists()
        and out.stat().st_size > 0
        and all(p.exists() and p.stat().st_size > 0 for p in existing)
    ):
        print(f"♻️  AUDIO SCÈNE {scene_no}: déjà présent, reprise automatique.")
        return out

    clips = []

    for i, (speaker, text) in enumerate(valid_lines, 1):
        mp3 = scene_dir / f"line_{i:02d}.mp3"

        if (
            not force
            and mp3.exists()
            and mp3.stat().st_size > 0
        ):
            print(f"♻️  Ligne {i:02d}: audio déjà présent.")
        else:
            print(f"🗣️  {speaker}: {text}")
            tts_line(text, speaker, mp3)

        clips.append(mp3)

    if not all(p.exists() and p.stat().st_size > 0 for p in clips):
        raise RuntimeError(
            f"Scène {scene_no}: un ou plusieurs fichiers audio sont absents."
        )

    concat_txt = scene_dir / "audio_concat.txt"
    concat_txt.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in clips),
        encoding="utf-8"
    )

    run([
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(out),
    ])

    print(f"✅ AUDIO SCÈNE {scene_no}: {out}")
    return out


def mux_audio(video: Path, audio: Path | None, out: Path):
    if audio is None:
        shutil.copy2(video, out)
        return
    ffmpeg = ffmpeg_path()

    # Preserve the full video duration instead of cutting it to the end of a short voice line.
    probe = run([
        ffmpeg, "-i", str(video), "-f", "null", "-"
    ])
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe)
    if not m:
        raise RuntimeError("Impossible de lire la durée vidéo")
    duration = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))

    run([
        ffmpeg, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-filter_complex", "[1:a]apad[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        str(out),
    ])

def assemble_episode(scene_videos: list[Path], out: Path):
    ffmpeg = ffmpeg_path()
    concat_txt = out.parent / "episode_concat.txt"
    concat_txt.write_text("\n".join(f"file '{p.as_posix()}'" for p in scene_videos), encoding="utf-8")
    run([
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(out),
    ])

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    ap.add_argument("--scenes", default="episode_01_scenes_wolof.json")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    ap.add_argument("--seed", type=int, default=57820264156908)

    ap.add_argument("--with-audio", action="store_true")

    ap.add_argument(
        "--audio-only",
        action="store_true",
        help="Génère uniquement les audios; aucun job Comfy Cloud."
    )

    ap.add_argument(
        "--check-audio",
        action="store_true",
        help="Vérifie les dialogues et compte les caractères; aucun appel API."
    )

    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore les fichiers déjà terminés et force leur régénération."
    )

    args = ap.parse_args()

    if args.audio_only and args.check_audio:
        ap.error("--audio-only et --check-audio ne peuvent pas être utilisés ensemble")

    workflow = Path(args.workflow).expanduser()
    scenes_path = Path(args.scenes).expanduser()
    out_dir = Path(args.output_dir).expanduser()

    raw_dir = out_dir / "raw"
    scene_dir = out_dir / "scenes"
    work_dir = out_dir / "work"

    for d in (out_dir, raw_dir, scene_dir, work_dir):
        d.mkdir(parents=True, exist_ok=True)

    template = load_json(workflow)
    payload = load_json(scenes_path)
    scenes = payload["scenes"]

    print(f"📖 {payload.get('title', 'Épisode')}")
    print(f"🎞️  {len(scenes)} scènes")
    print(
        f"🔊 Audio: "
        f"{'OUI' if (args.with_audio or args.audio_only) else 'NON'}"
    )

    if args.force:
        print("⚠️ MODE FORCE: les fichiers existants seront régénérés.")

    # --------------------------------------------------------
    # CHECK AUDIO
    # --------------------------------------------------------
    if args.check_audio:
        total_chars = 0
        total_lines = 0

        print("\n🔎 CONTRÔLE AUDIO — aucun appel ElevenLabs")

        for scene in scenes:
            scene_no = int(scene["scene"])
            scene_chars = 0
            scene_lines = 0

            for line in scene.get("dialogue", []):
                text = (line.get("text") or "").strip()
                speaker = line.get("voice") or line.get("speaker")

                if text:
                    chars = len(text)
                    scene_chars += chars
                    scene_lines += 1
                    total_chars += chars
                    total_lines += 1

                    print(
                        f"Scène {scene_no:02d} | "
                        f"{speaker or '?'} | "
                        f"{chars} caractères | {text}"
                    )

            print(
                f"→ Scène {scene_no:02d}: "
                f"{scene_lines} ligne(s), {scene_chars} caractères"
            )

        print(
            f"\n✅ TOTAL: {total_lines} ligne(s), "
            f"{total_chars} caractères"
        )
        print("✅ Aucun appel ElevenLabs effectué")
        print("✅ Aucun job Comfy Cloud lancé")
        return

    # --------------------------------------------------------
    # AUDIO ONLY
    # --------------------------------------------------------
    if args.audio_only:
        print("\n🎧 MODE AUDIO UNIQUEMENT — aucun job Comfy Cloud")

        generated = 0

        for scene in scenes:
            n = int(scene["scene"])
            scene_audio_dir = scene_dir / f"scene_{n:02d}"

            audio = make_dialogue_audio(
                scene.get("dialogue", []),
                scene_audio_dir,
                n,
                force=args.force,
            )

            if audio and audio.exists():
                generated += 1

        print(
            f"\n✅ AUDIO TERMINÉ — "
            f"{generated}/{len(scenes)} scènes disponibles"
        )
        return

    # --------------------------------------------------------
    # VIDEO + AUDIO
    # --------------------------------------------------------
    final_scene_videos: list[Path] = []

    for scene in scenes:
        n = int(scene["scene"])

        final_scene = scene_dir / f"scene_{n:02d}_final.mp4"

        # Sans audio demandé, une scène finale existante peut être réutilisée.
        if (
            not args.with_audio
            and not args.force
            and final_scene.exists()
            and final_scene.stat().st_size > 0
        ):
            print(
                f"♻️  SCÈNE {n}: vidéo finale déjà présente, "
                f"aucune génération."
            )
            final_scene_videos.append(final_scene)
            continue

        raw_video = generate_scene(
            template,
            scene,
            work_dir,
            raw_dir,
            args.seed + n - 1,
            force=args.force,
        )

        audio = None

        if args.with_audio and scene.get("dialogue"):
            scene_audio_dir = scene_dir / f"scene_{n:02d}"

            audio = make_dialogue_audio(
                scene.get("dialogue", []),
                scene_audio_dir,
                n,
                force=args.force,
            )

        # Si la vidéo finale existe déjà et qu'on a l'audio requis,
        # on peut la garder seulement si elle n'est pas forcée.
        if (
            not args.force
            and final_scene.exists()
            and final_scene.stat().st_size > 0
            and audio is not None
        ):
            print(
                f"♻️  SCÈNE {n}: fichier final déjà présent."
            )
        else:
            mux_audio(raw_video, audio, final_scene)

        final_scene_videos.append(final_scene)

    # --------------------------------------------------------
    # ASSEMBLAGE FINAL
    # --------------------------------------------------------
    final = out_dir / "episode_final.mp4"

    print("\n🎞️ ASSEMBLAGE DE L'ÉPISODE...")
    assemble_episode(final_scene_videos, final)

    print(f"\n✅ ÉPISODE TERMINÉ")
    print(f"📁 {final}")


if __name__ == "__main__":
    try:
        main()
    except ElevenLabsQuotaExceeded as e:
        print("\n🛑 ELEVENLABS : QUOTA INSUFFISANT")
        print(f"ℹ️ {e}")
        print("♻️ Les fichiers audio déjà générés sont conservés.")
        print("▶ Relance --audio-only lorsque le quota sera disponible.")
        raise SystemExit(2)
