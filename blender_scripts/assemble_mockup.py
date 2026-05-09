"""
Tilemap JSON -> Blender 3D mockup assembler.

USAGE
1. Open Blender -> Scripting tab -> open this file (or paste contents)
2. Edit JSON_PATH below to point to your saved tilemap JSON
3. Press Alt+P to run

RESULT
- Existing scene cleared
- 3D placeholder cubes placed per JSON placements (color/height per module type)
- Top-down orthographic camera + sun light auto-configured
- Coordinate mapping: image y-axis (down) -> world +Y (up = north in top-down view)

Keep MODULE_STYLE keys in sync with the editor's MODULES list (index.html).
"""
import bpy
import json
from pathlib import Path

# ────────────────────────────────────────────────────────────
# CONFIG: edit JSON_PATH to your saved tilemap
# ────────────────────────────────────────────────────────────
JSON_PATH = r"C:\path\to\your\tilemap.json"

# Module styling — keep keys in sync with index.html MODULES
MODULE_STYLE = {
    "block_1m_grass": {"height": 1.0, "shape_factor": 1.0, "color": (0.29, 0.60, 0.29)},
    "block_1m_dirt":  {"height": 0.3, "shape_factor": 1.0, "color": (0.48, 0.35, 0.23)},
    "block_1m_stone": {"height": 1.0, "shape_factor": 1.0, "color": (0.60, 0.60, 0.60)},
    "block_5m_stone": {"height": 2.5, "shape_factor": 1.0, "color": (0.35, 0.35, 0.35)},
    "tree":           {"height": 2.5, "shape_factor": 0.4, "color": (0.05, 0.35, 0.10)},
    "building_3x3":   {"height": 5.0, "shape_factor": 1.0, "color": (0.67, 0.20, 0.20)},
    "mountain_5x5":   {"height": 6.0, "shape_factor": 1.0, "color": (0.27, 0.29, 0.31)},
}


def make_cube_mesh(name, sx, sy, sz):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        (-hx, -hy, -hz), ( hx, -hy, -hz), ( hx,  hy, -hz), (-hx,  hy, -hz),
        (-hx, -hy,  hz), ( hx, -hy,  hz), ( hx,  hy,  hz), (-hx,  hy,  hz),
    ]
    faces = [(0,1,2,3), (4,7,6,5), (0,4,5,1), (1,5,6,2), (2,6,7,3), (3,7,4,0)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def get_or_create_material(module_id, mat_cache):
    if module_id in mat_cache:
        return mat_cache[module_id]
    style = MODULE_STYLE[module_id]
    mat = bpy.data.materials.new(f"Mat_{module_id}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*style["color"], 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    mat_cache[module_id] = mat
    return mat


def clear_scene():
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in [bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras]:
        for item in list(col):
            if item.users == 0:
                col.remove(item)
    for c in list(bpy.data.collections):
        if not c.objects and not c.children and c.name != "Collection":
            bpy.data.collections.remove(c)


def assemble(json_path):
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON not found: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    grid_w, grid_h = data["size"]
    tile_m = data.get("tile_size_m", 1.0)
    placements = data["placements"]

    clear_scene()

    mockup_col = bpy.data.collections.new("TilemapMockup")
    bpy.context.scene.collection.children.link(mockup_col)

    mat_cache = {}
    counts, skipped = {}, []

    for p in placements:
        module_id = p["module"]
        if module_id not in MODULE_STYLE:
            skipped.append(module_id)
            continue
        style = MODULE_STYLE[module_id]
        x, y = p["x"], p["y"]
        fw, fh = p["footprint"]
        sx = fw * tile_m * style["shape_factor"]
        sy = fh * tile_m * style["shape_factor"]
        sz = style["height"]
        cx = (x + fw / 2.0) * tile_m
        cy = (grid_h - (y + fh / 2.0)) * tile_m  # flip Y
        cz = sz / 2.0
        mesh = make_cube_mesh(f"M_{module_id}_{x}_{y}", sx, sy, sz)
        obj = bpy.data.objects.new(f"O_{module_id}_{x}_{y}", mesh)
        obj.location = (cx, cy, cz)
        obj.data.materials.append(get_or_create_material(module_id, mat_cache))
        mockup_col.objects.link(obj)
        counts[module_id] = counts.get(module_id, 0) + 1

    # Ground plate
    ground_mesh = make_cube_mesh("Ground_mesh",
                                 grid_w * tile_m * 1.5,
                                 grid_h * tile_m * 1.5,
                                 0.05)
    ground = bpy.data.objects.new("Ground", ground_mesh)
    ground.location = (grid_w * tile_m / 2.0, grid_h * tile_m / 2.0, -0.025)
    gmat = bpy.data.materials.new("Mat_Ground")
    gmat.use_nodes = True
    gbsdf = gmat.node_tree.nodes.get("Principled BSDF")
    gbsdf.inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1.0)
    gbsdf.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(gmat)
    mockup_col.objects.link(ground)

    # Top-down ortho camera
    cam_data = bpy.data.cameras.new("TopDownCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(grid_w, grid_h) * tile_m * 1.10
    cam_data.clip_end = 500.0
    cam = bpy.data.objects.new("TopDownCam", cam_data)
    cam.location = (grid_w * tile_m / 2.0, grid_h * tile_m / 2.0, 100.0)
    cam.rotation_euler = (0, 0, 0)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # Sun
    sun_data = bpy.data.lights.new("Sun", type='SUN')
    sun_data.energy = 4.0
    sun_data.angle = 0.05
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (20.0, -20.0, 50.0)
    sun.rotation_euler = (0.6, 0.2, 0.6)
    bpy.context.scene.collection.objects.link(sun)

    # World
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    wbg = world.node_tree.nodes.get("Background")
    wbg.inputs["Color"].default_value = (0.06, 0.06, 0.07, 1.0)
    wbg.inputs["Strength"].default_value = 0.4

    # Render
    scene = bpy.context.scene
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.use_gtao = True
    except Exception:
        pass

    print(f"[Tilemap Mockup] Placed {sum(counts.values())} modules")
    print(f"  By type: {counts}")
    if skipped:
        print(f"  Skipped (unknown modules): {set(skipped)}")
    return counts, skipped


if __name__ == "__main__":
    assemble(JSON_PATH)
