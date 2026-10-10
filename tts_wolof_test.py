from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from datasets import load_dataset
from transformers import (
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
    SpeechT5Processor,
)


MODEL_ID = "bilalfaye/speecht5_tts-wolof-v0.2"
VOCODER_ID = "microsoft/speecht5_hifigan"

TEXT = "Naka nga def? Tey, nu dina lekk ak ciyaar ak seeni xarit."


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"🤖 Device : {device}")
    print(f"🎙️ Modèle : {MODEL_ID}")

    processor = SpeechT5Processor.from_pretrained(MODEL_ID)
    model = SpeechT5ForTextToSpeech.from_pretrained(MODEL_ID).to(device)
    vocoder = SpeechT5HifiGan.from_pretrained(VOCODER_ID).to(device)

    print("✅ Modèle et vocodeur chargés")

    import zipfile
    from huggingface_hub import hf_hub_download

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
            speaker_embedding = torch.tensor(
                np.load(f),
                dtype=torch.float32,
            ).unsqueeze(0)

    print("✅ Speaker embedding chargé")

    inputs = processor(
        text=TEXT,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=model.config.max_text_positions,
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    print("🗣️ Génération de la voix Wolof...")

    with torch.no_grad():
        speech = model.generate(
            inputs["input_ids"],
            speaker_embeddings=speaker_embedding.to(device),
            vocoder=vocoder,
            num_beams=7,
            temperature=0.6,
            no_repeat_ngram_size=3,
            repetition_penalty=1.5,
        )

    audio = speech.detach().cpu().numpy().squeeze()

    output_dir = Path("output/tts_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "wolof_test.wav"

    sf.write(
        output_file,
        np.asarray(audio, dtype=np.float32),
        16000,
    )

    print("✅ AUDIO WOOLOF GÉNÉRÉ")
    print(f"📄 Fichier : {output_file}")
    print(f"⏱️ Durée : {len(audio) / 16000:.2f}s")


if __name__ == "__main__":
    main()
