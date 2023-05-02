from dataclasses import dataclass
from typing import List

import bpy


@dataclass
class Textures:
    Diffuse: List[str]
    Normal: List[str]
    Specular: List[str]
    Emission: List[str]
    Mask: List[str]

    def to_dict(self):
        return {
            "Diffuse": self.Diffuse,
            "Normal": self.Normal,
            "Specular": self.Specular,
            "Emission": self.Emission,
            "MaskTexture": self.Mask
        }


class TextureMapping:
    UV1: Textures
    UV2: Textures
    UV3: Textures
    UV4: Textures

    def __init__(self) -> None:
        self.UV1 = Textures(
            ["Trunk_BaseColor", "Diffuse", "DiffuseTexture", "Base_Color_Tex", "Tex_Color"],
            ["Trunk_Normal", "Normals", "Normal", "Base_Normal_Tex", "Tex_Normal"],
            ["Trunk_Specular", "SpecularMasks"],
            ["EmissiveTexture"],
            ["MaskTexture"]
        )
        self.UV2 = Textures(
            ["Diffuse_Texture_2"],
            ["Normals_Texture_2"],
            ["Specular_Texture_2"],
            ["Emissive_Texture_2"],
            ["MaskTexture_2"]
        )
        self.UV3 = Textures(
            ["Diffuse_Texture_3"],
            ["Normals_Texture_3"],
            ["Specular_Texture_3"],
            ["Emissive_Texture_3"],
            ["MaskTexture_3"]
        )
        self.UV4 = Textures(
            ["Diffuse_Texture_4"],
            ["Normals_Texture_4"],
            ["Specular_Texture_4"],
            ["Emissive_Texture_4"],
            ["MaskTexture_4"]
        )

    def to_dict(self):
        return {
            "UV1": self.UV1.to_dict(),
            "UV2": self.UV2.to_dict(),
            "UV3": self.UV3.to_dict(),
            "UV4": self.UV4.to_dict()
        }

def textures_to_mapping(context: bpy.context) -> TextureMapping:
    temp_map = TextureMapping()
    for i in range(1, 5):  # 4UVs
        for t in ["Diffuse", "Normal", "Specular", "Emission", "Mask"]:
            textures = getattr(context, f"{t}_{i}".lower(), "").split(",")
            textures = [x.strip() for x in textures]
            if len(t) != 0 and textures != ['']:
                setattr(getattr(temp_map, f"UV{i}"), t, textures)  # temp_map.UV{i}.{Texture} = textures
    return temp_map
