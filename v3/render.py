"""Monte un épisode complet à partir de son fichier JSON et des audios de make_audio.py.
Usage : python render.py episodes/ep02.json build/ep02
Sorties dans build/ep02 : episode.mp4, short.mp4, thumbnail.jpg, timings.json
"""
import json, os, sys, math, hashlib, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import engine as E
from engine import Scene, Sprite, FPS, OW, OH
from series import CHARS, COLORS, BGS, HEIGHT

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = HERE + "/assets/"


class Ep:
    pass


EPO = Ep()
EPO.colors = COLORS
EPO.sprites = {k: Sprite(ASSETS + "chars/" + v[0], v[1], v[2]) for k, v in CHARS.items()}

fL = ImageFont.truetype(E.FB, 52)
_LC = {}


def lyric_img(text):
    if text not in _LC:
        tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        w = int(tmp.textlength(text, font=fL)) + 120
        img = Image.new("RGBA", (w, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, w, 96], 46, fill=(255, 220, 60, 235), outline=(230, 70, 140), width=5)
        d.text((60, 18), text, font=fL, fill=(70, 30, 40))
        _LC[text] = E.rgba_np(img)
    return _LC[text]


def song_overlay(fr, t, S):
    lyr = S["lyr"]
    i = min(len(lyr) - 1, int(t / (S["e"] - S["s"]) * len(lyr)))
    img = lyric_img("♪ " + lyr[i] + " ♪")
    E.blend(fr, img, (OW - img.shape[1]) // 2, OH - 150 - int(abs(math.sin(t * math.pi * 1.8)) * 10), 1.0)


EPO.song_overlay = song_overlay


def layout(bg, cast):
    B = BGS[bg]
    names = [c if isinstance(c, str) else c["name"] for c in cast]
    n = len(names)
    out = {}
    for i, c in enumerate(cast):
        c = {"name": c} if isinstance(c, str) else dict(c)
        cls = CHARS[c["name"]][3]
        x = c.get("x", B["x0"] + (B["x1"] - B["x0"]) * (i + 0.5) / n)
        y = B["floor"] + {"baby": 30, "teacher": 150 if bg == "classe" else 0}.get(cls, 0)
        out[c["name"]] = dict(x=x, y=c.get("y", y), h=HEIGHT[cls] * B["scale"], visible=c.get("visible", True),
                              flip=c.get("flip", False))
    return out


def build_scene(ep, si, sc, build, audio_map):
    bg = sc["bg"]
    cast = layout(bg, sc["cast"])
    evs = []
    for ev in sc["events"]:
        k = ev[0]
        if k == "line":
            spk, wo, fr = ev[1], ev[2], ev[3]
            opts = dict(ev[4]) if len(ev) > 4 else {}
            if spk == "Narratrice":
                opts.setdefault("cam", "wide"); opts.setdefault("who", "-"); opts.setdefault("label", "Mame (narratrice)")
            if spk in ("Élèves", "Un élève") and "cam" not in opts:
                opts["cam"] = "wide"
            evs.append(("line", audio_map[id(ev)], spk, wo, fr, opts))
        elif k == "sfx":
            evs.append(("line", audio_map[id(ev)], "", ev[2] if len(ev) > 2 else "", "",
                        {"cam": "wide", "who": "-", "label": ""}))
        elif k == "song":
            evs.append(("song", build + "/song.wav", ep["song"]["lyrics"]))
        else:
            evs.append(tuple(ev))
    s = Scene(EPO, ASSETS + "bg/" + BGS[bg]["file"], None, cast, evs)
    return s


def map_audio(ep, build, model_hint=None):
    """associe chaque réplique à son wav (fichiers line_<md5>.wav créés par make_audio)."""
    import glob
    files = {os.path.basename(f) for f in glob.glob(build + "/*.wav")}
    model = open(build + "/model.txt").read().strip() if os.path.exists(build + "/model.txt") else None
    amap = {}
    for sc in ep["scenes"]:
        for ev in sc["events"]:
            if ev[0] == "line":
                opts = ev[4] if len(ev) > 4 else {}
                text = opts.get("tts", ev[2]); voice = opts.get("voice", ev[1])
                key = hashlib.md5(f"{voice}|{text}|{model}".encode()).hexdigest()[:10]
                amap[id(ev)] = f"{build}/line_{key}.wav"
            elif ev[0] == "sfx":
                amap[id(ev)] = f"{build}/sfx_{hashlib.md5(ev[1].encode()).hexdigest()[:10]}.wav"
    missing = [v for v in amap.values() if not os.path.exists(v)]
    if missing:
        raise SystemExit(f"audios manquants : {missing[:3]}")
    return amap


def write_wav(path, arr, sr=44100):
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(arr, -1, 1) * 32767).astype(np.int16).tobytes())


