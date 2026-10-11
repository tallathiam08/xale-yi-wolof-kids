import json
import os
from datetime import datetime, timezone

from google import genai
from pydantic import BaseModel, Field
from typing import Literal


TOTAL_SCENES = 60
SCENE_DURATION = 5
TARGET_SECONDS = 300


Speaker = Literal["Samba", "Awa", "Ibrahima"]

Location = Literal[
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

SceneType = Literal[
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

Action = Literal[
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

Emotion = Literal[
    "happy",
    "excited",
    "curious",
    "funny",
    "surprised",
    "calm",
    "sad",
]

Camera = Literal[
    "wide",
    "medium",
    "close",
    "follow",
    "dance",
]


class Dialogue(BaseModel):
    speaker: Speaker
    text: str = Field(min_length=3, max_length=160)


class CharacterAction(BaseModel):
    name: Literal["Samba", "Awa", "Ibrahima", "Toto"]
    action: Action
    emotion: Emotion


class Scene(BaseModel):
    scene: int
    duration_hint: int
    scene_type: SceneType
    location: Location
    camera: Camera
    music: bool
    characters: list[CharacterAction]
    prompt: str = Field(min_length=40)
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

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash",
    )

    seed = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d%H%M%S")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Tu es le SHOWRUNNER de la série originale
« Xale Yi – Wolof Kids ».

SEED DE L'ÉPISODE :
{seed}

OBJECTIF :
Créer un épisode original de 5 minutes pour enfants sénégalais.

L'épisode doit avoir exactement :
- 60 scènes
- 5 secondes par scène
- 300 secondes au total
- exactement 2 dialogues par scène

PERSONNAGES FIXES :
- Samba : garçon sénégalais, joyeux, énergique
- Awa : fille sénégalaise, vive, intelligente, drôle
- Ibrahima : garçon sénégalais avec lunettes rondes, amusant
- Toto : petit chien marron très joueur, il ne parle jamais

IMPORTANT :
Ne force PAS la même structure à chaque épisode.

Tu dois choisir librement un concept parmi :
- aventure
- école
- maison
- bus
- marché
- parc
- plage
- anniversaire
- jeu
- apprentissage
- chasse amusante
- mystère léger
- journée familiale
- histoire comique
- chanson
- danse

Tu peux mélanger plusieurs concepts.

VARIATION :
Chaque épisode doit être différent.
Les lieux doivent varier.
Les actions doivent varier.
Les émotions doivent varier.
Les positions de caméra doivent varier.
Les moments musicaux doivent être placés à différents endroits.

MUSIQUE :
Créer environ 2 à 5 petits moments musicaux par épisode.
Ils ne doivent PAS obligatoirement être consécutifs.
Un moment musical peut durer 1 à 4 scènes.
Certains épisodes peuvent avoir peu de musique.
D'autres peuvent avoir davantage de danse.

ACTIONS POSSIBLES :
idle
talk
walk
run
jump
dance
clap
wave
laugh
surprised
sad

TOTO :
Toto doit être actif dans l'histoire.
Il peut courir, sauter, danser, renifler, jouer,
faire une bêtise, suivre les enfants ou découvrir quelque chose.
Toto ne parle jamais.

DIALOGUES :
TOUS les dialogues doivent être en WOOLOF NATUREL.

Interdiction :
- français
- anglais
- traduction française
- phrases littérales étranges
- narration
- monologue

Les enfants doivent parler comme de vrais enfants sénégalais :
- phrases courtes
- réponses rapides
- appels-réponses
- humour naturel
- réactions spontanées
- vocabulaire simple
- conversation dynamique

Chaque réplique doit provoquer ou accompagner
une action visible.

Environ 6 à 12 mots par réplique.

STYLE VISUEL :
Animation 2D cartoon premium originale pour enfants.
Couleurs vives.
Visages expressifs.
Grande lisibilité.
Ambiance sénégalaise chaleureuse.
Aucune copie de Bebefinn, BabyBus, CoComelon,
Aram Sam Sam ou d'une autre œuvre.

PROMPTS VISUELS :
Les prompts doivent être en anglais.

Chaque prompt doit décrire :
- le lieu
- les personnages présents
- leur action
- leur émotion
- l'ambiance
- l'action principale
- éventuellement un accessoire
- la caméra

Aucune écriture dans l'image.
Aucun logo.
Aucun sous-titre.
Aucun watermark.

CONTINUITÉ :
Chaque scène doit continuer naturellement la précédente.
Les personnages doivent se souvenir de ce qui vient de se passer.
L'histoire doit progresser.

RÈGLE IMPORTANTE :
Ne mets pas la musique toujours au milieu de l'épisode.
Les scènes musicales doivent être naturellement intégrées à l'histoire.

EXEMPLES DE RYTHME :

SCÈNE :
Samba court → Awa réagit → Toto saute.

OU :

Ibrahima découvre quelque chose →
les autres arrivent →
petite chanson →
danse →
retour à l'histoire.

OU :

bus →
erreur amusante →
recherche →
fausse piste →
chanson courte →
solution.

La scène 60 doit terminer l'histoire
avec une conclusion positive pour les enfants.

RÉPONDS UNIQUEMENT AVEC LE JSON CONFORME AU SCHÉMA.
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
        raise RuntimeError(
            "Gemini n'a pas retourné un JSON valide"
        )

    episode = response.parsed

    if len(episode.scenes) != TOTAL_SCENES:
        raise RuntimeError(
            f"Nombre de scènes incorrect : "
            f"{len(episode.scenes)}"
        )

    numbers = [
        scene.scene
        for scene in episode.scenes
    ]

    expected = list(
        range(1, TOTAL_SCENES + 1)
    )

    if numbers != expected:
        raise RuntimeError(
            "Numérotation des scènes incorrecte"
        )

    for scene in episode.scenes:
        if scene.duration_hint != SCENE_DURATION:
            raise RuntimeError(
                f"Scène {scene.scene}: durée incorrecte"
            )

        if len(scene.dialogue) != 2:
            raise RuntimeError(
                f"Scène {scene.scene}: "
                f"2 dialogues attendus"
            )

        if not 2 <= len(scene.characters) <= 4:
            raise RuntimeError(
                f"Scène {scene.scene}: "
                f"2 à 4 personnages attendus"
            )

        for line in scene.dialogue:
            count = len(line.text.split())

            if not 5 <= count <= 14:
                raise RuntimeError(
                    f"Scène {scene.scene}: "
                    f"réplique de {count} mots"
                )

    total_seconds = sum(
        scene.duration_hint
        for scene in episode.scenes
    )

    if total_seconds != TARGET_SECONDS:
        raise RuntimeError(
            f"Durée incorrecte : {total_seconds}s"
        )

    # Vérification légère du français
    french_markers = {
        " je ",
        " tu ",
        " il ",
        " elle ",
        " nous ",
        " vous ",
        " ils ",
        " avec ",
        " dans ",
        " pour ",
        " mais ",
        " parce ",
        " très ",
        " maintenant ",
        " regarde ",
    }

    for scene in episode.scenes:
        for dialogue in scene.dialogue:
            text = (
                f" {dialogue.text.lower().strip()} "
            )

            hits = sum(
                1
                for marker in french_markers
                if marker in text
            )

            if hits >= 2:
                raise RuntimeError(
                    "Dialogue probablement français "
                    f"détecté scène {scene.scene}: "
                    f"{dialogue.text}"
                )

    episode.target_duration = "5min"

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

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

    music_scenes = sum(
        1 for scene in episode.scenes
        if scene.music
    )

    locations = sorted({
        scene.location
        for scene in episode.scenes
    })

    print("✅ Épisode Xale Yi généré")
    print(f"🎬 Titre : {episode.title}")
    print(f"🎞️ Scènes : {len(episode.scenes)}/60")
    print(f"⏱️ Durée : {total_seconds}s")
    print(f"🎵 Scènes musicales : {music_scenes}")
    print(f"📍 Lieux utilisés : {', '.join(locations)}")
    print(f"🤖 Modèle : {model}")
    print(f"📄 Fichier : {output_file}")


if __name__ == "__main__":
    main()
