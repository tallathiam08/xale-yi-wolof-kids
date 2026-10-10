import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


class Dialogue(BaseModel):
    speaker: Literal["Samba", "Awa", "Ibrahima"]
    text: str = Field(min_length=3, max_length=160)


class Scene(BaseModel):
    scene: int
    duration_hint: int
    prompt: str = Field(min_length=30)
    dialogue: list[Dialogue]


class Episode(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    language: Literal["Wolof"]
    target_duration: str
    scenes: list[Scene]


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY introuvable")

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Tu es le scénariste principal de la chaîne YouTube jeunesse
« Xale Yi – Wolof Kids ».

Nous faisons aujourd'hui un TEST AUTOMATISÉ le {now}.

Crée un épisode COMPLET pour enfants en 12 scènes, environ 5 secondes par scène,
soit environ 1 minute avec le workflow vidéo actuel.

PERSONNAGES FIXES :
- Samba : garçon
- Awa : fille
- Ibrahima : garçon avec lunettes
- Toto : petit chien marron

RÈGLES :
1. L'histoire doit être nouvelle et différente des épisodes précédents.
2. Elle doit être simple, amusante, positive et adaptée aux jeunes enfants.
3. Le contexte culturel peut être sénégalais : école, famille, quartier, bus,
   marché, plage, maison, parc, etc.
4. Tous les dialogues doivent être en WOLOF.
5. Les dialogues doivent être courts et naturels.
6. Chaque scène contient 1 ou 2 répliques maximum.
7. Les prompts visuels doivent être en ANGLAIS.
8. Les prompts visuels doivent toujours conserver les mêmes personnages,
   vêtements et style 2D cartoon pour assurer la continuité.
9. Aucun texte, sous-titre, logo ou watermark dans les prompts visuels.
10. Chaque scène doit faire avancer clairement l'histoire.
11. La scène 12 doit donner une vraie conclusion avec une petite leçon positive.
12. Ne retourne AUCUN markdown.
13. Retourne UNIQUEMENT le JSON conforme au schéma demandé.

Le résultat doit contenir EXACTEMENT 12 scènes numérotées de 1 à 12.
Chaque scène doit avoir duration_hint = 5.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Episode,
        },
    )

    if not response.parsed:
        raise RuntimeError("Gemini n'a pas retourné une structure JSON valide")

    episode = response.parsed

    if len(episode.scenes) != 12:
        raise RuntimeError(
            f"Nombre de scènes incorrect : {len(episode.scenes)} au lieu de 12"
        )

    expected_numbers = list(range(1, 13))
    actual_numbers = [scene.scene for scene in episode.scenes]

    if actual_numbers != expected_numbers:
        raise RuntimeError(
            f"Numérotation incorrecte : {actual_numbers}"
        )

    for scene in episode.scenes:
        if scene.duration_hint != 5:
            raise RuntimeError(
                f"Scène {scene.scene}: duration_hint doit être 5"
            )

        if not (1 <= len(scene.dialogue) <= 2):
            raise RuntimeError(
                f"Scène {scene.scene}: 1 à 2 dialogues attendus"
            )

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "episode_github_generated.json"
    output_file.write_text(
        json.dumps(episode.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_dialogues = sum(len(scene.dialogue) for scene in episode.scenes)

    print("✅ Épisode généré avec succès")
    print(f"🎬 Titre : {episode.title}")
    print(f"🎞️ Scènes : {len(episode.scenes)}/12")
    print(f"🗣️ Dialogues : {total_dialogues}")
    print(f"🤖 Modèle : {model}")
    print(f"📄 Fichier : {output_file}")


if __name__ == "__main__":
    main()
