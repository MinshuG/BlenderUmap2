import bpy
from mathutils import Vector
from math import cos, pi, radians, degrees

def get_rgb_255(pv: dict) -> tuple:
            return (
                pv["R"] / 255,
                pv["G"] / 255,
                pv["B"] / 255,
                pv["A"] / 255
            )

def get_light_type(object):
    if "Point" in object["Type"]:
        return "POINT"
    if "Spot" in object["Type"]:
        return "SPOT"
    if "RectLightComponent" in object["Type"]:
        return "AREA"

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
            x = object["RelativeRotation"]["Roll"]-90 if object["RelativeRotation"]["Roll"] != 0.0 and object["RelativeRotation"]["Roll"] > -10 else object["RelativeRotation"]["Roll"]
            if object["RelativeRotation"]["Roll"] > 180.0: x += 90
            byo.rotation_mode = 'XYZ'
            byo.rotation_euler = [
                # rotator.Roll2, -rotator.Pitch0, -rotator.Yaw1
                radians(x),
                radians(-object["RelativeRotation"]["Pitch"]),
                radians(-object["RelativeRotation"]["Yaw"])
            ]

            # original
            # byo.rotation_mode = 'XYZ'
            # byo.rotation_euler = [
            #     # rotator.Roll2, -rotator.Pitch0, -rotator.Yaw1
            #     radians(object["RelativeRotation"]["Roll"]),
            #     radians(-object["RelativeRotation"]["Pitch"]),
            #     radians(-object["RelativeRotation"]["Yaw"])
            # ]

            # y = object["RelativeRotation"]["Pitch"]
            # z = object["RelativeRotation"]["Yaw"]
            # print(f"X: {x} Y: {y} Z: {z}")
            # print(f"X: {degrees(byo.rotation_euler[0])} Y: {degrees(byo.rotation_euler[1])} Z: {degrees(byo.rotation_euler[2])}")
            # print("--------------------------------")

        if "RelativeScale3D" in object:
            byo.scale = [
                object["RelativeScale3D"]["X"],
                object["RelativeScale3D"]["Y"],
                object["RelativeScale3D"]["Z"]
            ]


def create_light(light, lights_collection):
    object_data = light["Props"]
    # light['Props']['Properties']['RelativeLocation'] = light['Location']
    # light['Props']['Properties']['RelativeRotation'] = light['Rotation']


    # Set variables
    light_type = get_light_type(object_data)
    light_name = object_data["Outer"]
    light_props = object_data["Properties"]

    light_intensity = 0
    if "Intensity" in object_data["Properties"]:
        light_intensity = object_data["Properties"]["Intensity"]
    light_unit = "UNITLESS"
    if "IntensityUnits" in object_data["Properties"]:
        light_unit = "CANDELAS"
    cone_angle = 90
    if "OuterConeAngle" in object_data["Properties"]:
        cone_angle = object_data["Properties"]["OuterConeAngle"]

    light_data = bpy.data.lights.new(name=light_name, type=light_type)
    light_object = bpy.data.objects.new(name=light_name, object_data=light_data)
    light_object.delta_rotation_euler = (radians(0.0), radians(-90), 0.0)  # still broken??
    lights_collection.objects.link(light_object)

    for prop_name, prop_value in light_props.items():
        # OtherTypes.append(prop_name)
        if "Intensity" == prop_name:
            if light_type == "POINT":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity*4*pi)/683
                else:
                    light_object.data.energy = (light_intensity*49.7)/683
            if light_type == "AREA":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity*2*pi)/683
                else:
                    light_object.data.energy = (light_intensity*199)/683
            if light_type == "SPOT":
                if light_unit == "CANDELAS":
                    light_object.data.energy = (light_intensity*2*pi*(1-cos(cone_angle/2)))/683
                else:
                    light_object.data.energy = ((99.5*(1-cos(cone_angle/2)))*light_intensity)

        if "LightColor" == prop_name:
            light_object.data.color = get_rgb_255(prop_value)[:-1]
        if "SourceRadius" == prop_name:
            if light_type == "SPOT":
                light_object.data.shadow_soft_size = prop_value * 0.01
            else:
                light_object.data.shadow_soft_size = prop_value * 0.1
        if "CastShadows" == prop_name:
            light_object.data.use_shadow = prop_value
            if hasattr(light_object.data, "cycles"):
                light_object.data.cycles.cast_shadow = prop_value


        if light_type == "AREA":
            light_object.data.shape = 'RECTANGLE'
            if "SourceWidth" == prop_name:
                light_object.data.size = prop_value * 0.01
            if "SourceHeight" == prop_name:
                light_object.data.size_y = prop_value * 0.01

        if light_type == "SPOT":
            if "InnerConeAngle" == prop_name:
                light_object.data.spot_blend = 1 # TODO handle this correctly
            if "OuterConeAngle" == prop_name:
                light_object.data.spot_size = radians(prop_value)



    set_properties(byo=light_object, object=light_props)

    return light_object