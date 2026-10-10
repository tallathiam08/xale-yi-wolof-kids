import argparse
import json
import re
import shlex
import subprocess
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


def ffmpeg_path() -> str:
    if imageio_ffmpeg:
        return imageio_ffmpeg.get_ffmpeg_exe()
    return "ffmpeg"


def run(cmd):
    print("▶", " ".join(shlex.quote(str(x)) for x in cmd))
    p = subprocess.run(
        [str(x) for x in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stdout)
    return p.stdout


def duration(path: Path) -> float:
    ffmpeg = ffmpeg_path()
    cmd = [
        ffmpeg,
        "-i", str(path),
        "-f", "null",
        "-",
    ]
    out = run(cmd)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
    if not m:
        raise RuntimeError(f"Durée introuvable : {path}")
    return (
        int(m.group(1)) * 3600
        + int(m.group(2)) * 60
        + float(m.group(3))
    )


def has_audio(path: Path) -> bool:
    ffmpeg = ffmpeg_path()
    cmd = [
        ffmpeg,
        "-i", str(path),
        "-map", "0:a:0",
        "-f", "null",
        "-",
    ]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return p.returncode == 0


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_scenes(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        raise RuntimeError("Le JSON ne contient pas de liste 'scenes'.")
    return data, scenes


def find_scene_video(input_dir: Path, n: int) -> Path:
    p = input_dir / "scenes" / f"scene_{n:02d}_final.mp4"
    if p.exists():
        return p

    p = input_dir / f"scene_{n:02d}_final.mp4"
    if p.exists():
        return p

    raise FileNotFoundError(f"Vidéo finale absente pour la scène {n:02d}: {p}")


def find_line_audio(input_dir: Path, n: int):
    folder = input_dir / "scenes" / f"scene_{n:02d}"
    if not folder.exists():
        folder = input_dir / f"scene_{n:02d}"

    return sorted(folder.glob("line_*.mp3"))


def build_srt(scenes, input_dir: Path, out_srt: Path):
    cursor = 0.0
    entries = []
    subtitle_no = 1

    for scene in scenes:
        n = int(scene["scene"])
        video = find_scene_video(input_dir, n)
        video_duration = duration(video)

        audios = find_line_audio(input_dir, n)
        dialogue = scene.get("dialogue", [])

        if len(audios) != len([x for x in dialogue if (x.get("text") or "").strip()]):
            raise RuntimeError(
                f"Scène {n:02d}: nombre de MP3 ({len(audios)}) "
                f"différent du nombre de dialogues."
            )

        local_cursor = cursor

        for audio_file, line in zip(audios, dialogue):
            text = (line.get("text") or "").strip()
            if not text:
                continue

            line_duration = duration(audio_file)
            start = local_cursor
            end = local_cursor + line_duration

            entries.append(
                f"{subtitle_no}\n"
                f"{srt_time(start)} --> {srt_time(end)}\n"
                f"{text}\n"
            )

            subtitle_no += 1
            local_cursor = end

        cursor += video_duration

    out_srt.write_text(
        "\n".join(entries) + "\n",
        encoding="utf-8"
    )

    return cursor, len(entries)


def create_concat(scenes, input_dir: Path, concat_file: Path):
    lines = []

    for scene in scenes:
        n = int(scene["scene"])
        video = find_scene_video(input_dir, n)
        lines.append(f"file {shlex.quote(str(video))}")

    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        description="Post-production automatique épisode YouTube"
    )
    ap.add_argument(
        "--scenes",
        default="episode_01_scenes_wolof.json",
    )
    ap.add_argument(
        "--input-dir",
        default="output/episode",
    )
    ap.add_argument(
        "--output",
        default="output/episode/episode_youtube.mp4",
    )
    ap.add_argument(
        "--music",
        default=None,
        help="MP3 musique de fond facultatif",
    )
    ap.add_argument(
        "--music-volume",
        type=float,
        default=0.08,
    )
    ap.add_argument(
        "--burn-subs",
        action="store_true",
        help="Incruste les sous-titres directement dans la vidéo",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Vérifie les fichiers sans produire de vidéo",
    )

    args = ap.parse_args()

    scenes_path = Path(args.scenes).expanduser()
    input_dir = Path(args.input_dir).expanduser()
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)

    _, scenes = load_scenes(scenes_path)

    print(f"📖 {scenes_path.name}")
    print(f"🎞️  {len(scenes)} scènes")

    missing_videos = []
    missing_audio = []

    for scene in scenes:
        n = int(scene["scene"])

        try:
            video = find_scene_video(input_dir, n)
            print(f"✅ Scène {n:02d} vidéo : {video.name}")
        except FileNotFoundError:
            missing_videos.append(n)
            print(f"❌ Scène {n:02d} vidéo absente")

        audios = find_line_audio(input_dir, n)
        expected = len([
            x for x in scene.get("dialogue", [])
            if (x.get("text") or "").strip()
        ])

        if len(audios) == expected:
            print(f"✅ Scène {n:02d} audio : {len(audios)} ligne(s)")
        else:
            missing_audio.append(n)
            print(
                f"❌ Scène {n:02d} audio : "
                f"{len(audios)}/{expected}"
            )

    if args.check:
        print("\n🔎 CONTRÔLE TERMINÉ")
        if missing_videos or missing_audio:
            print("⚠️ Des fichiers sont encore absents.")
        else:
            print("✅ Toutes les vidéos et pistes audio sont présentes.")
        return

    if missing_videos:
        raise RuntimeError(
            f"Vidéos manquantes : {missing_videos}"
        )

    if missing_audio:
        raise RuntimeError(
            f"Audios manquants : {missing_audio}"
        )

    out_srt = output.parent / "episode_subtitles.srt"
    concat_file = output.parent / "episode_concat.txt"
    temp_video = output.parent / "episode_video_temp.mp4"

    print("\n📝 Création des sous-titres...")
    total_duration, subtitle_count = build_srt(
        scenes,
        input_dir,
        out_srt
    )

    print(f"✅ {subtitle_count} sous-titres")
    print(f"✅ Durée totale estimée : {total_duration:.2f}s")
    print(f"📄 {out_srt}")

    create_concat(scenes, input_dir, concat_file)

    ffmpeg = ffmpeg_path()

    print("\n🎬 Assemblage des scènes...")
    run([
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(temp_video),
    ])

    input_args = [
        "-i", str(temp_video)
    ]

    if args.music:
        music = Path(args.music).expanduser()
        if not music.exists():
            raise FileNotFoundError(f"Musique introuvable : {music}")
        input_args += [
            "-stream_loop", "-1",
            "-i", str(music),
        ]

    video_filter = "null"

    if args.burn_subs:
        subtitle_path = str(out_srt).replace("\\", "/")
        video_filter = (
            f"subtitles='{subtitle_path}':"
            "force_style='FontName=DejaVu Sans,"
            "FontSize=22,"
            "Outline=2,"
            "Shadow=1,"
            "Alignment=2,"
            "MarginV=30'"
        )

    final_cmd = [
        ffmpeg,
        "-y",
        *input_args,
        "-filter:v", video_filter,
    ]

    if args.music:
        if has_audio(temp_video):
            final_cmd += [
                "-filter_complex",
                (
                    f"[1:a]volume={args.music_volume}[music];"
                    "[0:a][music]"
                    "amix=inputs=2:duration=first:"
                    "dropout_transition=2[aout]"
                ),
                "-map", "0:v:0",
                "-map", "[aout]",
            ]
        else:
            final_cmd += [
                "-filter_complex",
                f"[1:a]volume={args.music_volume}[aout]",
                "-map", "0:v:0",
                "-map", "[aout]",
            ]
    else:
        final_cmd += [
            "-map", "0:v:0",
            "-map", "0:a:0?",
        ]

    final_cmd += [
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(output),
    ]

    print("\n🎧 Post-production finale...")
    run(final_cmd)

    try:
        temp_video.unlink()
    except FileNotFoundError:
        pass

    print("\n✅ ÉPISODE FINALISÉ")
    print(f"🎬 Vidéo : {output}")
    print(f"📝 Sous-titres : {out_srt}")


if __name__ == "__main__":
    main()
