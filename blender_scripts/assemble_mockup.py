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

# Module styling — keep keys in sync with index.html MODULES (v2 naming)
#   Naming: [CATEGORY]_[Type]_[Material]
#   Categories: TRN(Terrain), ELV(Elevation), ENV(Environment), BLD(Building), ZON(Zone — v0.4)
MODULE_STYLE = {
    # Base terrain
    "TRN_Base_Grass":     {"height": 1.0, "shape_factor": 1.0, "color": (0.29, 0.60, 0.29)},
    "TRN_Base_Dirt":      {"height": 0.3, "shape_factor": 1.0, "color": (0.48, 0.35, 0.23)},
    "TRN_Base_Stone":     {"height": 1.0, "shape_factor": 1.0, "color": (0.60, 0.60, 0.60)},
    # Elevation (multi-cell platforms / slopes — height > base)
    "ELV_Platform_Stone": {"height": 2.5, "shape_factor": 1.0, "color": (0.35, 0.35, 0.35)},
    # Environment
    "ENV_Tree_Pine":      {"height": 2.5, "shape_factor": 0.4, "color": (0.05, 0.35, 0.10)},
    "ENV_Mount_Peak":     {"height": 6.0, "shape_factor": 1.0, "color": (0.27, 0.29, 0.31)},
    # Buildings
    "BLD_House_Generic":  {"height": 5.0, "shape_factor": 1.0, "color": (0.67, 0.20, 0.20)},
}

# v1 → v2 ID migration (auto-applied at load time so old JSONs still work)
LEGACY_ID_MAP = {
    "block_1m_grass": "TRN_Base_Grass",
    "block_1m_dirt":  "TRN_Base_Dirt",
    "block_1m_stone": "TRN_Base_Stone",
    "block_5m_stone": "ELV_Platform_Stone",
    "tree":           "ENV_Tree_Pine",
    "building_3x3":   "BLD_House_Generic",
    "mountain_5x5":   "ENV_Mount_Peak",
}

# ────────────────────────────────────────────────────────────
# Layer system — per-layer tiny Z offset to avoid Z-fighting between
# coincident bottom faces (e.g. base grass + elevation platform at same cell).
# Layer is derived from module ID prefix.
# ────────────────────────────────────────────────────────────
LAYER_Z_OFFSET = {
    "base":        0.000,   # ground level
    "elevation":   0.001,   # +1 mm above base
    "environment": 0.002,   # +2 mm above base
}

def get_module_layer(module_id):
    if module_id.startswith("TRN_"): return "base"
    if module_id.startswith("ELV_"): return "elevation"
    return "environment"   # ENV_, BLD_, ZON_ (future)


def make_cube_mesh(name, fw, fh, sz, shape_factor=1.0):
    """
    Axis-aligned cuboid with **pivot at footprint bottom-left-bottom corner (0, 0, 0)**.
    Mesh body fills (fw * shape_factor) × (fh * shape_factor) × sz,
    centered within the footprint via inset on X/Y when shape_factor < 1.

    This matches Unreal modular-kit convention: every module's pivot is at the
    corner of its tile, so placing at grid (x, y, z) = move actor to
    (x * tile_uu, y_world * tile_uu, z_layer * tile_uu) with no center offset math.

    Face winding is CCW from outside → outward normals → solid look under
    Unreal back-face culling.
    """
    inset_x = fw * (1.0 - shape_factor) / 2.0
    inset_y = fh * (1.0 - shape_factor) / 2.0
    x0, y0 = inset_x, inset_y
    x1 = x0 + fw * shape_factor
    y1 = y0 + fh * shape_factor
    verts = [
        (x0, y0, 0),  (x1, y0, 0),  (x1, y1, 0),  (x0, y1, 0),     # 0..3 bottom
        (x0, y0, sz), (x1, y0, sz), (x1, y1, sz), (x0, y1, sz),    # 4..7 top
    ]
    # Outward winding (CCW from outside)
    faces = [(3,2,1,0), (4,5,6,7), (1,5,4,0), (2,6,5,1), (3,7,6,2), (0,4,7,3)]
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


