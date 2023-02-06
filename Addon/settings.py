import bpy
from bpy.types import Operator, AddonPreferences, UILayout
from bpy.props import StringProperty
import os


class BlenderUmapPreferences(AddonPreferences): # TODO: Finished it
    bl_idname = __package__

    filepath: StringProperty(
        name="Custom exporter",
        description="Path to custom exporter",
        subtype='FILE_PATH',
        default=""
    )

    def draw(self, context: bpy.types.Context):
        layout: UILayout = self.layout
        layout.prop(self, "filepath")
        fp = context.preferences.addons[__package__].preferences.get("filepath")
        if fp is not None and fp != "" and not os.path.exists(fp):
            layout.label(text="Cannot find Exporter", icon='ERROR')


class OBJECT_OT_blenderUmap_prefs(Operator):
    bl_idname = "object.blenderumap_prefs"
    bl_label = "BlenderUmap Preferences"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # preferences = context.preferences
        # addon_prefs = preferences.addons[__name__].preferences

        return {'FINISHED'}

classes = (BlenderUmapPreferences, OBJECT_OT_blenderUmap_prefs)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
