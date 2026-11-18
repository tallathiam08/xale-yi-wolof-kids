"""Écrit le prochain épisode (JSON) avec Gemini quand la file d'épisodes prêts est vide.
Usage : python write_episode.py <numéro>  → crée episodes/epNN.json
"""
import json, os, sys, glob, time, re
import requests
from series import CHARS, VOICES, BGS

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = [m for m in os.environ.get("GEMINI_MODELS", "gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite").split(",") if m]

RULES = """Tu écris des épisodes d'un dessin animé pour enfants (3-7 ans) en WOLOF de Dakar, la chaîne « Xale Yi – Wolof Kids ».
Style du wolof (TRÈS IMPORTANT) : wolof de tous les jours à Dakar, mélangé avec des mots français comme on parle vraiment
(ékool, sac, cahier, maîtresse, récréation, chanson, l'année prochaine, pardon, coucou, à ce soir). Écriture phonétique
simple (ékool, nék, ngui, rétane). Phrases COURTES et faciles. Dans une question, on dit l'âge avec « at » (ñaata at nga am ?) ;
seul l'enfant qui répond peut dire « 3 ans ». Chaque réplique a sa traduction française naturelle.
Histoires drôles de la vie réelle, gags visuels, une chanson originale courte et répétitive (refrain facile).
Pas de leçon de comptage, pas de vocabulaire « papa / maman ». Fin avec un petit suspense annoncé par la narratrice.
Environ 30 à 40 répliques, réparties en 3 scènes. La chanson est jouée une fois au milieu (événement ["song"]).

RÈGLES POUR FAIRE GRANDIR LA CHAÎNE (titres, description, miniature, Short) :
- Les 20 premières secondes doivent accrocher : un gag ou une surprise dès la 1re réplique, pas de longue présentation.
- « youtube.title » (60 à 80 caractères) : commence par l'action drôle ou surprenante + 1 emoji, puis une phrase courte en wolof,
  puis « | Dessin animé en wolof pour enfants | Épisode N ». Exemple : « Un mouton dans la maison ! 🐑 Xar bi dafa dugg ! | Dessin animé en wolof pour enfants | Épisode 3 ».
- « youtube.description » : 2 premières lignes = l'accroche (français puis wolof) avec une question qui donne envie de regarder ;
  puis la chanson, les personnages, « Sous-titres en wolof et en français. », et 5 hashtags (#wolof #dessinanimé #enfants #senegal #chansonenfant).
- « youtube.tags » : 15 à 20 tags, mélange français / wolof / anglais (wolof, dessin animé wolof, chanson wolof, Awa et Modou, xale yi,
  Wolof cartoon for kids, Senegal cartoon, apprendre le wolof, + 4 à 6 mots du thème de l'épisode).
- « thumbnail.text » : 2 lignes très courtes (2 à 3 mots chacune) qui montrent l'émotion ou la surprise, en wolof.
- « short » : choisis le moment le plus drôle (8 à 12 répliques). « short.text » = 2 lignes courtes qui résument ce moment.
  « short_youtube.title » doit décrire EXACTEMENT ce moment (le même que « short.text »), avec emoji, + « #wolof #shorts »."""


def schema_example():
    return open(HERE + "/episodes/ep02.json", encoding="utf-8").read()


def ask(prompt):
    key = os.environ["GEMINI_API_KEY"]
    for model in MODELS:
        for k in range(3):
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                              json={"contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}},
                              timeout=300)
            if r.status_code == 200:
                try:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    pass
            print(model, r.status_code, r.text[:200])
            time.sleep(10 * (k + 1))
    raise SystemExit("Gemini indisponible")


def validate(ep):
    assert ep["scenes"] and len(ep["scenes"]) <= 4
    n = 0
    for sc in ep["scenes"]:
        assert sc["bg"] in BGS, sc["bg"]
        names = [c if isinstance(c, str) else c["name"] for c in sc["cast"]]
        assert all(x in CHARS for x in names), names
        assert len(names) <= 5
        for ev in sc["events"]:
            if ev[0] == "line":
                n += 1
                assert ev[1] in VOICES, ev[1]
                assert ev[1] in names or ev[1] in ("Élèves", "Un élève", "Narratrice"), (ev[1], names)
                assert isinstance(ev[2], str) and isinstance(ev[3], str)
            elif ev[0] == "act":
                assert ev[1] in names and ev[2] in ("hop", "shake", "dance", "walk", "move", "hide", "show", "pop", "flip"), ev
            elif ev[0] not in ("wait", "song", "sfx"):
                raise AssertionError(ev)
    assert 18 <= n <= 50, n
    assert sum(ev[0] == "song" for sc in ep["scenes"] for ev in sc["events"]) == 1
    assert ep["song"]["lyrics"] and ep["youtube"]["title"] and ep["thumbnail"]["text"]
    sh = ep["short"]
    lines = [e for e in ep["scenes"][sh["scene"]]["events"] if e[0] == "line"]
    assert 0 <= sh["from"] <= sh["to"] < len(lines)


def main(num):
    eps = sorted(glob.glob(HERE + "/episodes/ep*.json"))
    prev = [json.load(open(p, encoding="utf-8")) for p in eps]
    recap = "\n".join(f"- Épisode {e['number']} « {e['title']} » : " +
                      " / ".join(ev[3] for sc in e["scenes"] for ev in sc["events"] if ev[0] == "line")[-600:] for e in prev[-2:])
    prompt = f"""{RULES}

Plan de la saison :
{open(HERE + '/season.md', encoding='utf-8').read()}

Fin des épisodes précédents (pour la continuité) :
{recap}

Personnages disponibles (noms EXACTS) : {', '.join(CHARS)}. Voix de groupe : « Élèves », « Un élève ». Narratrice : « Narratrice ».
Décors disponibles (EXACTS) : maison, rue, classe. Maximum 5 personnages par scène.
Actions possibles : ["act", nom, "hop"|"shake"|"dance"|"walk"|"move"|"hide"|"show"|"pop", durée, {{paramètres}}].
Bruitage : ["sfx", "description en anglais du son", "texte affiché", secondes].
Balises d'émotion possibles dans "tts" : [laughs], [giggles], [whispers], [surprised], [sneezes], [yawns], [snoring], [proudly].

Écris l'épisode {num} (« number »: {num}, « id »: "ep{num:02d}") en JSON, EXACTEMENT au même format que cet exemple :
{schema_example()}
Réponds uniquement avec le JSON."""
    for k in range(3):
        txt = ask(prompt)
        txt = re.sub(r"^```(json)?|```$", "", txt.strip()).strip()
        try:
            ep = json.loads(txt)
            ep["number"], ep["id"] = num, f"ep{num:02d}"
            validate(ep)
            out = f"{HERE}/episodes/ep{num:02d}.json"
            json.dump(ep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("écrit :", out, "-", ep["title"])
            return out
        except Exception as e:
            print("épisode invalide, nouvel essai :", repr(e)[:300])
    raise SystemExit("impossible d'écrire un épisode valide")


if __name__ == "__main__":
    main(int(sys.argv[1]))
