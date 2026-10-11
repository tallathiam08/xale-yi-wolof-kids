import soundfile as sf
import torch

from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer


MODEL = "AYI-TEKK/Adia_TTS"

TEXT = (
    "Naka nga def? Tey, nu dem ci ekol ak seeni xarit."
)

DESCRIPTION = (
    "A warm, natural and friendly Senegalese Wolof voice, "
    "clear pronunciation, lively rhythm, cheerful and expressive, "
    "suitable for a children's animation."
)


def main():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    print(f"🖥️ Device : {device}")
    print(f"🎙️ Modèle : {MODEL}")
    print("📥 Chargement...")

    model = ParlerTTSForConditionalGeneration.from_pretrained(
        MODEL
    ).to(device)

    tokenizer = AutoTokenizer.from_pretrained(MODEL)

    print("✅ Modèle chargé")
    print("🗣️ Génération...")

    input_ids = tokenizer(
        DESCRIPTION,
        return_tensors="pt"
    ).input_ids.to(device)

    prompt_ids = tokenizer(
        TEXT,
        return_tensors="pt"
    ).input_ids.to(device)

    with torch.inference_mode():
        audio = model.generate(
            input_ids=input_ids,
            prompt_input_ids=prompt_ids,
        )

    output = "output/adia_wolof_test.wav"

    sf.write(
        output,
        audio.cpu().numpy().squeeze(),
        model.config.sampling_rate,
    )

    print("✅ ADIA WOOLOF GÉNÉRÉ")
    print(f"📄 {output}")
    print(
        f"⏱️ Durée : "
        f"{len(audio.squeeze()) / model.config.sampling_rate:.2f}s"
    )


if __name__ == "__main__":
    main()
