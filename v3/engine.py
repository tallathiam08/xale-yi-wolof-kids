"""Moteur d'animation 2.5D pour les épisodes (personnages 3D découpés + voix ElevenLabs).
Un épisode = une liste de scènes ; chaque scène = un décor, une distribution, une suite d'événements.
"""
import math, subprocess, wave, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OW, OH, FPS = 1920, 1080, 30
CW, CH = 2880, 1620
GAP = 0.32
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FI = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
D = os.path.dirname(os.path.abspath(__file__)) + "/"


# ---------------------------------------------------------------- audio helpers
def read_wav(path):
    with wave.open(path) as w:
        sr = w.getframerate(); n = w.getnframes()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a, sr


def envelope(path):
    a, sr = read_wav(path)
    hop = sr // FPS
    n = len(a) // hop
    e = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    if e.max() > 0:
        e = e / np.percentile(e[e > 0.01] if (e > 0.01).any() else e, 90)
    return np.clip(e, 0, 1.4), len(a) / sr


# ---------------------------------------------------------------- sprites
def mouth_layer(size, cx, cy, mw, k):
    s = 3
    w, h = size
    L = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    rx = mw * 0.30 * s
    ry = mw * (0.10 + 0.17 * k) * s
    X, Y = cx * s, (cy + mw * 0.04) * s
    d.ellipse([X - rx, Y - ry, X + rx, Y + ry], fill=(55, 14, 18, 245))
    d.chord([X - rx * 0.75, Y - ry * 1.0, X + rx * 0.75, Y - ry * 0.45], 180, 360, fill=(225, 218, 212, 190))
    d.ellipse([X - rx * 0.55, Y + ry * 0.15, X + rx * 0.55, Y + ry * 0.95], fill=(165, 62, 72, 235))
    return L.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))


class Sprite:
    def __init__(self, png, mouth, mw, H0=900):
        im = Image.open(png).convert("RGBA")
        bb = im.getchannel("A").getbbox()
        im = im.crop(bb)
        mx, my = mouth[0] - bb[0], mouth[1] - bb[1]
        sc = H0 / im.height
        base = im.resize((int(im.width * sc), H0), Image.LANCZOS)
        mx, my, mw = mx * sc, my * sc, mw * sc
        vs = [base]
        for k in (0.35, 0.7, 1.0):
            v = base.copy()
            v.alpha_composite(mouth_layer(base.size, mx, my, mw, k))
            v.putalpha(base.getchannel("A"))
            vs.append(v)
        # premultiplied float arrays
        self.v = [np.asarray(x).astype(np.float32) / 255 for x in vs]
        self.H0 = H0
        self.w0 = base.width
        self.cache = {}

    def get(self, idx, h, flip=False):
        h = max(8, int(round(h / 4) * 4))
        key = (idx, h, flip)
        if key not in self.cache:
            src = self.v[idx]
            w = max(4, int(self.w0 * h / self.H0))
            r = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA if h < self.H0 else cv2.INTER_LINEAR)
            if flip:
                r = r[:, ::-1]
            if len(self.cache) > 40:
                self.cache.clear()
            self.cache[key] = np.ascontiguousarray(r)
        return self.cache[key]


def blend(dst, src, x, y, alpha=1.0):
    """dst float HxWx3 ; src float hxwx4 ; top-left x,y"""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4] * alpha
    d = dst[y0:y1, x0:x1]
    d *= (1 - a)
    d += s[..., :3] * a


# ---------------------------------------------------------------- text cards
def rgba_np(img):
    return np.asarray(img).astype(np.float32) / 255


def subtitle_img(speaker, wo, fr, color):
    fW = ImageFont.truetype(FB, 46); fF = ImageFont.truetype(FI, 31); fN = ImageFont.truetype(FB, 30)
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    wl = wrap(tmp, wo, fW, 1500)
    fl = wrap(tmp, fr, fF, 1500) if fr else []
    bw = int(max([tmp.textlength(l, font=fW) for l in wl] + [tmp.textlength(l, font=fF) for l in fl])) + 90
    bh = 56 * len(wl) + 40 * len(fl) + 46
    img = Image.new("RGBA", (bw, bh + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 24, bw, 24 + bh], 26, fill=(255, 255, 255, 230), outline=color, width=5)
    if speaker:
        nw = tmp.textlength(speaker, font=fN) + 34
        d.rounded_rectangle([26, 0, 26 + nw, 46], 18, fill=color)
        d.text((43, 5), speaker, font=fN, fill=(255, 255, 255))
    y = 48
    for l in wl:
        d.text(((bw - tmp.textlength(l, font=fW)) / 2, y), l, font=fW, fill=(40, 30, 30)); y += 56
    for l in fl:
        d.text(((bw - tmp.textlength(l, font=fF)) / 2, y + 2), l, font=fF, fill=(105, 95, 95)); y += 40
    return rgba_np(img)


