import json
import shutil
from pathlib import Path


MANIFEST = Path("output/adia_audio/manifest.json")
SOURCE_DIR = Path("output/adia_audio")
TARGET_DIR = Path("output/wolof_audio")


def main():
    if not MANIFEST.exists():
        raise RuntimeError(f"Manifest introuvable : {MANIFEST}")

    data = json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )

    files = data.get("files", [])

    if not files:
        raise RuntimeError("Aucun audio ADIA trouvé")

    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)

    TARGET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for item in files:
        scene = int(item["scene"])
        line = int(item["line"])
        speaker = item["speaker"]

        source = Path(item["file"])

        if not source.exists():
            source = SOURCE_DIR / source.name

        if not source.exists():
            raise RuntimeError(
                f"Audio introuvable : {source}"
            )

        scene_dir = (
            TARGET_DIR / f"scene_{scene:02d}"
        )
        scene_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            scene_dir
            / f"line_{line:02d}_{speaker}.wav"
        )

        shutil.copy2(
            source,
            destination,
        )

        print(
            f"✅ Scène {scene:02d} "
            f"/ ligne {line:02d} "
            f"/ {speaker}"
        )

    total = len(list(TARGET_DIR.rglob("*.wav")))

    if total != len(files):
        raise RuntimeError(
            f"Nombre incorrect : {total} WAV "
            f"pour {len(files)} dialogues"
        )

    print()
    print("🎉 AUDIO ADIA PRÊT POUR LE PIPELINE")
    print(f"🗣️ Dialogues : {total}")
    print(f"📁 Dossier : {TARGET_DIR}")


if __name__ == "__main__":
    main()
