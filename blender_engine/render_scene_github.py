import bpy
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BLEND_FILE = PROJECT / "blender_engine" / "renders" / "xale_scene_v1.blend"
OUTPUT = PROJECT / "blender_engine" / "renders" / "xale_scene_github.mp4"

if not BLEND_FILE.exists():
    raise FileNotFoundError(
        f"Blend introuvable : {BLEND_FILE}"
    )

print("📂 Ouverture :", BLEND_FILE)

bpy.ops.wm.open_mainfile(
    filepath=str(BLEND_FILE)
)

scene = bpy.context.scene

# ------------------------------------------------------------
# RENDU LÉGER POUR LE RUNNER GITHUB
# ------------------------------------------------------------

scene.render.engine = "BLENDER_WORKBENCH"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 150

scene.render.image_settings.file_format = "FFMPEG"

scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.ffmpeg.audio_codec = "AAC"

scene.render.filepath = str(OUTPUT)

scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True

print("")
print("============================================")
print("🎬 XALE YI — BLENDER GITHUB RENDER")
print("============================================")
print("📐 640x360")
print("🎞️ 150 frames")
print("⏱️ 5 secondes")
print("⚡ Workbench")
print("============================================")
print("")

bpy.ops.render.render(
    animation=True
)

if not OUTPUT.exists():
    raise RuntimeError(
        f"❌ Le MP4 n'a pas été créé : {OUTPUT}"
    )

print("")
print("✅ RENDU TERMINÉ")
print("📁", OUTPUT)
print("============================================")
