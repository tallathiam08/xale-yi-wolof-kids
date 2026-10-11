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


if not BLEND.exists():
    raise RuntimeError(
        f"Blend absent : {BLEND}"
    )


bpy.ops.wm.open_mainfile(
    filepath=str(BLEND)
)

scene = bpy.context.scene

scene.render.engine = (
    "BLENDER_EEVEE_NEXT"
)

scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

scene.frame_set(45)

scene.render.image_settings.file_format = (
    "PNG"
)

scene.render.film_transparent = False

scene.render.filepath = str(OUTPUT)

bpy.ops.render.render(
    write_still=True
)

if not OUTPUT.exists():
    raise RuntimeError(
        "Preview absente"
    )

print("✅ PREVIEW CRÉÉE")
print(OUTPUT)
