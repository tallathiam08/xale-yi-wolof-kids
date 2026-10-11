import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


TOTAL_SCENES = 60
SCENE_DURATION = 5
TARGET_SECONDS = TOTAL_SCENES * SCENE_DURATION


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

Nous créons un épisode entièrement automatisé le {now}.

OBJECTIF TECHNIQUE :
- durée totale : exactement 5 minutes
- exactement {TOTAL_SCENES} scènes
- chaque scène dure exactement {SCENE_DURATION} secondes
- total : exactement {TARGET_SECONDS} secondes

PERSONNAGES FIXES :
- Samba : garçon sénégalais, t-shirt jaune, short bleu
- Awa : fille sénégalaise, robe orange
- Ibrahima : garçon sénégalais, lunettes rondes, polo vert, short beige
- Toto : petit chien marron

STYLE VISUEL FIXE :
- animation 2D cartoon pour enfants
- couleurs vives
- expressions joyeuses
- apparence cohérente d'une scène à l'autre
- mêmes vêtements et mêmes personnages pendant tout l'épisode
- ambiance sénégalaise familiale et positive

RÈGLES DE L'HISTOIRE :
1. Crée UNE histoire complète, originale et amusante.
2. L'histoire doit progresser du début jusqu'à une vraie conclusion.
3. Les 60 scènes doivent être liées entre elles.
4. Aucun saut brutal ou changement inexplicable de lieu.
5. Les scènes doivent être faciles à transformer en clips vidéo séparés.
6. Les enfants doivent pouvoir comprendre l'histoire simplement.
7. La fin doit contenir une petite morale positive.
8. L'histoire doit être adaptée aux enfants.
9. Aucun contenu violent, dangereux, sexuel ou effrayant.
10. Le contexte peut être sénégalais : école, maison, quartier, bus,
    plage, parc, marché, famille, anniversaire, etc.

DIALOGUES :
1. Tous les dialogues doivent être en WOLOF.
2. Maximum 2 répliques par scène.
3. Les phrases doivent être courtes et naturelles.
4. Les personnages doivent réellement dialoguer.
5. Ne donne jamais une longue narration à la place des dialogues.
6. Chaque scène doit contenir EXACTEMENT 2 répliques.
7. Répartis les dialogues naturellement entre Samba, Awa et Ibrahima.
8. Toto ne parle pas : il agit, aboie ou réagit visuellement.
9. Chaque réplique doit contenir environ 6 à 14 mots.
10. Le deuxième personnage doit répondre rapidement au premier.
11. Utilise des réactions amusantes et naturelles : ah!, waaw!, ehe!, déedéet!, kaay!, etc. seulement quand elles sont naturelles.
12. Évite les longues phrases et les explications.
13. Le rythme doit ressembler à une vraie conversation d'enfants.

PROMPTS VISUELS :
1. Les prompts visuels doivent être en ANGLAIS.
2. Chaque prompt doit décrire précisément l'action de la scène.
3. Conserve strictement les personnages, vêtements et style.
4. Décris le décor, les actions et les expressions.
5. Pas de texte à l'écran.
6. Pas de sous-titres.
7. Pas de logo.
8. Pas de watermark.
9. Aucun changement arbitraire d'apparence des personnages.

STRUCTURE :
- Scène 1 commence l'histoire.
- Scènes 2 à 55 développent progressivement le problème et les actions.
- Scènes 56 à 59 résolvent le problème.
- Scène 60 conclut l'histoire avec une petite morale positive.

IMPORTANT :
- Retourne UNIQUEMENT le JSON.
- Aucun markdown.
- EXACTEMENT {TOTAL_SCENES} scènes.
- Numéros de scène exactement de 1 à {TOTAL_SCENES}.
- Chaque duration_hint doit être exactement {SCENE_DURATION}.
- Chaque scène doit contenir entre 1 et 2 dialogues.
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

    if len(episode.scenes) != TOTAL_SCENES:
        raise RuntimeError(
            f"Nombre de scènes incorrect : {len(episode.scenes)} "
            f"au lieu de {TOTAL_SCENES}"
        )

    expected_numbers = list(range(1, TOTAL_SCENES + 1))
    actual_numbers = [scene.scene for scene in episode.scenes]

    if actual_numbers != expected_numbers:
        raise RuntimeError(
            f"Numérotation incorrecte : {actual_numbers}"
        )

    for scene in episode.scenes:
        if scene.duration_hint != SCENE_DURATION:
            raise RuntimeError(
                f"Scène {scene.scene}: duration_hint doit être "
                f"{SCENE_DURATION}"
            )

        if len(scene.dialogue) != 2:
            raise RuntimeError(
                f"Scène {scene.scene}: exactement 2 dialogues attendus"
            )

        for dialogue in scene.dialogue:
            word_count = len(dialogue.text.split())

            if not (6 <= word_count <= 14):
                raise RuntimeError(
                    f"Scène {scene.scene}: réplique trop courte ou trop longue "
                    f"({word_count} mots, attendu 6 à 14)"
                )

        if not scene.prompt.strip():
            raise RuntimeError(
                f"Scène {scene.scene}: prompt visuel vide"
            )

    total_seconds = sum(
        scene.duration_hint for scene in episode.scenes
    )

    if total_seconds != TARGET_SECONDS:
        raise RuntimeError(
            f"Durée incorrecte : {total_seconds}s "
            f"au lieu de {TARGET_SECONDS}s"
        )

    episode.target_duration = "5min"

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "episode_github_generated.json"

    output_file.write_text(
        json.dumps(
            episode.model_dump(),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8",
    )

    total_dialogues = sum(
        len(scene.dialogue) for scene in episode.scenes
    )

    print("✅ Épisode 5 minutes généré avec succès")
    print(f"🎬 Titre : {episode.title}")
    print(f"🎞️ Scènes : {len(episode.scenes)}/{TOTAL_SCENES}")
    print(f"⏱️ Durée : {total_seconds}s / 300s")
    print(f"🗣️ Dialogues : {total_dialogues}")
    print(f"🤖 Modèle : {model}")
    print(f"📄 Fichier : {output_file}")


if __name__ == "__main__":
    main()
