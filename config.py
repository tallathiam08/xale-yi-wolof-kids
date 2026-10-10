import os
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not ELEVENLABS_API_KEY:
    raise RuntimeError(
        "ELEVENLABS_API_KEY est introuvable dans le fichier .env"
    )

VOICES = {
    "samba": "X865dA5LI1E5Gjl4Dm7g",
    "ibrahima": "hDAktVoHpCg7hnHohRjC",
    "awa": "9hOVxSsZXpvpKz5POzU1",
}

