import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY introuvable dans .env")

client = genai.Client(api_key=API_KEY)

SCRIPT_DIR = Path("scripts")
SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

theme = input("\n🎬 Thème de l'épisode : ").strip()

if not theme:
    raise RuntimeError("❌ Aucun thème fourni.")

prompt = f"""
Tu es scénariste professionnel d'une série d'animation pour enfants.

Tu dois écrire un épisode ORIGINAL en WOLOF.

PERSONNAGES RÉCURRENTS :
- Samba : garçon énergique, curieux et drôle.
- Ibrahima : garçon calme, intelligent et réfléchi.
- Awa : fille intelligente, chaleureuse et dynamique.
- Toto : petit chien joueur et expressif.

THÈME DE L'ÉPISODE :
{theme}

RÈGLES ABSOLUES :

1. L'épisode doit contenir EXACTEMENT 8 scènes.
2. Chaque scène doit avoir une vraie action visuelle.
3. Chaque scène doit contenir au moins 2 interventions parlées.
4. Les scènes doivent avoir des dialogues assez longs pour environ 6 à 10 secondes
   de parole naturelle minimum.
5. Le texte parlé doit être UNIQUEMENT EN WOLOF.
6. Ne mets AUCUN français dans les dialogues.
7. Ne mets AUCUN anglais dans les dialogues.
8. Utilise un Wolof naturel, simple et compréhensible par des enfants.
9. Évite les traductions littérales étranges.
10. Ne mets pas de commentaires en français dans les dialogues.
11. Les indications d'action peuvent être courtes et en français.
12. Toto ne parle pas avec des phrases humaines.
    Toto peut seulement faire : Waf! Waf!, Grrrr!, ou des actions.
13. Chaque scène doit faire avancer l'histoire.
14. Les scènes doivent être dynamiques et adaptées à une animation.
15. Maintiens exactement les mêmes personnages et leurs personnalités.
16. Pas de violence graphique, pas de contenu adulte.
17. L'histoire doit avoir un début, un problème, une recherche ou aventure,
    puis une résolution positive.
18. Pas de répétitions inutiles.
19. Chaque personnage doit parler comme un personnage différent.
20. Fais des dialogues assez longs, mais naturels.

FORMAT OBLIGATOIRE :

SCÈNE 1:
[Description courte de l'action]

Samba:
[Dialogue Wolof]

Awa:
[Dialogue Wolof]

Ibrahima:
[Dialogue Wolof]

Toto:
Waf! Waf!

SCÈNE 2:
[Description courte de l'action]

Samba:
[Dialogue Wolof]

Ibrahima:
[Dialogue Wolof]

Awa:
[Dialogue Wolof]

SCÈNE 3:
...

Continue exactement jusqu'à :

SCÈNE 8:

IMPORTANT :
- Écris exactement "SCÈNE 1:" jusqu'à "SCÈNE 8:"
- Chaque personnage doit être suivi de ":" sur une ligne séparée.
- Aucun markdown autour des titres.
- N'utilise pas "**".
- Aucun dialogue vide.
- Ne mets jamais "Samba :" avec le texte sur la même ligne.
- Ne mets jamais d'indication comme "(en français)" dans une réplique.
"""

models = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]

response = None
last_error = None

for model in models:
    try:
        print(f"\n🤖 Génération avec {model}...")
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        if response and response.text:
            break
    except Exception as e:
        last_error = e
        print(f"⚠️ {model} indisponible.")
        print(e)

if response is None or not response.text:
    raise RuntimeError(
        f"❌ Gemini n'a pas généré le scénario.\n{last_error}"
    )

script = response.text.strip()

# Nettoyage Markdown éventuel
script = script.replace("**", "")
script = script.replace("__", "")

# Vérification des 8 scènes
for number in range(1, 9):
    if f"SCÈNE {number}:" not in script:
        raise RuntimeError(
            f"❌ Le scénario ne contient pas correctement SCÈNE {number}:"
        )

# Vérifie les scènes supplémentaires
if "SCÈNE 9:" in script:
    raise RuntimeError("❌ Gemini a généré plus de 8 scènes.")

# Vérifie qu'il n'y a pas de titres anglais
if "SCENE " in script:
    raise RuntimeError("❌ Format anglais détecté.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = SCRIPT_DIR / f"episode_{timestamp}.txt"

output_file.write_text(script, encoding="utf-8")

print("\n========================================")
print("🎉 ÉPISODE GÉNÉRÉ")
print("========================================")
print(f"📄 Fichier sauvegardé : {output_file}")
print("\n✅ 8 scènes demandées")
print("✅ Dialogues Wolof")
print("✅ Format compatible avec le générateur audio")
print("✅ Dialogues volontairement plus longs")
