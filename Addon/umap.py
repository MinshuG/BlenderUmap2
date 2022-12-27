"""
BlenderUmap v0.4.1
(C) amrsatrio. All rights reserved.
"""
import bpy
import json
import os
import time
from io_import_scene_unreal_psa_psk_280 import pskimport
from math import *
from .piana import *

# ---------- END INPUTS, DO NOT MODIFY ANYTHING BELOW UNLESS YOU NEED TO ----------
def import_umap(processed_map_path: str,
                into_collection: bpy.types.Collection, data_dir: str, reuse_maps: bool, reuse_meshes: bool, use_cube_as_fallback: bool, tex_shader) -> bpy.types.Object:
    map_name = processed_map_path[processed_map_path.rindex("/") + 1:]
    map_collection = bpy.data.collections.get(map_name)

    if reuse_maps and map_collection:
        return place_map(map_collection, into_collection)

    map_collection = bpy.data.collections.new(map_name)
    map_collection_inst = place_map(map_collection, into_collection)
    map_scene = bpy.data.scenes.get(map_collection.name) or bpy.data.scenes.new(map_collection.name)
    map_scene.collection.children.link(map_collection)
    map_layer_collection = map_scene.view_layers[0].layer_collection.children[map_collection.name]

    with open(os.path.join(data_dir, "jsons" + processed_map_path + ".processed.json")) as file:
        comps = json.loads(file.read())

    blights_exist = False
    if os.path.exists(os.path.join(data_dir, "jsons" + processed_map_path + ".lights.processed.json")):
        with open(os.path.join(data_dir, "jsons" + processed_map_path + ".lights.processed.json")) as file:
            lights = json.loads(file.read())
        blights_exist = True

    for comp_i, comp in enumerate(comps):
        # guid = comp[0]
        name = comp[1]
        mesh_path = comp[2]
        mats = comp[3]
        texture_data = comp[4]
        location = comp[5] or [0, 0, 0]
        rotation = comp[6] or [0, 0, 0]
        scale = comp[7] or [1, 1, 1]
        child_comps = comp[8]
        light_index = comp[9] if blights_exist else -1

        # if name is bigger than 50 (58 is blender limit) than hash it and use it as name
        if len(name) > 50:
            name = name[:40] + f"_{abs(string_hash_code(name)):08x}"

        print("\nActor %d of %d: %s" % (comp_i + 1, len(comps), name))

        def apply_ob_props(ob: bpy.types.Object, new_name: str = name) -> bpy.types.Object:
            ob.name = new_name
            ob.location = [location[0] * 0.01, location[1] * -0.01, location[2] * 0.01]
            ob.rotation_mode = 'XYZ'
            ob.rotation_euler = [radians(rotation[2]), radians(-rotation[0]), radians(-rotation[1])]
            ob.scale = scale
            return ob

        def new_object(data: bpy.types.Mesh = None):
            ob = apply_ob_props(bpy.data.objects.new(name, data or bpy.data.meshes["__fallback" if use_cube_as_fallback else "__empty"]), name)
            bpy.context.collection.objects.link(ob)
            bpy.context.view_layer.objects.active = ob

            if light_index != -1:
                for light in lights[light_index]["Props"]:
                    l = create_light(light, map_collection)
                    l.parent = ob

        if child_comps and len(child_comps) > 0:
            for i, child_comp in enumerate(child_comps):
                apply_ob_props(
                    import_umap(child_comp, map_collection, data_dir, reuse_maps, reuse_meshes, use_cube_as_fallback, tex_shader),
                    name if i == 0 else ("%s_%d" % (name, i)))

            continue

        bpy.context.window.scene = map_scene
        bpy.context.view_layer.active_layer_collection = map_layer_collection

        if not mesh_path:
            print("WARNING: No mesh, defaulting to fallback mesh")
            new_object()
            continue

        if mesh_path.startswith("/"):
            mesh_path = mesh_path[1:]

        key = os.path.basename(mesh_path)
        td_suffix = ""

        if mats and len(mats) > 0:
            key += f"_{abs(string_hash_code(';'.join(mats.keys()))):08x}"
        if texture_data and len(texture_data) > 0:
            td_suffix = f"_{abs(string_hash_code(';'.join([list(it.values())[0] if it else '' for it in texture_data]))):08x}"
            key += td_suffix

        existing_mesh = bpy.data.meshes.get(key) if reuse_meshes else None

        if existing_mesh:
            new_object(existing_mesh)
            continue

        full_mesh_path = os.path.join(data_dir, mesh_path)
        if os.path.exists(full_mesh_path + ".psk"):
            full_mesh_path += ".psk"
        elif os.path.exists(full_mesh_path + ".pskx"):
            full_mesh_path += ".pskx"

        if os.path.exists(full_mesh_path) and pskimport(full_mesh_path, bpy.context, bReorientBones=True):
            imported = bpy.context.active_object
            apply_ob_props(imported)
            imported.data.name = key
            bpy.ops.object.shade_smooth()

            if light_index != -1:
                for light in lights[light_index]["Props"]:
                    l = create_light(light, map_collection)
                    l.parent = imported

            for m_idx, (m_path, m_textures) in enumerate(mats.items()):
                if m_textures:
                    import_material(imported, m_idx, m_path, td_suffix, m_textures, texture_data, tex_shader, data_dir)
        else:
            print("WARNING: Mesh not imported, defaulting to fallback mesh:", full_mesh_path)
            new_object()

    return map_collection_inst

