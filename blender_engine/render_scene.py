import bpy
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BLEND_FILE = PROJECT / "blender_engine" / "renders" / "xale_scene_v1.blend"
OUTPUT = PROJECT / "blender_engine" / "renders" / "xale_scene_v1.mp4"

if not BLEND_FILE.exists():
    raise FileNotFoundError(f"❌ Fichier Blender introuvable : {BLEND_FILE}")

bpy.ops.wm.open_mainfile(filepath=str(BLEND_FILE))

scene = bpy.context.scene

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 50

scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 150

scene.render.image_settings.file_format = "FFMPEG"

scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.audio_codec = "AAC"

scene.render.filepath = str(OUTPUT)

print("")
print("🎬 RENDU XALE YI")
print(f"📁 Sortie : {OUTPUT}")
print("⏱️ Durée  : 5 secondes")
print("🎞️ Frames : 150")
print("")

bpy.ops.render.render(animation=True)

print("")
print("✅ VIDÉO TERMINÉE")
print(f"📁 {OUTPUT}")
