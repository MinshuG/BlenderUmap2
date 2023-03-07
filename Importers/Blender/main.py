import typing
import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, BoolProperty
import json
import os
from urllib.request import urlopen, Request
import subprocess
import sys

from bpy.types import Context
from .config import Config

try:
    from .umap import import_umap, cleanup
except ImportError:
    from ..umap import import_umap, cleanup

classes = []

def register_class(cls):
    classes.append(cls)
    return cls

def config_file_exists():
    return os.path.isfile(os.path.join(bpy.context.scene.exportPath, "config.json"))

def main(context, onlyimport=False):
    sc = bpy.context.scene
    reuse_maps = sc.reuse_maps
    reuse_meshes = sc.reuse_mesh
    use_cube_as_fallback = sc.use_cube_as_fallback
    data_dir = sc.exportPath
    addon_dir = os.path.dirname(os.path.splitext(__file__)[0])

    if not onlyimport:
        Config().dump(sc.exportPath)
        exporter = os.path.join(addon_dir, "BlenderUmap")
        addon_prefs = context.preferences.addons[__package__].preferences
        if addon_prefs.filepath != "":
            exporter = addon_prefs.filepath
        if sys.platform == "win32" and not exporter.endswith(".exe"):
            executable = exporter.replace(r"\\", "/") + ".exe"
            cmd = []
        else:
            executable = exporter.replace(r"\\", "/")
            cmd = []

        env_vars = os.environ.copy()
        env_vars["PATH"] = f"{sc.exportPath};" + env_vars["PATH"]

        subprocess.run(
            cmd,
            executable=executable,
            capture_output=False,
            shell=False,
            check=True,
            cwd=data_dir.replace(r"\\", "/"),
            env=env_vars
        )

    uvm = bpy.data.node_groups.get("UV Shader Mix")
    tex_shader = bpy.data.node_groups.get("Texture Shader")

    if not uvm or not tex_shader:
        create_node_groups()
        # with bpy.data.libraries.load(os.path.join(addon_dir, "deps.blend")) as (data_from, data_to):
        #     data_to.node_groups = data_from.node_groups

        uvm = bpy.data.node_groups.get("UV Shader Mix")
        tex_shader = bpy.data.node_groups.get("Texture Shader")

    # make sure we're on main scene to deal with the fallback objects
    main_scene = bpy.data.scenes.get("Scene") or bpy.data.scenes.new("Scene")
    bpy.context.window.scene = main_scene

    # prepare collection for imports
    import_collection = bpy.data.collections.get("Imported")

    if import_collection:
        bpy.ops.object.select_all(action="DESELECT")

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
        import time
        stime = time.time()
        import_umap(
            json.loads(file.read()),
            import_collection,
            data_dir,
            reuse_maps,
            reuse_meshes,
            use_cube_as_fallback,
            tex_shader,
        )
        print(f"Imported in {time.time() - stime} seconds")

    # go back to main scene
    bpy.context.window.scene = main_scene
    cleanup()


class UE4Version:  # idk why
    """Supported UE4 Versions"""

    Versions = (
        ("GAME_UE4_0", "GAME_UE4_0", ""),
        ("GAME_UE4_1", "GAME_UE4_1", ""),
        ("GAME_UE4_2", "GAME_UE4_2", ""),
        ("GAME_UE4_3", "GAME_UE4_3", ""),
        ("GAME_UE4_4", "GAME_UE4_4", ""),
        ("GAME_UE4_5", "GAME_UE4_5", ""),
        ("GAME_UE4_6", "GAME_UE4_6", ""),
        ("GAME_UE4_7", "GAME_UE4_7", ""),
        ("GAME_UE4_8", "GAME_UE4_8", ""),
        ("GAME_UE4_9", "GAME_UE4_9", ""),
        ("GAME_UE4_10", "GAME_UE4_10", ""),
        ("GAME_UE4_11", "GAME_UE4_11", ""),
        ("GAME_UE4_12", "GAME_UE4_12", ""),
        ("GAME_UE4_13", "GAME_UE4_13", ""),
        ("GAME_UE4_14", "GAME_UE4_14", ""),
        ("GAME_UE4_15", "GAME_UE4_15", ""),
        ("GAME_UE4_16", "GAME_UE4_16", ""),
        ("GAME_UE4_17", "GAME_UE4_17", ""),
        ("GAME_UE4_18", "GAME_UE4_18", ""),
        ("GAME_UE4_19", "GAME_UE4_19", ""),
        ("GAME_UE4_20", "GAME_UE4_20", ""),
        ("GAME_UE4_21", "GAME_UE4_21", ""),
        ("GAME_UE4_22", "GAME_UE4_22", ""),
        ("GAME_UE4_23", "GAME_UE4_23", ""),
        ("GAME_UE4_24", "GAME_UE4_24", ""),
        ("GAME_UE4_25", "GAME_UE4_25", ""),
        ("GAME_UE4_26", "GAME_UE4_26", ""),
        ("GAME_UE4_27", "GAME_UE4_27", ""),
        ("GAME_UE5_0", "GAME_UE5_0", ""),
        ("GAME_UE5_1", "GAME_UE5_1", ""),
        ("GAME_UE5_2", "GAME_UE5_2", ""),
    )