def import_material(ob: bpy.types.Object,
                    m_idx: int,
                    path: str,
                    suffix: str,
                    material_info: dict,
                    tex_data: dict, tex_shader, data_dir) -> bpy.types.Material:
    # .mat is required to prevent conflicts with empty ones imported by PSK/PSA plugin
    m_name = os.path.basename(path + ".mat" + suffix)
    m = bpy.data.materials.get(m_name)

    if not m:
        # TODO this is used for BuildTextureData stuff

        m = bpy.data.materials.new(name=m_name)
        m.use_nodes = True
        tree = m.node_tree

        for node in tree.nodes:
            tree.nodes.remove(node)

        m.use_backface_culling = False
        # m.blend_method = "OPAQUE"
        m.blend_method = "CLIP"

        shader_name = material_info["ShaderName"]
        shader_node_group = create_node_group(shader_name, material_info.get("TextureParams", []), material_info.get("ScalerParams", []), material_info.get("VectorParams", []))

        # spawn the shader into material and connect it to output
        shader_node = tree.nodes.new("ShaderNodeGroup")
        shader_node.node_tree = shader_node_group
        shader_node.location = 0, 0
        shader_node.name = shader_name

        output_node = tree.nodes.new("ShaderNodeOutputMaterial")
        output_node.location = 300, 0
        tree.links.new(shader_node.outputs[0], output_node.inputs[0])

        offset = 0
        for input_name, tex_path in material_info["TextureParams"].items():
            if input_name not in shader_node.inputs: # too big name
                continue
            tex = get_or_load_img(tex_path, data_dir)
            if tex:
                tex_node = tree.nodes.new("ShaderNodeTexImage")
                tex_node.image = tex
                tex_node.location = -300, offset
                tex_node.hide = True
                tree.links.new(tex_node.outputs[0], shader_node.inputs[input_name])

                if tex.depth == 32 and input_name+"_Alpha" in shader_node.inputs: # if we have alpha channel, connect it to alpha input
                    tree.links.new(tex_node.outputs[1], shader_node.inputs[input_name+"_Alpha"])
                    if input_name+"_HasValue" in shader_node.inputs:
                        shader_node.inputs[input_name+"_HasValue"].default_value = 1
                elif input_name+"_Alpha" in shader_node.inputs:
                    shader_node.inputs[input_name+"_Alpha"].default_value = 1
                    if input_name+"_HasValue" in shader_node.inputs:
                        shader_node.inputs[input_name+"_HasValue"].default_value = 0
                offset -= 40

        for input_name, value in material_info["ScalerParams"].items():
            if input_name not in shader_node.inputs:
                continue
            shader_node.inputs[input_name].default_value = value

        # VectorParams (Color)
        for input_name, value in material_info["VectorParams"].items():
            if input_name not in shader_node.inputs:
                continue
            shader_node.inputs[input_name].default_value = hex_to_rgb(value)

        print("Material imported")

    # if m_idx < len(ob.data.materials):
    #     ob.data.materials[m_idx] = m
    found_index = find_mat_index(ob.data.materials, m.name[:-4])  # remove .mat
    if found_index is None:
        if m_idx < len(ob.data.materials):
            ob.data.materials[m_idx] = m
    else:
        ob.data.materials[found_index] = m

    return m

def hex_to_rgb(hex_): # ARGB
    hex_ = "ff" + hex_ if len(hex_) == 6 else hex_
    return tuple(int(hex_[i:i+2], 16)/255 for i in (2, 4, 6, 0))

