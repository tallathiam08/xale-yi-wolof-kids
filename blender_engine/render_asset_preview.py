import bpy
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]

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

scene = bpy.context.scene

scene.render.engine = "BLENDER_EEVEE_NEXT"

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.frame_set(45)

scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

if scene.camera is None:
    raise RuntimeError(
        "❌ Aucune caméra dans le .blend chargé"
    )

scene.render.filepath = str(OUTPUT)

print("======================================")
print("🎨 XALE YI — RENDU PREVIEW")
print("======================================")
print(f"📁 Sortie : {OUTPUT}")
print(f"🎥 Caméra : {scene.camera.name}")
print("")

mesh_count = sum(
    1
    for obj in scene.objects
    if obj.type == "MESH"
)

print(
    f"🧩 Objets mesh : {mesh_count}"
)

if mesh_count < 5:
    raise RuntimeError(
        "❌ La scène Blender ne contient pas assez d'objets"
    )

bpy.ops.render.render(
    write_still=True
)

if not OUTPUT.exists():
    raise RuntimeError(
        f"❌ Preview non créée : {OUTPUT}"
    )

if OUTPUT.stat().st_size < 1000:
    raise RuntimeError(
        f"❌ Preview trop petite : "
        f"{OUTPUT.stat().st_size} octets"
    )

print("")
print("✅ PREVIEW CRÉÉE")
print(f"📦 Taille : {OUTPUT.stat().st_size} octets")
print(f"📁 {OUTPUT}")
print("======================================")
