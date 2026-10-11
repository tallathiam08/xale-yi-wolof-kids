import bpy
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]

BLEND = (
    PROJECT
    / "blender_engine"
    / "renders"
    / "xale_asset_scene.blend"
)

OUTPUT = (
    PROJECT
    / "blender_engine"
    / "renders"
    / "xale_asset_preview.png"
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if not BLEND.exists():
    raise RuntimeError(
        f"❌ Blend introuvable : {BLEND}"
    )

bpy.ops.wm.open_mainfile(
    filepath=str(BLEND)
)

scene = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE_NEXT"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.frame_set(45)

scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

if scene.camera is None:
    raise RuntimeError("❌ Aucune caméra")

scene.render.filepath = str(OUTPUT)

print("🎨 Rendu de la preview...")

result = bpy.ops.render.render(
    write_still=False
)

print("Blender render result :", result)

render_result = bpy.data.images.get("Render Result")

if render_result is None:
    raise RuntimeError(
        "❌ Blender n'a pas produit de Render Result"
    )

# Sauvegarde FORCÉE vers le chemin absolu
render_result.save_render(
    filepath=str(OUTPUT),
    scene=scene,
)

if not OUTPUT.exists():
    raise RuntimeError(
        f"❌ PNG non créée : {OUTPUT}"
    )

if OUTPUT.stat().st_size < 1000:
    raise RuntimeError(
        f"❌ PNG anormalement petite : "
        f"{OUTPUT.stat().st_size} octets"
    )

print("")
print("================================")
print("✅ PREVIEW XALE YI CRÉÉE")
print("================================")
print(f"📁 {OUTPUT}")
print(f"📦 Taille : {OUTPUT.stat().st_size} octets")
print("================================")