def create_node_group(name, texture_inputs, scaler_inputs, vector_inputs):
        group = bpy.data.node_groups.get(name)
        if group is None:
            group = bpy.data.node_groups.new(name, 'ShaderNodeTree')
            group.nodes.new('NodeGroupOutput')
            group.nodes.new('NodeGroupInput')
            group.outputs.new('NodeSocketShader', 'Out')

        # scaler_inputs, texture_inputs, vector_inputs = self.scaler_params, self.texture_params, self.vector_params

        for input_name in texture_inputs:
            if group.inputs.get(input_name) is None:
                group.inputs.new('NodeSocketColor', input_name)
                group.inputs[input_name].hide_value = True

        for input_name in scaler_inputs:
            if group.inputs.get(input_name) is None:
                group.inputs.new('NodeSocketFloat', input_name)

        for input_name in vector_inputs:
            if group.inputs.get(input_name) is None:
                group.inputs.new('NodeSocketColor', input_name)

        return group

def find_mat_index(materials, mat_name):
    for i, mat in enumerate(materials):
        if mat.name == mat_name:
            return i
    return None

def place_map(collection: bpy.types.Collection, into_collection: bpy.types.Collection):
    c_inst = bpy.data.objects.new(collection.name, None)
    c_inst.instance_type = 'COLLECTION'
    c_inst.instance_collection = collection
    into_collection.objects.link(c_inst)
    return c_inst

def get_or_load_img(img_path: str, data_dir: str) -> bpy.types.Image:
    name = os.path.basename(img_path)
    existing = bpy.data.images.get(name)

    if existing:
        return existing

    img_path = os.path.join(data_dir, img_path[1:])

    if os.path.exists(img_path + ".tga"):
        img_path += ".tga"
    elif os.path.exists(img_path + ".png"):
        img_path += ".png"
    elif os.path.exists(img_path + ".dds"):
        img_path += ".dds"

    if os.path.exists(img_path):
        loaded = bpy.data.images.load(filepath=img_path)
        loaded.name = name
        loaded.alpha_mode = 'CHANNEL_PACKED'
        return loaded
    else:
        print("WARNING: " + img_path + " not found")
        return None


def cleanup():
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)

    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def string_hash_code(s: str) -> int:
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000

if __name__ == "__main__":
    data_dir = r"C:\Users\satri\Documents\AppProjects\BlenderUmap\run"

    reuse_maps = True
    reuse_meshes = True
    use_cube_as_fallback = True

    start = int(time.time() * 1000.0)

    uvm = bpy.data.node_groups.get("UV Shader Mix")
    tex_shader = bpy.data.node_groups.get("Texture Shader")

    if not uvm or not tex_shader:
        with bpy.data.libraries.load(os.path.join(data_dir, "deps.blend")) as (data_from, data_to):
            data_to.node_groups = data_from.node_groups

        uvm = bpy.data.node_groups.get("UV Shader Mix")
        tex_shader = bpy.data.node_groups.get("Texture Shader")

    # make sure we're on main scene to deal with the fallback objects
    main_scene = bpy.data.scenes.get("Scene") or bpy.data.scenes.new("Scene")
    bpy.context.window.scene = main_scene

    # prepare collection for imports
    import_collection = bpy.data.collections.get("Imported")

    if import_collection:
        bpy.ops.object.select_all(action='DESELECT')

        for obj in import_collection.objects:
            obj.select_set(True)

        bpy.ops.object.delete()
    else:
        import_collection = bpy.data.collections.new("Imported")
        main_scene.collection.children.link(import_collection)

    cleanup()

    # setup fallback cube mesh
    bpy.ops.mesh.primitive_cube_add(size=2)
    fallback_cube = bpy.context.active_object
    fallback_cube_mesh = fallback_cube.data
    fallback_cube_mesh.name = "__fallback"
    bpy.data.objects.remove(fallback_cube)

    # 2. empty mesh
    empty_mesh = bpy.data.meshes.get("__empty", bpy.data.meshes.new("__empty"))

    # do it!
    with open(os.path.join(data_dir, "processed.json")) as file:
        import_umap(json.loads(file.read()), import_collection, data_dir, reuse_maps, reuse_meshes, use_cube_as_fallback, tex_shader)

    # go back to main scene
    bpy.context.window.scene = main_scene
    cleanup()

    print("All done in " + str(int((time.time() * 1000.0) - start)) + "ms")
