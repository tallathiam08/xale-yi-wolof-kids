import json
import os
from pathlib import Path

import soundfile as sf
import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer


MODEL = "AYI-TEKK/Adia_TTS"

EPISODE_FILE = Path("output/episode_github_generated.json")
OUTPUT_DIR = Path("output/adia_audio")

LIMIT = int(os.getenv("ADIA_LIMIT", "3"))


DESCRIPTION = (
    "A warm, natural and friendly Senegalese Wolof voice, "
    "clear pronunciation, lively rhythm, cheerful and expressive, "
    "suitable for a children's animation."
)


def main():
    if not EPISODE_FILE.exists():
        raise RuntimeError(
            f"Épisode introuvable : {EPISODE_FILE}"
        )

    data = json.loads(
        EPISODE_FILE.read_text(encoding="utf-8")
    )

    dialogues = []

    for scene in data.get("scenes", []):
        scene_number = int(scene["scene"])

        for line_number, dialogue in enumerate(
            scene.get("dialogue", []),
            start=1,
        ):
            dialogues.append(
                {
                    "scene": scene_number,
                    "line": line_number,
                    "speaker": dialogue["speaker"],
                    "text": dialogue["text"].strip(),
                }
            )

    if not dialogues:
        raise RuntimeError("Aucun dialogue trouvé")

    dialogues = dialogues[:LIMIT]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    device = (
        "cuda:0"
        if torch.cuda.is_available()
        else "cpu"
    )

    if device == "cpu":
        torch.set_num_threads(
            max(1, min(os.cpu_count() or 2, 4))
        )

    print(f"🖥️ Device : {device}")
    print(f"🎙️ Modèle : {MODEL}")
    print(f"🗣️ Dialogues à générer : {len(dialogues)}")
    print("📥 Chargement du modèle...")

    model = ParlerTTSForConditionalGeneration.from_pretrained(
        MODEL
    ).to(device)

    tokenizer = AutoTokenizer.from_pretrained(MODEL)

    model.eval()

    print("✅ Modèle chargé")

    description_ids = tokenizer(
        DESCRIPTION,
        return_tensors="pt",
    ).input_ids.to(device)

    manifest = []

    for item in dialogues:
        scene = item["scene"]
        line = item["line"]
        speaker = item["speaker"]
        text = item["text"]

        if not text:
            continue

        output_file = (
            OUTPUT_DIR
            / f"scene_{scene:02d}_line_{line:02d}_{speaker}.wav"
        )

        print()
        print(
            f"🗣️ Scène {scene:02d} "
            f"/ ligne {line:02d} "
            f"/ {speaker}"
        )
        print(f"   {text}")

        prompt_ids = tokenizer(
            text,
            return_tensors="pt",
        ).input_ids.to(device)

        with torch.inference_mode():
            audio = model.generate(
                input_ids=description_ids,
                prompt_input_ids=prompt_ids,
                temperature=0.8,
                do_sample=True,
                top_k=50,
                repetition_penalty=1.2,
                max_new_tokens=1000,
            )

        waveform = audio.cpu().numpy().squeeze()

        if waveform.size == 0:
            raise RuntimeError(
                f"Audio vide : scène {scene}, ligne {line}"
            )

        sf.write(
            output_file,
            waveform,
            model.config.sampling_rate,
        )

        duration = (
            len(waveform)
            / model.config.sampling_rate
        )

        manifest.append(
            {
                "scene": scene,
                "line": line,
                "speaker": speaker,
                "text": text,
                "file": str(output_file),
                "duration_seconds": round(
                    duration,
                    3,
                ),
            }
        )

        print(
            f"   ✅ {duration:.2f}s"
        )

    manifest_file = OUTPUT_DIR / "manifest.json"

    manifest_file.write_text(
        json.dumps(
            {
                "model": MODEL,
                "dialogues_generated": len(manifest),
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("🎉 TEST ADIA TERMINÉ")
    print(
        f"🗣️ Dialogues : {len(manifest)}"
    )
    print(
        f"📄 Manifest : {manifest_file}"
    )


if __name__ == "__main__":
    main()
