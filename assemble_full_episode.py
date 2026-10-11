import json
import subprocess
from pathlib import Path


PROJECT = Path(".")
EPISODE_FILE = PROJECT / "output/episode_github_generated.json"

AUDIO_DIR = PROJECT / "output/wolof_audio"
BLENDER_VIDEO = PROJECT / "output/blender/episode_silent.mp4"

MUSIC_FILE = PROJECT / "output/free_build/kids_music.wav"

WORK_DIR = PROJECT / "output/final_build"
SCENE_AUDIO_DIR = WORK_DIR / "scene_audio"

FINAL_DIR = PROJECT / "output/final"

VOICE_TRACK = WORK_DIR / "voice_track.wav"
FULL_AUDIO = WORK_DIR / "full_audio.wav"

FINAL_VIDEO = FINAL_DIR / "episode_final.mp4"
SRT_FILE = FINAL_DIR / "episode.srt"

SCENE_DURATION = 5.0
TARGET_DURATION = 300.0


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
            "Commande échouée : "
            + " ".join(str(x) for x in cmd)
        )

    return result


def duration(path):
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


def ts(value):
    value = max(0.0, value)

    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    millis = int(round((value - int(value)) * 1000))

    if millis >= 1000:
        seconds += 1
        millis -= 1000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d},"
        f"{millis:03d}"
    )


def create_scene_audio(scene, scene_number):
    scene_dir = (
        AUDIO_DIR
        / f"scene_{scene_number:02d}"
    )

    if not scene_dir.exists():
        raise RuntimeError(
            f"❌ Audio manquant : {scene_dir}"
        )

    parts = []

    for index, dialogue in enumerate(
        scene["dialogue"],
        start=1,
    ):
        speaker = dialogue["speaker"]

        matches = list(
            scene_dir.glob(
                f"line_{index:02d}_{speaker}.wav"
            )
        )

        if not matches:
            raise RuntimeError(
                f"❌ Audio manquant : "
                f"scène {scene_number}, "
                f"ligne {index}, "
                f"{speaker}"
            )

        parts.append(
            matches[0]
        )

    if len(parts) != 2:
        raise RuntimeError(
            f"❌ Scène {scene_number}: "
            "2 lignes vocales attendues"
        )

    concat_list = (
        SCENE_AUDIO_DIR
        / f"scene_{scene_number:02d}_lines.txt"
    )

    with concat_list.open(
        "w",
        encoding="utf-8",
    ) as f:
        for part in parts:
            f.write(
                f"file '{part.resolve()}'\n"
            )

    raw = (
        SCENE_AUDIO_DIR
        / f"scene_{scene_number:02d}_raw.wav"
    )

    run([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(raw),
    ])

    raw_duration = duration(raw)

    target_voice = 4.8

    speed_factor = 1.0

    if raw_duration > target_voice:
        speed_factor = raw_duration / target_voice

        if speed_factor > 2.0:
            raise RuntimeError(
                f"❌ Scène {scene_number}: "
                f"voix trop longue "
                f"({raw_duration:.2f}s)"
            )

    fitted = raw

    if speed_factor > 1.001:
        fitted = (
            SCENE_AUDIO_DIR
            / f"scene_{scene_number:02d}_fitted.wav"
        )

        run([
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-filter:a",
            f"atempo={speed_factor:.6f}",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(fitted),
        ])

    fitted_duration = duration(fitted)

    final_scene = (
        SCENE_AUDIO_DIR
        / f"scene_{scene_number:02d}.wav"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(fitted),
        "-af",
        "apad",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-t",
        str(SCENE_DURATION),
        str(final_scene),
    ])

    line_durations = [
        duration(path)
        for path in parts
    ]

    line_durations = [
        d / speed_factor
        for d in line_durations
    ]

    # Limite de sécurité : les deux lignes doivent
    # toujours rester dans la scène de 5 secondes.
    remaining = SCENE_DURATION

    scaled = []

    for d in line_durations:
        actual = min(
            d,
            max(0.0, remaining),
        )

        scaled.append(actual)
        remaining -= actual

    return final_scene, scaled


def build_voice_track(episode):
    SCENE_AUDIO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    concat_file = (
        WORK_DIR / "voice_concat.txt"
    )

    scene_files = []

    for scene in episode["scenes"]:
        number = int(scene["scene"])

        print(
            f"🎙️ Audio scène "
            f"{number:02d}/60"
        )

        scene_file, _ = create_scene_audio(
            scene,
            number,
        )

        scene_files.append(
            scene_file
        )

    with concat_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        for file in scene_files:
            f.write(
                f"file '{file.resolve()}'\n"
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
        str(TARGET_DURATION),
        str(VOICE_TRACK),
    ])

    print(
        f"✅ Piste voix : "
        f"{duration(VOICE_TRACK):.2f}s"
    )


