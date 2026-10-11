import subprocess
from pathlib import Path
import os

AUDIO_DIR = Path("output/wolof_audio")
SPEED = float(os.getenv("DIALOGUE_SPEED", "1.10"))

if SPEED <= 0:
    raise RuntimeError("DIALOGUE_SPEED doit être > 0")

wav_files = sorted(AUDIO_DIR.rglob("*.wav"))

if not wav_files:
    raise RuntimeError(f"Aucun WAV trouvé dans {AUDIO_DIR}")

print(f"🎙️ Accélération dialogues : x{SPEED:.2f}")
print(f"🔊 Fichiers : {len(wav_files)}")

for index, wav in enumerate(wav_files, start=1):
    temp = wav.with_name(wav.stem + "_retimed.wav")

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav),
            "-filter:a",
            f"atempo={SPEED:.4f}",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(temp),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"Échec audio : {wav}")

    temp.replace(wav)

    if index % 10 == 0 or index == len(wav_files):
        print(f"✅ {index}/{len(wav_files)}")

print("🎉 Dialogues accélérés avec succès")
