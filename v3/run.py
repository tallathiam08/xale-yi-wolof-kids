"""Production d'un épisode : écrit (si besoin), génère l'audio, monte, range dans une « Release » GitHub,
met ses Shorts en file d'attente, et publie l'épisode sur YouTube si la publication est activée (config.json).
Usage : python run.py [epNN]
"""
import json, os, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(HERE + "/config.json"))
PUB = HERE + "/state/published.json"
BUILT = HERE + "/state/built.json"
QUEUE = HERE + "/state/shorts_queue.json"


def load(p, d):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d


def save(p, x):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(x, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def sh(*a, **kw):
    print("$", " ".join(a), flush=True)
    subprocess.run(list(a), check=True, cwd=kw.get("cwd", HERE))


def youtube_ok():
    if not (CFG.get("publish_youtube") and os.environ.get("YT_REFRESH_TOKEN")):
        print("ℹ️ Publication YouTube désactivée (config.json) : on prépare seulement.", flush=True)
        return False
    r = subprocess.run([sys.executable, "publish.py", "--check"], cwd=HERE)
    if r.returncode:
        print("⚠️ Accès YouTube refusé : on prépare seulement.", flush=True)
    return r.returncode == 0


def build(ep_id):
    ep_path, b = f"episodes/{ep_id}.json", f"build/{ep_id}"
    sh(sys.executable, "make_audio.py", ep_path, b)
    os.environ["SHORTS_PER_EPISODE"] = str(CFG.get("shorts_per_episode", 6))
    sh(sys.executable, "render.py", ep_path, b)
    ep = json.load(open(HERE + "/" + ep_path, encoding="utf-8"))
    shorts = json.load(open(f"{HERE}/{b}/shorts.json", encoding="utf-8"))
    files = [f"{b}/episode.mp4", f"{b}/thumbnail.jpg", f"{b}/shorts.json"] + [f"{b}/{s['file']}" for s in shorts]
    if os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "release", "delete", ep_id, "-y", "--cleanup-tag"], cwd=HERE)
        sh("gh", "release", "create", ep_id, *files, "--title", f"Épisode {ep['number']} – {ep['title']}",
           "--notes", "Vidéo, miniature et Shorts fabriqués automatiquement.")
    built = load(BUILT, {}); built[ep_id] = {"release": ep_id, "shorts": len(shorts)}; save(BUILT, built)
    q = load(QUEUE, [])
    q += [dict(ep=ep_id, file=s["file"], title=s["title"], description=s["description"], done=False) for s in shorts]
    save(QUEUE, q)
    return b


def fetch(ep_id, b, *names):
    os.makedirs(f"{HERE}/{b}", exist_ok=True)
    for n in names:
        if not os.path.exists(f"{HERE}/{b}/{n}"):
            sh("gh", "release", "download", ep_id, "-p", n, "-D", b, "--clobber")


def main():
    pub, built = load(PUB, {}), load(BUILT, {})
    eps = sorted(os.path.basename(p)[:-5] for p in glob.glob(HERE + "/episodes/ep*.json"))
    yt = youtube_ok()
    forced = sys.argv[1] if len(sys.argv) > 1 else None
    # 1) fabriquer le prochain épisode si la réserve n'est pas pleine
    waiting = [e for e in built if e not in pub]
    if forced or len(waiting) < CFG.get("max_built_waiting", 4):
        todo = forced or next((e for e in eps if e not in built and e not in pub), None)
        if not todo:
            num = max([int(e[2:]) for e in list(pub) + list(built) + eps] + [1]) + 1
            sh(sys.executable, "write_episode.py", str(num))
            todo = f"ep{num:02d}"
        print("🎬 fabrication :", todo, flush=True)
        build(todo)
        open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a").write(f"episode={todo}\n")
    else:
        print("ℹ️ Réserve pleine :", waiting, flush=True)
    # 2) publier le plus ancien épisode prêt
    built = load(BUILT, {})
    ready = sorted(e for e in built if e not in pub)
    if yt and ready and os.environ.get("PUBLISH", "1") == "1":
        e = ready[0]; b = f"build/{e}"
        fetch(e, b, "episode.mp4", "thumbnail.jpg", "short_01.mp4", "shorts.json")
        sh(sys.executable, "publish.py", f"episodes/{e}.json", b)
        pub[e] = load(f"{HERE}/{b}/published.json", {}); save(PUB, pub)
        # le premier Short de l'épisode est publié avec lui
        q = load(QUEUE, [])
        for s in q:
            if s["ep"] == e and s["file"] == "short_01.mp4":
                s["done"] = True
        save(QUEUE, q)


if __name__ == "__main__":
    main()