@register_class
class VIEW3D_MT_AdditionalOptions(bpy.types.Menu):
    bl_label = "Additional Options"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="Fortnite:")
        col.operator("umap.fillfortnitekeys", depress=False)
        col.operator("umap.downloadmappings", depress=False)

try:
    from .__version__ import __version__
    version = ".".join(__version__.split(".")[:2])
except:
    version = "0"

# UI
class BlenderUmapPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Umap"
    bl_context = "objectmode"


@register_class
class VIEW3D_PT_BlenderUmapMain(BlenderUmapPanel):
    """Creates a Panel in Properties(N)"""

    bl_label = f"BlenderUmap2 (v{version})"
    bl_idname = "VIEW3D_PT_BlenderUmapMain"

    bpy.types.Scene.ue4_versions = bpy.props.EnumProperty(
        name="UE Version", items=UE4Version.Versions
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True, heading="Exporter Settings:")

        if config_file_exists():
            col.operator(
                "umap.load_configs", icon="FILE_REFRESH", text="Reload Last Used Config"
            )

        col.prop(context.scene, "Game_Path")
        col.prop(context.scene, "aeskey")
        col.prop(context.scene, "exportPath")
        col.label(text="Dynamic Keys:")

        row = col.row(align=True)

        col2 = row.column(align=True)
        col2.template_list("VIEW3D_UL_DPKLIST", "VIEW3D_UL_dpklist", context.scene, "dpklist", context.scene, "list_index", rows=3)
        row.separator()

        col3 = row.column(align=True)
        col3.operator("dpklist.new_item", icon="ADD", text="")
        col3.operator("dpklist.delete_item", icon="REMOVE", text="")
        col3.separator()
        col3.menu("VIEW3D_MT_AdditionalOptions", icon="DOWNARROW_HLT", text="")
        col.separator()

        if context.scene.list_index >= 0 and context.scene.dpklist:
            item = context.scene.dpklist[context.scene.list_index]
            col.prop(item, "pakname")
            col.prop(item, "daeskey")
            col.prop(item, "guid")
            col.separator()

        col.prop(context.scene, "package")

        if not context.scene.bUseCustomEngineVer:
            col.prop(context.scene, "ue4_versions")
        col.prop(context.scene, "bUseCustomEngineVer")
        if context.scene.bUseCustomEngineVer:
            col.prop(context.scene, "customEngineVer")

        col.prop(context.scene, "readmats")
        col.prop(context.scene, "bExportToDDSWhenPossible")
        col.prop(context.scene, "bExportBuildingFoundations")
        col.prop(context.scene, "bdumpassets")
        col.prop(context.scene, "ObjectCacheSize")
        col.separator()

        col = col.column(align=True, heading="Importer Settings:")
        col.prop(context.scene, "reuse_maps", text="Reuse Maps")
        col.prop(context.scene, "reuse_mesh", text="Reuse Meshes")
        col.prop(context.scene, "use_cube_as_fallback")

        export_path_exists = os.path.exists(bpy.context.scene.exportPath)
        game_path_exists = os.path.exists(context.scene.Game_Path)
        import_col = col.column(align=True)
        import_col.enabled = game_path_exists and export_path_exists
        if not game_path_exists:
            import_col.label(text="Game Path must exist", icon="ERROR")
        if not export_path_exists:
            import_col.label(text="Export Path must exist", icon="ERROR")
        import_col.operator(
            "umap.import",
            text="Import",
            icon="IMPORT",
        )

        if os.path.exists(os.path.join(context.scene.exportPath, "processed.json")):
            col.operator("umap.onlyimport", text="Only Import", icon="IMPORT")

        if version == "0":
            col.operator("umap.dumpconfig", text="Dump Config", icon="DOWNARROW_HLT")


