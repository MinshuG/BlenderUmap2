import bpy
from mathutils import Vector, Quaternion
from math import cos, pi, radians, degrees, atan2, asin
import mathutils

def get_rgb_255(pv: dict) -> tuple:
    return (
        srgb2lin(pv["R"] / 255),
        srgb2lin(pv["G"] / 255),
        srgb2lin(pv["B"] / 255),
        srgb2lin(pv["A"] / 255)
    )

def get_light_type(object):
    if "Point" in object["Type"]:
        return "POINT"
    if "Spot" in object["Type"]:
        return "SPOT"
    if "RectLightComponent" in object["Type"]:
        return "AREA"

def game_to_blender_rotations(x, y, z):
    """
    Unreal to Blender rotations
    rotation conversion by hatsune miku
    POGGERS CODE WAOOOO
    """

    def quaternion_to_euler(quaternion):
        w, y, x, z = quaternion
        roll = atan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y))
        pitch = asin(max(min(2 * (w*y - z*x), 1), -1 ))
        yaw = atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
        return(roll, pitch, yaw)

    # lol do this because
    euler = mathutils.Euler((
        radians(x),
        radians(y),
        radians(z)
    ))

    quat = euler.to_quaternion()

    # do a little trolling
    quat = mathutils.Quaternion([quat.w, quat.x, quat.y, -quat.z])

    x, y, z = quaternion_to_euler(quat)

    x = degrees(-x) - 90
    y = degrees(-y)
    z = degrees(z) - 270

    return mathutils.Euler((radians(x), radians(y), radians(z)))

def set_properties(byo: bpy.types.Object, object: dict, is_instanced: bool = False):
    if is_instanced:
        transform = object["TransformData"]
        if "Rotation" in transform:
            byo.rotation_mode = 'QUATERNION'
            byo.rotation_quaternion = [
                (-transform["Rotation"]["W"]),
                (transform["Rotation"]["X"]),
                (-transform["Rotation"]["Y"]),
                (transform["Rotation"]["Z"])
            ]
        if "Translation" in transform:
            byo.location = [
                byo.location[0] + (transform["Translation"]["X"] * 0.01),
                byo.location[1] + (transform["Translation"]["Y"] * -0.01),
                byo.location[2] + (transform["Translation"]["Z"] * 0.01)
            ]
        if "Scale3D" in transform:
            byo.scale = [
                transform["Scale3D"]["X"],
                transform["Scale3D"]["Y"],
                transform["Scale3D"]["Z"]
            ]
    else:
        if "RelativeLocation" in object:
            byo.location = [
                object["RelativeLocation"]["X"] * 0.01,
                object["RelativeLocation"]["Y"] * -0.01,
                object["RelativeLocation"]["Z"] * 0.01
            ]
        if "RelativeRotation" in object:
            # rotator.Roll2, -rotator.Pitch0, -rotator.Yaw1
            byo.rotation_mode = 'XYZ' # QUATERNION
            byo.rotation_euler = game_to_blender_rotations(
                object["RelativeRotation"]["Roll"],
                object["RelativeRotation"]["Pitch"],
                object["RelativeRotation"]["Yaw"]
            )

        if "RelativeScale3D" in object:
            byo.scale = [
                object["RelativeScale3D"]["X"],
                object["RelativeScale3D"]["Y"],
                object["RelativeScale3D"]["Z"]
            ]


def create_light(object_data, lights_collection):
    object_data['Properties']['RelativeRotation'] = object_data['RelativeRotation']

    # Set variables
    light_type = get_light_type(object_data)
    light_name = object_data["Outer"]
    light_props = object_data["Properties"]

    light_intensity = 0
    if "Intensity" in light_props:
        light_intensity = light_props["Intensity"]
    light_unit = "UNITLESS"
    if "IntensityUnits" in light_props:
        light_unit = "CANDELAS"
    cone_angle = 44 if light_type == "SPOT" else 90
    inner_cone_angle = 0
    if "OuterConeAngle" in light_props:
        cone_angle = light_props["OuterConeAngle"]
    if "InnerConeAngle" in light_props:
        inner_cone_angle = light_props["InnerConeAngle"]


    light_data = bpy.data.lights.new(name=light_name, type=light_type)
    light_object = bpy.data.objects.new(name=light_name, object_data=light_data)
    lights_collection.objects.link(light_object)

    light_object.data.use_custom_distance = True
    light_object.data.cutoff_distance = 1000 * 0.01 # default value

    if light_type == "SPOT":
        light_object.data.spot_size = radians(cone_angle)
        light_object.data.spot_blend = 1.0 - (radians(inner_cone_angle) / radians(cone_angle))


    for prop_name, prop_value in light_props.items():
        if "Intensity" == prop_name:
            if light_type == "POINT":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity * 683 / (4 * pi))
                else:
                    light_object.data.energy = ((99.5*(1-cos(cone_angle/2)))*light_intensity)
            if light_type == "AREA":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity * 683 / (4 * pi))
                else:
                    light_object.data.energy = (light_intensity*199)/683
            if light_type == "SPOT":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity * 683 / (4 * pi))
                else:
                    light_object.data.energy = ((99.5*(1-cos(cone_angle/2)))*light_intensity)

        if "LightColor" == prop_name:
            light_object.data.color = get_rgb_255(prop_value)[:-1]
        if "SourceRadius" == prop_name:
            # if light_type == "SPOT":
            #     light_object.data.shadow_soft_size = prop_value / 0.01
            # else:
            light_object.data.shadow_soft_size = prop_value * 0.01
        if "CastShadows" == prop_name:
            light_object.data.use_shadow = prop_value
            if hasattr(light_object.data, "cycles"):
                light_object.data.cycles.cast_shadow = prop_value

        if "AttenuationRadius" == prop_name:
            light_object.data.use_custom_distance = True
            light_object.data.cutoff_distance = prop_value * 0.01

        if light_type == "AREA":
            light_object.data.shape = 'RECTANGLE'
            if "SourceWidth" == prop_name:
                light_object.data.size = prop_value * 0.01
            if "SourceHeight" == prop_name:
                light_object.data.size_y = prop_value * 0.01

    set_properties(byo=light_object, object=light_props)

    return light_object

def srgb2lin(s):
    if s <= 0.0404482362771082:
        lin = s / 12.92
    else:
        lin = pow(((s + 0.055) / 1.055), 2.4)
    return lin