def render_scene(sc, out):
    n = int(sc.dur * FPS)
    rc = E.encode((sc.frame(i / FPS) for i in range(n)), out + ".tmp.mp4", n)
    if rc != 0:
        raise SystemExit("ffmpeg a échoué : " + out)
    os.replace(out + ".tmp.mp4", out)
    sr = 44100
    total = np.zeros(int(n / FPS * sr) + sr, np.float32)
    for t, w in sc.audio:
        a, r = E.read_wav(w)
        i = int(t * sr)
        total[i:i + len(a)] += a[:max(0, len(total) - i)]
    write_wav(out.replace(".mp4", ".wav"), total[:int(n / FPS * sr)])
    return n / FPS


def intro_scene(ep, build):
    sr = 44100
    a, _ = E.read_wav(build + "/song.wav")
    seg = a[:6 * sr].copy()
    seg[-int(1.5 * sr):] *= np.linspace(1, 0, int(1.5 * sr))
    write_wav(build + "/intro.wav", seg)
    cast = layout("maison", ["Awa", "Modou", "Papa"])
    s = Scene(EPO, ASSETS + "bg/room_bg.jpg", None, cast,
              [("song", build + "/intro.wav", None), ("act", "Awa", "hop", 5, {"n": 6}),
               ("act", "Modou", "hop", 5, {"n": 5}), ("act", "Papa", "dance", 5)])
    s.cards = [(0.4, s.dur - 0.2, E.title_card(ep["title"], f"Épisode {ep['number']}  •  {ep['subtitle']}"))]
    return s


def outro_scene(ep, build):
    a, sr = E.read_wav(build + "/song.wav")
    d = len(a) / sr
    cast = layout("classe", [{"name": "Awa", "x": 1000}, {"name": "Modou", "x": 1450}, {"name": "Maîtresse Sokhna", "x": 2200}]) \
        if ep.get("outro_bg", "classe") == "classe" else layout("maison", ["Mame Ndèye", "Awa", "Modou", "Papa", "Yaay Fatou"])
    evs = [("act", n, "dance", d + 1) for n in cast] + [("song", build + "/song.wav", ep["song"]["lyrics"])]
    bgf = BGS[ep.get("outro_bg", "classe")]["file"]
    s = Scene(EPO, ASSETS + "bg/" + bgf, None, cast, evs)
    s.cards = [(0.3, 3.5, E.title_card("Woy ak ñun !", "Chante avec nous !", (90, 150, 60), (230, 70, 140)))]
    return s


