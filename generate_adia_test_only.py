import json
from pathlib import Path

import soundfile as sf
import torch

from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer


MODEL = "AYI-TEKK/Adia_TTS"

OUTPUT_DIR = Path("output/adia_audio_test")

DESCRIPTION = (
    "A warm, natural and friendly Senegalese Wolof voice, "
    "clear pronunciation, lively rhythm, cheerful and expressive, "
    "suitable for a children's animation."
)

TEST_DIALOGUES = [
    {
        "scene": 1,
        "line": 1,
        "speaker": "Samba",
        "text": "Naka nga def? Tey nu dem ci ekol.",
    },
    {
        "scene": 1,
        "line": 2,
        "speaker": "Awa",
        "text": "Waaw Samba, nu dem!",
    },
    {
        "scene": 2,
        "line": 1,
        "speaker": "Ibrahima",
        "text": "Toto, bul daw bu gaaw!",
    },
]


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    device = (
        "cuda:0"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(f"🖥️ Device : {device}")
    print(f"🎙️ Modèle : {MODEL}")
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

    for item in TEST_DIALOGUES:
        scene = item["scene"]
        line = item["line"]
        speaker = item["speaker"]
        text = item["text"]

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


if __name__ == "__main__":
    main()
