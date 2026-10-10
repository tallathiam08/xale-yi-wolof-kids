import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from elevenlabs.client import ElevenLabs

from config import ELEVENLABS_API_KEY, VOICES

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

SCRIPT_DIR = Path("scripts")
AUDIO_DIR = Path("audio/episode")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Trouve le dernier épisode généré
scripts = sorted(SCRIPT_DIR.glob("episode_*.txt"))

if not scripts:
    raise RuntimeError("❌ Aucun scénario trouvé dans scripts/")

script_file = scripts[-1]

print(f"📄 Épisode sélectionné : {script_file}")

content = script_file.read_text(encoding="utf-8")

# Enlève le Markdown utilisé par Gemini :
# **SCÈNE 1:** -> SCÈNE 1:
# **Samba:** -> Samba:
clean_content = re.sub(r"\*\*", "", content)
clean_content = re.sub(r"__", "", clean_content)

# Recherche des scènes
scene_pattern = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?SC[EÈ]NE\s*(\d+)\s*:?.*$"
)

matches = list(scene_pattern.finditer(clean_content))

if not matches:
    print("\n❌ Aucune scène détectée.")
    print("\nVoici le début du scénario :")
    print(clean_content[:4000])
    raise RuntimeError("❌ Aucune scène détectée dans le scénario.")

print(f"🎬 {len(matches)} scènes détectées.")

# Supprime les anciens fichiers audio de scène
for old_file in AUDIO_DIR.glob("scene_*.mp3"):
    old_file.unlink()

for i, match in enumerate(matches):

    scene_number = int(match.group(1))

    start = match.end()

    if i + 1 < len(matches):
        end = matches[i + 1].start()
        scene_text = clean_content[start:end]
    else:
        scene_text = clean_content[start:]

    print(f"\n🎞️ SCÈNE {scene_number}")

    # Accepte :
    # Samba: texte
    # Samba : texte
    # Samba - texte
    # Samba — texte
    dialogue_pattern = re.compile(
        r"(?im)^\s*(Samba|Ibrahima|Awa(?:\s+ak\s+Toto)?)\s*[:\-—]\s*(.+?)\s*$"
    )

    dialogues = dialogue_pattern.findall(scene_text)

    if not dialogues:
        print("⚠️ Aucun dialogue trouvé dans cette scène.")
        continue

    scene_parts = []

    for index, (speaker, text) in enumerate(dialogues):

        # Supprime les indications entre parenthèses
        text = re.sub(r"\([^)]*\)", "", text)

        # Supprime les indications entre crochets
        text = re.sub(r"\[[^\]]*\]", "", text)

        # Nettoyage
        text = text.strip()

        if not text:
            continue

        speaker_clean = speaker.lower().strip()

        if speaker_clean.startswith("awa"):
            voice_id = VOICES["awa"]
        elif speaker_clean == "samba":
            voice_id = VOICES["samba"]
        elif speaker_clean == "ibrahima":
            voice_id = VOICES["ibrahima"]
        else:
            print(f"⚠️ Personnage inconnu : {speaker}")
            continue

        print(f"   🗣️ {speaker}: {text}")

        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
model_id="eleven_v4",
            output_format="mp3_44100_128",
        )

        temp_file = AUDIO_DIR / f"temp_{scene_number:02d}_{index:02d}.mp3"

        with open(temp_file, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        scene_parts.append(temp_file)

    if not scene_parts:
        print("⚠️ Aucun audio créé pour cette scène.")
        continue

    # Fichier concaténation
    concat_file = AUDIO_DIR / f"concat_{scene_number:02d}.txt"
    output_file = AUDIO_DIR / f"scene_{scene_number:02d}.mp3"

    with open(concat_file, "w", encoding="utf-8") as f:
        for part in scene_parts:
            f.write(f"file '{part.resolve()}'\n")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_file),
    ]

    subprocess.run(command, check=True)

    # Nettoyage
    for part in scene_parts:
        part.unlink(missing_ok=True)

    concat_file.unlink(missing_ok=True)

    print(f"   ✅ {output_file}")

print("\n========================================")
print("🎉 AUDIO DE L'ÉPISODE TERMINÉ")
print("========================================")
