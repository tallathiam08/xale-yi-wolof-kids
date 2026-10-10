import os
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY, VOICES

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

dialogue = [
    {
        "text": "[cheerfully] Salaam Awa! Ndax diyaar nga?",
        "voice_id": VOICES["samba"],
    },
    {
        "text": "[excited] Waaw! Man diyaar naa! Yow Ibrahima?",
        "voice_id": VOICES["awa"],
    },
    {
        "text": "[calmly] Waaw, man itam diyaar naa. Ñu dem!",
        "voice_id": VOICES["ibrahima"],
    },
    {
        "text": "[laughing] Ha ha ha! Toto, ñëwal ak nun!",
        "voice_id": VOICES["samba"],
    },
]

os.makedirs("audio/dialogues", exist_ok=True)

print("🎬 Génération du dialogue...")

audio = client.text_to_dialogue.convert(
    inputs=dialogue,
    model_id="eleven_v4",
    output_format="mp3_44100_128",
)

filename = "audio/dialogues/test_scene_01.mp3"

with open(filename, "wb") as f:
    for chunk in audio:
        f.write(chunk)

print(f"✅ Dialogue créé : {filename}")
à