@register_class
class VIEW3D_PT_BlenderUmapTextureMappings(BlenderUmapPanel):
    """Creates a Panel in Properties(N)"""

    bl_label = f"Texture Mappings"
    bl_parent_id = "VIEW3D_PT_BlenderUmapMain"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.separator()
        col = layout.grid_flow(align=True, even_columns=True, even_rows=True)

        for i in range(1, 5):  # 4UVs
            if i != 1:
                col.separator()
            col.label(text=f"UV Map {i}", icon="GROUP_UVS")
            for t in ["Diffuse", "Normal", "Specular", "Emission", "Mask"]:
                col.prop(context.scene, f"{t}_{i}".lower())


@register_class
class VIEW3D_PT_BlenderUmapAdvancedOptions(BlenderUmapPanel):
    bl_label = f"Advanced Options"
    bl_parent_id = "VIEW3D_PT_BlenderUmapMain"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # warning only change if you know what you are doing
        layout.label(text="Warning: Only change if you know what you are doing", icon="ERROR")

        col = layout.column(align=True)
        col.label(text="Options Overrides:")

        col.prop(context.scene, "bUseCustomOptions")
        if context.scene.bUseCustomOptions:
            row = col.row(align=True)

            col2 = row.column(align=True)
            col2.template_list("VIEW3D_UL_CustomOptions", "custom_options_list", context.scene,
                            "custom_options", context.scene, "custom_options_index", rows=3)

            row.separator()

            col3 = row.column(align=True)
            col3.operator("custom_options.new_item", icon="ADD", text="")
            col3.operator("custom_options.delete_item", icon="REMOVE", text="")


@register_class
class CustomOptionsListItem(bpy.types.PropertyGroup):
    """Group of properties representing an item in the list."""

    name: StringProperty(
           name="Name",
           description="",
           default="key")

    value: BoolProperty(
           name="True",
           description="",
           default=False)

