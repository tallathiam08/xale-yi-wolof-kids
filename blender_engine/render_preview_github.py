import bpy
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BLEND = PROJECT / "blender_engine" / "renders" / "xale_scene_v1.blend"
OUTPUT = PROJECT / "blender_engine" / "renders" / "preview.png"

if not BLEND.exists():
    raise RuntimeError(f"Blend introuvable : {BLEND}")

bpy.ops.wm.open_mainfile(filepath=str(BLEND))

scene = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE_NEXT"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

scene.frame_start = 1
scene.frame_end = 1
scene.frame_set(1)

if scene.camera is None:
    raise RuntimeError("❌ Aucune caméra dans la scène")

scene.render.filepath = str(OUTPUT)

bpy.ops.render.render(write_still=True)

if not OUTPUT.exists():
    raise RuntimeError("❌ preview.png non créé")

print("✅ PREVIEW CRÉÉE")
print(f"📁 {OUTPUT}")
