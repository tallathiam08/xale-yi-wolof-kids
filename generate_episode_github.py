import json
import os
import time
from datetime import datetime, timezone
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


TOTAL_SCENES = 60
SCENE_DURATION = 5
TARGET_SECONDS = 300


class Dialogue(BaseModel):
    speaker: Literal["Samba", "Awa", "Ibrahima"]
    text: str = Field(min_length=3, max_length=140)


class CharacterAction(BaseModel):
    name: Literal["Samba", "Awa", "Ibrahima", "Toto"]
    action: Literal[
        "idle",
        "talk",
        "walk",
        "run",
        "jump",
        "dance",
        "clap",
        "wave",
        "laugh",
        "surprised",
        "sad",
    ]
    emotion: Literal[
        "happy",
        "excited",
        "curious",
        "funny",
        "surprised",
        "calm",
        "sad",
    ]


class Scene(BaseModel):
    scene: int
    duration_hint: int
    scene_type: Literal[
        "story",
        "adventure",
        "comedy",
        "learning",
        "music",
        "dance",
        "calm",
        "celebration",
        "chase",
    ]
    location: Literal[
        "home",
        "school",
        "bus",
        "park",
        "market",
        "beach",
        "street",
        "kitchen",
        "bedroom",
        "celebration",
    ]
    camera: Literal[
        "wide",
        "medium",
        "close",
        "follow",
        "dance",
    ]
    music: bool
    characters: list[CharacterAction]
    prompt: str = Field(min_length=30, max_length=500)
    dialogue: list[Dialogue]


class Episode(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    language: Literal["Wolof"]
    target_duration: str
    scenes: list[Scene]


def build_prompt():
    seed = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d%H%M%S")

    return f"""
Tu es le showrunner de la série originale
« Xale Yi – Wolof Kids ».

SEED : {seed}

Crée un épisode original de 5 minutes pour enfants
sénégalais.

RÈGLES ABSOLUES :
- exactement 60 scènes
- chaque scène dure 5 secondes
- exactement 300 secondes
- exactement 2 dialogues par scène
- dialogues naturels en WOLof
- aucune phrase française ou anglaise
- Toto ne parle jamais
- les dialogues sont courts et rapides
- environ 5 à 9 mots par réplique

PERSONNAGES :
Samba = garçon sénégalais joyeux et énergique
Awa = fille sénégalaise vive, intelligente et drôle
Ibrahima = garçon sénégalais amusant avec lunettes rondes
Toto = petit chien marron joueur

IMPORTANT :
Ne reproduis pas une structure fixe.

Chaque épisode doit être différent.

Gemini doit choisir librement le thème :
- école
- maison
- bus
- marché
- parc
- plage
- anniversaire
- famille
- jeu
- aventure
- apprentissage
- mystère léger
- humour
- chanson
- danse
- chasse amusante

Mélange plusieurs situations quand c'est naturel.

MUSIQUE :
Il doit y avoir environ 2 à 5 moments musicaux.
Ils doivent être répartis naturellement.
Ils peuvent être séparés par des scènes d'histoire.
La danse ne doit jamais apparaître toujours au même endroit.

ACTION :
Chaque scène doit montrer une action claire :
courir, marcher, sauter, danser, applaudir,
chercher, découvrir, rire, tomber, saluer,
jouer, pousser, tirer, suivre Toto, etc.

CAMÉRA :
Varie :
wide, medium, close, follow, dance.

AMBIANCE :
Varie :
journée ensoleillée, intérieur chaleureux,
fête, parc animé, marché coloré, plage,
matin, après-midi, soirée calme, etc.

CONTINUITÉ :
Chaque scène doit continuer logiquement la précédente.
L'histoire doit avancer.

DIALOGUES :
Écris en véritable Wolof naturel.
Répliques rapides.
Réactions spontanées.
Humour simple.
Appels-réponses.
Pas de narration dans les dialogues.
Pas de français.
Pas d'anglais.
Pas de traduction.

PROMPTS VISUELS :
Écris-les en anglais.
Ils doivent décrire :
- lieu
- personnages
- action
- émotion
- ambiance
- caméra

Aucune écriture dans l'image.
Aucun logo.
Aucun watermark.
Aucun sous-titre.

STYLE :
Animation 2D cartoon premium originale.
Couleurs vives.
Visages expressifs.
Mouvements lisibles.
Univers sénégalais chaleureux.

Ne copie aucune autre chaîne ni aucun personnage existant.

La scène 60 doit conclure positivement l'histoire.

Retourne UNIQUEMENT le JSON conforme au schéma.
"""


def generate_with_fallback(client, prompt):
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
    ]

    retryable = {429, 500, 503, 504}
    last_error = None

    for model in models:
        for attempt in range(1, 4):
            try:
                print(
                    f"🤖 {model} — tentative {attempt}/3"
                )

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": Episode,
                    },
                )

                if not response.parsed:
                    raise RuntimeError(
                        "Réponse Gemini sans JSON structuré"
                    )

                print(
                    f"✅ Gemini disponible : {model}"
                )

                return response.parsed, model

            except Exception as exc:
                last_error = exc
                text = str(exc)

                print(
                    f"⚠️ Échec {model}: "
                    f"{text[:250]}"
                )

                code = None
                for value in retryable:
                    if (
                        f"{value} " in text
                        or f"code': {value}" in text
                        or f"code\": {value}" in text
                    ):
                        code = value
                        break

                if code not in retryable:
                    raise

                if attempt < 3:
                    delay = 8 * (2 ** (attempt - 1))

                    print(
                        f"⏳ Attente {delay}s..."
                    )

                    time.sleep(delay)

        print(
            f"🔄 Passage à {model} terminé"
        )

    raise RuntimeError(
        f"Tous les modèles Gemini ont échoué : {last_error}"
    )


