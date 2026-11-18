"""Génère les voix (ElevenLabs TTS), la chanson (ElevenLabs Music) et les bruitages d'un épisode.
Usage : python make_audio.py episodes/ep02.json build/ep02
Chaque fichier déjà présent est réutilisé (relance sans repayer).
"""
import json, os, sys, subprocess, time, hashlib
import requests
from series import VOICES

API = "https://api.elevenlabs.io/v1"
KEY = os.environ["ELEVENLABS_API_KEY"]
H = {"xi-api-key": KEY}


def wav(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "44100", "-ac", "1", dst], check=True)


def post(url, payload, out, tries=4):
    for k in range(tries):
        r = requests.post(url, headers={**H, "Content-Type": "application/json"}, json=payload, timeout=600)
        if r.status_code == 200:
            open(out, "wb").write(r.content)
            return
        print("ElevenLabs", r.status_code, r.text[:300])
        time.sleep(5 * (k + 1))
    raise SystemExit(f"échec ElevenLabs pour {out}")


def voice_ids():
    r = requests.get(API + "/voices", headers=H, params={"page_size": 100}, timeout=60)
    r.raise_for_status()
    voices = r.json()["voices"]
    ids = {}
    for who, name in VOICES.items():
        m = [v for v in voices if v["name"].lower().startswith(name.lower())]
        if not m:
            raise SystemExit(f"voix introuvable dans « Mes voix » : {name} ({who})")
        ids[who] = m[0]["voice_id"]
    return ids


def pick_model(test_voice):
    want = os.environ.get("ELEVEN_MODEL")
    if want:
        return want
    # la clé n'a pas forcément le droit de lister les modèles : on essaie directement
    for m in ("eleven_v4", "eleven_v3", "eleven_multilingual_v2"):
        r = requests.post(f"{API}/text-to-speech/{test_voice}?output_format=mp3_44100_128",
                          headers={**H, "Content-Type": "application/json"},
                          json={"text": "Waaw.", "model_id": m}, timeout=120)
        if r.status_code == 200:
            return m
        print("modèle", m, "refusé :", r.status_code, r.text[:200])
    raise SystemExit("aucun modèle ElevenLabs utilisable (vérifie les droits de la clé : Text to Speech)")


def main(ep_path, out):
    ep = json.load(open(ep_path, encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    ids = voice_ids()
    model = pick_model(ids["Awa"])
    print("modèle TTS :", model)
    open(out + "/model.txt", "w").write(model)
    n = 0
    for si, sc in enumerate(ep["scenes"]):
        for ev in sc["events"]:
            if ev[0] == "line":
                spk, wo = ev[1], ev[2]
                opts = ev[4] if len(ev) > 4 else {}
                text = opts.get("tts", wo)
                voice = opts.get("voice", spk)
                key = hashlib.md5(f"{voice}|{text}|{model}".encode()).hexdigest()[:10]
                dst = f"{out}/line_{key}.wav"
                if not os.path.exists(dst):
                    post(f"{API}/text-to-speech/{ids[voice]}?output_format=mp3_44100_128",
                         {"text": text, "model_id": model,
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}, dst + ".mp3")
                    wav(dst + ".mp3", dst); os.remove(dst + ".mp3"); n += 1
            elif ev[0] == "sfx":
                key = hashlib.md5(ev[1].encode()).hexdigest()[:10]
                dst = f"{out}/sfx_{key}.wav"
                if not os.path.exists(dst):
                    post(f"{API}/sound-generation", {"text": ev[1], "duration_seconds": ev[3] if len(ev) > 3 else 2.0},
                         dst + ".mp3")
                    wav(dst + ".mp3", dst); os.remove(dst + ".mp3")
    song = ep.get("song")
    if song and not os.path.exists(f"{out}/song.wav"):
        lyr = "\n".join(song["lyrics"])
        prompt = (song.get("style") or "Joyful children's nursery song for a kids cartoon, sung in Wolof (Senegal) "
                  "by a cheerful little girl with a small kids choir on the chorus, Senegalese mbalax-pop feel with "
                  "djembe, sabar, light guitar and claps, bright and simple, easy to sing along") + \
            f", about {song.get('seconds', 60)} seconds. Lyrics:\n" + lyr
        post(f"{API}/music", {"prompt": prompt, "music_length_ms": int(song.get("seconds", 60) * 1000)},
             f"{out}/song.mp3")
        wav(f"{out}/song.mp3", f"{out}/song.wav")
    print(f"voix générées : {n}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