@register_class
class VIEW3D_UL_CustomOptions(bpy.types.UIList):
    """Custom Options List"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            split = layout.split(factor=0.6)
            split.prop(item, "name", text="", emboss=True)
            split.separator()
            split.prop(item, "value", text= "True" if item.value else "False", toggle=0, emboss=True)
        elif self.layout_type in {"GRID"}:
            pass

@register_class
class CustomOptions_OT_NewItem(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "custom_options.new_item"
    bl_label = "Add a new item"

    def execute(self, context):
        context.scene.custom_options.add()
        context.scene.custom_options_index + 1
        return {"FINISHED"}

@register_class
class CustomOptions_OT_DeleteItem(bpy.types.Operator):
    """Delete the selected item from the list."""

    bl_idname = "custom_options.delete_item"
    bl_label = "Deletes an item"

    @classmethod
    def poll(cls, context):
        return len(context.scene.custom_options) > 0

    def execute(self, context):
        custom_options = context.scene.custom_options
        index = context.scene.custom_options_index
        custom_options.remove(index)
        context.scene.custom_options_index = min(max(0, index - 1), len(custom_options) - 1)
        return {"FINISHED"}

@register_class
class VIEW_PT_UmapOperator(bpy.types.Operator):
    """Import Umap"""

    bl_idname = "umap.import"
    bl_label = "Umap Exporter"

    def execute(self, context):
        main(context)
        return {"FINISHED"}

@register_class
class VIEW_PT_UmapOnlyImport(bpy.types.Operator):
    """Only import already exported umap"""

    bl_idname = "umap.onlyimport"
    bl_label = "Umap Import"

    def execute(self, context):
        main(context, True)
        return {"FINISHED"}

# dump config operator
@register_class
class VIEW_PT_UmapDumpConfig(bpy.types.Operator):
    """Dump config to file"""

    bl_idname = "umap.dumpconfig"
    bl_label = "Dump Config"

    @classmethod
    def poll(cls, context):
        return config_file_exists()

    def execute(self, context):
        print("Dumping config to file")
        Config().dump(context.scene.exportPath)
        return {"FINISHED"}

@register_class
class Fortnite(bpy.types.Operator):
    bl_idname = "umap.fillfortnitekeys"
    bl_label = "Fill Fortnite AES keys"
    bl_description = "Automatically fill AES Key/s for latest Fortnite version"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3"
        }

        req = Request(url="https://fortnite-api.com/v2/aes", headers=headers)
        r = urlopen(req)

        if r.status != 200:
            self.report({"ERROR"}, "API returned {r.status} status code")
            return {"CANCELLED"}

        raw_data = r.read().decode(r.info().get_param("charset") or "utf-8")
        try:
            data = json.loads(raw_data)["data"]
        except Exception as e:
            self.report({"ERROR"}, "Error loading JSON \n{e}")
            return {"CANCELLED"}

        main_key = data.get("mainKey", None)
        if main_key is None:
            self.report({"ERROR"}, "failed get main key")
        else:
            bpy.context.scene.aeskey = (
                main_key if main_key.startswith("0x") else f"0x{main_key}"
            )

        dpklist = context.scene.dpklist
        context.scene.list_index = len(dpklist)
        index = context.scene.list_index

        for _ in bpy.context.scene.dpklist:
            dpklist.remove(index)
            index = index - 1

        context.scene.list_index = 0
        for x in data["dynamicKeys"]:
            PakPath, Guid, AESKey = x.values()
            Pakname = os.path.basename(PakPath)
            context.scene.dpklist.add()
            item = context.scene.dpklist[index]
            item.pakname = Pakname
            item.guid = Guid
            item.daeskey = AESKey if AESKey.startswith("0x") else "0x" + AESKey
            index = index + 1

        return {"FINISHED"}

@register_class
class FortniteMappings(bpy.types.Operator):
    bl_idname = "umap.downloadmappings"
    bl_label = "Download mappings for Fortnite"

    @classmethod
    def poll(cls, context):
        return True  # TODO check if machine is connected to internet

    def execute(self, context):
        self.check_mappings()
        return {"FINISHED"}

    def check_mappings(self):
        path = bpy.context.scene.exportPath
        mappings_path = os.path.join(path, "mappings")
        if not os.path.exists(mappings_path):
            os.makedirs(mappings_path)
            self.dl_mappings(mappings_path)
            return True
        try:
            self.dl_mappings(mappings_path)
        except:
            pass
        return True

    def dl_mappings(self, path):
        ENDPOINT = "https://fortnitecentral.genxgames.gg/api/v1/mappings"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        }

        req = Request(url=ENDPOINT, headers=headers)
        r = urlopen(req)
        datas = json.loads(r.read().decode(r.info().get_param("charset") or "utf-8"))

        if r.status != 200:
            self.report({"ERROR"}, "API returned {r.status} status code")
            return {"CANCELLED"}

        if len(datas) == 0:
            self.report({"ERROR"}, "no mappings found in response")
            return {"CANCELLED"}

        data = datas[0]
        for data_ in datas:
            if data_["meta"]["platform"] == "Android":
                data = data_
                break

        import hashlib
        filepath = os.path.join(path, data["fileName"])
        if not os.path.exists(filepath) or data["hash"] != hashlib.sha1(open(filepath, "rb").read()).hexdigest():
            with open(filepath, "wb") as f:
                downfile = urlopen(Request(url=data["url"], headers=headers))
                print("Downloading", data["fileName"])
                f.write(downfile.read(downfile.length))
        return True

@register_class
class ListItem(bpy.types.PropertyGroup):
    pakname: StringProperty(
        name="Pak Name", description="Name of the Pak file. (Optional)", default=""
    )
    daeskey: StringProperty(
        name="AES Key", description="AES key for the Pak file.", default=""
    )
    guid: StringProperty(
        name="Encryption Guid",
        description="Encryption Guid for the Pak file.",
        default="",
        maxlen=32,
    )

@register_class
class VIEW3D_UL_DPKLIST(bpy.types.UIList):
    """Dynamic Pak AES key List"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            if item.pakname == "":
                layout.label(text=f"{item.guid}:{item.daeskey}")
            else:
                layout.label(text=f"{item.pakname}:{item.daeskey}")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            if item.pakname == "":
                layout.label(text=f"{item.guid}")
            else:
                layout.label(text=item.pakname)

@register_class
class DPKLIST_OT_NewItem(bpy.types.Operator):
    """Add a new item to the list."""

    bl_idname = "dpklist.new_item"
    bl_label = "Add a new item"

    def execute(self, context):
        context.scene.dpklist.add()
        context.scene.list_index + 1
        return {"FINISHED"}

