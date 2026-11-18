"""Chaîne complète : choisit le prochain épisode, l'écrit si besoin, génère l'audio, monte, publie.
Usage : python run.py [epNN]   (sans argument : prochain épisode non publié)
Variables : PUBLISH=0 pour fabriquer sans publier.
"""
import json, os, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = HERE + "/state/published.json"


def sh(*a):
    print("$", " ".join(a), flush=True)
    subprocess.run(list(a), check=True, cwd=HERE)


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if len(sys.argv) > 1:
        ep_id = sys.argv[1]
    else:
        ready = sorted(os.path.basename(p)[:-5] for p in glob.glob(HERE + "/episodes/ep*.json"))
        todo = [e for e in ready if e not in state]
        if todo:
            ep_id = todo[0]
        else:
            num = max([int(e[2:]) for e in list(state) + ready] + [1]) + 1
            sh(sys.executable, "write_episode.py", str(num))
            ep_id = f"ep{num:02d}"
    ep_path = f"episodes/{ep_id}.json"
    b = f"build/{ep_id}"
    print("🎬 épisode :", ep_id, flush=True)
    if os.environ.get("YT_REFRESH_TOKEN"):
        r = subprocess.run([sys.executable, "publish.py", "--check"], cwd=HERE)
        if r.returncode != 0:
            print("⚠️ Accès YouTube refusé : la vidéo sera fabriquée mais pas publiée.", flush=True)
            os.environ["PUBLISH"] = "0"
    sh(sys.executable, "make_audio.py", ep_path, b)
    sh(sys.executable, "render.py", ep_path, b)
    if os.environ.get("PUBLISH", "1") == "1":
        sh(sys.executable, "publish.py", ep_path, b)
        pub = f"{HERE}/{b}/published.json"
        if os.path.exists(pub):
            state[ep_id] = json.load(open(pub))
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(state, open(STATE, "w"), indent=1)
    open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a").write(f"episode={ep_id}\n")


if __name__ == "__main__":
    main()
