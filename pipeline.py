import argparse
import subprocess
import sys


def run(cmd):
    print("\n▶", " ".join(str(x) for x in cmd))
    result = subprocess.run([str(x) for x in cmd])
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    ap = argparse.ArgumentParser(
        description="Pipeline automatique YouTube Wolof"
    )

    ap.add_argument("--check", action="store_true",
                    help="Vérifie tout sans générer")

    ap.add_argument("--status", action="store_true",
                    help="Affiche l'état du pipeline sans rien générer")

    ap.add_argument("--audio-only", action="store_true",
                    help="Génère/reprend uniquement les audios")

    ap.add_argument("--with-audio", action="store_true",
                    help="Génère/reprend les vidéos + audios")

    ap.add_argument("--postprocess", action="store_true",
                    help="Assemble les scènes et crée les sous-titres")

    ap.add_argument("--full", action="store_true",
                    help="Audio → vidéo → post-production")

    ap.add_argument("--upload", action="store_true",
                    help="Envoie l'épisode final sur YouTube")

    ap.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="Visibilité YouTube (défaut: private)"
    )

    ap.add_argument(
        "--made-for-kids",
        action="store_true",
        help="Déclare la vidéo comme destinée aux enfants"
    )

    ap.add_argument(
        "--publish-at",
        default=None,
        help="Date ISO 8601 pour programmer la publication"
    )

    ap.add_argument("--force", action="store_true",
                    help="Régénère les fichiers existants")

    args = ap.parse_args()

    modes = [
        args.check,
        args.status,
        args.audio_only,
        args.with_audio,
        args.postprocess,
        args.full,
    ]

    if sum(modes) > 1:
        ap.error("Choisis un seul mode principal.")

    # ---------------------------------------------------------
    # CHECK GLOBAL
    # ---------------------------------------------------------
    if args.check:
        run([
            sys.executable,
            "episode_automation_v2.py",
            "--check-audio",
        ])

        run([
            sys.executable,
            "postprocess_episode.py",
            "--check",
        ])

        print("\n✅ CHECK GLOBAL TERMINÉ")
        return

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------
    if args.status:
        import json
        from pathlib import Path

        scenes_file = Path("episode_01_scenes_wolof.json")
        output_dir = Path("output/episode")

        data = json.loads(
            scenes_file.read_text(encoding="utf-8")
        )

        scenes = data["scenes"]

        video_ok = 0
        audio_ok = 0
        audio_lines_ok = 0
        audio_lines_total = 0

        print("\n📊 STATUT DU PIPELINE")
        print(f"🎞️  Scènes : {len(scenes)}")

        for scene in scenes:
            n = int(scene["scene"])

            video_candidates = [
                output_dir / "scenes" / f"scene_{n:02d}_final.mp4",
                output_dir / f"scene_{n:02d}_final.mp4",
            ]

            video = next(
                (
                    x for x in video_candidates
                    if x.exists() and x.stat().st_size > 0
                ),
                None,
            )

            if video:
                video_ok += 1
                v = "✅"
            else:
                v = "❌"

            dialogue = [
                x for x in scene.get("dialogue", [])
                if (x.get("text") or "").strip()
            ]

            audio_dirs = [
                output_dir / "scenes" / f"scene_{n:02d}",
                output_dir / f"scene_{n:02d}",
            ]

            audio_dir = next(
                (x for x in audio_dirs if x.exists()),
                audio_dirs[0],
            )

            line_ok = 0

            for i in range(1, len(dialogue) + 1):
                audio = audio_dir / f"line_{i:02d}.mp3"
                audio_lines_total += 1

                if audio.exists() and audio.stat().st_size > 0:
                    line_ok += 1
                    audio_lines_ok += 1

            if line_ok == len(dialogue):
                audio_ok += 1
                a = "✅"
            else:
                a = "❌"

            print(
                f"Scène {n:02d} | "
                f"Vidéo {v} | "
                f"Audio {a} "
                f"({line_ok}/{len(dialogue)})"
            )

        print(
            f"\n🎬 Vidéos prêtes : "
            f"{video_ok}/{len(scenes)}"
        )

        print(
            f"🎧 Audios scènes prêtes : "
            f"{audio_ok}/{len(scenes)}"
        )

        print(
            f"🗣️  Lignes audio prêtes : "
            f"{audio_lines_ok}/{audio_lines_total}"
        )

        final = output_dir / "episode_final.mp4"

        if (
            final.exists()
            and final.stat().st_size > 0
            and video_ok == len(scenes)
        ):
            print("🎥 Épisode actuel : ✅ PRÉSENT")
        elif final.exists() and final.stat().st_size > 0:
            print("🎥 Épisode actuel : ❌ ABSENT")
            print("⚠️ Ancien episode_final.mp4 détecté")
        else:
            print("🎥 Épisode actuel : ❌ ABSENT")

        print("\n✅ Aucun service externe appelé")
        return

    # ---------------------------------------------------------
    # AUDIO ONLY
    # ---------------------------------------------------------
    if args.audio_only:
        cmd = [
            sys.executable,
            "episode_automation_v2.py",
            "--audio-only",
        ]

        if args.force:
            cmd.append("--force")

        run(cmd)
        return

    # ---------------------------------------------------------
    # VIDEO + AUDIO
    # ---------------------------------------------------------
    if args.with_audio:
        cmd = [
            sys.executable,
            "episode_automation_v2.py",
            "--with-audio",
        ]

        if args.force:
            cmd.append("--force")

        run(cmd)
        return

    # ---------------------------------------------------------
    # POST-PRODUCTION
    # ---------------------------------------------------------
    if args.postprocess:
        run([
            sys.executable,
            "postprocess_episode.py",
        ])
        return

    # ---------------------------------------------------------
    # UPLOAD EXISTANT
    # ---------------------------------------------------------
    if args.upload and not args.full:
        cmd = [
            sys.executable,
            "youtube_upload.py",
            "--video",
            "output/episode/episode_final.mp4",
            "--srt",
            "output/episode/episode_subtitles.srt",
            "--privacy",
            args.privacy,
        ]

        if args.made_for_kids:
            cmd.append("--made-for-kids")

        if args.publish_at:
            cmd += [
                "--publish-at",
                args.publish_at,
            ]

        run(cmd)
        return

    # ---------------------------------------------------------
    # FULL PIPELINE
    # ---------------------------------------------------------
    if args.full:
        print("\n🚀 PIPELINE COMPLET")
        print("================================")
        print("1️⃣  Audio")
        print("2️⃣  Vidéo + audio")
        print("3️⃣  Post-production")

        if args.upload:
            print("4️⃣  YouTube")

        print("================================")

        # 1 — AUDIO
        cmd_audio = [
            sys.executable,
            "episode_automation_v2.py",
            "--audio-only",
        ]

        if args.force:
            cmd_audio.append("--force")

        run(cmd_audio)

        # 2 — VIDEO + AUDIO
        cmd_video = [
            sys.executable,
            "episode_automation_v2.py",
            "--with-audio",
        ]

        if args.force:
            cmd_video.append("--force")

        run(cmd_video)

        # 3 — POST-PRODUCTION
        run([
            sys.executable,
            "postprocess_episode.py",
        ])

        # 4 — YOUTUBE
        if args.upload:
            cmd_upload = [
                sys.executable,
                "youtube_upload.py",
                "--video",
                "output/episode/episode_final.mp4",
                "--srt",
                "output/episode/episode_subtitles.srt",
                "--privacy",
                args.privacy,
            ]

            if args.made_for_kids:
                cmd_upload.append("--made-for-kids")

            if args.publish_at:
                cmd_upload += [
                    "--publish-at",
                    args.publish_at,
                ]

            run(cmd_upload)

        print("\n🎉 PIPELINE COMPLET TERMINÉ")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