def validate_episode(episode):
    if len(episode.scenes) != TOTAL_SCENES:
        raise RuntimeError(
            f"Nombre de scènes incorrect : "
            f"{len(episode.scenes)}"
        )

    expected = list(
        range(1, TOTAL_SCENES + 1)
    )

    actual = [
        scene.scene
        for scene in episode.scenes
    ]

    if actual != expected:
        raise RuntimeError(
            "Numérotation des scènes incorrecte"
        )

    total = 0

    for scene in episode.scenes:
        if scene.duration_hint != SCENE_DURATION:
            raise RuntimeError(
                f"Scène {scene.scene}: durée incorrecte"
            )

        if len(scene.dialogue) != 2:
            raise RuntimeError(
                f"Scène {scene.scene}: "
                "2 dialogues attendus"
            )

        if not 2 <= len(scene.characters) <= 4:
            raise RuntimeError(
                f"Scène {scene.scene}: "
                "2 à 4 personnages attendus"
            )

        total += scene.duration_hint

    if total != TARGET_SECONDS:
        raise RuntimeError(
            f"Durée incorrecte : {total}s"
        )


def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY introuvable"
        )

    client = genai.Client(
        api_key=api_key
    )

    episode, model = generate_with_fallback(
        client,
        build_prompt(),
    )

    validate_episode(episode)

    episode.target_duration = "5min"

    output_dir = "output"
    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    output_file = (
        f"{output_dir}/episode_github_generated.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            episode.model_dump(),
            f,
            ensure_ascii=False,
            indent=2,
        )

    music_count = sum(
        1
        for scene in episode.scenes
        if scene.music
    )

    locations = sorted({
        scene.location
        for scene in episode.scenes
    })

    print("")
    print("====================================")
    print("✅ ÉPISODE GEMINI PRÊT")
    print("====================================")
    print(f"🎬 Titre : {episode.title}")
    print(f"🎞️ Scènes : 60")
    print(f"⏱️ Durée : 300s")
    print(f"🎵 Musique : {music_count} scènes")
    print(
        f"📍 Lieux : {', '.join(locations)}"
    )
    print(f"🤖 Modèle : {model}")
    print(f"📄 {output_file}")
    print("====================================")


if __name__ == "__main__":
    main()