def main(ep_path, build):
    ep = json.load(open(ep_path, encoding="utf-8"))
    amap = map_audio(ep, build)
    parts, timings = [], {}
    order = [("intro", lambda: intro_scene(ep, build))]
    for si, sc in enumerate(ep["scenes"]):
        order.append((f"s{si}", (lambda si=si, sc=sc: build_scene(ep, si, sc, build, amap))))
    order.append(("outro", lambda: outro_scene(ep, build)))
    t0 = 0.0
    for key, fn in order:
        sc = fn()
        if key == f"s{len(ep['scenes']) - 1}":
            sc.cards = [(sc.dur - 1.9, sc.dur, E.title_card("À suivre…", "Ba beneen yoon !", (240, 120, 20), (60, 140, 220)))]
        out = f"{build}/{key}.mp4"
        d = render_scene(sc, out)
        timings[key] = dict(start=t0, dur=d, lines=[(L["s"], L["e"]) for L in sc.lines],
                            wo=[L["wo"] for L in sc.lines], spk=[L["spk"] for L in sc.lines],
                            songs=[(S["s"], S["e"]) for S in sc.songs])
        t0 += d
        parts.append(key)
        print(key, round(d, 2), flush=True)
    with open(build + "/list.txt", "w") as f:
        for p in parts: f.write(f"file '{p}.mp4'\n")
    with open(build + "/alist.txt", "w") as f:
        for p in parts: f.write(f"file '{p}.wav'\n")
    run = lambda *a: subprocess.run(list(a), check=True, cwd=build)
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "v.mp4")
    run("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "alist.txt", "a.wav")
    run("ffmpeg", "-v", "error", "-y", "-i", "v.mp4", "-i", "a.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5", "-movflags", "+faststart", "-shortest", "episode.mp4")
    json.dump(timings, open(build + "/timings.json", "w"), indent=1)
    make_shorts(ep, build, timings)
    make_thumb(ep, build)


def pick_clips(ep, timings, n_max=6):
    """choisit jusqu'à n_max moments pour les Shorts : le moment choisi, la chanson, puis des gags."""
    clips = []
    def add(k, a, b, text, wo):
        if b - a < 12:
            return
        for c in clips:
            if c["scene"] == k and not (b <= c["a"] or a >= c["b"]):
                return
        clips.append(dict(scene=k, a=a, b=min(b, a + 55), text=text, wo=wo))
    sh = ep.get("short")
    if sh:
        T = timings[f"s{sh['scene']}"]
        add(f"s{sh['scene']}", max(0, T["lines"][sh["from"]][0] - 0.4), min(T["dur"], T["lines"][sh["to"]][1] + 0.6),
            sh["text"], T["wo"][sh["from"]])
    words = ep["title"].upper().split()
    gen_text = [" ".join(words[:2]), " ".join(words[2:]) or f"ÉP. {ep['number']}"]
    for k, T in timings.items():
        if not k.startswith("s"):
            continue
        for (sa, se) in T["songs"]:
            add(k, sa, min(se, sa + 45), ["♪ " + ep["song"]["title"].upper(), "WOY AK ÑUN !"], ep["song"]["lyrics"][0])
    for k, T in timings.items():
        if not k.startswith("s"):
            continue
        L = T["lines"]
        i = 0
        while i < len(L):
            j = i
            while j + 1 < len(L) and L[j + 1][1] - L[i][0] < 40:
                j += 1
            if L[j][1] - L[i][0] >= 15:
                add(k, max(0, L[i][0] - 0.4), min(T["dur"], L[j][1] + 0.6), gen_text, T["wo"][i])
            i = j + 1
    return clips[:n_max]


def make_shorts(ep, build, timings):
    clips = pick_clips(ep, timings, int(os.environ.get("SHORTS_PER_EPISODE", "6")))
    F = E.FB
    meta = []
    for n, c in enumerate(clips, 1):
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        f1 = ImageFont.truetype(F, 88); f2 = ImageFont.truetype(F, 46)
        for t, y in zip(c["text"], (250, 360)):
            while d.textlength(t, font=f1) > 1000 and f1.size > 50:
                f1 = ImageFont.truetype(F, f1.size - 6)
            w = d.textlength(t, font=f1); d.text(((1080 - w) / 2, y), t, font=f1, fill=(255, 225, 40), stroke_width=9, stroke_fill=(60, 20, 40))
        t = "Épisode complet sur la chaîne"
        w = d.textlength(t, font=f2); d.rounded_rectangle([(1080 - w) / 2 - 30, 1500, (1080 + w) / 2 + 30, 1580], 36, fill=(230, 70, 140))
        d.text(((1080 - w) / 2, 1512), t, font=f2, fill="white")
        img.save(f"{build}/short_overlay_{n}.png")
        a, dur = c["a"], c["b"] - c["a"]
        out = f"short_{n:02d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(dur), "-i", f"{c['scene']}.mp4", "-ss", str(a), "-t", str(dur),
                        "-i", f"{c['scene']}.wav", "-i", f"short_overlay_{n}.png", "-filter_complex",
                        "[0:v]split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=25:2,eq=brightness=-0.08[bg];[b]scale=1080:-2[fg];"
                        f"[bg][fg]overlay=0:(H-h)/2+80[v1];[v1][2:v]overlay=0:0,fade=t=out:st={dur - 0.6}:d=0.6[v]",
                        "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-af", f"loudnorm=I=-16:TP=-1.5,afade=t=out:st={dur - 1}:d=1", "-r", "30", out],
                       check=True, cwd=build)
        wo = c["wo"].rstrip(" !?.…")
        emo = "🎵" if c["text"][0].startswith("♪") else "😂"
        title = f"{wo[:45]} {emo} | {ep['title']} #wolof #shorts"
        meta.append(dict(file=out, title=title[:100],
                         description=f"Un moment de l'épisode {ep['number']} « {ep['title']} » 😄 Dessin animé en wolof pour enfants. "
                                     "Épisode complet sur la chaîne Xale Yi !\n#wolof #senegal #enfants #dessinanimé #shorts"))
    if os.path.exists(f"{build}/short_01.mp4"):
        import shutil; shutil.copy(f"{build}/short_01.mp4", f"{build}/short.mp4")
    json.dump(meta, open(f"{build}/shorts.json", "w"), ensure_ascii=False, indent=1)
    print("shorts :", len(meta))


