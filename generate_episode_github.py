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
Tu es le SHOWRUNNER de la chaîne YouTube jeunesse
« Xale Yi – Wolof Kids ».

Nous voulons une série originale pour enfants, inspirée par le rythme
des grandes chaînes Kids musicales et éducatives : petites scènes,
dialogues rapides, appels-réponses, humour visuel, répétitions,
chansons originales, danse, surprise et beaucoup d'action.

IMPORTANT :
Nous pouvons nous inspirer de la STRUCTURE et du RYTHME de ce type de
contenu, mais nous ne devons copier aucun dialogue, aucune histoire,
aucune chanson ni aucun personnage appartenant à une autre chaîne.

OBJECTIF :
- exactement 60 scènes
- chaque scène = 5 secondes
- durée totale = exactement 300 secondes
- exactement 2 répliques par scène
- répliques courtes et rapides
- 6 à 8 mots environ par réplique
- environ 720 à 960 mots de dialogue sur tout l'épisode

PERSONNAGES FIXES :
- Samba : garçon sénégalais, joyeux, énergique
- Awa : fille sénégalaise, vive, intelligente, drôle
- Ibrahima : garçon sénégalais, lunettes rondes, amusant
- Toto : petit chien marron, très joueur, ne parle jamais

STYLE :
- animation 2D cartoon premium pour enfants
- couleurs vives
- visages très expressifs
- grandes réactions
- beaucoup de mouvements
- ambiance chaleureuse et sénégalaise
- humour simple et positif
- aucun contenu dangereux, violent, sexuel ou effrayant

RYTHME DES DIALOGUES :
1. Les personnages ne doivent presque jamais parler seuls pendant longtemps.
2. Le deuxième personnage doit répondre immédiatement au premier.
3. Utilise parfois des réactions courtes et naturelles :
   « Waaw ! », « Déedéet ! », « Kaay ! », « Hé ! », « Woow ! »,
   « Vite ! », « Attends ! », etc., uniquement quand cela sonne naturel.
4. Évite les explications longues.
5. Écris comme de vrais enfants qui parlent rapidement.
6. Les répliques doivent provoquer une action ou une réaction visuelle.
7. Pas de monologue.
8. Pas de narration dans les dialogues.

CONSTRUCTION DE L'HISTOIRE :
- scènes 1–4 : HOOK immédiat et drôle
- scènes 5–12 : découverte d'un petit problème
- scènes 13–20 : première tentative, humour
- scènes 21–28 : complication amusante
- scènes 29–36 : petite chanson originale + danse ou répétition
- scènes 37–44 : recherche / aventure / fausse piste
- scènes 45–52 : solution collective
- scènes 53–57 : victoire + moment drôle
- scènes 58–60 : conclusion + morale positive

ACTION :
Chaque scène doit comporter une action visuelle clairement identifiable.
Exemples :
- courir
- sauter
- chercher
- ouvrir
- fermer
- montrer
- tirer
- pousser
- danser
- rire
- applaudir
- faire tourner un objet
- jouer
- se cacher
- suivre Toto
- découvrir quelque chose

TOTO :
Toto doit être utile à l'histoire.
Il peut :
- courir
- aboyer
- renifler
- se cacher
- rapporter un objet
- faire une petite bêtise
- surprendre les enfants
- déclencher un moment comique
Il ne parle jamais.

MUSIQUE :
Crée 4 à 6 MOMENTS MUSICAUX ORIGINAUX répartis dans l'épisode.
Ils doivent être courts et faciles à chanter.
Ils peuvent inclure :
- répétition d'un mot
- comptage
- encouragement
- petite danse
- refrain simple
- sons amusants

IMPORTANT :
Les paroles des chansons doivent être ORIGINALES et en Wolof.
Ne copie aucune chanson existante.

SCÈNES MUSICALES :
Pour les scènes musicales, les dialogues peuvent devenir des
phrases chantées très courtes, mais chaque scène doit quand même avoir
exactement 2 répliques.

PROMPTS VISUELS :
- écrits en ANGLAIS
- détaillés
- montrer précisément l'action
- indiquer les émotions
- indiquer le décor
- conserver strictement l'identité des quatre personnages
- même apparence générale d'une scène à l'autre
- aucune écriture dans l'image
- aucun sous-titre
- aucun logo
- aucun watermark

CONTINUITÉ :
Chaque scène doit être une continuation logique de la précédente.
Le problème doit évoluer.
Les personnages doivent savoir ce qui vient de se passer.

QUALITÉ :
Le résultat doit donner l'impression d'un mini dessin animé musical
et non d'une suite de diapositives.

À LA FIN :
La scène 60 doit résoudre l'histoire et donner une morale courte,
positive et compréhensible par un enfant.

FORMAT :
Retourne UNIQUEMENT le JSON conforme au schéma.
Aucun markdown.
EXACTEMENT 60 scènes.
Chaque scène = duration_hint 5.
Chaque scène = exactement 2 dialogues.
Chaque réplique = environ 6 à 8 mots.
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

    french_markers = {
        " je ", " tu ", " il ", " elle ", " on ", " nous ",
        " vous ", " ils ", " le ", " la ", " les ", " un ",
        " une ", " des ", " est ", " sont ", " suis ",
        " avec ", " dans ", " pour ", " mais ", " parce ",
        " maintenant ", " regarde ", " allons ", " très ",
    }

    for scene in episode.scenes:
        for dialogue in scene.dialogue:
            text_lower = f" {dialogue.text.lower().strip()} "
            hits = sum(1 for marker in french_markers if marker in text_lower)

            if hits >= 2:
                raise RuntimeError(
                    f"Dialogue probablement français détecté "
                    f"(scène {scene.scene}): {dialogue.text}"
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
