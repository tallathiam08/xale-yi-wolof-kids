import argparse
import json
import subprocess
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET = BASE_DIR / "credentials" / "client_secret.json"
TOKEN_FILE = BASE_DIR / "credentials" / "youtube_token.json"
VIDEO_DEFAULT = BASE_DIR / "output" / "episode" / "episode_final.mp4"
SRT_DEFAULT = BASE_DIR / "output" / "episode" / "episode_subtitles.srt"
THUMB_DEFAULT = BASE_DIR / "output" / "episode" / "thumbnail.jpg"
SCENES_DEFAULT = BASE_DIR / "episode_01_scenes_wolof.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def authenticate():
    if not CLIENT_SECRET.exists():
        raise FileNotFoundError(
            f"Fichier OAuth introuvable : {CLIENT_SECRET}"
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET), SCOPES
        )
        creds = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def title_from_scenes():
    if SCENES_DEFAULT.exists():
        try:
            data = json.loads(SCENES_DEFAULT.read_text(encoding="utf-8"))
            return data.get("title") or "Histoire en Wolof pour les enfants"
        except Exception:
            pass
    return "Histoire en Wolof pour les enfants"


def create_thumbnail(video: Path, output: Path, title: str):
    from PIL import Image, ImageDraw, ImageFont
    import imageio_ffmpeg

    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    frame = output.with_name("thumbnail_frame.jpg")

    subprocess.run(
        [ffmpeg, "-y", "-ss", "1", "-i", str(video),
         "-frames:v", "1", "-q:v", "2", str(frame)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    image = Image.open(frame).convert("RGB").resize((1280, 720))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 500, 1280, 720), fill=(0, 0, 0, 175))

    font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    try:
        font = ImageFont.truetype(font_path, 58)
    except Exception:
        font = ImageFont.load_default()

    text = title if len(title) <= 45 else title[:42].rstrip() + "..."
    draw.text(
        (50, 545), text, font=font,
        fill=(255, 215, 80, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 255),
    )
    image.save(output, format="JPEG", quality=95, optimize=True)
    frame.unlink(missing_ok=True)


def upload_video(youtube, video, title, description, tags, privacy, made_for_kids, publish_at):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",
            "defaultLanguage": "wo",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
            "license": "youtube",
        },
    }

    if publish_at:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(
        str(video), mimetype="video/mp4", resumable=True,
        chunksize=8 * 1024 * 1024,
    )
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"⬆️ Upload : {int(status.progress() * 100)}%")

    return response["id"]


def upload_thumbnail(youtube, video_id, thumbnail):
    media = MediaFileUpload(str(thumbnail), mimetype="image/jpeg")
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def upload_captions(youtube, video_id, srt):
    if not srt.exists():
        print("⚠️ SRT absent — sous-titres non envoyés.")
        return
    media = MediaFileUpload(str(srt), mimetype="application/octet-stream")
    body = {
        "snippet": {
            "videoId": video_id,
            "language": "wo",
            "name": "Wolof",
            "isDraft": False,
        }
    }
    youtube.captions().insert(
        part="snippet", body=body, media_body=media
    ).execute()


def main():
    ap = argparse.ArgumentParser(description="YouTube uploader automatisé")
    ap.add_argument("--auth-only", action="store_true", help="Teste OAuth sans upload")
    ap.add_argument("--video", default=str(VIDEO_DEFAULT))
    ap.add_argument("--srt", default=str(SRT_DEFAULT))
    ap.add_argument("--thumbnail", default=str(THUMB_DEFAULT))
    ap.add_argument("--title", default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--tags", default="wolof,enfants,histoire,enfants wolof,animation,senegal")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    ap.add_argument("--made-for-kids", action="store_true")
    ap.add_argument("--publish-at", default=None)
    ap.add_argument("--skip-thumbnail", action="store_true")
    ap.add_argument("--skip-captions", action="store_true")
    args = ap.parse_args()

    youtube = authenticate()
    print("✅ Authentification YouTube réussie")

    if args.auth_only:
        return

    video = Path(args.video).expanduser()
    srt = Path(args.srt).expanduser()
    thumbnail = Path(args.thumbnail).expanduser()
    if not video.exists():
        raise FileNotFoundError(f"Vidéo introuvable : {video}")

    title = args.title or title_from_scenes()
    description = args.description or (
        f"{title}\n\n"
        "Une histoire animée en wolof pour les enfants.\n\n"
        "🎬 Animation pour enfants\n"
        "🗣️ Langue : Wolof\n\n"
        "#Wolof #Enfants #Animation #Senegal"
    )
    tags = [x.strip() for x in args.tags.split(",") if x.strip()]

    if not args.skip_thumbnail:
        create_thumbnail(video, thumbnail, title)
        print(f"✅ Miniature créée : {thumbnail}")

    video_id = upload_video(
        youtube, video, title, description, tags,
        args.privacy, args.made_for_kids, args.publish_at,
    )
    print(f"✅ Upload terminé : {video_id}")

    if thumbnail.exists():
        upload_thumbnail(youtube, video_id, thumbnail)
        print("✅ Miniature YouTube définie")

    if not args.skip_captions:
        upload_captions(youtube, video_id, srt)
        print("✅ Traitement des sous-titres terminé")

    print(f"https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