def make_thumb(ep, build):
    th = ep["thumbnail"]
    W, H = 1280, 720
    bg = Image.open(ASSETS + "bg/" + BGS[th.get("bg", "classe")]["file"]).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(3))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (255, 200, 90)), 0.15)
    c = bg.convert("RGBA")

    def spr(name, h):
        im = Image.open(ASSETS + "chars/" + CHARS[name][0]).convert("RGBA")
        a = im.getchannel("A").point(lambda v: 0 if v < 40 else v); im.putalpha(a); im = im.crop(a.getbbox())
        return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)

    def glow(im):
        a = im.getchannel("A").point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(6))
        g = Image.new("RGBA", im.size, (255, 255, 255, 0)); g.putalpha(a); return g

    names = th.get("chars", ["Awa", "Modou"])
    pos = [(40, 170, 880), (800, 250, 700)]
    for name, (x, y, h) in zip(names, pos):
        im = spr(name, h); c.alpha_composite(glow(im), (x, y)); c.alpha_composite(im, (x, y))
    d = ImageDraw.Draw(c)
    f1 = ImageFont.truetype(E.FB, 96); f2 = ImageFont.truetype(E.FB, 58)
    for t, y in zip(th["text"], (40, 140)):
        w = d.textlength(t, font=f1)
        d.text((min(1240 - w, 820 - w / 2), y), t, font=f1, fill=(255, 225, 40), stroke_width=8, stroke_fill=(60, 20, 40))
    lab = f"ÉP. {ep['number']}"
    d.rounded_rectangle([590, 262, 600 + d.textlength(lab, font=f2) + 30, 330], 20, fill=(230, 70, 140))
    d.text((612, 268), lab, font=f2, fill="white")
    c.convert("RGB").save(build + "/thumbnail.jpg", quality=92)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