@register_class
class DPKLIST_OT_DeleteItem(bpy.types.Operator):
    """Delete the selected item from the list."""

    bl_idname = "dpklist.delete_item"
    bl_label = "Deletes an item"

    @classmethod
    def poll(cls, context):
        return len(context.scene.dpklist) > 0

    def execute(self, context):
        dpklist = context.scene.dpklist
        index = context.scene.list_index
        dpklist.remove(index)
        context.scene.list_index = min(max(0, index - 1), len(dpklist) - 1)
        return {"FINISHED"}

@register_class
class LOAD_Configs(bpy.types.Operator):
    bl_label = "Load Config from File"
    bl_idname = "umap.load_configs"
    bl_description = "Load Configs from File"

    def execute(
        self, context: "Context"
    ) -> typing.Union[typing.Set[str], typing.Set[int]]:
        try:
            Config().load()
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


def create_node_groups():
    # create UV shader mix node group, credits to @FriesFX
    uvm = bpy.data.node_groups.get("UV Shader Mix")

    if not uvm:
        uvm = bpy.data.node_groups.new(name="UV Shader Mix", type="ShaderNodeTree")
        # for node in tex_shader.nodes: tex_shader.nodes.remove(node)

        mix_1 = uvm.nodes.new("ShaderNodeMixShader")
        mix_2 = uvm.nodes.new("ShaderNodeMixShader")
        mix_3 = uvm.nodes.new("ShaderNodeMixShader")
        mix_4 = uvm.nodes.new("ShaderNodeMixShader")
        mix_1.location = [-500, 300]
        mix_2.location = [-300, 300]
        mix_3.location = [-100, 300]
        mix_4.location = [100, 300]
        uvm.links.new(mix_1.outputs[0], mix_2.inputs[1])
        uvm.links.new(mix_2.outputs[0], mix_3.inputs[1])
        uvm.links.new(mix_3.outputs[0], mix_4.inputs[1])

        x = -1700
        y = 700
        sep = uvm.nodes.new("ShaderNodeSeparateRGB")
        sep.location = [x + 200, y - 200]

        m1_1 = uvm.nodes.new("ShaderNodeMath")
        m1_2 = uvm.nodes.new("ShaderNodeMath")
        m1_3 = uvm.nodes.new("ShaderNodeMath")
        m1_1.location = [x + 400, y]
        m1_2.location = [x + 400, y - 200]
        m1_3.location = [x + 400, y - 400]
        m1_1.operation = "LESS_THAN"
        m1_2.operation = "LESS_THAN"
        m1_3.operation = "LESS_THAN"
        m1_1.inputs[1].default_value = 1.420
        m1_2.inputs[1].default_value = 1.720
        m1_3.inputs[1].default_value = 3.000
        uvm.links.new(sep.outputs[0], m1_1.inputs[0])
        uvm.links.new(sep.outputs[0], m1_2.inputs[0])
        uvm.links.new(sep.outputs[0], m1_3.inputs[0])

        add_1_2 = uvm.nodes.new("ShaderNodeMath")
        add_1_2.location = [x + 600, y - 300]
        add_1_2.operation = "ADD"
        uvm.links.new(m1_1.outputs[0], add_1_2.inputs[0])
        uvm.links.new(m1_2.outputs[0], add_1_2.inputs[1])

        m2_1 = uvm.nodes.new("ShaderNodeMath")
        m2_2 = uvm.nodes.new("ShaderNodeMath")
        m2_3 = uvm.nodes.new("ShaderNodeMath")
        m2_4 = uvm.nodes.new("ShaderNodeMath")
        m2_1.location = [x + 800, y]
        m2_2.location = [x + 800, y - 200]
        m2_3.location = [x + 800, y - 400]
        m2_4.location = [x + 800, y - 600]
        m2_1.operation = "ADD"
        m2_2.operation = "SUBTRACT"
        m2_3.operation = "SUBTRACT"
        m2_4.operation = "LESS_THAN"
        m2_1.use_clamp = True
        m2_2.use_clamp = True
        m2_3.use_clamp = True
        m2_4.use_clamp = True
        m2_1.inputs[1].default_value = 0
        m2_4.inputs[1].default_value = 0.700
        uvm.links.new(m1_1.outputs[0], m2_1.inputs[0])
        uvm.links.new(m1_2.outputs[0], m2_2.inputs[0])
        uvm.links.new(m1_1.outputs[0], m2_2.inputs[1])
        uvm.links.new(m1_3.outputs[0], m2_3.inputs[0])
        uvm.links.new(add_1_2.outputs[0], m2_3.inputs[1])
        uvm.links.new(m1_3.outputs[0], m2_4.inputs[0])

        uvm.links.new(m2_1.outputs[0], mix_1.inputs[0])
        uvm.links.new(m2_2.outputs[0], mix_4.inputs[0])
        uvm.links.new(m2_3.outputs[0], mix_2.inputs[0])
        uvm.links.new(m2_4.outputs[0], mix_3.inputs[0])

        # I/O
        g_in = uvm.nodes.new("NodeGroupInput")
        g_out = uvm.nodes.new("NodeGroupOutput")
        g_in.location = [-1700, 220]
        g_out.location = [300, 300]
        uvm.links.new(g_in.outputs[0], sep.inputs[0])
        uvm.links.new(g_in.outputs[1], mix_1.inputs[2])
        uvm.links.new(g_in.outputs[2], mix_2.inputs[2])
        uvm.links.new(g_in.outputs[3], mix_3.inputs[2])
        uvm.links.new(g_in.outputs[4], mix_4.inputs[2])
        uvm.links.new(mix_4.outputs[0], g_out.inputs[0])

    # create texture shader node group, credits to @Lucas7yoshi
    tex_shader = bpy.data.node_groups.get("Texture Shader")

    if not tex_shader:
        tex_shader = bpy.data.node_groups.new(
            name="Texture Shader", type="ShaderNodeTree"
        )
        # for node in tex_shader.nodes: tex_shader.nodes.remove(node)

        g_in = tex_shader.nodes.new("NodeGroupInput")
        g_out = tex_shader.nodes.new("NodeGroupOutput")
        g_in.location = [-700, 0]
        g_out.location = [350, 300]

        principled_bsdf = tex_shader.nodes.new(type="ShaderNodeBsdfPrincipled")
        principled_bsdf.location = [50, 300]
        tex_shader.links.new(principled_bsdf.outputs[0], g_out.inputs[0])

        # diffuse
        tex_shader.links.new(g_in.outputs[0], principled_bsdf.inputs["Base Color"])

        # normal
        norm_y = -1
        norm_curve = tex_shader.nodes.new("ShaderNodeRGBCurve")
        norm_map = tex_shader.nodes.new("ShaderNodeNormalMap")
        norm_curve.location = [-500, norm_y]
        norm_map.location = [-200, norm_y]
        norm_curve.mapping.curves[1].points[0].location = [0, 1]
        norm_curve.mapping.curves[1].points[1].location = [1, 0]
        tex_shader.links.new(g_in.outputs[1], norm_curve.inputs[1])
        tex_shader.links.new(norm_curve.outputs[0], norm_map.inputs[1])
        tex_shader.links.new(norm_map.outputs[0], principled_bsdf.inputs["Normal"])
        tex_shader.inputs[1].default_value = [0.5, 0.5, 1, 1]

        # specular
        spec_y = 140
        spec_separate_rgb = tex_shader.nodes.new("ShaderNodeSeparateRGB")
        spec_separate_rgb.location = [-200, spec_y]
        tex_shader.links.new(g_in.outputs[2], spec_separate_rgb.inputs[0])
        tex_shader.links.new(
            spec_separate_rgb.outputs[0], principled_bsdf.inputs["Specular"]
        )
        tex_shader.links.new(
            spec_separate_rgb.outputs[1], principled_bsdf.inputs["Metallic"]
        )
        tex_shader.links.new(
            spec_separate_rgb.outputs[2], principled_bsdf.inputs["Roughness"]
        )
        tex_shader.inputs[2].default_value = [0.5, 0, 0.5, 1]

        # emission
        tex_shader.links.new(g_in.outputs[3], principled_bsdf.inputs["Emission"])
        tex_shader.inputs[3].default_value = [0, 0, 0, 1]

        # alpha
        alpha_separate_rgb = tex_shader.nodes.new("ShaderNodeSeparateRGB")
        alpha_separate_rgb.location = [-200, -180]
        tex_shader.links.new(g_in.outputs[4], alpha_separate_rgb.inputs[0])
        tex_shader.links.new(
            alpha_separate_rgb.outputs[0], principled_bsdf.inputs["Alpha"]
        )
        tex_shader.inputs[4].default_value = [1, 0, 0, 1]

        tex_shader.inputs[0].name = "Diffuse"
        tex_shader.inputs[1].name = "Normal"
        tex_shader.inputs[2].name = "Specular"
        tex_shader.inputs[3].name = "Emission"
        tex_shader.inputs[4].name = "Alpha"

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dpklist = CollectionProperty(type=ListItem)
    bpy.types.Scene.list_index = IntProperty(name="", default=0)

    bpy.types.Scene.custom_options = CollectionProperty(type=CustomOptionsListItem)
    bpy.types.Scene.custom_options_index = IntProperty(name="", default=0)

    # bool use custom options
    bpy.types.Scene.bUseCustomOptions = BoolProperty(
        name="Use Options Overrides",
        description="Use Custom Options Overrides",
        default=False,
        subtype="NONE",
    )

    bpy.types.Scene.Game_Path = StringProperty(
        name="Game Path",
        description="Path to the Paks folder",
        subtype="DIR_PATH",
    )

    bpy.types.Scene.aeskey = StringProperty(
        name="Main AES Key",
        description="AES key",
        subtype="NONE",
    )

    bpy.types.Scene.package = StringProperty(
        name="Package",
        description="Umap to export",
        subtype="NONE",
    )

    bpy.types.Scene.bUseCustomEngineVer = BoolProperty(
        name="Use UE Custom Version",
        description="Use Custom Unreal Engine Version",
        default=False,
        subtype="NONE",
    )

    bpy.types.Scene.customEngineVer = StringProperty(
        name="Custom Engine Version", description="Custom UE4 Version"
    )

    bpy.types.Scene.readmats = BoolProperty(
        name="Read Materials",
        description="Import Materials",
        default=True,
        subtype="NONE",
    )

    bpy.types.Scene.bExportToDDSWhenPossible = BoolProperty(
        name="Export DDS When Possible",
        description="Export textures to .dds format",
        default=False,
        subtype="NONE",
    )

    bpy.types.Scene.bExportBuildingFoundations = BoolProperty(
        name="Export Building Foundations",
        description="You can turn off exporting sub-buildings in large POIs if you want to quickly port the base POI structures, by setting this to false",
        default=True,
        subtype="NONE",
    )

    bpy.types.Scene.bdumpassets = BoolProperty(
        name="Dump Assets",
        description="Save assets as JSON format",
        default=False,
        subtype="NONE",
    )

    bpy.types.Scene.ObjectCacheSize = IntProperty(
        name="Object Cache Size",
        description="Configure the object loader cache size to tune the performance, or set to 0 to disable",
        default=100,
        min=0,
    )

    bpy.types.Scene.reuse_maps = BoolProperty(
        name="Reuse Maps",
        description="Reuse already imported map rather then importing them again",
        default=True,
        subtype="NONE",
    )

    bpy.types.Scene.reuse_mesh = BoolProperty(
        name="Reuse Meshes",
        description="Reuse already imported meshes rather then importing them again",
        default=True,
        subtype="NONE",
    )

    bpy.types.Scene.use_cube_as_fallback = BoolProperty(
        name="Use Cube as Fallback Mesh",
        description="Use cube if mesh is not found",
        default=True,
        subtype="NONE",
    )

    bpy.types.Scene.exportPath = StringProperty(
        name="Export Path",
        description="Path to Export Folder",
        subtype="DIR_PATH",
    )

    for i in range(1, 5):  # 4UVs
        for t in ["Diffuse", "Normal", "Specular", "Emission", "Mask"]:
            prop_to_set = StringProperty(
                name=t,
                description=f"Parameter value name of {t.lower()} texture",
                default="",
            )
            setattr(bpy.types.Scene, f"{t}_{i}".lower(), prop_to_set)


def unregister():

    for cls in classes:
        bpy.utils.unregister_class(cls)

    sc = bpy.types.Scene
    del sc.Game_Path
    del sc.aeskey
    del sc.package
    del sc.readmats
    del sc.bExportToDDSWhenPossible
    del sc.bExportBuildingFoundations
    del sc.bdumpassets
    del sc.ObjectCacheSize
    del sc.reuse_maps
    del sc.reuse_mesh
    del sc.use_cube_as_fallback
    del sc.exportPath
    del sc.bUseCustomOptions


if __name__ == "__main__":
    register()
