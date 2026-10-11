import json
import subprocess
from pathlib import Path


EPISODE_FILE = Path("output/episode_github_generated.json")
REFERENCE = Path("reference/characters_reference.png")
AUDIO_DIR = Path("output/wolof_audio")
WORK_DIR = Path("output/free_build")
SCENES_DIR = WORK_DIR / "scenes"
FINAL_DIR = Path("output/final")

WIDTH = 1280
HEIGHT = 720
FPS = 30
SCENE_DURATION = 5


def run(cmd):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"Commande échouée : {' '.join(cmd)}"
        )

    return result


def duration_seconds(path):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])

    return float(result.stdout.strip())


def create_scene_audio(scene_number):
    scene_dir = AUDIO_DIR / f"scene_{scene_number:02d}"

    if not scene_dir.exists():
        raise RuntimeError(
            f"Audio introuvable : {scene_dir}"
        )

    files = sorted(scene_dir.glob("*.wav"))

    if not files:
        raise RuntimeError(
            f"Aucun WAV pour la scène {scene_number}"
        )

    list_file = SCENES_DIR / (
        f"scene_{scene_number:02d}_audio.txt"
    )

    with list_file.open("w", encoding="utf-8") as f:
        for wav in files:
            safe_path = wav.resolve()
            f.write(f"file '{safe_path}'\n")

    merged = SCENES_DIR / (
        f"scene_{scene_number:02d}_audio_raw.wav"
    )

    run([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(merged),
    ])

    original_duration = duration_seconds(merged)

    # On essaie de faire tenir le dialogue dans 4.8 secondes
    # maximum, afin de laisser un petit espace avant la scène suivante.
    target_audio = SCENE_DURATION - 0.2

    if original_duration > target_audio:
        factor = original_duration / target_audio

        if factor > 2.0:
            raise RuntimeError(
                f"Scène {scene_number}: audio trop long "
                f"({original_duration:.2f}s)"
            )

        # atempo accepte ici une accélération modérée.
        stretched = SCENES_DIR / (
            f"scene_{scene_number:02d}_audio_fit.wav"
        )

        run([
            "ffmpeg",
            "-y",
            "-i",
            str(merged),
            "-filter:a",
            f"atempo={factor:.5f}",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(stretched),
        ])

        merged = stretched
        fitted_duration = duration_seconds(merged)
    else:
        fitted_duration = original_duration

    final_audio = SCENES_DIR / (
        f"scene_{scene_number:02d}_audio.wav"
    )

    silence = SCENES_DIR / (
        f"scene_{scene_number:02d}_silence.wav"
    )

    # Silence de sécurité.
    remaining = max(
        0.0,
        SCENE_DURATION - fitted_duration,
    )

    if remaining > 0.01:
        run([
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            f"{remaining:.3f}",
            str(silence),
        ])

        concat_file = SCENES_DIR / (
            f"scene_{scene_number:02d}_final_audio.txt"
        )

        with concat_file.open(
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                f"file '{str(merged.resolve())}'\n"
            )
            f.write(
                f"file '{str(silence.resolve())}'\n"
            )

        run([
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-t",
            str(SCENE_DURATION),
            str(final_audio),
        ])
    else:
        run([
            "ffmpeg",
            "-y",
            "-i",
            str(merged),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-t",
            str(SCENE_DURATION),
            str(final_audio),
        ])

    return final_audio


def create_scene_video(scene_number):
    output = SCENES_DIR / (
        f"scene_{scene_number:02d}.mp4"
    )

    # Variation de mouvement de caméra selon la scène.
    mode = scene_number % 6

    if mode == 0:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0010,1.08)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)'"
        )
    elif mode == 1:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0008,1.06)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)'"
        )
    elif mode == 2:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0008,1.06)':"
            "x='iw*0.40-(iw/zoom*0.40)':"
            "y='ih/2-(ih/zoom/2)'"
        )
    elif mode == 3:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0008,1.06)':"
            "x='iw*0.60-(iw/zoom*0.60)':"
            "y='ih/2-(ih/zoom/2)'"
        )
    elif mode == 4:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0007,1.05)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih*0.40-(ih/zoom*0.40)'"
        )
    else:
        zoom = (
            "zoompan="
            "z='min(zoom+0.0007,1.05)':"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih*0.60-(ih/zoom*0.60)'"
        )

    filter_complex = (
        zoom
        + f":d={FPS * SCENE_DURATION}"
        + f":s={WIDTH}x{HEIGHT}"
        + f":fps={FPS},format=yuv420p"
    )

    run([
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(REFERENCE),
        "-vf",
        filter_complex,
        "-t",
        str(SCENE_DURATION),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ])

    return output


