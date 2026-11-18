"""Publie le prochain Short de la file d'attente (lancé 3 fois par jour)."""
import json, os, sys, subprocess
from run import load, save, QUEUE, PUB, CFG, HERE, youtube_ok

TAGS = ["wolof", "dessin animé wolof", "chanson wolof", "enfants sénégal", "xale yi", "Wolof cartoon for kids", "shorts"]


def main():
    if not youtube_ok():
        return
    q = load(QUEUE, [])
    nxt = next((s for s in q if not s["done"]), None)
    if not nxt:
        print("file de Shorts vide"); return
    e, b = nxt["ep"], f"build/{nxt['ep']}"
    os.makedirs(f"{HERE}/{b}", exist_ok=True)
    subprocess.run(["gh", "release", "download", e, "-p", nxt["file"], "-D", b, "--clobber"], cwd=HERE, check=True)
    from publish import post_short
    desc = nxt["description"]
    vid = load(PUB, {}).get(e, {}).get("video")
    if vid:
        desc += f"\n\nÉpisode complet : https://youtu.be/{vid}"
    sid = post_short(f"{HERE}/{b}/{nxt['file']}", nxt["title"], desc, TAGS)
    print("short publié :", f"https://youtu.be/{sid}")
    nxt["done"], nxt["video"] = True, sid
    save(QUEUE, q)


if __name__ == "__main__":
    main()