def build_music(episode):
    music_scenes = [
        scene
        for scene in episode["scenes"]
        if scene.get("music", False)
    ]

    print(
        f"🎵 Scènes musicales : "
        f"{len(music_scenes)}"
    )

    if not MUSIC_FILE.exists():
        raise RuntimeError(
            f"❌ Musique absente : {MUSIC_FILE}"
        )

    # Ambiance faible partout + musique plus forte
    # pendant les scènes marquées music=true.
    expressions = []

    for scene in music_scenes:
        number = int(scene["scene"])

        start = (number - 1) * 5
        end = number * 5

        expressions.append(
            f"between(t,{start},{end})"
        )

    if expressions:
        gate = "+".join(expressions)
        volume_expression = (
            f"0.012+0.068*({gate})"
        )
    else:
        volume_expression = "0.012"

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(MUSIC_FILE),
        "-t",
        str(TARGET_DURATION),
        "-filter:a",
        f"volume=volume='{volume_expression}'",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(WORK_DIR / "music_mix.wav"),
    ])

    return WORK_DIR / "music_mix.wav"


def mix_audio(voice_file, music_file):
    # La musique est automatiquement abaissée
    # lorsqu'une voix est présente.
    filter_complex = (
        "[1:a][0:a]"
        "sidechaincompress="
        "threshold=0.020:"
        "ratio=6:"
        "attack=15:"
        "release=250:"
        "makeup=1"
        "[music_duck];"
        "[0:a][music_duck]"
        "amix=inputs=2:"
        "duration=first:"
        "dropout_transition=2:"
        "normalize=0"
        "[a]"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(voice_file),
        "-i",
        str(music_file),
        "-filter_complex",
        filter_complex,
        "-map",
        "[a]",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-t",
        str(TARGET_DURATION),
        str(FULL_AUDIO),
    ])

    print(
        f"✅ Audio complet : "
        f"{duration(FULL_AUDIO):.2f}s"
    )


def build_srt(episode):
    FINAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    current = 0.0
    subtitle_index = 1

    with SRT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for scene in episode["scenes"]:

            number = int(
                scene["scene"]
            )

            scene_dir = (
                AUDIO_DIR
                / f"scene_{number:02d}"
            )

            line_cursor = current

            for index, dialogue in enumerate(
                scene["dialogue"],
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
                    raise RuntimeError(
                        f"Audio SRT manquant : "
                        f"{number}/{index}"
                    )

                line_duration = duration(
                    matches[0]
                )

                line_end = min(
                    current + SCENE_DURATION,
                    line_cursor + line_duration,
                )

                if line_end > line_cursor:

                    f.write(
                        f"{subtitle_index}\n"
                    )

                    f.write(
                        f"{ts(line_cursor)} --> "
                        f"{ts(line_end)}\n"
                    )

                    f.write(
                        f"{speaker}: {text}\n\n"
                    )

                    subtitle_index += 1

                line_cursor = line_end

    print(
        f"✅ SRT créé : {SRT_FILE}"
    )


def mux_final():
    FINAL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        str(BLENDER_VIDEO),
        "-i",
        str(FULL_AUDIO),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-t",
        str(TARGET_DURATION),
        "-movflags",
        "+faststart",
        str(FINAL_VIDEO),
    ])

    final_duration = duration(
        FINAL_VIDEO
    )

    if not 295.0 <= final_duration <= 305.0:
        raise RuntimeError(
            f"❌ Durée finale incorrecte : "
            f"{final_duration:.2f}s"
        )

    print("")
    print("==============================")
    print("🎉 ÉPISODE FINAL TERMINÉ")
    print("==============================")
    print(
        f"🎬 {FINAL_VIDEO}"
    )
    print(
        f"⏱️ {final_duration:.2f}s"
    )
    print(
        f"📝 {SRT_FILE}"
    )
    print("==============================")


def main():
    if not EPISODE_FILE.exists():
        raise RuntimeError(
            f"❌ JSON introuvable : {EPISODE_FILE}"
        )

    if not BLENDER_VIDEO.exists():
        raise RuntimeError(
            f"❌ Vidéo Blender absente : "
            f"{BLENDER_VIDEO}"
        )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with EPISODE_FILE.open(
        encoding="utf-8"
    ) as f:
        episode = json.load(f)

    scenes = episode.get("scenes", [])

    if len(scenes) != 60:
        raise RuntimeError(
            f"❌ {len(scenes)} scènes "
            "au lieu de 60"
        )

    build_voice_track(episode)

    music_file = build_music(
        episode
    )

    mix_audio(
        VOICE_TRACK,
        music_file,
    )

    build_srt(episode)

    mux_final()


if __name__ == "__main__":
    main()