def get_or_create_mesh_template(module_id, fw, fh, tile_m, mesh_cache, mat_cache):
    """
    Returns a **shared** mesh datablock per (module_id, footprint).
    All placements of the same module+footprint share one mesh → many objects,
    one underlying mesh.  Memory + .blend file size drops dramatically
    (e.g. 5707 unique meshes → 7 templates).

    Material is attached to the mesh once, so all instances inherit it
    automatically (no per-object material slot).
    """
    key = (module_id, fw, fh)
    cached = mesh_cache.get(key)
    if cached is not None:
        return cached
    style = MODULE_STYLE[module_id]
    mesh = make_cube_mesh(
        f"Tpl_{module_id}_{fw}x{fh}",
        fw * tile_m, fh * tile_m,
        style["height"], style["shape_factor"],
    )
    mat = get_or_create_material(module_id, mat_cache)
    mesh.materials.append(mat)
    mesh_cache[key] = mesh
    return mesh


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
    mesh_cache = {}  # (module_id, fw, fh) → shared mesh datablock
    counts, skipped, migrated = {}, [], 0

    for p in placements:
        module_id = p["module"]
        # Auto-migrate legacy v1 IDs
        if module_id in LEGACY_ID_MAP:
            module_id = LEGACY_ID_MAP[module_id]
            migrated += 1
        if module_id not in MODULE_STYLE:
            skipped.append(module_id)
            continue
        x, y = p["x"], p["y"]
        z_layer = p.get("z", 0)
        fw, fh = p["footprint"]

        # 1) Shared mesh template (all same-module placements reference one mesh)
        mesh = get_or_create_mesh_template(module_id, fw, fh, tile_m, mesh_cache, mat_cache)

        # 2) Per-layer Z offset to mitigate Z-fighting at coincident faces
        layer_name = get_module_layer(module_id)
        z_offset = LAYER_Z_OFFSET[layer_name]

        # 3) Pivot at footprint bottom-left corner (matches Unreal modular-kit pivot)
        #    Image-Y is down → world-Y up: world Y bottom-of-tile = grid_h - y - fh
        obj = bpy.data.objects.new(f"O_{module_id}_{x}_{y}_z{z_layer}", mesh)
        obj.location = (
            x * tile_m,
            (grid_h - y - fh) * tile_m,
            z_layer * tile_m + z_offset,
        )
        mockup_col.objects.link(obj)
        counts[module_id] = counts.get(module_id, 0) + 1

    # Ground plate — sized exactly to the play area (matches Unreal Landscape target).
    # Corner pivot at (0, 0, 0) so it covers world (0,0,-0.05) .. (grid_w, grid_h, 0).
    gw = grid_w * tile_m
    gh = grid_h * tile_m
    ground_mesh = make_cube_mesh("Ground_mesh", gw, gh, 0.05, shape_factor=1.0)
    gmat = bpy.data.materials.new("Mat_Ground")
    gmat.use_nodes = True
    gbsdf = gmat.node_tree.nodes.get("Principled BSDF")
    gbsdf.inputs["Base Color"].default_value = (0.10, 0.10, 0.11, 1.0)
    gbsdf.inputs["Roughness"].default_value = 0.95
    ground_mesh.materials.append(gmat)
    ground = bpy.data.objects.new("Ground", ground_mesh)
    ground.location = (0, 0, -0.05)
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

    ver = data.get("version", 1)
    n_placed = sum(counts.values())
    n_templates = len(mesh_cache)
    print(f"[Tilemap Mockup] Placed {n_placed} modules (schema v{ver})")
    print(f"  Mesh templates: {n_templates}  (shared by {n_placed} instances → "
          f"{n_placed - n_templates} mesh datablocks saved)")
    print(f"  By type: {counts}")
    print(f"  Layer Z-offsets: {LAYER_Z_OFFSET}")
    if migrated:
        print(f"  Auto-migrated {migrated} legacy v1 IDs → v2")
    if skipped:
        print(f"  Skipped (unknown modules): {set(skipped)}")
    return counts, skipped


if __name__ == "__main__":
    assemble(JSON_PATH)
