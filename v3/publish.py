"""Publie l'épisode et son Short sur YouTube (API YouTube Data v3, jeton OAuth « refresh token »).
Secrets GitHub nécessaires : YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Usage : python publish.py episodes/ep02.json build/ep02
"""
import json, os, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def yt():
    c = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                    client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token",
                    scopes=["https://www.googleapis.com/auth/youtube"])
    c.refresh(Request())
    return build("youtube", "v3", credentials=c, cache_discovery=False)


SUB = "\n\n🔔 Abonne-toi pour voir la suite d'Awa et Modou : https://www.youtube.com/@wolof-kids?sub_confirmation=1"


def upload(api, path, title, desc, tags, privacy, thumb=None):
    if "sub_confirmation" not in desc:
        desc = (desc + SUB)[:4900]
    body = {
        "snippet": {"title": title[:100], "description": desc, "tags": tags, "categoryId": "1",
                    "defaultLanguage": "fr", "defaultAudioLanguage": "wo"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": True, "containsSyntheticMedia": True,
                   "embeddable": True},
    }
    req = api.videos().insert(part="snippet,status", body=body,
                              media_body=MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True))
    res = None
    while res is None:
        st, res = req.next_chunk()
        if st:
            print(f"  envoi {int(st.progress() * 100)} %", flush=True)
    vid = res["id"]
    if thumb:
        try:
            api.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute()
        except Exception as e:  # la miniature personnalisée exige une chaîne validée
            print("miniature non appliquée :", e)
    return vid


def main(ep_path, b):
    need = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
    if not all(os.environ.get(k) for k in need):
        print("⚠️ Secrets YouTube absents : la vidéo est fabriquée mais pas publiée.")
        return None
    ep = json.load(open(ep_path, encoding="utf-8"))
    privacy = os.environ.get("PUBLISH_PRIVACY", "public")
    api = yt()
    y = ep["youtube"]
    vid = upload(api, f"{b}/episode.mp4", y["title"], y["description"], y["tags"], privacy, f"{b}/thumbnail.jpg")
    print("épisode :", f"https://youtu.be/{vid}")
    sid = None
    if os.path.exists(f"{b}/short_01.mp4"):
        meta = json.load(open(f"{b}/shorts.json", encoding="utf-8"))[0] if os.path.exists(f"{b}/shorts.json") else {}
        s = ep.get("short_youtube", {})
        sid = upload(api, f"{b}/short_01.mp4", s.get("title", meta.get("title", ep["title"] + " #shorts")),
                     s.get("description", meta.get("description", "")) + f"\n\nÉpisode complet : https://youtu.be/{vid}",
                     y["tags"][:10], privacy)
        print("short :", f"https://youtu.be/{sid}")
    return {"video": vid, "short": sid, "privacy": privacy}


def post_short(path, title, desc, tags):
    privacy = os.environ.get("PUBLISH_PRIVACY", "public")
    return upload(yt(), path, title, desc, tags, privacy)


def check():
    """vérifie l'accès YouTube sans rien publier"""
    ch = yt().channels().list(part="snippet", mine=True).execute()
    for c in ch.get("items", []):
        print("✅ accès YouTube OK – chaîne :", c["snippet"]["title"])


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        check(); sys.exit(0)
    r = main(sys.argv[1], sys.argv[2])
    if r:
        json.dump(r, open(sys.argv[2] + "/published.json", "w"))
