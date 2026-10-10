import json
import os
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from huggingface_hub import hf_hub_download
from transformers import (
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
    SpeechT5Processor,
)


MODEL_ID = "bilalfaye/speecht5_tts-wolof-v0.2"
VOCODER_ID = "microsoft/speecht5_hifigan"

EPISODE_FILE = Path("output/episode_github_generated.json")
OUTPUT_DIR = Path("output/wolof_audio")
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"

EXPECTED_SCENES = 60


def load_speaker_embedding(device):
    print("📥 Téléchargement des speaker embeddings...")

    zip_path = hf_hub_download(
        repo_id="Matthijs/cmu-arctic-xvectors",
        filename="spkrec-xvect.zip",
        repo_type="dataset",
    )

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(
            name for name in zf.namelist()
            if name.endswith(".npy")
        )

        if len(names) <= 7306:
            raise RuntimeError(
                f"Nombre de speaker embeddings insuffisant : {len(names)}"
            )

        with zf.open(names[7306]) as f:
            embedding = np.load(f)

    tensor = torch.tensor(
        embedding,
        dtype=torch.float32,
    ).unsqueeze(0).to(device)

    print("✅ Speaker embedding chargé")

    return tensor


def generate_line(
    model,
    processor,
    vocoder,
    speaker_embedding,
    text,
    output_file,
    device,
):
    inputs = processor(
        text=text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=model.config.max_text_positions,
    )

    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs.get("attention_mask")

    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    with torch.no_grad():
        speech = model.generate(
            input_ids,
            attention_mask=attention_mask,
            speaker_embeddings=speaker_embedding,
            vocoder=vocoder,
            num_beams=4,
            no_repeat_ngram_size=3,
            repetition_penalty=1.5,
        )

    audio = speech.detach().cpu().numpy().squeeze()

    if audio.size == 0:
        raise RuntimeError(f"Audio vide généré pour : {text}")

    sf.write(
        output_file,
        np.asarray(audio, dtype=np.float32),
        16000,
    )

    return len(audio) / 16000


def main():
    if not EPISODE_FILE.exists():
        raise RuntimeError(
            f"Épisode introuvable : {EPISODE_FILE}"
        )

    episode = json.loads(
        EPISODE_FILE.read_text(encoding="utf-8")
    )

    scenes = episode.get("scenes", [])

    if len(scenes) != EXPECTED_SCENES:
        raise RuntimeError(
            f"Nombre de scènes incorrect : "
            f"{len(scenes)} au lieu de {EXPECTED_SCENES}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    cpu_count = os.cpu_count() or 2

    if device.type == "cpu":
        torch.set_num_threads(
            max(1, min(cpu_count, 4))
        )

    print(f"🖥️ Device : {device}")
    print(f"🎙️ Modèle : {MODEL_ID}")
    print(f"🎞️ Scènes : {len(scenes)}")

    print("📦 Chargement du modèle...")

    processor = SpeechT5Processor.from_pretrained(
        MODEL_ID
    )

    model = SpeechT5ForTextToSpeech.from_pretrained(
        MODEL_ID
    ).to(device)

    vocoder = SpeechT5HifiGan.from_pretrained(
        VOCODER_ID
    ).to(device)

    model.eval()
    vocoder.eval()

    print("✅ Modèle et vocodeur chargés")

    speaker_embedding = load_speaker_embedding(device)

    manifest = []
    total_dialogues = 0
    total_seconds = 0.0

    for scene in scenes:
        scene_number = int(scene["scene"])
        dialogues = scene.get("dialogue", [])

        if not dialogues:
            raise RuntimeError(
                f"Scène {scene_number}: aucun dialogue"
            )

        scene_dir = OUTPUT_DIR / f"scene_{scene_number:02d}"
        scene_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        for line_number, dialogue in enumerate(
            dialogues,
            start=1,
        ):
            speaker = dialogue["speaker"]
            text = dialogue["text"].strip()

            if not text:
                raise RuntimeError(
                    f"Scène {scene_number}, ligne "
                    f"{line_number}: texte vide"
                )

            output_file = (
                scene_dir
                / f"line_{line_number:02d}_{speaker}.wav"
            )

            print(
                f"🗣️ Scène {scene_number:02d} "
                f"/ ligne {line_number:02d} "
                f"/ {speaker}"
            )

            duration = generate_line(
                model=model,
                processor=processor,
                vocoder=vocoder,
                speaker_embedding=speaker_embedding,
                text=text,
                output_file=output_file,
                device=device,
            )

            total_dialogues += 1
            total_seconds += duration

            manifest.append(
                {
                    "scene": scene_number,
                    "line": line_number,
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

    MANIFEST_FILE.write_text(
        json.dumps(
            {
                "model": MODEL_ID,
                "sample_rate": 16000,
                "scenes": EXPECTED_SCENES,
                "dialogues": total_dialogues,
                "total_audio_seconds": round(
                    total_seconds,
                    2,
                ),
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("🎉 AUDIO WOLOF COMPLET")
    print(
        f"🎞️ Scènes : {EXPECTED_SCENES}/{EXPECTED_SCENES}"
    )
    print(
        f"🗣️ Dialogues : {total_dialogues}"
    )
    print(
        f"⏱️ Audio généré : {total_seconds:.2f}s"
    )
    print(
        f"📁 Dossier : {OUTPUT_DIR}"
    )
    print(
        f"📄 Manifest : {MANIFEST_FILE}"
    )


if __name__ == "__main__":
    main()
