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
    """Gemini est parfois surchargé (503) : on alterne les modèles pendant ~30 minutes avant d'abandonner."""
    key = os.environ["GEMINI_API_KEY"]
    deadline = time.time() + int(os.environ.get("GEMINI_PATIENCE", "1800"))
    k = 0
    while time.time() < deadline:
        model = MODELS[k % len(MODELS)]
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                              json={"contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8}},
                              timeout=240)
            if r.status_code == 200:
                try:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    print(model, "réponse vide")
            else:
                print(model, r.status_code, r.text[:120].replace("\n", " "))
        except requests.RequestException as e:
            print(model, "erreur réseau :", repr(e)[:150])
        k += 1
        if k % len(MODELS) == 0:  # tous les modèles ont échoué : on attend un peu plus à chaque tour
            time.sleep(min(60 * (k // len(MODELS)), 240))
        else:
            time.sleep(5)
    raise SystemExit("Gemini indisponible pour le moment (surcharge) – nouvel essai au prochain passage")


ACTS = ("hop", "shake", "dance", "walk", "move", "hide", "show", "pop", "flip")
GROUP = ("Élèves", "Un élève", "Narratrice")


def repair(ep):
    """Corrige automatiquement les petites erreurs de Gemini au lieu de rejeter tout l'épisode."""
    ep["scenes"] = [sc for sc in ep.get("scenes", []) if sc.get("events")][:4]
    for sc in ep["scenes"]:
        if sc.get("bg") not in BGS:
            sc["bg"] = "maison"
        cast = [c for c in sc.get("cast", []) if (c if isinstance(c, str) else c.get("name")) in CHARS]
        speakers = []
        for ev in sc["events"]:
            if ev and ev[0] == "line" and ev[1] in CHARS and ev[1] not in speakers:
                speakers.append(ev[1])
        names = [c if isinstance(c, str) else c["name"] for c in cast]
        for sp in speakers:  # un personnage qui parle doit être dans la scène
            if sp not in names:
                cast.append(sp); names.append(sp)
        while len(cast) > 5:  # on retire d'abord ceux qui ne parlent pas
            idx = next((i for i, nm in enumerate(names) if nm not in speakers), len(cast) - 1)
            cast.pop(idx); names.pop(idx)
        sc["cast"] = cast
        evs = []
        for ev in sc["events"]:
            if not ev:
                continue
            if ev[0] == "line":
                if len(ev) < 4 or not isinstance(ev[2], str) or not isinstance(ev[3], str):
                    continue
                if ev[1] not in names and ev[1] not in GROUP:
                    continue
            elif ev[0] == "act":
                if len(ev) < 3 or ev[1] not in names or ev[2] not in ACTS:
                    continue
            elif ev[0] not in ("wait", "song", "sfx"):
                continue
            evs.append(ev)
        sc["events"] = evs
    songs = [(i, j) for i, sc in enumerate(ep["scenes"]) for j, ev in enumerate(sc["events"]) if ev[0] == "song"]
    for i, j in reversed(songs[1:]):
        ep["scenes"][i]["events"].pop(j)
    if not songs and ep["scenes"]:
        mid = ep["scenes"][len(ep["scenes"]) // 2]["events"]
        mid.insert(len(mid) // 2, ["song"])
    y = ep.setdefault("youtube", {})
    y.setdefault("title", f"{ep.get('title', 'Xale Yi')} | Dessin animé en wolof pour enfants | Épisode {ep.get('number', '')}")
    y.setdefault("description", ep.get("title", ""))
    y.setdefault("tags", ["wolof", "dessin animé wolof", "xale yi"])
    th = ep.setdefault("thumbnail", {})
    th.setdefault("text", ep.get("title", "XALE YI").upper().split()[:3] and [" ".join(ep.get("title", "XALE YI").upper().split()[:2]), f"ÉP. {ep.get('number', '')}"])
    sh = ep.get("short")
    if sh and ep["scenes"]:
        sh["scene"] = min(max(int(sh.get("scene", 0)), 0), len(ep["scenes"]) - 1)
        nl = sum(e[0] == "line" for e in ep["scenes"][sh["scene"]]["events"])
        if nl == 0:
            ep.pop("short")
        else:
            sh["from"] = min(max(int(sh.get("from", 0)), 0), nl - 1)
            sh["to"] = min(max(int(sh.get("to", nl - 1)), sh["from"]), nl - 1)
            sh.setdefault("text", th["text"])
    return ep


def validate(ep):
    assert ep["scenes"] and len(ep["scenes"]) <= 4, "nombre de scènes"
    n = 0
    for sc in ep["scenes"]:
        assert sc["bg"] in BGS, sc["bg"]
        names = [c if isinstance(c, str) else c["name"] for c in sc["cast"]]
        assert all(x in CHARS for x in names), names
        assert len(names) <= 5, "trop de personnages"
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
    assert sum(ev[0] == "song" for sc in ep["scenes"] for ev in sc["events"]) == 1, "une seule chanson"
    assert ep["song"]["lyrics"] and ep["youtube"]["title"] and ep["thumbnail"]["text"], "chanson / titre / miniature"
    sh = ep.get("short")
    if not sh:
        return
    lines = [e for e in ep["scenes"][sh["scene"]]["events"] if e[0] == "line"]
    assert 0 <= sh["from"] <= sh["to"] < len(lines), "moment du Short"


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
    err = ""
    for k in range(6):
        txt = ask(prompt + (f"\n\nATTENTION, ta réponse précédente était invalide ({err}). Corrige ce point. Rappel : 30 à 40 répliques au total (événements « line »), 3 scènes, une seule chanson." if err else ""))
        txt = re.sub(r"^```(json)?|```$", "", txt.strip()).strip()
        try:
            ep = json.loads(txt)
            ep["number"], ep["id"] = num, f"ep{num:02d}"
            repair(ep)
            validate(ep)
            out = f"{HERE}/episodes/ep{num:02d}.json"
            json.dump(ep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("écrit :", out, "-", ep["title"])
            return out
        except Exception as e:
            err = repr(e)[:200]
            print("épisode invalide, nouvel essai :", err)
    raise SystemExit("impossible d'écrire un épisode valide")


if __name__ == "__main__":
    main(int(sys.argv[1]))
