import bpy
from pathlib import Path
import math


PROJECT = Path(__file__).resolve().parents[1]

OUTPUT = (
    PROJECT
    / "blender_engine"
    / "renders"
    / "xale_asset_preview.png"
)


scene = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE_NEXT"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.frame_set(45)

# Supprimer les anciennes caméras
for obj in list(bpy.data.objects):
    if obj.type == "CAMERA":
        bpy.data.objects.remove(
            obj,
            do_unlink=True,
        )

# Caméra frontale
bpy.ops.object.camera_add(
    location=(0, -20, 3.6),
    rotation=(math.radians(90), 0, 0),
)

camera = bpy.context.object
camera.name = "XalePreviewCamera"

camera.data.type = "ORTHO"
camera.data.ortho_scale = 9.0

camera.data.clip_start = 0.1
camera.data.clip_end = 1000

scene.camera = camera

scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = str(OUTPUT)

try:
    scene.view_settings.view_transform = "Standard"
except Exception:
    pass

print("======================================")
print("🎨 XALE YI — PREVIEW V4")
print("======================================")
print(f"🎥 Caméra : frontale")
print(f"📐 640x360")
print("")

objects = [
    o for o in scene.objects
    if o.type == "MESH"
]

print(f"🧩 Objets : {len(objects)}")

if len(objects) < 5:
    raise RuntimeError(
        "❌ Pas assez d'objets dans la scène"
    )

bpy.ops.render.render(
    write_still=True
)

if not OUTPUT.exists():
    raise RuntimeError(
        "❌ Preview PNG non créée"
    )

if OUTPUT.stat().st_size < 1000:
    raise RuntimeError(
        "❌ Preview PNG anormalement petite"
    )

print("")
print("✅ PREVIEW CRÉÉE")
print(f"📁 {OUTPUT}")
print(f"📦 {OUTPUT.stat().st_size} octets")
print("======================================")