def wrap(d, text, font, maxw):
    out = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if d.textlength(t, font=font) > maxw and cur:
                out.append(cur); cur = wd
            else:
                cur = t
        out.append(cur)
    return out


def title_card(t1, t2, c1=(230, 70, 140), c2=(30, 140, 110)):
    img = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1, f2 = ImageFont.truetype(FB, 96), ImageFont.truetype(FB, 46)
    w1, w2 = d.textlength(t1, font=f1), d.textlength(t2, font=f2)
    bw = max(w1, w2) + 140
    x0 = (OW - bw) / 2
    d.rounded_rectangle([x0, 330, x0 + bw, 720], 50, fill=(255, 250, 240, 238), outline=c1, width=9)
    d.text(((OW - w1) / 2 + 4, 394), t1, font=f1, fill=(0, 0, 0, 60))
    d.text(((OW - w1) / 2, 390), t1, font=f1, fill=c1)
    d.text(((OW - w2) / 2, 560), t2, font=f2, fill=c2)
    return rgba_np(img)


# ---------------------------------------------------------------- easing
def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


# ---------------------------------------------------------------- scene
class Scene:
    """bg: path ; crop: (x0,y0,x1,y1) of bg to use ; cast: {name: dict(x,y,h,flip)} ;
    events: list of tuples:
      ('wait', sec)
      ('line', wavpath, speaker, wolof, french[, opts])   opts: dict(cam='wide'|name, who=name-for-mouth)
      ('song', wavpath, lyrics_lines)
      ('act', name, kind, dur, params)   non-blocking, starts at cursor
    """

    def __init__(self, E, bg, crop, cast, events, pan=None, music_bed=None):
        self.E = E
        im = Image.open(bg).convert("RGB")
        if crop:
            im = im.crop(crop)
        self.bgw = CW * (1.35 if pan else 1.0)
        bgimg = im.resize((int(self.bgw), CH), Image.LANCZOS)
        self.bg = np.asarray(bgimg).astype(np.float32) / 255
        self.pan = pan
        self.cast = {k: dict(v) for k, v in cast.items()}
        self.build(events)

    def build(self, events):
        t = 0.0
        self.lines, self.acts, self.songs = [], [], []
        self.audio = []  # (start, wav)
        for ev in events:
            k = ev[0]
            if k == "wait":
                t += ev[1]
            elif k == "line":
                wav, spk, wo, fr = ev[1:5]
                opts = ev[5] if len(ev) > 5 else {}
                env, dur = envelope(wav)
                self.lines.append(dict(s=t, e=t + dur, spk=spk, wo=wo, fr=fr, env=env, opts=opts,
                                       sub=subtitle_img(opts.get("label", spk), wo, fr,
                                                        self.E.colors.get(spk, (90, 90, 90)))))
                self.audio.append((t, wav))
                t += dur + opts.get("gap", GAP)
            elif k == "song":
                wav, lyr = ev[1], ev[2]
                env, dur = envelope(wav)
                self.songs.append(dict(s=t, e=t + dur, lyr=lyr, env=env))
                self.audio.append((t, wav))
                t += dur + 0.2
            elif k == "act":
                self.acts.append(dict(s=t, name=ev[1], kind=ev[2], d=ev[3], p=ev[4] if len(ev) > 4 else {}))
        self.dur = t + 0.8
        self.make_shots()

    # ------------- camera
    def head(self, name, z):
        c = self.cast[name]
        return (c["x"], c["y"] - c["h"] * 0.62, z)

    def make_shots(self):
        W = (self.bgw / 2 if not self.pan else CW / 2, CH / 2, 1.0)
        shots = [(0.0, W, W)]
        for L in self.lines:
            cam = L["opts"].get("cam", L["spk"])
            if cam == "wide" or cam not in self.cast:
                tgt = (W[0], W[1], 1.04)
            elif isinstance(cam, tuple):
                tgt = cam
            else:
                c = self.cast[cam]
                z = L["opts"].get("z", 1.65 if c["h"] > 700 else 2.0)
                tgt = self.head(cam, z)
            end = (tgt[0], tgt[1], tgt[2] * 1.04)
            shots.append((max(0, L["s"] - 0.25), tgt, end))
        for S in self.songs:
            shots.append((S["s"], W, (W[0], W[1], 1.08)))
        self.shots = sorted(shots, key=lambda s: s[0])

    def camera(self, t):
        cur = self.shots[0]
        nxt_t = self.dur
        for i, s in enumerate(self.shots):
            if s[0] <= t:
                cur = s
                nxt_t = self.shots[i + 1][0] if i + 1 < len(self.shots) else self.dur
        t0, a, b = cur
        k = (t - t0) / max(0.01, nxt_t - t0)
        pos = [lerp(a[j], b[j], k) for j in range(3)]
        # transition from previous shot end
        idx = self.shots.index(cur)
        if idx > 0 and t - t0 < 0.35:
            p0, pa, pb = self.shots[idx - 1]
            prev_end = [lerp(pa[j], pb[j], 1.0) for j in range(3)]
            kk = ease((t - t0) / 0.35)
            pos = [lerp(prev_end[j], pos[j], kk) for j in range(3)]
        return pos

    # ------------- character state
    def mouth(self, name, t):
        for L in self.lines:
            who = L["opts"].get("who", L["spk"])
            if who == name and L["s"] <= t < L["e"]:
                i = int((t - L["s"]) * FPS)
                v = L["env"][i] if i < len(L["env"]) else 0
                if v < 0.18: return 0
                return 1 if v < 0.45 else (2 if v < 0.8 else 3)
        return 0

    def talking(self, name, t):
        return any(L["opts"].get("who", L["spk"]) == name and L["s"] <= t < L["e"] for L in self.lines)

    def state(self, name, t):
        c = self.cast[name]
        st = dict(x=c["x"], y=c["y"], h=c["h"], rot=0.0, sx=1.0, sy=1.0, alpha=1.0, flip=c.get("flip", False),
                  visible=c.get("visible", True))
        ph = (hash(name) % 100) / 100
        # idle breathing
        st["sy"] *= 1 + 0.012 * math.sin((t + ph) * 2 * math.pi * 0.45)
        if self.talking(name, t):
            st["y"] -= abs(math.sin((t + ph) * 2 * math.pi * 1.6)) * c["h"] * 0.012
            st["rot"] += math.sin((t + ph) * 2 * math.pi * 0.8) * 1.6
        for A in self.acts:
            if A["name"] != name or t < A["s"]:
                continue
            k = (t - A["s"]) / A["d"]
            p = A["p"]
            kind = A["kind"]
            if kind == "hide" and k >= 0:
                st["visible"] = k < 1 and st["visible"]
                if k < 1:
                    st["alpha"] = 1 - ease(k)
                    st["y"] += ease(k) * c["h"] * 0.25
            elif kind == "show" and k >= 0:
                st["visible"] = True
                if k < 1:
                    st["alpha"] = ease(k)
            elif kind == "pop" and k >= 0:
                st["visible"] = True
                if k < 1:
                    kk = ease(k)
                    st["y"] += (1 - kk) * c["h"] * 0.9
                    st["sy"] *= 1 + 0.18 * math.sin(k * math.pi)
            elif kind == "move" and k >= 0:
                kk = ease(min(1, k))
                st["x"] = lerp(st["x"], p["x"], kk)
                if "y" in p: st["y"] = lerp(st["y"], p["y"], kk)
                c_end = c.setdefault("_end", {})
                if k >= 1:
                    st["x"] = p["x"]
                if k < 1:
                    st["y"] -= abs(math.sin(k * A["d"] * math.pi * 2.2)) * c["h"] * 0.03
            elif kind == "walk" and 0 <= k < 1:
                st["y"] -= abs(math.sin(t * math.pi * 2.6)) * c["h"] * 0.03
                st["rot"] += math.sin(t * math.pi * 2.6) * 2.5
            elif kind == "hop" and 0 <= k < 1:
                st["y"] -= abs(math.sin(k * math.pi * p.get("n", 3))) * c["h"] * 0.09
            elif kind == "shake" and 0 <= k < 1:
                st["rot"] += math.sin(t * 2 * math.pi * 7) * p.get("a", 3.5)
            elif kind == "flip" and k >= 0:
                st["flip"] = p.get("v", True)
            elif kind == "dance" and 0 <= k < 1:
                st["rot"] += math.sin(t * 2 * math.pi * 1.8) * 6
                st["y"] -= abs(math.sin(t * 2 * math.pi * 1.8)) * c["h"] * 0.05
        # persistent move results
        for A in self.acts:
            if A["name"] == name and A["kind"] == "move" and t >= A["s"] + A["d"]:
                st["x"] = A["p"]["x"]
                if "y" in A["p"]: st["y"] = A["p"]["y"]
        return st

    # ------------- frame
    def frame(self, t):
        cx, cy, z = self.camera(t)
        vw, vh = CW / z, CH / z
        if self.pan:
            # horizontal pan of the wide background during the scene
            off = (self.bgw - CW) * ease(t / self.dur) if self.pan == "lr" else 0
        else:
            off = 0
        x0 = min(max(cx - vw / 2, 0), CW - vw)
        y0 = min(max(cy - vh / 2, 0), CH - vh)
        s = OW / vw
        bx0 = int(x0 + off)
        crop = self.bg[int(y0):int(y0 + vh), bx0:int(bx0 + vw)]
        fr = cv2.resize(crop, (OW, OH), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR).copy()
        order = sorted(self.cast, key=lambda n: self.cast[n]["y"])
        for name in order:
            st = self.state(name, t)
            if not st["visible"] or st["alpha"] <= 0.01:
                continue
            spr = self.E.sprites[name]
            idx = self.mouth(name, t)
            h = st["h"] * s * st["sy"]
            img = spr.get(idx, h, st["flip"])
            if st["rot"]:
                hh, ww = img.shape[:2]
                M = cv2.getRotationMatrix2D((ww / 2, hh), st["rot"], 1.0)
                pad = int(hh * 0.12)
                M[0, 2] += pad; M[1, 2] += pad
                img = cv2.warpAffine(img, M, (ww + 2 * pad, hh + 2 * pad), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                fx = (st["x"] - x0) * s - ww / 2 - pad
                fy = (st["y"] - y0) * s - hh - pad
            else:
                hh, ww = img.shape[:2]
                fx = (st["x"] - x0) * s - ww / 2
                fy = (st["y"] - y0) * s - hh
            # contact shadow
            if self.cast[name].get("shadow", True):
                sw = int(ww * 0.75); sh = max(4, int(sw * 0.16))
                sx_ = int((st["x"] - x0) * s - sw / 2); sy_ = int((self.cast[name]["y"] - y0) * s - sh / 2)
                blend_shadow(fr, sx_, sy_, sw, sh, 0.28 * st["alpha"])
            blend(fr, img, int(fx), int(fy), st["alpha"])
        # overlays
        for L in self.lines:
            if L["s"] - 0.05 <= t < L["e"] + 0.2 and L["wo"]:
                sub = L["sub"]
                a = min(1, (t - L["s"] + 0.05) / 0.15, (L["e"] + 0.2 - t) / 0.15)
                blend(fr, sub, (OW - sub.shape[1]) // 2, OH - sub.shape[0] - 34, max(0, a))
        for S in self.songs:
            if S["s"] <= t < S["e"] and S.get("lyr"):
                self.E.song_overlay(fr, t - S["s"], S)
        for (t0, t1, img) in getattr(self, "cards", []):
            if t0 <= t < t1:
                a = min(1, (t - t0) / 0.3, (t1 - t) / 0.3)
                blend(fr, img, 0, 0, max(0, a))
        f = min(1.0, t / 0.35, (self.dur - t) / 0.35)
        if f < 1:
            fr *= max(0.0, f)
        return fr


def blend_shadow(fr, x, y, w, h, a):
    key = (w, h)
    m = _SH.get(key)
    if m is None:
        m = np.zeros((h, w), np.float32)
        cv2.ellipse(m, (w // 2, h // 2), (w // 2 - 2, h // 2 - 1), 0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), max(1, h / 4))
        _SH[key] = m
    H, W = fr.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    mm = m[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * a
    fr[y0:y1, x0:x1] *= (1 - mm * 0.75)
_SH = {}


# ---------------------------------------------------------------- render helpers
def encode(frames_iter, out, n):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in frames_iter:
        p.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    return p.returncode
