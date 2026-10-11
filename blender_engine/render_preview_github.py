import bpy
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

BLEND = (
    PROJECT
    / "blender_engine"
    / "renders"
    / "xale_scene_v1.blend"
)

OUTPUT = (
    PROJECT
    / "blender_engine"
    / "renders"
    / "preview.png"
)

if not BLEND.exists():
    raise RuntimeError(
        f"❌ Blend introuvable : {BLEND}"
    )

bpy.ops.wm.open_mainfile(
    filepath=str(BLEND)
)

scene = bpy.context.scene

# Workbench = rendu rapide et extrêmement fiable
scene.render.engine = "BLENDER_WORKBENCH"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.frame_set(1)

# ------------------------------------------------------------
# NOUVELLE CAMÉRA DE PREVIEW
# ------------------------------------------------------------

for obj in list(bpy.data.objects):
    if obj.type == "CAMERA":
        bpy.data.objects.remove(
            obj,
            do_unlink=True,
        )

bpy.ops.object.camera_add(
    location=(0, -20, 4.5),
)

camera = bpy.context.object
camera.name = "PreviewCamera"

camera.data.type = "ORTHO"
camera.data.ortho_scale = 10.0

camera.rotation_euler = (
    math.radians(86),
    0,
    0,
)

camera.data.clip_start = 0.1
camera.data.clip_end = 1000

scene.camera = camera

# ------------------------------------------------------------
# WORKBENCH
# ------------------------------------------------------------

scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "paint.sl"
scene.display.shading.color_type = "MATERIAL"

scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True

scene.display.shading.cavity_type = "WORLD"
scene.display.shading.curvature_ridge_factor = 1.5
scene.display.shading.curvature_valley_factor = 1.0

scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

scene.render.filepath = str(OUTPUT)

print("")
print("======================================")
print("🎨 XALE YI — PREVIEW VISUELLE")
print("======================================")
print("📐 640x360")
print("🎥 Caméra frontale")
print("⚡ Workbench")
print("")

objects = [
    obj
    for obj in scene.objects
    if obj.type == "MESH"
]

print(
    f"🧩 Objets visibles dans la scène : "
    f"{len(objects)}"
)

if not objects:
    raise RuntimeError(
        "❌ Aucun objet 3D dans la scène"
    )

bpy.ops.render.render(
    write_still=True
)

if not OUTPUT.exists():
    raise RuntimeError(
        "❌ preview.png non créé"
    )

print("")
print("✅ PREVIEW CRÉÉE")
print(f"📁 {OUTPUT}")