def mux_scene(scene_number):
    video = SCENES_DIR / (
        f"scene_{scene_number:02d}.mp4"
    )
    audio = SCENES_DIR / (
        f"scene_{scene_number:02d}_audio.wav"
    )
    output = SCENES_DIR / (
        f"scene_{scene_number:02d}_complete.mp4"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(output),
    ])

    return output


def create_srt(episode):
    srt_path = FINAL_DIR / "episode.srt"

    counter = 1
    current = 0.0

    with srt_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for scene in episode["scenes"]:
            scene_number = int(scene["scene"])
            dialogues = scene.get("dialogue", [])

            scene_dir = AUDIO_DIR / (
                f"scene_{scene_number:02d}"
            )

            scene_start = current

            line_start = scene_start

            for index, dialogue in enumerate(
                dialogues,
                start=1,
            ):
                speaker = dialogue["speaker"]
                text = dialogue["text"]

                matches = list(
                    scene_dir.glob(
                        f"line_{index:02d}_{speaker}.wav"
                    )
                )

                if not matches:
                    continue

                duration = duration_seconds(matches[0])

                # Répartir proportionnellement si nécessaire.
                line_end = min(
                    scene_start + SCENE_DURATION,
                    line_start + duration,
                )

                def ts(value):
                    hours = int(value // 3600)
                    minutes = int(
                        (value % 3600) // 60
                    )
                    seconds = int(
                        value % 60
                    )
                    millis = int(
                        round((value - int(value)) * 1000)
                    )

                    if millis >= 1000:
                        seconds += 1
                        millis -= 1000

                    return (
                        f"{hours:02d}:"
                        f"{minutes:02d}:"
                        f"{seconds:02d},"
                        f"{millis:03d}"
                    )

                f.write(f"{counter}\n")
                f.write(
                    f"{ts(line_start)} --> "
                    f"{ts(line_end)}\n"
                )
                f.write(
                    f"{speaker}: {text}\n\n"
                )

                counter += 1
                line_start = line_end

            current += SCENE_DURATION

    return srt_path


def main():
    if not EPISODE_FILE.exists():
        raise RuntimeError(
            f"Épisode introuvable : {EPISODE_FILE}"
        )

    if not REFERENCE.exists():
        raise RuntimeError(
            f"Référence introuvable : {REFERENCE}"
        )

    episode = json.loads(
        EPISODE_FILE.read_text(
            encoding="utf-8"
        )
    )

    scenes = episode.get("scenes", [])

    if len(scenes) != 60:
        raise RuntimeError(
            f"60 scènes attendues, obtenu : {len(scenes)}"
        )

    SCENES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("🎬 CONSTRUCTION DE L'ÉPISODE")
    print("🎞️ 60 scènes")
    print("⏱️ 5 minutes")
    print()

    complete_scenes = []

    for scene in scenes:
        number = int(scene["scene"])

        print(
            f"▶️ Scène {number:02d}/60"
        )

        create_scene_audio(number)
        create_scene_video(number)
        complete = mux_scene(number)

        complete_scenes.append(complete)

        print(
            f"   ✅ Scène {number:02d} terminée"
        )

    concat_file = WORK_DIR / "concat.txt"

    with concat_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        for scene_file in complete_scenes:
            f.write(
                f"file '{scene_file.resolve()}'\n"
            )

    final_video = FINAL_DIR / (
        "episode_final.mp4"
    )

    print()
    print("🎞️ Assemblage des 60 scènes...")

    run([
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
        str(final_video),
    ])

    srt = create_srt(episode)

    total_duration = duration_seconds(
        final_video
    )

    print()
    print("🎉 ÉPISODE COMPLET")
    print(
        f"🎬 Titre : {episode['title']}"
    )
    print(
        f"⏱️ Durée vidéo : {total_duration:.2f}s"
    )
    print(
        f"📄 Vidéo : {final_video}"
    )
    print(
        f"📝 Sous-titres : {srt}"
    )


if __name__ == "__main__":
    main()
